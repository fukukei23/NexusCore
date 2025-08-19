
# === NexusCore/openenv\Lib\site-packages\openai\resources\fine_tuning\checkpoints\permissions.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List
from typing_extensions import Literal

import httpx

from .... import _legacy_response
from ...._types import NOT_GIVEN, Body, Query, Headers, NotGiven
from ...._utils import maybe_transform
from ...._compat import cached_property
from ...._resource import SyncAPIResource, AsyncAPIResource
from ...._response import to_streamed_response_wrapper, async_to_streamed_response_wrapper
from ....pagination import SyncPage, AsyncPage, SyncCursorPage, AsyncCursorPage
from ...._base_client import AsyncPaginator, make_request_options
from ....types.fine_tuning.checkpoints import permission_create_params, permission_retrieve_params
from ....types.fine_tuning.checkpoints.permission_create_response import PermissionCreateResponse
from ....types.fine_tuning.checkpoints.permission_delete_response import PermissionDeleteResponse
from ....types.fine_tuning.checkpoints.permission_retrieve_response import PermissionRetrieveResponse

__all__ = ["Permissions", "AsyncPermissions"]


class Permissions(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> PermissionsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return PermissionsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> PermissionsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return PermissionsWithStreamingResponse(self)

    def create(
        self,
        fine_tuned_model_checkpoint: str,
        *,
        project_ids: List[str],
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> SyncPage[PermissionCreateResponse]:
        """
        **NOTE:** Calling this endpoint requires an [admin API key](../admin-api-keys).

        This enables organization owners to share fine-tuned models with other projects
        in their organization.

        Args:
          project_ids: The project identifiers to grant access to.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not fine_tuned_model_checkpoint:
            raise ValueError(
                f"Expected a non-empty value for `fine_tuned_model_checkpoint` but received {fine_tuned_model_checkpoint!r}"
            )
        return self._get_api_list(
            f"/fine_tuning/checkpoints/{fine_tuned_model_checkpoint}/permissions",
            page=SyncPage[PermissionCreateResponse],
            body=maybe_transform({"project_ids": project_ids}, permission_create_params.PermissionCreateParams),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            model=PermissionCreateResponse,
            method="post",
        )

    def retrieve(
        self,
        fine_tuned_model_checkpoint: str,
        *,
        after: str | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        order: Literal["ascending", "descending"] | NotGiven = NOT_GIVEN,
        project_id: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> SyncCursorPage[PermissionRetrieveResponse]:
        """
        **NOTE:** This endpoint requires an [admin API key](../admin-api-keys).

        Organization owners can use this endpoint to view all permissions for a
        fine-tuned model checkpoint.

        Args:
          after: Identifier for the last permission ID from the previous pagination request.

          limit: Number of permissions to retrieve.

          order: The order in which to retrieve permissions.

          project_id: The ID of the project to get permissions for.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not fine_tuned_model_checkpoint:
            raise ValueError(
                f"Expected a non-empty value for `fine_tuned_model_checkpoint` but received {fine_tuned_model_checkpoint!r}"
            )
        return self._get_api_list(
            f"/fine_tuning/checkpoints/{fine_tuned_model_checkpoint}/permissions",
            page=SyncCursorPage[PermissionRetrieveResponse],
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "after": after,
                        "limit": limit,
                        "order": order,
                        "project_id": project_id,
                    },
                    permission_retrieve_params.PermissionRetrieveParams,
                ),
            ),
            model=PermissionRetrieveResponse,
        )

    def delete(
        self,
        permission_id: str,
        *,
        fine_tuned_model_checkpoint: str,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> PermissionDeleteResponse:
        """
        **NOTE:** This endpoint requires an [admin API key](../admin-api-keys).

        Organization owners can use this endpoint to delete a permission for a
        fine-tuned model checkpoint.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not fine_tuned_model_checkpoint:
            raise ValueError(
                f"Expected a non-empty value for `fine_tuned_model_checkpoint` but received {fine_tuned_model_checkpoint!r}"
            )
        if not permission_id:
            raise ValueError(f"Expected a non-empty value for `permission_id` but received {permission_id!r}")
        return self._delete(
            f"/fine_tuning/checkpoints/{fine_tuned_model_checkpoint}/permissions/{permission_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=PermissionDeleteResponse,
        )


class AsyncPermissions(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncPermissionsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return AsyncPermissionsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncPermissionsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return AsyncPermissionsWithStreamingResponse(self)

    def create(
        self,
        fine_tuned_model_checkpoint: str,
        *,
        project_ids: List[str],
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncPaginator[PermissionCreateResponse, AsyncPage[PermissionCreateResponse]]:
        """
        **NOTE:** Calling this endpoint requires an [admin API key](../admin-api-keys).

        This enables organization owners to share fine-tuned models with other projects
        in their organization.

        Args:
          project_ids: The project identifiers to grant access to.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not fine_tuned_model_checkpoint:
            raise ValueError(
                f"Expected a non-empty value for `fine_tuned_model_checkpoint` but received {fine_tuned_model_checkpoint!r}"
            )
        return self._get_api_list(
            f"/fine_tuning/checkpoints/{fine_tuned_model_checkpoint}/permissions",
            page=AsyncPage[PermissionCreateResponse],
            body=maybe_transform({"project_ids": project_ids}, permission_create_params.PermissionCreateParams),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            model=PermissionCreateResponse,
            method="post",
        )

    def retrieve(
        self,
        fine_tuned_model_checkpoint: str,
        *,
        after: str | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        order: Literal["ascending", "descending"] | NotGiven = NOT_GIVEN,
        project_id: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncPaginator[PermissionRetrieveResponse, AsyncCursorPage[PermissionRetrieveResponse]]:
        """
        **NOTE:** This endpoint requires an [admin API key](../admin-api-keys).

        Organization owners can use this endpoint to view all permissions for a
        fine-tuned model checkpoint.

        Args:
          after: Identifier for the last permission ID from the previous pagination request.

          limit: Number of permissions to retrieve.

          order: The order in which to retrieve permissions.

          project_id: The ID of the project to get permissions for.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not fine_tuned_model_checkpoint:
            raise ValueError(
                f"Expected a non-empty value for `fine_tuned_model_checkpoint` but received {fine_tuned_model_checkpoint!r}"
            )
        return self._get_api_list(
            f"/fine_tuning/checkpoints/{fine_tuned_model_checkpoint}/permissions",
            page=AsyncCursorPage[PermissionRetrieveResponse],
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "after": after,
                        "limit": limit,
                        "order": order,
                        "project_id": project_id,
                    },
                    permission_retrieve_params.PermissionRetrieveParams,
                ),
            ),
            model=PermissionRetrieveResponse,
        )

    async def delete(
        self,
        permission_id: str,
        *,
        fine_tuned_model_checkpoint: str,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> PermissionDeleteResponse:
        """
        **NOTE:** This endpoint requires an [admin API key](../admin-api-keys).

        Organization owners can use this endpoint to delete a permission for a
        fine-tuned model checkpoint.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not fine_tuned_model_checkpoint:
            raise ValueError(
                f"Expected a non-empty value for `fine_tuned_model_checkpoint` but received {fine_tuned_model_checkpoint!r}"
            )
        if not permission_id:
            raise ValueError(f"Expected a non-empty value for `permission_id` but received {permission_id!r}")
        return await self._delete(
            f"/fine_tuning/checkpoints/{fine_tuned_model_checkpoint}/permissions/{permission_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=PermissionDeleteResponse,
        )


class PermissionsWithRawResponse:
    def __init__(self, permissions: Permissions) -> None:
        self._permissions = permissions

        self.create = _legacy_response.to_raw_response_wrapper(
            permissions.create,
        )
        self.retrieve = _legacy_response.to_raw_response_wrapper(
            permissions.retrieve,
        )
        self.delete = _legacy_response.to_raw_response_wrapper(
            permissions.delete,
        )


class AsyncPermissionsWithRawResponse:
    def __init__(self, permissions: AsyncPermissions) -> None:
        self._permissions = permissions

        self.create = _legacy_response.async_to_raw_response_wrapper(
            permissions.create,
        )
        self.retrieve = _legacy_response.async_to_raw_response_wrapper(
            permissions.retrieve,
        )
        self.delete = _legacy_response.async_to_raw_response_wrapper(
            permissions.delete,
        )


class PermissionsWithStreamingResponse:
    def __init__(self, permissions: Permissions) -> None:
        self._permissions = permissions

        self.create = to_streamed_response_wrapper(
            permissions.create,
        )
        self.retrieve = to_streamed_response_wrapper(
            permissions.retrieve,
        )
        self.delete = to_streamed_response_wrapper(
            permissions.delete,
        )


class AsyncPermissionsWithStreamingResponse:
    def __init__(self, permissions: AsyncPermissions) -> None:
        self._permissions = permissions

        self.create = async_to_streamed_response_wrapper(
            permissions.create,
        )
        self.retrieve = async_to_streamed_response_wrapper(
            permissions.retrieve,
        )
        self.delete = async_to_streamed_response_wrapper(
            permissions.delete,
        )

# === NexusCore/openenv\Lib\site-packages\google\protobuf\internal\_parameterized.py ===
#! /usr/bin/env python
#
# Protocol Buffers - Google's data interchange format
# Copyright 2008 Google Inc.  All rights reserved.
#
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file or at
# https://developers.google.com/open-source/licenses/bsd

"""Adds support for parameterized tests to Python's unittest TestCase class.

A parameterized test is a method in a test case that is invoked with different
argument tuples.

A simple example:

  class AdditionExample(_parameterized.TestCase):
    @_parameterized.parameters(
       (1, 2, 3),
       (4, 5, 9),
       (1, 1, 3))
    def testAddition(self, op1, op2, result):
      self.assertEqual(result, op1 + op2)


Each invocation is a separate test case and properly isolated just
like a normal test method, with its own setUp/tearDown cycle. In the
example above, there are three separate testcases, one of which will
fail due to an assertion error (1 + 1 != 3).

Parameters for individual test cases can be tuples (with positional parameters)
or dictionaries (with named parameters):

  class AdditionExample(_parameterized.TestCase):
    @_parameterized.parameters(
       {'op1': 1, 'op2': 2, 'result': 3},
       {'op1': 4, 'op2': 5, 'result': 9},
    )
    def testAddition(self, op1, op2, result):
      self.assertEqual(result, op1 + op2)

If a parameterized test fails, the error message will show the
original test name (which is modified internally) and the arguments
for the specific invocation, which are part of the string returned by
the shortDescription() method on test cases.

The id method of the test, used internally by the unittest framework,
is also modified to show the arguments. To make sure that test names
stay the same across several invocations, object representations like

  >>> class Foo(object):
  ...  pass
  >>> repr(Foo())
  '<__main__.Foo object at 0x23d8610>'

are turned into '<__main__.Foo>'. For even more descriptive names,
especially in test logs, you can use the named_parameters decorator. In
this case, only tuples are supported, and the first parameters has to
be a string (or an object that returns an apt name when converted via
str()):

  class NamedExample(_parameterized.TestCase):
    @_parameterized.named_parameters(
       ('Normal', 'aa', 'aaa', True),
       ('EmptyPrefix', '', 'abc', True),
       ('BothEmpty', '', '', True))
    def testStartsWith(self, prefix, string, result):
      self.assertEqual(result, strings.startswith(prefix))

Named tests also have the benefit that they can be run individually
from the command line:

  $ testmodule.py NamedExample.testStartsWithNormal
  .
  --------------------------------------------------------------------
  Ran 1 test in 0.000s

  OK

Parameterized Classes
=====================
If invocation arguments are shared across test methods in a single
TestCase class, instead of decorating all test methods
individually, the class itself can be decorated:

  @_parameterized.parameters(
    (1, 2, 3)
    (4, 5, 9))
  class ArithmeticTest(_parameterized.TestCase):
    def testAdd(self, arg1, arg2, result):
      self.assertEqual(arg1 + arg2, result)

    def testSubtract(self, arg2, arg2, result):
      self.assertEqual(result - arg1, arg2)

Inputs from Iterables
=====================
If parameters should be shared across several test cases, or are dynamically
created from other sources, a single non-tuple iterable can be passed into
the decorator. This iterable will be used to obtain the test cases:

  class AdditionExample(_parameterized.TestCase):
    @_parameterized.parameters(
      c.op1, c.op2, c.result for c in testcases
    )
    def testAddition(self, op1, op2, result):
      self.assertEqual(result, op1 + op2)


Single-Argument Test Methods
============================
If a test method takes only one argument, the single argument does not need to
be wrapped into a tuple:

  class NegativeNumberExample(_parameterized.TestCase):
    @_parameterized.parameters(
       -1, -3, -4, -5
    )
    def testIsNegative(self, arg):
      self.assertTrue(IsNegative(arg))
"""

__author__ = 'tmarek@google.com (Torsten Marek)'

import functools
import re
import types
import unittest
import uuid

try:
  # Since python 3
  import collections.abc as collections_abc
except ImportError:
  # Won't work after python 3.8
  import collections as collections_abc

ADDR_RE = re.compile(r'\<([a-zA-Z0-9_\-\.]+) object at 0x[a-fA-F0-9]+\>')
_SEPARATOR = uuid.uuid1().hex
_FIRST_ARG = object()
_ARGUMENT_REPR = object()


def _CleanRepr(obj):
  return ADDR_RE.sub(r'<\1>', repr(obj))


# Helper function formerly from the unittest module, removed from it in
# Python 2.7.
def _StrClass(cls):
  return '%s.%s' % (cls.__module__, cls.__name__)


def _NonStringIterable(obj):
  return (isinstance(obj, collections_abc.Iterable) and
          not isinstance(obj, str))


def _FormatParameterList(testcase_params):
  if isinstance(testcase_params, collections_abc.Mapping):
    return ', '.join('%s=%s' % (argname, _CleanRepr(value))
                     for argname, value in testcase_params.items())
  elif _NonStringIterable(testcase_params):
    return ', '.join(map(_CleanRepr, testcase_params))
  else:
    return _FormatParameterList((testcase_params,))


class _ParameterizedTestIter(object):
  """Callable and iterable class for producing new test cases."""

  def __init__(self, test_method, testcases, naming_type):
    """Returns concrete test functions for a test and a list of parameters.

    The naming_type is used to determine the name of the concrete
    functions as reported by the unittest framework. If naming_type is
    _FIRST_ARG, the testcases must be tuples, and the first element must
    have a string representation that is a valid Python identifier.

    Args:
      test_method: The decorated test method.
      testcases: (list of tuple/dict) A list of parameter
                 tuples/dicts for individual test invocations.
      naming_type: The test naming type, either _NAMED or _ARGUMENT_REPR.
    """
    self._test_method = test_method
    self.testcases = testcases
    self._naming_type = naming_type

  def __call__(self, *args, **kwargs):
    raise RuntimeError('You appear to be running a parameterized test case '
                       'without having inherited from parameterized.'
                       'TestCase. This is bad because none of '
                       'your test cases are actually being run.')

  def __iter__(self):
    test_method = self._test_method
    naming_type = self._naming_type

    def MakeBoundParamTest(testcase_params):
      @functools.wraps(test_method)
      def BoundParamTest(self):
        if isinstance(testcase_params, collections_abc.Mapping):
          test_method(self, **testcase_params)
        elif _NonStringIterable(testcase_params):
          test_method(self, *testcase_params)
        else:
          test_method(self, testcase_params)

      if naming_type is _FIRST_ARG:
        # Signal the metaclass that the name of the test function is unique
        # and descriptive.
        BoundParamTest.__x_use_name__ = True
        BoundParamTest.__name__ += str(testcase_params[0])
        testcase_params = testcase_params[1:]
      elif naming_type is _ARGUMENT_REPR:
        # __x_extra_id__ is used to pass naming information to the __new__
        # method of TestGeneratorMetaclass.
        # The metaclass will make sure to create a unique, but nondescriptive
        # name for this test.
        BoundParamTest.__x_extra_id__ = '(%s)' % (
            _FormatParameterList(testcase_params),)
      else:
        raise RuntimeError('%s is not a valid naming type.' % (naming_type,))

      BoundParamTest.__doc__ = '%s(%s)' % (
          BoundParamTest.__name__, _FormatParameterList(testcase_params))
      if test_method.__doc__:
        BoundParamTest.__doc__ += '\n%s' % (test_method.__doc__,)
      return BoundParamTest
    return (MakeBoundParamTest(c) for c in self.testcases)


def _IsSingletonList(testcases):
  """True iff testcases contains only a single non-tuple element."""
  return len(testcases) == 1 and not isinstance(testcases[0], tuple)


def _ModifyClass(class_object, testcases, naming_type):
  assert not getattr(class_object, '_id_suffix', None), (
      'Cannot add parameters to %s,'
      ' which already has parameterized methods.' % (class_object,))
  class_object._id_suffix = id_suffix = {}
  # We change the size of __dict__ while we iterate over it,
  # which Python 3.x will complain about, so use copy().
  for name, obj in class_object.__dict__.copy().items():
    if (name.startswith(unittest.TestLoader.testMethodPrefix)
        and isinstance(obj, types.FunctionType)):
      delattr(class_object, name)
      methods = {}
      _UpdateClassDictForParamTestCase(
          methods, id_suffix, name,
          _ParameterizedTestIter(obj, testcases, naming_type))
      for name, meth in methods.items():
        setattr(class_object, name, meth)


def _ParameterDecorator(naming_type, testcases):
  """Implementation of the parameterization decorators.

  Args:
    naming_type: The naming type.
    testcases: Testcase parameters.

  Returns:
    A function for modifying the decorated object.
  """
  def _Apply(obj):
    if isinstance(obj, type):
      _ModifyClass(
          obj,
          list(testcases) if not isinstance(testcases, collections_abc.Sequence)
          else testcases,
          naming_type)
      return obj
    else:
      return _ParameterizedTestIter(obj, testcases, naming_type)

  if _IsSingletonList(testcases):
    assert _NonStringIterable(testcases[0]), (
        'Single parameter argument must be a non-string iterable')
    testcases = testcases[0]

  return _Apply


def parameters(*testcases):  # pylint: disable=invalid-name
  """A decorator for creating parameterized tests.

  See the module docstring for a usage example.
  Args:
    *testcases: Parameters for the decorated method, either a single
                iterable, or a list of tuples/dicts/objects (for tests
                with only one argument).

  Returns:
     A test generator to be handled by TestGeneratorMetaclass.
  """
  return _ParameterDecorator(_ARGUMENT_REPR, testcases)


def named_parameters(*testcases):  # pylint: disable=invalid-name
  """A decorator for creating parameterized tests.

  See the module docstring for a usage example. The first element of
  each parameter tuple should be a string and will be appended to the
  name of the test method.

  Args:
    *testcases: Parameters for the decorated method, either a single
                iterable, or a list of tuples.

  Returns:
     A test generator to be handled by TestGeneratorMetaclass.
  """
  return _ParameterDecorator(_FIRST_ARG, testcases)


class TestGeneratorMetaclass(type):
  """Metaclass for test cases with test generators.

  A test generator is an iterable in a testcase that produces callables. These
  callables must be single-argument methods. These methods are injected into
  the class namespace and the original iterable is removed. If the name of the
  iterable conforms to the test pattern, the injected methods will be picked
  up as tests by the unittest framework.

  In general, it is supposed to be used in conjunction with the
  parameters decorator.
  """

  def __new__(mcs, class_name, bases, dct):
    dct['_id_suffix'] = id_suffix = {}
    for name, obj in dct.copy().items():
      if (name.startswith(unittest.TestLoader.testMethodPrefix) and
          _NonStringIterable(obj)):
        iterator = iter(obj)
        dct.pop(name)
        _UpdateClassDictForParamTestCase(dct, id_suffix, name, iterator)

    return type.__new__(mcs, class_name, bases, dct)


def _UpdateClassDictForParamTestCase(dct, id_suffix, name, iterator):
  """Adds individual test cases to a dictionary.

  Args:
    dct: The target dictionary.
    id_suffix: The dictionary for mapping names to test IDs.
    name: The original name of the test case.
    iterator: The iterator generating the individual test cases.
  """
  for idx, func in enumerate(iterator):
    assert callable(func), 'Test generators must yield callables, got %r' % (
        func,)
    if getattr(func, '__x_use_name__', False):
      new_name = func.__name__
    else:
      new_name = '%s%s%d' % (name, _SEPARATOR, idx)
    assert new_name not in dct, (
        'Name of parameterized test case "%s" not unique' % (new_name,))
    dct[new_name] = func
    id_suffix[new_name] = getattr(func, '__x_extra_id__', '')


class TestCase(unittest.TestCase, metaclass=TestGeneratorMetaclass):
  """Base class for test cases using the parameters decorator."""

  def _OriginalName(self):
    return self._testMethodName.split(_SEPARATOR)[0]

  def __str__(self):
    return '%s (%s)' % (self._OriginalName(), _StrClass(self.__class__))

  def id(self):  # pylint: disable=invalid-name
    """Returns the descriptive ID of the test.

    This is used internally by the unittesting framework to get a name
    for the test to be used in reports.

    Returns:
      The test id.
    """
    return '%s.%s%s' % (_StrClass(self.__class__),
                        self._OriginalName(),
                        self._id_suffix.get(self._testMethodName, ''))


def CoopTestCase(other_base_class):
  """Returns a new base class with a cooperative metaclass base.

  This enables the TestCase to be used in combination
  with other base classes that have custom metaclasses, such as
  mox.MoxTestBase.

  Only works with metaclasses that do not override type.__new__.

  Example:

    import google3
    import mox

    from google.protobuf.internal import _parameterized

    class ExampleTest(parameterized.CoopTestCase(mox.MoxTestBase)):
      ...

  Args:
    other_base_class: (class) A test case base class.

  Returns:
    A new class object.
  """
  metaclass = type(
      'CoopMetaclass',
      (other_base_class.__metaclass__,
       TestGeneratorMetaclass), {})
  return metaclass(
      'CoopTestCase',
      (other_base_class, TestCase), {})

# === NexusCore/openenv\Lib\site-packages\httpcore\_async\connection_pool.py ===
from __future__ import annotations

import ssl
import sys
import types
import typing

from .._backends.auto import AutoBackend
from .._backends.base import SOCKET_OPTION, AsyncNetworkBackend
from .._exceptions import ConnectionNotAvailable, UnsupportedProtocol
from .._models import Origin, Proxy, Request, Response
from .._synchronization import AsyncEvent, AsyncShieldCancellation, AsyncThreadLock
from .connection import AsyncHTTPConnection
from .interfaces import AsyncConnectionInterface, AsyncRequestInterface


class AsyncPoolRequest:
    def __init__(self, request: Request) -> None:
        self.request = request
        self.connection: AsyncConnectionInterface | None = None
        self._connection_acquired = AsyncEvent()

    def assign_to_connection(self, connection: AsyncConnectionInterface | None) -> None:
        self.connection = connection
        self._connection_acquired.set()

    def clear_connection(self) -> None:
        self.connection = None
        self._connection_acquired = AsyncEvent()

    async def wait_for_connection(
        self, timeout: float | None = None
    ) -> AsyncConnectionInterface:
        if self.connection is None:
            await self._connection_acquired.wait(timeout=timeout)
        assert self.connection is not None
        return self.connection

    def is_queued(self) -> bool:
        return self.connection is None


class AsyncConnectionPool(AsyncRequestInterface):
    """
    A connection pool for making HTTP requests.
    """

    def __init__(
        self,
        ssl_context: ssl.SSLContext | None = None,
        proxy: Proxy | None = None,
        max_connections: int | None = 10,
        max_keepalive_connections: int | None = None,
        keepalive_expiry: float | None = None,
        http1: bool = True,
        http2: bool = False,
        retries: int = 0,
        local_address: str | None = None,
        uds: str | None = None,
        network_backend: AsyncNetworkBackend | None = None,
        socket_options: typing.Iterable[SOCKET_OPTION] | None = None,
    ) -> None:
        """
        A connection pool for making HTTP requests.

        Parameters:
            ssl_context: An SSL context to use for verifying connections.
                If not specified, the default `httpcore.default_ssl_context()`
                will be used.
            max_connections: The maximum number of concurrent HTTP connections that
                the pool should allow. Any attempt to send a request on a pool that
                would exceed this amount will block until a connection is available.
            max_keepalive_connections: The maximum number of idle HTTP connections
                that will be maintained in the pool.
            keepalive_expiry: The duration in seconds that an idle HTTP connection
                may be maintained for before being expired from the pool.
            http1: A boolean indicating if HTTP/1.1 requests should be supported
                by the connection pool. Defaults to True.
            http2: A boolean indicating if HTTP/2 requests should be supported by
                the connection pool. Defaults to False.
            retries: The maximum number of retries when trying to establish a
                connection.
            local_address: Local address to connect from. Can also be used to connect
                using a particular address family. Using `local_address="0.0.0.0"`
                will connect using an `AF_INET` address (IPv4), while using
                `local_address="::"` will connect using an `AF_INET6` address (IPv6).
            uds: Path to a Unix Domain Socket to use instead of TCP sockets.
            network_backend: A backend instance to use for handling network I/O.
            socket_options: Socket options that have to be included
             in the TCP socket when the connection was established.
        """
        self._ssl_context = ssl_context
        self._proxy = proxy
        self._max_connections = (
            sys.maxsize if max_connections is None else max_connections
        )
        self._max_keepalive_connections = (
            sys.maxsize
            if max_keepalive_connections is None
            else max_keepalive_connections
        )
        self._max_keepalive_connections = min(
            self._max_connections, self._max_keepalive_connections
        )

        self._keepalive_expiry = keepalive_expiry
        self._http1 = http1
        self._http2 = http2
        self._retries = retries
        self._local_address = local_address
        self._uds = uds

        self._network_backend = (
            AutoBackend() if network_backend is None else network_backend
        )
        self._socket_options = socket_options

        # The mutable state on a connection pool is the queue of incoming requests,
        # and the set of connections that are servicing those requests.
        self._connections: list[AsyncConnectionInterface] = []
        self._requests: list[AsyncPoolRequest] = []

        # We only mutate the state of the connection pool within an 'optional_thread_lock'
        # context. This holds a threading lock unless we're running in async mode,
        # in which case it is a no-op.
        self._optional_thread_lock = AsyncThreadLock()

    def create_connection(self, origin: Origin) -> AsyncConnectionInterface:
        if self._proxy is not None:
            if self._proxy.url.scheme in (b"socks5", b"socks5h"):
                from .socks_proxy import AsyncSocks5Connection

                return AsyncSocks5Connection(
                    proxy_origin=self._proxy.url.origin,
                    proxy_auth=self._proxy.auth,
                    remote_origin=origin,
                    ssl_context=self._ssl_context,
                    keepalive_expiry=self._keepalive_expiry,
                    http1=self._http1,
                    http2=self._http2,
                    network_backend=self._network_backend,
                )
            elif origin.scheme == b"http":
                from .http_proxy import AsyncForwardHTTPConnection

                return AsyncForwardHTTPConnection(
                    proxy_origin=self._proxy.url.origin,
                    proxy_headers=self._proxy.headers,
                    proxy_ssl_context=self._proxy.ssl_context,
                    remote_origin=origin,
                    keepalive_expiry=self._keepalive_expiry,
                    network_backend=self._network_backend,
                )
            from .http_proxy import AsyncTunnelHTTPConnection

            return AsyncTunnelHTTPConnection(
                proxy_origin=self._proxy.url.origin,
                proxy_headers=self._proxy.headers,
                proxy_ssl_context=self._proxy.ssl_context,
                remote_origin=origin,
                ssl_context=self._ssl_context,
                keepalive_expiry=self._keepalive_expiry,
                http1=self._http1,
                http2=self._http2,
                network_backend=self._network_backend,
            )

        return AsyncHTTPConnection(
            origin=origin,
            ssl_context=self._ssl_context,
            keepalive_expiry=self._keepalive_expiry,
            http1=self._http1,
            http2=self._http2,
            retries=self._retries,
            local_address=self._local_address,
            uds=self._uds,
            network_backend=self._network_backend,
            socket_options=self._socket_options,
        )

    @property
    def connections(self) -> list[AsyncConnectionInterface]:
        """
        Return a list of the connections currently in the pool.

        For example:

        ```python
        >>> pool.connections
        [
            <AsyncHTTPConnection ['https://example.com:443', HTTP/1.1, ACTIVE, Request Count: 6]>,
            <AsyncHTTPConnection ['https://example.com:443', HTTP/1.1, IDLE, Request Count: 9]> ,
            <AsyncHTTPConnection ['http://example.com:80', HTTP/1.1, IDLE, Request Count: 1]>,
        ]
        ```
        """
        return list(self._connections)

    async def handle_async_request(self, request: Request) -> Response:
        """
        Send an HTTP request, and return an HTTP response.

        This is the core implementation that is called into by `.request()` or `.stream()`.
        """
        scheme = request.url.scheme.decode()
        if scheme == "":
            raise UnsupportedProtocol(
                "Request URL is missing an 'http://' or 'https://' protocol."
            )
        if scheme not in ("http", "https", "ws", "wss"):
            raise UnsupportedProtocol(
                f"Request URL has an unsupported protocol '{scheme}://'."
            )

        timeouts = request.extensions.get("timeout", {})
        timeout = timeouts.get("pool", None)

        with self._optional_thread_lock:
            # Add the incoming request to our request queue.
            pool_request = AsyncPoolRequest(request)
            self._requests.append(pool_request)

        try:
            while True:
                with self._optional_thread_lock:
                    # Assign incoming requests to available connections,
                    # closing or creating new connections as required.
                    closing = self._assign_requests_to_connections()
                await self._close_connections(closing)

                # Wait until this request has an assigned connection.
                connection = await pool_request.wait_for_connection(timeout=timeout)

                try:
                    # Send the request on the assigned connection.
                    response = await connection.handle_async_request(
                        pool_request.request
                    )
                except ConnectionNotAvailable:
                    # In some cases a connection may initially be available to
                    # handle a request, but then become unavailable.
                    #
                    # In this case we clear the connection and try again.
                    pool_request.clear_connection()
                else:
                    break  # pragma: nocover

        except BaseException as exc:
            with self._optional_thread_lock:
                # For any exception or cancellation we remove the request from
                # the queue, and then re-assign requests to connections.
                self._requests.remove(pool_request)
                closing = self._assign_requests_to_connections()

            await self._close_connections(closing)
            raise exc from None

        # Return the response. Note that in this case we still have to manage
        # the point at which the response is closed.
        assert isinstance(response.stream, typing.AsyncIterable)
        return Response(
            status=response.status,
            headers=response.headers,
            content=PoolByteStream(
                stream=response.stream, pool_request=pool_request, pool=self
            ),
            extensions=response.extensions,
        )

    def _assign_requests_to_connections(self) -> list[AsyncConnectionInterface]:
        """
        Manage the state of the connection pool, assigning incoming
        requests to connections as available.

        Called whenever a new request is added or removed from the pool.

        Any closing connections are returned, allowing the I/O for closing
        those connections to be handled seperately.
        """
        closing_connections = []

        # First we handle cleaning up any connections that are closed,
        # have expired their keep-alive, or surplus idle connections.
        for connection in list(self._connections):
            if connection.is_closed():
                # log: "removing closed connection"
                self._connections.remove(connection)
            elif connection.has_expired():
                # log: "closing expired connection"
                self._connections.remove(connection)
                closing_connections.append(connection)
            elif (
                connection.is_idle()
                and len([connection.is_idle() for connection in self._connections])
                > self._max_keepalive_connections
            ):
                # log: "closing idle connection"
                self._connections.remove(connection)
                closing_connections.append(connection)

        # Assign queued requests to connections.
        queued_requests = [request for request in self._requests if request.is_queued()]
        for pool_request in queued_requests:
            origin = pool_request.request.url.origin
            available_connections = [
                connection
                for connection in self._connections
                if connection.can_handle_request(origin) and connection.is_available()
            ]
            idle_connections = [
                connection for connection in self._connections if connection.is_idle()
            ]

            # There are three cases for how we may be able to handle the request:
            #
            # 1. There is an existing connection that can handle the request.
            # 2. We can create a new connection to handle the request.
            # 3. We can close an idle connection and then create a new connection
            #    to handle the request.
            if available_connections:
                # log: "reusing existing connection"
                connection = available_connections[0]
                pool_request.assign_to_connection(connection)
            elif len(self._connections) < self._max_connections:
                # log: "creating new connection"
                connection = self.create_connection(origin)
                self._connections.append(connection)
                pool_request.assign_to_connection(connection)
            elif idle_connections:
                # log: "closing idle connection"
                connection = idle_connections[0]
                self._connections.remove(connection)
                closing_connections.append(connection)
                # log: "creating new connection"
                connection = self.create_connection(origin)
                self._connections.append(connection)
                pool_request.assign_to_connection(connection)

        return closing_connections

    async def _close_connections(self, closing: list[AsyncConnectionInterface]) -> None:
        # Close connections which have been removed from the pool.
        with AsyncShieldCancellation():
            for connection in closing:
                await connection.aclose()

    async def aclose(self) -> None:
        # Explicitly close the connection pool.
        # Clears all existing requests and connections.
        with self._optional_thread_lock:
            closing_connections = list(self._connections)
            self._connections = []
        await self._close_connections(closing_connections)

    async def __aenter__(self) -> AsyncConnectionPool:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: types.TracebackType | None = None,
    ) -> None:
        await self.aclose()

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        with self._optional_thread_lock:
            request_is_queued = [request.is_queued() for request in self._requests]
            connection_is_idle = [
                connection.is_idle() for connection in self._connections
            ]

            num_active_requests = request_is_queued.count(False)
            num_queued_requests = request_is_queued.count(True)
            num_active_connections = connection_is_idle.count(False)
            num_idle_connections = connection_is_idle.count(True)

        requests_info = (
            f"Requests: {num_active_requests} active, {num_queued_requests} queued"
        )
        connection_info = (
            f"Connections: {num_active_connections} active, {num_idle_connections} idle"
        )

        return f"<{class_name} [{requests_info} | {connection_info}]>"


class PoolByteStream:
    def __init__(
        self,
        stream: typing.AsyncIterable[bytes],
        pool_request: AsyncPoolRequest,
        pool: AsyncConnectionPool,
    ) -> None:
        self._stream = stream
        self._pool_request = pool_request
        self._pool = pool
        self._closed = False

    async def __aiter__(self) -> typing.AsyncIterator[bytes]:
        try:
            async for part in self._stream:
                yield part
        except BaseException as exc:
            await self.aclose()
            raise exc from None

    async def aclose(self) -> None:
        if not self._closed:
            self._closed = True
            with AsyncShieldCancellation():
                if hasattr(self._stream, "aclose"):
                    await self._stream.aclose()

            with self._pool._optional_thread_lock:
                self._pool._requests.remove(self._pool_request)
                closing = self._pool._assign_requests_to_connections()

            await self._pool._close_connections(closing)

# === NexusCore/openenv\Lib\site-packages\httpcore\_sync\connection_pool.py ===
from __future__ import annotations

import ssl
import sys
import types
import typing

from .._backends.sync import SyncBackend
from .._backends.base import SOCKET_OPTION, NetworkBackend
from .._exceptions import ConnectionNotAvailable, UnsupportedProtocol
from .._models import Origin, Proxy, Request, Response
from .._synchronization import Event, ShieldCancellation, ThreadLock
from .connection import HTTPConnection
from .interfaces import ConnectionInterface, RequestInterface


class PoolRequest:
    def __init__(self, request: Request) -> None:
        self.request = request
        self.connection: ConnectionInterface | None = None
        self._connection_acquired = Event()

    def assign_to_connection(self, connection: ConnectionInterface | None) -> None:
        self.connection = connection
        self._connection_acquired.set()

    def clear_connection(self) -> None:
        self.connection = None
        self._connection_acquired = Event()

    def wait_for_connection(
        self, timeout: float | None = None
    ) -> ConnectionInterface:
        if self.connection is None:
            self._connection_acquired.wait(timeout=timeout)
        assert self.connection is not None
        return self.connection

    def is_queued(self) -> bool:
        return self.connection is None


class ConnectionPool(RequestInterface):
    """
    A connection pool for making HTTP requests.
    """

    def __init__(
        self,
        ssl_context: ssl.SSLContext | None = None,
        proxy: Proxy | None = None,
        max_connections: int | None = 10,
        max_keepalive_connections: int | None = None,
        keepalive_expiry: float | None = None,
        http1: bool = True,
        http2: bool = False,
        retries: int = 0,
        local_address: str | None = None,
        uds: str | None = None,
        network_backend: NetworkBackend | None = None,
        socket_options: typing.Iterable[SOCKET_OPTION] | None = None,
    ) -> None:
        """
        A connection pool for making HTTP requests.

        Parameters:
            ssl_context: An SSL context to use for verifying connections.
                If not specified, the default `httpcore.default_ssl_context()`
                will be used.
            max_connections: The maximum number of concurrent HTTP connections that
                the pool should allow. Any attempt to send a request on a pool that
                would exceed this amount will block until a connection is available.
            max_keepalive_connections: The maximum number of idle HTTP connections
                that will be maintained in the pool.
            keepalive_expiry: The duration in seconds that an idle HTTP connection
                may be maintained for before being expired from the pool.
            http1: A boolean indicating if HTTP/1.1 requests should be supported
                by the connection pool. Defaults to True.
            http2: A boolean indicating if HTTP/2 requests should be supported by
                the connection pool. Defaults to False.
            retries: The maximum number of retries when trying to establish a
                connection.
            local_address: Local address to connect from. Can also be used to connect
                using a particular address family. Using `local_address="0.0.0.0"`
                will connect using an `AF_INET` address (IPv4), while using
                `local_address="::"` will connect using an `AF_INET6` address (IPv6).
            uds: Path to a Unix Domain Socket to use instead of TCP sockets.
            network_backend: A backend instance to use for handling network I/O.
            socket_options: Socket options that have to be included
             in the TCP socket when the connection was established.
        """
        self._ssl_context = ssl_context
        self._proxy = proxy
        self._max_connections = (
            sys.maxsize if max_connections is None else max_connections
        )
        self._max_keepalive_connections = (
            sys.maxsize
            if max_keepalive_connections is None
            else max_keepalive_connections
        )
        self._max_keepalive_connections = min(
            self._max_connections, self._max_keepalive_connections
        )

        self._keepalive_expiry = keepalive_expiry
        self._http1 = http1
        self._http2 = http2
        self._retries = retries
        self._local_address = local_address
        self._uds = uds

        self._network_backend = (
            SyncBackend() if network_backend is None else network_backend
        )
        self._socket_options = socket_options

        # The mutable state on a connection pool is the queue of incoming requests,
        # and the set of connections that are servicing those requests.
        self._connections: list[ConnectionInterface] = []
        self._requests: list[PoolRequest] = []

        # We only mutate the state of the connection pool within an 'optional_thread_lock'
        # context. This holds a threading lock unless we're running in async mode,
        # in which case it is a no-op.
        self._optional_thread_lock = ThreadLock()

    def create_connection(self, origin: Origin) -> ConnectionInterface:
        if self._proxy is not None:
            if self._proxy.url.scheme in (b"socks5", b"socks5h"):
                from .socks_proxy import Socks5Connection

                return Socks5Connection(
                    proxy_origin=self._proxy.url.origin,
                    proxy_auth=self._proxy.auth,
                    remote_origin=origin,
                    ssl_context=self._ssl_context,
                    keepalive_expiry=self._keepalive_expiry,
                    http1=self._http1,
                    http2=self._http2,
                    network_backend=self._network_backend,
                )
            elif origin.scheme == b"http":
                from .http_proxy import ForwardHTTPConnection

                return ForwardHTTPConnection(
                    proxy_origin=self._proxy.url.origin,
                    proxy_headers=self._proxy.headers,
                    proxy_ssl_context=self._proxy.ssl_context,
                    remote_origin=origin,
                    keepalive_expiry=self._keepalive_expiry,
                    network_backend=self._network_backend,
                )
            from .http_proxy import TunnelHTTPConnection

            return TunnelHTTPConnection(
                proxy_origin=self._proxy.url.origin,
                proxy_headers=self._proxy.headers,
                proxy_ssl_context=self._proxy.ssl_context,
                remote_origin=origin,
                ssl_context=self._ssl_context,
                keepalive_expiry=self._keepalive_expiry,
                http1=self._http1,
                http2=self._http2,
                network_backend=self._network_backend,
            )

        return HTTPConnection(
            origin=origin,
            ssl_context=self._ssl_context,
            keepalive_expiry=self._keepalive_expiry,
            http1=self._http1,
            http2=self._http2,
            retries=self._retries,
            local_address=self._local_address,
            uds=self._uds,
            network_backend=self._network_backend,
            socket_options=self._socket_options,
        )

    @property
    def connections(self) -> list[ConnectionInterface]:
        """
        Return a list of the connections currently in the pool.

        For example:

        ```python
        >>> pool.connections
        [
            <HTTPConnection ['https://example.com:443', HTTP/1.1, ACTIVE, Request Count: 6]>,
            <HTTPConnection ['https://example.com:443', HTTP/1.1, IDLE, Request Count: 9]> ,
            <HTTPConnection ['http://example.com:80', HTTP/1.1, IDLE, Request Count: 1]>,
        ]
        ```
        """
        return list(self._connections)

    def handle_request(self, request: Request) -> Response:
        """
        Send an HTTP request, and return an HTTP response.

        This is the core implementation that is called into by `.request()` or `.stream()`.
        """
        scheme = request.url.scheme.decode()
        if scheme == "":
            raise UnsupportedProtocol(
                "Request URL is missing an 'http://' or 'https://' protocol."
            )
        if scheme not in ("http", "https", "ws", "wss"):
            raise UnsupportedProtocol(
                f"Request URL has an unsupported protocol '{scheme}://'."
            )

        timeouts = request.extensions.get("timeout", {})
        timeout = timeouts.get("pool", None)

        with self._optional_thread_lock:
            # Add the incoming request to our request queue.
            pool_request = PoolRequest(request)
            self._requests.append(pool_request)

        try:
            while True:
                with self._optional_thread_lock:
                    # Assign incoming requests to available connections,
                    # closing or creating new connections as required.
                    closing = self._assign_requests_to_connections()
                self._close_connections(closing)

                # Wait until this request has an assigned connection.
                connection = pool_request.wait_for_connection(timeout=timeout)

                try:
                    # Send the request on the assigned connection.
                    response = connection.handle_request(
                        pool_request.request
                    )
                except ConnectionNotAvailable:
                    # In some cases a connection may initially be available to
                    # handle a request, but then become unavailable.
                    #
                    # In this case we clear the connection and try again.
                    pool_request.clear_connection()
                else:
                    break  # pragma: nocover

        except BaseException as exc:
            with self._optional_thread_lock:
                # For any exception or cancellation we remove the request from
                # the queue, and then re-assign requests to connections.
                self._requests.remove(pool_request)
                closing = self._assign_requests_to_connections()

            self._close_connections(closing)
            raise exc from None

        # Return the response. Note that in this case we still have to manage
        # the point at which the response is closed.
        assert isinstance(response.stream, typing.Iterable)
        return Response(
            status=response.status,
            headers=response.headers,
            content=PoolByteStream(
                stream=response.stream, pool_request=pool_request, pool=self
            ),
            extensions=response.extensions,
        )

    def _assign_requests_to_connections(self) -> list[ConnectionInterface]:
        """
        Manage the state of the connection pool, assigning incoming
        requests to connections as available.

        Called whenever a new request is added or removed from the pool.

        Any closing connections are returned, allowing the I/O for closing
        those connections to be handled seperately.
        """
        closing_connections = []

        # First we handle cleaning up any connections that are closed,
        # have expired their keep-alive, or surplus idle connections.
        for connection in list(self._connections):
            if connection.is_closed():
                # log: "removing closed connection"
                self._connections.remove(connection)
            elif connection.has_expired():
                # log: "closing expired connection"
                self._connections.remove(connection)
                closing_connections.append(connection)
            elif (
                connection.is_idle()
                and len([connection.is_idle() for connection in self._connections])
                > self._max_keepalive_connections
            ):
                # log: "closing idle connection"
                self._connections.remove(connection)
                closing_connections.append(connection)

        # Assign queued requests to connections.
        queued_requests = [request for request in self._requests if request.is_queued()]
        for pool_request in queued_requests:
            origin = pool_request.request.url.origin
            available_connections = [
                connection
                for connection in self._connections
                if connection.can_handle_request(origin) and connection.is_available()
            ]
            idle_connections = [
                connection for connection in self._connections if connection.is_idle()
            ]

            # There are three cases for how we may be able to handle the request:
            #
            # 1. There is an existing connection that can handle the request.
            # 2. We can create a new connection to handle the request.
            # 3. We can close an idle connection and then create a new connection
            #    to handle the request.
            if available_connections:
                # log: "reusing existing connection"
                connection = available_connections[0]
                pool_request.assign_to_connection(connection)
            elif len(self._connections) < self._max_connections:
                # log: "creating new connection"
                connection = self.create_connection(origin)
                self._connections.append(connection)
                pool_request.assign_to_connection(connection)
            elif idle_connections:
                # log: "closing idle connection"
                connection = idle_connections[0]
                self._connections.remove(connection)
                closing_connections.append(connection)
                # log: "creating new connection"
                connection = self.create_connection(origin)
                self._connections.append(connection)
                pool_request.assign_to_connection(connection)

        return closing_connections

    def _close_connections(self, closing: list[ConnectionInterface]) -> None:
        # Close connections which have been removed from the pool.
        with ShieldCancellation():
            for connection in closing:
                connection.close()

    def close(self) -> None:
        # Explicitly close the connection pool.
        # Clears all existing requests and connections.
        with self._optional_thread_lock:
            closing_connections = list(self._connections)
            self._connections = []
        self._close_connections(closing_connections)

    def __enter__(self) -> ConnectionPool:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: types.TracebackType | None = None,
    ) -> None:
        self.close()

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        with self._optional_thread_lock:
            request_is_queued = [request.is_queued() for request in self._requests]
            connection_is_idle = [
                connection.is_idle() for connection in self._connections
            ]

            num_active_requests = request_is_queued.count(False)
            num_queued_requests = request_is_queued.count(True)
            num_active_connections = connection_is_idle.count(False)
            num_idle_connections = connection_is_idle.count(True)

        requests_info = (
            f"Requests: {num_active_requests} active, {num_queued_requests} queued"
        )
        connection_info = (
            f"Connections: {num_active_connections} active, {num_idle_connections} idle"
        )

        return f"<{class_name} [{requests_info} | {connection_info}]>"


class PoolByteStream:
    def __init__(
        self,
        stream: typing.Iterable[bytes],
        pool_request: PoolRequest,
        pool: ConnectionPool,
    ) -> None:
        self._stream = stream
        self._pool_request = pool_request
        self._pool = pool
        self._closed = False

    def __iter__(self) -> typing.Iterator[bytes]:
        try:
            for part in self._stream:
                yield part
        except BaseException as exc:
            self.close()
            raise exc from None

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            with ShieldCancellation():
                if hasattr(self._stream, "close"):
                    self._stream.close()

            with self._pool._optional_thread_lock:
                self._pool._requests.remove(self._pool_request)
                closing = self._pool._assign_requests_to_connections()

            self._pool._close_connections(closing)

# === NexusCore/openenv\Lib\site-packages\zmq\sugar\context.py ===
"""Python bindings for 0MQ."""

# Copyright (C) PyZMQ Developers
# Distributed under the terms of the Modified BSD License.

from __future__ import annotations

import atexit
import os
from threading import Lock
from typing import Any, Callable, Generic, TypeVar, overload
from warnings import warn
from weakref import WeakSet

import zmq
from zmq._typing import TypeAlias
from zmq.backend import Context as ContextBase
from zmq.constants import ContextOption, Errno, SocketOption
from zmq.error import ZMQError
from zmq.utils.interop import cast_int_addr

from .attrsettr import AttributeSetter, OptValT
from .socket import Socket, SyncSocket

# notice when exiting, to avoid triggering term on exit
_exiting = False


def _notice_atexit() -> None:
    global _exiting
    _exiting = True


atexit.register(_notice_atexit)

_ContextType = TypeVar('_ContextType', bound='Context')
_SocketType = TypeVar('_SocketType', bound='Socket', covariant=True)


class Context(ContextBase, AttributeSetter, Generic[_SocketType]):
    """Create a zmq Context

    A zmq Context creates sockets via its ``ctx.socket`` method.

    .. versionchanged:: 24

        When using a Context as a context manager (``with zmq.Context()``),
        or deleting a context without closing it first,
        ``ctx.destroy()`` is called,
        closing any leftover sockets,
        instead of `ctx.term()` which requires sockets to be closed first.

        This prevents hangs caused by `ctx.term()` if sockets are left open,
        but means that unclean destruction of contexts
        (with sockets left open) is not safe
        if sockets are managed in other threads.

    .. versionadded:: 25

        Contexts can now be shadowed by passing another Context.
        This helps in creating an async copy of a sync context or vice versa::

            ctx = zmq.Context(async_ctx)

        Which previously had to be::

            ctx = zmq.Context.shadow(async_ctx.underlying)
    """

    sockopts: dict[int, Any]
    _instance: Any = None
    _instance_lock = Lock()
    _instance_pid: int | None = None
    _shadow = False
    _shadow_obj = None
    _warn_destroy_close = False
    _sockets: WeakSet
    # mypy doesn't like a default value here
    _socket_class: type[_SocketType] = Socket  # type: ignore

    @overload
    def __init__(self: SyncContext, io_threads: int = 1): ...

    @overload
    def __init__(self: SyncContext, io_threads: Context, /): ...

    @overload
    def __init__(self: SyncContext, *, shadow: Context | int): ...

    def __init__(
        self: SyncContext,
        io_threads: int | Context = 1,
        shadow: Context | int = 0,
    ) -> None:
        if isinstance(io_threads, Context):
            # allow positional shadow `zmq.Context(zmq.asyncio.Context())`
            # this s
            shadow = io_threads
            io_threads = 1

        shadow_address: int = 0
        if shadow:
            self._shadow = True
            # hold a reference to the shadow object
            self._shadow_obj = shadow
            if not isinstance(shadow, int):
                try:
                    shadow = shadow.underlying
                except AttributeError:
                    pass
            shadow_address = cast_int_addr(shadow)
        else:
            self._shadow = False
        super().__init__(io_threads=io_threads, shadow=shadow_address)
        self.sockopts = {}
        self._sockets = WeakSet()

    def __del__(self) -> None:
        """Deleting a Context without closing it destroys it and all sockets.

        .. versionchanged:: 24
            Switch from threadsafe `term()` which hangs in the event of open sockets
            to less safe `destroy()` which
            warns about any leftover sockets and closes them.
        """

        # Calling locals() here conceals issue #1167 on Windows CPython 3.5.4.
        locals()

        if not self._shadow and not _exiting and not self.closed:
            self._warn_destroy_close = True
            if warn is not None and getattr(self, "_sockets", None) is not None:
                # warn can be None during process teardown
                warn(
                    f"Unclosed context {self}",
                    ResourceWarning,
                    stacklevel=2,
                    source=self,
                )
            self.destroy()

    _repr_cls = "zmq.Context"

    def __repr__(self) -> str:
        cls = self.__class__
        # look up _repr_cls on exact class, not inherited
        _repr_cls = cls.__dict__.get("_repr_cls", None)
        if _repr_cls is None:
            _repr_cls = f"{cls.__module__}.{cls.__name__}"

        closed = ' closed' if self.closed else ''
        if getattr(self, "_sockets", None):
            n_sockets = len(self._sockets)
            s = 's' if n_sockets > 1 else ''
            sockets = f"{n_sockets} socket{s}"
        else:
            sockets = ""
        return f"<{_repr_cls}({sockets}) at {hex(id(self))}{closed}>"

    def __enter__(self: _ContextType) -> _ContextType:
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        # warn about any leftover sockets before closing them
        self._warn_destroy_close = True
        self.destroy()

    def __copy__(self: _ContextType, memo: Any = None) -> _ContextType:
        """Copying a Context creates a shadow copy"""
        return self.__class__.shadow(self.underlying)

    __deepcopy__ = __copy__

    @classmethod
    def shadow(cls: type[_ContextType], address: int | zmq.Context) -> _ContextType:
        """Shadow an existing libzmq context

        address is a zmq.Context or an integer (or FFI pointer)
        representing the address of the libzmq context.

        .. versionadded:: 14.1

        .. versionadded:: 25
            Support for shadowing `zmq.Context` objects,
            instead of just integer addresses.
        """
        return cls(shadow=address)

    @classmethod
    def shadow_pyczmq(cls: type[_ContextType], ctx: Any) -> _ContextType:
        """Shadow an existing pyczmq context

        ctx is the FFI `zctx_t *` pointer

        .. versionadded:: 14.1
        """
        from pyczmq import zctx  # type: ignore

        from zmq.utils.interop import cast_int_addr

        underlying = zctx.underlying(ctx)
        address = cast_int_addr(underlying)
        return cls(shadow=address)

    # static method copied from tornado IOLoop.instance
    @classmethod
    def instance(cls: type[_ContextType], io_threads: int = 1) -> _ContextType:
        """Returns a global Context instance.

        Most single-process applications have a single, global Context.
        Use this method instead of passing around Context instances
        throughout your code.

        A common pattern for classes that depend on Contexts is to use
        a default argument to enable programs with multiple Contexts
        but not require the argument for simpler applications::

            class MyClass(object):
                def __init__(self, context=None):
                    self.context = context or Context.instance()

        .. versionchanged:: 18.1

            When called in a subprocess after forking,
            a new global instance is created instead of inheriting
            a Context that won't work from the parent process.
        """
        if (
            cls._instance is None
            or cls._instance_pid != os.getpid()
            or cls._instance.closed
        ):
            with cls._instance_lock:
                if (
                    cls._instance is None
                    or cls._instance_pid != os.getpid()
                    or cls._instance.closed
                ):
                    cls._instance = cls(io_threads=io_threads)
                    cls._instance_pid = os.getpid()
        return cls._instance

    def term(self) -> None:
        """Close or terminate the context.

        Context termination is performed in the following steps:

        - Any blocking operations currently in progress on sockets open within context shall
          raise :class:`zmq.ContextTerminated`.
          With the exception of socket.close(), any further operations on sockets open within this context
          shall raise :class:`zmq.ContextTerminated`.
        - After interrupting all blocking calls, term shall block until the following conditions are satisfied:
            - All sockets open within context have been closed.
            - For each socket within context, all messages sent on the socket have either been
              physically transferred to a network peer,
              or the socket's linger period set with the zmq.LINGER socket option has expired.

        For further details regarding socket linger behaviour refer to libzmq documentation for ZMQ_LINGER.

        This can be called to close the context by hand. If this is not called,
        the context will automatically be closed when it is garbage collected,
        in which case you may see a ResourceWarning about the unclosed context.
        """
        super().term()

    # -------------------------------------------------------------------------
    # Hooks for ctxopt completion
    # -------------------------------------------------------------------------

    def __dir__(self) -> list[str]:
        keys = dir(self.__class__)
        keys.extend(ContextOption.__members__)
        return keys

    # -------------------------------------------------------------------------
    # Creating Sockets
    # -------------------------------------------------------------------------

    def _add_socket(self, socket: Any) -> None:
        """Add a weakref to a socket for Context.destroy / reference counting"""
        self._sockets.add(socket)

    def _rm_socket(self, socket: Any) -> None:
        """Remove a socket for Context.destroy / reference counting"""
        # allow _sockets to be None in case of process teardown
        if getattr(self, "_sockets", None) is not None:
            self._sockets.discard(socket)

    def destroy(self, linger: int | None = None) -> None:
        """Close all sockets associated with this context and then terminate
        the context.

        .. warning::

            destroy involves calling :meth:`Socket.close`, which is **NOT** threadsafe.
            If there are active sockets in other threads, this must not be called.

        Parameters
        ----------

        linger : int, optional
            If specified, set LINGER on sockets prior to closing them.
        """
        if self.closed:
            return

        sockets: list[_SocketType] = list(getattr(self, "_sockets", None) or [])
        for s in sockets:
            if s and not s.closed:
                if self._warn_destroy_close and warn is not None:
                    # warn can be None during process teardown
                    warn(
                        f"Destroying context with unclosed socket {s}",
                        ResourceWarning,
                        stacklevel=3,
                        source=s,
                    )
                if linger is not None:
                    s.setsockopt(SocketOption.LINGER, linger)
                s.close()

        self.term()

    def socket(
        self: _ContextType,
        socket_type: int,
        socket_class: Callable[[_ContextType, int], _SocketType] | None = None,
        **kwargs: Any,
    ) -> _SocketType:
        """Create a Socket associated with this Context.

        Parameters
        ----------
        socket_type : int
            The socket type, which can be any of the 0MQ socket types:
            REQ, REP, PUB, SUB, PAIR, DEALER, ROUTER, PULL, PUSH, etc.

        socket_class: zmq.Socket
            The socket class to instantiate, if different from the default for this Context.
            e.g. for creating an asyncio socket attached to a default Context or vice versa.

            .. versionadded:: 25

        kwargs:
            will be passed to the __init__ method of the socket class.
        """
        if self.closed:
            raise ZMQError(Errno.ENOTSUP)
        if socket_class is None:
            socket_class = self._socket_class
        s: _SocketType = (
            socket_class(  # set PYTHONTRACEMALLOC=2 to get the calling frame
                self, socket_type, **kwargs
            )
        )
        for opt, value in self.sockopts.items():
            try:
                s.setsockopt(opt, value)
            except ZMQError:
                # ignore ZMQErrors, which are likely for socket options
                # that do not apply to a particular socket type, e.g.
                # SUBSCRIBE for non-SUB sockets.
                pass
        self._add_socket(s)
        return s

    def setsockopt(self, opt: int, value: Any) -> None:
        """set default socket options for new sockets created by this Context

        .. versionadded:: 13.0
        """
        self.sockopts[opt] = value

    def getsockopt(self, opt: int) -> OptValT:
        """get default socket options for new sockets created by this Context

        .. versionadded:: 13.0
        """
        return self.sockopts[opt]

    def _set_attr_opt(self, name: str, opt: int, value: OptValT) -> None:
        """set default sockopts as attributes"""
        if name in ContextOption.__members__:
            return self.set(opt, value)
        elif name in SocketOption.__members__:
            self.sockopts[opt] = value
        else:
            raise AttributeError(f"No such context or socket option: {name}")

    def _get_attr_opt(self, name: str, opt: int) -> OptValT:
        """get default sockopts as attributes"""
        if name in ContextOption.__members__:
            return self.get(opt)
        else:
            if opt not in self.sockopts:
                raise AttributeError(name)
            else:
                return self.sockopts[opt]

    def __delattr__(self, key: str) -> None:
        """delete default sockopts as attributes"""
        if key in self.__dict__:
            self.__dict__.pop(key)
            return
        key = key.upper()
        try:
            opt = getattr(SocketOption, key)
        except AttributeError:
            raise AttributeError(f"No such socket option: {key!r}")
        else:
            if opt not in self.sockopts:
                raise AttributeError(key)
            else:
                del self.sockopts[opt]


SyncContext: TypeAlias = Context[SyncSocket]


__all__ = ['Context', 'SyncContext']

# === NexusCore/openenv\Lib\site-packages\dateutil\tz\_common.py ===
from six import PY2

from functools import wraps

from datetime import datetime, timedelta, tzinfo


ZERO = timedelta(0)

__all__ = ['tzname_in_python2', 'enfold']


def tzname_in_python2(namefunc):
    """Change unicode output into bytestrings in Python 2

    tzname() API changed in Python 3. It used to return bytes, but was changed
    to unicode strings
    """
    if PY2:
        @wraps(namefunc)
        def adjust_encoding(*args, **kwargs):
            name = namefunc(*args, **kwargs)
            if name is not None:
                name = name.encode()

            return name

        return adjust_encoding
    else:
        return namefunc


# The following is adapted from Alexander Belopolsky's tz library
# https://github.com/abalkin/tz
if hasattr(datetime, 'fold'):
    # This is the pre-python 3.6 fold situation
    def enfold(dt, fold=1):
        """
        Provides a unified interface for assigning the ``fold`` attribute to
        datetimes both before and after the implementation of PEP-495.

        :param fold:
            The value for the ``fold`` attribute in the returned datetime. This
            should be either 0 or 1.

        :return:
            Returns an object for which ``getattr(dt, 'fold', 0)`` returns
            ``fold`` for all versions of Python. In versions prior to
            Python 3.6, this is a ``_DatetimeWithFold`` object, which is a
            subclass of :py:class:`datetime.datetime` with the ``fold``
            attribute added, if ``fold`` is 1.

        .. versionadded:: 2.6.0
        """
        return dt.replace(fold=fold)

else:
    class _DatetimeWithFold(datetime):
        """
        This is a class designed to provide a PEP 495-compliant interface for
        Python versions before 3.6. It is used only for dates in a fold, so
        the ``fold`` attribute is fixed at ``1``.

        .. versionadded:: 2.6.0
        """
        __slots__ = ()

        def replace(self, *args, **kwargs):
            """
            Return a datetime with the same attributes, except for those
            attributes given new values by whichever keyword arguments are
            specified. Note that tzinfo=None can be specified to create a naive
            datetime from an aware datetime with no conversion of date and time
            data.

            This is reimplemented in ``_DatetimeWithFold`` because pypy3 will
            return a ``datetime.datetime`` even if ``fold`` is unchanged.
            """
            argnames = (
                'year', 'month', 'day', 'hour', 'minute', 'second',
                'microsecond', 'tzinfo'
            )

            for arg, argname in zip(args, argnames):
                if argname in kwargs:
                    raise TypeError('Duplicate argument: {}'.format(argname))

                kwargs[argname] = arg

            for argname in argnames:
                if argname not in kwargs:
                    kwargs[argname] = getattr(self, argname)

            dt_class = self.__class__ if kwargs.get('fold', 1) else datetime

            return dt_class(**kwargs)

        @property
        def fold(self):
            return 1

    def enfold(dt, fold=1):
        """
        Provides a unified interface for assigning the ``fold`` attribute to
        datetimes both before and after the implementation of PEP-495.

        :param fold:
            The value for the ``fold`` attribute in the returned datetime. This
            should be either 0 or 1.

        :return:
            Returns an object for which ``getattr(dt, 'fold', 0)`` returns
            ``fold`` for all versions of Python. In versions prior to
            Python 3.6, this is a ``_DatetimeWithFold`` object, which is a
            subclass of :py:class:`datetime.datetime` with the ``fold``
            attribute added, if ``fold`` is 1.

        .. versionadded:: 2.6.0
        """
        if getattr(dt, 'fold', 0) == fold:
            return dt

        args = dt.timetuple()[:6]
        args += (dt.microsecond, dt.tzinfo)

        if fold:
            return _DatetimeWithFold(*args)
        else:
            return datetime(*args)


def _validate_fromutc_inputs(f):
    """
    The CPython version of ``fromutc`` checks that the input is a ``datetime``
    object and that ``self`` is attached as its ``tzinfo``.
    """
    @wraps(f)
    def fromutc(self, dt):
        if not isinstance(dt, datetime):
            raise TypeError("fromutc() requires a datetime argument")
        if dt.tzinfo is not self:
            raise ValueError("dt.tzinfo is not self")

        return f(self, dt)

    return fromutc


class _tzinfo(tzinfo):
    """
    Base class for all ``dateutil`` ``tzinfo`` objects.
    """

    def is_ambiguous(self, dt):
        """
        Whether or not the "wall time" of a given datetime is ambiguous in this
        zone.

        :param dt:
            A :py:class:`datetime.datetime`, naive or time zone aware.


        :return:
            Returns ``True`` if ambiguous, ``False`` otherwise.

        .. versionadded:: 2.6.0
        """

        dt = dt.replace(tzinfo=self)

        wall_0 = enfold(dt, fold=0)
        wall_1 = enfold(dt, fold=1)

        same_offset = wall_0.utcoffset() == wall_1.utcoffset()
        same_dt = wall_0.replace(tzinfo=None) == wall_1.replace(tzinfo=None)

        return same_dt and not same_offset

    def _fold_status(self, dt_utc, dt_wall):
        """
        Determine the fold status of a "wall" datetime, given a representation
        of the same datetime as a (naive) UTC datetime. This is calculated based
        on the assumption that ``dt.utcoffset() - dt.dst()`` is constant for all
        datetimes, and that this offset is the actual number of hours separating
        ``dt_utc`` and ``dt_wall``.

        :param dt_utc:
            Representation of the datetime as UTC

        :param dt_wall:
            Representation of the datetime as "wall time". This parameter must
            either have a `fold` attribute or have a fold-naive
            :class:`datetime.tzinfo` attached, otherwise the calculation may
            fail.
        """
        if self.is_ambiguous(dt_wall):
            delta_wall = dt_wall - dt_utc
            _fold = int(delta_wall == (dt_utc.utcoffset() - dt_utc.dst()))
        else:
            _fold = 0

        return _fold

    def _fold(self, dt):
        return getattr(dt, 'fold', 0)

    def _fromutc(self, dt):
        """
        Given a timezone-aware datetime in a given timezone, calculates a
        timezone-aware datetime in a new timezone.

        Since this is the one time that we *know* we have an unambiguous
        datetime object, we take this opportunity to determine whether the
        datetime is ambiguous and in a "fold" state (e.g. if it's the first
        occurrence, chronologically, of the ambiguous datetime).

        :param dt:
            A timezone-aware :class:`datetime.datetime` object.
        """

        # Re-implement the algorithm from Python's datetime.py
        dtoff = dt.utcoffset()
        if dtoff is None:
            raise ValueError("fromutc() requires a non-None utcoffset() "
                             "result")

        # The original datetime.py code assumes that `dst()` defaults to
        # zero during ambiguous times. PEP 495 inverts this presumption, so
        # for pre-PEP 495 versions of python, we need to tweak the algorithm.
        dtdst = dt.dst()
        if dtdst is None:
            raise ValueError("fromutc() requires a non-None dst() result")
        delta = dtoff - dtdst

        dt += delta
        # Set fold=1 so we can default to being in the fold for
        # ambiguous dates.
        dtdst = enfold(dt, fold=1).dst()
        if dtdst is None:
            raise ValueError("fromutc(): dt.dst gave inconsistent "
                             "results; cannot convert")
        return dt + dtdst

    @_validate_fromutc_inputs
    def fromutc(self, dt):
        """
        Given a timezone-aware datetime in a given timezone, calculates a
        timezone-aware datetime in a new timezone.

        Since this is the one time that we *know* we have an unambiguous
        datetime object, we take this opportunity to determine whether the
        datetime is ambiguous and in a "fold" state (e.g. if it's the first
        occurrence, chronologically, of the ambiguous datetime).

        :param dt:
            A timezone-aware :class:`datetime.datetime` object.
        """
        dt_wall = self._fromutc(dt)

        # Calculate the fold status given the two datetimes.
        _fold = self._fold_status(dt, dt_wall)

        # Set the default fold value for ambiguous dates
        return enfold(dt_wall, fold=_fold)


class tzrangebase(_tzinfo):
    """
    This is an abstract base class for time zones represented by an annual
    transition into and out of DST. Child classes should implement the following
    methods:

        * ``__init__(self, *args, **kwargs)``
        * ``transitions(self, year)`` - this is expected to return a tuple of
          datetimes representing the DST on and off transitions in standard
          time.

    A fully initialized ``tzrangebase`` subclass should also provide the
    following attributes:
        * ``hasdst``: Boolean whether or not the zone uses DST.
        * ``_dst_offset`` / ``_std_offset``: :class:`datetime.timedelta` objects
          representing the respective UTC offsets.
        * ``_dst_abbr`` / ``_std_abbr``: Strings representing the timezone short
          abbreviations in DST and STD, respectively.
        * ``_hasdst``: Whether or not the zone has DST.

    .. versionadded:: 2.6.0
    """
    def __init__(self):
        raise NotImplementedError('tzrangebase is an abstract base class')

    def utcoffset(self, dt):
        isdst = self._isdst(dt)

        if isdst is None:
            return None
        elif isdst:
            return self._dst_offset
        else:
            return self._std_offset

    def dst(self, dt):
        isdst = self._isdst(dt)

        if isdst is None:
            return None
        elif isdst:
            return self._dst_base_offset
        else:
            return ZERO

    @tzname_in_python2
    def tzname(self, dt):
        if self._isdst(dt):
            return self._dst_abbr
        else:
            return self._std_abbr

    def fromutc(self, dt):
        """ Given a datetime in UTC, return local time """
        if not isinstance(dt, datetime):
            raise TypeError("fromutc() requires a datetime argument")

        if dt.tzinfo is not self:
            raise ValueError("dt.tzinfo is not self")

        # Get transitions - if there are none, fixed offset
        transitions = self.transitions(dt.year)
        if transitions is None:
            return dt + self.utcoffset(dt)

        # Get the transition times in UTC
        dston, dstoff = transitions

        dston -= self._std_offset
        dstoff -= self._std_offset

        utc_transitions = (dston, dstoff)
        dt_utc = dt.replace(tzinfo=None)

        isdst = self._naive_isdst(dt_utc, utc_transitions)

        if isdst:
            dt_wall = dt + self._dst_offset
        else:
            dt_wall = dt + self._std_offset

        _fold = int(not isdst and self.is_ambiguous(dt_wall))

        return enfold(dt_wall, fold=_fold)

    def is_ambiguous(self, dt):
        """
        Whether or not the "wall time" of a given datetime is ambiguous in this
        zone.

        :param dt:
            A :py:class:`datetime.datetime`, naive or time zone aware.


        :return:
            Returns ``True`` if ambiguous, ``False`` otherwise.

        .. versionadded:: 2.6.0
        """
        if not self.hasdst:
            return False

        start, end = self.transitions(dt.year)

        dt = dt.replace(tzinfo=None)
        return (end <= dt < end + self._dst_base_offset)

    def _isdst(self, dt):
        if not self.hasdst:
            return False
        elif dt is None:
            return None

        transitions = self.transitions(dt.year)

        if transitions is None:
            return False

        dt = dt.replace(tzinfo=None)

        isdst = self._naive_isdst(dt, transitions)

        # Handle ambiguous dates
        if not isdst and self.is_ambiguous(dt):
            return not self._fold(dt)
        else:
            return isdst

    def _naive_isdst(self, dt, transitions):
        dston, dstoff = transitions

        dt = dt.replace(tzinfo=None)

        if dston < dstoff:
            isdst = dston <= dt < dstoff
        else:
            isdst = not dstoff <= dt < dston

        return isdst

    @property
    def _dst_base_offset(self):
        return self._dst_offset - self._std_offset

    __hash__ = None

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        return "%s(...)" % self.__class__.__name__

    __reduce__ = object.__reduce__

# === NexusCore/openenv\Lib\site-packages\git\repo\fun.py ===
# This module is part of GitPython and is released under the
# 3-Clause BSD License: https://opensource.org/license/bsd-3-clause/

"""General repository-related functions."""

from __future__ import annotations

__all__ = [
    "rev_parse",
    "is_git_dir",
    "touch",
    "find_submodule_git_dir",
    "name_to_object",
    "short_to_long",
    "deref_tag",
    "to_commit",
    "find_worktree_git_dir",
]

import os
import os.path as osp
from pathlib import Path
import stat
from string import digits

from gitdb.exc import BadName, BadObject

from git.cmd import Git
from git.exc import WorkTreeRepositoryUnsupported
from git.objects import Object
from git.refs import SymbolicReference
from git.util import cygpath, bin_to_hex, hex_to_bin

# Typing ----------------------------------------------------------------------

from typing import Optional, TYPE_CHECKING, Union, cast, overload

from git.types import AnyGitObject, Literal, PathLike

if TYPE_CHECKING:
    from git.db import GitCmdObjectDB
    from git.objects import Commit, TagObject
    from git.refs.reference import Reference
    from git.refs.tag import Tag

    from .base import Repo

# ----------------------------------------------------------------------------


def touch(filename: str) -> str:
    with open(filename, "ab"):
        pass
    return filename


def is_git_dir(d: PathLike) -> bool:
    """This is taken from the git setup.c:is_git_directory function.

    :raise git.exc.WorkTreeRepositoryUnsupported:
        If it sees a worktree directory. It's quite hacky to do that here, but at least
        clearly indicates that we don't support it. There is the unlikely danger to
        throw if we see directories which just look like a worktree dir, but are none.
    """
    if osp.isdir(d):
        if (osp.isdir(osp.join(d, "objects")) or "GIT_OBJECT_DIRECTORY" in os.environ) and osp.isdir(
            osp.join(d, "refs")
        ):
            headref = osp.join(d, "HEAD")
            return osp.isfile(headref) or (osp.islink(headref) and os.readlink(headref).startswith("refs"))
        elif (
            osp.isfile(osp.join(d, "gitdir"))
            and osp.isfile(osp.join(d, "commondir"))
            and osp.isfile(osp.join(d, "gitfile"))
        ):
            raise WorkTreeRepositoryUnsupported(d)
    return False


def find_worktree_git_dir(dotgit: PathLike) -> Optional[str]:
    """Search for a gitdir for this worktree."""
    try:
        statbuf = os.stat(dotgit)
    except OSError:
        return None
    if not stat.S_ISREG(statbuf.st_mode):
        return None

    try:
        lines = Path(dotgit).read_text().splitlines()
        for key, value in [line.strip().split(": ") for line in lines]:
            if key == "gitdir":
                return value
    except ValueError:
        pass
    return None


def find_submodule_git_dir(d: PathLike) -> Optional[PathLike]:
    """Search for a submodule repo."""
    if is_git_dir(d):
        return d

    try:
        with open(d) as fp:
            content = fp.read().rstrip()
    except IOError:
        # It's probably not a file.
        pass
    else:
        if content.startswith("gitdir: "):
            path = content[8:]

            if Git.is_cygwin():
                # Cygwin creates submodules prefixed with `/cygdrive/...`.
                # Cygwin git understands Cygwin paths much better than Windows ones.
                # Also the Cygwin tests are assuming Cygwin paths.
                path = cygpath(path)
            if not osp.isabs(path):
                path = osp.normpath(osp.join(osp.dirname(d), path))
            return find_submodule_git_dir(path)
    # END handle exception
    return None


def short_to_long(odb: "GitCmdObjectDB", hexsha: str) -> Optional[bytes]:
    """
    :return:
        Long hexadecimal sha1 from the given less than 40 byte hexsha, or ``None`` if no
        candidate could be found.

    :param hexsha:
        hexsha with less than 40 bytes.
    """
    try:
        return bin_to_hex(odb.partial_to_complete_sha_hex(hexsha))
    except BadObject:
        return None
    # END exception handling


@overload
def name_to_object(repo: "Repo", name: str, return_ref: Literal[False] = ...) -> AnyGitObject: ...


@overload
def name_to_object(repo: "Repo", name: str, return_ref: Literal[True]) -> Union[AnyGitObject, SymbolicReference]: ...


def name_to_object(repo: "Repo", name: str, return_ref: bool = False) -> Union[AnyGitObject, SymbolicReference]:
    """
    :return:
        Object specified by the given name - hexshas (short and long) as well as
        references are supported.

    :param return_ref:
        If ``True``, and name specifies a reference, we will return the reference
        instead of the object. Otherwise it will raise :exc:`~gitdb.exc.BadObject` or
        :exc:`~gitdb.exc.BadName`.
    """
    hexsha: Union[None, str, bytes] = None

    # Is it a hexsha? Try the most common ones, which is 7 to 40.
    if repo.re_hexsha_shortened.match(name):
        if len(name) != 40:
            # Find long sha for short sha.
            hexsha = short_to_long(repo.odb, name)
        else:
            hexsha = name
        # END handle short shas
    # END find sha if it matches

    # If we couldn't find an object for what seemed to be a short hexsha, try to find it
    # as reference anyway, it could be named 'aaa' for instance.
    if hexsha is None:
        for base in (
            "%s",
            "refs/%s",
            "refs/tags/%s",
            "refs/heads/%s",
            "refs/remotes/%s",
            "refs/remotes/%s/HEAD",
        ):
            try:
                hexsha = SymbolicReference.dereference_recursive(repo, base % name)
                if return_ref:
                    return SymbolicReference(repo, base % name)
                # END handle symbolic ref
                break
            except ValueError:
                pass
        # END for each base
    # END handle hexsha

    # Didn't find any ref, this is an error.
    if return_ref:
        raise BadObject("Couldn't find reference named %r" % name)
    # END handle return ref

    # Tried everything ? fail.
    if hexsha is None:
        raise BadName(name)
    # END assert hexsha was found

    return Object.new_from_sha(repo, hex_to_bin(hexsha))


def deref_tag(tag: "Tag") -> AnyGitObject:
    """Recursively dereference a tag and return the resulting object."""
    while True:
        try:
            tag = tag.object
        except AttributeError:
            break
    # END dereference tag
    return tag


def to_commit(obj: Object) -> "Commit":
    """Convert the given object to a commit if possible and return it."""
    if obj.type == "tag":
        obj = deref_tag(obj)

    if obj.type != "commit":
        raise ValueError("Cannot convert object %r to type commit" % obj)
    # END verify type
    return obj


def rev_parse(repo: "Repo", rev: str) -> AnyGitObject:
    """Parse a revision string. Like :manpage:`git-rev-parse(1)`.

    :return:
        `~git.objects.base.Object` at the given revision.

        This may be any type of git object:

        * :class:`Commit <git.objects.commit.Commit>`
        * :class:`TagObject <git.objects.tag.TagObject>`
        * :class:`Tree <git.objects.tree.Tree>`
        * :class:`Blob <git.objects.blob.Blob>`

    :param rev:
        :manpage:`git-rev-parse(1)`-compatible revision specification as string.
        Please see :manpage:`git-rev-parse(1)` for details.

    :raise gitdb.exc.BadObject:
        If the given revision could not be found.

    :raise ValueError:
        If `rev` couldn't be parsed.

    :raise IndexError:
        If an invalid reflog index is specified.
    """
    # Are we in colon search mode?
    if rev.startswith(":/"):
        # Colon search mode
        raise NotImplementedError("commit by message search (regex)")
    # END handle search

    obj: Optional[AnyGitObject] = None
    ref = None
    output_type = "commit"
    start = 0
    parsed_to = 0
    lr = len(rev)
    while start < lr:
        if rev[start] not in "^~:@":
            start += 1
            continue
        # END handle start

        token = rev[start]

        if obj is None:
            # token is a rev name.
            if start == 0:
                ref = repo.head.ref
            else:
                if token == "@":
                    ref = cast("Reference", name_to_object(repo, rev[:start], return_ref=True))
                else:
                    obj = name_to_object(repo, rev[:start])
                # END handle token
            # END handle refname
        else:
            if ref is not None:
                obj = cast("Commit", ref.commit)
            # END handle ref
        # END initialize obj on first token

        start += 1

        # Try to parse {type}.
        if start < lr and rev[start] == "{":
            end = rev.find("}", start)
            if end == -1:
                raise ValueError("Missing closing brace to define type in %s" % rev)
            output_type = rev[start + 1 : end]  # Exclude brace.

            # Handle type.
            if output_type == "commit":
                pass  # Default.
            elif output_type == "tree":
                try:
                    obj = cast(AnyGitObject, obj)
                    obj = to_commit(obj).tree
                except (AttributeError, ValueError):
                    pass  # Error raised later.
                # END exception handling
            elif output_type in ("", "blob"):
                obj = cast("TagObject", obj)
                if obj and obj.type == "tag":
                    obj = deref_tag(obj)
                else:
                    # Cannot do anything for non-tags.
                    pass
                # END handle tag
            elif token == "@":
                # try single int
                assert ref is not None, "Require Reference to access reflog"
                revlog_index = None
                try:
                    # Transform reversed index into the format of our revlog.
                    revlog_index = -(int(output_type) + 1)
                except ValueError as e:
                    # TODO: Try to parse the other date options, using parse_date maybe.
                    raise NotImplementedError("Support for additional @{...} modes not implemented") from e
                # END handle revlog index

                try:
                    entry = ref.log_entry(revlog_index)
                except IndexError as e:
                    raise IndexError("Invalid revlog index: %i" % revlog_index) from e
                # END handle index out of bound

                obj = Object.new_from_sha(repo, hex_to_bin(entry.newhexsha))

                # Make it pass the following checks.
                output_type = ""
            else:
                raise ValueError("Invalid output type: %s ( in %s )" % (output_type, rev))
            # END handle output type

            # Empty output types don't require any specific type, its just about
            # dereferencing tags.
            if output_type and obj and obj.type != output_type:
                raise ValueError("Could not accommodate requested object type %r, got %s" % (output_type, obj.type))
            # END verify output type

            start = end + 1  # Skip brace.
            parsed_to = start
            continue
        # END parse type

        # Try to parse a number.
        num = 0
        if token != ":":
            found_digit = False
            while start < lr:
                if rev[start] in digits:
                    num = num * 10 + int(rev[start])
                    start += 1
                    found_digit = True
                else:
                    break
                # END handle number
            # END number parse loop

            # No explicit number given, 1 is the default. It could be 0 though.
            if not found_digit:
                num = 1
            # END set default num
        # END number parsing only if non-blob mode

        parsed_to = start
        # Handle hierarchy walk.
        try:
            obj = cast(AnyGitObject, obj)
            if token == "~":
                obj = to_commit(obj)
                for _ in range(num):
                    obj = obj.parents[0]
                # END for each history item to walk
            elif token == "^":
                obj = to_commit(obj)
                # Must be n'th parent.
                if num:
                    obj = obj.parents[num - 1]
            elif token == ":":
                if obj.type != "tree":
                    obj = obj.tree
                # END get tree type
                obj = obj[rev[start:]]
                parsed_to = lr
            else:
                raise ValueError("Invalid token: %r" % token)
            # END end handle tag
        except (IndexError, AttributeError) as e:
            raise BadName(
                f"Invalid revision spec '{rev}' - not enough " f"parent commits to reach '{token}{int(num)}'"
            ) from e
        # END exception handling
    # END parse loop

    # Still no obj? It's probably a simple name.
    if obj is None:
        obj = name_to_object(repo, rev)
        parsed_to = lr
    # END handle simple name

    if obj is None:
        raise ValueError("Revision specifier could not be parsed: %s" % rev)

    if parsed_to != lr:
        raise ValueError("Didn't consume complete rev spec %s, consumed part: %s" % (rev, rev[:parsed_to]))

    return obj

# === NexusCore/openenv\Lib\site-packages\litellm\types\integrations\prometheus.py ===
from enum import Enum
from typing import Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field
from typing_extensions import Annotated

import litellm

REQUESTED_MODEL = "requested_model"
EXCEPTION_STATUS = "exception_status"
EXCEPTION_CLASS = "exception_class"
STATUS_CODE = "status_code"
EXCEPTION_LABELS = [EXCEPTION_STATUS, EXCEPTION_CLASS]
LATENCY_BUCKETS = (
    0.005,
    0.00625,
    0.0125,
    0.025,
    0.05,
    0.1,
    0.5,
    1.0,
    1.5,
    2.0,
    2.5,
    3.0,
    3.5,
    4.0,
    4.5,
    5.0,
    5.5,
    6.0,
    6.5,
    7.0,
    7.5,
    8.0,
    8.5,
    9.0,
    9.5,
    10.0,
    15.0,
    20.0,
    25.0,
    30.0,
    60.0,
    120.0,
    180.0,
    240.0,
    300.0,
    float("inf"),
)


class UserAPIKeyLabelNames(Enum):
    END_USER = "end_user"
    USER = "user"
    USER_EMAIL = "user_email"
    API_KEY_HASH = "hashed_api_key"
    API_KEY_ALIAS = "api_key_alias"
    TEAM = "team"
    TEAM_ALIAS = "team_alias"
    REQUESTED_MODEL = REQUESTED_MODEL
    v1_LITELLM_MODEL_NAME = "model"
    v2_LITELLM_MODEL_NAME = "litellm_model_name"
    TAG = "tag"
    MODEL_ID = "model_id"
    API_BASE = "api_base"
    API_PROVIDER = "api_provider"
    EXCEPTION_STATUS = EXCEPTION_STATUS
    EXCEPTION_CLASS = EXCEPTION_CLASS
    STATUS_CODE = "status_code"
    FALLBACK_MODEL = "fallback_model"
    ROUTE = "route"
    MODEL_GROUP = "model_group"


DEFINED_PROMETHEUS_METRICS = Literal[
    "litellm_llm_api_latency_metric",
    "litellm_request_total_latency_metric",
    "litellm_overhead_latency_metric",
    "litellm_remaining_requests_metric",
    "litellm_remaining_tokens_metric",
    "litellm_proxy_total_requests_metric",
    "litellm_proxy_failed_requests_metric",
    "litellm_deployment_latency_per_output_token",
    "litellm_requests_metric",
    "litellm_total_tokens_metric",
    "litellm_input_tokens_metric",
    "litellm_output_tokens_metric",
    "litellm_deployment_successful_fallbacks",
    "litellm_deployment_failed_fallbacks",
    "litellm_remaining_team_budget_metric",
    "litellm_team_max_budget_metric",
    "litellm_team_budget_remaining_hours_metric",
    "litellm_remaining_api_key_budget_metric",
    "litellm_api_key_max_budget_metric",
    "litellm_api_key_budget_remaining_hours_metric",
    "litellm_deployment_failure_responses",
    "litellm_deployment_total_requests",
    "litellm_deployment_success_responses",
]


class PrometheusMetricLabels:
    litellm_llm_api_latency_metric = [
        UserAPIKeyLabelNames.v1_LITELLM_MODEL_NAME.value,
        UserAPIKeyLabelNames.API_KEY_HASH.value,
        UserAPIKeyLabelNames.API_KEY_ALIAS.value,
        UserAPIKeyLabelNames.TEAM.value,
        UserAPIKeyLabelNames.TEAM_ALIAS.value,
        UserAPIKeyLabelNames.REQUESTED_MODEL.value,
        UserAPIKeyLabelNames.END_USER.value,
        UserAPIKeyLabelNames.USER.value,
    ]

    litellm_request_total_latency_metric = [
        UserAPIKeyLabelNames.END_USER.value,
        UserAPIKeyLabelNames.API_KEY_HASH.value,
        UserAPIKeyLabelNames.API_KEY_ALIAS.value,
        UserAPIKeyLabelNames.REQUESTED_MODEL.value,
        UserAPIKeyLabelNames.TEAM.value,
        UserAPIKeyLabelNames.TEAM_ALIAS.value,
        UserAPIKeyLabelNames.USER.value,
        UserAPIKeyLabelNames.v1_LITELLM_MODEL_NAME.value,
    ]

    litellm_proxy_total_requests_metric = [
        UserAPIKeyLabelNames.END_USER.value,
        UserAPIKeyLabelNames.API_KEY_HASH.value,
        UserAPIKeyLabelNames.API_KEY_ALIAS.value,
        UserAPIKeyLabelNames.REQUESTED_MODEL.value,
        UserAPIKeyLabelNames.TEAM.value,
        UserAPIKeyLabelNames.TEAM_ALIAS.value,
        UserAPIKeyLabelNames.USER.value,
        UserAPIKeyLabelNames.STATUS_CODE.value,
        UserAPIKeyLabelNames.USER_EMAIL.value,
        UserAPIKeyLabelNames.ROUTE.value,
    ]

    litellm_proxy_failed_requests_metric = [
        UserAPIKeyLabelNames.END_USER.value,
        UserAPIKeyLabelNames.API_KEY_HASH.value,
        UserAPIKeyLabelNames.API_KEY_ALIAS.value,
        UserAPIKeyLabelNames.REQUESTED_MODEL.value,
        UserAPIKeyLabelNames.TEAM.value,
        UserAPIKeyLabelNames.TEAM_ALIAS.value,
        UserAPIKeyLabelNames.USER.value,
        UserAPIKeyLabelNames.EXCEPTION_STATUS.value,
        UserAPIKeyLabelNames.EXCEPTION_CLASS.value,
        UserAPIKeyLabelNames.ROUTE.value,
    ]

    litellm_deployment_latency_per_output_token = [
        UserAPIKeyLabelNames.v2_LITELLM_MODEL_NAME.value,
        UserAPIKeyLabelNames.MODEL_ID.value,
        UserAPIKeyLabelNames.API_BASE.value,
        UserAPIKeyLabelNames.API_PROVIDER.value,
        UserAPIKeyLabelNames.API_KEY_HASH.value,
        UserAPIKeyLabelNames.API_KEY_ALIAS.value,
        UserAPIKeyLabelNames.TEAM.value,
        UserAPIKeyLabelNames.TEAM_ALIAS.value,
    ]

    litellm_overhead_latency_metric = [
        UserAPIKeyLabelNames.MODEL_GROUP.value,
        UserAPIKeyLabelNames.API_PROVIDER.value,
        UserAPIKeyLabelNames.API_BASE.value,
        UserAPIKeyLabelNames.v2_LITELLM_MODEL_NAME.value,
        UserAPIKeyLabelNames.API_KEY_HASH.value,
        UserAPIKeyLabelNames.API_KEY_ALIAS.value,
    ]

    litellm_remaining_requests_metric = [
        UserAPIKeyLabelNames.MODEL_GROUP.value,
        UserAPIKeyLabelNames.API_PROVIDER.value,
        UserAPIKeyLabelNames.API_BASE.value,
        UserAPIKeyLabelNames.v2_LITELLM_MODEL_NAME.value,
        UserAPIKeyLabelNames.API_KEY_HASH.value,
        UserAPIKeyLabelNames.API_KEY_ALIAS.value,
    ]

    litellm_remaining_tokens_metric = [
        UserAPIKeyLabelNames.MODEL_GROUP.value,
        UserAPIKeyLabelNames.API_PROVIDER.value,
        UserAPIKeyLabelNames.API_BASE.value,
        UserAPIKeyLabelNames.v2_LITELLM_MODEL_NAME.value,
        UserAPIKeyLabelNames.API_KEY_HASH.value,
        UserAPIKeyLabelNames.API_KEY_ALIAS.value,
    ]

    litellm_requests_metric = [
        UserAPIKeyLabelNames.END_USER.value,
        UserAPIKeyLabelNames.API_KEY_HASH.value,
        UserAPIKeyLabelNames.API_KEY_ALIAS.value,
        UserAPIKeyLabelNames.v1_LITELLM_MODEL_NAME.value,
        UserAPIKeyLabelNames.TEAM.value,
        UserAPIKeyLabelNames.TEAM_ALIAS.value,
        UserAPIKeyLabelNames.USER.value,
        UserAPIKeyLabelNames.USER_EMAIL.value,
    ]

    litellm_input_tokens_metric = [
        UserAPIKeyLabelNames.END_USER.value,
        UserAPIKeyLabelNames.API_KEY_HASH.value,
        UserAPIKeyLabelNames.API_KEY_ALIAS.value,
        UserAPIKeyLabelNames.v1_LITELLM_MODEL_NAME.value,
        UserAPIKeyLabelNames.TEAM.value,
        UserAPIKeyLabelNames.TEAM_ALIAS.value,
        UserAPIKeyLabelNames.USER.value,
        UserAPIKeyLabelNames.REQUESTED_MODEL.value,
    ]

    litellm_total_tokens_metric = [
        UserAPIKeyLabelNames.END_USER.value,
        UserAPIKeyLabelNames.API_KEY_HASH.value,
        UserAPIKeyLabelNames.API_KEY_ALIAS.value,
        UserAPIKeyLabelNames.v1_LITELLM_MODEL_NAME.value,
        UserAPIKeyLabelNames.TEAM.value,
        UserAPIKeyLabelNames.TEAM_ALIAS.value,
        UserAPIKeyLabelNames.USER.value,
        UserAPIKeyLabelNames.REQUESTED_MODEL.value,
    ]

    litellm_output_tokens_metric = [
        UserAPIKeyLabelNames.END_USER.value,
        UserAPIKeyLabelNames.API_KEY_HASH.value,
        UserAPIKeyLabelNames.API_KEY_ALIAS.value,
        UserAPIKeyLabelNames.v1_LITELLM_MODEL_NAME.value,
        UserAPIKeyLabelNames.TEAM.value,
        UserAPIKeyLabelNames.TEAM_ALIAS.value,
        UserAPIKeyLabelNames.USER.value,
        UserAPIKeyLabelNames.REQUESTED_MODEL.value,
    ]

    litellm_deployment_successful_fallbacks = [
        UserAPIKeyLabelNames.REQUESTED_MODEL.value,
        UserAPIKeyLabelNames.FALLBACK_MODEL.value,
        UserAPIKeyLabelNames.API_KEY_HASH.value,
        UserAPIKeyLabelNames.API_KEY_ALIAS.value,
        UserAPIKeyLabelNames.TEAM.value,
        UserAPIKeyLabelNames.TEAM_ALIAS.value,
        UserAPIKeyLabelNames.EXCEPTION_STATUS.value,
        UserAPIKeyLabelNames.EXCEPTION_CLASS.value,
    ]

    litellm_deployment_failed_fallbacks = litellm_deployment_successful_fallbacks

    litellm_remaining_team_budget_metric = [
        UserAPIKeyLabelNames.TEAM.value,
        UserAPIKeyLabelNames.TEAM_ALIAS.value,
    ]

    litellm_team_max_budget_metric = [
        UserAPIKeyLabelNames.TEAM.value,
        UserAPIKeyLabelNames.TEAM_ALIAS.value,
    ]

    litellm_team_budget_remaining_hours_metric = [
        UserAPIKeyLabelNames.TEAM.value,
        UserAPIKeyLabelNames.TEAM_ALIAS.value,
    ]

    litellm_remaining_api_key_budget_metric = [
        UserAPIKeyLabelNames.API_KEY_HASH.value,
        UserAPIKeyLabelNames.API_KEY_ALIAS.value,
    ]

    litellm_api_key_max_budget_metric = litellm_remaining_api_key_budget_metric

    litellm_api_key_budget_remaining_hours_metric = (
        litellm_remaining_api_key_budget_metric
    )

    # Add deployment metrics
    litellm_deployment_failure_responses = [
        UserAPIKeyLabelNames.REQUESTED_MODEL.value,
        UserAPIKeyLabelNames.v2_LITELLM_MODEL_NAME.value,
        UserAPIKeyLabelNames.MODEL_ID.value,
        UserAPIKeyLabelNames.API_BASE.value,
        UserAPIKeyLabelNames.API_PROVIDER.value,
        UserAPIKeyLabelNames.EXCEPTION_STATUS.value,
        UserAPIKeyLabelNames.EXCEPTION_CLASS.value,
        UserAPIKeyLabelNames.API_KEY_HASH.value,
        UserAPIKeyLabelNames.API_KEY_ALIAS.value,
        UserAPIKeyLabelNames.TEAM.value,
        UserAPIKeyLabelNames.TEAM_ALIAS.value,
    ]

    litellm_deployment_total_requests = [
        UserAPIKeyLabelNames.REQUESTED_MODEL.value,
        UserAPIKeyLabelNames.v2_LITELLM_MODEL_NAME.value,
        UserAPIKeyLabelNames.MODEL_ID.value,
        UserAPIKeyLabelNames.API_BASE.value,
        UserAPIKeyLabelNames.API_PROVIDER.value,
        UserAPIKeyLabelNames.API_KEY_HASH.value,
        UserAPIKeyLabelNames.API_KEY_ALIAS.value,
        UserAPIKeyLabelNames.TEAM.value,
        UserAPIKeyLabelNames.TEAM_ALIAS.value,
    ]

    litellm_deployment_success_responses = litellm_deployment_total_requests

    @staticmethod
    def get_labels(label_name: DEFINED_PROMETHEUS_METRICS) -> List[str]:
        default_labels = getattr(PrometheusMetricLabels, label_name)
        return default_labels + [
            metric.replace(".", "_")
            for metric in litellm.custom_prometheus_metadata_labels
        ]


from typing import List, Optional

from pydantic import BaseModel, Field


class UserAPIKeyLabelValues(BaseModel):
    end_user: Annotated[
        Optional[str], Field(..., alias=UserAPIKeyLabelNames.END_USER.value)
    ] = None
    user: Annotated[
        Optional[str], Field(..., alias=UserAPIKeyLabelNames.USER.value)
    ] = None
    user_email: Annotated[
        Optional[str], Field(..., alias=UserAPIKeyLabelNames.USER_EMAIL.value)
    ] = None
    hashed_api_key: Annotated[
        Optional[str], Field(..., alias=UserAPIKeyLabelNames.API_KEY_HASH.value)
    ] = None
    api_key_alias: Annotated[
        Optional[str], Field(..., alias=UserAPIKeyLabelNames.API_KEY_ALIAS.value)
    ] = None
    team: Annotated[
        Optional[str], Field(..., alias=UserAPIKeyLabelNames.TEAM.value)
    ] = None
    team_alias: Annotated[
        Optional[str], Field(..., alias=UserAPIKeyLabelNames.TEAM_ALIAS.value)
    ] = None
    model_group: Annotated[
        Optional[str], Field(..., alias=UserAPIKeyLabelNames.MODEL_GROUP.value)
    ] = None
    requested_model: Annotated[
        Optional[str], Field(..., alias=UserAPIKeyLabelNames.REQUESTED_MODEL.value)
    ] = None
    model: Annotated[
        Optional[str],
        Field(..., alias=UserAPIKeyLabelNames.v1_LITELLM_MODEL_NAME.value),
    ] = None
    litellm_model_name: Annotated[
        Optional[str],
        Field(..., alias=UserAPIKeyLabelNames.v2_LITELLM_MODEL_NAME.value),
    ] = None
    tags: List[str] = []
    custom_metadata_labels: Dict[str, str] = {}
    model_id: Annotated[
        Optional[str], Field(..., alias=UserAPIKeyLabelNames.MODEL_ID.value)
    ] = None
    api_base: Annotated[
        Optional[str], Field(..., alias=UserAPIKeyLabelNames.API_BASE.value)
    ] = None
    api_provider: Annotated[
        Optional[str], Field(..., alias=UserAPIKeyLabelNames.API_PROVIDER.value)
    ] = None
    exception_status: Annotated[
        Optional[str], Field(..., alias=UserAPIKeyLabelNames.EXCEPTION_STATUS.value)
    ] = None
    exception_class: Annotated[
        Optional[str], Field(..., alias=UserAPIKeyLabelNames.EXCEPTION_CLASS.value)
    ] = None
    status_code: Annotated[
        Optional[str], Field(..., alias=UserAPIKeyLabelNames.STATUS_CODE.value)
    ] = None
    fallback_model: Annotated[
        Optional[str], Field(..., alias=UserAPIKeyLabelNames.FALLBACK_MODEL.value)
    ] = None
    route: Annotated[
        Optional[str], Field(..., alias=UserAPIKeyLabelNames.ROUTE.value)
    ] = None


class PrometheusMetricsConfig(BaseModel):
    """Configuration for filtering Prometheus metrics"""

    group: str = Field(..., description="Group name for this set of metrics")
    metrics: List[str] = Field(
        ..., description="List of metric names to include in this group"
    )
    include_labels: Optional[List[str]] = Field(
        None,
        description="List of labels to include for these metrics. If None, includes all default labels.",
    )


class PrometheusSettings(BaseModel):
    """Settings for Prometheus metrics configuration"""

    prometheus_metrics_config: Optional[List[PrometheusMetricsConfig]] = Field(
        None,
        description="Configuration for filtering Prometheus metrics by groups and labels",
    )


class NoOpMetric:
    """A no-op metric that has the same interface as prometheus metrics but does nothing"""

    def __init__(self, *args, **kwargs):
        pass

    def labels(self, *args, **kwargs):
        return self

    def inc(self, *args, **kwargs):
        pass

    def set(self, *args, **kwargs):
        pass

    def observe(self, *args, **kwargs):
        pass

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\filters\app.py ===
"""
Filters that accept a `Application` as argument.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from prompt_toolkit.application.current import get_app
from prompt_toolkit.cache import memoized
from prompt_toolkit.enums import EditingMode

from .base import Condition

if TYPE_CHECKING:
    from prompt_toolkit.layout.layout import FocusableElement


__all__ = [
    "has_arg",
    "has_completions",
    "completion_is_selected",
    "has_focus",
    "buffer_has_focus",
    "has_selection",
    "has_suggestion",
    "has_validation_error",
    "is_done",
    "is_read_only",
    "is_multiline",
    "renderer_height_is_known",
    "in_editing_mode",
    "in_paste_mode",
    "vi_mode",
    "vi_navigation_mode",
    "vi_insert_mode",
    "vi_insert_multiple_mode",
    "vi_replace_mode",
    "vi_selection_mode",
    "vi_waiting_for_text_object_mode",
    "vi_digraph_mode",
    "vi_recording_macro",
    "emacs_mode",
    "emacs_insert_mode",
    "emacs_selection_mode",
    "shift_selection_mode",
    "is_searching",
    "control_is_searchable",
    "vi_search_direction_reversed",
]


# NOTE: `has_focus` below should *not* be `memoized`. It can reference any user
#       control. For instance, if we would continuously create new
#       `PromptSession` instances, then previous instances won't be released,
#       because this memoize (which caches results in the global scope) will
#       still refer to each instance.
def has_focus(value: FocusableElement) -> Condition:
    """
    Enable when this buffer has the focus.
    """
    from prompt_toolkit.buffer import Buffer
    from prompt_toolkit.layout import walk
    from prompt_toolkit.layout.containers import Container, Window, to_container
    from prompt_toolkit.layout.controls import UIControl

    if isinstance(value, str):

        def test() -> bool:
            return get_app().current_buffer.name == value

    elif isinstance(value, Buffer):

        def test() -> bool:
            return get_app().current_buffer == value

    elif isinstance(value, UIControl):

        def test() -> bool:
            return get_app().layout.current_control == value

    else:
        value = to_container(value)

        if isinstance(value, Window):

            def test() -> bool:
                return get_app().layout.current_window == value

        else:

            def test() -> bool:
                # Consider focused when any window inside this container is
                # focused.
                current_window = get_app().layout.current_window

                for c in walk(cast(Container, value)):
                    if isinstance(c, Window) and c == current_window:
                        return True
                return False

    @Condition
    def has_focus_filter() -> bool:
        return test()

    return has_focus_filter


@Condition
def buffer_has_focus() -> bool:
    """
    Enabled when the currently focused control is a `BufferControl`.
    """
    return get_app().layout.buffer_has_focus


@Condition
def has_selection() -> bool:
    """
    Enable when the current buffer has a selection.
    """
    return bool(get_app().current_buffer.selection_state)


@Condition
def has_suggestion() -> bool:
    """
    Enable when the current buffer has a suggestion.
    """
    buffer = get_app().current_buffer
    return buffer.suggestion is not None and buffer.suggestion.text != ""


@Condition
def has_completions() -> bool:
    """
    Enable when the current buffer has completions.
    """
    state = get_app().current_buffer.complete_state
    return state is not None and len(state.completions) > 0


@Condition
def completion_is_selected() -> bool:
    """
    True when the user selected a completion.
    """
    complete_state = get_app().current_buffer.complete_state
    return complete_state is not None and complete_state.current_completion is not None


@Condition
def is_read_only() -> bool:
    """
    True when the current buffer is read only.
    """
    return get_app().current_buffer.read_only()


@Condition
def is_multiline() -> bool:
    """
    True when the current buffer has been marked as multiline.
    """
    return get_app().current_buffer.multiline()


@Condition
def has_validation_error() -> bool:
    "Current buffer has validation error."
    return get_app().current_buffer.validation_error is not None


@Condition
def has_arg() -> bool:
    "Enable when the input processor has an 'arg'."
    return get_app().key_processor.arg is not None


@Condition
def is_done() -> bool:
    """
    True when the CLI is returning, aborting or exiting.
    """
    return get_app().is_done


@Condition
def renderer_height_is_known() -> bool:
    """
    Only True when the renderer knows it's real height.

    (On VT100 terminals, we have to wait for a CPR response, before we can be
    sure of the available height between the cursor position and the bottom of
    the terminal. And usually it's nicer to wait with drawing bottom toolbars
    until we receive the height, in order to avoid flickering -- first drawing
    somewhere in the middle, and then again at the bottom.)
    """
    return get_app().renderer.height_is_known


@memoized()
def in_editing_mode(editing_mode: EditingMode) -> Condition:
    """
    Check whether a given editing mode is active. (Vi or Emacs.)
    """

    @Condition
    def in_editing_mode_filter() -> bool:
        return get_app().editing_mode == editing_mode

    return in_editing_mode_filter


@Condition
def in_paste_mode() -> bool:
    return get_app().paste_mode()


@Condition
def vi_mode() -> bool:
    return get_app().editing_mode == EditingMode.VI


@Condition
def vi_navigation_mode() -> bool:
    """
    Active when the set for Vi navigation key bindings are active.
    """
    from prompt_toolkit.key_binding.vi_state import InputMode

    app = get_app()

    if (
        app.editing_mode != EditingMode.VI
        or app.vi_state.operator_func
        or app.vi_state.waiting_for_digraph
        or app.current_buffer.selection_state
    ):
        return False

    return (
        app.vi_state.input_mode == InputMode.NAVIGATION
        or app.vi_state.temporary_navigation_mode
        or app.current_buffer.read_only()
    )


@Condition
def vi_insert_mode() -> bool:
    from prompt_toolkit.key_binding.vi_state import InputMode

    app = get_app()

    if (
        app.editing_mode != EditingMode.VI
        or app.vi_state.operator_func
        or app.vi_state.waiting_for_digraph
        or app.current_buffer.selection_state
        or app.vi_state.temporary_navigation_mode
        or app.current_buffer.read_only()
    ):
        return False

    return app.vi_state.input_mode == InputMode.INSERT


@Condition
def vi_insert_multiple_mode() -> bool:
    from prompt_toolkit.key_binding.vi_state import InputMode

    app = get_app()

    if (
        app.editing_mode != EditingMode.VI
        or app.vi_state.operator_func
        or app.vi_state.waiting_for_digraph
        or app.current_buffer.selection_state
        or app.vi_state.temporary_navigation_mode
        or app.current_buffer.read_only()
    ):
        return False

    return app.vi_state.input_mode == InputMode.INSERT_MULTIPLE


@Condition
def vi_replace_mode() -> bool:
    from prompt_toolkit.key_binding.vi_state import InputMode

    app = get_app()

    if (
        app.editing_mode != EditingMode.VI
        or app.vi_state.operator_func
        or app.vi_state.waiting_for_digraph
        or app.current_buffer.selection_state
        or app.vi_state.temporary_navigation_mode
        or app.current_buffer.read_only()
    ):
        return False

    return app.vi_state.input_mode == InputMode.REPLACE


@Condition
def vi_replace_single_mode() -> bool:
    from prompt_toolkit.key_binding.vi_state import InputMode

    app = get_app()

    if (
        app.editing_mode != EditingMode.VI
        or app.vi_state.operator_func
        or app.vi_state.waiting_for_digraph
        or app.current_buffer.selection_state
        or app.vi_state.temporary_navigation_mode
        or app.current_buffer.read_only()
    ):
        return False

    return app.vi_state.input_mode == InputMode.REPLACE_SINGLE


@Condition
def vi_selection_mode() -> bool:
    app = get_app()
    if app.editing_mode != EditingMode.VI:
        return False

    return bool(app.current_buffer.selection_state)


@Condition
def vi_waiting_for_text_object_mode() -> bool:
    app = get_app()
    if app.editing_mode != EditingMode.VI:
        return False

    return app.vi_state.operator_func is not None


@Condition
def vi_digraph_mode() -> bool:
    app = get_app()
    if app.editing_mode != EditingMode.VI:
        return False

    return app.vi_state.waiting_for_digraph


@Condition
def vi_recording_macro() -> bool:
    "When recording a Vi macro."
    app = get_app()
    if app.editing_mode != EditingMode.VI:
        return False

    return app.vi_state.recording_register is not None


@Condition
def emacs_mode() -> bool:
    "When the Emacs bindings are active."
    return get_app().editing_mode == EditingMode.EMACS


@Condition
def emacs_insert_mode() -> bool:
    app = get_app()
    if (
        app.editing_mode != EditingMode.EMACS
        or app.current_buffer.selection_state
        or app.current_buffer.read_only()
    ):
        return False
    return True


@Condition
def emacs_selection_mode() -> bool:
    app = get_app()
    return bool(
        app.editing_mode == EditingMode.EMACS and app.current_buffer.selection_state
    )


@Condition
def shift_selection_mode() -> bool:
    app = get_app()
    return bool(
        app.current_buffer.selection_state
        and app.current_buffer.selection_state.shift_mode
    )


@Condition
def is_searching() -> bool:
    "When we are searching."
    app = get_app()
    return app.layout.is_searching


@Condition
def control_is_searchable() -> bool:
    "When the current UIControl is searchable."
    from prompt_toolkit.layout.controls import BufferControl

    control = get_app().layout.current_control

    return (
        isinstance(control, BufferControl) and control.search_buffer_control is not None
    )


@Condition
def vi_search_direction_reversed() -> bool:
    "When the '/' and '?' key bindings for Vi-style searching have been reversed."
    return get_app().reverse_vi_search_direction()

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\rebol.py ===
"""
    pygments.lexers.rebol
    ~~~~~~~~~~~~~~~~~~~~~

    Lexers for the REBOL and related languages.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, bygroups
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Generic, Whitespace

__all__ = ['RebolLexer', 'RedLexer']


class RebolLexer(RegexLexer):
    """
    A REBOL lexer.
    """
    name = 'REBOL'
    aliases = ['rebol']
    filenames = ['*.r', '*.r3', '*.reb']
    mimetypes = ['text/x-rebol']
    url = 'http://www.rebol.com'
    version_added = '1.1'

    flags = re.IGNORECASE | re.MULTILINE

    escape_re = r'(?:\^\([0-9a-f]{1,4}\)*)'

    def word_callback(lexer, match):
        word = match.group()

        if re.match(".*:$", word):
            yield match.start(), Generic.Subheading, word
        elif re.match(
            r'(native|alias|all|any|as-string|as-binary|bind|bound\?|case|'
            r'catch|checksum|comment|debase|dehex|exclude|difference|disarm|'
            r'either|else|enbase|foreach|remove-each|form|free|get|get-env|if|'
            r'in|intersect|loop|minimum-of|maximum-of|mold|new-line|'
            r'new-line\?|not|now|prin|print|reduce|compose|construct|repeat|'
            r'reverse|save|script\?|set|shift|switch|throw|to-hex|trace|try|'
            r'type\?|union|unique|unless|unprotect|unset|until|use|value\?|'
            r'while|compress|decompress|secure|open|close|read|read-io|'
            r'write-io|write|update|query|wait|input\?|exp|log-10|log-2|'
            r'log-e|square-root|cosine|sine|tangent|arccosine|arcsine|'
            r'arctangent|protect|lowercase|uppercase|entab|detab|connected\?|'
            r'browse|launch|stats|get-modes|set-modes|to-local-file|'
            r'to-rebol-file|encloak|decloak|create-link|do-browser|bind\?|'
            r'hide|draw|show|size-text|textinfo|offset-to-caret|'
            r'caret-to-offset|local-request-file|rgb-to-hsv|hsv-to-rgb|'
            r'crypt-strength\?|dh-make-key|dh-generate-key|dh-compute-key|'
            r'dsa-make-key|dsa-generate-key|dsa-make-signature|'
            r'dsa-verify-signature|rsa-make-key|rsa-generate-key|'
            r'rsa-encrypt)$', word):
            yield match.start(), Name.Builtin, word
        elif re.match(
            r'(add|subtract|multiply|divide|remainder|power|and~|or~|xor~|'
            r'minimum|maximum|negate|complement|absolute|random|head|tail|'
            r'next|back|skip|at|pick|first|second|third|fourth|fifth|sixth|'
            r'seventh|eighth|ninth|tenth|last|path|find|select|make|to|copy\*|'
            r'insert|remove|change|poke|clear|trim|sort|min|max|abs|cp|'
            r'copy)$', word):
            yield match.start(), Name.Function, word
        elif re.match(
            r'(error|source|input|license|help|install|echo|Usage|with|func|'
            r'throw-on-error|function|does|has|context|probe|\?\?|as-pair|'
            r'mod|modulo|round|repend|about|set-net|append|join|rejoin|reform|'
            r'remold|charset|array|replace|move|extract|forskip|forall|alter|'
            r'first+|also|take|for|forever|dispatch|attempt|what-dir|'
            r'change-dir|clean-path|list-dir|dirize|rename|split-path|delete|'
            r'make-dir|delete-dir|in-dir|confirm|dump-obj|upgrade|what|'
            r'build-tag|process-source|build-markup|decode-cgi|read-cgi|'
            r'write-user|save-user|set-user-name|protect-system|parse-xml|'
            r'cvs-date|cvs-version|do-boot|get-net-info|desktop|layout|'
            r'scroll-para|get-face|alert|set-face|uninstall|unfocus|'
            r'request-dir|center-face|do-events|net-error|decode-url|'
            r'parse-header|parse-header-date|parse-email-addrs|import-email|'
            r'send|build-attach-body|resend|show-popup|hide-popup|open-events|'
            r'find-key-face|do-face|viewtop|confine|find-window|'
            r'insert-event-func|remove-event-func|inform|dump-pane|dump-face|'
            r'flag-face|deflag-face|clear-fields|read-net|vbug|path-thru|'
            r'read-thru|load-thru|do-thru|launch-thru|load-image|'
            r'request-download|do-face-alt|set-font|set-para|get-style|'
            r'set-style|make-face|stylize|choose|hilight-text|hilight-all|'
            r'unlight-text|focus|scroll-drag|clear-face|reset-face|scroll-face|'
            r'resize-face|load-stock|load-stock-block|notify|request|flash|'
            r'request-color|request-pass|request-text|request-list|'
            r'request-date|request-file|dbug|editor|link-relative-path|'
            r'emailer|parse-error)$', word):
            yield match.start(), Keyword.Namespace, word
        elif re.match(
            r'(halt|quit|do|load|q|recycle|call|run|ask|parse|view|unview|'
            r'return|exit|break)$', word):
            yield match.start(), Name.Exception, word
        elif re.match('REBOL$', word):
            yield match.start(), Generic.Heading, word
        elif re.match("to-.*", word):
            yield match.start(), Keyword, word
        elif re.match(r'(\+|-|\*|/|//|\*\*|and|or|xor|=\?|=|==|<>|<|>|<=|>=)$',
                      word):
            yield match.start(), Operator, word
        elif re.match(r".*\?$", word):
            yield match.start(), Keyword, word
        elif re.match(r".*\!$", word):
            yield match.start(), Keyword.Type, word
        elif re.match("'.*", word):
            yield match.start(), Name.Variable.Instance, word  # lit-word
        elif re.match("#.*", word):
            yield match.start(), Name.Label, word  # issue
        elif re.match("%.*", word):
            yield match.start(), Name.Decorator, word  # file
        else:
            yield match.start(), Name.Variable, word

    tokens = {
        'root': [
            (r'\s+', Text),
            (r'#"', String.Char, 'char'),
            (r'#\{[0-9a-f]*\}', Number.Hex),
            (r'2#\{', Number.Hex, 'bin2'),
            (r'64#\{[0-9a-z+/=\s]*\}', Number.Hex),
            (r'"', String, 'string'),
            (r'\{', String, 'string2'),
            (r';#+.*\n', Comment.Special),
            (r';\*+.*\n', Comment.Preproc),
            (r';.*\n', Comment),
            (r'%"', Name.Decorator, 'stringFile'),
            (r'%[^(^{")\s\[\]]+', Name.Decorator),
            (r'[+-]?([a-z]{1,3})?\$\d+(\.\d+)?', Number.Float),  # money
            (r'[+-]?\d+\:\d+(\:\d+)?(\.\d+)?', String.Other),    # time
            (r'\d+[\-/][0-9a-z]+[\-/]\d+(\/\d+\:\d+((\:\d+)?'
             r'([.\d+]?([+-]?\d+:\d+)?)?)?)?', String.Other),   # date
            (r'\d+(\.\d+)+\.\d+', Keyword.Constant),             # tuple
            (r'\d+X\d+', Keyword.Constant),                   # pair
            (r'[+-]?\d+(\'\d+)?([.,]\d*)?E[+-]?\d+', Number.Float),
            (r'[+-]?\d+(\'\d+)?[.,]\d*', Number.Float),
            (r'[+-]?\d+(\'\d+)?', Number),
            (r'[\[\]()]', Generic.Strong),
            (r'[a-z]+[^(^{"\s:)]*://[^(^{"\s)]*', Name.Decorator),  # url
            (r'mailto:[^(^{"@\s)]+@[^(^{"@\s)]+', Name.Decorator),  # url
            (r'[^(^{"@\s)]+@[^(^{"@\s)]+', Name.Decorator),         # email
            (r'comment\s"', Comment, 'commentString1'),
            (r'comment\s\{', Comment, 'commentString2'),
            (r'comment\s\[', Comment, 'commentBlock'),
            (r'comment\s[^(\s{"\[]+', Comment),
            (r'/[^(^{")\s/[\]]*', Name.Attribute),
            (r'([^(^{")\s/[\]]+)(?=[:({"\s/\[\]])', word_callback),
            (r'<[\w:.-]*>', Name.Tag),
            (r'<[^(<>\s")]+', Name.Tag, 'tag'),
            (r'([^(^{")\s]+)', Text),
        ],
        'string': [
            (r'[^(^")]+', String),
            (escape_re, String.Escape),
            (r'[(|)]+', String),
            (r'\^.', String.Escape),
            (r'"', String, '#pop'),
        ],
        'string2': [
            (r'[^(^{})]+', String),
            (escape_re, String.Escape),
            (r'[(|)]+', String),
            (r'\^.', String.Escape),
            (r'\{', String, '#push'),
            (r'\}', String, '#pop'),
        ],
        'stringFile': [
            (r'[^(^")]+', Name.Decorator),
            (escape_re, Name.Decorator),
            (r'\^.', Name.Decorator),
            (r'"', Name.Decorator, '#pop'),
        ],
        'char': [
            (escape_re + '"', String.Char, '#pop'),
            (r'\^."', String.Char, '#pop'),
            (r'."', String.Char, '#pop'),
        ],
        'tag': [
            (escape_re, Name.Tag),
            (r'"', Name.Tag, 'tagString'),
            (r'[^(<>\r\n")]+', Name.Tag),
            (r'>', Name.Tag, '#pop'),
        ],
        'tagString': [
            (r'[^(^")]+', Name.Tag),
            (escape_re, Name.Tag),
            (r'[(|)]+', Name.Tag),
            (r'\^.', Name.Tag),
            (r'"', Name.Tag, '#pop'),
        ],
        'tuple': [
            (r'(\d+\.)+', Keyword.Constant),
            (r'\d+', Keyword.Constant, '#pop'),
        ],
        'bin2': [
            (r'\s+', Number.Hex),
            (r'([01]\s*){8}', Number.Hex),
            (r'\}', Number.Hex, '#pop'),
        ],
        'commentString1': [
            (r'[^(^")]+', Comment),
            (escape_re, Comment),
            (r'[(|)]+', Comment),
            (r'\^.', Comment),
            (r'"', Comment, '#pop'),
        ],
        'commentString2': [
            (r'[^(^{})]+', Comment),
            (escape_re, Comment),
            (r'[(|)]+', Comment),
            (r'\^.', Comment),
            (r'\{', Comment, '#push'),
            (r'\}', Comment, '#pop'),
        ],
        'commentBlock': [
            (r'\[', Comment, '#push'),
            (r'\]', Comment, '#pop'),
            (r'"', Comment, "commentString1"),
            (r'\{', Comment, "commentString2"),
            (r'[^(\[\]"{)]+', Comment),
        ],
    }

    def analyse_text(text):
        """
        Check if code contains REBOL header and so it probably not R code
        """
        if re.match(r'^\s*REBOL\s*\[', text, re.IGNORECASE):
            # The code starts with REBOL header
            return 1.0
        elif re.search(r'\s*REBOL\s*\[', text, re.IGNORECASE):
            # The code contains REBOL header but also some text before it
            return 0.5


class RedLexer(RegexLexer):
    """
    A Red-language lexer.
    """
    name = 'Red'
    aliases = ['red', 'red/system']
    filenames = ['*.red', '*.reds']
    mimetypes = ['text/x-red', 'text/x-red-system']
    url = 'https://www.red-lang.org'
    version_added = '2.0'

    flags = re.IGNORECASE | re.MULTILINE

    escape_re = r'(?:\^\([0-9a-f]{1,4}\)*)'

    def word_callback(lexer, match):
        word = match.group()

        if re.match(".*:$", word):
            yield match.start(), Generic.Subheading, word
        elif re.match(r'(if|unless|either|any|all|while|until|loop|repeat|'
                      r'foreach|forall|func|function|does|has|switch|'
                      r'case|reduce|compose|get|set|print|prin|equal\?|'
                      r'not-equal\?|strict-equal\?|lesser\?|greater\?|lesser-or-equal\?|'
                      r'greater-or-equal\?|same\?|not|type\?|stats|'
                      r'bind|union|replace|charset|routine)$', word):
            yield match.start(), Name.Builtin, word
        elif re.match(r'(make|random|reflect|to|form|mold|absolute|add|divide|multiply|negate|'
                      r'power|remainder|round|subtract|even\?|odd\?|and~|complement|or~|xor~|'
                      r'append|at|back|change|clear|copy|find|head|head\?|index\?|insert|'
                      r'length\?|next|pick|poke|remove|reverse|select|sort|skip|swap|tail|tail\?|'
                      r'take|trim|create|close|delete|modify|open|open\?|query|read|rename|'
                      r'update|write)$', word):
            yield match.start(), Name.Function, word
        elif re.match(r'(yes|on|no|off|true|false|tab|cr|lf|newline|escape|slash|sp|space|null|'
                      r'none|crlf|dot|null-byte)$', word):
            yield match.start(), Name.Builtin.Pseudo, word
        elif re.match(r'(#system-global|#include|#enum|#define|#either|#if|#import|#export|'
                      r'#switch|#default|#get-definition)$', word):
            yield match.start(), Keyword.Namespace, word
        elif re.match(r'(system|halt|quit|quit-return|do|load|q|recycle|call|run|ask|parse|'
                      r'raise-error|return|exit|break|alias|push|pop|probe|\?\?|spec-of|body-of|'
                      r'quote|forever)$', word):
            yield match.start(), Name.Exception, word
        elif re.match(r'(action\?|block\?|char\?|datatype\?|file\?|function\?|get-path\?|zero\?|'
                      r'get-word\?|integer\?|issue\?|lit-path\?|lit-word\?|logic\?|native\?|'
                      r'op\?|paren\?|path\?|refinement\?|set-path\?|set-word\?|string\?|unset\?|'
                      r'any-struct\?|none\?|word\?|any-series\?)$', word):
            yield match.start(), Keyword, word
        elif re.match(r'(JNICALL|stdcall|cdecl|infix)$', word):
            yield match.start(), Keyword.Namespace, word
        elif re.match("to-.*", word):
            yield match.start(), Keyword, word
        elif re.match(r'(\+|-\*\*|-|\*\*|//|/|\*|and|or|xor|=\?|===|==|=|<>|<=|>=|'
                      r'<<<|>>>|<<|>>|<|>%)$', word):
            yield match.start(), Operator, word
        elif re.match(r".*\!$", word):
            yield match.start(), Keyword.Type, word
        elif re.match("'.*", word):
            yield match.start(), Name.Variable.Instance, word  # lit-word
        elif re.match("#.*", word):
            yield match.start(), Name.Label, word  # issue
        elif re.match("%.*", word):
            yield match.start(), Name.Decorator, word  # file
        elif re.match(":.*", word):
            yield match.start(), Generic.Subheading, word  # get-word
        else:
            yield match.start(), Name.Variable, word

    tokens = {
        'root': [
            (r'\s+', Text),
            (r'#"', String.Char, 'char'),
            (r'#\{[0-9a-f\s]*\}', Number.Hex),
            (r'2#\{', Number.Hex, 'bin2'),
            (r'64#\{[0-9a-z+/=\s]*\}', Number.Hex),
            (r'([0-9a-f]+)(h)((\s)|(?=[\[\]{}"()]))',
             bygroups(Number.Hex, Name.Variable, Whitespace)),
            (r'"', String, 'string'),
            (r'\{', String, 'string2'),
            (r';#+.*\n', Comment.Special),
            (r';\*+.*\n', Comment.Preproc),
            (r';.*\n', Comment),
            (r'%"', Name.Decorator, 'stringFile'),
            (r'%[^(^{")\s\[\]]+', Name.Decorator),
            (r'[+-]?([a-z]{1,3})?\$\d+(\.\d+)?', Number.Float),  # money
            (r'[+-]?\d+\:\d+(\:\d+)?(\.\d+)?', String.Other),    # time
            (r'\d+[\-/][0-9a-z]+[\-/]\d+(/\d+:\d+((:\d+)?'
             r'([\.\d+]?([+-]?\d+:\d+)?)?)?)?', String.Other),   # date
            (r'\d+(\.\d+)+\.\d+', Keyword.Constant),             # tuple
            (r'\d+X\d+', Keyword.Constant),                   # pair
            (r'[+-]?\d+(\'\d+)?([.,]\d*)?E[+-]?\d+', Number.Float),
            (r'[+-]?\d+(\'\d+)?[.,]\d*', Number.Float),
            (r'[+-]?\d+(\'\d+)?', Number),
            (r'[\[\]()]', Generic.Strong),
            (r'[a-z]+[^(^{"\s:)]*://[^(^{"\s)]*', Name.Decorator),  # url
            (r'mailto:[^(^{"@\s)]+@[^(^{"@\s)]+', Name.Decorator),  # url
            (r'[^(^{"@\s)]+@[^(^{"@\s)]+', Name.Decorator),         # email
            (r'comment\s"', Comment, 'commentString1'),
            (r'comment\s\{', Comment, 'commentString2'),
            (r'comment\s\[', Comment, 'commentBlock'),
            (r'comment\s[^(\s{"\[]+', Comment),
            (r'/[^(^{^")\s/[\]]*', Name.Attribute),
            (r'([^(^{^")\s/[\]]+)(?=[:({"\s/\[\]])', word_callback),
            (r'<[\w:.-]*>', Name.Tag),
            (r'<[^(<>\s")]+', Name.Tag, 'tag'),
            (r'([^(^{")\s]+)', Text),
        ],
        'string': [
            (r'[^(^")]+', String),
            (escape_re, String.Escape),
            (r'[(|)]+', String),
            (r'\^.', String.Escape),
            (r'"', String, '#pop'),
        ],
        'string2': [
            (r'[^(^{})]+', String),
            (escape_re, String.Escape),
            (r'[(|)]+', String),
            (r'\^.', String.Escape),
            (r'\{', String, '#push'),
            (r'\}', String, '#pop'),
        ],
        'stringFile': [
            (r'[^(^")]+', Name.Decorator),
            (escape_re, Name.Decorator),
            (r'\^.', Name.Decorator),
            (r'"', Name.Decorator, '#pop'),
        ],
        'char': [
            (escape_re + '"', String.Char, '#pop'),
            (r'\^."', String.Char, '#pop'),
            (r'."', String.Char, '#pop'),
        ],
        'tag': [
            (escape_re, Name.Tag),
            (r'"', Name.Tag, 'tagString'),
            (r'[^(<>\r\n")]+', Name.Tag),
            (r'>', Name.Tag, '#pop'),
        ],
        'tagString': [
            (r'[^(^")]+', Name.Tag),
            (escape_re, Name.Tag),
            (r'[(|)]+', Name.Tag),
            (r'\^.', Name.Tag),
            (r'"', Name.Tag, '#pop'),
        ],
        'tuple': [
            (r'(\d+\.)+', Keyword.Constant),
            (r'\d+', Keyword.Constant, '#pop'),
        ],
        'bin2': [
            (r'\s+', Number.Hex),
            (r'([01]\s*){8}', Number.Hex),
            (r'\}', Number.Hex, '#pop'),
        ],
        'commentString1': [
            (r'[^(^")]+', Comment),
            (escape_re, Comment),
            (r'[(|)]+', Comment),
            (r'\^.', Comment),
            (r'"', Comment, '#pop'),
        ],
        'commentString2': [
            (r'[^(^{})]+', Comment),
            (escape_re, Comment),
            (r'[(|)]+', Comment),
            (r'\^.', Comment),
            (r'\{', Comment, '#push'),
            (r'\}', Comment, '#pop'),
        ],
        'commentBlock': [
            (r'\[', Comment, '#push'),
            (r'\]', Comment, '#pop'),
            (r'"', Comment, "commentString1"),
            (r'\{', Comment, "commentString2"),
            (r'[^(\[\]"{)]+', Comment),
        ],
    }

# === NexusCore/openenv\Lib\site-packages\trio\_tests\test_highlevel_open_tcp_listeners.py ===
from __future__ import annotations

import errno
import socket as stdlib_socket
import sys
from socket import AddressFamily, SocketKind
from typing import TYPE_CHECKING, cast, overload

import attrs
import pytest

import trio
from trio import (
    SocketListener,
    open_tcp_listeners,
    open_tcp_stream,
    serve_tcp,
)
from trio.abc import HostnameResolver, SendStream, SocketFactory
from trio.testing import open_stream_to_socket_listener

from .. import socket as tsocket
from .._core._tests.tutil import binds_ipv6, slow

if sys.version_info < (3, 11):
    from exceptiongroup import BaseExceptionGroup

if TYPE_CHECKING:
    from collections.abc import Sequence

    from typing_extensions import Buffer

    from trio._socket import AddressFormat


async def test_open_tcp_listeners_basic() -> None:
    listeners = await open_tcp_listeners(0)
    assert isinstance(listeners, list)
    for obj in listeners:
        assert isinstance(obj, SocketListener)
        # Binds to wildcard address by default
        assert obj.socket.family in [tsocket.AF_INET, tsocket.AF_INET6]
        assert obj.socket.getsockname()[0] in ["0.0.0.0", "::"]

    listener = listeners[0]
    # Make sure the backlog is at least 2
    c1 = await open_stream_to_socket_listener(listener)
    c2 = await open_stream_to_socket_listener(listener)

    s1 = await listener.accept()
    s2 = await listener.accept()

    # Note that we don't know which client stream is connected to which server
    # stream
    await s1.send_all(b"x")
    await s2.send_all(b"x")
    assert await c1.receive_some(1) == b"x"
    assert await c2.receive_some(1) == b"x"

    for resource in [c1, c2, s1, s2, *listeners]:
        await resource.aclose()


async def test_open_tcp_listeners_specific_port_specific_host() -> None:
    # Pick a port
    sock = tsocket.socket()
    await sock.bind(("127.0.0.1", 0))
    host, port = sock.getsockname()
    sock.close()

    (listener,) = await open_tcp_listeners(port, host=host)
    async with listener:
        assert listener.socket.getsockname() == (host, port)


@binds_ipv6
@slow
async def test_open_tcp_listeners_ipv6_v6only() -> None:
    # Check IPV6_V6ONLY is working properly
    (ipv6_listener,) = await open_tcp_listeners(0, host="::1")
    async with ipv6_listener:
        _, port, *_ = ipv6_listener.socket.getsockname()

        with pytest.raises(
            OSError,
            match=r"(Error|all attempts to) connect(ing)* to (\(')*127\.0\.0\.1(', |:)\d+(\): Connection refused| failed)$",
        ):
            # Windows retries failed connections so this takes seconds
            # (and that's why this is marked @slow)
            await open_tcp_stream("127.0.0.1", port)


async def test_open_tcp_listeners_rebind() -> None:
    (l1,) = await open_tcp_listeners(0, host="127.0.0.1")
    sockaddr1 = l1.socket.getsockname()

    # Plain old rebinding while it's still there should fail, even if we have
    # SO_REUSEADDR set
    with stdlib_socket.socket() as probe:
        probe.setsockopt(stdlib_socket.SOL_SOCKET, stdlib_socket.SO_REUSEADDR, 1)
        with pytest.raises(
            OSError,
            match=r"(Address (already )?in use|An attempt was made to access a socket in a way forbidden by its access permissions)$",
        ):
            probe.bind(sockaddr1)

    # Now use the first listener to set up some connections in various states,
    # and make sure that they don't create any obstacle to rebinding a second
    # listener after the first one is closed.
    c_established = await open_stream_to_socket_listener(l1)
    s_established = await l1.accept()

    c_time_wait = await open_stream_to_socket_listener(l1)
    s_time_wait = await l1.accept()
    # Server-initiated close leaves socket in TIME_WAIT
    await s_time_wait.aclose()

    await l1.aclose()
    (l2,) = await open_tcp_listeners(sockaddr1[1], host="127.0.0.1")
    sockaddr2 = l2.socket.getsockname()

    assert sockaddr1 == sockaddr2
    assert s_established.socket.getsockname() == sockaddr2
    assert c_time_wait.socket.getpeername() == sockaddr2

    for resource in [
        l1,
        l2,
        c_established,
        s_established,
        c_time_wait,
        s_time_wait,
    ]:
        await resource.aclose()


class FakeOSError(OSError):
    pass


@attrs.define(slots=False)
class FakeSocket(tsocket.SocketType):
    _family: AddressFamily = attrs.field(converter=AddressFamily)
    _type: SocketKind = attrs.field(converter=SocketKind)
    _proto: int

    closed: bool = False
    poison_listen: bool = False
    backlog: int | None = None

    @property
    def type(self) -> SocketKind:
        return self._type

    @property
    def family(self) -> AddressFamily:
        return self._family

    @property
    def proto(self) -> int:  # pragma: no cover
        return self._proto

    @overload
    def getsockopt(self, /, level: int, optname: int) -> int: ...

    @overload
    def getsockopt(self, /, level: int, optname: int, buflen: int) -> bytes: ...

    def getsockopt(
        self,
        /,
        level: int,
        optname: int,
        buflen: int | None = None,
    ) -> int | bytes:
        if (level, optname) == (tsocket.SOL_SOCKET, tsocket.SO_ACCEPTCONN):
            return True
        raise AssertionError()  # pragma: no cover

    @overload
    def setsockopt(self, /, level: int, optname: int, value: int | Buffer) -> None: ...

    @overload
    def setsockopt(
        self,
        /,
        level: int,
        optname: int,
        value: None,
        optlen: int,
    ) -> None: ...

    def setsockopt(
        self,
        /,
        level: int,
        optname: int,
        value: int | Buffer | None,
        optlen: int | None = None,
    ) -> None:
        pass

    async def bind(self, address: AddressFormat) -> None:
        pass

    def listen(self, /, backlog: int = min(stdlib_socket.SOMAXCONN, 128)) -> None:
        assert self.backlog is None
        assert backlog is not None
        self.backlog = backlog
        if self.poison_listen:
            raise FakeOSError("whoops")

    def close(self) -> None:
        self.closed = True


@attrs.define(slots=False)
class FakeSocketFactory(SocketFactory):
    poison_after: int
    sockets: list[tsocket.SocketType] = attrs.Factory(list)
    raise_on_family: dict[AddressFamily, int] = attrs.Factory(dict)  # family => errno

    def socket(
        self,
        family: AddressFamily | int | None = None,
        type_: SocketKind | int | None = None,
        proto: int = 0,
    ) -> tsocket.SocketType:
        assert family is not None
        assert type_ is not None
        if isinstance(family, int) and not isinstance(family, AddressFamily):
            family = AddressFamily(family)  # pragma: no cover
        if family in self.raise_on_family:
            raise OSError(self.raise_on_family[family], "nope")
        sock = FakeSocket(family, type_, proto)
        self.poison_after -= 1
        if self.poison_after == 0:
            sock.poison_listen = True
        self.sockets.append(sock)
        return sock


@attrs.define(slots=False)
class FakeHostnameResolver(HostnameResolver):
    family_addr_pairs: Sequence[tuple[AddressFamily, str]]

    async def getaddrinfo(
        self,
        host: bytes | None,
        port: bytes | str | int | None,
        family: int = 0,
        type: int = 0,
        proto: int = 0,
        flags: int = 0,
    ) -> list[
        tuple[
            AddressFamily,
            SocketKind,
            int,
            str,
            tuple[str, int] | tuple[str, int, int, int] | tuple[int, bytes],
        ]
    ]:
        assert isinstance(port, int)
        return [
            (family, tsocket.SOCK_STREAM, 0, "", (addr, port))
            for family, addr in self.family_addr_pairs
        ]

    async def getnameinfo(
        self,
        sockaddr: tuple[str, int] | tuple[str, int, int, int],
        flags: int,
    ) -> tuple[str, str]:
        raise NotImplementedError()


async def test_open_tcp_listeners_multiple_host_cleanup_on_error() -> None:
    # If we were trying to bind to multiple hosts and one of them failed, they
    # call get cleaned up before returning
    fsf = FakeSocketFactory(3)
    tsocket.set_custom_socket_factory(fsf)
    tsocket.set_custom_hostname_resolver(
        FakeHostnameResolver(
            [
                (tsocket.AF_INET, "1.1.1.1"),
                (tsocket.AF_INET, "2.2.2.2"),
                (tsocket.AF_INET, "3.3.3.3"),
            ],
        ),
    )

    with pytest.raises(FakeOSError):
        await open_tcp_listeners(80, host="example.org")

    assert len(fsf.sockets) == 3
    for sock in fsf.sockets:
        # property only exists on FakeSocket
        assert sock.closed  # type: ignore[attr-defined]


async def test_open_tcp_listeners_port_checking() -> None:
    for host in ["127.0.0.1", None]:
        with pytest.raises(TypeError):
            await open_tcp_listeners(None, host=host)  # type: ignore[arg-type]
        with pytest.raises(TypeError):
            await open_tcp_listeners(b"80", host=host)  # type: ignore[arg-type]
        with pytest.raises(TypeError):
            await open_tcp_listeners("http", host=host)  # type: ignore[arg-type]


async def test_serve_tcp() -> None:
    async def handler(stream: SendStream) -> None:
        await stream.send_all(b"x")

    async with trio.open_nursery() as nursery:
        # nursery.start is incorrectly typed, awaiting #2773
        value = await nursery.start(serve_tcp, handler, 0)
        assert isinstance(value, list)
        listeners = cast("list[SocketListener]", value)
        stream = await open_stream_to_socket_listener(listeners[0])
        async with stream:
            assert await stream.receive_some(1) == b"x"
            nursery.cancel_scope.cancel()


@pytest.mark.parametrize(
    "try_families",
    [{tsocket.AF_INET}, {tsocket.AF_INET6}, {tsocket.AF_INET, tsocket.AF_INET6}],
)
@pytest.mark.parametrize(
    "fail_families",
    [{tsocket.AF_INET}, {tsocket.AF_INET6}, {tsocket.AF_INET, tsocket.AF_INET6}],
)
async def test_open_tcp_listeners_some_address_families_unavailable(
    try_families: set[AddressFamily],
    fail_families: set[AddressFamily],
) -> None:
    fsf = FakeSocketFactory(
        10,
        raise_on_family=dict.fromkeys(fail_families, errno.EAFNOSUPPORT),
    )
    tsocket.set_custom_socket_factory(fsf)
    tsocket.set_custom_hostname_resolver(
        FakeHostnameResolver([(family, "foo") for family in try_families]),
    )

    should_succeed = try_families - fail_families

    if not should_succeed:
        with pytest.raises(OSError, match="This system doesn't support") as exc_info:
            await open_tcp_listeners(80, host="example.org")

        # open_listeners always creates an exceptiongroup with the
        # unsupported address families, regardless of the value of
        # strict_exception_groups or number of unsupported families.
        assert isinstance(exc_info.value.__cause__, BaseExceptionGroup)
        for subexc in exc_info.value.__cause__.exceptions:
            assert "nope" in str(subexc)
    else:
        listeners = await open_tcp_listeners(80)
        for listener in listeners:
            should_succeed.remove(listener.socket.family)
        assert not should_succeed


async def test_open_tcp_listeners_socket_fails_not_afnosupport() -> None:
    fsf = FakeSocketFactory(
        10,
        raise_on_family={
            tsocket.AF_INET: errno.EAFNOSUPPORT,
            tsocket.AF_INET6: errno.EINVAL,
        },
    )
    tsocket.set_custom_socket_factory(fsf)
    tsocket.set_custom_hostname_resolver(
        FakeHostnameResolver([(tsocket.AF_INET, "foo"), (tsocket.AF_INET6, "bar")]),
    )

    with pytest.raises(OSError, match="nope") as exc_info:
        await open_tcp_listeners(80, host="example.org")
    assert exc_info.value.errno == errno.EINVAL
    assert exc_info.value.__cause__ is None
    assert "nope" in str(exc_info.value)


# We used to have an elaborate test that opened a real TCP listening socket
# and then tried to measure its backlog by making connections to it. And most
# of the time, it worked. But no matter what we tried, it was always fragile,
# because it had to do things like use timeouts to guess when the listening
# queue was full, sometimes the CI hosts go into SYN-cookie mode (where there
# effectively is no backlog), sometimes the host might not be enough resources
# to give us the full requested backlog... it was a mess. So now we just check
# that the backlog argument is passed through correctly.
async def test_open_tcp_listeners_backlog() -> None:
    fsf = FakeSocketFactory(99)
    tsocket.set_custom_socket_factory(fsf)
    for given, expected in [
        (None, 0xFFFF),
        (99999999, 0xFFFF),
        (10, 10),
        (1, 1),
    ]:
        listeners = await open_tcp_listeners(0, backlog=given)
        assert listeners
        for listener in listeners:
            # `backlog` only exists on FakeSocket
            assert listener.socket.backlog == expected  # type: ignore[attr-defined]


async def test_open_tcp_listeners_backlog_float_error() -> None:
    fsf = FakeSocketFactory(99)
    tsocket.set_custom_socket_factory(fsf)
    for should_fail in (0.0, 2.18, 3.15, 9.75):
        with pytest.raises(
            TypeError,
            match=f"backlog must be an int or None, not {should_fail!r}",
        ):
            await open_tcp_listeners(0, backlog=should_fail)  # type: ignore[arg-type]

# === NexusCore/openenv\Lib\site-packages\aiohttp\web_fileresponse.py ===
import asyncio
import io
import os
import pathlib
import sys
from contextlib import suppress
from enum import Enum, auto
from mimetypes import MimeTypes
from stat import S_ISREG
from types import MappingProxyType
from typing import (  # noqa
    IO,
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Final,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
    Union,
    cast,
)

from . import hdrs
from .abc import AbstractStreamWriter
from .helpers import ETAG_ANY, ETag, must_be_empty_body
from .typedefs import LooseHeaders, PathLike
from .web_exceptions import (
    HTTPForbidden,
    HTTPNotFound,
    HTTPNotModified,
    HTTPPartialContent,
    HTTPPreconditionFailed,
    HTTPRequestRangeNotSatisfiable,
)
from .web_response import StreamResponse

__all__ = ("FileResponse",)

if TYPE_CHECKING:
    from .web_request import BaseRequest


_T_OnChunkSent = Optional[Callable[[bytes], Awaitable[None]]]


NOSENDFILE: Final[bool] = bool(os.environ.get("AIOHTTP_NOSENDFILE"))

CONTENT_TYPES: Final[MimeTypes] = MimeTypes()

# File extension to IANA encodings map that will be checked in the order defined.
ENCODING_EXTENSIONS = MappingProxyType(
    {ext: CONTENT_TYPES.encodings_map[ext] for ext in (".br", ".gz")}
)

FALLBACK_CONTENT_TYPE = "application/octet-stream"

# Provide additional MIME type/extension pairs to be recognized.
# https://en.wikipedia.org/wiki/List_of_archive_formats#Compression_only
ADDITIONAL_CONTENT_TYPES = MappingProxyType(
    {
        "application/gzip": ".gz",
        "application/x-brotli": ".br",
        "application/x-bzip2": ".bz2",
        "application/x-compress": ".Z",
        "application/x-xz": ".xz",
    }
)


class _FileResponseResult(Enum):
    """The result of the file response."""

    SEND_FILE = auto()  # Ie a regular file to send
    NOT_ACCEPTABLE = auto()  # Ie a socket, or non-regular file
    PRE_CONDITION_FAILED = auto()  # Ie If-Match or If-None-Match failed
    NOT_MODIFIED = auto()  # 304 Not Modified


# Add custom pairs and clear the encodings map so guess_type ignores them.
CONTENT_TYPES.encodings_map.clear()
for content_type, extension in ADDITIONAL_CONTENT_TYPES.items():
    CONTENT_TYPES.add_type(content_type, extension)


_CLOSE_FUTURES: Set[asyncio.Future[None]] = set()


class FileResponse(StreamResponse):
    """A response object can be used to send files."""

    def __init__(
        self,
        path: PathLike,
        chunk_size: int = 256 * 1024,
        status: int = 200,
        reason: Optional[str] = None,
        headers: Optional[LooseHeaders] = None,
    ) -> None:
        super().__init__(status=status, reason=reason, headers=headers)

        self._path = pathlib.Path(path)
        self._chunk_size = chunk_size

    def _seek_and_read(self, fobj: IO[Any], offset: int, chunk_size: int) -> bytes:
        fobj.seek(offset)
        return fobj.read(chunk_size)  # type: ignore[no-any-return]

    async def _sendfile_fallback(
        self, writer: AbstractStreamWriter, fobj: IO[Any], offset: int, count: int
    ) -> AbstractStreamWriter:
        # To keep memory usage low,fobj is transferred in chunks
        # controlled by the constructor's chunk_size argument.

        chunk_size = self._chunk_size
        loop = asyncio.get_event_loop()
        chunk = await loop.run_in_executor(
            None, self._seek_and_read, fobj, offset, chunk_size
        )
        while chunk:
            await writer.write(chunk)
            count = count - chunk_size
            if count <= 0:
                break
            chunk = await loop.run_in_executor(None, fobj.read, min(chunk_size, count))

        await writer.drain()
        return writer

    async def _sendfile(
        self, request: "BaseRequest", fobj: IO[Any], offset: int, count: int
    ) -> AbstractStreamWriter:
        writer = await super().prepare(request)
        assert writer is not None

        if NOSENDFILE or self.compression:
            return await self._sendfile_fallback(writer, fobj, offset, count)

        loop = request._loop
        transport = request.transport
        assert transport is not None

        try:
            await loop.sendfile(transport, fobj, offset, count)
        except NotImplementedError:
            return await self._sendfile_fallback(writer, fobj, offset, count)

        await super().write_eof()
        return writer

    @staticmethod
    def _etag_match(etag_value: str, etags: Tuple[ETag, ...], *, weak: bool) -> bool:
        if len(etags) == 1 and etags[0].value == ETAG_ANY:
            return True
        return any(
            etag.value == etag_value for etag in etags if weak or not etag.is_weak
        )

    async def _not_modified(
        self, request: "BaseRequest", etag_value: str, last_modified: float
    ) -> Optional[AbstractStreamWriter]:
        self.set_status(HTTPNotModified.status_code)
        self._length_check = False
        self.etag = etag_value  # type: ignore[assignment]
        self.last_modified = last_modified  # type: ignore[assignment]
        # Delete any Content-Length headers provided by user. HTTP 304
        # should always have empty response body
        return await super().prepare(request)

    async def _precondition_failed(
        self, request: "BaseRequest"
    ) -> Optional[AbstractStreamWriter]:
        self.set_status(HTTPPreconditionFailed.status_code)
        self.content_length = 0
        return await super().prepare(request)

    def _make_response(
        self, request: "BaseRequest", accept_encoding: str
    ) -> Tuple[
        _FileResponseResult, Optional[io.BufferedReader], os.stat_result, Optional[str]
    ]:
        """Return the response result, io object, stat result, and encoding.

        If an uncompressed file is returned, the encoding is set to
        :py:data:`None`.

        This method should be called from a thread executor
        since it calls os.stat which may block.
        """
        file_path, st, file_encoding = self._get_file_path_stat_encoding(
            accept_encoding
        )
        if not file_path:
            return _FileResponseResult.NOT_ACCEPTABLE, None, st, None

        etag_value = f"{st.st_mtime_ns:x}-{st.st_size:x}"

        # https://www.rfc-editor.org/rfc/rfc9110#section-13.1.1-2
        if (ifmatch := request.if_match) is not None and not self._etag_match(
            etag_value, ifmatch, weak=False
        ):
            return _FileResponseResult.PRE_CONDITION_FAILED, None, st, file_encoding

        if (
            (unmodsince := request.if_unmodified_since) is not None
            and ifmatch is None
            and st.st_mtime > unmodsince.timestamp()
        ):
            return _FileResponseResult.PRE_CONDITION_FAILED, None, st, file_encoding

        # https://www.rfc-editor.org/rfc/rfc9110#section-13.1.2-2
        if (ifnonematch := request.if_none_match) is not None and self._etag_match(
            etag_value, ifnonematch, weak=True
        ):
            return _FileResponseResult.NOT_MODIFIED, None, st, file_encoding

        if (
            (modsince := request.if_modified_since) is not None
            and ifnonematch is None
            and st.st_mtime <= modsince.timestamp()
        ):
            return _FileResponseResult.NOT_MODIFIED, None, st, file_encoding

        fobj = file_path.open("rb")
        with suppress(OSError):
            # fstat() may not be available on all platforms
            # Once we open the file, we want the fstat() to ensure
            # the file has not changed between the first stat()
            # and the open().
            st = os.stat(fobj.fileno())
        return _FileResponseResult.SEND_FILE, fobj, st, file_encoding

    def _get_file_path_stat_encoding(
        self, accept_encoding: str
    ) -> Tuple[Optional[pathlib.Path], os.stat_result, Optional[str]]:
        file_path = self._path
        for file_extension, file_encoding in ENCODING_EXTENSIONS.items():
            if file_encoding not in accept_encoding:
                continue

            compressed_path = file_path.with_suffix(file_path.suffix + file_extension)
            with suppress(OSError):
                # Do not follow symlinks and ignore any non-regular files.
                st = compressed_path.lstat()
                if S_ISREG(st.st_mode):
                    return compressed_path, st, file_encoding

        # Fallback to the uncompressed file
        st = file_path.stat()
        return file_path if S_ISREG(st.st_mode) else None, st, None

    async def prepare(self, request: "BaseRequest") -> Optional[AbstractStreamWriter]:
        loop = asyncio.get_running_loop()
        # Encoding comparisons should be case-insensitive
        # https://www.rfc-editor.org/rfc/rfc9110#section-8.4.1
        accept_encoding = request.headers.get(hdrs.ACCEPT_ENCODING, "").lower()
        try:
            response_result, fobj, st, file_encoding = await loop.run_in_executor(
                None, self._make_response, request, accept_encoding
            )
        except PermissionError:
            self.set_status(HTTPForbidden.status_code)
            return await super().prepare(request)
        except OSError:
            # Most likely to be FileNotFoundError or OSError for circular
            # symlinks in python >= 3.13, so respond with 404.
            self.set_status(HTTPNotFound.status_code)
            return await super().prepare(request)

        # Forbid special files like sockets, pipes, devices, etc.
        if response_result is _FileResponseResult.NOT_ACCEPTABLE:
            self.set_status(HTTPForbidden.status_code)
            return await super().prepare(request)

        if response_result is _FileResponseResult.PRE_CONDITION_FAILED:
            return await self._precondition_failed(request)

        if response_result is _FileResponseResult.NOT_MODIFIED:
            etag_value = f"{st.st_mtime_ns:x}-{st.st_size:x}"
            last_modified = st.st_mtime
            return await self._not_modified(request, etag_value, last_modified)

        assert fobj is not None
        try:
            return await self._prepare_open_file(request, fobj, st, file_encoding)
        finally:
            # We do not await here because we do not want to wait
            # for the executor to finish before returning the response
            # so the connection can begin servicing another request
            # as soon as possible.
            close_future = loop.run_in_executor(None, fobj.close)
            # Hold a strong reference to the future to prevent it from being
            # garbage collected before it completes.
            _CLOSE_FUTURES.add(close_future)
            close_future.add_done_callback(_CLOSE_FUTURES.remove)

    async def _prepare_open_file(
        self,
        request: "BaseRequest",
        fobj: io.BufferedReader,
        st: os.stat_result,
        file_encoding: Optional[str],
    ) -> Optional[AbstractStreamWriter]:
        status = self._status
        file_size: int = st.st_size
        file_mtime: float = st.st_mtime
        count: int = file_size
        start: Optional[int] = None

        if (ifrange := request.if_range) is None or file_mtime <= ifrange.timestamp():
            # If-Range header check:
            # condition = cached date >= last modification date
            # return 206 if True else 200.
            # if False:
            #   Range header would not be processed, return 200
            # if True but Range header missing
            #   return 200
            try:
                rng = request.http_range
                start = rng.start
                end: Optional[int] = rng.stop
            except ValueError:
                # https://tools.ietf.org/html/rfc7233:
                # A server generating a 416 (Range Not Satisfiable) response to
                # a byte-range request SHOULD send a Content-Range header field
                # with an unsatisfied-range value.
                # The complete-length in a 416 response indicates the current
                # length of the selected representation.
                #
                # Will do the same below. Many servers ignore this and do not
                # send a Content-Range header with HTTP 416
                self._headers[hdrs.CONTENT_RANGE] = f"bytes */{file_size}"
                self.set_status(HTTPRequestRangeNotSatisfiable.status_code)
                return await super().prepare(request)

            # If a range request has been made, convert start, end slice
            # notation into file pointer offset and count
            if start is not None:
                if start < 0 and end is None:  # return tail of file
                    start += file_size
                    if start < 0:
                        # if Range:bytes=-1000 in request header but file size
                        # is only 200, there would be trouble without this
                        start = 0
                    count = file_size - start
                else:
                    # rfc7233:If the last-byte-pos value is
                    # absent, or if the value is greater than or equal to
                    # the current length of the representation data,
                    # the byte range is interpreted as the remainder
                    # of the representation (i.e., the server replaces the
                    # value of last-byte-pos with a value that is one less than
                    # the current length of the selected representation).
                    count = (
                        min(end if end is not None else file_size, file_size) - start
                    )

                if start >= file_size:
                    # HTTP 416 should be returned in this case.
                    #
                    # According to https://tools.ietf.org/html/rfc7233:
                    # If a valid byte-range-set includes at least one
                    # byte-range-spec with a first-byte-pos that is less than
                    # the current length of the representation, or at least one
                    # suffix-byte-range-spec with a non-zero suffix-length,
                    # then the byte-range-set is satisfiable. Otherwise, the
                    # byte-range-set is unsatisfiable.
                    self._headers[hdrs.CONTENT_RANGE] = f"bytes */{file_size}"
                    self.set_status(HTTPRequestRangeNotSatisfiable.status_code)
                    return await super().prepare(request)

                status = HTTPPartialContent.status_code
                # Even though you are sending the whole file, you should still
                # return a HTTP 206 for a Range request.
                self.set_status(status)

        # If the Content-Type header is not already set, guess it based on the
        # extension of the request path. The encoding returned by guess_type
        #  can be ignored since the map was cleared above.
        if hdrs.CONTENT_TYPE not in self._headers:
            if sys.version_info >= (3, 13):
                guesser = CONTENT_TYPES.guess_file_type
            else:
                guesser = CONTENT_TYPES.guess_type
            self.content_type = guesser(self._path)[0] or FALLBACK_CONTENT_TYPE

        if file_encoding:
            self._headers[hdrs.CONTENT_ENCODING] = file_encoding
            self._headers[hdrs.VARY] = hdrs.ACCEPT_ENCODING
            # Disable compression if we are already sending
            # a compressed file since we don't want to double
            # compress.
            self._compression = False

        self.etag = f"{st.st_mtime_ns:x}-{st.st_size:x}"  # type: ignore[assignment]
        self.last_modified = file_mtime  # type: ignore[assignment]
        self.content_length = count

        self._headers[hdrs.ACCEPT_RANGES] = "bytes"

        if status == HTTPPartialContent.status_code:
            real_start = start
            assert real_start is not None
            self._headers[hdrs.CONTENT_RANGE] = "bytes {}-{}/{}".format(
                real_start, real_start + count - 1, file_size
            )

        # If we are sending 0 bytes calling sendfile() will throw a ValueError
        if count == 0 or must_be_empty_body(request.method, status):
            return await super().prepare(request)

        # be aware that start could be None or int=0 here.
        offset = start or 0

        return await self._sendfile(request, fobj, offset, count)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\permission_service\transports\grpc.py ===
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
from typing import Callable, Dict, Optional, Sequence, Tuple, Union
import warnings

from google.api_core import gapic_v1, grpc_helpers
import google.auth  # type: ignore
from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
from google.longrunning import operations_pb2  # type: ignore
from google.protobuf import empty_pb2  # type: ignore
import grpc  # type: ignore

from google.ai.generativelanguage_v1beta.types import permission as gag_permission
from google.ai.generativelanguage_v1beta.types import permission
from google.ai.generativelanguage_v1beta.types import permission_service

from .base import DEFAULT_CLIENT_INFO, PermissionServiceTransport


class PermissionServiceGrpcTransport(PermissionServiceTransport):
    """gRPC backend transport for PermissionService.

    Provides methods for managing permissions to PaLM API
    resources.

    This class defines the same methods as the primary client, so the
    primary client can load the underlying transport implementation
    and call it.

    It sends protocol buffers over the wire using gRPC (which is built on
    top of HTTP/2); the ``grpcio`` package must be installed.
    """

    _stubs: Dict[str, Callable]

    def __init__(
        self,
        *,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        channel: Optional[Union[grpc.Channel, Callable[..., grpc.Channel]]] = None,
        api_mtls_endpoint: Optional[str] = None,
        client_cert_source: Optional[Callable[[], Tuple[bytes, bytes]]] = None,
        ssl_channel_credentials: Optional[grpc.ChannelCredentials] = None,
        client_cert_source_for_mtls: Optional[Callable[[], Tuple[bytes, bytes]]] = None,
        quota_project_id: Optional[str] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
        always_use_jwt_access: Optional[bool] = False,
        api_audience: Optional[str] = None,
    ) -> None:
        """Instantiate the transport.

        Args:
            host (Optional[str]):
                 The hostname to connect to (default: 'generativelanguage.googleapis.com').
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
                This argument is ignored if a ``channel`` instance is provided.
            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
                This argument is ignored if a ``channel`` instance is provided.
            scopes (Optional(Sequence[str])): A list of scopes. This argument is
                ignored if a ``channel`` instance is provided.
            channel (Optional[Union[grpc.Channel, Callable[..., grpc.Channel]]]):
                A ``Channel`` instance through which to make calls, or a Callable
                that constructs and returns one. If set to None, ``self.create_channel``
                is used to create the channel. If a Callable is given, it will be called
                with the same arguments as used in ``self.create_channel``.
            api_mtls_endpoint (Optional[str]): Deprecated. The mutual TLS endpoint.
                If provided, it overrides the ``host`` argument and tries to create
                a mutual TLS channel with client SSL credentials from
                ``client_cert_source`` or application default SSL credentials.
            client_cert_source (Optional[Callable[[], Tuple[bytes, bytes]]]):
                Deprecated. A callback to provide client SSL certificate bytes and
                private key bytes, both in PEM format. It is ignored if
                ``api_mtls_endpoint`` is None.
            ssl_channel_credentials (grpc.ChannelCredentials): SSL credentials
                for the grpc channel. It is ignored if a ``channel`` instance is provided.
            client_cert_source_for_mtls (Optional[Callable[[], Tuple[bytes, bytes]]]):
                A callback to provide client certificate bytes and private key bytes,
                both in PEM format. It is used to configure a mutual TLS channel. It is
                ignored if a ``channel`` instance or ``ssl_channel_credentials`` is provided.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you're developing
                your own client library.
            always_use_jwt_access (Optional[bool]): Whether self signed JWT should
                be used for service account credentials.

        Raises:
          google.auth.exceptions.MutualTLSChannelError: If mutual TLS transport
              creation failed for any reason.
          google.api_core.exceptions.DuplicateCredentialArgs: If both ``credentials``
              and ``credentials_file`` are passed.
        """
        self._grpc_channel = None
        self._ssl_channel_credentials = ssl_channel_credentials
        self._stubs: Dict[str, Callable] = {}

        if api_mtls_endpoint:
            warnings.warn("api_mtls_endpoint is deprecated", DeprecationWarning)
        if client_cert_source:
            warnings.warn("client_cert_source is deprecated", DeprecationWarning)

        if isinstance(channel, grpc.Channel):
            # Ignore credentials if a channel was passed.
            credentials = False
            # If a channel was explicitly provided, set it.
            self._grpc_channel = channel
            self._ssl_channel_credentials = None

        else:
            if api_mtls_endpoint:
                host = api_mtls_endpoint

                # Create SSL credentials with client_cert_source or application
                # default SSL credentials.
                if client_cert_source:
                    cert, key = client_cert_source()
                    self._ssl_channel_credentials = grpc.ssl_channel_credentials(
                        certificate_chain=cert, private_key=key
                    )
                else:
                    self._ssl_channel_credentials = SslCredentials().ssl_credentials

            else:
                if client_cert_source_for_mtls and not ssl_channel_credentials:
                    cert, key = client_cert_source_for_mtls()
                    self._ssl_channel_credentials = grpc.ssl_channel_credentials(
                        certificate_chain=cert, private_key=key
                    )

        # The base transport sets the host, credentials and scopes
        super().__init__(
            host=host,
            credentials=credentials,
            credentials_file=credentials_file,
            scopes=scopes,
            quota_project_id=quota_project_id,
            client_info=client_info,
            always_use_jwt_access=always_use_jwt_access,
            api_audience=api_audience,
        )

        if not self._grpc_channel:
            # initialize with the provided callable or the default channel
            channel_init = channel or type(self).create_channel
            self._grpc_channel = channel_init(
                self._host,
                # use the credentials which are saved
                credentials=self._credentials,
                # Set ``credentials_file`` to ``None`` here as
                # the credentials that we saved earlier should be used.
                credentials_file=None,
                scopes=self._scopes,
                ssl_credentials=self._ssl_channel_credentials,
                quota_project_id=quota_project_id,
                options=[
                    ("grpc.max_send_message_length", -1),
                    ("grpc.max_receive_message_length", -1),
                ],
            )

        # Wrap messages. This must be done after self._grpc_channel exists
        self._prep_wrapped_messages(client_info)

    @classmethod
    def create_channel(
        cls,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        quota_project_id: Optional[str] = None,
        **kwargs,
    ) -> grpc.Channel:
        """Create and return a gRPC channel object.
        Args:
            host (Optional[str]): The host for the channel to use.
            credentials (Optional[~.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify this application to the service. If
                none are specified, the client will attempt to ascertain
                the credentials from the environment.
            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
                This argument is mutually exclusive with credentials.
            scopes (Optional[Sequence[str]]): A optional list of scopes needed for this
                service. These are only used when credentials are not specified and
                are passed to :func:`google.auth.default`.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            kwargs (Optional[dict]): Keyword arguments, which are passed to the
                channel creation.
        Returns:
            grpc.Channel: A gRPC channel object.

        Raises:
            google.api_core.exceptions.DuplicateCredentialArgs: If both ``credentials``
              and ``credentials_file`` are passed.
        """

        return grpc_helpers.create_channel(
            host,
            credentials=credentials,
            credentials_file=credentials_file,
            quota_project_id=quota_project_id,
            default_scopes=cls.AUTH_SCOPES,
            scopes=scopes,
            default_host=cls.DEFAULT_HOST,
            **kwargs,
        )

    @property
    def grpc_channel(self) -> grpc.Channel:
        """Return the channel designed to connect to this service."""
        return self._grpc_channel

    @property
    def create_permission(
        self,
    ) -> Callable[
        [permission_service.CreatePermissionRequest], gag_permission.Permission
    ]:
        r"""Return a callable for the create permission method over gRPC.

        Create a permission to a specific resource.

        Returns:
            Callable[[~.CreatePermissionRequest],
                    ~.Permission]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "create_permission" not in self._stubs:
            self._stubs["create_permission"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.PermissionService/CreatePermission",
                request_serializer=permission_service.CreatePermissionRequest.serialize,
                response_deserializer=gag_permission.Permission.deserialize,
            )
        return self._stubs["create_permission"]

    @property
    def get_permission(
        self,
    ) -> Callable[[permission_service.GetPermissionRequest], permission.Permission]:
        r"""Return a callable for the get permission method over gRPC.

        Gets information about a specific Permission.

        Returns:
            Callable[[~.GetPermissionRequest],
                    ~.Permission]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "get_permission" not in self._stubs:
            self._stubs["get_permission"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.PermissionService/GetPermission",
                request_serializer=permission_service.GetPermissionRequest.serialize,
                response_deserializer=permission.Permission.deserialize,
            )
        return self._stubs["get_permission"]

    @property
    def list_permissions(
        self,
    ) -> Callable[
        [permission_service.ListPermissionsRequest],
        permission_service.ListPermissionsResponse,
    ]:
        r"""Return a callable for the list permissions method over gRPC.

        Lists permissions for the specific resource.

        Returns:
            Callable[[~.ListPermissionsRequest],
                    ~.ListPermissionsResponse]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "list_permissions" not in self._stubs:
            self._stubs["list_permissions"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.PermissionService/ListPermissions",
                request_serializer=permission_service.ListPermissionsRequest.serialize,
                response_deserializer=permission_service.ListPermissionsResponse.deserialize,
            )
        return self._stubs["list_permissions"]

    @property
    def update_permission(
        self,
    ) -> Callable[
        [permission_service.UpdatePermissionRequest], gag_permission.Permission
    ]:
        r"""Return a callable for the update permission method over gRPC.

        Updates the permission.

        Returns:
            Callable[[~.UpdatePermissionRequest],
                    ~.Permission]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "update_permission" not in self._stubs:
            self._stubs["update_permission"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.PermissionService/UpdatePermission",
                request_serializer=permission_service.UpdatePermissionRequest.serialize,
                response_deserializer=gag_permission.Permission.deserialize,
            )
        return self._stubs["update_permission"]

    @property
    def delete_permission(
        self,
    ) -> Callable[[permission_service.DeletePermissionRequest], empty_pb2.Empty]:
        r"""Return a callable for the delete permission method over gRPC.

        Deletes the permission.

        Returns:
            Callable[[~.DeletePermissionRequest],
                    ~.Empty]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "delete_permission" not in self._stubs:
            self._stubs["delete_permission"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.PermissionService/DeletePermission",
                request_serializer=permission_service.DeletePermissionRequest.serialize,
                response_deserializer=empty_pb2.Empty.FromString,
            )
        return self._stubs["delete_permission"]

    @property
    def transfer_ownership(
        self,
    ) -> Callable[
        [permission_service.TransferOwnershipRequest],
        permission_service.TransferOwnershipResponse,
    ]:
        r"""Return a callable for the transfer ownership method over gRPC.

        Transfers ownership of the tuned model.
        This is the only way to change ownership of the tuned
        model. The current owner will be downgraded to writer
        role.

        Returns:
            Callable[[~.TransferOwnershipRequest],
                    ~.TransferOwnershipResponse]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "transfer_ownership" not in self._stubs:
            self._stubs["transfer_ownership"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.PermissionService/TransferOwnership",
                request_serializer=permission_service.TransferOwnershipRequest.serialize,
                response_deserializer=permission_service.TransferOwnershipResponse.deserialize,
            )
        return self._stubs["transfer_ownership"]

    def close(self):
        self.grpc_channel.close()

    @property
    def kind(self) -> str:
        return "grpc"


__all__ = ("PermissionServiceGrpcTransport",)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta3\services\permission_service\transports\grpc.py ===
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
from typing import Callable, Dict, Optional, Sequence, Tuple, Union
import warnings

from google.api_core import gapic_v1, grpc_helpers
import google.auth  # type: ignore
from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
from google.longrunning import operations_pb2  # type: ignore
from google.protobuf import empty_pb2  # type: ignore
import grpc  # type: ignore

from google.ai.generativelanguage_v1beta3.types import permission as gag_permission
from google.ai.generativelanguage_v1beta3.types import permission
from google.ai.generativelanguage_v1beta3.types import permission_service

from .base import DEFAULT_CLIENT_INFO, PermissionServiceTransport


class PermissionServiceGrpcTransport(PermissionServiceTransport):
    """gRPC backend transport for PermissionService.

    Provides methods for managing permissions to PaLM API
    resources.

    This class defines the same methods as the primary client, so the
    primary client can load the underlying transport implementation
    and call it.

    It sends protocol buffers over the wire using gRPC (which is built on
    top of HTTP/2); the ``grpcio`` package must be installed.
    """

    _stubs: Dict[str, Callable]

    def __init__(
        self,
        *,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        channel: Optional[Union[grpc.Channel, Callable[..., grpc.Channel]]] = None,
        api_mtls_endpoint: Optional[str] = None,
        client_cert_source: Optional[Callable[[], Tuple[bytes, bytes]]] = None,
        ssl_channel_credentials: Optional[grpc.ChannelCredentials] = None,
        client_cert_source_for_mtls: Optional[Callable[[], Tuple[bytes, bytes]]] = None,
        quota_project_id: Optional[str] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
        always_use_jwt_access: Optional[bool] = False,
        api_audience: Optional[str] = None,
    ) -> None:
        """Instantiate the transport.

        Args:
            host (Optional[str]):
                 The hostname to connect to (default: 'generativelanguage.googleapis.com').
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
                This argument is ignored if a ``channel`` instance is provided.
            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
                This argument is ignored if a ``channel`` instance is provided.
            scopes (Optional(Sequence[str])): A list of scopes. This argument is
                ignored if a ``channel`` instance is provided.
            channel (Optional[Union[grpc.Channel, Callable[..., grpc.Channel]]]):
                A ``Channel`` instance through which to make calls, or a Callable
                that constructs and returns one. If set to None, ``self.create_channel``
                is used to create the channel. If a Callable is given, it will be called
                with the same arguments as used in ``self.create_channel``.
            api_mtls_endpoint (Optional[str]): Deprecated. The mutual TLS endpoint.
                If provided, it overrides the ``host`` argument and tries to create
                a mutual TLS channel with client SSL credentials from
                ``client_cert_source`` or application default SSL credentials.
            client_cert_source (Optional[Callable[[], Tuple[bytes, bytes]]]):
                Deprecated. A callback to provide client SSL certificate bytes and
                private key bytes, both in PEM format. It is ignored if
                ``api_mtls_endpoint`` is None.
            ssl_channel_credentials (grpc.ChannelCredentials): SSL credentials
                for the grpc channel. It is ignored if a ``channel`` instance is provided.
            client_cert_source_for_mtls (Optional[Callable[[], Tuple[bytes, bytes]]]):
                A callback to provide client certificate bytes and private key bytes,
                both in PEM format. It is used to configure a mutual TLS channel. It is
                ignored if a ``channel`` instance or ``ssl_channel_credentials`` is provided.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you're developing
                your own client library.
            always_use_jwt_access (Optional[bool]): Whether self signed JWT should
                be used for service account credentials.

        Raises:
          google.auth.exceptions.MutualTLSChannelError: If mutual TLS transport
              creation failed for any reason.
          google.api_core.exceptions.DuplicateCredentialArgs: If both ``credentials``
              and ``credentials_file`` are passed.
        """
        self._grpc_channel = None
        self._ssl_channel_credentials = ssl_channel_credentials
        self._stubs: Dict[str, Callable] = {}

        if api_mtls_endpoint:
            warnings.warn("api_mtls_endpoint is deprecated", DeprecationWarning)
        if client_cert_source:
            warnings.warn("client_cert_source is deprecated", DeprecationWarning)

        if isinstance(channel, grpc.Channel):
            # Ignore credentials if a channel was passed.
            credentials = False
            # If a channel was explicitly provided, set it.
            self._grpc_channel = channel
            self._ssl_channel_credentials = None

        else:
            if api_mtls_endpoint:
                host = api_mtls_endpoint

                # Create SSL credentials with client_cert_source or application
                # default SSL credentials.
                if client_cert_source:
                    cert, key = client_cert_source()
                    self._ssl_channel_credentials = grpc.ssl_channel_credentials(
                        certificate_chain=cert, private_key=key
                    )
                else:
                    self._ssl_channel_credentials = SslCredentials().ssl_credentials

            else:
                if client_cert_source_for_mtls and not ssl_channel_credentials:
                    cert, key = client_cert_source_for_mtls()
                    self._ssl_channel_credentials = grpc.ssl_channel_credentials(
                        certificate_chain=cert, private_key=key
                    )

        # The base transport sets the host, credentials and scopes
        super().__init__(
            host=host,
            credentials=credentials,
            credentials_file=credentials_file,
            scopes=scopes,
            quota_project_id=quota_project_id,
            client_info=client_info,
            always_use_jwt_access=always_use_jwt_access,
            api_audience=api_audience,
        )

        if not self._grpc_channel:
            # initialize with the provided callable or the default channel
            channel_init = channel or type(self).create_channel
            self._grpc_channel = channel_init(
                self._host,
                # use the credentials which are saved
                credentials=self._credentials,
                # Set ``credentials_file`` to ``None`` here as
                # the credentials that we saved earlier should be used.
                credentials_file=None,
                scopes=self._scopes,
                ssl_credentials=self._ssl_channel_credentials,
                quota_project_id=quota_project_id,
                options=[
                    ("grpc.max_send_message_length", -1),
                    ("grpc.max_receive_message_length", -1),
                ],
            )

        # Wrap messages. This must be done after self._grpc_channel exists
        self._prep_wrapped_messages(client_info)

    @classmethod
    def create_channel(
        cls,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        quota_project_id: Optional[str] = None,
        **kwargs,
    ) -> grpc.Channel:
        """Create and return a gRPC channel object.
        Args:
            host (Optional[str]): The host for the channel to use.
            credentials (Optional[~.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify this application to the service. If
                none are specified, the client will attempt to ascertain
                the credentials from the environment.
            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
                This argument is mutually exclusive with credentials.
            scopes (Optional[Sequence[str]]): A optional list of scopes needed for this
                service. These are only used when credentials are not specified and
                are passed to :func:`google.auth.default`.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            kwargs (Optional[dict]): Keyword arguments, which are passed to the
                channel creation.
        Returns:
            grpc.Channel: A gRPC channel object.

        Raises:
            google.api_core.exceptions.DuplicateCredentialArgs: If both ``credentials``
              and ``credentials_file`` are passed.
        """

        return grpc_helpers.create_channel(
            host,
            credentials=credentials,
            credentials_file=credentials_file,
            quota_project_id=quota_project_id,
            default_scopes=cls.AUTH_SCOPES,
            scopes=scopes,
            default_host=cls.DEFAULT_HOST,
            **kwargs,
        )

    @property
    def grpc_channel(self) -> grpc.Channel:
        """Return the channel designed to connect to this service."""
        return self._grpc_channel

    @property
    def create_permission(
        self,
    ) -> Callable[
        [permission_service.CreatePermissionRequest], gag_permission.Permission
    ]:
        r"""Return a callable for the create permission method over gRPC.

        Create a permission to a specific resource.

        Returns:
            Callable[[~.CreatePermissionRequest],
                    ~.Permission]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "create_permission" not in self._stubs:
            self._stubs["create_permission"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta3.PermissionService/CreatePermission",
                request_serializer=permission_service.CreatePermissionRequest.serialize,
                response_deserializer=gag_permission.Permission.deserialize,
            )
        return self._stubs["create_permission"]

    @property
    def get_permission(
        self,
    ) -> Callable[[permission_service.GetPermissionRequest], permission.Permission]:
        r"""Return a callable for the get permission method over gRPC.

        Gets information about a specific Permission.

        Returns:
            Callable[[~.GetPermissionRequest],
                    ~.Permission]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "get_permission" not in self._stubs:
            self._stubs["get_permission"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta3.PermissionService/GetPermission",
                request_serializer=permission_service.GetPermissionRequest.serialize,
                response_deserializer=permission.Permission.deserialize,
            )
        return self._stubs["get_permission"]

    @property
    def list_permissions(
        self,
    ) -> Callable[
        [permission_service.ListPermissionsRequest],
        permission_service.ListPermissionsResponse,
    ]:
        r"""Return a callable for the list permissions method over gRPC.

        Lists permissions for the specific resource.

        Returns:
            Callable[[~.ListPermissionsRequest],
                    ~.ListPermissionsResponse]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "list_permissions" not in self._stubs:
            self._stubs["list_permissions"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta3.PermissionService/ListPermissions",
                request_serializer=permission_service.ListPermissionsRequest.serialize,
                response_deserializer=permission_service.ListPermissionsResponse.deserialize,
            )
        return self._stubs["list_permissions"]

    @property
    def update_permission(
        self,
    ) -> Callable[
        [permission_service.UpdatePermissionRequest], gag_permission.Permission
    ]:
        r"""Return a callable for the update permission method over gRPC.

        Updates the permission.

        Returns:
            Callable[[~.UpdatePermissionRequest],
                    ~.Permission]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "update_permission" not in self._stubs:
            self._stubs["update_permission"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta3.PermissionService/UpdatePermission",
                request_serializer=permission_service.UpdatePermissionRequest.serialize,
                response_deserializer=gag_permission.Permission.deserialize,
            )
        return self._stubs["update_permission"]

    @property
    def delete_permission(
        self,
    ) -> Callable[[permission_service.DeletePermissionRequest], empty_pb2.Empty]:
        r"""Return a callable for the delete permission method over gRPC.

        Deletes the permission.

        Returns:
            Callable[[~.DeletePermissionRequest],
                    ~.Empty]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "delete_permission" not in self._stubs:
            self._stubs["delete_permission"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta3.PermissionService/DeletePermission",
                request_serializer=permission_service.DeletePermissionRequest.serialize,
                response_deserializer=empty_pb2.Empty.FromString,
            )
        return self._stubs["delete_permission"]

    @property
    def transfer_ownership(
        self,
    ) -> Callable[
        [permission_service.TransferOwnershipRequest],
        permission_service.TransferOwnershipResponse,
    ]:
        r"""Return a callable for the transfer ownership method over gRPC.

        Transfers ownership of the tuned model.
        This is the only way to change ownership of the tuned
        model. The current owner will be downgraded to writer
        role.

        Returns:
            Callable[[~.TransferOwnershipRequest],
                    ~.TransferOwnershipResponse]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "transfer_ownership" not in self._stubs:
            self._stubs["transfer_ownership"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta3.PermissionService/TransferOwnership",
                request_serializer=permission_service.TransferOwnershipRequest.serialize,
                response_deserializer=permission_service.TransferOwnershipResponse.deserialize,
            )
        return self._stubs["transfer_ownership"]

    def close(self):
        self.grpc_channel.close()

    @property
    def kind(self) -> str:
        return "grpc"


__all__ = ("PermissionServiceGrpcTransport",)

# === NexusCore/openenv\Lib\site-packages\nltk\tbl\demo.py ===
# Natural Language Toolkit: Transformation-based learning
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Marcus Uneson <marcus.uneson@gmail.com>
#   based on previous (nltk2) version by
#   Christopher Maloof, Edward Loper, Steven Bird
# URL: <https://www.nltk.org/>
# For license information, see  LICENSE.TXT

import os
import pickle
import random
import time

from nltk.corpus import treebank
from nltk.tag import BrillTaggerTrainer, RegexpTagger, UnigramTagger
from nltk.tag.brill import Pos, Word
from nltk.tbl import Template, error_list


def demo():
    """
    Run a demo with defaults. See source comments for details,
    or docstrings of any of the more specific demo_* functions.
    """
    postag()


def demo_repr_rule_format():
    """
    Exemplify repr(Rule) (see also str(Rule) and Rule.format("verbose"))
    """
    postag(ruleformat="repr")


def demo_str_rule_format():
    """
    Exemplify repr(Rule) (see also str(Rule) and Rule.format("verbose"))
    """
    postag(ruleformat="str")


def demo_verbose_rule_format():
    """
    Exemplify Rule.format("verbose")
    """
    postag(ruleformat="verbose")


def demo_multiposition_feature():
    """
    The feature/s of a template takes a list of positions
    relative to the current word where the feature should be
    looked for, conceptually joined by logical OR. For instance,
    Pos([-1, 1]), given a value V, will hold whenever V is found
    one step to the left and/or one step to the right.

    For contiguous ranges, a 2-arg form giving inclusive end
    points can also be used: Pos(-3, -1) is the same as the arg
    below.
    """
    postag(templates=[Template(Pos([-3, -2, -1]))])


def demo_multifeature_template():
    """
    Templates can have more than a single feature.
    """
    postag(templates=[Template(Word([0]), Pos([-2, -1]))])


def demo_template_statistics():
    """
    Show aggregate statistics per template. Little used templates are
    candidates for deletion, much used templates may possibly be refined.

    Deleting unused templates is mostly about saving time and/or space:
    training is basically O(T) in the number of templates T
    (also in terms of memory usage, which often will be the limiting factor).
    """
    postag(incremental_stats=True, template_stats=True)


def demo_generated_templates():
    """
    Template.expand and Feature.expand are class methods facilitating
    generating large amounts of templates. See their documentation for
    details.

    Note: training with 500 templates can easily fill all available
    even on relatively small corpora
    """
    wordtpls = Word.expand([-1, 0, 1], [1, 2], excludezero=False)
    tagtpls = Pos.expand([-2, -1, 0, 1], [1, 2], excludezero=True)
    templates = list(Template.expand([wordtpls, tagtpls], combinations=(1, 3)))
    print(
        "Generated {} templates for transformation-based learning".format(
            len(templates)
        )
    )
    postag(templates=templates, incremental_stats=True, template_stats=True)


def demo_learning_curve():
    """
    Plot a learning curve -- the contribution on tagging accuracy of
    the individual rules.
    Note: requires matplotlib
    """
    postag(
        incremental_stats=True,
        separate_baseline_data=True,
        learning_curve_output="learningcurve.png",
    )


def demo_error_analysis():
    """
    Writes a file with context for each erroneous word after tagging testing data
    """
    postag(error_output="errors.txt")


def demo_serialize_tagger():
    """
    Serializes the learned tagger to a file in pickle format; reloads it
    and validates the process.
    """
    postag(serialize_output="tagger.pcl")


def demo_high_accuracy_rules():
    """
    Discard rules with low accuracy. This may hurt performance a bit,
    but will often produce rules which are more interesting read to a human.
    """
    postag(num_sents=3000, min_acc=0.96, min_score=10)


def postag(
    templates=None,
    tagged_data=None,
    num_sents=1000,
    max_rules=300,
    min_score=3,
    min_acc=None,
    train=0.8,
    trace=3,
    randomize=False,
    ruleformat="str",
    incremental_stats=False,
    template_stats=False,
    error_output=None,
    serialize_output=None,
    learning_curve_output=None,
    learning_curve_take=300,
    baseline_backoff_tagger=None,
    separate_baseline_data=False,
    cache_baseline_tagger=None,
):
    """
    Brill Tagger Demonstration
    :param templates: how many sentences of training and testing data to use
    :type templates: list of Template

    :param tagged_data: maximum number of rule instances to create
    :type tagged_data: C{int}

    :param num_sents: how many sentences of training and testing data to use
    :type num_sents: C{int}

    :param max_rules: maximum number of rule instances to create
    :type max_rules: C{int}

    :param min_score: the minimum score for a rule in order for it to be considered
    :type min_score: C{int}

    :param min_acc: the minimum score for a rule in order for it to be considered
    :type min_acc: C{float}

    :param train: the fraction of the the corpus to be used for training (1=all)
    :type train: C{float}

    :param trace: the level of diagnostic tracing output to produce (0-4)
    :type trace: C{int}

    :param randomize: whether the training data should be a random subset of the corpus
    :type randomize: C{bool}

    :param ruleformat: rule output format, one of "str", "repr", "verbose"
    :type ruleformat: C{str}

    :param incremental_stats: if true, will tag incrementally and collect stats for each rule (rather slow)
    :type incremental_stats: C{bool}

    :param template_stats: if true, will print per-template statistics collected in training and (optionally) testing
    :type template_stats: C{bool}

    :param error_output: the file where errors will be saved
    :type error_output: C{string}

    :param serialize_output: the file where the learned tbl tagger will be saved
    :type serialize_output: C{string}

    :param learning_curve_output: filename of plot of learning curve(s) (train and also test, if available)
    :type learning_curve_output: C{string}

    :param learning_curve_take: how many rules plotted
    :type learning_curve_take: C{int}

    :param baseline_backoff_tagger: the file where rules will be saved
    :type baseline_backoff_tagger: tagger

    :param separate_baseline_data: use a fraction of the training data exclusively for training baseline
    :type separate_baseline_data: C{bool}

    :param cache_baseline_tagger: cache baseline tagger to this file (only interesting as a temporary workaround to get
                                  deterministic output from the baseline unigram tagger between python versions)
    :type cache_baseline_tagger: C{string}


    Note on separate_baseline_data: if True, reuse training data both for baseline and rule learner. This
    is fast and fine for a demo, but is likely to generalize worse on unseen data.
    Also cannot be sensibly used for learning curves on training data (the baseline will be artificially high).
    """

    # defaults
    baseline_backoff_tagger = baseline_backoff_tagger or REGEXP_TAGGER
    if templates is None:
        from nltk.tag.brill import brill24, describe_template_sets

        # some pre-built template sets taken from typical systems or publications are
        # available. Print a list with describe_template_sets()
        # for instance:
        templates = brill24()
    (training_data, baseline_data, gold_data, testing_data) = _demo_prepare_data(
        tagged_data, train, num_sents, randomize, separate_baseline_data
    )

    # creating (or reloading from cache) a baseline tagger (unigram tagger)
    # this is just a mechanism for getting deterministic output from the baseline between
    # python versions
    if cache_baseline_tagger:
        if not os.path.exists(cache_baseline_tagger):
            baseline_tagger = UnigramTagger(
                baseline_data, backoff=baseline_backoff_tagger
            )
            with open(cache_baseline_tagger, "w") as print_rules:
                pickle.dump(baseline_tagger, print_rules)
            print(
                "Trained baseline tagger, pickled it to {}".format(
                    cache_baseline_tagger
                )
            )
        with open(cache_baseline_tagger) as print_rules:
            baseline_tagger = pickle.load(print_rules)
            print(f"Reloaded pickled tagger from {cache_baseline_tagger}")
    else:
        baseline_tagger = UnigramTagger(baseline_data, backoff=baseline_backoff_tagger)
        print("Trained baseline tagger")
    if gold_data:
        print(
            "    Accuracy on test set: {:0.4f}".format(
                baseline_tagger.accuracy(gold_data)
            )
        )

    # creating a Brill tagger
    tbrill = time.time()
    trainer = BrillTaggerTrainer(
        baseline_tagger, templates, trace, ruleformat=ruleformat
    )
    print("Training tbl tagger...")
    brill_tagger = trainer.train(training_data, max_rules, min_score, min_acc)
    print(f"Trained tbl tagger in {time.time() - tbrill:0.2f} seconds")
    if gold_data:
        print("    Accuracy on test set: %.4f" % brill_tagger.accuracy(gold_data))

    # printing the learned rules, if learned silently
    if trace == 1:
        print("\nLearned rules: ")
        for ruleno, rule in enumerate(brill_tagger.rules(), 1):
            print(f"{ruleno:4d} {rule.format(ruleformat):s}")

    # printing template statistics (optionally including comparison with the training data)
    # note: if not separate_baseline_data, then baseline accuracy will be artificially high
    if incremental_stats:
        print(
            "Incrementally tagging the test data, collecting individual rule statistics"
        )
        (taggedtest, teststats) = brill_tagger.batch_tag_incremental(
            testing_data, gold_data
        )
        print("    Rule statistics collected")
        if not separate_baseline_data:
            print(
                "WARNING: train_stats asked for separate_baseline_data=True; the baseline "
                "will be artificially high"
            )
        trainstats = brill_tagger.train_stats()
        if template_stats:
            brill_tagger.print_template_statistics(teststats)
        if learning_curve_output:
            _demo_plot(
                learning_curve_output, teststats, trainstats, take=learning_curve_take
            )
            print(f"Wrote plot of learning curve to {learning_curve_output}")
    else:
        print("Tagging the test data")
        taggedtest = brill_tagger.tag_sents(testing_data)
        if template_stats:
            brill_tagger.print_template_statistics()

    # writing error analysis to file
    if error_output is not None:
        with open(error_output, "w") as f:
            f.write("Errors for Brill Tagger %r\n\n" % serialize_output)
            f.write("\n".join(error_list(gold_data, taggedtest)).encode("utf-8") + "\n")
        print(f"Wrote tagger errors including context to {error_output}")

    # serializing the tagger to a pickle file and reloading (just to see it works)
    if serialize_output is not None:
        taggedtest = brill_tagger.tag_sents(testing_data)
        with open(serialize_output, "w") as print_rules:
            pickle.dump(brill_tagger, print_rules)
        print(f"Wrote pickled tagger to {serialize_output}")
        with open(serialize_output) as print_rules:
            brill_tagger_reloaded = pickle.load(print_rules)
        print(f"Reloaded pickled tagger from {serialize_output}")
        taggedtest_reloaded = brill_tagger.tag_sents(testing_data)
        if taggedtest == taggedtest_reloaded:
            print("Reloaded tagger tried on test set, results identical")
        else:
            print("PROBLEM: Reloaded tagger gave different results on test set")


def _demo_prepare_data(
    tagged_data, train, num_sents, randomize, separate_baseline_data
):
    # train is the proportion of data used in training; the rest is reserved
    # for testing.
    if tagged_data is None:
        print("Loading tagged data from treebank... ")
        tagged_data = treebank.tagged_sents()
    if num_sents is None or len(tagged_data) <= num_sents:
        num_sents = len(tagged_data)
    if randomize:
        random.seed(len(tagged_data))
        random.shuffle(tagged_data)
    cutoff = int(num_sents * train)
    training_data = tagged_data[:cutoff]
    gold_data = tagged_data[cutoff:num_sents]
    testing_data = [[t[0] for t in sent] for sent in gold_data]
    if not separate_baseline_data:
        baseline_data = training_data
    else:
        bl_cutoff = len(training_data) // 3
        (baseline_data, training_data) = (
            training_data[:bl_cutoff],
            training_data[bl_cutoff:],
        )
    (trainseqs, traintokens) = corpus_size(training_data)
    (testseqs, testtokens) = corpus_size(testing_data)
    (bltrainseqs, bltraintokens) = corpus_size(baseline_data)
    print(f"Read testing data ({testseqs:d} sents/{testtokens:d} wds)")
    print(f"Read training data ({trainseqs:d} sents/{traintokens:d} wds)")
    print(
        "Read baseline data ({:d} sents/{:d} wds) {:s}".format(
            bltrainseqs,
            bltraintokens,
            "" if separate_baseline_data else "[reused the training set]",
        )
    )
    return (training_data, baseline_data, gold_data, testing_data)


def _demo_plot(learning_curve_output, teststats, trainstats=None, take=None):
    testcurve = [teststats["initialerrors"]]
    for rulescore in teststats["rulescores"]:
        testcurve.append(testcurve[-1] - rulescore)
    testcurve = [1 - x / teststats["tokencount"] for x in testcurve[:take]]

    traincurve = [trainstats["initialerrors"]]
    for rulescore in trainstats["rulescores"]:
        traincurve.append(traincurve[-1] - rulescore)
    traincurve = [1 - x / trainstats["tokencount"] for x in traincurve[:take]]

    import matplotlib.pyplot as plt

    r = list(range(len(testcurve)))
    plt.plot(r, testcurve, r, traincurve)
    plt.axis([None, None, None, 1.0])
    plt.savefig(learning_curve_output)


NN_CD_TAGGER = RegexpTagger([(r"^-?[0-9]+(\.[0-9]+)?$", "CD"), (r".*", "NN")])

REGEXP_TAGGER = RegexpTagger(
    [
        (r"^-?[0-9]+(\.[0-9]+)?$", "CD"),  # cardinal numbers
        (r"(The|the|A|a|An|an)$", "AT"),  # articles
        (r".*able$", "JJ"),  # adjectives
        (r".*ness$", "NN"),  # nouns formed from adjectives
        (r".*ly$", "RB"),  # adverbs
        (r".*s$", "NNS"),  # plural nouns
        (r".*ing$", "VBG"),  # gerunds
        (r".*ed$", "VBD"),  # past tense verbs
        (r".*", "NN"),  # nouns (default)
    ]
)


def corpus_size(seqs):
    return (len(seqs), sum(len(x) for x in seqs))


if __name__ == "__main__":
    demo_learning_curve()

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v135\profiler.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Profiler
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import debugger
from . import runtime


@dataclass
class ProfileNode:
    '''
    Profile node. Holds callsite information, execution statistics and child nodes.
    '''
    #: Unique id of the node.
    id_: int

    #: Function location.
    call_frame: runtime.CallFrame

    #: Number of samples where this node was on top of the call stack.
    hit_count: typing.Optional[int] = None

    #: Child node ids.
    children: typing.Optional[typing.List[int]] = None

    #: The reason of being not optimized. The function may be deoptimized or marked as don't
    #: optimize.
    deopt_reason: typing.Optional[str] = None

    #: An array of source position ticks.
    position_ticks: typing.Optional[typing.List[PositionTickInfo]] = None

    def to_json(self):
        json = dict()
        json['id'] = self.id_
        json['callFrame'] = self.call_frame.to_json()
        if self.hit_count is not None:
            json['hitCount'] = self.hit_count
        if self.children is not None:
            json['children'] = [i for i in self.children]
        if self.deopt_reason is not None:
            json['deoptReason'] = self.deopt_reason
        if self.position_ticks is not None:
            json['positionTicks'] = [i.to_json() for i in self.position_ticks]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            id_=int(json['id']),
            call_frame=runtime.CallFrame.from_json(json['callFrame']),
            hit_count=int(json['hitCount']) if 'hitCount' in json else None,
            children=[int(i) for i in json['children']] if 'children' in json else None,
            deopt_reason=str(json['deoptReason']) if 'deoptReason' in json else None,
            position_ticks=[PositionTickInfo.from_json(i) for i in json['positionTicks']] if 'positionTicks' in json else None,
        )


@dataclass
class Profile:
    '''
    Profile.
    '''
    #: The list of profile nodes. First item is the root node.
    nodes: typing.List[ProfileNode]

    #: Profiling start timestamp in microseconds.
    start_time: float

    #: Profiling end timestamp in microseconds.
    end_time: float

    #: Ids of samples top nodes.
    samples: typing.Optional[typing.List[int]] = None

    #: Time intervals between adjacent samples in microseconds. The first delta is relative to the
    #: profile startTime.
    time_deltas: typing.Optional[typing.List[int]] = None

    def to_json(self):
        json = dict()
        json['nodes'] = [i.to_json() for i in self.nodes]
        json['startTime'] = self.start_time
        json['endTime'] = self.end_time
        if self.samples is not None:
            json['samples'] = [i for i in self.samples]
        if self.time_deltas is not None:
            json['timeDeltas'] = [i for i in self.time_deltas]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            nodes=[ProfileNode.from_json(i) for i in json['nodes']],
            start_time=float(json['startTime']),
            end_time=float(json['endTime']),
            samples=[int(i) for i in json['samples']] if 'samples' in json else None,
            time_deltas=[int(i) for i in json['timeDeltas']] if 'timeDeltas' in json else None,
        )


@dataclass
class PositionTickInfo:
    '''
    Specifies a number of samples attributed to a certain source position.
    '''
    #: Source line number (1-based).
    line: int

    #: Number of samples attributed to the source line.
    ticks: int

    def to_json(self):
        json = dict()
        json['line'] = self.line
        json['ticks'] = self.ticks
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            line=int(json['line']),
            ticks=int(json['ticks']),
        )


@dataclass
class CoverageRange:
    '''
    Coverage data for a source range.
    '''
    #: JavaScript script source offset for the range start.
    start_offset: int

    #: JavaScript script source offset for the range end.
    end_offset: int

    #: Collected execution count of the source range.
    count: int

    def to_json(self):
        json = dict()
        json['startOffset'] = self.start_offset
        json['endOffset'] = self.end_offset
        json['count'] = self.count
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            start_offset=int(json['startOffset']),
            end_offset=int(json['endOffset']),
            count=int(json['count']),
        )


@dataclass
class FunctionCoverage:
    '''
    Coverage data for a JavaScript function.
    '''
    #: JavaScript function name.
    function_name: str

    #: Source ranges inside the function with coverage data.
    ranges: typing.List[CoverageRange]

    #: Whether coverage data for this function has block granularity.
    is_block_coverage: bool

    def to_json(self):
        json = dict()
        json['functionName'] = self.function_name
        json['ranges'] = [i.to_json() for i in self.ranges]
        json['isBlockCoverage'] = self.is_block_coverage
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            function_name=str(json['functionName']),
            ranges=[CoverageRange.from_json(i) for i in json['ranges']],
            is_block_coverage=bool(json['isBlockCoverage']),
        )


@dataclass
class ScriptCoverage:
    '''
    Coverage data for a JavaScript script.
    '''
    #: JavaScript script id.
    script_id: runtime.ScriptId

    #: JavaScript script name or url.
    url: str

    #: Functions contained in the script that has coverage data.
    functions: typing.List[FunctionCoverage]

    def to_json(self):
        json = dict()
        json['scriptId'] = self.script_id.to_json()
        json['url'] = self.url
        json['functions'] = [i.to_json() for i in self.functions]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            script_id=runtime.ScriptId.from_json(json['scriptId']),
            url=str(json['url']),
            functions=[FunctionCoverage.from_json(i) for i in json['functions']],
        )


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:

    cmd_dict: T_JSON_DICT = {
        'method': 'Profiler.disable',
    }
    json = yield cmd_dict


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:

    cmd_dict: T_JSON_DICT = {
        'method': 'Profiler.enable',
    }
    json = yield cmd_dict


def get_best_effort_coverage() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[ScriptCoverage]]:
    '''
    Collect coverage data for the current isolate. The coverage data may be incomplete due to
    garbage collection.

    :returns: Coverage data for the current isolate.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Profiler.getBestEffortCoverage',
    }
    json = yield cmd_dict
    return [ScriptCoverage.from_json(i) for i in json['result']]


def set_sampling_interval(
        interval: int
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Changes CPU profiler sampling interval. Must be called before CPU profiles recording started.

    :param interval: New sampling interval in microseconds.
    '''
    params: T_JSON_DICT = dict()
    params['interval'] = interval
    cmd_dict: T_JSON_DICT = {
        'method': 'Profiler.setSamplingInterval',
        'params': params,
    }
    json = yield cmd_dict


def start() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:

    cmd_dict: T_JSON_DICT = {
        'method': 'Profiler.start',
    }
    json = yield cmd_dict


def start_precise_coverage(
        call_count: typing.Optional[bool] = None,
        detailed: typing.Optional[bool] = None,
        allow_triggered_updates: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,float]:
    '''
    Enable precise code coverage. Coverage data for JavaScript executed before enabling precise code
    coverage may be incomplete. Enabling prevents running optimized code and resets execution
    counters.

    :param call_count: *(Optional)* Collect accurate call counts beyond simple 'covered' or 'not covered'.
    :param detailed: *(Optional)* Collect block-based coverage.
    :param allow_triggered_updates: *(Optional)* Allow the backend to send updates on its own initiative
    :returns: Monotonically increasing time (in seconds) when the coverage update was taken in the backend.
    '''
    params: T_JSON_DICT = dict()
    if call_count is not None:
        params['callCount'] = call_count
    if detailed is not None:
        params['detailed'] = detailed
    if allow_triggered_updates is not None:
        params['allowTriggeredUpdates'] = allow_triggered_updates
    cmd_dict: T_JSON_DICT = {
        'method': 'Profiler.startPreciseCoverage',
        'params': params,
    }
    json = yield cmd_dict
    return float(json['timestamp'])


def stop() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,Profile]:
    '''


    :returns: Recorded profile.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Profiler.stop',
    }
    json = yield cmd_dict
    return Profile.from_json(json['profile'])


def stop_precise_coverage() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disable precise code coverage. Disabling releases unnecessary execution count records and allows
    executing optimized code.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Profiler.stopPreciseCoverage',
    }
    json = yield cmd_dict


def take_precise_coverage() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[typing.List[ScriptCoverage], float]]:
    '''
    Collect coverage data for the current isolate, and resets execution counters. Precise code
    coverage needs to have started.

    :returns: A tuple with the following items:

        0. **result** - Coverage data for the current isolate.
        1. **timestamp** - Monotonically increasing time (in seconds) when the coverage update was taken in the backend.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Profiler.takePreciseCoverage',
    }
    json = yield cmd_dict
    return (
        [ScriptCoverage.from_json(i) for i in json['result']],
        float(json['timestamp'])
    )


@event_class('Profiler.consoleProfileFinished')
@dataclass
class ConsoleProfileFinished:
    id_: str
    #: Location of console.profileEnd().
    location: debugger.Location
    profile: Profile
    #: Profile title passed as an argument to console.profile().
    title: typing.Optional[str]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ConsoleProfileFinished:
        return cls(
            id_=str(json['id']),
            location=debugger.Location.from_json(json['location']),
            profile=Profile.from_json(json['profile']),
            title=str(json['title']) if 'title' in json else None
        )


@event_class('Profiler.consoleProfileStarted')
@dataclass
class ConsoleProfileStarted:
    '''
    Sent when new profile recording is started using console.profile() call.
    '''
    id_: str
    #: Location of console.profile().
    location: debugger.Location
    #: Profile title passed as an argument to console.profile().
    title: typing.Optional[str]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ConsoleProfileStarted:
        return cls(
            id_=str(json['id']),
            location=debugger.Location.from_json(json['location']),
            title=str(json['title']) if 'title' in json else None
        )


@event_class('Profiler.preciseCoverageDeltaUpdate')
@dataclass
class PreciseCoverageDeltaUpdate:
    '''
    **EXPERIMENTAL**

    Reports coverage delta since the last poll (either from an event like this, or from
    ``takePreciseCoverage`` for the current isolate. May only be sent if precise code
    coverage has been started. This event can be trigged by the embedder to, for example,
    trigger collection of coverage data immediately at a certain point in time.
    '''
    #: Monotonically increasing time (in seconds) when the coverage update was taken in the backend.
    timestamp: float
    #: Identifier for distinguishing coverage events.
    occasion: str
    #: Coverage data for the current isolate.
    result: typing.List[ScriptCoverage]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> PreciseCoverageDeltaUpdate:
        return cls(
            timestamp=float(json['timestamp']),
            occasion=str(json['occasion']),
            result=[ScriptCoverage.from_json(i) for i in json['result']]
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v136\profiler.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Profiler
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import debugger
from . import runtime


@dataclass
class ProfileNode:
    '''
    Profile node. Holds callsite information, execution statistics and child nodes.
    '''
    #: Unique id of the node.
    id_: int

    #: Function location.
    call_frame: runtime.CallFrame

    #: Number of samples where this node was on top of the call stack.
    hit_count: typing.Optional[int] = None

    #: Child node ids.
    children: typing.Optional[typing.List[int]] = None

    #: The reason of being not optimized. The function may be deoptimized or marked as don't
    #: optimize.
    deopt_reason: typing.Optional[str] = None

    #: An array of source position ticks.
    position_ticks: typing.Optional[typing.List[PositionTickInfo]] = None

    def to_json(self):
        json = dict()
        json['id'] = self.id_
        json['callFrame'] = self.call_frame.to_json()
        if self.hit_count is not None:
            json['hitCount'] = self.hit_count
        if self.children is not None:
            json['children'] = [i for i in self.children]
        if self.deopt_reason is not None:
            json['deoptReason'] = self.deopt_reason
        if self.position_ticks is not None:
            json['positionTicks'] = [i.to_json() for i in self.position_ticks]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            id_=int(json['id']),
            call_frame=runtime.CallFrame.from_json(json['callFrame']),
            hit_count=int(json['hitCount']) if 'hitCount' in json else None,
            children=[int(i) for i in json['children']] if 'children' in json else None,
            deopt_reason=str(json['deoptReason']) if 'deoptReason' in json else None,
            position_ticks=[PositionTickInfo.from_json(i) for i in json['positionTicks']] if 'positionTicks' in json else None,
        )


@dataclass
class Profile:
    '''
    Profile.
    '''
    #: The list of profile nodes. First item is the root node.
    nodes: typing.List[ProfileNode]

    #: Profiling start timestamp in microseconds.
    start_time: float

    #: Profiling end timestamp in microseconds.
    end_time: float

    #: Ids of samples top nodes.
    samples: typing.Optional[typing.List[int]] = None

    #: Time intervals between adjacent samples in microseconds. The first delta is relative to the
    #: profile startTime.
    time_deltas: typing.Optional[typing.List[int]] = None

    def to_json(self):
        json = dict()
        json['nodes'] = [i.to_json() for i in self.nodes]
        json['startTime'] = self.start_time
        json['endTime'] = self.end_time
        if self.samples is not None:
            json['samples'] = [i for i in self.samples]
        if self.time_deltas is not None:
            json['timeDeltas'] = [i for i in self.time_deltas]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            nodes=[ProfileNode.from_json(i) for i in json['nodes']],
            start_time=float(json['startTime']),
            end_time=float(json['endTime']),
            samples=[int(i) for i in json['samples']] if 'samples' in json else None,
            time_deltas=[int(i) for i in json['timeDeltas']] if 'timeDeltas' in json else None,
        )


@dataclass
class PositionTickInfo:
    '''
    Specifies a number of samples attributed to a certain source position.
    '''
    #: Source line number (1-based).
    line: int

    #: Number of samples attributed to the source line.
    ticks: int

    def to_json(self):
        json = dict()
        json['line'] = self.line
        json['ticks'] = self.ticks
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            line=int(json['line']),
            ticks=int(json['ticks']),
        )


@dataclass
class CoverageRange:
    '''
    Coverage data for a source range.
    '''
    #: JavaScript script source offset for the range start.
    start_offset: int

    #: JavaScript script source offset for the range end.
    end_offset: int

    #: Collected execution count of the source range.
    count: int

    def to_json(self):
        json = dict()
        json['startOffset'] = self.start_offset
        json['endOffset'] = self.end_offset
        json['count'] = self.count
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            start_offset=int(json['startOffset']),
            end_offset=int(json['endOffset']),
            count=int(json['count']),
        )


@dataclass
class FunctionCoverage:
    '''
    Coverage data for a JavaScript function.
    '''
    #: JavaScript function name.
    function_name: str

    #: Source ranges inside the function with coverage data.
    ranges: typing.List[CoverageRange]

    #: Whether coverage data for this function has block granularity.
    is_block_coverage: bool

    def to_json(self):
        json = dict()
        json['functionName'] = self.function_name
        json['ranges'] = [i.to_json() for i in self.ranges]
        json['isBlockCoverage'] = self.is_block_coverage
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            function_name=str(json['functionName']),
            ranges=[CoverageRange.from_json(i) for i in json['ranges']],
            is_block_coverage=bool(json['isBlockCoverage']),
        )


@dataclass
class ScriptCoverage:
    '''
    Coverage data for a JavaScript script.
    '''
    #: JavaScript script id.
    script_id: runtime.ScriptId

    #: JavaScript script name or url.
    url: str

    #: Functions contained in the script that has coverage data.
    functions: typing.List[FunctionCoverage]

    def to_json(self):
        json = dict()
        json['scriptId'] = self.script_id.to_json()
        json['url'] = self.url
        json['functions'] = [i.to_json() for i in self.functions]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            script_id=runtime.ScriptId.from_json(json['scriptId']),
            url=str(json['url']),
            functions=[FunctionCoverage.from_json(i) for i in json['functions']],
        )


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:

    cmd_dict: T_JSON_DICT = {
        'method': 'Profiler.disable',
    }
    json = yield cmd_dict


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:

    cmd_dict: T_JSON_DICT = {
        'method': 'Profiler.enable',
    }
    json = yield cmd_dict


def get_best_effort_coverage() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[ScriptCoverage]]:
    '''
    Collect coverage data for the current isolate. The coverage data may be incomplete due to
    garbage collection.

    :returns: Coverage data for the current isolate.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Profiler.getBestEffortCoverage',
    }
    json = yield cmd_dict
    return [ScriptCoverage.from_json(i) for i in json['result']]


def set_sampling_interval(
        interval: int
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Changes CPU profiler sampling interval. Must be called before CPU profiles recording started.

    :param interval: New sampling interval in microseconds.
    '''
    params: T_JSON_DICT = dict()
    params['interval'] = interval
    cmd_dict: T_JSON_DICT = {
        'method': 'Profiler.setSamplingInterval',
        'params': params,
    }
    json = yield cmd_dict


def start() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:

    cmd_dict: T_JSON_DICT = {
        'method': 'Profiler.start',
    }
    json = yield cmd_dict


def start_precise_coverage(
        call_count: typing.Optional[bool] = None,
        detailed: typing.Optional[bool] = None,
        allow_triggered_updates: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,float]:
    '''
    Enable precise code coverage. Coverage data for JavaScript executed before enabling precise code
    coverage may be incomplete. Enabling prevents running optimized code and resets execution
    counters.

    :param call_count: *(Optional)* Collect accurate call counts beyond simple 'covered' or 'not covered'.
    :param detailed: *(Optional)* Collect block-based coverage.
    :param allow_triggered_updates: *(Optional)* Allow the backend to send updates on its own initiative
    :returns: Monotonically increasing time (in seconds) when the coverage update was taken in the backend.
    '''
    params: T_JSON_DICT = dict()
    if call_count is not None:
        params['callCount'] = call_count
    if detailed is not None:
        params['detailed'] = detailed
    if allow_triggered_updates is not None:
        params['allowTriggeredUpdates'] = allow_triggered_updates
    cmd_dict: T_JSON_DICT = {
        'method': 'Profiler.startPreciseCoverage',
        'params': params,
    }
    json = yield cmd_dict
    return float(json['timestamp'])


def stop() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,Profile]:
    '''


    :returns: Recorded profile.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Profiler.stop',
    }
    json = yield cmd_dict
    return Profile.from_json(json['profile'])


def stop_precise_coverage() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disable precise code coverage. Disabling releases unnecessary execution count records and allows
    executing optimized code.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Profiler.stopPreciseCoverage',
    }
    json = yield cmd_dict


def take_precise_coverage() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[typing.List[ScriptCoverage], float]]:
    '''
    Collect coverage data for the current isolate, and resets execution counters. Precise code
    coverage needs to have started.

    :returns: A tuple with the following items:

        0. **result** - Coverage data for the current isolate.
        1. **timestamp** - Monotonically increasing time (in seconds) when the coverage update was taken in the backend.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Profiler.takePreciseCoverage',
    }
    json = yield cmd_dict
    return (
        [ScriptCoverage.from_json(i) for i in json['result']],
        float(json['timestamp'])
    )


@event_class('Profiler.consoleProfileFinished')
@dataclass
class ConsoleProfileFinished:
    id_: str
    #: Location of console.profileEnd().
    location: debugger.Location
    profile: Profile
    #: Profile title passed as an argument to console.profile().
    title: typing.Optional[str]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ConsoleProfileFinished:
        return cls(
            id_=str(json['id']),
            location=debugger.Location.from_json(json['location']),
            profile=Profile.from_json(json['profile']),
            title=str(json['title']) if 'title' in json else None
        )


@event_class('Profiler.consoleProfileStarted')
@dataclass
class ConsoleProfileStarted:
    '''
    Sent when new profile recording is started using console.profile() call.
    '''
    id_: str
    #: Location of console.profile().
    location: debugger.Location
    #: Profile title passed as an argument to console.profile().
    title: typing.Optional[str]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ConsoleProfileStarted:
        return cls(
            id_=str(json['id']),
            location=debugger.Location.from_json(json['location']),
            title=str(json['title']) if 'title' in json else None
        )


@event_class('Profiler.preciseCoverageDeltaUpdate')
@dataclass
class PreciseCoverageDeltaUpdate:
    '''
    **EXPERIMENTAL**

    Reports coverage delta since the last poll (either from an event like this, or from
    ``takePreciseCoverage`` for the current isolate. May only be sent if precise code
    coverage has been started. This event can be trigged by the embedder to, for example,
    trigger collection of coverage data immediately at a certain point in time.
    '''
    #: Monotonically increasing time (in seconds) when the coverage update was taken in the backend.
    timestamp: float
    #: Identifier for distinguishing coverage events.
    occasion: str
    #: Coverage data for the current isolate.
    result: typing.List[ScriptCoverage]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> PreciseCoverageDeltaUpdate:
        return cls(
            timestamp=float(json['timestamp']),
            occasion=str(json['occasion']),
            result=[ScriptCoverage.from_json(i) for i in json['result']]
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v137\profiler.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Profiler
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import debugger
from . import runtime


@dataclass
class ProfileNode:
    '''
    Profile node. Holds callsite information, execution statistics and child nodes.
    '''
    #: Unique id of the node.
    id_: int

    #: Function location.
    call_frame: runtime.CallFrame

    #: Number of samples where this node was on top of the call stack.
    hit_count: typing.Optional[int] = None

    #: Child node ids.
    children: typing.Optional[typing.List[int]] = None

    #: The reason of being not optimized. The function may be deoptimized or marked as don't
    #: optimize.
    deopt_reason: typing.Optional[str] = None

    #: An array of source position ticks.
    position_ticks: typing.Optional[typing.List[PositionTickInfo]] = None

    def to_json(self):
        json = dict()
        json['id'] = self.id_
        json['callFrame'] = self.call_frame.to_json()
        if self.hit_count is not None:
            json['hitCount'] = self.hit_count
        if self.children is not None:
            json['children'] = [i for i in self.children]
        if self.deopt_reason is not None:
            json['deoptReason'] = self.deopt_reason
        if self.position_ticks is not None:
            json['positionTicks'] = [i.to_json() for i in self.position_ticks]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            id_=int(json['id']),
            call_frame=runtime.CallFrame.from_json(json['callFrame']),
            hit_count=int(json['hitCount']) if 'hitCount' in json else None,
            children=[int(i) for i in json['children']] if 'children' in json else None,
            deopt_reason=str(json['deoptReason']) if 'deoptReason' in json else None,
            position_ticks=[PositionTickInfo.from_json(i) for i in json['positionTicks']] if 'positionTicks' in json else None,
        )


@dataclass
class Profile:
    '''
    Profile.
    '''
    #: The list of profile nodes. First item is the root node.
    nodes: typing.List[ProfileNode]

    #: Profiling start timestamp in microseconds.
    start_time: float

    #: Profiling end timestamp in microseconds.
    end_time: float

    #: Ids of samples top nodes.
    samples: typing.Optional[typing.List[int]] = None

    #: Time intervals between adjacent samples in microseconds. The first delta is relative to the
    #: profile startTime.
    time_deltas: typing.Optional[typing.List[int]] = None

    def to_json(self):
        json = dict()
        json['nodes'] = [i.to_json() for i in self.nodes]
        json['startTime'] = self.start_time
        json['endTime'] = self.end_time
        if self.samples is not None:
            json['samples'] = [i for i in self.samples]
        if self.time_deltas is not None:
            json['timeDeltas'] = [i for i in self.time_deltas]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            nodes=[ProfileNode.from_json(i) for i in json['nodes']],
            start_time=float(json['startTime']),
            end_time=float(json['endTime']),
            samples=[int(i) for i in json['samples']] if 'samples' in json else None,
            time_deltas=[int(i) for i in json['timeDeltas']] if 'timeDeltas' in json else None,
        )


@dataclass
class PositionTickInfo:
    '''
    Specifies a number of samples attributed to a certain source position.
    '''
    #: Source line number (1-based).
    line: int

    #: Number of samples attributed to the source line.
    ticks: int

    def to_json(self):
        json = dict()
        json['line'] = self.line
        json['ticks'] = self.ticks
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            line=int(json['line']),
            ticks=int(json['ticks']),
        )


@dataclass
class CoverageRange:
    '''
    Coverage data for a source range.
    '''
    #: JavaScript script source offset for the range start.
    start_offset: int

    #: JavaScript script source offset for the range end.
    end_offset: int

    #: Collected execution count of the source range.
    count: int

    def to_json(self):
        json = dict()
        json['startOffset'] = self.start_offset
        json['endOffset'] = self.end_offset
        json['count'] = self.count
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            start_offset=int(json['startOffset']),
            end_offset=int(json['endOffset']),
            count=int(json['count']),
        )


@dataclass
class FunctionCoverage:
    '''
    Coverage data for a JavaScript function.
    '''
    #: JavaScript function name.
    function_name: str

    #: Source ranges inside the function with coverage data.
    ranges: typing.List[CoverageRange]

    #: Whether coverage data for this function has block granularity.
    is_block_coverage: bool

    def to_json(self):
        json = dict()
        json['functionName'] = self.function_name
        json['ranges'] = [i.to_json() for i in self.ranges]
        json['isBlockCoverage'] = self.is_block_coverage
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            function_name=str(json['functionName']),
            ranges=[CoverageRange.from_json(i) for i in json['ranges']],
            is_block_coverage=bool(json['isBlockCoverage']),
        )


@dataclass
class ScriptCoverage:
    '''
    Coverage data for a JavaScript script.
    '''
    #: JavaScript script id.
    script_id: runtime.ScriptId

    #: JavaScript script name or url.
    url: str

    #: Functions contained in the script that has coverage data.
    functions: typing.List[FunctionCoverage]

    def to_json(self):
        json = dict()
        json['scriptId'] = self.script_id.to_json()
        json['url'] = self.url
        json['functions'] = [i.to_json() for i in self.functions]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            script_id=runtime.ScriptId.from_json(json['scriptId']),
            url=str(json['url']),
            functions=[FunctionCoverage.from_json(i) for i in json['functions']],
        )


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:

    cmd_dict: T_JSON_DICT = {
        'method': 'Profiler.disable',
    }
    json = yield cmd_dict


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:

    cmd_dict: T_JSON_DICT = {
        'method': 'Profiler.enable',
    }
    json = yield cmd_dict


def get_best_effort_coverage() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[ScriptCoverage]]:
    '''
    Collect coverage data for the current isolate. The coverage data may be incomplete due to
    garbage collection.

    :returns: Coverage data for the current isolate.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Profiler.getBestEffortCoverage',
    }
    json = yield cmd_dict
    return [ScriptCoverage.from_json(i) for i in json['result']]


def set_sampling_interval(
        interval: int
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Changes CPU profiler sampling interval. Must be called before CPU profiles recording started.

    :param interval: New sampling interval in microseconds.
    '''
    params: T_JSON_DICT = dict()
    params['interval'] = interval
    cmd_dict: T_JSON_DICT = {
        'method': 'Profiler.setSamplingInterval',
        'params': params,
    }
    json = yield cmd_dict


def start() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:

    cmd_dict: T_JSON_DICT = {
        'method': 'Profiler.start',
    }
    json = yield cmd_dict


def start_precise_coverage(
        call_count: typing.Optional[bool] = None,
        detailed: typing.Optional[bool] = None,
        allow_triggered_updates: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,float]:
    '''
    Enable precise code coverage. Coverage data for JavaScript executed before enabling precise code
    coverage may be incomplete. Enabling prevents running optimized code and resets execution
    counters.

    :param call_count: *(Optional)* Collect accurate call counts beyond simple 'covered' or 'not covered'.
    :param detailed: *(Optional)* Collect block-based coverage.
    :param allow_triggered_updates: *(Optional)* Allow the backend to send updates on its own initiative
    :returns: Monotonically increasing time (in seconds) when the coverage update was taken in the backend.
    '''
    params: T_JSON_DICT = dict()
    if call_count is not None:
        params['callCount'] = call_count
    if detailed is not None:
        params['detailed'] = detailed
    if allow_triggered_updates is not None:
        params['allowTriggeredUpdates'] = allow_triggered_updates
    cmd_dict: T_JSON_DICT = {
        'method': 'Profiler.startPreciseCoverage',
        'params': params,
    }
    json = yield cmd_dict
    return float(json['timestamp'])


def stop() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,Profile]:
    '''


    :returns: Recorded profile.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Profiler.stop',
    }
    json = yield cmd_dict
    return Profile.from_json(json['profile'])


def stop_precise_coverage() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disable precise code coverage. Disabling releases unnecessary execution count records and allows
    executing optimized code.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Profiler.stopPreciseCoverage',
    }
    json = yield cmd_dict


def take_precise_coverage() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[typing.List[ScriptCoverage], float]]:
    '''
    Collect coverage data for the current isolate, and resets execution counters. Precise code
    coverage needs to have started.

    :returns: A tuple with the following items:

        0. **result** - Coverage data for the current isolate.
        1. **timestamp** - Monotonically increasing time (in seconds) when the coverage update was taken in the backend.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Profiler.takePreciseCoverage',
    }
    json = yield cmd_dict
    return (
        [ScriptCoverage.from_json(i) for i in json['result']],
        float(json['timestamp'])
    )


@event_class('Profiler.consoleProfileFinished')
@dataclass
class ConsoleProfileFinished:
    id_: str
    #: Location of console.profileEnd().
    location: debugger.Location
    profile: Profile
    #: Profile title passed as an argument to console.profile().
    title: typing.Optional[str]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ConsoleProfileFinished:
        return cls(
            id_=str(json['id']),
            location=debugger.Location.from_json(json['location']),
            profile=Profile.from_json(json['profile']),
            title=str(json['title']) if 'title' in json else None
        )


@event_class('Profiler.consoleProfileStarted')
@dataclass
class ConsoleProfileStarted:
    '''
    Sent when new profile recording is started using console.profile() call.
    '''
    id_: str
    #: Location of console.profile().
    location: debugger.Location
    #: Profile title passed as an argument to console.profile().
    title: typing.Optional[str]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ConsoleProfileStarted:
        return cls(
            id_=str(json['id']),
            location=debugger.Location.from_json(json['location']),
            title=str(json['title']) if 'title' in json else None
        )


@event_class('Profiler.preciseCoverageDeltaUpdate')
@dataclass
class PreciseCoverageDeltaUpdate:
    '''
    **EXPERIMENTAL**

    Reports coverage delta since the last poll (either from an event like this, or from
    ``takePreciseCoverage`` for the current isolate. May only be sent if precise code
    coverage has been started. This event can be trigged by the embedder to, for example,
    trigger collection of coverage data immediately at a certain point in time.
    '''
    #: Monotonically increasing time (in seconds) when the coverage update was taken in the backend.
    timestamp: float
    #: Identifier for distinguishing coverage events.
    occasion: str
    #: Coverage data for the current isolate.
    result: typing.List[ScriptCoverage]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> PreciseCoverageDeltaUpdate:
        return cls(
            timestamp=float(json['timestamp']),
            occasion=str(json['occasion']),
            result=[ScriptCoverage.from_json(i) for i in json['result']]
        )

# === NexusCore/openenv\Lib\site-packages\tokenizers\implementations\base_tokenizer.py ===
from typing import Dict, List, Optional, Tuple, Union

from tokenizers import AddedToken, EncodeInput, Encoding, InputSequence, Tokenizer
from tokenizers.decoders import Decoder
from tokenizers.models import Model
from tokenizers.normalizers import Normalizer
from tokenizers.pre_tokenizers import PreTokenizer
from tokenizers.processors import PostProcessor


Offsets = Tuple[int, int]


class BaseTokenizer:
    def __init__(self, tokenizer: Tokenizer, parameters=None):
        self._tokenizer = tokenizer
        self._parameters = parameters if parameters is not None else {}

    def __repr__(self):
        return "Tokenizer(vocabulary_size={}, {})".format(
            self._tokenizer.get_vocab_size(),
            ", ".join(k + "=" + str(v) for k, v in self._parameters.items()),
        )

    def num_special_tokens_to_add(self, is_pair: bool) -> int:
        """
        Return the number of special tokens that would be added for single/pair sentences.
        :param is_pair: Boolean indicating if the input would be a single sentence or a pair
        :return:
        """
        return self._tokenizer.num_special_tokens_to_add(is_pair)

    def get_vocab(self, with_added_tokens: bool = True) -> Dict[str, int]:
        """Returns the vocabulary

        Args:
            with_added_tokens: boolean:
                Whether to include the added tokens in the vocabulary

        Returns:
            The vocabulary
        """
        return self._tokenizer.get_vocab(with_added_tokens=with_added_tokens)

    def get_added_tokens_decoder(self) -> Dict[int, AddedToken]:
        """Returns the added reverse vocabulary

        Returns:
            The added vocabulary mapping ints to AddedTokens
        """
        return self._tokenizer.get_added_tokens_decoder()

    def get_vocab_size(self, with_added_tokens: bool = True) -> int:
        """Return the size of vocabulary, with or without added tokens.

        Args:
            with_added_tokens: (`optional`) bool:
                Whether to count in added special tokens or not

        Returns:
            Size of vocabulary
        """
        return self._tokenizer.get_vocab_size(with_added_tokens=with_added_tokens)

    def enable_padding(
        self,
        direction: Optional[str] = "right",
        pad_to_multiple_of: Optional[int] = None,
        pad_id: Optional[int] = 0,
        pad_type_id: Optional[int] = 0,
        pad_token: Optional[str] = "[PAD]",
        length: Optional[int] = None,
    ):
        """Change the padding strategy

        Args:
            direction: (`optional`) str:
                Can be one of: `right` or `left`

            pad_to_multiple_of: (`optional`) unsigned int:
                If specified, the padding length should always snap to the next multiple of
                the given value. For example if we were going to pad with a length of 250 but
                `pad_to_multiple_of=8` then we will pad to 256.

            pad_id: (`optional`) unsigned int:
                The indice to be used when padding

            pad_type_id: (`optional`) unsigned int:
                The type indice to be used when padding

            pad_token: (`optional`) str:
                The pad token to be used when padding

            length: (`optional`) unsigned int:
                If specified, the length at which to pad. If not specified
                we pad using the size of the longest sequence in a batch
        """
        return self._tokenizer.enable_padding(
            direction=direction,
            pad_to_multiple_of=pad_to_multiple_of,
            pad_id=pad_id,
            pad_type_id=pad_type_id,
            pad_token=pad_token,
            length=length,
        )

    def no_padding(self):
        """Disable padding"""
        return self._tokenizer.no_padding()

    @property
    def padding(self) -> Optional[dict]:
        """Get the current padding parameters

        Returns:
            None if padding is disabled, a dict with the currently set parameters
            if the padding is enabled.
        """
        return self._tokenizer.padding

    def enable_truncation(self, max_length: int, stride: Optional[int] = 0, strategy: Optional[str] = "longest_first"):
        """Change the truncation options

        Args:
            max_length: unsigned int:
                The maximum length at which to truncate

            stride: (`optional`) unsigned int:
                The length of the previous first sequence to be included
                in the overflowing sequence

            strategy: (`optional`) str:
                Can be one of `longest_first`, `only_first` or `only_second`
        """
        return self._tokenizer.enable_truncation(max_length, stride=stride, strategy=strategy)

    def no_truncation(self):
        """Disable truncation"""
        return self._tokenizer.no_truncation()

    @property
    def truncation(self) -> Optional[dict]:
        """Get the current truncation parameters

        Returns:
            None if truncation is disabled, a dict with the current truncation parameters if
            truncation is enabled
        """
        return self._tokenizer.truncation

    def add_tokens(self, tokens: List[Union[str, AddedToken]]) -> int:
        """Add the given tokens to the vocabulary

        Args:
            tokens: List[Union[str, AddedToken]]:
                A list of tokens to add to the vocabulary. Each token can either be
                a string, or an instance of AddedToken

        Returns:
            The number of tokens that were added to the vocabulary
        """
        return self._tokenizer.add_tokens(tokens)

    def add_special_tokens(self, special_tokens: List[Union[str, AddedToken]]) -> int:
        """Add the given special tokens to the vocabulary, and treat them as special tokens.

        The special tokens will never be processed by the model, and will be
        removed while decoding.

        Args:
            tokens: List[Union[str, AddedToken]]:
                A list of special tokens to add to the vocabulary. Each token can either be
                a string, or an instance of AddedToken

        Returns:
            The number of tokens that were added to the vocabulary
        """
        return self._tokenizer.add_special_tokens(special_tokens)

    def normalize(self, sequence: str) -> str:
        """Normalize the given sequence

        Args:
            sequence: str:
                The sequence to normalize

        Returns:
            The normalized string
        """
        return self._tokenizer.normalize(sequence)

    def encode(
        self,
        sequence: InputSequence,
        pair: Optional[InputSequence] = None,
        is_pretokenized: bool = False,
        add_special_tokens: bool = True,
    ) -> Encoding:
        """Encode the given sequence and pair. This method can process raw text sequences as well
        as already pre-tokenized sequences.

        Args:
            sequence: InputSequence:
                The sequence we want to encode. This sequence can be either raw text or
                pre-tokenized, according to the `is_pretokenized` argument:

                - If `is_pretokenized=False`: `InputSequence` is expected to be `str`
                - If `is_pretokenized=True`: `InputSequence` is expected to be
                    `Union[List[str], Tuple[str]]`

            is_pretokenized: bool:
                Whether the input is already pre-tokenized.

            add_special_tokens: bool:
                Whether to add the special tokens while encoding.

        Returns:
            An Encoding
        """
        if sequence is None:
            raise ValueError("encode: `sequence` can't be `None`")

        return self._tokenizer.encode(sequence, pair, is_pretokenized, add_special_tokens)

    def encode_batch(
        self,
        inputs: List[EncodeInput],
        is_pretokenized: bool = False,
        add_special_tokens: bool = True,
    ) -> List[Encoding]:
        """Encode the given inputs. This method accept both raw text sequences as well as already
        pre-tokenized sequences.

        Args:
            inputs: List[EncodeInput]:
                A list of single sequences or pair sequences to encode. Each `EncodeInput` is
                expected to be of the following form:
                    `Union[InputSequence, Tuple[InputSequence, InputSequence]]`

                Each `InputSequence` can either be raw text or pre-tokenized,
                according to the `is_pretokenized` argument:

                - If `is_pretokenized=False`: `InputSequence` is expected to be `str`
                - If `is_pretokenized=True`: `InputSequence` is expected to be
                    `Union[List[str], Tuple[str]]`

            is_pretokenized: bool:
                Whether the input is already pre-tokenized.

            add_special_tokens: bool:
                Whether to add the special tokens while encoding.

        Returns:
            A list of Encoding
        """

        if inputs is None:
            raise ValueError("encode_batch: `inputs` can't be `None`")

        return self._tokenizer.encode_batch(inputs, is_pretokenized, add_special_tokens)

    def decode(self, ids: List[int], skip_special_tokens: Optional[bool] = True) -> str:
        """Decode the given list of ids to a string sequence

        Args:
            ids: List[unsigned int]:
                A list of ids to be decoded

            skip_special_tokens: (`optional`) boolean:
                Whether to remove all the special tokens from the output string

        Returns:
            The decoded string
        """
        if ids is None:
            raise ValueError("None input is not valid. Should be a list of integers.")

        return self._tokenizer.decode(ids, skip_special_tokens=skip_special_tokens)

    def decode_batch(self, sequences: List[List[int]], skip_special_tokens: Optional[bool] = True) -> str:
        """Decode the list of sequences to a list of string sequences

        Args:
            sequences: List[List[unsigned int]]:
                A list of sequence of ids to be decoded

            skip_special_tokens: (`optional`) boolean:
                Whether to remove all the special tokens from the output strings

        Returns:
            A list of decoded strings
        """
        if sequences is None:
            raise ValueError("None input is not valid. Should be list of list of integers.")

        return self._tokenizer.decode_batch(sequences, skip_special_tokens=skip_special_tokens)

    def token_to_id(self, token: str) -> Optional[int]:
        """Convert the given token to its corresponding id

        Args:
            token: str:
                The token to convert

        Returns:
            The corresponding id if it exists, None otherwise
        """
        return self._tokenizer.token_to_id(token)

    def id_to_token(self, id: int) -> Optional[str]:
        """Convert the given token id to its corresponding string

        Args:
            token: id:
                The token id to convert

        Returns:
            The corresponding string if it exists, None otherwise
        """
        return self._tokenizer.id_to_token(id)

    def save_model(self, directory: str, prefix: Optional[str] = None):
        """Save the current model to the given directory

        Args:
            directory: str:
                A path to the destination directory

            prefix: (Optional) str:
                An optional prefix, used to prefix each file name
        """
        return self._tokenizer.model.save(directory, prefix=prefix)

    def save(self, path: str, pretty: bool = True):
        """Save the current Tokenizer at the given path

        Args:
            path: str:
                A path to the destination Tokenizer file
        """
        return self._tokenizer.save(path, pretty)

    def to_str(self, pretty: bool = False):
        """Get a serialized JSON version of the Tokenizer as a str

        Args:
            pretty: bool:
                Whether the JSON string should be prettified

        Returns:
            str
        """
        return self._tokenizer.to_str(pretty)

    def post_process(
        self, encoding: Encoding, pair: Optional[Encoding] = None, add_special_tokens: bool = True
    ) -> Encoding:
        """Apply all the post-processing steps to the given encodings.

        The various steps are:
            1. Truncate according to global params (provided to `enable_truncation`)
            2. Apply the PostProcessor
            3. Pad according to global params. (provided to `enable_padding`)

        Args:
            encoding: Encoding:
                The main Encoding to post process

            pair: Optional[Encoding]:
                An optional pair Encoding

            add_special_tokens: bool:
                Whether to add special tokens

        Returns:
            The resulting Encoding
        """
        return self._tokenizer.post_process(encoding, pair, add_special_tokens)

    @property
    def model(self) -> Model:
        return self._tokenizer.model

    @model.setter
    def model(self, model: Model):
        self._tokenizer.model = model

    @property
    def normalizer(self) -> Normalizer:
        return self._tokenizer.normalizer

    @normalizer.setter
    def normalizer(self, normalizer: Normalizer):
        self._tokenizer.normalizer = normalizer

    @property
    def pre_tokenizer(self) -> PreTokenizer:
        return self._tokenizer.pre_tokenizer

    @pre_tokenizer.setter
    def pre_tokenizer(self, pre_tokenizer: PreTokenizer):
        self._tokenizer.pre_tokenizer = pre_tokenizer

    @property
    def post_processor(self) -> PostProcessor:
        return self._tokenizer.post_processor

    @post_processor.setter
    def post_processor(self, post_processor: PostProcessor):
        self._tokenizer.post_processor = post_processor

    @property
    def decoder(self) -> Decoder:
        return self._tokenizer.decoder

    @decoder.setter
    def decoder(self, decoder: Decoder):
        self._tokenizer.decoder = decoder

# === NexusCore/openenv\Lib\site-packages\fsspec\gui.py ===
import ast
import contextlib
import logging
import os
import re
from typing import ClassVar, Sequence

import panel as pn

from .core import OpenFile, get_filesystem_class, split_protocol
from .registry import known_implementations

pn.extension()
logger = logging.getLogger("fsspec.gui")


class SigSlot:
    """Signal-slot mixin, for Panel event passing

    Include this class in a widget manager's superclasses to be able to
    register events and callbacks on Panel widgets managed by that class.

    The method ``_register`` should be called as widgets are added, and external
    code should call ``connect`` to associate callbacks.

    By default, all signals emit a DEBUG logging statement.
    """

    # names of signals that this class may emit each of which must be
    # set by _register for any new instance
    signals: ClassVar[Sequence[str]] = []
    # names of actions that this class may respond to
    slots: ClassVar[Sequence[str]] = []

    # each of which must be a method name

    def __init__(self):
        self._ignoring_events = False
        self._sigs = {}
        self._map = {}
        self._setup()

    def _setup(self):
        """Create GUI elements and register signals"""
        self.panel = pn.pane.PaneBase()
        # no signals to set up in the base class

    def _register(
        self, widget, name, thing="value", log_level=logging.DEBUG, auto=False
    ):
        """Watch the given attribute of a widget and assign it a named event

        This is normally called at the time a widget is instantiated, in the
        class which owns it.

        Parameters
        ----------
        widget : pn.layout.Panel or None
            Widget to watch. If None, an anonymous signal not associated with
            any widget.
        name : str
            Name of this event
        thing : str
            Attribute of the given widget to watch
        log_level : int
            When the signal is triggered, a logging event of the given level
            will be fired in the dfviz logger.
        auto : bool
            If True, automatically connects with a method in this class of the
            same name.
        """
        if name not in self.signals:
            raise ValueError(f"Attempt to assign an undeclared signal: {name}")
        self._sigs[name] = {
            "widget": widget,
            "callbacks": [],
            "thing": thing,
            "log": log_level,
        }
        wn = "-".join(
            [
                getattr(widget, "name", str(widget)) if widget is not None else "none",
                thing,
            ]
        )
        self._map[wn] = name
        if widget is not None:
            widget.param.watch(self._signal, thing, onlychanged=True)
        if auto and hasattr(self, name):
            self.connect(name, getattr(self, name))

    def _repr_mimebundle_(self, *args, **kwargs):
        """Display in a notebook or a server"""
        try:
            return self.panel._repr_mimebundle_(*args, **kwargs)
        except (ValueError, AttributeError) as exc:
            raise NotImplementedError(
                "Panel does not seem to be set up properly"
            ) from exc

    def connect(self, signal, slot):
        """Associate call back with given event

        The callback must be a function which takes the "new" value of the
        watched attribute as the only parameter. If the callback return False,
        this cancels any further processing of the given event.

        Alternatively, the callback can be a string, in which case it means
        emitting the correspondingly-named event (i.e., connect to self)
        """
        self._sigs[signal]["callbacks"].append(slot)

    def _signal(self, event):
        """This is called by a an action on a widget

        Within an self.ignore_events context, nothing happens.

        Tests can execute this method by directly changing the values of
        widget components.
        """
        if not self._ignoring_events:
            wn = "-".join([event.obj.name, event.name])
            if wn in self._map and self._map[wn] in self._sigs:
                self._emit(self._map[wn], event.new)

    @contextlib.contextmanager
    def ignore_events(self):
        """Temporarily turn off events processing in this instance

        (does not propagate to children)
        """
        self._ignoring_events = True
        try:
            yield
        finally:
            self._ignoring_events = False

    def _emit(self, sig, value=None):
        """An event happened, call its callbacks

        This method can be used in tests to simulate message passing without
        directly changing visual elements.

        Calling of callbacks will halt whenever one returns False.
        """
        logger.log(self._sigs[sig]["log"], f"{sig}: {value}")
        for callback in self._sigs[sig]["callbacks"]:
            if isinstance(callback, str):
                self._emit(callback)
            else:
                try:
                    # running callbacks should not break the interface
                    ret = callback(value)
                    if ret is False:
                        break
                except Exception as e:
                    logger.exception(
                        "Exception (%s) while executing callback for signal: %s",
                        e,
                        sig,
                    )

    def show(self, threads=False):
        """Open a new browser tab and display this instance's interface"""
        self.panel.show(threads=threads, verbose=False)
        return self


class SingleSelect(SigSlot):
    """A multiselect which only allows you to select one item for an event"""

    signals = ["_selected", "selected"]  # the first is internal
    slots = ["set_options", "set_selection", "add", "clear", "select"]

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        super().__init__()

    def _setup(self):
        self.panel = pn.widgets.MultiSelect(**self.kwargs)
        self._register(self.panel, "_selected", "value")
        self._register(None, "selected")
        self.connect("_selected", self.select_one)

    def _signal(self, *args, **kwargs):
        super()._signal(*args, **kwargs)

    def select_one(self, *_):
        with self.ignore_events():
            val = [self.panel.value[-1]] if self.panel.value else []
            self.panel.value = val
        self._emit("selected", self.panel.value)

    def set_options(self, options):
        self.panel.options = options

    def clear(self):
        self.panel.options = []

    @property
    def value(self):
        return self.panel.value

    def set_selection(self, selection):
        self.panel.value = [selection]


class FileSelector(SigSlot):
    """Panel-based graphical file selector widget

    Instances of this widget are interactive and can be displayed in jupyter by having
    them as the output of a cell,  or in a separate browser tab using ``.show()``.
    """

    signals = [
        "protocol_changed",
        "selection_changed",
        "directory_entered",
        "home_clicked",
        "up_clicked",
        "go_clicked",
        "filters_changed",
    ]
    slots = ["set_filters", "go_home"]

    def __init__(self, url=None, filters=None, ignore=None, kwargs=None):
        """

        Parameters
        ----------
        url : str (optional)
            Initial value of the URL to populate the dialog; should include protocol
        filters : list(str) (optional)
            File endings to include in the listings. If not included, all files are
            allowed. Does not affect directories.
            If given, the endings will appear as checkboxes in the interface
        ignore : list(str) (optional)
            Regex(s) of file basename patterns to ignore, e.g., "\\." for typical
            hidden files on posix
        kwargs : dict (optional)
            To pass to file system instance
        """
        if url:
            self.init_protocol, url = split_protocol(url)
        else:
            self.init_protocol, url = "file", os.getcwd()
        self.init_url = url
        self.init_kwargs = (kwargs if isinstance(kwargs, str) else str(kwargs)) or "{}"
        self.filters = filters
        self.ignore = [re.compile(i) for i in ignore or []]
        self._fs = None
        super().__init__()

    def _setup(self):
        self.url = pn.widgets.TextInput(
            name="url",
            value=self.init_url,
            align="end",
            sizing_mode="stretch_width",
            width_policy="max",
        )
        self.protocol = pn.widgets.Select(
            options=sorted(known_implementations),
            value=self.init_protocol,
            name="protocol",
            align="center",
        )
        self.kwargs = pn.widgets.TextInput(
            name="kwargs", value=self.init_kwargs, align="center"
        )
        self.go = pn.widgets.Button(name="⇨", align="end", width=45)
        self.main = SingleSelect(size=10)
        self.home = pn.widgets.Button(name="🏠", width=40, height=30, align="end")
        self.up = pn.widgets.Button(name="‹", width=30, height=30, align="end")

        self._register(self.protocol, "protocol_changed", auto=True)
        self._register(self.go, "go_clicked", "clicks", auto=True)
        self._register(self.up, "up_clicked", "clicks", auto=True)
        self._register(self.home, "home_clicked", "clicks", auto=True)
        self._register(None, "selection_changed")
        self.main.connect("selected", self.selection_changed)
        self._register(None, "directory_entered")
        self.prev_protocol = self.protocol.value
        self.prev_kwargs = self.storage_options

        self.filter_sel = pn.widgets.CheckBoxGroup(
            value=[], options=[], inline=False, align="end", width_policy="min"
        )
        self._register(self.filter_sel, "filters_changed", auto=True)

        self.panel = pn.Column(
            pn.Row(self.protocol, self.kwargs),
            pn.Row(self.home, self.up, self.url, self.go, self.filter_sel),
            self.main.panel,
        )
        self.set_filters(self.filters)
        self.go_clicked()

    def set_filters(self, filters=None):
        self.filters = filters
        if filters:
            self.filter_sel.options = filters
            self.filter_sel.value = filters
        else:
            self.filter_sel.options = []
            self.filter_sel.value = []

    @property
    def storage_options(self):
        """Value of the kwargs box as a dictionary"""
        return ast.literal_eval(self.kwargs.value) or {}

    @property
    def fs(self):
        """Current filesystem instance"""
        if self._fs is None:
            cls = get_filesystem_class(self.protocol.value)
            self._fs = cls(**self.storage_options)
        return self._fs

    @property
    def urlpath(self):
        """URL of currently selected item"""
        return (
            (f"{self.protocol.value}://{self.main.value[0]}")
            if self.main.value
            else None
        )

    def open_file(self, mode="rb", compression=None, encoding=None):
        """Create OpenFile instance for the currently selected item

        For example, in a notebook you might do something like

        .. code-block::

            [ ]: sel = FileSelector(); sel

            # user selects their file

            [ ]: with sel.open_file('rb') as f:
            ...      out = f.read()

        Parameters
        ----------
        mode: str (optional)
            Open mode for the file.
        compression: str (optional)
            The interact with the file as compressed. Set to 'infer' to guess
            compression from the file ending
        encoding: str (optional)
            If using text mode, use this encoding; defaults to UTF8.
        """
        if self.urlpath is None:
            raise ValueError("No file selected")
        return OpenFile(self.fs, self.urlpath, mode, compression, encoding)

    def filters_changed(self, values):
        self.filters = values
        self.go_clicked()

    def selection_changed(self, *_):
        if self.urlpath is None:
            return
        if self.fs.isdir(self.urlpath):
            self.url.value = self.fs._strip_protocol(self.urlpath)
        self.go_clicked()

    def go_clicked(self, *_):
        if (
            self.prev_protocol != self.protocol.value
            or self.prev_kwargs != self.storage_options
        ):
            self._fs = None  # causes fs to be recreated
            self.prev_protocol = self.protocol.value
            self.prev_kwargs = self.storage_options
        listing = sorted(
            self.fs.ls(self.url.value, detail=True), key=lambda x: x["name"]
        )
        listing = [
            l
            for l in listing
            if not any(i.match(l["name"].rsplit("/", 1)[-1]) for i in self.ignore)
        ]
        folders = {
            "📁 " + o["name"].rsplit("/", 1)[-1]: o["name"]
            for o in listing
            if o["type"] == "directory"
        }
        files = {
            "📄 " + o["name"].rsplit("/", 1)[-1]: o["name"]
            for o in listing
            if o["type"] == "file"
        }
        if self.filters:
            files = {
                k: v
                for k, v in files.items()
                if any(v.endswith(ext) for ext in self.filters)
            }
        self.main.set_options(dict(**folders, **files))

    def protocol_changed(self, *_):
        self._fs = None
        self.main.options = []
        self.url.value = ""

    def home_clicked(self, *_):
        self.protocol.value = self.init_protocol
        self.kwargs.value = self.init_kwargs
        self.url.value = self.init_url
        self.go_clicked()

    def up_clicked(self, *_):
        self.url.value = self.fs._parent(self.url.value)
        self.go_clicked()

# === NexusCore/openenv\Lib\site-packages\dateutil\parser\isoparser.py ===
# -*- coding: utf-8 -*-
"""
This module offers a parser for ISO-8601 strings

It is intended to support all valid date, time and datetime formats per the
ISO-8601 specification.

..versionadded:: 2.7.0
"""
from datetime import datetime, timedelta, time, date
import calendar
from dateutil import tz

from functools import wraps

import re
import six

__all__ = ["isoparse", "isoparser"]


def _takes_ascii(f):
    @wraps(f)
    def func(self, str_in, *args, **kwargs):
        # If it's a stream, read the whole thing
        str_in = getattr(str_in, 'read', lambda: str_in)()

        # If it's unicode, turn it into bytes, since ISO-8601 only covers ASCII
        if isinstance(str_in, six.text_type):
            # ASCII is the same in UTF-8
            try:
                str_in = str_in.encode('ascii')
            except UnicodeEncodeError as e:
                msg = 'ISO-8601 strings should contain only ASCII characters'
                six.raise_from(ValueError(msg), e)

        return f(self, str_in, *args, **kwargs)

    return func


class isoparser(object):
    def __init__(self, sep=None):
        """
        :param sep:
            A single character that separates date and time portions. If
            ``None``, the parser will accept any single character.
            For strict ISO-8601 adherence, pass ``'T'``.
        """
        if sep is not None:
            if (len(sep) != 1 or ord(sep) >= 128 or sep in '0123456789'):
                raise ValueError('Separator must be a single, non-numeric ' +
                                 'ASCII character')

            sep = sep.encode('ascii')

        self._sep = sep

    @_takes_ascii
    def isoparse(self, dt_str):
        """
        Parse an ISO-8601 datetime string into a :class:`datetime.datetime`.

        An ISO-8601 datetime string consists of a date portion, followed
        optionally by a time portion - the date and time portions are separated
        by a single character separator, which is ``T`` in the official
        standard. Incomplete date formats (such as ``YYYY-MM``) may *not* be
        combined with a time portion.

        Supported date formats are:

        Common:

        - ``YYYY``
        - ``YYYY-MM``
        - ``YYYY-MM-DD`` or ``YYYYMMDD``

        Uncommon:

        - ``YYYY-Www`` or ``YYYYWww`` - ISO week (day defaults to 0)
        - ``YYYY-Www-D`` or ``YYYYWwwD`` - ISO week and day

        The ISO week and day numbering follows the same logic as
        :func:`datetime.date.isocalendar`.

        Supported time formats are:

        - ``hh``
        - ``hh:mm`` or ``hhmm``
        - ``hh:mm:ss`` or ``hhmmss``
        - ``hh:mm:ss.ssssss`` (Up to 6 sub-second digits)

        Midnight is a special case for `hh`, as the standard supports both
        00:00 and 24:00 as a representation. The decimal separator can be
        either a dot or a comma.


        .. caution::

            Support for fractional components other than seconds is part of the
            ISO-8601 standard, but is not currently implemented in this parser.

        Supported time zone offset formats are:

        - `Z` (UTC)
        - `±HH:MM`
        - `±HHMM`
        - `±HH`

        Offsets will be represented as :class:`dateutil.tz.tzoffset` objects,
        with the exception of UTC, which will be represented as
        :class:`dateutil.tz.tzutc`. Time zone offsets equivalent to UTC (such
        as `+00:00`) will also be represented as :class:`dateutil.tz.tzutc`.

        :param dt_str:
            A string or stream containing only an ISO-8601 datetime string

        :return:
            Returns a :class:`datetime.datetime` representing the string.
            Unspecified components default to their lowest value.

        .. warning::

            As of version 2.7.0, the strictness of the parser should not be
            considered a stable part of the contract. Any valid ISO-8601 string
            that parses correctly with the default settings will continue to
            parse correctly in future versions, but invalid strings that
            currently fail (e.g. ``2017-01-01T00:00+00:00:00``) are not
            guaranteed to continue failing in future versions if they encode
            a valid date.

        .. versionadded:: 2.7.0
        """
        components, pos = self._parse_isodate(dt_str)

        if len(dt_str) > pos:
            if self._sep is None or dt_str[pos:pos + 1] == self._sep:
                components += self._parse_isotime(dt_str[pos + 1:])
            else:
                raise ValueError('String contains unknown ISO components')

        if len(components) > 3 and components[3] == 24:
            components[3] = 0
            return datetime(*components) + timedelta(days=1)

        return datetime(*components)

    @_takes_ascii
    def parse_isodate(self, datestr):
        """
        Parse the date portion of an ISO string.

        :param datestr:
            The string portion of an ISO string, without a separator

        :return:
            Returns a :class:`datetime.date` object
        """
        components, pos = self._parse_isodate(datestr)
        if pos < len(datestr):
            raise ValueError('String contains unknown ISO ' +
                             'components: {!r}'.format(datestr.decode('ascii')))
        return date(*components)

    @_takes_ascii
    def parse_isotime(self, timestr):
        """
        Parse the time portion of an ISO string.

        :param timestr:
            The time portion of an ISO string, without a separator

        :return:
            Returns a :class:`datetime.time` object
        """
        components = self._parse_isotime(timestr)
        if components[0] == 24:
            components[0] = 0
        return time(*components)

    @_takes_ascii
    def parse_tzstr(self, tzstr, zero_as_utc=True):
        """
        Parse a valid ISO time zone string.

        See :func:`isoparser.isoparse` for details on supported formats.

        :param tzstr:
            A string representing an ISO time zone offset

        :param zero_as_utc:
            Whether to return :class:`dateutil.tz.tzutc` for zero-offset zones

        :return:
            Returns :class:`dateutil.tz.tzoffset` for offsets and
            :class:`dateutil.tz.tzutc` for ``Z`` and (if ``zero_as_utc`` is
            specified) offsets equivalent to UTC.
        """
        return self._parse_tzstr(tzstr, zero_as_utc=zero_as_utc)

    # Constants
    _DATE_SEP = b'-'
    _TIME_SEP = b':'
    _FRACTION_REGEX = re.compile(b'[\\.,]([0-9]+)')

    def _parse_isodate(self, dt_str):
        try:
            return self._parse_isodate_common(dt_str)
        except ValueError:
            return self._parse_isodate_uncommon(dt_str)

    def _parse_isodate_common(self, dt_str):
        len_str = len(dt_str)
        components = [1, 1, 1]

        if len_str < 4:
            raise ValueError('ISO string too short')

        # Year
        components[0] = int(dt_str[0:4])
        pos = 4
        if pos >= len_str:
            return components, pos

        has_sep = dt_str[pos:pos + 1] == self._DATE_SEP
        if has_sep:
            pos += 1

        # Month
        if len_str - pos < 2:
            raise ValueError('Invalid common month')

        components[1] = int(dt_str[pos:pos + 2])
        pos += 2

        if pos >= len_str:
            if has_sep:
                return components, pos
            else:
                raise ValueError('Invalid ISO format')

        if has_sep:
            if dt_str[pos:pos + 1] != self._DATE_SEP:
                raise ValueError('Invalid separator in ISO string')
            pos += 1

        # Day
        if len_str - pos < 2:
            raise ValueError('Invalid common day')
        components[2] = int(dt_str[pos:pos + 2])
        return components, pos + 2

    def _parse_isodate_uncommon(self, dt_str):
        if len(dt_str) < 4:
            raise ValueError('ISO string too short')

        # All ISO formats start with the year
        year = int(dt_str[0:4])

        has_sep = dt_str[4:5] == self._DATE_SEP

        pos = 4 + has_sep       # Skip '-' if it's there
        if dt_str[pos:pos + 1] == b'W':
            # YYYY-?Www-?D?
            pos += 1
            weekno = int(dt_str[pos:pos + 2])
            pos += 2

            dayno = 1
            if len(dt_str) > pos:
                if (dt_str[pos:pos + 1] == self._DATE_SEP) != has_sep:
                    raise ValueError('Inconsistent use of dash separator')

                pos += has_sep

                dayno = int(dt_str[pos:pos + 1])
                pos += 1

            base_date = self._calculate_weekdate(year, weekno, dayno)
        else:
            # YYYYDDD or YYYY-DDD
            if len(dt_str) - pos < 3:
                raise ValueError('Invalid ordinal day')

            ordinal_day = int(dt_str[pos:pos + 3])
            pos += 3

            if ordinal_day < 1 or ordinal_day > (365 + calendar.isleap(year)):
                raise ValueError('Invalid ordinal day' +
                                 ' {} for year {}'.format(ordinal_day, year))

            base_date = date(year, 1, 1) + timedelta(days=ordinal_day - 1)

        components = [base_date.year, base_date.month, base_date.day]
        return components, pos

    def _calculate_weekdate(self, year, week, day):
        """
        Calculate the day of corresponding to the ISO year-week-day calendar.

        This function is effectively the inverse of
        :func:`datetime.date.isocalendar`.

        :param year:
            The year in the ISO calendar

        :param week:
            The week in the ISO calendar - range is [1, 53]

        :param day:
            The day in the ISO calendar - range is [1 (MON), 7 (SUN)]

        :return:
            Returns a :class:`datetime.date`
        """
        if not 0 < week < 54:
            raise ValueError('Invalid week: {}'.format(week))

        if not 0 < day < 8:     # Range is 1-7
            raise ValueError('Invalid weekday: {}'.format(day))

        # Get week 1 for the specific year:
        jan_4 = date(year, 1, 4)   # Week 1 always has January 4th in it
        week_1 = jan_4 - timedelta(days=jan_4.isocalendar()[2] - 1)

        # Now add the specific number of weeks and days to get what we want
        week_offset = (week - 1) * 7 + (day - 1)
        return week_1 + timedelta(days=week_offset)

    def _parse_isotime(self, timestr):
        len_str = len(timestr)
        components = [0, 0, 0, 0, None]
        pos = 0
        comp = -1

        if len_str < 2:
            raise ValueError('ISO time too short')

        has_sep = False

        while pos < len_str and comp < 5:
            comp += 1

            if timestr[pos:pos + 1] in b'-+Zz':
                # Detect time zone boundary
                components[-1] = self._parse_tzstr(timestr[pos:])
                pos = len_str
                break

            if comp == 1 and timestr[pos:pos+1] == self._TIME_SEP:
                has_sep = True
                pos += 1
            elif comp == 2 and has_sep:
                if timestr[pos:pos+1] != self._TIME_SEP:
                    raise ValueError('Inconsistent use of colon separator')
                pos += 1

            if comp < 3:
                # Hour, minute, second
                components[comp] = int(timestr[pos:pos + 2])
                pos += 2

            if comp == 3:
                # Fraction of a second
                frac = self._FRACTION_REGEX.match(timestr[pos:])
                if not frac:
                    continue

                us_str = frac.group(1)[:6]  # Truncate to microseconds
                components[comp] = int(us_str) * 10**(6 - len(us_str))
                pos += len(frac.group())

        if pos < len_str:
            raise ValueError('Unused components in ISO string')

        if components[0] == 24:
            # Standard supports 00:00 and 24:00 as representations of midnight
            if any(component != 0 for component in components[1:4]):
                raise ValueError('Hour may only be 24 at 24:00:00.000')

        return components

    def _parse_tzstr(self, tzstr, zero_as_utc=True):
        if tzstr == b'Z' or tzstr == b'z':
            return tz.UTC

        if len(tzstr) not in {3, 5, 6}:
            raise ValueError('Time zone offset must be 1, 3, 5 or 6 characters')

        if tzstr[0:1] == b'-':
            mult = -1
        elif tzstr[0:1] == b'+':
            mult = 1
        else:
            raise ValueError('Time zone offset requires sign')

        hours = int(tzstr[1:3])
        if len(tzstr) == 3:
            minutes = 0
        else:
            minutes = int(tzstr[(4 if tzstr[3:4] == self._TIME_SEP else 3):])

        if zero_as_utc and hours == 0 and minutes == 0:
            return tz.UTC
        else:
            if minutes > 59:
                raise ValueError('Invalid minutes in time zone offset')

            if hours > 23:
                raise ValueError('Invalid hours in time zone offset')

            return tz.tzoffset(None, mult * (hours * 60 + minutes) * 60)


DEFAULT_ISOPARSER = isoparser()
isoparse = DEFAULT_ISOPARSER.isoparse

# === NexusCore/openenv\Lib\site-packages\fsspec\implementations\smb.py ===
"""
This module contains SMBFileSystem class responsible for handling access to
Windows Samba network shares by using package smbprotocol
"""

import datetime
import re
import uuid
from stat import S_ISDIR, S_ISLNK

import smbclient
import smbprotocol.exceptions

from .. import AbstractFileSystem
from ..utils import infer_storage_options

# ! pylint: disable=bad-continuation


class SMBFileSystem(AbstractFileSystem):
    """Allow reading and writing to Windows and Samba network shares.

    When using `fsspec.open()` for getting a file-like object the URI
    should be specified as this format:
    ``smb://workgroup;user:password@server:port/share/folder/file.csv``.

    Example::

        >>> import fsspec
        >>> with fsspec.open(
        ...     'smb://myuser:mypassword@myserver.com/' 'share/folder/file.csv'
        ... ) as smbfile:
        ...     df = pd.read_csv(smbfile, sep='|', header=None)

    Note that you need to pass in a valid hostname or IP address for the host
    component of the URL. Do not use the Windows/NetBIOS machine name for the
    host component.

    The first component of the path in the URL points to the name of the shared
    folder. Subsequent path components will point to the directory/folder/file.

    The URL components ``workgroup`` , ``user``, ``password`` and ``port`` may be
    optional.

    .. note::

        For working this source require `smbprotocol`_ to be installed, e.g.::

            $ pip install smbprotocol
            # or
            # pip install smbprotocol[kerberos]

    .. _smbprotocol: https://github.com/jborean93/smbprotocol#requirements

    Note: if using this with the ``open`` or ``open_files``, with full URLs,
    there is no way to tell if a path is relative, so all paths are assumed
    to be absolute.
    """

    protocol = "smb"

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        host,
        port=None,
        username=None,
        password=None,
        timeout=60,
        encrypt=None,
        share_access=None,
        register_session_retries=4,
        register_session_retry_wait=1,
        register_session_retry_factor=10,
        auto_mkdir=False,
        **kwargs,
    ):
        """
        You can use _get_kwargs_from_urls to get some kwargs from
        a reasonable SMB url.

        Authentication will be anonymous or integrated if username/password are not
        given.

        Parameters
        ----------
        host: str
            The remote server name/ip to connect to
        port: int or None
            Port to connect with. Usually 445, sometimes 139.
        username: str or None
            Username to connect with. Required if Kerberos auth is not being used.
        password: str or None
            User's password on the server, if using username
        timeout: int
            Connection timeout in seconds
        encrypt: bool
            Whether to force encryption or not, once this has been set to True
            the session cannot be changed back to False.
        share_access: str or None
            Specifies the default access applied to file open operations
            performed with this file system object.
            This affects whether other processes can concurrently open a handle
            to the same file.

            - None (the default): exclusively locks the file until closed.
            - 'r': Allow other handles to be opened with read access.
            - 'w': Allow other handles to be opened with write access.
            - 'd': Allow other handles to be opened with delete access.
        register_session_retries: int
            Number of retries to register a session with the server. Retries are not performed
            for authentication errors, as they are considered as invalid credentials and not network
            issues. If set to negative value, no register attempts will be performed.
        register_session_retry_wait: int
            Time in seconds to wait between each retry. Number must be non-negative.
        register_session_retry_factor: int
            Base factor for the wait time between each retry. The wait time
            is calculated using exponential function. For factor=1 all wait times
            will be equal to `register_session_retry_wait`. For any number of retries,
            the last wait time will be equal to `register_session_retry_wait` and for retries>1
            the first wait time will be equal to `register_session_retry_wait / factor`.
            Number must be equal to or greater than 1. Optimal factor is 10.
        auto_mkdir: bool
            Whether, when opening a file, the directory containing it should
            be created (if it doesn't already exist). This is assumed by pyarrow
            and zarr-python code.
        """
        super().__init__(**kwargs)
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        self.encrypt = encrypt
        self.temppath = kwargs.pop("temppath", "")
        self.share_access = share_access
        self.register_session_retries = register_session_retries
        if register_session_retry_wait < 0:
            raise ValueError(
                "register_session_retry_wait must be a non-negative integer"
            )
        self.register_session_retry_wait = register_session_retry_wait
        if register_session_retry_factor < 1:
            raise ValueError(
                "register_session_retry_factor must be a positive "
                "integer equal to or greater than 1"
            )
        self.register_session_retry_factor = register_session_retry_factor
        self.auto_mkdir = auto_mkdir
        self._connect()

    @property
    def _port(self):
        return 445 if self.port is None else self.port

    def _connect(self):
        import time

        if self.register_session_retries <= -1:
            return

        retried_errors = []

        wait_time = self.register_session_retry_wait
        n_waits = (
            self.register_session_retries - 1
        )  # -1 = No wait time after the last retry
        factor = self.register_session_retry_factor

        # Generate wait times for each retry attempt.
        # Wait times are calculated using exponential function. For factor=1 all wait times
        # will be equal to `wait`. For any number of retries the last wait time will be
        # equal to `wait` and for retries>2 the first wait time will be equal to `wait / factor`.
        wait_times = iter(
            factor ** (n / n_waits - 1) * wait_time for n in range(0, n_waits + 1)
        )

        for attempt in range(self.register_session_retries + 1):
            try:
                smbclient.register_session(
                    self.host,
                    username=self.username,
                    password=self.password,
                    port=self._port,
                    encrypt=self.encrypt,
                    connection_timeout=self.timeout,
                )
                return
            except (
                smbprotocol.exceptions.SMBAuthenticationError,
                smbprotocol.exceptions.LogonFailure,
            ):
                # These exceptions should not be repeated, as they clearly indicate
                # that the credentials are invalid and not a network issue.
                raise
            except ValueError as exc:
                if re.findall(r"\[Errno -\d+]", str(exc)):
                    # This exception is raised by the smbprotocol.transport:Tcp.connect
                    # and originates from socket.gaierror (OSError). These exceptions might
                    # be raised due to network instability. We will retry to connect.
                    retried_errors.append(exc)
                else:
                    # All another ValueError exceptions should be raised, as they are not
                    # related to network issues.
                    raise
            except Exception as exc:
                # Save the exception and retry to connect. This except might be dropped
                # in the future, once all exceptions suited for retry are identified.
                retried_errors.append(exc)

            if attempt < self.register_session_retries:
                time.sleep(next(wait_times))

        # Raise last exception to inform user about the connection issues.
        # Note: Should we use ExceptionGroup to raise all exceptions?
        raise retried_errors[-1]

    @classmethod
    def _strip_protocol(cls, path):
        return infer_storage_options(path)["path"]

    @staticmethod
    def _get_kwargs_from_urls(path):
        # smb://workgroup;user:password@host:port/share/folder/file.csv
        out = infer_storage_options(path)
        out.pop("path", None)
        out.pop("protocol", None)
        return out

    def mkdir(self, path, create_parents=True, **kwargs):
        wpath = _as_unc_path(self.host, path)
        if create_parents:
            smbclient.makedirs(wpath, exist_ok=False, port=self._port, **kwargs)
        else:
            smbclient.mkdir(wpath, port=self._port, **kwargs)

    def makedirs(self, path, exist_ok=False):
        if _share_has_path(path):
            wpath = _as_unc_path(self.host, path)
            smbclient.makedirs(wpath, exist_ok=exist_ok, port=self._port)

    def rmdir(self, path):
        if _share_has_path(path):
            wpath = _as_unc_path(self.host, path)
            smbclient.rmdir(wpath, port=self._port)

    def info(self, path, **kwargs):
        wpath = _as_unc_path(self.host, path)
        stats = smbclient.stat(wpath, port=self._port, **kwargs)
        if S_ISDIR(stats.st_mode):
            stype = "directory"
        elif S_ISLNK(stats.st_mode):
            stype = "link"
        else:
            stype = "file"
        res = {
            "name": path + "/" if stype == "directory" else path,
            "size": stats.st_size,
            "type": stype,
            "uid": stats.st_uid,
            "gid": stats.st_gid,
            "time": stats.st_atime,
            "mtime": stats.st_mtime,
        }
        return res

    def created(self, path):
        """Return the created timestamp of a file as a datetime.datetime"""
        wpath = _as_unc_path(self.host, path)
        stats = smbclient.stat(wpath, port=self._port)
        return datetime.datetime.fromtimestamp(stats.st_ctime, tz=datetime.timezone.utc)

    def modified(self, path):
        """Return the modified timestamp of a file as a datetime.datetime"""
        wpath = _as_unc_path(self.host, path)
        stats = smbclient.stat(wpath, port=self._port)
        return datetime.datetime.fromtimestamp(stats.st_mtime, tz=datetime.timezone.utc)

    def ls(self, path, detail=True, **kwargs):
        unc = _as_unc_path(self.host, path)
        listed = smbclient.listdir(unc, port=self._port, **kwargs)
        dirs = ["/".join([path.rstrip("/"), p]) for p in listed]
        if detail:
            dirs = [self.info(d) for d in dirs]
        return dirs

    # pylint: disable=too-many-arguments
    def _open(
        self,
        path,
        mode="rb",
        block_size=-1,
        autocommit=True,
        cache_options=None,
        **kwargs,
    ):
        """
        block_size: int or None
            If 0, no buffering, 1, line buffering, >1, buffer that many bytes

        Notes
        -----
        By specifying 'share_access' in 'kwargs' it is possible to override the
        default shared access setting applied in the constructor of this object.
        """
        if self.auto_mkdir and "w" in mode:
            self.makedirs(self._parent(path), exist_ok=True)
        bls = block_size if block_size is not None and block_size >= 0 else -1
        wpath = _as_unc_path(self.host, path)
        share_access = kwargs.pop("share_access", self.share_access)
        if "w" in mode and autocommit is False:
            temp = _as_temp_path(self.host, path, self.temppath)
            return SMBFileOpener(
                wpath, temp, mode, port=self._port, block_size=bls, **kwargs
            )
        return smbclient.open_file(
            wpath,
            mode,
            buffering=bls,
            share_access=share_access,
            port=self._port,
            **kwargs,
        )

    def copy(self, path1, path2, **kwargs):
        """Copy within two locations in the same filesystem"""
        wpath1 = _as_unc_path(self.host, path1)
        wpath2 = _as_unc_path(self.host, path2)
        if self.auto_mkdir:
            self.makedirs(self._parent(path2), exist_ok=True)
        smbclient.copyfile(wpath1, wpath2, port=self._port, **kwargs)

    def _rm(self, path):
        if _share_has_path(path):
            wpath = _as_unc_path(self.host, path)
            stats = smbclient.stat(wpath, port=self._port)
            if S_ISDIR(stats.st_mode):
                smbclient.rmdir(wpath, port=self._port)
            else:
                smbclient.remove(wpath, port=self._port)

    def mv(self, path1, path2, recursive=None, maxdepth=None, **kwargs):
        wpath1 = _as_unc_path(self.host, path1)
        wpath2 = _as_unc_path(self.host, path2)
        smbclient.rename(wpath1, wpath2, port=self._port, **kwargs)


def _as_unc_path(host, path):
    rpath = path.replace("/", "\\")
    unc = f"\\\\{host}{rpath}"
    return unc


def _as_temp_path(host, path, temppath):
    share = path.split("/")[1]
    temp_file = f"/{share}{temppath}/{uuid.uuid4()}"
    unc = _as_unc_path(host, temp_file)
    return unc


def _share_has_path(path):
    parts = path.count("/")
    if path.endswith("/"):
        return parts > 2
    return parts > 1


class SMBFileOpener:
    """writes to remote temporary file, move on commit"""

    def __init__(self, path, temp, mode, port=445, block_size=-1, **kwargs):
        self.path = path
        self.temp = temp
        self.mode = mode
        self.block_size = block_size
        self.kwargs = kwargs
        self.smbfile = None
        self._incontext = False
        self.port = port
        self._open()

    def _open(self):
        if self.smbfile is None or self.smbfile.closed:
            self.smbfile = smbclient.open_file(
                self.temp,
                self.mode,
                port=self.port,
                buffering=self.block_size,
                **self.kwargs,
            )

    def commit(self):
        """Move temp file to definitive on success."""
        # TODO: use transaction support in SMB protocol
        smbclient.replace(self.temp, self.path, port=self.port)

    def discard(self):
        """Remove the temp file on failure."""
        smbclient.remove(self.temp, port=self.port)

    def __fspath__(self):
        return self.path

    def __iter__(self):
        return self.smbfile.__iter__()

    def __getattr__(self, item):
        return getattr(self.smbfile, item)

    def __enter__(self):
        self._incontext = True
        return self.smbfile.__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        self._incontext = False
        self.smbfile.__exit__(exc_type, exc_value, traceback)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta2\services\model_service\transports\rest.py ===
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

import dataclasses
import json  # type: ignore
import re
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union
import warnings

from google.api_core import gapic_v1, path_template, rest_helpers, rest_streaming
from google.api_core import exceptions as core_exceptions
from google.api_core import retry as retries
from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
from google.auth.transport.requests import AuthorizedSession  # type: ignore
from google.protobuf import json_format
import grpc  # type: ignore
from requests import __version__ as requests_version

try:
    OptionalRetry = Union[retries.Retry, gapic_v1.method._MethodDefault, None]
except AttributeError:  # pragma: NO COVER
    OptionalRetry = Union[retries.Retry, object, None]  # type: ignore


from google.ai.generativelanguage_v1beta2.types import model, model_service

from .base import DEFAULT_CLIENT_INFO as BASE_DEFAULT_CLIENT_INFO
from .base import ModelServiceTransport

DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=BASE_DEFAULT_CLIENT_INFO.gapic_version,
    grpc_version=None,
    rest_version=requests_version,
)


class ModelServiceRestInterceptor:
    """Interceptor for ModelService.

    Interceptors are used to manipulate requests, request metadata, and responses
    in arbitrary ways.
    Example use cases include:
    * Logging
    * Verifying requests according to service or custom semantics
    * Stripping extraneous information from responses

    These use cases and more can be enabled by injecting an
    instance of a custom subclass when constructing the ModelServiceRestTransport.

    .. code-block:: python
        class MyCustomModelServiceInterceptor(ModelServiceRestInterceptor):
            def pre_get_model(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_get_model(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_list_models(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_list_models(self, response):
                logging.log(f"Received response: {response}")
                return response

        transport = ModelServiceRestTransport(interceptor=MyCustomModelServiceInterceptor())
        client = ModelServiceClient(transport=transport)


    """

    def pre_get_model(
        self,
        request: model_service.GetModelRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[model_service.GetModelRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for get_model

        Override in a subclass to manipulate the request or metadata
        before they are sent to the ModelService server.
        """
        return request, metadata

    def post_get_model(self, response: model.Model) -> model.Model:
        """Post-rpc interceptor for get_model

        Override in a subclass to manipulate the response
        after it is returned by the ModelService server but before
        it is returned to user code.
        """
        return response

    def pre_list_models(
        self,
        request: model_service.ListModelsRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[model_service.ListModelsRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for list_models

        Override in a subclass to manipulate the request or metadata
        before they are sent to the ModelService server.
        """
        return request, metadata

    def post_list_models(
        self, response: model_service.ListModelsResponse
    ) -> model_service.ListModelsResponse:
        """Post-rpc interceptor for list_models

        Override in a subclass to manipulate the response
        after it is returned by the ModelService server but before
        it is returned to user code.
        """
        return response


@dataclasses.dataclass
class ModelServiceRestStub:
    _session: AuthorizedSession
    _host: str
    _interceptor: ModelServiceRestInterceptor


class ModelServiceRestTransport(ModelServiceTransport):
    """REST backend transport for ModelService.

    Provides methods for getting metadata information about
    Generative Models.

    This class defines the same methods as the primary client, so the
    primary client can load the underlying transport implementation
    and call it.

    It sends JSON representations of protocol buffers over HTTP/1.1

    """

    def __init__(
        self,
        *,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        client_cert_source_for_mtls: Optional[Callable[[], Tuple[bytes, bytes]]] = None,
        quota_project_id: Optional[str] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
        always_use_jwt_access: Optional[bool] = False,
        url_scheme: str = "https",
        interceptor: Optional[ModelServiceRestInterceptor] = None,
        api_audience: Optional[str] = None,
    ) -> None:
        """Instantiate the transport.

        Args:
            host (Optional[str]):
                 The hostname to connect to (default: 'generativelanguage.googleapis.com').
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.

            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
                This argument is ignored if ``channel`` is provided.
            scopes (Optional(Sequence[str])): A list of scopes. This argument is
                ignored if ``channel`` is provided.
            client_cert_source_for_mtls (Callable[[], Tuple[bytes, bytes]]): Client
                certificate to configure mutual TLS HTTP channel. It is ignored
                if ``channel`` is provided.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you are developing
                your own client library.
            always_use_jwt_access (Optional[bool]): Whether self signed JWT should
                be used for service account credentials.
            url_scheme: the protocol scheme for the API endpoint.  Normally
                "https", but for testing or local servers,
                "http" can be specified.
        """
        # Run the base constructor
        # TODO(yon-mg): resolve other ctor params i.e. scopes, quota, etc.
        # TODO: When custom host (api_endpoint) is set, `scopes` must *also* be set on the
        # credentials object
        maybe_url_match = re.match("^(?P<scheme>http(?:s)?://)?(?P<host>.*)$", host)
        if maybe_url_match is None:
            raise ValueError(
                f"Unexpected hostname structure: {host}"
            )  # pragma: NO COVER

        url_match_items = maybe_url_match.groupdict()

        host = f"{url_scheme}://{host}" if not url_match_items["scheme"] else host

        super().__init__(
            host=host,
            credentials=credentials,
            client_info=client_info,
            always_use_jwt_access=always_use_jwt_access,
            api_audience=api_audience,
        )
        self._session = AuthorizedSession(
            self._credentials, default_host=self.DEFAULT_HOST
        )
        if client_cert_source_for_mtls:
            self._session.configure_mtls_channel(client_cert_source_for_mtls)
        self._interceptor = interceptor or ModelServiceRestInterceptor()
        self._prep_wrapped_messages(client_info)

    class _GetModel(ModelServiceRestStub):
        def __hash__(self):
            return hash("GetModel")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] = {}

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {
                k: v
                for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items()
                if k not in message_dict
            }

        def __call__(
            self,
            request: model_service.GetModelRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> model.Model:
            r"""Call the get model method over HTTP.

            Args:
                request (~.model_service.GetModelRequest):
                    The request object. Request for getting information about
                a specific Model.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.model.Model:
                    Information about a Generative
                Language Model.

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "get",
                    "uri": "/v1beta2/{name=models/*}",
                },
            ]
            request, metadata = self._interceptor.pre_get_model(request, metadata)
            pb_request = model_service.GetModelRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )
            query_params.update(self._get_unset_required_fields(query_params))

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = model.Model()
            pb_resp = model.Model.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_get_model(resp)
            return resp

    class _ListModels(ModelServiceRestStub):
        def __hash__(self):
            return hash("ListModels")

        def __call__(
            self,
            request: model_service.ListModelsRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> model_service.ListModelsResponse:
            r"""Call the list models method over HTTP.

            Args:
                request (~.model_service.ListModelsRequest):
                    The request object. Request for listing all Models.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.model_service.ListModelsResponse:
                    Response from ``ListModel`` containing a paginated list
                of Models.

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "get",
                    "uri": "/v1beta2/models",
                },
            ]
            request, metadata = self._interceptor.pre_list_models(request, metadata)
            pb_request = model_service.ListModelsRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = model_service.ListModelsResponse()
            pb_resp = model_service.ListModelsResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_list_models(resp)
            return resp

    @property
    def get_model(self) -> Callable[[model_service.GetModelRequest], model.Model]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._GetModel(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def list_models(
        self,
    ) -> Callable[[model_service.ListModelsRequest], model_service.ListModelsResponse]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._ListModels(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def kind(self) -> str:
        return "rest"

    def close(self):
        self._session.close()


__all__ = ("ModelServiceRestTransport",)

# === NexusCore/openenv\Lib\site-packages\litellm\llms\vertex_ai\context_caching\vertex_ai_context_caching.py ===
from typing import List, Literal, Optional, Tuple, Union

import httpx

import litellm
from litellm.caching.caching import Cache, LiteLLMCacheType
from litellm.litellm_core_utils.litellm_logging import Logging
from litellm.llms.custom_httpx.http_handler import (
    AsyncHTTPHandler,
    HTTPHandler,
    get_async_httpx_client,
)
from litellm.llms.openai.openai import AllMessageValues
from litellm.types.llms.vertex_ai import (
    CachedContentListAllResponseBody,
    VertexAICachedContentResponseObject,
)

from ..common_utils import VertexAIError
from ..vertex_llm_base import VertexBase
from .transformation import (
    separate_cached_messages,
    transform_openai_messages_to_gemini_context_caching,
)

local_cache_obj = Cache(
    type=LiteLLMCacheType.LOCAL
)  # only used for calling 'get_cache_key' function


class ContextCachingEndpoints(VertexBase):
    """
    Covers context caching endpoints for Vertex AI + Google AI Studio

    v0: covers Google AI Studio
    """

    def __init__(self) -> None:
        pass

    def _get_token_and_url_context_caching(
        self,
        gemini_api_key: Optional[str],
        custom_llm_provider: Literal["gemini"],
        api_base: Optional[str],
    ) -> Tuple[Optional[str], str]:
        """
        Internal function. Returns the token and url for the call.

        Handles logic if it's google ai studio vs. vertex ai.

        Returns
            token, url
        """
        if custom_llm_provider == "gemini":
            auth_header = None
            endpoint = "cachedContents"
            url = "https://generativelanguage.googleapis.com/v1beta/{}?key={}".format(
                endpoint, gemini_api_key
            )

        else:
            raise NotImplementedError

        return self._check_custom_proxy(
            api_base=api_base,
            custom_llm_provider=custom_llm_provider,
            gemini_api_key=gemini_api_key,
            endpoint=endpoint,
            stream=None,
            auth_header=auth_header,
            url=url,
        )

    def check_cache(
        self,
        cache_key: str,
        client: HTTPHandler,
        headers: dict,
        api_key: str,
        api_base: Optional[str],
        logging_obj: Logging,
    ) -> Optional[str]:
        """
        Checks if content already cached.

        Currently, checks cache list, for cache key == displayName, since Google doesn't let us set the name of the cache (their API docs are out of sync with actual implementation).

        Returns
        - cached_content_name - str - cached content name stored on google. (if found.)
        OR
        - None
        """

        _, url = self._get_token_and_url_context_caching(
            gemini_api_key=api_key,
            custom_llm_provider="gemini",
            api_base=api_base,
        )
        try:
            ## LOGGING
            logging_obj.pre_call(
                input="",
                api_key="",
                additional_args={
                    "complete_input_dict": {},
                    "api_base": url,
                    "headers": headers,
                },
            )

            resp = client.get(url=url, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                return None
            raise VertexAIError(
                status_code=e.response.status_code, message=e.response.text
            )
        except Exception as e:
            raise VertexAIError(status_code=500, message=str(e))
        raw_response = resp.json()
        logging_obj.post_call(original_response=raw_response)

        if "cachedContents" not in raw_response:
            return None

        all_cached_items = CachedContentListAllResponseBody(**raw_response)

        if "cachedContents" not in all_cached_items:
            return None

        for cached_item in all_cached_items["cachedContents"]:
            display_name = cached_item.get("displayName")
            if display_name is not None and display_name == cache_key:
                return cached_item.get("name")

        return None

    async def async_check_cache(
        self,
        cache_key: str,
        client: AsyncHTTPHandler,
        headers: dict,
        api_key: str,
        api_base: Optional[str],
        logging_obj: Logging,
    ) -> Optional[str]:
        """
        Checks if content already cached.

        Currently, checks cache list, for cache key == displayName, since Google doesn't let us set the name of the cache (their API docs are out of sync with actual implementation).

        Returns
        - cached_content_name - str - cached content name stored on google. (if found.)
        OR
        - None
        """

        _, url = self._get_token_and_url_context_caching(
            gemini_api_key=api_key,
            custom_llm_provider="gemini",
            api_base=api_base,
        )
        try:
            ## LOGGING
            logging_obj.pre_call(
                input="",
                api_key="",
                additional_args={
                    "complete_input_dict": {},
                    "api_base": url,
                    "headers": headers,
                },
            )

            resp = await client.get(url=url, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                return None
            raise VertexAIError(
                status_code=e.response.status_code, message=e.response.text
            )
        except Exception as e:
            raise VertexAIError(status_code=500, message=str(e))
        raw_response = resp.json()
        logging_obj.post_call(original_response=raw_response)

        if "cachedContents" not in raw_response:
            return None

        all_cached_items = CachedContentListAllResponseBody(**raw_response)

        if "cachedContents" not in all_cached_items:
            return None

        for cached_item in all_cached_items["cachedContents"]:
            display_name = cached_item.get("displayName")
            if display_name is not None and display_name == cache_key:
                return cached_item.get("name")

        return None

    def check_and_create_cache(
        self,
        messages: List[AllMessageValues],  # receives openai format messages
        api_key: str,
        api_base: Optional[str],
        model: str,
        client: Optional[HTTPHandler],
        timeout: Optional[Union[float, httpx.Timeout]],
        logging_obj: Logging,
        extra_headers: Optional[dict] = None,
        cached_content: Optional[str] = None,
    ) -> Tuple[List[AllMessageValues], Optional[str]]:
        """
        Receives
        - messages: List of dict - messages in the openai format

        Returns
        - messages - List[dict] - filtered list of messages in the openai format.
        - cached_content - str - the cache content id, to be passed in the gemini request body

        Follows - https://ai.google.dev/api/caching#request-body
        """
        if cached_content is not None:
            return messages, cached_content

        ## AUTHORIZATION ##
        token, url = self._get_token_and_url_context_caching(
            gemini_api_key=api_key,
            custom_llm_provider="gemini",
            api_base=api_base,
        )

        headers = {
            "Content-Type": "application/json",
        }
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        if extra_headers is not None:
            headers.update(extra_headers)

        if client is None or not isinstance(client, HTTPHandler):
            _params = {}
            if timeout is not None:
                if isinstance(timeout, float) or isinstance(timeout, int):
                    timeout = httpx.Timeout(timeout)
                _params["timeout"] = timeout
            client = HTTPHandler(**_params)  # type: ignore
        else:
            client = client

        cached_messages, non_cached_messages = separate_cached_messages(
            messages=messages
        )

        if len(cached_messages) == 0:
            return messages, None

        ## CHECK IF CACHED ALREADY
        generated_cache_key = local_cache_obj.get_cache_key(messages=cached_messages)
        google_cache_name = self.check_cache(
            cache_key=generated_cache_key,
            client=client,
            headers=headers,
            api_key=api_key,
            api_base=api_base,
            logging_obj=logging_obj,
        )
        if google_cache_name:
            return non_cached_messages, google_cache_name

        ## TRANSFORM REQUEST
        cached_content_request_body = (
            transform_openai_messages_to_gemini_context_caching(
                model=model, messages=cached_messages, cache_key=generated_cache_key
            )
        )

        ## LOGGING
        logging_obj.pre_call(
            input=messages,
            api_key="",
            additional_args={
                "complete_input_dict": cached_content_request_body,
                "api_base": url,
                "headers": headers,
            },
        )

        try:
            response = client.post(
                url=url, headers=headers, json=cached_content_request_body  # type: ignore
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as err:
            error_code = err.response.status_code
            raise VertexAIError(status_code=error_code, message=err.response.text)
        except httpx.TimeoutException:
            raise VertexAIError(status_code=408, message="Timeout error occurred.")

        raw_response_cached = response.json()
        cached_content_response_obj = VertexAICachedContentResponseObject(
            name=raw_response_cached.get("name"), model=raw_response_cached.get("model")
        )
        return (non_cached_messages, cached_content_response_obj["name"])

    async def async_check_and_create_cache(
        self,
        messages: List[AllMessageValues],  # receives openai format messages
        api_key: str,
        api_base: Optional[str],
        model: str,
        client: Optional[AsyncHTTPHandler],
        timeout: Optional[Union[float, httpx.Timeout]],
        logging_obj: Logging,
        extra_headers: Optional[dict] = None,
        cached_content: Optional[str] = None,
    ) -> Tuple[List[AllMessageValues], Optional[str]]:
        """
        Receives
        - messages: List of dict - messages in the openai format

        Returns
        - messages - List[dict] - filtered list of messages in the openai format.
        - cached_content - str - the cache content id, to be passed in the gemini request body

        Follows - https://ai.google.dev/api/caching#request-body
        """
        if cached_content is not None:
            return messages, cached_content

        cached_messages, non_cached_messages = separate_cached_messages(
            messages=messages
        )

        if len(cached_messages) == 0:
            return messages, None

        ## AUTHORIZATION ##
        token, url = self._get_token_and_url_context_caching(
            gemini_api_key=api_key,
            custom_llm_provider="gemini",
            api_base=api_base,
        )

        headers = {
            "Content-Type": "application/json",
        }
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        if extra_headers is not None:
            headers.update(extra_headers)

        if client is None or not isinstance(client, AsyncHTTPHandler):
            client = get_async_httpx_client(
                params={"timeout": timeout}, llm_provider=litellm.LlmProviders.VERTEX_AI
            )
        else:
            client = client

        ## CHECK IF CACHED ALREADY
        generated_cache_key = local_cache_obj.get_cache_key(messages=cached_messages)
        google_cache_name = await self.async_check_cache(
            cache_key=generated_cache_key,
            client=client,
            headers=headers,
            api_key=api_key,
            api_base=api_base,
            logging_obj=logging_obj,
        )
        if google_cache_name:
            return non_cached_messages, google_cache_name

        ## TRANSFORM REQUEST
        cached_content_request_body = (
            transform_openai_messages_to_gemini_context_caching(
                model=model, messages=cached_messages, cache_key=generated_cache_key
            )
        )

        ## LOGGING
        logging_obj.pre_call(
            input=messages,
            api_key="",
            additional_args={
                "complete_input_dict": cached_content_request_body,
                "api_base": url,
                "headers": headers,
            },
        )

        try:
            response = await client.post(
                url=url, headers=headers, json=cached_content_request_body  # type: ignore
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as err:
            error_code = err.response.status_code
            raise VertexAIError(status_code=error_code, message=err.response.text)
        except httpx.TimeoutException:
            raise VertexAIError(status_code=408, message="Timeout error occurred.")

        raw_response_cached = response.json()
        cached_content_response_obj = VertexAICachedContentResponseObject(
            name=raw_response_cached.get("name"), model=raw_response_cached.get("model")
        )
        return (non_cached_messages, cached_content_response_obj["name"])

    def get_cache(self):
        pass

    async def async_get_cache(self):
        pass