
# === NexusCore/openenv\Lib\site-packages\nltk\sem\boxer.py ===
# Natural Language Toolkit: Interface to Boxer
# <http://svn.ask.it.usyd.edu.au/trac/candc/wiki/boxer>
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# Copyright (C) 2001-2024 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
An interface to Boxer.

This interface relies on the latest version of the development (subversion) version of
C&C and Boxer.

Usage
=====

Set the environment variable CANDC to the bin directory of your CandC installation.
The models directory should be in the CandC root directory.
For example::

    /path/to/candc/
    bin/
        candc
        boxer
    models/
        boxer/
"""

import operator
import os
import re
import subprocess
import tempfile
from functools import reduce
from optparse import OptionParser

from nltk.internals import find_binary
from nltk.sem.drt import (
    DRS,
    DrtApplicationExpression,
    DrtEqualityExpression,
    DrtNegatedExpression,
    DrtOrExpression,
    DrtParser,
    DrtProposition,
    DrtTokens,
    DrtVariableExpression,
)
from nltk.sem.logic import (
    ExpectedMoreTokensException,
    LogicalExpressionException,
    UnexpectedTokenException,
    Variable,
)


class Boxer:
    """
    This class is an interface to Johan Bos's program Boxer, a wide-coverage
    semantic parser that produces Discourse Representation Structures (DRSs).
    """

    def __init__(
        self,
        boxer_drs_interpreter=None,
        elimeq=False,
        bin_dir=None,
        verbose=False,
        resolve=True,
    ):
        """
        :param boxer_drs_interpreter: A class that converts from the
            ``AbstractBoxerDrs`` object hierarchy to a different object.  The
            default is ``NltkDrtBoxerDrsInterpreter``, which converts to the NLTK
            DRT hierarchy.
        :param elimeq: When set to true, Boxer removes all equalities from the
            DRSs and discourse referents standing in the equality relation are
            unified, but only if this can be done in a meaning-preserving manner.
        :param resolve: When set to true, Boxer will resolve all anaphoric DRSs and perform merge-reduction.
            Resolution follows Van der Sandt's theory of binding and accommodation.
        """
        if boxer_drs_interpreter is None:
            boxer_drs_interpreter = NltkDrtBoxerDrsInterpreter()
        self._boxer_drs_interpreter = boxer_drs_interpreter

        self._resolve = resolve
        self._elimeq = elimeq

        self.set_bin_dir(bin_dir, verbose)

    def set_bin_dir(self, bin_dir, verbose=False):
        self._candc_bin = self._find_binary("candc", bin_dir, verbose)
        self._candc_models_path = os.path.normpath(
            os.path.join(self._candc_bin[:-5], "../models")
        )
        self._boxer_bin = self._find_binary("boxer", bin_dir, verbose)

    def interpret(self, input, discourse_id=None, question=False, verbose=False):
        """
        Use Boxer to give a first order representation.

        :param input: str Input sentence to parse
        :param occur_index: bool Should predicates be occurrence indexed?
        :param discourse_id: str An identifier to be inserted to each occurrence-indexed predicate.
        :return: ``drt.DrtExpression``
        """
        discourse_ids = [discourse_id] if discourse_id is not None else None
        (d,) = self.interpret_multi_sents([[input]], discourse_ids, question, verbose)
        if not d:
            raise Exception(f'Unable to interpret: "{input}"')
        return d

    def interpret_multi(self, input, discourse_id=None, question=False, verbose=False):
        """
        Use Boxer to give a first order representation.

        :param input: list of str Input sentences to parse as a single discourse
        :param occur_index: bool Should predicates be occurrence indexed?
        :param discourse_id: str An identifier to be inserted to each occurrence-indexed predicate.
        :return: ``drt.DrtExpression``
        """
        discourse_ids = [discourse_id] if discourse_id is not None else None
        (d,) = self.interpret_multi_sents([input], discourse_ids, question, verbose)
        if not d:
            raise Exception(f'Unable to interpret: "{input}"')
        return d

    def interpret_sents(
        self, inputs, discourse_ids=None, question=False, verbose=False
    ):
        """
        Use Boxer to give a first order representation.

        :param inputs: list of str Input sentences to parse as individual discourses
        :param occur_index: bool Should predicates be occurrence indexed?
        :param discourse_ids: list of str Identifiers to be inserted to each occurrence-indexed predicate.
        :return: list of ``drt.DrtExpression``
        """
        return self.interpret_multi_sents(
            [[input] for input in inputs], discourse_ids, question, verbose
        )

    def interpret_multi_sents(
        self, inputs, discourse_ids=None, question=False, verbose=False
    ):
        """
        Use Boxer to give a first order representation.

        :param inputs: list of list of str Input discourses to parse
        :param occur_index: bool Should predicates be occurrence indexed?
        :param discourse_ids: list of str Identifiers to be inserted to each occurrence-indexed predicate.
        :return: ``drt.DrtExpression``
        """
        if discourse_ids is not None:
            assert len(inputs) == len(discourse_ids)
            assert reduce(operator.and_, (id is not None for id in discourse_ids))
            use_disc_id = True
        else:
            discourse_ids = list(map(str, range(len(inputs))))
            use_disc_id = False

        candc_out = self._call_candc(inputs, discourse_ids, question, verbose=verbose)
        boxer_out = self._call_boxer(candc_out, verbose=verbose)

        #        if 'ERROR: input file contains no ccg/2 terms.' in boxer_out:
        #            raise UnparseableInputException('Could not parse with candc: "%s"' % input_str)

        drs_dict = self._parse_to_drs_dict(boxer_out, use_disc_id)
        return [drs_dict.get(id, None) for id in discourse_ids]

    def _call_candc(self, inputs, discourse_ids, question, verbose=False):
        """
        Call the ``candc`` binary with the given input.

        :param inputs: list of list of str Input discourses to parse
        :param discourse_ids: list of str Identifiers to be inserted to each occurrence-indexed predicate.
        :param filename: str A filename for the output file
        :return: stdout
        """
        args = [
            "--models",
            os.path.join(self._candc_models_path, ["boxer", "questions"][question]),
            "--candc-printer",
            "boxer",
        ]
        return self._call(
            "\n".join(
                sum(
                    ([f"<META>'{id}'"] + d for d, id in zip(inputs, discourse_ids)),
                    [],
                )
            ),
            self._candc_bin,
            args,
            verbose,
        )

    def _call_boxer(self, candc_out, verbose=False):
        """
        Call the ``boxer`` binary with the given input.

        :param candc_out: str output from C&C parser
        :return: stdout
        """
        f = None
        try:
            fd, temp_filename = tempfile.mkstemp(
                prefix="boxer-", suffix=".in", text=True
            )
            f = os.fdopen(fd, "w")
            f.write(candc_out.decode("utf-8"))
        finally:
            if f:
                f.close()

        args = [
            "--box",
            "false",
            "--semantics",
            "drs",
            #'--flat', 'false', # removed from boxer
            "--resolve",
            ["false", "true"][self._resolve],
            "--elimeq",
            ["false", "true"][self._elimeq],
            "--format",
            "prolog",
            "--instantiate",
            "true",
            "--input",
            temp_filename,
        ]
        stdout = self._call(None, self._boxer_bin, args, verbose)
        os.remove(temp_filename)
        return stdout

    def _find_binary(self, name, bin_dir, verbose=False):
        return find_binary(
            name,
            path_to_bin=bin_dir,
            env_vars=["CANDC"],
            url="http://svn.ask.it.usyd.edu.au/trac/candc/",
            binary_names=[name, name + ".exe"],
            verbose=verbose,
        )

    def _call(self, input_str, binary, args=[], verbose=False):
        """
        Call the binary with the given input.

        :param input_str: A string whose contents are used as stdin.
        :param binary: The location of the binary to call
        :param args: A list of command-line arguments.
        :return: stdout
        """
        if verbose:
            print("Calling:", binary)
            print("Args:", args)
            print("Input:", input_str)
            print("Command:", binary + " " + " ".join(args))

        # Call via a subprocess
        if input_str is None:
            cmd = [binary] + args
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            cmd = 'echo "{}" | {} {}'.format(input_str, binary, " ".join(args))
            p = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
            )
        stdout, stderr = p.communicate()

        if verbose:
            print("Return code:", p.returncode)
            if stdout:
                print("stdout:\n", stdout, "\n")
            if stderr:
                print("stderr:\n", stderr, "\n")
        if p.returncode != 0:
            raise Exception(
                "ERROR CALLING: {} {}\nReturncode: {}\n{}".format(
                    binary, " ".join(args), p.returncode, stderr
                )
            )

        return stdout

    def _parse_to_drs_dict(self, boxer_out, use_disc_id):
        lines = boxer_out.decode("utf-8").split("\n")
        drs_dict = {}
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith("id("):
                comma_idx = line.index(",")
                discourse_id = line[3:comma_idx]
                if discourse_id[0] == "'" and discourse_id[-1] == "'":
                    discourse_id = discourse_id[1:-1]
                drs_id = line[comma_idx + 1 : line.index(")")]
                i += 1
                line = lines[i]
                assert line.startswith(f"sem({drs_id},")
                if line[-4:] == "').'":
                    line = line[:-4] + ")."
                assert line.endswith(")."), f"can't parse line: {line}"

                search_start = len(f"sem({drs_id},[")
                brace_count = 1
                drs_start = -1
                for j, c in enumerate(line[search_start:]):
                    if c == "[":
                        brace_count += 1
                    if c == "]":
                        brace_count -= 1
                        if brace_count == 0:
                            drs_start = search_start + j + 1
                            if line[drs_start : drs_start + 3] == "','":
                                drs_start = drs_start + 3
                            else:
                                drs_start = drs_start + 1
                            break
                assert drs_start > -1

                drs_input = line[drs_start:-2].strip()
                parsed = self._parse_drs(drs_input, discourse_id, use_disc_id)
                drs_dict[discourse_id] = self._boxer_drs_interpreter.interpret(parsed)
            i += 1
        return drs_dict

    def _parse_drs(self, drs_string, discourse_id, use_disc_id):
        return BoxerOutputDrsParser([None, discourse_id][use_disc_id]).parse(drs_string)


class BoxerOutputDrsParser(DrtParser):
    def __init__(self, discourse_id=None):
        """
        This class is used to parse the Prolog DRS output from Boxer into a
        hierarchy of python objects.
        """
        DrtParser.__init__(self)
        self.discourse_id = discourse_id
        self.sentence_id_offset = None
        self.quote_chars = [("'", "'", "\\", False)]

    def parse(self, data, signature=None):
        return DrtParser.parse(self, data, signature)

    def get_all_symbols(self):
        return ["(", ")", ",", "[", "]", ":"]

    def handle(self, tok, context):
        return self.handle_drs(tok)

    def attempt_adjuncts(self, expression, context):
        return expression

    def parse_condition(self, indices):
        """
        Parse a DRS condition

        :return: list of ``DrtExpression``
        """
        tok = self.token()
        accum = self.handle_condition(tok, indices)
        if accum is None:
            raise UnexpectedTokenException(tok)
        return accum

    def handle_drs(self, tok):
        if tok == "drs":
            return self.parse_drs()
        elif tok in ["merge", "smerge"]:
            return self._handle_binary_expression(self._make_merge_expression)(None, [])
        elif tok in ["alfa"]:
            return self._handle_alfa(self._make_merge_expression)(None, [])

    def handle_condition(self, tok, indices):
        """
        Handle a DRS condition

        :param indices: list of int
        :return: list of ``DrtExpression``
        """
        if tok == "not":
            return [self._handle_not()]

        if tok == "or":
            conds = [self._handle_binary_expression(self._make_or_expression)]
        elif tok == "imp":
            conds = [self._handle_binary_expression(self._make_imp_expression)]
        elif tok == "eq":
            conds = [self._handle_eq()]
        elif tok == "prop":
            conds = [self._handle_prop()]

        elif tok == "pred":
            conds = [self._handle_pred()]
        elif tok == "named":
            conds = [self._handle_named()]
        elif tok == "rel":
            conds = [self._handle_rel()]
        elif tok == "timex":
            conds = self._handle_timex()
        elif tok == "card":
            conds = [self._handle_card()]

        elif tok == "whq":
            conds = [self._handle_whq()]
        elif tok == "duplex":
            conds = [self._handle_duplex()]

        else:
            conds = []

        return sum(
            (
                [cond(sent_index, word_indices) for cond in conds]
                for sent_index, word_indices in self._sent_and_word_indices(indices)
            ),
            [],
        )

    def _handle_not(self):
        self.assertToken(self.token(), "(")
        drs = self.process_next_expression(None)
        self.assertToken(self.token(), ")")
        return BoxerNot(drs)

    def _handle_pred(self):
        # pred(_G3943, dog, n, 0)
        self.assertToken(self.token(), "(")
        variable = self.parse_variable()
        self.assertToken(self.token(), ",")
        name = self.token()
        self.assertToken(self.token(), ",")
        pos = self.token()
        self.assertToken(self.token(), ",")
        sense = int(self.token())
        self.assertToken(self.token(), ")")

        def _handle_pred_f(sent_index, word_indices):
            return BoxerPred(
                self.discourse_id, sent_index, word_indices, variable, name, pos, sense
            )

        return _handle_pred_f

    def _handle_duplex(self):
        # duplex(whq, drs(...), var, drs(...))
        self.assertToken(self.token(), "(")
        # self.assertToken(self.token(), '[')
        ans_types = []
        # while self.token(0) != ']':
        #     cat = self.token()
        #     self.assertToken(self.token(), ':')
        #     if cat == 'des':
        #         ans_types.append(self.token())
        #     elif cat == 'num':
        #         ans_types.append('number')
        #         typ = self.token()
        #         if typ == 'cou':
        #             ans_types.append('count')
        #         else:
        #             ans_types.append(typ)
        #     else:
        #         ans_types.append(self.token())
        # self.token() #swallow the ']'

        self.assertToken(self.token(), "whq")
        self.assertToken(self.token(), ",")
        d1 = self.process_next_expression(None)
        self.assertToken(self.token(), ",")
        ref = self.parse_variable()
        self.assertToken(self.token(), ",")
        d2 = self.process_next_expression(None)
        self.assertToken(self.token(), ")")
        return lambda sent_index, word_indices: BoxerWhq(
            self.discourse_id, sent_index, word_indices, ans_types, d1, ref, d2
        )

    def _handle_named(self):
        # named(x0, john, per, 0)
        self.assertToken(self.token(), "(")
        variable = self.parse_variable()
        self.assertToken(self.token(), ",")
        name = self.token()
        self.assertToken(self.token(), ",")
        type = self.token()
        self.assertToken(self.token(), ",")
        sense = self.token()  # as per boxer rev 2554
        self.assertToken(self.token(), ")")
        return lambda sent_index, word_indices: BoxerNamed(
            self.discourse_id, sent_index, word_indices, variable, name, type, sense
        )

    def _handle_rel(self):
        # rel(_G3993, _G3943, agent, 0)
        self.assertToken(self.token(), "(")
        var1 = self.parse_variable()
        self.assertToken(self.token(), ",")
        var2 = self.parse_variable()
        self.assertToken(self.token(), ",")
        rel = self.token()
        self.assertToken(self.token(), ",")
        sense = int(self.token())
        self.assertToken(self.token(), ")")
        return lambda sent_index, word_indices: BoxerRel(
            self.discourse_id, sent_index, word_indices, var1, var2, rel, sense
        )

    def _handle_timex(self):
        # timex(_G18322, date([]: (+), []:'XXXX', [1004]:'04', []:'XX'))
        self.assertToken(self.token(), "(")
        arg = self.parse_variable()
        self.assertToken(self.token(), ",")
        new_conds = self._handle_time_expression(arg)
        self.assertToken(self.token(), ")")
        return new_conds

    def _handle_time_expression(self, arg):
        # date([]: (+), []:'XXXX', [1004]:'04', []:'XX')
        tok = self.token()
        self.assertToken(self.token(), "(")
        if tok == "date":
            conds = self._handle_date(arg)
        elif tok == "time":
            conds = self._handle_time(arg)
        else:
            return None
        self.assertToken(self.token(), ")")

        def func_gen(x):
            return lambda sent_index, word_indices: x

        return [
            lambda sent_index, word_indices: BoxerPred(
                self.discourse_id, sent_index, word_indices, arg, tok, "n", 0
            )
        ] + [func_gen(cond) for cond in conds]

    def _handle_date(self, arg):
        # []: (+), []:'XXXX', [1004]:'04', []:'XX'
        conds = []
        ((sent_index, word_indices),) = self._sent_and_word_indices(
            self._parse_index_list()
        )
        self.assertToken(self.token(), "(")
        pol = self.token()
        self.assertToken(self.token(), ")")
        conds.append(
            BoxerPred(
                self.discourse_id,
                sent_index,
                word_indices,
                arg,
                f"date_pol_{pol}",
                "a",
                0,
            )
        )
        self.assertToken(self.token(), ",")

        ((sent_index, word_indices),) = self._sent_and_word_indices(
            self._parse_index_list()
        )
        year = self.token()
        if year != "XXXX":
            year = year.replace(":", "_")
            conds.append(
                BoxerPred(
                    self.discourse_id,
                    sent_index,
                    word_indices,
                    arg,
                    f"date_year_{year}",
                    "a",
                    0,
                )
            )
        self.assertToken(self.token(), ",")

        ((sent_index, word_indices),) = self._sent_and_word_indices(
            self._parse_index_list()
        )
        month = self.token()
        if month != "XX":
            conds.append(
                BoxerPred(
                    self.discourse_id,
                    sent_index,
                    word_indices,
                    arg,
                    f"date_month_{month}",
                    "a",
                    0,
                )
            )
        self.assertToken(self.token(), ",")

        ((sent_index, word_indices),) = self._sent_and_word_indices(
            self._parse_index_list()
        )
        day = self.token()
        if day != "XX":
            conds.append(
                BoxerPred(
                    self.discourse_id,
                    sent_index,
                    word_indices,
                    arg,
                    f"date_day_{day}",
                    "a",
                    0,
                )
            )

        return conds

    def _handle_time(self, arg):
        # time([1018]:'18', []:'XX', []:'XX')
        conds = []
        self._parse_index_list()
        hour = self.token()
        if hour != "XX":
            conds.append(self._make_atom("r_hour_2", arg, hour))
        self.assertToken(self.token(), ",")

        self._parse_index_list()
        min = self.token()
        if min != "XX":
            conds.append(self._make_atom("r_min_2", arg, min))
        self.assertToken(self.token(), ",")

        self._parse_index_list()
        sec = self.token()
        if sec != "XX":
            conds.append(self._make_atom("r_sec_2", arg, sec))

        return conds

    def _handle_card(self):
        # card(_G18535, 28, ge)
        self.assertToken(self.token(), "(")
        variable = self.parse_variable()
        self.assertToken(self.token(), ",")
        value = self.token()
        self.assertToken(self.token(), ",")
        type = self.token()
        self.assertToken(self.token(), ")")
        return lambda sent_index, word_indices: BoxerCard(
            self.discourse_id, sent_index, word_indices, variable, value, type
        )

    def _handle_prop(self):
        # prop(_G15949, drs(...))
        self.assertToken(self.token(), "(")
        variable = self.parse_variable()
        self.assertToken(self.token(), ",")
        drs = self.process_next_expression(None)
        self.assertToken(self.token(), ")")
        return lambda sent_index, word_indices: BoxerProp(
            self.discourse_id, sent_index, word_indices, variable, drs
        )

    def _parse_index_list(self):
        # [1001,1002]:
        indices = []
        self.assertToken(self.token(), "[")
        while self.token(0) != "]":
            indices.append(self.parse_index())
            if self.token(0) == ",":
                self.token()  # swallow ','
        self.token()  # swallow ']'
        self.assertToken(self.token(), ":")
        return indices

    def parse_drs(self):
        # drs([[1001]:_G3943],
        #    [[1002]:pred(_G3943, dog, n, 0)]
        #   )
        self.assertToken(self.token(), "(")
        self.assertToken(self.token(), "[")
        refs = set()
        while self.token(0) != "]":
            indices = self._parse_index_list()
            refs.add(self.parse_variable())
            if self.token(0) == ",":
                self.token()  # swallow ','
        self.token()  # swallow ']'
        self.assertToken(self.token(), ",")
        self.assertToken(self.token(), "[")
        conds = []
        while self.token(0) != "]":
            indices = self._parse_index_list()
            conds.extend(self.parse_condition(indices))
            if self.token(0) == ",":
                self.token()  # swallow ','
        self.token()  # swallow ']'
        self.assertToken(self.token(), ")")
        return BoxerDrs(list(refs), conds)

    def _handle_binary_expression(self, make_callback):
        self.assertToken(self.token(), "(")
        drs1 = self.process_next_expression(None)
        self.assertToken(self.token(), ",")
        drs2 = self.process_next_expression(None)
        self.assertToken(self.token(), ")")
        return lambda sent_index, word_indices: make_callback(
            sent_index, word_indices, drs1, drs2
        )

    def _handle_alfa(self, make_callback):
        self.assertToken(self.token(), "(")
        type = self.token()
        self.assertToken(self.token(), ",")
        drs1 = self.process_next_expression(None)
        self.assertToken(self.token(), ",")
        drs2 = self.process_next_expression(None)
        self.assertToken(self.token(), ")")
        return lambda sent_index, word_indices: make_callback(
            sent_index, word_indices, drs1, drs2
        )

    def _handle_eq(self):
        self.assertToken(self.token(), "(")
        var1 = self.parse_variable()
        self.assertToken(self.token(), ",")
        var2 = self.parse_variable()
        self.assertToken(self.token(), ")")
        return lambda sent_index, word_indices: BoxerEq(
            self.discourse_id, sent_index, word_indices, var1, var2
        )

    def _handle_whq(self):
        self.assertToken(self.token(), "(")
        self.assertToken(self.token(), "[")
        ans_types = []
        while self.token(0) != "]":
            cat = self.token()
            self.assertToken(self.token(), ":")
            if cat == "des":
                ans_types.append(self.token())
            elif cat == "num":
                ans_types.append("number")
                typ = self.token()
                if typ == "cou":
                    ans_types.append("count")
                else:
                    ans_types.append(typ)
            else:
                ans_types.append(self.token())
        self.token()  # swallow the ']'

        self.assertToken(self.token(), ",")
        d1 = self.process_next_expression(None)
        self.assertToken(self.token(), ",")
        ref = self.parse_variable()
        self.assertToken(self.token(), ",")
        d2 = self.process_next_expression(None)
        self.assertToken(self.token(), ")")
        return lambda sent_index, word_indices: BoxerWhq(
            self.discourse_id, sent_index, word_indices, ans_types, d1, ref, d2
        )

    def _make_merge_expression(self, sent_index, word_indices, drs1, drs2):
        return BoxerDrs(drs1.refs + drs2.refs, drs1.conds + drs2.conds)

    def _make_or_expression(self, sent_index, word_indices, drs1, drs2):
        return BoxerOr(self.discourse_id, sent_index, word_indices, drs1, drs2)

    def _make_imp_expression(self, sent_index, word_indices, drs1, drs2):
        return BoxerDrs(drs1.refs, drs1.conds, drs2)

    def parse_variable(self):
        var = self.token()
        assert re.match(r"^[exps]\d+$", var), var
        return var

    def parse_index(self):
        return int(self.token())

    def _sent_and_word_indices(self, indices):
        """
        :return: list of (sent_index, word_indices) tuples
        """
        sent_indices = {(i / 1000) - 1 for i in indices if i >= 0}
        if sent_indices:
            pairs = []
            for sent_index in sent_indices:
                word_indices = [
                    (i % 1000) - 1 for i in indices if sent_index == (i / 1000) - 1
                ]
                pairs.append((sent_index, word_indices))
            return pairs
        else:
            word_indices = [(i % 1000) - 1 for i in indices]
            return [(None, word_indices)]


class BoxerDrsParser(DrtParser):
    """
    Reparse the str form of subclasses of ``AbstractBoxerDrs``
    """

    def __init__(self, discourse_id=None):
        DrtParser.__init__(self)
        self.discourse_id = discourse_id

    def get_all_symbols(self):
        return [
            DrtTokens.OPEN,
            DrtTokens.CLOSE,
            DrtTokens.COMMA,
            DrtTokens.OPEN_BRACKET,
            DrtTokens.CLOSE_BRACKET,
        ]

    def attempt_adjuncts(self, expression, context):
        return expression

    def handle(self, tok, context):
        try:
            #             if tok == 'drs':
            #                 self.assertNextToken(DrtTokens.OPEN)
            #                 label = int(self.token())
            #                 self.assertNextToken(DrtTokens.COMMA)
            #                 refs = list(map(int, self.handle_refs()))
            #                 self.assertNextToken(DrtTokens.COMMA)
            #                 conds = self.handle_conds(None)
            #                 self.assertNextToken(DrtTokens.CLOSE)
            #                 return BoxerDrs(label, refs, conds)
            if tok == "pred":
                self.assertNextToken(DrtTokens.OPEN)
                disc_id = (
                    self.discourse_id if self.discourse_id is not None else self.token()
                )
                self.assertNextToken(DrtTokens.COMMA)
                sent_id = self.nullableIntToken()
                self.assertNextToken(DrtTokens.COMMA)
                word_ids = list(map(int, self.handle_refs()))
                self.assertNextToken(DrtTokens.COMMA)
                variable = int(self.token())
                self.assertNextToken(DrtTokens.COMMA)
                name = self.token()
                self.assertNextToken(DrtTokens.COMMA)
                pos = self.token()
                self.assertNextToken(DrtTokens.COMMA)
                sense = int(self.token())
                self.assertNextToken(DrtTokens.CLOSE)
                return BoxerPred(disc_id, sent_id, word_ids, variable, name, pos, sense)
            elif tok == "named":
                self.assertNextToken(DrtTokens.OPEN)
                disc_id = (
                    self.discourse_id if self.discourse_id is not None else self.token()
                )
                self.assertNextToken(DrtTokens.COMMA)
                sent_id = int(self.token())
                self.assertNextToken(DrtTokens.COMMA)
                word_ids = map(int, self.handle_refs())
                self.assertNextToken(DrtTokens.COMMA)
                variable = int(self.token())
                self.assertNextToken(DrtTokens.COMMA)
                name = self.token()
                self.assertNextToken(DrtTokens.COMMA)
                type = self.token()
                self.assertNextToken(DrtTokens.COMMA)
                sense = int(self.token())
                self.assertNextToken(DrtTokens.CLOSE)
                return BoxerNamed(
                    disc_id, sent_id, word_ids, variable, name, type, sense
                )
            elif tok == "rel":
                self.assertNextToken(DrtTokens.OPEN)
                disc_id = (
                    self.discourse_id if self.discourse_id is not None else self.token()
                )
                self.assertNextToken(DrtTokens.COMMA)
                sent_id = self.nullableIntToken()
                self.assertNextToken(DrtTokens.COMMA)
                word_ids = list(map(int, self.handle_refs()))
                self.assertNextToken(DrtTokens.COMMA)
                var1 = int(self.token())
                self.assertNextToken(DrtTokens.COMMA)
                var2 = int(self.token())
                self.assertNextToken(DrtTokens.COMMA)
                rel = self.token()
                self.assertNextToken(DrtTokens.COMMA)
                sense = int(self.token())
                self.assertNextToken(DrtTokens.CLOSE)
                return BoxerRel(disc_id, sent_id, word_ids, var1, var2, rel, sense)
            elif tok == "prop":
                self.assertNextToken(DrtTokens.OPEN)
                disc_id = (
                    self.discourse_id if self.discourse_id is not None else self.token()
                )
                self.assertNextToken(DrtTokens.COMMA)
                sent_id = int(self.token())
                self.assertNextToken(DrtTokens.COMMA)
                word_ids = list(map(int, self.handle_refs()))
                self.assertNextToken(DrtTokens.COMMA)
                variable = int(self.token())
                self.assertNextToken(DrtTokens.COMMA)
                drs = self.process_next_expression(None)
                self.assertNextToken(DrtTokens.CLOSE)
                return BoxerProp(disc_id, sent_id, word_ids, variable, drs)
            elif tok == "not":
                self.assertNextToken(DrtTokens.OPEN)
                drs = self.process_next_expression(None)
                self.assertNextToken(DrtTokens.CLOSE)
                return BoxerNot(drs)
            elif tok == "imp":
                self.assertNextToken(DrtTokens.OPEN)
                drs1 = self.process_next_expression(None)
                self.assertNextToken(DrtTokens.COMMA)
                drs2 = self.process_next_expression(None)
                self.assertNextToken(DrtTokens.CLOSE)
                return BoxerDrs(drs1.refs, drs1.conds, drs2)
            elif tok == "or":
                self.assertNextToken(DrtTokens.OPEN)
                disc_id = (
                    self.discourse_id if self.discourse_id is not None else self.token()
                )
                self.assertNextToken(DrtTokens.COMMA)
                sent_id = self.nullableIntToken()
                self.assertNextToken(DrtTokens.COMMA)
                word_ids = map(int, self.handle_refs())
                self.assertNextToken(DrtTokens.COMMA)
                drs1 = self.process_next_expression(None)
                self.assertNextToken(DrtTokens.COMMA)
                drs2 = self.process_next_expression(None)
                self.assertNextToken(DrtTokens.CLOSE)
                return BoxerOr(disc_id, sent_id, word_ids, drs1, drs2)
            elif tok == "eq":
                self.assertNextToken(DrtTokens.OPEN)
                disc_id = (
                    self.discourse_id if self.discourse_id is not None else self.token()
                )
                self.assertNextToken(DrtTokens.COMMA)
                sent_id = self.nullableIntToken()
                self.assertNextToken(DrtTokens.COMMA)
                word_ids = list(map(int, self.handle_refs()))
                self.assertNextToken(DrtTokens.COMMA)
                var1 = int(self.token())
                self.assertNextToken(DrtTokens.COMMA)
                var2 = int(self.token())
                self.assertNextToken(DrtTokens.CLOSE)
                return BoxerEq(disc_id, sent_id, word_ids, var1, var2)
            elif tok == "card":
                self.assertNextToken(DrtTokens.OPEN)
                disc_id = (
                    self.discourse_id if self.discourse_id is not None else self.token()
                )
                self.assertNextToken(DrtTokens.COMMA)
                sent_id = self.nullableIntToken()
                self.assertNextToken(DrtTokens.COMMA)
                word_ids = map(int, self.handle_refs())
                self.assertNextToken(DrtTokens.COMMA)
                var = int(self.token())
                self.assertNextToken(DrtTokens.COMMA)
                value = self.token()
                self.assertNextToken(DrtTokens.COMMA)
                type = self.token()
                self.assertNextToken(DrtTokens.CLOSE)
                return BoxerCard(disc_id, sent_id, word_ids, var, value, type)
            elif tok == "whq":
                self.assertNextToken(DrtTokens.OPEN)
                disc_id = (
                    self.discourse_id if self.discourse_id is not None else self.token()
                )
                self.assertNextToken(DrtTokens.COMMA)
                sent_id = self.nullableIntToken()
                self.assertNextToken(DrtTokens.COMMA)
                word_ids = list(map(int, self.handle_refs()))
                self.assertNextToken(DrtTokens.COMMA)
                ans_types = self.handle_refs()
                self.assertNextToken(DrtTokens.COMMA)
                drs1 = self.process_next_expression(None)
                self.assertNextToken(DrtTokens.COMMA)
                var = int(self.token())
                self.assertNextToken(DrtTokens.COMMA)
                drs2 = self.process_next_expression(None)
                self.assertNextToken(DrtTokens.CLOSE)
                return BoxerWhq(disc_id, sent_id, word_ids, ans_types, drs1, var, drs2)
        except Exception as e:
            raise LogicalExpressionException(self._currentIndex, str(e)) from e
        assert False, repr(tok)

    def nullableIntToken(self):
        t = self.token()
        return int(t) if t != "None" else None

    def get_next_token_variable(self, description):
        try:
            return self.token()
        except ExpectedMoreTokensException as e:
            raise ExpectedMoreTokensException(e.index, "Variable expected.") from e


class AbstractBoxerDrs:
    def variables(self):
        """
        :return: (set<variables>, set<events>, set<propositions>)
        """
        variables, events, propositions = self._variables()
        return (variables - (events | propositions), events, propositions - events)

    def variable_types(self):
        vartypes = {}
        for t, vars in zip(("z", "e", "p"), self.variables()):
            for v in vars:
                vartypes[v] = t
        return vartypes

    def _variables(self):
        """
        :return: (set<variables>, set<events>, set<propositions>)
        """
        return (set(), set(), set())

    def atoms(self):
        return set()

    def clean(self):
        return self

    def _clean_name(self, name):
        return name.replace("-", "_").replace("'", "_")

    def renumber_sentences(self, f):
        return self

    def __hash__(self):
        return hash(f"{self}")


class BoxerDrs(AbstractBoxerDrs):
    def __init__(self, refs, conds, consequent=None):
        AbstractBoxerDrs.__init__(self)
        self.refs = refs
        self.conds = conds
        self.consequent = consequent

    def _variables(self):
        variables = (set(), set(), set())
        for cond in self.conds:
            for s, v in zip(variables, cond._variables()):
                s.update(v)
        if self.consequent is not None:
            for s, v in zip(variables, self.consequent._variables()):
                s.update(v)
        return variables

    def atoms(self):
        atoms = reduce(operator.or_, (cond.atoms() for cond in self.conds), set())
        if self.consequent is not None:
            atoms.update(self.consequent.atoms())
        return atoms

    def clean(self):
        consequent = self.consequent.clean() if self.consequent else None
        return BoxerDrs(self.refs, [c.clean() for c in self.conds], consequent)

    def renumber_sentences(self, f):
        consequent = self.consequent.renumber_sentences(f) if self.consequent else None
        return BoxerDrs(
            self.refs, [c.renumber_sentences(f) for c in self.conds], consequent
        )

    def __repr__(self):
        s = "drs([{}], [{}])".format(
            ", ".join("%s" % r for r in self.refs),
            ", ".join("%s" % c for c in self.conds),
        )
        if self.consequent is not None:
            s = f"imp({s}, {self.consequent})"
        return s

    def __eq__(self, other):
        return (
            self.__class__ == other.__class__
            and self.refs == other.refs
            and len(self.conds) == len(other.conds)
            and reduce(
                operator.and_, (c1 == c2 for c1, c2 in zip(self.conds, other.conds))
            )
            and self.consequent == other.consequent
        )

    def __ne__(self, other):
        return not self == other

    __hash__ = AbstractBoxerDrs.__hash__


class BoxerNot(AbstractBoxerDrs):
    def __init__(self, drs):
        AbstractBoxerDrs.__init__(self)
        self.drs = drs

    def _variables(self):
        return self.drs._variables()

    def atoms(self):
        return self.drs.atoms()

    def clean(self):
        return BoxerNot(self.drs.clean())

    def renumber_sentences(self, f):
        return BoxerNot(self.drs.renumber_sentences(f))

    def __repr__(self):
        return "not(%s)" % (self.drs)

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.drs == other.drs

    def __ne__(self, other):
        return not self == other

    __hash__ = AbstractBoxerDrs.__hash__


class BoxerIndexed(AbstractBoxerDrs):
    def __init__(self, discourse_id, sent_index, word_indices):
        AbstractBoxerDrs.__init__(self)
        self.discourse_id = discourse_id
        self.sent_index = sent_index
        self.word_indices = word_indices

    def atoms(self):
        return {self}

    def __eq__(self, other):
        return (
            self.__class__ == other.__class__
            and self.discourse_id == other.discourse_id
            and self.sent_index == other.sent_index
            and self.word_indices == other.word_indices
            and reduce(operator.and_, (s == o for s, o in zip(self, other)))
        )

    def __ne__(self, other):
        return not self == other

    __hash__ = AbstractBoxerDrs.__hash__

    def __repr__(self):
        s = "{}({}, {}, [{}]".format(
            self._pred(),
            self.discourse_id,
            self.sent_index,
            ", ".join("%s" % wi for wi in self.word_indices),
        )
        for v in self:
            s += ", %s" % v
        return s + ")"


class BoxerPred(BoxerIndexed):
    def __init__(self, discourse_id, sent_index, word_indices, var, name, pos, sense):
        BoxerIndexed.__init__(self, discourse_id, sent_index, word_indices)
        self.var = var
        self.name = name
        self.pos = pos
        self.sense = sense

    def _variables(self):
        return ({self.var}, set(), set())

    def change_var(self, var):
        return BoxerPred(
            self.discourse_id,
            self.sent_index,
            self.word_indices,
            var,
            self.name,
            self.pos,
            self.sense,
        )

    def clean(self):
        return BoxerPred(
            self.discourse_id,
            self.sent_index,
            self.word_indices,
            self.var,
            self._clean_name(self.name),
            self.pos,
            self.sense,
        )

    def renumber_sentences(self, f):
        new_sent_index = f(self.sent_index)
        return BoxerPred(
            self.discourse_id,
            new_sent_index,
            self.word_indices,
            self.var,
            self.name,
            self.pos,
            self.sense,
        )

    def __iter__(self):
        return iter((self.var, self.name, self.pos, self.sense))

    def _pred(self):
        return "pred"


class BoxerNamed(BoxerIndexed):
    def __init__(self, discourse_id, sent_index, word_indices, var, name, type, sense):
        BoxerIndexed.__init__(self, discourse_id, sent_index, word_indices)
        self.var = var
        self.name = name
        self.type = type
        self.sense = sense

    def _variables(self):
        return ({self.var}, set(), set())

    def change_var(self, var):
        return BoxerNamed(
            self.discourse_id,
            self.sent_index,
            self.word_indices,
            var,
            self.name,
            self.type,
            self.sense,
        )

    def clean(self):
        return BoxerNamed(
            self.discourse_id,
            self.sent_index,
            self.word_indices,
            self.var,
            self._clean_name(self.name),
            self.type,
            self.sense,
        )

    def renumber_sentences(self, f):
        return BoxerNamed(
            self.discourse_id,
            f(self.sent_index),
            self.word_indices,
            self.var,
            self.name,
            self.type,
            self.sense,
        )

    def __iter__(self):
        return iter((self.var, self.name, self.type, self.sense))

    def _pred(self):
        return "named"


class BoxerRel(BoxerIndexed):
    def __init__(self, discourse_id, sent_index, word_indices, var1, var2, rel, sense):
        BoxerIndexed.__init__(self, discourse_id, sent_index, word_indices)
        self.var1 = var1
        self.var2 = var2
        self.rel = rel
        self.sense = sense

    def _variables(self):
        return ({self.var1, self.var2}, set(), set())

    def clean(self):
        return BoxerRel(
            self.discourse_id,
            self.sent_index,
            self.word_indices,
            self.var1,
            self.var2,
            self._clean_name(self.rel),
            self.sense,
        )

    def renumber_sentences(self, f):
        return BoxerRel(
            self.discourse_id,
            f(self.sent_index),
            self.word_indices,
            self.var1,
            self.var2,
            self.rel,
            self.sense,
        )

    def __iter__(self):
        return iter((self.var1, self.var2, self.rel, self.sense))

    def _pred(self):
        return "rel"


class BoxerProp(BoxerIndexed):
    def __init__(self, discourse_id, sent_index, word_indices, var, drs):
        BoxerIndexed.__init__(self, discourse_id, sent_index, word_indices)
        self.var = var
        self.drs = drs

    def _variables(self):
        return tuple(
            map(operator.or_, (set(), set(), {self.var}), self.drs._variables())
        )

    def referenced_labels(self):
        return {self.drs}

    def atoms(self):
        return self.drs.atoms()

    def clean(self):
        return BoxerProp(
            self.discourse_id,
            self.sent_index,
            self.word_indices,
            self.var,
            self.drs.clean(),
        )

    def renumber_sentences(self, f):
        return BoxerProp(
            self.discourse_id,
            f(self.sent_index),
            self.word_indices,
            self.var,
            self.drs.renumber_sentences(f),
        )

    def __iter__(self):
        return iter((self.var, self.drs))

    def _pred(self):
        return "prop"


class BoxerEq(BoxerIndexed):
    def __init__(self, discourse_id, sent_index, word_indices, var1, var2):
        BoxerIndexed.__init__(self, discourse_id, sent_index, word_indices)
        self.var1 = var1
        self.var2 = var2

    def _variables(self):
        return ({self.var1, self.var2}, set(), set())

    def atoms(self):
        return set()

    def renumber_sentences(self, f):
        return BoxerEq(
            self.discourse_id,
            f(self.sent_index),
            self.word_indices,
            self.var1,
            self.var2,
        )

    def __iter__(self):
        return iter((self.var1, self.var2))

    def _pred(self):
        return "eq"


class BoxerCard(BoxerIndexed):
    def __init__(self, discourse_id, sent_index, word_indices, var, value, type):
        BoxerIndexed.__init__(self, discourse_id, sent_index, word_indices)
        self.var = var
        self.value = value
        self.type = type

    def _variables(self):
        return ({self.var}, set(), set())

    def renumber_sentences(self, f):
        return BoxerCard(
            self.discourse_id,
            f(self.sent_index),
            self.word_indices,
            self.var,
            self.value,
            self.type,
        )

    def __iter__(self):
        return iter((self.var, self.value, self.type))

    def _pred(self):
        return "card"


class BoxerOr(BoxerIndexed):
    def __init__(self, discourse_id, sent_index, word_indices, drs1, drs2):
        BoxerIndexed.__init__(self, discourse_id, sent_index, word_indices)
        self.drs1 = drs1
        self.drs2 = drs2

    def _variables(self):
        return tuple(map(operator.or_, self.drs1._variables(), self.drs2._variables()))

    def atoms(self):
        return self.drs1.atoms() | self.drs2.atoms()

    def clean(self):
        return BoxerOr(
            self.discourse_id,
            self.sent_index,
            self.word_indices,
            self.drs1.clean(),
            self.drs2.clean(),
        )

    def renumber_sentences(self, f):
        return BoxerOr(
            self.discourse_id,
            f(self.sent_index),
            self.word_indices,
            self.drs1,
            self.drs2,
        )

    def __iter__(self):
        return iter((self.drs1, self.drs2))

    def _pred(self):
        return "or"


class BoxerWhq(BoxerIndexed):
    def __init__(
        self, discourse_id, sent_index, word_indices, ans_types, drs1, variable, drs2
    ):
        BoxerIndexed.__init__(self, discourse_id, sent_index, word_indices)
        self.ans_types = ans_types
        self.drs1 = drs1
        self.variable = variable
        self.drs2 = drs2

    def _variables(self):
        return tuple(
            map(
                operator.or_,
                ({self.variable}, set(), set()),
                self.drs1._variables(),
                self.drs2._variables(),
            )
        )

    def atoms(self):
        return self.drs1.atoms() | self.drs2.atoms()

    def clean(self):
        return BoxerWhq(
            self.discourse_id,
            self.sent_index,
            self.word_indices,
            self.ans_types,
            self.drs1.clean(),
            self.variable,
            self.drs2.clean(),
        )

    def renumber_sentences(self, f):
        return BoxerWhq(
            self.discourse_id,
            f(self.sent_index),
            self.word_indices,
            self.ans_types,
            self.drs1,
            self.variable,
            self.drs2,
        )

    def __iter__(self):
        return iter(
            ("[" + ",".join(self.ans_types) + "]", self.drs1, self.variable, self.drs2)
        )

    def _pred(self):
        return "whq"


class PassthroughBoxerDrsInterpreter:
    def interpret(self, ex):
        return ex


class NltkDrtBoxerDrsInterpreter:
    def __init__(self, occur_index=False):
        self._occur_index = occur_index

    def interpret(self, ex):
        """
        :param ex: ``AbstractBoxerDrs``
        :return: ``DrtExpression``
        """
        if isinstance(ex, BoxerDrs):
            drs = DRS(
                [Variable(r) for r in ex.refs], list(map(self.interpret, ex.conds))
            )
            if ex.consequent is not None:
                drs.consequent = self.interpret(ex.consequent)
            return drs
        elif isinstance(ex, BoxerNot):
            return DrtNegatedExpression(self.interpret(ex.drs))
        elif isinstance(ex, BoxerPred):
            pred = self._add_occur_indexing(f"{ex.pos}_{ex.name}", ex)
            return self._make_atom(pred, ex.var)
        elif isinstance(ex, BoxerNamed):
            pred = self._add_occur_indexing(f"ne_{ex.type}_{ex.name}", ex)
            return self._make_atom(pred, ex.var)
        elif isinstance(ex, BoxerRel):
            pred = self._add_occur_indexing("%s" % (ex.rel), ex)
            return self._make_atom(pred, ex.var1, ex.var2)
        elif isinstance(ex, BoxerProp):
            return DrtProposition(Variable(ex.var), self.interpret(ex.drs))
        elif isinstance(ex, BoxerEq):
            return DrtEqualityExpression(
                DrtVariableExpression(Variable(ex.var1)),
                DrtVariableExpression(Variable(ex.var2)),
            )
        elif isinstance(ex, BoxerCard):
            pred = self._add_occur_indexing(f"card_{ex.type}_{ex.value}", ex)
            return self._make_atom(pred, ex.var)
        elif isinstance(ex, BoxerOr):
            return DrtOrExpression(self.interpret(ex.drs1), self.interpret(ex.drs2))
        elif isinstance(ex, BoxerWhq):
            drs1 = self.interpret(ex.drs1)
            drs2 = self.interpret(ex.drs2)
            return DRS(drs1.refs + drs2.refs, drs1.conds + drs2.conds)
        assert False, f"{ex.__class__.__name__}: {ex}"

    def _make_atom(self, pred, *args):
        accum = DrtVariableExpression(Variable(pred))
        for arg in args:
            accum = DrtApplicationExpression(
                accum, DrtVariableExpression(Variable(arg))
            )
        return accum

    def _add_occur_indexing(self, base, ex):
        if self._occur_index and ex.sent_index is not None:
            if ex.discourse_id:
                base += "_%s" % ex.discourse_id
            base += "_s%s" % ex.sent_index
            base += "_w%s" % sorted(ex.word_indices)[0]
        return base


class UnparseableInputException(Exception):
    pass


if __name__ == "__main__":
    opts = OptionParser("usage: %prog TEXT [options]")
    opts.add_option(
        "--verbose",
        "-v",
        help="display verbose logs",
        action="store_true",
        default=False,
        dest="verbose",
    )
    opts.add_option(
        "--fol", "-f", help="output FOL", action="store_true", default=False, dest="fol"
    )
    opts.add_option(
        "--question",
        "-q",
        help="input is a question",
        action="store_true",
        default=False,
        dest="question",
    )
    opts.add_option(
        "--occur",
        "-o",
        help="occurrence index",
        action="store_true",
        default=False,
        dest="occur_index",
    )
    (options, args) = opts.parse_args()

    if len(args) != 1:
        opts.error("incorrect number of arguments")

    interpreter = NltkDrtBoxerDrsInterpreter(occur_index=options.occur_index)
    drs = Boxer(interpreter).interpret_multi(
        args[0].split(r"\n"), question=options.question, verbose=options.verbose
    )
    if drs is None:
        print(None)
    else:
        drs = drs.simplify().eliminate_equality()
        if options.fol:
            print(drs.fol().normalize())
        else:
            drs.pretty_print()

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\_scheme_builtins.py ===
"""
    pygments.lexers._scheme_builtins
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Scheme builtins.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

# Autogenerated by external/scheme-builtins-generator.scm
# using Guile 3.0.5.130-5a1e7.

scheme_keywords = {
    "*unspecified*",
    "...",
    "=>",
    "@",
    "@@",
    "_",
    "add-to-load-path",
    "and",
    "begin",
    "begin-deprecated",
    "case",
    "case-lambda",
    "case-lambda*",
    "cond",
    "cond-expand",
    "current-filename",
    "current-source-location",
    "debug-set!",
    "define",
    "define*",
    "define-inlinable",
    "define-library",
    "define-macro",
    "define-module",
    "define-once",
    "define-option-interface",
    "define-private",
    "define-public",
    "define-record-type",
    "define-syntax",
    "define-syntax-parameter",
    "define-syntax-rule",
    "define-values",
    "defmacro",
    "defmacro-public",
    "delay",
    "do",
    "else",
    "eval-when",
    "export",
    "export!",
    "export-syntax",
    "false-if-exception",
    "identifier-syntax",
    "if",
    "import",
    "include",
    "include-ci",
    "include-from-path",
    "include-library-declarations",
    "lambda",
    "lambda*",
    "let",
    "let*",
    "let*-values",
    "let-syntax",
    "let-values",
    "letrec",
    "letrec*",
    "letrec-syntax",
    "library",
    "load",
    "match",
    "match-lambda",
    "match-lambda*",
    "match-let",
    "match-let*",
    "match-letrec",
    "or",
    "parameterize",
    "print-set!",
    "quasiquote",
    "quasisyntax",
    "quote",
    "quote-syntax",
    "re-export",
    "re-export-syntax",
    "read-set!",
    "require-extension",
    "set!",
    "start-stack",
    "syntax",
    "syntax-case",
    "syntax-error",
    "syntax-parameterize",
    "syntax-rules",
    "unless",
    "unquote",
    "unquote-splicing",
    "unsyntax",
    "unsyntax-splicing",
    "use-modules",
    "when",
    "while",
    "with-ellipsis",
    "with-fluids",
    "with-syntax",
    "λ",
}

scheme_builtins = {
    "$sc-dispatch",
    "%char-set-dump",
    "%get-pre-modules-obarray",
    "%get-stack-size",
    "%global-site-dir",
    "%init-rdelim-builtins",
    "%init-rw-builtins",
    "%library-dir",
    "%load-announce",
    "%load-hook",
    "%make-void-port",
    "%package-data-dir",
    "%port-property",
    "%print-module",
    "%resolve-variable",
    "%search-load-path",
    "%set-port-property!",
    "%site-ccache-dir",
    "%site-dir",
    "%start-stack",
    "%string-dump",
    "%symbol-dump",
    "%warn-auto-compilation-enabled",
    "*",
    "+",
    "-",
    "->bool",
    "->char-set",
    "/",
    "1+",
    "1-",
    "<",
    "<=",
    "=",
    ">",
    ">=",
    "abort-to-prompt",
    "abort-to-prompt*",
    "abs",
    "absolute-file-name?",
    "accept",
    "access?",
    "acons",
    "acos",
    "acosh",
    "add-hook!",
    "addrinfo:addr",
    "addrinfo:canonname",
    "addrinfo:fam",
    "addrinfo:flags",
    "addrinfo:protocol",
    "addrinfo:socktype",
    "adjust-port-revealed!",
    "alarm",
    "alist-cons",
    "alist-copy",
    "alist-delete",
    "alist-delete!",
    "allocate-struct",
    "and-map",
    "and=>",
    "angle",
    "any",
    "append",
    "append!",
    "append-map",
    "append-map!",
    "append-reverse",
    "append-reverse!",
    "apply",
    "array->list",
    "array-cell-ref",
    "array-cell-set!",
    "array-contents",
    "array-copy!",
    "array-copy-in-order!",
    "array-dimensions",
    "array-equal?",
    "array-fill!",
    "array-for-each",
    "array-in-bounds?",
    "array-index-map!",
    "array-length",
    "array-map!",
    "array-map-in-order!",
    "array-rank",
    "array-ref",
    "array-set!",
    "array-shape",
    "array-slice",
    "array-slice-for-each",
    "array-slice-for-each-in-order",
    "array-type",
    "array-type-code",
    "array?",
    "ash",
    "asin",
    "asinh",
    "assert-load-verbosity",
    "assoc",
    "assoc-ref",
    "assoc-remove!",
    "assoc-set!",
    "assq",
    "assq-ref",
    "assq-remove!",
    "assq-set!",
    "assv",
    "assv-ref",
    "assv-remove!",
    "assv-set!",
    "atan",
    "atanh",
    "autoload-done!",
    "autoload-done-or-in-progress?",
    "autoload-in-progress!",
    "backtrace",
    "basename",
    "batch-mode?",
    "beautify-user-module!",
    "bind",
    "bind-textdomain-codeset",
    "bindtextdomain",
    "bit-count",
    "bit-count*",
    "bit-extract",
    "bit-invert!",
    "bit-position",
    "bit-set*!",
    "bitvector",
    "bitvector->list",
    "bitvector-bit-clear?",
    "bitvector-bit-set?",
    "bitvector-clear-all-bits!",
    "bitvector-clear-bit!",
    "bitvector-clear-bits!",
    "bitvector-count",
    "bitvector-count-bits",
    "bitvector-fill!",
    "bitvector-flip-all-bits!",
    "bitvector-length",
    "bitvector-position",
    "bitvector-ref",
    "bitvector-set!",
    "bitvector-set-all-bits!",
    "bitvector-set-bit!",
    "bitvector-set-bits!",
    "bitvector?",
    "boolean?",
    "bound-identifier=?",
    "break",
    "break!",
    "caaaar",
    "caaadr",
    "caaar",
    "caadar",
    "caaddr",
    "caadr",
    "caar",
    "cadaar",
    "cadadr",
    "cadar",
    "caddar",
    "cadddr",
    "caddr",
    "cadr",
    "call-with-blocked-asyncs",
    "call-with-current-continuation",
    "call-with-deferred-observers",
    "call-with-include-port",
    "call-with-input-file",
    "call-with-input-string",
    "call-with-module-autoload-lock",
    "call-with-output-file",
    "call-with-output-string",
    "call-with-port",
    "call-with-prompt",
    "call-with-unblocked-asyncs",
    "call-with-values",
    "call/cc",
    "canonicalize-path",
    "car",
    "car+cdr",
    "catch",
    "cdaaar",
    "cdaadr",
    "cdaar",
    "cdadar",
    "cdaddr",
    "cdadr",
    "cdar",
    "cddaar",
    "cddadr",
    "cddar",
    "cdddar",
    "cddddr",
    "cdddr",
    "cddr",
    "cdr",
    "ceiling",
    "ceiling-quotient",
    "ceiling-remainder",
    "ceiling/",
    "centered-quotient",
    "centered-remainder",
    "centered/",
    "char->integer",
    "char-alphabetic?",
    "char-ci<=?",
    "char-ci<?",
    "char-ci=?",
    "char-ci>=?",
    "char-ci>?",
    "char-downcase",
    "char-general-category",
    "char-is-both?",
    "char-lower-case?",
    "char-numeric?",
    "char-ready?",
    "char-set",
    "char-set->list",
    "char-set->string",
    "char-set-adjoin",
    "char-set-adjoin!",
    "char-set-any",
    "char-set-complement",
    "char-set-complement!",
    "char-set-contains?",
    "char-set-copy",
    "char-set-count",
    "char-set-cursor",
    "char-set-cursor-next",
    "char-set-delete",
    "char-set-delete!",
    "char-set-diff+intersection",
    "char-set-diff+intersection!",
    "char-set-difference",
    "char-set-difference!",
    "char-set-every",
    "char-set-filter",
    "char-set-filter!",
    "char-set-fold",
    "char-set-for-each",
    "char-set-hash",
    "char-set-intersection",
    "char-set-intersection!",
    "char-set-map",
    "char-set-ref",
    "char-set-size",
    "char-set-unfold",
    "char-set-unfold!",
    "char-set-union",
    "char-set-union!",
    "char-set-xor",
    "char-set-xor!",
    "char-set<=",
    "char-set=",
    "char-set?",
    "char-titlecase",
    "char-upcase",
    "char-upper-case?",
    "char-whitespace?",
    "char<=?",
    "char<?",
    "char=?",
    "char>=?",
    "char>?",
    "char?",
    "chdir",
    "chmod",
    "chown",
    "chroot",
    "circular-list",
    "circular-list?",
    "close",
    "close-fdes",
    "close-input-port",
    "close-output-port",
    "close-port",
    "closedir",
    "command-line",
    "complex?",
    "compose",
    "concatenate",
    "concatenate!",
    "cond-expand-provide",
    "connect",
    "cons",
    "cons*",
    "cons-source",
    "const",
    "convert-assignment",
    "copy-file",
    "copy-random-state",
    "copy-tree",
    "cos",
    "cosh",
    "count",
    "crypt",
    "ctermid",
    "current-dynamic-state",
    "current-error-port",
    "current-input-port",
    "current-language",
    "current-load-port",
    "current-module",
    "current-output-port",
    "current-time",
    "current-warning-port",
    "datum->random-state",
    "datum->syntax",
    "debug-disable",
    "debug-enable",
    "debug-options",
    "debug-options-interface",
    "default-duplicate-binding-handler",
    "default-duplicate-binding-procedures",
    "default-prompt-tag",
    "define!",
    "define-module*",
    "defined?",
    "delete",
    "delete!",
    "delete-duplicates",
    "delete-duplicates!",
    "delete-file",
    "delete1!",
    "delq",
    "delq!",
    "delq1!",
    "delv",
    "delv!",
    "delv1!",
    "denominator",
    "directory-stream?",
    "dirname",
    "display",
    "display-application",
    "display-backtrace",
    "display-error",
    "dotted-list?",
    "doubly-weak-hash-table?",
    "drain-input",
    "drop",
    "drop-right",
    "drop-right!",
    "drop-while",
    "dup",
    "dup->fdes",
    "dup->inport",
    "dup->outport",
    "dup->port",
    "dup2",
    "duplicate-port",
    "dynamic-call",
    "dynamic-func",
    "dynamic-link",
    "dynamic-object?",
    "dynamic-pointer",
    "dynamic-state?",
    "dynamic-unlink",
    "dynamic-wind",
    "effective-version",
    "eighth",
    "end-of-char-set?",
    "endgrent",
    "endhostent",
    "endnetent",
    "endprotoent",
    "endpwent",
    "endservent",
    "ensure-batch-mode!",
    "environ",
    "eof-object?",
    "eq?",
    "equal?",
    "eqv?",
    "error",
    "euclidean-quotient",
    "euclidean-remainder",
    "euclidean/",
    "eval",
    "eval-string",
    "even?",
    "every",
    "exact->inexact",
    "exact-integer-sqrt",
    "exact-integer?",
    "exact?",
    "exception-accessor",
    "exception-args",
    "exception-kind",
    "exception-predicate",
    "exception-type?",
    "exception?",
    "execl",
    "execle",
    "execlp",
    "exit",
    "exp",
    "expt",
    "f32vector",
    "f32vector->list",
    "f32vector-length",
    "f32vector-ref",
    "f32vector-set!",
    "f32vector?",
    "f64vector",
    "f64vector->list",
    "f64vector-length",
    "f64vector-ref",
    "f64vector-set!",
    "f64vector?",
    "fcntl",
    "fdes->inport",
    "fdes->outport",
    "fdes->ports",
    "fdopen",
    "fifth",
    "file-encoding",
    "file-exists?",
    "file-is-directory?",
    "file-name-separator?",
    "file-port?",
    "file-position",
    "file-set-position",
    "fileno",
    "filter",
    "filter!",
    "filter-map",
    "find",
    "find-tail",
    "finite?",
    "first",
    "flock",
    "floor",
    "floor-quotient",
    "floor-remainder",
    "floor/",
    "fluid->parameter",
    "fluid-bound?",
    "fluid-ref",
    "fluid-ref*",
    "fluid-set!",
    "fluid-thread-local?",
    "fluid-unset!",
    "fluid?",
    "flush-all-ports",
    "fold",
    "fold-right",
    "for-each",
    "force",
    "force-output",
    "format",
    "fourth",
    "frame-address",
    "frame-arguments",
    "frame-dynamic-link",
    "frame-instruction-pointer",
    "frame-previous",
    "frame-procedure-name",
    "frame-return-address",
    "frame-source",
    "frame-stack-pointer",
    "frame?",
    "free-identifier=?",
    "fsync",
    "ftell",
    "gai-strerror",
    "gc",
    "gc-disable",
    "gc-dump",
    "gc-enable",
    "gc-run-time",
    "gc-stats",
    "gcd",
    "generate-temporaries",
    "gensym",
    "get-internal-real-time",
    "get-internal-run-time",
    "get-output-string",
    "get-print-state",
    "getaddrinfo",
    "getaffinity",
    "getcwd",
    "getegid",
    "getenv",
    "geteuid",
    "getgid",
    "getgr",
    "getgrent",
    "getgrgid",
    "getgrnam",
    "getgroups",
    "gethost",
    "gethostbyaddr",
    "gethostbyname",
    "gethostent",
    "gethostname",
    "getitimer",
    "getlogin",
    "getnet",
    "getnetbyaddr",
    "getnetbyname",
    "getnetent",
    "getpass",
    "getpeername",
    "getpgrp",
    "getpid",
    "getppid",
    "getpriority",
    "getproto",
    "getprotobyname",
    "getprotobynumber",
    "getprotoent",
    "getpw",
    "getpwent",
    "getpwnam",
    "getpwuid",
    "getrlimit",
    "getserv",
    "getservbyname",
    "getservbyport",
    "getservent",
    "getsid",
    "getsockname",
    "getsockopt",
    "gettext",
    "gettimeofday",
    "getuid",
    "gmtime",
    "group:gid",
    "group:mem",
    "group:name",
    "group:passwd",
    "hash",
    "hash-clear!",
    "hash-count",
    "hash-create-handle!",
    "hash-fold",
    "hash-for-each",
    "hash-for-each-handle",
    "hash-get-handle",
    "hash-map->list",
    "hash-ref",
    "hash-remove!",
    "hash-set!",
    "hash-table?",
    "hashq",
    "hashq-create-handle!",
    "hashq-get-handle",
    "hashq-ref",
    "hashq-remove!",
    "hashq-set!",
    "hashv",
    "hashv-create-handle!",
    "hashv-get-handle",
    "hashv-ref",
    "hashv-remove!",
    "hashv-set!",
    "hashx-create-handle!",
    "hashx-get-handle",
    "hashx-ref",
    "hashx-remove!",
    "hashx-set!",
    "hook->list",
    "hook-empty?",
    "hook?",
    "hostent:addr-list",
    "hostent:addrtype",
    "hostent:aliases",
    "hostent:length",
    "hostent:name",
    "identifier?",
    "identity",
    "imag-part",
    "in-vicinity",
    "include-deprecated-features",
    "inet-lnaof",
    "inet-makeaddr",
    "inet-netof",
    "inet-ntop",
    "inet-pton",
    "inexact->exact",
    "inexact?",
    "inf",
    "inf?",
    "inherit-print-state",
    "input-port?",
    "install-r6rs!",
    "install-r7rs!",
    "integer->char",
    "integer-expt",
    "integer-length",
    "integer?",
    "interaction-environment",
    "iota",
    "isatty?",
    "issue-deprecation-warning",
    "keyword->symbol",
    "keyword-like-symbol->keyword",
    "keyword?",
    "kill",
    "kw-arg-ref",
    "last",
    "last-pair",
    "lcm",
    "length",
    "length+",
    "link",
    "list",
    "list->array",
    "list->bitvector",
    "list->char-set",
    "list->char-set!",
    "list->f32vector",
    "list->f64vector",
    "list->s16vector",
    "list->s32vector",
    "list->s64vector",
    "list->s8vector",
    "list->string",
    "list->symbol",
    "list->typed-array",
    "list->u16vector",
    "list->u32vector",
    "list->u64vector",
    "list->u8vector",
    "list->vector",
    "list-cdr-ref",
    "list-cdr-set!",
    "list-copy",
    "list-head",
    "list-index",
    "list-ref",
    "list-set!",
    "list-tabulate",
    "list-tail",
    "list=",
    "list?",
    "listen",
    "load-compiled",
    "load-extension",
    "load-from-path",
    "load-in-vicinity",
    "load-user-init",
    "local-define",
    "local-define-module",
    "local-ref",
    "local-ref-module",
    "local-remove",
    "local-set!",
    "localtime",
    "log",
    "log10",
    "logand",
    "logbit?",
    "logcount",
    "logior",
    "lognot",
    "logtest",
    "logxor",
    "lookup-duplicates-handlers",
    "lset-adjoin",
    "lset-diff+intersection",
    "lset-diff+intersection!",
    "lset-difference",
    "lset-difference!",
    "lset-intersection",
    "lset-intersection!",
    "lset-union",
    "lset-union!",
    "lset-xor",
    "lset-xor!",
    "lset<=",
    "lset=",
    "lstat",
    "macro-binding",
    "macro-name",
    "macro-transformer",
    "macro-type",
    "macro?",
    "macroexpand",
    "macroexpanded?",
    "magnitude",
    "major-version",
    "make-array",
    "make-autoload-interface",
    "make-bitvector",
    "make-doubly-weak-hash-table",
    "make-exception",
    "make-exception-from-throw",
    "make-exception-type",
    "make-f32vector",
    "make-f64vector",
    "make-fluid",
    "make-fresh-user-module",
    "make-generalized-vector",
    "make-guardian",
    "make-hash-table",
    "make-hook",
    "make-list",
    "make-module",
    "make-modules-in",
    "make-mutable-parameter",
    "make-object-property",
    "make-parameter",
    "make-polar",
    "make-procedure-with-setter",
    "make-promise",
    "make-prompt-tag",
    "make-record-type",
    "make-rectangular",
    "make-regexp",
    "make-s16vector",
    "make-s32vector",
    "make-s64vector",
    "make-s8vector",
    "make-shared-array",
    "make-socket-address",
    "make-soft-port",
    "make-srfi-4-vector",
    "make-stack",
    "make-string",
    "make-struct-layout",
    "make-struct/no-tail",
    "make-struct/simple",
    "make-symbol",
    "make-syntax-transformer",
    "make-thread-local-fluid",
    "make-typed-array",
    "make-u16vector",
    "make-u32vector",
    "make-u64vector",
    "make-u8vector",
    "make-unbound-fluid",
    "make-undefined-variable",
    "make-variable",
    "make-variable-transformer",
    "make-vector",
    "make-vtable",
    "make-weak-key-hash-table",
    "make-weak-value-hash-table",
    "map",
    "map!",
    "map-in-order",
    "max",
    "member",
    "memoize-expression",
    "memoized-typecode",
    "memq",
    "memv",
    "merge",
    "merge!",
    "micro-version",
    "min",
    "minor-version",
    "mkdir",
    "mkdtemp",
    "mknod",
    "mkstemp",
    "mkstemp!",
    "mktime",
    "module-add!",
    "module-autoload!",
    "module-binder",
    "module-bound?",
    "module-call-observers",
    "module-clear!",
    "module-constructor",
    "module-declarative?",
    "module-defer-observers",
    "module-define!",
    "module-define-submodule!",
    "module-defined?",
    "module-duplicates-handlers",
    "module-ensure-local-variable!",
    "module-export!",
    "module-export-all!",
    "module-filename",
    "module-for-each",
    "module-generate-unique-id!",
    "module-gensym",
    "module-import-interface",
    "module-import-obarray",
    "module-kind",
    "module-local-variable",
    "module-locally-bound?",
    "module-make-local-var!",
    "module-map",
    "module-modified",
    "module-name",
    "module-next-unique-id",
    "module-obarray",
    "module-obarray-get-handle",
    "module-obarray-ref",
    "module-obarray-remove!",
    "module-obarray-set!",
    "module-observe",
    "module-observe-weak",
    "module-observers",
    "module-public-interface",
    "module-re-export!",
    "module-ref",
    "module-ref-submodule",
    "module-remove!",
    "module-replace!",
    "module-replacements",
    "module-reverse-lookup",
    "module-search",
    "module-set!",
    "module-submodule-binder",
    "module-submodules",
    "module-symbol-binding",
    "module-symbol-interned?",
    "module-symbol-local-binding",
    "module-symbol-locally-interned?",
    "module-transformer",
    "module-unobserve",
    "module-use!",
    "module-use-interfaces!",
    "module-uses",
    "module-variable",
    "module-version",
    "module-weak-observers",
    "module?",
    "modulo",
    "modulo-expt",
    "move->fdes",
    "nan",
    "nan?",
    "negate",
    "negative?",
    "nested-define!",
    "nested-define-module!",
    "nested-ref",
    "nested-ref-module",
    "nested-remove!",
    "nested-set!",
    "netent:addrtype",
    "netent:aliases",
    "netent:name",
    "netent:net",
    "newline",
    "ngettext",
    "nice",
    "nil?",
    "ninth",
    "noop",
    "not",
    "not-pair?",
    "null-environment",
    "null-list?",
    "null?",
    "number->string",
    "number?",
    "numerator",
    "object->string",
    "object-address",
    "object-properties",
    "object-property",
    "odd?",
    "open",
    "open-fdes",
    "open-file",
    "open-input-file",
    "open-input-string",
    "open-io-file",
    "open-output-file",
    "open-output-string",
    "opendir",
    "or-map",
    "output-port?",
    "pair-fold",
    "pair-fold-right",
    "pair-for-each",
    "pair?",
    "parameter-converter",
    "parameter-fluid",
    "parameter?",
    "parse-path",
    "parse-path-with-ellipsis",
    "partition",
    "partition!",
    "passwd:dir",
    "passwd:gecos",
    "passwd:gid",
    "passwd:name",
    "passwd:passwd",
    "passwd:shell",
    "passwd:uid",
    "pause",
    "peek",
    "peek-char",
    "pipe",
    "pk",
    "port->fdes",
    "port-closed?",
    "port-column",
    "port-conversion-strategy",
    "port-encoding",
    "port-filename",
    "port-for-each",
    "port-line",
    "port-mode",
    "port-revealed",
    "port-with-print-state",
    "port?",
    "positive?",
    "primitive-_exit",
    "primitive-eval",
    "primitive-exit",
    "primitive-fork",
    "primitive-load",
    "primitive-load-path",
    "primitive-move->fdes",
    "primitive-read",
    "print-disable",
    "print-enable",
    "print-exception",
    "print-options",
    "print-options-interface",
    "procedure",
    "procedure-documentation",
    "procedure-minimum-arity",
    "procedure-name",
    "procedure-properties",
    "procedure-property",
    "procedure-source",
    "procedure-with-setter?",
    "procedure?",
    "process-use-modules",
    "program-arguments",
    "promise?",
    "proper-list?",
    "protoent:aliases",
    "protoent:name",
    "protoent:proto",
    "provide",
    "provided?",
    "purify-module!",
    "putenv",
    "quit",
    "quotient",
    "raise",
    "raise-exception",
    "random",
    "random-state->datum",
    "random-state-from-platform",
    "random:exp",
    "random:hollow-sphere!",
    "random:normal",
    "random:normal-vector!",
    "random:solid-sphere!",
    "random:uniform",
    "rational?",
    "rationalize",
    "read",
    "read-char",
    "read-disable",
    "read-enable",
    "read-hash-extend",
    "read-hash-procedure",
    "read-hash-procedures",
    "read-options",
    "read-options-interface",
    "read-syntax",
    "readdir",
    "readlink",
    "real-part",
    "real?",
    "record-accessor",
    "record-constructor",
    "record-modifier",
    "record-predicate",
    "record-type-constructor",
    "record-type-descriptor",
    "record-type-extensible?",
    "record-type-fields",
    "record-type-has-parent?",
    "record-type-mutable-fields",
    "record-type-name",
    "record-type-opaque?",
    "record-type-parent",
    "record-type-parents",
    "record-type-properties",
    "record-type-uid",
    "record-type?",
    "record?",
    "recv!",
    "recvfrom!",
    "redirect-port",
    "reduce",
    "reduce-right",
    "regexp-exec",
    "regexp?",
    "release-port-handle",
    "reload-module",
    "remainder",
    "remove",
    "remove!",
    "remove-hook!",
    "rename-file",
    "repl-reader",
    "reset-hook!",
    "resolve-interface",
    "resolve-module",
    "resolve-r6rs-interface",
    "restore-signals",
    "restricted-vector-sort!",
    "reverse",
    "reverse!",
    "reverse-list->string",
    "rewinddir",
    "rmdir",
    "round",
    "round-ash",
    "round-quotient",
    "round-remainder",
    "round/",
    "run-hook",
    "s16vector",
    "s16vector->list",
    "s16vector-length",
    "s16vector-ref",
    "s16vector-set!",
    "s16vector?",
    "s32vector",
    "s32vector->list",
    "s32vector-length",
    "s32vector-ref",
    "s32vector-set!",
    "s32vector?",
    "s64vector",
    "s64vector->list",
    "s64vector-length",
    "s64vector-ref",
    "s64vector-set!",
    "s64vector?",
    "s8vector",
    "s8vector->list",
    "s8vector-length",
    "s8vector-ref",
    "s8vector-set!",
    "s8vector?",
    "save-module-excursion",
    "scheme-report-environment",
    "scm-error",
    "search-path",
    "second",
    "seed->random-state",
    "seek",
    "select",
    "self-evaluating?",
    "send",
    "sendfile",
    "sendto",
    "servent:aliases",
    "servent:name",
    "servent:port",
    "servent:proto",
    "set-autoloaded!",
    "set-car!",
    "set-cdr!",
    "set-current-dynamic-state",
    "set-current-error-port",
    "set-current-input-port",
    "set-current-module",
    "set-current-output-port",
    "set-exception-printer!",
    "set-module-binder!",
    "set-module-declarative?!",
    "set-module-duplicates-handlers!",
    "set-module-filename!",
    "set-module-kind!",
    "set-module-name!",
    "set-module-next-unique-id!",
    "set-module-obarray!",
    "set-module-observers!",
    "set-module-public-interface!",
    "set-module-submodule-binder!",
    "set-module-submodules!",
    "set-module-transformer!",
    "set-module-uses!",
    "set-module-version!",
    "set-object-properties!",
    "set-object-property!",
    "set-port-column!",
    "set-port-conversion-strategy!",
    "set-port-encoding!",
    "set-port-filename!",
    "set-port-line!",
    "set-port-revealed!",
    "set-procedure-minimum-arity!",
    "set-procedure-properties!",
    "set-procedure-property!",
    "set-program-arguments",
    "set-source-properties!",
    "set-source-property!",
    "set-struct-vtable-name!",
    "set-symbol-property!",
    "set-tm:gmtoff",
    "set-tm:hour",
    "set-tm:isdst",
    "set-tm:mday",
    "set-tm:min",
    "set-tm:mon",
    "set-tm:sec",
    "set-tm:wday",
    "set-tm:yday",
    "set-tm:year",
    "set-tm:zone",
    "setaffinity",
    "setegid",
    "setenv",
    "seteuid",
    "setgid",
    "setgr",
    "setgrent",
    "setgroups",
    "sethost",
    "sethostent",
    "sethostname",
    "setitimer",
    "setlocale",
    "setnet",
    "setnetent",
    "setpgid",
    "setpriority",
    "setproto",
    "setprotoent",
    "setpw",
    "setpwent",
    "setrlimit",
    "setserv",
    "setservent",
    "setsid",
    "setsockopt",
    "setter",
    "setuid",
    "setvbuf",
    "seventh",
    "shared-array-increments",
    "shared-array-offset",
    "shared-array-root",
    "shutdown",
    "sigaction",
    "simple-exceptions",
    "simple-format",
    "sin",
    "sinh",
    "sixth",
    "sleep",
    "sloppy-assoc",
    "sloppy-assq",
    "sloppy-assv",
    "sockaddr:addr",
    "sockaddr:fam",
    "sockaddr:flowinfo",
    "sockaddr:path",
    "sockaddr:port",
    "sockaddr:scopeid",
    "socket",
    "socketpair",
    "sort",
    "sort!",
    "sort-list",
    "sort-list!",
    "sorted?",
    "source-properties",
    "source-property",
    "span",
    "span!",
    "split-at",
    "split-at!",
    "sqrt",
    "stable-sort",
    "stable-sort!",
    "stack-id",
    "stack-length",
    "stack-ref",
    "stack?",
    "stat",
    "stat:atime",
    "stat:atimensec",
    "stat:blksize",
    "stat:blocks",
    "stat:ctime",
    "stat:ctimensec",
    "stat:dev",
    "stat:gid",
    "stat:ino",
    "stat:mode",
    "stat:mtime",
    "stat:mtimensec",
    "stat:nlink",
    "stat:perms",
    "stat:rdev",
    "stat:size",
    "stat:type",
    "stat:uid",
    "status:exit-val",
    "status:stop-sig",
    "status:term-sig",
    "strerror",
    "strftime",
    "string",
    "string->char-set",
    "string->char-set!",
    "string->list",
    "string->number",
    "string->symbol",
    "string-any",
    "string-any-c-code",
    "string-append",
    "string-append/shared",
    "string-bytes-per-char",
    "string-capitalize",
    "string-capitalize!",
    "string-ci->symbol",
    "string-ci<",
    "string-ci<=",
    "string-ci<=?",
    "string-ci<>",
    "string-ci<?",
    "string-ci=",
    "string-ci=?",
    "string-ci>",
    "string-ci>=",
    "string-ci>=?",
    "string-ci>?",
    "string-compare",
    "string-compare-ci",
    "string-concatenate",
    "string-concatenate-reverse",
    "string-concatenate-reverse/shared",
    "string-concatenate/shared",
    "string-contains",
    "string-contains-ci",
    "string-copy",
    "string-copy!",
    "string-count",
    "string-delete",
    "string-downcase",
    "string-downcase!",
    "string-drop",
    "string-drop-right",
    "string-every",
    "string-every-c-code",
    "string-fill!",
    "string-filter",
    "string-fold",
    "string-fold-right",
    "string-for-each",
    "string-for-each-index",
    "string-hash",
    "string-hash-ci",
    "string-index",
    "string-index-right",
    "string-join",
    "string-length",
    "string-map",
    "string-map!",
    "string-normalize-nfc",
    "string-normalize-nfd",
    "string-normalize-nfkc",
    "string-normalize-nfkd",
    "string-null?",
    "string-pad",
    "string-pad-right",
    "string-prefix-ci?",
    "string-prefix-length",
    "string-prefix-length-ci",
    "string-prefix?",
    "string-ref",
    "string-replace",
    "string-reverse",
    "string-reverse!",
    "string-rindex",
    "string-set!",
    "string-skip",
    "string-skip-right",
    "string-split",
    "string-suffix-ci?",
    "string-suffix-length",
    "string-suffix-length-ci",
    "string-suffix?",
    "string-tabulate",
    "string-take",
    "string-take-right",
    "string-titlecase",
    "string-titlecase!",
    "string-tokenize",
    "string-trim",
    "string-trim-both",
    "string-trim-right",
    "string-unfold",
    "string-unfold-right",
    "string-upcase",
    "string-upcase!",
    "string-utf8-length",
    "string-xcopy!",
    "string<",
    "string<=",
    "string<=?",
    "string<>",
    "string<?",
    "string=",
    "string=?",
    "string>",
    "string>=",
    "string>=?",
    "string>?",
    "string?",
    "strptime",
    "struct-layout",
    "struct-ref",
    "struct-ref/unboxed",
    "struct-set!",
    "struct-set!/unboxed",
    "struct-vtable",
    "struct-vtable-name",
    "struct-vtable?",
    "struct?",
    "substring",
    "substring-fill!",
    "substring-move!",
    "substring/copy",
    "substring/read-only",
    "substring/shared",
    "supports-source-properties?",
    "symbol",
    "symbol->keyword",
    "symbol->string",
    "symbol-append",
    "symbol-fref",
    "symbol-fset!",
    "symbol-hash",
    "symbol-interned?",
    "symbol-pref",
    "symbol-prefix-proc",
    "symbol-property",
    "symbol-property-remove!",
    "symbol-pset!",
    "symbol?",
    "symlink",
    "sync",
    "syntax->datum",
    "syntax-source",
    "syntax-violation",
    "system",
    "system*",
    "system-async-mark",
    "system-error-errno",
    "system-file-name-convention",
    "take",
    "take!",
    "take-right",
    "take-while",
    "take-while!",
    "tan",
    "tanh",
    "tcgetpgrp",
    "tcsetpgrp",
    "tenth",
    "textdomain",
    "third",
    "throw",
    "thunk?",
    "times",
    "tm:gmtoff",
    "tm:hour",
    "tm:isdst",
    "tm:mday",
    "tm:min",
    "tm:mon",
    "tm:sec",
    "tm:wday",
    "tm:yday",
    "tm:year",
    "tm:zone",
    "tmpfile",
    "tmpnam",
    "tms:clock",
    "tms:cstime",
    "tms:cutime",
    "tms:stime",
    "tms:utime",
    "transpose-array",
    "truncate",
    "truncate-file",
    "truncate-quotient",
    "truncate-remainder",
    "truncate/",
    "try-load-module",
    "try-module-autoload",
    "ttyname",
    "typed-array?",
    "tzset",
    "u16vector",
    "u16vector->list",
    "u16vector-length",
    "u16vector-ref",
    "u16vector-set!",
    "u16vector?",
    "u32vector",
    "u32vector->list",
    "u32vector-length",
    "u32vector-ref",
    "u32vector-set!",
    "u32vector?",
    "u64vector",
    "u64vector->list",
    "u64vector-length",
    "u64vector-ref",
    "u64vector-set!",
    "u64vector?",
    "u8vector",
    "u8vector->list",
    "u8vector-length",
    "u8vector-ref",
    "u8vector-set!",
    "u8vector?",
    "ucs-range->char-set",
    "ucs-range->char-set!",
    "umask",
    "uname",
    "unfold",
    "unfold-right",
    "unmemoize-expression",
    "unread-char",
    "unread-string",
    "unsetenv",
    "unspecified?",
    "unzip1",
    "unzip2",
    "unzip3",
    "unzip4",
    "unzip5",
    "use-srfis",
    "user-modules-declarative?",
    "using-readline?",
    "usleep",
    "utime",
    "utsname:machine",
    "utsname:nodename",
    "utsname:release",
    "utsname:sysname",
    "utsname:version",
    "values",
    "variable-bound?",
    "variable-ref",
    "variable-set!",
    "variable-unset!",
    "variable?",
    "vector",
    "vector->list",
    "vector-copy",
    "vector-fill!",
    "vector-length",
    "vector-move-left!",
    "vector-move-right!",
    "vector-ref",
    "vector-set!",
    "vector?",
    "version",
    "version-matches?",
    "waitpid",
    "warn",
    "weak-key-hash-table?",
    "weak-value-hash-table?",
    "with-continuation-barrier",
    "with-dynamic-state",
    "with-error-to-file",
    "with-error-to-port",
    "with-error-to-string",
    "with-exception-handler",
    "with-fluid*",
    "with-fluids*",
    "with-input-from-file",
    "with-input-from-port",
    "with-input-from-string",
    "with-output-to-file",
    "with-output-to-port",
    "with-output-to-string",
    "with-throw-handler",
    "write",
    "write-char",
    "xcons",
    "xsubstring",
    "zero?",
    "zip",
}


# === NexusCore/openenv\Lib\site-packages\aiohttp\client.py ===
"""HTTP Client for asyncio."""

import asyncio
import base64
import hashlib
import json
import os
import sys
import traceback
import warnings
from contextlib import suppress
from types import TracebackType
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Coroutine,
    Final,
    FrozenSet,
    Generator,
    Generic,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    TypedDict,
    TypeVar,
    Union,
)

import attr
from multidict import CIMultiDict, MultiDict, MultiDictProxy, istr
from yarl import URL

from . import hdrs, http, payload
from ._websocket.reader import WebSocketDataQueue
from .abc import AbstractCookieJar
from .client_exceptions import (
    ClientConnectionError,
    ClientConnectionResetError,
    ClientConnectorCertificateError,
    ClientConnectorDNSError,
    ClientConnectorError,
    ClientConnectorSSLError,
    ClientError,
    ClientHttpProxyError,
    ClientOSError,
    ClientPayloadError,
    ClientProxyConnectionError,
    ClientResponseError,
    ClientSSLError,
    ConnectionTimeoutError,
    ContentTypeError,
    InvalidURL,
    InvalidUrlClientError,
    InvalidUrlRedirectClientError,
    NonHttpUrlClientError,
    NonHttpUrlRedirectClientError,
    RedirectClientError,
    ServerConnectionError,
    ServerDisconnectedError,
    ServerFingerprintMismatch,
    ServerTimeoutError,
    SocketTimeoutError,
    TooManyRedirects,
    WSMessageTypeError,
    WSServerHandshakeError,
)
from .client_middlewares import ClientMiddlewareType, build_client_middlewares
from .client_reqrep import (
    ClientRequest as ClientRequest,
    ClientResponse as ClientResponse,
    Fingerprint as Fingerprint,
    RequestInfo as RequestInfo,
    _merge_ssl_params,
)
from .client_ws import (
    DEFAULT_WS_CLIENT_TIMEOUT,
    ClientWebSocketResponse as ClientWebSocketResponse,
    ClientWSTimeout as ClientWSTimeout,
)
from .connector import (
    HTTP_AND_EMPTY_SCHEMA_SET,
    BaseConnector as BaseConnector,
    NamedPipeConnector as NamedPipeConnector,
    TCPConnector as TCPConnector,
    UnixConnector as UnixConnector,
)
from .cookiejar import CookieJar
from .helpers import (
    _SENTINEL,
    DEBUG,
    EMPTY_BODY_METHODS,
    BasicAuth,
    TimeoutHandle,
    get_env_proxy_for_url,
    sentinel,
    strip_auth_from_url,
)
from .http import WS_KEY, HttpVersion, WebSocketReader, WebSocketWriter
from .http_websocket import WSHandshakeError, ws_ext_gen, ws_ext_parse
from .tracing import Trace, TraceConfig
from .typedefs import JSONEncoder, LooseCookies, LooseHeaders, Query, StrOrURL

__all__ = (
    # client_exceptions
    "ClientConnectionError",
    "ClientConnectionResetError",
    "ClientConnectorCertificateError",
    "ClientConnectorDNSError",
    "ClientConnectorError",
    "ClientConnectorSSLError",
    "ClientError",
    "ClientHttpProxyError",
    "ClientOSError",
    "ClientPayloadError",
    "ClientProxyConnectionError",
    "ClientResponseError",
    "ClientSSLError",
    "ConnectionTimeoutError",
    "ContentTypeError",
    "InvalidURL",
    "InvalidUrlClientError",
    "RedirectClientError",
    "NonHttpUrlClientError",
    "InvalidUrlRedirectClientError",
    "NonHttpUrlRedirectClientError",
    "ServerConnectionError",
    "ServerDisconnectedError",
    "ServerFingerprintMismatch",
    "ServerTimeoutError",
    "SocketTimeoutError",
    "TooManyRedirects",
    "WSServerHandshakeError",
    # client_reqrep
    "ClientRequest",
    "ClientResponse",
    "Fingerprint",
    "RequestInfo",
    # connector
    "BaseConnector",
    "TCPConnector",
    "UnixConnector",
    "NamedPipeConnector",
    # client_ws
    "ClientWebSocketResponse",
    # client
    "ClientSession",
    "ClientTimeout",
    "ClientWSTimeout",
    "request",
    "WSMessageTypeError",
)


if TYPE_CHECKING:
    from ssl import SSLContext
else:
    SSLContext = None

if sys.version_info >= (3, 11) and TYPE_CHECKING:
    from typing import Unpack


class _RequestOptions(TypedDict, total=False):
    params: Query
    data: Any
    json: Any
    cookies: Union[LooseCookies, None]
    headers: Union[LooseHeaders, None]
    skip_auto_headers: Union[Iterable[str], None]
    auth: Union[BasicAuth, None]
    allow_redirects: bool
    max_redirects: int
    compress: Union[str, bool, None]
    chunked: Union[bool, None]
    expect100: bool
    raise_for_status: Union[None, bool, Callable[[ClientResponse], Awaitable[None]]]
    read_until_eof: bool
    proxy: Union[StrOrURL, None]
    proxy_auth: Union[BasicAuth, None]
    timeout: "Union[ClientTimeout, _SENTINEL, None]"
    ssl: Union[SSLContext, bool, Fingerprint]
    server_hostname: Union[str, None]
    proxy_headers: Union[LooseHeaders, None]
    trace_request_ctx: Union[Mapping[str, Any], None]
    read_bufsize: Union[int, None]
    auto_decompress: Union[bool, None]
    max_line_size: Union[int, None]
    max_field_size: Union[int, None]
    middlewares: Optional[Sequence[ClientMiddlewareType]]


@attr.s(auto_attribs=True, frozen=True, slots=True)
class ClientTimeout:
    total: Optional[float] = None
    connect: Optional[float] = None
    sock_read: Optional[float] = None
    sock_connect: Optional[float] = None
    ceil_threshold: float = 5

    # pool_queue_timeout: Optional[float] = None
    # dns_resolution_timeout: Optional[float] = None
    # socket_connect_timeout: Optional[float] = None
    # connection_acquiring_timeout: Optional[float] = None
    # new_connection_timeout: Optional[float] = None
    # http_header_timeout: Optional[float] = None
    # response_body_timeout: Optional[float] = None

    # to create a timeout specific for a single request, either
    # - create a completely new one to overwrite the default
    # - or use http://www.attrs.org/en/stable/api.html#attr.evolve
    # to overwrite the defaults


# 5 Minute default read timeout
DEFAULT_TIMEOUT: Final[ClientTimeout] = ClientTimeout(total=5 * 60, sock_connect=30)

# https://www.rfc-editor.org/rfc/rfc9110#section-9.2.2
IDEMPOTENT_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE", "PUT", "DELETE"})

_RetType = TypeVar("_RetType", ClientResponse, ClientWebSocketResponse)
_CharsetResolver = Callable[[ClientResponse, bytes], str]


class ClientSession:
    """First-class interface for making HTTP requests."""

    ATTRS = frozenset(
        [
            "_base_url",
            "_base_url_origin",
            "_source_traceback",
            "_connector",
            "_loop",
            "_cookie_jar",
            "_connector_owner",
            "_default_auth",
            "_version",
            "_json_serialize",
            "_requote_redirect_url",
            "_timeout",
            "_raise_for_status",
            "_auto_decompress",
            "_trust_env",
            "_default_headers",
            "_skip_auto_headers",
            "_request_class",
            "_response_class",
            "_ws_response_class",
            "_trace_configs",
            "_read_bufsize",
            "_max_line_size",
            "_max_field_size",
            "_resolve_charset",
            "_default_proxy",
            "_default_proxy_auth",
            "_retry_connection",
            "_middlewares",
            "requote_redirect_url",
        ]
    )

    _source_traceback: Optional[traceback.StackSummary] = None
    _connector: Optional[BaseConnector] = None

    def __init__(
        self,
        base_url: Optional[StrOrURL] = None,
        *,
        connector: Optional[BaseConnector] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        cookies: Optional[LooseCookies] = None,
        headers: Optional[LooseHeaders] = None,
        proxy: Optional[StrOrURL] = None,
        proxy_auth: Optional[BasicAuth] = None,
        skip_auto_headers: Optional[Iterable[str]] = None,
        auth: Optional[BasicAuth] = None,
        json_serialize: JSONEncoder = json.dumps,
        request_class: Type[ClientRequest] = ClientRequest,
        response_class: Type[ClientResponse] = ClientResponse,
        ws_response_class: Type[ClientWebSocketResponse] = ClientWebSocketResponse,
        version: HttpVersion = http.HttpVersion11,
        cookie_jar: Optional[AbstractCookieJar] = None,
        connector_owner: bool = True,
        raise_for_status: Union[
            bool, Callable[[ClientResponse], Awaitable[None]]
        ] = False,
        read_timeout: Union[float, _SENTINEL] = sentinel,
        conn_timeout: Optional[float] = None,
        timeout: Union[object, ClientTimeout] = sentinel,
        auto_decompress: bool = True,
        trust_env: bool = False,
        requote_redirect_url: bool = True,
        trace_configs: Optional[List[TraceConfig]] = None,
        read_bufsize: int = 2**16,
        max_line_size: int = 8190,
        max_field_size: int = 8190,
        fallback_charset_resolver: _CharsetResolver = lambda r, b: "utf-8",
        middlewares: Sequence[ClientMiddlewareType] = (),
        ssl_shutdown_timeout: Union[_SENTINEL, None, float] = sentinel,
    ) -> None:
        # We initialise _connector to None immediately, as it's referenced in __del__()
        # and could cause issues if an exception occurs during initialisation.
        self._connector: Optional[BaseConnector] = None

        if loop is None:
            if connector is not None:
                loop = connector._loop

        loop = loop or asyncio.get_running_loop()

        if base_url is None or isinstance(base_url, URL):
            self._base_url: Optional[URL] = base_url
            self._base_url_origin = None if base_url is None else base_url.origin()
        else:
            self._base_url = URL(base_url)
            self._base_url_origin = self._base_url.origin()
            assert self._base_url.absolute, "Only absolute URLs are supported"
        if self._base_url is not None and not self._base_url.path.endswith("/"):
            raise ValueError("base_url must have a trailing '/'")

        if timeout is sentinel or timeout is None:
            self._timeout = DEFAULT_TIMEOUT
            if read_timeout is not sentinel:
                warnings.warn(
                    "read_timeout is deprecated, use timeout argument instead",
                    DeprecationWarning,
                    stacklevel=2,
                )
                self._timeout = attr.evolve(self._timeout, total=read_timeout)
            if conn_timeout is not None:
                self._timeout = attr.evolve(self._timeout, connect=conn_timeout)
                warnings.warn(
                    "conn_timeout is deprecated, use timeout argument instead",
                    DeprecationWarning,
                    stacklevel=2,
                )
        else:
            if not isinstance(timeout, ClientTimeout):
                raise ValueError(
                    f"timeout parameter cannot be of {type(timeout)} type, "
                    "please use 'timeout=ClientTimeout(...)'",
                )
            self._timeout = timeout
            if read_timeout is not sentinel:
                raise ValueError(
                    "read_timeout and timeout parameters "
                    "conflict, please setup "
                    "timeout.read"
                )
            if conn_timeout is not None:
                raise ValueError(
                    "conn_timeout and timeout parameters "
                    "conflict, please setup "
                    "timeout.connect"
                )

        if ssl_shutdown_timeout is not sentinel:
            warnings.warn(
                "The ssl_shutdown_timeout parameter is deprecated and will be removed in aiohttp 4.0",
                DeprecationWarning,
                stacklevel=2,
            )

        if connector is None:
            connector = TCPConnector(
                loop=loop, ssl_shutdown_timeout=ssl_shutdown_timeout
            )

        if connector._loop is not loop:
            raise RuntimeError("Session and connector has to use same event loop")

        self._loop = loop

        if loop.get_debug():
            self._source_traceback = traceback.extract_stack(sys._getframe(1))

        if cookie_jar is None:
            cookie_jar = CookieJar(loop=loop)
        self._cookie_jar = cookie_jar

        if cookies:
            self._cookie_jar.update_cookies(cookies)

        self._connector = connector
        self._connector_owner = connector_owner
        self._default_auth = auth
        self._version = version
        self._json_serialize = json_serialize
        self._raise_for_status = raise_for_status
        self._auto_decompress = auto_decompress
        self._trust_env = trust_env
        self._requote_redirect_url = requote_redirect_url
        self._read_bufsize = read_bufsize
        self._max_line_size = max_line_size
        self._max_field_size = max_field_size

        # Convert to list of tuples
        if headers:
            real_headers: CIMultiDict[str] = CIMultiDict(headers)
        else:
            real_headers = CIMultiDict()
        self._default_headers: CIMultiDict[str] = real_headers
        if skip_auto_headers is not None:
            self._skip_auto_headers = frozenset(istr(i) for i in skip_auto_headers)
        else:
            self._skip_auto_headers = frozenset()

        self._request_class = request_class
        self._response_class = response_class
        self._ws_response_class = ws_response_class

        self._trace_configs = trace_configs or []
        for trace_config in self._trace_configs:
            trace_config.freeze()

        self._resolve_charset = fallback_charset_resolver

        self._default_proxy = proxy
        self._default_proxy_auth = proxy_auth
        self._retry_connection: bool = True
        self._middlewares = middlewares

    def __init_subclass__(cls: Type["ClientSession"]) -> None:
        warnings.warn(
            "Inheritance class {} from ClientSession "
            "is discouraged".format(cls.__name__),
            DeprecationWarning,
            stacklevel=2,
        )

    if DEBUG:

        def __setattr__(self, name: str, val: Any) -> None:
            if name not in self.ATTRS:
                warnings.warn(
                    "Setting custom ClientSession.{} attribute "
                    "is discouraged".format(name),
                    DeprecationWarning,
                    stacklevel=2,
                )
            super().__setattr__(name, val)

    def __del__(self, _warnings: Any = warnings) -> None:
        if not self.closed:
            kwargs = {"source": self}
            _warnings.warn(
                f"Unclosed client session {self!r}", ResourceWarning, **kwargs
            )
            context = {"client_session": self, "message": "Unclosed client session"}
            if self._source_traceback is not None:
                context["source_traceback"] = self._source_traceback
            self._loop.call_exception_handler(context)

    if sys.version_info >= (3, 11) and TYPE_CHECKING:

        def request(
            self,
            method: str,
            url: StrOrURL,
            **kwargs: Unpack[_RequestOptions],
        ) -> "_RequestContextManager": ...

    else:

        def request(
            self, method: str, url: StrOrURL, **kwargs: Any
        ) -> "_RequestContextManager":
            """Perform HTTP request."""
            return _RequestContextManager(self._request(method, url, **kwargs))

    def _build_url(self, str_or_url: StrOrURL) -> URL:
        url = URL(str_or_url)
        if self._base_url and not url.absolute:
            return self._base_url.join(url)
        return url

    async def _request(
        self,
        method: str,
        str_or_url: StrOrURL,
        *,
        params: Query = None,
        data: Any = None,
        json: Any = None,
        cookies: Optional[LooseCookies] = None,
        headers: Optional[LooseHeaders] = None,
        skip_auto_headers: Optional[Iterable[str]] = None,
        auth: Optional[BasicAuth] = None,
        allow_redirects: bool = True,
        max_redirects: int = 10,
        compress: Union[str, bool, None] = None,
        chunked: Optional[bool] = None,
        expect100: bool = False,
        raise_for_status: Union[
            None, bool, Callable[[ClientResponse], Awaitable[None]]
        ] = None,
        read_until_eof: bool = True,
        proxy: Optional[StrOrURL] = None,
        proxy_auth: Optional[BasicAuth] = None,
        timeout: Union[ClientTimeout, _SENTINEL] = sentinel,
        verify_ssl: Optional[bool] = None,
        fingerprint: Optional[bytes] = None,
        ssl_context: Optional[SSLContext] = None,
        ssl: Union[SSLContext, bool, Fingerprint] = True,
        server_hostname: Optional[str] = None,
        proxy_headers: Optional[LooseHeaders] = None,
        trace_request_ctx: Optional[Mapping[str, Any]] = None,
        read_bufsize: Optional[int] = None,
        auto_decompress: Optional[bool] = None,
        max_line_size: Optional[int] = None,
        max_field_size: Optional[int] = None,
        middlewares: Optional[Sequence[ClientMiddlewareType]] = None,
    ) -> ClientResponse:

        # NOTE: timeout clamps existing connect and read timeouts.  We cannot
        # set the default to None because we need to detect if the user wants
        # to use the existing timeouts by setting timeout to None.

        if self.closed:
            raise RuntimeError("Session is closed")

        ssl = _merge_ssl_params(ssl, verify_ssl, ssl_context, fingerprint)

        if data is not None and json is not None:
            raise ValueError(
                "data and json parameters can not be used at the same time"
            )
        elif json is not None:
            data = payload.JsonPayload(json, dumps=self._json_serialize)

        if not isinstance(chunked, bool) and chunked is not None:
            warnings.warn("Chunk size is deprecated #1615", DeprecationWarning)

        redirects = 0
        history: List[ClientResponse] = []
        version = self._version
        params = params or {}

        # Merge with default headers and transform to CIMultiDict
        headers = self._prepare_headers(headers)

        try:
            url = self._build_url(str_or_url)
        except ValueError as e:
            raise InvalidUrlClientError(str_or_url) from e

        assert self._connector is not None
        if url.scheme not in self._connector.allowed_protocol_schema_set:
            raise NonHttpUrlClientError(url)

        skip_headers: Optional[Iterable[istr]]
        if skip_auto_headers is not None:
            skip_headers = {
                istr(i) for i in skip_auto_headers
            } | self._skip_auto_headers
        elif self._skip_auto_headers:
            skip_headers = self._skip_auto_headers
        else:
            skip_headers = None

        if proxy is None:
            proxy = self._default_proxy
        if proxy_auth is None:
            proxy_auth = self._default_proxy_auth

        if proxy is None:
            proxy_headers = None
        else:
            proxy_headers = self._prepare_headers(proxy_headers)
            try:
                proxy = URL(proxy)
            except ValueError as e:
                raise InvalidURL(proxy) from e

        if timeout is sentinel:
            real_timeout: ClientTimeout = self._timeout
        else:
            if not isinstance(timeout, ClientTimeout):
                real_timeout = ClientTimeout(total=timeout)
            else:
                real_timeout = timeout
        # timeout is cumulative for all request operations
        # (request, redirects, responses, data consuming)
        tm = TimeoutHandle(
            self._loop, real_timeout.total, ceil_threshold=real_timeout.ceil_threshold
        )
        handle = tm.start()

        if read_bufsize is None:
            read_bufsize = self._read_bufsize

        if auto_decompress is None:
            auto_decompress = self._auto_decompress

        if max_line_size is None:
            max_line_size = self._max_line_size

        if max_field_size is None:
            max_field_size = self._max_field_size

        traces = [
            Trace(
                self,
                trace_config,
                trace_config.trace_config_ctx(trace_request_ctx=trace_request_ctx),
            )
            for trace_config in self._trace_configs
        ]

        for trace in traces:
            await trace.send_request_start(method, url.update_query(params), headers)

        timer = tm.timer()
        try:
            with timer:
                # https://www.rfc-editor.org/rfc/rfc9112.html#name-retrying-requests
                retry_persistent_connection = (
                    self._retry_connection and method in IDEMPOTENT_METHODS
                )
                while True:
                    url, auth_from_url = strip_auth_from_url(url)
                    if not url.raw_host:
                        # NOTE: Bail early, otherwise, causes `InvalidURL` through
                        # NOTE: `self._request_class()` below.
                        err_exc_cls = (
                            InvalidUrlRedirectClientError
                            if redirects
                            else InvalidUrlClientError
                        )
                        raise err_exc_cls(url)
                    # If `auth` was passed for an already authenticated URL,
                    # disallow only if this is the initial URL; this is to avoid issues
                    # with sketchy redirects that are not the caller's responsibility
                    if not history and (auth and auth_from_url):
                        raise ValueError(
                            "Cannot combine AUTH argument with "
                            "credentials encoded in URL"
                        )

                    # Override the auth with the one from the URL only if we
                    # have no auth, or if we got an auth from a redirect URL
                    if auth is None or (history and auth_from_url is not None):
                        auth = auth_from_url

                    if (
                        auth is None
                        and self._default_auth
                        and (
                            not self._base_url or self._base_url_origin == url.origin()
                        )
                    ):
                        auth = self._default_auth
                    # It would be confusing if we support explicit
                    # Authorization header with auth argument
                    if (
                        headers is not None
                        and auth is not None
                        and hdrs.AUTHORIZATION in headers
                    ):
                        raise ValueError(
                            "Cannot combine AUTHORIZATION header "
                            "with AUTH argument or credentials "
                            "encoded in URL"
                        )

                    all_cookies = self._cookie_jar.filter_cookies(url)

                    if cookies is not None:
                        tmp_cookie_jar = CookieJar(
                            quote_cookie=self._cookie_jar.quote_cookie
                        )
                        tmp_cookie_jar.update_cookies(cookies)
                        req_cookies = tmp_cookie_jar.filter_cookies(url)
                        if req_cookies:
                            all_cookies.load(req_cookies)

                    proxy_: Optional[URL] = None
                    if proxy is not None:
                        proxy_ = URL(proxy)
                    elif self._trust_env:
                        with suppress(LookupError):
                            proxy_, proxy_auth = await asyncio.to_thread(
                                get_env_proxy_for_url, url
                            )

                    req = self._request_class(
                        method,
                        url,
                        params=params,
                        headers=headers,
                        skip_auto_headers=skip_headers,
                        data=data,
                        cookies=all_cookies,
                        auth=auth,
                        version=version,
                        compress=compress,
                        chunked=chunked,
                        expect100=expect100,
                        loop=self._loop,
                        response_class=self._response_class,
                        proxy=proxy_,
                        proxy_auth=proxy_auth,
                        timer=timer,
                        session=self,
                        ssl=ssl if ssl is not None else True,
                        server_hostname=server_hostname,
                        proxy_headers=proxy_headers,
                        traces=traces,
                        trust_env=self.trust_env,
                    )

                    async def _connect_and_send_request(
                        req: ClientRequest,
                    ) -> ClientResponse:
                        # connection timeout
                        assert self._connector is not None
                        try:
                            conn = await self._connector.connect(
                                req, traces=traces, timeout=real_timeout
                            )
                        except asyncio.TimeoutError as exc:
                            raise ConnectionTimeoutError(
                                f"Connection timeout to host {req.url}"
                            ) from exc

                        assert conn.protocol is not None
                        conn.protocol.set_response_params(
                            timer=timer,
                            skip_payload=req.method in EMPTY_BODY_METHODS,
                            read_until_eof=read_until_eof,
                            auto_decompress=auto_decompress,
                            read_timeout=real_timeout.sock_read,
                            read_bufsize=read_bufsize,
                            timeout_ceil_threshold=self._connector._timeout_ceil_threshold,
                            max_line_size=max_line_size,
                            max_field_size=max_field_size,
                        )
                        try:
                            resp = await req.send(conn)
                            try:
                                await resp.start(conn)
                            except BaseException:
                                resp.close()
                                raise
                        except BaseException:
                            conn.close()
                            raise
                        return resp

                    # Apply middleware (if any) - per-request middleware overrides session middleware
                    effective_middlewares = (
                        self._middlewares if middlewares is None else middlewares
                    )

                    if effective_middlewares:
                        handler = build_client_middlewares(
                            _connect_and_send_request, effective_middlewares
                        )
                    else:
                        handler = _connect_and_send_request

                    try:
                        resp = await handler(req)
                    # Client connector errors should not be retried
                    except (
                        ConnectionTimeoutError,
                        ClientConnectorError,
                        ClientConnectorCertificateError,
                        ClientConnectorSSLError,
                    ):
                        raise
                    except (ClientOSError, ServerDisconnectedError):
                        if retry_persistent_connection:
                            retry_persistent_connection = False
                            continue
                        raise
                    except ClientError:
                        raise
                    except OSError as exc:
                        if exc.errno is None and isinstance(exc, asyncio.TimeoutError):
                            raise
                        raise ClientOSError(*exc.args) from exc

                    # Update cookies from raw headers to preserve duplicates
                    if resp._raw_cookie_headers:
                        self._cookie_jar.update_cookies_from_headers(
                            resp._raw_cookie_headers, resp.url
                        )

                    # redirects
                    if resp.status in (301, 302, 303, 307, 308) and allow_redirects:

                        for trace in traces:
                            await trace.send_request_redirect(
                                method, url.update_query(params), headers, resp
                            )

                        redirects += 1
                        history.append(resp)
                        if max_redirects and redirects >= max_redirects:
                            if req._body is not None:
                                await req._body.close()
                            resp.close()
                            raise TooManyRedirects(
                                history[0].request_info, tuple(history)
                            )

                        # For 301 and 302, mimic IE, now changed in RFC
                        # https://github.com/kennethreitz/requests/pull/269
                        if (resp.status == 303 and resp.method != hdrs.METH_HEAD) or (
                            resp.status in (301, 302) and resp.method == hdrs.METH_POST
                        ):
                            method = hdrs.METH_GET
                            data = None
                            if headers.get(hdrs.CONTENT_LENGTH):
                                headers.pop(hdrs.CONTENT_LENGTH)

                        r_url = resp.headers.get(hdrs.LOCATION) or resp.headers.get(
                            hdrs.URI
                        )
                        if r_url is None:
                            # see github.com/aio-libs/aiohttp/issues/2022
                            break
                        else:
                            # reading from correct redirection
                            # response is forbidden
                            resp.release()

                        try:
                            parsed_redirect_url = URL(
                                r_url, encoded=not self._requote_redirect_url
                            )
                        except ValueError as e:
                            if req._body is not None:
                                await req._body.close()
                            resp.close()
                            raise InvalidUrlRedirectClientError(
                                r_url,
                                "Server attempted redirecting to a location that does not look like a URL",
                            ) from e

                        scheme = parsed_redirect_url.scheme
                        if scheme not in HTTP_AND_EMPTY_SCHEMA_SET:
                            if req._body is not None:
                                await req._body.close()
                            resp.close()
                            raise NonHttpUrlRedirectClientError(r_url)
                        elif not scheme:
                            parsed_redirect_url = url.join(parsed_redirect_url)

                        try:
                            redirect_origin = parsed_redirect_url.origin()
                        except ValueError as origin_val_err:
                            if req._body is not None:
                                await req._body.close()
                            resp.close()
                            raise InvalidUrlRedirectClientError(
                                parsed_redirect_url,
                                "Invalid redirect URL origin",
                            ) from origin_val_err

                        if url.origin() != redirect_origin:
                            auth = None
                            headers.pop(hdrs.AUTHORIZATION, None)

                        url = parsed_redirect_url
                        params = {}
                        resp.release()
                        continue

                    break

            if req._body is not None:
                await req._body.close()
            # check response status
            if raise_for_status is None:
                raise_for_status = self._raise_for_status

            if raise_for_status is None:
                pass
            elif callable(raise_for_status):
                await raise_for_status(resp)
            elif raise_for_status:
                resp.raise_for_status()

            # register connection
            if handle is not None:
                if resp.connection is not None:
                    resp.connection.add_callback(handle.cancel)
                else:
                    handle.cancel()

            resp._history = tuple(history)

            for trace in traces:
                await trace.send_request_end(
                    method, url.update_query(params), headers, resp
                )
            return resp

        except BaseException as e:
            # cleanup timer
            tm.close()
            if handle:
                handle.cancel()
                handle = None

            for trace in traces:
                await trace.send_request_exception(
                    method, url.update_query(params), headers, e
                )
            raise

    def ws_connect(
        self,
        url: StrOrURL,
        *,
        method: str = hdrs.METH_GET,
        protocols: Iterable[str] = (),
        timeout: Union[ClientWSTimeout, _SENTINEL] = sentinel,
        receive_timeout: Optional[float] = None,
        autoclose: bool = True,
        autoping: bool = True,
        heartbeat: Optional[float] = None,
        auth: Optional[BasicAuth] = None,
        origin: Optional[str] = None,
        params: Query = None,
        headers: Optional[LooseHeaders] = None,
        proxy: Optional[StrOrURL] = None,
        proxy_auth: Optional[BasicAuth] = None,
        ssl: Union[SSLContext, bool, Fingerprint] = True,
        verify_ssl: Optional[bool] = None,
        fingerprint: Optional[bytes] = None,
        ssl_context: Optional[SSLContext] = None,
        server_hostname: Optional[str] = None,
        proxy_headers: Optional[LooseHeaders] = None,
        compress: int = 0,
        max_msg_size: int = 4 * 1024 * 1024,
    ) -> "_WSRequestContextManager":
        """Initiate websocket connection."""
        return _WSRequestContextManager(
            self._ws_connect(
                url,
                method=method,
                protocols=protocols,
                timeout=timeout,
                receive_timeout=receive_timeout,
                autoclose=autoclose,
                autoping=autoping,
                heartbeat=heartbeat,
                auth=auth,
                origin=origin,
                params=params,
                headers=headers,
                proxy=proxy,
                proxy_auth=proxy_auth,
                ssl=ssl,
                verify_ssl=verify_ssl,
                fingerprint=fingerprint,
                ssl_context=ssl_context,
                server_hostname=server_hostname,
                proxy_headers=proxy_headers,
                compress=compress,
                max_msg_size=max_msg_size,
            )
        )

    async def _ws_connect(
        self,
        url: StrOrURL,
        *,
        method: str = hdrs.METH_GET,
        protocols: Iterable[str] = (),
        timeout: Union[ClientWSTimeout, _SENTINEL] = sentinel,
        receive_timeout: Optional[float] = None,
        autoclose: bool = True,
        autoping: bool = True,
        heartbeat: Optional[float] = None,
        auth: Optional[BasicAuth] = None,
        origin: Optional[str] = None,
        params: Query = None,
        headers: Optional[LooseHeaders] = None,
        proxy: Optional[StrOrURL] = None,
        proxy_auth: Optional[BasicAuth] = None,
        ssl: Union[SSLContext, bool, Fingerprint] = True,
        verify_ssl: Optional[bool] = None,
        fingerprint: Optional[bytes] = None,
        ssl_context: Optional[SSLContext] = None,
        server_hostname: Optional[str] = None,
        proxy_headers: Optional[LooseHeaders] = None,
        compress: int = 0,
        max_msg_size: int = 4 * 1024 * 1024,
    ) -> ClientWebSocketResponse:
        if timeout is not sentinel:
            if isinstance(timeout, ClientWSTimeout):
                ws_timeout = timeout
            else:
                warnings.warn(
                    "parameter 'timeout' of type 'float' "
                    "is deprecated, please use "
                    "'timeout=ClientWSTimeout(ws_close=...)'",
                    DeprecationWarning,
                    stacklevel=2,
                )
                ws_timeout = ClientWSTimeout(ws_close=timeout)
        else:
            ws_timeout = DEFAULT_WS_CLIENT_TIMEOUT
        if receive_timeout is not None:
            warnings.warn(
                "float parameter 'receive_timeout' "
                "is deprecated, please use parameter "
                "'timeout=ClientWSTimeout(ws_receive=...)'",
                DeprecationWarning,
                stacklevel=2,
            )
            ws_timeout = attr.evolve(ws_timeout, ws_receive=receive_timeout)

        if headers is None:
            real_headers: CIMultiDict[str] = CIMultiDict()
        else:
            real_headers = CIMultiDict(headers)

        default_headers = {
            hdrs.UPGRADE: "websocket",
            hdrs.CONNECTION: "Upgrade",
            hdrs.SEC_WEBSOCKET_VERSION: "13",
        }

        for key, value in default_headers.items():
            real_headers.setdefault(key, value)

        sec_key = base64.b64encode(os.urandom(16))
        real_headers[hdrs.SEC_WEBSOCKET_KEY] = sec_key.decode()

        if protocols:
            real_headers[hdrs.SEC_WEBSOCKET_PROTOCOL] = ",".join(protocols)
        if origin is not None:
            real_headers[hdrs.ORIGIN] = origin
        if compress:
            extstr = ws_ext_gen(compress=compress)
            real_headers[hdrs.SEC_WEBSOCKET_EXTENSIONS] = extstr

        # For the sake of backward compatibility, if user passes in None, convert it to True
        if ssl is None:
            warnings.warn(
                "ssl=None is deprecated, please use ssl=True",
                DeprecationWarning,
                stacklevel=2,
            )
            ssl = True
        ssl = _merge_ssl_params(ssl, verify_ssl, ssl_context, fingerprint)

        # send request
        resp = await self.request(
            method,
            url,
            params=params,
            headers=real_headers,
            read_until_eof=False,
            auth=auth,
            proxy=proxy,
            proxy_auth=proxy_auth,
            ssl=ssl,
            server_hostname=server_hostname,
            proxy_headers=proxy_headers,
        )

        try:
            # check handshake
            if resp.status != 101:
                raise WSServerHandshakeError(
                    resp.request_info,
                    resp.history,
                    message="Invalid response status",
                    status=resp.status,
                    headers=resp.headers,
                )

            if resp.headers.get(hdrs.UPGRADE, "").lower() != "websocket":
                raise WSServerHandshakeError(
                    resp.request_info,
                    resp.history,
                    message="Invalid upgrade header",
                    status=resp.status,
                    headers=resp.headers,
                )

            if resp.headers.get(hdrs.CONNECTION, "").lower() != "upgrade":
                raise WSServerHandshakeError(
                    resp.request_info,
                    resp.history,
                    message="Invalid connection header",
                    status=resp.status,
                    headers=resp.headers,
                )

            # key calculation
            r_key = resp.headers.get(hdrs.SEC_WEBSOCKET_ACCEPT, "")
            match = base64.b64encode(hashlib.sha1(sec_key + WS_KEY).digest()).decode()
            if r_key != match:
                raise WSServerHandshakeError(
                    resp.request_info,
                    resp.history,
                    message="Invalid challenge response",
                    status=resp.status,
                    headers=resp.headers,
                )

            # websocket protocol
            protocol = None
            if protocols and hdrs.SEC_WEBSOCKET_PROTOCOL in resp.headers:
                resp_protocols = [
                    proto.strip()
                    for proto in resp.headers[hdrs.SEC_WEBSOCKET_PROTOCOL].split(",")
                ]

                for proto in resp_protocols:
                    if proto in protocols:
                        protocol = proto
                        break

            # websocket compress
            notakeover = False
            if compress:
                compress_hdrs = resp.headers.get(hdrs.SEC_WEBSOCKET_EXTENSIONS)
                if compress_hdrs:
                    try:
                        compress, notakeover = ws_ext_parse(compress_hdrs)
                    except WSHandshakeError as exc:
                        raise WSServerHandshakeError(
                            resp.request_info,
                            resp.history,
                            message=exc.args[0],
                            status=resp.status,
                            headers=resp.headers,
                        ) from exc
                else:
                    compress = 0
                    notakeover = False

            conn = resp.connection
            assert conn is not None
            conn_proto = conn.protocol
            assert conn_proto is not None

            # For WS connection the read_timeout must be either receive_timeout or greater
            # None == no timeout, i.e. infinite timeout, so None is the max timeout possible
            if ws_timeout.ws_receive is None:
                # Reset regardless
                conn_proto.read_timeout = None
            elif conn_proto.read_timeout is not None:
                conn_proto.read_timeout = max(
                    ws_timeout.ws_receive, conn_proto.read_timeout
                )

            transport = conn.transport
            assert transport is not None
            reader = WebSocketDataQueue(conn_proto, 2**16, loop=self._loop)
            conn_proto.set_parser(WebSocketReader(reader, max_msg_size), reader)
            writer = WebSocketWriter(
                conn_proto,
                transport,
                use_mask=True,
                compress=compress,
                notakeover=notakeover,
            )
        except BaseException:
            resp.close()
            raise
        else:
            return self._ws_response_class(
                reader,
                writer,
                protocol,
                resp,
                ws_timeout,
                autoclose,
                autoping,
                self._loop,
                heartbeat=heartbeat,
                compress=compress,
                client_notakeover=notakeover,
            )

    def _prepare_headers(self, headers: Optional[LooseHeaders]) -> "CIMultiDict[str]":
        """Add default headers and transform it to CIMultiDict"""
        # Convert headers to MultiDict
        result = CIMultiDict(self._default_headers)
        if headers:
            if not isinstance(headers, (MultiDictProxy, MultiDict)):
                headers = CIMultiDict(headers)
            added_names: Set[str] = set()
            for key, value in headers.items():
                if key in added_names:
                    result.add(key, value)
                else:
                    result[key] = value
                    added_names.add(key)
        return result

    if sys.version_info >= (3, 11) and TYPE_CHECKING:

        def get(
            self,
            url: StrOrURL,
            **kwargs: Unpack[_RequestOptions],
        ) -> "_RequestContextManager": ...

        def options(
            self,
            url: StrOrURL,
            **kwargs: Unpack[_RequestOptions],
        ) -> "_RequestContextManager": ...

        def head(
            self,
            url: StrOrURL,
            **kwargs: Unpack[_RequestOptions],
        ) -> "_RequestContextManager": ...

        def post(
            self,
            url: StrOrURL,
            **kwargs: Unpack[_RequestOptions],
        ) -> "_RequestContextManager": ...

        def put(
            self,
            url: StrOrURL,
            **kwargs: Unpack[_RequestOptions],
        ) -> "_RequestContextManager": ...

        def patch(
            self,
            url: StrOrURL,
            **kwargs: Unpack[_RequestOptions],
        ) -> "_RequestContextManager": ...

        def delete(
            self,
            url: StrOrURL,
            **kwargs: Unpack[_RequestOptions],
        ) -> "_RequestContextManager": ...

    else:

        def get(
            self, url: StrOrURL, *, allow_redirects: bool = True, **kwargs: Any
        ) -> "_RequestContextManager":
            """Perform HTTP GET request."""
            return _RequestContextManager(
                self._request(
                    hdrs.METH_GET, url, allow_redirects=allow_redirects, **kwargs
                )
            )

        def options(
            self, url: StrOrURL, *, allow_redirects: bool = True, **kwargs: Any
        ) -> "_RequestContextManager":
            """Perform HTTP OPTIONS request."""
            return _RequestContextManager(
                self._request(
                    hdrs.METH_OPTIONS, url, allow_redirects=allow_redirects, **kwargs
                )
            )

        def head(
            self, url: StrOrURL, *, allow_redirects: bool = False, **kwargs: Any
        ) -> "_RequestContextManager":
            """Perform HTTP HEAD request."""
            return _RequestContextManager(
                self._request(
                    hdrs.METH_HEAD, url, allow_redirects=allow_redirects, **kwargs
                )
            )

        def post(
            self, url: StrOrURL, *, data: Any = None, **kwargs: Any
        ) -> "_RequestContextManager":
            """Perform HTTP POST request."""
            return _RequestContextManager(
                self._request(hdrs.METH_POST, url, data=data, **kwargs)
            )

        def put(
            self, url: StrOrURL, *, data: Any = None, **kwargs: Any
        ) -> "_RequestContextManager":
            """Perform HTTP PUT request."""
            return _RequestContextManager(
                self._request(hdrs.METH_PUT, url, data=data, **kwargs)
            )

        def patch(
            self, url: StrOrURL, *, data: Any = None, **kwargs: Any
        ) -> "_RequestContextManager":
            """Perform HTTP PATCH request."""
            return _RequestContextManager(
                self._request(hdrs.METH_PATCH, url, data=data, **kwargs)
            )

        def delete(self, url: StrOrURL, **kwargs: Any) -> "_RequestContextManager":
            """Perform HTTP DELETE request."""
            return _RequestContextManager(
                self._request(hdrs.METH_DELETE, url, **kwargs)
            )

    async def close(self) -> None:
        """Close underlying connector.

        Release all acquired resources.
        """
        if not self.closed:
            if self._connector is not None and self._connector_owner:
                await self._connector.close()
            self._connector = None

    @property
    def closed(self) -> bool:
        """Is client session closed.

        A readonly property.
        """
        return self._connector is None or self._connector.closed

    @property
    def connector(self) -> Optional[BaseConnector]:
        """Connector instance used for the session."""
        return self._connector

    @property
    def cookie_jar(self) -> AbstractCookieJar:
        """The session cookies."""
        return self._cookie_jar

    @property
    def version(self) -> Tuple[int, int]:
        """The session HTTP protocol version."""
        return self._version

    @property
    def requote_redirect_url(self) -> bool:
        """Do URL requoting on redirection handling."""
        return self._requote_redirect_url

    @requote_redirect_url.setter
    def requote_redirect_url(self, val: bool) -> None:
        """Do URL requoting on redirection handling."""
        warnings.warn(
            "session.requote_redirect_url modification is deprecated #2778",
            DeprecationWarning,
            stacklevel=2,
        )
        self._requote_redirect_url = val

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        """Session's loop."""
        warnings.warn(
            "client.loop property is deprecated", DeprecationWarning, stacklevel=2
        )
        return self._loop

    @property
    def timeout(self) -> ClientTimeout:
        """Timeout for the session."""
        return self._timeout

    @property
    def headers(self) -> "CIMultiDict[str]":
        """The default headers of the client session."""
        return self._default_headers

    @property
    def skip_auto_headers(self) -> FrozenSet[istr]:
        """Headers for which autogeneration should be skipped"""
        return self._skip_auto_headers

    @property
    def auth(self) -> Optional[BasicAuth]:
        """An object that represents HTTP Basic Authorization"""
        return self._default_auth

    @property
    def json_serialize(self) -> JSONEncoder:
        """Json serializer callable"""
        return self._json_serialize

    @property
    def connector_owner(self) -> bool:
        """Should connector be closed on session closing"""
        return self._connector_owner

    @property
    def raise_for_status(
        self,
    ) -> Union[bool, Callable[[ClientResponse], Awaitable[None]]]:
        """Should `ClientResponse.raise_for_status()` be called for each response."""
        return self._raise_for_status

    @property
    def auto_decompress(self) -> bool:
        """Should the body response be automatically decompressed."""
        return self._auto_decompress

    @property
    def trust_env(self) -> bool:
        """
        Should proxies information from environment or netrc be trusted.

        Information is from HTTP_PROXY / HTTPS_PROXY environment variables
        or ~/.netrc file if present.
        """
        return self._trust_env

    @property
    def trace_configs(self) -> List[TraceConfig]:
        """A list of TraceConfig instances used for client tracing"""
        return self._trace_configs

    def detach(self) -> None:
        """Detach connector from session without closing the former.

        Session is switched to closed state anyway.
        """
        self._connector = None

    def __enter__(self) -> None:
        raise TypeError("Use async with instead")

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        # __exit__ should exist in pair with __enter__ but never executed
        pass  # pragma: no cover

    async def __aenter__(self) -> "ClientSession":
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        await self.close()


class _BaseRequestContextManager(Coroutine[Any, Any, _RetType], Generic[_RetType]):

    __slots__ = ("_coro", "_resp")

    def __init__(self, coro: Coroutine["asyncio.Future[Any]", None, _RetType]) -> None:
        self._coro: Coroutine["asyncio.Future[Any]", None, _RetType] = coro

    def send(self, arg: None) -> "asyncio.Future[Any]":
        return self._coro.send(arg)

    def throw(self, *args: Any, **kwargs: Any) -> "asyncio.Future[Any]":
        return self._coro.throw(*args, **kwargs)

    def close(self) -> None:
        return self._coro.close()

    def __await__(self) -> Generator[Any, None, _RetType]:
        ret = self._coro.__await__()
        return ret

    def __iter__(self) -> Generator[Any, None, _RetType]:
        return self.__await__()

    async def __aenter__(self) -> _RetType:
        self._resp: _RetType = await self._coro
        return await self._resp.__aenter__()

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        await self._resp.__aexit__(exc_type, exc, tb)


_RequestContextManager = _BaseRequestContextManager[ClientResponse]
_WSRequestContextManager = _BaseRequestContextManager[ClientWebSocketResponse]


class _SessionRequestContextManager:

    __slots__ = ("_coro", "_resp", "_session")

    def __init__(
        self,
        coro: Coroutine["asyncio.Future[Any]", None, ClientResponse],
        session: ClientSession,
    ) -> None:
        self._coro = coro
        self._resp: Optional[ClientResponse] = None
        self._session = session

    async def __aenter__(self) -> ClientResponse:
        try:
            self._resp = await self._coro
        except BaseException:
            await self._session.close()
            raise
        else:
            return self._resp

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        assert self._resp is not None
        self._resp.close()
        await self._session.close()


if sys.version_info >= (3, 11) and TYPE_CHECKING:

    def request(
        method: str,
        url: StrOrURL,
        *,
        version: HttpVersion = http.HttpVersion11,
        connector: Optional[BaseConnector] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        **kwargs: Unpack[_RequestOptions],
    ) -> _SessionRequestContextManager: ...

else:

    def request(
        method: str,
        url: StrOrURL,
        *,
        version: HttpVersion = http.HttpVersion11,
        connector: Optional[BaseConnector] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        **kwargs: Any,
    ) -> _SessionRequestContextManager:
        """Constructs and sends a request.

        Returns response object.
        method - HTTP method
        url - request url
        params - (optional) Dictionary or bytes to be sent in the query
        string of the new request
        data - (optional) Dictionary, bytes, or file-like object to
        send in the body of the request
        json - (optional) Any json compatible python object
        headers - (optional) Dictionary of HTTP Headers to send with
        the request
        cookies - (optional) Dict object to send with the request
        auth - (optional) BasicAuth named tuple represent HTTP Basic Auth
        auth - aiohttp.helpers.BasicAuth
        allow_redirects - (optional) If set to False, do not follow
        redirects
        version - Request HTTP version.
        compress - Set to True if request has to be compressed
        with deflate encoding.
        chunked - Set to chunk size for chunked transfer encoding.
        expect100 - Expect 100-continue response from server.
        connector - BaseConnector sub-class instance to support
        connection pooling.
        read_until_eof - Read response until eof if response
        does not have Content-Length header.
        loop - Optional event loop.
        timeout - Optional ClientTimeout settings structure, 5min
        total timeout by default.
        Usage::
        >>> import aiohttp
        >>> async with aiohttp.request('GET', 'http://python.org/') as resp:
        ...    print(resp)
        ...    data = await resp.read()
        <ClientResponse(https://www.python.org/) [200 OK]>
        """
        connector_owner = False
        if connector is None:
            connector_owner = True
            connector = TCPConnector(loop=loop, force_close=True)

        session = ClientSession(
            loop=loop,
            cookies=kwargs.pop("cookies", None),
            version=version,
            timeout=kwargs.pop("timeout", sentinel),
            connector=connector,
            connector_owner=connector_owner,
        )

        return _SessionRequestContextManager(
            session._request(method, url, **kwargs),
            session,
        )

# === NexusCore/openenv\Lib\site-packages\numpy\polynomial\legendre.py ===
"""
==================================================
Legendre Series (:mod:`numpy.polynomial.legendre`)
==================================================

This module provides a number of objects (mostly functions) useful for
dealing with Legendre series, including a `Legendre` class that
encapsulates the usual arithmetic operations.  (General information
on how this module represents and works with such polynomials is in the
docstring for its "parent" sub-package, `numpy.polynomial`).

Classes
-------
.. autosummary::
   :toctree: generated/

    Legendre

Constants
---------

.. autosummary::
   :toctree: generated/

   legdomain
   legzero
   legone
   legx

Arithmetic
----------

.. autosummary::
   :toctree: generated/

   legadd
   legsub
   legmulx
   legmul
   legdiv
   legpow
   legval
   legval2d
   legval3d
   leggrid2d
   leggrid3d

Calculus
--------

.. autosummary::
   :toctree: generated/

   legder
   legint

Misc Functions
--------------

.. autosummary::
   :toctree: generated/

   legfromroots
   legroots
   legvander
   legvander2d
   legvander3d
   leggauss
   legweight
   legcompanion
   legfit
   legtrim
   legline
   leg2poly
   poly2leg

See also
--------
numpy.polynomial

"""
import numpy as np
import numpy.linalg as la
from numpy.lib.array_utils import normalize_axis_index

from . import polyutils as pu
from ._polybase import ABCPolyBase

__all__ = [
    'legzero', 'legone', 'legx', 'legdomain', 'legline', 'legadd',
    'legsub', 'legmulx', 'legmul', 'legdiv', 'legpow', 'legval', 'legder',
    'legint', 'leg2poly', 'poly2leg', 'legfromroots', 'legvander',
    'legfit', 'legtrim', 'legroots', 'Legendre', 'legval2d', 'legval3d',
    'leggrid2d', 'leggrid3d', 'legvander2d', 'legvander3d', 'legcompanion',
    'leggauss', 'legweight']

legtrim = pu.trimcoef


def poly2leg(pol):
    """
    Convert a polynomial to a Legendre series.

    Convert an array representing the coefficients of a polynomial (relative
    to the "standard" basis) ordered from lowest degree to highest, to an
    array of the coefficients of the equivalent Legendre series, ordered
    from lowest to highest degree.

    Parameters
    ----------
    pol : array_like
        1-D array containing the polynomial coefficients

    Returns
    -------
    c : ndarray
        1-D array containing the coefficients of the equivalent Legendre
        series.

    See Also
    --------
    leg2poly

    Notes
    -----
    The easy way to do conversions between polynomial basis sets
    is to use the convert method of a class instance.

    Examples
    --------
    >>> import numpy as np
    >>> from numpy import polynomial as P
    >>> p = P.Polynomial(np.arange(4))
    >>> p
    Polynomial([0.,  1.,  2.,  3.], domain=[-1.,  1.], window=[-1.,  1.], ...
    >>> c = P.Legendre(P.legendre.poly2leg(p.coef))
    >>> c
    Legendre([ 1.  ,  3.25,  1.  ,  0.75], domain=[-1,  1], window=[-1,  1]) # may vary

    """
    [pol] = pu.as_series([pol])
    deg = len(pol) - 1
    res = 0
    for i in range(deg, -1, -1):
        res = legadd(legmulx(res), pol[i])
    return res


def leg2poly(c):
    """
    Convert a Legendre series to a polynomial.

    Convert an array representing the coefficients of a Legendre series,
    ordered from lowest degree to highest, to an array of the coefficients
    of the equivalent polynomial (relative to the "standard" basis) ordered
    from lowest to highest degree.

    Parameters
    ----------
    c : array_like
        1-D array containing the Legendre series coefficients, ordered
        from lowest order term to highest.

    Returns
    -------
    pol : ndarray
        1-D array containing the coefficients of the equivalent polynomial
        (relative to the "standard" basis) ordered from lowest order term
        to highest.

    See Also
    --------
    poly2leg

    Notes
    -----
    The easy way to do conversions between polynomial basis sets
    is to use the convert method of a class instance.

    Examples
    --------
    >>> from numpy import polynomial as P
    >>> c = P.Legendre(range(4))
    >>> c
    Legendre([0., 1., 2., 3.], domain=[-1.,  1.], window=[-1.,  1.], symbol='x')
    >>> p = c.convert(kind=P.Polynomial)
    >>> p
    Polynomial([-1. , -3.5,  3. ,  7.5], domain=[-1.,  1.], window=[-1., ...
    >>> P.legendre.leg2poly(range(4))
    array([-1. , -3.5,  3. ,  7.5])


    """
    from .polynomial import polyadd, polymulx, polysub

    [c] = pu.as_series([c])
    n = len(c)
    if n < 3:
        return c
    else:
        c0 = c[-2]
        c1 = c[-1]
        # i is the current degree of c1
        for i in range(n - 1, 1, -1):
            tmp = c0
            c0 = polysub(c[i - 2], (c1 * (i - 1)) / i)
            c1 = polyadd(tmp, (polymulx(c1) * (2 * i - 1)) / i)
        return polyadd(c0, polymulx(c1))


#
# These are constant arrays are of integer type so as to be compatible
# with the widest range of other types, such as Decimal.
#

# Legendre
legdomain = np.array([-1., 1.])

# Legendre coefficients representing zero.
legzero = np.array([0])

# Legendre coefficients representing one.
legone = np.array([1])

# Legendre coefficients representing the identity x.
legx = np.array([0, 1])


def legline(off, scl):
    """
    Legendre series whose graph is a straight line.



    Parameters
    ----------
    off, scl : scalars
        The specified line is given by ``off + scl*x``.

    Returns
    -------
    y : ndarray
        This module's representation of the Legendre series for
        ``off + scl*x``.

    See Also
    --------
    numpy.polynomial.polynomial.polyline
    numpy.polynomial.chebyshev.chebline
    numpy.polynomial.laguerre.lagline
    numpy.polynomial.hermite.hermline
    numpy.polynomial.hermite_e.hermeline

    Examples
    --------
    >>> import numpy.polynomial.legendre as L
    >>> L.legline(3,2)
    array([3, 2])
    >>> L.legval(-3, L.legline(3,2)) # should be -3
    -3.0

    """
    if scl != 0:
        return np.array([off, scl])
    else:
        return np.array([off])


def legfromroots(roots):
    """
    Generate a Legendre series with given roots.

    The function returns the coefficients of the polynomial

    .. math:: p(x) = (x - r_0) * (x - r_1) * ... * (x - r_n),

    in Legendre form, where the :math:`r_n` are the roots specified in `roots`.
    If a zero has multiplicity n, then it must appear in `roots` n times.
    For instance, if 2 is a root of multiplicity three and 3 is a root of
    multiplicity 2, then `roots` looks something like [2, 2, 2, 3, 3]. The
    roots can appear in any order.

    If the returned coefficients are `c`, then

    .. math:: p(x) = c_0 + c_1 * L_1(x) + ... +  c_n * L_n(x)

    The coefficient of the last term is not generally 1 for monic
    polynomials in Legendre form.

    Parameters
    ----------
    roots : array_like
        Sequence containing the roots.

    Returns
    -------
    out : ndarray
        1-D array of coefficients.  If all roots are real then `out` is a
        real array, if some of the roots are complex, then `out` is complex
        even if all the coefficients in the result are real (see Examples
        below).

    See Also
    --------
    numpy.polynomial.polynomial.polyfromroots
    numpy.polynomial.chebyshev.chebfromroots
    numpy.polynomial.laguerre.lagfromroots
    numpy.polynomial.hermite.hermfromroots
    numpy.polynomial.hermite_e.hermefromroots

    Examples
    --------
    >>> import numpy.polynomial.legendre as L
    >>> L.legfromroots((-1,0,1)) # x^3 - x relative to the standard basis
    array([ 0. , -0.4,  0. ,  0.4])
    >>> j = complex(0,1)
    >>> L.legfromroots((-j,j)) # x^2 + 1 relative to the standard basis
    array([ 1.33333333+0.j,  0.00000000+0.j,  0.66666667+0.j]) # may vary

    """
    return pu._fromroots(legline, legmul, roots)


def legadd(c1, c2):
    """
    Add one Legendre series to another.

    Returns the sum of two Legendre series `c1` + `c2`.  The arguments
    are sequences of coefficients ordered from lowest order term to
    highest, i.e., [1,2,3] represents the series ``P_0 + 2*P_1 + 3*P_2``.

    Parameters
    ----------
    c1, c2 : array_like
        1-D arrays of Legendre series coefficients ordered from low to
        high.

    Returns
    -------
    out : ndarray
        Array representing the Legendre series of their sum.

    See Also
    --------
    legsub, legmulx, legmul, legdiv, legpow

    Notes
    -----
    Unlike multiplication, division, etc., the sum of two Legendre series
    is a Legendre series (without having to "reproject" the result onto
    the basis set) so addition, just like that of "standard" polynomials,
    is simply "component-wise."

    Examples
    --------
    >>> from numpy.polynomial import legendre as L
    >>> c1 = (1,2,3)
    >>> c2 = (3,2,1)
    >>> L.legadd(c1,c2)
    array([4.,  4.,  4.])

    """
    return pu._add(c1, c2)


def legsub(c1, c2):
    """
    Subtract one Legendre series from another.

    Returns the difference of two Legendre series `c1` - `c2`.  The
    sequences of coefficients are from lowest order term to highest, i.e.,
    [1,2,3] represents the series ``P_0 + 2*P_1 + 3*P_2``.

    Parameters
    ----------
    c1, c2 : array_like
        1-D arrays of Legendre series coefficients ordered from low to
        high.

    Returns
    -------
    out : ndarray
        Of Legendre series coefficients representing their difference.

    See Also
    --------
    legadd, legmulx, legmul, legdiv, legpow

    Notes
    -----
    Unlike multiplication, division, etc., the difference of two Legendre
    series is a Legendre series (without having to "reproject" the result
    onto the basis set) so subtraction, just like that of "standard"
    polynomials, is simply "component-wise."

    Examples
    --------
    >>> from numpy.polynomial import legendre as L
    >>> c1 = (1,2,3)
    >>> c2 = (3,2,1)
    >>> L.legsub(c1,c2)
    array([-2.,  0.,  2.])
    >>> L.legsub(c2,c1) # -C.legsub(c1,c2)
    array([ 2.,  0., -2.])

    """
    return pu._sub(c1, c2)


def legmulx(c):
    """Multiply a Legendre series by x.

    Multiply the Legendre series `c` by x, where x is the independent
    variable.


    Parameters
    ----------
    c : array_like
        1-D array of Legendre series coefficients ordered from low to
        high.

    Returns
    -------
    out : ndarray
        Array representing the result of the multiplication.

    See Also
    --------
    legadd, legsub, legmul, legdiv, legpow

    Notes
    -----
    The multiplication uses the recursion relationship for Legendre
    polynomials in the form

    .. math::

      xP_i(x) = ((i + 1)*P_{i + 1}(x) + i*P_{i - 1}(x))/(2i + 1)

    Examples
    --------
    >>> from numpy.polynomial import legendre as L
    >>> L.legmulx([1,2,3])
    array([ 0.66666667, 2.2, 1.33333333, 1.8]) # may vary

    """
    # c is a trimmed copy
    [c] = pu.as_series([c])
    # The zero series needs special treatment
    if len(c) == 1 and c[0] == 0:
        return c

    prd = np.empty(len(c) + 1, dtype=c.dtype)
    prd[0] = c[0] * 0
    prd[1] = c[0]
    for i in range(1, len(c)):
        j = i + 1
        k = i - 1
        s = i + j
        prd[j] = (c[i] * j) / s
        prd[k] += (c[i] * i) / s
    return prd


def legmul(c1, c2):
    """
    Multiply one Legendre series by another.

    Returns the product of two Legendre series `c1` * `c2`.  The arguments
    are sequences of coefficients, from lowest order "term" to highest,
    e.g., [1,2,3] represents the series ``P_0 + 2*P_1 + 3*P_2``.

    Parameters
    ----------
    c1, c2 : array_like
        1-D arrays of Legendre series coefficients ordered from low to
        high.

    Returns
    -------
    out : ndarray
        Of Legendre series coefficients representing their product.

    See Also
    --------
    legadd, legsub, legmulx, legdiv, legpow

    Notes
    -----
    In general, the (polynomial) product of two C-series results in terms
    that are not in the Legendre polynomial basis set.  Thus, to express
    the product as a Legendre series, it is necessary to "reproject" the
    product onto said basis set, which may produce "unintuitive" (but
    correct) results; see Examples section below.

    Examples
    --------
    >>> from numpy.polynomial import legendre as L
    >>> c1 = (1,2,3)
    >>> c2 = (3,2)
    >>> L.legmul(c1,c2) # multiplication requires "reprojection"
    array([  4.33333333,  10.4       ,  11.66666667,   3.6       ]) # may vary

    """
    # s1, s2 are trimmed copies
    [c1, c2] = pu.as_series([c1, c2])

    if len(c1) > len(c2):
        c = c2
        xs = c1
    else:
        c = c1
        xs = c2

    if len(c) == 1:
        c0 = c[0] * xs
        c1 = 0
    elif len(c) == 2:
        c0 = c[0] * xs
        c1 = c[1] * xs
    else:
        nd = len(c)
        c0 = c[-2] * xs
        c1 = c[-1] * xs
        for i in range(3, len(c) + 1):
            tmp = c0
            nd = nd - 1
            c0 = legsub(c[-i] * xs, (c1 * (nd - 1)) / nd)
            c1 = legadd(tmp, (legmulx(c1) * (2 * nd - 1)) / nd)
    return legadd(c0, legmulx(c1))


def legdiv(c1, c2):
    """
    Divide one Legendre series by another.

    Returns the quotient-with-remainder of two Legendre series
    `c1` / `c2`.  The arguments are sequences of coefficients from lowest
    order "term" to highest, e.g., [1,2,3] represents the series
    ``P_0 + 2*P_1 + 3*P_2``.

    Parameters
    ----------
    c1, c2 : array_like
        1-D arrays of Legendre series coefficients ordered from low to
        high.

    Returns
    -------
    quo, rem : ndarrays
        Of Legendre series coefficients representing the quotient and
        remainder.

    See Also
    --------
    legadd, legsub, legmulx, legmul, legpow

    Notes
    -----
    In general, the (polynomial) division of one Legendre series by another
    results in quotient and remainder terms that are not in the Legendre
    polynomial basis set.  Thus, to express these results as a Legendre
    series, it is necessary to "reproject" the results onto the Legendre
    basis set, which may produce "unintuitive" (but correct) results; see
    Examples section below.

    Examples
    --------
    >>> from numpy.polynomial import legendre as L
    >>> c1 = (1,2,3)
    >>> c2 = (3,2,1)
    >>> L.legdiv(c1,c2) # quotient "intuitive," remainder not
    (array([3.]), array([-8., -4.]))
    >>> c2 = (0,1,2,3)
    >>> L.legdiv(c2,c1) # neither "intuitive"
    (array([-0.07407407,  1.66666667]), array([-1.03703704, -2.51851852])) # may vary

    """
    return pu._div(legmul, c1, c2)


def legpow(c, pow, maxpower=16):
    """Raise a Legendre series to a power.

    Returns the Legendre series `c` raised to the power `pow`. The
    argument `c` is a sequence of coefficients ordered from low to high.
    i.e., [1,2,3] is the series  ``P_0 + 2*P_1 + 3*P_2.``

    Parameters
    ----------
    c : array_like
        1-D array of Legendre series coefficients ordered from low to
        high.
    pow : integer
        Power to which the series will be raised
    maxpower : integer, optional
        Maximum power allowed. This is mainly to limit growth of the series
        to unmanageable size. Default is 16

    Returns
    -------
    coef : ndarray
        Legendre series of power.

    See Also
    --------
    legadd, legsub, legmulx, legmul, legdiv

    """
    return pu._pow(legmul, c, pow, maxpower)


def legder(c, m=1, scl=1, axis=0):
    """
    Differentiate a Legendre series.

    Returns the Legendre series coefficients `c` differentiated `m` times
    along `axis`.  At each iteration the result is multiplied by `scl` (the
    scaling factor is for use in a linear change of variable). The argument
    `c` is an array of coefficients from low to high degree along each
    axis, e.g., [1,2,3] represents the series ``1*L_0 + 2*L_1 + 3*L_2``
    while [[1,2],[1,2]] represents ``1*L_0(x)*L_0(y) + 1*L_1(x)*L_0(y) +
    2*L_0(x)*L_1(y) + 2*L_1(x)*L_1(y)`` if axis=0 is ``x`` and axis=1 is
    ``y``.

    Parameters
    ----------
    c : array_like
        Array of Legendre series coefficients. If c is multidimensional the
        different axis correspond to different variables with the degree in
        each axis given by the corresponding index.
    m : int, optional
        Number of derivatives taken, must be non-negative. (Default: 1)
    scl : scalar, optional
        Each differentiation is multiplied by `scl`.  The end result is
        multiplication by ``scl**m``.  This is for use in a linear change of
        variable. (Default: 1)
    axis : int, optional
        Axis over which the derivative is taken. (Default: 0).

    Returns
    -------
    der : ndarray
        Legendre series of the derivative.

    See Also
    --------
    legint

    Notes
    -----
    In general, the result of differentiating a Legendre series does not
    resemble the same operation on a power series. Thus the result of this
    function may be "unintuitive," albeit correct; see Examples section
    below.

    Examples
    --------
    >>> from numpy.polynomial import legendre as L
    >>> c = (1,2,3,4)
    >>> L.legder(c)
    array([  6.,   9.,  20.])
    >>> L.legder(c, 3)
    array([60.])
    >>> L.legder(c, scl=-1)
    array([ -6.,  -9., -20.])
    >>> L.legder(c, 2,-1)
    array([  9.,  60.])

    """
    c = np.array(c, ndmin=1, copy=True)
    if c.dtype.char in '?bBhHiIlLqQpP':
        c = c.astype(np.double)
    cnt = pu._as_int(m, "the order of derivation")
    iaxis = pu._as_int(axis, "the axis")
    if cnt < 0:
        raise ValueError("The order of derivation must be non-negative")
    iaxis = normalize_axis_index(iaxis, c.ndim)

    if cnt == 0:
        return c

    c = np.moveaxis(c, iaxis, 0)
    n = len(c)
    if cnt >= n:
        c = c[:1] * 0
    else:
        for i in range(cnt):
            n = n - 1
            c *= scl
            der = np.empty((n,) + c.shape[1:], dtype=c.dtype)
            for j in range(n, 2, -1):
                der[j - 1] = (2 * j - 1) * c[j]
                c[j - 2] += c[j]
            if n > 1:
                der[1] = 3 * c[2]
            der[0] = c[1]
            c = der
    c = np.moveaxis(c, 0, iaxis)
    return c


def legint(c, m=1, k=[], lbnd=0, scl=1, axis=0):
    """
    Integrate a Legendre series.

    Returns the Legendre series coefficients `c` integrated `m` times from
    `lbnd` along `axis`. At each iteration the resulting series is
    **multiplied** by `scl` and an integration constant, `k`, is added.
    The scaling factor is for use in a linear change of variable.  ("Buyer
    beware": note that, depending on what one is doing, one may want `scl`
    to be the reciprocal of what one might expect; for more information,
    see the Notes section below.)  The argument `c` is an array of
    coefficients from low to high degree along each axis, e.g., [1,2,3]
    represents the series ``L_0 + 2*L_1 + 3*L_2`` while [[1,2],[1,2]]
    represents ``1*L_0(x)*L_0(y) + 1*L_1(x)*L_0(y) + 2*L_0(x)*L_1(y) +
    2*L_1(x)*L_1(y)`` if axis=0 is ``x`` and axis=1 is ``y``.

    Parameters
    ----------
    c : array_like
        Array of Legendre series coefficients. If c is multidimensional the
        different axis correspond to different variables with the degree in
        each axis given by the corresponding index.
    m : int, optional
        Order of integration, must be positive. (Default: 1)
    k : {[], list, scalar}, optional
        Integration constant(s).  The value of the first integral at
        ``lbnd`` is the first value in the list, the value of the second
        integral at ``lbnd`` is the second value, etc.  If ``k == []`` (the
        default), all constants are set to zero.  If ``m == 1``, a single
        scalar can be given instead of a list.
    lbnd : scalar, optional
        The lower bound of the integral. (Default: 0)
    scl : scalar, optional
        Following each integration the result is *multiplied* by `scl`
        before the integration constant is added. (Default: 1)
    axis : int, optional
        Axis over which the integral is taken. (Default: 0).

    Returns
    -------
    S : ndarray
        Legendre series coefficient array of the integral.

    Raises
    ------
    ValueError
        If ``m < 0``, ``len(k) > m``, ``np.ndim(lbnd) != 0``, or
        ``np.ndim(scl) != 0``.

    See Also
    --------
    legder

    Notes
    -----
    Note that the result of each integration is *multiplied* by `scl`.
    Why is this important to note?  Say one is making a linear change of
    variable :math:`u = ax + b` in an integral relative to `x`.  Then
    :math:`dx = du/a`, so one will need to set `scl` equal to
    :math:`1/a` - perhaps not what one would have first thought.

    Also note that, in general, the result of integrating a C-series needs
    to be "reprojected" onto the C-series basis set.  Thus, typically,
    the result of this function is "unintuitive," albeit correct; see
    Examples section below.

    Examples
    --------
    >>> from numpy.polynomial import legendre as L
    >>> c = (1,2,3)
    >>> L.legint(c)
    array([ 0.33333333,  0.4       ,  0.66666667,  0.6       ]) # may vary
    >>> L.legint(c, 3)
    array([  1.66666667e-02,  -1.78571429e-02,   4.76190476e-02, # may vary
             -1.73472348e-18,   1.90476190e-02,   9.52380952e-03])
    >>> L.legint(c, k=3)
     array([ 3.33333333,  0.4       ,  0.66666667,  0.6       ]) # may vary
    >>> L.legint(c, lbnd=-2)
    array([ 7.33333333,  0.4       ,  0.66666667,  0.6       ]) # may vary
    >>> L.legint(c, scl=2)
    array([ 0.66666667,  0.8       ,  1.33333333,  1.2       ]) # may vary

    """
    c = np.array(c, ndmin=1, copy=True)
    if c.dtype.char in '?bBhHiIlLqQpP':
        c = c.astype(np.double)
    if not np.iterable(k):
        k = [k]
    cnt = pu._as_int(m, "the order of integration")
    iaxis = pu._as_int(axis, "the axis")
    if cnt < 0:
        raise ValueError("The order of integration must be non-negative")
    if len(k) > cnt:
        raise ValueError("Too many integration constants")
    if np.ndim(lbnd) != 0:
        raise ValueError("lbnd must be a scalar.")
    if np.ndim(scl) != 0:
        raise ValueError("scl must be a scalar.")
    iaxis = normalize_axis_index(iaxis, c.ndim)

    if cnt == 0:
        return c

    c = np.moveaxis(c, iaxis, 0)
    k = list(k) + [0] * (cnt - len(k))
    for i in range(cnt):
        n = len(c)
        c *= scl
        if n == 1 and np.all(c[0] == 0):
            c[0] += k[i]
        else:
            tmp = np.empty((n + 1,) + c.shape[1:], dtype=c.dtype)
            tmp[0] = c[0] * 0
            tmp[1] = c[0]
            if n > 1:
                tmp[2] = c[1] / 3
            for j in range(2, n):
                t = c[j] / (2 * j + 1)
                tmp[j + 1] = t
                tmp[j - 1] -= t
            tmp[0] += k[i] - legval(lbnd, tmp)
            c = tmp
    c = np.moveaxis(c, 0, iaxis)
    return c


def legval(x, c, tensor=True):
    """
    Evaluate a Legendre series at points x.

    If `c` is of length ``n + 1``, this function returns the value:

    .. math:: p(x) = c_0 * L_0(x) + c_1 * L_1(x) + ... + c_n * L_n(x)

    The parameter `x` is converted to an array only if it is a tuple or a
    list, otherwise it is treated as a scalar. In either case, either `x`
    or its elements must support multiplication and addition both with
    themselves and with the elements of `c`.

    If `c` is a 1-D array, then ``p(x)`` will have the same shape as `x`.  If
    `c` is multidimensional, then the shape of the result depends on the
    value of `tensor`. If `tensor` is true the shape will be c.shape[1:] +
    x.shape. If `tensor` is false the shape will be c.shape[1:]. Note that
    scalars have shape (,).

    Trailing zeros in the coefficients will be used in the evaluation, so
    they should be avoided if efficiency is a concern.

    Parameters
    ----------
    x : array_like, compatible object
        If `x` is a list or tuple, it is converted to an ndarray, otherwise
        it is left unchanged and treated as a scalar. In either case, `x`
        or its elements must support addition and multiplication with
        themselves and with the elements of `c`.
    c : array_like
        Array of coefficients ordered so that the coefficients for terms of
        degree n are contained in c[n]. If `c` is multidimensional the
        remaining indices enumerate multiple polynomials. In the two
        dimensional case the coefficients may be thought of as stored in
        the columns of `c`.
    tensor : boolean, optional
        If True, the shape of the coefficient array is extended with ones
        on the right, one for each dimension of `x`. Scalars have dimension 0
        for this action. The result is that every column of coefficients in
        `c` is evaluated for every element of `x`. If False, `x` is broadcast
        over the columns of `c` for the evaluation.  This keyword is useful
        when `c` is multidimensional. The default value is True.

    Returns
    -------
    values : ndarray, algebra_like
        The shape of the return value is described above.

    See Also
    --------
    legval2d, leggrid2d, legval3d, leggrid3d

    Notes
    -----
    The evaluation uses Clenshaw recursion, aka synthetic division.

    """
    c = np.array(c, ndmin=1, copy=None)
    if c.dtype.char in '?bBhHiIlLqQpP':
        c = c.astype(np.double)
    if isinstance(x, (tuple, list)):
        x = np.asarray(x)
    if isinstance(x, np.ndarray) and tensor:
        c = c.reshape(c.shape + (1,) * x.ndim)

    if len(c) == 1:
        c0 = c[0]
        c1 = 0
    elif len(c) == 2:
        c0 = c[0]
        c1 = c[1]
    else:
        nd = len(c)
        c0 = c[-2]
        c1 = c[-1]
        for i in range(3, len(c) + 1):
            tmp = c0
            nd = nd - 1
            c0 = c[-i] - c1 * ((nd - 1) / nd)
            c1 = tmp + c1 * x * ((2 * nd - 1) / nd)
    return c0 + c1 * x


def legval2d(x, y, c):
    """
    Evaluate a 2-D Legendre series at points (x, y).

    This function returns the values:

    .. math:: p(x,y) = \\sum_{i,j} c_{i,j} * L_i(x) * L_j(y)

    The parameters `x` and `y` are converted to arrays only if they are
    tuples or a lists, otherwise they are treated as a scalars and they
    must have the same shape after conversion. In either case, either `x`
    and `y` or their elements must support multiplication and addition both
    with themselves and with the elements of `c`.

    If `c` is a 1-D array a one is implicitly appended to its shape to make
    it 2-D. The shape of the result will be c.shape[2:] + x.shape.

    Parameters
    ----------
    x, y : array_like, compatible objects
        The two dimensional series is evaluated at the points ``(x, y)``,
        where `x` and `y` must have the same shape. If `x` or `y` is a list
        or tuple, it is first converted to an ndarray, otherwise it is left
        unchanged and if it isn't an ndarray it is treated as a scalar.
    c : array_like
        Array of coefficients ordered so that the coefficient of the term
        of multi-degree i,j is contained in ``c[i,j]``. If `c` has
        dimension greater than two the remaining indices enumerate multiple
        sets of coefficients.

    Returns
    -------
    values : ndarray, compatible object
        The values of the two dimensional Legendre series at points formed
        from pairs of corresponding values from `x` and `y`.

    See Also
    --------
    legval, leggrid2d, legval3d, leggrid3d
    """
    return pu._valnd(legval, c, x, y)


def leggrid2d(x, y, c):
    """
    Evaluate a 2-D Legendre series on the Cartesian product of x and y.

    This function returns the values:

    .. math:: p(a,b) = \\sum_{i,j} c_{i,j} * L_i(a) * L_j(b)

    where the points ``(a, b)`` consist of all pairs formed by taking
    `a` from `x` and `b` from `y`. The resulting points form a grid with
    `x` in the first dimension and `y` in the second.

    The parameters `x` and `y` are converted to arrays only if they are
    tuples or a lists, otherwise they are treated as a scalars. In either
    case, either `x` and `y` or their elements must support multiplication
    and addition both with themselves and with the elements of `c`.

    If `c` has fewer than two dimensions, ones are implicitly appended to
    its shape to make it 2-D. The shape of the result will be c.shape[2:] +
    x.shape + y.shape.

    Parameters
    ----------
    x, y : array_like, compatible objects
        The two dimensional series is evaluated at the points in the
        Cartesian product of `x` and `y`.  If `x` or `y` is a list or
        tuple, it is first converted to an ndarray, otherwise it is left
        unchanged and, if it isn't an ndarray, it is treated as a scalar.
    c : array_like
        Array of coefficients ordered so that the coefficient of the term of
        multi-degree i,j is contained in ``c[i,j]``. If `c` has dimension
        greater than two the remaining indices enumerate multiple sets of
        coefficients.

    Returns
    -------
    values : ndarray, compatible object
        The values of the two dimensional Chebyshev series at points in the
        Cartesian product of `x` and `y`.

    See Also
    --------
    legval, legval2d, legval3d, leggrid3d
    """
    return pu._gridnd(legval, c, x, y)


def legval3d(x, y, z, c):
    """
    Evaluate a 3-D Legendre series at points (x, y, z).

    This function returns the values:

    .. math:: p(x,y,z) = \\sum_{i,j,k} c_{i,j,k} * L_i(x) * L_j(y) * L_k(z)

    The parameters `x`, `y`, and `z` are converted to arrays only if
    they are tuples or a lists, otherwise they are treated as a scalars and
    they must have the same shape after conversion. In either case, either
    `x`, `y`, and `z` or their elements must support multiplication and
    addition both with themselves and with the elements of `c`.

    If `c` has fewer than 3 dimensions, ones are implicitly appended to its
    shape to make it 3-D. The shape of the result will be c.shape[3:] +
    x.shape.

    Parameters
    ----------
    x, y, z : array_like, compatible object
        The three dimensional series is evaluated at the points
        ``(x, y, z)``, where `x`, `y`, and `z` must have the same shape.  If
        any of `x`, `y`, or `z` is a list or tuple, it is first converted
        to an ndarray, otherwise it is left unchanged and if it isn't an
        ndarray it is  treated as a scalar.
    c : array_like
        Array of coefficients ordered so that the coefficient of the term of
        multi-degree i,j,k is contained in ``c[i,j,k]``. If `c` has dimension
        greater than 3 the remaining indices enumerate multiple sets of
        coefficients.

    Returns
    -------
    values : ndarray, compatible object
        The values of the multidimensional polynomial on points formed with
        triples of corresponding values from `x`, `y`, and `z`.

    See Also
    --------
    legval, legval2d, leggrid2d, leggrid3d
    """
    return pu._valnd(legval, c, x, y, z)


def leggrid3d(x, y, z, c):
    """
    Evaluate a 3-D Legendre series on the Cartesian product of x, y, and z.

    This function returns the values:

    .. math:: p(a,b,c) = \\sum_{i,j,k} c_{i,j,k} * L_i(a) * L_j(b) * L_k(c)

    where the points ``(a, b, c)`` consist of all triples formed by taking
    `a` from `x`, `b` from `y`, and `c` from `z`. The resulting points form
    a grid with `x` in the first dimension, `y` in the second, and `z` in
    the third.

    The parameters `x`, `y`, and `z` are converted to arrays only if they
    are tuples or a lists, otherwise they are treated as a scalars. In
    either case, either `x`, `y`, and `z` or their elements must support
    multiplication and addition both with themselves and with the elements
    of `c`.

    If `c` has fewer than three dimensions, ones are implicitly appended to
    its shape to make it 3-D. The shape of the result will be c.shape[3:] +
    x.shape + y.shape + z.shape.

    Parameters
    ----------
    x, y, z : array_like, compatible objects
        The three dimensional series is evaluated at the points in the
        Cartesian product of `x`, `y`, and `z`.  If `x`, `y`, or `z` is a
        list or tuple, it is first converted to an ndarray, otherwise it is
        left unchanged and, if it isn't an ndarray, it is treated as a
        scalar.
    c : array_like
        Array of coefficients ordered so that the coefficients for terms of
        degree i,j are contained in ``c[i,j]``. If `c` has dimension
        greater than two the remaining indices enumerate multiple sets of
        coefficients.

    Returns
    -------
    values : ndarray, compatible object
        The values of the two dimensional polynomial at points in the Cartesian
        product of `x` and `y`.

    See Also
    --------
    legval, legval2d, leggrid2d, legval3d
    """
    return pu._gridnd(legval, c, x, y, z)


def legvander(x, deg):
    """Pseudo-Vandermonde matrix of given degree.

    Returns the pseudo-Vandermonde matrix of degree `deg` and sample points
    `x`. The pseudo-Vandermonde matrix is defined by

    .. math:: V[..., i] = L_i(x)

    where ``0 <= i <= deg``. The leading indices of `V` index the elements of
    `x` and the last index is the degree of the Legendre polynomial.

    If `c` is a 1-D array of coefficients of length ``n + 1`` and `V` is the
    array ``V = legvander(x, n)``, then ``np.dot(V, c)`` and
    ``legval(x, c)`` are the same up to roundoff. This equivalence is
    useful both for least squares fitting and for the evaluation of a large
    number of Legendre series of the same degree and sample points.

    Parameters
    ----------
    x : array_like
        Array of points. The dtype is converted to float64 or complex128
        depending on whether any of the elements are complex. If `x` is
        scalar it is converted to a 1-D array.
    deg : int
        Degree of the resulting matrix.

    Returns
    -------
    vander : ndarray
        The pseudo-Vandermonde matrix. The shape of the returned matrix is
        ``x.shape + (deg + 1,)``, where The last index is the degree of the
        corresponding Legendre polynomial.  The dtype will be the same as
        the converted `x`.

    """
    ideg = pu._as_int(deg, "deg")
    if ideg < 0:
        raise ValueError("deg must be non-negative")

    x = np.array(x, copy=None, ndmin=1) + 0.0
    dims = (ideg + 1,) + x.shape
    dtyp = x.dtype
    v = np.empty(dims, dtype=dtyp)
    # Use forward recursion to generate the entries. This is not as accurate
    # as reverse recursion in this application but it is more efficient.
    v[0] = x * 0 + 1
    if ideg > 0:
        v[1] = x
        for i in range(2, ideg + 1):
            v[i] = (v[i - 1] * x * (2 * i - 1) - v[i - 2] * (i - 1)) / i
    return np.moveaxis(v, 0, -1)


def legvander2d(x, y, deg):
    """Pseudo-Vandermonde matrix of given degrees.

    Returns the pseudo-Vandermonde matrix of degrees `deg` and sample
    points ``(x, y)``. The pseudo-Vandermonde matrix is defined by

    .. math:: V[..., (deg[1] + 1)*i + j] = L_i(x) * L_j(y),

    where ``0 <= i <= deg[0]`` and ``0 <= j <= deg[1]``. The leading indices of
    `V` index the points ``(x, y)`` and the last index encodes the degrees of
    the Legendre polynomials.

    If ``V = legvander2d(x, y, [xdeg, ydeg])``, then the columns of `V`
    correspond to the elements of a 2-D coefficient array `c` of shape
    (xdeg + 1, ydeg + 1) in the order

    .. math:: c_{00}, c_{01}, c_{02} ... , c_{10}, c_{11}, c_{12} ...

    and ``np.dot(V, c.flat)`` and ``legval2d(x, y, c)`` will be the same
    up to roundoff. This equivalence is useful both for least squares
    fitting and for the evaluation of a large number of 2-D Legendre
    series of the same degrees and sample points.

    Parameters
    ----------
    x, y : array_like
        Arrays of point coordinates, all of the same shape. The dtypes
        will be converted to either float64 or complex128 depending on
        whether any of the elements are complex. Scalars are converted to
        1-D arrays.
    deg : list of ints
        List of maximum degrees of the form [x_deg, y_deg].

    Returns
    -------
    vander2d : ndarray
        The shape of the returned matrix is ``x.shape + (order,)``, where
        :math:`order = (deg[0]+1)*(deg[1]+1)`.  The dtype will be the same
        as the converted `x` and `y`.

    See Also
    --------
    legvander, legvander3d, legval2d, legval3d
    """
    return pu._vander_nd_flat((legvander, legvander), (x, y), deg)


def legvander3d(x, y, z, deg):
    """Pseudo-Vandermonde matrix of given degrees.

    Returns the pseudo-Vandermonde matrix of degrees `deg` and sample
    points ``(x, y, z)``. If `l`, `m`, `n` are the given degrees in `x`, `y`, `z`,
    then The pseudo-Vandermonde matrix is defined by

    .. math:: V[..., (m+1)(n+1)i + (n+1)j + k] = L_i(x)*L_j(y)*L_k(z),

    where ``0 <= i <= l``, ``0 <= j <= m``, and ``0 <= j <= n``.  The leading
    indices of `V` index the points ``(x, y, z)`` and the last index encodes
    the degrees of the Legendre polynomials.

    If ``V = legvander3d(x, y, z, [xdeg, ydeg, zdeg])``, then the columns
    of `V` correspond to the elements of a 3-D coefficient array `c` of
    shape (xdeg + 1, ydeg + 1, zdeg + 1) in the order

    .. math:: c_{000}, c_{001}, c_{002},... , c_{010}, c_{011}, c_{012},...

    and ``np.dot(V, c.flat)`` and ``legval3d(x, y, z, c)`` will be the
    same up to roundoff. This equivalence is useful both for least squares
    fitting and for the evaluation of a large number of 3-D Legendre
    series of the same degrees and sample points.

    Parameters
    ----------
    x, y, z : array_like
        Arrays of point coordinates, all of the same shape. The dtypes will
        be converted to either float64 or complex128 depending on whether
        any of the elements are complex. Scalars are converted to 1-D
        arrays.
    deg : list of ints
        List of maximum degrees of the form [x_deg, y_deg, z_deg].

    Returns
    -------
    vander3d : ndarray
        The shape of the returned matrix is ``x.shape + (order,)``, where
        :math:`order = (deg[0]+1)*(deg[1]+1)*(deg[2]+1)`.  The dtype will
        be the same as the converted `x`, `y`, and `z`.

    See Also
    --------
    legvander, legvander3d, legval2d, legval3d
    """
    return pu._vander_nd_flat((legvander, legvander, legvander), (x, y, z), deg)


def legfit(x, y, deg, rcond=None, full=False, w=None):
    """
    Least squares fit of Legendre series to data.

    Return the coefficients of a Legendre series of degree `deg` that is the
    least squares fit to the data values `y` given at points `x`. If `y` is
    1-D the returned coefficients will also be 1-D. If `y` is 2-D multiple
    fits are done, one for each column of `y`, and the resulting
    coefficients are stored in the corresponding columns of a 2-D return.
    The fitted polynomial(s) are in the form

    .. math::  p(x) = c_0 + c_1 * L_1(x) + ... + c_n * L_n(x),

    where `n` is `deg`.

    Parameters
    ----------
    x : array_like, shape (M,)
        x-coordinates of the M sample points ``(x[i], y[i])``.
    y : array_like, shape (M,) or (M, K)
        y-coordinates of the sample points. Several data sets of sample
        points sharing the same x-coordinates can be fitted at once by
        passing in a 2D-array that contains one dataset per column.
    deg : int or 1-D array_like
        Degree(s) of the fitting polynomials. If `deg` is a single integer
        all terms up to and including the `deg`'th term are included in the
        fit. For NumPy versions >= 1.11.0 a list of integers specifying the
        degrees of the terms to include may be used instead.
    rcond : float, optional
        Relative condition number of the fit. Singular values smaller than
        this relative to the largest singular value will be ignored. The
        default value is len(x)*eps, where eps is the relative precision of
        the float type, about 2e-16 in most cases.
    full : bool, optional
        Switch determining nature of return value. When it is False (the
        default) just the coefficients are returned, when True diagnostic
        information from the singular value decomposition is also returned.
    w : array_like, shape (`M`,), optional
        Weights. If not None, the weight ``w[i]`` applies to the unsquared
        residual ``y[i] - y_hat[i]`` at ``x[i]``. Ideally the weights are
        chosen so that the errors of the products ``w[i]*y[i]`` all have the
        same variance.  When using inverse-variance weighting, use
        ``w[i] = 1/sigma(y[i])``.  The default value is None.

    Returns
    -------
    coef : ndarray, shape (M,) or (M, K)
        Legendre coefficients ordered from low to high. If `y` was
        2-D, the coefficients for the data in column k of `y` are in
        column `k`. If `deg` is specified as a list, coefficients for
        terms not included in the fit are set equal to zero in the
        returned `coef`.

    [residuals, rank, singular_values, rcond] : list
        These values are only returned if ``full == True``

        - residuals -- sum of squared residuals of the least squares fit
        - rank -- the numerical rank of the scaled Vandermonde matrix
        - singular_values -- singular values of the scaled Vandermonde matrix
        - rcond -- value of `rcond`.

        For more details, see `numpy.linalg.lstsq`.

    Warns
    -----
    RankWarning
        The rank of the coefficient matrix in the least-squares fit is
        deficient. The warning is only raised if ``full == False``.  The
        warnings can be turned off by

        >>> import warnings
        >>> warnings.simplefilter('ignore', np.exceptions.RankWarning)

    See Also
    --------
    numpy.polynomial.polynomial.polyfit
    numpy.polynomial.chebyshev.chebfit
    numpy.polynomial.laguerre.lagfit
    numpy.polynomial.hermite.hermfit
    numpy.polynomial.hermite_e.hermefit
    legval : Evaluates a Legendre series.
    legvander : Vandermonde matrix of Legendre series.
    legweight : Legendre weight function (= 1).
    numpy.linalg.lstsq : Computes a least-squares fit from the matrix.
    scipy.interpolate.UnivariateSpline : Computes spline fits.

    Notes
    -----
    The solution is the coefficients of the Legendre series `p` that
    minimizes the sum of the weighted squared errors

    .. math:: E = \\sum_j w_j^2 * |y_j - p(x_j)|^2,

    where :math:`w_j` are the weights. This problem is solved by setting up
    as the (typically) overdetermined matrix equation

    .. math:: V(x) * c = w * y,

    where `V` is the weighted pseudo Vandermonde matrix of `x`, `c` are the
    coefficients to be solved for, `w` are the weights, and `y` are the
    observed values.  This equation is then solved using the singular value
    decomposition of `V`.

    If some of the singular values of `V` are so small that they are
    neglected, then a `~exceptions.RankWarning` will be issued. This means that
    the coefficient values may be poorly determined. Using a lower order fit
    will usually get rid of the warning.  The `rcond` parameter can also be
    set to a value smaller than its default, but the resulting fit may be
    spurious and have large contributions from roundoff error.

    Fits using Legendre series are usually better conditioned than fits
    using power series, but much can depend on the distribution of the
    sample points and the smoothness of the data. If the quality of the fit
    is inadequate splines may be a good alternative.

    References
    ----------
    .. [1] Wikipedia, "Curve fitting",
           https://en.wikipedia.org/wiki/Curve_fitting

    Examples
    --------

    """
    return pu._fit(legvander, x, y, deg, rcond, full, w)


def legcompanion(c):
    """Return the scaled companion matrix of c.

    The basis polynomials are scaled so that the companion matrix is
    symmetric when `c` is an Legendre basis polynomial. This provides
    better eigenvalue estimates than the unscaled case and for basis
    polynomials the eigenvalues are guaranteed to be real if
    `numpy.linalg.eigvalsh` is used to obtain them.

    Parameters
    ----------
    c : array_like
        1-D array of Legendre series coefficients ordered from low to high
        degree.

    Returns
    -------
    mat : ndarray
        Scaled companion matrix of dimensions (deg, deg).
    """
    # c is a trimmed copy
    [c] = pu.as_series([c])
    if len(c) < 2:
        raise ValueError('Series must have maximum degree of at least 1.')
    if len(c) == 2:
        return np.array([[-c[0] / c[1]]])

    n = len(c) - 1
    mat = np.zeros((n, n), dtype=c.dtype)
    scl = 1. / np.sqrt(2 * np.arange(n) + 1)
    top = mat.reshape(-1)[1::n + 1]
    bot = mat.reshape(-1)[n::n + 1]
    top[...] = np.arange(1, n) * scl[:n - 1] * scl[1:n]
    bot[...] = top
    mat[:, -1] -= (c[:-1] / c[-1]) * (scl / scl[-1]) * (n / (2 * n - 1))
    return mat


def legroots(c):
    """
    Compute the roots of a Legendre series.

    Return the roots (a.k.a. "zeros") of the polynomial

    .. math:: p(x) = \\sum_i c[i] * L_i(x).

    Parameters
    ----------
    c : 1-D array_like
        1-D array of coefficients.

    Returns
    -------
    out : ndarray
        Array of the roots of the series. If all the roots are real,
        then `out` is also real, otherwise it is complex.

    See Also
    --------
    numpy.polynomial.polynomial.polyroots
    numpy.polynomial.chebyshev.chebroots
    numpy.polynomial.laguerre.lagroots
    numpy.polynomial.hermite.hermroots
    numpy.polynomial.hermite_e.hermeroots

    Notes
    -----
    The root estimates are obtained as the eigenvalues of the companion
    matrix, Roots far from the origin of the complex plane may have large
    errors due to the numerical instability of the series for such values.
    Roots with multiplicity greater than 1 will also show larger errors as
    the value of the series near such points is relatively insensitive to
    errors in the roots. Isolated roots near the origin can be improved by
    a few iterations of Newton's method.

    The Legendre series basis polynomials aren't powers of ``x`` so the
    results of this function may seem unintuitive.

    Examples
    --------
    >>> import numpy.polynomial.legendre as leg
    >>> leg.legroots((1, 2, 3, 4)) # 4L_3 + 3L_2 + 2L_1 + 1L_0, all real roots
    array([-0.85099543, -0.11407192,  0.51506735]) # may vary

    """
    # c is a trimmed copy
    [c] = pu.as_series([c])
    if len(c) < 2:
        return np.array([], dtype=c.dtype)
    if len(c) == 2:
        return np.array([-c[0] / c[1]])

    # rotated companion matrix reduces error
    m = legcompanion(c)[::-1, ::-1]
    r = la.eigvals(m)
    r.sort()
    return r


def leggauss(deg):
    """
    Gauss-Legendre quadrature.

    Computes the sample points and weights for Gauss-Legendre quadrature.
    These sample points and weights will correctly integrate polynomials of
    degree :math:`2*deg - 1` or less over the interval :math:`[-1, 1]` with
    the weight function :math:`f(x) = 1`.

    Parameters
    ----------
    deg : int
        Number of sample points and weights. It must be >= 1.

    Returns
    -------
    x : ndarray
        1-D ndarray containing the sample points.
    y : ndarray
        1-D ndarray containing the weights.

    Notes
    -----
    The results have only been tested up to degree 100, higher degrees may
    be problematic. The weights are determined by using the fact that

    .. math:: w_k = c / (L'_n(x_k) * L_{n-1}(x_k))

    where :math:`c` is a constant independent of :math:`k` and :math:`x_k`
    is the k'th root of :math:`L_n`, and then scaling the results to get
    the right value when integrating 1.

    """
    ideg = pu._as_int(deg, "deg")
    if ideg <= 0:
        raise ValueError("deg must be a positive integer")

    # first approximation of roots. We use the fact that the companion
    # matrix is symmetric in this case in order to obtain better zeros.
    c = np.array([0] * deg + [1])
    m = legcompanion(c)
    x = la.eigvalsh(m)

    # improve roots by one application of Newton
    dy = legval(x, c)
    df = legval(x, legder(c))
    x -= dy / df

    # compute the weights. We scale the factor to avoid possible numerical
    # overflow.
    fm = legval(x, c[1:])
    fm /= np.abs(fm).max()
    df /= np.abs(df).max()
    w = 1 / (fm * df)

    # for Legendre we can also symmetrize
    w = (w + w[::-1]) / 2
    x = (x - x[::-1]) / 2

    # scale w to get the right value
    w *= 2. / w.sum()

    return x, w


def legweight(x):
    """
    Weight function of the Legendre polynomials.

    The weight function is :math:`1` and the interval of integration is
    :math:`[-1, 1]`. The Legendre polynomials are orthogonal, but not
    normalized, with respect to this weight function.

    Parameters
    ----------
    x : array_like
       Values at which the weight function will be computed.

    Returns
    -------
    w : ndarray
       The weight function at `x`.
    """
    w = x * 0.0 + 1.0
    return w

#
# Legendre series class
#

class Legendre(ABCPolyBase):
    """A Legendre series class.

    The Legendre class provides the standard Python numerical methods
    '+', '-', '*', '//', '%', 'divmod', '**', and '()' as well as the
    attributes and methods listed below.

    Parameters
    ----------
    coef : array_like
        Legendre coefficients in order of increasing degree, i.e.,
        ``(1, 2, 3)`` gives ``1*P_0(x) + 2*P_1(x) + 3*P_2(x)``.
    domain : (2,) array_like, optional
        Domain to use. The interval ``[domain[0], domain[1]]`` is mapped
        to the interval ``[window[0], window[1]]`` by shifting and scaling.
        The default value is [-1., 1.].
    window : (2,) array_like, optional
        Window, see `domain` for its use. The default value is [-1., 1.].
    symbol : str, optional
        Symbol used to represent the independent variable in string
        representations of the polynomial expression, e.g. for printing.
        The symbol must be a valid Python identifier. Default value is 'x'.

        .. versionadded:: 1.24

    """
    # Virtual Functions
    _add = staticmethod(legadd)
    _sub = staticmethod(legsub)
    _mul = staticmethod(legmul)
    _div = staticmethod(legdiv)
    _pow = staticmethod(legpow)
    _val = staticmethod(legval)
    _int = staticmethod(legint)
    _der = staticmethod(legder)
    _fit = staticmethod(legfit)
    _line = staticmethod(legline)
    _roots = staticmethod(legroots)
    _fromroots = staticmethod(legfromroots)

    # Virtual properties
    domain = np.array(legdomain)
    window = np.array(legdomain)
    basis_name = 'P'

# === NexusCore/openenv\Lib\site-packages\yarl\_url.py ===
import re
import sys
import warnings
from collections.abc import Mapping, Sequence
from enum import Enum
from functools import _CacheInfo, lru_cache
from ipaddress import ip_address
from typing import TYPE_CHECKING, Any, NoReturn, TypedDict, TypeVar, Union, overload
from urllib.parse import SplitResult, uses_relative

import idna
from multidict import MultiDict, MultiDictProxy
from propcache.api import under_cached_property as cached_property

from ._parse import (
    USES_AUTHORITY,
    SplitURLType,
    make_netloc,
    query_to_pairs,
    split_netloc,
    split_url,
    unsplit_result,
)
from ._path import normalize_path, normalize_path_segments
from ._query import (
    Query,
    QueryVariable,
    SimpleQuery,
    get_str_query,
    get_str_query_from_iterable,
    get_str_query_from_sequence_iterable,
)
from ._quoters import (
    FRAGMENT_QUOTER,
    FRAGMENT_REQUOTER,
    PATH_QUOTER,
    PATH_REQUOTER,
    PATH_SAFE_UNQUOTER,
    PATH_UNQUOTER,
    QS_UNQUOTER,
    QUERY_QUOTER,
    QUERY_REQUOTER,
    QUOTER,
    REQUOTER,
    UNQUOTER,
    human_quote,
)

DEFAULT_PORTS = {"http": 80, "https": 443, "ws": 80, "wss": 443, "ftp": 21}
USES_RELATIVE = frozenset(uses_relative)

# Special schemes https://url.spec.whatwg.org/#special-scheme
# are not allowed to have an empty host https://url.spec.whatwg.org/#url-representation
SCHEME_REQUIRES_HOST = frozenset(("http", "https", "ws", "wss", "ftp"))


# reg-name: unreserved / pct-encoded / sub-delims
# this pattern matches anything that is *not* in those classes. and is only used
# on lower-cased ASCII values.
NOT_REG_NAME = re.compile(
    r"""
        # any character not in the unreserved or sub-delims sets, plus %
        # (validated with the additional check for pct-encoded sequences below)
        [^a-z0-9\-._~!$&'()*+,;=%]
    |
        # % only allowed if it is part of a pct-encoded
        # sequence of 2 hex digits.
        %(?![0-9a-f]{2})
    """,
    re.VERBOSE,
)

_T = TypeVar("_T")

if sys.version_info >= (3, 11):
    from typing import Self
else:
    Self = Any


class UndefinedType(Enum):
    """Singleton type for use with not set sentinel values."""

    _singleton = 0


UNDEFINED = UndefinedType._singleton


class CacheInfo(TypedDict):
    """Host encoding cache."""

    idna_encode: _CacheInfo
    idna_decode: _CacheInfo
    ip_address: _CacheInfo
    host_validate: _CacheInfo
    encode_host: _CacheInfo


class _InternalURLCache(TypedDict, total=False):
    _val: SplitURLType
    _origin: "URL"
    absolute: bool
    hash: int
    scheme: str
    raw_authority: str
    authority: str
    raw_user: Union[str, None]
    user: Union[str, None]
    raw_password: Union[str, None]
    password: Union[str, None]
    raw_host: Union[str, None]
    host: Union[str, None]
    host_subcomponent: Union[str, None]
    host_port_subcomponent: Union[str, None]
    port: Union[int, None]
    explicit_port: Union[int, None]
    raw_path: str
    path: str
    _parsed_query: list[tuple[str, str]]
    query: "MultiDictProxy[str]"
    raw_query_string: str
    query_string: str
    path_qs: str
    raw_path_qs: str
    raw_fragment: str
    fragment: str
    raw_parts: tuple[str, ...]
    parts: tuple[str, ...]
    parent: "URL"
    raw_name: str
    name: str
    raw_suffix: str
    suffix: str
    raw_suffixes: tuple[str, ...]
    suffixes: tuple[str, ...]


def rewrite_module(obj: _T) -> _T:
    obj.__module__ = "yarl"
    return obj


@lru_cache
def encode_url(url_str: str) -> "URL":
    """Parse unencoded URL."""
    cache: _InternalURLCache = {}
    host: Union[str, None]
    scheme, netloc, path, query, fragment = split_url(url_str)
    if not netloc:  # netloc
        host = ""
    else:
        if ":" in netloc or "@" in netloc or "[" in netloc:
            # Complex netloc
            username, password, host, port = split_netloc(netloc)
        else:
            username = password = port = None
            host = netloc
        if host is None:
            if scheme in SCHEME_REQUIRES_HOST:
                msg = (
                    "Invalid URL: host is required for "
                    f"absolute urls with the {scheme} scheme"
                )
                raise ValueError(msg)
            else:
                host = ""
        host = _encode_host(host, validate_host=False)
        # Remove brackets as host encoder adds back brackets for IPv6 addresses
        cache["raw_host"] = host[1:-1] if "[" in host else host
        cache["explicit_port"] = port
        if password is None and username is None:
            # Fast path for URLs without user, password
            netloc = host if port is None else f"{host}:{port}"
            cache["raw_user"] = None
            cache["raw_password"] = None
        else:
            raw_user = REQUOTER(username) if username else username
            raw_password = REQUOTER(password) if password else password
            netloc = make_netloc(raw_user, raw_password, host, port)
            cache["raw_user"] = raw_user
            cache["raw_password"] = raw_password

    if path:
        path = PATH_REQUOTER(path)
        if netloc and "." in path:
            path = normalize_path(path)
    if query:
        query = QUERY_REQUOTER(query)
    if fragment:
        fragment = FRAGMENT_REQUOTER(fragment)

    cache["scheme"] = scheme
    cache["raw_path"] = "/" if not path and netloc else path
    cache["raw_query_string"] = query
    cache["raw_fragment"] = fragment

    self = object.__new__(URL)
    self._scheme = scheme
    self._netloc = netloc
    self._path = path
    self._query = query
    self._fragment = fragment
    self._cache = cache
    return self


@lru_cache
def pre_encoded_url(url_str: str) -> "URL":
    """Parse pre-encoded URL."""
    self = object.__new__(URL)
    val = split_url(url_str)
    self._scheme, self._netloc, self._path, self._query, self._fragment = val
    self._cache = {}
    return self


@lru_cache
def build_pre_encoded_url(
    scheme: str,
    authority: str,
    user: Union[str, None],
    password: Union[str, None],
    host: str,
    port: Union[int, None],
    path: str,
    query_string: str,
    fragment: str,
) -> "URL":
    """Build a pre-encoded URL from parts."""
    self = object.__new__(URL)
    self._scheme = scheme
    if authority:
        self._netloc = authority
    elif host:
        if port is not None:
            port = None if port == DEFAULT_PORTS.get(scheme) else port
        if user is None and password is None:
            self._netloc = host if port is None else f"{host}:{port}"
        else:
            self._netloc = make_netloc(user, password, host, port)
    else:
        self._netloc = ""
    self._path = path
    self._query = query_string
    self._fragment = fragment
    self._cache = {}
    return self


def from_parts_uncached(
    scheme: str, netloc: str, path: str, query: str, fragment: str
) -> "URL":
    """Create a new URL from parts."""
    self = object.__new__(URL)
    self._scheme = scheme
    self._netloc = netloc
    self._path = path
    self._query = query
    self._fragment = fragment
    self._cache = {}
    return self


from_parts = lru_cache(from_parts_uncached)


@rewrite_module
class URL:
    # Don't derive from str
    # follow pathlib.Path design
    # probably URL will not suffer from pathlib problems:
    # it's intended for libraries like aiohttp,
    # not to be passed into standard library functions like os.open etc.

    # URL grammar (RFC 3986)
    # pct-encoded = "%" HEXDIG HEXDIG
    # reserved    = gen-delims / sub-delims
    # gen-delims  = ":" / "/" / "?" / "#" / "[" / "]" / "@"
    # sub-delims  = "!" / "$" / "&" / "'" / "(" / ")"
    #             / "*" / "+" / "," / ";" / "="
    # unreserved  = ALPHA / DIGIT / "-" / "." / "_" / "~"
    # URI         = scheme ":" hier-part [ "?" query ] [ "#" fragment ]
    # hier-part   = "//" authority path-abempty
    #             / path-absolute
    #             / path-rootless
    #             / path-empty
    # scheme      = ALPHA *( ALPHA / DIGIT / "+" / "-" / "." )
    # authority   = [ userinfo "@" ] host [ ":" port ]
    # userinfo    = *( unreserved / pct-encoded / sub-delims / ":" )
    # host        = IP-literal / IPv4address / reg-name
    # IP-literal = "[" ( IPv6address / IPvFuture  ) "]"
    # IPvFuture  = "v" 1*HEXDIG "." 1*( unreserved / sub-delims / ":" )
    # IPv6address =                            6( h16 ":" ) ls32
    #             /                       "::" 5( h16 ":" ) ls32
    #             / [               h16 ] "::" 4( h16 ":" ) ls32
    #             / [ *1( h16 ":" ) h16 ] "::" 3( h16 ":" ) ls32
    #             / [ *2( h16 ":" ) h16 ] "::" 2( h16 ":" ) ls32
    #             / [ *3( h16 ":" ) h16 ] "::"    h16 ":"   ls32
    #             / [ *4( h16 ":" ) h16 ] "::"              ls32
    #             / [ *5( h16 ":" ) h16 ] "::"              h16
    #             / [ *6( h16 ":" ) h16 ] "::"
    # ls32        = ( h16 ":" h16 ) / IPv4address
    #             ; least-significant 32 bits of address
    # h16         = 1*4HEXDIG
    #             ; 16 bits of address represented in hexadecimal
    # IPv4address = dec-octet "." dec-octet "." dec-octet "." dec-octet
    # dec-octet   = DIGIT                 ; 0-9
    #             / %x31-39 DIGIT         ; 10-99
    #             / "1" 2DIGIT            ; 100-199
    #             / "2" %x30-34 DIGIT     ; 200-249
    #             / "25" %x30-35          ; 250-255
    # reg-name    = *( unreserved / pct-encoded / sub-delims )
    # port        = *DIGIT
    # path          = path-abempty    ; begins with "/" or is empty
    #               / path-absolute   ; begins with "/" but not "//"
    #               / path-noscheme   ; begins with a non-colon segment
    #               / path-rootless   ; begins with a segment
    #               / path-empty      ; zero characters
    # path-abempty  = *( "/" segment )
    # path-absolute = "/" [ segment-nz *( "/" segment ) ]
    # path-noscheme = segment-nz-nc *( "/" segment )
    # path-rootless = segment-nz *( "/" segment )
    # path-empty    = 0<pchar>
    # segment       = *pchar
    # segment-nz    = 1*pchar
    # segment-nz-nc = 1*( unreserved / pct-encoded / sub-delims / "@" )
    #               ; non-zero-length segment without any colon ":"
    # pchar         = unreserved / pct-encoded / sub-delims / ":" / "@"
    # query       = *( pchar / "/" / "?" )
    # fragment    = *( pchar / "/" / "?" )
    # URI-reference = URI / relative-ref
    # relative-ref  = relative-part [ "?" query ] [ "#" fragment ]
    # relative-part = "//" authority path-abempty
    #               / path-absolute
    #               / path-noscheme
    #               / path-empty
    # absolute-URI  = scheme ":" hier-part [ "?" query ]
    __slots__ = ("_cache", "_scheme", "_netloc", "_path", "_query", "_fragment")

    _cache: _InternalURLCache
    _scheme: str
    _netloc: str
    _path: str
    _query: str
    _fragment: str

    def __new__(
        cls,
        val: Union[str, SplitResult, "URL", UndefinedType] = UNDEFINED,
        *,
        encoded: bool = False,
        strict: Union[bool, None] = None,
    ) -> "URL":
        if strict is not None:  # pragma: no cover
            warnings.warn("strict parameter is ignored")
        if type(val) is str:
            return pre_encoded_url(val) if encoded else encode_url(val)
        if type(val) is cls:
            return val
        if type(val) is SplitResult:
            if not encoded:
                raise ValueError("Cannot apply decoding to SplitResult")
            return from_parts(*val)
        if isinstance(val, str):
            return pre_encoded_url(str(val)) if encoded else encode_url(str(val))
        if val is UNDEFINED:
            # Special case for UNDEFINED since it might be unpickling and we do
            # not want to cache as the `__set_state__` call would mutate the URL
            # object in the `pre_encoded_url` or `encoded_url` caches.
            self = object.__new__(URL)
            self._scheme = self._netloc = self._path = self._query = self._fragment = ""
            self._cache = {}
            return self
        raise TypeError("Constructor parameter should be str")

    @classmethod
    def build(
        cls,
        *,
        scheme: str = "",
        authority: str = "",
        user: Union[str, None] = None,
        password: Union[str, None] = None,
        host: str = "",
        port: Union[int, None] = None,
        path: str = "",
        query: Union[Query, None] = None,
        query_string: str = "",
        fragment: str = "",
        encoded: bool = False,
    ) -> "URL":
        """Creates and returns a new URL"""

        if authority and (user or password or host or port):
            raise ValueError(
                'Can\'t mix "authority" with "user", "password", "host" or "port".'
            )
        if port is not None and not isinstance(port, int):
            raise TypeError(f"The port is required to be int, got {type(port)!r}.")
        if port and not host:
            raise ValueError('Can\'t build URL with "port" but without "host".')
        if query and query_string:
            raise ValueError('Only one of "query" or "query_string" should be passed')
        if (
            scheme is None  # type: ignore[redundant-expr]
            or authority is None  # type: ignore[redundant-expr]
            or host is None  # type: ignore[redundant-expr]
            or path is None  # type: ignore[redundant-expr]
            or query_string is None  # type: ignore[redundant-expr]
            or fragment is None
        ):
            raise TypeError(
                'NoneType is illegal for "scheme", "authority", "host", "path", '
                '"query_string", and "fragment" args, use empty string instead.'
            )

        if query:
            query_string = get_str_query(query) or ""

        if encoded:
            return build_pre_encoded_url(
                scheme,
                authority,
                user,
                password,
                host,
                port,
                path,
                query_string,
                fragment,
            )

        self = object.__new__(URL)
        self._scheme = scheme
        _host: Union[str, None] = None
        if authority:
            user, password, _host, port = split_netloc(authority)
            _host = _encode_host(_host, validate_host=False) if _host else ""
        elif host:
            _host = _encode_host(host, validate_host=True)
        else:
            self._netloc = ""

        if _host is not None:
            if port is not None:
                port = None if port == DEFAULT_PORTS.get(scheme) else port
            if user is None and password is None:
                self._netloc = _host if port is None else f"{_host}:{port}"
            else:
                self._netloc = make_netloc(user, password, _host, port, True)

        path = PATH_QUOTER(path) if path else path
        if path and self._netloc:
            if "." in path:
                path = normalize_path(path)
            if path[0] != "/":
                msg = (
                    "Path in a URL with authority should "
                    "start with a slash ('/') if set"
                )
                raise ValueError(msg)

        self._path = path
        if not query and query_string:
            query_string = QUERY_QUOTER(query_string)
        self._query = query_string
        self._fragment = FRAGMENT_QUOTER(fragment) if fragment else fragment
        self._cache = {}
        return self

    def __init_subclass__(cls) -> NoReturn:
        raise TypeError(f"Inheriting a class {cls!r} from URL is forbidden")

    def __str__(self) -> str:
        if not self._path and self._netloc and (self._query or self._fragment):
            path = "/"
        else:
            path = self._path
        if (port := self.explicit_port) is not None and port == DEFAULT_PORTS.get(
            self._scheme
        ):
            # port normalization - using None for default ports to remove from rendering
            # https://datatracker.ietf.org/doc/html/rfc3986.html#section-6.2.3
            host = self.host_subcomponent
            netloc = make_netloc(self.raw_user, self.raw_password, host, None)
        else:
            netloc = self._netloc
        return unsplit_result(self._scheme, netloc, path, self._query, self._fragment)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}('{str(self)}')"

    def __bytes__(self) -> bytes:
        return str(self).encode("ascii")

    def __eq__(self, other: object) -> bool:
        if type(other) is not URL:
            return NotImplemented

        path1 = "/" if not self._path and self._netloc else self._path
        path2 = "/" if not other._path and other._netloc else other._path
        return (
            self._scheme == other._scheme
            and self._netloc == other._netloc
            and path1 == path2
            and self._query == other._query
            and self._fragment == other._fragment
        )

    def __hash__(self) -> int:
        if (ret := self._cache.get("hash")) is None:
            path = "/" if not self._path and self._netloc else self._path
            ret = self._cache["hash"] = hash(
                (self._scheme, self._netloc, path, self._query, self._fragment)
            )
        return ret

    def __le__(self, other: object) -> bool:
        if type(other) is not URL:
            return NotImplemented
        return self._val <= other._val

    def __lt__(self, other: object) -> bool:
        if type(other) is not URL:
            return NotImplemented
        return self._val < other._val

    def __ge__(self, other: object) -> bool:
        if type(other) is not URL:
            return NotImplemented
        return self._val >= other._val

    def __gt__(self, other: object) -> bool:
        if type(other) is not URL:
            return NotImplemented
        return self._val > other._val

    def __truediv__(self, name: str) -> "URL":
        if not isinstance(name, str):
            return NotImplemented  # type: ignore[unreachable]
        return self._make_child((str(name),))

    def __mod__(self, query: Query) -> "URL":
        return self.update_query(query)

    def __bool__(self) -> bool:
        return bool(self._netloc or self._path or self._query or self._fragment)

    def __getstate__(self) -> tuple[SplitResult]:
        return (tuple.__new__(SplitResult, self._val),)

    def __setstate__(
        self, state: Union[tuple[SplitURLType], tuple[None, _InternalURLCache]]
    ) -> None:
        if state[0] is None and isinstance(state[1], dict):
            # default style pickle
            val = state[1]["_val"]
        else:
            unused: list[object]
            val, *unused = state
        self._scheme, self._netloc, self._path, self._query, self._fragment = val
        self._cache = {}

    def _cache_netloc(self) -> None:
        """Cache the netloc parts of the URL."""
        c = self._cache
        split_loc = split_netloc(self._netloc)
        c["raw_user"], c["raw_password"], c["raw_host"], c["explicit_port"] = split_loc

    def is_absolute(self) -> bool:
        """A check for absolute URLs.

        Return True for absolute ones (having scheme or starting
        with //), False otherwise.

        Is is preferred to call the .absolute property instead
        as it is cached.
        """
        return self.absolute

    def is_default_port(self) -> bool:
        """A check for default port.

        Return True if port is default for specified scheme,
        e.g. 'http://python.org' or 'http://python.org:80', False
        otherwise.

        Return False for relative URLs.

        """
        if (explicit := self.explicit_port) is None:
            # If the explicit port is None, then the URL must be
            # using the default port unless its a relative URL
            # which does not have an implicit port / default port
            return self._netloc != ""
        return explicit == DEFAULT_PORTS.get(self._scheme)

    def origin(self) -> "URL":
        """Return an URL with scheme, host and port parts only.

        user, password, path, query and fragment are removed.

        """
        # TODO: add a keyword-only option for keeping user/pass maybe?
        return self._origin

    @cached_property
    def _val(self) -> SplitURLType:
        return (self._scheme, self._netloc, self._path, self._query, self._fragment)

    @cached_property
    def _origin(self) -> "URL":
        """Return an URL with scheme, host and port parts only.

        user, password, path, query and fragment are removed.
        """
        if not (netloc := self._netloc):
            raise ValueError("URL should be absolute")
        if not (scheme := self._scheme):
            raise ValueError("URL should have scheme")
        if "@" in netloc:
            encoded_host = self.host_subcomponent
            netloc = make_netloc(None, None, encoded_host, self.explicit_port)
        elif not self._path and not self._query and not self._fragment:
            return self
        return from_parts(scheme, netloc, "", "", "")

    def relative(self) -> "URL":
        """Return a relative part of the URL.

        scheme, user, password, host and port are removed.

        """
        if not self._netloc:
            raise ValueError("URL should be absolute")
        return from_parts("", "", self._path, self._query, self._fragment)

    @cached_property
    def absolute(self) -> bool:
        """A check for absolute URLs.

        Return True for absolute ones (having scheme or starting
        with //), False otherwise.

        """
        # `netloc`` is an empty string for relative URLs
        # Checking `netloc` is faster than checking `hostname`
        # because `hostname` is a property that does some extra work
        # to parse the host from the `netloc`
        return self._netloc != ""

    @cached_property
    def scheme(self) -> str:
        """Scheme for absolute URLs.

        Empty string for relative URLs or URLs starting with //

        """
        return self._scheme

    @cached_property
    def raw_authority(self) -> str:
        """Encoded authority part of URL.

        Empty string for relative URLs.

        """
        return self._netloc

    @cached_property
    def authority(self) -> str:
        """Decoded authority part of URL.

        Empty string for relative URLs.

        """
        return make_netloc(self.user, self.password, self.host, self.port)

    @cached_property
    def raw_user(self) -> Union[str, None]:
        """Encoded user part of URL.

        None if user is missing.

        """
        # not .username
        self._cache_netloc()
        return self._cache["raw_user"]

    @cached_property
    def user(self) -> Union[str, None]:
        """Decoded user part of URL.

        None if user is missing.

        """
        if (raw_user := self.raw_user) is None:
            return None
        return UNQUOTER(raw_user)

    @cached_property
    def raw_password(self) -> Union[str, None]:
        """Encoded password part of URL.

        None if password is missing.

        """
        self._cache_netloc()
        return self._cache["raw_password"]

    @cached_property
    def password(self) -> Union[str, None]:
        """Decoded password part of URL.

        None if password is missing.

        """
        if (raw_password := self.raw_password) is None:
            return None
        return UNQUOTER(raw_password)

    @cached_property
    def raw_host(self) -> Union[str, None]:
        """Encoded host part of URL.

        None for relative URLs.

        When working with IPv6 addresses, use the `host_subcomponent` property instead
        as it will return the host subcomponent with brackets.
        """
        # Use host instead of hostname for sake of shortness
        # May add .hostname prop later
        self._cache_netloc()
        return self._cache["raw_host"]

    @cached_property
    def host(self) -> Union[str, None]:
        """Decoded host part of URL.

        None for relative URLs.

        """
        if (raw := self.raw_host) is None:
            return None
        if raw and raw[-1].isdigit() or ":" in raw:
            # IP addresses are never IDNA encoded
            return raw
        return _idna_decode(raw)

    @cached_property
    def host_subcomponent(self) -> Union[str, None]:
        """Return the host subcomponent part of URL.

        None for relative URLs.

        https://datatracker.ietf.org/doc/html/rfc3986#section-3.2.2

        `IP-literal = "[" ( IPv6address / IPvFuture  ) "]"`

        Examples:
        - `http://example.com:8080` -> `example.com`
        - `http://example.com:80` -> `example.com`
        - `https://127.0.0.1:8443` -> `127.0.0.1`
        - `https://[::1]:8443` -> `[::1]`
        - `http://[::1]` -> `[::1]`

        """
        if (raw := self.raw_host) is None:
            return None
        return f"[{raw}]" if ":" in raw else raw

    @cached_property
    def host_port_subcomponent(self) -> Union[str, None]:
        """Return the host and port subcomponent part of URL.

        Trailing dots are removed from the host part.

        This value is suitable for use in the Host header of an HTTP request.

        None for relative URLs.

        https://datatracker.ietf.org/doc/html/rfc3986#section-3.2.2
        `IP-literal = "[" ( IPv6address / IPvFuture  ) "]"`
        https://datatracker.ietf.org/doc/html/rfc3986#section-3.2.3
        port        = *DIGIT

        Examples:
        - `http://example.com:8080` -> `example.com:8080`
        - `http://example.com:80` -> `example.com`
        - `http://example.com.:80` -> `example.com`
        - `https://127.0.0.1:8443` -> `127.0.0.1:8443`
        - `https://[::1]:8443` -> `[::1]:8443`
        - `http://[::1]` -> `[::1]`

        """
        if (raw := self.raw_host) is None:
            return None
        if raw[-1] == ".":
            # Remove all trailing dots from the netloc as while
            # they are valid FQDNs in DNS, TLS validation fails.
            # See https://github.com/aio-libs/aiohttp/issues/3636.
            # To avoid string manipulation we only call rstrip if
            # the last character is a dot.
            raw = raw.rstrip(".")
        port = self.explicit_port
        if port is None or port == DEFAULT_PORTS.get(self._scheme):
            return f"[{raw}]" if ":" in raw else raw
        return f"[{raw}]:{port}" if ":" in raw else f"{raw}:{port}"

    @cached_property
    def port(self) -> Union[int, None]:
        """Port part of URL, with scheme-based fallback.

        None for relative URLs or URLs without explicit port and
        scheme without default port substitution.

        """
        if (explicit_port := self.explicit_port) is not None:
            return explicit_port
        return DEFAULT_PORTS.get(self._scheme)

    @cached_property
    def explicit_port(self) -> Union[int, None]:
        """Port part of URL, without scheme-based fallback.

        None for relative URLs or URLs without explicit port.

        """
        self._cache_netloc()
        return self._cache["explicit_port"]

    @cached_property
    def raw_path(self) -> str:
        """Encoded path of URL.

        / for absolute URLs without path part.

        """
        return self._path if self._path or not self._netloc else "/"

    @cached_property
    def path(self) -> str:
        """Decoded path of URL.

        / for absolute URLs without path part.

        """
        return PATH_UNQUOTER(self._path) if self._path else "/" if self._netloc else ""

    @cached_property
    def path_safe(self) -> str:
        """Decoded path of URL.

        / for absolute URLs without path part.

        / (%2F) and % (%25) are not decoded

        """
        if self._path:
            return PATH_SAFE_UNQUOTER(self._path)
        return "/" if self._netloc else ""

    @cached_property
    def _parsed_query(self) -> list[tuple[str, str]]:
        """Parse query part of URL."""
        return query_to_pairs(self._query)

    @cached_property
    def query(self) -> "MultiDictProxy[str]":
        """A MultiDictProxy representing parsed query parameters in decoded
        representation.

        Empty value if URL has no query part.

        """
        return MultiDictProxy(MultiDict(self._parsed_query))

    @cached_property
    def raw_query_string(self) -> str:
        """Encoded query part of URL.

        Empty string if query is missing.

        """
        return self._query

    @cached_property
    def query_string(self) -> str:
        """Decoded query part of URL.

        Empty string if query is missing.

        """
        return QS_UNQUOTER(self._query) if self._query else ""

    @cached_property
    def path_qs(self) -> str:
        """Decoded path of URL with query."""
        return self.path if not (q := self.query_string) else f"{self.path}?{q}"

    @cached_property
    def raw_path_qs(self) -> str:
        """Encoded path of URL with query."""
        if q := self._query:
            return f"{self._path}?{q}" if self._path or not self._netloc else f"/?{q}"
        return self._path if self._path or not self._netloc else "/"

    @cached_property
    def raw_fragment(self) -> str:
        """Encoded fragment part of URL.

        Empty string if fragment is missing.

        """
        return self._fragment

    @cached_property
    def fragment(self) -> str:
        """Decoded fragment part of URL.

        Empty string if fragment is missing.

        """
        return UNQUOTER(self._fragment) if self._fragment else ""

    @cached_property
    def raw_parts(self) -> tuple[str, ...]:
        """A tuple containing encoded *path* parts.

        ('/',) for absolute URLs if *path* is missing.

        """
        path = self._path
        if self._netloc:
            return ("/", *path[1:].split("/")) if path else ("/",)
        if path and path[0] == "/":
            return ("/", *path[1:].split("/"))
        return tuple(path.split("/"))

    @cached_property
    def parts(self) -> tuple[str, ...]:
        """A tuple containing decoded *path* parts.

        ('/',) for absolute URLs if *path* is missing.

        """
        return tuple(UNQUOTER(part) for part in self.raw_parts)

    @cached_property
    def parent(self) -> "URL":
        """A new URL with last part of path removed and cleaned up query and
        fragment.

        """
        path = self._path
        if not path or path == "/":
            if self._fragment or self._query:
                return from_parts(self._scheme, self._netloc, path, "", "")
            return self
        parts = path.split("/")
        return from_parts(self._scheme, self._netloc, "/".join(parts[:-1]), "", "")

    @cached_property
    def raw_name(self) -> str:
        """The last part of raw_parts."""
        parts = self.raw_parts
        if not self._netloc:
            return parts[-1]
        parts = parts[1:]
        return parts[-1] if parts else ""

    @cached_property
    def name(self) -> str:
        """The last part of parts."""
        return UNQUOTER(self.raw_name)

    @cached_property
    def raw_suffix(self) -> str:
        name = self.raw_name
        i = name.rfind(".")
        return name[i:] if 0 < i < len(name) - 1 else ""

    @cached_property
    def suffix(self) -> str:
        return UNQUOTER(self.raw_suffix)

    @cached_property
    def raw_suffixes(self) -> tuple[str, ...]:
        name = self.raw_name
        if name.endswith("."):
            return ()
        name = name.lstrip(".")
        return tuple("." + suffix for suffix in name.split(".")[1:])

    @cached_property
    def suffixes(self) -> tuple[str, ...]:
        return tuple(UNQUOTER(suffix) for suffix in self.raw_suffixes)

    def _make_child(self, paths: "Sequence[str]", encoded: bool = False) -> "URL":
        """
        add paths to self._path, accounting for absolute vs relative paths,
        keep existing, but do not create new, empty segments
        """
        parsed: list[str] = []
        needs_normalize: bool = False
        for idx, path in enumerate(reversed(paths)):
            # empty segment of last is not removed
            last = idx == 0
            if path and path[0] == "/":
                raise ValueError(
                    f"Appending path {path!r} starting from slash is forbidden"
                )
            # We need to quote the path if it is not already encoded
            # This cannot be done at the end because the existing
            # path is already quoted and we do not want to double quote
            # the existing path.
            path = path if encoded else PATH_QUOTER(path)
            needs_normalize |= "." in path
            segments = path.split("/")
            segments.reverse()
            # remove trailing empty segment for all but the last path
            parsed += segments[1:] if not last and segments[0] == "" else segments

        if (path := self._path) and (old_segments := path.split("/")):
            # If the old path ends with a slash, the last segment is an empty string
            # and should be removed before adding the new path segments.
            old = old_segments[:-1] if old_segments[-1] == "" else old_segments
            old.reverse()
            parsed += old

        # If the netloc is present, inject a leading slash when adding a
        # path to an absolute URL where there was none before.
        if (netloc := self._netloc) and parsed and parsed[-1] != "":
            parsed.append("")

        parsed.reverse()
        if not netloc or not needs_normalize:
            return from_parts(self._scheme, netloc, "/".join(parsed), "", "")

        path = "/".join(normalize_path_segments(parsed))
        # If normalizing the path segments removed the leading slash, add it back.
        if path and path[0] != "/":
            path = f"/{path}"
        return from_parts(self._scheme, netloc, path, "", "")

    def with_scheme(self, scheme: str) -> "URL":
        """Return a new URL with scheme replaced."""
        # N.B. doesn't cleanup query/fragment
        if not isinstance(scheme, str):
            raise TypeError("Invalid scheme type")
        lower_scheme = scheme.lower()
        netloc = self._netloc
        if not netloc and lower_scheme in SCHEME_REQUIRES_HOST:
            msg = (
                "scheme replacement is not allowed for "
                f"relative URLs for the {lower_scheme} scheme"
            )
            raise ValueError(msg)
        return from_parts(lower_scheme, netloc, self._path, self._query, self._fragment)

    def with_user(self, user: Union[str, None]) -> "URL":
        """Return a new URL with user replaced.

        Autoencode user if needed.

        Clear user/password if user is None.

        """
        # N.B. doesn't cleanup query/fragment
        if user is None:
            password = None
        elif isinstance(user, str):
            user = QUOTER(user)
            password = self.raw_password
        else:
            raise TypeError("Invalid user type")
        if not (netloc := self._netloc):
            raise ValueError("user replacement is not allowed for relative URLs")
        encoded_host = self.host_subcomponent or ""
        netloc = make_netloc(user, password, encoded_host, self.explicit_port)
        return from_parts(self._scheme, netloc, self._path, self._query, self._fragment)

    def with_password(self, password: Union[str, None]) -> "URL":
        """Return a new URL with password replaced.

        Autoencode password if needed.

        Clear password if argument is None.

        """
        # N.B. doesn't cleanup query/fragment
        if password is None:
            pass
        elif isinstance(password, str):
            password = QUOTER(password)
        else:
            raise TypeError("Invalid password type")
        if not (netloc := self._netloc):
            raise ValueError("password replacement is not allowed for relative URLs")
        encoded_host = self.host_subcomponent or ""
        port = self.explicit_port
        netloc = make_netloc(self.raw_user, password, encoded_host, port)
        return from_parts(self._scheme, netloc, self._path, self._query, self._fragment)

    def with_host(self, host: str) -> "URL":
        """Return a new URL with host replaced.

        Autoencode host if needed.

        Changing host for relative URLs is not allowed, use .join()
        instead.

        """
        # N.B. doesn't cleanup query/fragment
        if not isinstance(host, str):
            raise TypeError("Invalid host type")
        if not (netloc := self._netloc):
            raise ValueError("host replacement is not allowed for relative URLs")
        if not host:
            raise ValueError("host removing is not allowed")
        encoded_host = _encode_host(host, validate_host=True) if host else ""
        port = self.explicit_port
        netloc = make_netloc(self.raw_user, self.raw_password, encoded_host, port)
        return from_parts(self._scheme, netloc, self._path, self._query, self._fragment)

    def with_port(self, port: Union[int, None]) -> "URL":
        """Return a new URL with port replaced.

        Clear port to default if None is passed.

        """
        # N.B. doesn't cleanup query/fragment
        if port is not None:
            if isinstance(port, bool) or not isinstance(port, int):
                raise TypeError(f"port should be int or None, got {type(port)}")
            if not (0 <= port <= 65535):
                raise ValueError(f"port must be between 0 and 65535, got {port}")
        if not (netloc := self._netloc):
            raise ValueError("port replacement is not allowed for relative URLs")
        encoded_host = self.host_subcomponent or ""
        netloc = make_netloc(self.raw_user, self.raw_password, encoded_host, port)
        return from_parts(self._scheme, netloc, self._path, self._query, self._fragment)

    def with_path(
        self,
        path: str,
        *,
        encoded: bool = False,
        keep_query: bool = False,
        keep_fragment: bool = False,
    ) -> "URL":
        """Return a new URL with path replaced."""
        netloc = self._netloc
        if not encoded:
            path = PATH_QUOTER(path)
            if netloc:
                path = normalize_path(path) if "." in path else path
        if path and path[0] != "/":
            path = f"/{path}"
        query = self._query if keep_query else ""
        fragment = self._fragment if keep_fragment else ""
        return from_parts(self._scheme, netloc, path, query, fragment)

    @overload
    def with_query(self, query: Query) -> "URL": ...

    @overload
    def with_query(self, **kwargs: QueryVariable) -> "URL": ...

    def with_query(self, *args: Any, **kwargs: Any) -> "URL":
        """Return a new URL with query part replaced.

        Accepts any Mapping (e.g. dict, multidict.MultiDict instances)
        or str, autoencode the argument if needed.

        A sequence of (key, value) pairs is supported as well.

        It also can take an arbitrary number of keyword arguments.

        Clear query if None is passed.

        """
        # N.B. doesn't cleanup query/fragment
        query = get_str_query(*args, **kwargs) or ""
        return from_parts_uncached(
            self._scheme, self._netloc, self._path, query, self._fragment
        )

    @overload
    def extend_query(self, query: Query) -> "URL": ...

    @overload
    def extend_query(self, **kwargs: QueryVariable) -> "URL": ...

    def extend_query(self, *args: Any, **kwargs: Any) -> "URL":
        """Return a new URL with query part combined with the existing.

        This method will not remove existing query parameters.

        Example:
        >>> url = URL('http://example.com/?a=1&b=2')
        >>> url.extend_query(a=3, c=4)
        URL('http://example.com/?a=1&b=2&a=3&c=4')
        """
        if not (new_query := get_str_query(*args, **kwargs)):
            return self
        if query := self._query:
            # both strings are already encoded so we can use a simple
            # string join
            query += new_query if query[-1] == "&" else f"&{new_query}"
        else:
            query = new_query
        return from_parts_uncached(
            self._scheme, self._netloc, self._path, query, self._fragment
        )

    @overload
    def update_query(self, query: Query) -> "URL": ...

    @overload
    def update_query(self, **kwargs: QueryVariable) -> "URL": ...

    def update_query(self, *args: Any, **kwargs: Any) -> "URL":
        """Return a new URL with query part updated.

        This method will overwrite existing query parameters.

        Example:
        >>> url = URL('http://example.com/?a=1&b=2')
        >>> url.update_query(a=3, c=4)
        URL('http://example.com/?a=3&b=2&c=4')
        """
        in_query: Union[str, Mapping[str, QueryVariable], None]
        if kwargs:
            if args:
                msg = "Either kwargs or single query parameter must be present"
                raise ValueError(msg)
            in_query = kwargs
        elif len(args) == 1:
            in_query = args[0]
        else:
            raise ValueError("Either kwargs or single query parameter must be present")

        if in_query is None:
            query = ""
        elif not in_query:
            query = self._query
        elif isinstance(in_query, Mapping):
            qm: MultiDict[QueryVariable] = MultiDict(self._parsed_query)
            qm.update(in_query)
            query = get_str_query_from_sequence_iterable(qm.items())
        elif isinstance(in_query, str):
            qstr: MultiDict[str] = MultiDict(self._parsed_query)
            qstr.update(query_to_pairs(in_query))
            query = get_str_query_from_iterable(qstr.items())
        elif isinstance(in_query, (bytes, bytearray, memoryview)):  # type: ignore[unreachable]
            msg = "Invalid query type: bytes, bytearray and memoryview are forbidden"
            raise TypeError(msg)
        elif isinstance(in_query, Sequence):
            # We don't expect sequence values if we're given a list of pairs
            # already; only mappings like builtin `dict` which can't have the
            # same key pointing to multiple values are allowed to use
            # `_query_seq_pairs`.
            qs: MultiDict[SimpleQuery] = MultiDict(self._parsed_query)
            qs.update(in_query)
            query = get_str_query_from_iterable(qs.items())
        else:
            raise TypeError(
                "Invalid query type: only str, mapping or "
                "sequence of (key, value) pairs is allowed"
            )
        return from_parts_uncached(
            self._scheme, self._netloc, self._path, query, self._fragment
        )

    def without_query_params(self, *query_params: str) -> "URL":
        """Remove some keys from query part and return new URL."""
        params_to_remove = set(query_params) & self.query.keys()
        if not params_to_remove:
            return self
        return self.with_query(
            tuple(
                (name, value)
                for name, value in self.query.items()
                if name not in params_to_remove
            )
        )

    def with_fragment(self, fragment: Union[str, None]) -> "URL":
        """Return a new URL with fragment replaced.

        Autoencode fragment if needed.

        Clear fragment to default if None is passed.

        """
        # N.B. doesn't cleanup query/fragment
        if fragment is None:
            raw_fragment = ""
        elif not isinstance(fragment, str):
            raise TypeError("Invalid fragment type")
        else:
            raw_fragment = FRAGMENT_QUOTER(fragment)
        if self._fragment == raw_fragment:
            return self
        return from_parts(
            self._scheme, self._netloc, self._path, self._query, raw_fragment
        )

    def with_name(
        self,
        name: str,
        *,
        keep_query: bool = False,
        keep_fragment: bool = False,
    ) -> "URL":
        """Return a new URL with name (last part of path) replaced.

        Query and fragment parts are cleaned up.

        Name is encoded if needed.

        """
        # N.B. DOES cleanup query/fragment
        if not isinstance(name, str):
            raise TypeError("Invalid name type")
        if "/" in name:
            raise ValueError("Slash in name is not allowed")
        name = PATH_QUOTER(name)
        if name in (".", ".."):
            raise ValueError(". and .. values are forbidden")
        parts = list(self.raw_parts)
        if netloc := self._netloc:
            if len(parts) == 1:
                parts.append(name)
            else:
                parts[-1] = name
            parts[0] = ""  # replace leading '/'
        else:
            parts[-1] = name
            if parts[0] == "/":
                parts[0] = ""  # replace leading '/'

        query = self._query if keep_query else ""
        fragment = self._fragment if keep_fragment else ""
        return from_parts(self._scheme, netloc, "/".join(parts), query, fragment)

    def with_suffix(
        self,
        suffix: str,
        *,
        keep_query: bool = False,
        keep_fragment: bool = False,
    ) -> "URL":
        """Return a new URL with suffix (file extension of name) replaced.

        Query and fragment parts are cleaned up.

        suffix is encoded if needed.
        """
        if not isinstance(suffix, str):
            raise TypeError("Invalid suffix type")
        if suffix and not suffix[0] == "." or suffix == "." or "/" in suffix:
            raise ValueError(f"Invalid suffix {suffix!r}")
        name = self.raw_name
        if not name:
            raise ValueError(f"{self!r} has an empty name")
        old_suffix = self.raw_suffix
        suffix = PATH_QUOTER(suffix)
        name = name + suffix if not old_suffix else name[: -len(old_suffix)] + suffix
        if name in (".", ".."):
            raise ValueError(". and .. values are forbidden")
        parts = list(self.raw_parts)
        if netloc := self._netloc:
            if len(parts) == 1:
                parts.append(name)
            else:
                parts[-1] = name
            parts[0] = ""  # replace leading '/'
        else:
            parts[-1] = name
            if parts[0] == "/":
                parts[0] = ""  # replace leading '/'

        query = self._query if keep_query else ""
        fragment = self._fragment if keep_fragment else ""
        return from_parts(self._scheme, netloc, "/".join(parts), query, fragment)

    def join(self, url: "URL") -> "URL":
        """Join URLs

        Construct a full (“absolute”) URL by combining a “base URL”
        (self) with another URL (url).

        Informally, this uses components of the base URL, in
        particular the addressing scheme, the network location and
        (part of) the path, to provide missing components in the
        relative URL.

        """
        if type(url) is not URL:
            raise TypeError("url should be URL")

        scheme = url._scheme or self._scheme
        if scheme != self._scheme or scheme not in USES_RELATIVE:
            return url

        # scheme is in uses_authority as uses_authority is a superset of uses_relative
        if (join_netloc := url._netloc) and scheme in USES_AUTHORITY:
            return from_parts(scheme, join_netloc, url._path, url._query, url._fragment)

        orig_path = self._path
        if join_path := url._path:
            if join_path[0] == "/":
                path = join_path
            elif not orig_path:
                path = f"/{join_path}"
            elif orig_path[-1] == "/":
                path = f"{orig_path}{join_path}"
            else:
                # …
                # and relativizing ".."
                # parts[0] is / for absolute urls,
                # this join will add a double slash there
                path = "/".join([*self.parts[:-1], ""]) + join_path
                # which has to be removed
                if orig_path[0] == "/":
                    path = path[1:]
            path = normalize_path(path) if "." in path else path
        else:
            path = orig_path

        return from_parts(
            scheme,
            self._netloc,
            path,
            url._query if join_path or url._query else self._query,
            url._fragment if join_path or url._fragment else self._fragment,
        )

    def joinpath(self, *other: str, encoded: bool = False) -> "URL":
        """Return a new URL with the elements in other appended to the path."""
        return self._make_child(other, encoded=encoded)

    def human_repr(self) -> str:
        """Return decoded human readable string for URL representation."""
        user = human_quote(self.user, "#/:?@[]")
        password = human_quote(self.password, "#/:?@[]")
        if (host := self.host) and ":" in host:
            host = f"[{host}]"
        path = human_quote(self.path, "#?")
        if TYPE_CHECKING:
            assert path is not None
        query_string = "&".join(
            "{}={}".format(human_quote(k, "#&+;="), human_quote(v, "#&+;="))
            for k, v in self.query.items()
        )
        fragment = human_quote(self.fragment, "")
        if TYPE_CHECKING:
            assert fragment is not None
        netloc = make_netloc(user, password, host, self.explicit_port)
        return unsplit_result(self._scheme, netloc, path, query_string, fragment)


_DEFAULT_IDNA_SIZE = 256
_DEFAULT_ENCODE_SIZE = 512


@lru_cache(_DEFAULT_IDNA_SIZE)
def _idna_decode(raw: str) -> str:
    try:
        return idna.decode(raw.encode("ascii"))
    except UnicodeError:  # e.g. '::1'
        return raw.encode("ascii").decode("idna")


@lru_cache(_DEFAULT_IDNA_SIZE)
def _idna_encode(host: str) -> str:
    try:
        return idna.encode(host, uts46=True).decode("ascii")
    except UnicodeError:
        return host.encode("idna").decode("ascii")


@lru_cache(_DEFAULT_ENCODE_SIZE)
def _encode_host(host: str, validate_host: bool) -> str:
    """Encode host part of URL."""
    # If the host ends with a digit or contains a colon, its likely
    # an IP address.
    if host and (host[-1].isdigit() or ":" in host):
        raw_ip, sep, zone = host.partition("%")
        # If it looks like an IP, we check with _ip_compressed_version
        # and fall-through if its not an IP address. This is a performance
        # optimization to avoid parsing IP addresses as much as possible
        # because it is orders of magnitude slower than almost any other
        # operation this library does.
        # Might be an IP address, check it
        #
        # IP Addresses can look like:
        # https://datatracker.ietf.org/doc/html/rfc3986#section-3.2.2
        # - 127.0.0.1 (last character is a digit)
        # - 2001:db8::ff00:42:8329 (contains a colon)
        # - 2001:db8::ff00:42:8329%eth0 (contains a colon)
        # - [2001:db8::ff00:42:8329] (contains a colon -- brackets should
        #                             have been removed before it gets here)
        # Rare IP Address formats are not supported per:
        # https://datatracker.ietf.org/doc/html/rfc3986#section-7.4
        #
        # IP parsing is slow, so its wrapped in an LRU
        try:
            ip = ip_address(raw_ip)
        except ValueError:
            pass
        else:
            # These checks should not happen in the
            # LRU to keep the cache size small
            host = ip.compressed
            if ip.version == 6:
                return f"[{host}%{zone}]" if sep else f"[{host}]"
            return f"{host}%{zone}" if sep else host

    # IDNA encoding is slow, skip it for ASCII-only strings
    if host.isascii():
        # Check for invalid characters explicitly; _idna_encode() does this
        # for non-ascii host names.
        host = host.lower()
        if validate_host and (invalid := NOT_REG_NAME.search(host)):
            value, pos, extra = invalid.group(), invalid.start(), ""
            if value == "@" or (value == ":" and "@" in host[pos:]):
                # this looks like an authority string
                extra = (
                    ", if the value includes a username or password, "
                    "use 'authority' instead of 'host'"
                )
            raise ValueError(
                f"Host {host!r} cannot contain {value!r} (at position {pos}){extra}"
            ) from None
        return host

    return _idna_encode(host)


@rewrite_module
def cache_clear() -> None:
    """Clear all LRU caches."""
    _idna_encode.cache_clear()
    _idna_decode.cache_clear()
    _encode_host.cache_clear()


@rewrite_module
def cache_info() -> CacheInfo:
    """Report cache statistics."""
    return {
        "idna_encode": _idna_encode.cache_info(),
        "idna_decode": _idna_decode.cache_info(),
        "ip_address": _encode_host.cache_info(),
        "host_validate": _encode_host.cache_info(),
        "encode_host": _encode_host.cache_info(),
    }


@rewrite_module
def cache_configure(
    *,
    idna_encode_size: Union[int, None] = _DEFAULT_IDNA_SIZE,
    idna_decode_size: Union[int, None] = _DEFAULT_IDNA_SIZE,
    ip_address_size: Union[int, None, UndefinedType] = UNDEFINED,
    host_validate_size: Union[int, None, UndefinedType] = UNDEFINED,
    encode_host_size: Union[int, None, UndefinedType] = UNDEFINED,
) -> None:
    """Configure LRU cache sizes."""
    global _idna_decode, _idna_encode, _encode_host
    # ip_address_size, host_validate_size are no longer
    # used, but are kept for backwards compatibility.
    if ip_address_size is not UNDEFINED or host_validate_size is not UNDEFINED:
        warnings.warn(
            "cache_configure() no longer accepts the "
            "ip_address_size or host_validate_size arguments, "
            "they are used to set the encode_host_size instead "
            "and will be removed in the future",
            DeprecationWarning,
            stacklevel=2,
        )

    if encode_host_size is not None:
        for size in (ip_address_size, host_validate_size):
            if size is None:
                encode_host_size = None
            elif encode_host_size is UNDEFINED:
                if size is not UNDEFINED:
                    encode_host_size = size
            elif size is not UNDEFINED:
                if TYPE_CHECKING:
                    assert isinstance(size, int)
                    assert isinstance(encode_host_size, int)
                encode_host_size = max(size, encode_host_size)
        if encode_host_size is UNDEFINED:
            encode_host_size = _DEFAULT_ENCODE_SIZE

    _encode_host = lru_cache(encode_host_size)(_encode_host.__wrapped__)
    _idna_decode = lru_cache(idna_decode_size)(_idna_decode.__wrapped__)
    _idna_encode = lru_cache(idna_encode_size)(_idna_encode.__wrapped__)

# === NexusCore/openenv\Lib\site-packages\cffi\recompiler.py ===
import os, sys, io
from . import ffiplatform, model
from .error import VerificationError
from .cffi_opcode import *

VERSION_BASE = 0x2601
VERSION_EMBEDDED = 0x2701
VERSION_CHAR16CHAR32 = 0x2801

USE_LIMITED_API = (sys.platform != 'win32' or sys.version_info < (3, 0) or
                   sys.version_info >= (3, 5))


class GlobalExpr:
    def __init__(self, name, address, type_op, size=0, check_value=0):
        self.name = name
        self.address = address
        self.type_op = type_op
        self.size = size
        self.check_value = check_value

    def as_c_expr(self):
        return '  { "%s", (void *)%s, %s, (void *)%s },' % (
            self.name, self.address, self.type_op.as_c_expr(), self.size)

    def as_python_expr(self):
        return "b'%s%s',%d" % (self.type_op.as_python_bytes(), self.name,
                               self.check_value)

class FieldExpr:
    def __init__(self, name, field_offset, field_size, fbitsize, field_type_op):
        self.name = name
        self.field_offset = field_offset
        self.field_size = field_size
        self.fbitsize = fbitsize
        self.field_type_op = field_type_op

    def as_c_expr(self):
        spaces = " " * len(self.name)
        return ('  { "%s", %s,\n' % (self.name, self.field_offset) +
                '     %s   %s,\n' % (spaces, self.field_size) +
                '     %s   %s },' % (spaces, self.field_type_op.as_c_expr()))

    def as_python_expr(self):
        raise NotImplementedError

    def as_field_python_expr(self):
        if self.field_type_op.op == OP_NOOP:
            size_expr = ''
        elif self.field_type_op.op == OP_BITFIELD:
            size_expr = format_four_bytes(self.fbitsize)
        else:
            raise NotImplementedError
        return "b'%s%s%s'" % (self.field_type_op.as_python_bytes(),
                              size_expr,
                              self.name)

class StructUnionExpr:
    def __init__(self, name, type_index, flags, size, alignment, comment,
                 first_field_index, c_fields):
        self.name = name
        self.type_index = type_index
        self.flags = flags
        self.size = size
        self.alignment = alignment
        self.comment = comment
        self.first_field_index = first_field_index
        self.c_fields = c_fields

    def as_c_expr(self):
        return ('  { "%s", %d, %s,' % (self.name, self.type_index, self.flags)
                + '\n    %s, %s, ' % (self.size, self.alignment)
                + '%d, %d ' % (self.first_field_index, len(self.c_fields))
                + ('/* %s */ ' % self.comment if self.comment else '')
                + '},')

    def as_python_expr(self):
        flags = eval(self.flags, G_FLAGS)
        fields_expr = [c_field.as_field_python_expr()
                       for c_field in self.c_fields]
        return "(b'%s%s%s',%s)" % (
            format_four_bytes(self.type_index),
            format_four_bytes(flags),
            self.name,
            ','.join(fields_expr))

class EnumExpr:
    def __init__(self, name, type_index, size, signed, allenums):
        self.name = name
        self.type_index = type_index
        self.size = size
        self.signed = signed
        self.allenums = allenums

    def as_c_expr(self):
        return ('  { "%s", %d, _cffi_prim_int(%s, %s),\n'
                '    "%s" },' % (self.name, self.type_index,
                                 self.size, self.signed, self.allenums))

    def as_python_expr(self):
        prim_index = {
            (1, 0): PRIM_UINT8,  (1, 1):  PRIM_INT8,
            (2, 0): PRIM_UINT16, (2, 1):  PRIM_INT16,
            (4, 0): PRIM_UINT32, (4, 1):  PRIM_INT32,
            (8, 0): PRIM_UINT64, (8, 1):  PRIM_INT64,
            }[self.size, self.signed]
        return "b'%s%s%s\\x00%s'" % (format_four_bytes(self.type_index),
                                     format_four_bytes(prim_index),
                                     self.name, self.allenums)

class TypenameExpr:
    def __init__(self, name, type_index):
        self.name = name
        self.type_index = type_index

    def as_c_expr(self):
        return '  { "%s", %d },' % (self.name, self.type_index)

    def as_python_expr(self):
        return "b'%s%s'" % (format_four_bytes(self.type_index), self.name)


# ____________________________________________________________


class Recompiler:
    _num_externpy = 0

    def __init__(self, ffi, module_name, target_is_python=False):
        self.ffi = ffi
        self.module_name = module_name
        self.target_is_python = target_is_python
        self._version = VERSION_BASE

    def needs_version(self, ver):
        self._version = max(self._version, ver)

    def collect_type_table(self):
        self._typesdict = {}
        self._generate("collecttype")
        #
        all_decls = sorted(self._typesdict, key=str)
        #
        # prepare all FUNCTION bytecode sequences first
        self.cffi_types = []
        for tp in all_decls:
            if tp.is_raw_function:
                assert self._typesdict[tp] is None
                self._typesdict[tp] = len(self.cffi_types)
                self.cffi_types.append(tp)     # placeholder
                for tp1 in tp.args:
                    assert isinstance(tp1, (model.VoidType,
                                            model.BasePrimitiveType,
                                            model.PointerType,
                                            model.StructOrUnionOrEnum,
                                            model.FunctionPtrType))
                    if self._typesdict[tp1] is None:
                        self._typesdict[tp1] = len(self.cffi_types)
                    self.cffi_types.append(tp1)   # placeholder
                self.cffi_types.append('END')     # placeholder
        #
        # prepare all OTHER bytecode sequences
        for tp in all_decls:
            if not tp.is_raw_function and self._typesdict[tp] is None:
                self._typesdict[tp] = len(self.cffi_types)
                self.cffi_types.append(tp)        # placeholder
                if tp.is_array_type and tp.length is not None:
                    self.cffi_types.append('LEN') # placeholder
        assert None not in self._typesdict.values()
        #
        # collect all structs and unions and enums
        self._struct_unions = {}
        self._enums = {}
        for tp in all_decls:
            if isinstance(tp, model.StructOrUnion):
                self._struct_unions[tp] = None
            elif isinstance(tp, model.EnumType):
                self._enums[tp] = None
        for i, tp in enumerate(sorted(self._struct_unions,
                                      key=lambda tp: tp.name)):
            self._struct_unions[tp] = i
        for i, tp in enumerate(sorted(self._enums,
                                      key=lambda tp: tp.name)):
            self._enums[tp] = i
        #
        # emit all bytecode sequences now
        for tp in all_decls:
            method = getattr(self, '_emit_bytecode_' + tp.__class__.__name__)
            method(tp, self._typesdict[tp])
        #
        # consistency check
        for op in self.cffi_types:
            assert isinstance(op, CffiOp)
        self.cffi_types = tuple(self.cffi_types)    # don't change any more

    def _enum_fields(self, tp):
        # When producing C, expand all anonymous struct/union fields.
        # That's necessary to have C code checking the offsets of the
        # individual fields contained in them.  When producing Python,
        # don't do it and instead write it like it is, with the
        # corresponding fields having an empty name.  Empty names are
        # recognized at runtime when we import the generated Python
        # file.
        expand_anonymous_struct_union = not self.target_is_python
        return tp.enumfields(expand_anonymous_struct_union)

    def _do_collect_type(self, tp):
        if not isinstance(tp, model.BaseTypeByIdentity):
            if isinstance(tp, tuple):
                for x in tp:
                    self._do_collect_type(x)
            return
        if tp not in self._typesdict:
            self._typesdict[tp] = None
            if isinstance(tp, model.FunctionPtrType):
                self._do_collect_type(tp.as_raw_function())
            elif isinstance(tp, model.StructOrUnion):
                if tp.fldtypes is not None and (
                        tp not in self.ffi._parser._included_declarations):
                    for name1, tp1, _, _ in self._enum_fields(tp):
                        self._do_collect_type(self._field_type(tp, name1, tp1))
            else:
                for _, x in tp._get_items():
                    self._do_collect_type(x)

    def _generate(self, step_name):
        lst = self.ffi._parser._declarations.items()
        for name, (tp, quals) in sorted(lst):
            kind, realname = name.split(' ', 1)
            try:
                method = getattr(self, '_generate_cpy_%s_%s' % (kind,
                                                                step_name))
            except AttributeError:
                raise VerificationError(
                    "not implemented in recompile(): %r" % name)
            try:
                self._current_quals = quals
                method(tp, realname)
            except Exception as e:
                model.attach_exception_info(e, name)
                raise

    # ----------

    ALL_STEPS = ["global", "field", "struct_union", "enum", "typename"]

    def collect_step_tables(self):
        # collect the declarations for '_cffi_globals', '_cffi_typenames', etc.
        self._lsts = {}
        for step_name in self.ALL_STEPS:
            self._lsts[step_name] = []
        self._seen_struct_unions = set()
        self._generate("ctx")
        self._add_missing_struct_unions()
        #
        for step_name in self.ALL_STEPS:
            lst = self._lsts[step_name]
            if step_name != "field":
                lst.sort(key=lambda entry: entry.name)
            self._lsts[step_name] = tuple(lst)    # don't change any more
        #
        # check for a possible internal inconsistency: _cffi_struct_unions
        # should have been generated with exactly self._struct_unions
        lst = self._lsts["struct_union"]
        for tp, i in self._struct_unions.items():
            assert i < len(lst)
            assert lst[i].name == tp.name
        assert len(lst) == len(self._struct_unions)
        # same with enums
        lst = self._lsts["enum"]
        for tp, i in self._enums.items():
            assert i < len(lst)
            assert lst[i].name == tp.name
        assert len(lst) == len(self._enums)

    # ----------

    def _prnt(self, what=''):
        self._f.write(what + '\n')

    def write_source_to_f(self, f, preamble):
        if self.target_is_python:
            assert preamble is None
            self.write_py_source_to_f(f)
        else:
            assert preamble is not None
            self.write_c_source_to_f(f, preamble)

    def _rel_readlines(self, filename):
        g = open(os.path.join(os.path.dirname(__file__), filename), 'r')
        lines = g.readlines()
        g.close()
        return lines

    def write_c_source_to_f(self, f, preamble):
        self._f = f
        prnt = self._prnt
        if self.ffi._embedding is not None:
            prnt('#define _CFFI_USE_EMBEDDING')
        if not USE_LIMITED_API:
            prnt('#define _CFFI_NO_LIMITED_API')
        #
        # first the '#include' (actually done by inlining the file's content)
        lines = self._rel_readlines('_cffi_include.h')
        i = lines.index('#include "parse_c_type.h"\n')
        lines[i:i+1] = self._rel_readlines('parse_c_type.h')
        prnt(''.join(lines))
        #
        # if we have ffi._embedding != None, we give it here as a macro
        # and include an extra file
        base_module_name = self.module_name.split('.')[-1]
        if self.ffi._embedding is not None:
            prnt('#define _CFFI_MODULE_NAME  "%s"' % (self.module_name,))
            prnt('static const char _CFFI_PYTHON_STARTUP_CODE[] = {')
            self._print_string_literal_in_array(self.ffi._embedding)
            prnt('0 };')
            prnt('#ifdef PYPY_VERSION')
            prnt('# define _CFFI_PYTHON_STARTUP_FUNC  _cffi_pypyinit_%s' % (
                base_module_name,))
            prnt('#elif PY_MAJOR_VERSION >= 3')
            prnt('# define _CFFI_PYTHON_STARTUP_FUNC  PyInit_%s' % (
                base_module_name,))
            prnt('#else')
            prnt('# define _CFFI_PYTHON_STARTUP_FUNC  init%s' % (
                base_module_name,))
            prnt('#endif')
            lines = self._rel_readlines('_embedding.h')
            i = lines.index('#include "_cffi_errors.h"\n')
            lines[i:i+1] = self._rel_readlines('_cffi_errors.h')
            prnt(''.join(lines))
            self.needs_version(VERSION_EMBEDDED)
        #
        # then paste the C source given by the user, verbatim.
        prnt('/************************************************************/')
        prnt()
        prnt(preamble)
        prnt()
        prnt('/************************************************************/')
        prnt()
        #
        # the declaration of '_cffi_types'
        prnt('static void *_cffi_types[] = {')
        typeindex2type = dict([(i, tp) for (tp, i) in self._typesdict.items()])
        for i, op in enumerate(self.cffi_types):
            comment = ''
            if i in typeindex2type:
                comment = ' // ' + typeindex2type[i]._get_c_name()
            prnt('/* %2d */ %s,%s' % (i, op.as_c_expr(), comment))
        if not self.cffi_types:
            prnt('  0')
        prnt('};')
        prnt()
        #
        # call generate_cpy_xxx_decl(), for every xxx found from
        # ffi._parser._declarations.  This generates all the functions.
        self._seen_constants = set()
        self._generate("decl")
        #
        # the declaration of '_cffi_globals' and '_cffi_typenames'
        nums = {}
        for step_name in self.ALL_STEPS:
            lst = self._lsts[step_name]
            nums[step_name] = len(lst)
            if nums[step_name] > 0:
                prnt('static const struct _cffi_%s_s _cffi_%ss[] = {' % (
                    step_name, step_name))
                for entry in lst:
                    prnt(entry.as_c_expr())
                prnt('};')
                prnt()
        #
        # the declaration of '_cffi_includes'
        if self.ffi._included_ffis:
            prnt('static const char * const _cffi_includes[] = {')
            for ffi_to_include in self.ffi._included_ffis:
                try:
                    included_module_name, included_source = (
                        ffi_to_include._assigned_source[:2])
                except AttributeError:
                    raise VerificationError(
                        "ffi object %r includes %r, but the latter has not "
                        "been prepared with set_source()" % (
                            self.ffi, ffi_to_include,))
                if included_source is None:
                    raise VerificationError(
                        "not implemented yet: ffi.include() of a Python-based "
                        "ffi inside a C-based ffi")
                prnt('  "%s",' % (included_module_name,))
            prnt('  NULL')
            prnt('};')
            prnt()
        #
        # the declaration of '_cffi_type_context'
        prnt('static const struct _cffi_type_context_s _cffi_type_context = {')
        prnt('  _cffi_types,')
        for step_name in self.ALL_STEPS:
            if nums[step_name] > 0:
                prnt('  _cffi_%ss,' % step_name)
            else:
                prnt('  NULL,  /* no %ss */' % step_name)
        for step_name in self.ALL_STEPS:
            if step_name != "field":
                prnt('  %d,  /* num_%ss */' % (nums[step_name], step_name))
        if self.ffi._included_ffis:
            prnt('  _cffi_includes,')
        else:
            prnt('  NULL,  /* no includes */')
        prnt('  %d,  /* num_types */' % (len(self.cffi_types),))
        flags = 0
        if self._num_externpy > 0 or self.ffi._embedding is not None:
            flags |= 1     # set to mean that we use extern "Python"
        prnt('  %d,  /* flags */' % flags)
        prnt('};')
        prnt()
        #
        # the init function
        prnt('#ifdef __GNUC__')
        prnt('#  pragma GCC visibility push(default)  /* for -fvisibility= */')
        prnt('#endif')
        prnt()
        prnt('#ifdef PYPY_VERSION')
        prnt('PyMODINIT_FUNC')
        prnt('_cffi_pypyinit_%s(const void *p[])' % (base_module_name,))
        prnt('{')
        if flags & 1:
            prnt('    if (((intptr_t)p[0]) >= 0x0A03) {')
            prnt('        _cffi_call_python_org = '
                 '(void(*)(struct _cffi_externpy_s *, char *))p[1];')
            prnt('    }')
        prnt('    p[0] = (const void *)0x%x;' % self._version)
        prnt('    p[1] = &_cffi_type_context;')
        prnt('#if PY_MAJOR_VERSION >= 3')
        prnt('    return NULL;')
        prnt('#endif')
        prnt('}')
        # on Windows, distutils insists on putting init_cffi_xyz in
        # 'export_symbols', so instead of fighting it, just give up and
        # give it one
        prnt('#  ifdef _MSC_VER')
        prnt('     PyMODINIT_FUNC')
        prnt('#  if PY_MAJOR_VERSION >= 3')
        prnt('     PyInit_%s(void) { return NULL; }' % (base_module_name,))
        prnt('#  else')
        prnt('     init%s(void) { }' % (base_module_name,))
        prnt('#  endif')
        prnt('#  endif')
        prnt('#elif PY_MAJOR_VERSION >= 3')
        prnt('PyMODINIT_FUNC')
        prnt('PyInit_%s(void)' % (base_module_name,))
        prnt('{')
        prnt('  return _cffi_init("%s", 0x%x, &_cffi_type_context);' % (
            self.module_name, self._version))
        prnt('}')
        prnt('#else')
        prnt('PyMODINIT_FUNC')
        prnt('init%s(void)' % (base_module_name,))
        prnt('{')
        prnt('  _cffi_init("%s", 0x%x, &_cffi_type_context);' % (
            self.module_name, self._version))
        prnt('}')
        prnt('#endif')
        prnt()
        prnt('#ifdef __GNUC__')
        prnt('#  pragma GCC visibility pop')
        prnt('#endif')
        self._version = None

    def _to_py(self, x):
        if isinstance(x, str):
            return "b'%s'" % (x,)
        if isinstance(x, (list, tuple)):
            rep = [self._to_py(item) for item in x]
            if len(rep) == 1:
                rep.append('')
            return "(%s)" % (','.join(rep),)
        return x.as_python_expr()  # Py2: unicode unexpected; Py3: bytes unexp.

    def write_py_source_to_f(self, f):
        self._f = f
        prnt = self._prnt
        #
        # header
        prnt("# auto-generated file")
        prnt("import _cffi_backend")
        #
        # the 'import' of the included ffis
        num_includes = len(self.ffi._included_ffis or ())
        for i in range(num_includes):
            ffi_to_include = self.ffi._included_ffis[i]
            try:
                included_module_name, included_source = (
                    ffi_to_include._assigned_source[:2])
            except AttributeError:
                raise VerificationError(
                    "ffi object %r includes %r, but the latter has not "
                    "been prepared with set_source()" % (
                        self.ffi, ffi_to_include,))
            if included_source is not None:
                raise VerificationError(
                    "not implemented yet: ffi.include() of a C-based "
                    "ffi inside a Python-based ffi")
            prnt('from %s import ffi as _ffi%d' % (included_module_name, i))
        prnt()
        prnt("ffi = _cffi_backend.FFI('%s'," % (self.module_name,))
        prnt("    _version = 0x%x," % (self._version,))
        self._version = None
        #
        # the '_types' keyword argument
        self.cffi_types = tuple(self.cffi_types)    # don't change any more
        types_lst = [op.as_python_bytes() for op in self.cffi_types]
        prnt('    _types = %s,' % (self._to_py(''.join(types_lst)),))
        typeindex2type = dict([(i, tp) for (tp, i) in self._typesdict.items()])
        #
        # the keyword arguments from ALL_STEPS
        for step_name in self.ALL_STEPS:
            lst = self._lsts[step_name]
            if len(lst) > 0 and step_name != "field":
                prnt('    _%ss = %s,' % (step_name, self._to_py(lst)))
        #
        # the '_includes' keyword argument
        if num_includes > 0:
            prnt('    _includes = (%s,),' % (
                ', '.join(['_ffi%d' % i for i in range(num_includes)]),))
        #
        # the footer
        prnt(')')

    # ----------

    def _gettypenum(self, type):
        # a KeyError here is a bug.  please report it! :-)
        return self._typesdict[type]

    def _convert_funcarg_to_c(self, tp, fromvar, tovar, errcode):
        extraarg = ''
        if isinstance(tp, model.BasePrimitiveType) and not tp.is_complex_type():
            if tp.is_integer_type() and tp.name != '_Bool':
                converter = '_cffi_to_c_int'
                extraarg = ', %s' % tp.name
            elif isinstance(tp, model.UnknownFloatType):
                # don't check with is_float_type(): it may be a 'long
                # double' here, and _cffi_to_c_double would loose precision
                converter = '(%s)_cffi_to_c_double' % (tp.get_c_name(''),)
            else:
                cname = tp.get_c_name('')
                converter = '(%s)_cffi_to_c_%s' % (cname,
                                                   tp.name.replace(' ', '_'))
                if cname in ('char16_t', 'char32_t'):
                    self.needs_version(VERSION_CHAR16CHAR32)
            errvalue = '-1'
        #
        elif isinstance(tp, model.PointerType):
            self._convert_funcarg_to_c_ptr_or_array(tp, fromvar,
                                                    tovar, errcode)
            return
        #
        elif (isinstance(tp, model.StructOrUnionOrEnum) or
              isinstance(tp, model.BasePrimitiveType)):
            # a struct (not a struct pointer) as a function argument;
            # or, a complex (the same code works)
            self._prnt('  if (_cffi_to_c((char *)&%s, _cffi_type(%d), %s) < 0)'
                      % (tovar, self._gettypenum(tp), fromvar))
            self._prnt('    %s;' % errcode)
            return
        #
        elif isinstance(tp, model.FunctionPtrType):
            converter = '(%s)_cffi_to_c_pointer' % tp.get_c_name('')
            extraarg = ', _cffi_type(%d)' % self._gettypenum(tp)
            errvalue = 'NULL'
        #
        else:
            raise NotImplementedError(tp)
        #
        self._prnt('  %s = %s(%s%s);' % (tovar, converter, fromvar, extraarg))
        self._prnt('  if (%s == (%s)%s && PyErr_Occurred())' % (
            tovar, tp.get_c_name(''), errvalue))
        self._prnt('    %s;' % errcode)

    def _extra_local_variables(self, tp, localvars, freelines):
        if isinstance(tp, model.PointerType):
            localvars.add('Py_ssize_t datasize')
            localvars.add('struct _cffi_freeme_s *large_args_free = NULL')
            freelines.add('if (large_args_free != NULL)'
                          ' _cffi_free_array_arguments(large_args_free);')

    def _convert_funcarg_to_c_ptr_or_array(self, tp, fromvar, tovar, errcode):
        self._prnt('  datasize = _cffi_prepare_pointer_call_argument(')
        self._prnt('      _cffi_type(%d), %s, (char **)&%s);' % (
            self._gettypenum(tp), fromvar, tovar))
        self._prnt('  if (datasize != 0) {')
        self._prnt('    %s = ((size_t)datasize) <= 640 ? '
                   '(%s)alloca((size_t)datasize) : NULL;' % (
            tovar, tp.get_c_name('')))
        self._prnt('    if (_cffi_convert_array_argument(_cffi_type(%d), %s, '
                   '(char **)&%s,' % (self._gettypenum(tp), fromvar, tovar))
        self._prnt('            datasize, &large_args_free) < 0)')
        self._prnt('      %s;' % errcode)
        self._prnt('  }')

    def _convert_expr_from_c(self, tp, var, context):
        if isinstance(tp, model.BasePrimitiveType):
            if tp.is_integer_type() and tp.name != '_Bool':
                return '_cffi_from_c_int(%s, %s)' % (var, tp.name)
            elif isinstance(tp, model.UnknownFloatType):
                return '_cffi_from_c_double(%s)' % (var,)
            elif tp.name != 'long double' and not tp.is_complex_type():
                cname = tp.name.replace(' ', '_')
                if cname in ('char16_t', 'char32_t'):
                    self.needs_version(VERSION_CHAR16CHAR32)
                return '_cffi_from_c_%s(%s)' % (cname, var)
            else:
                return '_cffi_from_c_deref((char *)&%s, _cffi_type(%d))' % (
                    var, self._gettypenum(tp))
        elif isinstance(tp, (model.PointerType, model.FunctionPtrType)):
            return '_cffi_from_c_pointer((char *)%s, _cffi_type(%d))' % (
                var, self._gettypenum(tp))
        elif isinstance(tp, model.ArrayType):
            return '_cffi_from_c_pointer((char *)%s, _cffi_type(%d))' % (
                var, self._gettypenum(model.PointerType(tp.item)))
        elif isinstance(tp, model.StructOrUnion):
            if tp.fldnames is None:
                raise TypeError("'%s' is used as %s, but is opaque" % (
                    tp._get_c_name(), context))
            return '_cffi_from_c_struct((char *)&%s, _cffi_type(%d))' % (
                var, self._gettypenum(tp))
        elif isinstance(tp, model.EnumType):
            return '_cffi_from_c_deref((char *)&%s, _cffi_type(%d))' % (
                var, self._gettypenum(tp))
        else:
            raise NotImplementedError(tp)

    # ----------
    # typedefs

    def _typedef_type(self, tp, name):
        return self._global_type(tp, "(*(%s *)0)" % (name,))

    def _generate_cpy_typedef_collecttype(self, tp, name):
        self._do_collect_type(self._typedef_type(tp, name))

    def _generate_cpy_typedef_decl(self, tp, name):
        pass

    def _typedef_ctx(self, tp, name):
        type_index = self._typesdict[tp]
        self._lsts["typename"].append(TypenameExpr(name, type_index))

    def _generate_cpy_typedef_ctx(self, tp, name):
        tp = self._typedef_type(tp, name)
        self._typedef_ctx(tp, name)
        if getattr(tp, "origin", None) == "unknown_type":
            self._struct_ctx(tp, tp.name, approxname=None)
        elif isinstance(tp, model.NamedPointerType):
            self._struct_ctx(tp.totype, tp.totype.name, approxname=tp.name,
                             named_ptr=tp)

    # ----------
    # function declarations

    def _generate_cpy_function_collecttype(self, tp, name):
        self._do_collect_type(tp.as_raw_function())
        if tp.ellipsis and not self.target_is_python:
            self._do_collect_type(tp)

    def _generate_cpy_function_decl(self, tp, name):
        assert not self.target_is_python
        assert isinstance(tp, model.FunctionPtrType)
        if tp.ellipsis:
            # cannot support vararg functions better than this: check for its
            # exact type (including the fixed arguments), and build it as a
            # constant function pointer (no CPython wrapper)
            self._generate_cpy_constant_decl(tp, name)
            return
        prnt = self._prnt
        numargs = len(tp.args)
        if numargs == 0:
            argname = 'noarg'
        elif numargs == 1:
            argname = 'arg0'
        else:
            argname = 'args'
        #
        # ------------------------------
        # the 'd' version of the function, only for addressof(lib, 'func')
        arguments = []
        call_arguments = []
        context = 'argument of %s' % name
        for i, type in enumerate(tp.args):
            arguments.append(type.get_c_name(' x%d' % i, context))
            call_arguments.append('x%d' % i)
        repr_arguments = ', '.join(arguments)
        repr_arguments = repr_arguments or 'void'
        if tp.abi:
            abi = tp.abi + ' '
        else:
            abi = ''
        name_and_arguments = '%s_cffi_d_%s(%s)' % (abi, name, repr_arguments)
        prnt('static %s' % (tp.result.get_c_name(name_and_arguments),))
        prnt('{')
        call_arguments = ', '.join(call_arguments)
        result_code = 'return '
        if isinstance(tp.result, model.VoidType):
            result_code = ''
        prnt('  %s%s(%s);' % (result_code, name, call_arguments))
        prnt('}')
        #
        prnt('#ifndef PYPY_VERSION')        # ------------------------------
        #
        prnt('static PyObject *')
        prnt('_cffi_f_%s(PyObject *self, PyObject *%s)' % (name, argname))
        prnt('{')
        #
        context = 'argument of %s' % name
        for i, type in enumerate(tp.args):
            arg = type.get_c_name(' x%d' % i, context)
            prnt('  %s;' % arg)
        #
        localvars = set()
        freelines = set()
        for type in tp.args:
            self._extra_local_variables(type, localvars, freelines)
        for decl in sorted(localvars):
            prnt('  %s;' % (decl,))
        #
        if not isinstance(tp.result, model.VoidType):
            result_code = 'result = '
            context = 'result of %s' % name
            result_decl = '  %s;' % tp.result.get_c_name(' result', context)
            prnt(result_decl)
            prnt('  PyObject *pyresult;')
        else:
            result_decl = None
            result_code = ''
        #
        if len(tp.args) > 1:
            rng = range(len(tp.args))
            for i in rng:
                prnt('  PyObject *arg%d;' % i)
            prnt()
            prnt('  if (!PyArg_UnpackTuple(args, "%s", %d, %d, %s))' % (
                name, len(rng), len(rng),
                ', '.join(['&arg%d' % i for i in rng])))
            prnt('    return NULL;')
        prnt()
        #
        for i, type in enumerate(tp.args):
            self._convert_funcarg_to_c(type, 'arg%d' % i, 'x%d' % i,
                                       'return NULL')
            prnt()
        #
        prnt('  Py_BEGIN_ALLOW_THREADS')
        prnt('  _cffi_restore_errno();')
        call_arguments = ['x%d' % i for i in range(len(tp.args))]
        call_arguments = ', '.join(call_arguments)
        prnt('  { %s%s(%s); }' % (result_code, name, call_arguments))
        prnt('  _cffi_save_errno();')
        prnt('  Py_END_ALLOW_THREADS')
        prnt()
        #
        prnt('  (void)self; /* unused */')
        if numargs == 0:
            prnt('  (void)noarg; /* unused */')
        if result_code:
            prnt('  pyresult = %s;' %
                 self._convert_expr_from_c(tp.result, 'result', 'result type'))
            for freeline in freelines:
                prnt('  ' + freeline)
            prnt('  return pyresult;')
        else:
            for freeline in freelines:
                prnt('  ' + freeline)
            prnt('  Py_INCREF(Py_None);')
            prnt('  return Py_None;')
        prnt('}')
        #
        prnt('#else')        # ------------------------------
        #
        # the PyPy version: need to replace struct/union arguments with
        # pointers, and if the result is a struct/union, insert a first
        # arg that is a pointer to the result.  We also do that for
        # complex args and return type.
        def need_indirection(type):
            return (isinstance(type, model.StructOrUnion) or
                    (isinstance(type, model.PrimitiveType) and
                     type.is_complex_type()))
        difference = False
        arguments = []
        call_arguments = []
        context = 'argument of %s' % name
        for i, type in enumerate(tp.args):
            indirection = ''
            if need_indirection(type):
                indirection = '*'
                difference = True
            arg = type.get_c_name(' %sx%d' % (indirection, i), context)
            arguments.append(arg)
            call_arguments.append('%sx%d' % (indirection, i))
        tp_result = tp.result
        if need_indirection(tp_result):
            context = 'result of %s' % name
            arg = tp_result.get_c_name(' *result', context)
            arguments.insert(0, arg)
            tp_result = model.void_type
            result_decl = None
            result_code = '*result = '
            difference = True
        if difference:
            repr_arguments = ', '.join(arguments)
            repr_arguments = repr_arguments or 'void'
            name_and_arguments = '%s_cffi_f_%s(%s)' % (abi, name,
                                                       repr_arguments)
            prnt('static %s' % (tp_result.get_c_name(name_and_arguments),))
            prnt('{')
            if result_decl:
                prnt(result_decl)
            call_arguments = ', '.join(call_arguments)
            prnt('  { %s%s(%s); }' % (result_code, name, call_arguments))
            if result_decl:
                prnt('  return result;')
            prnt('}')
        else:
            prnt('#  define _cffi_f_%s _cffi_d_%s' % (name, name))
        #
        prnt('#endif')        # ------------------------------
        prnt()

    def _generate_cpy_function_ctx(self, tp, name):
        if tp.ellipsis and not self.target_is_python:
            self._generate_cpy_constant_ctx(tp, name)
            return
        type_index = self._typesdict[tp.as_raw_function()]
        numargs = len(tp.args)
        if self.target_is_python:
            meth_kind = OP_DLOPEN_FUNC
        elif numargs == 0:
            meth_kind = OP_CPYTHON_BLTN_N   # 'METH_NOARGS'
        elif numargs == 1:
            meth_kind = OP_CPYTHON_BLTN_O   # 'METH_O'
        else:
            meth_kind = OP_CPYTHON_BLTN_V   # 'METH_VARARGS'
        self._lsts["global"].append(
            GlobalExpr(name, '_cffi_f_%s' % name,
                       CffiOp(meth_kind, type_index),
                       size='_cffi_d_%s' % name))

    # ----------
    # named structs or unions

    def _field_type(self, tp_struct, field_name, tp_field):
        if isinstance(tp_field, model.ArrayType):
            actual_length = tp_field.length
            if actual_length == '...':
                ptr_struct_name = tp_struct.get_c_name('*')
                actual_length = '_cffi_array_len(((%s)0)->%s)' % (
                    ptr_struct_name, field_name)
            tp_item = self._field_type(tp_struct, '%s[0]' % field_name,
                                       tp_field.item)
            tp_field = model.ArrayType(tp_item, actual_length)
        return tp_field

    def _struct_collecttype(self, tp):
        self._do_collect_type(tp)
        if self.target_is_python:
            # also requires nested anon struct/unions in ABI mode, recursively
            for fldtype in tp.anonymous_struct_fields():
                self._struct_collecttype(fldtype)

    def _struct_decl(self, tp, cname, approxname):
        if tp.fldtypes is None:
            return
        prnt = self._prnt
        checkfuncname = '_cffi_checkfld_%s' % (approxname,)
        prnt('_CFFI_UNUSED_FN')
        prnt('static void %s(%s *p)' % (checkfuncname, cname))
        prnt('{')
        prnt('  /* only to generate compile-time warnings or errors */')
        prnt('  (void)p;')
        for fname, ftype, fbitsize, fqual in self._enum_fields(tp):
            try:
                if ftype.is_integer_type() or fbitsize >= 0:
                    # accept all integers, but complain on float or double
                    if fname != '':
                        prnt("  (void)((p->%s) | 0);  /* check that '%s.%s' is "
                             "an integer */" % (fname, cname, fname))
                    continue
                # only accept exactly the type declared, except that '[]'
                # is interpreted as a '*' and so will match any array length.
                # (It would also match '*', but that's harder to detect...)
                while (isinstance(ftype, model.ArrayType)
                       and (ftype.length is None or ftype.length == '...')):
                    ftype = ftype.item
                    fname = fname + '[0]'
                prnt('  { %s = &p->%s; (void)tmp; }' % (
                    ftype.get_c_name('*tmp', 'field %r'%fname, quals=fqual),
                    fname))
            except VerificationError as e:
                prnt('  /* %s */' % str(e))   # cannot verify it, ignore
        prnt('}')
        prnt('struct _cffi_align_%s { char x; %s y; };' % (approxname, cname))
        prnt()

    def _struct_ctx(self, tp, cname, approxname, named_ptr=None):
        type_index = self._typesdict[tp]
        reason_for_not_expanding = None
        flags = []
        if isinstance(tp, model.UnionType):
            flags.append("_CFFI_F_UNION")
        if tp.fldtypes is None:
            flags.append("_CFFI_F_OPAQUE")
            reason_for_not_expanding = "opaque"
        if (tp not in self.ffi._parser._included_declarations and
                (named_ptr is None or
                 named_ptr not in self.ffi._parser._included_declarations)):
            if tp.fldtypes is None:
                pass    # opaque
            elif tp.partial or any(tp.anonymous_struct_fields()):
                pass    # field layout obtained silently from the C compiler
            else:
                flags.append("_CFFI_F_CHECK_FIELDS")
            if tp.packed:
                if tp.packed > 1:
                    raise NotImplementedError(
                        "%r is declared with 'pack=%r'; only 0 or 1 are "
                        "supported in API mode (try to use \"...;\", which "
                        "does not require a 'pack' declaration)" %
                        (tp, tp.packed))
                flags.append("_CFFI_F_PACKED")
        else:
            flags.append("_CFFI_F_EXTERNAL")
            reason_for_not_expanding = "external"
        flags = '|'.join(flags) or '0'
        c_fields = []
        if reason_for_not_expanding is None:
            enumfields = list(self._enum_fields(tp))
            for fldname, fldtype, fbitsize, fqual in enumfields:
                fldtype = self._field_type(tp, fldname, fldtype)
                self._check_not_opaque(fldtype,
                                       "field '%s.%s'" % (tp.name, fldname))
                # cname is None for _add_missing_struct_unions() only
                op = OP_NOOP
                if fbitsize >= 0:
                    op = OP_BITFIELD
                    size = '%d /* bits */' % fbitsize
                elif cname is None or (
                        isinstance(fldtype, model.ArrayType) and
                        fldtype.length is None):
                    size = '(size_t)-1'
                else:
                    size = 'sizeof(((%s)0)->%s)' % (
                        tp.get_c_name('*') if named_ptr is None
                                           else named_ptr.name,
                        fldname)
                if cname is None or fbitsize >= 0:
                    offset = '(size_t)-1'
                elif named_ptr is not None:
                    offset = '((char *)&((%s)4096)->%s) - (char *)4096' % (
                        named_ptr.name, fldname)
                else:
                    offset = 'offsetof(%s, %s)' % (tp.get_c_name(''), fldname)
                c_fields.append(
                    FieldExpr(fldname, offset, size, fbitsize,
                              CffiOp(op, self._typesdict[fldtype])))
            first_field_index = len(self._lsts["field"])
            self._lsts["field"].extend(c_fields)
            #
            if cname is None:  # unknown name, for _add_missing_struct_unions
                size = '(size_t)-2'
                align = -2
                comment = "unnamed"
            else:
                if named_ptr is not None:
                    size = 'sizeof(*(%s)0)' % (named_ptr.name,)
                    align = '-1 /* unknown alignment */'
                else:
                    size = 'sizeof(%s)' % (cname,)
                    align = 'offsetof(struct _cffi_align_%s, y)' % (approxname,)
                comment = None
        else:
            size = '(size_t)-1'
            align = -1
            first_field_index = -1
            comment = reason_for_not_expanding
        self._lsts["struct_union"].append(
            StructUnionExpr(tp.name, type_index, flags, size, align, comment,
                            first_field_index, c_fields))
        self._seen_struct_unions.add(tp)

    def _check_not_opaque(self, tp, location):
        while isinstance(tp, model.ArrayType):
            tp = tp.item
        if isinstance(tp, model.StructOrUnion) and tp.fldtypes is None:
            raise TypeError(
                "%s is of an opaque type (not declared in cdef())" % location)

    def _add_missing_struct_unions(self):
        # not very nice, but some struct declarations might be missing
        # because they don't have any known C name.  Check that they are
        # not partial (we can't complete or verify them!) and emit them
        # anonymously.
        lst = list(self._struct_unions.items())
        lst.sort(key=lambda tp_order: tp_order[1])
        for tp, order in lst:
            if tp not in self._seen_struct_unions:
                if tp.partial:
                    raise NotImplementedError("internal inconsistency: %r is "
                                              "partial but was not seen at "
                                              "this point" % (tp,))
                if tp.name.startswith('$') and tp.name[1:].isdigit():
                    approxname = tp.name[1:]
                elif tp.name == '_IO_FILE' and tp.forcename == 'FILE':
                    approxname = 'FILE'
                    self._typedef_ctx(tp, 'FILE')
                else:
                    raise NotImplementedError("internal inconsistency: %r" %
                                              (tp,))
                self._struct_ctx(tp, None, approxname)

    def _generate_cpy_struct_collecttype(self, tp, name):
        self._struct_collecttype(tp)
    _generate_cpy_union_collecttype = _generate_cpy_struct_collecttype

    def _struct_names(self, tp):
        cname = tp.get_c_name('')
        if ' ' in cname:
            return cname, cname.replace(' ', '_')
        else:
            return cname, '_' + cname

    def _generate_cpy_struct_decl(self, tp, name):
        self._struct_decl(tp, *self._struct_names(tp))
    _generate_cpy_union_decl = _generate_cpy_struct_decl

    def _generate_cpy_struct_ctx(self, tp, name):
        self._struct_ctx(tp, *self._struct_names(tp))
    _generate_cpy_union_ctx = _generate_cpy_struct_ctx

    # ----------
    # 'anonymous' declarations.  These are produced for anonymous structs
    # or unions; the 'name' is obtained by a typedef.

    def _generate_cpy_anonymous_collecttype(self, tp, name):
        if isinstance(tp, model.EnumType):
            self._generate_cpy_enum_collecttype(tp, name)
        else:
            self._struct_collecttype(tp)

    def _generate_cpy_anonymous_decl(self, tp, name):
        if isinstance(tp, model.EnumType):
            self._generate_cpy_enum_decl(tp)
        else:
            self._struct_decl(tp, name, 'typedef_' + name)

    def _generate_cpy_anonymous_ctx(self, tp, name):
        if isinstance(tp, model.EnumType):
            self._enum_ctx(tp, name)
        else:
            self._struct_ctx(tp, name, 'typedef_' + name)

    # ----------
    # constants, declared with "static const ..."

    def _generate_cpy_const(self, is_int, name, tp=None, category='const',
                            check_value=None):
        if (category, name) in self._seen_constants:
            raise VerificationError(
                "duplicate declaration of %s '%s'" % (category, name))
        self._seen_constants.add((category, name))
        #
        prnt = self._prnt
        funcname = '_cffi_%s_%s' % (category, name)
        if is_int:
            prnt('static int %s(unsigned long long *o)' % funcname)
            prnt('{')
            prnt('  int n = (%s) <= 0;' % (name,))
            prnt('  *o = (unsigned long long)((%s) | 0);'
                 '  /* check that %s is an integer */' % (name, name))
            if check_value is not None:
                if check_value > 0:
                    check_value = '%dU' % (check_value,)
                prnt('  if (!_cffi_check_int(*o, n, %s))' % (check_value,))
                prnt('    n |= 2;')
            prnt('  return n;')
            prnt('}')
        else:
            assert check_value is None
            prnt('static void %s(char *o)' % funcname)
            prnt('{')
            prnt('  *(%s)o = %s;' % (tp.get_c_name('*'), name))
            prnt('}')
        prnt()

    def _generate_cpy_constant_collecttype(self, tp, name):
        is_int = tp.is_integer_type()
        if not is_int or self.target_is_python:
            self._do_collect_type(tp)

    def _generate_cpy_constant_decl(self, tp, name):
        is_int = tp.is_integer_type()
        self._generate_cpy_const(is_int, name, tp)

    def _generate_cpy_constant_ctx(self, tp, name):
        if not self.target_is_python and tp.is_integer_type():
            type_op = CffiOp(OP_CONSTANT_INT, -1)
        else:
            if self.target_is_python:
                const_kind = OP_DLOPEN_CONST
            else:
                const_kind = OP_CONSTANT
            type_index = self._typesdict[tp]
            type_op = CffiOp(const_kind, type_index)
        self._lsts["global"].append(
            GlobalExpr(name, '_cffi_const_%s' % name, type_op))

    # ----------
    # enums

    def _generate_cpy_enum_collecttype(self, tp, name):
        self._do_collect_type(tp)

    def _generate_cpy_enum_decl(self, tp, name=None):
        for enumerator in tp.enumerators:
            self._generate_cpy_const(True, enumerator)

    def _enum_ctx(self, tp, cname):
        type_index = self._typesdict[tp]
        type_op = CffiOp(OP_ENUM, -1)
        if self.target_is_python:
            tp.check_not_partial()
        for enumerator, enumvalue in zip(tp.enumerators, tp.enumvalues):
            self._lsts["global"].append(
                GlobalExpr(enumerator, '_cffi_const_%s' % enumerator, type_op,
                           check_value=enumvalue))
        #
        if cname is not None and '$' not in cname and not self.target_is_python:
            size = "sizeof(%s)" % cname
            signed = "((%s)-1) <= 0" % cname
        else:
            basetp = tp.build_baseinttype(self.ffi, [])
            size = self.ffi.sizeof(basetp)
            signed = int(int(self.ffi.cast(basetp, -1)) < 0)
        allenums = ",".join(tp.enumerators)
        self._lsts["enum"].append(
            EnumExpr(tp.name, type_index, size, signed, allenums))

    def _generate_cpy_enum_ctx(self, tp, name):
        self._enum_ctx(tp, tp._get_c_name())

    # ----------
    # macros: for now only for integers

    def _generate_cpy_macro_collecttype(self, tp, name):
        pass

    def _generate_cpy_macro_decl(self, tp, name):
        if tp == '...':
            check_value = None
        else:
            check_value = tp     # an integer
        self._generate_cpy_const(True, name, check_value=check_value)

    def _generate_cpy_macro_ctx(self, tp, name):
        if tp == '...':
            if self.target_is_python:
                raise VerificationError(
                    "cannot use the syntax '...' in '#define %s ...' when "
                    "using the ABI mode" % (name,))
            check_value = None
        else:
            check_value = tp     # an integer
        type_op = CffiOp(OP_CONSTANT_INT, -1)
        self._lsts["global"].append(
            GlobalExpr(name, '_cffi_const_%s' % name, type_op,
                       check_value=check_value))

    # ----------
    # global variables

    def _global_type(self, tp, global_name):
        if isinstance(tp, model.ArrayType):
            actual_length = tp.length
            if actual_length == '...':
                actual_length = '_cffi_array_len(%s)' % (global_name,)
            tp_item = self._global_type(tp.item, '%s[0]' % global_name)
            tp = model.ArrayType(tp_item, actual_length)
        return tp

    def _generate_cpy_variable_collecttype(self, tp, name):
        self._do_collect_type(self._global_type(tp, name))

    def _generate_cpy_variable_decl(self, tp, name):
        prnt = self._prnt
        tp = self._global_type(tp, name)
        if isinstance(tp, model.ArrayType) and tp.length is None:
            tp = tp.item
            ampersand = ''
        else:
            ampersand = '&'
        # This code assumes that casts from "tp *" to "void *" is a
        # no-op, i.e. a function that returns a "tp *" can be called
        # as if it returned a "void *".  This should be generally true
        # on any modern machine.  The only exception to that rule (on
        # uncommon architectures, and as far as I can tell) might be
        # if 'tp' were a function type, but that is not possible here.
        # (If 'tp' is a function _pointer_ type, then casts from "fn_t
        # **" to "void *" are again no-ops, as far as I can tell.)
        decl = '*_cffi_var_%s(void)' % (name,)
        prnt('static ' + tp.get_c_name(decl, quals=self._current_quals))
        prnt('{')
        prnt('  return %s(%s);' % (ampersand, name))
        prnt('}')
        prnt()

    def _generate_cpy_variable_ctx(self, tp, name):
        tp = self._global_type(tp, name)
        type_index = self._typesdict[tp]
        if self.target_is_python:
            op = OP_GLOBAL_VAR
        else:
            op = OP_GLOBAL_VAR_F
        self._lsts["global"].append(
            GlobalExpr(name, '_cffi_var_%s' % name, CffiOp(op, type_index)))

    # ----------
    # extern "Python"

    def _generate_cpy_extern_python_collecttype(self, tp, name):
        assert isinstance(tp, model.FunctionPtrType)
        self._do_collect_type(tp)
    _generate_cpy_dllexport_python_collecttype = \
      _generate_cpy_extern_python_plus_c_collecttype = \
      _generate_cpy_extern_python_collecttype

    def _extern_python_decl(self, tp, name, tag_and_space):
        prnt = self._prnt
        if isinstance(tp.result, model.VoidType):
            size_of_result = '0'
        else:
            context = 'result of %s' % name
            size_of_result = '(int)sizeof(%s)' % (
                tp.result.get_c_name('', context),)
        prnt('static struct _cffi_externpy_s _cffi_externpy__%s =' % name)
        prnt('  { "%s.%s", %s, 0, 0 };' % (
            self.module_name, name, size_of_result))
        prnt()
        #
        arguments = []
        context = 'argument of %s' % name
        for i, type in enumerate(tp.args):
            arg = type.get_c_name(' a%d' % i, context)
            arguments.append(arg)
        #
        repr_arguments = ', '.join(arguments)
        repr_arguments = repr_arguments or 'void'
        name_and_arguments = '%s(%s)' % (name, repr_arguments)
        if tp.abi == "__stdcall":
            name_and_arguments = '_cffi_stdcall ' + name_and_arguments
        #
        def may_need_128_bits(tp):
            return (isinstance(tp, model.PrimitiveType) and
                    tp.name == 'long double')
        #
        size_of_a = max(len(tp.args)*8, 8)
        if may_need_128_bits(tp.result):
            size_of_a = max(size_of_a, 16)
        if isinstance(tp.result, model.StructOrUnion):
            size_of_a = 'sizeof(%s) > %d ? sizeof(%s) : %d' % (
                tp.result.get_c_name(''), size_of_a,
                tp.result.get_c_name(''), size_of_a)
        prnt('%s%s' % (tag_and_space, tp.result.get_c_name(name_and_arguments)))
        prnt('{')
        prnt('  char a[%s];' % size_of_a)
        prnt('  char *p = a;')
        for i, type in enumerate(tp.args):
            arg = 'a%d' % i
            if (isinstance(type, model.StructOrUnion) or
                    may_need_128_bits(type)):
                arg = '&' + arg
                type = model.PointerType(type)
            prnt('  *(%s)(p + %d) = %s;' % (type.get_c_name('*'), i*8, arg))
        prnt('  _cffi_call_python(&_cffi_externpy__%s, p);' % name)
        if not isinstance(tp.result, model.VoidType):
            prnt('  return *(%s)p;' % (tp.result.get_c_name('*'),))
        prnt('}')
        prnt()
        self._num_externpy += 1

    def _generate_cpy_extern_python_decl(self, tp, name):
        self._extern_python_decl(tp, name, 'static ')

    def _generate_cpy_dllexport_python_decl(self, tp, name):
        self._extern_python_decl(tp, name, 'CFFI_DLLEXPORT ')

    def _generate_cpy_extern_python_plus_c_decl(self, tp, name):
        self._extern_python_decl(tp, name, '')

    def _generate_cpy_extern_python_ctx(self, tp, name):
        if self.target_is_python:
            raise VerificationError(
                "cannot use 'extern \"Python\"' in the ABI mode")
        if tp.ellipsis:
            raise NotImplementedError("a vararg function is extern \"Python\"")
        type_index = self._typesdict[tp]
        type_op = CffiOp(OP_EXTERN_PYTHON, type_index)
        self._lsts["global"].append(
            GlobalExpr(name, '&_cffi_externpy__%s' % name, type_op, name))

    _generate_cpy_dllexport_python_ctx = \
      _generate_cpy_extern_python_plus_c_ctx = \
      _generate_cpy_extern_python_ctx

    def _print_string_literal_in_array(self, s):
        prnt = self._prnt
        prnt('// # NB. this is not a string because of a size limit in MSVC')
        if not isinstance(s, bytes):    # unicode
            s = s.encode('utf-8')       # -> bytes
        else:
            s.decode('utf-8')           # got bytes, check for valid utf-8
        try:
            s.decode('ascii')
        except UnicodeDecodeError:
            s = b'# -*- encoding: utf8 -*-\n' + s
        for line in s.splitlines(True):
            comment = line
            if type('//') is bytes:     # python2
                line = map(ord, line)   #     make a list of integers
            else:                       # python3
                # type(line) is bytes, which enumerates like a list of integers
                comment = ascii(comment)[1:-1]
            prnt(('// ' + comment).rstrip())
            printed_line = ''
            for c in line:
                if len(printed_line) >= 76:
                    prnt(printed_line)
                    printed_line = ''
                printed_line += '%d,' % (c,)
            prnt(printed_line)

    # ----------
    # emitting the opcodes for individual types

    def _emit_bytecode_VoidType(self, tp, index):
        self.cffi_types[index] = CffiOp(OP_PRIMITIVE, PRIM_VOID)

    def _emit_bytecode_PrimitiveType(self, tp, index):
        prim_index = PRIMITIVE_TO_INDEX[tp.name]
        self.cffi_types[index] = CffiOp(OP_PRIMITIVE, prim_index)

    def _emit_bytecode_UnknownIntegerType(self, tp, index):
        s = ('_cffi_prim_int(sizeof(%s), (\n'
             '           ((%s)-1) | 0 /* check that %s is an integer type */\n'
             '         ) <= 0)' % (tp.name, tp.name, tp.name))
        self.cffi_types[index] = CffiOp(OP_PRIMITIVE, s)

    def _emit_bytecode_UnknownFloatType(self, tp, index):
        s = ('_cffi_prim_float(sizeof(%s) *\n'
             '           (((%s)1) / 2) * 2 /* integer => 0, float => 1 */\n'
             '         )' % (tp.name, tp.name))
        self.cffi_types[index] = CffiOp(OP_PRIMITIVE, s)

    def _emit_bytecode_RawFunctionType(self, tp, index):
        self.cffi_types[index] = CffiOp(OP_FUNCTION, self._typesdict[tp.result])
        index += 1
        for tp1 in tp.args:
            realindex = self._typesdict[tp1]
            if index != realindex:
                if isinstance(tp1, model.PrimitiveType):
                    self._emit_bytecode_PrimitiveType(tp1, index)
                else:
                    self.cffi_types[index] = CffiOp(OP_NOOP, realindex)
            index += 1
        flags = int(tp.ellipsis)
        if tp.abi is not None:
            if tp.abi == '__stdcall':
                flags |= 2
            else:
                raise NotImplementedError("abi=%r" % (tp.abi,))
        self.cffi_types[index] = CffiOp(OP_FUNCTION_END, flags)

    def _emit_bytecode_PointerType(self, tp, index):
        self.cffi_types[index] = CffiOp(OP_POINTER, self._typesdict[tp.totype])

    _emit_bytecode_ConstPointerType = _emit_bytecode_PointerType
    _emit_bytecode_NamedPointerType = _emit_bytecode_PointerType

    def _emit_bytecode_FunctionPtrType(self, tp, index):
        raw = tp.as_raw_function()
        self.cffi_types[index] = CffiOp(OP_POINTER, self._typesdict[raw])

    def _emit_bytecode_ArrayType(self, tp, index):
        item_index = self._typesdict[tp.item]
        if tp.length is None:
            self.cffi_types[index] = CffiOp(OP_OPEN_ARRAY, item_index)
        elif tp.length == '...':
            raise VerificationError(
                "type %s badly placed: the '...' array length can only be "
                "used on global arrays or on fields of structures" % (
                    str(tp).replace('/*...*/', '...'),))
        else:
            assert self.cffi_types[index + 1] == 'LEN'
            self.cffi_types[index] = CffiOp(OP_ARRAY, item_index)
            self.cffi_types[index + 1] = CffiOp(None, str(tp.length))

    def _emit_bytecode_StructType(self, tp, index):
        struct_index = self._struct_unions[tp]
        self.cffi_types[index] = CffiOp(OP_STRUCT_UNION, struct_index)
    _emit_bytecode_UnionType = _emit_bytecode_StructType

    def _emit_bytecode_EnumType(self, tp, index):
        enum_index = self._enums[tp]
        self.cffi_types[index] = CffiOp(OP_ENUM, enum_index)


if sys.version_info >= (3,):
    NativeIO = io.StringIO
else:
    class NativeIO(io.BytesIO):
        def write(self, s):
            if isinstance(s, unicode):
                s = s.encode('ascii')
            super(NativeIO, self).write(s)

def _is_file_like(maybefile):
    # compare to xml.etree.ElementTree._get_writer
    return hasattr(maybefile, 'write')

def _make_c_or_py_source(ffi, module_name, preamble, target_file, verbose):
    if verbose:
        print("generating %s" % (target_file,))
    recompiler = Recompiler(ffi, module_name,
                            target_is_python=(preamble is None))
    recompiler.collect_type_table()
    recompiler.collect_step_tables()
    if _is_file_like(target_file):
        recompiler.write_source_to_f(target_file, preamble)
        return True
    f = NativeIO()
    recompiler.write_source_to_f(f, preamble)
    output = f.getvalue()
    try:
        with open(target_file, 'r') as f1:
            if f1.read(len(output) + 1) != output:
                raise IOError
        if verbose:
            print("(already up-to-date)")
        return False     # already up-to-date
    except IOError:
        tmp_file = '%s.~%d' % (target_file, os.getpid())
        with open(tmp_file, 'w') as f1:
            f1.write(output)
        try:
            os.rename(tmp_file, target_file)
        except OSError:
            os.unlink(target_file)
            os.rename(tmp_file, target_file)
        return True

def make_c_source(ffi, module_name, preamble, target_c_file, verbose=False):
    assert preamble is not None
    return _make_c_or_py_source(ffi, module_name, preamble, target_c_file,
                                verbose)

def make_py_source(ffi, module_name, target_py_file, verbose=False):
    return _make_c_or_py_source(ffi, module_name, None, target_py_file,
                                verbose)

def _modname_to_file(outputdir, modname, extension):
    parts = modname.split('.')
    try:
        os.makedirs(os.path.join(outputdir, *parts[:-1]))
    except OSError:
        pass
    parts[-1] += extension
    return os.path.join(outputdir, *parts), parts


# Aaargh.  Distutils is not tested at all for the purpose of compiling
# DLLs that are not extension modules.  Here are some hacks to work
# around that, in the _patch_for_*() functions...

def _patch_meth(patchlist, cls, name, new_meth):
    old = getattr(cls, name)
    patchlist.append((cls, name, old))
    setattr(cls, name, new_meth)
    return old

def _unpatch_meths(patchlist):
    for cls, name, old_meth in reversed(patchlist):
        setattr(cls, name, old_meth)

def _patch_for_embedding(patchlist):
    if sys.platform == 'win32':
        # we must not remove the manifest when building for embedding!
        # FUTURE: this module was removed in setuptools 74; this is likely dead code and should be removed,
        #  since the toolchain it supports (VS2005-2008) is also long dead.
        from cffi._shimmed_dist_utils import MSVCCompiler
        if MSVCCompiler is not None:
            _patch_meth(patchlist, MSVCCompiler, '_remove_visual_c_ref',
                        lambda self, manifest_file: manifest_file)

    if sys.platform == 'darwin':
        # we must not make a '-bundle', but a '-dynamiclib' instead
        from cffi._shimmed_dist_utils import CCompiler
        def my_link_shared_object(self, *args, **kwds):
            if '-bundle' in self.linker_so:
                self.linker_so = list(self.linker_so)
                i = self.linker_so.index('-bundle')
                self.linker_so[i] = '-dynamiclib'
            return old_link_shared_object(self, *args, **kwds)
        old_link_shared_object = _patch_meth(patchlist, CCompiler,
                                             'link_shared_object',
                                             my_link_shared_object)

def _patch_for_target(patchlist, target):
    from cffi._shimmed_dist_utils import build_ext
    # if 'target' is different from '*', we need to patch some internal
    # method to just return this 'target' value, instead of having it
    # built from module_name
    if target.endswith('.*'):
        target = target[:-2]
        if sys.platform == 'win32':
            target += '.dll'
        elif sys.platform == 'darwin':
            target += '.dylib'
        else:
            target += '.so'
    _patch_meth(patchlist, build_ext, 'get_ext_filename',
                lambda self, ext_name: target)


def recompile(ffi, module_name, preamble, tmpdir='.', call_c_compiler=True,
              c_file=None, source_extension='.c', extradir=None,
              compiler_verbose=1, target=None, debug=None,
              uses_ffiplatform=True, **kwds):
    if not isinstance(module_name, str):
        module_name = module_name.encode('ascii')
    if ffi._windows_unicode:
        ffi._apply_windows_unicode(kwds)
    if preamble is not None:
        if call_c_compiler and _is_file_like(c_file):
            raise TypeError("Writing to file-like objects is not supported "
                            "with call_c_compiler=True")
        embedding = (ffi._embedding is not None)
        if embedding:
            ffi._apply_embedding_fix(kwds)
        if c_file is None:
            c_file, parts = _modname_to_file(tmpdir, module_name,
                                             source_extension)
            if extradir:
                parts = [extradir] + parts
            ext_c_file = os.path.join(*parts)
        else:
            ext_c_file = c_file
        #
        if target is None:
            if embedding:
                target = '%s.*' % module_name
            else:
                target = '*'
        #
        if uses_ffiplatform:
            ext = ffiplatform.get_extension(ext_c_file, module_name, **kwds)
        else:
            ext = None
        updated = make_c_source(ffi, module_name, preamble, c_file,
                                verbose=compiler_verbose)
        if call_c_compiler:
            patchlist = []
            cwd = os.getcwd()
            try:
                if embedding:
                    _patch_for_embedding(patchlist)
                if target != '*':
                    _patch_for_target(patchlist, target)
                if compiler_verbose:
                    if tmpdir == '.':
                        msg = 'the current directory is'
                    else:
                        msg = 'setting the current directory to'
                    print('%s %r' % (msg, os.path.abspath(tmpdir)))
                os.chdir(tmpdir)
                outputfilename = ffiplatform.compile('.', ext,
                                                     compiler_verbose, debug)
            finally:
                os.chdir(cwd)
                _unpatch_meths(patchlist)
            return outputfilename
        else:
            return ext, updated
    else:
        if c_file is None:
            c_file, _ = _modname_to_file(tmpdir, module_name, '.py')
        updated = make_py_source(ffi, module_name, c_file,
                                 verbose=compiler_verbose)
        if call_c_compiler:
            return c_file
        else:
            return None, updated


# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\tables\_c_m_a_p.py ===
from fontTools.misc.textTools import bytesjoin, safeEval, readHex
from fontTools.misc.encodingTools import getEncoding
from fontTools.ttLib import getSearchRange
from fontTools.unicode import Unicode
from . import DefaultTable
import sys
import struct
import array
import logging


log = logging.getLogger(__name__)


def _make_map(font, chars, gids):
    assert len(chars) == len(gids)
    glyphNames = font.getGlyphNameMany(gids)
    cmap = {}
    for char, gid, name in zip(chars, gids, glyphNames):
        if gid == 0:
            continue
        cmap[char] = name
    return cmap


class table__c_m_a_p(DefaultTable.DefaultTable):
    """Character to Glyph Index Mapping Table

    This class represents the `cmap <https://docs.microsoft.com/en-us/typography/opentype/spec/cmap>`_
    table, which maps between input characters (in Unicode or other system encodings)
    and glyphs within the font. The ``cmap`` table contains one or more subtables
    which determine the mapping of of characters to glyphs across different platforms
    and encoding systems.

    ``table__c_m_a_p`` objects expose an accessor ``.tables`` which provides access
    to the subtables, although it is normally easier to retrieve individual subtables
    through the utility methods described below. To add new subtables to a font,
    first determine the subtable format (if in doubt use format 4 for glyphs within
    the BMP, format 12 for glyphs outside the BMP, and format 14 for Unicode Variation
    Sequences) construct subtable objects with ``CmapSubtable.newSubtable(format)``,
    and append them to the ``.tables`` list.

    Within a subtable, the mapping of characters to glyphs is provided by the ``.cmap``
    attribute.

    Example::

            cmap4_0_3 = CmapSubtable.newSubtable(4)
            cmap4_0_3.platformID = 0
            cmap4_0_3.platEncID = 3
            cmap4_0_3.language = 0
            cmap4_0_3.cmap = { 0xC1: "Aacute" }

            cmap = newTable("cmap")
            cmap.tableVersion = 0
            cmap.tables = [cmap4_0_3]

    See also https://learn.microsoft.com/en-us/typography/opentype/spec/cmap
    """

    def getcmap(self, platformID, platEncID):
        """Returns the first subtable which matches the given platform and encoding.

        Args:
                platformID (int): The platform ID. Use 0 for Unicode, 1 for Macintosh
                        (deprecated for new fonts), 2 for ISO (deprecated) and 3 for Windows.
                encodingID (int): Encoding ID. Interpretation depends on the platform ID.
                        See the OpenType specification for details.

        Returns:
                An object which is a subclass of :py:class:`CmapSubtable` if a matching
                subtable is found within the font, or ``None`` otherwise.
        """

        for subtable in self.tables:
            if subtable.platformID == platformID and subtable.platEncID == platEncID:
                return subtable
        return None  # not found

    def getBestCmap(
        self,
        cmapPreferences=(
            (3, 10),
            (0, 6),
            (0, 4),
            (3, 1),
            (0, 3),
            (0, 2),
            (0, 1),
            (0, 0),
        ),
    ):
        """Returns the 'best' Unicode cmap dictionary available in the font
        or ``None``, if no Unicode cmap subtable is available.

        By default it will search for the following (platformID, platEncID)
        pairs in order::

                        (3, 10), # Windows Unicode full repertoire
                        (0, 6),  # Unicode full repertoire (format 13 subtable)
                        (0, 4),  # Unicode 2.0 full repertoire
                        (3, 1),  # Windows Unicode BMP
                        (0, 3),  # Unicode 2.0 BMP
                        (0, 2),  # Unicode ISO/IEC 10646
                        (0, 1),  # Unicode 1.1
                        (0, 0)   # Unicode 1.0

        This particular order matches what HarfBuzz uses to choose what
        subtable to use by default. This order prefers the largest-repertoire
        subtable, and among those, prefers the Windows-platform over the
        Unicode-platform as the former has wider support.

        This order can be customized via the ``cmapPreferences`` argument.
        """
        for platformID, platEncID in cmapPreferences:
            cmapSubtable = self.getcmap(platformID, platEncID)
            if cmapSubtable is not None:
                return cmapSubtable.cmap
        return None  # None of the requested cmap subtables were found

    def buildReversed(self):
        """Builds a reverse mapping dictionary

        Iterates over all Unicode cmap tables and returns a dictionary mapping
        glyphs to sets of codepoints, such as::

                {
                        'one': {0x31}
                        'A': {0x41,0x391}
                }

        The values are sets of Unicode codepoints because
        some fonts map different codepoints to the same glyph.
        For example, ``U+0041 LATIN CAPITAL LETTER A`` and ``U+0391
        GREEK CAPITAL LETTER ALPHA`` are sometimes the same glyph.
        """
        result = {}
        for subtable in self.tables:
            if subtable.isUnicode():
                for codepoint, name in subtable.cmap.items():
                    result.setdefault(name, set()).add(codepoint)
        return result

    def buildReversedMin(self):
        result = {}
        for subtable in self.tables:
            if subtable.isUnicode():
                for codepoint, name in subtable.cmap.items():
                    if name in result:
                        result[name] = min(result[name], codepoint)
                    else:
                        result[name] = codepoint
        return result

    def decompile(self, data, ttFont):
        tableVersion, numSubTables = struct.unpack(">HH", data[:4])
        self.tableVersion = int(tableVersion)
        self.tables = tables = []
        seenOffsets = {}
        for i in range(numSubTables):
            platformID, platEncID, offset = struct.unpack(
                ">HHl", data[4 + i * 8 : 4 + (i + 1) * 8]
            )
            platformID, platEncID = int(platformID), int(platEncID)
            format, length = struct.unpack(">HH", data[offset : offset + 4])
            if format in [8, 10, 12, 13]:
                format, reserved, length = struct.unpack(
                    ">HHL", data[offset : offset + 8]
                )
            elif format in [14]:
                format, length = struct.unpack(">HL", data[offset : offset + 6])

            if not length:
                log.error(
                    "cmap subtable is reported as having zero length: platformID %s, "
                    "platEncID %s, format %s offset %s. Skipping table.",
                    platformID,
                    platEncID,
                    format,
                    offset,
                )
                continue
            table = CmapSubtable.newSubtable(format)
            table.platformID = platformID
            table.platEncID = platEncID
            # Note that by default we decompile only the subtable header info;
            # any other data gets decompiled only when an attribute of the
            # subtable is referenced.
            table.decompileHeader(data[offset : offset + int(length)], ttFont)
            if offset in seenOffsets:
                table.data = None  # Mark as decompiled
                table.cmap = tables[seenOffsets[offset]].cmap
            else:
                seenOffsets[offset] = i
            tables.append(table)
        if ttFont.lazy is False:  # Be lazy for None and True
            self.ensureDecompiled()

    def ensureDecompiled(self, recurse=False):
        # The recurse argument is unused, but part of the signature of
        # ensureDecompiled across the library.
        for st in self.tables:
            st.ensureDecompiled()

    def compile(self, ttFont):
        self.tables.sort()  # sort according to the spec; see CmapSubtable.__lt__()
        numSubTables = len(self.tables)
        totalOffset = 4 + 8 * numSubTables
        data = struct.pack(">HH", self.tableVersion, numSubTables)
        tableData = b""
        seen = (
            {}
        )  # Some tables are the same object reference. Don't compile them twice.
        done = (
            {}
        )  # Some tables are different objects, but compile to the same data chunk
        for table in self.tables:
            offset = seen.get(id(table.cmap))
            if offset is None:
                chunk = table.compile(ttFont)
                offset = done.get(chunk)
                if offset is None:
                    offset = seen[id(table.cmap)] = done[chunk] = totalOffset + len(
                        tableData
                    )
                    tableData = tableData + chunk
            data = data + struct.pack(">HHl", table.platformID, table.platEncID, offset)
        return data + tableData

    def toXML(self, writer, ttFont):
        writer.simpletag("tableVersion", version=self.tableVersion)
        writer.newline()
        for table in self.tables:
            table.toXML(writer, ttFont)

    def fromXML(self, name, attrs, content, ttFont):
        if name == "tableVersion":
            self.tableVersion = safeEval(attrs["version"])
            return
        if name[:12] != "cmap_format_":
            return
        if not hasattr(self, "tables"):
            self.tables = []
        format = safeEval(name[12:])
        table = CmapSubtable.newSubtable(format)
        table.platformID = safeEval(attrs["platformID"])
        table.platEncID = safeEval(attrs["platEncID"])
        table.fromXML(name, attrs, content, ttFont)
        self.tables.append(table)


class CmapSubtable(object):
    """Base class for all cmap subtable formats.

    Subclasses which handle the individual subtable formats are named
    ``cmap_format_0``, ``cmap_format_2`` etc. Use :py:meth:`getSubtableClass`
    to retrieve the concrete subclass, or :py:meth:`newSubtable` to get a
    new subtable object for a given format.

    The object exposes a ``.cmap`` attribute, which contains a dictionary mapping
    character codepoints to glyph names.
    """

    @staticmethod
    def getSubtableClass(format):
        """Return the subtable class for a format."""
        return cmap_classes.get(format, cmap_format_unknown)

    @staticmethod
    def newSubtable(format):
        """Return a new instance of a subtable for the given format
        ."""
        subtableClass = CmapSubtable.getSubtableClass(format)
        return subtableClass(format)

    def __init__(self, format):
        self.format = format
        self.data = None
        self.ttFont = None
        self.platformID = None  #: The platform ID of this subtable
        self.platEncID = None  #: The encoding ID of this subtable (interpretation depends on ``platformID``)
        self.language = (
            None  #: The language ID of this subtable (Macintosh platform only)
        )

    def ensureDecompiled(self, recurse=False):
        # The recurse argument is unused, but part of the signature of
        # ensureDecompiled across the library.
        if self.data is None:
            return
        self.decompile(None, None)  # use saved data.
        self.data = None  # Once this table has been decompiled, make sure we don't
        # just return the original data. Also avoids recursion when
        # called with an attribute that the cmap subtable doesn't have.

    def __getattr__(self, attr):
        # allow lazy decompilation of subtables.
        if attr[:2] == "__":  # don't handle requests for member functions like '__lt__'
            raise AttributeError(attr)
        if self.data is None:
            raise AttributeError(attr)
        self.ensureDecompiled()
        return getattr(self, attr)

    def decompileHeader(self, data, ttFont):
        format, length, language = struct.unpack(">HHH", data[:6])
        assert (
            len(data) == length
        ), "corrupt cmap table format %d (data length: %d, header length: %d)" % (
            format,
            len(data),
            length,
        )
        self.format = int(format)
        self.length = int(length)
        self.language = int(language)
        self.data = data[6:]
        self.ttFont = ttFont

    def toXML(self, writer, ttFont):
        writer.begintag(
            self.__class__.__name__,
            [
                ("platformID", self.platformID),
                ("platEncID", self.platEncID),
                ("language", self.language),
            ],
        )
        writer.newline()
        codes = sorted(self.cmap.items())
        self._writeCodes(codes, writer)
        writer.endtag(self.__class__.__name__)
        writer.newline()

    def getEncoding(self, default=None):
        """Returns the Python encoding name for this cmap subtable based on its platformID,
        platEncID, and language.  If encoding for these values is not known, by default
        ``None`` is returned.  That can be overridden by passing a value to the ``default``
        argument.

        Note that if you want to choose a "preferred" cmap subtable, most of the time
        ``self.isUnicode()`` is what you want as that one only returns true for the modern,
        commonly used, Unicode-compatible triplets, not the legacy ones.
        """
        return getEncoding(self.platformID, self.platEncID, self.language, default)

    def isUnicode(self):
        """Returns true if the characters are interpreted as Unicode codepoints."""
        return self.platformID == 0 or (
            self.platformID == 3 and self.platEncID in [0, 1, 10]
        )

    def isSymbol(self):
        """Returns true if the subtable is for the Symbol encoding (3,0)"""
        return self.platformID == 3 and self.platEncID == 0

    def _writeCodes(self, codes, writer):
        isUnicode = self.isUnicode()
        for code, name in codes:
            writer.simpletag("map", code=hex(code), name=name)
            if isUnicode:
                writer.comment(Unicode[code])
            writer.newline()

    def __lt__(self, other):
        if not isinstance(other, CmapSubtable):
            return NotImplemented

        # implemented so that list.sort() sorts according to the spec.
        selfTuple = (
            getattr(self, "platformID", None),
            getattr(self, "platEncID", None),
            getattr(self, "language", None),
            self.__dict__,
        )
        otherTuple = (
            getattr(other, "platformID", None),
            getattr(other, "platEncID", None),
            getattr(other, "language", None),
            other.__dict__,
        )
        return selfTuple < otherTuple


class cmap_format_0(CmapSubtable):
    def decompile(self, data, ttFont):
        # we usually get here indirectly from the subtable __getattr__ function, in which case both args must be None.
        # If not, someone is calling the subtable decompile() directly, and must provide both args.
        if data is not None and ttFont is not None:
            self.decompileHeader(data, ttFont)
        else:
            assert (
                data is None and ttFont is None
            ), "Need both data and ttFont arguments"
        data = (
            self.data
        )  # decompileHeader assigns the data after the header to self.data
        assert 262 == self.length, "Format 0 cmap subtable not 262 bytes"
        gids = array.array("B")
        gids.frombytes(self.data)
        charCodes = list(range(len(gids)))
        self.cmap = _make_map(self.ttFont, charCodes, gids)

    def compile(self, ttFont):
        if self.data:
            return struct.pack(">HHH", 0, 262, self.language) + self.data

        cmap = self.cmap
        assert set(cmap.keys()).issubset(range(256))
        getGlyphID = ttFont.getGlyphID
        valueList = [getGlyphID(cmap[i]) if i in cmap else 0 for i in range(256)]

        gids = array.array("B", valueList)
        data = struct.pack(">HHH", 0, 262, self.language) + gids.tobytes()
        assert len(data) == 262
        return data

    def fromXML(self, name, attrs, content, ttFont):
        self.language = safeEval(attrs["language"])
        if not hasattr(self, "cmap"):
            self.cmap = {}
        cmap = self.cmap
        for element in content:
            if not isinstance(element, tuple):
                continue
            name, attrs, content = element
            if name != "map":
                continue
            cmap[safeEval(attrs["code"])] = attrs["name"]


subHeaderFormat = ">HHhH"


class SubHeader(object):
    def __init__(self):
        self.firstCode = None
        self.entryCount = None
        self.idDelta = None
        self.idRangeOffset = None
        self.glyphIndexArray = []


class cmap_format_2(CmapSubtable):
    def setIDDelta(self, subHeader):
        subHeader.idDelta = 0
        # find the minGI which is not zero.
        minGI = subHeader.glyphIndexArray[0]
        for gid in subHeader.glyphIndexArray:
            if (gid != 0) and (gid < minGI):
                minGI = gid
        # The lowest gid in glyphIndexArray, after subtracting idDelta, must be 1.
        # idDelta is a short, and must be between -32K and 32K. minGI can be between 1 and 64K.
        # We would like to pick an idDelta such that the first glyphArray GID is 1,
        # so that we are more likely to be able to combine glypharray GID subranges.
        # This means that we have a problem when minGI is > 32K
        # Since the final gi is reconstructed from the glyphArray GID by:
        #    (short)finalGID = (gid + idDelta) % 0x10000),
        # we can get from a glypharray GID of 1 to a final GID of 65K by subtracting 2, and casting the
        # negative number to an unsigned short.

        if minGI > 1:
            if minGI > 0x7FFF:
                subHeader.idDelta = -(0x10000 - minGI) - 1
            else:
                subHeader.idDelta = minGI - 1
            idDelta = subHeader.idDelta
            for i in range(subHeader.entryCount):
                gid = subHeader.glyphIndexArray[i]
                if gid > 0:
                    subHeader.glyphIndexArray[i] = gid - idDelta

    def decompile(self, data, ttFont):
        # we usually get here indirectly from the subtable __getattr__ function, in which case both args must be None.
        # If not, someone is calling the subtable decompile() directly, and must provide both args.
        if data is not None and ttFont is not None:
            self.decompileHeader(data, ttFont)
        else:
            assert (
                data is None and ttFont is None
            ), "Need both data and ttFont arguments"

        data = (
            self.data
        )  # decompileHeader assigns the data after the header to self.data
        subHeaderKeys = []
        maxSubHeaderindex = 0
        # get the key array, and determine the number of subHeaders.
        allKeys = array.array("H")
        allKeys.frombytes(data[:512])
        data = data[512:]
        if sys.byteorder != "big":
            allKeys.byteswap()
        subHeaderKeys = [key // 8 for key in allKeys]
        maxSubHeaderindex = max(subHeaderKeys)

        # Load subHeaders
        subHeaderList = []
        pos = 0
        for i in range(maxSubHeaderindex + 1):
            subHeader = SubHeader()
            (
                subHeader.firstCode,
                subHeader.entryCount,
                subHeader.idDelta,
                subHeader.idRangeOffset,
            ) = struct.unpack(subHeaderFormat, data[pos : pos + 8])
            pos += 8
            giDataPos = pos + subHeader.idRangeOffset - 2
            giList = array.array("H")
            giList.frombytes(data[giDataPos : giDataPos + subHeader.entryCount * 2])
            if sys.byteorder != "big":
                giList.byteswap()
            subHeader.glyphIndexArray = giList
            subHeaderList.append(subHeader)
        # How this gets processed.
        # Charcodes may be one or two bytes.
        # The first byte of a charcode is mapped through the subHeaderKeys, to select
        # a subHeader. For any subheader but 0, the next byte is then mapped through the
        # selected subheader. If subheader Index 0 is selected, then the byte itself is
        # mapped through the subheader, and there is no second byte.
        # Then assume that the subsequent byte is the first byte of the next charcode,and repeat.
        #
        # Each subheader references a range in the glyphIndexArray whose length is entryCount.
        # The range in glyphIndexArray referenced by a sunheader may overlap with the range in glyphIndexArray
        # referenced by another subheader.
        # The only subheader that will be referenced by more than one first-byte value is the subheader
        # that maps the entire range of glyphID values to glyphIndex 0, e.g notdef:
        # 	 {firstChar 0, EntryCount 0,idDelta 0,idRangeOffset xx}
        # A byte being mapped though a subheader is treated as in index into a mapping of array index to font glyphIndex.
        # A subheader specifies a subrange within (0...256) by the
        # firstChar and EntryCount values. If the byte value is outside the subrange, then the glyphIndex is zero
        # (e.g. glyph not in font).
        # If the byte index is in the subrange, then an offset index is calculated as (byteIndex - firstChar).
        # The index to glyphIndex mapping is a subrange of the glyphIndexArray. You find the start of the subrange by
        # counting idRangeOffset bytes from the idRangeOffset word. The first value in this subrange is the
        # glyphIndex for the index firstChar. The offset index should then be used in this array to get the glyphIndex.
        # Example for Logocut-Medium
        # first byte of charcode = 129; selects subheader 1.
        # subheader 1 = {firstChar 64, EntryCount 108,idDelta 42,idRangeOffset 0252}
        # second byte of charCode = 66
        # the index offset = 66-64 = 2.
        # The subrange of the glyphIndexArray starting at 0x0252 bytes from the idRangeOffset word is:
        # [glyphIndexArray index], [subrange array index] = glyphIndex
        # [256], [0]=1 	from charcode [129, 64]
        # [257], [1]=2  	from charcode [129, 65]
        # [258], [2]=3  	from charcode [129, 66]
        # [259], [3]=4  	from charcode [129, 67]
        # So, the glyphIndex = 3 from the array. Then if idDelta is not zero and the glyph ID is not zero,
        # add it to the glyphID to get the final glyphIndex
        # value. In this case the final glyph index = 3+ 42 -> 45 for the final glyphIndex. Whew!

        self.data = b""
        cmap = {}
        notdefGI = 0
        for firstByte in range(256):
            subHeadindex = subHeaderKeys[firstByte]
            subHeader = subHeaderList[subHeadindex]
            if subHeadindex == 0:
                if (firstByte < subHeader.firstCode) or (
                    firstByte >= subHeader.firstCode + subHeader.entryCount
                ):
                    continue  # gi is notdef.
                else:
                    charCode = firstByte
                    offsetIndex = firstByte - subHeader.firstCode
                    gi = subHeader.glyphIndexArray[offsetIndex]
                    if gi != 0:
                        gi = (gi + subHeader.idDelta) % 0x10000
                    else:
                        continue  # gi is notdef.
                cmap[charCode] = gi
            else:
                if subHeader.entryCount:
                    charCodeOffset = firstByte * 256 + subHeader.firstCode
                    for offsetIndex in range(subHeader.entryCount):
                        charCode = charCodeOffset + offsetIndex
                        gi = subHeader.glyphIndexArray[offsetIndex]
                        if gi != 0:
                            gi = (gi + subHeader.idDelta) % 0x10000
                        else:
                            continue
                        cmap[charCode] = gi
                # If not subHeader.entryCount, then all char codes with this first byte are
                # mapped to .notdef. We can skip this subtable, and leave the glyphs un-encoded, which is the
                # same as mapping it to .notdef.

        gids = list(cmap.values())
        charCodes = list(cmap.keys())
        self.cmap = _make_map(self.ttFont, charCodes, gids)

    def compile(self, ttFont):
        if self.data:
            return (
                struct.pack(">HHH", self.format, self.length, self.language) + self.data
            )
        kEmptyTwoCharCodeRange = -1
        notdefGI = 0

        items = sorted(self.cmap.items())
        charCodes = [item[0] for item in items]
        names = [item[1] for item in items]
        nameMap = ttFont.getReverseGlyphMap()
        try:
            gids = [nameMap[name] for name in names]
        except KeyError:
            nameMap = ttFont.getReverseGlyphMap(rebuild=True)
            try:
                gids = [nameMap[name] for name in names]
            except KeyError:
                # allow virtual GIDs in format 2 tables
                gids = []
                for name in names:
                    try:
                        gid = nameMap[name]
                    except KeyError:
                        try:
                            if name[:3] == "gid":
                                gid = int(name[3:])
                            else:
                                gid = ttFont.getGlyphID(name)
                        except:
                            raise KeyError(name)

                    gids.append(gid)

        # Process the (char code to gid) item list in char code order.
        # By definition, all one byte char codes map to subheader 0.
        # For all the two byte char codes, we assume that the first byte maps maps to the empty subhead (with an entry count of 0,
        # which defines all char codes in its range to map to notdef) unless proven otherwise.
        # Note that since the char code items are processed in char code order, all the char codes with the
        # same first byte are in sequential order.

        subHeaderKeys = [
            kEmptyTwoCharCodeRange for x in range(256)
        ]  # list of indices into subHeaderList.
        subHeaderList = []

        # We force this subheader entry 0 to exist in the subHeaderList in the case where some one comes up
        # with a cmap where all the one byte char codes map to notdef,
        # with the result that the subhead 0 would not get created just by processing the item list.
        charCode = charCodes[0]
        if charCode > 255:
            subHeader = SubHeader()
            subHeader.firstCode = 0
            subHeader.entryCount = 0
            subHeader.idDelta = 0
            subHeader.idRangeOffset = 0
            subHeaderList.append(subHeader)

        lastFirstByte = -1
        items = zip(charCodes, gids)
        for charCode, gid in items:
            if gid == 0:
                continue
            firstbyte = charCode >> 8
            secondByte = charCode & 0x00FF

            if (
                firstbyte != lastFirstByte
            ):  # Need to update the current subhead, and start a new one.
                if lastFirstByte > -1:
                    # fix GI's and iDelta of current subheader.
                    self.setIDDelta(subHeader)

                    # If it was sunheader 0 for one-byte charCodes, then we need to set the subHeaderKeys value to zero
                    # for the indices matching the char codes.
                    if lastFirstByte == 0:
                        for index in range(subHeader.entryCount):
                            charCode = subHeader.firstCode + index
                            subHeaderKeys[charCode] = 0

                    assert subHeader.entryCount == len(
                        subHeader.glyphIndexArray
                    ), "Error - subhead entry count does not match len of glyphID subrange."
                # init new subheader
                subHeader = SubHeader()
                subHeader.firstCode = secondByte
                subHeader.entryCount = 1
                subHeader.glyphIndexArray.append(gid)
                subHeaderList.append(subHeader)
                subHeaderKeys[firstbyte] = len(subHeaderList) - 1
                lastFirstByte = firstbyte
            else:
                # need to fill in with notdefs all the code points between the last charCode and the current charCode.
                codeDiff = secondByte - (subHeader.firstCode + subHeader.entryCount)
                for i in range(codeDiff):
                    subHeader.glyphIndexArray.append(notdefGI)
                subHeader.glyphIndexArray.append(gid)
                subHeader.entryCount = subHeader.entryCount + codeDiff + 1

        # fix GI's and iDelta of last subheader that we we added to the subheader array.
        self.setIDDelta(subHeader)

        # Now we add a final subheader for the subHeaderKeys which maps to empty two byte charcode ranges.
        subHeader = SubHeader()
        subHeader.firstCode = 0
        subHeader.entryCount = 0
        subHeader.idDelta = 0
        subHeader.idRangeOffset = 2
        subHeaderList.append(subHeader)
        emptySubheadIndex = len(subHeaderList) - 1
        for index in range(256):
            if subHeaderKeys[index] == kEmptyTwoCharCodeRange:
                subHeaderKeys[index] = emptySubheadIndex
        # Since this is the last subheader, the GlyphIndex Array starts two bytes after the start of the
        # idRangeOffset word of this subHeader. We can safely point to the first entry in the GlyphIndexArray,
        # since the first subrange of the GlyphIndexArray is for subHeader 0, which always starts with
        # charcode 0 and GID 0.

        idRangeOffset = (
            len(subHeaderList) - 1
        ) * 8 + 2  # offset to beginning of glyphIDArray from first subheader idRangeOffset.
        subheadRangeLen = (
            len(subHeaderList) - 1
        )  # skip last special empty-set subheader; we've already hardocodes its idRangeOffset to 2.
        for index in range(subheadRangeLen):
            subHeader = subHeaderList[index]
            subHeader.idRangeOffset = 0
            for j in range(index):
                prevSubhead = subHeaderList[j]
                if (
                    prevSubhead.glyphIndexArray == subHeader.glyphIndexArray
                ):  # use the glyphIndexArray subarray
                    subHeader.idRangeOffset = (
                        prevSubhead.idRangeOffset - (index - j) * 8
                    )
                    subHeader.glyphIndexArray = []
                    break
            if subHeader.idRangeOffset == 0:  # didn't find one.
                subHeader.idRangeOffset = idRangeOffset
                idRangeOffset = (
                    idRangeOffset - 8
                ) + subHeader.entryCount * 2  # one less subheader, one more subArray.
            else:
                idRangeOffset = idRangeOffset - 8  # one less subheader

        # Now we can write out the data!
        length = (
            6 + 512 + 8 * len(subHeaderList)
        )  # header, 256 subHeaderKeys, and subheader array.
        for subhead in subHeaderList[:-1]:
            length = (
                length + len(subhead.glyphIndexArray) * 2
            )  # We can't use subhead.entryCount, as some of the subhead may share subArrays.
        dataList = [struct.pack(">HHH", 2, length, self.language)]
        for index in subHeaderKeys:
            dataList.append(struct.pack(">H", index * 8))
        for subhead in subHeaderList:
            dataList.append(
                struct.pack(
                    subHeaderFormat,
                    subhead.firstCode,
                    subhead.entryCount,
                    subhead.idDelta,
                    subhead.idRangeOffset,
                )
            )
        for subhead in subHeaderList[:-1]:
            for gi in subhead.glyphIndexArray:
                dataList.append(struct.pack(">H", gi))
        data = bytesjoin(dataList)
        assert len(data) == length, (
            "Error: cmap format 2 is not same length as calculated! actual: "
            + str(len(data))
            + " calc : "
            + str(length)
        )
        return data

    def fromXML(self, name, attrs, content, ttFont):
        self.language = safeEval(attrs["language"])
        if not hasattr(self, "cmap"):
            self.cmap = {}
        cmap = self.cmap

        for element in content:
            if not isinstance(element, tuple):
                continue
            name, attrs, content = element
            if name != "map":
                continue
            cmap[safeEval(attrs["code"])] = attrs["name"]


cmap_format_4_format = ">7H"

# uint16  endCode[segCount]          # Ending character code for each segment, last = 0xFFFF.
# uint16  reservedPad                # This value should be zero
# uint16  startCode[segCount]        # Starting character code for each segment
# uint16  idDelta[segCount]          # Delta for all character codes in segment
# uint16  idRangeOffset[segCount]    # Offset in bytes to glyph indexArray, or 0
# uint16  glyphIndexArray[variable]  # Glyph index array


def splitRange(startCode, endCode, cmap):
    # Try to split a range of character codes into subranges with consecutive
    # glyph IDs in such a way that the cmap4 subtable can be stored "most"
    # efficiently. I can't prove I've got the optimal solution, but it seems
    # to do well with the fonts I tested: none became bigger, many became smaller.
    if startCode == endCode:
        return [], [endCode]

    lastID = cmap[startCode]
    lastCode = startCode
    inOrder = None
    orderedBegin = None
    subRanges = []

    # Gather subranges in which the glyph IDs are consecutive.
    for code in range(startCode + 1, endCode + 1):
        glyphID = cmap[code]

        if glyphID - 1 == lastID:
            if inOrder is None or not inOrder:
                inOrder = 1
                orderedBegin = lastCode
        else:
            if inOrder:
                inOrder = 0
                subRanges.append((orderedBegin, lastCode))
                orderedBegin = None

        lastID = glyphID
        lastCode = code

    if inOrder:
        subRanges.append((orderedBegin, lastCode))
    assert lastCode == endCode

    # Now filter out those new subranges that would only make the data bigger.
    # A new segment cost 8 bytes, not using a new segment costs 2 bytes per
    # character.
    newRanges = []
    for b, e in subRanges:
        if b == startCode and e == endCode:
            break  # the whole range, we're fine
        if b == startCode or e == endCode:
            threshold = 4  # split costs one more segment
        else:
            threshold = 8  # split costs two more segments
        if (e - b + 1) > threshold:
            newRanges.append((b, e))
    subRanges = newRanges

    if not subRanges:
        return [], [endCode]

    if subRanges[0][0] != startCode:
        subRanges.insert(0, (startCode, subRanges[0][0] - 1))
    if subRanges[-1][1] != endCode:
        subRanges.append((subRanges[-1][1] + 1, endCode))

    # Fill the "holes" in the segments list -- those are the segments in which
    # the glyph IDs are _not_ consecutive.
    i = 1
    while i < len(subRanges):
        if subRanges[i - 1][1] + 1 != subRanges[i][0]:
            subRanges.insert(i, (subRanges[i - 1][1] + 1, subRanges[i][0] - 1))
            i = i + 1
        i = i + 1

    # Transform the ranges into startCode/endCode lists.
    start = []
    end = []
    for b, e in subRanges:
        start.append(b)
        end.append(e)
    start.pop(0)

    assert len(start) + 1 == len(end)
    return start, end


class cmap_format_4(CmapSubtable):
    def decompile(self, data, ttFont):
        # we usually get here indirectly from the subtable __getattr__ function, in which case both args must be None.
        # If not, someone is calling the subtable decompile() directly, and must provide both args.
        if data is not None and ttFont is not None:
            self.decompileHeader(data, ttFont)
        else:
            assert (
                data is None and ttFont is None
            ), "Need both data and ttFont arguments"

        data = (
            self.data
        )  # decompileHeader assigns the data after the header to self.data
        (segCountX2, searchRange, entrySelector, rangeShift) = struct.unpack(
            ">4H", data[:8]
        )
        data = data[8:]
        segCount = segCountX2 // 2

        allCodes = array.array("H")
        allCodes.frombytes(data)
        self.data = data = None

        if sys.byteorder != "big":
            allCodes.byteswap()

        # divide the data
        endCode = allCodes[:segCount]
        allCodes = allCodes[segCount + 1 :]  # the +1 is skipping the reservedPad field
        startCode = allCodes[:segCount]
        allCodes = allCodes[segCount:]
        idDelta = allCodes[:segCount]
        allCodes = allCodes[segCount:]
        idRangeOffset = allCodes[:segCount]
        glyphIndexArray = allCodes[segCount:]
        lenGIArray = len(glyphIndexArray)

        # build 2-byte character mapping
        charCodes = []
        gids = []
        for i in range(len(startCode) - 1):  # don't do 0xffff!
            start = startCode[i]
            delta = idDelta[i]
            rangeOffset = idRangeOffset[i]
            partial = rangeOffset // 2 - start + i - len(idRangeOffset)

            rangeCharCodes = list(range(startCode[i], endCode[i] + 1))
            charCodes.extend(rangeCharCodes)
            if rangeOffset == 0:
                gids.extend(
                    [(charCode + delta) & 0xFFFF for charCode in rangeCharCodes]
                )
            else:
                for charCode in rangeCharCodes:
                    index = charCode + partial
                    assert index < lenGIArray, (
                        "In format 4 cmap, range (%d), the calculated index (%d) into the glyph index array is not less than the length of the array (%d) !"
                        % (i, index, lenGIArray)
                    )
                    if glyphIndexArray[index] != 0:  # if not missing glyph
                        glyphID = glyphIndexArray[index] + delta
                    else:
                        glyphID = 0  # missing glyph
                    gids.append(glyphID & 0xFFFF)

        self.cmap = _make_map(self.ttFont, charCodes, gids)

    def compile(self, ttFont):
        if self.data:
            return (
                struct.pack(">HHH", self.format, self.length, self.language) + self.data
            )

        charCodes = list(self.cmap.keys())
        if not charCodes:
            startCode = [0xFFFF]
            endCode = [0xFFFF]
        else:
            charCodes.sort()
            names = [self.cmap[code] for code in charCodes]
            nameMap = ttFont.getReverseGlyphMap()
            try:
                gids = [nameMap[name] for name in names]
            except KeyError:
                nameMap = ttFont.getReverseGlyphMap(rebuild=True)
                try:
                    gids = [nameMap[name] for name in names]
                except KeyError:
                    # allow virtual GIDs in format 4 tables
                    gids = []
                    for name in names:
                        try:
                            gid = nameMap[name]
                        except KeyError:
                            try:
                                if name[:3] == "gid":
                                    gid = int(name[3:])
                                else:
                                    gid = ttFont.getGlyphID(name)
                            except:
                                raise KeyError(name)

                        gids.append(gid)
            cmap = {}  # code:glyphID mapping
            for code, gid in zip(charCodes, gids):
                cmap[code] = gid

            # Build startCode and endCode lists.
            # Split the char codes in ranges of consecutive char codes, then split
            # each range in more ranges of consecutive/not consecutive glyph IDs.
            # See splitRange().
            lastCode = charCodes[0]
            endCode = []
            startCode = [lastCode]
            for charCode in charCodes[
                1:
            ]:  # skip the first code, it's the first start code
                if charCode == lastCode + 1:
                    lastCode = charCode
                    continue
                start, end = splitRange(startCode[-1], lastCode, cmap)
                startCode.extend(start)
                endCode.extend(end)
                startCode.append(charCode)
                lastCode = charCode
            start, end = splitRange(startCode[-1], lastCode, cmap)
            startCode.extend(start)
            endCode.extend(end)
            startCode.append(0xFFFF)
            endCode.append(0xFFFF)

        # build up rest of cruft
        idDelta = []
        idRangeOffset = []
        glyphIndexArray = []
        for i in range(len(endCode) - 1):  # skip the closing codes (0xffff)
            indices = []
            for charCode in range(startCode[i], endCode[i] + 1):
                indices.append(cmap[charCode])
            if indices == list(range(indices[0], indices[0] + len(indices))):
                idDelta.append((indices[0] - startCode[i]) % 0x10000)
                idRangeOffset.append(0)
            else:
                idDelta.append(0)
                idRangeOffset.append(2 * (len(endCode) + len(glyphIndexArray) - i))
                glyphIndexArray.extend(indices)
        idDelta.append(1)  # 0xffff + 1 == (tadaa!) 0. So this end code maps to .notdef
        idRangeOffset.append(0)

        # Insane.
        segCount = len(endCode)
        segCountX2 = segCount * 2
        searchRange, entrySelector, rangeShift = getSearchRange(segCount, 2)

        charCodeArray = array.array("H", endCode + [0] + startCode)
        idDeltaArray = array.array("H", idDelta)
        restArray = array.array("H", idRangeOffset + glyphIndexArray)
        if sys.byteorder != "big":
            charCodeArray.byteswap()
        if sys.byteorder != "big":
            idDeltaArray.byteswap()
        if sys.byteorder != "big":
            restArray.byteswap()
        data = charCodeArray.tobytes() + idDeltaArray.tobytes() + restArray.tobytes()

        length = struct.calcsize(cmap_format_4_format) + len(data)
        header = struct.pack(
            cmap_format_4_format,
            self.format,
            length,
            self.language,
            segCountX2,
            searchRange,
            entrySelector,
            rangeShift,
        )
        return header + data

    def fromXML(self, name, attrs, content, ttFont):
        self.language = safeEval(attrs["language"])
        if not hasattr(self, "cmap"):
            self.cmap = {}
        cmap = self.cmap

        for element in content:
            if not isinstance(element, tuple):
                continue
            nameMap, attrsMap, dummyContent = element
            if nameMap != "map":
                assert 0, "Unrecognized keyword in cmap subtable"
            cmap[safeEval(attrsMap["code"])] = attrsMap["name"]


class cmap_format_6(CmapSubtable):
    def decompile(self, data, ttFont):
        # we usually get here indirectly from the subtable __getattr__ function, in which case both args must be None.
        # If not, someone is calling the subtable decompile() directly, and must provide both args.
        if data is not None and ttFont is not None:
            self.decompileHeader(data, ttFont)
        else:
            assert (
                data is None and ttFont is None
            ), "Need both data and ttFont arguments"

        data = (
            self.data
        )  # decompileHeader assigns the data after the header to self.data
        firstCode, entryCount = struct.unpack(">HH", data[:4])
        firstCode = int(firstCode)
        data = data[4:]
        # assert len(data) == 2 * entryCount  # XXX not true in Apple's Helvetica!!!
        gids = array.array("H")
        gids.frombytes(data[: 2 * int(entryCount)])
        if sys.byteorder != "big":
            gids.byteswap()
        self.data = data = None

        charCodes = list(range(firstCode, firstCode + len(gids)))
        self.cmap = _make_map(self.ttFont, charCodes, gids)

    def compile(self, ttFont):
        if self.data:
            return (
                struct.pack(">HHH", self.format, self.length, self.language) + self.data
            )
        cmap = self.cmap
        codes = sorted(cmap.keys())
        if codes:  # yes, there are empty cmap tables.
            codes = list(range(codes[0], codes[-1] + 1))
            firstCode = codes[0]
            valueList = [
                ttFont.getGlyphID(cmap[code]) if code in cmap else 0 for code in codes
            ]
            gids = array.array("H", valueList)
            if sys.byteorder != "big":
                gids.byteswap()
            data = gids.tobytes()
        else:
            data = b""
            firstCode = 0
        header = struct.pack(
            ">HHHHH", 6, len(data) + 10, self.language, firstCode, len(codes)
        )
        return header + data

    def fromXML(self, name, attrs, content, ttFont):
        self.language = safeEval(attrs["language"])
        if not hasattr(self, "cmap"):
            self.cmap = {}
        cmap = self.cmap

        for element in content:
            if not isinstance(element, tuple):
                continue
            name, attrs, content = element
            if name != "map":
                continue
            cmap[safeEval(attrs["code"])] = attrs["name"]


class cmap_format_12_or_13(CmapSubtable):
    def __init__(self, format):
        self.format = format
        self.reserved = 0
        self.data = None
        self.ttFont = None

    def decompileHeader(self, data, ttFont):
        format, reserved, length, language, nGroups = struct.unpack(">HHLLL", data[:16])
        assert (
            len(data) == (16 + nGroups * 12) == (length)
        ), "corrupt cmap table format %d (data length: %d, header length: %d)" % (
            self.format,
            len(data),
            length,
        )
        self.format = format
        self.reserved = reserved
        self.length = length
        self.language = language
        self.nGroups = nGroups
        self.data = data[16:]
        self.ttFont = ttFont

    def decompile(self, data, ttFont):
        # we usually get here indirectly from the subtable __getattr__ function, in which case both args must be None.
        # If not, someone is calling the subtable decompile() directly, and must provide both args.
        if data is not None and ttFont is not None:
            self.decompileHeader(data, ttFont)
        else:
            assert (
                data is None and ttFont is None
            ), "Need both data and ttFont arguments"

        data = (
            self.data
        )  # decompileHeader assigns the data after the header to self.data
        charCodes = []
        gids = []
        pos = 0
        groups = array.array("I", data[: self.nGroups * 12])
        if sys.byteorder != "big":
            groups.byteswap()
        for i in range(self.nGroups):
            startCharCode = groups[i * 3]
            endCharCode = groups[i * 3 + 1]
            glyphID = groups[i * 3 + 2]
            lenGroup = 1 + endCharCode - startCharCode
            charCodes.extend(range(startCharCode, endCharCode + 1))
            gids.extend(self._computeGIDs(glyphID, lenGroup))
        self.data = data = None
        self.cmap = _make_map(self.ttFont, charCodes, gids)

    def compile(self, ttFont):
        if self.data:
            return (
                struct.pack(
                    ">HHLLL",
                    self.format,
                    self.reserved,
                    self.length,
                    self.language,
                    self.nGroups,
                )
                + self.data
            )
        charCodes = list(self.cmap.keys())
        names = list(self.cmap.values())
        nameMap = ttFont.getReverseGlyphMap()
        try:
            gids = [nameMap[name] for name in names]
        except KeyError:
            nameMap = ttFont.getReverseGlyphMap(rebuild=True)
            try:
                gids = [nameMap[name] for name in names]
            except KeyError:
                # allow virtual GIDs in format 12 tables
                gids = []
                for name in names:
                    try:
                        gid = nameMap[name]
                    except KeyError:
                        try:
                            if name[:3] == "gid":
                                gid = int(name[3:])
                            else:
                                gid = ttFont.getGlyphID(name)
                        except:
                            raise KeyError(name)

                    gids.append(gid)

        cmap = {}  # code:glyphID mapping
        for code, gid in zip(charCodes, gids):
            cmap[code] = gid

        charCodes.sort()
        index = 0
        startCharCode = charCodes[0]
        startGlyphID = cmap[startCharCode]
        lastGlyphID = startGlyphID - self._format_step
        lastCharCode = startCharCode - 1
        nGroups = 0
        dataList = []
        maxIndex = len(charCodes)
        for index in range(maxIndex):
            charCode = charCodes[index]
            glyphID = cmap[charCode]
            if not self._IsInSameRun(glyphID, lastGlyphID, charCode, lastCharCode):
                dataList.append(
                    struct.pack(">LLL", startCharCode, lastCharCode, startGlyphID)
                )
                startCharCode = charCode
                startGlyphID = glyphID
                nGroups = nGroups + 1
            lastGlyphID = glyphID
            lastCharCode = charCode
        dataList.append(struct.pack(">LLL", startCharCode, lastCharCode, startGlyphID))
        nGroups = nGroups + 1
        data = bytesjoin(dataList)
        lengthSubtable = len(data) + 16
        assert len(data) == (nGroups * 12) == (lengthSubtable - 16)
        return (
            struct.pack(
                ">HHLLL",
                self.format,
                self.reserved,
                lengthSubtable,
                self.language,
                nGroups,
            )
            + data
        )

    def toXML(self, writer, ttFont):
        writer.begintag(
            self.__class__.__name__,
            [
                ("platformID", self.platformID),
                ("platEncID", self.platEncID),
                ("format", self.format),
                ("reserved", self.reserved),
                ("length", self.length),
                ("language", self.language),
                ("nGroups", self.nGroups),
            ],
        )
        writer.newline()
        codes = sorted(self.cmap.items())
        self._writeCodes(codes, writer)
        writer.endtag(self.__class__.__name__)
        writer.newline()

    def fromXML(self, name, attrs, content, ttFont):
        self.format = safeEval(attrs["format"])
        self.reserved = safeEval(attrs["reserved"])
        self.length = safeEval(attrs["length"])
        self.language = safeEval(attrs["language"])
        self.nGroups = safeEval(attrs["nGroups"])
        if not hasattr(self, "cmap"):
            self.cmap = {}
        cmap = self.cmap

        for element in content:
            if not isinstance(element, tuple):
                continue
            name, attrs, content = element
            if name != "map":
                continue
            cmap[safeEval(attrs["code"])] = attrs["name"]


class cmap_format_12(cmap_format_12_or_13):
    _format_step = 1

    def __init__(self, format=12):
        cmap_format_12_or_13.__init__(self, format)

    def _computeGIDs(self, startingGlyph, numberOfGlyphs):
        return range(startingGlyph, startingGlyph + numberOfGlyphs)

    def _IsInSameRun(self, glyphID, lastGlyphID, charCode, lastCharCode):
        return (glyphID == 1 + lastGlyphID) and (charCode == 1 + lastCharCode)


class cmap_format_13(cmap_format_12_or_13):
    _format_step = 0

    def __init__(self, format=13):
        cmap_format_12_or_13.__init__(self, format)

    def _computeGIDs(self, startingGlyph, numberOfGlyphs):
        return [startingGlyph] * numberOfGlyphs

    def _IsInSameRun(self, glyphID, lastGlyphID, charCode, lastCharCode):
        return (glyphID == lastGlyphID) and (charCode == 1 + lastCharCode)


def cvtToUVS(threeByteString):
    data = b"\0" + threeByteString
    (val,) = struct.unpack(">L", data)
    return val


def cvtFromUVS(val):
    assert 0 <= val < 0x1000000
    fourByteString = struct.pack(">L", val)
    return fourByteString[1:]


class cmap_format_14(CmapSubtable):
    def decompileHeader(self, data, ttFont):
        format, length, numVarSelectorRecords = struct.unpack(">HLL", data[:10])
        self.data = data[10:]
        self.length = length
        self.numVarSelectorRecords = numVarSelectorRecords
        self.ttFont = ttFont
        self.language = 0xFF  # has no language.

    def decompile(self, data, ttFont):
        if data is not None and ttFont is not None:
            self.decompileHeader(data, ttFont)
        else:
            assert (
                data is None and ttFont is None
            ), "Need both data and ttFont arguments"
        data = self.data

        self.cmap = (
            {}
        )  # so that clients that expect this to exist in a cmap table won't fail.
        uvsDict = {}
        recOffset = 0
        for n in range(self.numVarSelectorRecords):
            uvs, defOVSOffset, nonDefUVSOffset = struct.unpack(
                ">3sLL", data[recOffset : recOffset + 11]
            )
            recOffset += 11
            varUVS = cvtToUVS(uvs)
            if defOVSOffset:
                startOffset = defOVSOffset - 10
                (numValues,) = struct.unpack(">L", data[startOffset : startOffset + 4])
                startOffset += 4
                for r in range(numValues):
                    uv, addtlCnt = struct.unpack(
                        ">3sB", data[startOffset : startOffset + 4]
                    )
                    startOffset += 4
                    firstBaseUV = cvtToUVS(uv)
                    cnt = addtlCnt + 1
                    baseUVList = list(range(firstBaseUV, firstBaseUV + cnt))
                    glyphList = [None] * cnt
                    localUVList = zip(baseUVList, glyphList)
                    try:
                        uvsDict[varUVS].extend(localUVList)
                    except KeyError:
                        uvsDict[varUVS] = list(localUVList)

            if nonDefUVSOffset:
                startOffset = nonDefUVSOffset - 10
                (numRecs,) = struct.unpack(">L", data[startOffset : startOffset + 4])
                startOffset += 4
                localUVList = []
                for r in range(numRecs):
                    uv, gid = struct.unpack(">3sH", data[startOffset : startOffset + 5])
                    startOffset += 5
                    uv = cvtToUVS(uv)
                    glyphName = self.ttFont.getGlyphName(gid)
                    localUVList.append((uv, glyphName))
                try:
                    uvsDict[varUVS].extend(localUVList)
                except KeyError:
                    uvsDict[varUVS] = localUVList

        self.uvsDict = uvsDict

    def toXML(self, writer, ttFont):
        writer.begintag(
            self.__class__.__name__,
            [
                ("platformID", self.platformID),
                ("platEncID", self.platEncID),
            ],
        )
        writer.newline()
        uvsDict = self.uvsDict
        uvsList = sorted(uvsDict.keys())
        for uvs in uvsList:
            uvList = uvsDict[uvs]
            uvList.sort(key=lambda item: (item[1] is not None, item[0], item[1]))
            for uv, gname in uvList:
                attrs = [("uv", hex(uv)), ("uvs", hex(uvs))]
                if gname is not None:
                    attrs.append(("name", gname))
                writer.simpletag("map", attrs)
                writer.newline()
        writer.endtag(self.__class__.__name__)
        writer.newline()

    def fromXML(self, name, attrs, content, ttFont):
        self.language = 0xFF  # provide a value so that CmapSubtable.__lt__() won't fail
        if not hasattr(self, "cmap"):
            self.cmap = (
                {}
            )  # so that clients that expect this to exist in a cmap table won't fail.
        if not hasattr(self, "uvsDict"):
            self.uvsDict = {}
            uvsDict = self.uvsDict

        # For backwards compatibility reasons we accept "None" as an indicator
        # for "default mapping", unless the font actually has a glyph named
        # "None".
        _hasGlyphNamedNone = None

        for element in content:
            if not isinstance(element, tuple):
                continue
            name, attrs, content = element
            if name != "map":
                continue
            uvs = safeEval(attrs["uvs"])
            uv = safeEval(attrs["uv"])
            gname = attrs.get("name")
            if gname == "None":
                if _hasGlyphNamedNone is None:
                    _hasGlyphNamedNone = "None" in ttFont.getGlyphOrder()
                if not _hasGlyphNamedNone:
                    gname = None
            try:
                uvsDict[uvs].append((uv, gname))
            except KeyError:
                uvsDict[uvs] = [(uv, gname)]

    def compile(self, ttFont):
        if self.data:
            return (
                struct.pack(
                    ">HLL", self.format, self.length, self.numVarSelectorRecords
                )
                + self.data
            )

        uvsDict = self.uvsDict
        uvsList = sorted(uvsDict.keys())
        self.numVarSelectorRecords = len(uvsList)
        offset = (
            10 + self.numVarSelectorRecords * 11
        )  # current value is end of VarSelectorRecords block.
        data = []
        varSelectorRecords = []
        for uvs in uvsList:
            entryList = uvsDict[uvs]

            defList = [entry for entry in entryList if entry[1] is None]
            if defList:
                defList = [entry[0] for entry in defList]
                defOVSOffset = offset
                defList.sort()

                lastUV = defList[0]
                cnt = -1
                defRecs = []
                for defEntry in defList:
                    cnt += 1
                    if (lastUV + cnt) != defEntry:
                        rec = struct.pack(">3sB", cvtFromUVS(lastUV), cnt - 1)
                        lastUV = defEntry
                        defRecs.append(rec)
                        cnt = 0

                rec = struct.pack(">3sB", cvtFromUVS(lastUV), cnt)
                defRecs.append(rec)

                numDefRecs = len(defRecs)
                data.append(struct.pack(">L", numDefRecs))
                data.extend(defRecs)
                offset += 4 + numDefRecs * 4
            else:
                defOVSOffset = 0

            ndefList = [entry for entry in entryList if entry[1] is not None]
            if ndefList:
                nonDefUVSOffset = offset
                ndefList.sort()
                numNonDefRecs = len(ndefList)
                data.append(struct.pack(">L", numNonDefRecs))
                offset += 4 + numNonDefRecs * 5

                for uv, gname in ndefList:
                    gid = ttFont.getGlyphID(gname)
                    ndrec = struct.pack(">3sH", cvtFromUVS(uv), gid)
                    data.append(ndrec)
            else:
                nonDefUVSOffset = 0

            vrec = struct.pack(">3sLL", cvtFromUVS(uvs), defOVSOffset, nonDefUVSOffset)
            varSelectorRecords.append(vrec)

        data = bytesjoin(varSelectorRecords) + bytesjoin(data)
        self.length = 10 + len(data)
        headerdata = struct.pack(
            ">HLL", self.format, self.length, self.numVarSelectorRecords
        )

        return headerdata + data


class cmap_format_unknown(CmapSubtable):
    def toXML(self, writer, ttFont):
        cmapName = self.__class__.__name__[:12] + str(self.format)
        writer.begintag(
            cmapName,
            [
                ("platformID", self.platformID),
                ("platEncID", self.platEncID),
            ],
        )
        writer.newline()
        writer.dumphex(self.data)
        writer.endtag(cmapName)
        writer.newline()

    def fromXML(self, name, attrs, content, ttFont):
        self.data = readHex(content)
        self.cmap = {}

    def decompileHeader(self, data, ttFont):
        self.language = 0  # dummy value
        self.data = data

    def decompile(self, data, ttFont):
        # we usually get here indirectly from the subtable __getattr__ function, in which case both args must be None.
        # If not, someone is calling the subtable decompile() directly, and must provide both args.
        if data is not None and ttFont is not None:
            self.decompileHeader(data, ttFont)
        else:
            assert (
                data is None and ttFont is None
            ), "Need both data and ttFont arguments"

    def compile(self, ttFont):
        if self.data:
            return self.data
        else:
            return None


cmap_classes = {
    0: cmap_format_0,
    2: cmap_format_2,
    4: cmap_format_4,
    6: cmap_format_6,
    12: cmap_format_12,
    13: cmap_format_13,
    14: cmap_format_14,
}