
# === NexusCore/tools\exports\export_20250803_114325\combined_165.py ===

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\resolvelib\resolvers.py ===
import collections
import itertools
import operator

from .providers import AbstractResolver
from .structs import DirectedGraph, IteratorMapping, build_iter_view

RequirementInformation = collections.namedtuple(
    "RequirementInformation", ["requirement", "parent"]
)


class ResolverException(Exception):
    """A base class for all exceptions raised by this module.

    Exceptions derived by this class should all be handled in this module. Any
    bubbling pass the resolver should be treated as a bug.
    """


class RequirementsConflicted(ResolverException):
    def __init__(self, criterion):
        super(RequirementsConflicted, self).__init__(criterion)
        self.criterion = criterion

    def __str__(self):
        return "Requirements conflict: {}".format(
            ", ".join(repr(r) for r in self.criterion.iter_requirement()),
        )


class InconsistentCandidate(ResolverException):
    def __init__(self, candidate, criterion):
        super(InconsistentCandidate, self).__init__(candidate, criterion)
        self.candidate = candidate
        self.criterion = criterion

    def __str__(self):
        return "Provided candidate {!r} does not satisfy {}".format(
            self.candidate,
            ", ".join(repr(r) for r in self.criterion.iter_requirement()),
        )


class Criterion(object):
    """Representation of possible resolution results of a package.

    This holds three attributes:

    * `information` is a collection of `RequirementInformation` pairs.
      Each pair is a requirement contributing to this criterion, and the
      candidate that provides the requirement.
    * `incompatibilities` is a collection of all known not-to-work candidates
      to exclude from consideration.
    * `candidates` is a collection containing all possible candidates deducted
      from the union of contributing requirements and known incompatibilities.
      It should never be empty, except when the criterion is an attribute of a
      raised `RequirementsConflicted` (in which case it is always empty).

    .. note::
        This class is intended to be externally immutable. **Do not** mutate
        any of its attribute containers.
    """

    def __init__(self, candidates, information, incompatibilities):
        self.candidates = candidates
        self.information = information
        self.incompatibilities = incompatibilities

    def __repr__(self):
        requirements = ", ".join(
            "({!r}, via={!r})".format(req, parent)
            for req, parent in self.information
        )
        return "Criterion({})".format(requirements)

    def iter_requirement(self):
        return (i.requirement for i in self.information)

    def iter_parent(self):
        return (i.parent for i in self.information)


class ResolutionError(ResolverException):
    pass


class ResolutionImpossible(ResolutionError):
    def __init__(self, causes):
        super(ResolutionImpossible, self).__init__(causes)
        # causes is a list of RequirementInformation objects
        self.causes = causes


class ResolutionTooDeep(ResolutionError):
    def __init__(self, round_count):
        super(ResolutionTooDeep, self).__init__(round_count)
        self.round_count = round_count


# Resolution state in a round.
State = collections.namedtuple("State", "mapping criteria backtrack_causes")


class Resolution(object):
    """Stateful resolution object.

    This is designed as a one-off object that holds information to kick start
    the resolution process, and holds the results afterwards.
    """

    def __init__(self, provider, reporter):
        self._p = provider
        self._r = reporter
        self._states = []

    @property
    def state(self):
        try:
            return self._states[-1]
        except IndexError:
            raise AttributeError("state")

    def _push_new_state(self):
        """Push a new state into history.

        This new state will be used to hold resolution results of the next
        coming round.
        """
        base = self._states[-1]
        state = State(
            mapping=base.mapping.copy(),
            criteria=base.criteria.copy(),
            backtrack_causes=base.backtrack_causes[:],
        )
        self._states.append(state)

    def _add_to_criteria(self, criteria, requirement, parent):
        self._r.adding_requirement(requirement=requirement, parent=parent)

        identifier = self._p.identify(requirement_or_candidate=requirement)
        criterion = criteria.get(identifier)
        if criterion:
            incompatibilities = list(criterion.incompatibilities)
        else:
            incompatibilities = []

        matches = self._p.find_matches(
            identifier=identifier,
            requirements=IteratorMapping(
                criteria,
                operator.methodcaller("iter_requirement"),
                {identifier: [requirement]},
            ),
            incompatibilities=IteratorMapping(
                criteria,
                operator.attrgetter("incompatibilities"),
                {identifier: incompatibilities},
            ),
        )

        if criterion:
            information = list(criterion.information)
            information.append(RequirementInformation(requirement, parent))
        else:
            information = [RequirementInformation(requirement, parent)]

        criterion = Criterion(
            candidates=build_iter_view(matches),
            information=information,
            incompatibilities=incompatibilities,
        )
        if not criterion.candidates:
            raise RequirementsConflicted(criterion)
        criteria[identifier] = criterion

    def _remove_information_from_criteria(self, criteria, parents):
        """Remove information from parents of criteria.

        Concretely, removes all values from each criterion's ``information``
        field that have one of ``parents`` as provider of the requirement.

        :param criteria: The criteria to update.
        :param parents: Identifiers for which to remove information from all criteria.
        """
        if not parents:
            return
        for key, criterion in criteria.items():
            criteria[key] = Criterion(
                criterion.candidates,
                [
                    information
                    for information in criterion.information
                    if (
                        information.parent is None
                        or self._p.identify(information.parent) not in parents
                    )
                ],
                criterion.incompatibilities,
            )

    def _get_preference(self, name):
        return self._p.get_preference(
            identifier=name,
            resolutions=self.state.mapping,
            candidates=IteratorMapping(
                self.state.criteria,
                operator.attrgetter("candidates"),
            ),
            information=IteratorMapping(
                self.state.criteria,
                operator.attrgetter("information"),
            ),
            backtrack_causes=self.state.backtrack_causes,
        )

    def _is_current_pin_satisfying(self, name, criterion):
        try:
            current_pin = self.state.mapping[name]
        except KeyError:
            return False
        return all(
            self._p.is_satisfied_by(requirement=r, candidate=current_pin)
            for r in criterion.iter_requirement()
        )

    def _get_updated_criteria(self, candidate):
        criteria = self.state.criteria.copy()
        for requirement in self._p.get_dependencies(candidate=candidate):
            self._add_to_criteria(criteria, requirement, parent=candidate)
        return criteria

    def _attempt_to_pin_criterion(self, name):
        criterion = self.state.criteria[name]

        causes = []
        for candidate in criterion.candidates:
            try:
                criteria = self._get_updated_criteria(candidate)
            except RequirementsConflicted as e:
                self._r.rejecting_candidate(e.criterion, candidate)
                causes.append(e.criterion)
                continue

            # Check the newly-pinned candidate actually works. This should
            # always pass under normal circumstances, but in the case of a
            # faulty provider, we will raise an error to notify the implementer
            # to fix find_matches() and/or is_satisfied_by().
            satisfied = all(
                self._p.is_satisfied_by(requirement=r, candidate=candidate)
                for r in criterion.iter_requirement()
            )
            if not satisfied:
                raise InconsistentCandidate(candidate, criterion)

            self._r.pinning(candidate=candidate)
            self.state.criteria.update(criteria)

            # Put newly-pinned candidate at the end. This is essential because
            # backtracking looks at this mapping to get the last pin.
            self.state.mapping.pop(name, None)
            self.state.mapping[name] = candidate

            return []

        # All candidates tried, nothing works. This criterion is a dead
        # end, signal for backtracking.
        return causes

    def _backjump(self, causes):
        """Perform backjumping.

        When we enter here, the stack is like this::

            [ state Z ]
            [ state Y ]
            [ state X ]
            .... earlier states are irrelevant.

        1. No pins worked for Z, so it does not have a pin.
        2. We want to reset state Y to unpinned, and pin another candidate.
        3. State X holds what state Y was before the pin, but does not
           have the incompatibility information gathered in state Y.

        Each iteration of the loop will:

        1.  Identify Z. The incompatibility is not always caused by the latest
            state. For example, given three requirements A, B and C, with
            dependencies A1, B1 and C1, where A1 and B1 are incompatible: the
            last state might be related to C, so we want to discard the
            previous state.
        2.  Discard Z.
        3.  Discard Y but remember its incompatibility information gathered
            previously, and the failure we're dealing with right now.
        4.  Push a new state Y' based on X, and apply the incompatibility
            information from Y to Y'.
        5a. If this causes Y' to conflict, we need to backtrack again. Make Y'
            the new Z and go back to step 2.
        5b. If the incompatibilities apply cleanly, end backtracking.
        """
        incompatible_reqs = itertools.chain(
            (c.parent for c in causes if c.parent is not None),
            (c.requirement for c in causes),
        )
        incompatible_deps = {self._p.identify(r) for r in incompatible_reqs}
        while len(self._states) >= 3:
            # Remove the state that triggered backtracking.
            del self._states[-1]

            # Ensure to backtrack to a state that caused the incompatibility
            incompatible_state = False
            while not incompatible_state:
                # Retrieve the last candidate pin and known incompatibilities.
                try:
                    broken_state = self._states.pop()
                    name, candidate = broken_state.mapping.popitem()
                except (IndexError, KeyError):
                    raise ResolutionImpossible(causes)
                current_dependencies = {
                    self._p.identify(d)
                    for d in self._p.get_dependencies(candidate)
                }
                incompatible_state = not current_dependencies.isdisjoint(
                    incompatible_deps
                )

            incompatibilities_from_broken = [
                (k, list(v.incompatibilities))
                for k, v in broken_state.criteria.items()
            ]

            # Also mark the newly known incompatibility.
            incompatibilities_from_broken.append((name, [candidate]))

            # Create a new state from the last known-to-work one, and apply
            # the previously gathered incompatibility information.
            def _patch_criteria():
                for k, incompatibilities in incompatibilities_from_broken:
                    if not incompatibilities:
                        continue
                    try:
                        criterion = self.state.criteria[k]
                    except KeyError:
                        continue
                    matches = self._p.find_matches(
                        identifier=k,
                        requirements=IteratorMapping(
                            self.state.criteria,
                            operator.methodcaller("iter_requirement"),
                        ),
                        incompatibilities=IteratorMapping(
                            self.state.criteria,
                            operator.attrgetter("incompatibilities"),
                            {k: incompatibilities},
                        ),
                    )
                    candidates = build_iter_view(matches)
                    if not candidates:
                        return False
                    incompatibilities.extend(criterion.incompatibilities)
                    self.state.criteria[k] = Criterion(
                        candidates=candidates,
                        information=list(criterion.information),
                        incompatibilities=incompatibilities,
                    )
                return True

            self._push_new_state()
            success = _patch_criteria()

            # It works! Let's work on this new state.
            if success:
                return True

            # State does not work after applying known incompatibilities.
            # Try the still previous state.

        # No way to backtrack anymore.
        return False

    def resolve(self, requirements, max_rounds):
        if self._states:
            raise RuntimeError("already resolved")

        self._r.starting()

        # Initialize the root state.
        self._states = [
            State(
                mapping=collections.OrderedDict(),
                criteria={},
                backtrack_causes=[],
            )
        ]
        for r in requirements:
            try:
                self._add_to_criteria(self.state.criteria, r, parent=None)
            except RequirementsConflicted as e:
                raise ResolutionImpossible(e.criterion.information)

        # The root state is saved as a sentinel so the first ever pin can have
        # something to backtrack to if it fails. The root state is basically
        # pinning the virtual "root" package in the graph.
        self._push_new_state()

        for round_index in range(max_rounds):
            self._r.starting_round(index=round_index)

            unsatisfied_names = [
                key
                for key, criterion in self.state.criteria.items()
                if not self._is_current_pin_satisfying(key, criterion)
            ]

            # All criteria are accounted for. Nothing more to pin, we are done!
            if not unsatisfied_names:
                self._r.ending(state=self.state)
                return self.state

            # keep track of satisfied names to calculate diff after pinning
            satisfied_names = set(self.state.criteria.keys()) - set(
                unsatisfied_names
            )

            # Choose the most preferred unpinned criterion to try.
            name = min(unsatisfied_names, key=self._get_preference)
            failure_causes = self._attempt_to_pin_criterion(name)

            if failure_causes:
                causes = [i for c in failure_causes for i in c.information]
                # Backjump if pinning fails. The backjump process puts us in
                # an unpinned state, so we can work on it in the next round.
                self._r.resolving_conflicts(causes=causes)
                success = self._backjump(causes)
                self.state.backtrack_causes[:] = causes

                # Dead ends everywhere. Give up.
                if not success:
                    raise ResolutionImpossible(self.state.backtrack_causes)
            else:
                # discard as information sources any invalidated names
                # (unsatisfied names that were previously satisfied)
                newly_unsatisfied_names = {
                    key
                    for key, criterion in self.state.criteria.items()
                    if key in satisfied_names
                    and not self._is_current_pin_satisfying(key, criterion)
                }
                self._remove_information_from_criteria(
                    self.state.criteria, newly_unsatisfied_names
                )
                # Pinning was successful. Push a new state to do another pin.
                self._push_new_state()

            self._r.ending_round(index=round_index, state=self.state)

        raise ResolutionTooDeep(max_rounds)


def _has_route_to_root(criteria, key, all_keys, connected):
    if key in connected:
        return True
    if key not in criteria:
        return False
    for p in criteria[key].iter_parent():
        try:
            pkey = all_keys[id(p)]
        except KeyError:
            continue
        if pkey in connected:
            connected.add(key)
            return True
        if _has_route_to_root(criteria, pkey, all_keys, connected):
            connected.add(key)
            return True
    return False


Result = collections.namedtuple("Result", "mapping graph criteria")


def _build_result(state):
    mapping = state.mapping
    all_keys = {id(v): k for k, v in mapping.items()}
    all_keys[id(None)] = None

    graph = DirectedGraph()
    graph.add(None)  # Sentinel as root dependencies' parent.

    connected = {None}
    for key, criterion in state.criteria.items():
        if not _has_route_to_root(state.criteria, key, all_keys, connected):
            continue
        if key not in graph:
            graph.add(key)
        for p in criterion.iter_parent():
            try:
                pkey = all_keys[id(p)]
            except KeyError:
                continue
            if pkey not in graph:
                graph.add(pkey)
            graph.connect(pkey, key)

    return Result(
        mapping={k: v for k, v in mapping.items() if k in connected},
        graph=graph,
        criteria=state.criteria,
    )


class Resolver(AbstractResolver):
    """The thing that performs the actual resolution work."""

    base_exception = ResolverException

    def resolve(self, requirements, max_rounds=100):
        """Take a collection of constraints, spit out the resolution result.

        The return value is a representation to the final resolution result. It
        is a tuple subclass with three public members:

        * `mapping`: A dict of resolved candidates. Each key is an identifier
            of a requirement (as returned by the provider's `identify` method),
            and the value is the resolved candidate.
        * `graph`: A `DirectedGraph` instance representing the dependency tree.
            The vertices are keys of `mapping`, and each edge represents *why*
            a particular package is included. A special vertex `None` is
            included to represent parents of user-supplied requirements.
        * `criteria`: A dict of "criteria" that hold detailed information on
            how edges in the graph are derived. Each key is an identifier of a
            requirement, and the value is a `Criterion` instance.

        The following exceptions may be raised if a resolution cannot be found:

        * `ResolutionImpossible`: A resolution cannot be found for the given
            combination of requirements. The `causes` attribute of the
            exception is a list of (requirement, parent), giving the
            requirements that could not be satisfied.
        * `ResolutionTooDeep`: The dependency tree is too deeply nested and
            the resolver gave up. This is usually caused by a circular
            dependency, but you can try to resolve this by increasing the
            `max_rounds` argument.
        """
        resolution = Resolution(self.provider, self.reporter)
        state = resolution.resolve(requirements, max_rounds=max_rounds)
        return _build_result(state)

# === NexusCore/openenv\Lib\site-packages\pydantic\_internal\_generics.py ===
from __future__ import annotations

import sys
import types
import typing
from collections import ChainMap
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from itertools import zip_longest
from types import prepare_class
from typing import TYPE_CHECKING, Annotated, Any, TypeVar
from weakref import WeakValueDictionary

import typing_extensions
from typing_inspection import typing_objects
from typing_inspection.introspection import is_union_origin

from . import _typing_extra
from ._core_utils import get_type_ref
from ._forward_ref import PydanticRecursiveRef
from ._utils import all_identical, is_model_class

if sys.version_info >= (3, 10):
    from typing import _UnionGenericAlias  # type: ignore[attr-defined]

if TYPE_CHECKING:
    from ..main import BaseModel

GenericTypesCacheKey = tuple[Any, Any, tuple[Any, ...]]

# Note: We want to remove LimitedDict, but to do this, we'd need to improve the handling of generics caching.
#   Right now, to handle recursive generics, we some types must remain cached for brief periods without references.
#   By chaining the WeakValuesDict with a LimitedDict, we have a way to retain caching for all types with references,
#   while also retaining a limited number of types even without references. This is generally enough to build
#   specific recursive generic models without losing required items out of the cache.

KT = TypeVar('KT')
VT = TypeVar('VT')
_LIMITED_DICT_SIZE = 100


class LimitedDict(dict[KT, VT]):
    def __init__(self, size_limit: int = _LIMITED_DICT_SIZE) -> None:
        self.size_limit = size_limit
        super().__init__()

    def __setitem__(self, key: KT, value: VT, /) -> None:
        super().__setitem__(key, value)
        if len(self) > self.size_limit:
            excess = len(self) - self.size_limit + self.size_limit // 10
            to_remove = list(self.keys())[:excess]
            for k in to_remove:
                del self[k]


# weak dictionaries allow the dynamically created parametrized versions of generic models to get collected
# once they are no longer referenced by the caller.
GenericTypesCache = WeakValueDictionary[GenericTypesCacheKey, 'type[BaseModel]']

if TYPE_CHECKING:

    class DeepChainMap(ChainMap[KT, VT]):  # type: ignore
        ...

else:

    class DeepChainMap(ChainMap):
        """Variant of ChainMap that allows direct updates to inner scopes.

        Taken from https://docs.python.org/3/library/collections.html#collections.ChainMap,
        with some light modifications for this use case.
        """

        def clear(self) -> None:
            for mapping in self.maps:
                mapping.clear()

        def __setitem__(self, key: KT, value: VT) -> None:
            for mapping in self.maps:
                mapping[key] = value

        def __delitem__(self, key: KT) -> None:
            hit = False
            for mapping in self.maps:
                if key in mapping:
                    del mapping[key]
                    hit = True
            if not hit:
                raise KeyError(key)


# Despite the fact that LimitedDict _seems_ no longer necessary, I'm very nervous to actually remove it
# and discover later on that we need to re-add all this infrastructure...
# _GENERIC_TYPES_CACHE = DeepChainMap(GenericTypesCache(), LimitedDict())

_GENERIC_TYPES_CACHE: ContextVar[GenericTypesCache | None] = ContextVar('_GENERIC_TYPES_CACHE', default=None)


class PydanticGenericMetadata(typing_extensions.TypedDict):
    origin: type[BaseModel] | None  # analogous to typing._GenericAlias.__origin__
    args: tuple[Any, ...]  # analogous to typing._GenericAlias.__args__
    parameters: tuple[TypeVar, ...]  # analogous to typing.Generic.__parameters__


def create_generic_submodel(
    model_name: str, origin: type[BaseModel], args: tuple[Any, ...], params: tuple[Any, ...]
) -> type[BaseModel]:
    """Dynamically create a submodel of a provided (generic) BaseModel.

    This is used when producing concrete parametrizations of generic models. This function
    only *creates* the new subclass; the schema/validators/serialization must be updated to
    reflect a concrete parametrization elsewhere.

    Args:
        model_name: The name of the newly created model.
        origin: The base class for the new model to inherit from.
        args: A tuple of generic metadata arguments.
        params: A tuple of generic metadata parameters.

    Returns:
        The created submodel.
    """
    namespace: dict[str, Any] = {'__module__': origin.__module__}
    bases = (origin,)
    meta, ns, kwds = prepare_class(model_name, bases)
    namespace.update(ns)
    created_model = meta(
        model_name,
        bases,
        namespace,
        __pydantic_generic_metadata__={
            'origin': origin,
            'args': args,
            'parameters': params,
        },
        __pydantic_reset_parent_namespace__=False,
        **kwds,
    )

    model_module, called_globally = _get_caller_frame_info(depth=3)
    if called_globally:  # create global reference and therefore allow pickling
        object_by_reference = None
        reference_name = model_name
        reference_module_globals = sys.modules[created_model.__module__].__dict__
        while object_by_reference is not created_model:
            object_by_reference = reference_module_globals.setdefault(reference_name, created_model)
            reference_name += '_'

    return created_model


def _get_caller_frame_info(depth: int = 2) -> tuple[str | None, bool]:
    """Used inside a function to check whether it was called globally.

    Args:
        depth: The depth to get the frame.

    Returns:
        A tuple contains `module_name` and `called_globally`.

    Raises:
        RuntimeError: If the function is not called inside a function.
    """
    try:
        previous_caller_frame = sys._getframe(depth)
    except ValueError as e:
        raise RuntimeError('This function must be used inside another function') from e
    except AttributeError:  # sys module does not have _getframe function, so there's nothing we can do about it
        return None, False
    frame_globals = previous_caller_frame.f_globals
    return frame_globals.get('__name__'), previous_caller_frame.f_locals is frame_globals


DictValues: type[Any] = {}.values().__class__


def iter_contained_typevars(v: Any) -> Iterator[TypeVar]:
    """Recursively iterate through all subtypes and type args of `v` and yield any typevars that are found.

    This is inspired as an alternative to directly accessing the `__parameters__` attribute of a GenericAlias,
    since __parameters__ of (nested) generic BaseModel subclasses won't show up in that list.
    """
    if isinstance(v, TypeVar):
        yield v
    elif is_model_class(v):
        yield from v.__pydantic_generic_metadata__['parameters']
    elif isinstance(v, (DictValues, list)):
        for var in v:
            yield from iter_contained_typevars(var)
    else:
        args = get_args(v)
        for arg in args:
            yield from iter_contained_typevars(arg)


def get_args(v: Any) -> Any:
    pydantic_generic_metadata: PydanticGenericMetadata | None = getattr(v, '__pydantic_generic_metadata__', None)
    if pydantic_generic_metadata:
        return pydantic_generic_metadata.get('args')
    return typing_extensions.get_args(v)


def get_origin(v: Any) -> Any:
    pydantic_generic_metadata: PydanticGenericMetadata | None = getattr(v, '__pydantic_generic_metadata__', None)
    if pydantic_generic_metadata:
        return pydantic_generic_metadata.get('origin')
    return typing_extensions.get_origin(v)


def get_standard_typevars_map(cls: Any) -> dict[TypeVar, Any] | None:
    """Package a generic type's typevars and parametrization (if present) into a dictionary compatible with the
    `replace_types` function. Specifically, this works with standard typing generics and typing._GenericAlias.
    """
    origin = get_origin(cls)
    if origin is None:
        return None
    if not hasattr(origin, '__parameters__'):
        return None

    # In this case, we know that cls is a _GenericAlias, and origin is the generic type
    # So it is safe to access cls.__args__ and origin.__parameters__
    args: tuple[Any, ...] = cls.__args__  # type: ignore
    parameters: tuple[TypeVar, ...] = origin.__parameters__
    return dict(zip(parameters, args))


def get_model_typevars_map(cls: type[BaseModel]) -> dict[TypeVar, Any]:
    """Package a generic BaseModel's typevars and concrete parametrization (if present) into a dictionary compatible
    with the `replace_types` function.

    Since BaseModel.__class_getitem__ does not produce a typing._GenericAlias, and the BaseModel generic info is
    stored in the __pydantic_generic_metadata__ attribute, we need special handling here.
    """
    # TODO: This could be unified with `get_standard_typevars_map` if we stored the generic metadata
    #   in the __origin__, __args__, and __parameters__ attributes of the model.
    generic_metadata = cls.__pydantic_generic_metadata__
    origin = generic_metadata['origin']
    args = generic_metadata['args']
    if not args:
        # No need to go into `iter_contained_typevars`:
        return {}
    return dict(zip(iter_contained_typevars(origin), args))


def replace_types(type_: Any, type_map: Mapping[TypeVar, Any] | None) -> Any:
    """Return type with all occurrences of `type_map` keys recursively replaced with their values.

    Args:
        type_: The class or generic alias.
        type_map: Mapping from `TypeVar` instance to concrete types.

    Returns:
        A new type representing the basic structure of `type_` with all
        `typevar_map` keys recursively replaced.

    Example:
        ```python
        from typing import List, Union

        from pydantic._internal._generics import replace_types

        replace_types(tuple[str, Union[List[str], float]], {str: int})
        #> tuple[int, Union[List[int], float]]
        ```
    """
    if not type_map:
        return type_

    type_args = get_args(type_)
    origin_type = get_origin(type_)

    if typing_objects.is_annotated(origin_type):
        annotated_type, *annotations = type_args
        annotated_type = replace_types(annotated_type, type_map)
        # TODO remove parentheses when we drop support for Python 3.10:
        return Annotated[(annotated_type, *annotations)]

    # Having type args is a good indicator that this is a typing special form
    # instance or a generic alias of some sort.
    if type_args:
        resolved_type_args = tuple(replace_types(arg, type_map) for arg in type_args)
        if all_identical(type_args, resolved_type_args):
            # If all arguments are the same, there is no need to modify the
            # type or create a new object at all
            return type_

        if (
            origin_type is not None
            and isinstance(type_, _typing_extra.typing_base)
            and not isinstance(origin_type, _typing_extra.typing_base)
            and getattr(type_, '_name', None) is not None
        ):
            # In python < 3.9 generic aliases don't exist so any of these like `list`,
            # `type` or `collections.abc.Callable` need to be translated.
            # See: https://www.python.org/dev/peps/pep-0585
            origin_type = getattr(typing, type_._name)
        assert origin_type is not None

        if is_union_origin(origin_type):
            if any(typing_objects.is_any(arg) for arg in resolved_type_args):
                # `Any | T` ~ `Any`:
                resolved_type_args = (Any,)
            # `Never | T` ~ `T`:
            resolved_type_args = tuple(
                arg
                for arg in resolved_type_args
                if not (typing_objects.is_noreturn(arg) or typing_objects.is_never(arg))
            )

        # PEP-604 syntax (Ex.: list | str) is represented with a types.UnionType object that does not have __getitem__.
        # We also cannot use isinstance() since we have to compare types.
        if sys.version_info >= (3, 10) and origin_type is types.UnionType:
            return _UnionGenericAlias(origin_type, resolved_type_args)
        # NotRequired[T] and Required[T] don't support tuple type resolved_type_args, hence the condition below
        return origin_type[resolved_type_args[0] if len(resolved_type_args) == 1 else resolved_type_args]

    # We handle pydantic generic models separately as they don't have the same
    # semantics as "typing" classes or generic aliases

    if not origin_type and is_model_class(type_):
        parameters = type_.__pydantic_generic_metadata__['parameters']
        if not parameters:
            return type_
        resolved_type_args = tuple(replace_types(t, type_map) for t in parameters)
        if all_identical(parameters, resolved_type_args):
            return type_
        return type_[resolved_type_args]

    # Handle special case for typehints that can have lists as arguments.
    # `typing.Callable[[int, str], int]` is an example for this.
    if isinstance(type_, list):
        resolved_list = [replace_types(element, type_map) for element in type_]
        if all_identical(type_, resolved_list):
            return type_
        return resolved_list

    # If all else fails, we try to resolve the type directly and otherwise just
    # return the input with no modifications.
    return type_map.get(type_, type_)


def map_generic_model_arguments(cls: type[BaseModel], args: tuple[Any, ...]) -> dict[TypeVar, Any]:
    """Return a mapping between the parameters of a generic model and the provided arguments during parameterization.

    Raises:
        TypeError: If the number of arguments does not match the parameters (i.e. if providing too few or too many arguments).

    Example:
        ```python {test="skip" lint="skip"}
        class Model[T, U, V = int](BaseModel): ...

        map_generic_model_arguments(Model, (str, bytes))
        #> {T: str, U: bytes, V: int}

        map_generic_model_arguments(Model, (str,))
        #> TypeError: Too few arguments for <class '__main__.Model'>; actual 1, expected at least 2

        map_generic_model_arguments(Model, (str, bytes, int, complex))
        #> TypeError: Too many arguments for <class '__main__.Model'>; actual 4, expected 3
        ```

    Note:
        This function is analogous to the private `typing._check_generic_specialization` function.
    """
    parameters = cls.__pydantic_generic_metadata__['parameters']
    expected_len = len(parameters)
    typevars_map: dict[TypeVar, Any] = {}

    _missing = object()
    for parameter, argument in zip_longest(parameters, args, fillvalue=_missing):
        if parameter is _missing:
            raise TypeError(f'Too many arguments for {cls}; actual {len(args)}, expected {expected_len}')

        if argument is _missing:
            param = typing.cast(TypeVar, parameter)
            try:
                has_default = param.has_default()
            except AttributeError:
                # Happens if using `typing.TypeVar` (and not `typing_extensions`) on Python < 3.13.
                has_default = False
            if has_default:
                # The default might refer to other type parameters. For an example, see:
                # https://typing.readthedocs.io/en/latest/spec/generics.html#type-parameters-as-parameters-to-generics
                typevars_map[param] = replace_types(param.__default__, typevars_map)
            else:
                expected_len -= sum(hasattr(p, 'has_default') and p.has_default() for p in parameters)
                raise TypeError(f'Too few arguments for {cls}; actual {len(args)}, expected at least {expected_len}')
        else:
            param = typing.cast(TypeVar, parameter)
            typevars_map[param] = argument

    return typevars_map


_generic_recursion_cache: ContextVar[set[str] | None] = ContextVar('_generic_recursion_cache', default=None)


@contextmanager
def generic_recursion_self_type(
    origin: type[BaseModel], args: tuple[Any, ...]
) -> Iterator[PydanticRecursiveRef | None]:
    """This contextmanager should be placed around the recursive calls used to build a generic type,
    and accept as arguments the generic origin type and the type arguments being passed to it.

    If the same origin and arguments are observed twice, it implies that a self-reference placeholder
    can be used while building the core schema, and will produce a schema_ref that will be valid in the
    final parent schema.
    """
    previously_seen_type_refs = _generic_recursion_cache.get()
    if previously_seen_type_refs is None:
        previously_seen_type_refs = set()
        token = _generic_recursion_cache.set(previously_seen_type_refs)
    else:
        token = None

    try:
        type_ref = get_type_ref(origin, args_override=args)
        if type_ref in previously_seen_type_refs:
            self_type = PydanticRecursiveRef(type_ref=type_ref)
            yield self_type
        else:
            previously_seen_type_refs.add(type_ref)
            yield
            previously_seen_type_refs.remove(type_ref)
    finally:
        if token:
            _generic_recursion_cache.reset(token)


def recursively_defined_type_refs() -> set[str]:
    visited = _generic_recursion_cache.get()
    if not visited:
        return set()  # not in a generic recursion, so there are no types

    return visited.copy()  # don't allow modifications


def get_cached_generic_type_early(parent: type[BaseModel], typevar_values: Any) -> type[BaseModel] | None:
    """The use of a two-stage cache lookup approach was necessary to have the highest performance possible for
    repeated calls to `__class_getitem__` on generic types (which may happen in tighter loops during runtime),
    while still ensuring that certain alternative parametrizations ultimately resolve to the same type.

    As a concrete example, this approach was necessary to make Model[List[T]][int] equal to Model[List[int]].
    The approach could be modified to not use two different cache keys at different points, but the
    _early_cache_key is optimized to be as quick to compute as possible (for repeated-access speed), and the
    _late_cache_key is optimized to be as "correct" as possible, so that two types that will ultimately be the
    same after resolving the type arguments will always produce cache hits.

    If we wanted to move to only using a single cache key per type, we would either need to always use the
    slower/more computationally intensive logic associated with _late_cache_key, or would need to accept
    that Model[List[T]][int] is a different type than Model[List[T]][int]. Because we rely on subclass relationships
    during validation, I think it is worthwhile to ensure that types that are functionally equivalent are actually
    equal.
    """
    generic_types_cache = _GENERIC_TYPES_CACHE.get()
    if generic_types_cache is None:
        generic_types_cache = GenericTypesCache()
        _GENERIC_TYPES_CACHE.set(generic_types_cache)
    return generic_types_cache.get(_early_cache_key(parent, typevar_values))


def get_cached_generic_type_late(
    parent: type[BaseModel], typevar_values: Any, origin: type[BaseModel], args: tuple[Any, ...]
) -> type[BaseModel] | None:
    """See the docstring of `get_cached_generic_type_early` for more information about the two-stage cache lookup."""
    generic_types_cache = _GENERIC_TYPES_CACHE.get()
    if (
        generic_types_cache is None
    ):  # pragma: no cover (early cache is guaranteed to run first and initialize the cache)
        generic_types_cache = GenericTypesCache()
        _GENERIC_TYPES_CACHE.set(generic_types_cache)
    cached = generic_types_cache.get(_late_cache_key(origin, args, typevar_values))
    if cached is not None:
        set_cached_generic_type(parent, typevar_values, cached, origin, args)
    return cached


def set_cached_generic_type(
    parent: type[BaseModel],
    typevar_values: tuple[Any, ...],
    type_: type[BaseModel],
    origin: type[BaseModel] | None = None,
    args: tuple[Any, ...] | None = None,
) -> None:
    """See the docstring of `get_cached_generic_type_early` for more information about why items are cached with
    two different keys.
    """
    generic_types_cache = _GENERIC_TYPES_CACHE.get()
    if (
        generic_types_cache is None
    ):  # pragma: no cover (cache lookup is guaranteed to run first and initialize the cache)
        generic_types_cache = GenericTypesCache()
        _GENERIC_TYPES_CACHE.set(generic_types_cache)
    generic_types_cache[_early_cache_key(parent, typevar_values)] = type_
    if len(typevar_values) == 1:
        generic_types_cache[_early_cache_key(parent, typevar_values[0])] = type_
    if origin and args:
        generic_types_cache[_late_cache_key(origin, args, typevar_values)] = type_


def _union_orderings_key(typevar_values: Any) -> Any:
    """This is intended to help differentiate between Union types with the same arguments in different order.

    Thanks to caching internal to the `typing` module, it is not possible to distinguish between
    List[Union[int, float]] and List[Union[float, int]] (and similarly for other "parent" origins besides List)
    because `typing` considers Union[int, float] to be equal to Union[float, int].

    However, you _can_ distinguish between (top-level) Union[int, float] vs. Union[float, int].
    Because we parse items as the first Union type that is successful, we get slightly more consistent behavior
    if we make an effort to distinguish the ordering of items in a union. It would be best if we could _always_
    get the exact-correct order of items in the union, but that would require a change to the `typing` module itself.
    (See https://github.com/python/cpython/issues/86483 for reference.)
    """
    if isinstance(typevar_values, tuple):
        args_data = []
        for value in typevar_values:
            args_data.append(_union_orderings_key(value))
        return tuple(args_data)
    elif typing_objects.is_union(typing_extensions.get_origin(typevar_values)):
        return get_args(typevar_values)
    else:
        return ()


def _early_cache_key(cls: type[BaseModel], typevar_values: Any) -> GenericTypesCacheKey:
    """This is intended for minimal computational overhead during lookups of cached types.

    Note that this is overly simplistic, and it's possible that two different cls/typevar_values
    inputs would ultimately result in the same type being created in BaseModel.__class_getitem__.
    To handle this, we have a fallback _late_cache_key that is checked later if the _early_cache_key
    lookup fails, and should result in a cache hit _precisely_ when the inputs to __class_getitem__
    would result in the same type.
    """
    return cls, typevar_values, _union_orderings_key(typevar_values)


def _late_cache_key(origin: type[BaseModel], args: tuple[Any, ...], typevar_values: Any) -> GenericTypesCacheKey:
    """This is intended for use later in the process of creating a new type, when we have more information
    about the exact args that will be passed. If it turns out that a different set of inputs to
    __class_getitem__ resulted in the same inputs to the generic type creation process, we can still
    return the cached type, and update the cache with the _early_cache_key as well.
    """
    # The _union_orderings_key is placed at the start here to ensure there cannot be a collision with an
    # _early_cache_key, as that function will always produce a BaseModel subclass as the first item in the key,
    # whereas this function will always produce a tuple as the first item in the key.
    return _union_orderings_key(typevar_values), origin, args

# === NexusCore/openenv\Lib\site-packages\playwright\_impl\_fetch.py ===
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
import json
import pathlib
import typing
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, cast

import playwright._impl._network as network
from playwright._impl._api_structures import (
    ClientCertificate,
    FilePayload,
    FormField,
    Headers,
    HttpCredentials,
    ProxySettings,
    ServerFilePayload,
    StorageState,
)
from playwright._impl._connection import ChannelOwner, from_channel
from playwright._impl._errors import is_target_closed_error
from playwright._impl._helper import (
    Error,
    NameValue,
    TargetClosedError,
    async_readfile,
    async_writefile,
    is_file_payload,
    locals_to_params,
    object_to_array,
    to_impl,
)
from playwright._impl._network import serialize_headers, to_client_certificates_protocol
from playwright._impl._tracing import Tracing

if typing.TYPE_CHECKING:
    from playwright._impl._playwright import Playwright


FormType = Dict[str, Union[bool, float, str]]
DataType = Union[Any, bytes, str]
MultipartType = Dict[str, Union[bytes, bool, float, str, FilePayload]]
ParamsType = Union[Dict[str, Union[bool, float, str]], str]


class APIRequest:
    def __init__(self, playwright: "Playwright") -> None:
        self.playwright = playwright
        self._loop = playwright._loop
        self._dispatcher_fiber = playwright._connection._dispatcher_fiber

    async def new_context(
        self,
        baseURL: str = None,
        extraHTTPHeaders: Dict[str, str] = None,
        httpCredentials: HttpCredentials = None,
        ignoreHTTPSErrors: bool = None,
        proxy: ProxySettings = None,
        userAgent: str = None,
        timeout: float = None,
        storageState: Union[StorageState, str, Path] = None,
        clientCertificates: List[ClientCertificate] = None,
        failOnStatusCode: bool = None,
        maxRedirects: int = None,
    ) -> "APIRequestContext":
        params = locals_to_params(locals())
        if "storageState" in params:
            storage_state = params["storageState"]
            if not isinstance(storage_state, dict) and storage_state:
                params["storageState"] = json.loads(
                    (await async_readfile(storage_state)).decode()
                )
        if "extraHTTPHeaders" in params:
            params["extraHTTPHeaders"] = serialize_headers(params["extraHTTPHeaders"])
        params["clientCertificates"] = await to_client_certificates_protocol(
            params.get("clientCertificates")
        )
        context = cast(
            APIRequestContext,
            from_channel(await self.playwright._channel.send("newRequest", params)),
        )
        return context


class APIRequestContext(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._tracing: Tracing = from_channel(initializer["tracing"])
        self._close_reason: Optional[str] = None

    async def dispose(self, reason: str = None) -> None:
        self._close_reason = reason
        try:
            await self._channel.send("dispose", {"reason": reason})
        except Error as e:
            if is_target_closed_error(e):
                return
            raise e
        self._tracing._reset_stack_counter()

    async def delete(
        self,
        url: str,
        params: ParamsType = None,
        headers: Headers = None,
        data: DataType = None,
        form: FormType = None,
        multipart: MultipartType = None,
        timeout: float = None,
        failOnStatusCode: bool = None,
        ignoreHTTPSErrors: bool = None,
        maxRedirects: int = None,
        maxRetries: int = None,
    ) -> "APIResponse":
        return await self.fetch(
            url,
            method="DELETE",
            params=params,
            headers=headers,
            data=data,
            form=form,
            multipart=multipart,
            timeout=timeout,
            failOnStatusCode=failOnStatusCode,
            ignoreHTTPSErrors=ignoreHTTPSErrors,
            maxRedirects=maxRedirects,
            maxRetries=maxRetries,
        )

    async def head(
        self,
        url: str,
        params: ParamsType = None,
        headers: Headers = None,
        data: DataType = None,
        form: FormType = None,
        multipart: MultipartType = None,
        timeout: float = None,
        failOnStatusCode: bool = None,
        ignoreHTTPSErrors: bool = None,
        maxRedirects: int = None,
        maxRetries: int = None,
    ) -> "APIResponse":
        return await self.fetch(
            url,
            method="HEAD",
            params=params,
            headers=headers,
            data=data,
            form=form,
            multipart=multipart,
            timeout=timeout,
            failOnStatusCode=failOnStatusCode,
            ignoreHTTPSErrors=ignoreHTTPSErrors,
            maxRedirects=maxRedirects,
            maxRetries=maxRetries,
        )

    async def get(
        self,
        url: str,
        params: ParamsType = None,
        headers: Headers = None,
        data: DataType = None,
        form: FormType = None,
        multipart: MultipartType = None,
        timeout: float = None,
        failOnStatusCode: bool = None,
        ignoreHTTPSErrors: bool = None,
        maxRedirects: int = None,
        maxRetries: int = None,
    ) -> "APIResponse":
        return await self.fetch(
            url,
            method="GET",
            params=params,
            headers=headers,
            data=data,
            form=form,
            multipart=multipart,
            timeout=timeout,
            failOnStatusCode=failOnStatusCode,
            ignoreHTTPSErrors=ignoreHTTPSErrors,
            maxRedirects=maxRedirects,
            maxRetries=maxRetries,
        )

    async def patch(
        self,
        url: str,
        params: ParamsType = None,
        headers: Headers = None,
        data: DataType = None,
        form: FormType = None,
        multipart: Dict[str, Union[bytes, bool, float, str, FilePayload]] = None,
        timeout: float = None,
        failOnStatusCode: bool = None,
        ignoreHTTPSErrors: bool = None,
        maxRedirects: int = None,
        maxRetries: int = None,
    ) -> "APIResponse":
        return await self.fetch(
            url,
            method="PATCH",
            params=params,
            headers=headers,
            data=data,
            form=form,
            multipart=multipart,
            timeout=timeout,
            failOnStatusCode=failOnStatusCode,
            ignoreHTTPSErrors=ignoreHTTPSErrors,
            maxRedirects=maxRedirects,
            maxRetries=maxRetries,
        )

    async def put(
        self,
        url: str,
        params: ParamsType = None,
        headers: Headers = None,
        data: DataType = None,
        form: FormType = None,
        multipart: Dict[str, Union[bytes, bool, float, str, FilePayload]] = None,
        timeout: float = None,
        failOnStatusCode: bool = None,
        ignoreHTTPSErrors: bool = None,
        maxRedirects: int = None,
        maxRetries: int = None,
    ) -> "APIResponse":
        return await self.fetch(
            url,
            method="PUT",
            params=params,
            headers=headers,
            data=data,
            form=form,
            multipart=multipart,
            timeout=timeout,
            failOnStatusCode=failOnStatusCode,
            ignoreHTTPSErrors=ignoreHTTPSErrors,
            maxRedirects=maxRedirects,
            maxRetries=maxRetries,
        )

    async def post(
        self,
        url: str,
        params: ParamsType = None,
        headers: Headers = None,
        data: DataType = None,
        form: FormType = None,
        multipart: Dict[str, Union[bytes, bool, float, str, FilePayload]] = None,
        timeout: float = None,
        failOnStatusCode: bool = None,
        ignoreHTTPSErrors: bool = None,
        maxRedirects: int = None,
        maxRetries: int = None,
    ) -> "APIResponse":
        return await self.fetch(
            url,
            method="POST",
            params=params,
            headers=headers,
            data=data,
            form=form,
            multipart=multipart,
            timeout=timeout,
            failOnStatusCode=failOnStatusCode,
            ignoreHTTPSErrors=ignoreHTTPSErrors,
            maxRedirects=maxRedirects,
            maxRetries=maxRetries,
        )

    async def fetch(
        self,
        urlOrRequest: Union[str, network.Request],
        params: ParamsType = None,
        method: str = None,
        headers: Headers = None,
        data: DataType = None,
        form: FormType = None,
        multipart: Dict[str, Union[bytes, bool, float, str, FilePayload]] = None,
        timeout: float = None,
        failOnStatusCode: bool = None,
        ignoreHTTPSErrors: bool = None,
        maxRedirects: int = None,
        maxRetries: int = None,
    ) -> "APIResponse":
        url = urlOrRequest if isinstance(urlOrRequest, str) else None
        request = (
            cast(network.Request, to_impl(urlOrRequest))
            if isinstance(to_impl(urlOrRequest), network.Request)
            else None
        )
        assert request or isinstance(
            urlOrRequest, str
        ), "First argument must be either URL string or Request"
        return await self._inner_fetch(
            request,
            url,
            method,
            headers,
            data,
            params,
            form,
            multipart,
            timeout,
            failOnStatusCode,
            ignoreHTTPSErrors,
            maxRedirects,
            maxRetries,
        )

    async def _inner_fetch(
        self,
        request: Optional[network.Request],
        url: Optional[str],
        method: str = None,
        headers: Headers = None,
        data: DataType = None,
        params: ParamsType = None,
        form: FormType = None,
        multipart: Dict[str, Union[bytes, bool, float, str, FilePayload]] = None,
        timeout: float = None,
        failOnStatusCode: bool = None,
        ignoreHTTPSErrors: bool = None,
        maxRedirects: int = None,
        maxRetries: int = None,
    ) -> "APIResponse":
        if self._close_reason:
            raise TargetClosedError(self._close_reason)
        assert (
            (1 if data else 0) + (1 if form else 0) + (1 if multipart else 0)
        ) <= 1, "Only one of 'data', 'form' or 'multipart' can be specified"
        assert (
            maxRedirects is None or maxRedirects >= 0
        ), "'max_redirects' must be greater than or equal to '0'"
        assert (
            maxRetries is None or maxRetries >= 0
        ), "'max_retries' must be greater than or equal to '0'"
        url = url or (request.url if request else url)
        method = method or (request.method if request else "GET")
        # Cannot call allHeaders() here as the request may be paused inside route handler.
        headers_obj = headers or (request.headers if request else None)
        serialized_headers = serialize_headers(headers_obj) if headers_obj else None
        json_data: Any = None
        form_data: Optional[List[NameValue]] = None
        multipart_data: Optional[List[FormField]] = None
        post_data_buffer: Optional[bytes] = None
        if data is not None:
            if isinstance(data, str):
                if is_json_content_type(serialized_headers):
                    json_data = data if is_json_parsable(data) else json.dumps(data)
                else:
                    post_data_buffer = data.encode()
            elif isinstance(data, bytes):
                post_data_buffer = data
            elif isinstance(data, (dict, list, int, bool)):
                json_data = json.dumps(data)
            else:
                raise Error(f"Unsupported 'data' type: {type(data)}")
        elif form:
            form_data = object_to_array(form)
        elif multipart:
            multipart_data = []
            # Convert file-like values to ServerFilePayload structs.
            for name, value in multipart.items():
                if is_file_payload(value):
                    payload = cast(FilePayload, value)
                    assert isinstance(
                        payload["buffer"], bytes
                    ), f"Unexpected buffer type of 'data.{name}'"
                    multipart_data.append(
                        FormField(name=name, file=file_payload_to_json(payload))
                    )
                elif isinstance(value, str):
                    multipart_data.append(FormField(name=name, value=value))
        if (
            post_data_buffer is None
            and json_data is None
            and form_data is None
            and multipart_data is None
        ):
            post_data_buffer = request.post_data_buffer if request else None
        post_data = (
            base64.b64encode(post_data_buffer).decode() if post_data_buffer else None
        )

        response = await self._channel.send(
            "fetch",
            {
                "url": url,
                "params": object_to_array(params) if isinstance(params, dict) else None,
                "encodedParams": params if isinstance(params, str) else None,
                "method": method,
                "headers": serialized_headers,
                "postData": post_data,
                "jsonData": json_data,
                "formData": form_data,
                "multipartData": multipart_data,
                "timeout": timeout,
                "failOnStatusCode": failOnStatusCode,
                "ignoreHTTPSErrors": ignoreHTTPSErrors,
                "maxRedirects": maxRedirects,
                "maxRetries": maxRetries,
            },
        )
        return APIResponse(self, response)

    async def storage_state(
        self,
        path: Union[pathlib.Path, str] = None,
        indexedDB: bool = None,
    ) -> StorageState:
        result = await self._channel.send_return_as_dict(
            "storageState", {"indexedDB": indexedDB}
        )
        if path:
            await async_writefile(path, json.dumps(result))
        return result


def file_payload_to_json(payload: FilePayload) -> ServerFilePayload:
    return ServerFilePayload(
        name=payload["name"],
        mimeType=payload["mimeType"],
        buffer=base64.b64encode(payload["buffer"]).decode(),
    )


class APIResponse:
    def __init__(self, context: APIRequestContext, initializer: Dict) -> None:
        self._loop = context._loop
        self._dispatcher_fiber = context._connection._dispatcher_fiber
        self._request = context
        self._initializer = initializer
        self._headers = network.RawHeaders(initializer["headers"])

    def __repr__(self) -> str:
        return f"<APIResponse url={self.url!r} status={self.status!r} status_text={self.status_text!r}>"

    @property
    def ok(self) -> bool:
        return self.status >= 200 and self.status <= 299

    @property
    def url(self) -> str:
        return self._initializer["url"]

    @property
    def status(self) -> int:
        return self._initializer["status"]

    @property
    def status_text(self) -> str:
        return self._initializer["statusText"]

    @property
    def headers(self) -> Headers:
        return self._headers.headers()

    @property
    def headers_array(self) -> network.HeadersArray:
        return self._headers.headers_array()

    async def body(self) -> bytes:
        try:
            result = await self._request._connection.wrap_api_call(
                lambda: self._request._channel.send_return_as_dict(
                    "fetchResponseBody",
                    {
                        "fetchUid": self._fetch_uid,
                    },
                ),
                True,
            )
            if result is None:
                raise Error("Response has been disposed")
            return base64.b64decode(result["binary"])
        except Error as exc:
            if is_target_closed_error(exc):
                raise Error("Response has been disposed")
            raise exc

    async def text(self) -> str:
        content = await self.body()
        return content.decode()

    async def json(self) -> Any:
        content = await self.text()
        return json.loads(content)

    async def dispose(self) -> None:
        await self._request._channel.send(
            "disposeAPIResponse",
            {
                "fetchUid": self._fetch_uid,
            },
        )

    @property
    def _fetch_uid(self) -> str:
        return self._initializer["fetchUid"]

    async def _fetch_log(self) -> List[str]:
        return await self._request._channel.send(
            "fetchLog",
            {
                "fetchUid": self._fetch_uid,
            },
        )


def is_json_content_type(headers: network.HeadersArray = None) -> bool:
    if not headers:
        return False
    for header in headers:
        if header["name"] == "Content-Type":
            return header["value"].startswith("application/json")
    return False


def is_json_parsable(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        json.loads(value)
        return True
    except json.JSONDecodeError:
        return False

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\common_utils\reset_budget_job.py ===
import asyncio
import json
import time
from datetime import datetime, timedelta, timezone
from typing import List, Literal, Optional, Union

from litellm._logging import verbose_proxy_logger
from litellm.proxy._types import (
    LiteLLM_BudgetTableFull,
    LiteLLM_EndUserTable,
    LiteLLM_TeamTable,
    LiteLLM_UserTable,
    LiteLLM_VerificationToken,
)
from litellm.proxy.utils import PrismaClient, ProxyLogging
from litellm.types.services import ServiceTypes


class ResetBudgetJob:
    """
    Resets the budget for all the keys, users, and teams that need it
    """

    def __init__(self, proxy_logging_obj: ProxyLogging, prisma_client: PrismaClient):
        self.proxy_logging_obj: ProxyLogging = proxy_logging_obj
        self.prisma_client: PrismaClient = prisma_client

    async def reset_budget(
        self,
    ):
        """
        Gets all the non-expired keys for a db, which need spend to be reset

        Resets their spend

        Updates db
        """
        if self.prisma_client is not None:
            ### RESET KEY BUDGET ###
            await self.reset_budget_for_litellm_keys()

            ### RESET USER BUDGET ###
            await self.reset_budget_for_litellm_users()

            ## Reset Team Budget
            await self.reset_budget_for_litellm_teams()

            ### RESET ENDUSER (Customer) BUDGET and corresponding Budget duration ###
            await self.reset_budget_for_litellm_endusers()

    async def reset_budget_for_litellm_endusers(self):
        """
        Resets the budget for all LiteLLM End-Users (Customers) if their budget has expired
        The corresponding Budget duration is also updated.
        """
        now = datetime.now(timezone.utc)
        start_time = time.time()
        endusers_to_reset: Optional[List[LiteLLM_EndUserTable]] = None
        budgets_to_reset: Optional[List[LiteLLM_BudgetTableFull]] = None
        updated_endusers: List[LiteLLM_EndUserTable] = []
        failed_endusers = []
        try:
            budgets_to_reset = await self.prisma_client.get_data(
                table_name="budget", query_type="find_all", reset_at=now
            )

            if budgets_to_reset is not None and len(budgets_to_reset) > 0:
                for budget in budgets_to_reset:
                    budget = await ResetBudgetJob._reset_budget_reset_at_date(
                        budget, now
                    )
                await self.prisma_client.update_data(
                    query_type="update_many",
                    data_list=budgets_to_reset,
                    table_name="budget",
                )

                endusers_to_reset = await self.prisma_client.get_data(
                    table_name="enduser",
                    query_type="find_all",
                    budget_id_list=[budget.budget_id for budget in budgets_to_reset],
                )

            if endusers_to_reset is not None and len(endusers_to_reset) > 0:
                for enduser in endusers_to_reset:
                    try:
                        updated_enduser = (
                            await ResetBudgetJob._reset_budget_for_enduser(
                                enduser=enduser
                            )
                        )
                        if updated_enduser is not None:
                            updated_endusers.append(updated_enduser)
                        else:
                            failed_endusers.append(
                                {
                                    "enduser": enduser,
                                    "error": "Returned None without exception",
                                }
                            )
                    except Exception as e:
                        failed_endusers.append({"enduser": enduser, "error": str(e)})
                        verbose_proxy_logger.exception(
                            "Failed to reset budget for enduser: %s", enduser
                        )

                verbose_proxy_logger.debug(
                    "Updated users %s",
                    json.dumps(updated_endusers, indent=4, default=str),
                )

                await self.prisma_client.update_data(
                    query_type="update_many",
                    data_list=updated_endusers,
                    table_name="enduser",
                )

            end_time = time.time()
            if len(failed_endusers) > 0:  # If any endusers failed to reset
                raise Exception(
                    f"Failed to reset {len(failed_endusers)} endusers: {json.dumps(failed_endusers, default=str)}"
                )

            asyncio.create_task(
                self.proxy_logging_obj.service_logging_obj.async_service_success_hook(
                    service=ServiceTypes.RESET_BUDGET_JOB,
                    duration=end_time - start_time,
                    call_type="reset_budget_endusers",
                    start_time=start_time,
                    end_time=end_time,
                    event_metadata={
                        "num_budgets_found": len(budgets_to_reset)
                        if budgets_to_reset
                        else 0,
                        "budgets_found": json.dumps(
                            budgets_to_reset, indent=4, default=str
                        ),
                        "num_endusers_found": len(endusers_to_reset)
                        if endusers_to_reset
                        else 0,
                        "endusers_found": json.dumps(
                            endusers_to_reset, indent=4, default=str
                        ),
                        "num_endusers_updated": len(updated_endusers),
                        "endusers_updated": json.dumps(
                            updated_endusers, indent=4, default=str
                        ),
                        "num_endusers_failed": len(failed_endusers),
                        "endusers_failed": json.dumps(
                            failed_endusers, indent=4, default=str
                        ),
                    },
                )
            )
        except Exception as e:
            end_time = time.time()
            asyncio.create_task(
                self.proxy_logging_obj.service_logging_obj.async_service_failure_hook(
                    service=ServiceTypes.RESET_BUDGET_JOB,
                    duration=end_time - start_time,
                    error=e,
                    call_type="reset_budget_endusers",
                    start_time=start_time,
                    end_time=end_time,
                    event_metadata={
                        "num_budgets_found": len(budgets_to_reset)
                        if budgets_to_reset
                        else 0,
                        "budgets_found": json.dumps(
                            budgets_to_reset, indent=4, default=str
                        ),
                        "num_endusers_found": len(endusers_to_reset)
                        if endusers_to_reset
                        else 0,
                        "endusers_found": json.dumps(
                            endusers_to_reset, indent=4, default=str
                        ),
                    },
                )
            )
            verbose_proxy_logger.exception("Failed to reset budget for endusers: %s", e)

    async def reset_budget_for_litellm_keys(self):
        """
        Resets the budget for all the litellm keys

        Catches Exceptions and logs them
        """
        now = datetime.utcnow()
        start_time = time.time()
        keys_to_reset: Optional[List[LiteLLM_VerificationToken]] = None
        try:
            keys_to_reset = await self.prisma_client.get_data(
                table_name="key", query_type="find_all", expires=now, reset_at=now
            )
            verbose_proxy_logger.debug(
                "Keys to reset %s", json.dumps(keys_to_reset, indent=4, default=str)
            )
            updated_keys: List[LiteLLM_VerificationToken] = []
            failed_keys = []
            if keys_to_reset is not None and len(keys_to_reset) > 0:
                for key in keys_to_reset:
                    try:
                        updated_key = await ResetBudgetJob._reset_budget_for_key(
                            key=key, current_time=now
                        )
                        if updated_key is not None:
                            updated_keys.append(updated_key)
                        else:
                            failed_keys.append(
                                {"key": key, "error": "Returned None without exception"}
                            )
                    except Exception as e:
                        failed_keys.append({"key": key, "error": str(e)})
                        verbose_proxy_logger.exception(
                            "Failed to reset budget for key: %s", key
                        )

                verbose_proxy_logger.debug(
                    "Updated keys %s", json.dumps(updated_keys, indent=4, default=str)
                )

                if updated_keys:
                    await self.prisma_client.update_data(
                        query_type="update_many",
                        data_list=updated_keys,
                        table_name="key",
                    )

            end_time = time.time()
            if len(failed_keys) > 0:  # If any keys failed to reset
                raise Exception(
                    f"Failed to reset {len(failed_keys)} keys: {json.dumps(failed_keys, default=str)}"
                )

            asyncio.create_task(
                self.proxy_logging_obj.service_logging_obj.async_service_success_hook(
                    service=ServiceTypes.RESET_BUDGET_JOB,
                    duration=end_time - start_time,
                    call_type="reset_budget_keys",
                    start_time=start_time,
                    end_time=end_time,
                    event_metadata={
                        "num_keys_found": len(keys_to_reset) if keys_to_reset else 0,
                        "keys_found": json.dumps(keys_to_reset, indent=4, default=str),
                        "num_keys_updated": len(updated_keys),
                        "keys_updated": json.dumps(updated_keys, indent=4, default=str),
                        "num_keys_failed": len(failed_keys),
                        "keys_failed": json.dumps(failed_keys, indent=4, default=str),
                    },
                )
            )
        except Exception as e:
            end_time = time.time()
            asyncio.create_task(
                self.proxy_logging_obj.service_logging_obj.async_service_failure_hook(
                    service=ServiceTypes.RESET_BUDGET_JOB,
                    duration=end_time - start_time,
                    error=e,
                    call_type="reset_budget_keys",
                    start_time=start_time,
                    end_time=end_time,
                    event_metadata={
                        "num_keys_found": len(keys_to_reset) if keys_to_reset else 0,
                        "keys_found": json.dumps(keys_to_reset, indent=4, default=str),
                    },
                )
            )
            verbose_proxy_logger.exception("Failed to reset budget for keys: %s", e)

    async def reset_budget_for_litellm_users(self):
        """
        Resets the budget for all LiteLLM Internal Users if their budget has expired
        """
        now = datetime.utcnow()
        start_time = time.time()
        users_to_reset: Optional[List[LiteLLM_UserTable]] = None
        try:
            users_to_reset = await self.prisma_client.get_data(
                table_name="user", query_type="find_all", reset_at=now
            )
            updated_users: List[LiteLLM_UserTable] = []
            failed_users = []
            if users_to_reset is not None and len(users_to_reset) > 0:
                for user in users_to_reset:
                    try:
                        updated_user = await ResetBudgetJob._reset_budget_for_user(
                            user=user, current_time=now
                        )
                        if updated_user is not None:
                            updated_users.append(updated_user)
                        else:
                            failed_users.append(
                                {
                                    "user": user,
                                    "error": "Returned None without exception",
                                }
                            )
                    except Exception as e:
                        failed_users.append({"user": user, "error": str(e)})
                        verbose_proxy_logger.exception(
                            "Failed to reset budget for user: %s", user
                        )

                verbose_proxy_logger.debug(
                    "Updated users %s", json.dumps(updated_users, indent=4, default=str)
                )
                if updated_users:
                    await self.prisma_client.update_data(
                        query_type="update_many",
                        data_list=updated_users,
                        table_name="user",
                    )

            end_time = time.time()
            if len(failed_users) > 0:  # If any users failed to reset
                raise Exception(
                    f"Failed to reset {len(failed_users)} users: {json.dumps(failed_users, default=str)}"
                )

            asyncio.create_task(
                self.proxy_logging_obj.service_logging_obj.async_service_success_hook(
                    service=ServiceTypes.RESET_BUDGET_JOB,
                    duration=end_time - start_time,
                    call_type="reset_budget_users",
                    start_time=start_time,
                    end_time=end_time,
                    event_metadata={
                        "num_users_found": len(users_to_reset) if users_to_reset else 0,
                        "users_found": json.dumps(
                            users_to_reset, indent=4, default=str
                        ),
                        "num_users_updated": len(updated_users),
                        "users_updated": json.dumps(
                            updated_users, indent=4, default=str
                        ),
                        "num_users_failed": len(failed_users),
                        "users_failed": json.dumps(failed_users, indent=4, default=str),
                    },
                )
            )
        except Exception as e:
            end_time = time.time()
            asyncio.create_task(
                self.proxy_logging_obj.service_logging_obj.async_service_failure_hook(
                    service=ServiceTypes.RESET_BUDGET_JOB,
                    duration=end_time - start_time,
                    error=e,
                    call_type="reset_budget_users",
                    start_time=start_time,
                    end_time=end_time,
                    event_metadata={
                        "num_users_found": len(users_to_reset) if users_to_reset else 0,
                        "users_found": json.dumps(
                            users_to_reset, indent=4, default=str
                        ),
                    },
                )
            )
            verbose_proxy_logger.exception("Failed to reset budget for users: %s", e)

    async def reset_budget_for_litellm_teams(self):
        """
        Resets the budget for all LiteLLM Internal Teams if their budget has expired
        """
        now = datetime.utcnow()
        start_time = time.time()
        teams_to_reset: Optional[List[LiteLLM_TeamTable]] = None
        try:
            teams_to_reset = await self.prisma_client.get_data(
                table_name="team", query_type="find_all", reset_at=now
            )
            updated_teams: List[LiteLLM_TeamTable] = []
            failed_teams = []
            if teams_to_reset is not None and len(teams_to_reset) > 0:
                for team in teams_to_reset:
                    try:
                        updated_team = await ResetBudgetJob._reset_budget_for_team(
                            team=team, current_time=now
                        )
                        if updated_team is not None:
                            updated_teams.append(updated_team)
                        else:
                            failed_teams.append(
                                {
                                    "team": team,
                                    "error": "Returned None without exception",
                                }
                            )
                    except Exception as e:
                        failed_teams.append({"team": team, "error": str(e)})
                        verbose_proxy_logger.exception(
                            "Failed to reset budget for team: %s", team
                        )

                verbose_proxy_logger.debug(
                    "Updated teams %s", json.dumps(updated_teams, indent=4, default=str)
                )
                if updated_teams:
                    await self.prisma_client.update_data(
                        query_type="update_many",
                        data_list=updated_teams,
                        table_name="team",
                    )

            end_time = time.time()
            if len(failed_teams) > 0:  # If any teams failed to reset
                raise Exception(
                    f"Failed to reset {len(failed_teams)} teams: {json.dumps(failed_teams, default=str)}"
                )

            asyncio.create_task(
                self.proxy_logging_obj.service_logging_obj.async_service_success_hook(
                    service=ServiceTypes.RESET_BUDGET_JOB,
                    duration=end_time - start_time,
                    call_type="reset_budget_teams",
                    start_time=start_time,
                    end_time=end_time,
                    event_metadata={
                        "num_teams_found": len(teams_to_reset) if teams_to_reset else 0,
                        "teams_found": json.dumps(
                            teams_to_reset, indent=4, default=str
                        ),
                        "num_teams_updated": len(updated_teams),
                        "teams_updated": json.dumps(
                            updated_teams, indent=4, default=str
                        ),
                        "num_teams_failed": len(failed_teams),
                        "teams_failed": json.dumps(failed_teams, indent=4, default=str),
                    },
                )
            )
        except Exception as e:
            end_time = time.time()
            asyncio.create_task(
                self.proxy_logging_obj.service_logging_obj.async_service_failure_hook(
                    service=ServiceTypes.RESET_BUDGET_JOB,
                    duration=end_time - start_time,
                    error=e,
                    call_type="reset_budget_teams",
                    start_time=start_time,
                    end_time=end_time,
                    event_metadata={
                        "num_teams_found": len(teams_to_reset) if teams_to_reset else 0,
                        "teams_found": json.dumps(
                            teams_to_reset, indent=4, default=str
                        ),
                    },
                )
            )
            verbose_proxy_logger.exception("Failed to reset budget for teams: %s", e)

    @staticmethod
    async def _reset_budget_common(
        item: Union[LiteLLM_TeamTable, LiteLLM_UserTable, LiteLLM_VerificationToken],
        current_time: datetime,
        item_type: Literal["key", "team", "user"],
    ):
        """
        In-place, updates spend=0, and sets budget_reset_at to current_time + budget_duration

        Common logic for resetting budget for a team, user, or key
        """
        try:
            item.spend = 0.0
            if hasattr(item, "budget_duration") and item.budget_duration is not None:
                # Get standardized reset time based on budget duration
                from litellm.proxy.common_utils.timezone_utils import get_budget_reset_time
                item.budget_reset_at = get_budget_reset_time(
                    budget_duration=item.budget_duration
                )
            return item
        except Exception as e:
            verbose_proxy_logger.exception(
                "Error resetting budget for %s: %s. Item: %s", item_type, e, item
            )
            raise e

    @staticmethod
    async def _reset_budget_for_team(
        team: LiteLLM_TeamTable, current_time: datetime
    ) -> Optional[LiteLLM_TeamTable]:
        await ResetBudgetJob._reset_budget_common(
            item=team, current_time=current_time, item_type="team"
        )
        return team

    @staticmethod
    async def _reset_budget_for_user(
        user: LiteLLM_UserTable, current_time: datetime
    ) -> Optional[LiteLLM_UserTable]:
        await ResetBudgetJob._reset_budget_common(
            item=user, current_time=current_time, item_type="user"
        )
        return user

    @staticmethod
    async def _reset_budget_for_enduser(
        enduser: LiteLLM_EndUserTable,
    ) -> Optional[LiteLLM_EndUserTable]:
        try:
            enduser.spend = 0.0
        except Exception as e:
            verbose_proxy_logger.exception(
                "Error resetting budget for enduser: %s. Item: %s", e, enduser
            )
            raise e
        return enduser

    @staticmethod
    async def _reset_budget_reset_at_date(
        budget: LiteLLM_BudgetTableFull, current_time: datetime
    ) -> Optional[LiteLLM_BudgetTableFull]:
        try:
            if budget.budget_duration is not None:
                from litellm.litellm_core_utils.duration_parser import duration_in_seconds
                duration_s = duration_in_seconds(duration=budget.budget_duration)

                # Fallback for existing budgets that do not have a budget_reset_at date set, ensuring the duration is taken into account
                if (
                    budget.budget_reset_at is None
                    and budget.created_at + timedelta(seconds=duration_s) > current_time
                ):
                    budget.budget_reset_at = budget.created_at + timedelta(
                        seconds=duration_s
                    )
                else:
                    budget.budget_reset_at = current_time + timedelta(
                        seconds=duration_s
                    )
        except Exception as e:
            verbose_proxy_logger.exception(
                "Error resetting budget_reset_at for budget: %s. Item: %s", e, budget
            )
            raise e
        return budget

    @staticmethod
    async def _reset_budget_for_key(
        key: LiteLLM_VerificationToken, current_time: datetime
    ) -> Optional[LiteLLM_VerificationToken]:
        await ResetBudgetJob._reset_budget_common(
            item=key, current_time=current_time, item_type="key"
        )
        return key

# === NexusCore/openenv\Lib\site-packages\numpy\_core\function_base.py ===
import functools
import operator
import types
import warnings

import numpy as np
from numpy._core import overrides
from numpy._core._multiarray_umath import _array_converter
from numpy._core.multiarray import add_docstring

from . import numeric as _nx
from .numeric import asanyarray, nan, ndim, result_type

__all__ = ['logspace', 'linspace', 'geomspace']


array_function_dispatch = functools.partial(
    overrides.array_function_dispatch, module='numpy')


def _linspace_dispatcher(start, stop, num=None, endpoint=None, retstep=None,
                         dtype=None, axis=None, *, device=None):
    return (start, stop)


@array_function_dispatch(_linspace_dispatcher)
def linspace(start, stop, num=50, endpoint=True, retstep=False, dtype=None,
             axis=0, *, device=None):
    """
    Return evenly spaced numbers over a specified interval.

    Returns `num` evenly spaced samples, calculated over the
    interval [`start`, `stop`].

    The endpoint of the interval can optionally be excluded.

    .. versionchanged:: 1.20.0
        Values are rounded towards ``-inf`` instead of ``0`` when an
        integer ``dtype`` is specified. The old behavior can
        still be obtained with ``np.linspace(start, stop, num).astype(int)``

    Parameters
    ----------
    start : array_like
        The starting value of the sequence.
    stop : array_like
        The end value of the sequence, unless `endpoint` is set to False.
        In that case, the sequence consists of all but the last of ``num + 1``
        evenly spaced samples, so that `stop` is excluded.  Note that the step
        size changes when `endpoint` is False.
    num : int, optional
        Number of samples to generate. Default is 50. Must be non-negative.
    endpoint : bool, optional
        If True, `stop` is the last sample. Otherwise, it is not included.
        Default is True.
    retstep : bool, optional
        If True, return (`samples`, `step`), where `step` is the spacing
        between samples.
    dtype : dtype, optional
        The type of the output array.  If `dtype` is not given, the data type
        is inferred from `start` and `stop`. The inferred dtype will never be
        an integer; `float` is chosen even if the arguments would produce an
        array of integers.
    axis : int, optional
        The axis in the result to store the samples.  Relevant only if start
        or stop are array-like.  By default (0), the samples will be along a
        new axis inserted at the beginning. Use -1 to get an axis at the end.
    device : str, optional
        The device on which to place the created array. Default: None.
        For Array-API interoperability only, so must be ``"cpu"`` if passed.

        .. versionadded:: 2.0.0

    Returns
    -------
    samples : ndarray
        There are `num` equally spaced samples in the closed interval
        ``[start, stop]`` or the half-open interval ``[start, stop)``
        (depending on whether `endpoint` is True or False).
    step : float, optional
        Only returned if `retstep` is True

        Size of spacing between samples.


    See Also
    --------
    arange : Similar to `linspace`, but uses a step size (instead of the
             number of samples).
    geomspace : Similar to `linspace`, but with numbers spaced evenly on a log
                scale (a geometric progression).
    logspace : Similar to `geomspace`, but with the end points specified as
               logarithms.
    :ref:`how-to-partition`

    Examples
    --------
    >>> import numpy as np
    >>> np.linspace(2.0, 3.0, num=5)
    array([2.  , 2.25, 2.5 , 2.75, 3.  ])
    >>> np.linspace(2.0, 3.0, num=5, endpoint=False)
    array([2. ,  2.2,  2.4,  2.6,  2.8])
    >>> np.linspace(2.0, 3.0, num=5, retstep=True)
    (array([2.  ,  2.25,  2.5 ,  2.75,  3.  ]), 0.25)

    Graphical illustration:

    >>> import matplotlib.pyplot as plt
    >>> N = 8
    >>> y = np.zeros(N)
    >>> x1 = np.linspace(0, 10, N, endpoint=True)
    >>> x2 = np.linspace(0, 10, N, endpoint=False)
    >>> plt.plot(x1, y, 'o')
    [<matplotlib.lines.Line2D object at 0x...>]
    >>> plt.plot(x2, y + 0.5, 'o')
    [<matplotlib.lines.Line2D object at 0x...>]
    >>> plt.ylim([-0.5, 1])
    (-0.5, 1)
    >>> plt.show()

    """
    num = operator.index(num)
    if num < 0:
        raise ValueError(
            f"Number of samples, {num}, must be non-negative."
        )
    div = (num - 1) if endpoint else num

    conv = _array_converter(start, stop)
    start, stop = conv.as_arrays()
    dt = conv.result_type(ensure_inexact=True)

    if dtype is None:
        dtype = dt
        integer_dtype = False
    else:
        integer_dtype = _nx.issubdtype(dtype, _nx.integer)

    # Use `dtype=type(dt)` to enforce a floating point evaluation:
    delta = np.subtract(stop, start, dtype=type(dt))
    y = _nx.arange(
        0, num, dtype=dt, device=device
    ).reshape((-1,) + (1,) * ndim(delta))

    # In-place multiplication y *= delta/div is faster, but prevents
    # the multiplicant from overriding what class is produced, and thus
    # prevents, e.g. use of Quantities, see gh-7142. Hence, we multiply
    # in place only for standard scalar types.
    if div > 0:
        _mult_inplace = _nx.isscalar(delta)
        step = delta / div
        any_step_zero = (
            step == 0 if _mult_inplace else _nx.asanyarray(step == 0).any())
        if any_step_zero:
            # Special handling for denormal numbers, gh-5437
            y /= div
            if _mult_inplace:
                y *= delta
            else:
                y = y * delta
        elif _mult_inplace:
            y *= step
        else:
            y = y * step
    else:
        # sequences with 0 items or 1 item with endpoint=True (i.e. div <= 0)
        # have an undefined step
        step = nan
        # Multiply with delta to allow possible override of output class.
        y = y * delta

    y += start

    if endpoint and num > 1:
        y[-1, ...] = stop

    if axis != 0:
        y = _nx.moveaxis(y, 0, axis)

    if integer_dtype:
        _nx.floor(y, out=y)

    y = conv.wrap(y.astype(dtype, copy=False))
    if retstep:
        return y, step
    else:
        return y


def _logspace_dispatcher(start, stop, num=None, endpoint=None, base=None,
                         dtype=None, axis=None):
    return (start, stop, base)


@array_function_dispatch(_logspace_dispatcher)
def logspace(start, stop, num=50, endpoint=True, base=10.0, dtype=None,
             axis=0):
    """
    Return numbers spaced evenly on a log scale.

    In linear space, the sequence starts at ``base ** start``
    (`base` to the power of `start`) and ends with ``base ** stop``
    (see `endpoint` below).

    .. versionchanged:: 1.25.0
        Non-scalar 'base` is now supported

    Parameters
    ----------
    start : array_like
        ``base ** start`` is the starting value of the sequence.
    stop : array_like
        ``base ** stop`` is the final value of the sequence, unless `endpoint`
        is False.  In that case, ``num + 1`` values are spaced over the
        interval in log-space, of which all but the last (a sequence of
        length `num`) are returned.
    num : integer, optional
        Number of samples to generate.  Default is 50.
    endpoint : boolean, optional
        If true, `stop` is the last sample. Otherwise, it is not included.
        Default is True.
    base : array_like, optional
        The base of the log space. The step size between the elements in
        ``ln(samples) / ln(base)`` (or ``log_base(samples)``) is uniform.
        Default is 10.0.
    dtype : dtype
        The type of the output array.  If `dtype` is not given, the data type
        is inferred from `start` and `stop`. The inferred type will never be
        an integer; `float` is chosen even if the arguments would produce an
        array of integers.
    axis : int, optional
        The axis in the result to store the samples.  Relevant only if start,
        stop, or base are array-like.  By default (0), the samples will be
        along a new axis inserted at the beginning. Use -1 to get an axis at
        the end.

    Returns
    -------
    samples : ndarray
        `num` samples, equally spaced on a log scale.

    See Also
    --------
    arange : Similar to linspace, with the step size specified instead of the
             number of samples. Note that, when used with a float endpoint, the
             endpoint may or may not be included.
    linspace : Similar to logspace, but with the samples uniformly distributed
               in linear space, instead of log space.
    geomspace : Similar to logspace, but with endpoints specified directly.
    :ref:`how-to-partition`

    Notes
    -----
    If base is a scalar, logspace is equivalent to the code

    >>> y = np.linspace(start, stop, num=num, endpoint=endpoint)
    ... # doctest: +SKIP
    >>> power(base, y).astype(dtype)
    ... # doctest: +SKIP

    Examples
    --------
    >>> import numpy as np
    >>> np.logspace(2.0, 3.0, num=4)
    array([ 100.        ,  215.443469  ,  464.15888336, 1000.        ])
    >>> np.logspace(2.0, 3.0, num=4, endpoint=False)
    array([100.        ,  177.827941  ,  316.22776602,  562.34132519])
    >>> np.logspace(2.0, 3.0, num=4, base=2.0)
    array([4.        ,  5.0396842 ,  6.34960421,  8.        ])
    >>> np.logspace(2.0, 3.0, num=4, base=[2.0, 3.0], axis=-1)
    array([[ 4.        ,  5.0396842 ,  6.34960421,  8.        ],
           [ 9.        , 12.98024613, 18.72075441, 27.        ]])

    Graphical illustration:

    >>> import matplotlib.pyplot as plt
    >>> N = 10
    >>> x1 = np.logspace(0.1, 1, N, endpoint=True)
    >>> x2 = np.logspace(0.1, 1, N, endpoint=False)
    >>> y = np.zeros(N)
    >>> plt.plot(x1, y, 'o')
    [<matplotlib.lines.Line2D object at 0x...>]
    >>> plt.plot(x2, y + 0.5, 'o')
    [<matplotlib.lines.Line2D object at 0x...>]
    >>> plt.ylim([-0.5, 1])
    (-0.5, 1)
    >>> plt.show()

    """
    if not isinstance(base, (float, int)) and np.ndim(base):
        # If base is non-scalar, broadcast it with the others, since it
        # may influence how axis is interpreted.
        ndmax = np.broadcast(start, stop, base).ndim
        start, stop, base = (
            np.array(a, copy=None, subok=True, ndmin=ndmax)
            for a in (start, stop, base)
        )
        base = np.expand_dims(base, axis=axis)
    y = linspace(start, stop, num=num, endpoint=endpoint, axis=axis)
    if dtype is None:
        return _nx.power(base, y)
    return _nx.power(base, y).astype(dtype, copy=False)


def _geomspace_dispatcher(start, stop, num=None, endpoint=None, dtype=None,
                          axis=None):
    return (start, stop)


@array_function_dispatch(_geomspace_dispatcher)
def geomspace(start, stop, num=50, endpoint=True, dtype=None, axis=0):
    """
    Return numbers spaced evenly on a log scale (a geometric progression).

    This is similar to `logspace`, but with endpoints specified directly.
    Each output sample is a constant multiple of the previous.

    Parameters
    ----------
    start : array_like
        The starting value of the sequence.
    stop : array_like
        The final value of the sequence, unless `endpoint` is False.
        In that case, ``num + 1`` values are spaced over the
        interval in log-space, of which all but the last (a sequence of
        length `num`) are returned.
    num : integer, optional
        Number of samples to generate.  Default is 50.
    endpoint : boolean, optional
        If true, `stop` is the last sample. Otherwise, it is not included.
        Default is True.
    dtype : dtype
        The type of the output array.  If `dtype` is not given, the data type
        is inferred from `start` and `stop`. The inferred dtype will never be
        an integer; `float` is chosen even if the arguments would produce an
        array of integers.
    axis : int, optional
        The axis in the result to store the samples.  Relevant only if start
        or stop are array-like.  By default (0), the samples will be along a
        new axis inserted at the beginning. Use -1 to get an axis at the end.

    Returns
    -------
    samples : ndarray
        `num` samples, equally spaced on a log scale.

    See Also
    --------
    logspace : Similar to geomspace, but with endpoints specified using log
               and base.
    linspace : Similar to geomspace, but with arithmetic instead of geometric
               progression.
    arange : Similar to linspace, with the step size specified instead of the
             number of samples.
    :ref:`how-to-partition`

    Notes
    -----
    If the inputs or dtype are complex, the output will follow a logarithmic
    spiral in the complex plane.  (There are an infinite number of spirals
    passing through two points; the output will follow the shortest such path.)

    Examples
    --------
    >>> import numpy as np
    >>> np.geomspace(1, 1000, num=4)
    array([    1.,    10.,   100.,  1000.])
    >>> np.geomspace(1, 1000, num=3, endpoint=False)
    array([   1.,   10.,  100.])
    >>> np.geomspace(1, 1000, num=4, endpoint=False)
    array([   1.        ,    5.62341325,   31.6227766 ,  177.827941  ])
    >>> np.geomspace(1, 256, num=9)
    array([   1.,    2.,    4.,    8.,   16.,   32.,   64.,  128.,  256.])

    Note that the above may not produce exact integers:

    >>> np.geomspace(1, 256, num=9, dtype=int)
    array([  1,   2,   4,   7,  16,  32,  63, 127, 256])
    >>> np.around(np.geomspace(1, 256, num=9)).astype(int)
    array([  1,   2,   4,   8,  16,  32,  64, 128, 256])

    Negative, decreasing, and complex inputs are allowed:

    >>> np.geomspace(1000, 1, num=4)
    array([1000.,  100.,   10.,    1.])
    >>> np.geomspace(-1000, -1, num=4)
    array([-1000.,  -100.,   -10.,    -1.])
    >>> np.geomspace(1j, 1000j, num=4)  # Straight line
    array([0.   +1.j, 0.  +10.j, 0. +100.j, 0.+1000.j])
    >>> np.geomspace(-1+0j, 1+0j, num=5)  # Circle
    array([-1.00000000e+00+1.22464680e-16j, -7.07106781e-01+7.07106781e-01j,
            6.12323400e-17+1.00000000e+00j,  7.07106781e-01+7.07106781e-01j,
            1.00000000e+00+0.00000000e+00j])

    Graphical illustration of `endpoint` parameter:

    >>> import matplotlib.pyplot as plt
    >>> N = 10
    >>> y = np.zeros(N)
    >>> plt.semilogx(np.geomspace(1, 1000, N, endpoint=True), y + 1, 'o')
    [<matplotlib.lines.Line2D object at 0x...>]
    >>> plt.semilogx(np.geomspace(1, 1000, N, endpoint=False), y + 2, 'o')
    [<matplotlib.lines.Line2D object at 0x...>]
    >>> plt.axis([0.5, 2000, 0, 3])
    [0.5, 2000, 0, 3]
    >>> plt.grid(True, color='0.7', linestyle='-', which='both', axis='both')
    >>> plt.show()

    """
    start = asanyarray(start)
    stop = asanyarray(stop)
    if _nx.any(start == 0) or _nx.any(stop == 0):
        raise ValueError('Geometric sequence cannot include zero')

    dt = result_type(start, stop, float(num), _nx.zeros((), dtype))
    if dtype is None:
        dtype = dt
    else:
        # complex to dtype('complex128'), for instance
        dtype = _nx.dtype(dtype)

    # Promote both arguments to the same dtype in case, for instance, one is
    # complex and another is negative and log would produce NaN otherwise.
    # Copy since we may change things in-place further down.
    start = start.astype(dt, copy=True)
    stop = stop.astype(dt, copy=True)

    # Allow negative real values and ensure a consistent result for complex
    # (including avoiding negligible real or imaginary parts in output) by
    # rotating start to positive real, calculating, then undoing rotation.
    out_sign = _nx.sign(start)
    start /= out_sign
    stop = stop / out_sign

    log_start = _nx.log10(start)
    log_stop = _nx.log10(stop)
    result = logspace(log_start, log_stop, num=num,
                      endpoint=endpoint, base=10.0, dtype=dt)

    # Make sure the endpoints match the start and stop arguments. This is
    # necessary because np.exp(np.log(x)) is not necessarily equal to x.
    if num > 0:
        result[0] = start
        if num > 1 and endpoint:
            result[-1] = stop

    result *= out_sign

    if axis != 0:
        result = _nx.moveaxis(result, 0, axis)

    return result.astype(dtype, copy=False)


def _needs_add_docstring(obj):
    """
    Returns true if the only way to set the docstring of `obj` from python is
    via add_docstring.

    This function errs on the side of being overly conservative.
    """
    Py_TPFLAGS_HEAPTYPE = 1 << 9

    if isinstance(obj, (types.FunctionType, types.MethodType, property)):
        return False

    if isinstance(obj, type) and obj.__flags__ & Py_TPFLAGS_HEAPTYPE:
        return False

    return True


def _add_docstring(obj, doc, warn_on_python):
    if warn_on_python and not _needs_add_docstring(obj):
        warnings.warn(
            f"add_newdoc was used on a pure-python object {obj}. "
            "Prefer to attach it directly to the source.",
            UserWarning,
            stacklevel=3)
    try:
        add_docstring(obj, doc)
    except Exception:
        pass


def add_newdoc(place, obj, doc, warn_on_python=True):
    """
    Add documentation to an existing object, typically one defined in C

    The purpose is to allow easier editing of the docstrings without requiring
    a re-compile. This exists primarily for internal use within numpy itself.

    Parameters
    ----------
    place : str
        The absolute name of the module to import from
    obj : str or None
        The name of the object to add documentation to, typically a class or
        function name.
    doc : {str, Tuple[str, str], List[Tuple[str, str]]}
        If a string, the documentation to apply to `obj`

        If a tuple, then the first element is interpreted as an attribute
        of `obj` and the second as the docstring to apply -
        ``(method, docstring)``

        If a list, then each element of the list should be a tuple of length
        two - ``[(method1, docstring1), (method2, docstring2), ...]``
    warn_on_python : bool
        If True, the default, emit `UserWarning` if this is used to attach
        documentation to a pure-python object.

    Notes
    -----
    This routine never raises an error if the docstring can't be written, but
    will raise an error if the object being documented does not exist.

    This routine cannot modify read-only docstrings, as appear
    in new-style classes or built-in functions. Because this
    routine never raises an error the caller must check manually
    that the docstrings were changed.

    Since this function grabs the ``char *`` from a c-level str object and puts
    it into the ``tp_doc`` slot of the type of `obj`, it violates a number of
    C-API best-practices, by:

    - modifying a `PyTypeObject` after calling `PyType_Ready`
    - calling `Py_INCREF` on the str and losing the reference, so the str
      will never be released

    If possible it should be avoided.
    """
    new = getattr(__import__(place, globals(), {}, [obj]), obj)
    if isinstance(doc, str):
        if "${ARRAY_FUNCTION_LIKE}" in doc:
            doc = overrides.get_array_function_like_doc(new, doc)
        _add_docstring(new, doc.strip(), warn_on_python)
    elif isinstance(doc, tuple):
        attr, docstring = doc
        _add_docstring(getattr(new, attr), docstring.strip(), warn_on_python)
    elif isinstance(doc, list):
        for attr, docstring in doc:
            _add_docstring(
                getattr(new, attr), docstring.strip(), warn_on_python
            )

# === NexusCore/openenv\Lib\site-packages\openai\resources\containers\files\files.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Mapping, cast
from typing_extensions import Literal

import httpx

from .... import _legacy_response
from .content import (
    Content,
    AsyncContent,
    ContentWithRawResponse,
    AsyncContentWithRawResponse,
    ContentWithStreamingResponse,
    AsyncContentWithStreamingResponse,
)
from ...._types import NOT_GIVEN, Body, Query, Headers, NoneType, NotGiven, FileTypes
from ...._utils import extract_files, maybe_transform, deepcopy_minimal, async_maybe_transform
from ...._compat import cached_property
from ...._resource import SyncAPIResource, AsyncAPIResource
from ...._response import to_streamed_response_wrapper, async_to_streamed_response_wrapper
from ....pagination import SyncCursorPage, AsyncCursorPage
from ...._base_client import AsyncPaginator, make_request_options
from ....types.containers import file_list_params, file_create_params
from ....types.containers.file_list_response import FileListResponse
from ....types.containers.file_create_response import FileCreateResponse
from ....types.containers.file_retrieve_response import FileRetrieveResponse

__all__ = ["Files", "AsyncFiles"]


class Files(SyncAPIResource):
    @cached_property
    def content(self) -> Content:
        return Content(self._client)

    @cached_property
    def with_raw_response(self) -> FilesWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return FilesWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> FilesWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return FilesWithStreamingResponse(self)

    def create(
        self,
        container_id: str,
        *,
        file: FileTypes | NotGiven = NOT_GIVEN,
        file_id: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> FileCreateResponse:
        """
        Create a Container File

        You can send either a multipart/form-data request with the raw file content, or
        a JSON request with a file ID.

        Args:
          file: The File object (not file name) to be uploaded.

          file_id: Name of the file to create.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not container_id:
            raise ValueError(f"Expected a non-empty value for `container_id` but received {container_id!r}")
        body = deepcopy_minimal(
            {
                "file": file,
                "file_id": file_id,
            }
        )
        files = extract_files(cast(Mapping[str, object], body), paths=[["file"]])
        # It should be noted that the actual Content-Type header that will be
        # sent to the server will contain a `boundary` parameter, e.g.
        # multipart/form-data; boundary=---abc--
        extra_headers = {"Content-Type": "multipart/form-data", **(extra_headers or {})}
        return self._post(
            f"/containers/{container_id}/files",
            body=maybe_transform(body, file_create_params.FileCreateParams),
            files=files,
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=FileCreateResponse,
        )

    def retrieve(
        self,
        file_id: str,
        *,
        container_id: str,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> FileRetrieveResponse:
        """
        Retrieve Container File

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not container_id:
            raise ValueError(f"Expected a non-empty value for `container_id` but received {container_id!r}")
        if not file_id:
            raise ValueError(f"Expected a non-empty value for `file_id` but received {file_id!r}")
        return self._get(
            f"/containers/{container_id}/files/{file_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=FileRetrieveResponse,
        )

    def list(
        self,
        container_id: str,
        *,
        after: str | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        order: Literal["asc", "desc"] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> SyncCursorPage[FileListResponse]:
        """List Container files

        Args:
          after: A cursor for use in pagination.

        `after` is an object ID that defines your place
              in the list. For instance, if you make a list request and receive 100 objects,
              ending with obj_foo, your subsequent call can include after=obj_foo in order to
              fetch the next page of the list.

          limit: A limit on the number of objects to be returned. Limit can range between 1 and
              100, and the default is 20.

          order: Sort order by the `created_at` timestamp of the objects. `asc` for ascending
              order and `desc` for descending order.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not container_id:
            raise ValueError(f"Expected a non-empty value for `container_id` but received {container_id!r}")
        return self._get_api_list(
            f"/containers/{container_id}/files",
            page=SyncCursorPage[FileListResponse],
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
                    },
                    file_list_params.FileListParams,
                ),
            ),
            model=FileListResponse,
        )

    def delete(
        self,
        file_id: str,
        *,
        container_id: str,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> None:
        """
        Delete Container File

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not container_id:
            raise ValueError(f"Expected a non-empty value for `container_id` but received {container_id!r}")
        if not file_id:
            raise ValueError(f"Expected a non-empty value for `file_id` but received {file_id!r}")
        extra_headers = {"Accept": "*/*", **(extra_headers or {})}
        return self._delete(
            f"/containers/{container_id}/files/{file_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=NoneType,
        )


class AsyncFiles(AsyncAPIResource):
    @cached_property
    def content(self) -> AsyncContent:
        return AsyncContent(self._client)

    @cached_property
    def with_raw_response(self) -> AsyncFilesWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return AsyncFilesWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncFilesWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return AsyncFilesWithStreamingResponse(self)

    async def create(
        self,
        container_id: str,
        *,
        file: FileTypes | NotGiven = NOT_GIVEN,
        file_id: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> FileCreateResponse:
        """
        Create a Container File

        You can send either a multipart/form-data request with the raw file content, or
        a JSON request with a file ID.

        Args:
          file: The File object (not file name) to be uploaded.

          file_id: Name of the file to create.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not container_id:
            raise ValueError(f"Expected a non-empty value for `container_id` but received {container_id!r}")
        body = deepcopy_minimal(
            {
                "file": file,
                "file_id": file_id,
            }
        )
        files = extract_files(cast(Mapping[str, object], body), paths=[["file"]])
        # It should be noted that the actual Content-Type header that will be
        # sent to the server will contain a `boundary` parameter, e.g.
        # multipart/form-data; boundary=---abc--
        extra_headers = {"Content-Type": "multipart/form-data", **(extra_headers or {})}
        return await self._post(
            f"/containers/{container_id}/files",
            body=await async_maybe_transform(body, file_create_params.FileCreateParams),
            files=files,
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=FileCreateResponse,
        )

    async def retrieve(
        self,
        file_id: str,
        *,
        container_id: str,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> FileRetrieveResponse:
        """
        Retrieve Container File

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not container_id:
            raise ValueError(f"Expected a non-empty value for `container_id` but received {container_id!r}")
        if not file_id:
            raise ValueError(f"Expected a non-empty value for `file_id` but received {file_id!r}")
        return await self._get(
            f"/containers/{container_id}/files/{file_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=FileRetrieveResponse,
        )

    def list(
        self,
        container_id: str,
        *,
        after: str | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        order: Literal["asc", "desc"] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncPaginator[FileListResponse, AsyncCursorPage[FileListResponse]]:
        """List Container files

        Args:
          after: A cursor for use in pagination.

        `after` is an object ID that defines your place
              in the list. For instance, if you make a list request and receive 100 objects,
              ending with obj_foo, your subsequent call can include after=obj_foo in order to
              fetch the next page of the list.

          limit: A limit on the number of objects to be returned. Limit can range between 1 and
              100, and the default is 20.

          order: Sort order by the `created_at` timestamp of the objects. `asc` for ascending
              order and `desc` for descending order.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not container_id:
            raise ValueError(f"Expected a non-empty value for `container_id` but received {container_id!r}")
        return self._get_api_list(
            f"/containers/{container_id}/files",
            page=AsyncCursorPage[FileListResponse],
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
                    },
                    file_list_params.FileListParams,
                ),
            ),
            model=FileListResponse,
        )

    async def delete(
        self,
        file_id: str,
        *,
        container_id: str,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> None:
        """
        Delete Container File

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not container_id:
            raise ValueError(f"Expected a non-empty value for `container_id` but received {container_id!r}")
        if not file_id:
            raise ValueError(f"Expected a non-empty value for `file_id` but received {file_id!r}")
        extra_headers = {"Accept": "*/*", **(extra_headers or {})}
        return await self._delete(
            f"/containers/{container_id}/files/{file_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=NoneType,
        )


class FilesWithRawResponse:
    def __init__(self, files: Files) -> None:
        self._files = files

        self.create = _legacy_response.to_raw_response_wrapper(
            files.create,
        )
        self.retrieve = _legacy_response.to_raw_response_wrapper(
            files.retrieve,
        )
        self.list = _legacy_response.to_raw_response_wrapper(
            files.list,
        )
        self.delete = _legacy_response.to_raw_response_wrapper(
            files.delete,
        )

    @cached_property
    def content(self) -> ContentWithRawResponse:
        return ContentWithRawResponse(self._files.content)


class AsyncFilesWithRawResponse:
    def __init__(self, files: AsyncFiles) -> None:
        self._files = files

        self.create = _legacy_response.async_to_raw_response_wrapper(
            files.create,
        )
        self.retrieve = _legacy_response.async_to_raw_response_wrapper(
            files.retrieve,
        )
        self.list = _legacy_response.async_to_raw_response_wrapper(
            files.list,
        )
        self.delete = _legacy_response.async_to_raw_response_wrapper(
            files.delete,
        )

    @cached_property
    def content(self) -> AsyncContentWithRawResponse:
        return AsyncContentWithRawResponse(self._files.content)


class FilesWithStreamingResponse:
    def __init__(self, files: Files) -> None:
        self._files = files

        self.create = to_streamed_response_wrapper(
            files.create,
        )
        self.retrieve = to_streamed_response_wrapper(
            files.retrieve,
        )
        self.list = to_streamed_response_wrapper(
            files.list,
        )
        self.delete = to_streamed_response_wrapper(
            files.delete,
        )

    @cached_property
    def content(self) -> ContentWithStreamingResponse:
        return ContentWithStreamingResponse(self._files.content)


class AsyncFilesWithStreamingResponse:
    def __init__(self, files: AsyncFiles) -> None:
        self._files = files

        self.create = async_to_streamed_response_wrapper(
            files.create,
        )
        self.retrieve = async_to_streamed_response_wrapper(
            files.retrieve,
        )
        self.list = async_to_streamed_response_wrapper(
            files.list,
        )
        self.delete = async_to_streamed_response_wrapper(
            files.delete,
        )

    @cached_property
    def content(self) -> AsyncContentWithStreamingResponse:
        return AsyncContentWithStreamingResponse(self._files.content)

# === NexusCore/openenv\Lib\site-packages\fontTools\misc\loggingTools.py ===
import sys
import logging
import timeit
from functools import wraps
from collections.abc import Mapping, Callable
import warnings
from logging import PercentStyle


# default logging level used by Timer class
TIME_LEVEL = logging.DEBUG

# per-level format strings used by the default formatter
# (the level name is not printed for INFO and DEBUG messages)
DEFAULT_FORMATS = {
    "*": "%(levelname)s: %(message)s",
    "INFO": "%(message)s",
    "DEBUG": "%(message)s",
}


class LevelFormatter(logging.Formatter):
    """Log formatter with level-specific formatting.

    Formatter class which optionally takes a dict of logging levels to
    format strings, allowing to customise the log records appearance for
    specific levels.


    Attributes:
            fmt: A dictionary mapping logging levels to format strings.
                    The ``*`` key identifies the default format string.
            datefmt: As per py:class:`logging.Formatter`
            style: As per py:class:`logging.Formatter`

    >>> import sys
    >>> handler = logging.StreamHandler(sys.stdout)
    >>> formatter = LevelFormatter(
    ...     fmt={
    ...         '*':     '[%(levelname)s] %(message)s',
    ...         'DEBUG': '%(name)s [%(levelname)s] %(message)s',
    ...         'INFO':  '%(message)s',
    ...     })
    >>> handler.setFormatter(formatter)
    >>> log = logging.getLogger('test')
    >>> log.setLevel(logging.DEBUG)
    >>> log.addHandler(handler)
    >>> log.debug('this uses a custom format string')
    test [DEBUG] this uses a custom format string
    >>> log.info('this also uses a custom format string')
    this also uses a custom format string
    >>> log.warning("this one uses the default format string")
    [WARNING] this one uses the default format string
    """

    def __init__(self, fmt=None, datefmt=None, style="%"):
        if style != "%":
            raise ValueError(
                "only '%' percent style is supported in both python 2 and 3"
            )
        if fmt is None:
            fmt = DEFAULT_FORMATS
        if isinstance(fmt, str):
            default_format = fmt
            custom_formats = {}
        elif isinstance(fmt, Mapping):
            custom_formats = dict(fmt)
            default_format = custom_formats.pop("*", None)
        else:
            raise TypeError("fmt must be a str or a dict of str: %r" % fmt)
        super(LevelFormatter, self).__init__(default_format, datefmt)
        self.default_format = self._fmt
        self.custom_formats = {}
        for level, fmt in custom_formats.items():
            level = logging._checkLevel(level)
            self.custom_formats[level] = fmt

    def format(self, record):
        if self.custom_formats:
            fmt = self.custom_formats.get(record.levelno, self.default_format)
            if self._fmt != fmt:
                self._fmt = fmt
                # for python >= 3.2, _style needs to be set if _fmt changes
                if PercentStyle:
                    self._style = PercentStyle(fmt)
        return super(LevelFormatter, self).format(record)


def configLogger(**kwargs):
    """A more sophisticated logging system configuation manager.

    This is more or less the same as :py:func:`logging.basicConfig`,
    with some additional options and defaults.

    The default behaviour is to create a ``StreamHandler`` which writes to
    sys.stderr, set a formatter using the ``DEFAULT_FORMATS`` strings, and add
    the handler to the top-level library logger ("fontTools").

    A number of optional keyword arguments may be specified, which can alter
    the default behaviour.

    Args:

            logger: Specifies the logger name or a Logger instance to be
                    configured. (Defaults to "fontTools" logger). Unlike ``basicConfig``,
                    this function can be called multiple times to reconfigure a logger.
                    If the logger or any of its children already exists before the call is
                    made, they will be reset before the new configuration is applied.
            filename: Specifies that a ``FileHandler`` be created, using the
                    specified filename, rather than a ``StreamHandler``.
            filemode: Specifies the mode to open the file, if filename is
                    specified. (If filemode is unspecified, it defaults to ``a``).
            format: Use the specified format string for the handler. This
                    argument also accepts a dictionary of format strings keyed by
                    level name, to allow customising the records appearance for
                    specific levels. The special ``'*'`` key is for 'any other' level.
            datefmt: Use the specified date/time format.
            level: Set the logger level to the specified level.
            stream: Use the specified stream to initialize the StreamHandler. Note
                    that this argument is incompatible with ``filename`` - if both
                    are present, ``stream`` is ignored.
            handlers: If specified, this should be an iterable of already created
                    handlers, which will be added to the logger. Any handler in the
                    list which does not have a formatter assigned will be assigned the
                    formatter created in this function.
            filters: If specified, this should be an iterable of already created
                    filters. If the ``handlers`` do not already have filters assigned,
                    these filters will be added to them.
            propagate: All loggers have a ``propagate`` attribute which determines
                    whether to continue searching for handlers up the logging hierarchy.
                    If not provided, the "propagate" attribute will be set to ``False``.
    """
    # using kwargs to enforce keyword-only arguments in py2.
    handlers = kwargs.pop("handlers", None)
    if handlers is None:
        if "stream" in kwargs and "filename" in kwargs:
            raise ValueError(
                "'stream' and 'filename' should not be " "specified together"
            )
    else:
        if "stream" in kwargs or "filename" in kwargs:
            raise ValueError(
                "'stream' or 'filename' should not be "
                "specified together with 'handlers'"
            )
    if handlers is None:
        filename = kwargs.pop("filename", None)
        mode = kwargs.pop("filemode", "a")
        if filename:
            h = logging.FileHandler(filename, mode)
        else:
            stream = kwargs.pop("stream", None)
            h = logging.StreamHandler(stream)
        handlers = [h]
    # By default, the top-level library logger is configured.
    logger = kwargs.pop("logger", "fontTools")
    if not logger or isinstance(logger, str):
        # empty "" or None means the 'root' logger
        logger = logging.getLogger(logger)
    # before (re)configuring, reset named logger and its children (if exist)
    _resetExistingLoggers(parent=logger.name)
    # use DEFAULT_FORMATS if 'format' is None
    fs = kwargs.pop("format", None)
    dfs = kwargs.pop("datefmt", None)
    # XXX: '%' is the only format style supported on both py2 and 3
    style = kwargs.pop("style", "%")
    fmt = LevelFormatter(fs, dfs, style)
    filters = kwargs.pop("filters", [])
    for h in handlers:
        if h.formatter is None:
            h.setFormatter(fmt)
        if not h.filters:
            for f in filters:
                h.addFilter(f)
        logger.addHandler(h)
    if logger.name != "root":
        # stop searching up the hierarchy for handlers
        logger.propagate = kwargs.pop("propagate", False)
    # set a custom severity level
    level = kwargs.pop("level", None)
    if level is not None:
        logger.setLevel(level)
    if kwargs:
        keys = ", ".join(kwargs.keys())
        raise ValueError("Unrecognised argument(s): %s" % keys)


def _resetExistingLoggers(parent="root"):
    """Reset the logger named 'parent' and all its children to their initial
    state, if they already exist in the current configuration.
    """
    root = logging.root
    # get sorted list of all existing loggers
    existing = sorted(root.manager.loggerDict.keys())
    if parent == "root":
        # all the existing loggers are children of 'root'
        loggers_to_reset = [parent] + existing
    elif parent not in existing:
        # nothing to do
        return
    elif parent in existing:
        loggers_to_reset = [parent]
        # collect children, starting with the entry after parent name
        i = existing.index(parent) + 1
        prefixed = parent + "."
        pflen = len(prefixed)
        num_existing = len(existing)
        while i < num_existing:
            if existing[i][:pflen] == prefixed:
                loggers_to_reset.append(existing[i])
            i += 1
    for name in loggers_to_reset:
        if name == "root":
            root.setLevel(logging.WARNING)
            for h in root.handlers[:]:
                root.removeHandler(h)
            for f in root.filters[:]:
                root.removeFilters(f)
            root.disabled = False
        else:
            logger = root.manager.loggerDict[name]
            logger.level = logging.NOTSET
            logger.handlers = []
            logger.filters = []
            logger.propagate = True
            logger.disabled = False


class Timer(object):
    """Keeps track of overall time and split/lap times.

    >>> import time
    >>> timer = Timer()
    >>> time.sleep(0.01)
    >>> print("First lap:", timer.split())
    First lap: ...
    >>> time.sleep(0.02)
    >>> print("Second lap:", timer.split())
    Second lap: ...
    >>> print("Overall time:", timer.time())
    Overall time: ...

    Can be used as a context manager inside with-statements.

    >>> with Timer() as t:
    ...     time.sleep(0.01)
    >>> print("%0.3f seconds" % t.elapsed)
    0... seconds

    If initialised with a logger, it can log the elapsed time automatically
    upon exiting the with-statement.

    >>> import logging
    >>> log = logging.getLogger("my-fancy-timer-logger")
    >>> configLogger(logger=log, level="DEBUG", format="%(message)s", stream=sys.stdout)
    >>> with Timer(log, 'do something'):
    ...     time.sleep(0.01)
    Took ... to do something

    The same Timer instance, holding a reference to a logger, can be reused
    in multiple with-statements, optionally with different messages or levels.

    >>> timer = Timer(log)
    >>> with timer():
    ...     time.sleep(0.01)
    elapsed time: ...s
    >>> with timer('redo it', level=logging.INFO):
    ...     time.sleep(0.02)
    Took ... to redo it

    It can also be used as a function decorator to log the time elapsed to run
    the decorated function.

    >>> @timer()
    ... def test1():
    ...    time.sleep(0.01)
    >>> @timer('run test 2', level=logging.INFO)
    ... def test2():
    ...    time.sleep(0.02)
    >>> test1()
    Took ... to run 'test1'
    >>> test2()
    Took ... to run test 2
    """

    # timeit.default_timer choses the most accurate clock for each platform
    _time: Callable[[], float] = staticmethod(timeit.default_timer)
    default_msg = "elapsed time: %(time).3fs"
    default_format = "Took %(time).3fs to %(msg)s"

    def __init__(self, logger=None, msg=None, level=None, start=None):
        self.reset(start)
        if logger is None:
            for arg in ("msg", "level"):
                if locals().get(arg) is not None:
                    raise ValueError("'%s' can't be specified without a 'logger'" % arg)
        self.logger = logger
        self.level = level if level is not None else TIME_LEVEL
        self.msg = msg

    def reset(self, start=None):
        """Reset timer to 'start_time' or the current time."""
        if start is None:
            self.start = self._time()
        else:
            self.start = start
        self.last = self.start
        self.elapsed = 0.0

    def time(self):
        """Return the overall time (in seconds) since the timer started."""
        return self._time() - self.start

    def split(self):
        """Split and return the lap time (in seconds) in between splits."""
        current = self._time()
        self.elapsed = current - self.last
        self.last = current
        return self.elapsed

    def formatTime(self, msg, time):
        """Format 'time' value in 'msg' and return formatted string.
        If 'msg' contains a '%(time)' format string, try to use that.
        Otherwise, use the predefined 'default_format'.
        If 'msg' is empty or None, fall back to 'default_msg'.
        """
        if not msg:
            msg = self.default_msg
        if msg.find("%(time)") < 0:
            msg = self.default_format % {"msg": msg, "time": time}
        else:
            try:
                msg = msg % {"time": time}
            except (KeyError, ValueError):
                pass  # skip if the format string is malformed
        return msg

    def __enter__(self):
        """Start a new lap"""
        self.last = self._time()
        self.elapsed = 0.0
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """End the current lap. If timer has a logger, log the time elapsed,
        using the format string in self.msg (or the default one).
        """
        time = self.split()
        if self.logger is None or exc_type:
            # if there's no logger attached, or if any exception occurred in
            # the with-statement, exit without logging the time
            return
        message = self.formatTime(self.msg, time)
        # Allow log handlers to see the individual parts to facilitate things
        # like a server accumulating aggregate stats.
        msg_parts = {"msg": self.msg, "time": time}
        self.logger.log(self.level, message, msg_parts)

    def __call__(self, func_or_msg=None, **kwargs):
        """If the first argument is a function, return a decorator which runs
        the wrapped function inside Timer's context manager.
        Otherwise, treat the first argument as a 'msg' string and return an updated
        Timer instance, referencing the same logger.
        A 'level' keyword can also be passed to override self.level.
        """
        if isinstance(func_or_msg, Callable):
            func = func_or_msg
            # use the function name when no explicit 'msg' is provided
            if not self.msg:
                self.msg = "run '%s'" % func.__name__

            @wraps(func)
            def wrapper(*args, **kwds):
                with self:
                    return func(*args, **kwds)

            return wrapper
        else:
            msg = func_or_msg or kwargs.get("msg")
            level = kwargs.get("level", self.level)
            return self.__class__(self.logger, msg, level)

    def __float__(self):
        return self.elapsed

    def __int__(self):
        return int(self.elapsed)

    def __str__(self):
        return "%.3f" % self.elapsed


class ChannelsFilter(logging.Filter):
    """Provides a hierarchical filter for log entries based on channel names.

    Filters out records emitted from a list of enabled channel names,
    including their children. It works the same as the ``logging.Filter``
    class, but allows the user to specify multiple channel names.

    >>> import sys
    >>> handler = logging.StreamHandler(sys.stdout)
    >>> handler.setFormatter(logging.Formatter("%(message)s"))
    >>> filter = ChannelsFilter("A.B", "C.D")
    >>> handler.addFilter(filter)
    >>> root = logging.getLogger()
    >>> root.addHandler(handler)
    >>> root.setLevel(level=logging.DEBUG)
    >>> logging.getLogger('A.B').debug('this record passes through')
    this record passes through
    >>> logging.getLogger('A.B.C').debug('records from children also pass')
    records from children also pass
    >>> logging.getLogger('C.D').debug('this one as well')
    this one as well
    >>> logging.getLogger('A.B.').debug('also this one')
    also this one
    >>> logging.getLogger('A.F').debug('but this one does not!')
    >>> logging.getLogger('C.DE').debug('neither this one!')
    """

    def __init__(self, *names):
        self.names = names
        self.num = len(names)
        self.lengths = {n: len(n) for n in names}

    def filter(self, record):
        if self.num == 0:
            return True
        for name in self.names:
            nlen = self.lengths[name]
            if name == record.name:
                return True
            elif record.name.find(name, 0, nlen) == 0 and record.name[nlen] == ".":
                return True
        return False


class CapturingLogHandler(logging.Handler):
    def __init__(self, logger, level):
        super(CapturingLogHandler, self).__init__(level=level)
        self.records = []
        if isinstance(logger, str):
            self.logger = logging.getLogger(logger)
        else:
            self.logger = logger

    def __enter__(self):
        self.original_disabled = self.logger.disabled
        self.original_level = self.logger.level
        self.original_propagate = self.logger.propagate

        self.logger.addHandler(self)
        self.logger.setLevel(self.level)
        self.logger.disabled = False
        self.logger.propagate = False

        return self

    def __exit__(self, type, value, traceback):
        self.logger.removeHandler(self)
        self.logger.setLevel(self.original_level)
        self.logger.disabled = self.original_disabled
        self.logger.propagate = self.original_propagate

        return self

    def emit(self, record):
        self.records.append(record)

    def assertRegex(self, regexp, msg=None):
        import re

        pattern = re.compile(regexp)
        for r in self.records:
            if pattern.search(r.getMessage()):
                return True
        if msg is None:
            msg = "Pattern '%s' not found in logger records" % regexp
        assert 0, msg


class LogMixin(object):
    """Mixin class that adds logging functionality to another class.

    You can define a new class that subclasses from ``LogMixin`` as well as
    other base classes through multiple inheritance.
    All instances of that class will have a ``log`` property that returns
    a ``logging.Logger`` named after their respective ``<module>.<class>``.

    For example:

    >>> class BaseClass(object):
    ...     pass
    >>> class MyClass(LogMixin, BaseClass):
    ...     pass
    >>> a = MyClass()
    >>> isinstance(a.log, logging.Logger)
    True
    >>> print(a.log.name)
    fontTools.misc.loggingTools.MyClass
    >>> class AnotherClass(MyClass):
    ...     pass
    >>> b = AnotherClass()
    >>> isinstance(b.log, logging.Logger)
    True
    >>> print(b.log.name)
    fontTools.misc.loggingTools.AnotherClass
    """

    @property
    def log(self):
        if not hasattr(self, "_log"):
            name = ".".join((self.__class__.__module__, self.__class__.__name__))
            self._log = logging.getLogger(name)
        return self._log


def deprecateArgument(name, msg, category=UserWarning):
    """Raise a warning about deprecated function argument 'name'."""
    warnings.warn("%r is deprecated; %s" % (name, msg), category=category, stacklevel=3)


def deprecateFunction(msg, category=UserWarning):
    """Decorator to raise a warning when a deprecated function is called."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(
                "%r is deprecated; %s" % (func.__name__, msg),
                category=category,
                stacklevel=2,
            )
            return func(*args, **kwargs)

        return wrapper

    return decorator


if __name__ == "__main__":
    import doctest

    sys.exit(doctest.testmod(optionflags=doctest.ELLIPSIS).failed)

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\pydevd_suspended_frames.py ===
from contextlib import contextmanager
import sys

from _pydevd_bundle.pydevd_constants import get_frame, RETURN_VALUES_DICT, ForkSafeLock, GENERATED_LEN_ATTR_NAME, silence_warnings_decorator
from _pydevd_bundle.pydevd_xml import get_variable_details, get_type
from _pydev_bundle.pydev_override import overrides
from _pydevd_bundle.pydevd_resolver import sorted_attributes_key, TOO_LARGE_ATTR, get_var_scope
from _pydevd_bundle.pydevd_safe_repr import SafeRepr
from _pydev_bundle import pydev_log
from _pydevd_bundle import pydevd_vars
from _pydev_bundle.pydev_imports import Exec
from _pydevd_bundle.pydevd_frame_utils import FramesList
from _pydevd_bundle.pydevd_utils import ScopeRequest, DAPGrouper, Timer
from typing import Optional


class _AbstractVariable(object):
    # Default attributes in class, set in instance.

    name = None
    value = None
    evaluate_name = None

    def __init__(self, py_db):
        assert py_db is not None
        self.py_db = py_db

    def get_name(self):
        return self.name

    def get_value(self):
        return self.value

    def get_variable_reference(self):
        return id(self.value)

    def get_var_data(self, fmt: Optional[dict] = None, context: Optional[str] = None, **safe_repr_custom_attrs):
        """
        :param dict fmt:
            Format expected by the DAP (keys: 'hex': bool, 'rawString': bool)

        :param context:
            This is the context in which the variable is being requested. Valid values:
                "watch",
                "repl",
                "hover",
                "clipboard"
        """
        timer = Timer()
        safe_repr = SafeRepr()
        if fmt is not None:
            safe_repr.convert_to_hex = fmt.get("hex", False)
            safe_repr.raw_value = fmt.get("rawString", False)
        for key, val in safe_repr_custom_attrs.items():
            setattr(safe_repr, key, val)

        type_name, _type_qualifier, _is_exception_on_eval, resolver, value = get_variable_details(
            self.value, to_string=safe_repr, context=context
        )

        is_raw_string = type_name in ("str", "bytes", "bytearray")

        attributes = []

        if is_raw_string:
            attributes.append("rawString")

        name = self.name

        if self._is_return_value:
            attributes.append("readOnly")
            name = "(return) %s" % (name,)

        elif name in (TOO_LARGE_ATTR, GENERATED_LEN_ATTR_NAME):
            attributes.append("readOnly")

        try:
            if self.value.__class__ == DAPGrouper:
                type_name = ""
        except:
            pass  # Ignore errors accessing __class__.

        var_data = {
            "name": name,
            "value": value,
            "type": type_name,
        }

        if self.evaluate_name is not None:
            var_data["evaluateName"] = self.evaluate_name

        if resolver is not None:  # I.e.: it's a container
            var_data["variablesReference"] = self.get_variable_reference()
        else:
            var_data["variablesReference"] = 0  # It's mandatory (although if == 0 it doesn't have children).

        if len(attributes) > 0:
            var_data["presentationHint"] = {"attributes": attributes}

        timer.report_if_compute_repr_attr_slow("", name, type_name)
        return var_data

    def get_children_variables(self, fmt=None, scope=None):
        raise NotImplementedError()

    def get_child_variable_named(self, name, fmt=None, scope=None):
        for child_var in self.get_children_variables(fmt=fmt, scope=scope):
            if child_var.get_name() == name:
                return child_var
        return None

    def _group_entries(self, lst, handle_return_values):
        scope_to_grouper = {}

        group_entries = []
        if isinstance(self.value, DAPGrouper):
            new_lst = lst
        else:
            new_lst = []
            get_presentation = self.py_db.variable_presentation.get_presentation
            # Now that we have the contents, group items.
            for attr_name, attr_value, evaluate_name in lst:
                scope = get_var_scope(attr_name, attr_value, evaluate_name, handle_return_values)

                entry = (attr_name, attr_value, evaluate_name)
                if scope:
                    presentation = get_presentation(scope)
                    if presentation == "hide":
                        continue

                    elif presentation == "inline":
                        new_lst.append(entry)

                    else:  # group
                        if scope not in scope_to_grouper:
                            grouper = DAPGrouper(scope)
                            scope_to_grouper[scope] = grouper
                        else:
                            grouper = scope_to_grouper[scope]

                        grouper.contents_debug_adapter_protocol.append(entry)

                else:
                    new_lst.append(entry)

            for scope in DAPGrouper.SCOPES_SORTED:
                grouper = scope_to_grouper.get(scope)
                if grouper is not None:
                    group_entries.append((scope, grouper, None))

        return new_lst, group_entries


class _ObjectVariable(_AbstractVariable):
    def __init__(self, py_db, name, value, register_variable, is_return_value=False, evaluate_name=None, frame=None):
        _AbstractVariable.__init__(self, py_db)
        self.frame = frame
        self.name = name
        self.value = value
        self._register_variable = register_variable
        self._register_variable(self)
        self._is_return_value = is_return_value
        self.evaluate_name = evaluate_name

    @silence_warnings_decorator
    @overrides(_AbstractVariable.get_children_variables)
    def get_children_variables(self, fmt=None, scope=None):
        _type, _type_name, resolver = get_type(self.value)

        children_variables = []
        if resolver is not None:  # i.e.: it's a container.
            if hasattr(resolver, "get_contents_debug_adapter_protocol"):
                # The get_contents_debug_adapter_protocol needs to return sorted.
                lst = resolver.get_contents_debug_adapter_protocol(self.value, fmt=fmt)
            else:
                # If there's no special implementation, the default is sorting the keys.
                dct = resolver.get_dictionary(self.value)
                lst = sorted(dct.items(), key=lambda tup: sorted_attributes_key(tup[0]))
                # No evaluate name in this case.
                lst = [(key, value, None) for (key, value) in lst]

            lst, group_entries = self._group_entries(lst, handle_return_values=False)
            if group_entries:
                lst = group_entries + lst
            parent_evaluate_name = self.evaluate_name
            if parent_evaluate_name:
                for key, val, evaluate_name in lst:
                    if evaluate_name is not None:
                        if callable(evaluate_name):
                            evaluate_name = evaluate_name(parent_evaluate_name)
                        else:
                            evaluate_name = parent_evaluate_name + evaluate_name
                    variable = _ObjectVariable(self.py_db, key, val, self._register_variable, evaluate_name=evaluate_name, frame=self.frame)
                    children_variables.append(variable)
            else:
                for key, val, evaluate_name in lst:
                    # No evaluate name
                    variable = _ObjectVariable(self.py_db, key, val, self._register_variable, frame=self.frame)
                    children_variables.append(variable)

        return children_variables

    def change_variable(self, name, value, py_db, fmt=None, scope: Optional[ScopeRequest]=None):
        children_variable = self.get_child_variable_named(name)
        if children_variable is None:
            return None

        var_data = children_variable.get_var_data()
        evaluate_name = var_data.get("evaluateName")

        if not evaluate_name:
            # Note: right now we only pass control to the resolver in the cases where
            # there's no evaluate name (the idea being that if we can evaluate it,
            # we can use that evaluation to set the value too -- if in the future
            # a case where this isn't true is found this logic may need to be changed).
            _type, _type_name, container_resolver = get_type(self.value)
            if hasattr(container_resolver, "change_var_from_name"):
                try:
                    new_value = eval(value)
                except:
                    return None
                new_key = container_resolver.change_var_from_name(self.value, name, new_value)
                if new_key is not None:
                    return _ObjectVariable(self.py_db, new_key, new_value, self._register_variable, evaluate_name=None, frame=self.frame)

                return None
            else:
                return None

        frame = self.frame
        if frame is None:
            return None

        try:
            # This handles the simple cases (such as dict, list, object)
            Exec("%s=%s" % (evaluate_name, value), frame.f_globals, frame.f_locals)
        except:
            return None

        return self.get_child_variable_named(name, fmt=fmt)


def sorted_variables_key(obj):
    return sorted_attributes_key(obj.name)


class _FrameVariable(_AbstractVariable):
    def __init__(self, py_db, frame, register_variable):
        _AbstractVariable.__init__(self, py_db)
        self.frame = frame

        self.name = self.frame.f_code.co_name
        self.value = frame

        self._register_variable = register_variable
        self._register_variable(self)

    def change_variable(self, name, value, py_db, fmt=None, scope: Optional[ScopeRequest]=None):
        frame = self.frame
        pydevd_vars.change_attr_expression(frame, name, value, py_db, scope=scope)
        return self.get_child_variable_named(name, fmt=fmt, scope=scope)

    @silence_warnings_decorator
    @overrides(_AbstractVariable.get_children_variables)
    def get_children_variables(self, fmt=None, scope=None):
        children_variables = []
        if scope is not None:
            assert isinstance(scope, ScopeRequest)
            scope = scope.scope

        if scope in ("locals", None):
            dct = self.frame.f_locals
        elif scope == "globals":
            dct = self.frame.f_globals
        else:
            raise AssertionError("Unexpected scope: %s" % (scope,))

        lst, group_entries = self._group_entries(
            [(x[0], x[1], None) for x in list(dct.items()) if x[0] != "_pydev_stop_at_break"], handle_return_values=True
        )
        group_variables = []

        for key, val, _ in group_entries:
            # Make sure that the contents in the group are also sorted.
            val.contents_debug_adapter_protocol.sort(key=lambda v: sorted_attributes_key(v[0]))
            variable = _ObjectVariable(self.py_db, key, val, self._register_variable, False, key, frame=self.frame)
            group_variables.append(variable)

        for key, val, _ in lst:
            is_return_value = key == RETURN_VALUES_DICT
            if is_return_value:
                for return_key, return_value in val.items():
                    variable = _ObjectVariable(
                        self.py_db,
                        return_key,
                        return_value,
                        self._register_variable,
                        is_return_value,
                        "%s[%r]" % (key, return_key),
                        frame=self.frame,
                    )
                    children_variables.append(variable)
            else:
                variable = _ObjectVariable(self.py_db, key, val, self._register_variable, is_return_value, key, frame=self.frame)
                children_variables.append(variable)

        # Frame variables always sorted.
        children_variables.sort(key=sorted_variables_key)
        if group_variables:
            # Groups have priority over other variables.
            children_variables = group_variables + children_variables

        return children_variables


class _FramesTracker(object):
    """
    This is a helper class to be used to track frames when a thread becomes suspended.
    """

    def __init__(self, suspended_frames_manager, py_db):
        self._suspended_frames_manager = suspended_frames_manager
        self.py_db = py_db
        self._frame_id_to_frame = {}

        # Note that a given frame may appear in multiple threads when we have custom
        # frames added, but as those are coroutines, this map will point to the actual
        # main thread (which is the one that needs to be suspended for us to get the
        # variables).
        self._frame_id_to_main_thread_id = {}

        # A map of the suspended thread id -> list(frames ids) -- note that
        # frame ids are kept in order (the first one is the suspended frame).
        self._thread_id_to_frame_ids = {}

        self._thread_id_to_frames_list = {}

        # The main suspended thread (if this is a coroutine this isn't the id of the
        # coroutine thread, it's the id of the actual suspended thread).
        self._main_thread_id = None

        # Helper to know if it was already untracked.
        self._untracked = False

        # We need to be thread-safe!
        self._lock = ForkSafeLock(rlock=True)

        self._variable_reference_to_variable = {}

    def _register_variable(self, variable):
        variable_reference = variable.get_variable_reference()
        self._variable_reference_to_variable[variable_reference] = variable

    def obtain_as_variable(self, name, value, evaluate_name=None, frame=None):
        if evaluate_name is None:
            evaluate_name = name

        variable_reference = id(value)
        variable = self._variable_reference_to_variable.get(variable_reference)
        if variable is not None:
            return variable

        # Still not created, let's do it now.
        return _ObjectVariable(
            self.py_db, name, value, self._register_variable, is_return_value=False, evaluate_name=evaluate_name, frame=frame
        )

    def get_main_thread_id(self):
        return self._main_thread_id

    def get_variable(self, variable_reference):
        return self._variable_reference_to_variable[variable_reference]

    def track(self, thread_id, frames_list, frame_custom_thread_id=None):
        """
        :param thread_id:
            The thread id to be used for this frame.

        :param FramesList frames_list:
            A list of frames to be tracked (the first is the topmost frame which is suspended at the given thread).

        :param frame_custom_thread_id:
            If None this this is the id of the thread id for the custom frame (i.e.: coroutine).
        """
        assert frames_list.__class__ == FramesList
        with self._lock:
            coroutine_or_main_thread_id = frame_custom_thread_id or thread_id

            if coroutine_or_main_thread_id in self._suspended_frames_manager._thread_id_to_tracker:
                sys.stderr.write("pydevd: Something is wrong. Tracker being added twice to the same thread id.\n")

            self._suspended_frames_manager._thread_id_to_tracker[coroutine_or_main_thread_id] = self
            self._main_thread_id = thread_id

            frame_ids_from_thread = self._thread_id_to_frame_ids.setdefault(coroutine_or_main_thread_id, [])

            self._thread_id_to_frames_list[coroutine_or_main_thread_id] = frames_list
            for frame in frames_list:
                frame_id = id(frame)
                self._frame_id_to_frame[frame_id] = frame
                _FrameVariable(self.py_db, frame, self._register_variable)  # Instancing is enough to register.
                self._suspended_frames_manager._variable_reference_to_frames_tracker[frame_id] = self
                frame_ids_from_thread.append(frame_id)

                self._frame_id_to_main_thread_id[frame_id] = thread_id

            frame = None

    def untrack_all(self):
        with self._lock:
            if self._untracked:
                # Calling multiple times is expected for the set next statement.
                return
            self._untracked = True
            for thread_id in self._thread_id_to_frame_ids:
                self._suspended_frames_manager._thread_id_to_tracker.pop(thread_id, None)

            for frame_id in self._frame_id_to_frame:
                del self._suspended_frames_manager._variable_reference_to_frames_tracker[frame_id]

            self._frame_id_to_frame.clear()
            self._frame_id_to_main_thread_id.clear()
            self._thread_id_to_frame_ids.clear()
            self._thread_id_to_frames_list.clear()
            self._main_thread_id = None
            self._suspended_frames_manager = None
            self._variable_reference_to_variable.clear()

    def get_frames_list(self, thread_id):
        with self._lock:
            return self._thread_id_to_frames_list.get(thread_id)

    def find_frame(self, thread_id, frame_id):
        with self._lock:
            return self._frame_id_to_frame.get(frame_id)

    def create_thread_suspend_command(self, thread_id, stop_reason, message, trace_suspend_type, thread, additional_info):
        with self._lock:
            # First one is topmost frame suspended.
            frames_list = self._thread_id_to_frames_list[thread_id]

            cmd = self.py_db.cmd_factory.make_thread_suspend_message(
                self.py_db, thread_id, frames_list, stop_reason, message, trace_suspend_type, thread, additional_info
            )

            frames_list = None
            return cmd


class SuspendedFramesManager(object):
    def __init__(self):
        self._thread_id_to_fake_frames = {}
        self._thread_id_to_tracker = {}

        # Mappings
        self._variable_reference_to_frames_tracker = {}

    def _get_tracker_for_variable_reference(self, variable_reference):
        tracker = self._variable_reference_to_frames_tracker.get(variable_reference)
        if tracker is not None:
            return tracker

        for _thread_id, tracker in self._thread_id_to_tracker.items():
            try:
                tracker.get_variable(variable_reference)
            except KeyError:
                pass
            else:
                return tracker

        return None

    def get_thread_id_for_variable_reference(self, variable_reference):
        """
        We can't evaluate variable references values on any thread, only in the suspended
        thread (the main reason for this is that in UI frameworks inspecting a UI object
        from a different thread can potentially crash the application).

        :param int variable_reference:
            The variable reference (can be either a frame id or a reference to a previously
            gotten variable).

        :return str:
            The thread id for the thread to be used to inspect the given variable reference or
            None if the thread was already resumed.
        """
        frames_tracker = self._get_tracker_for_variable_reference(variable_reference)
        if frames_tracker is not None:
            return frames_tracker.get_main_thread_id()
        return None

    def get_frame_tracker(self, thread_id):
        return self._thread_id_to_tracker.get(thread_id)

    def get_variable(self, variable_reference):
        """
        :raises KeyError
        """
        frames_tracker = self._get_tracker_for_variable_reference(variable_reference)
        if frames_tracker is None:
            raise KeyError()
        return frames_tracker.get_variable(variable_reference)

    def get_frames_list(self, thread_id):
        tracker = self._thread_id_to_tracker.get(thread_id)
        if tracker is None:
            return None
        return tracker.get_frames_list(thread_id)

    @contextmanager
    def track_frames(self, py_db):
        tracker = _FramesTracker(self, py_db)
        try:
            yield tracker
        finally:
            tracker.untrack_all()

    def add_fake_frame(self, thread_id, frame_id, frame):
        self._thread_id_to_fake_frames.setdefault(thread_id, {})[int(frame_id)] = frame

    def find_frame(self, thread_id, frame_id):
        try:
            if frame_id == "*":
                return get_frame()  # any frame is specified with "*"
            frame_id = int(frame_id)

            fake_frames = self._thread_id_to_fake_frames.get(thread_id)
            if fake_frames is not None:
                frame = fake_frames.get(frame_id)
                if frame is not None:
                    return frame

            frames_tracker = self._thread_id_to_tracker.get(thread_id)
            if frames_tracker is not None:
                frame = frames_tracker.find_frame(thread_id, frame_id)
                if frame is not None:
                    return frame

            return None
        except:
            pydev_log.exception()
            return None

# === NexusCore/openenv\Lib\site-packages\fsspec\parquet.py ===
import io
import json
import warnings

from .core import url_to_fs
from .utils import merge_offset_ranges

# Parquet-Specific Utilities for fsspec
#
# Most of the functions defined in this module are NOT
# intended for public consumption. The only exception
# to this is `open_parquet_file`, which should be used
# place of `fs.open()` to open parquet-formatted files
# on remote file systems.


def open_parquet_file(
    path,
    mode="rb",
    fs=None,
    metadata=None,
    columns=None,
    row_groups=None,
    storage_options=None,
    strict=False,
    engine="auto",
    max_gap=64_000,
    max_block=256_000_000,
    footer_sample_size=1_000_000,
    **kwargs,
):
    """
    Return a file-like object for a single Parquet file.

    The specified parquet `engine` will be used to parse the
    footer metadata, and determine the required byte ranges
    from the file. The target path will then be opened with
    the "parts" (`KnownPartsOfAFile`) caching strategy.

    Note that this method is intended for usage with remote
    file systems, and is unlikely to improve parquet-read
    performance on local file systems.

    Parameters
    ----------
    path: str
        Target file path.
    mode: str, optional
        Mode option to be passed through to `fs.open`. Default is "rb".
    metadata: Any, optional
        Parquet metadata object. Object type must be supported
        by the backend parquet engine. For now, only the "fastparquet"
        engine supports an explicit `ParquetFile` metadata object.
        If a metadata object is supplied, the remote footer metadata
        will not need to be transferred into local memory.
    fs: AbstractFileSystem, optional
        Filesystem object to use for opening the file. If nothing is
        specified, an `AbstractFileSystem` object will be inferred.
    engine : str, default "auto"
        Parquet engine to use for metadata parsing. Allowed options
        include "fastparquet", "pyarrow", and "auto". The specified
        engine must be installed in the current environment. If
        "auto" is specified, and both engines are installed,
        "fastparquet" will take precedence over "pyarrow".
    columns: list, optional
        List of all column names that may be read from the file.
    row_groups : list, optional
        List of all row-groups that may be read from the file. This
        may be a list of row-group indices (integers), or it may be
        a list of `RowGroup` metadata objects (if the "fastparquet"
        engine is used).
    storage_options : dict, optional
        Used to generate an `AbstractFileSystem` object if `fs` was
        not specified.
    strict : bool, optional
        Whether the resulting `KnownPartsOfAFile` cache should
        fetch reads that go beyond a known byte-range boundary.
        If `False` (the default), any read that ends outside a
        known part will be zero padded. Note that using
        `strict=True` may be useful for debugging.
    max_gap : int, optional
        Neighboring byte ranges will only be merged when their
        inter-range gap is <= `max_gap`. Default is 64KB.
    max_block : int, optional
        Neighboring byte ranges will only be merged when the size of
        the aggregated range is <= `max_block`. Default is 256MB.
    footer_sample_size : int, optional
        Number of bytes to read from the end of the path to look
        for the footer metadata. If the sampled bytes do not contain
        the footer, a second read request will be required, and
        performance will suffer. Default is 1MB.
    **kwargs :
        Optional key-word arguments to pass to `fs.open`
    """

    # Make sure we have an `AbstractFileSystem` object
    # to work with
    if fs is None:
        fs = url_to_fs(path, **(storage_options or {}))[0]

    # For now, `columns == []` not supported. Just use
    # default `open` command with `path` input
    if columns is not None and len(columns) == 0:
        return fs.open(path, mode=mode)

    # Set the engine
    engine = _set_engine(engine)

    # Fetch the known byte ranges needed to read
    # `columns` and/or `row_groups`
    data = _get_parquet_byte_ranges(
        [path],
        fs,
        metadata=metadata,
        columns=columns,
        row_groups=row_groups,
        engine=engine,
        max_gap=max_gap,
        max_block=max_block,
        footer_sample_size=footer_sample_size,
    )

    # Extract file name from `data`
    fn = next(iter(data)) if data else path

    # Call self.open with "parts" caching
    options = kwargs.pop("cache_options", {}).copy()
    return fs.open(
        fn,
        mode=mode,
        cache_type="parts",
        cache_options={
            **options,
            "data": data.get(fn, {}),
            "strict": strict,
        },
        **kwargs,
    )


def _get_parquet_byte_ranges(
    paths,
    fs,
    metadata=None,
    columns=None,
    row_groups=None,
    max_gap=64_000,
    max_block=256_000_000,
    footer_sample_size=1_000_000,
    engine="auto",
):
    """Get a dictionary of the known byte ranges needed
    to read a specific column/row-group selection from a
    Parquet dataset. Each value in the output dictionary
    is intended for use as the `data` argument for the
    `KnownPartsOfAFile` caching strategy of a single path.
    """

    # Set engine if necessary
    if isinstance(engine, str):
        engine = _set_engine(engine)

    # Pass to specialized function if metadata is defined
    if metadata is not None:
        # Use the provided parquet metadata object
        # to avoid transferring/parsing footer metadata
        return _get_parquet_byte_ranges_from_metadata(
            metadata,
            fs,
            engine,
            columns=columns,
            row_groups=row_groups,
            max_gap=max_gap,
            max_block=max_block,
        )

    # Get file sizes asynchronously
    file_sizes = fs.sizes(paths)

    # Populate global paths, starts, & ends
    result = {}
    data_paths = []
    data_starts = []
    data_ends = []
    add_header_magic = True
    if columns is None and row_groups is None:
        # We are NOT selecting specific columns or row-groups.
        #
        # We can avoid sampling the footers, and just transfer
        # all file data with cat_ranges
        for i, path in enumerate(paths):
            result[path] = {}
            for b in range(0, file_sizes[i], max_block):
                data_paths.append(path)
                data_starts.append(b)
                data_ends.append(min(b + max_block, file_sizes[i]))
        add_header_magic = False  # "Magic" should already be included
    else:
        # We ARE selecting specific columns or row-groups.
        #
        # Gather file footers.
        # We just take the last `footer_sample_size` bytes of each
        # file (or the entire file if it is smaller than that)
        footer_starts = []
        footer_ends = []
        for i, path in enumerate(paths):
            footer_ends.append(file_sizes[i])
            sample_size = max(0, file_sizes[i] - footer_sample_size)
            footer_starts.append(sample_size)
        footer_samples = fs.cat_ranges(paths, footer_starts, footer_ends)

        # Check our footer samples and re-sample if necessary.
        missing_footer_starts = footer_starts.copy()
        large_footer = 0
        for i, path in enumerate(paths):
            footer_size = int.from_bytes(footer_samples[i][-8:-4], "little")
            real_footer_start = file_sizes[i] - (footer_size + 8)
            if real_footer_start < footer_starts[i]:
                missing_footer_starts[i] = real_footer_start
                large_footer = max(large_footer, (footer_size + 8))
        if large_footer:
            warnings.warn(
                f"Not enough data was used to sample the parquet footer. "
                f"Try setting footer_sample_size >= {large_footer}."
            )
            for i, block in enumerate(
                fs.cat_ranges(
                    paths,
                    missing_footer_starts,
                    footer_starts,
                )
            ):
                footer_samples[i] = block + footer_samples[i]
                footer_starts[i] = missing_footer_starts[i]

        # Calculate required byte ranges for each path
        for i, path in enumerate(paths):
            # Deal with small-file case.
            # Just include all remaining bytes of the file
            # in a single range.
            if file_sizes[i] < max_block:
                if footer_starts[i] > 0:
                    # Only need to transfer the data if the
                    # footer sample isn't already the whole file
                    data_paths.append(path)
                    data_starts.append(0)
                    data_ends.append(footer_starts[i])
                continue

            # Use "engine" to collect data byte ranges
            path_data_starts, path_data_ends = engine._parquet_byte_ranges(
                columns,
                row_groups=row_groups,
                footer=footer_samples[i],
                footer_start=footer_starts[i],
            )

            data_paths += [path] * len(path_data_starts)
            data_starts += path_data_starts
            data_ends += path_data_ends

        # Merge adjacent offset ranges
        data_paths, data_starts, data_ends = merge_offset_ranges(
            data_paths,
            data_starts,
            data_ends,
            max_gap=max_gap,
            max_block=max_block,
            sort=False,  # Should already be sorted
        )

        # Start by populating `result` with footer samples
        for i, path in enumerate(paths):
            result[path] = {(footer_starts[i], footer_ends[i]): footer_samples[i]}

    # Transfer the data byte-ranges into local memory
    _transfer_ranges(fs, result, data_paths, data_starts, data_ends)

    # Add b"PAR1" to header if necessary
    if add_header_magic:
        _add_header_magic(result)

    return result


def _get_parquet_byte_ranges_from_metadata(
    metadata,
    fs,
    engine,
    columns=None,
    row_groups=None,
    max_gap=64_000,
    max_block=256_000_000,
):
    """Simplified version of `_get_parquet_byte_ranges` for
    the case that an engine-specific `metadata` object is
    provided, and the remote footer metadata does not need to
    be transferred before calculating the required byte ranges.
    """

    # Use "engine" to collect data byte ranges
    data_paths, data_starts, data_ends = engine._parquet_byte_ranges(
        columns,
        row_groups=row_groups,
        metadata=metadata,
    )

    # Merge adjacent offset ranges
    data_paths, data_starts, data_ends = merge_offset_ranges(
        data_paths,
        data_starts,
        data_ends,
        max_gap=max_gap,
        max_block=max_block,
        sort=False,  # Should be sorted
    )

    # Transfer the data byte-ranges into local memory
    result = {fn: {} for fn in list(set(data_paths))}
    _transfer_ranges(fs, result, data_paths, data_starts, data_ends)

    # Add b"PAR1" to header
    _add_header_magic(result)

    return result


def _transfer_ranges(fs, blocks, paths, starts, ends):
    # Use cat_ranges to gather the data byte_ranges
    ranges = (paths, starts, ends)
    for path, start, stop, data in zip(*ranges, fs.cat_ranges(*ranges)):
        blocks[path][(start, stop)] = data


def _add_header_magic(data):
    # Add b"PAR1" to file headers
    for path in list(data.keys()):
        add_magic = True
        for k in data[path]:
            if k[0] == 0 and k[1] >= 4:
                add_magic = False
                break
        if add_magic:
            data[path][(0, 4)] = b"PAR1"


def _set_engine(engine_str):
    # Define a list of parquet engines to try
    if engine_str == "auto":
        try_engines = ("fastparquet", "pyarrow")
    elif not isinstance(engine_str, str):
        raise ValueError(
            "Failed to set parquet engine! "
            "Please pass 'fastparquet', 'pyarrow', or 'auto'"
        )
    elif engine_str not in ("fastparquet", "pyarrow"):
        raise ValueError(f"{engine_str} engine not supported by `fsspec.parquet`")
    else:
        try_engines = [engine_str]

    # Try importing the engines in `try_engines`,
    # and choose the first one that succeeds
    for engine in try_engines:
        try:
            if engine == "fastparquet":
                return FastparquetEngine()
            elif engine == "pyarrow":
                return PyarrowEngine()
        except ImportError:
            pass

    # Raise an error if a supported parquet engine
    # was not found
    raise ImportError(
        f"The following parquet engines are not installed "
        f"in your python environment: {try_engines}."
        f"Please install 'fastparquert' or 'pyarrow' to "
        f"utilize the `fsspec.parquet` module."
    )


class FastparquetEngine:
    # The purpose of the FastparquetEngine class is
    # to check if fastparquet can be imported (on initialization)
    # and to define a `_parquet_byte_ranges` method. In the
    # future, this class may also be used to define other
    # methods/logic that are specific to fastparquet.

    def __init__(self):
        import fastparquet as fp

        self.fp = fp

    def _row_group_filename(self, row_group, pf):
        return pf.row_group_filename(row_group)

    def _parquet_byte_ranges(
        self,
        columns,
        row_groups=None,
        metadata=None,
        footer=None,
        footer_start=None,
    ):
        # Initialize offset ranges and define ParqetFile metadata
        pf = metadata
        data_paths, data_starts, data_ends = [], [], []
        if pf is None:
            pf = self.fp.ParquetFile(io.BytesIO(footer))

        # Convert columns to a set and add any index columns
        # specified in the pandas metadata (just in case)
        column_set = None if columns is None else set(columns)
        if column_set is not None and hasattr(pf, "pandas_metadata"):
            md_index = [
                ind
                for ind in pf.pandas_metadata.get("index_columns", [])
                # Ignore RangeIndex information
                if not isinstance(ind, dict)
            ]
            column_set |= set(md_index)

        # Check if row_groups is a list of integers
        # or a list of row-group metadata
        if row_groups and not isinstance(row_groups[0], int):
            # Input row_groups contains row-group metadata
            row_group_indices = None
        else:
            # Input row_groups contains row-group indices
            row_group_indices = row_groups
            row_groups = pf.row_groups

        # Loop through column chunks to add required byte ranges
        for r, row_group in enumerate(row_groups):
            # Skip this row-group if we are targeting
            # specific row-groups
            if row_group_indices is None or r in row_group_indices:
                # Find the target parquet-file path for `row_group`
                fn = self._row_group_filename(row_group, pf)

                for column in row_group.columns:
                    name = column.meta_data.path_in_schema[0]
                    # Skip this column if we are targeting a
                    # specific columns
                    if column_set is None or name in column_set:
                        file_offset0 = column.meta_data.dictionary_page_offset
                        if file_offset0 is None:
                            file_offset0 = column.meta_data.data_page_offset
                        num_bytes = column.meta_data.total_compressed_size
                        if footer_start is None or file_offset0 < footer_start:
                            data_paths.append(fn)
                            data_starts.append(file_offset0)
                            data_ends.append(
                                min(
                                    file_offset0 + num_bytes,
                                    footer_start or (file_offset0 + num_bytes),
                                )
                            )

        if metadata:
            # The metadata in this call may map to multiple
            # file paths. Need to include `data_paths`
            return data_paths, data_starts, data_ends
        return data_starts, data_ends


class PyarrowEngine:
    # The purpose of the PyarrowEngine class is
    # to check if pyarrow can be imported (on initialization)
    # and to define a `_parquet_byte_ranges` method. In the
    # future, this class may also be used to define other
    # methods/logic that are specific to pyarrow.

    def __init__(self):
        import pyarrow.parquet as pq

        self.pq = pq

    def _row_group_filename(self, row_group, metadata):
        raise NotImplementedError

    def _parquet_byte_ranges(
        self,
        columns,
        row_groups=None,
        metadata=None,
        footer=None,
        footer_start=None,
    ):
        if metadata is not None:
            raise ValueError("metadata input not supported for PyarrowEngine")

        data_starts, data_ends = [], []
        md = self.pq.ParquetFile(io.BytesIO(footer)).metadata

        # Convert columns to a set and add any index columns
        # specified in the pandas metadata (just in case)
        column_set = None if columns is None else set(columns)
        if column_set is not None:
            schema = md.schema.to_arrow_schema()
            has_pandas_metadata = (
                schema.metadata is not None and b"pandas" in schema.metadata
            )
            if has_pandas_metadata:
                md_index = [
                    ind
                    for ind in json.loads(
                        schema.metadata[b"pandas"].decode("utf8")
                    ).get("index_columns", [])
                    # Ignore RangeIndex information
                    if not isinstance(ind, dict)
                ]
                column_set |= set(md_index)

        # Loop through column chunks to add required byte ranges
        for r in range(md.num_row_groups):
            # Skip this row-group if we are targeting
            # specific row-groups
            if row_groups is None or r in row_groups:
                row_group = md.row_group(r)
                for c in range(row_group.num_columns):
                    column = row_group.column(c)
                    name = column.path_in_schema
                    # Skip this column if we are targeting a
                    # specific columns
                    split_name = name.split(".")[0]
                    if (
                        column_set is None
                        or name in column_set
                        or split_name in column_set
                    ):
                        file_offset0 = column.dictionary_page_offset
                        if file_offset0 is None:
                            file_offset0 = column.data_page_offset
                        num_bytes = column.total_compressed_size
                        if file_offset0 < footer_start:
                            data_starts.append(file_offset0)
                            data_ends.append(
                                min(file_offset0 + num_bytes, footer_start)
                            )
        return data_starts, data_ends

# === NexusCore/openenv\Lib\site-packages\interpreter\terminal_interface\terminal_interface.py ===
"""
The terminal interface is just a view. Just handles the very top layer.
If you were to build a frontend this would be a way to do it.
"""

try:
    import readline
except ImportError:
    pass

import os
import platform
import random
import re
import subprocess
import tempfile
import time

from ..core.utils.scan_code import scan_code
from ..core.utils.system_debug_info import system_info
from ..core.utils.truncate_output import truncate_output
from .components.code_block import CodeBlock
from .components.message_block import MessageBlock
from .magic_commands import handle_magic_command
from .utils.check_for_package import check_for_package
from .utils.cli_input import cli_input
from .utils.display_output import display_output
from .utils.find_image_path import find_image_path

# Add examples to the readline history
examples = [
    "How many files are on my desktop?",
    "What time is it in Seattle?",
    "Make me a simple Pomodoro app.",
    "Open Chrome and go to YouTube.",
    "Can you set my system to light mode?",
]
random.shuffle(examples)
try:
    for example in examples:
        readline.add_history(example)
except:
    # If they don't have readline, that's fine
    pass


def terminal_interface(interpreter, message):
    # Auto run and offline (this.. this isn't right) don't display messages.
    # Probably worth abstracting this to something like "debug_cli" at some point.
    # If (len(interpreter.messages) == 1), they probably used the advanced "i {command}" entry, so no message should be displayed.
    if (
        not interpreter.auto_run
        and not interpreter.offline
        and not (len(interpreter.messages) == 1)
    ):
        interpreter_intro_message = [
            "**Open Interpreter** will require approval before running code."
        ]

        if interpreter.safe_mode == "ask" or interpreter.safe_mode == "auto":
            if not check_for_package("semgrep"):
                interpreter_intro_message.append(
                    f"**Safe Mode**: {interpreter.safe_mode}\n\n>Note: **Safe Mode** requires `semgrep` (`pip install semgrep`)"
                )
        else:
            interpreter_intro_message.append("Use `interpreter -y` to bypass this.")

        if (
            not interpreter.plain_text_display
        ):  # A proxy/heuristic for standard in mode, which isn't tracked (but prob should be)
            interpreter_intro_message.append("Press `CTRL-C` to exit.")

        interpreter.display_message("\n\n".join(interpreter_intro_message) + "\n")

    if message:
        interactive = False
    else:
        interactive = True

    active_block = None
    voice_subprocess = None

    while True:
        if interactive:
            if (
                len(interpreter.messages) == 1
                and interpreter.messages[-1]["role"] == "user"
                and interpreter.messages[-1]["type"] == "message"
            ):
                # They passed in a message already, probably via "i {command}"!
                message = interpreter.messages[-1]["content"]
                interpreter.messages = interpreter.messages[:-1]
            else:
                ### This is the primary input for Open Interpreter.
                try:
                    message = (
                        cli_input("> ").strip()
                        if interpreter.multi_line
                        else input("> ").strip()
                    )
                except (KeyboardInterrupt, EOFError):
                    # Treat Ctrl-D on an empty line the same as Ctrl-C by exiting gracefully
                    interpreter.display_message("\n\n`Exiting...`")
                    raise KeyboardInterrupt

            try:
                # This lets users hit the up arrow key for past messages
                readline.add_history(message)
            except:
                # If the user doesn't have readline (may be the case on windows), that's fine
                pass

        if isinstance(message, str):
            # This is for the terminal interface being used as a CLI — messages are strings.
            # This won't fire if they're in the python package, display=True, and they passed in an array of messages (for example).

            if message == "":
                # Ignore empty messages when user presses enter without typing anything
                continue

            if message.startswith("%") and interactive:
                handle_magic_command(interpreter, message)
                continue

            # Many users do this
            if message.strip() == "interpreter --local":
                print("Please exit this conversation, then run `interpreter --local`.")
                continue
            if message.strip() == "pip install --upgrade open-interpreter":
                print(
                    "Please exit this conversation, then run `pip install --upgrade open-interpreter`."
                )
                continue

            if (
                interpreter.llm.supports_vision
                or interpreter.llm.vision_renderer != None
            ):
                # Is the input a path to an image? Like they just dragged it into the terminal?
                image_path = find_image_path(message)

                ## If we found an image, add it to the message
                if image_path:
                    # Add the text interpreter's message history
                    interpreter.messages.append(
                        {
                            "role": "user",
                            "type": "message",
                            "content": message,
                        }
                    )

                    # Pass in the image to interpreter in a moment
                    message = {
                        "role": "user",
                        "type": "image",
                        "format": "path",
                        "content": image_path,
                    }

        try:
            for chunk in interpreter.chat(message, display=False, stream=True):
                yield chunk

                # Is this for thine eyes?
                if "recipient" in chunk and chunk["recipient"] != "user":
                    continue

                if interpreter.verbose:
                    print("Chunk in `terminal_interface`:", chunk)

                # Comply with PyAutoGUI fail-safe for OS mode
                # so people can turn it off by moving their mouse to a corner
                if interpreter.os:
                    if (
                        chunk.get("format") == "output"
                        and "failsafeexception" in chunk["content"].lower()
                    ):
                        print("Fail-safe triggered (mouse in one of the four corners).")
                        break

                if chunk["type"] == "review" and chunk.get("content"):
                    # Specialized models can emit a code review.
                    print(chunk.get("content"), end="", flush=True)

                # Execution notice
                if chunk["type"] == "confirmation":
                    if not interpreter.auto_run:
                        # OI is about to execute code. The user wants to approve this

                        # End the active code block so you can run input() below it
                        if active_block and not interpreter.plain_text_display:
                            active_block.refresh(cursor=False)
                            active_block.end()
                            active_block = None

                        code_to_run = chunk["content"]
                        language = code_to_run["format"]
                        code = code_to_run["content"]

                        should_scan_code = False

                        if not interpreter.safe_mode == "off":
                            if interpreter.safe_mode == "auto":
                                should_scan_code = True
                            elif interpreter.safe_mode == "ask":
                                response = input(
                                    "  Would you like to scan this code? (y/n)\n\n  "
                                )
                                print("")  # <- Aesthetic choice

                                if response.strip().lower() == "y":
                                    should_scan_code = True

                        if should_scan_code:
                            scan_code(code, language, interpreter)

                        if interpreter.plain_text_display:
                            response = input(
                                "Would you like to run this code? (y/n)\n\n"
                            )
                        else:
                            response = input(
                                "  Would you like to run this code? (y/n)\n\n  "
                            )
                        print("")  # <- Aesthetic choice

                        if response.strip().lower() == "y":
                            # Create a new, identical block where the code will actually be run
                            # Conveniently, the chunk includes everything we need to do this:
                            active_block = CodeBlock(interpreter)
                            active_block.margin_top = False  # <- Aesthetic choice
                            active_block.language = language
                            active_block.code = code
                        elif response.strip().lower() == "e":
                            # Edit

                            # Create a temporary file
                            with tempfile.NamedTemporaryFile(
                                suffix=".tmp", delete=False
                            ) as tf:
                                tf.write(code.encode())
                                tf.flush()

                            # Open the temporary file with the default editor
                            subprocess.call([os.environ.get("EDITOR", "vim"), tf.name])

                            # Read the modified code
                            with open(tf.name, "r") as tf:
                                code = tf.read()

                            interpreter.messages[-1]["content"] = code  # Give it code

                            # Delete the temporary file
                            os.unlink(tf.name)
                            active_block = CodeBlock()
                            active_block.margin_top = False  # <- Aesthetic choice
                            active_block.language = language
                            active_block.code = code
                        else:
                            # User declined to run code.
                            interpreter.messages.append(
                                {
                                    "role": "user",
                                    "type": "message",
                                    "content": "I have declined to run this code.",
                                }
                            )
                            break

                # Plain text mode
                if interpreter.plain_text_display:
                    if "start" in chunk or "end" in chunk:
                        print("")
                    if chunk["type"] in ["code", "console"] and "format" in chunk:
                        if "start" in chunk:
                            print("```" + chunk["format"], flush=True)
                        if "end" in chunk:
                            print("```", flush=True)
                    if chunk.get("format") != "active_line":
                        print(chunk.get("content", ""), end="", flush=True)
                    continue

                if "end" in chunk and active_block:
                    active_block.refresh(cursor=False)

                    if chunk["type"] in [
                        "message",
                        "console",
                    ]:  # We don't stop on code's end — code + console output are actually one block.
                        active_block.end()
                        active_block = None

                # Assistant message blocks
                if chunk["type"] == "message":
                    if "start" in chunk:
                        active_block = MessageBlock()
                        render_cursor = True

                    if "content" in chunk:
                        active_block.message += chunk["content"]

                    if "end" in chunk and interpreter.os:
                        last_message = interpreter.messages[-1]["content"]

                        # Remove markdown lists and the line above markdown lists
                        lines = last_message.split("\n")
                        i = 0
                        while i < len(lines):
                            # Match markdown lists starting with hyphen, asterisk or number
                            if re.match(r"^\s*([-*]|\d+\.)\s", lines[i]):
                                del lines[i]
                                if i > 0:
                                    del lines[i - 1]
                                    i -= 1
                            else:
                                i += 1
                        message = "\n".join(lines)
                        # Replace newlines with spaces, escape double quotes and backslashes
                        sanitized_message = (
                            message.replace("\\", "\\\\")
                            .replace("\n", " ")
                            .replace('"', '\\"')
                        )

                        # Display notification in OS mode
                        interpreter.computer.os.notify(sanitized_message)

                        # Speak message aloud
                        if platform.system() == "Darwin" and interpreter.speak_messages:
                            if voice_subprocess:
                                voice_subprocess.terminate()
                            voice_subprocess = subprocess.Popen(
                                [
                                    "osascript",
                                    "-e",
                                    f'say "{sanitized_message}" using "Fred"',
                                ]
                            )
                        else:
                            pass
                            # User isn't on a Mac, so we can't do this. You should tell them something about that when they first set this up.
                            # Or use a universal TTS library.

                # Assistant code blocks
                elif chunk["role"] == "assistant" and chunk["type"] == "code":
                    if "start" in chunk:
                        active_block = CodeBlock()
                        active_block.language = chunk["format"]
                        render_cursor = True

                    if "content" in chunk:
                        active_block.code += chunk["content"]

                # Computer can display visual types to user,
                # Which sometimes creates more computer output (e.g. HTML errors, eventually)
                if (
                    chunk["role"] == "computer"
                    and "content" in chunk
                    and (
                        chunk["type"] == "image"
                        or ("format" in chunk and chunk["format"] == "html")
                        or ("format" in chunk and chunk["format"] == "javascript")
                    )
                ):
                    if (interpreter.os == True) and (interpreter.verbose == False):
                        # We don't display things to the user in OS control mode, since we use vision to communicate the screen to the LLM so much.
                        # But if verbose is true, we do display it!
                        continue

                    assistant_code_blocks = [
                        m
                        for m in interpreter.messages
                        if m.get("role") == "assistant" and m.get("type") == "code"
                    ]
                    if assistant_code_blocks:
                        code = assistant_code_blocks[-1].get("content")
                        if any(
                            text in code
                            for text in [
                                "computer.display.view",
                                "computer.display.screenshot",
                                "computer.view",
                                "computer.screenshot",
                            ]
                        ):
                            # If the last line of the code is a computer.view command, don't display it.
                            # The LLM is going to see it, the user doesn't need to.
                            continue

                    # Display and give extra output back to the LLM
                    extra_computer_output = display_output(chunk)

                    # We're going to just add it to the messages directly, not changing `recipient` here.
                    # Mind you, the way we're doing this, this would make it appear to the user if they look at their conversation history,
                    # because we're not adding "recipient: assistant" to this block. But this is a good simple solution IMO.
                    # we just might want to change it in the future, once we're sure that a bunch of adjacent type:console blocks will be rendered normally to text-only LLMs
                    # and that if we made a new block here with "recipient: assistant" it wouldn't add new console outputs to that block (thus hiding them from the user)

                    if (
                        interpreter.messages[-1].get("format") != "output"
                        or interpreter.messages[-1]["role"] != "computer"
                        or interpreter.messages[-1]["type"] != "console"
                    ):
                        # If the last message isn't a console output, make a new block
                        interpreter.messages.append(
                            {
                                "role": "computer",
                                "type": "console",
                                "format": "output",
                                "content": extra_computer_output,
                            }
                        )
                    else:
                        # If the last message is a console output, simply append the extra output to it
                        interpreter.messages[-1]["content"] += (
                            "\n" + extra_computer_output
                        )
                        interpreter.messages[-1]["content"] = interpreter.messages[-1][
                            "content"
                        ].strip()

                # Console
                if chunk["type"] == "console":
                    render_cursor = False
                    if "format" in chunk and chunk["format"] == "output":
                        active_block.output += "\n" + chunk["content"]
                        active_block.output = (
                            active_block.output.strip()
                        )  # ^ Aesthetic choice

                        # Truncate output
                        active_block.output = truncate_output(
                            active_block.output,
                            interpreter.max_output,
                            add_scrollbars=False,
                        )  # ^ Notice that this doesn't add the "scrollbars" line, which I think is fine
                    if "format" in chunk and chunk["format"] == "active_line":
                        active_block.active_line = chunk["content"]

                        # Display action notifications if we're in OS mode
                        if interpreter.os and active_block.active_line != None:
                            action = ""

                            code_lines = active_block.code.split("\n")
                            if active_block.active_line < len(code_lines):
                                action = code_lines[active_block.active_line].strip()

                            if action.startswith("computer"):
                                description = None

                                # Extract arguments from the action
                                start_index = action.find("(")
                                end_index = action.rfind(")")
                                if start_index != -1 and end_index != -1:
                                    # (If we found both)
                                    arguments = action[start_index + 1 : end_index]
                                else:
                                    arguments = None

                                # NOTE: Do not put the text you're clicking on screen
                                # (unless we figure out how to do this AFTER taking the screenshot)
                                # otherwise it will try to click this notification!

                                if any(
                                    action.startswith(text)
                                    for text in [
                                        "computer.screenshot",
                                        "computer.display.screenshot",
                                        "computer.display.view",
                                        "computer.view",
                                    ]
                                ):
                                    description = "Viewing screen..."
                                elif action == "computer.mouse.click()":
                                    description = "Clicking..."
                                elif action.startswith("computer.mouse.click("):
                                    if "icon=" in arguments:
                                        text_or_icon = "icon"
                                    else:
                                        text_or_icon = "text"
                                    description = f"Clicking {text_or_icon}..."
                                elif action.startswith("computer.mouse.move("):
                                    if "icon=" in arguments:
                                        text_or_icon = "icon"
                                    else:
                                        text_or_icon = "text"
                                    if (
                                        "click" in active_block.code
                                    ):  # This could be better
                                        description = f"Clicking {text_or_icon}..."
                                    else:
                                        description = f"Mousing over {text_or_icon}..."
                                elif action.startswith("computer.keyboard.write("):
                                    description = f"Typing {arguments}."
                                elif action.startswith("computer.keyboard.hotkey("):
                                    description = f"Pressing {arguments}."
                                elif action.startswith("computer.keyboard.press("):
                                    description = f"Pressing {arguments}."
                                elif action == "computer.os.get_selected_text()":
                                    description = f"Getting selected text."

                                if description:
                                    interpreter.computer.os.notify(description)

                    if "start" in chunk:
                        # We need to make a code block if we pushed out an HTML block first, which would have closed our code block.
                        if not isinstance(active_block, CodeBlock):
                            if active_block:
                                active_block.end()
                            active_block = CodeBlock()

                if active_block:
                    active_block.refresh(cursor=render_cursor)

            # (Sometimes -- like if they CTRL-C quickly -- active_block is still None here)
            if "active_block" in locals():
                if active_block:
                    active_block.end()
                    active_block = None
                    time.sleep(0.1)

            if not interactive:
                # Don't loop
                break

        except KeyboardInterrupt:
            # Exit gracefully
            if "active_block" in locals() and active_block:
                active_block.end()
                active_block = None

            if interactive:
                # (this cancels LLM, returns to the interactive "> " input)
                continue
            else:
                break
        except:
            if interpreter.debug:
                system_info(interpreter)
            raise

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\urllib3\poolmanager.py ===
from __future__ import absolute_import

import collections
import functools
import logging

from ._collections import HTTPHeaderDict, RecentlyUsedContainer
from .connectionpool import HTTPConnectionPool, HTTPSConnectionPool, port_by_scheme
from .exceptions import (
    LocationValueError,
    MaxRetryError,
    ProxySchemeUnknown,
    ProxySchemeUnsupported,
    URLSchemeUnknown,
)
from .packages import six
from .packages.six.moves.urllib.parse import urljoin
from .request import RequestMethods
from .util.proxy import connection_requires_http_tunnel
from .util.retry import Retry
from .util.url import parse_url

__all__ = ["PoolManager", "ProxyManager", "proxy_from_url"]


log = logging.getLogger(__name__)

SSL_KEYWORDS = (
    "key_file",
    "cert_file",
    "cert_reqs",
    "ca_certs",
    "ssl_version",
    "ca_cert_dir",
    "ssl_context",
    "key_password",
    "server_hostname",
)

# All known keyword arguments that could be provided to the pool manager, its
# pools, or the underlying connections. This is used to construct a pool key.
_key_fields = (
    "key_scheme",  # str
    "key_host",  # str
    "key_port",  # int
    "key_timeout",  # int or float or Timeout
    "key_retries",  # int or Retry
    "key_strict",  # bool
    "key_block",  # bool
    "key_source_address",  # str
    "key_key_file",  # str
    "key_key_password",  # str
    "key_cert_file",  # str
    "key_cert_reqs",  # str
    "key_ca_certs",  # str
    "key_ssl_version",  # str
    "key_ca_cert_dir",  # str
    "key_ssl_context",  # instance of ssl.SSLContext or urllib3.util.ssl_.SSLContext
    "key_maxsize",  # int
    "key_headers",  # dict
    "key__proxy",  # parsed proxy url
    "key__proxy_headers",  # dict
    "key__proxy_config",  # class
    "key_socket_options",  # list of (level (int), optname (int), value (int or str)) tuples
    "key__socks_options",  # dict
    "key_assert_hostname",  # bool or string
    "key_assert_fingerprint",  # str
    "key_server_hostname",  # str
)

#: The namedtuple class used to construct keys for the connection pool.
#: All custom key schemes should include the fields in this key at a minimum.
PoolKey = collections.namedtuple("PoolKey", _key_fields)

_proxy_config_fields = ("ssl_context", "use_forwarding_for_https")
ProxyConfig = collections.namedtuple("ProxyConfig", _proxy_config_fields)


def _default_key_normalizer(key_class, request_context):
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

    Example::

        >>> manager = PoolManager(num_pools=2)
        >>> r = manager.request('GET', 'http://google.com/')
        >>> r = manager.request('GET', 'http://google.com/mail')
        >>> r = manager.request('GET', 'http://yahoo.com/')
        >>> len(manager.pools)
        2

    """

    proxy = None
    proxy_config = None

    def __init__(self, num_pools=10, headers=None, **connection_pool_kw):
        RequestMethods.__init__(self, headers)
        self.connection_pool_kw = connection_pool_kw
        self.pools = RecentlyUsedContainer(num_pools)

        # Locally set the pool classes and keys so other PoolManagers can
        # override them.
        self.pool_classes_by_scheme = pool_classes_by_scheme
        self.key_fn_by_scheme = key_fn_by_scheme.copy()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.clear()
        # Return False to re-raise any potential exceptions
        return False

    def _new_pool(self, scheme, host, port, request_context=None):
        """
        Create a new :class:`urllib3.connectionpool.ConnectionPool` based on host, port, scheme, and
        any additional pool keyword arguments.

        If ``request_context`` is provided, it is provided as keyword arguments
        to the pool class used. This method is used to actually create the
        connection pools handed out by :meth:`connection_from_url` and
        companion methods. It is intended to be overridden for customization.
        """
        pool_cls = self.pool_classes_by_scheme[scheme]
        if request_context is None:
            request_context = self.connection_pool_kw.copy()

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

    def clear(self):
        """
        Empty our store of pools and direct them all to close.

        This will not affect in-flight connections, but they will not be
        re-used after completion.
        """
        self.pools.clear()

    def connection_from_host(self, host, port=None, scheme="http", pool_kwargs=None):
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

    def connection_from_context(self, request_context):
        """
        Get a :class:`urllib3.connectionpool.ConnectionPool` based on the request context.

        ``request_context`` must at least contain the ``scheme`` key and its
        value must be a key in ``key_fn_by_scheme`` instance variable.
        """
        scheme = request_context["scheme"].lower()
        pool_key_constructor = self.key_fn_by_scheme.get(scheme)
        if not pool_key_constructor:
            raise URLSchemeUnknown(scheme)
        pool_key = pool_key_constructor(request_context)

        return self.connection_from_pool_key(pool_key, request_context=request_context)

    def connection_from_pool_key(self, pool_key, request_context=None):
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

    def connection_from_url(self, url, pool_kwargs=None):
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

    def _merge_pool_kwargs(self, override):
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

    def _proxy_requires_url_absolute_form(self, parsed_url):
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

    def _validate_proxy_scheme_url_selection(self, url_scheme):
        """
        Validates that were not attempting to do TLS in TLS connections on
        Python2 or with unsupported SSL implementations.
        """
        if self.proxy is None or url_scheme != "https":
            return

        if self.proxy.scheme != "https":
            return

        if six.PY2 and not self.proxy_config.use_forwarding_for_https:
            raise ProxySchemeUnsupported(
                "Contacting HTTPS destinations through HTTPS proxies "
                "'via CONNECT tunnels' is not supported in Python 2"
            )

    def urlopen(self, method, url, redirect=True, **kw):
        """
        Same as :meth:`urllib3.HTTPConnectionPool.urlopen`
        with custom cross-host redirect logic and only sends the request-uri
        portion of the ``url``.

        The given ``url`` parameter must be absolute, such that an appropriate
        :class:`urllib3.connectionpool.ConnectionPool` can be chosen for it.
        """
        u = parse_url(url)
        self._validate_proxy_scheme_url_selection(u.scheme)

        conn = self.connection_from_host(u.host, port=u.port, scheme=u.scheme)

        kw["assert_same_host"] = False
        kw["redirect"] = False

        if "headers" not in kw:
            kw["headers"] = self.headers.copy()

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
            headers = list(six.iterkeys(kw["headers"]))
            for header in headers:
                if header.lower() in retries.remove_headers_on_redirect:
                    kw["headers"].pop(header, None)

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

    Example:
        >>> proxy = urllib3.ProxyManager('http://localhost:3128/')
        >>> r1 = proxy.request('GET', 'http://google.com/')
        >>> r2 = proxy.request('GET', 'http://httpbin.org/')
        >>> len(proxy.pools)
        1
        >>> r3 = proxy.request('GET', 'https://httpbin.org/')
        >>> r4 = proxy.request('GET', 'https://twitter.com/')
        >>> len(proxy.pools)
        3

    """

    def __init__(
        self,
        proxy_url,
        num_pools=10,
        headers=None,
        proxy_headers=None,
        proxy_ssl_context=None,
        use_forwarding_for_https=False,
        **connection_pool_kw
    ):

        if isinstance(proxy_url, HTTPConnectionPool):
            proxy_url = "%s://%s:%i" % (
                proxy_url.scheme,
                proxy_url.host,
                proxy_url.port,
            )
        proxy = parse_url(proxy_url)

        if proxy.scheme not in ("http", "https"):
            raise ProxySchemeUnknown(proxy.scheme)

        if not proxy.port:
            port = port_by_scheme.get(proxy.scheme, 80)
            proxy = proxy._replace(port=port)

        self.proxy = proxy
        self.proxy_headers = proxy_headers or {}
        self.proxy_ssl_context = proxy_ssl_context
        self.proxy_config = ProxyConfig(proxy_ssl_context, use_forwarding_for_https)

        connection_pool_kw["_proxy"] = self.proxy
        connection_pool_kw["_proxy_headers"] = self.proxy_headers
        connection_pool_kw["_proxy_config"] = self.proxy_config

        super(ProxyManager, self).__init__(num_pools, headers, **connection_pool_kw)

    def connection_from_host(self, host, port=None, scheme="http", pool_kwargs=None):
        if scheme == "https":
            return super(ProxyManager, self).connection_from_host(
                host, port, scheme, pool_kwargs=pool_kwargs
            )

        return super(ProxyManager, self).connection_from_host(
            self.proxy.host, self.proxy.port, self.proxy.scheme, pool_kwargs=pool_kwargs
        )

    def _set_proxy_headers(self, url, headers=None):
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

    def urlopen(self, method, url, redirect=True, **kw):
        "Same as HTTP(S)ConnectionPool.urlopen, ``url`` must be absolute."
        u = parse_url(url)
        if not connection_requires_http_tunnel(self.proxy, self.proxy_config, u.scheme):
            # For connections using HTTP CONNECT, httplib sets the necessary
            # headers on the CONNECT to the proxy. If we're not using CONNECT,
            # we'll definitely need to set 'Host' at the very least.
            headers = kw.get("headers", self.headers)
            kw["headers"] = self._set_proxy_headers(url, headers)

        return super(ProxyManager, self).urlopen(method, url, redirect=redirect, **kw)


def proxy_from_url(url, **kw):
    return ProxyManager(proxy_url=url, **kw)

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\urllib3\poolmanager.py ===
from __future__ import absolute_import

import collections
import functools
import logging

from ._collections import HTTPHeaderDict, RecentlyUsedContainer
from .connectionpool import HTTPConnectionPool, HTTPSConnectionPool, port_by_scheme
from .exceptions import (
    LocationValueError,
    MaxRetryError,
    ProxySchemeUnknown,
    ProxySchemeUnsupported,
    URLSchemeUnknown,
)
from .packages import six
from .packages.six.moves.urllib.parse import urljoin
from .request import RequestMethods
from .util.proxy import connection_requires_http_tunnel
from .util.retry import Retry
from .util.url import parse_url

__all__ = ["PoolManager", "ProxyManager", "proxy_from_url"]


log = logging.getLogger(__name__)

SSL_KEYWORDS = (
    "key_file",
    "cert_file",
    "cert_reqs",
    "ca_certs",
    "ssl_version",
    "ca_cert_dir",
    "ssl_context",
    "key_password",
    "server_hostname",
)

# All known keyword arguments that could be provided to the pool manager, its
# pools, or the underlying connections. This is used to construct a pool key.
_key_fields = (
    "key_scheme",  # str
    "key_host",  # str
    "key_port",  # int
    "key_timeout",  # int or float or Timeout
    "key_retries",  # int or Retry
    "key_strict",  # bool
    "key_block",  # bool
    "key_source_address",  # str
    "key_key_file",  # str
    "key_key_password",  # str
    "key_cert_file",  # str
    "key_cert_reqs",  # str
    "key_ca_certs",  # str
    "key_ssl_version",  # str
    "key_ca_cert_dir",  # str
    "key_ssl_context",  # instance of ssl.SSLContext or urllib3.util.ssl_.SSLContext
    "key_maxsize",  # int
    "key_headers",  # dict
    "key__proxy",  # parsed proxy url
    "key__proxy_headers",  # dict
    "key__proxy_config",  # class
    "key_socket_options",  # list of (level (int), optname (int), value (int or str)) tuples
    "key__socks_options",  # dict
    "key_assert_hostname",  # bool or string
    "key_assert_fingerprint",  # str
    "key_server_hostname",  # str
)

#: The namedtuple class used to construct keys for the connection pool.
#: All custom key schemes should include the fields in this key at a minimum.
PoolKey = collections.namedtuple("PoolKey", _key_fields)

_proxy_config_fields = ("ssl_context", "use_forwarding_for_https")
ProxyConfig = collections.namedtuple("ProxyConfig", _proxy_config_fields)


def _default_key_normalizer(key_class, request_context):
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

    Example::

        >>> manager = PoolManager(num_pools=2)
        >>> r = manager.request('GET', 'http://google.com/')
        >>> r = manager.request('GET', 'http://google.com/mail')
        >>> r = manager.request('GET', 'http://yahoo.com/')
        >>> len(manager.pools)
        2

    """

    proxy = None
    proxy_config = None

    def __init__(self, num_pools=10, headers=None, **connection_pool_kw):
        RequestMethods.__init__(self, headers)
        self.connection_pool_kw = connection_pool_kw
        self.pools = RecentlyUsedContainer(num_pools)

        # Locally set the pool classes and keys so other PoolManagers can
        # override them.
        self.pool_classes_by_scheme = pool_classes_by_scheme
        self.key_fn_by_scheme = key_fn_by_scheme.copy()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.clear()
        # Return False to re-raise any potential exceptions
        return False

    def _new_pool(self, scheme, host, port, request_context=None):
        """
        Create a new :class:`urllib3.connectionpool.ConnectionPool` based on host, port, scheme, and
        any additional pool keyword arguments.

        If ``request_context`` is provided, it is provided as keyword arguments
        to the pool class used. This method is used to actually create the
        connection pools handed out by :meth:`connection_from_url` and
        companion methods. It is intended to be overridden for customization.
        """
        pool_cls = self.pool_classes_by_scheme[scheme]
        if request_context is None:
            request_context = self.connection_pool_kw.copy()

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

    def clear(self):
        """
        Empty our store of pools and direct them all to close.

        This will not affect in-flight connections, but they will not be
        re-used after completion.
        """
        self.pools.clear()

    def connection_from_host(self, host, port=None, scheme="http", pool_kwargs=None):
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

    def connection_from_context(self, request_context):
        """
        Get a :class:`urllib3.connectionpool.ConnectionPool` based on the request context.

        ``request_context`` must at least contain the ``scheme`` key and its
        value must be a key in ``key_fn_by_scheme`` instance variable.
        """
        scheme = request_context["scheme"].lower()
        pool_key_constructor = self.key_fn_by_scheme.get(scheme)
        if not pool_key_constructor:
            raise URLSchemeUnknown(scheme)
        pool_key = pool_key_constructor(request_context)

        return self.connection_from_pool_key(pool_key, request_context=request_context)

    def connection_from_pool_key(self, pool_key, request_context=None):
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

    def connection_from_url(self, url, pool_kwargs=None):
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

    def _merge_pool_kwargs(self, override):
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

    def _proxy_requires_url_absolute_form(self, parsed_url):
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

    def _validate_proxy_scheme_url_selection(self, url_scheme):
        """
        Validates that were not attempting to do TLS in TLS connections on
        Python2 or with unsupported SSL implementations.
        """
        if self.proxy is None or url_scheme != "https":
            return

        if self.proxy.scheme != "https":
            return

        if six.PY2 and not self.proxy_config.use_forwarding_for_https:
            raise ProxySchemeUnsupported(
                "Contacting HTTPS destinations through HTTPS proxies "
                "'via CONNECT tunnels' is not supported in Python 2"
            )

    def urlopen(self, method, url, redirect=True, **kw):
        """
        Same as :meth:`urllib3.HTTPConnectionPool.urlopen`
        with custom cross-host redirect logic and only sends the request-uri
        portion of the ``url``.

        The given ``url`` parameter must be absolute, such that an appropriate
        :class:`urllib3.connectionpool.ConnectionPool` can be chosen for it.
        """
        u = parse_url(url)
        self._validate_proxy_scheme_url_selection(u.scheme)

        conn = self.connection_from_host(u.host, port=u.port, scheme=u.scheme)

        kw["assert_same_host"] = False
        kw["redirect"] = False

        if "headers" not in kw:
            kw["headers"] = self.headers.copy()

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
            headers = list(six.iterkeys(kw["headers"]))
            for header in headers:
                if header.lower() in retries.remove_headers_on_redirect:
                    kw["headers"].pop(header, None)

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

    Example:
        >>> proxy = urllib3.ProxyManager('http://localhost:3128/')
        >>> r1 = proxy.request('GET', 'http://google.com/')
        >>> r2 = proxy.request('GET', 'http://httpbin.org/')
        >>> len(proxy.pools)
        1
        >>> r3 = proxy.request('GET', 'https://httpbin.org/')
        >>> r4 = proxy.request('GET', 'https://twitter.com/')
        >>> len(proxy.pools)
        3

    """

    def __init__(
        self,
        proxy_url,
        num_pools=10,
        headers=None,
        proxy_headers=None,
        proxy_ssl_context=None,
        use_forwarding_for_https=False,
        **connection_pool_kw
    ):

        if isinstance(proxy_url, HTTPConnectionPool):
            proxy_url = "%s://%s:%i" % (
                proxy_url.scheme,
                proxy_url.host,
                proxy_url.port,
            )
        proxy = parse_url(proxy_url)

        if proxy.scheme not in ("http", "https"):
            raise ProxySchemeUnknown(proxy.scheme)

        if not proxy.port:
            port = port_by_scheme.get(proxy.scheme, 80)
            proxy = proxy._replace(port=port)

        self.proxy = proxy
        self.proxy_headers = proxy_headers or {}
        self.proxy_ssl_context = proxy_ssl_context
        self.proxy_config = ProxyConfig(proxy_ssl_context, use_forwarding_for_https)

        connection_pool_kw["_proxy"] = self.proxy
        connection_pool_kw["_proxy_headers"] = self.proxy_headers
        connection_pool_kw["_proxy_config"] = self.proxy_config

        super(ProxyManager, self).__init__(num_pools, headers, **connection_pool_kw)

    def connection_from_host(self, host, port=None, scheme="http", pool_kwargs=None):
        if scheme == "https":
            return super(ProxyManager, self).connection_from_host(
                host, port, scheme, pool_kwargs=pool_kwargs
            )

        return super(ProxyManager, self).connection_from_host(
            self.proxy.host, self.proxy.port, self.proxy.scheme, pool_kwargs=pool_kwargs
        )

    def _set_proxy_headers(self, url, headers=None):
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

    def urlopen(self, method, url, redirect=True, **kw):
        "Same as HTTP(S)ConnectionPool.urlopen, ``url`` must be absolute."
        u = parse_url(url)
        if not connection_requires_http_tunnel(self.proxy, self.proxy_config, u.scheme):
            # For connections using HTTP CONNECT, httplib sets the necessary
            # headers on the CONNECT to the proxy. If we're not using CONNECT,
            # we'll definitely need to set 'Host' at the very least.
            headers = kw.get("headers", self.headers)
            kw["headers"] = self._set_proxy_headers(url, headers)

        return super(ProxyManager, self).urlopen(method, url, redirect=redirect, **kw)


def proxy_from_url(url, **kw):
    return ProxyManager(proxy_url=url, **kw)

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v137\bluetooth_emulation.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: BluetoothEmulation (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing

class CentralState(enum.Enum):
    '''
    Indicates the various states of Central.
    '''
    ABSENT = "absent"
    POWERED_OFF = "powered-off"
    POWERED_ON = "powered-on"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class GATTOperationType(enum.Enum):
    '''
    Indicates the various types of GATT event.
    '''
    CONNECTION = "connection"
    DISCOVERY = "discovery"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class CharacteristicWriteType(enum.Enum):
    '''
    Indicates the various types of characteristic write.
    '''
    WRITE_DEFAULT_DEPRECATED = "write-default-deprecated"
    WRITE_WITH_RESPONSE = "write-with-response"
    WRITE_WITHOUT_RESPONSE = "write-without-response"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class CharacteristicOperationType(enum.Enum):
    '''
    Indicates the various types of characteristic operation.
    '''
    READ = "read"
    WRITE = "write"
    SUBSCRIBE_TO_NOTIFICATIONS = "subscribe-to-notifications"
    UNSUBSCRIBE_FROM_NOTIFICATIONS = "unsubscribe-from-notifications"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class ManufacturerData:
    '''
    Stores the manufacturer data
    '''
    #: Company identifier
    #: https://bitbucket.org/bluetooth-SIG/public/src/main/assigned_numbers/company_identifiers/company_identifiers.yaml
    #: https://usb.org/developers
    key: int

    #: Manufacturer-specific data
    data: str

    def to_json(self):
        json = dict()
        json['key'] = self.key
        json['data'] = self.data
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            key=int(json['key']),
            data=str(json['data']),
        )


@dataclass
class ScanRecord:
    '''
    Stores the byte data of the advertisement packet sent by a Bluetooth device.
    '''
    name: typing.Optional[str] = None

    uuids: typing.Optional[typing.List[str]] = None

    #: Stores the external appearance description of the device.
    appearance: typing.Optional[int] = None

    #: Stores the transmission power of a broadcasting device.
    tx_power: typing.Optional[int] = None

    #: Key is the company identifier and the value is an array of bytes of
    #: manufacturer specific data.
    manufacturer_data: typing.Optional[typing.List[ManufacturerData]] = None

    def to_json(self):
        json = dict()
        if self.name is not None:
            json['name'] = self.name
        if self.uuids is not None:
            json['uuids'] = [i for i in self.uuids]
        if self.appearance is not None:
            json['appearance'] = self.appearance
        if self.tx_power is not None:
            json['txPower'] = self.tx_power
        if self.manufacturer_data is not None:
            json['manufacturerData'] = [i.to_json() for i in self.manufacturer_data]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']) if 'name' in json else None,
            uuids=[str(i) for i in json['uuids']] if 'uuids' in json else None,
            appearance=int(json['appearance']) if 'appearance' in json else None,
            tx_power=int(json['txPower']) if 'txPower' in json else None,
            manufacturer_data=[ManufacturerData.from_json(i) for i in json['manufacturerData']] if 'manufacturerData' in json else None,
        )


@dataclass
class ScanEntry:
    '''
    Stores the advertisement packet information that is sent by a Bluetooth device.
    '''
    device_address: str

    rssi: int

    scan_record: ScanRecord

    def to_json(self):
        json = dict()
        json['deviceAddress'] = self.device_address
        json['rssi'] = self.rssi
        json['scanRecord'] = self.scan_record.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            device_address=str(json['deviceAddress']),
            rssi=int(json['rssi']),
            scan_record=ScanRecord.from_json(json['scanRecord']),
        )


@dataclass
class CharacteristicProperties:
    '''
    Describes the properties of a characteristic. This follows Bluetooth Core
    Specification BT 4.2 Vol 3 Part G 3.3.1. Characteristic Properties.
    '''
    broadcast: typing.Optional[bool] = None

    read: typing.Optional[bool] = None

    write_without_response: typing.Optional[bool] = None

    write: typing.Optional[bool] = None

    notify: typing.Optional[bool] = None

    indicate: typing.Optional[bool] = None

    authenticated_signed_writes: typing.Optional[bool] = None

    extended_properties: typing.Optional[bool] = None

    def to_json(self):
        json = dict()
        if self.broadcast is not None:
            json['broadcast'] = self.broadcast
        if self.read is not None:
            json['read'] = self.read
        if self.write_without_response is not None:
            json['writeWithoutResponse'] = self.write_without_response
        if self.write is not None:
            json['write'] = self.write
        if self.notify is not None:
            json['notify'] = self.notify
        if self.indicate is not None:
            json['indicate'] = self.indicate
        if self.authenticated_signed_writes is not None:
            json['authenticatedSignedWrites'] = self.authenticated_signed_writes
        if self.extended_properties is not None:
            json['extendedProperties'] = self.extended_properties
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            broadcast=bool(json['broadcast']) if 'broadcast' in json else None,
            read=bool(json['read']) if 'read' in json else None,
            write_without_response=bool(json['writeWithoutResponse']) if 'writeWithoutResponse' in json else None,
            write=bool(json['write']) if 'write' in json else None,
            notify=bool(json['notify']) if 'notify' in json else None,
            indicate=bool(json['indicate']) if 'indicate' in json else None,
            authenticated_signed_writes=bool(json['authenticatedSignedWrites']) if 'authenticatedSignedWrites' in json else None,
            extended_properties=bool(json['extendedProperties']) if 'extendedProperties' in json else None,
        )


def enable(
        state: CentralState,
        le_supported: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enable the BluetoothEmulation domain.

    :param state: State of the simulated central.
    :param le_supported: If the simulated central supports low-energy.
    '''
    params: T_JSON_DICT = dict()
    params['state'] = state.to_json()
    params['leSupported'] = le_supported
    cmd_dict: T_JSON_DICT = {
        'method': 'BluetoothEmulation.enable',
        'params': params,
    }
    json = yield cmd_dict


def set_simulated_central_state(
        state: CentralState
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Set the state of the simulated central.

    :param state: State of the simulated central.
    '''
    params: T_JSON_DICT = dict()
    params['state'] = state.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'BluetoothEmulation.setSimulatedCentralState',
        'params': params,
    }
    json = yield cmd_dict


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disable the BluetoothEmulation domain.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'BluetoothEmulation.disable',
    }
    json = yield cmd_dict


def simulate_preconnected_peripheral(
        address: str,
        name: str,
        manufacturer_data: typing.List[ManufacturerData],
        known_service_uuids: typing.List[str]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Simulates a peripheral with ``address``, ``name`` and ``knownServiceUuids``
    that has already been connected to the system.

    :param address:
    :param name:
    :param manufacturer_data:
    :param known_service_uuids:
    '''
    params: T_JSON_DICT = dict()
    params['address'] = address
    params['name'] = name
    params['manufacturerData'] = [i.to_json() for i in manufacturer_data]
    params['knownServiceUuids'] = [i for i in known_service_uuids]
    cmd_dict: T_JSON_DICT = {
        'method': 'BluetoothEmulation.simulatePreconnectedPeripheral',
        'params': params,
    }
    json = yield cmd_dict


def simulate_advertisement(
        entry: ScanEntry
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Simulates an advertisement packet described in ``entry`` being received by
    the central.

    :param entry:
    '''
    params: T_JSON_DICT = dict()
    params['entry'] = entry.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'BluetoothEmulation.simulateAdvertisement',
        'params': params,
    }
    json = yield cmd_dict


def simulate_gatt_operation_response(
        address: str,
        type_: GATTOperationType,
        code: int
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Simulates the response code from the peripheral with ``address`` for a
    GATT operation of ``type``. The ``code`` value follows the HCI Error Codes from
    Bluetooth Core Specification Vol 2 Part D 1.3 List Of Error Codes.

    :param address:
    :param type_:
    :param code:
    '''
    params: T_JSON_DICT = dict()
    params['address'] = address
    params['type'] = type_.to_json()
    params['code'] = code
    cmd_dict: T_JSON_DICT = {
        'method': 'BluetoothEmulation.simulateGATTOperationResponse',
        'params': params,
    }
    json = yield cmd_dict


def simulate_characteristic_operation_response(
        characteristic_id: str,
        type_: CharacteristicOperationType,
        code: int,
        data: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Simulates the response from the characteristic with ``characteristicId`` for a
    characteristic operation of ``type``. The ``code`` value follows the Error
    Codes from Bluetooth Core Specification Vol 3 Part F 3.4.1.1 Error Response.
    The ``data`` is expected to exist when simulating a successful read operation
    response.

    :param characteristic_id:
    :param type_:
    :param code:
    :param data: *(Optional)*
    '''
    params: T_JSON_DICT = dict()
    params['characteristicId'] = characteristic_id
    params['type'] = type_.to_json()
    params['code'] = code
    if data is not None:
        params['data'] = data
    cmd_dict: T_JSON_DICT = {
        'method': 'BluetoothEmulation.simulateCharacteristicOperationResponse',
        'params': params,
    }
    json = yield cmd_dict


def add_service(
        address: str,
        service_uuid: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,str]:
    '''
    Adds a service with ``serviceUuid`` to the peripheral with ``address``.

    :param address:
    :param service_uuid:
    :returns: An identifier that uniquely represents this service.
    '''
    params: T_JSON_DICT = dict()
    params['address'] = address
    params['serviceUuid'] = service_uuid
    cmd_dict: T_JSON_DICT = {
        'method': 'BluetoothEmulation.addService',
        'params': params,
    }
    json = yield cmd_dict
    return str(json['serviceId'])


def remove_service(
        service_id: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Removes the service respresented by ``serviceId`` from the simulated central.

    :param service_id:
    '''
    params: T_JSON_DICT = dict()
    params['serviceId'] = service_id
    cmd_dict: T_JSON_DICT = {
        'method': 'BluetoothEmulation.removeService',
        'params': params,
    }
    json = yield cmd_dict


def add_characteristic(
        service_id: str,
        characteristic_uuid: str,
        properties: CharacteristicProperties
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,str]:
    '''
    Adds a characteristic with ``characteristicUuid`` and ``properties`` to the
    service represented by ``serviceId``.

    :param service_id:
    :param characteristic_uuid:
    :param properties:
    :returns: An identifier that uniquely represents this characteristic.
    '''
    params: T_JSON_DICT = dict()
    params['serviceId'] = service_id
    params['characteristicUuid'] = characteristic_uuid
    params['properties'] = properties.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'BluetoothEmulation.addCharacteristic',
        'params': params,
    }
    json = yield cmd_dict
    return str(json['characteristicId'])


def remove_characteristic(
        characteristic_id: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Removes the characteristic respresented by ``characteristicId`` from the
    simulated central.

    :param characteristic_id:
    '''
    params: T_JSON_DICT = dict()
    params['characteristicId'] = characteristic_id
    cmd_dict: T_JSON_DICT = {
        'method': 'BluetoothEmulation.removeCharacteristic',
        'params': params,
    }
    json = yield cmd_dict


def add_descriptor(
        characteristic_id: str,
        descriptor_uuid: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,str]:
    '''
    Adds a descriptor with ``descriptorUuid`` to the characteristic respresented
    by ``characteristicId``.

    :param characteristic_id:
    :param descriptor_uuid:
    :returns: An identifier that uniquely represents this descriptor.
    '''
    params: T_JSON_DICT = dict()
    params['characteristicId'] = characteristic_id
    params['descriptorUuid'] = descriptor_uuid
    cmd_dict: T_JSON_DICT = {
        'method': 'BluetoothEmulation.addDescriptor',
        'params': params,
    }
    json = yield cmd_dict
    return str(json['descriptorId'])


def remove_descriptor(
        descriptor_id: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Removes the descriptor with ``descriptorId`` from the simulated central.

    :param descriptor_id:
    '''
    params: T_JSON_DICT = dict()
    params['descriptorId'] = descriptor_id
    cmd_dict: T_JSON_DICT = {
        'method': 'BluetoothEmulation.removeDescriptor',
        'params': params,
    }
    json = yield cmd_dict


@event_class('BluetoothEmulation.gattOperationReceived')
@dataclass
class GattOperationReceived:
    '''
    Event for when a GATT operation of ``type`` to the peripheral with ``address``
    happened.
    '''
    address: str
    type_: GATTOperationType

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> GattOperationReceived:
        return cls(
            address=str(json['address']),
            type_=GATTOperationType.from_json(json['type'])
        )


@event_class('BluetoothEmulation.characteristicOperationReceived')
@dataclass
class CharacteristicOperationReceived:
    '''
    Event for when a characteristic operation of ``type`` to the characteristic
    respresented by ``characteristicId`` happened. ``data`` and ``writeType`` is
    expected to exist when ``type`` is write.
    '''
    characteristic_id: str
    type_: CharacteristicOperationType
    data: typing.Optional[str]
    write_type: typing.Optional[CharacteristicWriteType]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> CharacteristicOperationReceived:
        return cls(
            characteristic_id=str(json['characteristicId']),
            type_=CharacteristicOperationType.from_json(json['type']),
            data=str(json['data']) if 'data' in json else None,
            write_type=CharacteristicWriteType.from_json(json['writeType']) if 'writeType' in json else None
        )

# === NexusCore/openenv\Lib\site-packages\nltk\sem\relextract.py ===
# Natural Language Toolkit: Relation Extraction
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Code for extracting relational triples from the ieer and conll2002 corpora.

Relations are stored internally as dictionaries ('reldicts').

The two serialization outputs are "rtuple" and "clause".

- An rtuple is a tuple of the form ``(subj, filler, obj)``,
  where ``subj`` and ``obj`` are pairs of Named Entity mentions, and ``filler`` is the string of words
  occurring between ``sub`` and ``obj`` (with no intervening NEs). Strings are printed via ``repr()`` to
  circumvent locale variations in rendering utf-8 encoded strings.
- A clause is an atom of the form ``relsym(subjsym, objsym)``,
  where the relation, subject and object have been canonicalized to single strings.
"""

# todo: get a more general solution to canonicalized symbols for clauses -- maybe use xmlcharrefs?

import html
import re
from collections import defaultdict

# Dictionary that associates corpora with NE classes
NE_CLASSES = {
    "ieer": [
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
    "conll2002": ["LOC", "PER", "ORG"],
    "ace": [
        "LOCATION",
        "ORGANIZATION",
        "PERSON",
        "DURATION",
        "DATE",
        "CARDINAL",
        "PERCENT",
        "MONEY",
        "MEASURE",
        "FACILITY",
        "GPE",
    ],
}

# Allow abbreviated class labels
short2long = dict(LOC="LOCATION", ORG="ORGANIZATION", PER="PERSON")
long2short = dict(LOCATION="LOC", ORGANIZATION="ORG", PERSON="PER")


def _expand(type):
    """
    Expand an NE class name.
    :type type: str
    :rtype: str
    """
    try:
        return short2long[type]
    except KeyError:
        return type


def class_abbrev(type):
    """
    Abbreviate an NE class name.
    :type type: str
    :rtype: str
    """
    try:
        return long2short[type]
    except KeyError:
        return type


def _join(lst, sep=" ", untag=False):
    """
    Join a list into a string, turning tags tuples into tag strings or just words.
    :param untag: if ``True``, omit the tag from tagged input strings.
    :type lst: list
    :rtype: str
    """
    try:
        return sep.join(lst)
    except TypeError:
        if untag:
            return sep.join(tup[0] for tup in lst)
        from nltk.tag import tuple2str

        return sep.join(tuple2str(tup) for tup in lst)


def descape_entity(m, defs=html.entities.entitydefs):
    """
    Translate one entity to its ISO Latin value.
    Inspired by example from effbot.org


    """
    try:
        return defs[m.group(1)]

    except KeyError:
        return m.group(0)  # use as is


def list2sym(lst):
    """
    Convert a list of strings into a canonical symbol.
    :type lst: list
    :return: a Unicode string without whitespace
    :rtype: unicode
    """
    sym = _join(lst, "_", untag=True)
    sym = sym.lower()
    ENT = re.compile(r"&(\w+?);")
    sym = ENT.sub(descape_entity, sym)
    sym = sym.replace(".", "")
    return sym


def tree2semi_rel(tree):
    """
    Group a chunk structure into a list of 'semi-relations' of the form (list(str), ``Tree``).

    In order to facilitate the construction of (``Tree``, string, ``Tree``) triples, this
    identifies pairs whose first member is a list (possibly empty) of terminal
    strings, and whose second member is a ``Tree`` of the form (NE_label, terminals).

    :param tree: a chunk tree
    :return: a list of pairs (list(str), ``Tree``)
    :rtype: list of tuple
    """

    from nltk.tree import Tree

    semi_rels = []
    semi_rel = [[], None]

    for dtr in tree:
        if not isinstance(dtr, Tree):
            semi_rel[0].append(dtr)
        else:
            # dtr is a Tree
            semi_rel[1] = dtr
            semi_rels.append(semi_rel)
            semi_rel = [[], None]
    return semi_rels


def semi_rel2reldict(pairs, window=5, trace=False):
    """
    Converts the pairs generated by ``tree2semi_rel`` into a 'reldict': a dictionary which
    stores information about the subject and object NEs plus the filler between them.
    Additionally, a left and right context of length =< window are captured (within
    a given input sentence).

    :param pairs: a pair of list(str) and ``Tree``, as generated by
    :param window: a threshold for the number of items to include in the left and right context
    :type window: int
    :return: 'relation' dictionaries whose keys are 'lcon', 'subjclass', 'subjtext', 'subjsym', 'filler', objclass', objtext', 'objsym' and 'rcon'
    :rtype: list(defaultdict)
    """
    result = []
    while len(pairs) > 2:
        reldict = defaultdict(str)
        reldict["lcon"] = _join(pairs[0][0][-window:])
        reldict["subjclass"] = pairs[0][1].label()
        reldict["subjtext"] = _join(pairs[0][1].leaves())
        reldict["subjsym"] = list2sym(pairs[0][1].leaves())
        reldict["filler"] = _join(pairs[1][0])
        reldict["untagged_filler"] = _join(pairs[1][0], untag=True)
        reldict["objclass"] = pairs[1][1].label()
        reldict["objtext"] = _join(pairs[1][1].leaves())
        reldict["objsym"] = list2sym(pairs[1][1].leaves())
        reldict["rcon"] = _join(pairs[2][0][:window])
        if trace:
            print(
                "(%s(%s, %s)"
                % (
                    reldict["untagged_filler"],
                    reldict["subjclass"],
                    reldict["objclass"],
                )
            )
        result.append(reldict)
        pairs = pairs[1:]
    return result


def extract_rels(subjclass, objclass, doc, corpus="ace", pattern=None, window=10):
    """
    Filter the output of ``semi_rel2reldict`` according to specified NE classes and a filler pattern.

    The parameters ``subjclass`` and ``objclass`` can be used to restrict the
    Named Entities to particular types (any of 'LOCATION', 'ORGANIZATION',
    'PERSON', 'DURATION', 'DATE', 'CARDINAL', 'PERCENT', 'MONEY', 'MEASURE').

    :param subjclass: the class of the subject Named Entity.
    :type subjclass: str
    :param objclass: the class of the object Named Entity.
    :type objclass: str
    :param doc: input document
    :type doc: ieer document or a list of chunk trees
    :param corpus: name of the corpus to take as input; possible values are
        'ieer' and 'conll2002'
    :type corpus: str
    :param pattern: a regular expression for filtering the fillers of
        retrieved triples.
    :type pattern: SRE_Pattern
    :param window: filters out fillers which exceed this threshold
    :type window: int
    :return: see ``mk_reldicts``
    :rtype: list(defaultdict)
    """

    if subjclass and subjclass not in NE_CLASSES[corpus]:
        if _expand(subjclass) in NE_CLASSES[corpus]:
            subjclass = _expand(subjclass)
        else:
            raise ValueError(
                "your value for the subject type has not been recognized: %s"
                % subjclass
            )
    if objclass and objclass not in NE_CLASSES[corpus]:
        if _expand(objclass) in NE_CLASSES[corpus]:
            objclass = _expand(objclass)
        else:
            raise ValueError(
                "your value for the object type has not been recognized: %s" % objclass
            )

    if corpus == "ace" or corpus == "conll2002":
        pairs = tree2semi_rel(doc)
    elif corpus == "ieer":
        pairs = tree2semi_rel(doc.text) + tree2semi_rel(doc.headline)
    else:
        raise ValueError("corpus type not recognized")

    reldicts = semi_rel2reldict(pairs)

    relfilter = lambda x: (
        x["subjclass"] == subjclass
        and len(x["filler"].split()) <= window
        and pattern.match(x["filler"])
        and x["objclass"] == objclass
    )

    return list(filter(relfilter, reldicts))


def rtuple(reldict, lcon=False, rcon=False):
    """
    Pretty print the reldict as an rtuple.
    :param reldict: a relation dictionary
    :type reldict: defaultdict
    """
    items = [
        class_abbrev(reldict["subjclass"]),
        reldict["subjtext"],
        reldict["filler"],
        class_abbrev(reldict["objclass"]),
        reldict["objtext"],
    ]
    format = "[%s: %r] %r [%s: %r]"
    if lcon:
        items = [reldict["lcon"]] + items
        format = "...%r)" + format
    if rcon:
        items.append(reldict["rcon"])
        format = format + "(%r..."
    printargs = tuple(items)
    return format % printargs


def clause(reldict, relsym):
    """
    Print the relation in clausal form.
    :param reldict: a relation dictionary
    :type reldict: defaultdict
    :param relsym: a label for the relation
    :type relsym: str
    """
    items = (relsym, reldict["subjsym"], reldict["objsym"])
    return "%s(%r, %r)" % items


#######################################################
# Demos of relation extraction with regular expressions
#######################################################


############################################
# Example of in(ORG, LOC)
############################################
def in_demo(trace=0, sql=True):
    """
    Select pairs of organizations and locations whose mentions occur with an
    intervening occurrence of the preposition "in".

    If the sql parameter is set to True, then the entity pairs are loaded into
    an in-memory database, and subsequently pulled out using an SQL "SELECT"
    query.
    """
    from nltk.corpus import ieer

    if sql:
        try:
            import sqlite3

            connection = sqlite3.connect(":memory:")
            cur = connection.cursor()
            cur.execute(
                """create table Locations
            (OrgName text, LocationName text, DocID text)"""
            )
        except ImportError:
            import warnings

            warnings.warn("Cannot import sqlite; sql flag will be ignored.")

    IN = re.compile(r".*\bin\b(?!\b.+ing)")

    print()
    print("IEER: in(ORG, LOC) -- just the clauses:")
    print("=" * 45)

    for file in ieer.fileids():
        for doc in ieer.parsed_docs(file):
            if trace:
                print(doc.docno)
                print("=" * 15)
            for rel in extract_rels("ORG", "LOC", doc, corpus="ieer", pattern=IN):
                print(clause(rel, relsym="IN"))
                if sql:
                    try:
                        rtuple = (rel["subjtext"], rel["objtext"], doc.docno)
                        cur.execute(
                            """insert into Locations
                                    values (?, ?, ?)""",
                            rtuple,
                        )
                        connection.commit()
                    except NameError:
                        pass

    if sql:
        try:
            cur.execute(
                """select OrgName from Locations
                        where LocationName = 'Atlanta'"""
            )
            print()
            print("Extract data from SQL table: ORGs in Atlanta")
            print("-" * 15)
            for row in cur:
                print(row)
        except NameError:
            pass


############################################
# Example of has_role(PER, LOC)
############################################


def roles_demo(trace=0):
    from nltk.corpus import ieer

    roles = r"""
    (.*(                   # assorted roles
    analyst|
    chair(wo)?man|
    commissioner|
    counsel|
    director|
    economist|
    editor|
    executive|
    foreman|
    governor|
    head|
    lawyer|
    leader|
    librarian).*)|
    manager|
    partner|
    president|
    producer|
    professor|
    researcher|
    spokes(wo)?man|
    writer|
    ,\sof\sthe?\s*  # "X, of (the) Y"
    """
    ROLES = re.compile(roles, re.VERBOSE)

    print()
    print("IEER: has_role(PER, ORG) -- raw rtuples:")
    print("=" * 45)

    for file in ieer.fileids():
        for doc in ieer.parsed_docs(file):
            lcon = rcon = False
            if trace:
                print(doc.docno)
                print("=" * 15)
                lcon = rcon = True
            for rel in extract_rels("PER", "ORG", doc, corpus="ieer", pattern=ROLES):
                print(rtuple(rel, lcon=lcon, rcon=rcon))


##############################################
### Show what's in the IEER Headlines
##############################################


def ieer_headlines():
    from nltk.corpus import ieer
    from nltk.tree import Tree

    print("IEER: First 20 Headlines")
    print("=" * 45)

    trees = [
        (doc.docno, doc.headline)
        for file in ieer.fileids()
        for doc in ieer.parsed_docs(file)
    ]
    for tree in trees[:20]:
        print()
        print("%s:\n%s" % tree)


#############################################
## Dutch CONLL2002: take_on_role(PER, ORG
#############################################


def conllned(trace=1):
    """
    Find the copula+'van' relation ('of') in the Dutch tagged training corpus
    from CoNLL 2002.
    """

    from nltk.corpus import conll2002

    vnv = """
    (
    is/V|    # 3rd sing present and
    was/V|   # past forms of the verb zijn ('be')
    werd/V|  # and also present
    wordt/V  # past of worden ('become)
    )
    .*       # followed by anything
    van/Prep # followed by van ('of')
    """
    VAN = re.compile(vnv, re.VERBOSE)

    print()
    print("Dutch CoNLL2002: van(PER, ORG) -- raw rtuples with context:")
    print("=" * 45)

    for doc in conll2002.chunked_sents("ned.train"):
        lcon = rcon = False
        if trace:
            lcon = rcon = True
        for rel in extract_rels(
            "PER", "ORG", doc, corpus="conll2002", pattern=VAN, window=10
        ):
            print(rtuple(rel, lcon=lcon, rcon=rcon))


#############################################
## Spanish CONLL2002: (PER, ORG)
#############################################


def conllesp():
    from nltk.corpus import conll2002

    de = """
    .*
    (
    de/SP|
    del/SP
    )
    """
    DE = re.compile(de, re.VERBOSE)

    print()
    print("Spanish CoNLL2002: de(ORG, LOC) -- just the first 10 clauses:")
    print("=" * 45)
    rels = [
        rel
        for doc in conll2002.chunked_sents("esp.train")
        for rel in extract_rels("ORG", "LOC", doc, corpus="conll2002", pattern=DE)
    ]
    for r in rels[:10]:
        print(clause(r, relsym="DE"))
    print()


def ne_chunked():
    print()
    print("1500 Sentences from Penn Treebank, as processed by NLTK NE Chunker")
    print("=" * 45)
    ROLE = re.compile(
        r".*(chairman|president|trader|scientist|economist|analyst|partner).*"
    )
    rels = []
    for i, sent in enumerate(nltk.corpus.treebank.tagged_sents()[:1500]):
        sent = nltk.ne_chunk(sent)
        rels = extract_rels("PER", "ORG", sent, corpus="ace", pattern=ROLE, window=7)
        for rel in rels:
            print(f"{i:<5}{rtuple(rel)}")


if __name__ == "__main__":
    import nltk
    from nltk.sem import relextract

    in_demo(trace=0)
    roles_demo(trace=0)
    conllned()
    conllesp()
    ieer_headlines()
    ne_chunked()

# === NexusCore/openenv\Lib\site-packages\nltk\corpus\__init__.py ===
# Natural Language Toolkit: Corpus Readers
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

# TODO this docstring isn't up-to-date!
"""
NLTK corpus readers.  The modules in this package provide functions
that can be used to read corpus files in a variety of formats.  These
functions can be used to read both the corpus files that are
distributed in the NLTK corpus package, and corpus files that are part
of external corpora.

Available Corpora
=================

Please see https://www.nltk.org/nltk_data/ for a complete list.
Install corpora using nltk.download().

Corpus Reader Functions
=======================
Each corpus module defines one or more "corpus reader functions",
which can be used to read documents from that corpus.  These functions
take an argument, ``item``, which is used to indicate which document
should be read from the corpus:

- If ``item`` is one of the unique identifiers listed in the corpus
  module's ``items`` variable, then the corresponding document will
  be loaded from the NLTK corpus package.
- If ``item`` is a filename, then that file will be read.

Additionally, corpus reader functions can be given lists of item
names; in which case, they will return a concatenation of the
corresponding documents.

Corpus reader functions are named based on the type of information
they return.  Some common examples, and their return types, are:

- words(): list of str
- sents(): list of (list of str)
- paras(): list of (list of (list of str))
- tagged_words(): list of (str,str) tuple
- tagged_sents(): list of (list of (str,str))
- tagged_paras(): list of (list of (list of (str,str)))
- chunked_sents(): list of (Tree w/ (str,str) leaves)
- parsed_sents(): list of (Tree with str leaves)
- parsed_paras(): list of (list of (Tree with str leaves))
- xml(): A single xml ElementTree
- raw(): unprocessed corpus contents

For example, to read a list of the words in the Brown Corpus, use
``nltk.corpus.brown.words()``:

    >>> from nltk.corpus import brown
    >>> print(", ".join(brown.words())) # doctest: +ELLIPSIS
    The, Fulton, County, Grand, Jury, said, ...

"""

import re

from nltk.corpus.reader import *
from nltk.corpus.util import LazyCorpusLoader
from nltk.tokenize import RegexpTokenizer

abc: PlaintextCorpusReader = LazyCorpusLoader(
    "abc",
    PlaintextCorpusReader,
    r"(?!\.).*\.txt",
    encoding=[("science", "latin_1"), ("rural", "utf8")],
)
alpino: AlpinoCorpusReader = LazyCorpusLoader(
    "alpino", AlpinoCorpusReader, tagset="alpino"
)
bcp47: BCP47CorpusReader = LazyCorpusLoader(
    "bcp47", BCP47CorpusReader, r"(cldr|iana)/*"
)
brown: CategorizedTaggedCorpusReader = LazyCorpusLoader(
    "brown",
    CategorizedTaggedCorpusReader,
    r"c[a-z]\d\d",
    cat_file="cats.txt",
    tagset="brown",
    encoding="ascii",
)
cess_cat: BracketParseCorpusReader = LazyCorpusLoader(
    "cess_cat",
    BracketParseCorpusReader,
    r"(?!\.).*\.tbf",
    tagset="unknown",
    encoding="ISO-8859-15",
)
cess_esp: BracketParseCorpusReader = LazyCorpusLoader(
    "cess_esp",
    BracketParseCorpusReader,
    r"(?!\.).*\.tbf",
    tagset="unknown",
    encoding="ISO-8859-15",
)
cmudict: CMUDictCorpusReader = LazyCorpusLoader(
    "cmudict", CMUDictCorpusReader, ["cmudict"]
)
comtrans: AlignedCorpusReader = LazyCorpusLoader(
    "comtrans", AlignedCorpusReader, r"(?!\.).*\.txt"
)
comparative_sentences: ComparativeSentencesCorpusReader = LazyCorpusLoader(
    "comparative_sentences",
    ComparativeSentencesCorpusReader,
    r"labeledSentences\.txt",
    encoding="latin-1",
)
conll2000: ConllChunkCorpusReader = LazyCorpusLoader(
    "conll2000",
    ConllChunkCorpusReader,
    ["train.txt", "test.txt"],
    ("NP", "VP", "PP"),
    tagset="wsj",
    encoding="ascii",
)
conll2002: ConllChunkCorpusReader = LazyCorpusLoader(
    "conll2002",
    ConllChunkCorpusReader,
    r".*\.(test|train).*",
    ("LOC", "PER", "ORG", "MISC"),
    encoding="utf-8",
)
conll2007: DependencyCorpusReader = LazyCorpusLoader(
    "conll2007",
    DependencyCorpusReader,
    r".*\.(test|train).*",
    encoding=[("eus", "ISO-8859-2"), ("esp", "utf8")],
)
crubadan: CrubadanCorpusReader = LazyCorpusLoader(
    "crubadan", CrubadanCorpusReader, r".*\.txt"
)
dependency_treebank: DependencyCorpusReader = LazyCorpusLoader(
    "dependency_treebank", DependencyCorpusReader, r".*\.dp", encoding="ascii"
)
extended_omw: CorpusReader = LazyCorpusLoader(
    "extended_omw", CorpusReader, r".*/wn-[a-z\-]*\.tab", encoding="utf8"
)
floresta: BracketParseCorpusReader = LazyCorpusLoader(
    "floresta",
    BracketParseCorpusReader,
    r"(?!\.).*\.ptb",
    "#",
    tagset="unknown",
    encoding="ISO-8859-15",
)
framenet15: FramenetCorpusReader = LazyCorpusLoader(
    "framenet_v15",
    FramenetCorpusReader,
    [
        "frRelation.xml",
        "frameIndex.xml",
        "fulltextIndex.xml",
        "luIndex.xml",
        "semTypes.xml",
    ],
)
framenet: FramenetCorpusReader = LazyCorpusLoader(
    "framenet_v17",
    FramenetCorpusReader,
    [
        "frRelation.xml",
        "frameIndex.xml",
        "fulltextIndex.xml",
        "luIndex.xml",
        "semTypes.xml",
    ],
)
gazetteers: WordListCorpusReader = LazyCorpusLoader(
    "gazetteers", WordListCorpusReader, r"(?!LICENSE|\.).*\.txt", encoding="ISO-8859-2"
)
genesis: PlaintextCorpusReader = LazyCorpusLoader(
    "genesis",
    PlaintextCorpusReader,
    r"(?!\.).*\.txt",
    encoding=[
        ("finnish|french|german", "latin_1"),
        ("swedish", "cp865"),
        (".*", "utf_8"),
    ],
)
gutenberg: PlaintextCorpusReader = LazyCorpusLoader(
    "gutenberg", PlaintextCorpusReader, r"(?!\.).*\.txt", encoding="latin1"
)
ieer: IEERCorpusReader = LazyCorpusLoader("ieer", IEERCorpusReader, r"(?!README|\.).*")
inaugural: PlaintextCorpusReader = LazyCorpusLoader(
    "inaugural", PlaintextCorpusReader, r"(?!\.).*\.txt", encoding="latin1"
)
# [XX] This should probably just use TaggedCorpusReader:
indian: IndianCorpusReader = LazyCorpusLoader(
    "indian", IndianCorpusReader, r"(?!\.).*\.pos", tagset="unknown", encoding="utf8"
)

jeita: ChasenCorpusReader = LazyCorpusLoader(
    "jeita", ChasenCorpusReader, r".*\.chasen", encoding="utf-8"
)
knbc: KNBCorpusReader = LazyCorpusLoader(
    "knbc/corpus1", KNBCorpusReader, r".*/KN.*", encoding="euc-jp"
)
lin_thesaurus: LinThesaurusCorpusReader = LazyCorpusLoader(
    "lin_thesaurus", LinThesaurusCorpusReader, r".*\.lsp"
)
mac_morpho: MacMorphoCorpusReader = LazyCorpusLoader(
    "mac_morpho",
    MacMorphoCorpusReader,
    r"(?!\.).*\.txt",
    tagset="unknown",
    encoding="latin-1",
)
machado: PortugueseCategorizedPlaintextCorpusReader = LazyCorpusLoader(
    "machado",
    PortugueseCategorizedPlaintextCorpusReader,
    r"(?!\.).*\.txt",
    cat_pattern=r"([a-z]*)/.*",
    encoding="latin-1",
)
masc_tagged: CategorizedTaggedCorpusReader = LazyCorpusLoader(
    "masc_tagged",
    CategorizedTaggedCorpusReader,
    r"(spoken|written)/.*\.txt",
    cat_file="categories.txt",
    tagset="wsj",
    encoding="utf-8",
    sep="_",
)
movie_reviews: CategorizedPlaintextCorpusReader = LazyCorpusLoader(
    "movie_reviews",
    CategorizedPlaintextCorpusReader,
    r"(?!\.).*\.txt",
    cat_pattern=r"(neg|pos)/.*",
    encoding="ascii",
)
multext_east: MTECorpusReader = LazyCorpusLoader(
    "mte_teip5", MTECorpusReader, r"(oana).*\.xml", encoding="utf-8"
)
names: WordListCorpusReader = LazyCorpusLoader(
    "names", WordListCorpusReader, r"(?!\.).*\.txt", encoding="ascii"
)
nps_chat: NPSChatCorpusReader = LazyCorpusLoader(
    "nps_chat", NPSChatCorpusReader, r"(?!README|\.).*\.xml", tagset="wsj"
)
opinion_lexicon: OpinionLexiconCorpusReader = LazyCorpusLoader(
    "opinion_lexicon",
    OpinionLexiconCorpusReader,
    r"(\w+)\-words\.txt",
    encoding="ISO-8859-2",
)
ppattach: PPAttachmentCorpusReader = LazyCorpusLoader(
    "ppattach", PPAttachmentCorpusReader, ["training", "test", "devset"]
)
product_reviews_1: ReviewsCorpusReader = LazyCorpusLoader(
    "product_reviews_1", ReviewsCorpusReader, r"^(?!Readme).*\.txt", encoding="utf8"
)
product_reviews_2: ReviewsCorpusReader = LazyCorpusLoader(
    "product_reviews_2", ReviewsCorpusReader, r"^(?!Readme).*\.txt", encoding="utf8"
)
pros_cons: ProsConsCorpusReader = LazyCorpusLoader(
    "pros_cons",
    ProsConsCorpusReader,
    r"Integrated(Cons|Pros)\.txt",
    cat_pattern=r"Integrated(Cons|Pros)\.txt",
    encoding="ISO-8859-2",
)
ptb: CategorizedBracketParseCorpusReader = (
    LazyCorpusLoader(  # Penn Treebank v3: WSJ and Brown portions
        "ptb",
        CategorizedBracketParseCorpusReader,
        r"(WSJ/\d\d/WSJ_\d\d|BROWN/C[A-Z]/C[A-Z])\d\d.MRG",
        cat_file="allcats.txt",
        tagset="wsj",
    )
)
qc: StringCategoryCorpusReader = LazyCorpusLoader(
    "qc", StringCategoryCorpusReader, ["train.txt", "test.txt"], encoding="ISO-8859-2"
)
reuters: CategorizedPlaintextCorpusReader = LazyCorpusLoader(
    "reuters",
    CategorizedPlaintextCorpusReader,
    "(training|test).*",
    cat_file="cats.txt",
    encoding="ISO-8859-2",
)
rte: RTECorpusReader = LazyCorpusLoader("rte", RTECorpusReader, r"(?!\.).*\.xml")
senseval: SensevalCorpusReader = LazyCorpusLoader(
    "senseval", SensevalCorpusReader, r"(?!\.).*\.pos"
)
sentence_polarity: CategorizedSentencesCorpusReader = LazyCorpusLoader(
    "sentence_polarity",
    CategorizedSentencesCorpusReader,
    r"rt-polarity\.(neg|pos)",
    cat_pattern=r"rt-polarity\.(neg|pos)",
    encoding="utf-8",
)
sentiwordnet: SentiWordNetCorpusReader = LazyCorpusLoader(
    "sentiwordnet", SentiWordNetCorpusReader, "SentiWordNet_3.0.0.txt", encoding="utf-8"
)
shakespeare: XMLCorpusReader = LazyCorpusLoader(
    "shakespeare", XMLCorpusReader, r"(?!\.).*\.xml"
)
sinica_treebank: SinicaTreebankCorpusReader = LazyCorpusLoader(
    "sinica_treebank",
    SinicaTreebankCorpusReader,
    ["parsed"],
    tagset="unknown",
    encoding="utf-8",
)
state_union: PlaintextCorpusReader = LazyCorpusLoader(
    "state_union", PlaintextCorpusReader, r"(?!\.).*\.txt", encoding="ISO-8859-2"
)
stopwords: WordListCorpusReader = LazyCorpusLoader(
    "stopwords", WordListCorpusReader, r"(?!README|\.).*", encoding="utf8"
)
subjectivity: CategorizedSentencesCorpusReader = LazyCorpusLoader(
    "subjectivity",
    CategorizedSentencesCorpusReader,
    r"(quote.tok.gt9|plot.tok.gt9)\.5000",
    cat_map={"quote.tok.gt9.5000": ["subj"], "plot.tok.gt9.5000": ["obj"]},
    encoding="latin-1",
)
swadesh: SwadeshCorpusReader = LazyCorpusLoader(
    "swadesh", SwadeshCorpusReader, r"(?!README|\.).*", encoding="utf8"
)
swadesh110: PanlexSwadeshCorpusReader = LazyCorpusLoader(
    "panlex_swadesh", PanlexSwadeshCorpusReader, r"swadesh110/.*\.txt", encoding="utf8"
)
swadesh207: PanlexSwadeshCorpusReader = LazyCorpusLoader(
    "panlex_swadesh", PanlexSwadeshCorpusReader, r"swadesh207/.*\.txt", encoding="utf8"
)
switchboard: SwitchboardCorpusReader = LazyCorpusLoader(
    "switchboard", SwitchboardCorpusReader, tagset="wsj"
)
timit: TimitCorpusReader = LazyCorpusLoader("timit", TimitCorpusReader)
timit_tagged: TimitTaggedCorpusReader = LazyCorpusLoader(
    "timit", TimitTaggedCorpusReader, r".+\.tags", tagset="wsj", encoding="ascii"
)
toolbox: ToolboxCorpusReader = LazyCorpusLoader(
    "toolbox", ToolboxCorpusReader, r"(?!.*(README|\.)).*\.(dic|txt)"
)
treebank: BracketParseCorpusReader = LazyCorpusLoader(
    "treebank/combined",
    BracketParseCorpusReader,
    r"wsj_.*\.mrg",
    tagset="wsj",
    encoding="ascii",
)
treebank_chunk: ChunkedCorpusReader = LazyCorpusLoader(
    "treebank/tagged",
    ChunkedCorpusReader,
    r"wsj_.*\.pos",
    sent_tokenizer=RegexpTokenizer(r"(?<=/\.)\s*(?![^\[]*\])", gaps=True),
    para_block_reader=tagged_treebank_para_block_reader,
    tagset="wsj",
    encoding="ascii",
)
treebank_raw: PlaintextCorpusReader = LazyCorpusLoader(
    "treebank/raw", PlaintextCorpusReader, r"wsj_.*", encoding="ISO-8859-2"
)
twitter_samples: TwitterCorpusReader = LazyCorpusLoader(
    "twitter_samples", TwitterCorpusReader, r".*\.json"
)
udhr: UdhrCorpusReader = LazyCorpusLoader("udhr", UdhrCorpusReader)
udhr2: PlaintextCorpusReader = LazyCorpusLoader(
    "udhr2", PlaintextCorpusReader, r".*\.txt", encoding="utf8"
)
universal_treebanks: ConllCorpusReader = LazyCorpusLoader(
    "universal_treebanks_v20",
    ConllCorpusReader,
    r".*\.conll",
    columntypes=(
        "ignore",
        "words",
        "ignore",
        "ignore",
        "pos",
        "ignore",
        "ignore",
        "ignore",
        "ignore",
        "ignore",
    ),
)
verbnet: VerbnetCorpusReader = LazyCorpusLoader(
    "verbnet", VerbnetCorpusReader, r"(?!\.).*\.xml"
)
webtext: PlaintextCorpusReader = LazyCorpusLoader(
    "webtext", PlaintextCorpusReader, r"(?!README|\.).*\.txt", encoding="ISO-8859-2"
)
wordnet: WordNetCorpusReader = LazyCorpusLoader(
    "wordnet",
    WordNetCorpusReader,
    LazyCorpusLoader("omw-1.4", CorpusReader, r".*/wn-data-.*\.tab", encoding="utf8"),
)
wordnet31: WordNetCorpusReader = LazyCorpusLoader(
    "wordnet31",
    WordNetCorpusReader,
    LazyCorpusLoader("omw-1.4", CorpusReader, r".*/wn-data-.*\.tab", encoding="utf8"),
)
wordnet2021: WordNetCorpusReader = LazyCorpusLoader(
    "wordnet2021",
    WordNetCorpusReader,
    LazyCorpusLoader("omw-1.4", CorpusReader, r".*/wn-data-.*\.tab", encoding="utf8"),
)
# Latest Open English Wordnet:
wordnet2022: WordNetCorpusReader = LazyCorpusLoader(
    "wordnet2022",
    WordNetCorpusReader,
    LazyCorpusLoader("omw-1.4", CorpusReader, r".*/wn-data-.*\.tab", encoding="utf8"),
)
wordnet_ic: WordNetICCorpusReader = LazyCorpusLoader(
    "wordnet_ic", WordNetICCorpusReader, r".*\.dat"
)
words: WordListCorpusReader = LazyCorpusLoader(
    "words", WordListCorpusReader, r"(?!README|\.).*", encoding="ascii"
)

# defined after treebank
propbank: PropbankCorpusReader = LazyCorpusLoader(
    "propbank",
    PropbankCorpusReader,
    "prop.txt",
    r"frames/.*\.xml",
    "verbs.txt",
    lambda filename: re.sub(r"^wsj/\d\d/", "", filename),
    treebank,
)  # Must be defined *after* treebank corpus.
nombank: NombankCorpusReader = LazyCorpusLoader(
    "nombank.1.0",
    NombankCorpusReader,
    "nombank.1.0",
    r"frames/.*\.xml",
    "nombank.1.0.words",
    lambda filename: re.sub(r"^wsj/\d\d/", "", filename),
    treebank,
)  # Must be defined *after* treebank corpus.
propbank_ptb: PropbankCorpusReader = LazyCorpusLoader(
    "propbank",
    PropbankCorpusReader,
    "prop.txt",
    r"frames/.*\.xml",
    "verbs.txt",
    lambda filename: filename.upper(),
    ptb,
)  # Must be defined *after* ptb corpus.
nombank_ptb: NombankCorpusReader = LazyCorpusLoader(
    "nombank.1.0",
    NombankCorpusReader,
    "nombank.1.0",
    r"frames/.*\.xml",
    "nombank.1.0.words",
    lambda filename: filename.upper(),
    ptb,
)  # Must be defined *after* ptb corpus.
semcor: SemcorCorpusReader = LazyCorpusLoader(
    "semcor", SemcorCorpusReader, r"brown./tagfiles/br-.*\.xml", wordnet
)  # Must be defined *after* wordnet corpus.

nonbreaking_prefixes: NonbreakingPrefixesCorpusReader = LazyCorpusLoader(
    "nonbreaking_prefixes",
    NonbreakingPrefixesCorpusReader,
    r"(?!README|\.).*",
    encoding="utf8",
)
perluniprops: UnicharsCorpusReader = LazyCorpusLoader(
    "perluniprops",
    UnicharsCorpusReader,
    r"(?!README|\.).*",
    nltk_data_subdir="misc",
    encoding="utf8",
)

# mwa_ppdb = LazyCorpusLoader(
#     'mwa_ppdb', MWAPPDBCorpusReader, r'(?!README|\.).*', nltk_data_subdir='misc', encoding='utf8')

# See https://github.com/nltk/nltk/issues/1579
# and https://github.com/nltk/nltk/issues/1716
#
# pl196x = LazyCorpusLoader(
#     'pl196x', Pl196xCorpusReader, r'[a-z]-.*\.xml',
#     cat_file='cats.txt', textid_file='textids.txt', encoding='utf8')
#
# ipipan = LazyCorpusLoader(
#     'ipipan', IPIPANCorpusReader, r'(?!\.).*morph\.xml')
#
# nkjp = LazyCorpusLoader(
#     'nkjp', NKJPCorpusReader, r'', encoding='utf8')
#
# panlex_lite = LazyCorpusLoader(
#    'panlex_lite', PanLexLiteCorpusReader)
#
# ycoe = LazyCorpusLoader(
#     'ycoe', YCOECorpusReader)
#
# corpus not available with NLTK; these lines caused help(nltk.corpus) to break
# hebrew_treebank = LazyCorpusLoader(
#    'hebrew_treebank', BracketParseCorpusReader, r'.*\.txt')


# FIXME:  override any imported demo from various corpora, see https://github.com/nltk/nltk/issues/2116
def demo():
    # This is out-of-date:
    abc.demo()
    brown.demo()
    #    chat80.demo()
    cmudict.demo()
    conll2000.demo()
    conll2002.demo()
    genesis.demo()
    gutenberg.demo()
    ieer.demo()
    inaugural.demo()
    indian.demo()
    names.demo()
    ppattach.demo()
    senseval.demo()
    shakespeare.demo()
    sinica_treebank.demo()
    state_union.demo()
    stopwords.demo()
    timit.demo()
    toolbox.demo()
    treebank.demo()
    udhr.demo()
    webtext.demo()
    words.demo()


#    ycoe.demo()

if __name__ == "__main__":
    # demo()
    pass

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\idle\AutoIndent.py ===
import tokenize

from pywin import default_scintilla_encoding

from . import PyParse


class AutoIndent:
    menudefs = [
        (
            "edit",
            [
                None,
                ("_Indent region", "<<indent-region>>"),
                ("_Dedent region", "<<dedent-region>>"),
                ("Comment _out region", "<<comment-region>>"),
                ("U_ncomment region", "<<uncomment-region>>"),
                ("Tabify region", "<<tabify-region>>"),
                ("Untabify region", "<<untabify-region>>"),
                ("Toggle tabs", "<<toggle-tabs>>"),
                ("New indent width", "<<change-indentwidth>>"),
            ],
        ),
    ]

    keydefs = {
        "<<smart-backspace>>": ["<Key-BackSpace>"],
        "<<newline-and-indent>>": ["<Key-Return>", "<KP_Enter>"],
        "<<smart-indent>>": ["<Key-Tab>"],
    }

    windows_keydefs = {
        "<<indent-region>>": ["<Control-bracketright>"],
        "<<dedent-region>>": ["<Control-bracketleft>"],
        "<<comment-region>>": ["<Alt-Key-3>"],
        "<<uncomment-region>>": ["<Alt-Key-4>"],
        "<<tabify-region>>": ["<Alt-Key-5>"],
        "<<untabify-region>>": ["<Alt-Key-6>"],
        "<<toggle-tabs>>": ["<Alt-Key-t>"],
        "<<change-indentwidth>>": ["<Alt-Key-u>"],
    }

    unix_keydefs = {
        "<<indent-region>>": [
            "<Alt-bracketright>",
            "<Meta-bracketright>",
            "<Control-bracketright>",
        ],
        "<<dedent-region>>": [
            "<Alt-bracketleft>",
            "<Meta-bracketleft>",
            "<Control-bracketleft>",
        ],
        "<<comment-region>>": ["<Alt-Key-3>", "<Meta-Key-3>"],
        "<<uncomment-region>>": ["<Alt-Key-4>", "<Meta-Key-4>"],
        "<<tabify-region>>": ["<Alt-Key-5>", "<Meta-Key-5>"],
        "<<untabify-region>>": ["<Alt-Key-6>", "<Meta-Key-6>"],
        "<<toggle-tabs>>": ["<Alt-Key-t>"],
        "<<change-indentwidth>>": ["<Alt-Key-u>"],
    }

    # usetabs true  -> literal tab characters are used by indent and
    #                  dedent cmds, possibly mixed with spaces if
    #                  indentwidth is not a multiple of tabwidth
    #         false -> tab characters are converted to spaces by indent
    #                  and dedent cmds, and ditto TAB keystrokes
    # indentwidth is the number of characters per logical indent level.
    # tabwidth is the display width of a literal tab character.
    # CAUTION:  telling Tk to use anything other than its default
    # tab setting causes it to use an entirely different tabbing algorithm,
    # treating tab stops as fixed distances from the left margin.
    # Nobody expects this, so for now tabwidth should never be changed.
    usetabs = 1
    indentwidth = 4
    tabwidth = 8  # for IDLE use, must remain 8 until Tk is fixed

    # If context_use_ps1 is true, parsing searches back for a ps1 line;
    # else searches for a popular (if, def, ...) Python stmt.
    context_use_ps1 = 0

    # When searching backwards for a reliable place to begin parsing,
    # first start num_context_lines[0] lines back, then
    # num_context_lines[1] lines back if that didn't work, and so on.
    # The last value should be huge (larger than the # of lines in a
    # conceivable file).
    # Making the initial values larger slows things down more often.
    num_context_lines = 50, 500, 5000000

    def __init__(self, editwin):
        self.editwin = editwin
        self.text = editwin.text

    def config(self, **options):
        for key, value in options.items():
            if key == "usetabs":
                self.usetabs = value
            elif key == "indentwidth":
                self.indentwidth = value
            elif key == "tabwidth":
                self.tabwidth = value
            elif key == "context_use_ps1":
                self.context_use_ps1 = value
            else:
                raise KeyError(f"bad option name: {key!r}")

    # If ispythonsource and guess are true, guess a good value for
    # indentwidth based on file content (if possible), and if
    # indentwidth != tabwidth set usetabs false.
    # In any case, adjust the Text widget's view of what a tab
    # character means.

    def set_indentation_params(self, ispythonsource, guess=1):
        if guess and ispythonsource:
            i = self.guess_indent()
            if 2 <= i <= 8:
                self.indentwidth = i
            if self.indentwidth != self.tabwidth:
                self.usetabs = 0

        self.editwin.set_tabwidth(self.tabwidth)

    def smart_backspace_event(self, event):
        text = self.text
        first, last = self.editwin.get_selection_indices()
        if first and last:
            text.delete(first, last)
            text.mark_set("insert", first)
            return "break"
        # Delete whitespace left, until hitting a real char or closest
        # preceding virtual tab stop.
        chars = text.get("insert linestart", "insert")
        if chars == "":
            if text.compare("insert", ">", "1.0"):
                # easy: delete preceding newline
                text.delete("insert-1c")
            else:
                text.bell()  # at start of buffer
            return "break"
        if chars[-1] not in " \t":
            # easy: delete preceding real char
            text.delete("insert-1c")
            return "break"
        # Ick.  It may require *inserting* spaces if we back up over a
        # tab character!  This is written to be clear, not fast.
        have = len(chars.expandtabs(self.tabwidth))
        assert have > 0
        want = int((have - 1) / self.indentwidth) * self.indentwidth
        ncharsdeleted = 0
        while 1:
            chars = chars[:-1]
            ncharsdeleted += 1
            have = len(chars.expandtabs(self.tabwidth))
            if have <= want or chars[-1] not in " \t":
                break
        text.undo_block_start()
        text.delete("insert-%dc" % ncharsdeleted, "insert")
        if have < want:
            text.insert("insert", " " * (want - have))
        text.undo_block_stop()
        return "break"

    def smart_indent_event(self, event):
        # if intraline selection:
        #     delete it
        # elif multiline selection:
        #     do indent-region & return
        # indent one level
        text = self.text
        first, last = self.editwin.get_selection_indices()
        text.undo_block_start()
        try:
            if first and last:
                if index2line(first) != index2line(last):
                    return self.indent_region_event(event)
                text.delete(first, last)
                text.mark_set("insert", first)
            prefix = text.get("insert linestart", "insert")
            raw, effective = classifyws(prefix, self.tabwidth)
            if raw == len(prefix):
                # only whitespace to the left
                self.reindent_to(effective + self.indentwidth)
            else:
                if self.usetabs:
                    pad = "\t"
                else:
                    effective = len(prefix.expandtabs(self.tabwidth))
                    n = self.indentwidth
                    pad = " " * (n - effective % n)
                text.insert("insert", pad)
            text.see("insert")
            return "break"
        finally:
            text.undo_block_stop()

    def newline_and_indent_event(self, event):
        text = self.text
        first, last = self.editwin.get_selection_indices()
        text.undo_block_start()
        try:
            if first and last:
                text.delete(first, last)
                text.mark_set("insert", first)
            line = text.get("insert linestart", "insert")
            i, n = 0, len(line)
            while i < n and line[i] in " \t":
                i += 1
            if i == n:
                # the cursor is in or at leading indentation; just inject
                # an empty line at the start and strip space from current line
                text.delete("insert - %d chars" % i, "insert")
                text.insert("insert linestart", "\n")
                return "break"
            indent = line[:i]
            # strip whitespace before insert point
            i = 0
            while line and line[-1] in " \t":
                line = line[:-1]
                i += 1
            if i:
                text.delete("insert - %d chars" % i, "insert")
            # strip whitespace after insert point
            while text.get("insert") in " \t":
                text.delete("insert")
            # start new line
            text.insert("insert", "\n")

            # adjust indentation for continuations and block
            # open/close first need to find the last stmt
            lno = index2line(text.index("insert"))
            y = PyParse.Parser(self.indentwidth, self.tabwidth)
            for context in self.num_context_lines:
                startat = max(lno - context, 1)
                startatindex = f"{startat!r}.0"
                rawtext = text.get(startatindex, "insert")
                y.set_str(rawtext)
                bod = y.find_good_parse_start(
                    self.context_use_ps1, self._build_char_in_string_func(startatindex)
                )
                if bod is not None or startat == 1:
                    break
            y.set_lo(bod or 0)
            c = y.get_continuation_type()
            if c != PyParse.C_NONE:
                # The current stmt hasn't ended yet.
                if c == PyParse.C_STRING:
                    # inside a string; just mimic the current indent
                    text.insert("insert", indent)
                elif c == PyParse.C_BRACKET:
                    # line up with the first (if any) element of the
                    # last open bracket structure; else indent one
                    # level beyond the indent of the line with the
                    # last open bracket
                    self.reindent_to(y.compute_bracket_indent())
                elif c == PyParse.C_BACKSLASH:
                    # if more than one line in this stmt already, just
                    # mimic the current indent; else if initial line
                    # has a start on an assignment stmt, indent to
                    # beyond leftmost =; else to beyond first chunk of
                    # non-whitespace on initial line
                    if y.get_num_lines_in_stmt() > 1:
                        text.insert("insert", indent)
                    else:
                        self.reindent_to(y.compute_backslash_indent())
                else:
                    raise ValueError(f"bogus continuation type {c!r}")
                return "break"

            # This line starts a brand new stmt; indent relative to
            # indentation of initial line of closest preceding
            # interesting stmt.
            indent = y.get_base_indent_string()
            text.insert("insert", indent)
            if y.is_block_opener():
                self.smart_indent_event(event)
            elif indent and y.is_block_closer():
                self.smart_backspace_event(event)
            return "break"
        finally:
            text.see("insert")
            text.undo_block_stop()

    auto_indent = newline_and_indent_event

    # Our editwin provides a is_char_in_string function that works
    # with a Tk text index, but PyParse only knows about offsets into
    # a string. This builds a function for PyParse that accepts an
    # offset.

    def _build_char_in_string_func(self, startindex):
        def inner(offset, _startindex=startindex, _icis=self.editwin.is_char_in_string):
            return _icis(_startindex + "+%dc" % offset)

        return inner

    def indent_region_event(self, event):
        head, tail, chars, lines = self.get_region()
        for pos in range(len(lines)):
            line = lines[pos]
            if line:
                raw, effective = classifyws(line, self.tabwidth)
                effective += self.indentwidth
                lines[pos] = self._make_blanks(effective) + line[raw:]
        self.set_region(head, tail, chars, lines)
        return "break"

    def dedent_region_event(self, event):
        head, tail, chars, lines = self.get_region()
        for pos in range(len(lines)):
            line = lines[pos]
            if line:
                raw, effective = classifyws(line, self.tabwidth)
                effective = max(effective - self.indentwidth, 0)
                lines[pos] = self._make_blanks(effective) + line[raw:]
        self.set_region(head, tail, chars, lines)
        return "break"

    def comment_region_event(self, event):
        head, tail, chars, lines = self.get_region()
        for pos in range(len(lines) - 1):
            line = lines[pos]
            lines[pos] = "##" + line
        self.set_region(head, tail, chars, lines)

    def uncomment_region_event(self, event):
        head, tail, chars, lines = self.get_region()
        for pos in range(len(lines)):
            line = lines[pos]
            if not line:
                continue
            if line[:2] == "##":
                line = line[2:]
            elif line[:1] == "#":
                line = line[1:]
            lines[pos] = line
        self.set_region(head, tail, chars, lines)

    def tabify_region_event(self, event):
        head, tail, chars, lines = self.get_region()
        tabwidth = self._asktabwidth()
        for pos in range(len(lines)):
            line = lines[pos]
            if line:
                raw, effective = classifyws(line, tabwidth)
                ntabs, nspaces = divmod(effective, tabwidth)
                lines[pos] = "\t" * ntabs + " " * nspaces + line[raw:]
        self.set_region(head, tail, chars, lines)

    def untabify_region_event(self, event):
        head, tail, chars, lines = self.get_region()
        tabwidth = self._asktabwidth()
        for pos in range(len(lines)):
            lines[pos] = lines[pos].expandtabs(tabwidth)
        self.set_region(head, tail, chars, lines)

    def toggle_tabs_event(self, event):
        if self.editwin.askyesno(
            "Toggle tabs",
            "Turn tabs " + ("on", "off")[self.usetabs] + "?",
            parent=self.text,
        ):
            self.usetabs = not self.usetabs
        return "break"

    # XXX this isn't bound to anything -- see class tabwidth comments
    def change_tabwidth_event(self, event):
        new = self._asktabwidth()
        if new != self.tabwidth:
            self.tabwidth = new
            self.set_indentation_params(0, guess=0)
        return "break"

    def change_indentwidth_event(self, event):
        new = self.editwin.askinteger(
            "Indent width",
            "New indent width (1-16)",
            parent=self.text,
            initialvalue=self.indentwidth,
            minvalue=1,
            maxvalue=16,
        )
        if new and new != self.indentwidth:
            self.indentwidth = new
        return "break"

    def get_region(self):
        text = self.text
        first, last = self.editwin.get_selection_indices()
        if first and last:
            head = text.index(first + " linestart")
            tail = text.index(last + "-1c lineend +1c")
        else:
            head = text.index("insert linestart")
            tail = text.index("insert lineend +1c")
        chars = text.get(head, tail)
        lines = chars.split("\n")
        return head, tail, chars, lines

    def set_region(self, head, tail, chars, lines):
        text = self.text
        newchars = "\n".join(lines)
        if newchars == chars:
            text.bell()
            return
        text.tag_remove("sel", "1.0", "end")
        text.mark_set("insert", head)
        text.undo_block_start()
        text.delete(head, tail)
        text.insert(head, newchars)
        text.undo_block_stop()
        text.tag_add("sel", head, "insert")

    # Make string that displays as n leading blanks.

    def _make_blanks(self, n):
        if self.usetabs:
            ntabs, nspaces = divmod(n, self.tabwidth)
            return "\t" * ntabs + " " * nspaces
        else:
            return " " * n

    # Delete from beginning of line to insert point, then reinsert
    # column logical (meaning use tabs if appropriate) spaces.

    def reindent_to(self, column):
        text = self.text
        text.undo_block_start()
        if text.compare("insert linestart", "!=", "insert"):
            text.delete("insert linestart", "insert")
        if column:
            text.insert("insert", self._make_blanks(column))
        text.undo_block_stop()

    def _asktabwidth(self):
        return (
            self.editwin.askinteger(
                "Tab width",
                "Spaces per tab?",
                parent=self.text,
                initialvalue=self.tabwidth,
                minvalue=1,
                maxvalue=16,
            )
            or self.tabwidth
        )

    # Guess indentwidth from text content.
    # Return guessed indentwidth.  This should not be believed unless
    # it's in a reasonable range (e.g., it will be 0 if no indented
    # blocks are found).

    def guess_indent(self):
        opener, indented = IndentSearcher(self.text, self.tabwidth).run()
        if opener and indented:
            raw, indentsmall = classifyws(opener, self.tabwidth)
            raw, indentlarge = classifyws(indented, self.tabwidth)
        else:
            indentsmall = indentlarge = 0
        return indentlarge - indentsmall


# "line.col" -> line, as an int
def index2line(index):
    return int(float(index))


# Look at the leading whitespace in s.
# Return pair (# of leading ws characters,
#              effective # of leading blanks after expanding
#              tabs to width tabwidth)


def classifyws(s, tabwidth):
    raw = effective = 0
    for ch in s:
        if ch == " ":
            raw += 1
            effective += 1
        elif ch == "\t":
            raw += 1
            effective = (effective // tabwidth + 1) * tabwidth
        else:
            break
    return raw, effective


class IndentSearcher:
    # .run() chews over the Text widget, looking for a block opener
    # and the stmt following it.  Returns a pair,
    #     (line containing block opener, line containing stmt)
    # Either or both may be None.

    def __init__(self, text, tabwidth):
        self.text = text
        self.tabwidth = tabwidth
        self.i = self.finished = 0
        self.blkopenline = self.indentedline = None

    def readline(self):
        if self.finished:
            val = ""
        else:
            i = self.i = self.i + 1
            mark = f"{i!r}.0"
            if self.text.compare(mark, ">=", "end"):
                val = ""
            else:
                val = self.text.get(mark, mark + " lineend+1c")
        # hrm - not sure this is correct - the source code may have
        # an encoding declared, but the data will *always* be in
        # default_scintilla_encoding - so if anyone looks at the encoding decl
        # in the source they will be wrong.  I think.  Maybe.  Or something...
        return val.encode(default_scintilla_encoding)

    def run(self):
        OPENERS = ("class", "def", "for", "if", "try", "while")
        INDENT = tokenize.INDENT
        NAME = tokenize.NAME

        save_tabsize = tokenize.tabsize
        tokenize.tabsize = self.tabwidth
        try:
            try:
                for typ, token, start, end, line in tokenize.tokenize(self.readline):
                    if typ == NAME and token in OPENERS:
                        self.blkopenline = line
                    elif typ == INDENT and self.blkopenline:
                        self.indentedline = line
                        break

            except (tokenize.TokenError, IndentationError):
                # since we cut off the tokenizer early, we can trigger
                # spurious errors
                pass
        finally:
            tokenize.tabsize = save_tabsize
        return self.blkopenline, self.indentedline

# === NexusCore/openenv\Lib\site-packages\contourpy\util\mpl_renderer.py ===
from __future__ import annotations

import io
from itertools import pairwise
from typing import TYPE_CHECKING, Any, cast

import matplotlib.collections as mcollections
import matplotlib.pyplot as plt
import numpy as np

from contourpy import FillType, LineType
from contourpy.convert import convert_filled, convert_lines
from contourpy.enum_util import as_fill_type, as_line_type
from contourpy.util.mpl_util import filled_to_mpl_paths, lines_to_mpl_paths
from contourpy.util.renderer import Renderer

if TYPE_CHECKING:
    from collections.abc import Sequence

    from matplotlib.axes import Axes
    from matplotlib.figure import Figure
    from numpy.typing import ArrayLike

    import contourpy._contourpy as cpy


class MplRenderer(Renderer):
    """Utility renderer using Matplotlib to render a grid of plots over the same (x, y) range.

    Args:
        nrows (int, optional): Number of rows of plots, default ``1``.
        ncols (int, optional): Number of columns of plots, default ``1``.
        figsize (tuple(float, float), optional): Figure size in inches, default ``(9, 9)``.
        show_frame (bool, optional): Whether to show frame and axes ticks, default ``True``.
        backend (str, optional): Matplotlib backend to use or ``None`` for default backend.
            Default ``None``.
        gridspec_kw (dict, optional): Gridspec keyword arguments to pass to ``plt.subplots``,
            default None.
    """
    _axes: Sequence[Axes]
    _fig: Figure
    _want_tight: bool

    def __init__(
        self,
        nrows: int = 1,
        ncols: int = 1,
        figsize: tuple[float, float] = (9, 9),
        show_frame: bool = True,
        backend: str | None = None,
        gridspec_kw: dict[str, Any] | None = None,
    ) -> None:
        if backend is not None:
            import matplotlib as mpl
            mpl.use(backend)

        kwargs: dict[str, Any] = {"figsize": figsize, "squeeze": False,
                                  "sharex": True, "sharey": True}
        if gridspec_kw is not None:
            kwargs["gridspec_kw"] = gridspec_kw
        else:
            kwargs["subplot_kw"] = {"aspect": "equal"}

        self._fig, axes = plt.subplots(nrows, ncols, **kwargs)
        self._axes = axes.flatten()
        if not show_frame:
            for ax in self._axes:
                ax.axis("off")

        self._want_tight = True

    def __del__(self) -> None:
        if hasattr(self, "_fig"):
            plt.close(self._fig)

    def _autoscale(self) -> None:
        # Using axes._need_autoscale attribute if need to autoscale before rendering after adding
        # lines/filled.  Only want to autoscale once per axes regardless of how many lines/filled
        # added.
        for ax in self._axes:
            if getattr(ax, "_need_autoscale", False):
                ax.autoscale_view(tight=True)
                ax._need_autoscale = False  # type: ignore[attr-defined]
        if self._want_tight and len(self._axes) > 1:
            self._fig.tight_layout()

    def _get_ax(self, ax: Axes | int) -> Axes:
        if isinstance(ax, int):
            ax = self._axes[ax]
        return ax

    def filled(
        self,
        filled: cpy.FillReturn,
        fill_type: FillType | str,
        ax: Axes | int = 0,
        color: str = "C0",
        alpha: float = 0.7,
    ) -> None:
        """Plot filled contours on a single Axes.

        Args:
            filled (sequence of arrays): Filled contour data as returned by
                :meth:`~.ContourGenerator.filled`.
            fill_type (FillType or str): Type of :meth:`~.ContourGenerator.filled` data as returned
                by :attr:`~.ContourGenerator.fill_type`, or string equivalent
            ax (int or Maplotlib Axes, optional): Which axes to plot on, default ``0``.
            color (str, optional): Color to plot with. May be a string color or the letter ``"C"``
                followed by an integer in the range ``"C0"`` to ``"C9"`` to use a color from the
                ``tab10`` colormap. Default ``"C0"``.
            alpha (float, optional): Opacity to plot with, default ``0.7``.
        """
        fill_type = as_fill_type(fill_type)
        ax = self._get_ax(ax)
        paths = filled_to_mpl_paths(filled, fill_type)
        collection = mcollections.PathCollection(
            paths, facecolors=color, edgecolors="none", lw=0, alpha=alpha)
        ax.add_collection(collection)
        ax._need_autoscale = True  # type: ignore[attr-defined]

    def grid(
        self,
        x: ArrayLike,
        y: ArrayLike,
        ax: Axes | int = 0,
        color: str = "black",
        alpha: float = 0.1,
        point_color: str | None = None,
        quad_as_tri_alpha: float = 0,
    ) -> None:
        """Plot quad grid lines on a single Axes.

        Args:
            x (array-like of shape (ny, nx) or (nx,)): The x-coordinates of the grid points.
            y (array-like of shape (ny, nx) or (ny,)): The y-coordinates of the grid points.
            ax (int or Matplotlib Axes, optional): Which Axes to plot on, default ``0``.
            color (str, optional): Color to plot grid lines, default ``"black"``.
            alpha (float, optional): Opacity to plot lines with, default ``0.1``.
            point_color (str, optional): Color to plot grid points or ``None`` if grid points
                should not be plotted, default ``None``.
            quad_as_tri_alpha (float, optional): Opacity to plot ``quad_as_tri`` grid, default 0.

        Colors may be a string color or the letter ``"C"`` followed by an integer in the range
        ``"C0"`` to ``"C9"`` to use a color from the ``tab10`` colormap.

        Warning:
            ``quad_as_tri_alpha > 0`` plots all quads as though they are unmasked.
        """
        ax = self._get_ax(ax)
        x, y = self._grid_as_2d(x, y)
        kwargs: dict[str, Any] = {"color": color, "alpha": alpha}
        ax.plot(x, y, x.T, y.T, **kwargs)
        if quad_as_tri_alpha > 0:
            # Assumes no quad mask.
            xmid = 0.25*(x[:-1, :-1] + x[1:, :-1] + x[:-1, 1:] + x[1:, 1:])
            ymid = 0.25*(y[:-1, :-1] + y[1:, :-1] + y[:-1, 1:] + y[1:, 1:])
            kwargs["alpha"] = quad_as_tri_alpha
            ax.plot(
                np.stack((x[:-1, :-1], xmid, x[1:, 1:])).reshape((3, -1)),
                np.stack((y[:-1, :-1], ymid, y[1:, 1:])).reshape((3, -1)),
                np.stack((x[1:, :-1], xmid, x[:-1, 1:])).reshape((3, -1)),
                np.stack((y[1:, :-1], ymid, y[:-1, 1:])).reshape((3, -1)),
                **kwargs)
        if point_color is not None:
            ax.plot(x, y, color=point_color, alpha=alpha, marker="o", lw=0)
        ax._need_autoscale = True  # type: ignore[attr-defined]

    def lines(
        self,
        lines: cpy.LineReturn,
        line_type: LineType | str,
        ax: Axes | int = 0,
        color: str = "C0",
        alpha: float = 1.0,
        linewidth: float = 1,
    ) -> None:
        """Plot contour lines on a single Axes.

        Args:
            lines (sequence of arrays): Contour line data as returned by
                :meth:`~.ContourGenerator.lines`.
            line_type (LineType or str): Type of :meth:`~.ContourGenerator.lines` data as returned
                by :attr:`~.ContourGenerator.line_type`, or string equivalent.
            ax (int or Matplotlib Axes, optional): Which Axes to plot on, default ``0``.
            color (str, optional): Color to plot lines. May be a string color or the letter ``"C"``
                followed by an integer in the range ``"C0"`` to ``"C9"`` to use a color from the
                ``tab10`` colormap. Default ``"C0"``.
            alpha (float, optional): Opacity to plot lines with, default ``1.0``.
            linewidth (float, optional): Width of lines, default ``1``.
        """
        line_type = as_line_type(line_type)
        ax = self._get_ax(ax)
        paths = lines_to_mpl_paths(lines, line_type)
        collection = mcollections.PathCollection(
            paths, facecolors="none", edgecolors=color, lw=linewidth, alpha=alpha)
        ax.add_collection(collection)
        ax._need_autoscale = True  # type: ignore[attr-defined]

    def mask(
        self,
        x: ArrayLike,
        y: ArrayLike,
        z: ArrayLike | np.ma.MaskedArray[Any, Any],
        ax: Axes | int = 0,
        color: str = "black",
    ) -> None:
        """Plot masked out grid points as circles on a single Axes.

        Args:
            x (array-like of shape (ny, nx) or (nx,)): The x-coordinates of the grid points.
            y (array-like of shape (ny, nx) or (ny,)): The y-coordinates of the grid points.
            z (masked array of shape (ny, nx): z-values.
            ax (int or Matplotlib Axes, optional): Which Axes to plot on, default ``0``.
            color (str, optional): Circle color, default ``"black"``.
        """
        mask = np.ma.getmask(z)  # type: ignore[no-untyped-call]
        if mask is np.ma.nomask:
            return
        ax = self._get_ax(ax)
        x, y = self._grid_as_2d(x, y)
        ax.plot(x[mask], y[mask], "o", c=color)

    def save(self, filename: str, transparent: bool = False) -> None:
        """Save plots to SVG or PNG file.

        Args:
            filename (str): Filename to save to.
            transparent (bool, optional): Whether background should be transparent, default
                ``False``.
        """
        self._autoscale()
        self._fig.savefig(filename, transparent=transparent)

    def save_to_buffer(self) -> io.BytesIO:
        """Save plots to an ``io.BytesIO`` buffer.

        Return:
            BytesIO: PNG image buffer.
        """
        self._autoscale()
        buf = io.BytesIO()
        self._fig.savefig(buf, format="png")
        buf.seek(0)
        return buf

    def show(self) -> None:
        """Show plots in an interactive window, in the usual Matplotlib manner.
        """
        self._autoscale()
        plt.show()

    def title(self, title: str, ax: Axes | int = 0, color: str | None = None) -> None:
        """Set the title of a single Axes.

        Args:
            title (str): Title text.
            ax (int or Matplotlib Axes, optional): Which Axes to set the title of, default ``0``.
            color (str, optional): Color to set title. May be a string color or the letter ``"C"``
                followed by an integer in the range ``"C0"`` to ``"C9"`` to use a color from the
                ``tab10`` colormap. Default is ``None`` which uses Matplotlib's default title color
                that depends on the stylesheet in use.
        """
        if color:
            self._get_ax(ax).set_title(title, color=color)
        else:
            self._get_ax(ax).set_title(title)

    def z_values(
        self,
        x: ArrayLike,
        y: ArrayLike,
        z: ArrayLike,
        ax: Axes | int = 0,
        color: str = "green",
        fmt: str = ".1f",
        quad_as_tri: bool = False,
    ) -> None:
        """Show ``z`` values on a single Axes.

        Args:
            x (array-like of shape (ny, nx) or (nx,)): The x-coordinates of the grid points.
            y (array-like of shape (ny, nx) or (ny,)): The y-coordinates of the grid points.
            z (array-like of shape (ny, nx): z-values.
            ax (int or Matplotlib Axes, optional): Which Axes to plot on, default ``0``.
            color (str, optional): Color of added text. May be a string color or the letter ``"C"``
                followed by an integer in the range ``"C0"`` to ``"C9"`` to use a color from the
                ``tab10`` colormap. Default ``"green"``.
            fmt (str, optional): Format to display z-values, default ``".1f"``.
            quad_as_tri (bool, optional): Whether to show z-values at the ``quad_as_tri`` centers
                of quads.

        Warning:
            ``quad_as_tri=True`` shows z-values for all quads, even if masked.
        """
        ax = self._get_ax(ax)
        x, y = self._grid_as_2d(x, y)
        z = np.asarray(z)
        ny, nx = z.shape
        for j in range(ny):
            for i in range(nx):
                ax.text(x[j, i], y[j, i], f"{z[j, i]:{fmt}}", ha="center", va="center",
                        color=color, clip_on=True)
        if quad_as_tri:
            for j in range(ny-1):
                for i in range(nx-1):
                    xx = np.mean(x[j:j+2, i:i+2], dtype=np.float64)
                    yy = np.mean(y[j:j+2, i:i+2], dtype=np.float64)
                    zz = np.mean(z[j:j+2, i:i+2])
                    ax.text(xx, yy, f"{zz:{fmt}}", ha="center", va="center", color=color,
                            clip_on=True)


class MplTestRenderer(MplRenderer):
    """Test renderer implemented using Matplotlib.

    No whitespace around plots and no spines/ticks displayed.
    Uses Agg backend, so can only save to file/buffer, cannot call ``show()``.
    """
    def __init__(
        self,
        nrows: int = 1,
        ncols: int = 1,
        figsize: tuple[float, float] = (9, 9),
    ) -> None:
        gridspec = {
            "left": 0.01,
            "right": 0.99,
            "top": 0.99,
            "bottom": 0.01,
            "wspace": 0.01,
            "hspace": 0.01,
        }
        super().__init__(
            nrows, ncols, figsize, show_frame=True, backend="Agg", gridspec_kw=gridspec,
        )

        for ax in self._axes:
            ax.set_xmargin(0.0)
            ax.set_ymargin(0.0)
            ax.set_xticks([])
            ax.set_yticks([])

        self._want_tight = False


class MplDebugRenderer(MplRenderer):
    """Debug renderer implemented using Matplotlib.

    Extends ``MplRenderer`` to add extra information to help in debugging such as markers, arrows,
    text, etc.
    """
    def __init__(
        self,
        nrows: int = 1,
        ncols: int = 1,
        figsize: tuple[float, float] = (9, 9),
        show_frame: bool = True,
    ) -> None:
        super().__init__(nrows, ncols, figsize, show_frame)

    def _arrow(
        self,
        ax: Axes,
        line_start: cpy.CoordinateArray,
        line_end: cpy.CoordinateArray,
        color: str,
        alpha: float,
        arrow_size: float,
    ) -> None:
        mid = 0.5*(line_start + line_end)
        along = line_end - line_start
        along /= np.sqrt(np.dot(along, along))  # Unit vector.
        right = np.asarray((along[1], -along[0]))
        arrow = np.stack((
            mid - (along*0.5 - right)*arrow_size,
            mid + along*0.5*arrow_size,
            mid - (along*0.5 + right)*arrow_size,
        ))
        ax.plot(arrow[:, 0], arrow[:, 1], "-", c=color, alpha=alpha)

    def filled(
        self,
        filled: cpy.FillReturn,
        fill_type: FillType | str,
        ax: Axes | int = 0,
        color: str = "C1",
        alpha: float = 0.7,
        line_color: str = "C0",
        line_alpha: float = 0.7,
        point_color: str = "C0",
        start_point_color: str = "red",
        arrow_size: float = 0.1,
    ) -> None:
        fill_type = as_fill_type(fill_type)
        super().filled(filled, fill_type, ax, color, alpha)

        if line_color is None and point_color is None:
            return

        ax = self._get_ax(ax)
        filled = convert_filled(filled, fill_type, FillType.ChunkCombinedOffset)

        # Lines.
        if line_color is not None:
            for points, offsets in zip(*filled):
                if points is None:
                    continue
                for start, end in pairwise(offsets):
                    xys = points[start:end]
                    ax.plot(xys[:, 0], xys[:, 1], c=line_color, alpha=line_alpha)

                    if arrow_size > 0.0:
                        n = len(xys)
                        for i in range(n-1):
                            self._arrow(ax, xys[i], xys[i+1], line_color, line_alpha, arrow_size)

        # Points.
        if point_color is not None:
            for points, offsets in zip(*filled):
                if points is None:
                    continue
                mask = np.ones(offsets[-1], dtype=bool)
                mask[offsets[1:]-1] = False  # Exclude end points.
                if start_point_color is not None:
                    start_indices = offsets[:-1]
                    mask[start_indices] = False  # Exclude start points.
                ax.plot(
                    points[:, 0][mask], points[:, 1][mask], "o", c=point_color, alpha=line_alpha)

                if start_point_color is not None:
                    ax.plot(points[:, 0][start_indices], points[:, 1][start_indices], "o",
                            c=start_point_color, alpha=line_alpha)

    def lines(
        self,
        lines: cpy.LineReturn,
        line_type: LineType | str,
        ax: Axes | int = 0,
        color: str = "C0",
        alpha: float = 1.0,
        linewidth: float = 1,
        point_color: str = "C0",
        start_point_color: str = "red",
        arrow_size: float = 0.1,
    ) -> None:
        line_type = as_line_type(line_type)
        super().lines(lines, line_type, ax, color, alpha, linewidth)

        if arrow_size == 0.0 and point_color is None:
            return

        ax = self._get_ax(ax)
        separate_lines = convert_lines(lines, line_type, LineType.Separate)
        if TYPE_CHECKING:
            separate_lines = cast(cpy.LineReturn_Separate, separate_lines)

        if arrow_size > 0.0:
            for line in separate_lines:
                for i in range(len(line)-1):
                    self._arrow(ax, line[i], line[i+1], color, alpha, arrow_size)

        if point_color is not None:
            for line in separate_lines:
                start_index = 0
                end_index = len(line)
                if start_point_color is not None:
                    ax.plot(line[0, 0], line[0, 1], "o", c=start_point_color, alpha=alpha)
                    start_index = 1
                    if line[0][0] == line[-1][0] and line[0][1] == line[-1][1]:
                        end_index -= 1
                ax.plot(line[start_index:end_index, 0], line[start_index:end_index, 1], "o",
                        c=color, alpha=alpha)

    def point_numbers(
        self,
        x: ArrayLike,
        y: ArrayLike,
        z: ArrayLike,
        ax: Axes | int = 0,
        color: str = "red",
    ) -> None:
        ax = self._get_ax(ax)
        x, y = self._grid_as_2d(x, y)
        z = np.asarray(z)
        ny, nx = z.shape
        for j in range(ny):
            for i in range(nx):
                quad = i + j*nx
                ax.text(x[j, i], y[j, i], str(quad), ha="right", va="top", color=color,
                        clip_on=True)

    def quad_numbers(
        self,
        x: ArrayLike,
        y: ArrayLike,
        z: ArrayLike,
        ax: Axes | int = 0,
        color: str = "blue",
    ) -> None:
        ax = self._get_ax(ax)
        x, y = self._grid_as_2d(x, y)
        z = np.asarray(z)
        ny, nx = z.shape
        for j in range(1, ny):
            for i in range(1, nx):
                quad = i + j*nx
                xmid = x[j-1:j+1, i-1:i+1].mean()
                ymid = y[j-1:j+1, i-1:i+1].mean()
                ax.text(xmid, ymid, str(quad), ha="center", va="center", color=color, clip_on=True)

    def z_levels(
        self,
        x: ArrayLike,
        y: ArrayLike,
        z: ArrayLike,
        lower_level: float,
        upper_level: float | None = None,
        ax: Axes | int = 0,
        color: str = "green",
    ) -> None:
        ax = self._get_ax(ax)
        x, y = self._grid_as_2d(x, y)
        z = np.asarray(z)
        ny, nx = z.shape
        for j in range(ny):
            for i in range(nx):
                zz = z[j, i]
                if upper_level is not None and zz > upper_level:
                    z_level = 2
                elif zz > lower_level:
                    z_level = 1
                else:
                    z_level = 0
                ax.text(x[j, i], y[j, i], str(z_level), ha="left", va="bottom", color=color,
                        clip_on=True)

# === NexusCore/openenv\Lib\site-packages\tornado\test\locks_test.py ===
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

import asyncio
from datetime import timedelta
import typing  # noqa: F401
import unittest

from tornado import gen, locks
from tornado.gen import TimeoutError
from tornado.testing import gen_test, AsyncTestCase


class ConditionTest(AsyncTestCase):
    def setUp(self):
        super().setUp()
        self.history = []  # type: typing.List[typing.Union[int, str]]

    def record_done(self, future, key):
        """Record the resolution of a Future returned by Condition.wait."""

        def callback(_):
            if not future.result():
                # wait() resolved to False, meaning it timed out.
                self.history.append("timeout")
            else:
                self.history.append(key)

        future.add_done_callback(callback)

    def loop_briefly(self):
        """Run all queued callbacks on the IOLoop.

        In these tests, this method is used after calling notify() to
        preserve the pre-5.0 behavior in which callbacks ran
        synchronously.
        """
        self.io_loop.add_callback(self.stop)
        self.wait()

    def test_repr(self):
        c = locks.Condition()
        self.assertIn("Condition", repr(c))
        self.assertNotIn("waiters", repr(c))
        c.wait()
        self.assertIn("waiters", repr(c))

    @gen_test
    def test_notify(self):
        c = locks.Condition()
        self.io_loop.call_later(0.01, c.notify)
        yield c.wait()

    def test_notify_1(self):
        c = locks.Condition()
        self.record_done(c.wait(), "wait1")
        self.record_done(c.wait(), "wait2")
        c.notify(1)
        self.loop_briefly()
        self.history.append("notify1")
        c.notify(1)
        self.loop_briefly()
        self.history.append("notify2")
        self.assertEqual(["wait1", "notify1", "wait2", "notify2"], self.history)

    def test_notify_n(self):
        c = locks.Condition()
        for i in range(6):
            self.record_done(c.wait(), i)

        c.notify(3)
        self.loop_briefly()

        # Callbacks execute in the order they were registered.
        self.assertEqual(list(range(3)), self.history)
        c.notify(1)
        self.loop_briefly()
        self.assertEqual(list(range(4)), self.history)
        c.notify(2)
        self.loop_briefly()
        self.assertEqual(list(range(6)), self.history)

    def test_notify_all(self):
        c = locks.Condition()
        for i in range(4):
            self.record_done(c.wait(), i)

        c.notify_all()
        self.loop_briefly()
        self.history.append("notify_all")

        # Callbacks execute in the order they were registered.
        self.assertEqual(list(range(4)) + ["notify_all"], self.history)  # type: ignore

    @gen_test
    def test_wait_timeout(self):
        c = locks.Condition()
        wait = c.wait(timedelta(seconds=0.01))
        self.io_loop.call_later(0.02, c.notify)  # Too late.
        yield gen.sleep(0.03)
        self.assertFalse((yield wait))

    @gen_test
    def test_wait_timeout_preempted(self):
        c = locks.Condition()

        # This fires before the wait times out.
        self.io_loop.call_later(0.01, c.notify)
        wait = c.wait(timedelta(seconds=0.02))
        yield gen.sleep(0.03)
        yield wait  # No TimeoutError.

    @gen_test
    def test_notify_n_with_timeout(self):
        # Register callbacks 0, 1, 2, and 3. Callback 1 has a timeout.
        # Wait for that timeout to expire, then do notify(2) and make
        # sure everyone runs. Verifies that a timed-out callback does
        # not count against the 'n' argument to notify().
        c = locks.Condition()
        self.record_done(c.wait(), 0)
        self.record_done(c.wait(timedelta(seconds=0.01)), 1)
        self.record_done(c.wait(), 2)
        self.record_done(c.wait(), 3)

        # Wait for callback 1 to time out.
        yield gen.sleep(0.02)
        self.assertEqual(["timeout"], self.history)

        c.notify(2)
        yield gen.sleep(0.01)
        self.assertEqual(["timeout", 0, 2], self.history)
        self.assertEqual(["timeout", 0, 2], self.history)
        c.notify()
        yield
        self.assertEqual(["timeout", 0, 2, 3], self.history)

    @gen_test
    def test_notify_all_with_timeout(self):
        c = locks.Condition()
        self.record_done(c.wait(), 0)
        self.record_done(c.wait(timedelta(seconds=0.01)), 1)
        self.record_done(c.wait(), 2)

        # Wait for callback 1 to time out.
        yield gen.sleep(0.02)
        self.assertEqual(["timeout"], self.history)

        c.notify_all()
        yield
        self.assertEqual(["timeout", 0, 2], self.history)

    @gen_test
    def test_nested_notify(self):
        # Ensure no notifications lost, even if notify() is reentered by a
        # waiter calling notify().
        c = locks.Condition()

        # Three waiters.
        futures = [asyncio.ensure_future(c.wait()) for _ in range(3)]

        # First and second futures resolved. Second future reenters notify(),
        # resolving third future.
        futures[1].add_done_callback(lambda _: c.notify())
        c.notify(2)
        yield
        self.assertTrue(all(f.done() for f in futures))

    @gen_test
    def test_garbage_collection(self):
        # Test that timed-out waiters are occasionally cleaned from the queue.
        c = locks.Condition()
        for _ in range(101):
            c.wait(timedelta(seconds=0.01))

        future = asyncio.ensure_future(c.wait())
        self.assertEqual(102, len(c._waiters))

        # Let first 101 waiters time out, triggering a collection.
        yield gen.sleep(0.02)
        self.assertEqual(1, len(c._waiters))

        # Final waiter is still active.
        self.assertFalse(future.done())
        c.notify()
        self.assertTrue(future.done())


class EventTest(AsyncTestCase):
    def test_repr(self):
        event = locks.Event()
        self.assertTrue("clear" in str(event))
        self.assertFalse("set" in str(event))
        event.set()
        self.assertFalse("clear" in str(event))
        self.assertTrue("set" in str(event))

    def test_event(self):
        e = locks.Event()
        future_0 = asyncio.ensure_future(e.wait())
        e.set()
        future_1 = asyncio.ensure_future(e.wait())
        e.clear()
        future_2 = asyncio.ensure_future(e.wait())

        self.assertTrue(future_0.done())
        self.assertTrue(future_1.done())
        self.assertFalse(future_2.done())

    @gen_test
    def test_event_timeout(self):
        e = locks.Event()
        with self.assertRaises(TimeoutError):
            yield e.wait(timedelta(seconds=0.01))

        # After a timed-out waiter, normal operation works.
        self.io_loop.add_timeout(timedelta(seconds=0.01), e.set)
        yield e.wait(timedelta(seconds=1))

    def test_event_set_multiple(self):
        e = locks.Event()
        e.set()
        e.set()
        self.assertTrue(e.is_set())

    def test_event_wait_clear(self):
        e = locks.Event()
        f0 = asyncio.ensure_future(e.wait())
        e.clear()
        f1 = asyncio.ensure_future(e.wait())
        e.set()
        self.assertTrue(f0.done())
        self.assertTrue(f1.done())


class SemaphoreTest(AsyncTestCase):
    def test_negative_value(self):
        self.assertRaises(ValueError, locks.Semaphore, value=-1)

    def test_repr(self):
        sem = locks.Semaphore()
        self.assertIn("Semaphore", repr(sem))
        self.assertIn("unlocked,value:1", repr(sem))
        sem.acquire()
        self.assertIn("locked", repr(sem))
        self.assertNotIn("waiters", repr(sem))
        sem.acquire()
        self.assertIn("waiters", repr(sem))

    def test_acquire(self):
        sem = locks.Semaphore()
        f0 = asyncio.ensure_future(sem.acquire())
        self.assertTrue(f0.done())

        # Wait for release().
        f1 = asyncio.ensure_future(sem.acquire())
        self.assertFalse(f1.done())
        f2 = asyncio.ensure_future(sem.acquire())
        sem.release()
        self.assertTrue(f1.done())
        self.assertFalse(f2.done())
        sem.release()
        self.assertTrue(f2.done())

        sem.release()
        # Now acquire() is instant.
        self.assertTrue(asyncio.ensure_future(sem.acquire()).done())
        self.assertEqual(0, len(sem._waiters))

    @gen_test
    def test_acquire_timeout(self):
        sem = locks.Semaphore(2)
        yield sem.acquire()
        yield sem.acquire()
        acquire = sem.acquire(timedelta(seconds=0.01))
        self.io_loop.call_later(0.02, sem.release)  # Too late.
        yield gen.sleep(0.3)
        with self.assertRaises(gen.TimeoutError):
            yield acquire

        sem.acquire()
        f = asyncio.ensure_future(sem.acquire())
        self.assertFalse(f.done())
        sem.release()
        self.assertTrue(f.done())

    @gen_test
    def test_acquire_timeout_preempted(self):
        sem = locks.Semaphore(1)
        yield sem.acquire()

        # This fires before the wait times out.
        self.io_loop.call_later(0.01, sem.release)
        acquire = sem.acquire(timedelta(seconds=0.02))
        yield gen.sleep(0.03)
        yield acquire  # No TimeoutError.

    def test_release_unacquired(self):
        # Unbounded releases are allowed, and increment the semaphore's value.
        sem = locks.Semaphore()
        sem.release()
        sem.release()

        # Now the counter is 3. We can acquire three times before blocking.
        self.assertTrue(asyncio.ensure_future(sem.acquire()).done())
        self.assertTrue(asyncio.ensure_future(sem.acquire()).done())
        self.assertTrue(asyncio.ensure_future(sem.acquire()).done())
        self.assertFalse(asyncio.ensure_future(sem.acquire()).done())

    @gen_test
    def test_garbage_collection(self):
        # Test that timed-out waiters are occasionally cleaned from the queue.
        sem = locks.Semaphore(value=0)
        futures = [
            asyncio.ensure_future(sem.acquire(timedelta(seconds=0.01)))
            for _ in range(101)
        ]

        future = asyncio.ensure_future(sem.acquire())
        self.assertEqual(102, len(sem._waiters))

        # Let first 101 waiters time out, triggering a collection.
        yield gen.sleep(0.02)
        self.assertEqual(1, len(sem._waiters))

        # Final waiter is still active.
        self.assertFalse(future.done())
        sem.release()
        self.assertTrue(future.done())

        # Prevent "Future exception was never retrieved" messages.
        for future in futures:
            self.assertRaises(TimeoutError, future.result)


class SemaphoreContextManagerTest(AsyncTestCase):
    @gen_test
    def test_context_manager(self):
        sem = locks.Semaphore()
        with (yield sem.acquire()) as yielded:
            self.assertIsNone(yielded)

        # Semaphore was released and can be acquired again.
        self.assertTrue(asyncio.ensure_future(sem.acquire()).done())

    @gen_test
    def test_context_manager_async_await(self):
        # Repeat the above test using 'async with'.
        sem = locks.Semaphore()

        async def f():
            async with sem as yielded:
                self.assertIsNone(yielded)

        yield f()

        # Semaphore was released and can be acquired again.
        self.assertTrue(asyncio.ensure_future(sem.acquire()).done())

    @gen_test
    def test_context_manager_exception(self):
        sem = locks.Semaphore()
        with self.assertRaises(ZeroDivisionError):
            with (yield sem.acquire()):
                1 / 0

        # Semaphore was released and can be acquired again.
        self.assertTrue(asyncio.ensure_future(sem.acquire()).done())

    @gen_test
    def test_context_manager_timeout(self):
        sem = locks.Semaphore()
        with (yield sem.acquire(timedelta(seconds=0.01))):
            pass

        # Semaphore was released and can be acquired again.
        self.assertTrue(asyncio.ensure_future(sem.acquire()).done())

    @gen_test
    def test_context_manager_timeout_error(self):
        sem = locks.Semaphore(value=0)
        with self.assertRaises(gen.TimeoutError):
            with (yield sem.acquire(timedelta(seconds=0.01))):
                pass

        # Counter is still 0.
        self.assertFalse(asyncio.ensure_future(sem.acquire()).done())

    @gen_test
    def test_context_manager_contended(self):
        sem = locks.Semaphore()
        history = []

        @gen.coroutine
        def f(index):
            with (yield sem.acquire()):
                history.append("acquired %d" % index)
                yield gen.sleep(0.01)
                history.append("release %d" % index)

        yield [f(i) for i in range(2)]

        expected_history = []
        for i in range(2):
            expected_history.extend(["acquired %d" % i, "release %d" % i])

        self.assertEqual(expected_history, history)

    @gen_test
    def test_yield_sem(self):
        # Ensure we catch a "with (yield sem)", which should be
        # "with (yield sem.acquire())".
        with self.assertRaises(gen.BadYieldError):
            with (yield locks.Semaphore()):
                pass

    def test_context_manager_misuse(self):
        # Ensure we catch a "with sem", which should be
        # "with (yield sem.acquire())".
        with self.assertRaises(RuntimeError):
            with locks.Semaphore():
                pass


class BoundedSemaphoreTest(AsyncTestCase):
    def test_release_unacquired(self):
        sem = locks.BoundedSemaphore()
        self.assertRaises(ValueError, sem.release)
        # Value is 0.
        sem.acquire()
        # Block on acquire().
        future = asyncio.ensure_future(sem.acquire())
        self.assertFalse(future.done())
        sem.release()
        self.assertTrue(future.done())
        # Value is 1.
        sem.release()
        self.assertRaises(ValueError, sem.release)


class LockTests(AsyncTestCase):
    def test_repr(self):
        lock = locks.Lock()
        # No errors.
        repr(lock)
        lock.acquire()
        repr(lock)

    def test_acquire_release(self):
        lock = locks.Lock()
        self.assertTrue(asyncio.ensure_future(lock.acquire()).done())
        future = asyncio.ensure_future(lock.acquire())
        self.assertFalse(future.done())
        lock.release()
        self.assertTrue(future.done())

    @gen_test
    def test_acquire_fifo(self):
        lock = locks.Lock()
        self.assertTrue(asyncio.ensure_future(lock.acquire()).done())
        N = 5
        history = []

        @gen.coroutine
        def f(idx):
            with (yield lock.acquire()):
                history.append(idx)

        futures = [f(i) for i in range(N)]
        self.assertFalse(any(future.done() for future in futures))
        lock.release()
        yield futures
        self.assertEqual(list(range(N)), history)

    @gen_test
    def test_acquire_fifo_async_with(self):
        # Repeat the above test using `async with lock:`
        # instead of `with (yield lock.acquire()):`.
        lock = locks.Lock()
        self.assertTrue(asyncio.ensure_future(lock.acquire()).done())
        N = 5
        history = []

        async def f(idx):
            async with lock:
                history.append(idx)

        futures = [f(i) for i in range(N)]
        lock.release()
        yield futures
        self.assertEqual(list(range(N)), history)

    @gen_test
    def test_acquire_timeout(self):
        lock = locks.Lock()
        lock.acquire()
        with self.assertRaises(gen.TimeoutError):
            yield lock.acquire(timeout=timedelta(seconds=0.01))

        # Still locked.
        self.assertFalse(asyncio.ensure_future(lock.acquire()).done())

    def test_multi_release(self):
        lock = locks.Lock()
        self.assertRaises(RuntimeError, lock.release)
        lock.acquire()
        lock.release()
        self.assertRaises(RuntimeError, lock.release)

    @gen_test
    def test_yield_lock(self):
        # Ensure we catch a "with (yield lock)", which should be
        # "with (yield lock.acquire())".
        with self.assertRaises(gen.BadYieldError):
            with (yield locks.Lock()):
                pass

    def test_context_manager_misuse(self):
        # Ensure we catch a "with lock", which should be
        # "with (yield lock.acquire())".
        with self.assertRaises(RuntimeError):
            with locks.Lock():
                pass


if __name__ == "__main__":
    unittest.main()

# === NexusCore/openenv\Lib\site-packages\urllib3\util\retry.py ===
from __future__ import annotations

import email
import logging
import random
import re
import time
import typing
from itertools import takewhile
from types import TracebackType

from ..exceptions import (
    ConnectTimeoutError,
    InvalidHeader,
    MaxRetryError,
    ProtocolError,
    ProxyError,
    ReadTimeoutError,
    ResponseError,
)
from .util import reraise

if typing.TYPE_CHECKING:
    from typing_extensions import Self

    from ..connectionpool import ConnectionPool
    from ..response import BaseHTTPResponse

log = logging.getLogger(__name__)


# Data structure for representing the metadata of requests that result in a retry.
class RequestHistory(typing.NamedTuple):
    method: str | None
    url: str | None
    error: Exception | None
    status: int | None
    redirect_location: str | None


class Retry:
    """Retry configuration.

    Each retry attempt will create a new Retry object with updated values, so
    they can be safely reused.

    Retries can be defined as a default for a pool:

    .. code-block:: python

        retries = Retry(connect=5, read=2, redirect=5)
        http = PoolManager(retries=retries)
        response = http.request("GET", "https://example.com/")

    Or per-request (which overrides the default for the pool):

    .. code-block:: python

        response = http.request("GET", "https://example.com/", retries=Retry(10))

    Retries can be disabled by passing ``False``:

    .. code-block:: python

        response = http.request("GET", "https://example.com/", retries=False)

    Errors will be wrapped in :class:`~urllib3.exceptions.MaxRetryError` unless
    retries are disabled, in which case the causing exception will be raised.

    :param int total:
        Total number of retries to allow. Takes precedence over other counts.

        Set to ``None`` to remove this constraint and fall back on other
        counts.

        Set to ``0`` to fail on the first retry.

        Set to ``False`` to disable and imply ``raise_on_redirect=False``.

    :param int connect:
        How many connection-related errors to retry on.

        These are errors raised before the request is sent to the remote server,
        which we assume has not triggered the server to process the request.

        Set to ``0`` to fail on the first retry of this type.

    :param int read:
        How many times to retry on read errors.

        These errors are raised after the request was sent to the server, so the
        request may have side-effects.

        Set to ``0`` to fail on the first retry of this type.

    :param int redirect:
        How many redirects to perform. Limit this to avoid infinite redirect
        loops.

        A redirect is a HTTP response with a status code 301, 302, 303, 307 or
        308.

        Set to ``0`` to fail on the first retry of this type.

        Set to ``False`` to disable and imply ``raise_on_redirect=False``.

    :param int status:
        How many times to retry on bad status codes.

        These are retries made on responses, where status code matches
        ``status_forcelist``.

        Set to ``0`` to fail on the first retry of this type.

    :param int other:
        How many times to retry on other errors.

        Other errors are errors that are not connect, read, redirect or status errors.
        These errors might be raised after the request was sent to the server, so the
        request might have side-effects.

        Set to ``0`` to fail on the first retry of this type.

        If ``total`` is not set, it's a good idea to set this to 0 to account
        for unexpected edge cases and avoid infinite retry loops.

    :param Collection allowed_methods:
        Set of uppercased HTTP method verbs that we should retry on.

        By default, we only retry on methods which are considered to be
        idempotent (multiple requests with the same parameters end with the
        same state). See :attr:`Retry.DEFAULT_ALLOWED_METHODS`.

        Set to a ``None`` value to retry on any verb.

    :param Collection status_forcelist:
        A set of integer HTTP status codes that we should force a retry on.
        A retry is initiated if the request method is in ``allowed_methods``
        and the response status code is in ``status_forcelist``.

        By default, this is disabled with ``None``.

    :param float backoff_factor:
        A backoff factor to apply between attempts after the second try
        (most errors are resolved immediately by a second try without a
        delay). urllib3 will sleep for::

            {backoff factor} * (2 ** ({number of previous retries}))

        seconds. If `backoff_jitter` is non-zero, this sleep is extended by::

            random.uniform(0, {backoff jitter})

        seconds. For example, if the backoff_factor is 0.1, then :func:`Retry.sleep` will
        sleep for [0.0s, 0.2s, 0.4s, 0.8s, ...] between retries. No backoff will ever
        be longer than `backoff_max`.

        By default, backoff is disabled (factor set to 0).

    :param bool raise_on_redirect: Whether, if the number of redirects is
        exhausted, to raise a MaxRetryError, or to return a response with a
        response code in the 3xx range.

    :param bool raise_on_status: Similar meaning to ``raise_on_redirect``:
        whether we should raise an exception, or return a response,
        if status falls in ``status_forcelist`` range and retries have
        been exhausted.

    :param tuple history: The history of the request encountered during
        each call to :meth:`~Retry.increment`. The list is in the order
        the requests occurred. Each list item is of class :class:`RequestHistory`.

    :param bool respect_retry_after_header:
        Whether to respect Retry-After header on status codes defined as
        :attr:`Retry.RETRY_AFTER_STATUS_CODES` or not.

    :param Collection remove_headers_on_redirect:
        Sequence of headers to remove from the request when a response
        indicating a redirect is returned before firing off the redirected
        request.
    """

    #: Default methods to be used for ``allowed_methods``
    DEFAULT_ALLOWED_METHODS = frozenset(
        ["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"]
    )

    #: Default status codes to be used for ``status_forcelist``
    RETRY_AFTER_STATUS_CODES = frozenset([413, 429, 503])

    #: Default headers to be used for ``remove_headers_on_redirect``
    DEFAULT_REMOVE_HEADERS_ON_REDIRECT = frozenset(
        ["Cookie", "Authorization", "Proxy-Authorization"]
    )

    #: Default maximum backoff time.
    DEFAULT_BACKOFF_MAX = 120

    # Backward compatibility; assigned outside of the class.
    DEFAULT: typing.ClassVar[Retry]

    def __init__(
        self,
        total: bool | int | None = 10,
        connect: int | None = None,
        read: int | None = None,
        redirect: bool | int | None = None,
        status: int | None = None,
        other: int | None = None,
        allowed_methods: typing.Collection[str] | None = DEFAULT_ALLOWED_METHODS,
        status_forcelist: typing.Collection[int] | None = None,
        backoff_factor: float = 0,
        backoff_max: float = DEFAULT_BACKOFF_MAX,
        raise_on_redirect: bool = True,
        raise_on_status: bool = True,
        history: tuple[RequestHistory, ...] | None = None,
        respect_retry_after_header: bool = True,
        remove_headers_on_redirect: typing.Collection[
            str
        ] = DEFAULT_REMOVE_HEADERS_ON_REDIRECT,
        backoff_jitter: float = 0.0,
    ) -> None:
        self.total = total
        self.connect = connect
        self.read = read
        self.status = status
        self.other = other

        if redirect is False or total is False:
            redirect = 0
            raise_on_redirect = False

        self.redirect = redirect
        self.status_forcelist = status_forcelist or set()
        self.allowed_methods = allowed_methods
        self.backoff_factor = backoff_factor
        self.backoff_max = backoff_max
        self.raise_on_redirect = raise_on_redirect
        self.raise_on_status = raise_on_status
        self.history = history or ()
        self.respect_retry_after_header = respect_retry_after_header
        self.remove_headers_on_redirect = frozenset(
            h.lower() for h in remove_headers_on_redirect
        )
        self.backoff_jitter = backoff_jitter

    def new(self, **kw: typing.Any) -> Self:
        params = dict(
            total=self.total,
            connect=self.connect,
            read=self.read,
            redirect=self.redirect,
            status=self.status,
            other=self.other,
            allowed_methods=self.allowed_methods,
            status_forcelist=self.status_forcelist,
            backoff_factor=self.backoff_factor,
            backoff_max=self.backoff_max,
            raise_on_redirect=self.raise_on_redirect,
            raise_on_status=self.raise_on_status,
            history=self.history,
            remove_headers_on_redirect=self.remove_headers_on_redirect,
            respect_retry_after_header=self.respect_retry_after_header,
            backoff_jitter=self.backoff_jitter,
        )

        params.update(kw)
        return type(self)(**params)  # type: ignore[arg-type]

    @classmethod
    def from_int(
        cls,
        retries: Retry | bool | int | None,
        redirect: bool | int | None = True,
        default: Retry | bool | int | None = None,
    ) -> Retry:
        """Backwards-compatibility for the old retries format."""
        if retries is None:
            retries = default if default is not None else cls.DEFAULT

        if isinstance(retries, Retry):
            return retries

        redirect = bool(redirect) and None
        new_retries = cls(retries, redirect=redirect)
        log.debug("Converted retries value: %r -> %r", retries, new_retries)
        return new_retries

    def get_backoff_time(self) -> float:
        """Formula for computing the current backoff

        :rtype: float
        """
        # We want to consider only the last consecutive errors sequence (Ignore redirects).
        consecutive_errors_len = len(
            list(
                takewhile(lambda x: x.redirect_location is None, reversed(self.history))
            )
        )
        if consecutive_errors_len <= 1:
            return 0

        backoff_value = self.backoff_factor * (2 ** (consecutive_errors_len - 1))
        if self.backoff_jitter != 0.0:
            backoff_value += random.random() * self.backoff_jitter
        return float(max(0, min(self.backoff_max, backoff_value)))

    def parse_retry_after(self, retry_after: str) -> float:
        seconds: float
        # Whitespace: https://tools.ietf.org/html/rfc7230#section-3.2.4
        if re.match(r"^\s*[0-9]+\s*$", retry_after):
            seconds = int(retry_after)
        else:
            retry_date_tuple = email.utils.parsedate_tz(retry_after)
            if retry_date_tuple is None:
                raise InvalidHeader(f"Invalid Retry-After header: {retry_after}")

            retry_date = email.utils.mktime_tz(retry_date_tuple)
            seconds = retry_date - time.time()

        seconds = max(seconds, 0)

        return seconds

    def get_retry_after(self, response: BaseHTTPResponse) -> float | None:
        """Get the value of Retry-After in seconds."""

        retry_after = response.headers.get("Retry-After")

        if retry_after is None:
            return None

        return self.parse_retry_after(retry_after)

    def sleep_for_retry(self, response: BaseHTTPResponse) -> bool:
        retry_after = self.get_retry_after(response)
        if retry_after:
            time.sleep(retry_after)
            return True

        return False

    def _sleep_backoff(self) -> None:
        backoff = self.get_backoff_time()
        if backoff <= 0:
            return
        time.sleep(backoff)

    def sleep(self, response: BaseHTTPResponse | None = None) -> None:
        """Sleep between retry attempts.

        This method will respect a server's ``Retry-After`` response header
        and sleep the duration of the time requested. If that is not present, it
        will use an exponential backoff. By default, the backoff factor is 0 and
        this method will return immediately.
        """

        if self.respect_retry_after_header and response:
            slept = self.sleep_for_retry(response)
            if slept:
                return

        self._sleep_backoff()

    def _is_connection_error(self, err: Exception) -> bool:
        """Errors when we're fairly sure that the server did not receive the
        request, so it should be safe to retry.
        """
        if isinstance(err, ProxyError):
            err = err.original_error
        return isinstance(err, ConnectTimeoutError)

    def _is_read_error(self, err: Exception) -> bool:
        """Errors that occur after the request has been started, so we should
        assume that the server began processing it.
        """
        return isinstance(err, (ReadTimeoutError, ProtocolError))

    def _is_method_retryable(self, method: str) -> bool:
        """Checks if a given HTTP method should be retried upon, depending if
        it is included in the allowed_methods
        """
        if self.allowed_methods and method.upper() not in self.allowed_methods:
            return False
        return True

    def is_retry(
        self, method: str, status_code: int, has_retry_after: bool = False
    ) -> bool:
        """Is this method/status code retryable? (Based on allowlists and control
        variables such as the number of total retries to allow, whether to
        respect the Retry-After header, whether this header is present, and
        whether the returned status code is on the list of status codes to
        be retried upon on the presence of the aforementioned header)
        """
        if not self._is_method_retryable(method):
            return False

        if self.status_forcelist and status_code in self.status_forcelist:
            return True

        return bool(
            self.total
            and self.respect_retry_after_header
            and has_retry_after
            and (status_code in self.RETRY_AFTER_STATUS_CODES)
        )

    def is_exhausted(self) -> bool:
        """Are we out of retries?"""
        retry_counts = [
            x
            for x in (
                self.total,
                self.connect,
                self.read,
                self.redirect,
                self.status,
                self.other,
            )
            if x
        ]
        if not retry_counts:
            return False

        return min(retry_counts) < 0

    def increment(
        self,
        method: str | None = None,
        url: str | None = None,
        response: BaseHTTPResponse | None = None,
        error: Exception | None = None,
        _pool: ConnectionPool | None = None,
        _stacktrace: TracebackType | None = None,
    ) -> Self:
        """Return a new Retry object with incremented retry counters.

        :param response: A response object, or None, if the server did not
            return a response.
        :type response: :class:`~urllib3.response.BaseHTTPResponse`
        :param Exception error: An error encountered during the request, or
            None if the response was received successfully.

        :return: A new ``Retry`` object.
        """
        if self.total is False and error:
            # Disabled, indicate to re-raise the error.
            raise reraise(type(error), error, _stacktrace)

        total = self.total
        if total is not None:
            total -= 1

        connect = self.connect
        read = self.read
        redirect = self.redirect
        status_count = self.status
        other = self.other
        cause = "unknown"
        status = None
        redirect_location = None

        if error and self._is_connection_error(error):
            # Connect retry?
            if connect is False:
                raise reraise(type(error), error, _stacktrace)
            elif connect is not None:
                connect -= 1

        elif error and self._is_read_error(error):
            # Read retry?
            if read is False or method is None or not self._is_method_retryable(method):
                raise reraise(type(error), error, _stacktrace)
            elif read is not None:
                read -= 1

        elif error:
            # Other retry?
            if other is not None:
                other -= 1

        elif response and response.get_redirect_location():
            # Redirect retry?
            if redirect is not None:
                redirect -= 1
            cause = "too many redirects"
            response_redirect_location = response.get_redirect_location()
            if response_redirect_location:
                redirect_location = response_redirect_location
            status = response.status

        else:
            # Incrementing because of a server error like a 500 in
            # status_forcelist and the given method is in the allowed_methods
            cause = ResponseError.GENERIC_ERROR
            if response and response.status:
                if status_count is not None:
                    status_count -= 1
                cause = ResponseError.SPECIFIC_ERROR.format(status_code=response.status)
                status = response.status

        history = self.history + (
            RequestHistory(method, url, error, status, redirect_location),
        )

        new_retry = self.new(
            total=total,
            connect=connect,
            read=read,
            redirect=redirect,
            status=status_count,
            other=other,
            history=history,
        )

        if new_retry.is_exhausted():
            reason = error or ResponseError(cause)
            raise MaxRetryError(_pool, url, reason) from reason  # type: ignore[arg-type]

        log.debug("Incremented Retry for (url='%s'): %r", url, new_retry)

        return new_retry

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(total={self.total}, connect={self.connect}, "
            f"read={self.read}, redirect={self.redirect}, status={self.status})"
        )


# For backwards compatibility (equivalent to pre-v1.9):
Retry.DEFAULT = Retry(3)