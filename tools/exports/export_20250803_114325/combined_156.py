
# === NexusCore/openenv\Lib\site-packages\nltk\test\unit\lm\test_models.py ===
# Natural Language Toolkit: Language Model Unit Tests
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Ilia Kurenkov <ilia.kurenkov@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
import math
from math import fsum as sum
from operator import itemgetter

import pytest

from nltk.lm import (
    MLE,
    AbsoluteDiscountingInterpolated,
    KneserNeyInterpolated,
    Laplace,
    Lidstone,
    StupidBackoff,
    Vocabulary,
    WittenBellInterpolated,
)
from nltk.lm.preprocessing import padded_everygrams


@pytest.fixture(scope="session")
def vocabulary():
    return Vocabulary(["a", "b", "c", "d", "z", "<s>", "</s>"], unk_cutoff=1)


@pytest.fixture(scope="session")
def training_data():
    return [["a", "b", "c", "d"], ["e", "g", "a", "d", "b", "e"]]


@pytest.fixture(scope="session")
def bigram_training_data(training_data):
    return [list(padded_everygrams(2, sent)) for sent in training_data]


@pytest.fixture(scope="session")
def trigram_training_data(training_data):
    return [list(padded_everygrams(3, sent)) for sent in training_data]


@pytest.fixture
def mle_bigram_model(vocabulary, bigram_training_data):
    model = MLE(2, vocabulary=vocabulary)
    model.fit(bigram_training_data)
    return model


@pytest.mark.parametrize(
    "word, context, expected_score",
    [
        ("d", ["c"], 1),
        # Unseen ngrams should yield 0
        ("d", ["e"], 0),
        # Unigrams should also be 0
        ("z", None, 0),
        # N unigrams = 14
        # count('a') = 2
        ("a", None, 2.0 / 14),
        # count('y') = 3
        ("y", None, 3.0 / 14),
    ],
)
def test_mle_bigram_scores(mle_bigram_model, word, context, expected_score):
    assert pytest.approx(mle_bigram_model.score(word, context), 1e-4) == expected_score


def test_mle_bigram_logscore_for_zero_score(mle_bigram_model):
    assert math.isinf(mle_bigram_model.logscore("d", ["e"]))


def test_mle_bigram_entropy_perplexity_seen(mle_bigram_model):
    # ngrams seen during training
    trained = [
        ("<s>", "a"),
        ("a", "b"),
        ("b", "<UNK>"),
        ("<UNK>", "a"),
        ("a", "d"),
        ("d", "</s>"),
    ]
    # Ngram = Log score
    # <s>, a    = -1
    # a, b      = -1
    # b, UNK    = -1
    # UNK, a    = -1.585
    # a, d      = -1
    # d, </s>   = -1
    # TOTAL logscores   = -6.585
    # - AVG logscores   = 1.0975
    H = 1.0975
    perplexity = 2.1398
    assert pytest.approx(mle_bigram_model.entropy(trained), 1e-4) == H
    assert pytest.approx(mle_bigram_model.perplexity(trained), 1e-4) == perplexity


def test_mle_bigram_entropy_perplexity_unseen(mle_bigram_model):
    # In MLE, even one unseen ngram should make entropy and perplexity infinite
    untrained = [("<s>", "a"), ("a", "c"), ("c", "d"), ("d", "</s>")]

    assert math.isinf(mle_bigram_model.entropy(untrained))
    assert math.isinf(mle_bigram_model.perplexity(untrained))


def test_mle_bigram_entropy_perplexity_unigrams(mle_bigram_model):
    # word = score, log score
    # <s>   = 0.1429, -2.8074
    # a     = 0.1429, -2.8074
    # c     = 0.0714, -3.8073
    # UNK   = 0.2143, -2.2224
    # d     = 0.1429, -2.8074
    # c     = 0.0714, -3.8073
    # </s>  = 0.1429, -2.8074
    # TOTAL logscores = -21.6243
    # - AVG logscores = 3.0095
    H = 3.0095
    perplexity = 8.0529

    text = [("<s>",), ("a",), ("c",), ("-",), ("d",), ("c",), ("</s>",)]

    assert pytest.approx(mle_bigram_model.entropy(text), 1e-4) == H
    assert pytest.approx(mle_bigram_model.perplexity(text), 1e-4) == perplexity


@pytest.fixture
def mle_trigram_model(trigram_training_data, vocabulary):
    model = MLE(order=3, vocabulary=vocabulary)
    model.fit(trigram_training_data)
    return model


@pytest.mark.parametrize(
    "word, context, expected_score",
    [
        # count(d | b, c) = 1
        # count(b, c) = 1
        ("d", ("b", "c"), 1),
        # count(d | c) = 1
        # count(c) = 1
        ("d", ["c"], 1),
        # total number of tokens is 18, of which "a" occurred 2 times
        ("a", None, 2.0 / 18),
        # in vocabulary but unseen
        ("z", None, 0),
        # out of vocabulary should use "UNK" score
        ("y", None, 3.0 / 18),
    ],
)
def test_mle_trigram_scores(mle_trigram_model, word, context, expected_score):
    assert pytest.approx(mle_trigram_model.score(word, context), 1e-4) == expected_score


@pytest.fixture
def lidstone_bigram_model(bigram_training_data, vocabulary):
    model = Lidstone(0.1, order=2, vocabulary=vocabulary)
    model.fit(bigram_training_data)
    return model


@pytest.mark.parametrize(
    "word, context, expected_score",
    [
        # count(d | c) = 1
        # *count(d | c) = 1.1
        # Count(w | c for w in vocab) = 1
        # *Count(w | c for w in vocab) = 1.8
        ("d", ["c"], 1.1 / 1.8),
        # Total unigrams: 14
        # Vocab size: 8
        # Denominator: 14 + 0.8 = 14.8
        # count("a") = 2
        # *count("a") = 2.1
        ("a", None, 2.1 / 14.8),
        # in vocabulary but unseen
        # count("z") = 0
        # *count("z") = 0.1
        ("z", None, 0.1 / 14.8),
        # out of vocabulary should use "UNK" score
        # count("<UNK>") = 3
        # *count("<UNK>") = 3.1
        ("y", None, 3.1 / 14.8),
    ],
)
def test_lidstone_bigram_score(lidstone_bigram_model, word, context, expected_score):
    assert (
        pytest.approx(lidstone_bigram_model.score(word, context), 1e-4)
        == expected_score
    )


def test_lidstone_entropy_perplexity(lidstone_bigram_model):
    text = [
        ("<s>", "a"),
        ("a", "c"),
        ("c", "<UNK>"),
        ("<UNK>", "d"),
        ("d", "c"),
        ("c", "</s>"),
    ]
    # Unlike MLE this should be able to handle completely novel ngrams
    # Ngram = score, log score
    # <s>, a    = 0.3929, -1.3479
    # a, c      = 0.0357, -4.8074
    # c, UNK    = 0.0(5), -4.1699
    # UNK, d    = 0.0263,  -5.2479
    # d, c      = 0.0357, -4.8074
    # c, </s>   = 0.0(5), -4.1699
    # TOTAL logscore: −24.5504
    # - AVG logscore: 4.0917
    H = 4.0917
    perplexity = 17.0504
    assert pytest.approx(lidstone_bigram_model.entropy(text), 1e-4) == H
    assert pytest.approx(lidstone_bigram_model.perplexity(text), 1e-4) == perplexity


@pytest.fixture
def lidstone_trigram_model(trigram_training_data, vocabulary):
    model = Lidstone(0.1, order=3, vocabulary=vocabulary)
    model.fit(trigram_training_data)
    return model


@pytest.mark.parametrize(
    "word, context, expected_score",
    [
        # Logic behind this is the same as for bigram model
        ("d", ["c"], 1.1 / 1.8),
        # if we choose a word that hasn't appeared after (b, c)
        ("e", ["c"], 0.1 / 1.8),
        # Trigram score now
        ("d", ["b", "c"], 1.1 / 1.8),
        ("e", ["b", "c"], 0.1 / 1.8),
    ],
)
def test_lidstone_trigram_score(lidstone_trigram_model, word, context, expected_score):
    assert (
        pytest.approx(lidstone_trigram_model.score(word, context), 1e-4)
        == expected_score
    )


@pytest.fixture
def laplace_bigram_model(bigram_training_data, vocabulary):
    model = Laplace(2, vocabulary=vocabulary)
    model.fit(bigram_training_data)
    return model


@pytest.mark.parametrize(
    "word, context, expected_score",
    [
        # basic sanity-check:
        # count(d | c) = 1
        # *count(d | c) = 2
        # Count(w | c for w in vocab) = 1
        # *Count(w | c for w in vocab) = 9
        ("d", ["c"], 2.0 / 9),
        # Total unigrams: 14
        # Vocab size: 8
        # Denominator: 14 + 8 = 22
        # count("a") = 2
        # *count("a") = 3
        ("a", None, 3.0 / 22),
        # in vocabulary but unseen
        # count("z") = 0
        # *count("z") = 1
        ("z", None, 1.0 / 22),
        # out of vocabulary should use "UNK" score
        # count("<UNK>") = 3
        # *count("<UNK>") = 4
        ("y", None, 4.0 / 22),
    ],
)
def test_laplace_bigram_score(laplace_bigram_model, word, context, expected_score):
    assert (
        pytest.approx(laplace_bigram_model.score(word, context), 1e-4) == expected_score
    )


def test_laplace_bigram_entropy_perplexity(laplace_bigram_model):
    text = [
        ("<s>", "a"),
        ("a", "c"),
        ("c", "<UNK>"),
        ("<UNK>", "d"),
        ("d", "c"),
        ("c", "</s>"),
    ]
    # Unlike MLE this should be able to handle completely novel ngrams
    # Ngram = score, log score
    # <s>, a    = 0.2, -2.3219
    # a, c      = 0.1, -3.3219
    # c, UNK    = 0.(1), -3.1699
    # UNK, d    = 0.(09), 3.4594
    # d, c      = 0.1 -3.3219
    # c, </s>   = 0.(1), -3.1699
    # Total logscores: −18.7651
    # - AVG logscores: 3.1275
    H = 3.1275
    perplexity = 8.7393
    assert pytest.approx(laplace_bigram_model.entropy(text), 1e-4) == H
    assert pytest.approx(laplace_bigram_model.perplexity(text), 1e-4) == perplexity


def test_laplace_gamma(laplace_bigram_model):
    assert laplace_bigram_model.gamma == 1


@pytest.fixture
def wittenbell_trigram_model(trigram_training_data, vocabulary):
    model = WittenBellInterpolated(3, vocabulary=vocabulary)
    model.fit(trigram_training_data)
    return model


@pytest.mark.parametrize(
    "word, context, expected_score",
    [
        # For unigram scores by default revert to regular MLE
        # Total unigrams: 18
        # Vocab Size = 7
        # count('c'): 1
        ("c", None, 1.0 / 18),
        # in vocabulary but unseen
        # count("z") = 0
        ("z", None, 0 / 18),
        # out of vocabulary should use "UNK" score
        # count("<UNK>") = 3
        ("y", None, 3.0 / 18),
        # 2 words follow b and b occurred a total of 2 times
        # gamma(['b']) = 2 / (2 + 2) = 0.5
        # mle.score('c', ['b']) = 0.5
        # mle('c') = 1 / 18 = 0.055
        # (1 - gamma) * mle + gamma * mle('c') ~= 0.27 + 0.055
        ("c", ["b"], (1 - 0.5) * 0.5 + 0.5 * 1 / 18),
        # building on that, let's try 'a b c' as the trigram
        # 1 word follows 'a b' and 'a b' occurred 1 time
        # gamma(['a', 'b']) = 1 / (1 + 1) = 0.5
        # mle("c", ["a", "b"]) = 1
        ("c", ["a", "b"], (1 - 0.5) + 0.5 * ((1 - 0.5) * 0.5 + 0.5 * 1 / 18)),
        # P(c|zb)
        # The ngram 'zbc' was not seen, so we use P(c|b). See issue #2332.
        ("c", ["z", "b"], ((1 - 0.5) * 0.5 + 0.5 * 1 / 18)),
    ],
)
def test_wittenbell_trigram_score(
    wittenbell_trigram_model, word, context, expected_score
):
    assert (
        pytest.approx(wittenbell_trigram_model.score(word, context), 1e-4)
        == expected_score
    )


###############################################################################
#                              Notation Explained                             #
###############################################################################
# For all subsequent calculations we use the following notation:
# 1. '*': Placeholder for any word/character. E.g. '*b' stands for
#    all bigrams that end in 'b'. '*b*' stands for all trigrams that
#    contain 'b' in the middle.
# 1. count(ngram): Count all instances (tokens) of an ngram.
# 1. unique(ngram): Count unique instances (types) of an ngram.


@pytest.fixture
def kneserney_trigram_model(trigram_training_data, vocabulary):
    model = KneserNeyInterpolated(order=3, discount=0.75, vocabulary=vocabulary)
    model.fit(trigram_training_data)
    return model


@pytest.mark.parametrize(
    "word, context, expected_score",
    [
        # P(c) = count('*c') / unique('**')
        #      = 1 / 14
        ("c", None, 1.0 / 14),
        # P(z) = count('*z') / unique('**')
        #      = 0 / 14
        # 'z' is in the vocabulary, but it was not seen during training.
        ("z", None, 0.0 / 14),
        # P(y)
        # Out of vocabulary should use "UNK" score.
        # P(y) = P(UNK) = count('*UNK') / unique('**')
        ("y", None, 3 / 14),
        # We start with P(c|b)
        # P(c|b) = alpha('bc') + gamma('b') * P(c)
        # alpha('bc') = max(unique('*bc') - discount, 0) / unique('*b*')
        #             = max(1 - 0.75, 0) / 2
        #             = 0.125
        # gamma('b')  = discount * unique('b*') / unique('*b*')
        #             = (0.75 * 2) / 2
        #             = 0.75
        ("c", ["b"], (0.125 + 0.75 * (1 / 14))),
        # Building on that, let's try P(c|ab).
        # P(c|ab) = alpha('abc') + gamma('ab') * P(c|b)
        # alpha('abc') = max(count('abc') - discount, 0) / count('ab*')
        #              = max(1 - 0.75, 0) / 1
        #              = 0.25
        # gamma('ab')  = (discount * unique('ab*')) / count('ab*')
        #              = 0.75 * 1 / 1
        ("c", ["a", "b"], 0.25 + 0.75 * (0.125 + 0.75 * (1 / 14))),
        # P(c|zb)
        # The ngram 'zbc' was not seen, so we use P(c|b). See issue #2332.
        ("c", ["z", "b"], (0.125 + 0.75 * (1 / 14))),
    ],
)
def test_kneserney_trigram_score(
    kneserney_trigram_model, word, context, expected_score
):
    assert (
        pytest.approx(kneserney_trigram_model.score(word, context), 1e-4)
        == expected_score
    )


@pytest.fixture
def absolute_discounting_trigram_model(trigram_training_data, vocabulary):
    model = AbsoluteDiscountingInterpolated(order=3, vocabulary=vocabulary)
    model.fit(trigram_training_data)
    return model


@pytest.mark.parametrize(
    "word, context, expected_score",
    [
        # For unigram scores revert to uniform
        # P(c) = count('c') / count('**')
        ("c", None, 1.0 / 18),
        # in vocabulary but unseen
        # count('z') = 0
        ("z", None, 0.0 / 18),
        # out of vocabulary should use "UNK" score
        # count('<UNK>') = 3
        ("y", None, 3 / 18),
        # P(c|b) = alpha('bc') + gamma('b') * P(c)
        # alpha('bc') = max(count('bc') - discount, 0) / count('b*')
        #             = max(1 - 0.75, 0) / 2
        #             = 0.125
        # gamma('b')  = discount * unique('b*') / count('b*')
        #             = (0.75 * 2) / 2
        #             = 0.75
        ("c", ["b"], (0.125 + 0.75 * (2 / 2) * (1 / 18))),
        # Building on that, let's try P(c|ab).
        # P(c|ab) = alpha('abc') + gamma('ab') * P(c|b)
        # alpha('abc') = max(count('abc') - discount, 0) / count('ab*')
        #              = max(1 - 0.75, 0) / 1
        #              = 0.25
        # gamma('ab')  = (discount * unique('ab*')) / count('ab*')
        #              = 0.75 * 1 / 1
        ("c", ["a", "b"], 0.25 + 0.75 * (0.125 + 0.75 * (2 / 2) * (1 / 18))),
        # P(c|zb)
        # The ngram 'zbc' was not seen, so we use P(c|b). See issue #2332.
        ("c", ["z", "b"], (0.125 + 0.75 * (2 / 2) * (1 / 18))),
    ],
)
def test_absolute_discounting_trigram_score(
    absolute_discounting_trigram_model, word, context, expected_score
):
    assert (
        pytest.approx(absolute_discounting_trigram_model.score(word, context), 1e-4)
        == expected_score
    )


@pytest.fixture
def stupid_backoff_trigram_model(trigram_training_data, vocabulary):
    model = StupidBackoff(order=3, vocabulary=vocabulary)
    model.fit(trigram_training_data)
    return model


@pytest.mark.parametrize(
    "word, context, expected_score",
    [
        # For unigram scores revert to uniform
        # total bigrams = 18
        ("c", None, 1.0 / 18),
        # in vocabulary but unseen
        # bigrams ending with z = 0
        ("z", None, 0.0 / 18),
        # out of vocabulary should use "UNK" score
        # count('<UNK>'): 3
        ("y", None, 3 / 18),
        # c follows 1 time out of 2 after b
        ("c", ["b"], 1 / 2),
        # c always follows ab
        ("c", ["a", "b"], 1 / 1),
        # The ngram 'z b c' was not seen, so we backoff to
        # the score of the ngram 'b c' * smoothing factor
        ("c", ["z", "b"], (0.4 * (1 / 2))),
    ],
)
def test_stupid_backoff_trigram_score(
    stupid_backoff_trigram_model, word, context, expected_score
):
    assert (
        pytest.approx(stupid_backoff_trigram_model.score(word, context), 1e-4)
        == expected_score
    )


###############################################################################
#               Probability Distributions Should Sum up to Unity              #
###############################################################################


@pytest.fixture(scope="session")
def kneserney_bigram_model(bigram_training_data, vocabulary):
    model = KneserNeyInterpolated(order=2, vocabulary=vocabulary)
    model.fit(bigram_training_data)
    return model


@pytest.mark.parametrize(
    "model_fixture",
    [
        "mle_bigram_model",
        "mle_trigram_model",
        "lidstone_bigram_model",
        "laplace_bigram_model",
        "wittenbell_trigram_model",
        "absolute_discounting_trigram_model",
        "kneserney_bigram_model",
        pytest.param(
            "stupid_backoff_trigram_model",
            marks=pytest.mark.xfail(
                reason="Stupid Backoff is not a valid distribution"
            ),
        ),
    ],
)
@pytest.mark.parametrize(
    "context",
    [("a",), ("c",), ("<s>",), ("b",), ("<UNK>",), ("d",), ("e",), ("r",), ("w",)],
    ids=itemgetter(0),
)
def test_sums_to_1(model_fixture, context, request):
    model = request.getfixturevalue(model_fixture)
    scores_for_context = sum(model.score(w, context) for w in model.vocab)
    assert pytest.approx(scores_for_context, 1e-7) == 1.0


###############################################################################
#                               Generating Text                               #
###############################################################################


def test_generate_one_no_context(mle_trigram_model):
    assert mle_trigram_model.generate(random_seed=3) == "<UNK>"


def test_generate_one_from_limiting_context(mle_trigram_model):
    # We don't need random_seed for contexts with only one continuation
    assert mle_trigram_model.generate(text_seed=["c"]) == "d"
    assert mle_trigram_model.generate(text_seed=["b", "c"]) == "d"
    assert mle_trigram_model.generate(text_seed=["a", "c"]) == "d"


def test_generate_one_from_varied_context(mle_trigram_model):
    # When context doesn't limit our options enough, seed the random choice
    assert mle_trigram_model.generate(text_seed=("a", "<s>"), random_seed=2) == "a"


def test_generate_cycle(mle_trigram_model):
    # Add a cycle to the model: bd -> b, db -> d
    more_training_text = [padded_everygrams(mle_trigram_model.order, list("bdbdbd"))]

    mle_trigram_model.fit(more_training_text)
    # Test that we can escape the cycle
    assert mle_trigram_model.generate(7, text_seed=("b", "d"), random_seed=5) == [
        "b",
        "d",
        "b",
        "d",
        "b",
        "d",
        "</s>",
    ]


def test_generate_with_text_seed(mle_trigram_model):
    assert mle_trigram_model.generate(5, text_seed=("<s>", "e"), random_seed=3) == [
        "<UNK>",
        "a",
        "d",
        "b",
        "<UNK>",
    ]


def test_generate_oov_text_seed(mle_trigram_model):
    assert mle_trigram_model.generate(
        text_seed=("aliens",), random_seed=3
    ) == mle_trigram_model.generate(text_seed=("<UNK>",), random_seed=3)


def test_generate_None_text_seed(mle_trigram_model):
    # should crash with type error when we try to look it up in vocabulary
    with pytest.raises(TypeError):
        mle_trigram_model.generate(text_seed=(None,))

    # This will work
    assert mle_trigram_model.generate(
        text_seed=None, random_seed=3
    ) == mle_trigram_model.generate(random_seed=3)

# === NexusCore/openenv\Lib\site-packages\jedi\inference\value\instance.py ===
from abc import abstractproperty

from parso.tree import search_ancestor

from jedi import debug
from jedi import settings
from jedi.inference import compiled
from jedi.inference.compiled.value import CompiledValueFilter
from jedi.inference.helpers import values_from_qualified_names, is_big_annoying_library
from jedi.inference.filters import AbstractFilter, AnonymousFunctionExecutionFilter
from jedi.inference.names import ValueName, TreeNameDefinition, ParamName, \
    NameWrapper
from jedi.inference.base_value import Value, NO_VALUES, ValueSet, \
    iterator_to_value_set, ValueWrapper
from jedi.inference.lazy_value import LazyKnownValue, LazyKnownValues
from jedi.inference.cache import inference_state_method_cache
from jedi.inference.arguments import ValuesArguments, TreeArgumentsWrapper
from jedi.inference.value.function import \
    FunctionValue, FunctionMixin, OverloadedFunctionValue, \
    BaseFunctionExecutionContext, FunctionExecutionContext, FunctionNameInClass
from jedi.inference.value.klass import ClassFilter
from jedi.inference.value.dynamic_arrays import get_dynamic_array_instance
from jedi.parser_utils import function_is_staticmethod, function_is_classmethod


class InstanceExecutedParamName(ParamName):
    def __init__(self, instance, function_value, tree_name):
        super().__init__(
            function_value, tree_name, arguments=None)
        self._instance = instance

    def infer(self):
        return ValueSet([self._instance])

    def matches_signature(self):
        return True


class AnonymousMethodExecutionFilter(AnonymousFunctionExecutionFilter):
    def __init__(self, instance, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._instance = instance

    def _convert_param(self, param, name):
        if param.position_index == 0:
            if function_is_classmethod(self._function_value.tree_node):
                return InstanceExecutedParamName(
                    self._instance.py__class__(),
                    self._function_value,
                    name
                )
            elif not function_is_staticmethod(self._function_value.tree_node):
                return InstanceExecutedParamName(
                    self._instance,
                    self._function_value,
                    name
                )
        return super()._convert_param(param, name)


class AnonymousMethodExecutionContext(BaseFunctionExecutionContext):
    def __init__(self, instance, value):
        super().__init__(value)
        self.instance = instance

    def get_filters(self, until_position=None, origin_scope=None):
        yield AnonymousMethodExecutionFilter(
            self.instance, self, self._value,
            until_position=until_position,
            origin_scope=origin_scope,
        )

    def get_param_names(self):
        param_names = list(self._value.get_param_names())
        # set the self name
        param_names[0] = InstanceExecutedParamName(
            self.instance,
            self._value,
            param_names[0].tree_name
        )
        return param_names


class MethodExecutionContext(FunctionExecutionContext):
    def __init__(self, instance, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = instance


class AbstractInstanceValue(Value):
    api_type = 'instance'

    def __init__(self, inference_state, parent_context, class_value):
        super().__init__(inference_state, parent_context)
        # Generated instances are classes that are just generated by self
        # (No arguments) used.
        self.class_value = class_value

    def is_instance(self):
        return True

    def get_qualified_names(self):
        return self.class_value.get_qualified_names()

    def get_annotated_class_object(self):
        return self.class_value  # This is the default.

    def py__class__(self):
        return self.class_value

    def py__bool__(self):
        # Signalize that we don't know about the bool type.
        return None

    @abstractproperty
    def name(self):
        raise NotImplementedError

    def get_signatures(self):
        call_funcs = self.py__getattribute__('__call__').py__get__(self, self.class_value)
        return [s.bind(self) for s in call_funcs.get_signatures()]

    def get_function_slot_names(self, name):
        # Python classes don't look at the dictionary of the instance when
        # looking up `__call__`. This is something that has to do with Python's
        # internal slot system (note: not __slots__, but C slots).
        for filter in self.get_filters(include_self_names=False):
            names = filter.get(name)
            if names:
                return names
        return []

    def execute_function_slots(self, names, *inferred_args):
        return ValueSet.from_sets(
            name.infer().execute_with_values(*inferred_args)
            for name in names
        )

    def get_type_hint(self, add_class_info=True):
        return self.py__name__()

    def py__getitem__(self, index_value_set, contextualized_node):
        names = self.get_function_slot_names('__getitem__')
        if not names:
            return super().py__getitem__(
                index_value_set,
                contextualized_node,
            )

        args = ValuesArguments([index_value_set])
        return ValueSet.from_sets(name.infer().execute(args) for name in names)

    def py__iter__(self, contextualized_node=None):
        iter_slot_names = self.get_function_slot_names('__iter__')
        if not iter_slot_names:
            return super().py__iter__(contextualized_node)

        def iterate():
            for generator in self.execute_function_slots(iter_slot_names):
                yield from generator.py__next__(contextualized_node)
        return iterate()

    def __repr__(self):
        return "<%s of %s>" % (self.__class__.__name__, self.class_value)


class CompiledInstance(AbstractInstanceValue):
    # This is not really a compiled class, it's just an instance from a
    # compiled class.
    def __init__(self, inference_state, parent_context, class_value, arguments):
        super().__init__(inference_state, parent_context, class_value)
        self._arguments = arguments

    def get_filters(self, origin_scope=None, include_self_names=True):
        class_value = self.get_annotated_class_object()
        class_filters = class_value.get_filters(
            origin_scope=origin_scope,
            is_instance=True,
        )
        for f in class_filters:
            yield CompiledInstanceClassFilter(self, f)

    @property
    def name(self):
        return compiled.CompiledValueName(self, self.class_value.name.string_name)

    def is_stub(self):
        return False


class _BaseTreeInstance(AbstractInstanceValue):
    @property
    def array_type(self):
        name = self.class_value.py__name__()
        if name in ['list', 'set', 'dict'] \
                and self.parent_context.get_root_context().is_builtins_module():
            return name
        return None

    @property
    def name(self):
        return ValueName(self, self.class_value.name.tree_name)

    def get_filters(self, origin_scope=None, include_self_names=True):
        class_value = self.get_annotated_class_object()
        if include_self_names:
            for cls in class_value.py__mro__():
                if not cls.is_compiled():
                    # In this case we're excluding compiled objects that are
                    # not fake objects. It doesn't make sense for normal
                    # compiled objects to search for self variables.
                    yield SelfAttributeFilter(self, class_value, cls.as_context(), origin_scope)

        class_filters = class_value.get_filters(
            origin_scope=origin_scope,
            is_instance=True,
        )
        for f in class_filters:
            if isinstance(f, ClassFilter):
                yield InstanceClassFilter(self, f)
            elif isinstance(f, CompiledValueFilter):
                yield CompiledInstanceClassFilter(self, f)
            else:
                # Propably from the metaclass.
                yield f

    @inference_state_method_cache()
    def create_instance_context(self, class_context, node):
        new = node
        while True:
            func_node = new
            new = search_ancestor(new, 'funcdef', 'classdef')
            if class_context.tree_node is new:
                func = FunctionValue.from_context(class_context, func_node)
                bound_method = BoundMethod(self, class_context, func)
                if func_node.name.value == '__init__':
                    context = bound_method.as_context(self._arguments)
                else:
                    context = bound_method.as_context()
                break
        return context.create_context(node)

    def py__getattribute__alternatives(self, string_name):
        '''
        Since nothing was inferred, now check the __getattr__ and
        __getattribute__ methods. Stubs don't need to be checked, because
        they don't contain any logic.
        '''
        if self.is_stub():
            return NO_VALUES

        name = compiled.create_simple_object(self.inference_state, string_name)

        # This is a little bit special. `__getattribute__` is in Python
        # executed before `__getattr__`. But: I know no use case, where
        # this could be practical and where Jedi would return wrong types.
        # If you ever find something, let me know!
        # We are inversing this, because a hand-crafted `__getattribute__`
        # could still call another hand-crafted `__getattr__`, but not the
        # other way around.
        if is_big_annoying_library(self.parent_context):
            return NO_VALUES
        names = (self.get_function_slot_names('__getattr__')
                 or self.get_function_slot_names('__getattribute__'))
        return self.execute_function_slots(names, name)

    def py__next__(self, contextualized_node=None):
        name = u'__next__'
        next_slot_names = self.get_function_slot_names(name)
        if next_slot_names:
            yield LazyKnownValues(
                self.execute_function_slots(next_slot_names)
            )
        else:
            debug.warning('Instance has no __next__ function in %s.', self)

    def py__call__(self, arguments):
        names = self.get_function_slot_names('__call__')
        if not names:
            # Means the Instance is not callable.
            return super().py__call__(arguments)

        return ValueSet.from_sets(name.infer().execute(arguments) for name in names)

    def py__get__(self, instance, class_value):
        """
        obj may be None.
        """
        # Arguments in __get__ descriptors are obj, class.
        # `method` is the new parent of the array, don't know if that's good.
        for cls in self.class_value.py__mro__():
            result = cls.py__get__on_class(self, instance, class_value)
            if result is not NotImplemented:
                return result

        names = self.get_function_slot_names('__get__')
        if names:
            if instance is None:
                instance = compiled.builtin_from_name(self.inference_state, 'None')
            return self.execute_function_slots(names, instance, class_value)
        else:
            return ValueSet([self])


class TreeInstance(_BaseTreeInstance):
    def __init__(self, inference_state, parent_context, class_value, arguments):
        # I don't think that dynamic append lookups should happen here. That
        # sounds more like something that should go to py__iter__.
        if class_value.py__name__() in ['list', 'set'] \
                and parent_context.get_root_context().is_builtins_module():
            # compare the module path with the builtin name.
            if settings.dynamic_array_additions:
                arguments = get_dynamic_array_instance(self, arguments)

        super().__init__(inference_state, parent_context, class_value)
        self._arguments = arguments
        self.tree_node = class_value.tree_node

    # This can recurse, if the initialization of the class includes a reference
    # to itself.
    @inference_state_method_cache(default=None)
    def _get_annotated_class_object(self):
        from jedi.inference.gradual.annotation import py__annotations__, \
            infer_type_vars_for_execution

        args = InstanceArguments(self, self._arguments)
        for signature in self.class_value.py__getattribute__('__init__').get_signatures():
            # Just take the first result, it should always be one, because we
            # control the typeshed code.
            funcdef = signature.value.tree_node
            if funcdef is None or funcdef.type != 'funcdef' \
                    or not signature.matches_signature(args):
                # First check if the signature even matches, if not we don't
                # need to infer anything.
                continue
            bound_method = BoundMethod(self, self.class_value.as_context(), signature.value)
            all_annotations = py__annotations__(funcdef)
            type_var_dict = infer_type_vars_for_execution(bound_method, args, all_annotations)
            if type_var_dict:
                defined, = self.class_value.define_generics(
                    infer_type_vars_for_execution(signature.value, args, all_annotations),
                )
                debug.dbg('Inferred instance value as %s', defined, color='BLUE')
                return defined
        return None

    def get_annotated_class_object(self):
        return self._get_annotated_class_object() or self.class_value

    def get_key_values(self):
        values = NO_VALUES
        if self.array_type == 'dict':
            for i, (key, instance) in enumerate(self._arguments.unpack()):
                if key is None and i == 0:
                    values |= ValueSet.from_sets(
                        v.get_key_values()
                        for v in instance.infer()
                        if v.array_type == 'dict'
                    )
                if key:
                    values |= ValueSet([compiled.create_simple_object(
                        self.inference_state,
                        key,
                    )])

        return values

    def py__simple_getitem__(self, index):
        if self.array_type == 'dict':
            # Logic for dict({'foo': bar}) and dict(foo=bar)
            # reversed, because:
            # >>> dict({'a': 1}, a=3)
            # {'a': 3}
            # TODO tuple initializations
            # >>> dict([('a', 4)])
            # {'a': 4}
            for key, lazy_context in reversed(list(self._arguments.unpack())):
                if key is None:
                    values = ValueSet.from_sets(
                        dct_value.py__simple_getitem__(index)
                        for dct_value in lazy_context.infer()
                        if dct_value.array_type == 'dict'
                    )
                    if values:
                        return values
                else:
                    if key == index:
                        return lazy_context.infer()
        return super().py__simple_getitem__(index)

    def __repr__(self):
        return "<%s of %s(%s)>" % (self.__class__.__name__, self.class_value,
                                   self._arguments)


class AnonymousInstance(_BaseTreeInstance):
    _arguments = None


class CompiledInstanceName(NameWrapper):
    @iterator_to_value_set
    def infer(self):
        for result_value in self._wrapped_name.infer():
            if result_value.api_type == 'function':
                yield CompiledBoundMethod(result_value)
            else:
                yield result_value


class CompiledInstanceClassFilter(AbstractFilter):
    def __init__(self, instance, f):
        self._instance = instance
        self._class_filter = f

    def get(self, name):
        return self._convert(self._class_filter.get(name))

    def values(self):
        return self._convert(self._class_filter.values())

    def _convert(self, names):
        return [CompiledInstanceName(n) for n in names]


class BoundMethod(FunctionMixin, ValueWrapper):
    def __init__(self, instance, class_context, function):
        super().__init__(function)
        self.instance = instance
        self._class_context = class_context

    def is_bound_method(self):
        return True

    @property
    def name(self):
        return FunctionNameInClass(
            self._class_context,
            super().name
        )

    def py__class__(self):
        c, = values_from_qualified_names(self.inference_state, 'types', 'MethodType')
        return c

    def _get_arguments(self, arguments):
        assert arguments is not None
        return InstanceArguments(self.instance, arguments)

    def _as_context(self, arguments=None):
        if arguments is None:
            return AnonymousMethodExecutionContext(self.instance, self)

        arguments = self._get_arguments(arguments)
        return MethodExecutionContext(self.instance, self, arguments)

    def py__call__(self, arguments):
        if isinstance(self._wrapped_value, OverloadedFunctionValue):
            return self._wrapped_value.py__call__(self._get_arguments(arguments))

        function_execution = self.as_context(arguments)
        return function_execution.infer()

    def get_signature_functions(self):
        return [
            BoundMethod(self.instance, self._class_context, f)
            for f in self._wrapped_value.get_signature_functions()
        ]

    def get_signatures(self):
        return [sig.bind(self) for sig in super().get_signatures()]

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self._wrapped_value)


class CompiledBoundMethod(ValueWrapper):
    def is_bound_method(self):
        return True

    def get_signatures(self):
        return [sig.bind(self) for sig in self._wrapped_value.get_signatures()]


class SelfName(TreeNameDefinition):
    """
    This name calculates the parent_context lazily.
    """
    def __init__(self, instance, class_context, tree_name):
        self._instance = instance
        self.class_context = class_context
        self.tree_name = tree_name

    @property
    def parent_context(self):
        return self._instance.create_instance_context(self.class_context, self.tree_name)

    def get_defining_qualified_value(self):
        return self._instance

    def infer(self):
        stmt = search_ancestor(self.tree_name, 'expr_stmt')
        if stmt is not None:
            if stmt.children[1].type == "annassign":
                from jedi.inference.gradual.annotation import infer_annotation
                values = infer_annotation(
                    self.parent_context, stmt.children[1].children[1]
                ).execute_annotation()
                if values:
                    return values
        return super().infer()


class LazyInstanceClassName(NameWrapper):
    def __init__(self, instance, class_member_name):
        super().__init__(class_member_name)
        self._instance = instance

    @iterator_to_value_set
    def infer(self):
        for result_value in self._wrapped_name.infer():
            yield from result_value.py__get__(self._instance, self._instance.py__class__())

    def get_signatures(self):
        return self.infer().get_signatures()

    def get_defining_qualified_value(self):
        return self._instance


class InstanceClassFilter(AbstractFilter):
    """
    This filter is special in that it uses the class filter and wraps the
    resulting names in LazyInstanceClassName. The idea is that the class name
    filtering can be very flexible and always be reflected in instances.
    """
    def __init__(self, instance, class_filter):
        self._instance = instance
        self._class_filter = class_filter

    def get(self, name):
        return self._convert(self._class_filter.get(name))

    def values(self):
        return self._convert(self._class_filter.values())

    def _convert(self, names):
        return [
            LazyInstanceClassName(self._instance, n)
            for n in names
        ]

    def __repr__(self):
        return '<%s for %s>' % (self.__class__.__name__, self._class_filter)


class SelfAttributeFilter(ClassFilter):
    """
    This class basically filters all the use cases where `self.*` was assigned.
    """
    def __init__(self, instance, instance_class, node_context, origin_scope):
        super().__init__(
            class_value=instance_class,
            node_context=node_context,
            origin_scope=origin_scope,
            is_instance=True,
        )
        self._instance = instance

    def _filter(self, names):
        start, end = self._parser_scope.start_pos, self._parser_scope.end_pos
        names = [n for n in names if start < n.start_pos < end]
        return self._filter_self_names(names)

    def _filter_self_names(self, names):
        for name in names:
            trailer = name.parent
            if trailer.type == 'trailer' \
                    and len(trailer.parent.children) == 2 \
                    and trailer.children[0] == '.':
                if name.is_definition() and self._access_possible(name):
                    # TODO filter non-self assignments instead of this bad
                    #      filter.
                    if self._is_in_right_scope(trailer.parent.children[0], name):
                        yield name

    def _is_in_right_scope(self, self_name, name):
        self_context = self._node_context.create_context(self_name)
        names = self_context.goto(self_name, position=self_name.start_pos)
        return any(
            n.api_type == 'param'
            and n.tree_name.get_definition().position_index == 0
            and n.parent_context.tree_node is self._parser_scope
            for n in names
        )

    def _convert_names(self, names):
        return [SelfName(self._instance, self._node_context, name) for name in names]

    def _check_flows(self, names):
        return names


class InstanceArguments(TreeArgumentsWrapper):
    def __init__(self, instance, arguments):
        super().__init__(arguments)
        self.instance = instance

    def unpack(self, func=None):
        yield None, LazyKnownValue(self.instance)
        yield from self._wrapped_arguments.unpack(func)

# === NexusCore/openenv\Lib\site-packages\fontTools\pens\pointPen.py ===
"""
=========
PointPens
=========

Where **SegmentPens** have an intuitive approach to drawing
(if you're familiar with postscript anyway), the **PointPen**
is geared towards accessing all the data in the contours of
the glyph. A PointPen has a very simple interface, it just
steps through all the points in a call from glyph.drawPoints().
This allows the caller to provide more data for each point.
For instance, whether or not a point is smooth, and its name.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from fontTools.misc.loggingTools import LogMixin
from fontTools.misc.transform import DecomposedTransform, Identity
from fontTools.pens.basePen import AbstractPen, MissingComponentError, PenError

__all__ = [
    "AbstractPointPen",
    "BasePointToSegmentPen",
    "PointToSegmentPen",
    "SegmentToPointPen",
    "GuessSmoothPointPen",
    "ReverseContourPointPen",
]

# Some type aliases to make it easier below
Point = Tuple[float, float]
PointName = Optional[str]
# [(pt, smooth, name, kwargs)]
SegmentPointList = List[Tuple[Optional[Point], bool, PointName, Any]]
SegmentType = Optional[str]
SegmentList = List[Tuple[SegmentType, SegmentPointList]]


class AbstractPointPen:
    """Baseclass for all PointPens."""

    def beginPath(self, identifier: Optional[str] = None, **kwargs: Any) -> None:
        """Start a new sub path."""
        raise NotImplementedError

    def endPath(self) -> None:
        """End the current sub path."""
        raise NotImplementedError

    def addPoint(
        self,
        pt: Tuple[float, float],
        segmentType: Optional[str] = None,
        smooth: bool = False,
        name: Optional[str] = None,
        identifier: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Add a point to the current sub path."""
        raise NotImplementedError

    def addComponent(
        self,
        baseGlyphName: str,
        transformation: Tuple[float, float, float, float, float, float],
        identifier: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Add a sub glyph."""
        raise NotImplementedError

    def addVarComponent(
        self,
        glyphName: str,
        transformation: DecomposedTransform,
        location: Dict[str, float],
        identifier: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Add a VarComponent sub glyph. The 'transformation' argument
        must be a DecomposedTransform from the fontTools.misc.transform module,
        and the 'location' argument must be a dictionary mapping axis tags
        to their locations.
        """
        # ttGlyphSet decomposes for us
        raise AttributeError


class BasePointToSegmentPen(AbstractPointPen):
    """
    Base class for retrieving the outline in a segment-oriented
    way. The PointPen protocol is simple yet also a little tricky,
    so when you need an outline presented as segments but you have
    as points, do use this base implementation as it properly takes
    care of all the edge cases.
    """

    def __init__(self) -> None:
        self.currentPath = None

    def beginPath(self, identifier=None, **kwargs):
        if self.currentPath is not None:
            raise PenError("Path already begun.")
        self.currentPath = []

    def _flushContour(self, segments: SegmentList) -> None:
        """Override this method.

        It will be called for each non-empty sub path with a list
        of segments: the 'segments' argument.

        The segments list contains tuples of length 2:
                (segmentType, points)

        segmentType is one of "move", "line", "curve" or "qcurve".
        "move" may only occur as the first segment, and it signifies
        an OPEN path. A CLOSED path does NOT start with a "move", in
        fact it will not contain a "move" at ALL.

        The 'points' field in the 2-tuple is a list of point info
        tuples. The list has 1 or more items, a point tuple has
        four items:
                (point, smooth, name, kwargs)
        'point' is an (x, y) coordinate pair.

        For a closed path, the initial moveTo point is defined as
        the last point of the last segment.

        The 'points' list of "move" and "line" segments always contains
        exactly one point tuple.
        """
        raise NotImplementedError

    def endPath(self) -> None:
        if self.currentPath is None:
            raise PenError("Path not begun.")
        points = self.currentPath
        self.currentPath = None
        if not points:
            return
        if len(points) == 1:
            # Not much more we can do than output a single move segment.
            pt, segmentType, smooth, name, kwargs = points[0]
            segments: SegmentList = [("move", [(pt, smooth, name, kwargs)])]
            self._flushContour(segments)
            return
        segments = []
        if points[0][1] == "move":
            # It's an open contour, insert a "move" segment for the first
            # point and remove that first point from the point list.
            pt, segmentType, smooth, name, kwargs = points[0]
            segments.append(("move", [(pt, smooth, name, kwargs)]))
            points.pop(0)
        else:
            # It's a closed contour. Locate the first on-curve point, and
            # rotate the point list so that it _ends_ with an on-curve
            # point.
            firstOnCurve = None
            for i in range(len(points)):
                segmentType = points[i][1]
                if segmentType is not None:
                    firstOnCurve = i
                    break
            if firstOnCurve is None:
                # Special case for quadratics: a contour with no on-curve
                # points. Add a "None" point. (See also the Pen protocol's
                # qCurveTo() method and fontTools.pens.basePen.py.)
                points.append((None, "qcurve", None, None, None))
            else:
                points = points[firstOnCurve + 1 :] + points[: firstOnCurve + 1]

        currentSegment: SegmentPointList = []
        for pt, segmentType, smooth, name, kwargs in points:
            currentSegment.append((pt, smooth, name, kwargs))
            if segmentType is None:
                continue
            segments.append((segmentType, currentSegment))
            currentSegment = []

        self._flushContour(segments)

    def addPoint(
        self, pt, segmentType=None, smooth=False, name=None, identifier=None, **kwargs
    ):
        if self.currentPath is None:
            raise PenError("Path not begun")
        self.currentPath.append((pt, segmentType, smooth, name, kwargs))


class PointToSegmentPen(BasePointToSegmentPen):
    """
    Adapter class that converts the PointPen protocol to the
    (Segment)Pen protocol.

    NOTE: The segment pen does not support and will drop point names, identifiers
    and kwargs.
    """

    def __init__(self, segmentPen, outputImpliedClosingLine: bool = False) -> None:
        BasePointToSegmentPen.__init__(self)
        self.pen = segmentPen
        self.outputImpliedClosingLine = outputImpliedClosingLine

    def _flushContour(self, segments):
        if not segments:
            raise PenError("Must have at least one segment.")
        pen = self.pen
        if segments[0][0] == "move":
            # It's an open path.
            closed = False
            points = segments[0][1]
            if len(points) != 1:
                raise PenError(f"Illegal move segment point count: {len(points)}")
            movePt, _, _, _ = points[0]
            del segments[0]
        else:
            # It's a closed path, do a moveTo to the last
            # point of the last segment.
            closed = True
            segmentType, points = segments[-1]
            movePt, _, _, _ = points[-1]
        if movePt is None:
            # quad special case: a contour with no on-curve points contains
            # one "qcurve" segment that ends with a point that's None. We
            # must not output a moveTo() in that case.
            pass
        else:
            pen.moveTo(movePt)
        outputImpliedClosingLine = self.outputImpliedClosingLine
        nSegments = len(segments)
        lastPt = movePt
        for i in range(nSegments):
            segmentType, points = segments[i]
            points = [pt for pt, _, _, _ in points]
            if segmentType == "line":
                if len(points) != 1:
                    raise PenError(f"Illegal line segment point count: {len(points)}")
                pt = points[0]
                # For closed contours, a 'lineTo' is always implied from the last oncurve
                # point to the starting point, thus we can omit it when the last and
                # starting point don't overlap.
                # However, when the last oncurve point is a "line" segment and has same
                # coordinates as the starting point of a closed contour, we need to output
                # the closing 'lineTo' explicitly (regardless of the value of the
                # 'outputImpliedClosingLine' option) in order to disambiguate this case from
                # the implied closing 'lineTo', otherwise the duplicate point would be lost.
                # See https://github.com/googlefonts/fontmake/issues/572.
                if (
                    i + 1 != nSegments
                    or outputImpliedClosingLine
                    or not closed
                    or pt == lastPt
                ):
                    pen.lineTo(pt)
                    lastPt = pt
            elif segmentType == "curve":
                pen.curveTo(*points)
                lastPt = points[-1]
            elif segmentType == "qcurve":
                pen.qCurveTo(*points)
                lastPt = points[-1]
            else:
                raise PenError(f"Illegal segmentType: {segmentType}")
        if closed:
            pen.closePath()
        else:
            pen.endPath()

    def addComponent(self, glyphName, transform, identifier=None, **kwargs):
        del identifier  # unused
        del kwargs  # unused
        self.pen.addComponent(glyphName, transform)


class SegmentToPointPen(AbstractPen):
    """
    Adapter class that converts the (Segment)Pen protocol to the
    PointPen protocol.
    """

    def __init__(self, pointPen, guessSmooth=True) -> None:
        if guessSmooth:
            self.pen = GuessSmoothPointPen(pointPen)
        else:
            self.pen = pointPen
        self.contour: Optional[List[Tuple[Point, SegmentType]]] = None

    def _flushContour(self) -> None:
        pen = self.pen
        pen.beginPath()
        for pt, segmentType in self.contour:
            pen.addPoint(pt, segmentType=segmentType)
        pen.endPath()

    def moveTo(self, pt):
        self.contour = []
        self.contour.append((pt, "move"))

    def lineTo(self, pt):
        if self.contour is None:
            raise PenError("Contour missing required initial moveTo")
        self.contour.append((pt, "line"))

    def curveTo(self, *pts):
        if not pts:
            raise TypeError("Must pass in at least one point")
        if self.contour is None:
            raise PenError("Contour missing required initial moveTo")
        for pt in pts[:-1]:
            self.contour.append((pt, None))
        self.contour.append((pts[-1], "curve"))

    def qCurveTo(self, *pts):
        if not pts:
            raise TypeError("Must pass in at least one point")
        if pts[-1] is None:
            self.contour = []
        else:
            if self.contour is None:
                raise PenError("Contour missing required initial moveTo")
        for pt in pts[:-1]:
            self.contour.append((pt, None))
        if pts[-1] is not None:
            self.contour.append((pts[-1], "qcurve"))

    def closePath(self):
        if self.contour is None:
            raise PenError("Contour missing required initial moveTo")
        if len(self.contour) > 1 and self.contour[0][0] == self.contour[-1][0]:
            self.contour[0] = self.contour[-1]
            del self.contour[-1]
        else:
            # There's an implied line at the end, replace "move" with "line"
            # for the first point
            pt, tp = self.contour[0]
            if tp == "move":
                self.contour[0] = pt, "line"
        self._flushContour()
        self.contour = None

    def endPath(self):
        if self.contour is None:
            raise PenError("Contour missing required initial moveTo")
        self._flushContour()
        self.contour = None

    def addComponent(self, glyphName, transform):
        if self.contour is not None:
            raise PenError("Components must be added before or after contours")
        self.pen.addComponent(glyphName, transform)


class GuessSmoothPointPen(AbstractPointPen):
    """
    Filtering PointPen that tries to determine whether an on-curve point
    should be "smooth", ie. that it's a "tangent" point or a "curve" point.
    """

    def __init__(self, outPen, error=0.05):
        self._outPen = outPen
        self._error = error
        self._points = None

    def _flushContour(self):
        if self._points is None:
            raise PenError("Path not begun")
        points = self._points
        nPoints = len(points)
        if not nPoints:
            return
        if points[0][1] == "move":
            # Open path.
            indices = range(1, nPoints - 1)
        elif nPoints > 1:
            # Closed path. To avoid having to mod the contour index, we
            # simply abuse Python's negative index feature, and start at -1
            indices = range(-1, nPoints - 1)
        else:
            # closed path containing 1 point (!), ignore.
            indices = []
        for i in indices:
            pt, segmentType, _, name, kwargs = points[i]
            if segmentType is None:
                continue
            prev = i - 1
            next = i + 1
            if points[prev][1] is not None and points[next][1] is not None:
                continue
            # At least one of our neighbors is an off-curve point
            pt = points[i][0]
            prevPt = points[prev][0]
            nextPt = points[next][0]
            if pt != prevPt and pt != nextPt:
                dx1, dy1 = pt[0] - prevPt[0], pt[1] - prevPt[1]
                dx2, dy2 = nextPt[0] - pt[0], nextPt[1] - pt[1]
                a1 = math.atan2(dy1, dx1)
                a2 = math.atan2(dy2, dx2)
                if abs(a1 - a2) < self._error:
                    points[i] = pt, segmentType, True, name, kwargs

        for pt, segmentType, smooth, name, kwargs in points:
            self._outPen.addPoint(pt, segmentType, smooth, name, **kwargs)

    def beginPath(self, identifier=None, **kwargs):
        if self._points is not None:
            raise PenError("Path already begun")
        self._points = []
        if identifier is not None:
            kwargs["identifier"] = identifier
        self._outPen.beginPath(**kwargs)

    def endPath(self):
        self._flushContour()
        self._outPen.endPath()
        self._points = None

    def addPoint(
        self, pt, segmentType=None, smooth=False, name=None, identifier=None, **kwargs
    ):
        if self._points is None:
            raise PenError("Path not begun")
        if identifier is not None:
            kwargs["identifier"] = identifier
        self._points.append((pt, segmentType, False, name, kwargs))

    def addComponent(self, glyphName, transformation, identifier=None, **kwargs):
        if self._points is not None:
            raise PenError("Components must be added before or after contours")
        if identifier is not None:
            kwargs["identifier"] = identifier
        self._outPen.addComponent(glyphName, transformation, **kwargs)

    def addVarComponent(
        self, glyphName, transformation, location, identifier=None, **kwargs
    ):
        if self._points is not None:
            raise PenError("VarComponents must be added before or after contours")
        if identifier is not None:
            kwargs["identifier"] = identifier
        self._outPen.addVarComponent(glyphName, transformation, location, **kwargs)


class ReverseContourPointPen(AbstractPointPen):
    """
    This is a PointPen that passes outline data to another PointPen, but
    reversing the winding direction of all contours. Components are simply
    passed through unchanged.

    Closed contours are reversed in such a way that the first point remains
    the first point.
    """

    def __init__(self, outputPointPen):
        self.pen = outputPointPen
        # a place to store the points for the current sub path
        self.currentContour = None

    def _flushContour(self):
        pen = self.pen
        contour = self.currentContour
        if not contour:
            pen.beginPath(identifier=self.currentContourIdentifier)
            pen.endPath()
            return

        closed = contour[0][1] != "move"
        if not closed:
            lastSegmentType = "move"
        else:
            # Remove the first point and insert it at the end. When
            # the list of points gets reversed, this point will then
            # again be at the start. In other words, the following
            # will hold:
            #   for N in range(len(originalContour)):
            #       originalContour[N] == reversedContour[-N]
            contour.append(contour.pop(0))
            # Find the first on-curve point.
            firstOnCurve = None
            for i in range(len(contour)):
                if contour[i][1] is not None:
                    firstOnCurve = i
                    break
            if firstOnCurve is None:
                # There are no on-curve points, be basically have to
                # do nothing but contour.reverse().
                lastSegmentType = None
            else:
                lastSegmentType = contour[firstOnCurve][1]

        contour.reverse()
        if not closed:
            # Open paths must start with a move, so we simply dump
            # all off-curve points leading up to the first on-curve.
            while contour[0][1] is None:
                contour.pop(0)
        pen.beginPath(identifier=self.currentContourIdentifier)
        for pt, nextSegmentType, smooth, name, kwargs in contour:
            if nextSegmentType is not None:
                segmentType = lastSegmentType
                lastSegmentType = nextSegmentType
            else:
                segmentType = None
            pen.addPoint(
                pt, segmentType=segmentType, smooth=smooth, name=name, **kwargs
            )
        pen.endPath()

    def beginPath(self, identifier=None, **kwargs):
        if self.currentContour is not None:
            raise PenError("Path already begun")
        self.currentContour = []
        self.currentContourIdentifier = identifier
        self.onCurve = []

    def endPath(self):
        if self.currentContour is None:
            raise PenError("Path not begun")
        self._flushContour()
        self.currentContour = None

    def addPoint(
        self, pt, segmentType=None, smooth=False, name=None, identifier=None, **kwargs
    ):
        if self.currentContour is None:
            raise PenError("Path not begun")
        if identifier is not None:
            kwargs["identifier"] = identifier
        self.currentContour.append((pt, segmentType, smooth, name, kwargs))

    def addComponent(self, glyphName, transform, identifier=None, **kwargs):
        if self.currentContour is not None:
            raise PenError("Components must be added before or after contours")
        self.pen.addComponent(glyphName, transform, identifier=identifier, **kwargs)


class DecomposingPointPen(LogMixin, AbstractPointPen):
    """Implements a 'addComponent' method that decomposes components
    (i.e. draws them onto self as simple contours).
    It can also be used as a mixin class (e.g. see DecomposingRecordingPointPen).

    You must override beginPath, addPoint, endPath. You may
    additionally override addVarComponent and addComponent.

    By default a warning message is logged when a base glyph is missing;
    set the class variable ``skipMissingComponents`` to False if you want
    all instances of a sub-class to raise a :class:`MissingComponentError`
    exception by default.
    """

    skipMissingComponents = True
    # alias error for convenience
    MissingComponentError = MissingComponentError

    def __init__(
        self,
        glyphSet,
        *args,
        skipMissingComponents=None,
        reverseFlipped=False,
        **kwargs,
    ):
        """Takes a 'glyphSet' argument (dict), in which the glyphs that are referenced
        as components are looked up by their name.

        If the optional 'reverseFlipped' argument is True, components whose transformation
        matrix has a negative determinant will be decomposed with a reversed path direction
        to compensate for the flip.

        The optional 'skipMissingComponents' argument can be set to True/False to
        override the homonymous class attribute for a given pen instance.
        """
        super().__init__(*args, **kwargs)
        self.glyphSet = glyphSet
        self.skipMissingComponents = (
            self.__class__.skipMissingComponents
            if skipMissingComponents is None
            else skipMissingComponents
        )
        self.reverseFlipped = reverseFlipped

    def addComponent(self, baseGlyphName, transformation, identifier=None, **kwargs):
        """Transform the points of the base glyph and draw it onto self.

        The `identifier` parameter and any extra kwargs are ignored.
        """
        from fontTools.pens.transformPen import TransformPointPen

        try:
            glyph = self.glyphSet[baseGlyphName]
        except KeyError:
            if not self.skipMissingComponents:
                raise MissingComponentError(baseGlyphName)
            self.log.warning(
                "glyph '%s' is missing from glyphSet; skipped" % baseGlyphName
            )
        else:
            pen = self
            if transformation != Identity:
                pen = TransformPointPen(pen, transformation)
            if self.reverseFlipped:
                # if the transformation has a negative determinant, it will
                # reverse the contour direction of the component
                a, b, c, d = transformation[:4]
                if a * d - b * c < 0:
                    pen = ReverseContourPointPen(pen)
            glyph.drawPoints(pen)

# === NexusCore/openenv\Lib\site-packages\trio\_threads.py ===
from __future__ import annotations

import contextlib
import contextvars
import inspect
import queue as stdlib_queue
import threading
from itertools import count
from typing import TYPE_CHECKING, Generic, TypeVar

import attrs
import outcome
from attrs import define
from sniffio import current_async_library_cvar

import trio

from ._core import (
    RunVar,
    TrioToken,
    checkpoint,
    disable_ki_protection,
    enable_ki_protection,
    start_thread_soon,
)
from ._sync import CapacityLimiter, Event
from ._util import coroutine_or_error

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Generator

    from typing_extensions import TypeVarTuple, Unpack

    from trio._core._traps import RaiseCancelT

    Ts = TypeVarTuple("Ts")

RetT = TypeVar("RetT")


class _ParentTaskData(threading.local):
    """Global due to Threading API, thread local storage for data related to the
    parent task of native Trio threads."""

    token: TrioToken
    abandon_on_cancel: bool
    cancel_register: list[RaiseCancelT | None]
    task_register: list[trio.lowlevel.Task | None]


PARENT_TASK_DATA = _ParentTaskData()

_limiter_local: RunVar[CapacityLimiter] = RunVar("limiter")
# I pulled this number out of the air; it isn't based on anything. Probably we
# should make some kind of measurements to pick a good value.
DEFAULT_LIMIT = 40
_thread_counter = count()


@define
class _ActiveThreadCount:
    count: int
    event: Event


_active_threads_local: RunVar[_ActiveThreadCount] = RunVar("active_threads")


@contextlib.contextmanager
def _track_active_thread() -> Generator[None, None, None]:
    try:
        active_threads_local = _active_threads_local.get()
    except LookupError:
        active_threads_local = _ActiveThreadCount(0, Event())
        _active_threads_local.set(active_threads_local)

    active_threads_local.count += 1
    try:
        yield
    finally:
        active_threads_local.count -= 1
        if active_threads_local.count == 0:
            active_threads_local.event.set()
            active_threads_local.event = Event()


async def wait_all_threads_completed() -> None:
    """Wait until no threads are still running tasks.

    This is intended to be used when testing code with trio.to_thread to
    make sure no tasks are still making progress in a thread. See the
    following code for a usage example::

        async def wait_all_settled():
            while True:
                await trio.testing.wait_all_threads_complete()
                await trio.testing.wait_all_tasks_blocked()
                if trio.testing.active_thread_count() == 0:
                    break
    """

    await checkpoint()

    try:
        active_threads_local = _active_threads_local.get()
    except LookupError:
        # If there would have been active threads, the
        # _active_threads_local would have been set
        return

    while active_threads_local.count != 0:
        await active_threads_local.event.wait()


def active_thread_count() -> int:
    """Returns the number of threads that are currently running a task

    See `trio.testing.wait_all_threads_completed`
    """
    try:
        return _active_threads_local.get().count
    except LookupError:
        return 0


def current_default_thread_limiter() -> CapacityLimiter:
    """Get the default `~trio.CapacityLimiter` used by
    `trio.to_thread.run_sync`.

    The most common reason to call this would be if you want to modify its
    :attr:`~trio.CapacityLimiter.total_tokens` attribute.

    """
    try:
        limiter = _limiter_local.get()
    except LookupError:
        limiter = CapacityLimiter(DEFAULT_LIMIT)
        _limiter_local.set(limiter)
    return limiter


# Eventually we might build this into a full-fledged deadlock-detection
# system; see https://github.com/python-trio/trio/issues/182
# But for now we just need an object to stand in for the thread, so we can
# keep track of who's holding the CapacityLimiter's token.
@attrs.frozen(eq=False, slots=False)
class ThreadPlaceholder:
    name: str


# Types for the to_thread_run_sync message loop
@attrs.frozen(eq=False, slots=False)
class Run(Generic[RetT]):  # type: ignore[explicit-any]
    afn: Callable[..., Awaitable[RetT]]  # type: ignore[explicit-any]
    args: tuple[object, ...]
    context: contextvars.Context = attrs.field(
        init=False,
        factory=contextvars.copy_context,
    )
    queue: stdlib_queue.SimpleQueue[outcome.Outcome[RetT]] = attrs.field(
        init=False,
        factory=stdlib_queue.SimpleQueue,
    )

    @disable_ki_protection
    async def unprotected_afn(self) -> RetT:
        coro = coroutine_or_error(self.afn, *self.args)
        return await coro

    async def run(self) -> None:
        # we use extra checkpoints to pick up and reset any context changes
        task = trio.lowlevel.current_task()
        old_context = task.context
        task.context = self.context.copy()
        await trio.lowlevel.cancel_shielded_checkpoint()
        result = await outcome.acapture(self.unprotected_afn)
        task.context = old_context
        await trio.lowlevel.cancel_shielded_checkpoint()
        self.queue.put_nowait(result)

    async def run_system(self) -> None:
        result = await outcome.acapture(self.unprotected_afn)
        self.queue.put_nowait(result)

    def run_in_host_task(self, token: TrioToken) -> None:
        task_register = PARENT_TASK_DATA.task_register

        def in_trio_thread() -> None:
            task = task_register[0]
            assert task is not None, "guaranteed by abandon_on_cancel semantics"
            trio.lowlevel.reschedule(task, outcome.Value(self))

        token.run_sync_soon(in_trio_thread)

    def run_in_system_nursery(self, token: TrioToken) -> None:
        def in_trio_thread() -> None:
            try:
                trio.lowlevel.spawn_system_task(
                    self.run_system,
                    name=self.afn,
                    context=self.context,
                )
            except RuntimeError:  # system nursery is closed
                self.queue.put_nowait(
                    outcome.Error(trio.RunFinishedError("system nursery is closed")),
                )

        token.run_sync_soon(in_trio_thread)


@attrs.frozen(eq=False, slots=False)
class RunSync(Generic[RetT]):  # type: ignore[explicit-any]
    fn: Callable[..., RetT]  # type: ignore[explicit-any]
    args: tuple[object, ...]
    context: contextvars.Context = attrs.field(
        init=False,
        factory=contextvars.copy_context,
    )
    queue: stdlib_queue.SimpleQueue[outcome.Outcome[RetT]] = attrs.field(
        init=False,
        factory=stdlib_queue.SimpleQueue,
    )

    @disable_ki_protection
    def unprotected_fn(self) -> RetT:
        ret = self.context.run(self.fn, *self.args)

        if inspect.iscoroutine(ret):
            # Manually close coroutine to avoid RuntimeWarnings
            ret.close()
            raise TypeError(
                "Trio expected a synchronous function, but {!r} appears to be "
                "asynchronous".format(getattr(self.fn, "__qualname__", self.fn)),
            )

        return ret

    def run_sync(self) -> None:
        result = outcome.capture(self.unprotected_fn)
        self.queue.put_nowait(result)

    def run_in_host_task(self, token: TrioToken) -> None:
        task_register = PARENT_TASK_DATA.task_register

        def in_trio_thread() -> None:
            task = task_register[0]
            assert task is not None, "guaranteed by abandon_on_cancel semantics"
            trio.lowlevel.reschedule(task, outcome.Value(self))

        token.run_sync_soon(in_trio_thread)

    def run_in_system_nursery(self, token: TrioToken) -> None:
        token.run_sync_soon(self.run_sync)


@enable_ki_protection
async def to_thread_run_sync(
    sync_fn: Callable[[Unpack[Ts]], RetT],
    *args: Unpack[Ts],
    thread_name: str | None = None,
    abandon_on_cancel: bool = False,
    limiter: CapacityLimiter | None = None,
) -> RetT:
    """Convert a blocking operation into an async operation using a thread.

    These two lines are equivalent::

        sync_fn(*args)
        await trio.to_thread.run_sync(sync_fn, *args)

    except that if ``sync_fn`` takes a long time, then the first line will
    block the Trio loop while it runs, while the second line allows other Trio
    tasks to continue working while ``sync_fn`` runs. This is accomplished by
    pushing the call to ``sync_fn(*args)`` off into a worker thread.

    From inside the worker thread, you can get back into Trio using the
    functions in `trio.from_thread`.

    Args:
      sync_fn: An arbitrary synchronous callable.
      *args: Positional arguments to pass to sync_fn. If you need keyword
          arguments, use :func:`functools.partial`.
      abandon_on_cancel (bool): Whether to abandon this thread upon
          cancellation of this operation. See discussion below.
      thread_name (str): Optional string to set the name of the thread.
          Will always set `threading.Thread.name`, but only set the os name
          if pthread.h is available (i.e. most POSIX installations).
          pthread names are limited to 15 characters, and can be read from
          ``/proc/<PID>/task/<SPID>/comm`` or with ``ps -eT``, among others.
          Defaults to ``{sync_fn.__name__|None} from {trio.lowlevel.current_task().name}``.
      limiter (None, or CapacityLimiter-like object):
          An object used to limit the number of simultaneous threads. Most
          commonly this will be a `~trio.CapacityLimiter`, but it could be
          anything providing compatible
          :meth:`~trio.CapacityLimiter.acquire_on_behalf_of` and
          :meth:`~trio.CapacityLimiter.release_on_behalf_of` methods. This
          function will call ``acquire_on_behalf_of`` before starting the
          thread, and ``release_on_behalf_of`` after the thread has finished.

          If None (the default), uses the default `~trio.CapacityLimiter`, as
          returned by :func:`current_default_thread_limiter`.

    **Cancellation handling**: Cancellation is a tricky issue here, because
    neither Python nor the operating systems it runs on provide any general
    mechanism for cancelling an arbitrary synchronous function running in a
    thread. This function will always check for cancellation on entry, before
    starting the thread. But once the thread is running, there are two ways it
    can handle being cancelled:

    * If ``abandon_on_cancel=False``, the function ignores the cancellation and
      keeps going, just like if we had called ``sync_fn`` synchronously. This
      is the default behavior.

    * If ``abandon_on_cancel=True``, then this function immediately raises
      `~trio.Cancelled`. In this case **the thread keeps running in
      background** – we just abandon it to do whatever it's going to do, and
      silently discard any return value or errors that it raises. Only use
      this if you know that the operation is safe and side-effect free. (For
      example: :func:`trio.socket.getaddrinfo` uses a thread with
      ``abandon_on_cancel=True``, because it doesn't really affect anything if a
      stray hostname lookup keeps running in the background.)

      The ``limiter`` is only released after the thread has *actually*
      finished – which in the case of cancellation may be some time after this
      function has returned. If :func:`trio.run` finishes before the thread
      does, then the limiter release method will never be called at all.

    .. warning::

       You should not use this function to call long-running CPU-bound
       functions! In addition to the usual GIL-related reasons why using
       threads for CPU-bound work is not very effective in Python, there is an
       additional problem: on CPython, `CPU-bound threads tend to "starve out"
       IO-bound threads <https://bugs.python.org/issue7946>`__, so using
       threads for CPU-bound work is likely to adversely affect the main
       thread running Trio. If you need to do this, you're better off using a
       worker process, or perhaps PyPy (which still has a GIL, but may do a
       better job of fairly allocating CPU time between threads).

    Returns:
      Whatever ``sync_fn(*args)`` returns.

    Raises:
      Exception: Whatever ``sync_fn(*args)`` raises.

    """
    await trio.lowlevel.checkpoint_if_cancelled()
    # raise early if abandon_on_cancel.__bool__ raises
    # and give a new name to ensure mypy knows it's never None
    abandon_bool = bool(abandon_on_cancel)
    if limiter is None:
        limiter = current_default_thread_limiter()

    # Holds a reference to the task that's blocked in this function waiting
    # for the result – or None if this function was cancelled and we should
    # discard the result.
    task_register: list[trio.lowlevel.Task | None] = [trio.lowlevel.current_task()]
    # Holds a reference to the raise_cancel function provided if a cancellation
    # is attempted against this task - or None if no such delivery has happened.
    cancel_register: list[RaiseCancelT | None] = [None]  # type: ignore[assignment]
    name = f"trio.to_thread.run_sync-{next(_thread_counter)}"
    placeholder = ThreadPlaceholder(name)

    # This function gets scheduled into the Trio run loop to deliver the
    # thread's result.
    def report_back_in_trio_thread_fn(result: outcome.Outcome[RetT]) -> None:
        def do_release_then_return_result() -> RetT:
            # release_on_behalf_of is an arbitrary user-defined method, so it
            # might raise an error. If it does, we want that error to
            # replace the regular return value, and if the regular return was
            # already an exception then we want them to chain.
            try:
                return result.unwrap()
            finally:
                limiter.release_on_behalf_of(placeholder)

        result = outcome.capture(do_release_then_return_result)
        if task_register[0] is not None:
            trio.lowlevel.reschedule(task_register[0], outcome.Value(result))

    current_trio_token = trio.lowlevel.current_trio_token()

    if thread_name is None:
        thread_name = f"{getattr(sync_fn, '__name__', None)} from {trio.lowlevel.current_task().name}"

    def worker_fn() -> RetT:
        PARENT_TASK_DATA.token = current_trio_token
        PARENT_TASK_DATA.abandon_on_cancel = abandon_bool
        PARENT_TASK_DATA.cancel_register = cancel_register
        PARENT_TASK_DATA.task_register = task_register
        try:
            ret = context.run(sync_fn, *args)

            if inspect.iscoroutine(ret):
                # Manually close coroutine to avoid RuntimeWarnings
                ret.close()
                raise TypeError(
                    "Trio expected a sync function, but {!r} appears to be "
                    "asynchronous".format(getattr(sync_fn, "__qualname__", sync_fn)),
                )

            return ret
        finally:
            del PARENT_TASK_DATA.token
            del PARENT_TASK_DATA.abandon_on_cancel
            del PARENT_TASK_DATA.cancel_register
            del PARENT_TASK_DATA.task_register

    context = contextvars.copy_context()
    # Trio doesn't use current_async_library_cvar, but if someone
    # else set it, it would now shine through since
    # sniffio.thread_local isn't set in the new thread. Make sure
    # the new thread sees that it's not running in async context.
    context.run(current_async_library_cvar.set, None)

    def deliver_worker_fn_result(result: outcome.Outcome[RetT]) -> None:
        # If the entire run finished, the task we're trying to contact is
        # certainly long gone -- it must have been cancelled and abandoned
        # us. Just ignore the error in this case.
        with contextlib.suppress(trio.RunFinishedError):
            current_trio_token.run_sync_soon(report_back_in_trio_thread_fn, result)

    await limiter.acquire_on_behalf_of(placeholder)
    with _track_active_thread():
        try:
            start_thread_soon(worker_fn, deliver_worker_fn_result, thread_name)
        except:
            limiter.release_on_behalf_of(placeholder)
            raise

        def abort(raise_cancel: RaiseCancelT) -> trio.lowlevel.Abort:
            # fill so from_thread_check_cancelled can raise
            cancel_register[0] = raise_cancel
            if abandon_bool:
                # empty so report_back_in_trio_thread_fn cannot reschedule
                task_register[0] = None
                return trio.lowlevel.Abort.SUCCEEDED
            else:
                return trio.lowlevel.Abort.FAILED

        while True:
            # wait_task_rescheduled return value cannot be typed
            msg_from_thread: outcome.Outcome[RetT] | Run[object] | RunSync[object] = (
                await trio.lowlevel.wait_task_rescheduled(abort)
            )
            if isinstance(msg_from_thread, outcome.Outcome):
                return msg_from_thread.unwrap()
            elif isinstance(msg_from_thread, Run):
                await msg_from_thread.run()
            elif isinstance(msg_from_thread, RunSync):
                msg_from_thread.run_sync()
            else:  # pragma: no cover, internal debugging guard TODO: use assert_never
                raise TypeError(
                    f"trio.to_thread.run_sync received unrecognized thread message {msg_from_thread!r}.",
                )
            del msg_from_thread


def from_thread_check_cancelled() -> None:
    """Raise `trio.Cancelled` if the associated Trio task entered a cancelled status.

     Only applicable to threads spawned by `trio.to_thread.run_sync`. Poll to allow
     ``abandon_on_cancel=False`` threads to raise :exc:`~trio.Cancelled` at a suitable
     place, or to end abandoned ``abandon_on_cancel=True`` threads sooner than they may
     otherwise.

    Raises:
        Cancelled: If the corresponding call to `trio.to_thread.run_sync` has had a
            delivery of cancellation attempted against it, regardless of the value of
            ``abandon_on_cancel`` supplied as an argument to it.
        RuntimeError: If this thread is not spawned from `trio.to_thread.run_sync`.

    .. note::

       To be precise, :func:`~trio.from_thread.check_cancelled` checks whether the task
       running :func:`trio.to_thread.run_sync` has ever been cancelled since the last
       time it was running a :func:`trio.from_thread.run` or :func:`trio.from_thread.run_sync`
       function. It may raise `trio.Cancelled` even if a cancellation occurred that was
       later hidden by a modification to `trio.CancelScope.shield` between the cancelled
       `~trio.CancelScope` and :func:`trio.to_thread.run_sync`. This differs from the
       behavior of normal Trio checkpoints, which raise `~trio.Cancelled` only if the
       cancellation is still active when the checkpoint executes. The distinction here is
       *exceedingly* unlikely to be relevant to your application, but we mention it
       for completeness.
    """
    try:
        raise_cancel = PARENT_TASK_DATA.cancel_register[0]
    except AttributeError:
        raise RuntimeError(
            "this thread wasn't created by Trio, can't check for cancellation",
        ) from None
    if raise_cancel is not None:
        raise_cancel()


def _send_message_to_trio(
    trio_token: TrioToken | None,
    message_to_trio: Run[RetT] | RunSync[RetT],
) -> RetT:
    """Shared logic of from_thread functions"""
    token_provided = trio_token is not None

    if not token_provided:
        try:
            trio_token = PARENT_TASK_DATA.token
        except AttributeError:
            raise RuntimeError(
                "this thread wasn't created by Trio, pass kwarg trio_token=...",
            ) from None
    elif not isinstance(trio_token, TrioToken):
        raise RuntimeError("Passed kwarg trio_token is not of type TrioToken")

    # Avoid deadlock by making sure we're not called from Trio thread
    try:
        trio.lowlevel.current_task()
    except RuntimeError:
        pass
    else:
        raise RuntimeError("this is a blocking function; call it from a thread")

    if token_provided or PARENT_TASK_DATA.abandon_on_cancel:
        message_to_trio.run_in_system_nursery(trio_token)
    else:
        message_to_trio.run_in_host_task(trio_token)

    return message_to_trio.queue.get().unwrap()


def from_thread_run(
    afn: Callable[[Unpack[Ts]], Awaitable[RetT]],
    *args: Unpack[Ts],
    trio_token: TrioToken | None = None,
) -> RetT:
    """Run the given async function in the parent Trio thread, blocking until it
    is complete.

    Returns:
      Whatever ``afn(*args)`` returns.

    Returns or raises whatever the given function returns or raises. It
    can also raise exceptions of its own:

    Raises:
        RunFinishedError: if the corresponding call to :func:`trio.run` has
            already completed, or if the run has started its final cleanup phase
            and can no longer spawn new system tasks.
        Cancelled: If the original call to :func:`trio.to_thread.run_sync` is cancelled
            (if *trio_token* is None) or the call to :func:`trio.run` completes
            (if *trio_token* is not None) while ``afn(*args)`` is running,
            then *afn* is likely to raise :exc:`trio.Cancelled`.
        RuntimeError: if you try calling this from inside the Trio thread,
            which would otherwise cause a deadlock, or if no ``trio_token`` was
            provided, and we can't infer one from context.
        TypeError: if ``afn`` is not an asynchronous function.

    **Locating a TrioToken**: There are two ways to specify which
    `trio.run` loop to reenter:

        - Spawn this thread from `trio.to_thread.run_sync`. Trio will
          automatically capture the relevant Trio token and use it
          to re-enter the same Trio task.
        - Pass a keyword argument, ``trio_token`` specifying a specific
          `trio.run` loop to re-enter. This is useful in case you have a
          "foreign" thread, spawned using some other framework, and still want
          to enter Trio, or if you want to use a new system task to call ``afn``,
          maybe to avoid the cancellation context of a corresponding
          `trio.to_thread.run_sync` task. You can get this token from
          :func:`trio.lowlevel.current_trio_token`.
    """
    return _send_message_to_trio(trio_token, Run(afn, args))


def from_thread_run_sync(
    fn: Callable[[Unpack[Ts]], RetT],
    *args: Unpack[Ts],
    trio_token: TrioToken | None = None,
) -> RetT:
    """Run the given sync function in the parent Trio thread, blocking until it
    is complete.

    Returns:
      Whatever ``fn(*args)`` returns.

    Returns or raises whatever the given function returns or raises. It
    can also raise exceptions of its own:

    Raises:
        RunFinishedError: if the corresponding call to `trio.run` has
            already completed.
        RuntimeError: if you try calling this from inside the Trio thread,
            which would otherwise cause a deadlock or if no ``trio_token`` was
            provided, and we can't infer one from context.
        TypeError: if ``fn`` is an async function.

    **Locating a TrioToken**: There are two ways to specify which
    `trio.run` loop to reenter:

        - Spawn this thread from `trio.to_thread.run_sync`. Trio will
          automatically capture the relevant Trio token and use it when you
          want to re-enter Trio.
        - Pass a keyword argument, ``trio_token`` specifying a specific
          `trio.run` loop to re-enter. This is useful in case you have a
          "foreign" thread, spawned using some other framework, and still want
          to enter Trio, or if you want to use a new system task to call ``fn``,
          maybe to avoid the cancellation context of a corresponding
          `trio.to_thread.run_sync` task.
    """
    return _send_message_to_trio(trio_token, RunSync(fn, args))

# === NexusCore/openenv\Lib\site-packages\IPython\extensions\deduperreload\deduperreload.py ===
from __future__ import annotations
import ast
import builtins
import contextlib
import itertools
import os
import platform
import sys
import textwrap
from types import ModuleType
from typing import TYPE_CHECKING, Any, Generator, Iterable, NamedTuple, cast

from IPython.extensions.deduperreload.deduperreload_patching import (
    DeduperReloaderPatchingMixin,
)

if TYPE_CHECKING:
    TDefinitionAst = (
        ast.FunctionDef
        | ast.AsyncFunctionDef
        | ast.Import
        | ast.ImportFrom
        | ast.Assign
        | ast.AnnAssign
    )


def get_module_file_name(module: ModuleType | str) -> str:
    """Returns the module's file path, or the empty string if it's inaccessible"""
    if (mod := sys.modules.get(module) if isinstance(module, str) else module) is None:
        return ""
    return getattr(mod, "__file__", "") or ""


def compare_ast(node1: ast.AST | list[ast.AST], node2: ast.AST | list[ast.AST]) -> bool:
    """Checks if node1 and node2 have identical AST structure/values, apart from some attributes"""
    if type(node1) is not type(node2):
        return False

    if isinstance(node1, ast.AST):
        for k, v in node1.__dict__.items():
            if k in (
                "lineno",
                "end_lineno",
                "col_offset",
                "end_col_offset",
                "ctx",
                "parent",
            ):
                continue
            if not hasattr(node2, k) or not compare_ast(v, getattr(node2, k)):
                return False
        return True

    elif isinstance(node1, list) and isinstance(  # type:ignore [redundant-expr]
        node2, list
    ):
        return len(node1) == len(node2) and all(
            compare_ast(n1, n2) for n1, n2 in zip(node1, node2)
        )
    else:
        return node1 == node2


class DependencyNode(NamedTuple):
    """
    Each node represents a function.
    qualified_name: string which represents the namespace/name of the function
    abstract_syntax_tree: subtree of the overall module which corresponds to this function

    qualified_name is of the structure: (namespace1, namespace2, ..., name)

    For example, foo() in the following would be represented as (A, B, foo):

    class A:
        class B:
            def foo():
                pass
    """

    qualified_name: tuple[str, ...]
    abstract_syntax_tree: ast.AST


class GatherResult(NamedTuple):
    import_defs: list[tuple[tuple[str, ...], ast.Import | ast.ImportFrom]] = []
    assign_defs: list[tuple[tuple[str, ...], ast.Assign | ast.AnnAssign]] = []
    function_defs: list[
        tuple[tuple[str, ...], ast.FunctionDef | ast.AsyncFunctionDef]
    ] = []
    classes: dict[str, ast.ClassDef] = {}
    unfixable: list[ast.AST] = []

    @classmethod
    def create(cls) -> GatherResult:
        return cls([], [], [], {}, [])

    def all_defs(self) -> Iterable[tuple[tuple[str, ...], TDefinitionAst]]:
        return itertools.chain(self.import_defs, self.assign_defs, self.function_defs)

    def inplace_merge(self, other: GatherResult) -> None:
        self.import_defs.extend(other.import_defs)
        self.assign_defs.extend(other.assign_defs)
        self.function_defs.extend(other.function_defs)
        self.classes.update(other.classes)
        self.unfixable.extend(other.unfixable)


class ConstexprDetector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.is_constexpr = True
        self._allow_builtins_exceptions = True

    @contextlib.contextmanager
    def disallow_builtins_exceptions(self) -> Generator[None, None, None]:
        prev_allow = self._allow_builtins_exceptions
        self._allow_builtins_exceptions = False
        try:
            yield
        finally:
            self._allow_builtins_exceptions = prev_allow

    def visit_Attribute(self, node: ast.Attribute) -> None:
        with self.disallow_builtins_exceptions():
            self.visit(node.value)

    def visit_Name(self, node: ast.Name) -> None:
        if self._allow_builtins_exceptions and hasattr(builtins, node.id):
            return
        self.is_constexpr = False

    def visit(self, node: ast.AST) -> None:
        if not self.is_constexpr:
            # can short-circuit if we've already detected that it's not a constexpr
            return
        super().visit(node)

    def __call__(self, node: ast.AST) -> bool:
        self.is_constexpr = True
        self.visit(node)
        return self.is_constexpr


class AutoreloadTree:
    """
    Recursive data structure to keep track of reloadable functions/methods. Each object corresponds to a specific scope level.
    children: classes inside given scope, maps class name to autoreload tree for that class's scope
    funcs_to_autoreload: list of function names that can be autoreloaded in given scope.
    new_nested_classes: Classes getting added in new autoreload cycle
    """

    def __init__(self) -> None:
        self.children: dict[str, AutoreloadTree] = {}
        self.defs_to_reload: list[tuple[tuple[str, ...], ast.AST]] = []
        self.defs_to_delete: set[str] = set()
        self.new_nested_classes: dict[str, ast.AST] = {}

    def traverse_prefixes(self, prefixes: list[str]) -> AutoreloadTree:
        """
        Return ref to the AutoreloadTree at the namespace specified by prefixes
        """
        cur = self
        for prefix in prefixes:
            if prefix not in cur.children:
                cur.children[prefix] = AutoreloadTree()
            cur = cur.children[prefix]
        return cur


class DeduperReloader(DeduperReloaderPatchingMixin):
    """
    This version of autoreload detects when we can leverage targeted recompilation of a subset of a module and patching
    existing function/method objects to reflect these changes.

    Detects what functions/methods can be reloaded by recursively comparing the old/new AST of module-level classes,
    module-level classes' methods, recursing through nested classes' methods. If other changes are made, original
    autoreload algorithm is called directly.
    """

    def __init__(self) -> None:
        self._to_autoreload: AutoreloadTree = AutoreloadTree()
        self.source_by_modname: dict[str, str] = {}
        self.dependency_graph: dict[tuple[str, ...], list[DependencyNode]] = {}
        self._enabled = True

    @property
    def enabled(self) -> bool:
        return self._enabled and platform.python_implementation() == "CPython"

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    def update_sources(self) -> None:
        """
        Update dictionary source_by_modname with current modules' source codes.
        """
        if not self.enabled:
            return
        for new_modname in sys.modules.keys() - self.source_by_modname.keys():
            new_module = sys.modules[new_modname]
            if (
                (fname := get_module_file_name(new_module))
                is None  # type:ignore [redundant-expr]
                or "site-packages" in fname
                or "dist-packages" in fname
                or not os.access(fname, os.R_OK)
            ):
                self.source_by_modname[new_modname] = ""
                continue
            with open(fname, "r") as f:
                try:
                    self.source_by_modname[new_modname] = f.read()
                except Exception:
                    self.source_by_modname[new_modname] = ""

    constexpr_detector = ConstexprDetector()

    @staticmethod
    def is_enum_subclass(node: ast.Module | ast.ClassDef) -> bool:
        if isinstance(node, ast.Module):
            return False
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == "Enum":
                return True
            elif (
                isinstance(base, ast.Attribute)
                and base.attr == "Enum"
                and isinstance(base.value, ast.Name)
                and base.value.id == "enum"
            ):
                return True
        return False

    @classmethod
    def is_constexpr_assign(
        cls, node: ast.AST, parent_node: ast.Module | ast.ClassDef
    ) -> bool:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)) or node.value is None:
            return False
        if cls.is_enum_subclass(parent_node):
            return False
        for target in node.targets if isinstance(node, ast.Assign) else [node.target]:
            if not isinstance(target, ast.Name):
                return False
        return cls.constexpr_detector(node.value)

    @classmethod
    def _gather_children(
        cls, body: list[ast.stmt], parent_node: ast.Module | ast.ClassDef
    ) -> GatherResult:
        """
        Given list of ast elements, return:
        1. dict mapping function names to their ASTs.
        2. dict mapping class names to their ASTs.
        3. list of any other ASTs.
        """
        result = GatherResult.create()
        for ast_node in body:
            ast_elt: ast.expr | ast.stmt = ast_node
            while isinstance(ast_elt, ast.Expr):
                ast_elt = ast_elt.value
            if isinstance(ast_elt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                result.function_defs.append(((ast_elt.name,), ast_elt))
            elif isinstance(ast_elt, (ast.Import, ast.ImportFrom)):
                result.import_defs.append(
                    (tuple(name.asname or name.name for name in ast_elt.names), ast_elt)
                )
            elif isinstance(ast_elt, ast.ClassDef):
                result.classes[ast_elt.name] = ast_elt
            elif isinstance(ast_elt, ast.If):
                result.unfixable.append(ast_elt.test)
                result.inplace_merge(cls._gather_children(ast_elt.body, parent_node))
                result.inplace_merge(cls._gather_children(ast_elt.orelse, parent_node))
            elif isinstance(ast_elt, (ast.AsyncWith, ast.With)):
                result.unfixable.extend(ast_elt.items)
                result.inplace_merge(cls._gather_children(ast_elt.body, parent_node))
            elif isinstance(ast_elt, ast.Try):
                result.inplace_merge(cls._gather_children(ast_elt.body, parent_node))
                result.inplace_merge(cls._gather_children(ast_elt.orelse, parent_node))
                result.inplace_merge(
                    cls._gather_children(ast_elt.finalbody, parent_node)
                )
                for handler in ast_elt.handlers:
                    if handler.type is not None:
                        result.unfixable.append(handler.type)
                    result.inplace_merge(
                        cls._gather_children(handler.body, parent_node)
                    )
            elif not isinstance(ast_elt, (ast.Ellipsis, ast.Pass)):
                if cls.is_constexpr_assign(ast_elt, parent_node):
                    assert isinstance(ast_elt, (ast.Assign, ast.AnnAssign))
                    targets = (
                        ast_elt.targets
                        if isinstance(ast_elt, ast.Assign)
                        else [ast_elt.target]
                    )
                    result.assign_defs.append(
                        (
                            tuple(cast(ast.Name, target).id for target in targets),
                            ast_elt,
                        )
                    )
                else:
                    result.unfixable.append(ast_elt)
        return result

    def detect_autoreload(
        self,
        old_node: ast.Module | ast.ClassDef,
        new_node: ast.Module | ast.ClassDef,
        prefixes: list[str] | None = None,
    ) -> bool:
        """
        Returns
        -------
        `True` if we can run our targeted autoreload algorithm safely.
        `False` if we should instead use IPython's original autoreload implementation.
        """
        if not self.enabled:
            return False
        prefixes = prefixes or []

        old_result = self._gather_children(old_node.body, old_node)
        new_result = self._gather_children(new_node.body, new_node)
        old_defs_by_name: dict[str, ast.AST] = {
            name: ast_def for names, ast_def in old_result.all_defs() for name in names
        }
        new_defs_by_name: dict[str, ast.AST] = {
            name: ast_def for names, ast_def in new_result.all_defs() for name in names
        }

        if not compare_ast(old_result.unfixable, new_result.unfixable):
            return False

        cur = self._to_autoreload.traverse_prefixes(prefixes)
        for names, new_ast_def in new_result.all_defs():
            names_to_reload = []
            for name in names:
                if new_defs_by_name[name] is not new_ast_def:
                    continue
                if name not in old_defs_by_name or not compare_ast(
                    new_ast_def, old_defs_by_name[name]
                ):
                    names_to_reload.append(name)
            if names_to_reload:
                cur.defs_to_reload.append((tuple(names), new_ast_def))
        cur.defs_to_delete |= set(old_defs_by_name.keys()) - set(
            new_defs_by_name.keys()
        )
        for name, new_ast_def_class in new_result.classes.items():
            if name not in old_result.classes:
                cur.new_nested_classes[name] = new_ast_def_class
            elif not compare_ast(
                new_ast_def_class, old_result.classes[name]
            ) and not self.detect_autoreload(
                old_result.classes[name], new_ast_def_class, prefixes + [name]
            ):
                return False
        return True

    def _check_dependents(self) -> bool:
        """
        If a decorator function is modified, we should similarly reload the functions which are decorated by this
        decorator. Iterate through the Dependency Graph to find such cases in the given AutoreloadTree.
        """
        for node in self._check_dependents_inner():
            self._add_node_to_autoreload_tree(node)
        return True

    def _add_node_to_autoreload_tree(self, node: DependencyNode) -> None:
        """
        Given a node of the dependency graph, add decorator dependencies to the autoreload tree.
        """
        if len(node.qualified_name) == 0:
            return
        cur = self._to_autoreload.traverse_prefixes(list(node.qualified_name[:-1]))
        if node.abstract_syntax_tree is not None:
            cur.defs_to_reload.append(
                ((node.qualified_name[-1],), node.abstract_syntax_tree)
            )

    def _check_dependents_inner(
        self, prefixes: list[str] | None = None
    ) -> list[DependencyNode]:
        prefixes = prefixes or []
        cur = self._to_autoreload.traverse_prefixes(prefixes)
        ans = []
        for (func_name, *_), _ in cur.defs_to_reload:
            node = tuple(prefixes + [func_name])
            ans.extend(self._gen_dependents(node))
        for class_name in cur.new_nested_classes:
            ans.extend(self._check_dependents_inner(prefixes + [class_name]))
        return ans

    def _gen_dependents(self, qualname: tuple[str, ...]) -> list[DependencyNode]:
        ans = []
        if qualname not in self.dependency_graph:
            return []
        for elt in self.dependency_graph[qualname]:
            ans.extend(self._gen_dependents(elt.qualified_name))
            ans.append(elt)
        return ans

    def _patch_namespace_inner(
        self, ns: ModuleType | type, prefixes: list[str] | None = None
    ) -> bool:
        """
        This function patches module functions and methods. Specifically, only objects with their name in
        self.to_autoreload will be considered for patching. If an object has been marked to be autoreloaded,
        new_source_code gets executed in the old version's global environment. Then, replace the old function's
        attributes with the new function's attributes.
        """
        prefixes = prefixes or []
        cur = self._to_autoreload.traverse_prefixes(prefixes)
        namespace_to_check = ns
        for prefix in prefixes:
            namespace_to_check = namespace_to_check.__dict__[prefix]
        for names, new_ast_def in cur.defs_to_reload:
            local_env: dict[str, Any] = {}
            if (
                isinstance(new_ast_def, (ast.FunctionDef, ast.AsyncFunctionDef))
                and (name := names[0]) in namespace_to_check.__dict__
            ):
                assert len(names) == 1
                to_patch_to = namespace_to_check.__dict__[name]
                if isinstance(to_patch_to, (staticmethod, classmethod)):
                    to_patch_to = to_patch_to.__func__
                # exec new source code using old function's (obj) globals environment.
                func_code = textwrap.dedent(ast.unparse(new_ast_def))
                if is_method := (len(prefixes) > 0):
                    func_code = "class __autoreload_class__:\n" + textwrap.indent(
                        func_code, "    "
                    )
                global_env = namespace_to_check.__dict__
                if hasattr(to_patch_to, "__globals__"):
                    global_env = to_patch_to.__globals__
                elif isinstance(to_patch_to, property):
                    if to_patch_to.fget is not None:
                        global_env = to_patch_to.fget.__globals__
                    elif to_patch_to.fset is not None:
                        global_env = to_patch_to.fset.__globals__
                    elif to_patch_to.fdel is not None:
                        global_env = to_patch_to.fdel.__globals__
                if not isinstance(global_env, dict):
                    global_env = dict(global_env)
                exec(func_code, global_env, local_env)  # type: ignore[arg-type]
                # local_env contains the function exec'd from  new version of function
                if is_method:
                    to_patch_from = getattr(local_env["__autoreload_class__"], name)
                else:
                    to_patch_from = local_env[name]
                if isinstance(to_patch_from, (staticmethod, classmethod)):
                    to_patch_from = to_patch_from.__func__
                if isinstance(to_patch_to, property) and isinstance(
                    to_patch_from, property
                ):
                    for attr in ("fget", "fset", "fdel"):
                        if (
                            getattr(to_patch_to, attr) is None
                            or getattr(to_patch_from, attr) is None
                        ):
                            self.try_patch_attr(to_patch_to, to_patch_from, attr)
                        else:
                            self.patch_function(
                                getattr(to_patch_to, attr),
                                getattr(to_patch_from, attr),
                                is_method,
                            )
                elif not isinstance(to_patch_to, property) and not isinstance(
                    to_patch_from, property
                ):
                    self.patch_function(to_patch_to, to_patch_from, is_method)
                else:
                    raise ValueError(
                        "adding or removing property decorations not supported"
                    )
            else:
                exec(
                    ast.unparse(new_ast_def),
                    ns.__dict__ | namespace_to_check.__dict__,
                    local_env,
                )
                for name in names:
                    setattr(namespace_to_check, name, local_env[name])
        cur.defs_to_reload.clear()
        for name in cur.defs_to_delete:
            try:
                delattr(namespace_to_check, name)
            except (AttributeError, TypeError, ValueError):
                # give up on deleting the attribute, let the stale one dangle
                pass
        cur.defs_to_delete.clear()
        for class_name, class_ast_node in cur.new_nested_classes.items():
            local_env_class: dict[str, Any] = {}
            exec(
                ast.unparse(class_ast_node),
                ns.__dict__ | namespace_to_check.__dict__,
                local_env_class,
            )
            setattr(namespace_to_check, class_name, local_env_class[class_name])
        cur.new_nested_classes.clear()
        for class_name in cur.children.keys():
            if not self._patch_namespace(ns, prefixes + [class_name]):
                return False
        cur.children.clear()
        return True

    def _patch_namespace(
        self, ns: ModuleType | type, prefixes: list[str] | None = None
    ) -> bool:
        """
        Wrapper for patching all elements in a namespace as specified by the to_autoreload member variable.
        Returns `true` if patching was successful, and `false` if unsuccessful.
        """
        try:
            return self._patch_namespace_inner(ns, prefixes=prefixes)
        except Exception:
            return False

    def maybe_reload_module(self, module: ModuleType) -> bool:
        """
        Uses Deduperreload to try to update a module.
        Returns `true` on success and `false` on failure.
        """
        if not self.enabled:
            return False
        if not (modname := getattr(module, "__name__", None)):
            return False
        if (fname := get_module_file_name(module)) is None:
            return False
        with open(fname, "r") as f:
            new_source_code = f.read()
        patched_flag = False
        if old_source_code := self.source_by_modname.get(modname):
            # get old/new module ast
            try:
                old_module_ast = ast.parse(old_source_code)
                new_module_ast = ast.parse(new_source_code)
            except Exception:
                return False
            # detect if we are able to use our autoreload algorithm
            ctx = contextlib.suppress()
            with ctx:
                self._build_dependency_graph(new_module_ast)
                if (
                    self.detect_autoreload(old_module_ast, new_module_ast)
                    and self._check_dependents()
                    and self._patch_namespace(module)
                ):
                    patched_flag = True

        self.source_by_modname[modname] = new_source_code
        self._to_autoreload = AutoreloadTree()
        return patched_flag

    def _separate_name(
        self,
        decorator: ast.Attribute | ast.Name | ast.Call | ast.expr,
        accept_calls: bool,
    ) -> list[str] | None:
        """
        Generates a qualified name for a given decorator by finding its relative namespace.
        """
        if isinstance(decorator, ast.Name):
            return [decorator.id]
        elif isinstance(decorator, ast.Call):
            if accept_calls:
                return self._separate_name(decorator.func, False)
            else:
                return None
        if not isinstance(decorator, ast.Attribute):
            return None
        if pref := self._separate_name(decorator.value, False):
            return pref + [decorator.attr]
        else:
            return None

    def _gather_dependents(
        self, body: list[ast.stmt], body_prefixes: list[str] | None = None
    ) -> bool:
        body_prefixes = body_prefixes or []
        for ast_node in body:
            ast_elt: ast.expr | ast.stmt = ast_node
            if isinstance(ast_elt, ast.ClassDef):
                self._gather_dependents(ast_elt.body, body_prefixes + [ast_elt.name])
                continue
            if not isinstance(ast_elt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            qualified_name = tuple(body_prefixes + [ast_elt.name])
            cur_dependency_node = DependencyNode(qualified_name, ast_elt)
            for decorator in ast_elt.decorator_list:
                decorator_path = self._separate_name(decorator, True)
                if not decorator_path:
                    continue
                decorator_path_tuple = tuple(decorator_path)
                self.dependency_graph.setdefault(decorator_path_tuple, []).append(
                    cur_dependency_node
                )
        return True

    def _build_dependency_graph(self, new_ast: ast.Module | ast.ClassDef) -> bool:
        """
        Wrapper function for generating dependency graph given some AST.
        Returns `true` on success. Returns `false` on failure.
        Currently, only returns `true` as we do not block on failure to build this graph.
        """
        return self._gather_dependents(new_ast.body)

# === NexusCore/openenv\Lib\site-packages\tornado\test\auth_test.py ===
# These tests do not currently do much to verify the correct implementation
# of the openid/oauth protocols, they just exercise the major code paths
# and ensure that it doesn't blow up (e.g. with unicode/bytes issues in
# python 3)

import unittest

from tornado.auth import (
    OpenIdMixin,
    OAuthMixin,
    OAuth2Mixin,
    GoogleOAuth2Mixin,
    FacebookGraphMixin,
    TwitterMixin,
)
from tornado.escape import json_decode
from tornado import gen
from tornado.httpclient import HTTPClientError
from tornado.httputil import url_concat
from tornado.log import app_log
from tornado.testing import AsyncHTTPTestCase, ExpectLog
from tornado.web import RequestHandler, Application, HTTPError

try:
    from unittest import mock
except ImportError:
    mock = None  # type: ignore


class OpenIdClientLoginHandler(RequestHandler, OpenIdMixin):
    def initialize(self, test):
        self._OPENID_ENDPOINT = test.get_url("/openid/server/authenticate")

    @gen.coroutine
    def get(self):
        if self.get_argument("openid.mode", None):
            user = yield self.get_authenticated_user(
                http_client=self.settings["http_client"]
            )
            if user is None:
                raise Exception("user is None")
            self.finish(user)
            return
        res = self.authenticate_redirect()  # type: ignore
        assert res is None


class OpenIdServerAuthenticateHandler(RequestHandler):
    def post(self):
        if self.get_argument("openid.mode") != "check_authentication":
            raise Exception("incorrect openid.mode %r")
        self.write("is_valid:true")


class OAuth1ClientLoginHandler(RequestHandler, OAuthMixin):
    def initialize(self, test, version):
        self._OAUTH_VERSION = version
        self._OAUTH_REQUEST_TOKEN_URL = test.get_url("/oauth1/server/request_token")
        self._OAUTH_AUTHORIZE_URL = test.get_url("/oauth1/server/authorize")
        self._OAUTH_ACCESS_TOKEN_URL = test.get_url("/oauth1/server/access_token")

    def _oauth_consumer_token(self):
        return dict(key="asdf", secret="qwer")

    @gen.coroutine
    def get(self):
        if self.get_argument("oauth_token", None):
            user = yield self.get_authenticated_user(
                http_client=self.settings["http_client"]
            )
            if user is None:
                raise Exception("user is None")
            self.finish(user)
            return
        yield self.authorize_redirect(http_client=self.settings["http_client"])

    @gen.coroutine
    def _oauth_get_user_future(self, access_token):
        if self.get_argument("fail_in_get_user", None):
            raise Exception("failing in get_user")
        if access_token != dict(key="uiop", secret="5678"):
            raise Exception("incorrect access token %r" % access_token)
        return dict(email="foo@example.com")


class OAuth1ClientLoginCoroutineHandler(OAuth1ClientLoginHandler):
    """Replaces OAuth1ClientLoginCoroutineHandler's get() with a coroutine."""

    @gen.coroutine
    def get(self):
        if self.get_argument("oauth_token", None):
            # Ensure that any exceptions are set on the returned Future,
            # not simply thrown into the surrounding StackContext.
            try:
                yield self.get_authenticated_user()
            except Exception as e:
                self.set_status(503)
                self.write("got exception: %s" % e)
        else:
            yield self.authorize_redirect()


class OAuth1ClientRequestParametersHandler(RequestHandler, OAuthMixin):
    def initialize(self, version):
        self._OAUTH_VERSION = version

    def _oauth_consumer_token(self):
        return dict(key="asdf", secret="qwer")

    def get(self):
        params = self._oauth_request_parameters(
            "http://www.example.com/api/asdf",
            dict(key="uiop", secret="5678"),
            parameters=dict(foo="bar"),
        )
        self.write(params)


class OAuth1ServerRequestTokenHandler(RequestHandler):
    def get(self):
        self.write("oauth_token=zxcv&oauth_token_secret=1234")


class OAuth1ServerAccessTokenHandler(RequestHandler):
    def get(self):
        self.write("oauth_token=uiop&oauth_token_secret=5678")


class OAuth2ClientLoginHandler(RequestHandler, OAuth2Mixin):
    def initialize(self, test):
        self._OAUTH_AUTHORIZE_URL = test.get_url("/oauth2/server/authorize")

    def get(self):
        res = self.authorize_redirect()  # type: ignore
        assert res is None


class FacebookClientLoginHandler(RequestHandler, FacebookGraphMixin):
    def initialize(self, test):
        self._OAUTH_AUTHORIZE_URL = test.get_url("/facebook/server/authorize")
        self._OAUTH_ACCESS_TOKEN_URL = test.get_url("/facebook/server/access_token")
        self._FACEBOOK_BASE_URL = test.get_url("/facebook/server")

    @gen.coroutine
    def get(self):
        if self.get_argument("code", None):
            user = yield self.get_authenticated_user(
                redirect_uri=self.request.full_url(),
                client_id=self.settings["facebook_api_key"],
                client_secret=self.settings["facebook_secret"],
                code=self.get_argument("code"),
            )
            self.write(user)
        else:
            self.authorize_redirect(
                redirect_uri=self.request.full_url(),
                client_id=self.settings["facebook_api_key"],
                extra_params={"scope": "read_stream,offline_access"},
            )


class FacebookServerAccessTokenHandler(RequestHandler):
    def get(self):
        self.write(dict(access_token="asdf", expires_in=3600))


class FacebookServerMeHandler(RequestHandler):
    def get(self):
        self.write("{}")


class TwitterClientHandler(RequestHandler, TwitterMixin):
    def initialize(self, test):
        self._OAUTH_REQUEST_TOKEN_URL = test.get_url("/oauth1/server/request_token")
        self._OAUTH_ACCESS_TOKEN_URL = test.get_url("/twitter/server/access_token")
        self._OAUTH_AUTHORIZE_URL = test.get_url("/oauth1/server/authorize")
        self._OAUTH_AUTHENTICATE_URL = test.get_url("/twitter/server/authenticate")
        self._TWITTER_BASE_URL = test.get_url("/twitter/api")

    def get_auth_http_client(self):
        return self.settings["http_client"]


class TwitterClientLoginHandler(TwitterClientHandler):
    @gen.coroutine
    def get(self):
        if self.get_argument("oauth_token", None):
            user = yield self.get_authenticated_user()
            if user is None:
                raise Exception("user is None")
            self.finish(user)
            return
        yield self.authorize_redirect()


class TwitterClientAuthenticateHandler(TwitterClientHandler):
    # Like TwitterClientLoginHandler, but uses authenticate_redirect
    # instead of authorize_redirect.
    @gen.coroutine
    def get(self):
        if self.get_argument("oauth_token", None):
            user = yield self.get_authenticated_user()
            if user is None:
                raise Exception("user is None")
            self.finish(user)
            return
        yield self.authenticate_redirect()


class TwitterClientLoginGenCoroutineHandler(TwitterClientHandler):
    @gen.coroutine
    def get(self):
        if self.get_argument("oauth_token", None):
            user = yield self.get_authenticated_user()
            self.finish(user)
        else:
            # New style: with @gen.coroutine the result must be yielded
            # or else the request will be auto-finished too soon.
            yield self.authorize_redirect()


class TwitterClientShowUserHandler(TwitterClientHandler):
    @gen.coroutine
    def get(self):
        # TODO: would be nice to go through the login flow instead of
        # cheating with a hard-coded access token.
        try:
            response = yield self.twitter_request(
                "/users/show/%s" % self.get_argument("name"),
                access_token=dict(key="hjkl", secret="vbnm"),
            )
        except HTTPClientError:
            # TODO(bdarnell): Should we catch HTTP errors and
            # transform some of them (like 403s) into AuthError?
            self.set_status(500)
            self.finish("error from twitter request")
        else:
            self.finish(response)


class TwitterServerAccessTokenHandler(RequestHandler):
    def get(self):
        self.write("oauth_token=hjkl&oauth_token_secret=vbnm&screen_name=foo")


class TwitterServerShowUserHandler(RequestHandler):
    def get(self, screen_name):
        if screen_name == "error":
            raise HTTPError(500)
        assert "oauth_nonce" in self.request.arguments
        assert "oauth_timestamp" in self.request.arguments
        assert "oauth_signature" in self.request.arguments
        assert self.get_argument("oauth_consumer_key") == "test_twitter_consumer_key"
        assert self.get_argument("oauth_signature_method") == "HMAC-SHA1"
        assert self.get_argument("oauth_version") == "1.0"
        assert self.get_argument("oauth_token") == "hjkl"
        self.write(dict(screen_name=screen_name, name=screen_name.capitalize()))


class TwitterServerVerifyCredentialsHandler(RequestHandler):
    def get(self):
        assert "oauth_nonce" in self.request.arguments
        assert "oauth_timestamp" in self.request.arguments
        assert "oauth_signature" in self.request.arguments
        assert self.get_argument("oauth_consumer_key") == "test_twitter_consumer_key"
        assert self.get_argument("oauth_signature_method") == "HMAC-SHA1"
        assert self.get_argument("oauth_version") == "1.0"
        assert self.get_argument("oauth_token") == "hjkl"
        self.write(dict(screen_name="foo", name="Foo"))


class AuthTest(AsyncHTTPTestCase):
    def get_app(self):
        return Application(
            [
                # test endpoints
                ("/openid/client/login", OpenIdClientLoginHandler, dict(test=self)),
                (
                    "/oauth10/client/login",
                    OAuth1ClientLoginHandler,
                    dict(test=self, version="1.0"),
                ),
                (
                    "/oauth10/client/request_params",
                    OAuth1ClientRequestParametersHandler,
                    dict(version="1.0"),
                ),
                (
                    "/oauth10a/client/login",
                    OAuth1ClientLoginHandler,
                    dict(test=self, version="1.0a"),
                ),
                (
                    "/oauth10a/client/login_coroutine",
                    OAuth1ClientLoginCoroutineHandler,
                    dict(test=self, version="1.0a"),
                ),
                (
                    "/oauth10a/client/request_params",
                    OAuth1ClientRequestParametersHandler,
                    dict(version="1.0a"),
                ),
                ("/oauth2/client/login", OAuth2ClientLoginHandler, dict(test=self)),
                ("/facebook/client/login", FacebookClientLoginHandler, dict(test=self)),
                ("/twitter/client/login", TwitterClientLoginHandler, dict(test=self)),
                (
                    "/twitter/client/authenticate",
                    TwitterClientAuthenticateHandler,
                    dict(test=self),
                ),
                (
                    "/twitter/client/login_gen_coroutine",
                    TwitterClientLoginGenCoroutineHandler,
                    dict(test=self),
                ),
                (
                    "/twitter/client/show_user",
                    TwitterClientShowUserHandler,
                    dict(test=self),
                ),
                # simulated servers
                ("/openid/server/authenticate", OpenIdServerAuthenticateHandler),
                ("/oauth1/server/request_token", OAuth1ServerRequestTokenHandler),
                ("/oauth1/server/access_token", OAuth1ServerAccessTokenHandler),
                ("/facebook/server/access_token", FacebookServerAccessTokenHandler),
                ("/facebook/server/me", FacebookServerMeHandler),
                ("/twitter/server/access_token", TwitterServerAccessTokenHandler),
                (r"/twitter/api/users/show/(.*)\.json", TwitterServerShowUserHandler),
                (
                    r"/twitter/api/account/verify_credentials\.json",
                    TwitterServerVerifyCredentialsHandler,
                ),
            ],
            http_client=self.http_client,
            twitter_consumer_key="test_twitter_consumer_key",
            twitter_consumer_secret="test_twitter_consumer_secret",
            facebook_api_key="test_facebook_api_key",
            facebook_secret="test_facebook_secret",
        )

    def test_openid_redirect(self):
        response = self.fetch("/openid/client/login", follow_redirects=False)
        self.assertEqual(response.code, 302)
        self.assertIn("/openid/server/authenticate?", response.headers["Location"])

    def test_openid_get_user(self):
        response = self.fetch(
            "/openid/client/login?openid.mode=blah"
            "&openid.ns.ax=http://openid.net/srv/ax/1.0"
            "&openid.ax.type.email=http://axschema.org/contact/email"
            "&openid.ax.value.email=foo@example.com"
        )
        response.rethrow()
        parsed = json_decode(response.body)
        self.assertEqual(parsed["email"], "foo@example.com")

    def test_oauth10_redirect(self):
        response = self.fetch("/oauth10/client/login", follow_redirects=False)
        self.assertEqual(response.code, 302)
        self.assertTrue(
            response.headers["Location"].endswith(
                "/oauth1/server/authorize?oauth_token=zxcv"
            )
        )
        # the cookie is base64('zxcv')|base64('1234')
        self.assertIn(
            '_oauth_request_token="enhjdg==|MTIzNA=="',
            response.headers["Set-Cookie"],
            response.headers["Set-Cookie"],
        )

    def test_oauth10_get_user(self):
        response = self.fetch(
            "/oauth10/client/login?oauth_token=zxcv",
            headers={"Cookie": "_oauth_request_token=enhjdg==|MTIzNA=="},
        )
        response.rethrow()
        parsed = json_decode(response.body)
        self.assertEqual(parsed["email"], "foo@example.com")
        self.assertEqual(parsed["access_token"], dict(key="uiop", secret="5678"))

    def test_oauth10_request_parameters(self):
        response = self.fetch("/oauth10/client/request_params")
        response.rethrow()
        parsed = json_decode(response.body)
        self.assertEqual(parsed["oauth_consumer_key"], "asdf")
        self.assertEqual(parsed["oauth_token"], "uiop")
        self.assertIn("oauth_nonce", parsed)
        self.assertIn("oauth_signature", parsed)

    def test_oauth10a_redirect(self):
        response = self.fetch("/oauth10a/client/login", follow_redirects=False)
        self.assertEqual(response.code, 302)
        self.assertTrue(
            response.headers["Location"].endswith(
                "/oauth1/server/authorize?oauth_token=zxcv"
            )
        )
        # the cookie is base64('zxcv')|base64('1234')
        self.assertTrue(
            '_oauth_request_token="enhjdg==|MTIzNA=="'
            in response.headers["Set-Cookie"],
            response.headers["Set-Cookie"],
        )

    @unittest.skipIf(mock is None, "mock package not present")
    def test_oauth10a_redirect_error(self):
        with mock.patch.object(OAuth1ServerRequestTokenHandler, "get") as get:
            get.side_effect = Exception("boom")
            with ExpectLog(app_log, "Uncaught exception"):
                response = self.fetch("/oauth10a/client/login", follow_redirects=False)
            self.assertEqual(response.code, 500)

    def test_oauth10a_get_user(self):
        response = self.fetch(
            "/oauth10a/client/login?oauth_token=zxcv",
            headers={"Cookie": "_oauth_request_token=enhjdg==|MTIzNA=="},
        )
        response.rethrow()
        parsed = json_decode(response.body)
        self.assertEqual(parsed["email"], "foo@example.com")
        self.assertEqual(parsed["access_token"], dict(key="uiop", secret="5678"))

    def test_oauth10a_request_parameters(self):
        response = self.fetch("/oauth10a/client/request_params")
        response.rethrow()
        parsed = json_decode(response.body)
        self.assertEqual(parsed["oauth_consumer_key"], "asdf")
        self.assertEqual(parsed["oauth_token"], "uiop")
        self.assertIn("oauth_nonce", parsed)
        self.assertIn("oauth_signature", parsed)

    def test_oauth10a_get_user_coroutine_exception(self):
        response = self.fetch(
            "/oauth10a/client/login_coroutine?oauth_token=zxcv&fail_in_get_user=true",
            headers={"Cookie": "_oauth_request_token=enhjdg==|MTIzNA=="},
        )
        self.assertEqual(response.code, 503)

    def test_oauth2_redirect(self):
        response = self.fetch("/oauth2/client/login", follow_redirects=False)
        self.assertEqual(response.code, 302)
        self.assertIn("/oauth2/server/authorize?", response.headers["Location"])

    def test_facebook_login(self):
        response = self.fetch("/facebook/client/login", follow_redirects=False)
        self.assertEqual(response.code, 302)
        self.assertTrue("/facebook/server/authorize?" in response.headers["Location"])
        response = self.fetch(
            "/facebook/client/login?code=1234", follow_redirects=False
        )
        self.assertEqual(response.code, 200)
        user = json_decode(response.body)
        self.assertEqual(user["access_token"], "asdf")
        self.assertEqual(user["session_expires"], "3600")

    def base_twitter_redirect(self, url):
        # Same as test_oauth10a_redirect
        response = self.fetch(url, follow_redirects=False)
        self.assertEqual(response.code, 302)
        self.assertTrue(
            response.headers["Location"].endswith(
                "/oauth1/server/authorize?oauth_token=zxcv"
            )
        )
        # the cookie is base64('zxcv')|base64('1234')
        self.assertIn(
            '_oauth_request_token="enhjdg==|MTIzNA=="',
            response.headers["Set-Cookie"],
            response.headers["Set-Cookie"],
        )

    def test_twitter_redirect(self):
        self.base_twitter_redirect("/twitter/client/login")

    def test_twitter_redirect_gen_coroutine(self):
        self.base_twitter_redirect("/twitter/client/login_gen_coroutine")

    def test_twitter_authenticate_redirect(self):
        response = self.fetch("/twitter/client/authenticate", follow_redirects=False)
        self.assertEqual(response.code, 302)
        self.assertTrue(
            response.headers["Location"].endswith(
                "/twitter/server/authenticate?oauth_token=zxcv"
            ),
            response.headers["Location"],
        )
        # the cookie is base64('zxcv')|base64('1234')
        self.assertIn(
            '_oauth_request_token="enhjdg==|MTIzNA=="',
            response.headers["Set-Cookie"],
            response.headers["Set-Cookie"],
        )

    def test_twitter_get_user(self):
        response = self.fetch(
            "/twitter/client/login?oauth_token=zxcv",
            headers={"Cookie": "_oauth_request_token=enhjdg==|MTIzNA=="},
        )
        response.rethrow()
        parsed = json_decode(response.body)
        self.assertEqual(
            parsed,
            {
                "access_token": {
                    "key": "hjkl",
                    "screen_name": "foo",
                    "secret": "vbnm",
                },
                "name": "Foo",
                "screen_name": "foo",
                "username": "foo",
            },
        )

    def test_twitter_show_user(self):
        response = self.fetch("/twitter/client/show_user?name=somebody")
        response.rethrow()
        self.assertEqual(
            json_decode(response.body), {"name": "Somebody", "screen_name": "somebody"}
        )

    def test_twitter_show_user_error(self):
        response = self.fetch("/twitter/client/show_user?name=error")
        self.assertEqual(response.code, 500)
        self.assertEqual(response.body, b"error from twitter request")


class GoogleLoginHandler(RequestHandler, GoogleOAuth2Mixin):
    def initialize(self, test):
        self.test = test
        self._OAUTH_REDIRECT_URI = test.get_url("/client/login")
        self._OAUTH_AUTHORIZE_URL = test.get_url("/google/oauth2/authorize")
        self._OAUTH_ACCESS_TOKEN_URL = test.get_url("/google/oauth2/token")

    @gen.coroutine
    def get(self):
        code = self.get_argument("code", None)
        if code is not None:
            # retrieve authenticate google user
            access = yield self.get_authenticated_user(self._OAUTH_REDIRECT_URI, code)
            user = yield self.oauth2_request(
                self.test.get_url("/google/oauth2/userinfo"),
                access_token=access["access_token"],
            )
            # return the user and access token as json
            user["access_token"] = access["access_token"]
            self.write(user)
        else:
            self.authorize_redirect(
                redirect_uri=self._OAUTH_REDIRECT_URI,
                client_id=self.settings["google_oauth"]["key"],
                scope=["profile", "email"],
                response_type="code",
                extra_params={"prompt": "select_account"},
            )


class GoogleOAuth2AuthorizeHandler(RequestHandler):
    def get(self):
        # issue a fake auth code and redirect to redirect_uri
        code = "fake-authorization-code"
        self.redirect(url_concat(self.get_argument("redirect_uri"), dict(code=code)))


class GoogleOAuth2TokenHandler(RequestHandler):
    def post(self):
        assert self.get_argument("code") == "fake-authorization-code"
        # issue a fake token
        self.finish(
            {"access_token": "fake-access-token", "expires_in": "never-expires"}
        )


class GoogleOAuth2UserinfoHandler(RequestHandler):
    def get(self):
        assert self.get_argument("access_token") == "fake-access-token"
        # return a fake user
        self.finish({"name": "Foo", "email": "foo@example.com"})


class GoogleOAuth2Test(AsyncHTTPTestCase):
    def get_app(self):
        return Application(
            [
                # test endpoints
                ("/client/login", GoogleLoginHandler, dict(test=self)),
                # simulated google authorization server endpoints
                ("/google/oauth2/authorize", GoogleOAuth2AuthorizeHandler),
                ("/google/oauth2/token", GoogleOAuth2TokenHandler),
                ("/google/oauth2/userinfo", GoogleOAuth2UserinfoHandler),
            ],
            google_oauth={
                "key": "fake_google_client_id",
                "secret": "fake_google_client_secret",
            },
        )

    def test_google_login(self):
        response = self.fetch("/client/login")
        self.assertDictEqual(
            {
                "name": "Foo",
                "email": "foo@example.com",
                "access_token": "fake-access-token",
            },
            json_decode(response.body),
        )

# === NexusCore/openenv\Lib\site-packages\ipykernel\eventloops.py ===
"""Event loop integration for the ZeroMQ-based kernels."""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

import os
import platform
import sys
from functools import partial

import zmq
from packaging.version import Version as V
from traitlets.config.application import Application


def _use_appnope():
    """Should we use appnope for dealing with OS X app nap?

    Checks if we are on OS X 10.9 or greater.
    """
    return sys.platform == "darwin" and V(platform.mac_ver()[0]) >= V("10.9")


# mapping of keys to loop functions
loop_map = {
    "inline": None,
    "nbagg": None,
    "webagg": None,
    "notebook": None,
    "ipympl": None,
    "widget": None,
    None: None,
}


def register_integration(*toolkitnames):
    """Decorator to register an event loop to integrate with the IPython kernel

    The decorator takes names to register the event loop as for the %gui magic.
    You can provide alternative names for the same toolkit.

    The decorated function should take a single argument, the IPython kernel
    instance, arrange for the event loop to call ``kernel.do_one_iteration()``
    at least every ``kernel._poll_interval`` seconds, and start the event loop.

    :mod:`ipykernel.eventloops` provides and registers such functions
    for a few common event loops.
    """

    def decorator(func):
        """Integration registration decorator."""
        for name in toolkitnames:
            loop_map[name] = func

        func.exit_hook = lambda kernel: None  # noqa: ARG005

        def exit_decorator(exit_func):
            """@func.exit is now a decorator

            to register a function to be called on exit
            """
            func.exit_hook = exit_func
            return exit_func

        func.exit = exit_decorator
        return func

    return decorator


def _notify_stream_qt(kernel):
    import operator
    from functools import lru_cache

    from IPython.external.qt_for_kernel import QtCore

    try:
        from IPython.external.qt_for_kernel import enum_helper
    except ImportError:

        @lru_cache(None)
        def enum_helper(name):
            return operator.attrgetter(name.rpartition(".")[0])(sys.modules[QtCore.__package__])

    def exit_loop():
        """fall back to main loop"""
        kernel._qt_notifier.setEnabled(False)
        kernel.app.qt_event_loop.quit()

    def process_stream_events():
        """fall back to main loop when there's a socket event"""
        # call flush to ensure that the stream doesn't lose events
        # due to our consuming of the edge-triggered FD
        # flush returns the number of events consumed.
        # if there were any, wake it up
        if kernel.shell_stream.flush(limit=1):
            exit_loop()

    if not hasattr(kernel, "_qt_notifier"):
        fd = kernel.shell_stream.getsockopt(zmq.FD)
        kernel._qt_notifier = QtCore.QSocketNotifier(
            fd, enum_helper("QtCore.QSocketNotifier.Type").Read, kernel.app.qt_event_loop
        )
        kernel._qt_notifier.activated.connect(process_stream_events)
    else:
        kernel._qt_notifier.setEnabled(True)

    # allow for scheduling exits from the loop in case a timeout needs to
    # be set from the kernel level
    def _schedule_exit(delay):
        """schedule fall back to main loop in [delay] seconds"""
        # The signatures of QtCore.QTimer.singleShot are inconsistent between PySide and PyQt
        # if setting the TimerType, so we create a timer explicitly and store it
        # to avoid a memory leak.
        # PreciseTimer is needed so we exit after _at least_ the specified delay, not within 5% of it
        if not hasattr(kernel, "_qt_timer"):
            kernel._qt_timer = QtCore.QTimer(kernel.app)
            kernel._qt_timer.setSingleShot(True)
            kernel._qt_timer.setTimerType(enum_helper("QtCore.Qt.TimerType").PreciseTimer)
            kernel._qt_timer.timeout.connect(exit_loop)
        kernel._qt_timer.start(int(1000 * delay))

    loop_qt._schedule_exit = _schedule_exit

    # there may already be unprocessed events waiting.
    # these events will not wake zmq's edge-triggered FD
    # since edge-triggered notification only occurs on new i/o activity.
    # process all the waiting events immediately
    # so we start in a clean state ensuring that any new i/o events will notify.
    # schedule first call on the eventloop as soon as it's running,
    # so we don't block here processing events
    QtCore.QTimer.singleShot(0, process_stream_events)


@register_integration("qt", "qt5", "qt6")
def loop_qt(kernel):
    """Event loop for all supported versions of Qt."""
    _notify_stream_qt(kernel)  # install hook to stop event loop.

    # Start the event loop.
    kernel.app._in_event_loop = True

    # `exec` blocks until there's ZMQ activity.
    el = kernel.app.qt_event_loop  # for brevity
    el.exec() if hasattr(el, "exec") else el.exec_()
    kernel.app._in_event_loop = False


# NOTE: To be removed in version 7
loop_qt5 = loop_qt


# exit and watch are the same for qt 4 and 5
@loop_qt.exit
def loop_qt_exit(kernel):
    kernel.app.exit()


def _loop_wx(app):
    """Inner-loop for running the Wx eventloop

    Pulled from guisupport.start_event_loop in IPython < 5.2,
    since IPython 5.2 only checks `get_ipython().active_eventloop` is defined,
    rather than if the eventloop is actually running.
    """
    app._in_event_loop = True
    app.MainLoop()
    app._in_event_loop = False


@register_integration("wx")
def loop_wx(kernel):
    """Start a kernel with wx event loop support."""

    import wx

    # Wx uses milliseconds
    poll_interval = int(1000 * kernel._poll_interval)

    def wake():
        """wake from wx"""
        if kernel.shell_stream.flush(limit=1):
            kernel.app.ExitMainLoop()
            return

    # We have to put the wx.Timer in a wx.Frame for it to fire properly.
    # We make the Frame hidden when we create it in the main app below.
    class TimerFrame(wx.Frame):  # type:ignore[misc]
        def __init__(self, func):
            wx.Frame.__init__(self, None, -1)
            self.timer = wx.Timer(self)
            # Units for the timer are in milliseconds
            self.timer.Start(poll_interval)
            self.Bind(wx.EVT_TIMER, self.on_timer)
            self.func = func

        def on_timer(self, event):
            self.func()

    # We need a custom wx.App to create our Frame subclass that has the
    # wx.Timer to defer back to the tornado event loop.
    class IPWxApp(wx.App):  # type:ignore[misc]
        def OnInit(self):
            self.frame = TimerFrame(wake)
            self.frame.Show(False)
            return True

    # The redirect=False here makes sure that wx doesn't replace
    # sys.stdout/stderr with its own classes.
    if not (getattr(kernel, "app", None) and isinstance(kernel.app, wx.App)):
        kernel.app = IPWxApp(redirect=False)

    # The import of wx on Linux sets the handler for signal.SIGINT
    # to 0.  This is a bug in wx or gtk.  We fix by just setting it
    # back to the Python default.
    import signal

    if not callable(signal.getsignal(signal.SIGINT)):
        signal.signal(signal.SIGINT, signal.default_int_handler)

    _loop_wx(kernel.app)


@loop_wx.exit
def loop_wx_exit(kernel):
    """Exit the wx loop."""
    import wx

    wx.Exit()


@register_integration("tk")
def loop_tk(kernel):
    """Start a kernel with the Tk event loop."""

    from tkinter import READABLE, Tk

    app = Tk()
    # Capability detection:
    # per https://docs.python.org/3/library/tkinter.html#file-handlers
    # file handlers are not available on Windows
    if hasattr(app, "createfilehandler"):
        # A basic wrapper for structural similarity with the Windows version
        class BasicAppWrapper:
            def __init__(self, app):
                self.app = app
                self.app.withdraw()

        def exit_loop():
            """fall back to main loop"""
            app.tk.deletefilehandler(kernel.shell_stream.getsockopt(zmq.FD))
            app.quit()
            app.destroy()
            del kernel.app_wrapper

        def process_stream_events(*a, **kw):
            """fall back to main loop when there's a socket event"""
            if kernel.shell_stream.flush(limit=1):
                exit_loop()

        # allow for scheduling exits from the loop in case a timeout needs to
        # be set from the kernel level
        def _schedule_exit(delay):
            """schedule fall back to main loop in [delay] seconds"""
            app.after(int(1000 * delay), exit_loop)

        loop_tk._schedule_exit = _schedule_exit

        # For Tkinter, we create a Tk object and call its withdraw method.
        kernel.app_wrapper = BasicAppWrapper(app)
        app.tk.createfilehandler(
            kernel.shell_stream.getsockopt(zmq.FD), READABLE, process_stream_events
        )
        # schedule initial call after start
        app.after(0, process_stream_events)

        app.mainloop()

    else:
        import asyncio

        import nest_asyncio

        nest_asyncio.apply()

        doi = kernel.do_one_iteration
        # Tk uses milliseconds
        poll_interval = int(1000 * kernel._poll_interval)

        class TimedAppWrapper:
            def __init__(self, app, func):
                self.app = app
                self.app.withdraw()
                self.func = func

            def on_timer(self):
                loop = asyncio.get_event_loop()
                try:
                    loop.run_until_complete(self.func())
                except Exception:
                    kernel.log.exception("Error in message handler")
                self.app.after(poll_interval, self.on_timer)

            def start(self):
                self.on_timer()  # Call it once to get things going.
                self.app.mainloop()

        kernel.app_wrapper = TimedAppWrapper(app, doi)
        kernel.app_wrapper.start()


@loop_tk.exit
def loop_tk_exit(kernel):
    """Exit the tk loop."""
    try:
        kernel.app_wrapper.app.destroy()
        del kernel.app_wrapper
    except (RuntimeError, AttributeError):
        pass


@register_integration("gtk")
def loop_gtk(kernel):
    """Start the kernel, coordinating with the GTK event loop"""
    from .gui.gtkembed import GTKEmbed

    gtk_kernel = GTKEmbed(kernel)
    gtk_kernel.start()
    kernel._gtk = gtk_kernel


@loop_gtk.exit
def loop_gtk_exit(kernel):
    """Exit the gtk loop."""
    kernel._gtk.stop()


@register_integration("gtk3")
def loop_gtk3(kernel):
    """Start the kernel, coordinating with the GTK event loop"""
    from .gui.gtk3embed import GTKEmbed

    gtk_kernel = GTKEmbed(kernel)
    gtk_kernel.start()
    kernel._gtk = gtk_kernel


@loop_gtk3.exit
def loop_gtk3_exit(kernel):
    """Exit the gtk3 loop."""
    kernel._gtk.stop()


@register_integration("osx")
def loop_cocoa(kernel):
    """Start the kernel, coordinating with the Cocoa CFRunLoop event loop
    via the matplotlib MacOSX backend.
    """
    from ._eventloop_macos import mainloop, stop

    real_excepthook = sys.excepthook

    def handle_int(etype, value, tb):
        """don't let KeyboardInterrupts look like crashes"""
        # wake the eventloop when we get a signal
        stop()
        if etype is KeyboardInterrupt:
            print("KeyboardInterrupt caught in CFRunLoop", file=sys.__stdout__)
        else:
            real_excepthook(etype, value, tb)

    while not kernel.shell.exit_now:
        try:
            # double nested try/except, to properly catch KeyboardInterrupt
            # due to pyzmq Issue #130
            try:
                # don't let interrupts during mainloop invoke crash_handler:
                sys.excepthook = handle_int
                mainloop(kernel._poll_interval)
                if kernel.shell_stream.flush(limit=1):
                    # events to process, return control to kernel
                    return
            except BaseException:
                raise
        except KeyboardInterrupt:
            # Ctrl-C shouldn't crash the kernel
            print("KeyboardInterrupt caught in kernel", file=sys.__stdout__)
        finally:
            # ensure excepthook is restored
            sys.excepthook = real_excepthook


@loop_cocoa.exit
def loop_cocoa_exit(kernel):
    """Exit the cocoa loop."""
    from ._eventloop_macos import stop

    stop()


@register_integration("asyncio")
def loop_asyncio(kernel):
    """Start a kernel with asyncio event loop support."""
    import asyncio

    loop = asyncio.get_event_loop()
    # loop is already running (e.g. tornado 5), nothing left to do
    if loop.is_running():
        return

    if loop.is_closed():
        # main loop is closed, create a new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    loop._should_close = False  # type:ignore[attr-defined]

    # pause eventloop when there's an event on a zmq socket
    def process_stream_events(stream):
        """fall back to main loop when there's a socket event"""
        if stream.flush(limit=1):
            loop.stop()

    notifier = partial(process_stream_events, kernel.shell_stream)
    loop.add_reader(kernel.shell_stream.getsockopt(zmq.FD), notifier)
    loop.call_soon(notifier)

    while True:
        error = None
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            continue
        except Exception as e:
            error = e
        if loop._should_close:  # type:ignore[attr-defined]
            loop.close()
        if error is not None:
            raise error
        break


@loop_asyncio.exit
def loop_asyncio_exit(kernel):
    """Exit hook for asyncio"""
    import asyncio

    loop = asyncio.get_event_loop()

    async def close_loop():
        if hasattr(loop, "shutdown_asyncgens"):
            yield loop.shutdown_asyncgens()
        loop._should_close = True  # type:ignore[attr-defined]
        loop.stop()

    if loop.is_running():
        close_loop()

    elif not loop.is_closed():
        loop.run_until_complete(close_loop)  # type:ignore[arg-type]
        loop.close()


def set_qt_api_env_from_gui(gui):
    """
    Sets the QT_API environment variable by trying to import PyQtx or PySidex.

    The user can generically request `qt` or a specific Qt version, e.g. `qt6`.
    For a generic Qt request, we let the mechanism in IPython choose the best
    available version by leaving the `QT_API` environment variable blank.

    For specific versions, we check to see whether the PyQt or PySide
    implementations are present and set `QT_API` accordingly to indicate to
    IPython which version we want. If neither implementation is present, we
    leave the environment variable set so IPython will generate a helpful error
    message.

    Notes
    -----
    - If the environment variable is already set, it will be used unchanged,
      regardless of what the user requested.
    """
    qt_api = os.environ.get("QT_API", None)

    from IPython.external.qt_loaders import (
        QT_API_PYQT5,
        QT_API_PYQT6,
        QT_API_PYSIDE2,
        QT_API_PYSIDE6,
        loaded_api,
    )

    loaded = loaded_api()

    qt_env2gui = {
        QT_API_PYSIDE2: "qt5",
        QT_API_PYQT5: "qt5",
        QT_API_PYSIDE6: "qt6",
        QT_API_PYQT6: "qt6",
    }
    if loaded is not None and gui != "qt" and qt_env2gui[loaded] != gui:
        print(f"Cannot switch Qt versions for this session; you must use {qt_env2gui[loaded]}.")
        return

    if qt_api is not None and gui != "qt":
        if qt_env2gui[qt_api] != gui:
            print(
                f'Request for "{gui}" will be ignored because `QT_API` '
                f'environment variable is set to "{qt_api}"'
            )
            return
    else:
        if gui == "qt5":
            try:
                import PyQt5  # noqa: F401

                os.environ["QT_API"] = "pyqt5"
            except ImportError:
                try:
                    import PySide2  # noqa: F401

                    os.environ["QT_API"] = "pyside2"
                except ImportError:
                    os.environ["QT_API"] = "pyqt5"
        elif gui == "qt6":
            try:
                import PyQt6  # noqa: F401

                os.environ["QT_API"] = "pyqt6"
            except ImportError:
                try:
                    import PySide6  # noqa: F401

                    os.environ["QT_API"] = "pyside6"
                except ImportError:
                    os.environ["QT_API"] = "pyqt6"
        elif gui == "qt":
            # Don't set QT_API; let IPython logic choose the version.
            if "QT_API" in os.environ:
                del os.environ["QT_API"]
        else:
            print(f'Unrecognized Qt version: {gui}. Should be "qt5", "qt6", or "qt".')
            return

    # Do the actual import now that the environment variable is set to make sure it works.
    try:
        pass
    except Exception as e:
        # Clear the environment variable for the next attempt.
        if "QT_API" in os.environ:
            del os.environ["QT_API"]
            print(f"QT_API couldn't be set due to error {e}")
        return


def make_qt_app_for_kernel(gui, kernel):
    """Sets the `QT_API` environment variable if it isn't already set."""
    if hasattr(kernel, "app"):
        # Kernel is already running a Qt event loop, so there's no need to
        # create another app for it.
        return

    set_qt_api_env_from_gui(gui)

    # This import is guaranteed to work now:
    from IPython.external.qt_for_kernel import QtCore
    from IPython.lib.guisupport import get_app_qt4

    kernel.app = get_app_qt4([" "])
    kernel.app.qt_event_loop = QtCore.QEventLoop(kernel.app)


def enable_gui(gui, kernel=None):
    """Enable integration with a given GUI"""
    if gui not in loop_map:
        e = f"Invalid GUI request {gui!r}, valid ones are:{loop_map.keys()}"
        raise ValueError(e)
    if kernel is None:
        if Application.initialized():
            kernel = getattr(Application.instance(), "kernel", None)
        if kernel is None:
            msg = (
                "You didn't specify a kernel,"
                " and no IPython Application with a kernel appears to be running."
            )
            raise RuntimeError(msg)
    if gui is None:
        # User wants to turn off integration; clear any evidence if Qt was the last one.
        if hasattr(kernel, "app"):
            delattr(kernel, "app")
        if hasattr(kernel, "_qt_notifier"):
            delattr(kernel, "_qt_notifier")
        if hasattr(kernel, "_qt_timer"):
            delattr(kernel, "_qt_timer")
    else:
        if gui.startswith("qt"):
            # Prepare the kernel here so any exceptions are displayed in the client.
            make_qt_app_for_kernel(gui, kernel)

    loop = loop_map[gui]
    if (
        loop and kernel.eventloop is not None and kernel.eventloop is not loop  # type:ignore[unreachable]
    ):
        msg = "Cannot activate multiple GUI eventloops"  # type:ignore[unreachable]
        raise RuntimeError(msg)
    kernel.eventloop = loop
    # We set `eventloop`; the function the user chose is executed in `Kernel.enter_eventloop`, thus
    # any exceptions raised during the event loop will not be shown in the client.

# === NexusCore/openenv\Lib\site-packages\joblib\test\test_dask.py ===
from __future__ import absolute_import, division, print_function

import os
import warnings
from random import random
from time import sleep
from uuid import uuid4

import pytest

from .. import Parallel, delayed, parallel_backend, parallel_config
from .._dask import DaskDistributedBackend
from ..parallel import AutoBatchingMixin, ThreadingBackend
from .common import np, with_numpy
from .test_parallel import (
    _recursive_backend_info,
    _test_deadlock_with_generator,
    _test_parallel_unordered_generator_returns_fastest_first,  # noqa: E501
)

distributed = pytest.importorskip("distributed")
dask = pytest.importorskip("dask")

# These imports need to be after the pytest.importorskip hence the noqa: E402
from distributed import Client, LocalCluster, get_client  # noqa: E402
from distributed.metrics import time  # noqa: E402

# Note: pytest requires to manually import all fixtures used in the test
# and their dependencies.
from distributed.utils_test import cleanup, cluster, inc  # noqa: E402, F401


@pytest.fixture(scope="function", autouse=True)
def avoid_dask_env_leaks(tmp_path):
    # when starting a dask nanny, the environment variable might change.
    # this fixture makes sure the environment is reset after the test.

    from joblib._parallel_backends import ParallelBackendBase

    old_value = {k: os.environ.get(k) for k in ParallelBackendBase.MAX_NUM_THREADS_VARS}
    yield

    # Reset the environment variables to their original values
    for k, v in old_value.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


def noop(*args, **kwargs):
    pass


def slow_raise_value_error(condition, duration=0.05):
    sleep(duration)
    if condition:
        raise ValueError("condition evaluated to True")


def count_events(event_name, client):
    worker_events = client.run(lambda dask_worker: dask_worker.log)
    event_counts = {}
    for w, events in worker_events.items():
        event_counts[w] = len(
            [event for event in list(events) if event[1] == event_name]
        )
    return event_counts


def test_simple(loop):
    with cluster() as (s, [a, b]):
        with Client(s["address"], loop=loop) as client:  # noqa: F841
            with parallel_config(backend="dask"):
                seq = Parallel()(delayed(inc)(i) for i in range(10))
                assert seq == [inc(i) for i in range(10)]

                with pytest.raises(ValueError):
                    Parallel()(
                        delayed(slow_raise_value_error)(i == 3) for i in range(10)
                    )

                seq = Parallel()(delayed(inc)(i) for i in range(10))
                assert seq == [inc(i) for i in range(10)]


def test_dask_backend_uses_autobatching(loop):
    assert (
        DaskDistributedBackend.compute_batch_size
        is AutoBatchingMixin.compute_batch_size
    )

    with cluster() as (s, [a, b]):
        with Client(s["address"], loop=loop) as client:  # noqa: F841
            with parallel_config(backend="dask"):
                with Parallel() as parallel:
                    # The backend should be initialized with a default
                    # batch size of 1:
                    backend = parallel._backend
                    assert isinstance(backend, DaskDistributedBackend)
                    assert backend.parallel is parallel
                    assert backend._effective_batch_size == 1

                    # Launch many short tasks that should trigger
                    # auto-batching:
                    parallel(delayed(lambda: None)() for _ in range(int(1e4)))
                    assert backend._effective_batch_size > 10


@pytest.mark.parametrize("n_jobs", [2, -1])
@pytest.mark.parametrize("context", [parallel_config, parallel_backend])
def test_parallel_unordered_generator_returns_fastest_first_with_dask(n_jobs, context):
    with distributed.Client(n_workers=2, threads_per_worker=2), context("dask"):
        _test_parallel_unordered_generator_returns_fastest_first(None, n_jobs)


@with_numpy
@pytest.mark.parametrize("n_jobs", [2, -1])
@pytest.mark.parametrize("return_as", ["generator", "generator_unordered"])
@pytest.mark.parametrize("context", [parallel_config, parallel_backend])
def test_deadlock_with_generator_and_dask(context, return_as, n_jobs):
    with distributed.Client(n_workers=2, threads_per_worker=2), context("dask"):
        _test_deadlock_with_generator(None, return_as, n_jobs)


@with_numpy
@pytest.mark.parametrize("context", [parallel_config, parallel_backend])
def test_nested_parallelism_with_dask(context):
    with distributed.Client(n_workers=2, threads_per_worker=2):
        # 10 MB of data as argument to trigger implicit scattering
        data = np.ones(int(1e7), dtype=np.uint8)
        for i in range(2):
            with context("dask"):
                backend_types_and_levels = _recursive_backend_info(data=data)
            assert len(backend_types_and_levels) == 4
            assert all(
                name == "DaskDistributedBackend" for name, _ in backend_types_and_levels
            )

        # No argument
        with context("dask"):
            backend_types_and_levels = _recursive_backend_info()
        assert len(backend_types_and_levels) == 4
        assert all(
            name == "DaskDistributedBackend" for name, _ in backend_types_and_levels
        )


def random2():
    return random()


def test_dont_assume_function_purity(loop):
    with cluster() as (s, [a, b]):
        with Client(s["address"], loop=loop) as client:  # noqa: F841
            with parallel_config(backend="dask"):
                x, y = Parallel()(delayed(random2)() for i in range(2))
                assert x != y


@pytest.mark.parametrize("mixed", [True, False])
def test_dask_funcname(loop, mixed):
    from joblib._dask import Batch

    if not mixed:
        tasks = [delayed(inc)(i) for i in range(4)]
        batch_repr = "batch_of_inc_4_calls"
    else:
        tasks = [delayed(abs)(i) if i % 2 else delayed(inc)(i) for i in range(4)]
        batch_repr = "mixed_batch_of_inc_4_calls"

    assert repr(Batch(tasks)) == batch_repr

    with cluster() as (s, [a, b]):
        with Client(s["address"], loop=loop) as client:
            with parallel_config(backend="dask"):
                _ = Parallel(batch_size=2, pre_dispatch="all")(tasks)

            def f(dask_scheduler):
                return list(dask_scheduler.transition_log)

            batch_repr = batch_repr.replace("4", "2")
            log = client.run_on_scheduler(f)
            assert all("batch_of_inc" in tup[0] for tup in log)


def test_no_undesired_distributed_cache_hit():
    # Dask has a pickle cache for callables that are called many times. Because
    # the dask backends used to wrap both the functions and the arguments
    # under instances of the Batch callable class this caching mechanism could
    # lead to bugs as described in: https://github.com/joblib/joblib/pull/1055
    # The joblib-dask backend has been refactored to avoid bundling the
    # arguments as an attribute of the Batch instance to avoid this problem.
    # This test serves as non-regression problem.

    # Use a large number of input arguments to give the AutoBatchingMixin
    # enough tasks to kick-in.
    lists = [[] for _ in range(100)]
    np = pytest.importorskip("numpy")
    X = np.arange(int(1e6))

    def isolated_operation(list_, data=None):
        if data is not None:
            np.testing.assert_array_equal(data, X)
        list_.append(uuid4().hex)
        return list_

    cluster = LocalCluster(n_workers=1, threads_per_worker=2)
    client = Client(cluster)
    try:
        with parallel_config(backend="dask"):
            # dispatches joblib.parallel.BatchedCalls
            res = Parallel()(delayed(isolated_operation)(list_) for list_ in lists)

        # The original arguments should not have been mutated as the mutation
        # happens in the dask worker process.
        assert lists == [[] for _ in range(100)]

        # Here we did not pass any large numpy array as argument to
        # isolated_operation so no scattering event should happen under the
        # hood.
        counts = count_events("receive-from-scatter", client)
        assert sum(counts.values()) == 0
        assert all([len(r) == 1 for r in res])

        with parallel_config(backend="dask"):
            # Append a large array which will be scattered by dask, and
            # dispatch joblib._dask.Batch
            res = Parallel()(
                delayed(isolated_operation)(list_, data=X) for list_ in lists
            )

        # This time, auto-scattering should have kicked it.
        counts = count_events("receive-from-scatter", client)
        assert sum(counts.values()) > 0
        assert all([len(r) == 1 for r in res])
    finally:
        client.close(timeout=30)
        cluster.close(timeout=30)


class CountSerialized(object):
    def __init__(self, x):
        self.x = x
        self.count = 0

    def __add__(self, other):
        return self.x + getattr(other, "x", other)

    __radd__ = __add__

    def __reduce__(self):
        self.count += 1
        return (CountSerialized, (self.x,))


def add5(a, b, c, d=0, e=0):
    return a + b + c + d + e


def test_manual_scatter(loop):
    # Let's check that the number of times scattered and non-scattered
    # variables are serialized is consistent between `joblib.Parallel` calls
    # and equivalent native `client.submit` call.

    # Number of serializations can vary from dask to another, so this test only
    # checks that `joblib.Parallel` does not add more serialization steps than
    # a native `client.submit` call, but does not check for an exact number of
    # serialization steps.

    w, x, y, z = (CountSerialized(i) for i in range(4))

    f = delayed(add5)
    tasks = [f(x, y, z, d=4, e=5) for _ in range(10)]
    tasks += [
        f(x, z, y, d=5, e=4),
        f(y, x, z, d=x, e=5),
        f(z, z, x, d=z, e=y),
    ]
    expected = [func(*args, **kwargs) for func, args, kwargs in tasks]

    with cluster() as (s, _):
        with Client(s["address"], loop=loop) as client:  # noqa: F841
            with parallel_config(backend="dask", scatter=[w, x, y]):
                results_parallel = Parallel(batch_size=1)(tasks)
                assert results_parallel == expected

            # Check that an error is raised for bad arguments, as scatter must
            # take a list/tuple
            with pytest.raises(TypeError):
                with parallel_config(backend="dask", loop=loop, scatter=1):
                    pass

    # Scattered variables only serialized during scatter. Checking with an
    # extra variable as this count can vary from one dask version
    # to another.
    n_serialization_scatter_with_parallel = w.count
    assert x.count == n_serialization_scatter_with_parallel
    assert y.count == n_serialization_scatter_with_parallel
    n_serialization_with_parallel = z.count

    # Reset the cluster and the serialization count
    for var in (w, x, y, z):
        var.count = 0

    with cluster() as (s, _):
        with Client(s["address"], loop=loop) as client:  # noqa: F841
            scattered = dict()
            for obj in w, x, y:
                scattered[id(obj)] = client.scatter(obj, broadcast=True)
            results_native = [
                client.submit(
                    func,
                    *(scattered.get(id(arg), arg) for arg in args),
                    **dict(
                        (key, scattered.get(id(value), value))
                        for (key, value) in kwargs.items()
                    ),
                    key=str(uuid4()),
                ).result()
                for (func, args, kwargs) in tasks
            ]
            assert results_native == expected

    # Now check that the number of serialization steps is the same for joblib
    # and native dask calls.
    n_serialization_scatter_native = w.count
    assert x.count == n_serialization_scatter_native
    assert y.count == n_serialization_scatter_native

    assert n_serialization_scatter_with_parallel == n_serialization_scatter_native

    distributed_version = tuple(int(v) for v in distributed.__version__.split("."))
    if distributed_version < (2023, 4):
        # Previous to 2023.4, the serialization was adding an extra call to
        # __reduce__ for the last job `f(z, z, x, d=z, e=y)`, because `z`
        # appears both in the args and kwargs, which is not the case when
        # running with joblib. Cope with this discrepancy.
        assert z.count == n_serialization_with_parallel + 1
    else:
        assert z.count == n_serialization_with_parallel


# When the same IOLoop is used for multiple clients in a row, use
# loop_in_thread instead of loop to prevent the Client from closing it.  See
# dask/distributed #4112
def test_auto_scatter(loop_in_thread):
    np = pytest.importorskip("numpy")
    data1 = np.ones(int(1e4), dtype=np.uint8)
    data2 = np.ones(int(1e4), dtype=np.uint8)
    data_to_process = ([data1] * 3) + ([data2] * 3)

    with cluster() as (s, [a, b]):
        with Client(s["address"], loop=loop_in_thread) as client:
            with parallel_config(backend="dask"):
                # Passing the same data as arg and kwarg triggers a single
                # scatter operation whose result is reused.
                Parallel()(
                    delayed(noop)(data, data, i, opt=data)
                    for i, data in enumerate(data_to_process)
                )
            # By default large array are automatically scattered with
            # broadcast=1 which means that one worker must directly receive
            # the data from the scatter operation once.
            counts = count_events("receive-from-scatter", client)
            assert counts[a["address"]] + counts[b["address"]] == 2

    with cluster() as (s, [a, b]):
        with Client(s["address"], loop=loop_in_thread) as client:
            with parallel_config(backend="dask"):
                Parallel()(delayed(noop)(data1[:3], i) for i in range(5))
            # Small arrays are passed within the task definition without going
            # through a scatter operation.
            counts = count_events("receive-from-scatter", client)
            assert counts[a["address"]] == 0
            assert counts[b["address"]] == 0


@pytest.mark.parametrize("retry_no", list(range(2)))
def test_nested_scatter(loop, retry_no):
    np = pytest.importorskip("numpy")

    NUM_INNER_TASKS = 10
    NUM_OUTER_TASKS = 10

    def my_sum(x, i, j):
        return np.sum(x)

    def outer_function_joblib(array, i):
        client = get_client()  # noqa
        with parallel_config(backend="dask"):
            results = Parallel()(
                delayed(my_sum)(array[j:], i, j) for j in range(NUM_INNER_TASKS)
            )
        return sum(results)

    with cluster() as (s, [a, b]):
        with Client(s["address"], loop=loop) as _:
            with parallel_config(backend="dask"):
                my_array = np.ones(10000)
                _ = Parallel()(
                    delayed(outer_function_joblib)(my_array[i:], i)
                    for i in range(NUM_OUTER_TASKS)
                )


def test_nested_backend_context_manager(loop_in_thread):
    def get_nested_pids():
        pids = set(Parallel(n_jobs=2)(delayed(os.getpid)() for _ in range(2)))
        pids |= set(Parallel(n_jobs=2)(delayed(os.getpid)() for _ in range(2)))
        return pids

    with cluster() as (s, [a, b]):
        with Client(s["address"], loop=loop_in_thread) as client:
            with parallel_config(backend="dask"):
                pid_groups = Parallel(n_jobs=2)(
                    delayed(get_nested_pids)() for _ in range(10)
                )
                for pid_group in pid_groups:
                    assert len(set(pid_group)) <= 2

        # No deadlocks
        with Client(s["address"], loop=loop_in_thread) as client:  # noqa: F841
            with parallel_config(backend="dask"):
                pid_groups = Parallel(n_jobs=2)(
                    delayed(get_nested_pids)() for _ in range(10)
                )
                for pid_group in pid_groups:
                    assert len(set(pid_group)) <= 2


def test_nested_backend_context_manager_implicit_n_jobs(loop):
    # Check that Parallel with no explicit n_jobs value automatically selects
    # all the dask workers, including in nested calls.

    def _backend_type(p):
        return p._backend.__class__.__name__

    def get_nested_implicit_n_jobs():
        with Parallel() as p:
            return _backend_type(p), p.n_jobs

    with cluster() as (s, [a, b]):
        with Client(s["address"], loop=loop) as client:  # noqa: F841
            with parallel_config(backend="dask"):
                with Parallel() as p:
                    assert _backend_type(p) == "DaskDistributedBackend"
                    assert p.n_jobs == -1
                    all_nested_n_jobs = p(
                        delayed(get_nested_implicit_n_jobs)() for _ in range(2)
                    )
                for backend_type, nested_n_jobs in all_nested_n_jobs:
                    assert backend_type == "DaskDistributedBackend"
                    assert nested_n_jobs == -1


def test_errors(loop):
    with pytest.raises(ValueError) as info:
        with parallel_config(backend="dask"):
            pass

    assert "create a dask client" in str(info.value).lower()


def test_correct_nested_backend(loop):
    with cluster() as (s, [a, b]):
        with Client(s["address"], loop=loop) as client:  # noqa: F841
            # No requirement, should be us
            with parallel_config(backend="dask"):
                result = Parallel(n_jobs=2)(
                    delayed(outer)(nested_require=None) for _ in range(1)
                )
                assert isinstance(result[0][0][0], DaskDistributedBackend)

            # Require threads, should be threading
            with parallel_config(backend="dask"):
                result = Parallel(n_jobs=2)(
                    delayed(outer)(nested_require="sharedmem") for _ in range(1)
                )
                assert isinstance(result[0][0][0], ThreadingBackend)


def outer(nested_require):
    return Parallel(n_jobs=2, prefer="threads")(
        delayed(middle)(nested_require) for _ in range(1)
    )


def middle(require):
    return Parallel(n_jobs=2, require=require)(delayed(inner)() for _ in range(1))


def inner():
    return Parallel()._backend


def test_secede_with_no_processes(loop):
    # https://github.com/dask/distributed/issues/1775
    with Client(loop=loop, processes=False, set_as_default=True):
        with parallel_config(backend="dask"):
            Parallel(n_jobs=4)(delayed(id)(i) for i in range(2))


def _worker_address(_):
    from distributed import get_worker

    return get_worker().address


def test_dask_backend_keywords(loop):
    with cluster() as (s, [a, b]):
        with Client(s["address"], loop=loop) as client:  # noqa: F841
            with parallel_config(backend="dask", workers=a["address"]):
                seq = Parallel()(delayed(_worker_address)(i) for i in range(10))
                assert seq == [a["address"]] * 10

            with parallel_config(backend="dask", workers=b["address"]):
                seq = Parallel()(delayed(_worker_address)(i) for i in range(10))
                assert seq == [b["address"]] * 10


def test_scheduler_tasks_cleanup(loop):
    with Client(processes=False, loop=loop) as client:
        with parallel_config(backend="dask"):
            Parallel()(delayed(inc)(i) for i in range(10))

        start = time()
        while client.cluster.scheduler.tasks:
            sleep(0.01)
            assert time() < start + 5

        assert not client.futures


@pytest.mark.parametrize("cluster_strategy", ["adaptive", "late_scaling"])
@pytest.mark.skipif(
    distributed.__version__ <= "2.1.1" and distributed.__version__ >= "1.28.0",
    reason="distributed bug - https://github.com/dask/distributed/pull/2841",
)
def test_wait_for_workers(cluster_strategy):
    cluster = LocalCluster(n_workers=0, processes=False, threads_per_worker=2)
    client = Client(cluster)
    if cluster_strategy == "adaptive":
        cluster.adapt(minimum=0, maximum=2)
    elif cluster_strategy == "late_scaling":
        # Tell the cluster to start workers but this is a non-blocking call
        # and new workers might take time to connect. In this case the Parallel
        # call should wait for at least one worker to come up before starting
        # to schedule work.
        cluster.scale(2)
    try:
        with parallel_config(backend="dask"):
            # The following should wait a bit for at least one worker to
            # become available.
            Parallel()(delayed(inc)(i) for i in range(10))
    finally:
        client.close()
        cluster.close()


def test_wait_for_workers_timeout():
    # Start a cluster with 0 worker:
    cluster = LocalCluster(n_workers=0, processes=False, threads_per_worker=2)
    client = Client(cluster)
    try:
        with parallel_config(backend="dask", wait_for_workers_timeout=0.1):
            # Short timeout: DaskDistributedBackend
            msg = "DaskDistributedBackend has no worker after 0.1 seconds."
            with pytest.raises(TimeoutError, match=msg):
                Parallel()(delayed(inc)(i) for i in range(10))

        with parallel_config(backend="dask", wait_for_workers_timeout=0):
            # No timeout: fallback to generic joblib failure:
            msg = "DaskDistributedBackend has no active worker"
            with pytest.raises(RuntimeError, match=msg):
                Parallel()(delayed(inc)(i) for i in range(10))
    finally:
        client.close()
        cluster.close()


@pytest.mark.parametrize("backend", ["loky", "multiprocessing"])
def test_joblib_warning_inside_dask_daemonic_worker(backend):
    cluster = LocalCluster(n_workers=2)
    client = Client(cluster)
    try:

        def func_using_joblib_parallel():
            # Somehow trying to check the warning type here (e.g. with
            # pytest.warns(UserWarning)) make the test hang. Work-around:
            # return the warning record to the client and the warning check is
            # done client-side.
            with warnings.catch_warnings(record=True) as record:
                Parallel(n_jobs=2, backend=backend)(delayed(inc)(i) for i in range(10))

            return record

        fut = client.submit(func_using_joblib_parallel)
        record = fut.result()

        assert len(record) == 1
        warning = record[0].message
        assert isinstance(warning, UserWarning)
        assert "distributed.worker.daemon" in str(warning)
    finally:
        client.close(timeout=30)
        cluster.close(timeout=30)

# === NexusCore/openenv\Lib\site-packages\win32\scripts\regsetup.py ===
# A tool to setup the Python registry.


class error(Exception):
    pass


import sys  # at least we can count on this!


def FileExists(fname):
    """Check if a file exists.  Returns true or false."""
    import os

    try:
        os.stat(fname)
        return 1
    except OSError as details:
        return 0


def IsPackageDir(path, packageName, knownFileName):
    """Given a path, a ni package name, and possibly a known file name in
    the root of the package, see if this path is good.
    """
    import os

    if knownFileName is None:
        knownFileName = "."
    return FileExists(os.path.join(os.path.join(path, packageName), knownFileName))


def IsDebug():
    """Return "_d" if we're running a debug version.

    This is to be used within DLL names when locating them.
    """
    import importlib.machinery

    return "_d" if "_d.pyd" in importlib.machinery.EXTENSION_SUFFIXES else ""


def FindPackagePath(packageName, knownFileName, searchPaths):
    """Find a package.

    Given a ni style package name, check the package is registered.

    First place looked is the registry for an existing entry.  Then
    the searchPaths are searched.
    """
    import os

    import regutil

    pathLook = regutil.GetRegisteredNamedPath(packageName)
    if pathLook and IsPackageDir(pathLook, packageName, knownFileName):
        return pathLook, None  # The currently registered one is good.
    # Search down the search paths.
    for pathLook in searchPaths:
        if IsPackageDir(pathLook, packageName, knownFileName):
            # Found it
            ret = os.path.abspath(pathLook)
            return ret, ret
    raise error("The package %s can not be located" % packageName)


def FindHelpPath(helpFile, helpDesc, searchPaths):
    # See if the current registry entry is OK
    import os

    import win32api
    import win32con

    try:
        key = win32api.RegOpenKey(
            win32con.HKEY_LOCAL_MACHINE,
            "Software\\Microsoft\\Windows\\Help",
            0,
            win32con.KEY_ALL_ACCESS,
        )
        try:
            try:
                path = win32api.RegQueryValueEx(key, helpDesc)[0]
                if FileExists(os.path.join(path, helpFile)):
                    return os.path.abspath(path)
            except win32api.error:
                pass  # no registry entry.
        finally:
            key.Close()
    except win32api.error:
        pass
    for pathLook in searchPaths:
        if FileExists(os.path.join(pathLook, helpFile)):
            return os.path.abspath(pathLook)
        pathLook = os.path.join(pathLook, "Help")
        if FileExists(os.path.join(pathLook, helpFile)):
            return os.path.abspath(pathLook)
    raise error("The help file %s can not be located" % helpFile)


def FindAppPath(appName, knownFileName, searchPaths):
    """Find an application.

    First place looked is the registry for an existing entry.  Then
    the searchPaths are searched.
    """
    # Look in the first path.
    import os

    import regutil

    regPath = regutil.GetRegisteredNamedPath(appName)
    if regPath:
        pathLook = regPath.split(";")[0]
    if regPath and FileExists(os.path.join(pathLook, knownFileName)):
        return None  # The currently registered one is good.
    # Search down the search paths.
    for pathLook in searchPaths:
        if FileExists(os.path.join(pathLook, knownFileName)):
            # Found it
            return os.path.abspath(pathLook)
    raise error(
        f"The file {knownFileName} can not be located for application {appName}"
    )


def FindPythonExe(exeAlias, possibleRealNames, searchPaths):
    """Find an exe.

    Returns the full path to the .exe, and a boolean indicating if the current
    registered entry is OK.  We don't trust the already registered version even
    if it exists - it may be wrong (ie, for a different Python version)
    """
    import os
    import sys

    import regutil
    import win32api

    if possibleRealNames is None:
        possibleRealNames = exeAlias
    # Look first in Python's home.
    found = os.path.join(sys.prefix, possibleRealNames)
    if not FileExists(found):  # for developers
        if "64 bit" in sys.version:
            found = os.path.join(sys.prefix, "PCBuild", "amd64", possibleRealNames)
        else:
            found = os.path.join(sys.prefix, "PCBuild", possibleRealNames)
    if not FileExists(found):
        found = LocateFileName(possibleRealNames, searchPaths)

    registered_ok = 0
    try:
        registered = win32api.RegQueryValue(
            regutil.GetRootKey(), regutil.GetAppPathsKey() + "\\" + exeAlias
        )
        registered_ok = found == registered
    except win32api.error:
        pass
    return found, registered_ok


def QuotedFileName(fname):
    """Given a filename, return a quoted version if necessary"""

    import regutil

    try:
        fname.index(" ")  # Other chars forcing quote?
        return '"%s"' % fname
    except ValueError:
        # No space in name.
        return fname


def LocateFileName(fileNamesString, searchPaths):
    """Locate a file name, anywhere on the search path.

    If the file can not be located, prompt the user to find it for us
    (using a common OpenFile dialog)

    Raises KeyboardInterrupt if the user cancels.
    """
    import os

    import regutil

    fileNames = fileNamesString.split(";")
    for path in searchPaths:
        for fileName in fileNames:
            try:
                retPath = os.path.join(path, fileName)
                os.stat(retPath)
                break
            except OSError:
                retPath = None
        if retPath:
            break
    else:
        fileName = fileNames[0]
        try:
            import win32con
            import win32ui
        except ImportError:
            raise error(
                "Need to locate the file %s, but the win32ui module is not available\nPlease run the program again, passing as a parameter the path to this file."
                % fileName
            )
        # Display a common dialog to locate the file.
        flags = win32con.OFN_FILEMUSTEXIST
        ext = os.path.splitext(fileName)[1]
        filter = f"Files of requested type (*{ext})|*{ext}||"
        dlg = win32ui.CreateFileDialog(1, None, fileName, flags, filter, None)
        dlg.SetOFNTitle("Locate " + fileName)
        if dlg.DoModal() != win32con.IDOK:
            raise KeyboardInterrupt("User cancelled the process")
        retPath = dlg.GetPathName()
    return os.path.abspath(retPath)


def LocatePath(fileName, searchPaths):
    """Like LocateFileName, but returns a directory only."""
    import os

    return os.path.abspath(os.path.split(LocateFileName(fileName, searchPaths))[0])


def LocateOptionalPath(fileName, searchPaths):
    """Like LocatePath, but returns None if the user cancels."""
    try:
        return LocatePath(fileName, searchPaths)
    except KeyboardInterrupt:
        return None


def LocateOptionalFileName(fileName, searchPaths=None):
    """Like LocateFileName, but returns None if the user cancels."""
    try:
        return LocateFileName(fileName, searchPaths)
    except KeyboardInterrupt:
        return None


def LocatePythonCore(searchPaths):
    """Locate and validate the core Python directories.  Returns a list
    of paths that should be used as the core (ie, un-named) portion of
    the Python path.
    """
    import os

    import regutil

    currentPath = regutil.GetRegisteredNamedPath(None)
    if currentPath:
        presearchPaths = currentPath.split(";")
    else:
        presearchPaths = [os.path.abspath(".")]
    libPath = None
    for path in presearchPaths:
        if FileExists(os.path.join(path, "os.py")):
            libPath = path
            break
    if libPath is None and searchPaths is not None:
        libPath = LocatePath("os.py", searchPaths)
    if libPath is None:
        raise error("The core Python library could not be located.")

    corePath = None
    suffix = IsDebug()
    for path in presearchPaths:
        if FileExists(os.path.join(path, "unicodedata%s.pyd" % suffix)):
            corePath = path
            break
    if corePath is None and searchPaths is not None:
        corePath = LocatePath("unicodedata%s.pyd" % suffix, searchPaths)
    if corePath is None:
        raise error("The core Python path could not be located.")

    installPath = os.path.abspath(os.path.join(libPath, ".."))
    return installPath, [libPath, corePath]


def FindRegisterPackage(packageName, knownFile, searchPaths, registryAppName=None):
    """Find and Register a package.

    Assumes the core registry setup correctly.

    In addition, if the location located by the package is already
    in the **core** path, then an entry is registered, but no path.
    (no other paths are checked, as the application whose path was used
    may later be uninstalled.  This should not happen with the core)
    """

    import regutil

    if not packageName:
        raise error("A package name must be supplied")
    corePaths = regutil.GetRegisteredNamedPath(None).split(";")
    if not searchPaths:
        searchPaths = corePaths
    registryAppName = registryAppName or packageName
    try:
        pathLook, pathAdd = FindPackagePath(packageName, knownFile, searchPaths)
        if pathAdd is not None:
            if pathAdd in corePaths:
                pathAdd = ""
            regutil.RegisterNamedPath(registryAppName, pathAdd)
        return pathLook
    except error as details:
        print(f"*** The {packageName} package could not be registered - {details}")
        print(
            "*** Please ensure you have passed the correct paths on the command line."
        )
        print(
            "*** - For packages, you should pass a path to the packages parent directory,"
        )
        print("*** - and not the package directory itself...")


def FindRegisterApp(appName, knownFiles, searchPaths):
    """Find and Register a package.

    Assumes the core registry setup correctly.

    """

    import regutil

    if isinstance(knownFiles, str):
        knownFiles = [knownFiles]
    paths = []
    try:
        for knownFile in knownFiles:
            pathLook = FindAppPath(appName, knownFile, searchPaths)
            if pathLook:
                paths.append(pathLook)
    except error as details:
        print("*** ", details)
        return

    regutil.RegisterNamedPath(appName, ";".join(paths))


def FindRegisterPythonExe(exeAlias, searchPaths, actualFileNames=None):
    """Find and Register a Python exe (not necessarily *the* python.exe)

    Assumes the core registry setup correctly.
    """

    import regutil

    fname, ok = FindPythonExe(exeAlias, actualFileNames, searchPaths)
    if not ok:
        regutil.RegisterPythonExe(fname, exeAlias)
    return fname


def FindRegisterHelpFile(helpFile, searchPaths, helpDesc=None):
    import regutil

    try:
        pathLook = FindHelpPath(helpFile, helpDesc, searchPaths)
    except error as details:
        print("*** ", details)
        return
    # print(f"{helpFile} found at {pathLook}")
    regutil.RegisterHelpFile(helpFile, pathLook, helpDesc)


def SetupCore(searchPaths):
    """Setup the core Python information in the registry.

    This function makes no assumptions about the current state of sys.path.

    After this function has completed, you should have access to the standard
    Python library, and the standard Win32 extensions
    """

    import sys

    for path in searchPaths:
        sys.path.append(path)

    import os

    import regutil
    import win32api
    import win32con

    installPath, corePaths = LocatePythonCore(searchPaths)
    # Register the core Pythonpath.
    print(corePaths)
    regutil.RegisterNamedPath(None, ";".join(corePaths))

    # Register the install path.
    hKey = win32api.RegCreateKey(regutil.GetRootKey(), regutil.BuildDefaultPythonKey())
    try:
        # Core Paths.
        win32api.RegSetValue(hKey, "InstallPath", win32con.REG_SZ, installPath)
    finally:
        win32api.RegCloseKey(hKey)

    # Register the win32 core paths.
    win32paths = (
        os.path.abspath(os.path.split(win32api.__file__)[0])
        + ";"
        + os.path.abspath(
            os.path.split(LocateFileName("win32con.py;win32con.pyc", sys.path))[0]
        )
    )

    # Python has builtin support for finding a "DLLs" directory, but
    # not a PCBuild.  Having it in the core paths means it is ignored when
    # an EXE not in the Python dir is hosting us - so we add it as a named
    # value
    check = os.path.join(sys.prefix, "PCBuild")
    if "64 bit" in sys.version:
        check = os.path.join(check, "amd64")
    if os.path.isdir(check):
        regutil.RegisterNamedPath("PCBuild", check)


def RegisterShellInfo(searchPaths):
    """Registers key parts of the Python installation with the Windows Shell.

    Assumes a valid, minimal Python installation exists
    (ie, SetupCore() has been previously successfully run)
    """
    import regutil
    import win32con

    suffix = IsDebug()
    # Set up a pointer to the .exe's
    exePath = FindRegisterPythonExe("Python%s.exe" % suffix, searchPaths)
    regutil.SetRegistryDefaultValue(".py", "Python.File", win32con.HKEY_CLASSES_ROOT)
    regutil.RegisterShellCommand("Open", QuotedFileName(exePath) + ' "%1" %*', "&Run")
    regutil.SetRegistryDefaultValue(
        "Python.File\\DefaultIcon", "%s,0" % exePath, win32con.HKEY_CLASSES_ROOT
    )

    FindRegisterHelpFile("Python.hlp", searchPaths, "Main Python Documentation")
    FindRegisterHelpFile("ActivePython.chm", searchPaths, "Main Python Documentation")

    # We consider the win32 core, as it contains all the win32 api type
    # stuff we need.


#       FindRegisterApp("win32", ["win32con.pyc", "win32api%s.pyd" % suffix], searchPaths)

usage = """\
regsetup.py - Setup/maintain the registry for Python apps.

Run without options, (but possibly search paths) to repair a totally broken
python registry setup.  This should allow other options to work.

Usage:   %s [options ...] paths ...
-p packageName  -- Find and register a package.  Looks in the paths for
                   a sub-directory with the name of the package, and
                   adds a path entry for the package.
-a appName      -- Unconditionally add an application name to the path.
                   A new path entry is create with the app name, and the
                   paths specified are added to the registry.
-c              -- Add the specified paths to the core Pythonpath.
                   If a path appears on the core path, and a package also
                   needs that same path, the package will not bother
                   registering it.  Therefore, By adding paths to the
                   core path, you can avoid packages re-registering the same path.
-m filename     -- Find and register the specific file name as a module.
                   Do not include a path on the filename!
--shell         -- Register everything with the Win95/NT shell.
--upackage name -- Unregister the package
--uapp name     -- Unregister the app (identical to --upackage)
--umodule name  -- Unregister the module

--description   -- Print a description of the usage.
--examples      -- Print examples of usage.
""" % sys.argv[0]

description = """\
If no options are processed, the program attempts to validate and set
the standard Python path to the point where the standard library is
available.  This can be handy if you move Python to a new drive/sub-directory,
in which case most of the options would fail (as they need at least string.py,
os.py etc to function.)
Running without options should repair Python well enough to run with
the other options.

paths are search paths that the program will use to seek out a file.
For example, when registering the core Python, you may wish to
provide paths to non-standard places to look for the Python help files,
library files, etc.

See also the "regcheck.py" utility which will check and dump the contents
of the registry.
"""

# Using raw string so that all paths meant to be copied read correctly inline and when printed
examples = r"""
Examples:
"regsetup c:\weird\spot\1 c:\weird\spot\2"
Attempts to setup the core Python.  Looks in some standard places,
as well as the 2 weird spots to locate the core Python files (eg, Python.exe,
pythonXX.dll, the standard library and Win32 Extensions).

"regsetup -a myappname . .\subdir"
Registers a new Pythonpath entry named myappname, with "C:\I\AM\HERE" and
"C:\I\AM\HERE\subdir" added to the path (ie, all args are converted to
absolute paths)

"regsetup -c c:\my\python\files"
Unconditionally add "c:\my\python\files" to the 'core' Python path.

"regsetup -m some.pyd \windows\system"
Register the module some.pyd in \windows\system as a registered
module.  This will allow some.pyd to be imported, even though the
windows system directory is not (usually!) on the Python Path.

"regsetup --umodule some"
Unregister the module "some".  This means normal import rules then apply
for that module.
"""

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["/?", "-?", "-help", "-h"]:
        print(usage)
    elif len(sys.argv) == 1 or not sys.argv[1][0] in ["/", "-"]:
        # No args, or useful args.
        searchPath = sys.path[:]
        for arg in sys.argv[1:]:
            searchPath.append(arg)
        # Good chance we are being run from the "regsetup.py" directory.
        # Typically this will be "\somewhere\win32\Scripts" and the
        # "somewhere" and "..\Lib" should also be searched.
        searchPath.append("..\\Build")
        searchPath.append("..\\Lib")
        searchPath.append("..")
        searchPath.append("..\\..")

        # for developers:
        # also search somewhere\lib, ..\build, and ..\..\build
        searchPath.append("..\\..\\lib")
        searchPath.append("..\\build")
        if "64 bit" in sys.version:
            searchPath.append("..\\..\\pcbuild\\amd64")
        else:
            searchPath.append("..\\..\\pcbuild")

        print("Attempting to setup/repair the Python core")

        SetupCore(searchPath)
        RegisterShellInfo(searchPath)
        FindRegisterHelpFile("PyWin32.chm", searchPath, "Pythonwin Reference")
        # Check the registry.
        print("Registration complete - checking the registry...")
        import regcheck

        regcheck.CheckRegistry()
    else:
        searchPaths = []
        import getopt

        opts, args = getopt.getopt(
            sys.argv[1:],
            "p:a:m:c",
            ["shell", "upackage=", "uapp=", "umodule=", "description", "examples"],
        )
        for arg in args:
            searchPaths.append(arg)
        for o, a in opts:
            if o == "--description":
                print(description)
            if o == "--examples":
                print(examples)
            if o == "--shell":
                print("Registering the Python core.")
                RegisterShellInfo(searchPaths)
            if o == "-p":
                print("Registering package", a)
                FindRegisterPackage(a, None, searchPaths)
            if o in ["--upackage", "--uapp"]:
                import regutil

                print("Unregistering application/package", a)
                regutil.UnregisterNamedPath(a)
            if o == "-a":
                import regutil

                path = ";".join(searchPaths)
                print("Registering application", a, "to path", path)
                regutil.RegisterNamedPath(a, path)
            if o == "-c":
                if not len(searchPaths):
                    raise error("-c option must provide at least one additional path")
                import regutil

                currentPaths = regutil.GetRegisteredNamedPath(None).split(";")
                oldLen = len(currentPaths)
                for newPath in searchPaths:
                    if newPath not in currentPaths:
                        currentPaths.append(newPath)
                if len(currentPaths) != oldLen:
                    print(
                        "Registering %d new core paths" % (len(currentPaths) - oldLen)
                    )
                    regutil.RegisterNamedPath(None, ";".join(currentPaths))
                else:
                    print("All specified paths are already registered.")

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\_debug_adapter\__main__pydevd_gen_debug_adapter_protocol.py ===
"""
Run this module to regenerate the `pydevd_schema.py` file.

Note that it'll generate it based on the current debugProtocol.json. Erase it and rerun
to download the latest version.
"""


def is_variable_to_translate(cls_name, var_name):
    if var_name in ("variablesReference", "frameId", "threadId"):
        return True

    if cls_name == "StackFrame" and var_name == "id":
        # It's frameId everywhere except on StackFrame.
        return True

    if cls_name == "Thread" and var_name == "id":
        # It's threadId everywhere except on Thread.
        return True

    return False


def _get_noqa_for_var(prop_name):
    return "  # noqa (assign to builtin)" if prop_name in ("type", "format", "id", "hex", "breakpoint", "filter") else ""


class _OrderedSet(object):
    # Not a good ordered set (just something to be small without adding any deps)

    def __init__(self, initial_contents=None):
        self._contents = []
        self._contents_as_set = set()
        if initial_contents is not None:
            for x in initial_contents:
                self.add(x)

    def add(self, x):
        if x not in self._contents_as_set:
            self._contents_as_set.add(x)
            self._contents.append(x)

    def discard(self, x):
        if x in self._contents_as_set:
            self._contents_as_set.remove(x)
            self._contents.remove(x)

    def copy(self):
        return _OrderedSet(self._contents)

    def update(self, contents):
        for x in contents:
            self.add(x)

    def __iter__(self):
        return iter(self._contents)

    def __contains__(self, item):
        return item in self._contents_as_set

    def __len__(self):
        return len(self._contents)

    def set_repr(self):
        if len(self) == 0:
            return "set()"

        lst = [repr(x) for x in self]
        return "set([" + ", ".join(lst) + "])"


class Ref(object):
    def __init__(self, ref, ref_data):
        self.ref = ref
        self.ref_data = ref_data

    def __str__(self):
        return self.ref


def load_schema_data():
    import os.path
    import json

    json_file = os.path.join(os.path.dirname(__file__), "debugProtocol.json")
    if not os.path.exists(json_file):
        import requests

        req = requests.get("https://raw.githubusercontent.com/microsoft/debug-adapter-protocol/gh-pages/debugAdapterProtocol.json")
        assert req.status_code == 200
        with open(json_file, "wb") as stream:
            stream.write(req.content)

    with open(json_file, "rb") as json_contents:
        json_schema_data = json.loads(json_contents.read())
    return json_schema_data


def load_custom_schema_data():
    import os.path
    import json

    json_file = os.path.join(os.path.dirname(__file__), "debugProtocolCustom.json")

    with open(json_file, "rb") as json_contents:
        json_schema_data = json.loads(json_contents.read())
    return json_schema_data


def create_classes_to_generate_structure(json_schema_data):
    definitions = json_schema_data["definitions"]

    class_to_generatees = {}

    for name, definition in definitions.items():
        all_of = definition.get("allOf")
        description = definition.get("description")
        is_enum = definition.get("type") == "string" and "enum" in definition
        enum_values = None
        if is_enum:
            enum_values = definition["enum"]
        properties = {}
        properties.update(definition.get("properties", {}))
        required = _OrderedSet(definition.get("required", _OrderedSet()))
        base_definitions = []

        if all_of is not None:
            for definition in all_of:
                ref = definition.get("$ref")
                if ref is not None:
                    assert ref.startswith("#/definitions/")
                    ref = ref[len("#/definitions/") :]
                    base_definitions.append(ref)
                else:
                    if not description:
                        description = definition.get("description")
                    properties.update(definition.get("properties", {}))
                    required.update(_OrderedSet(definition.get("required", _OrderedSet())))

        if isinstance(description, (list, tuple)):
            description = "\n".join(description)

        if name == "ModulesRequest":  # Hack to accept modules request without arguments (ptvsd: 2050).
            required.discard("arguments")
        class_to_generatees[name] = dict(
            name=name,
            properties=properties,
            base_definitions=base_definitions,
            description=description,
            required=required,
            is_enum=is_enum,
            enum_values=enum_values,
        )
    return class_to_generatees


def collect_bases(curr_class, classes_to_generate, memo=None):
    ret = []
    if memo is None:
        memo = {}

    base_definitions = curr_class["base_definitions"]
    for base_definition in base_definitions:
        if base_definition not in memo:
            ret.append(base_definition)
            ret.extend(collect_bases(classes_to_generate[base_definition], classes_to_generate, memo))

    return ret


def fill_properties_and_required_from_base(classes_to_generate):
    # Now, resolve properties based on refs
    for class_to_generate in classes_to_generate.values():
        dct = {}
        s = _OrderedSet()

        for base_definition in reversed(collect_bases(class_to_generate, classes_to_generate)):
            # Note: go from base to current so that the initial order of the properties has that
            # same order.
            dct.update(classes_to_generate[base_definition].get("properties", {}))
            s.update(classes_to_generate[base_definition].get("required", _OrderedSet()))

        dct.update(class_to_generate["properties"])
        class_to_generate["properties"] = dct

        s.update(class_to_generate["required"])
        class_to_generate["required"] = s

    return class_to_generate


def update_class_to_generate_description(class_to_generate):
    import textwrap

    description = class_to_generate["description"]
    lines = []
    for line in description.splitlines():
        wrapped = textwrap.wrap(line.strip(), 100)
        lines.extend(wrapped)
        lines.append("")

    while lines and lines[-1] == "":
        lines = lines[:-1]

    class_to_generate["description"] = "    " + ("\n    ".join(lines))


def update_class_to_generate_type(classes_to_generate, class_to_generate):
    properties = class_to_generate.get("properties")
    for _prop_name, prop_val in properties.items():
        prop_type = prop_val.get("type", "")
        if not prop_type:
            prop_type = prop_val.pop("$ref", "")
            if prop_type:
                assert prop_type.startswith("#/definitions/")
                prop_type = prop_type[len("#/definitions/") :]
                prop_val["type"] = Ref(prop_type, classes_to_generate[prop_type])


def update_class_to_generate_register_dec(classes_to_generate, class_to_generate):
    # Default
    class_to_generate["register_request"] = ""
    class_to_generate["register_dec"] = "@register"

    properties = class_to_generate.get("properties")
    enum_type = properties.get("type", {}).get("enum")
    command = None
    event = None
    if enum_type and len(enum_type) == 1 and next(iter(enum_type)) in ("request", "response", "event"):
        msg_type = next(iter(enum_type))
        if msg_type == "response":
            # The actual command is typed in the request
            response_name = class_to_generate["name"]
            request_name = response_name[: -len("Response")] + "Request"
            if request_name in classes_to_generate:
                command = classes_to_generate[request_name]["properties"].get("command")
            else:
                if response_name == "ErrorResponse":
                    command = {"enum": ["error"]}
                else:
                    raise AssertionError("Unhandled: %s" % (response_name,))

        elif msg_type == "request":
            command = properties.get("command")

        elif msg_type == "event":
            command = properties.get("event")

        else:
            raise AssertionError("Unexpected condition.")

        if command:
            enum = command.get("enum")
            if enum and len(enum) == 1:
                class_to_generate["register_request"] = "@register_%s(%r)\n" % (msg_type, enum[0])


def extract_prop_name_and_prop(class_to_generate):
    properties = class_to_generate.get("properties")
    required = _OrderedSet(class_to_generate.get("required", _OrderedSet()))

    # Sort so that required come first
    prop_name_and_prop = list(properties.items())

    def compute_sort_key(x):
        key = x[0]
        if key in required:
            if key == "seq":
                return 0.5  # seq when required is after the other required keys (to have a default of -1).
            return 0
        return 1

    prop_name_and_prop.sort(key=compute_sort_key)

    return prop_name_and_prop


def update_class_to_generate_to_json(class_to_generate):
    required = _OrderedSet(class_to_generate.get("required", _OrderedSet()))
    prop_name_and_prop = extract_prop_name_and_prop(class_to_generate)

    to_dict_body = ["def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)"]

    translate_prop_names = []
    for prop_name, prop in prop_name_and_prop:
        if is_variable_to_translate(class_to_generate["name"], prop_name):
            translate_prop_names.append(prop_name)

    for prop_name, prop in prop_name_and_prop:
        namespace = dict(prop_name=prop_name, noqa=_get_noqa_for_var(prop_name))
        to_dict_body.append("    %(prop_name)s = self.%(prop_name)s%(noqa)s" % namespace)

        if prop.get("type") == "array":
            to_dict_body.append('    if %(prop_name)s and hasattr(%(prop_name)s[0], "to_dict"):' % namespace)
            to_dict_body.append("        %(prop_name)s = [x.to_dict() for x in %(prop_name)s]" % namespace)

    if translate_prop_names:
        to_dict_body.append("    if update_ids_to_dap:")
        for prop_name in translate_prop_names:
            namespace = dict(prop_name=prop_name, noqa=_get_noqa_for_var(prop_name))
            to_dict_body.append("        if %(prop_name)s is not None:" % namespace)
            to_dict_body.append("            %(prop_name)s = self._translate_id_to_dap(%(prop_name)s)%(noqa)s" % namespace)

    if not translate_prop_names:
        update_dict_ids_from_dap_body = []
    else:
        update_dict_ids_from_dap_body = ["", "", "@classmethod", "def update_dict_ids_from_dap(cls, dct):"]
        for prop_name in translate_prop_names:
            namespace = dict(prop_name=prop_name)
            update_dict_ids_from_dap_body.append("    if %(prop_name)r in dct:" % namespace)
            update_dict_ids_from_dap_body.append("        dct[%(prop_name)r] = cls._translate_id_from_dap(dct[%(prop_name)r])" % namespace)
        update_dict_ids_from_dap_body.append("    return dct")

    class_to_generate["update_dict_ids_from_dap"] = _indent_lines("\n".join(update_dict_ids_from_dap_body))

    to_dict_body.append("    dct = {")
    first_not_required = False

    for prop_name, prop in prop_name_and_prop:
        use_to_dict = prop["type"].__class__ == Ref and not prop["type"].ref_data.get("is_enum", False)
        is_array = prop["type"] == "array"
        ref_array_cls_name = ""
        if is_array:
            ref = prop["items"].get("$ref")
            if ref is not None:
                ref_array_cls_name = ref.split("/")[-1]

        namespace = dict(prop_name=prop_name, ref_array_cls_name=ref_array_cls_name)
        if prop_name in required:
            if use_to_dict:
                to_dict_body.append("        %(prop_name)r: %(prop_name)s.to_dict(update_ids_to_dap=update_ids_to_dap)," % namespace)
            else:
                if ref_array_cls_name:
                    to_dict_body.append(
                        "        %(prop_name)r: [%(ref_array_cls_name)s.update_dict_ids_to_dap(o) for o in %(prop_name)s] if (update_ids_to_dap and %(prop_name)s) else %(prop_name)s,"
                        % namespace
                    )
                else:
                    to_dict_body.append("        %(prop_name)r: %(prop_name)s," % namespace)
        else:
            if not first_not_required:
                first_not_required = True
                to_dict_body.append("    }")

            to_dict_body.append("    if %(prop_name)s is not None:" % namespace)
            if use_to_dict:
                to_dict_body.append("        dct[%(prop_name)r] = %(prop_name)s.to_dict(update_ids_to_dap=update_ids_to_dap)" % namespace)
            else:
                if ref_array_cls_name:
                    to_dict_body.append(
                        "        dct[%(prop_name)r] = [%(ref_array_cls_name)s.update_dict_ids_to_dap(o) for o in %(prop_name)s] if (update_ids_to_dap and %(prop_name)s) else %(prop_name)s"
                        % namespace
                    )
                else:
                    to_dict_body.append("        dct[%(prop_name)r] = %(prop_name)s" % namespace)

    if not first_not_required:
        first_not_required = True
        to_dict_body.append("    }")

    to_dict_body.append("    dct.update(self.kwargs)")
    to_dict_body.append("    return dct")

    class_to_generate["to_dict"] = _indent_lines("\n".join(to_dict_body))

    if not translate_prop_names:
        update_dict_ids_to_dap_body = []
    else:
        update_dict_ids_to_dap_body = ["", "", "@classmethod", "def update_dict_ids_to_dap(cls, dct):"]
        for prop_name in translate_prop_names:
            namespace = dict(prop_name=prop_name)
            update_dict_ids_to_dap_body.append("    if %(prop_name)r in dct:" % namespace)
            update_dict_ids_to_dap_body.append("        dct[%(prop_name)r] = cls._translate_id_to_dap(dct[%(prop_name)r])" % namespace)
        update_dict_ids_to_dap_body.append("    return dct")

    class_to_generate["update_dict_ids_to_dap"] = _indent_lines("\n".join(update_dict_ids_to_dap_body))


def update_class_to_generate_init(class_to_generate):
    args = []
    init_body = []
    docstring = []

    required = _OrderedSet(class_to_generate.get("required", _OrderedSet()))
    prop_name_and_prop = extract_prop_name_and_prop(class_to_generate)

    translate_prop_names = []
    for prop_name, prop in prop_name_and_prop:
        if is_variable_to_translate(class_to_generate["name"], prop_name):
            translate_prop_names.append(prop_name)

        enum = prop.get("enum")
        if enum and len(enum) == 1:
            init_body.append("    self.%(prop_name)s = %(enum)r" % dict(prop_name=prop_name, enum=next(iter(enum))))
        else:
            if prop_name in required:
                if prop_name == "seq":
                    args.append(prop_name + "=-1")
                else:
                    args.append(prop_name)
            else:
                args.append(prop_name + "=None")

            if prop["type"].__class__ == Ref:
                ref = prop["type"]
                ref_data = ref.ref_data
                if ref_data.get("is_enum", False):
                    init_body.append("    if %s is not None:" % (prop_name,))
                    init_body.append("        assert %s in %s.VALID_VALUES" % (prop_name, str(ref)))
                    init_body.append("    self.%(prop_name)s = %(prop_name)s" % dict(prop_name=prop_name))
                else:
                    namespace = dict(prop_name=prop_name, ref_name=str(ref))
                    init_body.append("    if %(prop_name)s is None:" % namespace)
                    init_body.append("        self.%(prop_name)s = %(ref_name)s()" % namespace)
                    init_body.append("    else:")
                    init_body.append(
                        "        self.%(prop_name)s = %(ref_name)s(update_ids_from_dap=update_ids_from_dap, **%(prop_name)s) if %(prop_name)s.__class__ !=  %(ref_name)s else %(prop_name)s"
                        % namespace
                    )

            else:
                init_body.append("    self.%(prop_name)s = %(prop_name)s" % dict(prop_name=prop_name))

                if prop["type"] == "array":
                    ref = prop["items"].get("$ref")
                    if ref is not None:
                        ref_array_cls_name = ref.split("/")[-1]
                        init_body.append("    if update_ids_from_dap and self.%(prop_name)s:" % dict(prop_name=prop_name))
                        init_body.append("        for o in self.%(prop_name)s:" % dict(prop_name=prop_name))
                        init_body.append(
                            "            %(ref_array_cls_name)s.update_dict_ids_from_dap(o)" % dict(ref_array_cls_name=ref_array_cls_name)
                        )

        prop_type = prop["type"]
        prop_description = prop.get("description", "")

        if isinstance(prop_description, (list, tuple)):
            prop_description = "\n    ".join(prop_description)

        docstring.append(
            ":param %(prop_type)s %(prop_name)s: %(prop_description)s"
            % dict(prop_type=prop_type, prop_name=prop_name, prop_description=prop_description)
        )

    if translate_prop_names:
        init_body.append("    if update_ids_from_dap:")
        for prop_name in translate_prop_names:
            init_body.append("        self.%(prop_name)s = self._translate_id_from_dap(self.%(prop_name)s)" % dict(prop_name=prop_name))

    docstring = _indent_lines("\n".join(docstring))
    init_body = "\n".join(init_body)

    # Actually bundle the whole __init__ from the parts.
    args = ", ".join(args)
    if args:
        args = ", " + args

    # Note: added kwargs because some messages are expected to be extended by the user (so, we'll actually
    # make all extendable so that we don't have to worry about which ones -- we loose a little on typing,
    # but may be better than doing a allow list based on something only pointed out in the documentation).
    class_to_generate[
        "init"
    ] = '''def __init__(self%(args)s, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
    """
%(docstring)s
    """
%(init_body)s
    self.kwargs = kwargs
''' % dict(args=args, init_body=init_body, docstring=docstring)

    class_to_generate["init"] = _indent_lines(class_to_generate["init"])


def update_class_to_generate_props(class_to_generate):
    import json

    def default(o):
        if isinstance(o, Ref):
            return o.ref
        raise AssertionError("Unhandled: %s" % (o,))

    properties = class_to_generate["properties"]
    class_to_generate["props"] = (
        "    __props__ = %s" % _indent_lines(json.dumps(properties, indent=4, default=default).replace("true", "True")).strip()
    )


def update_class_to_generate_refs(class_to_generate):
    properties = class_to_generate["properties"]
    class_to_generate["refs"] = (
        "    __refs__ = %s" % _OrderedSet(key for (key, val) in properties.items() if val["type"].__class__ == Ref).set_repr()
    )


def update_class_to_generate_enums(class_to_generate):
    class_to_generate["enums"] = ""
    if class_to_generate.get("is_enum", False):
        enums = ""
        for enum in class_to_generate["enum_values"]:
            enums += "    %s = %r\n" % (enum.upper(), enum)
        enums += "\n"
        enums += "    VALID_VALUES = %s\n\n" % _OrderedSet(class_to_generate["enum_values"]).set_repr()
        class_to_generate["enums"] = enums


def update_class_to_generate_objects(classes_to_generate, class_to_generate):
    properties = class_to_generate["properties"]
    for key, val in properties.items():
        if "type" not in val:
            val["type"] = "TypeNA"
            continue

        if val["type"] == "object":
            create_new = val.copy()
            create_new.update(
                {
                    "name": "%s%s" % (class_to_generate["name"], key.title()),
                    "description": '    "%s" of %s' % (key, class_to_generate["name"]),
                }
            )
            if "properties" not in create_new:
                create_new["properties"] = {}

            assert create_new["name"] not in classes_to_generate
            classes_to_generate[create_new["name"]] = create_new

            update_class_to_generate_type(classes_to_generate, create_new)
            update_class_to_generate_props(create_new)

            # Update nested object types
            update_class_to_generate_objects(classes_to_generate, create_new)

            val["type"] = Ref(create_new["name"], classes_to_generate[create_new["name"]])
            val.pop("properties", None)


def gen_debugger_protocol():
    import os.path
    import sys

    if sys.version_info[:2] < (3, 6):
        raise AssertionError("Must be run with Python 3.6 onwards (to keep dict order).")

    classes_to_generate = create_classes_to_generate_structure(load_schema_data())
    classes_to_generate.update(create_classes_to_generate_structure(load_custom_schema_data()))

    class_to_generate = fill_properties_and_required_from_base(classes_to_generate)

    for class_to_generate in list(classes_to_generate.values()):
        update_class_to_generate_description(class_to_generate)
        update_class_to_generate_type(classes_to_generate, class_to_generate)
        update_class_to_generate_props(class_to_generate)
        update_class_to_generate_objects(classes_to_generate, class_to_generate)

    for class_to_generate in classes_to_generate.values():
        update_class_to_generate_refs(class_to_generate)
        update_class_to_generate_init(class_to_generate)
        update_class_to_generate_enums(class_to_generate)
        update_class_to_generate_to_json(class_to_generate)
        update_class_to_generate_register_dec(classes_to_generate, class_to_generate)

    class_template = '''
%(register_request)s%(register_dec)s
class %(name)s(BaseSchema):
    """
%(description)s

    Note: automatically generated code. Do not edit manually.
    """

%(enums)s%(props)s
%(refs)s

    __slots__ = list(__props__.keys()) + ['kwargs']

%(init)s%(update_dict_ids_from_dap)s

%(to_dict)s%(update_dict_ids_to_dap)s
'''

    contents = []
    contents.append("# coding: utf-8")
    contents.append("# Automatically generated code.")
    contents.append("# Do not edit manually.")
    contents.append("# Generated by running: %s" % os.path.basename(__file__))
    contents.append("from .pydevd_base_schema import BaseSchema, register, register_request, register_response, register_event")
    contents.append("")
    for class_to_generate in classes_to_generate.values():
        contents.append(class_template % class_to_generate)

    parent_dir = os.path.dirname(__file__)
    schema = os.path.join(parent_dir, "pydevd_schema.py")
    with open(schema, "w", encoding="utf-8") as stream:
        stream.write("\n".join(contents))


def _indent_lines(lines, indent="    "):
    out_lines = []
    for line in lines.splitlines(keepends=True):
        out_lines.append(indent + line)

    return "".join(out_lines)


if __name__ == "__main__":
    gen_debugger_protocol()

# === NexusCore/openenv\Lib\site-packages\aiohttp\web.py ===
import asyncio
import logging
import os
import socket
import sys
import warnings
from argparse import ArgumentParser
from collections.abc import Iterable
from contextlib import suppress
from importlib import import_module
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Iterable as TypingIterable,
    List,
    Optional,
    Set,
    Type,
    Union,
    cast,
)

from .abc import AbstractAccessLogger
from .helpers import AppKey as AppKey
from .log import access_logger
from .typedefs import PathLike
from .web_app import Application as Application, CleanupError as CleanupError
from .web_exceptions import (
    HTTPAccepted as HTTPAccepted,
    HTTPBadGateway as HTTPBadGateway,
    HTTPBadRequest as HTTPBadRequest,
    HTTPClientError as HTTPClientError,
    HTTPConflict as HTTPConflict,
    HTTPCreated as HTTPCreated,
    HTTPError as HTTPError,
    HTTPException as HTTPException,
    HTTPExpectationFailed as HTTPExpectationFailed,
    HTTPFailedDependency as HTTPFailedDependency,
    HTTPForbidden as HTTPForbidden,
    HTTPFound as HTTPFound,
    HTTPGatewayTimeout as HTTPGatewayTimeout,
    HTTPGone as HTTPGone,
    HTTPInsufficientStorage as HTTPInsufficientStorage,
    HTTPInternalServerError as HTTPInternalServerError,
    HTTPLengthRequired as HTTPLengthRequired,
    HTTPMethodNotAllowed as HTTPMethodNotAllowed,
    HTTPMisdirectedRequest as HTTPMisdirectedRequest,
    HTTPMove as HTTPMove,
    HTTPMovedPermanently as HTTPMovedPermanently,
    HTTPMultipleChoices as HTTPMultipleChoices,
    HTTPNetworkAuthenticationRequired as HTTPNetworkAuthenticationRequired,
    HTTPNoContent as HTTPNoContent,
    HTTPNonAuthoritativeInformation as HTTPNonAuthoritativeInformation,
    HTTPNotAcceptable as HTTPNotAcceptable,
    HTTPNotExtended as HTTPNotExtended,
    HTTPNotFound as HTTPNotFound,
    HTTPNotImplemented as HTTPNotImplemented,
    HTTPNotModified as HTTPNotModified,
    HTTPOk as HTTPOk,
    HTTPPartialContent as HTTPPartialContent,
    HTTPPaymentRequired as HTTPPaymentRequired,
    HTTPPermanentRedirect as HTTPPermanentRedirect,
    HTTPPreconditionFailed as HTTPPreconditionFailed,
    HTTPPreconditionRequired as HTTPPreconditionRequired,
    HTTPProxyAuthenticationRequired as HTTPProxyAuthenticationRequired,
    HTTPRedirection as HTTPRedirection,
    HTTPRequestEntityTooLarge as HTTPRequestEntityTooLarge,
    HTTPRequestHeaderFieldsTooLarge as HTTPRequestHeaderFieldsTooLarge,
    HTTPRequestRangeNotSatisfiable as HTTPRequestRangeNotSatisfiable,
    HTTPRequestTimeout as HTTPRequestTimeout,
    HTTPRequestURITooLong as HTTPRequestURITooLong,
    HTTPResetContent as HTTPResetContent,
    HTTPSeeOther as HTTPSeeOther,
    HTTPServerError as HTTPServerError,
    HTTPServiceUnavailable as HTTPServiceUnavailable,
    HTTPSuccessful as HTTPSuccessful,
    HTTPTemporaryRedirect as HTTPTemporaryRedirect,
    HTTPTooManyRequests as HTTPTooManyRequests,
    HTTPUnauthorized as HTTPUnauthorized,
    HTTPUnavailableForLegalReasons as HTTPUnavailableForLegalReasons,
    HTTPUnprocessableEntity as HTTPUnprocessableEntity,
    HTTPUnsupportedMediaType as HTTPUnsupportedMediaType,
    HTTPUpgradeRequired as HTTPUpgradeRequired,
    HTTPUseProxy as HTTPUseProxy,
    HTTPVariantAlsoNegotiates as HTTPVariantAlsoNegotiates,
    HTTPVersionNotSupported as HTTPVersionNotSupported,
    NotAppKeyWarning as NotAppKeyWarning,
)
from .web_fileresponse import FileResponse as FileResponse
from .web_log import AccessLogger
from .web_middlewares import (
    middleware as middleware,
    normalize_path_middleware as normalize_path_middleware,
)
from .web_protocol import (
    PayloadAccessError as PayloadAccessError,
    RequestHandler as RequestHandler,
    RequestPayloadError as RequestPayloadError,
)
from .web_request import (
    BaseRequest as BaseRequest,
    FileField as FileField,
    Request as Request,
)
from .web_response import (
    ContentCoding as ContentCoding,
    Response as Response,
    StreamResponse as StreamResponse,
    json_response as json_response,
)
from .web_routedef import (
    AbstractRouteDef as AbstractRouteDef,
    RouteDef as RouteDef,
    RouteTableDef as RouteTableDef,
    StaticDef as StaticDef,
    delete as delete,
    get as get,
    head as head,
    options as options,
    patch as patch,
    post as post,
    put as put,
    route as route,
    static as static,
    view as view,
)
from .web_runner import (
    AppRunner as AppRunner,
    BaseRunner as BaseRunner,
    BaseSite as BaseSite,
    GracefulExit as GracefulExit,
    NamedPipeSite as NamedPipeSite,
    ServerRunner as ServerRunner,
    SockSite as SockSite,
    TCPSite as TCPSite,
    UnixSite as UnixSite,
)
from .web_server import Server as Server
from .web_urldispatcher import (
    AbstractResource as AbstractResource,
    AbstractRoute as AbstractRoute,
    DynamicResource as DynamicResource,
    PlainResource as PlainResource,
    PrefixedSubAppResource as PrefixedSubAppResource,
    Resource as Resource,
    ResourceRoute as ResourceRoute,
    StaticResource as StaticResource,
    UrlDispatcher as UrlDispatcher,
    UrlMappingMatchInfo as UrlMappingMatchInfo,
    View as View,
)
from .web_ws import (
    WebSocketReady as WebSocketReady,
    WebSocketResponse as WebSocketResponse,
    WSMsgType as WSMsgType,
)

__all__ = (
    # web_app
    "AppKey",
    "Application",
    "CleanupError",
    # web_exceptions
    "NotAppKeyWarning",
    "HTTPAccepted",
    "HTTPBadGateway",
    "HTTPBadRequest",
    "HTTPClientError",
    "HTTPConflict",
    "HTTPCreated",
    "HTTPError",
    "HTTPException",
    "HTTPExpectationFailed",
    "HTTPFailedDependency",
    "HTTPForbidden",
    "HTTPFound",
    "HTTPGatewayTimeout",
    "HTTPGone",
    "HTTPInsufficientStorage",
    "HTTPInternalServerError",
    "HTTPLengthRequired",
    "HTTPMethodNotAllowed",
    "HTTPMisdirectedRequest",
    "HTTPMove",
    "HTTPMovedPermanently",
    "HTTPMultipleChoices",
    "HTTPNetworkAuthenticationRequired",
    "HTTPNoContent",
    "HTTPNonAuthoritativeInformation",
    "HTTPNotAcceptable",
    "HTTPNotExtended",
    "HTTPNotFound",
    "HTTPNotImplemented",
    "HTTPNotModified",
    "HTTPOk",
    "HTTPPartialContent",
    "HTTPPaymentRequired",
    "HTTPPermanentRedirect",
    "HTTPPreconditionFailed",
    "HTTPPreconditionRequired",
    "HTTPProxyAuthenticationRequired",
    "HTTPRedirection",
    "HTTPRequestEntityTooLarge",
    "HTTPRequestHeaderFieldsTooLarge",
    "HTTPRequestRangeNotSatisfiable",
    "HTTPRequestTimeout",
    "HTTPRequestURITooLong",
    "HTTPResetContent",
    "HTTPSeeOther",
    "HTTPServerError",
    "HTTPServiceUnavailable",
    "HTTPSuccessful",
    "HTTPTemporaryRedirect",
    "HTTPTooManyRequests",
    "HTTPUnauthorized",
    "HTTPUnavailableForLegalReasons",
    "HTTPUnprocessableEntity",
    "HTTPUnsupportedMediaType",
    "HTTPUpgradeRequired",
    "HTTPUseProxy",
    "HTTPVariantAlsoNegotiates",
    "HTTPVersionNotSupported",
    # web_fileresponse
    "FileResponse",
    # web_middlewares
    "middleware",
    "normalize_path_middleware",
    # web_protocol
    "PayloadAccessError",
    "RequestHandler",
    "RequestPayloadError",
    # web_request
    "BaseRequest",
    "FileField",
    "Request",
    # web_response
    "ContentCoding",
    "Response",
    "StreamResponse",
    "json_response",
    # web_routedef
    "AbstractRouteDef",
    "RouteDef",
    "RouteTableDef",
    "StaticDef",
    "delete",
    "get",
    "head",
    "options",
    "patch",
    "post",
    "put",
    "route",
    "static",
    "view",
    # web_runner
    "AppRunner",
    "BaseRunner",
    "BaseSite",
    "GracefulExit",
    "ServerRunner",
    "SockSite",
    "TCPSite",
    "UnixSite",
    "NamedPipeSite",
    # web_server
    "Server",
    # web_urldispatcher
    "AbstractResource",
    "AbstractRoute",
    "DynamicResource",
    "PlainResource",
    "PrefixedSubAppResource",
    "Resource",
    "ResourceRoute",
    "StaticResource",
    "UrlDispatcher",
    "UrlMappingMatchInfo",
    "View",
    # web_ws
    "WebSocketReady",
    "WebSocketResponse",
    "WSMsgType",
    # web
    "run_app",
)


if TYPE_CHECKING:
    from ssl import SSLContext
else:
    try:
        from ssl import SSLContext
    except ImportError:  # pragma: no cover
        SSLContext = object  # type: ignore[misc,assignment]

# Only display warning when using -Wdefault, -We, -X dev or similar.
warnings.filterwarnings("ignore", category=NotAppKeyWarning, append=True)

HostSequence = TypingIterable[str]


async def _run_app(
    app: Union[Application, Awaitable[Application]],
    *,
    host: Optional[Union[str, HostSequence]] = None,
    port: Optional[int] = None,
    path: Union[PathLike, TypingIterable[PathLike], None] = None,
    sock: Optional[Union[socket.socket, TypingIterable[socket.socket]]] = None,
    shutdown_timeout: float = 60.0,
    keepalive_timeout: float = 75.0,
    ssl_context: Optional[SSLContext] = None,
    print: Optional[Callable[..., None]] = print,
    backlog: int = 128,
    access_log_class: Type[AbstractAccessLogger] = AccessLogger,
    access_log_format: str = AccessLogger.LOG_FORMAT,
    access_log: Optional[logging.Logger] = access_logger,
    handle_signals: bool = True,
    reuse_address: Optional[bool] = None,
    reuse_port: Optional[bool] = None,
    handler_cancellation: bool = False,
) -> None:
    # An internal function to actually do all dirty job for application running
    if asyncio.iscoroutine(app):
        app = await app

    app = cast(Application, app)

    runner = AppRunner(
        app,
        handle_signals=handle_signals,
        access_log_class=access_log_class,
        access_log_format=access_log_format,
        access_log=access_log,
        keepalive_timeout=keepalive_timeout,
        shutdown_timeout=shutdown_timeout,
        handler_cancellation=handler_cancellation,
    )

    await runner.setup()

    sites: List[BaseSite] = []

    try:
        if host is not None:
            if isinstance(host, str):
                sites.append(
                    TCPSite(
                        runner,
                        host,
                        port,
                        ssl_context=ssl_context,
                        backlog=backlog,
                        reuse_address=reuse_address,
                        reuse_port=reuse_port,
                    )
                )
            else:
                for h in host:
                    sites.append(
                        TCPSite(
                            runner,
                            h,
                            port,
                            ssl_context=ssl_context,
                            backlog=backlog,
                            reuse_address=reuse_address,
                            reuse_port=reuse_port,
                        )
                    )
        elif path is None and sock is None or port is not None:
            sites.append(
                TCPSite(
                    runner,
                    port=port,
                    ssl_context=ssl_context,
                    backlog=backlog,
                    reuse_address=reuse_address,
                    reuse_port=reuse_port,
                )
            )

        if path is not None:
            if isinstance(path, (str, os.PathLike)):
                sites.append(
                    UnixSite(
                        runner,
                        path,
                        ssl_context=ssl_context,
                        backlog=backlog,
                    )
                )
            else:
                for p in path:
                    sites.append(
                        UnixSite(
                            runner,
                            p,
                            ssl_context=ssl_context,
                            backlog=backlog,
                        )
                    )

        if sock is not None:
            if not isinstance(sock, Iterable):
                sites.append(
                    SockSite(
                        runner,
                        sock,
                        ssl_context=ssl_context,
                        backlog=backlog,
                    )
                )
            else:
                for s in sock:
                    sites.append(
                        SockSite(
                            runner,
                            s,
                            ssl_context=ssl_context,
                            backlog=backlog,
                        )
                    )
        for site in sites:
            await site.start()

        if print:  # pragma: no branch
            names = sorted(str(s.name) for s in runner.sites)
            print(
                "======== Running on {} ========\n"
                "(Press CTRL+C to quit)".format(", ".join(names))
            )

        # sleep forever by 1 hour intervals,
        while True:
            await asyncio.sleep(3600)
    finally:
        await runner.cleanup()


def _cancel_tasks(
    to_cancel: Set["asyncio.Task[Any]"], loop: asyncio.AbstractEventLoop
) -> None:
    if not to_cancel:
        return

    for task in to_cancel:
        task.cancel()

    loop.run_until_complete(asyncio.gather(*to_cancel, return_exceptions=True))

    for task in to_cancel:
        if task.cancelled():
            continue
        if task.exception() is not None:
            loop.call_exception_handler(
                {
                    "message": "unhandled exception during asyncio.run() shutdown",
                    "exception": task.exception(),
                    "task": task,
                }
            )


def run_app(
    app: Union[Application, Awaitable[Application]],
    *,
    host: Optional[Union[str, HostSequence]] = None,
    port: Optional[int] = None,
    path: Union[PathLike, TypingIterable[PathLike], None] = None,
    sock: Optional[Union[socket.socket, TypingIterable[socket.socket]]] = None,
    shutdown_timeout: float = 60.0,
    keepalive_timeout: float = 75.0,
    ssl_context: Optional[SSLContext] = None,
    print: Optional[Callable[..., None]] = print,
    backlog: int = 128,
    access_log_class: Type[AbstractAccessLogger] = AccessLogger,
    access_log_format: str = AccessLogger.LOG_FORMAT,
    access_log: Optional[logging.Logger] = access_logger,
    handle_signals: bool = True,
    reuse_address: Optional[bool] = None,
    reuse_port: Optional[bool] = None,
    handler_cancellation: bool = False,
    loop: Optional[asyncio.AbstractEventLoop] = None,
) -> None:
    """Run an app locally"""
    if loop is None:
        loop = asyncio.new_event_loop()

    # Configure if and only if in debugging mode and using the default logger
    if loop.get_debug() and access_log and access_log.name == "aiohttp.access":
        if access_log.level == logging.NOTSET:
            access_log.setLevel(logging.DEBUG)
        if not access_log.hasHandlers():
            access_log.addHandler(logging.StreamHandler())

    main_task = loop.create_task(
        _run_app(
            app,
            host=host,
            port=port,
            path=path,
            sock=sock,
            shutdown_timeout=shutdown_timeout,
            keepalive_timeout=keepalive_timeout,
            ssl_context=ssl_context,
            print=print,
            backlog=backlog,
            access_log_class=access_log_class,
            access_log_format=access_log_format,
            access_log=access_log,
            handle_signals=handle_signals,
            reuse_address=reuse_address,
            reuse_port=reuse_port,
            handler_cancellation=handler_cancellation,
        )
    )

    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main_task)
    except (GracefulExit, KeyboardInterrupt):  # pragma: no cover
        pass
    finally:
        try:
            main_task.cancel()
            with suppress(asyncio.CancelledError):
                loop.run_until_complete(main_task)
        finally:
            _cancel_tasks(asyncio.all_tasks(loop), loop)
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()


def main(argv: List[str]) -> None:
    arg_parser = ArgumentParser(
        description="aiohttp.web Application server", prog="aiohttp.web"
    )
    arg_parser.add_argument(
        "entry_func",
        help=(
            "Callable returning the `aiohttp.web.Application` instance to "
            "run. Should be specified in the 'module:function' syntax."
        ),
        metavar="entry-func",
    )
    arg_parser.add_argument(
        "-H",
        "--hostname",
        help="TCP/IP hostname to serve on (default: localhost)",
        default=None,
    )
    arg_parser.add_argument(
        "-P",
        "--port",
        help="TCP/IP port to serve on (default: %(default)r)",
        type=int,
        default=8080,
    )
    arg_parser.add_argument(
        "-U",
        "--path",
        help="Unix file system path to serve on. Can be combined with hostname "
        "to serve on both Unix and TCP.",
    )
    args, extra_argv = arg_parser.parse_known_args(argv)

    # Import logic
    mod_str, _, func_str = args.entry_func.partition(":")
    if not func_str or not mod_str:
        arg_parser.error("'entry-func' not in 'module:function' syntax")
    if mod_str.startswith("."):
        arg_parser.error("relative module names not supported")
    try:
        module = import_module(mod_str)
    except ImportError as ex:
        arg_parser.error(f"unable to import {mod_str}: {ex}")
    try:
        func = getattr(module, func_str)
    except AttributeError:
        arg_parser.error(f"module {mod_str!r} has no attribute {func_str!r}")

    # Compatibility logic
    if args.path is not None and not hasattr(socket, "AF_UNIX"):
        arg_parser.error(
            "file system paths not supported by your operating environment"
        )

    logging.basicConfig(level=logging.DEBUG)

    if args.path and args.hostname is None:
        host = port = None
    else:
        host = args.hostname or "localhost"
        port = args.port

    app = func(extra_argv)
    run_app(app, host=host, port=port, path=args.path)
    arg_parser.exit(message="Stopped\n")


if __name__ == "__main__":  # pragma: no branch
    main(sys.argv[1:])  # pragma: no cover

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\pydevd_code_to_source.py ===
"""
Decompiler that can be used with the debugger (where statements correctly represent the
line numbers).

Note: this is a work in progress / proof of concept / not ready to be used.
"""

import dis

from _pydevd_bundle.pydevd_collect_bytecode_info import iter_instructions
from _pydev_bundle import pydev_log
import sys
import inspect
from io import StringIO


class _Stack(object):
    def __init__(self):
        self._contents = []

    def push(self, obj):
        #         print('push', obj)
        self._contents.append(obj)

    def pop(self):
        return self._contents.pop(-1)


INDENT_MARKER = object()
DEDENT_MARKER = object()
_SENTINEL = object()

DEBUG = False


class _Token(object):
    def __init__(self, i_line, instruction=None, tok=_SENTINEL, priority=0, after=None, end_of_line=False):
        """
        :param i_line:
        :param instruction:
        :param tok:
        :param priority:
        :param after:
        :param end_of_line:
            Marker to signal only after all the other tokens have been written.
        """
        self.i_line = i_line
        if tok is not _SENTINEL:
            self.tok = tok
        else:
            if instruction is not None:
                if inspect.iscode(instruction.argval):
                    self.tok = ""
                else:
                    self.tok = str(instruction.argval)
            else:
                raise AssertionError("Either the tok or the instruction is needed.")
        self.instruction = instruction
        self.priority = priority
        self.end_of_line = end_of_line
        self._after_tokens = set()
        self._after_handler_tokens = set()
        if after:
            self.mark_after(after)

    def mark_after(self, v):
        if isinstance(v, _Token):
            self._after_tokens.add(v)
        elif isinstance(v, _BaseHandler):
            self._after_handler_tokens.add(v)

        else:
            raise AssertionError("Unhandled: %s" % (v,))

    def get_after_tokens(self):
        ret = self._after_tokens.copy()
        for handler in self._after_handler_tokens:
            ret.update(handler.tokens)
        return ret

    def __repr__(self):
        return "Token(%s, after: %s)" % (self.tok, self.get_after_tokens())

    __str__ = __repr__


class _Writer(object):
    def __init__(self):
        self.line_to_contents = {}
        self.all_tokens = set()

    def get_line(self, line):
        lst = self.line_to_contents.get(line)
        if lst is None:
            lst = self.line_to_contents[line] = []
        return lst

    def indent(self, line):
        self.get_line(line).append(INDENT_MARKER)

    def dedent(self, line):
        self.get_line(line).append(DEDENT_MARKER)

    def write(self, line, token):
        if token in self.all_tokens:
            return
        self.all_tokens.add(token)
        assert isinstance(token, _Token)
        lst = self.get_line(line)
        lst.append(token)


class _BaseHandler(object):
    def __init__(self, i_line, instruction, stack, writer, disassembler):
        self.i_line = i_line
        self.instruction = instruction
        self.stack = stack
        self.writer = writer
        self.disassembler = disassembler
        self.tokens = []
        self._handle()

    def _write_tokens(self):
        for token in self.tokens:
            self.writer.write(token.i_line, token)

    def _handle(self):
        raise NotImplementedError(self)

    def __repr__(self, *args, **kwargs):
        try:
            return "%s line:%s" % (self.instruction, self.i_line)
        except:
            return object.__repr__(self)

    __str__ = __repr__


_op_name_to_handler = {}


def _register(cls):
    _op_name_to_handler[cls.opname] = cls
    return cls


class _BasePushHandler(_BaseHandler):
    def _handle(self):
        self.stack.push(self)


class _BaseLoadHandler(_BasePushHandler):
    def _handle(self):
        _BasePushHandler._handle(self)
        self.tokens = [_Token(self.i_line, self.instruction)]


@_register
class _LoadBuildClass(_BasePushHandler):
    opname = "LOAD_BUILD_CLASS"


@_register
class _LoadConst(_BaseLoadHandler):
    opname = "LOAD_CONST"


@_register
class _LoadName(_BaseLoadHandler):
    opname = "LOAD_NAME"


@_register
class _LoadGlobal(_BaseLoadHandler):
    opname = "LOAD_GLOBAL"


@_register
class _LoadFast(_BaseLoadHandler):
    opname = "LOAD_FAST"


@_register
class _GetIter(_BaseHandler):
    """
    Implements TOS = iter(TOS).
    """

    opname = "GET_ITER"
    iter_target = None

    def _handle(self):
        self.iter_target = self.stack.pop()
        self.tokens.extend(self.iter_target.tokens)
        self.stack.push(self)


@_register
class _ForIter(_BaseHandler):
    """
    TOS is an iterator. Call its __next__() method. If this yields a new value, push it on the stack
    (leaving the iterator below it). If the iterator indicates it is exhausted TOS is popped, and
    the byte code counter is incremented by delta.
    """

    opname = "FOR_ITER"

    iter_in = None

    def _handle(self):
        self.iter_in = self.stack.pop()
        self.stack.push(self)

    def store_in_name(self, store_name):
        for_token = _Token(self.i_line, None, "for ")
        self.tokens.append(for_token)
        prev = for_token

        t_name = _Token(store_name.i_line, store_name.instruction, after=prev)
        self.tokens.append(t_name)
        prev = t_name

        in_token = _Token(store_name.i_line, None, " in ", after=prev)
        self.tokens.append(in_token)
        prev = in_token

        max_line = store_name.i_line
        if self.iter_in:
            for t in self.iter_in.tokens:
                t.mark_after(prev)
                max_line = max(max_line, t.i_line)
                prev = t
            self.tokens.extend(self.iter_in.tokens)

        colon_token = _Token(self.i_line, None, ":", after=prev)
        self.tokens.append(colon_token)
        prev = for_token

        self._write_tokens()


@_register
class _StoreName(_BaseHandler):
    """
    Implements name = TOS. namei is the index of name in the attribute co_names of the code object.
    The compiler tries to use STORE_FAST or STORE_GLOBAL if possible.
    """

    opname = "STORE_NAME"

    def _handle(self):
        v = self.stack.pop()

        if isinstance(v, _ForIter):
            v.store_in_name(self)
        else:
            if not isinstance(v, _MakeFunction) or v.is_lambda:
                line = self.i_line
                for t in v.tokens:
                    line = min(line, t.i_line)

                t_name = _Token(line, self.instruction)
                t_equal = _Token(line, None, "=", after=t_name)

                self.tokens.append(t_name)
                self.tokens.append(t_equal)

                for t in v.tokens:
                    t.mark_after(t_equal)
                self.tokens.extend(v.tokens)

                self._write_tokens()


@_register
class _ReturnValue(_BaseHandler):
    """
    Returns with TOS to the caller of the function.
    """

    opname = "RETURN_VALUE"

    def _handle(self):
        v = self.stack.pop()
        return_token = _Token(self.i_line, None, "return ", end_of_line=True)
        self.tokens.append(return_token)
        for token in v.tokens:
            token.mark_after(return_token)
        self.tokens.extend(v.tokens)

        self._write_tokens()


@_register
class _CallFunction(_BaseHandler):
    """

    CALL_FUNCTION(argc)

        Calls a callable object with positional arguments. argc indicates the number of positional
        arguments. The top of the stack contains positional arguments, with the right-most argument
        on top. Below the arguments is a callable object to call. CALL_FUNCTION pops all arguments
        and the callable object off the stack, calls the callable object with those arguments, and
        pushes the return value returned by the callable object.

        Changed in version 3.6: This opcode is used only for calls with positional arguments.

    """

    opname = "CALL_FUNCTION"

    def _handle(self):
        args = []
        for _i in range(self.instruction.argval + 1):
            arg = self.stack.pop()
            args.append(arg)
        it = reversed(args)
        name = next(it)
        max_line = name.i_line
        for t in name.tokens:
            self.tokens.append(t)

        tok_open_parens = _Token(name.i_line, None, "(", after=name)
        self.tokens.append(tok_open_parens)

        prev = tok_open_parens
        for i, arg in enumerate(it):
            for t in arg.tokens:
                t.mark_after(name)
                t.mark_after(prev)
                max_line = max(max_line, t.i_line)
                self.tokens.append(t)
            prev = arg

            if i > 0:
                comma_token = _Token(prev.i_line, None, ",", after=prev)
                self.tokens.append(comma_token)
                prev = comma_token

        tok_close_parens = _Token(max_line, None, ")", after=prev)
        self.tokens.append(tok_close_parens)

        self._write_tokens()

        self.stack.push(self)


@_register
class _MakeFunctionPy3(_BaseHandler):
    """
    Pushes a new function object on the stack. From bottom to top, the consumed stack must consist
    of values if the argument carries a specified flag value

        0x01 a tuple of default values for positional-only and positional-or-keyword parameters in positional order

        0x02 a dictionary of keyword-only parameters' default values

        0x04 an annotation dictionary

        0x08 a tuple containing cells for free variables, making a closure

        the code associated with the function (at TOS1)

        the qualified name of the function (at TOS)
    """

    opname = "MAKE_FUNCTION"
    is_lambda = False

    def _handle(self):
        stack = self.stack
        self.qualified_name = stack.pop()
        self.code = stack.pop()

        default_node = None
        if self.instruction.argval & 0x01:
            default_node = stack.pop()

        is_lambda = self.is_lambda = "<lambda>" in [x.tok for x in self.qualified_name.tokens]

        if not is_lambda:
            def_token = _Token(self.i_line, None, "def ")
            self.tokens.append(def_token)

        for token in self.qualified_name.tokens:
            self.tokens.append(token)
            if not is_lambda:
                token.mark_after(def_token)
        prev = token

        open_parens_token = _Token(self.i_line, None, "(", after=prev)
        self.tokens.append(open_parens_token)
        prev = open_parens_token

        code = self.code.instruction.argval

        if default_node:
            defaults = ([_SENTINEL] * (len(code.co_varnames) - len(default_node.instruction.argval))) + list(
                default_node.instruction.argval
            )
        else:
            defaults = [_SENTINEL] * len(code.co_varnames)

        for i, arg in enumerate(code.co_varnames):
            if i > 0:
                comma_token = _Token(prev.i_line, None, ", ", after=prev)
                self.tokens.append(comma_token)
                prev = comma_token

            arg_token = _Token(self.i_line, None, arg, after=prev)
            self.tokens.append(arg_token)

            default = defaults[i]
            if default is not _SENTINEL:
                eq_token = _Token(default_node.i_line, None, "=", after=prev)
                self.tokens.append(eq_token)
                prev = eq_token

                default_token = _Token(default_node.i_line, None, str(default), after=prev)
                self.tokens.append(default_token)
                prev = default_token

        tok_close_parens = _Token(prev.i_line, None, "):", after=prev)
        self.tokens.append(tok_close_parens)

        self._write_tokens()

        stack.push(self)
        self.writer.indent(prev.i_line + 1)
        self.writer.dedent(max(self.disassembler.merge_code(code)))


_MakeFunction = _MakeFunctionPy3


def _print_after_info(line_contents, stream=None):
    if stream is None:
        stream = sys.stdout
    for token in line_contents:
        after_tokens = token.get_after_tokens()
        if after_tokens:
            s = "%s after: %s\n" % (repr(token.tok), ('"' + '", "'.join(t.tok for t in token.get_after_tokens()) + '"'))
            stream.write(s)
        else:
            stream.write("%s      (NO REQUISITES)" % repr(token.tok))


def _compose_line_contents(line_contents, previous_line_tokens):
    lst = []
    handled = set()

    add_to_end_of_line = []
    delete_indexes = []
    for i, token in enumerate(line_contents):
        if token.end_of_line:
            add_to_end_of_line.append(token)
            delete_indexes.append(i)
    for i in reversed(delete_indexes):
        del line_contents[i]
    del delete_indexes

    while line_contents:
        added = False
        delete_indexes = []

        for i, token in enumerate(line_contents):
            after_tokens = token.get_after_tokens()
            for after in after_tokens:
                if after not in handled and after not in previous_line_tokens:
                    break
            else:
                added = True
                previous_line_tokens.add(token)
                handled.add(token)
                lst.append(token.tok)
                delete_indexes.append(i)

        for i in reversed(delete_indexes):
            del line_contents[i]

        if not added:
            if add_to_end_of_line:
                line_contents.extend(add_to_end_of_line)
                del add_to_end_of_line[:]
                continue

            # Something is off, let's just add as is.
            for token in line_contents:
                if token not in handled:
                    lst.append(token.tok)

            stream = StringIO()
            _print_after_info(line_contents, stream)
            pydev_log.critical("Error. After markers are not correct:\n%s", stream.getvalue())
            break
    return "".join(lst)


class _PyCodeToSource(object):
    def __init__(self, co, memo=None):
        if memo is None:
            memo = {}
        self.memo = memo
        self.co = co
        self.instructions = list(iter_instructions(co))
        self.stack = _Stack()
        self.writer = _Writer()

    def _process_next(self, i_line):
        instruction = self.instructions.pop(0)
        handler_class = _op_name_to_handler.get(instruction.opname)
        if handler_class is not None:
            s = handler_class(i_line, instruction, self.stack, self.writer, self)
            if DEBUG:
                print(s)

        else:
            if DEBUG:
                print("UNHANDLED", instruction)

    def build_line_to_contents(self):
        co = self.co

        op_offset_to_line = dict(dis.findlinestarts(co))
        curr_line_index = 0

        instructions = self.instructions
        while instructions:
            instruction = instructions[0]
            new_line_index = op_offset_to_line.get(instruction.offset)
            if new_line_index is not None:
                curr_line_index = new_line_index

            self._process_next(curr_line_index)
        return self.writer.line_to_contents

    def merge_code(self, code):
        if DEBUG:
            print("merge code ----")
        # for d in dir(code):
        #     if not d.startswith('_'):
        #         print(d, getattr(code, d))
        line_to_contents = _PyCodeToSource(code, self.memo).build_line_to_contents()
        lines = []
        for line, contents in sorted(line_to_contents.items()):
            lines.append(line)
            self.writer.get_line(line).extend(contents)
        if DEBUG:
            print("end merge code ----")
        return lines

    def disassemble(self):
        show_lines = False
        line_to_contents = self.build_line_to_contents()
        stream = StringIO()
        last_line = 0
        indent = ""
        previous_line_tokens = set()
        for i_line, contents in sorted(line_to_contents.items()):
            while last_line < i_line - 1:
                if show_lines:
                    stream.write("%s.\n" % (last_line + 1,))
                else:
                    stream.write("\n")
                last_line += 1

            line_contents = []
            dedents_found = 0
            for part in contents:
                if part is INDENT_MARKER:
                    if DEBUG:
                        print("found indent", i_line)
                    indent += "    "
                    continue
                if part is DEDENT_MARKER:
                    if DEBUG:
                        print("found dedent", i_line)
                    dedents_found += 1
                    continue
                line_contents.append(part)

            s = indent + _compose_line_contents(line_contents, previous_line_tokens)
            if show_lines:
                stream.write("%s. %s\n" % (i_line, s))
            else:
                stream.write("%s\n" % s)

            if dedents_found:
                indent = indent[: -(4 * dedents_found)]
            last_line = i_line

        return stream.getvalue()


def code_obj_to_source(co):
    """
    Converts a code object to source code to provide a suitable representation for the compiler when
    the actual source code is not found.

    This is a work in progress / proof of concept / not ready to be used.
    """
    ret = _PyCodeToSource(co).disassemble()
    if DEBUG:
        print(ret)
    return ret

# === NexusCore/myenv\Lib\site-packages\pip\_internal\models\link.py ===
import functools
import itertools
import logging
import os
import posixpath
import re
import urllib.parse
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Mapping,
    NamedTuple,
    Optional,
    Tuple,
    Union,
)

from pip._internal.utils.deprecation import deprecated
from pip._internal.utils.filetypes import WHEEL_EXTENSION
from pip._internal.utils.hashes import Hashes
from pip._internal.utils.misc import (
    pairwise,
    redact_auth_from_url,
    split_auth_from_netloc,
    splitext,
)
from pip._internal.utils.urls import path_to_url, url_to_path

if TYPE_CHECKING:
    from pip._internal.index.collector import IndexContent

logger = logging.getLogger(__name__)


# Order matters, earlier hashes have a precedence over later hashes for what
# we will pick to use.
_SUPPORTED_HASHES = ("sha512", "sha384", "sha256", "sha224", "sha1", "md5")


@dataclass(frozen=True)
class LinkHash:
    """Links to content may have embedded hash values. This class parses those.

    `name` must be any member of `_SUPPORTED_HASHES`.

    This class can be converted to and from `ArchiveInfo`. While ArchiveInfo intends to
    be JSON-serializable to conform to PEP 610, this class contains the logic for
    parsing a hash name and value for correctness, and then checking whether that hash
    conforms to a schema with `.is_hash_allowed()`."""

    name: str
    value: str

    _hash_url_fragment_re = re.compile(
        # NB: we do not validate that the second group (.*) is a valid hex
        # digest. Instead, we simply keep that string in this class, and then check it
        # against Hashes when hash-checking is needed. This is easier to debug than
        # proactively discarding an invalid hex digest, as we handle incorrect hashes
        # and malformed hashes in the same place.
        r"[#&]({choices})=([^&]*)".format(
            choices="|".join(re.escape(hash_name) for hash_name in _SUPPORTED_HASHES)
        ),
    )

    def __post_init__(self) -> None:
        assert self.name in _SUPPORTED_HASHES

    @classmethod
    @functools.lru_cache(maxsize=None)
    def find_hash_url_fragment(cls, url: str) -> Optional["LinkHash"]:
        """Search a string for a checksum algorithm name and encoded output value."""
        match = cls._hash_url_fragment_re.search(url)
        if match is None:
            return None
        name, value = match.groups()
        return cls(name=name, value=value)

    def as_dict(self) -> Dict[str, str]:
        return {self.name: self.value}

    def as_hashes(self) -> Hashes:
        """Return a Hashes instance which checks only for the current hash."""
        return Hashes({self.name: [self.value]})

    def is_hash_allowed(self, hashes: Optional[Hashes]) -> bool:
        """
        Return True if the current hash is allowed by `hashes`.
        """
        if hashes is None:
            return False
        return hashes.is_hash_allowed(self.name, hex_digest=self.value)


@dataclass(frozen=True)
class MetadataFile:
    """Information about a core metadata file associated with a distribution."""

    hashes: Optional[Dict[str, str]]

    def __post_init__(self) -> None:
        if self.hashes is not None:
            assert all(name in _SUPPORTED_HASHES for name in self.hashes)


def supported_hashes(hashes: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
    # Remove any unsupported hash types from the mapping. If this leaves no
    # supported hashes, return None
    if hashes is None:
        return None
    hashes = {n: v for n, v in hashes.items() if n in _SUPPORTED_HASHES}
    if not hashes:
        return None
    return hashes


def _clean_url_path_part(part: str) -> str:
    """
    Clean a "part" of a URL path (i.e. after splitting on "@" characters).
    """
    # We unquote prior to quoting to make sure nothing is double quoted.
    return urllib.parse.quote(urllib.parse.unquote(part))


def _clean_file_url_path(part: str) -> str:
    """
    Clean the first part of a URL path that corresponds to a local
    filesystem path (i.e. the first part after splitting on "@" characters).
    """
    # We unquote prior to quoting to make sure nothing is double quoted.
    # Also, on Windows the path part might contain a drive letter which
    # should not be quoted. On Linux where drive letters do not
    # exist, the colon should be quoted. We rely on urllib.request
    # to do the right thing here.
    return urllib.request.pathname2url(urllib.request.url2pathname(part))


# percent-encoded:                   /
_reserved_chars_re = re.compile("(@|%2F)", re.IGNORECASE)


def _clean_url_path(path: str, is_local_path: bool) -> str:
    """
    Clean the path portion of a URL.
    """
    if is_local_path:
        clean_func = _clean_file_url_path
    else:
        clean_func = _clean_url_path_part

    # Split on the reserved characters prior to cleaning so that
    # revision strings in VCS URLs are properly preserved.
    parts = _reserved_chars_re.split(path)

    cleaned_parts = []
    for to_clean, reserved in pairwise(itertools.chain(parts, [""])):
        cleaned_parts.append(clean_func(to_clean))
        # Normalize %xx escapes (e.g. %2f -> %2F)
        cleaned_parts.append(reserved.upper())

    return "".join(cleaned_parts)


def _ensure_quoted_url(url: str) -> str:
    """
    Make sure a link is fully quoted.
    For example, if ' ' occurs in the URL, it will be replaced with "%20",
    and without double-quoting other characters.
    """
    # Split the URL into parts according to the general structure
    # `scheme://netloc/path?query#fragment`.
    result = urllib.parse.urlsplit(url)
    # If the netloc is empty, then the URL refers to a local filesystem path.
    is_local_path = not result.netloc
    path = _clean_url_path(result.path, is_local_path=is_local_path)
    return urllib.parse.urlunsplit(result._replace(path=path))


def _absolute_link_url(base_url: str, url: str) -> str:
    """
    A faster implementation of urllib.parse.urljoin with a shortcut
    for absolute http/https URLs.
    """
    if url.startswith(("https://", "http://")):
        return url
    else:
        return urllib.parse.urljoin(base_url, url)


@functools.total_ordering
class Link:
    """Represents a parsed link from a Package Index's simple URL"""

    __slots__ = [
        "_parsed_url",
        "_url",
        "_path",
        "_hashes",
        "comes_from",
        "requires_python",
        "yanked_reason",
        "metadata_file_data",
        "cache_link_parsing",
        "egg_fragment",
    ]

    def __init__(
        self,
        url: str,
        comes_from: Optional[Union[str, "IndexContent"]] = None,
        requires_python: Optional[str] = None,
        yanked_reason: Optional[str] = None,
        metadata_file_data: Optional[MetadataFile] = None,
        cache_link_parsing: bool = True,
        hashes: Optional[Mapping[str, str]] = None,
    ) -> None:
        """
        :param url: url of the resource pointed to (href of the link)
        :param comes_from: instance of IndexContent where the link was found,
            or string.
        :param requires_python: String containing the `Requires-Python`
            metadata field, specified in PEP 345. This may be specified by
            a data-requires-python attribute in the HTML link tag, as
            described in PEP 503.
        :param yanked_reason: the reason the file has been yanked, if the
            file has been yanked, or None if the file hasn't been yanked.
            This is the value of the "data-yanked" attribute, if present, in
            a simple repository HTML link. If the file has been yanked but
            no reason was provided, this should be the empty string. See
            PEP 592 for more information and the specification.
        :param metadata_file_data: the metadata attached to the file, or None if
            no such metadata is provided. This argument, if not None, indicates
            that a separate metadata file exists, and also optionally supplies
            hashes for that file.
        :param cache_link_parsing: A flag that is used elsewhere to determine
            whether resources retrieved from this link should be cached. PyPI
            URLs should generally have this set to False, for example.
        :param hashes: A mapping of hash names to digests to allow us to
            determine the validity of a download.
        """

        # The comes_from, requires_python, and metadata_file_data arguments are
        # only used by classmethods of this class, and are not used in client
        # code directly.

        # url can be a UNC windows share
        if url.startswith("\\\\"):
            url = path_to_url(url)

        self._parsed_url = urllib.parse.urlsplit(url)
        # Store the url as a private attribute to prevent accidentally
        # trying to set a new value.
        self._url = url
        # The .path property is hot, so calculate its value ahead of time.
        self._path = urllib.parse.unquote(self._parsed_url.path)

        link_hash = LinkHash.find_hash_url_fragment(url)
        hashes_from_link = {} if link_hash is None else link_hash.as_dict()
        if hashes is None:
            self._hashes = hashes_from_link
        else:
            self._hashes = {**hashes, **hashes_from_link}

        self.comes_from = comes_from
        self.requires_python = requires_python if requires_python else None
        self.yanked_reason = yanked_reason
        self.metadata_file_data = metadata_file_data

        self.cache_link_parsing = cache_link_parsing
        self.egg_fragment = self._egg_fragment()

    @classmethod
    def from_json(
        cls,
        file_data: Dict[str, Any],
        page_url: str,
    ) -> Optional["Link"]:
        """
        Convert an pypi json document from a simple repository page into a Link.
        """
        file_url = file_data.get("url")
        if file_url is None:
            return None

        url = _ensure_quoted_url(_absolute_link_url(page_url, file_url))
        pyrequire = file_data.get("requires-python")
        yanked_reason = file_data.get("yanked")
        hashes = file_data.get("hashes", {})

        # PEP 714: Indexes must use the name core-metadata, but
        # clients should support the old name as a fallback for compatibility.
        metadata_info = file_data.get("core-metadata")
        if metadata_info is None:
            metadata_info = file_data.get("dist-info-metadata")

        # The metadata info value may be a boolean, or a dict of hashes.
        if isinstance(metadata_info, dict):
            # The file exists, and hashes have been supplied
            metadata_file_data = MetadataFile(supported_hashes(metadata_info))
        elif metadata_info:
            # The file exists, but there are no hashes
            metadata_file_data = MetadataFile(None)
        else:
            # False or not present: the file does not exist
            metadata_file_data = None

        # The Link.yanked_reason expects an empty string instead of a boolean.
        if yanked_reason and not isinstance(yanked_reason, str):
            yanked_reason = ""
        # The Link.yanked_reason expects None instead of False.
        elif not yanked_reason:
            yanked_reason = None

        return cls(
            url,
            comes_from=page_url,
            requires_python=pyrequire,
            yanked_reason=yanked_reason,
            hashes=hashes,
            metadata_file_data=metadata_file_data,
        )

    @classmethod
    def from_element(
        cls,
        anchor_attribs: Dict[str, Optional[str]],
        page_url: str,
        base_url: str,
    ) -> Optional["Link"]:
        """
        Convert an anchor element's attributes in a simple repository page to a Link.
        """
        href = anchor_attribs.get("href")
        if not href:
            return None

        url = _ensure_quoted_url(_absolute_link_url(base_url, href))
        pyrequire = anchor_attribs.get("data-requires-python")
        yanked_reason = anchor_attribs.get("data-yanked")

        # PEP 714: Indexes must use the name data-core-metadata, but
        # clients should support the old name as a fallback for compatibility.
        metadata_info = anchor_attribs.get("data-core-metadata")
        if metadata_info is None:
            metadata_info = anchor_attribs.get("data-dist-info-metadata")
        # The metadata info value may be the string "true", or a string of
        # the form "hashname=hashval"
        if metadata_info == "true":
            # The file exists, but there are no hashes
            metadata_file_data = MetadataFile(None)
        elif metadata_info is None:
            # The file does not exist
            metadata_file_data = None
        else:
            # The file exists, and hashes have been supplied
            hashname, sep, hashval = metadata_info.partition("=")
            if sep == "=":
                metadata_file_data = MetadataFile(supported_hashes({hashname: hashval}))
            else:
                # Error - data is wrong. Treat as no hashes supplied.
                logger.debug(
                    "Index returned invalid data-dist-info-metadata value: %s",
                    metadata_info,
                )
                metadata_file_data = MetadataFile(None)

        return cls(
            url,
            comes_from=page_url,
            requires_python=pyrequire,
            yanked_reason=yanked_reason,
            metadata_file_data=metadata_file_data,
        )

    def __str__(self) -> str:
        if self.requires_python:
            rp = f" (requires-python:{self.requires_python})"
        else:
            rp = ""
        if self.comes_from:
            return f"{redact_auth_from_url(self._url)} (from {self.comes_from}){rp}"
        else:
            return redact_auth_from_url(str(self._url))

    def __repr__(self) -> str:
        return f"<Link {self}>"

    def __hash__(self) -> int:
        return hash(self.url)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Link):
            return NotImplemented
        return self.url == other.url

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, Link):
            return NotImplemented
        return self.url < other.url

    @property
    def url(self) -> str:
        return self._url

    @property
    def filename(self) -> str:
        path = self.path.rstrip("/")
        name = posixpath.basename(path)
        if not name:
            # Make sure we don't leak auth information if the netloc
            # includes a username and password.
            netloc, user_pass = split_auth_from_netloc(self.netloc)
            return netloc

        name = urllib.parse.unquote(name)
        assert name, f"URL {self._url!r} produced no filename"
        return name

    @property
    def file_path(self) -> str:
        return url_to_path(self.url)

    @property
    def scheme(self) -> str:
        return self._parsed_url.scheme

    @property
    def netloc(self) -> str:
        """
        This can contain auth information.
        """
        return self._parsed_url.netloc

    @property
    def path(self) -> str:
        return self._path

    def splitext(self) -> Tuple[str, str]:
        return splitext(posixpath.basename(self.path.rstrip("/")))

    @property
    def ext(self) -> str:
        return self.splitext()[1]

    @property
    def url_without_fragment(self) -> str:
        scheme, netloc, path, query, fragment = self._parsed_url
        return urllib.parse.urlunsplit((scheme, netloc, path, query, ""))

    _egg_fragment_re = re.compile(r"[#&]egg=([^&]*)")

    # Per PEP 508.
    _project_name_re = re.compile(
        r"^([A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9])$", re.IGNORECASE
    )

    def _egg_fragment(self) -> Optional[str]:
        match = self._egg_fragment_re.search(self._url)
        if not match:
            return None

        # An egg fragment looks like a PEP 508 project name, along with
        # an optional extras specifier. Anything else is invalid.
        project_name = match.group(1)
        if not self._project_name_re.match(project_name):
            deprecated(
                reason=f"{self} contains an egg fragment with a non-PEP 508 name.",
                replacement="to use the req @ url syntax, and remove the egg fragment",
                gone_in="25.1",
                issue=13157,
            )

        return project_name

    _subdirectory_fragment_re = re.compile(r"[#&]subdirectory=([^&]*)")

    @property
    def subdirectory_fragment(self) -> Optional[str]:
        match = self._subdirectory_fragment_re.search(self._url)
        if not match:
            return None
        return match.group(1)

    def metadata_link(self) -> Optional["Link"]:
        """Return a link to the associated core metadata file (if any)."""
        if self.metadata_file_data is None:
            return None
        metadata_url = f"{self.url_without_fragment}.metadata"
        if self.metadata_file_data.hashes is None:
            return Link(metadata_url)
        return Link(metadata_url, hashes=self.metadata_file_data.hashes)

    def as_hashes(self) -> Hashes:
        return Hashes({k: [v] for k, v in self._hashes.items()})

    @property
    def hash(self) -> Optional[str]:
        return next(iter(self._hashes.values()), None)

    @property
    def hash_name(self) -> Optional[str]:
        return next(iter(self._hashes), None)

    @property
    def show_url(self) -> str:
        return posixpath.basename(self._url.split("#", 1)[0].split("?", 1)[0])

    @property
    def is_file(self) -> bool:
        return self.scheme == "file"

    def is_existing_dir(self) -> bool:
        return self.is_file and os.path.isdir(self.file_path)

    @property
    def is_wheel(self) -> bool:
        return self.ext == WHEEL_EXTENSION

    @property
    def is_vcs(self) -> bool:
        from pip._internal.vcs import vcs

        return self.scheme in vcs.all_schemes

    @property
    def is_yanked(self) -> bool:
        return self.yanked_reason is not None

    @property
    def has_hash(self) -> bool:
        return bool(self._hashes)

    def is_hash_allowed(self, hashes: Optional[Hashes]) -> bool:
        """
        Return True if the link has a hash and it is allowed by `hashes`.
        """
        if hashes is None:
            return False
        return any(hashes.is_hash_allowed(k, v) for k, v in self._hashes.items())


class _CleanResult(NamedTuple):
    """Convert link for equivalency check.

    This is used in the resolver to check whether two URL-specified requirements
    likely point to the same distribution and can be considered equivalent. This
    equivalency logic avoids comparing URLs literally, which can be too strict
    (e.g. "a=1&b=2" vs "b=2&a=1") and produce conflicts unexpecting to users.

    Currently this does three things:

    1. Drop the basic auth part. This is technically wrong since a server can
       serve different content based on auth, but if it does that, it is even
       impossible to guarantee two URLs without auth are equivalent, since
       the user can input different auth information when prompted. So the
       practical solution is to assume the auth doesn't affect the response.
    2. Parse the query to avoid the ordering issue. Note that ordering under the
       same key in the query are NOT cleaned; i.e. "a=1&a=2" and "a=2&a=1" are
       still considered different.
    3. Explicitly drop most of the fragment part, except ``subdirectory=`` and
       hash values, since it should have no impact the downloaded content. Note
       that this drops the "egg=" part historically used to denote the requested
       project (and extras), which is wrong in the strictest sense, but too many
       people are supplying it inconsistently to cause superfluous resolution
       conflicts, so we choose to also ignore them.
    """

    parsed: urllib.parse.SplitResult
    query: Dict[str, List[str]]
    subdirectory: str
    hashes: Dict[str, str]


def _clean_link(link: Link) -> _CleanResult:
    parsed = link._parsed_url
    netloc = parsed.netloc.rsplit("@", 1)[-1]
    # According to RFC 8089, an empty host in file: means localhost.
    if parsed.scheme == "file" and not netloc:
        netloc = "localhost"
    fragment = urllib.parse.parse_qs(parsed.fragment)
    if "egg" in fragment:
        logger.debug("Ignoring egg= fragment in %s", link)
    try:
        # If there are multiple subdirectory values, use the first one.
        # This matches the behavior of Link.subdirectory_fragment.
        subdirectory = fragment["subdirectory"][0]
    except (IndexError, KeyError):
        subdirectory = ""
    # If there are multiple hash values under the same algorithm, use the
    # first one. This matches the behavior of Link.hash_value.
    hashes = {k: fragment[k][0] for k in _SUPPORTED_HASHES if k in fragment}
    return _CleanResult(
        parsed=parsed._replace(netloc=netloc, query="", fragment=""),
        query=urllib.parse.parse_qs(parsed.query),
        subdirectory=subdirectory,
        hashes=hashes,
    )


@functools.lru_cache(maxsize=None)
def links_equivalent(link1: Link, link2: Link) -> bool:
    return _clean_link(link1) == _clean_link(link2)

# === NexusCore/openenv\Lib\site-packages\PIL\ImageFilter.py ===
#
# The Python Imaging Library.
# $Id$
#
# standard filters
#
# History:
# 1995-11-27 fl   Created
# 2002-06-08 fl   Added rank and mode filters
# 2003-09-15 fl   Fixed rank calculation in rank filter; added expand call
#
# Copyright (c) 1997-2003 by Secret Labs AB.
# Copyright (c) 1995-2002 by Fredrik Lundh.
#
# See the README file for information on usage and redistribution.
#
from __future__ import annotations

import abc
import functools
from collections.abc import Sequence
from types import ModuleType
from typing import Any, Callable, cast

TYPE_CHECKING = False
if TYPE_CHECKING:
    from . import _imaging
    from ._typing import NumpyArray


class Filter(abc.ABC):
    @abc.abstractmethod
    def filter(self, image: _imaging.ImagingCore) -> _imaging.ImagingCore:
        pass


class MultibandFilter(Filter):
    pass


class BuiltinFilter(MultibandFilter):
    filterargs: tuple[Any, ...]

    def filter(self, image: _imaging.ImagingCore) -> _imaging.ImagingCore:
        if image.mode == "P":
            msg = "cannot filter palette images"
            raise ValueError(msg)
        return image.filter(*self.filterargs)


class Kernel(BuiltinFilter):
    """
    Create a convolution kernel. This only supports 3x3 and 5x5 integer and floating
    point kernels.

    Kernels can only be applied to "L" and "RGB" images.

    :param size: Kernel size, given as (width, height). This must be (3,3) or (5,5).
    :param kernel: A sequence containing kernel weights. The kernel will be flipped
                   vertically before being applied to the image.
    :param scale: Scale factor. If given, the result for each pixel is divided by this
                  value. The default is the sum of the kernel weights.
    :param offset: Offset. If given, this value is added to the result, after it has
                   been divided by the scale factor.
    """

    name = "Kernel"

    def __init__(
        self,
        size: tuple[int, int],
        kernel: Sequence[float],
        scale: float | None = None,
        offset: float = 0,
    ) -> None:
        if scale is None:
            # default scale is sum of kernel
            scale = functools.reduce(lambda a, b: a + b, kernel)
        if size[0] * size[1] != len(kernel):
            msg = "not enough coefficients in kernel"
            raise ValueError(msg)
        self.filterargs = size, scale, offset, kernel


class RankFilter(Filter):
    """
    Create a rank filter.  The rank filter sorts all pixels in
    a window of the given size, and returns the ``rank``'th value.

    :param size: The kernel size, in pixels.
    :param rank: What pixel value to pick.  Use 0 for a min filter,
                 ``size * size / 2`` for a median filter, ``size * size - 1``
                 for a max filter, etc.
    """

    name = "Rank"

    def __init__(self, size: int, rank: int) -> None:
        self.size = size
        self.rank = rank

    def filter(self, image: _imaging.ImagingCore) -> _imaging.ImagingCore:
        if image.mode == "P":
            msg = "cannot filter palette images"
            raise ValueError(msg)
        image = image.expand(self.size // 2, self.size // 2)
        return image.rankfilter(self.size, self.rank)


class MedianFilter(RankFilter):
    """
    Create a median filter. Picks the median pixel value in a window with the
    given size.

    :param size: The kernel size, in pixels.
    """

    name = "Median"

    def __init__(self, size: int = 3) -> None:
        self.size = size
        self.rank = size * size // 2


class MinFilter(RankFilter):
    """
    Create a min filter.  Picks the lowest pixel value in a window with the
    given size.

    :param size: The kernel size, in pixels.
    """

    name = "Min"

    def __init__(self, size: int = 3) -> None:
        self.size = size
        self.rank = 0


class MaxFilter(RankFilter):
    """
    Create a max filter.  Picks the largest pixel value in a window with the
    given size.

    :param size: The kernel size, in pixels.
    """

    name = "Max"

    def __init__(self, size: int = 3) -> None:
        self.size = size
        self.rank = size * size - 1


class ModeFilter(Filter):
    """
    Create a mode filter. Picks the most frequent pixel value in a box with the
    given size.  Pixel values that occur only once or twice are ignored; if no
    pixel value occurs more than twice, the original pixel value is preserved.

    :param size: The kernel size, in pixels.
    """

    name = "Mode"

    def __init__(self, size: int = 3) -> None:
        self.size = size

    def filter(self, image: _imaging.ImagingCore) -> _imaging.ImagingCore:
        return image.modefilter(self.size)


class GaussianBlur(MultibandFilter):
    """Blurs the image with a sequence of extended box filters, which
    approximates a Gaussian kernel. For details on accuracy see
    <https://www.mia.uni-saarland.de/Publications/gwosdek-ssvm11.pdf>

    :param radius: Standard deviation of the Gaussian kernel. Either a sequence of two
                   numbers for x and y, or a single number for both.
    """

    name = "GaussianBlur"

    def __init__(self, radius: float | Sequence[float] = 2) -> None:
        self.radius = radius

    def filter(self, image: _imaging.ImagingCore) -> _imaging.ImagingCore:
        xy = self.radius
        if isinstance(xy, (int, float)):
            xy = (xy, xy)
        if xy == (0, 0):
            return image.copy()
        return image.gaussian_blur(xy)


class BoxBlur(MultibandFilter):
    """Blurs the image by setting each pixel to the average value of the pixels
    in a square box extending radius pixels in each direction.
    Supports float radius of arbitrary size. Uses an optimized implementation
    which runs in linear time relative to the size of the image
    for any radius value.

    :param radius: Size of the box in a direction. Either a sequence of two numbers for
                   x and y, or a single number for both.

                   Radius 0 does not blur, returns an identical image.
                   Radius 1 takes 1 pixel in each direction, i.e. 9 pixels in total.
    """

    name = "BoxBlur"

    def __init__(self, radius: float | Sequence[float]) -> None:
        xy = radius if isinstance(radius, (tuple, list)) else (radius, radius)
        if xy[0] < 0 or xy[1] < 0:
            msg = "radius must be >= 0"
            raise ValueError(msg)
        self.radius = radius

    def filter(self, image: _imaging.ImagingCore) -> _imaging.ImagingCore:
        xy = self.radius
        if isinstance(xy, (int, float)):
            xy = (xy, xy)
        if xy == (0, 0):
            return image.copy()
        return image.box_blur(xy)


class UnsharpMask(MultibandFilter):
    """Unsharp mask filter.

    See Wikipedia's entry on `digital unsharp masking`_ for an explanation of
    the parameters.

    :param radius: Blur Radius
    :param percent: Unsharp strength, in percent
    :param threshold: Threshold controls the minimum brightness change that
      will be sharpened

    .. _digital unsharp masking: https://en.wikipedia.org/wiki/Unsharp_masking#Digital_unsharp_masking

    """

    name = "UnsharpMask"

    def __init__(
        self, radius: float = 2, percent: int = 150, threshold: int = 3
    ) -> None:
        self.radius = radius
        self.percent = percent
        self.threshold = threshold

    def filter(self, image: _imaging.ImagingCore) -> _imaging.ImagingCore:
        return image.unsharp_mask(self.radius, self.percent, self.threshold)


class BLUR(BuiltinFilter):
    name = "Blur"
    # fmt: off
    filterargs = (5, 5), 16, 0, (
        1, 1, 1, 1, 1,
        1, 0, 0, 0, 1,
        1, 0, 0, 0, 1,
        1, 0, 0, 0, 1,
        1, 1, 1, 1, 1,
    )
    # fmt: on


class CONTOUR(BuiltinFilter):
    name = "Contour"
    # fmt: off
    filterargs = (3, 3), 1, 255, (
        -1, -1, -1,
        -1,  8, -1,
        -1, -1, -1,
    )
    # fmt: on


class DETAIL(BuiltinFilter):
    name = "Detail"
    # fmt: off
    filterargs = (3, 3), 6, 0, (
        0,  -1,  0,
        -1, 10, -1,
        0,  -1,  0,
    )
    # fmt: on


class EDGE_ENHANCE(BuiltinFilter):
    name = "Edge-enhance"
    # fmt: off
    filterargs = (3, 3), 2, 0, (
        -1, -1, -1,
        -1, 10, -1,
        -1, -1, -1,
    )
    # fmt: on


class EDGE_ENHANCE_MORE(BuiltinFilter):
    name = "Edge-enhance More"
    # fmt: off
    filterargs = (3, 3), 1, 0, (
        -1, -1, -1,
        -1,  9, -1,
        -1, -1, -1,
    )
    # fmt: on


class EMBOSS(BuiltinFilter):
    name = "Emboss"
    # fmt: off
    filterargs = (3, 3), 1, 128, (
        -1, 0, 0,
        0,  1, 0,
        0,  0, 0,
    )
    # fmt: on


class FIND_EDGES(BuiltinFilter):
    name = "Find Edges"
    # fmt: off
    filterargs = (3, 3), 1, 0, (
        -1, -1, -1,
        -1,  8, -1,
        -1, -1, -1,
    )
    # fmt: on


class SHARPEN(BuiltinFilter):
    name = "Sharpen"
    # fmt: off
    filterargs = (3, 3), 16, 0, (
        -2, -2, -2,
        -2, 32, -2,
        -2, -2, -2,
    )
    # fmt: on


class SMOOTH(BuiltinFilter):
    name = "Smooth"
    # fmt: off
    filterargs = (3, 3), 13, 0, (
        1, 1, 1,
        1, 5, 1,
        1, 1, 1,
    )
    # fmt: on


class SMOOTH_MORE(BuiltinFilter):
    name = "Smooth More"
    # fmt: off
    filterargs = (5, 5), 100, 0, (
        1, 1,  1, 1, 1,
        1, 5,  5, 5, 1,
        1, 5, 44, 5, 1,
        1, 5,  5, 5, 1,
        1, 1,  1, 1, 1,
    )
    # fmt: on


class Color3DLUT(MultibandFilter):
    """Three-dimensional color lookup table.

    Transforms 3-channel pixels using the values of the channels as coordinates
    in the 3D lookup table and interpolating the nearest elements.

    This method allows you to apply almost any color transformation
    in constant time by using pre-calculated decimated tables.

    .. versionadded:: 5.2.0

    :param size: Size of the table. One int or tuple of (int, int, int).
                 Minimal size in any dimension is 2, maximum is 65.
    :param table: Flat lookup table. A list of ``channels * size**3``
                  float elements or a list of ``size**3`` channels-sized
                  tuples with floats. Channels are changed first,
                  then first dimension, then second, then third.
                  Value 0.0 corresponds lowest value of output, 1.0 highest.
    :param channels: Number of channels in the table. Could be 3 or 4.
                     Default is 3.
    :param target_mode: A mode for the result image. Should have not less
                        than ``channels`` channels. Default is ``None``,
                        which means that mode wouldn't be changed.
    """

    name = "Color 3D LUT"

    def __init__(
        self,
        size: int | tuple[int, int, int],
        table: Sequence[float] | Sequence[Sequence[int]] | NumpyArray,
        channels: int = 3,
        target_mode: str | None = None,
        **kwargs: bool,
    ) -> None:
        if channels not in (3, 4):
            msg = "Only 3 or 4 output channels are supported"
            raise ValueError(msg)
        self.size = size = self._check_size(size)
        self.channels = channels
        self.mode = target_mode

        # Hidden flag `_copy_table=False` could be used to avoid extra copying
        # of the table if the table is specially made for the constructor.
        copy_table = kwargs.get("_copy_table", True)
        items = size[0] * size[1] * size[2]
        wrong_size = False

        numpy: ModuleType | None = None
        if hasattr(table, "shape"):
            try:
                import numpy
            except ImportError:
                pass

        if numpy and isinstance(table, numpy.ndarray):
            numpy_table: NumpyArray = table
            if copy_table:
                numpy_table = numpy_table.copy()

            if numpy_table.shape in [
                (items * channels,),
                (items, channels),
                (size[2], size[1], size[0], channels),
            ]:
                table = numpy_table.reshape(items * channels)
            else:
                wrong_size = True

        else:
            if copy_table:
                table = list(table)

            # Convert to a flat list
            if table and isinstance(table[0], (list, tuple)):
                raw_table = cast(Sequence[Sequence[int]], table)
                flat_table: list[int] = []
                for pixel in raw_table:
                    if len(pixel) != channels:
                        msg = (
                            "The elements of the table should "
                            f"have a length of {channels}."
                        )
                        raise ValueError(msg)
                    flat_table.extend(pixel)
                table = flat_table

        if wrong_size or len(table) != items * channels:
            msg = (
                "The table should have either channels * size**3 float items "
                "or size**3 items of channels-sized tuples with floats. "
                f"Table should be: {channels}x{size[0]}x{size[1]}x{size[2]}. "
                f"Actual length: {len(table)}"
            )
            raise ValueError(msg)
        self.table = table

    @staticmethod
    def _check_size(size: Any) -> tuple[int, int, int]:
        try:
            _, _, _ = size
        except ValueError as e:
            msg = "Size should be either an integer or a tuple of three integers."
            raise ValueError(msg) from e
        except TypeError:
            size = (size, size, size)
        size = tuple(int(x) for x in size)
        for size_1d in size:
            if not 2 <= size_1d <= 65:
                msg = "Size should be in [2, 65] range."
                raise ValueError(msg)
        return size

    @classmethod
    def generate(
        cls,
        size: int | tuple[int, int, int],
        callback: Callable[[float, float, float], tuple[float, ...]],
        channels: int = 3,
        target_mode: str | None = None,
    ) -> Color3DLUT:
        """Generates new LUT using provided callback.

        :param size: Size of the table. Passed to the constructor.
        :param callback: Function with three parameters which correspond
                         three color channels. Will be called ``size**3``
                         times with values from 0.0 to 1.0 and should return
                         a tuple with ``channels`` elements.
        :param channels: The number of channels which should return callback.
        :param target_mode: Passed to the constructor of the resulting
                            lookup table.
        """
        size_1d, size_2d, size_3d = cls._check_size(size)
        if channels not in (3, 4):
            msg = "Only 3 or 4 output channels are supported"
            raise ValueError(msg)

        table: list[float] = [0] * (size_1d * size_2d * size_3d * channels)
        idx_out = 0
        for b in range(size_3d):
            for g in range(size_2d):
                for r in range(size_1d):
                    table[idx_out : idx_out + channels] = callback(
                        r / (size_1d - 1), g / (size_2d - 1), b / (size_3d - 1)
                    )
                    idx_out += channels

        return cls(
            (size_1d, size_2d, size_3d),
            table,
            channels=channels,
            target_mode=target_mode,
            _copy_table=False,
        )

    def transform(
        self,
        callback: Callable[..., tuple[float, ...]],
        with_normals: bool = False,
        channels: int | None = None,
        target_mode: str | None = None,
    ) -> Color3DLUT:
        """Transforms the table values using provided callback and returns
        a new LUT with altered values.

        :param callback: A function which takes old lookup table values
                         and returns a new set of values. The number
                         of arguments which function should take is
                         ``self.channels`` or ``3 + self.channels``
                         if ``with_normals`` flag is set.
                         Should return a tuple of ``self.channels`` or
                         ``channels`` elements if it is set.
        :param with_normals: If true, ``callback`` will be called with
                             coordinates in the color cube as the first
                             three arguments. Otherwise, ``callback``
                             will be called only with actual color values.
        :param channels: The number of channels in the resulting lookup table.
        :param target_mode: Passed to the constructor of the resulting
                            lookup table.
        """
        if channels not in (None, 3, 4):
            msg = "Only 3 or 4 output channels are supported"
            raise ValueError(msg)
        ch_in = self.channels
        ch_out = channels or ch_in
        size_1d, size_2d, size_3d = self.size

        table: list[float] = [0] * (size_1d * size_2d * size_3d * ch_out)
        idx_in = 0
        idx_out = 0
        for b in range(size_3d):
            for g in range(size_2d):
                for r in range(size_1d):
                    values = self.table[idx_in : idx_in + ch_in]
                    if with_normals:
                        values = callback(
                            r / (size_1d - 1),
                            g / (size_2d - 1),
                            b / (size_3d - 1),
                            *values,
                        )
                    else:
                        values = callback(*values)
                    table[idx_out : idx_out + ch_out] = values
                    idx_in += ch_in
                    idx_out += ch_out

        return type(self)(
            self.size,
            table,
            channels=ch_out,
            target_mode=target_mode or self.mode,
            _copy_table=False,
        )

    def __repr__(self) -> str:
        r = [
            f"{self.__class__.__name__} from {self.table.__class__.__name__}",
            "size={:d}x{:d}x{:d}".format(*self.size),
            f"channels={self.channels:d}",
        ]
        if self.mode:
            r.append(f"target_mode={self.mode}")
        return "<{}>".format(" ".join(r))

    def filter(self, image: _imaging.ImagingCore) -> _imaging.ImagingCore:
        from . import Image

        return image.color_lut_3d(
            self.mode or image.mode,
            Image.Resampling.BILINEAR,
            self.channels,
            self.size,
            self.table,
        )

# === NexusCore/openenv\Lib\site-packages\pydantic\color.py ===
"""Color definitions are used as per the CSS3
[CSS Color Module Level 3](http://www.w3.org/TR/css3-color/#svg-color) specification.

A few colors have multiple names referring to the sames colors, eg. `grey` and `gray` or `aqua` and `cyan`.

In these cases the _last_ color when sorted alphabetically takes preferences,
eg. `Color((0, 255, 255)).as_named() == 'cyan'` because "cyan" comes after "aqua".

Warning: Deprecated
    The `Color` class is deprecated, use `pydantic_extra_types` instead.
    See [`pydantic-extra-types.Color`](../usage/types/extra_types/color_types.md)
    for more information.
"""

import math
import re
from colorsys import hls_to_rgb, rgb_to_hls
from typing import Any, Callable, Optional, Union, cast

from pydantic_core import CoreSchema, PydanticCustomError, core_schema
from typing_extensions import deprecated

from ._internal import _repr
from ._internal._schema_generation_shared import GetJsonSchemaHandler as _GetJsonSchemaHandler
from .json_schema import JsonSchemaValue
from .warnings import PydanticDeprecatedSince20

ColorTuple = Union[tuple[int, int, int], tuple[int, int, int, float]]
ColorType = Union[ColorTuple, str]
HslColorTuple = Union[tuple[float, float, float], tuple[float, float, float, float]]


class RGBA:
    """Internal use only as a representation of a color."""

    __slots__ = 'r', 'g', 'b', 'alpha', '_tuple'

    def __init__(self, r: float, g: float, b: float, alpha: Optional[float]):
        self.r = r
        self.g = g
        self.b = b
        self.alpha = alpha

        self._tuple: tuple[float, float, float, Optional[float]] = (r, g, b, alpha)

    def __getitem__(self, item: Any) -> Any:
        return self._tuple[item]


# these are not compiled here to avoid import slowdown, they'll be compiled the first time they're used, then cached
_r_255 = r'(\d{1,3}(?:\.\d+)?)'
_r_comma = r'\s*,\s*'
_r_alpha = r'(\d(?:\.\d+)?|\.\d+|\d{1,2}%)'
_r_h = r'(-?\d+(?:\.\d+)?|-?\.\d+)(deg|rad|turn)?'
_r_sl = r'(\d{1,3}(?:\.\d+)?)%'
r_hex_short = r'\s*(?:#|0x)?([0-9a-f])([0-9a-f])([0-9a-f])([0-9a-f])?\s*'
r_hex_long = r'\s*(?:#|0x)?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})?\s*'
# CSS3 RGB examples: rgb(0, 0, 0), rgba(0, 0, 0, 0.5), rgba(0, 0, 0, 50%)
r_rgb = rf'\s*rgba?\(\s*{_r_255}{_r_comma}{_r_255}{_r_comma}{_r_255}(?:{_r_comma}{_r_alpha})?\s*\)\s*'
# CSS3 HSL examples: hsl(270, 60%, 50%), hsla(270, 60%, 50%, 0.5), hsla(270, 60%, 50%, 50%)
r_hsl = rf'\s*hsla?\(\s*{_r_h}{_r_comma}{_r_sl}{_r_comma}{_r_sl}(?:{_r_comma}{_r_alpha})?\s*\)\s*'
# CSS4 RGB examples: rgb(0 0 0), rgb(0 0 0 / 0.5), rgb(0 0 0 / 50%), rgba(0 0 0 / 50%)
r_rgb_v4_style = rf'\s*rgba?\(\s*{_r_255}\s+{_r_255}\s+{_r_255}(?:\s*/\s*{_r_alpha})?\s*\)\s*'
# CSS4 HSL examples: hsl(270 60% 50%), hsl(270 60% 50% / 0.5), hsl(270 60% 50% / 50%), hsla(270 60% 50% / 50%)
r_hsl_v4_style = rf'\s*hsla?\(\s*{_r_h}\s+{_r_sl}\s+{_r_sl}(?:\s*/\s*{_r_alpha})?\s*\)\s*'

# colors where the two hex characters are the same, if all colors match this the short version of hex colors can be used
repeat_colors = {int(c * 2, 16) for c in '0123456789abcdef'}
rads = 2 * math.pi


@deprecated(
    'The `Color` class is deprecated, use `pydantic_extra_types` instead. '
    'See https://docs.pydantic.dev/latest/api/pydantic_extra_types_color/.',
    category=PydanticDeprecatedSince20,
)
class Color(_repr.Representation):
    """Represents a color."""

    __slots__ = '_original', '_rgba'

    def __init__(self, value: ColorType) -> None:
        self._rgba: RGBA
        self._original: ColorType
        if isinstance(value, (tuple, list)):
            self._rgba = parse_tuple(value)
        elif isinstance(value, str):
            self._rgba = parse_str(value)
        elif isinstance(value, Color):
            self._rgba = value._rgba
            value = value._original
        else:
            raise PydanticCustomError(
                'color_error', 'value is not a valid color: value must be a tuple, list or string'
            )

        # if we've got here value must be a valid color
        self._original = value

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: core_schema.CoreSchema, handler: _GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        field_schema = {}
        field_schema.update(type='string', format='color')
        return field_schema

    def original(self) -> ColorType:
        """Original value passed to `Color`."""
        return self._original

    def as_named(self, *, fallback: bool = False) -> str:
        """Returns the name of the color if it can be found in `COLORS_BY_VALUE` dictionary,
        otherwise returns the hexadecimal representation of the color or raises `ValueError`.

        Args:
            fallback: If True, falls back to returning the hexadecimal representation of
                the color instead of raising a ValueError when no named color is found.

        Returns:
            The name of the color, or the hexadecimal representation of the color.

        Raises:
            ValueError: When no named color is found and fallback is `False`.
        """
        if self._rgba.alpha is None:
            rgb = cast(tuple[int, int, int], self.as_rgb_tuple())
            try:
                return COLORS_BY_VALUE[rgb]
            except KeyError as e:
                if fallback:
                    return self.as_hex()
                else:
                    raise ValueError('no named color found, use fallback=True, as_hex() or as_rgb()') from e
        else:
            return self.as_hex()

    def as_hex(self) -> str:
        """Returns the hexadecimal representation of the color.

        Hex string representing the color can be 3, 4, 6, or 8 characters depending on whether the string
        a "short" representation of the color is possible and whether there's an alpha channel.

        Returns:
            The hexadecimal representation of the color.
        """
        values = [float_to_255(c) for c in self._rgba[:3]]
        if self._rgba.alpha is not None:
            values.append(float_to_255(self._rgba.alpha))

        as_hex = ''.join(f'{v:02x}' for v in values)
        if all(c in repeat_colors for c in values):
            as_hex = ''.join(as_hex[c] for c in range(0, len(as_hex), 2))
        return '#' + as_hex

    def as_rgb(self) -> str:
        """Color as an `rgb(<r>, <g>, <b>)` or `rgba(<r>, <g>, <b>, <a>)` string."""
        if self._rgba.alpha is None:
            return f'rgb({float_to_255(self._rgba.r)}, {float_to_255(self._rgba.g)}, {float_to_255(self._rgba.b)})'
        else:
            return (
                f'rgba({float_to_255(self._rgba.r)}, {float_to_255(self._rgba.g)}, {float_to_255(self._rgba.b)}, '
                f'{round(self._alpha_float(), 2)})'
            )

    def as_rgb_tuple(self, *, alpha: Optional[bool] = None) -> ColorTuple:
        """Returns the color as an RGB or RGBA tuple.

        Args:
            alpha: Whether to include the alpha channel. There are three options for this input:

                - `None` (default): Include alpha only if it's set. (e.g. not `None`)
                - `True`: Always include alpha.
                - `False`: Always omit alpha.

        Returns:
            A tuple that contains the values of the red, green, and blue channels in the range 0 to 255.
                If alpha is included, it is in the range 0 to 1.
        """
        r, g, b = (float_to_255(c) for c in self._rgba[:3])
        if alpha is None:
            if self._rgba.alpha is None:
                return r, g, b
            else:
                return r, g, b, self._alpha_float()
        elif alpha:
            return r, g, b, self._alpha_float()
        else:
            # alpha is False
            return r, g, b

    def as_hsl(self) -> str:
        """Color as an `hsl(<h>, <s>, <l>)` or `hsl(<h>, <s>, <l>, <a>)` string."""
        if self._rgba.alpha is None:
            h, s, li = self.as_hsl_tuple(alpha=False)  # type: ignore
            return f'hsl({h * 360:0.0f}, {s:0.0%}, {li:0.0%})'
        else:
            h, s, li, a = self.as_hsl_tuple(alpha=True)  # type: ignore
            return f'hsl({h * 360:0.0f}, {s:0.0%}, {li:0.0%}, {round(a, 2)})'

    def as_hsl_tuple(self, *, alpha: Optional[bool] = None) -> HslColorTuple:
        """Returns the color as an HSL or HSLA tuple.

        Args:
            alpha: Whether to include the alpha channel.

                - `None` (default): Include the alpha channel only if it's set (e.g. not `None`).
                - `True`: Always include alpha.
                - `False`: Always omit alpha.

        Returns:
            The color as a tuple of hue, saturation, lightness, and alpha (if included).
                All elements are in the range 0 to 1.

        Note:
            This is HSL as used in HTML and most other places, not HLS as used in Python's `colorsys`.
        """
        h, l, s = rgb_to_hls(self._rgba.r, self._rgba.g, self._rgba.b)  # noqa: E741
        if alpha is None:
            if self._rgba.alpha is None:
                return h, s, l
            else:
                return h, s, l, self._alpha_float()
        if alpha:
            return h, s, l, self._alpha_float()
        else:
            # alpha is False
            return h, s, l

    def _alpha_float(self) -> float:
        return 1 if self._rgba.alpha is None else self._rgba.alpha

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: type[Any], handler: Callable[[Any], CoreSchema]
    ) -> core_schema.CoreSchema:
        return core_schema.with_info_plain_validator_function(
            cls._validate, serialization=core_schema.to_string_ser_schema()
        )

    @classmethod
    def _validate(cls, __input_value: Any, _: Any) -> 'Color':
        return cls(__input_value)

    def __str__(self) -> str:
        return self.as_named(fallback=True)

    def __repr_args__(self) -> '_repr.ReprArgs':
        return [(None, self.as_named(fallback=True))] + [('rgb', self.as_rgb_tuple())]

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Color) and self.as_rgb_tuple() == other.as_rgb_tuple()

    def __hash__(self) -> int:
        return hash(self.as_rgb_tuple())


def parse_tuple(value: tuple[Any, ...]) -> RGBA:
    """Parse a tuple or list to get RGBA values.

    Args:
        value: A tuple or list.

    Returns:
        An `RGBA` tuple parsed from the input tuple.

    Raises:
        PydanticCustomError: If tuple is not valid.
    """
    if len(value) == 3:
        r, g, b = (parse_color_value(v) for v in value)
        return RGBA(r, g, b, None)
    elif len(value) == 4:
        r, g, b = (parse_color_value(v) for v in value[:3])
        return RGBA(r, g, b, parse_float_alpha(value[3]))
    else:
        raise PydanticCustomError('color_error', 'value is not a valid color: tuples must have length 3 or 4')


def parse_str(value: str) -> RGBA:
    """Parse a string representing a color to an RGBA tuple.

    Possible formats for the input string include:

    * named color, see `COLORS_BY_NAME`
    * hex short eg. `<prefix>fff` (prefix can be `#`, `0x` or nothing)
    * hex long eg. `<prefix>ffffff` (prefix can be `#`, `0x` or nothing)
    * `rgb(<r>, <g>, <b>)`
    * `rgba(<r>, <g>, <b>, <a>)`

    Args:
        value: A string representing a color.

    Returns:
        An `RGBA` tuple parsed from the input string.

    Raises:
        ValueError: If the input string cannot be parsed to an RGBA tuple.
    """
    value_lower = value.lower()
    try:
        r, g, b = COLORS_BY_NAME[value_lower]
    except KeyError:
        pass
    else:
        return ints_to_rgba(r, g, b, None)

    m = re.fullmatch(r_hex_short, value_lower)
    if m:
        *rgb, a = m.groups()
        r, g, b = (int(v * 2, 16) for v in rgb)
        if a:
            alpha: Optional[float] = int(a * 2, 16) / 255
        else:
            alpha = None
        return ints_to_rgba(r, g, b, alpha)

    m = re.fullmatch(r_hex_long, value_lower)
    if m:
        *rgb, a = m.groups()
        r, g, b = (int(v, 16) for v in rgb)
        if a:
            alpha = int(a, 16) / 255
        else:
            alpha = None
        return ints_to_rgba(r, g, b, alpha)

    m = re.fullmatch(r_rgb, value_lower) or re.fullmatch(r_rgb_v4_style, value_lower)
    if m:
        return ints_to_rgba(*m.groups())  # type: ignore

    m = re.fullmatch(r_hsl, value_lower) or re.fullmatch(r_hsl_v4_style, value_lower)
    if m:
        return parse_hsl(*m.groups())  # type: ignore

    raise PydanticCustomError('color_error', 'value is not a valid color: string not recognised as a valid color')


def ints_to_rgba(r: Union[int, str], g: Union[int, str], b: Union[int, str], alpha: Optional[float] = None) -> RGBA:
    """Converts integer or string values for RGB color and an optional alpha value to an `RGBA` object.

    Args:
        r: An integer or string representing the red color value.
        g: An integer or string representing the green color value.
        b: An integer or string representing the blue color value.
        alpha: A float representing the alpha value. Defaults to None.

    Returns:
        An instance of the `RGBA` class with the corresponding color and alpha values.
    """
    return RGBA(parse_color_value(r), parse_color_value(g), parse_color_value(b), parse_float_alpha(alpha))


def parse_color_value(value: Union[int, str], max_val: int = 255) -> float:
    """Parse the color value provided and return a number between 0 and 1.

    Args:
        value: An integer or string color value.
        max_val: Maximum range value. Defaults to 255.

    Raises:
        PydanticCustomError: If the value is not a valid color.

    Returns:
        A number between 0 and 1.
    """
    try:
        color = float(value)
    except ValueError:
        raise PydanticCustomError('color_error', 'value is not a valid color: color values must be a valid number')
    if 0 <= color <= max_val:
        return color / max_val
    else:
        raise PydanticCustomError(
            'color_error',
            'value is not a valid color: color values must be in the range 0 to {max_val}',
            {'max_val': max_val},
        )


def parse_float_alpha(value: Union[None, str, float, int]) -> Optional[float]:
    """Parse an alpha value checking it's a valid float in the range 0 to 1.

    Args:
        value: The input value to parse.

    Returns:
        The parsed value as a float, or `None` if the value was None or equal 1.

    Raises:
        PydanticCustomError: If the input value cannot be successfully parsed as a float in the expected range.
    """
    if value is None:
        return None
    try:
        if isinstance(value, str) and value.endswith('%'):
            alpha = float(value[:-1]) / 100
        else:
            alpha = float(value)
    except ValueError:
        raise PydanticCustomError('color_error', 'value is not a valid color: alpha values must be a valid float')

    if math.isclose(alpha, 1):
        return None
    elif 0 <= alpha <= 1:
        return alpha
    else:
        raise PydanticCustomError('color_error', 'value is not a valid color: alpha values must be in the range 0 to 1')


def parse_hsl(h: str, h_units: str, sat: str, light: str, alpha: Optional[float] = None) -> RGBA:
    """Parse raw hue, saturation, lightness, and alpha values and convert to RGBA.

    Args:
        h: The hue value.
        h_units: The unit for hue value.
        sat: The saturation value.
        light: The lightness value.
        alpha: Alpha value.

    Returns:
        An instance of `RGBA`.
    """
    s_value, l_value = parse_color_value(sat, 100), parse_color_value(light, 100)

    h_value = float(h)
    if h_units in {None, 'deg'}:
        h_value = h_value % 360 / 360
    elif h_units == 'rad':
        h_value = h_value % rads / rads
    else:
        # turns
        h_value = h_value % 1

    r, g, b = hls_to_rgb(h_value, l_value, s_value)
    return RGBA(r, g, b, parse_float_alpha(alpha))


def float_to_255(c: float) -> int:
    """Converts a float value between 0 and 1 (inclusive) to an integer between 0 and 255 (inclusive).

    Args:
        c: The float value to be converted. Must be between 0 and 1 (inclusive).

    Returns:
        The integer equivalent of the given float value rounded to the nearest whole number.

    Raises:
        ValueError: If the given float value is outside the acceptable range of 0 to 1 (inclusive).
    """
    return int(round(c * 255))


COLORS_BY_NAME = {
    'aliceblue': (240, 248, 255),
    'antiquewhite': (250, 235, 215),
    'aqua': (0, 255, 255),
    'aquamarine': (127, 255, 212),
    'azure': (240, 255, 255),
    'beige': (245, 245, 220),
    'bisque': (255, 228, 196),
    'black': (0, 0, 0),
    'blanchedalmond': (255, 235, 205),
    'blue': (0, 0, 255),
    'blueviolet': (138, 43, 226),
    'brown': (165, 42, 42),
    'burlywood': (222, 184, 135),
    'cadetblue': (95, 158, 160),
    'chartreuse': (127, 255, 0),
    'chocolate': (210, 105, 30),
    'coral': (255, 127, 80),
    'cornflowerblue': (100, 149, 237),
    'cornsilk': (255, 248, 220),
    'crimson': (220, 20, 60),
    'cyan': (0, 255, 255),
    'darkblue': (0, 0, 139),
    'darkcyan': (0, 139, 139),
    'darkgoldenrod': (184, 134, 11),
    'darkgray': (169, 169, 169),
    'darkgreen': (0, 100, 0),
    'darkgrey': (169, 169, 169),
    'darkkhaki': (189, 183, 107),
    'darkmagenta': (139, 0, 139),
    'darkolivegreen': (85, 107, 47),
    'darkorange': (255, 140, 0),
    'darkorchid': (153, 50, 204),
    'darkred': (139, 0, 0),
    'darksalmon': (233, 150, 122),
    'darkseagreen': (143, 188, 143),
    'darkslateblue': (72, 61, 139),
    'darkslategray': (47, 79, 79),
    'darkslategrey': (47, 79, 79),
    'darkturquoise': (0, 206, 209),
    'darkviolet': (148, 0, 211),
    'deeppink': (255, 20, 147),
    'deepskyblue': (0, 191, 255),
    'dimgray': (105, 105, 105),
    'dimgrey': (105, 105, 105),
    'dodgerblue': (30, 144, 255),
    'firebrick': (178, 34, 34),
    'floralwhite': (255, 250, 240),
    'forestgreen': (34, 139, 34),
    'fuchsia': (255, 0, 255),
    'gainsboro': (220, 220, 220),
    'ghostwhite': (248, 248, 255),
    'gold': (255, 215, 0),
    'goldenrod': (218, 165, 32),
    'gray': (128, 128, 128),
    'green': (0, 128, 0),
    'greenyellow': (173, 255, 47),
    'grey': (128, 128, 128),
    'honeydew': (240, 255, 240),
    'hotpink': (255, 105, 180),
    'indianred': (205, 92, 92),
    'indigo': (75, 0, 130),
    'ivory': (255, 255, 240),
    'khaki': (240, 230, 140),
    'lavender': (230, 230, 250),
    'lavenderblush': (255, 240, 245),
    'lawngreen': (124, 252, 0),
    'lemonchiffon': (255, 250, 205),
    'lightblue': (173, 216, 230),
    'lightcoral': (240, 128, 128),
    'lightcyan': (224, 255, 255),
    'lightgoldenrodyellow': (250, 250, 210),
    'lightgray': (211, 211, 211),
    'lightgreen': (144, 238, 144),
    'lightgrey': (211, 211, 211),
    'lightpink': (255, 182, 193),
    'lightsalmon': (255, 160, 122),
    'lightseagreen': (32, 178, 170),
    'lightskyblue': (135, 206, 250),
    'lightslategray': (119, 136, 153),
    'lightslategrey': (119, 136, 153),
    'lightsteelblue': (176, 196, 222),
    'lightyellow': (255, 255, 224),
    'lime': (0, 255, 0),
    'limegreen': (50, 205, 50),
    'linen': (250, 240, 230),
    'magenta': (255, 0, 255),
    'maroon': (128, 0, 0),
    'mediumaquamarine': (102, 205, 170),
    'mediumblue': (0, 0, 205),
    'mediumorchid': (186, 85, 211),
    'mediumpurple': (147, 112, 219),
    'mediumseagreen': (60, 179, 113),
    'mediumslateblue': (123, 104, 238),
    'mediumspringgreen': (0, 250, 154),
    'mediumturquoise': (72, 209, 204),
    'mediumvioletred': (199, 21, 133),
    'midnightblue': (25, 25, 112),
    'mintcream': (245, 255, 250),
    'mistyrose': (255, 228, 225),
    'moccasin': (255, 228, 181),
    'navajowhite': (255, 222, 173),
    'navy': (0, 0, 128),
    'oldlace': (253, 245, 230),
    'olive': (128, 128, 0),
    'olivedrab': (107, 142, 35),
    'orange': (255, 165, 0),
    'orangered': (255, 69, 0),
    'orchid': (218, 112, 214),
    'palegoldenrod': (238, 232, 170),
    'palegreen': (152, 251, 152),
    'paleturquoise': (175, 238, 238),
    'palevioletred': (219, 112, 147),
    'papayawhip': (255, 239, 213),
    'peachpuff': (255, 218, 185),
    'peru': (205, 133, 63),
    'pink': (255, 192, 203),
    'plum': (221, 160, 221),
    'powderblue': (176, 224, 230),
    'purple': (128, 0, 128),
    'red': (255, 0, 0),
    'rosybrown': (188, 143, 143),
    'royalblue': (65, 105, 225),
    'saddlebrown': (139, 69, 19),
    'salmon': (250, 128, 114),
    'sandybrown': (244, 164, 96),
    'seagreen': (46, 139, 87),
    'seashell': (255, 245, 238),
    'sienna': (160, 82, 45),
    'silver': (192, 192, 192),
    'skyblue': (135, 206, 235),
    'slateblue': (106, 90, 205),
    'slategray': (112, 128, 144),
    'slategrey': (112, 128, 144),
    'snow': (255, 250, 250),
    'springgreen': (0, 255, 127),
    'steelblue': (70, 130, 180),
    'tan': (210, 180, 140),
    'teal': (0, 128, 128),
    'thistle': (216, 191, 216),
    'tomato': (255, 99, 71),
    'turquoise': (64, 224, 208),
    'violet': (238, 130, 238),
    'wheat': (245, 222, 179),
    'white': (255, 255, 255),
    'whitesmoke': (245, 245, 245),
    'yellow': (255, 255, 0),
    'yellowgreen': (154, 205, 50),
}

COLORS_BY_VALUE = {v: k for k, v in COLORS_BY_NAME.items()}

# === NexusCore/openenv\Lib\site-packages\pip\_internal\models\link.py ===
import functools
import itertools
import logging
import os
import posixpath
import re
import urllib.parse
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Mapping,
    NamedTuple,
    Optional,
    Tuple,
    Union,
)

from pip._internal.utils.deprecation import deprecated
from pip._internal.utils.filetypes import WHEEL_EXTENSION
from pip._internal.utils.hashes import Hashes
from pip._internal.utils.misc import (
    pairwise,
    redact_auth_from_url,
    split_auth_from_netloc,
    splitext,
)
from pip._internal.utils.urls import path_to_url, url_to_path

if TYPE_CHECKING:
    from pip._internal.index.collector import IndexContent

logger = logging.getLogger(__name__)


# Order matters, earlier hashes have a precedence over later hashes for what
# we will pick to use.
_SUPPORTED_HASHES = ("sha512", "sha384", "sha256", "sha224", "sha1", "md5")


@dataclass(frozen=True)
class LinkHash:
    """Links to content may have embedded hash values. This class parses those.

    `name` must be any member of `_SUPPORTED_HASHES`.

    This class can be converted to and from `ArchiveInfo`. While ArchiveInfo intends to
    be JSON-serializable to conform to PEP 610, this class contains the logic for
    parsing a hash name and value for correctness, and then checking whether that hash
    conforms to a schema with `.is_hash_allowed()`."""

    name: str
    value: str

    _hash_url_fragment_re = re.compile(
        # NB: we do not validate that the second group (.*) is a valid hex
        # digest. Instead, we simply keep that string in this class, and then check it
        # against Hashes when hash-checking is needed. This is easier to debug than
        # proactively discarding an invalid hex digest, as we handle incorrect hashes
        # and malformed hashes in the same place.
        r"[#&]({choices})=([^&]*)".format(
            choices="|".join(re.escape(hash_name) for hash_name in _SUPPORTED_HASHES)
        ),
    )

    def __post_init__(self) -> None:
        assert self.name in _SUPPORTED_HASHES

    @classmethod
    @functools.lru_cache(maxsize=None)
    def find_hash_url_fragment(cls, url: str) -> Optional["LinkHash"]:
        """Search a string for a checksum algorithm name and encoded output value."""
        match = cls._hash_url_fragment_re.search(url)
        if match is None:
            return None
        name, value = match.groups()
        return cls(name=name, value=value)

    def as_dict(self) -> Dict[str, str]:
        return {self.name: self.value}

    def as_hashes(self) -> Hashes:
        """Return a Hashes instance which checks only for the current hash."""
        return Hashes({self.name: [self.value]})

    def is_hash_allowed(self, hashes: Optional[Hashes]) -> bool:
        """
        Return True if the current hash is allowed by `hashes`.
        """
        if hashes is None:
            return False
        return hashes.is_hash_allowed(self.name, hex_digest=self.value)


@dataclass(frozen=True)
class MetadataFile:
    """Information about a core metadata file associated with a distribution."""

    hashes: Optional[Dict[str, str]]

    def __post_init__(self) -> None:
        if self.hashes is not None:
            assert all(name in _SUPPORTED_HASHES for name in self.hashes)


def supported_hashes(hashes: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
    # Remove any unsupported hash types from the mapping. If this leaves no
    # supported hashes, return None
    if hashes is None:
        return None
    hashes = {n: v for n, v in hashes.items() if n in _SUPPORTED_HASHES}
    if not hashes:
        return None
    return hashes


def _clean_url_path_part(part: str) -> str:
    """
    Clean a "part" of a URL path (i.e. after splitting on "@" characters).
    """
    # We unquote prior to quoting to make sure nothing is double quoted.
    return urllib.parse.quote(urllib.parse.unquote(part))


def _clean_file_url_path(part: str) -> str:
    """
    Clean the first part of a URL path that corresponds to a local
    filesystem path (i.e. the first part after splitting on "@" characters).
    """
    # We unquote prior to quoting to make sure nothing is double quoted.
    # Also, on Windows the path part might contain a drive letter which
    # should not be quoted. On Linux where drive letters do not
    # exist, the colon should be quoted. We rely on urllib.request
    # to do the right thing here.
    return urllib.request.pathname2url(urllib.request.url2pathname(part))


# percent-encoded:                   /
_reserved_chars_re = re.compile("(@|%2F)", re.IGNORECASE)


def _clean_url_path(path: str, is_local_path: bool) -> str:
    """
    Clean the path portion of a URL.
    """
    if is_local_path:
        clean_func = _clean_file_url_path
    else:
        clean_func = _clean_url_path_part

    # Split on the reserved characters prior to cleaning so that
    # revision strings in VCS URLs are properly preserved.
    parts = _reserved_chars_re.split(path)

    cleaned_parts = []
    for to_clean, reserved in pairwise(itertools.chain(parts, [""])):
        cleaned_parts.append(clean_func(to_clean))
        # Normalize %xx escapes (e.g. %2f -> %2F)
        cleaned_parts.append(reserved.upper())

    return "".join(cleaned_parts)


def _ensure_quoted_url(url: str) -> str:
    """
    Make sure a link is fully quoted.
    For example, if ' ' occurs in the URL, it will be replaced with "%20",
    and without double-quoting other characters.
    """
    # Split the URL into parts according to the general structure
    # `scheme://netloc/path?query#fragment`.
    result = urllib.parse.urlsplit(url)
    # If the netloc is empty, then the URL refers to a local filesystem path.
    is_local_path = not result.netloc
    path = _clean_url_path(result.path, is_local_path=is_local_path)
    return urllib.parse.urlunsplit(result._replace(path=path))


def _absolute_link_url(base_url: str, url: str) -> str:
    """
    A faster implementation of urllib.parse.urljoin with a shortcut
    for absolute http/https URLs.
    """
    if url.startswith(("https://", "http://")):
        return url
    else:
        return urllib.parse.urljoin(base_url, url)


@functools.total_ordering
class Link:
    """Represents a parsed link from a Package Index's simple URL"""

    __slots__ = [
        "_parsed_url",
        "_url",
        "_path",
        "_hashes",
        "comes_from",
        "requires_python",
        "yanked_reason",
        "metadata_file_data",
        "cache_link_parsing",
        "egg_fragment",
    ]

    def __init__(
        self,
        url: str,
        comes_from: Optional[Union[str, "IndexContent"]] = None,
        requires_python: Optional[str] = None,
        yanked_reason: Optional[str] = None,
        metadata_file_data: Optional[MetadataFile] = None,
        cache_link_parsing: bool = True,
        hashes: Optional[Mapping[str, str]] = None,
    ) -> None:
        """
        :param url: url of the resource pointed to (href of the link)
        :param comes_from: instance of IndexContent where the link was found,
            or string.
        :param requires_python: String containing the `Requires-Python`
            metadata field, specified in PEP 345. This may be specified by
            a data-requires-python attribute in the HTML link tag, as
            described in PEP 503.
        :param yanked_reason: the reason the file has been yanked, if the
            file has been yanked, or None if the file hasn't been yanked.
            This is the value of the "data-yanked" attribute, if present, in
            a simple repository HTML link. If the file has been yanked but
            no reason was provided, this should be the empty string. See
            PEP 592 for more information and the specification.
        :param metadata_file_data: the metadata attached to the file, or None if
            no such metadata is provided. This argument, if not None, indicates
            that a separate metadata file exists, and also optionally supplies
            hashes for that file.
        :param cache_link_parsing: A flag that is used elsewhere to determine
            whether resources retrieved from this link should be cached. PyPI
            URLs should generally have this set to False, for example.
        :param hashes: A mapping of hash names to digests to allow us to
            determine the validity of a download.
        """

        # The comes_from, requires_python, and metadata_file_data arguments are
        # only used by classmethods of this class, and are not used in client
        # code directly.

        # url can be a UNC windows share
        if url.startswith("\\\\"):
            url = path_to_url(url)

        self._parsed_url = urllib.parse.urlsplit(url)
        # Store the url as a private attribute to prevent accidentally
        # trying to set a new value.
        self._url = url
        # The .path property is hot, so calculate its value ahead of time.
        self._path = urllib.parse.unquote(self._parsed_url.path)

        link_hash = LinkHash.find_hash_url_fragment(url)
        hashes_from_link = {} if link_hash is None else link_hash.as_dict()
        if hashes is None:
            self._hashes = hashes_from_link
        else:
            self._hashes = {**hashes, **hashes_from_link}

        self.comes_from = comes_from
        self.requires_python = requires_python if requires_python else None
        self.yanked_reason = yanked_reason
        self.metadata_file_data = metadata_file_data

        self.cache_link_parsing = cache_link_parsing
        self.egg_fragment = self._egg_fragment()

    @classmethod
    def from_json(
        cls,
        file_data: Dict[str, Any],
        page_url: str,
    ) -> Optional["Link"]:
        """
        Convert an pypi json document from a simple repository page into a Link.
        """
        file_url = file_data.get("url")
        if file_url is None:
            return None

        url = _ensure_quoted_url(_absolute_link_url(page_url, file_url))
        pyrequire = file_data.get("requires-python")
        yanked_reason = file_data.get("yanked")
        hashes = file_data.get("hashes", {})

        # PEP 714: Indexes must use the name core-metadata, but
        # clients should support the old name as a fallback for compatibility.
        metadata_info = file_data.get("core-metadata")
        if metadata_info is None:
            metadata_info = file_data.get("dist-info-metadata")

        # The metadata info value may be a boolean, or a dict of hashes.
        if isinstance(metadata_info, dict):
            # The file exists, and hashes have been supplied
            metadata_file_data = MetadataFile(supported_hashes(metadata_info))
        elif metadata_info:
            # The file exists, but there are no hashes
            metadata_file_data = MetadataFile(None)
        else:
            # False or not present: the file does not exist
            metadata_file_data = None

        # The Link.yanked_reason expects an empty string instead of a boolean.
        if yanked_reason and not isinstance(yanked_reason, str):
            yanked_reason = ""
        # The Link.yanked_reason expects None instead of False.
        elif not yanked_reason:
            yanked_reason = None

        return cls(
            url,
            comes_from=page_url,
            requires_python=pyrequire,
            yanked_reason=yanked_reason,
            hashes=hashes,
            metadata_file_data=metadata_file_data,
        )

    @classmethod
    def from_element(
        cls,
        anchor_attribs: Dict[str, Optional[str]],
        page_url: str,
        base_url: str,
    ) -> Optional["Link"]:
        """
        Convert an anchor element's attributes in a simple repository page to a Link.
        """
        href = anchor_attribs.get("href")
        if not href:
            return None

        url = _ensure_quoted_url(_absolute_link_url(base_url, href))
        pyrequire = anchor_attribs.get("data-requires-python")
        yanked_reason = anchor_attribs.get("data-yanked")

        # PEP 714: Indexes must use the name data-core-metadata, but
        # clients should support the old name as a fallback for compatibility.
        metadata_info = anchor_attribs.get("data-core-metadata")
        if metadata_info is None:
            metadata_info = anchor_attribs.get("data-dist-info-metadata")
        # The metadata info value may be the string "true", or a string of
        # the form "hashname=hashval"
        if metadata_info == "true":
            # The file exists, but there are no hashes
            metadata_file_data = MetadataFile(None)
        elif metadata_info is None:
            # The file does not exist
            metadata_file_data = None
        else:
            # The file exists, and hashes have been supplied
            hashname, sep, hashval = metadata_info.partition("=")
            if sep == "=":
                metadata_file_data = MetadataFile(supported_hashes({hashname: hashval}))
            else:
                # Error - data is wrong. Treat as no hashes supplied.
                logger.debug(
                    "Index returned invalid data-dist-info-metadata value: %s",
                    metadata_info,
                )
                metadata_file_data = MetadataFile(None)

        return cls(
            url,
            comes_from=page_url,
            requires_python=pyrequire,
            yanked_reason=yanked_reason,
            metadata_file_data=metadata_file_data,
        )

    def __str__(self) -> str:
        if self.requires_python:
            rp = f" (requires-python:{self.requires_python})"
        else:
            rp = ""
        if self.comes_from:
            return f"{redact_auth_from_url(self._url)} (from {self.comes_from}){rp}"
        else:
            return redact_auth_from_url(str(self._url))

    def __repr__(self) -> str:
        return f"<Link {self}>"

    def __hash__(self) -> int:
        return hash(self.url)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Link):
            return NotImplemented
        return self.url == other.url

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, Link):
            return NotImplemented
        return self.url < other.url

    @property
    def url(self) -> str:
        return self._url

    @property
    def filename(self) -> str:
        path = self.path.rstrip("/")
        name = posixpath.basename(path)
        if not name:
            # Make sure we don't leak auth information if the netloc
            # includes a username and password.
            netloc, user_pass = split_auth_from_netloc(self.netloc)
            return netloc

        name = urllib.parse.unquote(name)
        assert name, f"URL {self._url!r} produced no filename"
        return name

    @property
    def file_path(self) -> str:
        return url_to_path(self.url)

    @property
    def scheme(self) -> str:
        return self._parsed_url.scheme

    @property
    def netloc(self) -> str:
        """
        This can contain auth information.
        """
        return self._parsed_url.netloc

    @property
    def path(self) -> str:
        return self._path

    def splitext(self) -> Tuple[str, str]:
        return splitext(posixpath.basename(self.path.rstrip("/")))

    @property
    def ext(self) -> str:
        return self.splitext()[1]

    @property
    def url_without_fragment(self) -> str:
        scheme, netloc, path, query, fragment = self._parsed_url
        return urllib.parse.urlunsplit((scheme, netloc, path, query, ""))

    _egg_fragment_re = re.compile(r"[#&]egg=([^&]*)")

    # Per PEP 508.
    _project_name_re = re.compile(
        r"^([A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9])$", re.IGNORECASE
    )

    def _egg_fragment(self) -> Optional[str]:
        match = self._egg_fragment_re.search(self._url)
        if not match:
            return None

        # An egg fragment looks like a PEP 508 project name, along with
        # an optional extras specifier. Anything else is invalid.
        project_name = match.group(1)
        if not self._project_name_re.match(project_name):
            deprecated(
                reason=f"{self} contains an egg fragment with a non-PEP 508 name.",
                replacement="to use the req @ url syntax, and remove the egg fragment",
                gone_in="25.1",
                issue=13157,
            )

        return project_name

    _subdirectory_fragment_re = re.compile(r"[#&]subdirectory=([^&]*)")

    @property
    def subdirectory_fragment(self) -> Optional[str]:
        match = self._subdirectory_fragment_re.search(self._url)
        if not match:
            return None
        return match.group(1)

    def metadata_link(self) -> Optional["Link"]:
        """Return a link to the associated core metadata file (if any)."""
        if self.metadata_file_data is None:
            return None
        metadata_url = f"{self.url_without_fragment}.metadata"
        if self.metadata_file_data.hashes is None:
            return Link(metadata_url)
        return Link(metadata_url, hashes=self.metadata_file_data.hashes)

    def as_hashes(self) -> Hashes:
        return Hashes({k: [v] for k, v in self._hashes.items()})

    @property
    def hash(self) -> Optional[str]:
        return next(iter(self._hashes.values()), None)

    @property
    def hash_name(self) -> Optional[str]:
        return next(iter(self._hashes), None)

    @property
    def show_url(self) -> str:
        return posixpath.basename(self._url.split("#", 1)[0].split("?", 1)[0])

    @property
    def is_file(self) -> bool:
        return self.scheme == "file"

    def is_existing_dir(self) -> bool:
        return self.is_file and os.path.isdir(self.file_path)

    @property
    def is_wheel(self) -> bool:
        return self.ext == WHEEL_EXTENSION

    @property
    def is_vcs(self) -> bool:
        from pip._internal.vcs import vcs

        return self.scheme in vcs.all_schemes

    @property
    def is_yanked(self) -> bool:
        return self.yanked_reason is not None

    @property
    def has_hash(self) -> bool:
        return bool(self._hashes)

    def is_hash_allowed(self, hashes: Optional[Hashes]) -> bool:
        """
        Return True if the link has a hash and it is allowed by `hashes`.
        """
        if hashes is None:
            return False
        return any(hashes.is_hash_allowed(k, v) for k, v in self._hashes.items())


class _CleanResult(NamedTuple):
    """Convert link for equivalency check.

    This is used in the resolver to check whether two URL-specified requirements
    likely point to the same distribution and can be considered equivalent. This
    equivalency logic avoids comparing URLs literally, which can be too strict
    (e.g. "a=1&b=2" vs "b=2&a=1") and produce conflicts unexpecting to users.

    Currently this does three things:

    1. Drop the basic auth part. This is technically wrong since a server can
       serve different content based on auth, but if it does that, it is even
       impossible to guarantee two URLs without auth are equivalent, since
       the user can input different auth information when prompted. So the
       practical solution is to assume the auth doesn't affect the response.
    2. Parse the query to avoid the ordering issue. Note that ordering under the
       same key in the query are NOT cleaned; i.e. "a=1&a=2" and "a=2&a=1" are
       still considered different.
    3. Explicitly drop most of the fragment part, except ``subdirectory=`` and
       hash values, since it should have no impact the downloaded content. Note
       that this drops the "egg=" part historically used to denote the requested
       project (and extras), which is wrong in the strictest sense, but too many
       people are supplying it inconsistently to cause superfluous resolution
       conflicts, so we choose to also ignore them.
    """

    parsed: urllib.parse.SplitResult
    query: Dict[str, List[str]]
    subdirectory: str
    hashes: Dict[str, str]


def _clean_link(link: Link) -> _CleanResult:
    parsed = link._parsed_url
    netloc = parsed.netloc.rsplit("@", 1)[-1]
    # According to RFC 8089, an empty host in file: means localhost.
    if parsed.scheme == "file" and not netloc:
        netloc = "localhost"
    fragment = urllib.parse.parse_qs(parsed.fragment)
    if "egg" in fragment:
        logger.debug("Ignoring egg= fragment in %s", link)
    try:
        # If there are multiple subdirectory values, use the first one.
        # This matches the behavior of Link.subdirectory_fragment.
        subdirectory = fragment["subdirectory"][0]
    except (IndexError, KeyError):
        subdirectory = ""
    # If there are multiple hash values under the same algorithm, use the
    # first one. This matches the behavior of Link.hash_value.
    hashes = {k: fragment[k][0] for k in _SUPPORTED_HASHES if k in fragment}
    return _CleanResult(
        parsed=parsed._replace(netloc=netloc, query="", fragment=""),
        query=urllib.parse.parse_qs(parsed.query),
        subdirectory=subdirectory,
        hashes=hashes,
    )


@functools.lru_cache(maxsize=None)
def links_equivalent(link1: Link, link2: Link) -> bool:
    return _clean_link(link1) == _clean_link(link2)

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v135\web_audio.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: WebAudio (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing

class GraphObjectId(str):
    '''
    An unique ID for a graph object (AudioContext, AudioNode, AudioParam) in Web Audio API
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> GraphObjectId:
        return cls(json)

    def __repr__(self):
        return 'GraphObjectId({})'.format(super().__repr__())


class ContextType(enum.Enum):
    '''
    Enum of BaseAudioContext types
    '''
    REALTIME = "realtime"
    OFFLINE = "offline"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class ContextState(enum.Enum):
    '''
    Enum of AudioContextState from the spec
    '''
    SUSPENDED = "suspended"
    RUNNING = "running"
    CLOSED = "closed"
    INTERRUPTED = "interrupted"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class NodeType(str):
    '''
    Enum of AudioNode types
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> NodeType:
        return cls(json)

    def __repr__(self):
        return 'NodeType({})'.format(super().__repr__())


class ChannelCountMode(enum.Enum):
    '''
    Enum of AudioNode::ChannelCountMode from the spec
    '''
    CLAMPED_MAX = "clamped-max"
    EXPLICIT = "explicit"
    MAX_ = "max"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class ChannelInterpretation(enum.Enum):
    '''
    Enum of AudioNode::ChannelInterpretation from the spec
    '''
    DISCRETE = "discrete"
    SPEAKERS = "speakers"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class ParamType(str):
    '''
    Enum of AudioParam types
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> ParamType:
        return cls(json)

    def __repr__(self):
        return 'ParamType({})'.format(super().__repr__())


class AutomationRate(enum.Enum):
    '''
    Enum of AudioParam::AutomationRate from the spec
    '''
    A_RATE = "a-rate"
    K_RATE = "k-rate"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class ContextRealtimeData:
    '''
    Fields in AudioContext that change in real-time.
    '''
    #: The current context time in second in BaseAudioContext.
    current_time: float

    #: The time spent on rendering graph divided by render quantum duration,
    #: and multiplied by 100. 100 means the audio renderer reached the full
    #: capacity and glitch may occur.
    render_capacity: float

    #: A running mean of callback interval.
    callback_interval_mean: float

    #: A running variance of callback interval.
    callback_interval_variance: float

    def to_json(self):
        json = dict()
        json['currentTime'] = self.current_time
        json['renderCapacity'] = self.render_capacity
        json['callbackIntervalMean'] = self.callback_interval_mean
        json['callbackIntervalVariance'] = self.callback_interval_variance
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            current_time=float(json['currentTime']),
            render_capacity=float(json['renderCapacity']),
            callback_interval_mean=float(json['callbackIntervalMean']),
            callback_interval_variance=float(json['callbackIntervalVariance']),
        )


@dataclass
class BaseAudioContext:
    '''
    Protocol object for BaseAudioContext
    '''
    context_id: GraphObjectId

    context_type: ContextType

    context_state: ContextState

    #: Platform-dependent callback buffer size.
    callback_buffer_size: float

    #: Number of output channels supported by audio hardware in use.
    max_output_channel_count: float

    #: Context sample rate.
    sample_rate: float

    realtime_data: typing.Optional[ContextRealtimeData] = None

    def to_json(self):
        json = dict()
        json['contextId'] = self.context_id.to_json()
        json['contextType'] = self.context_type.to_json()
        json['contextState'] = self.context_state.to_json()
        json['callbackBufferSize'] = self.callback_buffer_size
        json['maxOutputChannelCount'] = self.max_output_channel_count
        json['sampleRate'] = self.sample_rate
        if self.realtime_data is not None:
            json['realtimeData'] = self.realtime_data.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            context_id=GraphObjectId.from_json(json['contextId']),
            context_type=ContextType.from_json(json['contextType']),
            context_state=ContextState.from_json(json['contextState']),
            callback_buffer_size=float(json['callbackBufferSize']),
            max_output_channel_count=float(json['maxOutputChannelCount']),
            sample_rate=float(json['sampleRate']),
            realtime_data=ContextRealtimeData.from_json(json['realtimeData']) if 'realtimeData' in json else None,
        )


@dataclass
class AudioListener:
    '''
    Protocol object for AudioListener
    '''
    listener_id: GraphObjectId

    context_id: GraphObjectId

    def to_json(self):
        json = dict()
        json['listenerId'] = self.listener_id.to_json()
        json['contextId'] = self.context_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            listener_id=GraphObjectId.from_json(json['listenerId']),
            context_id=GraphObjectId.from_json(json['contextId']),
        )


@dataclass
class AudioNode:
    '''
    Protocol object for AudioNode
    '''
    node_id: GraphObjectId

    context_id: GraphObjectId

    node_type: NodeType

    number_of_inputs: float

    number_of_outputs: float

    channel_count: float

    channel_count_mode: ChannelCountMode

    channel_interpretation: ChannelInterpretation

    def to_json(self):
        json = dict()
        json['nodeId'] = self.node_id.to_json()
        json['contextId'] = self.context_id.to_json()
        json['nodeType'] = self.node_type.to_json()
        json['numberOfInputs'] = self.number_of_inputs
        json['numberOfOutputs'] = self.number_of_outputs
        json['channelCount'] = self.channel_count
        json['channelCountMode'] = self.channel_count_mode.to_json()
        json['channelInterpretation'] = self.channel_interpretation.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            node_id=GraphObjectId.from_json(json['nodeId']),
            context_id=GraphObjectId.from_json(json['contextId']),
            node_type=NodeType.from_json(json['nodeType']),
            number_of_inputs=float(json['numberOfInputs']),
            number_of_outputs=float(json['numberOfOutputs']),
            channel_count=float(json['channelCount']),
            channel_count_mode=ChannelCountMode.from_json(json['channelCountMode']),
            channel_interpretation=ChannelInterpretation.from_json(json['channelInterpretation']),
        )


@dataclass
class AudioParam:
    '''
    Protocol object for AudioParam
    '''
    param_id: GraphObjectId

    node_id: GraphObjectId

    context_id: GraphObjectId

    param_type: ParamType

    rate: AutomationRate

    default_value: float

    min_value: float

    max_value: float

    def to_json(self):
        json = dict()
        json['paramId'] = self.param_id.to_json()
        json['nodeId'] = self.node_id.to_json()
        json['contextId'] = self.context_id.to_json()
        json['paramType'] = self.param_type.to_json()
        json['rate'] = self.rate.to_json()
        json['defaultValue'] = self.default_value
        json['minValue'] = self.min_value
        json['maxValue'] = self.max_value
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            param_id=GraphObjectId.from_json(json['paramId']),
            node_id=GraphObjectId.from_json(json['nodeId']),
            context_id=GraphObjectId.from_json(json['contextId']),
            param_type=ParamType.from_json(json['paramType']),
            rate=AutomationRate.from_json(json['rate']),
            default_value=float(json['defaultValue']),
            min_value=float(json['minValue']),
            max_value=float(json['maxValue']),
        )


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables the WebAudio domain and starts sending context lifetime events.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'WebAudio.enable',
    }
    json = yield cmd_dict


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables the WebAudio domain.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'WebAudio.disable',
    }
    json = yield cmd_dict


def get_realtime_data(
        context_id: GraphObjectId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,ContextRealtimeData]:
    '''
    Fetch the realtime data from the registered contexts.

    :param context_id:
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['contextId'] = context_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'WebAudio.getRealtimeData',
        'params': params,
    }
    json = yield cmd_dict
    return ContextRealtimeData.from_json(json['realtimeData'])


@event_class('WebAudio.contextCreated')
@dataclass
class ContextCreated:
    '''
    Notifies that a new BaseAudioContext has been created.
    '''
    context: BaseAudioContext

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ContextCreated:
        return cls(
            context=BaseAudioContext.from_json(json['context'])
        )


@event_class('WebAudio.contextWillBeDestroyed')
@dataclass
class ContextWillBeDestroyed:
    '''
    Notifies that an existing BaseAudioContext will be destroyed.
    '''
    context_id: GraphObjectId

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ContextWillBeDestroyed:
        return cls(
            context_id=GraphObjectId.from_json(json['contextId'])
        )


@event_class('WebAudio.contextChanged')
@dataclass
class ContextChanged:
    '''
    Notifies that existing BaseAudioContext has changed some properties (id stays the same)..
    '''
    context: BaseAudioContext

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ContextChanged:
        return cls(
            context=BaseAudioContext.from_json(json['context'])
        )


@event_class('WebAudio.audioListenerCreated')
@dataclass
class AudioListenerCreated:
    '''
    Notifies that the construction of an AudioListener has finished.
    '''
    listener: AudioListener

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> AudioListenerCreated:
        return cls(
            listener=AudioListener.from_json(json['listener'])
        )


@event_class('WebAudio.audioListenerWillBeDestroyed')
@dataclass
class AudioListenerWillBeDestroyed:
    '''
    Notifies that a new AudioListener has been created.
    '''
    context_id: GraphObjectId
    listener_id: GraphObjectId

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> AudioListenerWillBeDestroyed:
        return cls(
            context_id=GraphObjectId.from_json(json['contextId']),
            listener_id=GraphObjectId.from_json(json['listenerId'])
        )


@event_class('WebAudio.audioNodeCreated')
@dataclass
class AudioNodeCreated:
    '''
    Notifies that a new AudioNode has been created.
    '''
    node: AudioNode

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> AudioNodeCreated:
        return cls(
            node=AudioNode.from_json(json['node'])
        )


@event_class('WebAudio.audioNodeWillBeDestroyed')
@dataclass
class AudioNodeWillBeDestroyed:
    '''
    Notifies that an existing AudioNode has been destroyed.
    '''
    context_id: GraphObjectId
    node_id: GraphObjectId

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> AudioNodeWillBeDestroyed:
        return cls(
            context_id=GraphObjectId.from_json(json['contextId']),
            node_id=GraphObjectId.from_json(json['nodeId'])
        )


@event_class('WebAudio.audioParamCreated')
@dataclass
class AudioParamCreated:
    '''
    Notifies that a new AudioParam has been created.
    '''
    param: AudioParam

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> AudioParamCreated:
        return cls(
            param=AudioParam.from_json(json['param'])
        )


@event_class('WebAudio.audioParamWillBeDestroyed')
@dataclass
class AudioParamWillBeDestroyed:
    '''
    Notifies that an existing AudioParam has been destroyed.
    '''
    context_id: GraphObjectId
    node_id: GraphObjectId
    param_id: GraphObjectId

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> AudioParamWillBeDestroyed:
        return cls(
            context_id=GraphObjectId.from_json(json['contextId']),
            node_id=GraphObjectId.from_json(json['nodeId']),
            param_id=GraphObjectId.from_json(json['paramId'])
        )


@event_class('WebAudio.nodesConnected')
@dataclass
class NodesConnected:
    '''
    Notifies that two AudioNodes are connected.
    '''
    context_id: GraphObjectId
    source_id: GraphObjectId
    destination_id: GraphObjectId
    source_output_index: typing.Optional[float]
    destination_input_index: typing.Optional[float]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> NodesConnected:
        return cls(
            context_id=GraphObjectId.from_json(json['contextId']),
            source_id=GraphObjectId.from_json(json['sourceId']),
            destination_id=GraphObjectId.from_json(json['destinationId']),
            source_output_index=float(json['sourceOutputIndex']) if 'sourceOutputIndex' in json else None,
            destination_input_index=float(json['destinationInputIndex']) if 'destinationInputIndex' in json else None
        )


@event_class('WebAudio.nodesDisconnected')
@dataclass
class NodesDisconnected:
    '''
    Notifies that AudioNodes are disconnected. The destination can be null, and it means all the outgoing connections from the source are disconnected.
    '''
    context_id: GraphObjectId
    source_id: GraphObjectId
    destination_id: GraphObjectId
    source_output_index: typing.Optional[float]
    destination_input_index: typing.Optional[float]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> NodesDisconnected:
        return cls(
            context_id=GraphObjectId.from_json(json['contextId']),
            source_id=GraphObjectId.from_json(json['sourceId']),
            destination_id=GraphObjectId.from_json(json['destinationId']),
            source_output_index=float(json['sourceOutputIndex']) if 'sourceOutputIndex' in json else None,
            destination_input_index=float(json['destinationInputIndex']) if 'destinationInputIndex' in json else None
        )


@event_class('WebAudio.nodeParamConnected')
@dataclass
class NodeParamConnected:
    '''
    Notifies that an AudioNode is connected to an AudioParam.
    '''
    context_id: GraphObjectId
    source_id: GraphObjectId
    destination_id: GraphObjectId
    source_output_index: typing.Optional[float]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> NodeParamConnected:
        return cls(
            context_id=GraphObjectId.from_json(json['contextId']),
            source_id=GraphObjectId.from_json(json['sourceId']),
            destination_id=GraphObjectId.from_json(json['destinationId']),
            source_output_index=float(json['sourceOutputIndex']) if 'sourceOutputIndex' in json else None
        )


@event_class('WebAudio.nodeParamDisconnected')
@dataclass
class NodeParamDisconnected:
    '''
    Notifies that an AudioNode is disconnected to an AudioParam.
    '''
    context_id: GraphObjectId
    source_id: GraphObjectId
    destination_id: GraphObjectId
    source_output_index: typing.Optional[float]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> NodeParamDisconnected:
        return cls(
            context_id=GraphObjectId.from_json(json['contextId']),
            source_id=GraphObjectId.from_json(json['sourceId']),
            destination_id=GraphObjectId.from_json(json['destinationId']),
            source_output_index=float(json['sourceOutputIndex']) if 'sourceOutputIndex' in json else None
        )