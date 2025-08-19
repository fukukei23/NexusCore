
# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\recfunctions.py ===
"""
Collection of utilities to manipulate structured arrays.

Most of these functions were initially implemented by John Hunter for
matplotlib.  They have been rewritten and extended for convenience.

"""
import itertools

import numpy as np
import numpy.ma as ma
import numpy.ma.mrecords as mrec
from numpy._core.overrides import array_function_dispatch
from numpy.lib._iotools import _is_string_like

__all__ = [
    'append_fields', 'apply_along_fields', 'assign_fields_by_name',
    'drop_fields', 'find_duplicates', 'flatten_descr',
    'get_fieldstructure', 'get_names', 'get_names_flat',
    'join_by', 'merge_arrays', 'rec_append_fields',
    'rec_drop_fields', 'rec_join', 'recursive_fill_fields',
    'rename_fields', 'repack_fields', 'require_fields',
    'stack_arrays', 'structured_to_unstructured', 'unstructured_to_structured',
    ]


def _recursive_fill_fields_dispatcher(input, output):
    return (input, output)


@array_function_dispatch(_recursive_fill_fields_dispatcher)
def recursive_fill_fields(input, output):
    """
    Fills fields from output with fields from input,
    with support for nested structures.

    Parameters
    ----------
    input : ndarray
        Input array.
    output : ndarray
        Output array.

    Notes
    -----
    * `output` should be at least the same size as `input`

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.lib import recfunctions as rfn
    >>> a = np.array([(1, 10.), (2, 20.)], dtype=[('A', np.int64), ('B', np.float64)])
    >>> b = np.zeros((3,), dtype=a.dtype)
    >>> rfn.recursive_fill_fields(a, b)
    array([(1, 10.), (2, 20.), (0,  0.)], dtype=[('A', '<i8'), ('B', '<f8')])

    """
    newdtype = output.dtype
    for field in newdtype.names:
        try:
            current = input[field]
        except ValueError:
            continue
        if current.dtype.names is not None:
            recursive_fill_fields(current, output[field])
        else:
            output[field][:len(current)] = current
    return output


def _get_fieldspec(dtype):
    """
    Produce a list of name/dtype pairs corresponding to the dtype fields

    Similar to dtype.descr, but the second item of each tuple is a dtype, not a
    string. As a result, this handles subarray dtypes

    Can be passed to the dtype constructor to reconstruct the dtype, noting that
    this (deliberately) discards field offsets.

    Examples
    --------
    >>> import numpy as np
    >>> dt = np.dtype([(('a', 'A'), np.int64), ('b', np.double, 3)])
    >>> dt.descr
    [(('a', 'A'), '<i8'), ('b', '<f8', (3,))]
    >>> _get_fieldspec(dt)
    [(('a', 'A'), dtype('int64')), ('b', dtype(('<f8', (3,))))]

    """
    if dtype.names is None:
        # .descr returns a nameless field, so we should too
        return [('', dtype)]
    else:
        fields = ((name, dtype.fields[name]) for name in dtype.names)
        # keep any titles, if present
        return [
            (name if len(f) == 2 else (f[2], name), f[0])
            for name, f in fields
        ]


def get_names(adtype):
    """
    Returns the field names of the input datatype as a tuple. Input datatype
    must have fields otherwise error is raised.

    Parameters
    ----------
    adtype : dtype
        Input datatype

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.lib import recfunctions as rfn
    >>> rfn.get_names(np.empty((1,), dtype=[('A', int)]).dtype)
    ('A',)
    >>> rfn.get_names(np.empty((1,), dtype=[('A',int), ('B', float)]).dtype)
    ('A', 'B')
    >>> adtype = np.dtype([('a', int), ('b', [('ba', int), ('bb', int)])])
    >>> rfn.get_names(adtype)
    ('a', ('b', ('ba', 'bb')))
    """
    listnames = []
    names = adtype.names
    for name in names:
        current = adtype[name]
        if current.names is not None:
            listnames.append((name, tuple(get_names(current))))
        else:
            listnames.append(name)
    return tuple(listnames)


def get_names_flat(adtype):
    """
    Returns the field names of the input datatype as a tuple. Input datatype
    must have fields otherwise error is raised.
    Nested structure are flattened beforehand.

    Parameters
    ----------
    adtype : dtype
        Input datatype

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.lib import recfunctions as rfn
    >>> rfn.get_names_flat(np.empty((1,), dtype=[('A', int)]).dtype) is None
    False
    >>> rfn.get_names_flat(np.empty((1,), dtype=[('A',int), ('B', str)]).dtype)
    ('A', 'B')
    >>> adtype = np.dtype([('a', int), ('b', [('ba', int), ('bb', int)])])
    >>> rfn.get_names_flat(adtype)
    ('a', 'b', 'ba', 'bb')
    """
    listnames = []
    names = adtype.names
    for name in names:
        listnames.append(name)
        current = adtype[name]
        if current.names is not None:
            listnames.extend(get_names_flat(current))
    return tuple(listnames)


def flatten_descr(ndtype):
    """
    Flatten a structured data-type description.

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.lib import recfunctions as rfn
    >>> ndtype = np.dtype([('a', '<i4'), ('b', [('ba', '<f8'), ('bb', '<i4')])])
    >>> rfn.flatten_descr(ndtype)
    (('a', dtype('int32')), ('ba', dtype('float64')), ('bb', dtype('int32')))

    """
    names = ndtype.names
    if names is None:
        return (('', ndtype),)
    else:
        descr = []
        for field in names:
            (typ, _) = ndtype.fields[field]
            if typ.names is not None:
                descr.extend(flatten_descr(typ))
            else:
                descr.append((field, typ))
        return tuple(descr)


def _zip_dtype(seqarrays, flatten=False):
    newdtype = []
    if flatten:
        for a in seqarrays:
            newdtype.extend(flatten_descr(a.dtype))
    else:
        for a in seqarrays:
            current = a.dtype
            if current.names is not None and len(current.names) == 1:
                # special case - dtypes of 1 field are flattened
                newdtype.extend(_get_fieldspec(current))
            else:
                newdtype.append(('', current))
    return np.dtype(newdtype)


def _zip_descr(seqarrays, flatten=False):
    """
    Combine the dtype description of a series of arrays.

    Parameters
    ----------
    seqarrays : sequence of arrays
        Sequence of arrays
    flatten : {boolean}, optional
        Whether to collapse nested descriptions.
    """
    return _zip_dtype(seqarrays, flatten=flatten).descr


def get_fieldstructure(adtype, lastname=None, parents=None,):
    """
    Returns a dictionary with fields indexing lists of their parent fields.

    This function is used to simplify access to fields nested in other fields.

    Parameters
    ----------
    adtype : np.dtype
        Input datatype
    lastname : optional
        Last processed field name (used internally during recursion).
    parents : dictionary
        Dictionary of parent fields (used internally during recursion).

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.lib import recfunctions as rfn
    >>> ndtype =  np.dtype([('A', int),
    ...                     ('B', [('BA', int),
    ...                            ('BB', [('BBA', int), ('BBB', int)])])])
    >>> rfn.get_fieldstructure(ndtype)
    ... # XXX: possible regression, order of BBA and BBB is swapped
    {'A': [], 'B': [], 'BA': ['B'], 'BB': ['B'], 'BBA': ['B', 'BB'], 'BBB': ['B', 'BB']}

    """
    if parents is None:
        parents = {}
    names = adtype.names
    for name in names:
        current = adtype[name]
        if current.names is not None:
            if lastname:
                parents[name] = [lastname, ]
            else:
                parents[name] = []
            parents.update(get_fieldstructure(current, name, parents))
        else:
            lastparent = list(parents.get(lastname, []) or [])
            if lastparent:
                lastparent.append(lastname)
            elif lastname:
                lastparent = [lastname, ]
            parents[name] = lastparent or []
    return parents


def _izip_fields_flat(iterable):
    """
    Returns an iterator of concatenated fields from a sequence of arrays,
    collapsing any nested structure.

    """
    for element in iterable:
        if isinstance(element, np.void):
            yield from _izip_fields_flat(tuple(element))
        else:
            yield element


def _izip_fields(iterable):
    """
    Returns an iterator of concatenated fields from a sequence of arrays.

    """
    for element in iterable:
        if (hasattr(element, '__iter__') and
                not isinstance(element, str)):
            yield from _izip_fields(element)
        elif isinstance(element, np.void) and len(tuple(element)) == 1:
            # this statement is the same from the previous expression
            yield from _izip_fields(element)
        else:
            yield element


def _izip_records(seqarrays, fill_value=None, flatten=True):
    """
    Returns an iterator of concatenated items from a sequence of arrays.

    Parameters
    ----------
    seqarrays : sequence of arrays
        Sequence of arrays.
    fill_value : {None, integer}
        Value used to pad shorter iterables.
    flatten : {True, False},
        Whether to
    """

    # Should we flatten the items, or just use a nested approach
    if flatten:
        zipfunc = _izip_fields_flat
    else:
        zipfunc = _izip_fields

    for tup in itertools.zip_longest(*seqarrays, fillvalue=fill_value):
        yield tuple(zipfunc(tup))


def _fix_output(output, usemask=True, asrecarray=False):
    """
    Private function: return a recarray, a ndarray, a MaskedArray
    or a MaskedRecords depending on the input parameters
    """
    if not isinstance(output, ma.MaskedArray):
        usemask = False
    if usemask:
        if asrecarray:
            output = output.view(mrec.MaskedRecords)
    else:
        output = ma.filled(output)
        if asrecarray:
            output = output.view(np.recarray)
    return output


def _fix_defaults(output, defaults=None):
    """
    Update the fill_value and masked data of `output`
    from the default given in a dictionary defaults.
    """
    names = output.dtype.names
    (data, mask, fill_value) = (output.data, output.mask, output.fill_value)
    for (k, v) in (defaults or {}).items():
        if k in names:
            fill_value[k] = v
            data[k][mask[k]] = v
    return output


def _merge_arrays_dispatcher(seqarrays, fill_value=None, flatten=None,
                             usemask=None, asrecarray=None):
    return seqarrays


@array_function_dispatch(_merge_arrays_dispatcher)
def merge_arrays(seqarrays, fill_value=-1, flatten=False,
                 usemask=False, asrecarray=False):
    """
    Merge arrays field by field.

    Parameters
    ----------
    seqarrays : sequence of ndarrays
        Sequence of arrays
    fill_value : {float}, optional
        Filling value used to pad missing data on the shorter arrays.
    flatten : {False, True}, optional
        Whether to collapse nested fields.
    usemask : {False, True}, optional
        Whether to return a masked array or not.
    asrecarray : {False, True}, optional
        Whether to return a recarray (MaskedRecords) or not.

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.lib import recfunctions as rfn
    >>> rfn.merge_arrays((np.array([1, 2]), np.array([10., 20., 30.])))
    array([( 1, 10.), ( 2, 20.), (-1, 30.)],
          dtype=[('f0', '<i8'), ('f1', '<f8')])

    >>> rfn.merge_arrays((np.array([1, 2], dtype=np.int64),
    ...         np.array([10., 20., 30.])), usemask=False)
     array([(1, 10.0), (2, 20.0), (-1, 30.0)],
             dtype=[('f0', '<i8'), ('f1', '<f8')])
    >>> rfn.merge_arrays((np.array([1, 2]).view([('a', np.int64)]),
    ...               np.array([10., 20., 30.])),
    ...              usemask=False, asrecarray=True)
    rec.array([( 1, 10.), ( 2, 20.), (-1, 30.)],
              dtype=[('a', '<i8'), ('f1', '<f8')])

    Notes
    -----
    * Without a mask, the missing value will be filled with something,
      depending on what its corresponding type:

      * ``-1``      for integers
      * ``-1.0``    for floating point numbers
      * ``'-'``     for characters
      * ``'-1'``    for strings
      * ``True``    for boolean values
    * XXX: I just obtained these values empirically
    """
    # Only one item in the input sequence ?
    if (len(seqarrays) == 1):
        seqarrays = np.asanyarray(seqarrays[0])
    # Do we have a single ndarray as input ?
    if isinstance(seqarrays, (np.ndarray, np.void)):
        seqdtype = seqarrays.dtype
        # Make sure we have named fields
        if seqdtype.names is None:
            seqdtype = np.dtype([('', seqdtype)])
        if not flatten or _zip_dtype((seqarrays,), flatten=True) == seqdtype:
            # Minimal processing needed: just make sure everything's a-ok
            seqarrays = seqarrays.ravel()
            # Find what type of array we must return
            if usemask:
                if asrecarray:
                    seqtype = mrec.MaskedRecords
                else:
                    seqtype = ma.MaskedArray
            elif asrecarray:
                seqtype = np.recarray
            else:
                seqtype = np.ndarray
            return seqarrays.view(dtype=seqdtype, type=seqtype)
        else:
            seqarrays = (seqarrays,)
    else:
        # Make sure we have arrays in the input sequence
        seqarrays = [np.asanyarray(_m) for _m in seqarrays]
    # Find the sizes of the inputs and their maximum
    sizes = tuple(a.size for a in seqarrays)
    maxlength = max(sizes)
    # Get the dtype of the output (flattening if needed)
    newdtype = _zip_dtype(seqarrays, flatten=flatten)
    # Initialize the sequences for data and mask
    seqdata = []
    seqmask = []
    # If we expect some kind of MaskedArray, make a special loop.
    if usemask:
        for (a, n) in zip(seqarrays, sizes):
            nbmissing = (maxlength - n)
            # Get the data and mask
            data = a.ravel().__array__()
            mask = ma.getmaskarray(a).ravel()
            # Get the filling value (if needed)
            if nbmissing:
                fval = mrec._check_fill_value(fill_value, a.dtype)
                if isinstance(fval, (np.ndarray, np.void)):
                    if len(fval.dtype) == 1:
                        fval = fval.item()[0]
                        fmsk = True
                    else:
                        fval = np.array(fval, dtype=a.dtype, ndmin=1)
                        fmsk = np.ones((1,), dtype=mask.dtype)
            else:
                fval = None
                fmsk = True
            # Store an iterator padding the input to the expected length
            seqdata.append(itertools.chain(data, [fval] * nbmissing))
            seqmask.append(itertools.chain(mask, [fmsk] * nbmissing))
        # Create an iterator for the data
        data = tuple(_izip_records(seqdata, flatten=flatten))
        output = ma.array(np.fromiter(data, dtype=newdtype, count=maxlength),
                          mask=list(_izip_records(seqmask, flatten=flatten)))
        if asrecarray:
            output = output.view(mrec.MaskedRecords)
    else:
        # Same as before, without the mask we don't need...
        for (a, n) in zip(seqarrays, sizes):
            nbmissing = (maxlength - n)
            data = a.ravel().__array__()
            if nbmissing:
                fval = mrec._check_fill_value(fill_value, a.dtype)
                if isinstance(fval, (np.ndarray, np.void)):
                    if len(fval.dtype) == 1:
                        fval = fval.item()[0]
                    else:
                        fval = np.array(fval, dtype=a.dtype, ndmin=1)
            else:
                fval = None
            seqdata.append(itertools.chain(data, [fval] * nbmissing))
        output = np.fromiter(tuple(_izip_records(seqdata, flatten=flatten)),
                             dtype=newdtype, count=maxlength)
        if asrecarray:
            output = output.view(np.recarray)
    # And we're done...
    return output


def _drop_fields_dispatcher(base, drop_names, usemask=None, asrecarray=None):
    return (base,)


@array_function_dispatch(_drop_fields_dispatcher)
def drop_fields(base, drop_names, usemask=True, asrecarray=False):
    """
    Return a new array with fields in `drop_names` dropped.

    Nested fields are supported.

    Parameters
    ----------
    base : array
        Input array
    drop_names : string or sequence
        String or sequence of strings corresponding to the names of the
        fields to drop.
    usemask : {False, True}, optional
        Whether to return a masked array or not.
    asrecarray : string or sequence, optional
        Whether to return a recarray or a mrecarray (`asrecarray=True`) or
        a plain ndarray or masked array with flexible dtype. The default
        is False.

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.lib import recfunctions as rfn
    >>> a = np.array([(1, (2, 3.0)), (4, (5, 6.0))],
    ...   dtype=[('a', np.int64), ('b', [('ba', np.double), ('bb', np.int64)])])
    >>> rfn.drop_fields(a, 'a')
    array([((2., 3),), ((5., 6),)],
          dtype=[('b', [('ba', '<f8'), ('bb', '<i8')])])
    >>> rfn.drop_fields(a, 'ba')
    array([(1, (3,)), (4, (6,))], dtype=[('a', '<i8'), ('b', [('bb', '<i8')])])
    >>> rfn.drop_fields(a, ['ba', 'bb'])
    array([(1,), (4,)], dtype=[('a', '<i8')])
    """
    if _is_string_like(drop_names):
        drop_names = [drop_names]
    else:
        drop_names = set(drop_names)

    def _drop_descr(ndtype, drop_names):
        names = ndtype.names
        newdtype = []
        for name in names:
            current = ndtype[name]
            if name in drop_names:
                continue
            if current.names is not None:
                descr = _drop_descr(current, drop_names)
                if descr:
                    newdtype.append((name, descr))
            else:
                newdtype.append((name, current))
        return newdtype

    newdtype = _drop_descr(base.dtype, drop_names)

    output = np.empty(base.shape, dtype=newdtype)
    output = recursive_fill_fields(base, output)
    return _fix_output(output, usemask=usemask, asrecarray=asrecarray)


def _keep_fields(base, keep_names, usemask=True, asrecarray=False):
    """
    Return a new array keeping only the fields in `keep_names`,
    and preserving the order of those fields.

    Parameters
    ----------
    base : array
        Input array
    keep_names : string or sequence
        String or sequence of strings corresponding to the names of the
        fields to keep. Order of the names will be preserved.
    usemask : {False, True}, optional
        Whether to return a masked array or not.
    asrecarray : string or sequence, optional
        Whether to return a recarray or a mrecarray (`asrecarray=True`) or
        a plain ndarray or masked array with flexible dtype. The default
        is False.
    """
    newdtype = [(n, base.dtype[n]) for n in keep_names]
    output = np.empty(base.shape, dtype=newdtype)
    output = recursive_fill_fields(base, output)
    return _fix_output(output, usemask=usemask, asrecarray=asrecarray)


def _rec_drop_fields_dispatcher(base, drop_names):
    return (base,)


@array_function_dispatch(_rec_drop_fields_dispatcher)
def rec_drop_fields(base, drop_names):
    """
    Returns a new numpy.recarray with fields in `drop_names` dropped.
    """
    return drop_fields(base, drop_names, usemask=False, asrecarray=True)


def _rename_fields_dispatcher(base, namemapper):
    return (base,)


@array_function_dispatch(_rename_fields_dispatcher)
def rename_fields(base, namemapper):
    """
    Rename the fields from a flexible-datatype ndarray or recarray.

    Nested fields are supported.

    Parameters
    ----------
    base : ndarray
        Input array whose fields must be modified.
    namemapper : dictionary
        Dictionary mapping old field names to their new version.

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.lib import recfunctions as rfn
    >>> a = np.array([(1, (2, [3.0, 30.])), (4, (5, [6.0, 60.]))],
    ...   dtype=[('a', int),('b', [('ba', float), ('bb', (float, 2))])])
    >>> rfn.rename_fields(a, {'a':'A', 'bb':'BB'})
    array([(1, (2., [ 3., 30.])), (4, (5., [ 6., 60.]))],
          dtype=[('A', '<i8'), ('b', [('ba', '<f8'), ('BB', '<f8', (2,))])])

    """
    def _recursive_rename_fields(ndtype, namemapper):
        newdtype = []
        for name in ndtype.names:
            newname = namemapper.get(name, name)
            current = ndtype[name]
            if current.names is not None:
                newdtype.append(
                    (newname, _recursive_rename_fields(current, namemapper))
                    )
            else:
                newdtype.append((newname, current))
        return newdtype
    newdtype = _recursive_rename_fields(base.dtype, namemapper)
    return base.view(newdtype)


def _append_fields_dispatcher(base, names, data, dtypes=None,
                              fill_value=None, usemask=None, asrecarray=None):
    yield base
    yield from data


@array_function_dispatch(_append_fields_dispatcher)
def append_fields(base, names, data, dtypes=None,
                  fill_value=-1, usemask=True, asrecarray=False):
    """
    Add new fields to an existing array.

    The names of the fields are given with the `names` arguments,
    the corresponding values with the `data` arguments.
    If a single field is appended, `names`, `data` and `dtypes` do not have
    to be lists but just values.

    Parameters
    ----------
    base : array
        Input array to extend.
    names : string, sequence
        String or sequence of strings corresponding to the names
        of the new fields.
    data : array or sequence of arrays
        Array or sequence of arrays storing the fields to add to the base.
    dtypes : sequence of datatypes, optional
        Datatype or sequence of datatypes.
        If None, the datatypes are estimated from the `data`.
    fill_value : {float}, optional
        Filling value used to pad missing data on the shorter arrays.
    usemask : {False, True}, optional
        Whether to return a masked array or not.
    asrecarray : {False, True}, optional
        Whether to return a recarray (MaskedRecords) or not.

    """
    # Check the names
    if isinstance(names, (tuple, list)):
        if len(names) != len(data):
            msg = "The number of arrays does not match the number of names"
            raise ValueError(msg)
    elif isinstance(names, str):
        names = [names, ]
        data = [data, ]
    #
    if dtypes is None:
        data = [np.array(a, copy=None, subok=True) for a in data]
        data = [a.view([(name, a.dtype)]) for (name, a) in zip(names, data)]
    else:
        if not isinstance(dtypes, (tuple, list)):
            dtypes = [dtypes, ]
        if len(data) != len(dtypes):
            if len(dtypes) == 1:
                dtypes = dtypes * len(data)
            else:
                msg = "The dtypes argument must be None, a dtype, or a list."
                raise ValueError(msg)
        data = [np.array(a, copy=None, subok=True, dtype=d).view([(n, d)])
                for (a, n, d) in zip(data, names, dtypes)]
    #
    base = merge_arrays(base, usemask=usemask, fill_value=fill_value)
    if len(data) > 1:
        data = merge_arrays(data, flatten=True, usemask=usemask,
                            fill_value=fill_value)
    else:
        data = data.pop()
    #
    output = ma.masked_all(
        max(len(base), len(data)),
        dtype=_get_fieldspec(base.dtype) + _get_fieldspec(data.dtype))
    output = recursive_fill_fields(base, output)
    output = recursive_fill_fields(data, output)
    #
    return _fix_output(output, usemask=usemask, asrecarray=asrecarray)


def _rec_append_fields_dispatcher(base, names, data, dtypes=None):
    yield base
    yield from data


@array_function_dispatch(_rec_append_fields_dispatcher)
def rec_append_fields(base, names, data, dtypes=None):
    """
    Add new fields to an existing array.

    The names of the fields are given with the `names` arguments,
    the corresponding values with the `data` arguments.
    If a single field is appended, `names`, `data` and `dtypes` do not have
    to be lists but just values.

    Parameters
    ----------
    base : array
        Input array to extend.
    names : string, sequence
        String or sequence of strings corresponding to the names
        of the new fields.
    data : array or sequence of arrays
        Array or sequence of arrays storing the fields to add to the base.
    dtypes : sequence of datatypes, optional
        Datatype or sequence of datatypes.
        If None, the datatypes are estimated from the `data`.

    See Also
    --------
    append_fields

    Returns
    -------
    appended_array : np.recarray
    """
    return append_fields(base, names, data=data, dtypes=dtypes,
                         asrecarray=True, usemask=False)


def _repack_fields_dispatcher(a, align=None, recurse=None):
    return (a,)


@array_function_dispatch(_repack_fields_dispatcher)
def repack_fields(a, align=False, recurse=False):
    """
    Re-pack the fields of a structured array or dtype in memory.

    The memory layout of structured datatypes allows fields at arbitrary
    byte offsets. This means the fields can be separated by padding bytes,
    their offsets can be non-monotonically increasing, and they can overlap.

    This method removes any overlaps and reorders the fields in memory so they
    have increasing byte offsets, and adds or removes padding bytes depending
    on the `align` option, which behaves like the `align` option to
    `numpy.dtype`.

    If `align=False`, this method produces a "packed" memory layout in which
    each field starts at the byte the previous field ended, and any padding
    bytes are removed.

    If `align=True`, this methods produces an "aligned" memory layout in which
    each field's offset is a multiple of its alignment, and the total itemsize
    is a multiple of the largest alignment, by adding padding bytes as needed.

    Parameters
    ----------
    a : ndarray or dtype
       array or dtype for which to repack the fields.
    align : boolean
       If true, use an "aligned" memory layout, otherwise use a "packed" layout.
    recurse : boolean
       If True, also repack nested structures.

    Returns
    -------
    repacked : ndarray or dtype
       Copy of `a` with fields repacked, or `a` itself if no repacking was
       needed.

    Examples
    --------
    >>> import numpy as np

    >>> from numpy.lib import recfunctions as rfn
    >>> def print_offsets(d):
    ...     print("offsets:", [d.fields[name][1] for name in d.names])
    ...     print("itemsize:", d.itemsize)
    ...
    >>> dt = np.dtype('u1, <i8, <f8', align=True)
    >>> dt
    dtype({'names': ['f0', 'f1', 'f2'], 'formats': ['u1', '<i8', '<f8'], \
'offsets': [0, 8, 16], 'itemsize': 24}, align=True)
    >>> print_offsets(dt)
    offsets: [0, 8, 16]
    itemsize: 24
    >>> packed_dt = rfn.repack_fields(dt)
    >>> packed_dt
    dtype([('f0', 'u1'), ('f1', '<i8'), ('f2', '<f8')])
    >>> print_offsets(packed_dt)
    offsets: [0, 1, 9]
    itemsize: 17

    """
    if not isinstance(a, np.dtype):
        dt = repack_fields(a.dtype, align=align, recurse=recurse)
        return a.astype(dt, copy=False)

    if a.names is None:
        return a

    fieldinfo = []
    for name in a.names:
        tup = a.fields[name]
        if recurse:
            fmt = repack_fields(tup[0], align=align, recurse=True)
        else:
            fmt = tup[0]

        if len(tup) == 3:
            name = (tup[2], name)

        fieldinfo.append((name, fmt))

    dt = np.dtype(fieldinfo, align=align)
    return np.dtype((a.type, dt))

def _get_fields_and_offsets(dt, offset=0):
    """
    Returns a flat list of (dtype, count, offset) tuples of all the
    scalar fields in the dtype "dt", including nested fields, in left
    to right order.
    """

    # counts up elements in subarrays, including nested subarrays, and returns
    # base dtype and count
    def count_elem(dt):
        count = 1
        while dt.shape != ():
            for size in dt.shape:
                count *= size
            dt = dt.base
        return dt, count

    fields = []
    for name in dt.names:
        field = dt.fields[name]
        f_dt, f_offset = field[0], field[1]
        f_dt, n = count_elem(f_dt)

        if f_dt.names is None:
            fields.append((np.dtype((f_dt, (n,))), n, f_offset + offset))
        else:
            subfields = _get_fields_and_offsets(f_dt, f_offset + offset)
            size = f_dt.itemsize

            for i in range(n):
                if i == 0:
                    # optimization: avoid list comprehension if no subarray
                    fields.extend(subfields)
                else:
                    fields.extend([(d, c, o + i * size) for d, c, o in subfields])
    return fields

def _common_stride(offsets, counts, itemsize):
    """
    Returns the stride between the fields, or None if the stride is not
    constant. The values in "counts" designate the lengths of
    subarrays. Subarrays are treated as many contiguous fields, with
    always positive stride.
    """
    if len(offsets) <= 1:
        return itemsize

    negative = offsets[1] < offsets[0]  # negative stride
    if negative:
        # reverse, so offsets will be ascending
        it = zip(reversed(offsets), reversed(counts))
    else:
        it = zip(offsets, counts)

    prev_offset = None
    stride = None
    for offset, count in it:
        if count != 1:  # subarray: always c-contiguous
            if negative:
                return None  # subarrays can never have a negative stride
            if stride is None:
                stride = itemsize
            if stride != itemsize:
                return None
            end_offset = offset + (count - 1) * itemsize
        else:
            end_offset = offset

        if prev_offset is not None:
            new_stride = offset - prev_offset
            if stride is None:
                stride = new_stride
            if stride != new_stride:
                return None

        prev_offset = end_offset

    if negative:
        return -stride
    return stride


def _structured_to_unstructured_dispatcher(arr, dtype=None, copy=None,
                                           casting=None):
    return (arr,)

@array_function_dispatch(_structured_to_unstructured_dispatcher)
def structured_to_unstructured(arr, dtype=None, copy=False, casting='unsafe'):
    """
    Converts an n-D structured array into an (n+1)-D unstructured array.

    The new array will have a new last dimension equal in size to the
    number of field-elements of the input array. If not supplied, the output
    datatype is determined from the numpy type promotion rules applied to all
    the field datatypes.

    Nested fields, as well as each element of any subarray fields, all count
    as a single field-elements.

    Parameters
    ----------
    arr : ndarray
       Structured array or dtype to convert. Cannot contain object datatype.
    dtype : dtype, optional
       The dtype of the output unstructured array.
    copy : bool, optional
        If true, always return a copy. If false, a view is returned if
        possible, such as when the `dtype` and strides of the fields are
        suitable and the array subtype is one of `numpy.ndarray`,
        `numpy.recarray` or `numpy.memmap`.

        .. versionchanged:: 1.25.0
            A view can now be returned if the fields are separated by a
            uniform stride.

    casting : {'no', 'equiv', 'safe', 'same_kind', 'unsafe'}, optional
        See casting argument of `numpy.ndarray.astype`. Controls what kind of
        data casting may occur.

    Returns
    -------
    unstructured : ndarray
       Unstructured array with one more dimension.

    Examples
    --------
    >>> import numpy as np

    >>> from numpy.lib import recfunctions as rfn
    >>> a = np.zeros(4, dtype=[('a', 'i4'), ('b', 'f4,u2'), ('c', 'f4', 2)])
    >>> a
    array([(0, (0., 0), [0., 0.]), (0, (0., 0), [0., 0.]),
           (0, (0., 0), [0., 0.]), (0, (0., 0), [0., 0.])],
          dtype=[('a', '<i4'), ('b', [('f0', '<f4'), ('f1', '<u2')]), ('c', '<f4', (2,))])
    >>> rfn.structured_to_unstructured(a)
    array([[0., 0., 0., 0., 0.],
           [0., 0., 0., 0., 0.],
           [0., 0., 0., 0., 0.],
           [0., 0., 0., 0., 0.]])

    >>> b = np.array([(1, 2, 5), (4, 5, 7), (7, 8 ,11), (10, 11, 12)],
    ...              dtype=[('x', 'i4'), ('y', 'f4'), ('z', 'f8')])
    >>> np.mean(rfn.structured_to_unstructured(b[['x', 'z']]), axis=-1)
    array([ 3. ,  5.5,  9. , 11. ])

    """  # noqa: E501
    if arr.dtype.names is None:
        raise ValueError('arr must be a structured array')

    fields = _get_fields_and_offsets(arr.dtype)
    n_fields = len(fields)
    if n_fields == 0 and dtype is None:
        raise ValueError("arr has no fields. Unable to guess dtype")
    elif n_fields == 0:
        # too many bugs elsewhere for this to work now
        raise NotImplementedError("arr with no fields is not supported")

    dts, counts, offsets = zip(*fields)
    names = [f'f{n}' for n in range(n_fields)]

    if dtype is None:
        out_dtype = np.result_type(*[dt.base for dt in dts])
    else:
        out_dtype = np.dtype(dtype)

    # Use a series of views and casts to convert to an unstructured array:

    # first view using flattened fields (doesn't work for object arrays)
    # Note: dts may include a shape for subarrays
    flattened_fields = np.dtype({'names': names,
                                 'formats': dts,
                                 'offsets': offsets,
                                 'itemsize': arr.dtype.itemsize})
    arr = arr.view(flattened_fields)

    # we only allow a few types to be unstructured by manipulating the
    # strides, because we know it won't work with, for example, np.matrix nor
    # np.ma.MaskedArray.
    can_view = type(arr) in (np.ndarray, np.recarray, np.memmap)
    if (not copy) and can_view and all(dt.base == out_dtype for dt in dts):
        # all elements have the right dtype already; if they have a common
        # stride, we can just return a view
        common_stride = _common_stride(offsets, counts, out_dtype.itemsize)
        if common_stride is not None:
            wrap = arr.__array_wrap__

            new_shape = arr.shape + (sum(counts), out_dtype.itemsize)
            new_strides = arr.strides + (abs(common_stride), 1)

            arr = arr[..., np.newaxis].view(np.uint8)  # view as bytes
            arr = arr[..., min(offsets):]  # remove the leading unused data
            arr = np.lib.stride_tricks.as_strided(arr,
                                                  new_shape,
                                                  new_strides,
                                                  subok=True)

            # cast and drop the last dimension again
            arr = arr.view(out_dtype)[..., 0]

            if common_stride < 0:
                arr = arr[..., ::-1]  # reverse, if the stride was negative
            if type(arr) is not type(wrap.__self__):
                # Some types (e.g. recarray) turn into an ndarray along the
                # way, so we have to wrap it again in order to match the
                # behavior with copy=True.
                arr = wrap(arr)
            return arr

    # next cast to a packed format with all fields converted to new dtype
    packed_fields = np.dtype({'names': names,
                              'formats': [(out_dtype, dt.shape) for dt in dts]})
    arr = arr.astype(packed_fields, copy=copy, casting=casting)

    # finally is it safe to view the packed fields as the unstructured type
    return arr.view((out_dtype, (sum(counts),)))


def _unstructured_to_structured_dispatcher(arr, dtype=None, names=None,
                                           align=None, copy=None, casting=None):
    return (arr,)

@array_function_dispatch(_unstructured_to_structured_dispatcher)
def unstructured_to_structured(arr, dtype=None, names=None, align=False,
                               copy=False, casting='unsafe'):
    """
    Converts an n-D unstructured array into an (n-1)-D structured array.

    The last dimension of the input array is converted into a structure, with
    number of field-elements equal to the size of the last dimension of the
    input array. By default all output fields have the input array's dtype, but
    an output structured dtype with an equal number of fields-elements can be
    supplied instead.

    Nested fields, as well as each element of any subarray fields, all count
    towards the number of field-elements.

    Parameters
    ----------
    arr : ndarray
       Unstructured array or dtype to convert.
    dtype : dtype, optional
       The structured dtype of the output array
    names : list of strings, optional
       If dtype is not supplied, this specifies the field names for the output
       dtype, in order. The field dtypes will be the same as the input array.
    align : boolean, optional
       Whether to create an aligned memory layout.
    copy : bool, optional
        See copy argument to `numpy.ndarray.astype`. If true, always return a
        copy. If false, and `dtype` requirements are satisfied, a view is
        returned.
    casting : {'no', 'equiv', 'safe', 'same_kind', 'unsafe'}, optional
        See casting argument of `numpy.ndarray.astype`. Controls what kind of
        data casting may occur.

    Returns
    -------
    structured : ndarray
       Structured array with fewer dimensions.

    Examples
    --------
    >>> import numpy as np

    >>> from numpy.lib import recfunctions as rfn
    >>> dt = np.dtype([('a', 'i4'), ('b', 'f4,u2'), ('c', 'f4', 2)])
    >>> a = np.arange(20).reshape((4,5))
    >>> a
    array([[ 0,  1,  2,  3,  4],
           [ 5,  6,  7,  8,  9],
           [10, 11, 12, 13, 14],
           [15, 16, 17, 18, 19]])
    >>> rfn.unstructured_to_structured(a, dt)
    array([( 0, ( 1.,  2), [ 3.,  4.]), ( 5, ( 6.,  7), [ 8.,  9.]),
           (10, (11., 12), [13., 14.]), (15, (16., 17), [18., 19.])],
          dtype=[('a', '<i4'), ('b', [('f0', '<f4'), ('f1', '<u2')]), ('c', '<f4', (2,))])

    """  # noqa: E501
    if arr.shape == ():
        raise ValueError('arr must have at least one dimension')
    n_elem = arr.shape[-1]
    if n_elem == 0:
        # too many bugs elsewhere for this to work now
        raise NotImplementedError("last axis with size 0 is not supported")

    if dtype is None:
        if names is None:
            names = [f'f{n}' for n in range(n_elem)]
        out_dtype = np.dtype([(n, arr.dtype) for n in names], align=align)
        fields = _get_fields_and_offsets(out_dtype)
        dts, counts, offsets = zip(*fields)
    else:
        if names is not None:
            raise ValueError("don't supply both dtype and names")
        # if dtype is the args of np.dtype, construct it
        dtype = np.dtype(dtype)
        # sanity check of the input dtype
        fields = _get_fields_and_offsets(dtype)
        if len(fields) == 0:
            dts, counts, offsets = [], [], []
        else:
            dts, counts, offsets = zip(*fields)

        if n_elem != sum(counts):
            raise ValueError('The length of the last dimension of arr must '
                             'be equal to the number of fields in dtype')
        out_dtype = dtype
        if align and not out_dtype.isalignedstruct:
            raise ValueError("align was True but dtype is not aligned")

    names = [f'f{n}' for n in range(len(fields))]

    # Use a series of views and casts to convert to a structured array:

    # first view as a packed structured array of one dtype
    packed_fields = np.dtype({'names': names,
                              'formats': [(arr.dtype, dt.shape) for dt in dts]})
    arr = np.ascontiguousarray(arr).view(packed_fields)

    # next cast to an unpacked but flattened format with varied dtypes
    flattened_fields = np.dtype({'names': names,
                                 'formats': dts,
                                 'offsets': offsets,
                                 'itemsize': out_dtype.itemsize})
    arr = arr.astype(flattened_fields, copy=copy, casting=casting)

    # finally view as the final nested dtype and remove the last axis
    return arr.view(out_dtype)[..., 0]

def _apply_along_fields_dispatcher(func, arr):
    return (arr,)

@array_function_dispatch(_apply_along_fields_dispatcher)
def apply_along_fields(func, arr):
    """
    Apply function 'func' as a reduction across fields of a structured array.

    This is similar to `numpy.apply_along_axis`, but treats the fields of a
    structured array as an extra axis. The fields are all first cast to a
    common type following the type-promotion rules from `numpy.result_type`
    applied to the field's dtypes.

    Parameters
    ----------
    func : function
       Function to apply on the "field" dimension. This function must
       support an `axis` argument, like `numpy.mean`, `numpy.sum`, etc.
    arr : ndarray
       Structured array for which to apply func.

    Returns
    -------
    out : ndarray
       Result of the reduction operation

    Examples
    --------
    >>> import numpy as np

    >>> from numpy.lib import recfunctions as rfn
    >>> b = np.array([(1, 2, 5), (4, 5, 7), (7, 8 ,11), (10, 11, 12)],
    ...              dtype=[('x', 'i4'), ('y', 'f4'), ('z', 'f8')])
    >>> rfn.apply_along_fields(np.mean, b)
    array([ 2.66666667,  5.33333333,  8.66666667, 11.        ])
    >>> rfn.apply_along_fields(np.mean, b[['x', 'z']])
    array([ 3. ,  5.5,  9. , 11. ])

    """
    if arr.dtype.names is None:
        raise ValueError('arr must be a structured array')

    uarr = structured_to_unstructured(arr)
    return func(uarr, axis=-1)
    # works and avoids axis requirement, but very, very slow:
    #return np.apply_along_axis(func, -1, uarr)

def _assign_fields_by_name_dispatcher(dst, src, zero_unassigned=None):
    return dst, src

@array_function_dispatch(_assign_fields_by_name_dispatcher)
def assign_fields_by_name(dst, src, zero_unassigned=True):
    """
    Assigns values from one structured array to another by field name.

    Normally in numpy >= 1.14, assignment of one structured array to another
    copies fields "by position", meaning that the first field from the src is
    copied to the first field of the dst, and so on, regardless of field name.

    This function instead copies "by field name", such that fields in the dst
    are assigned from the identically named field in the src. This applies
    recursively for nested structures. This is how structure assignment worked
    in numpy >= 1.6 to <= 1.13.

    Parameters
    ----------
    dst : ndarray
    src : ndarray
        The source and destination arrays during assignment.
    zero_unassigned : bool, optional
        If True, fields in the dst for which there was no matching
        field in the src are filled with the value 0 (zero). This
        was the behavior of numpy <= 1.13. If False, those fields
        are not modified.
    """

    if dst.dtype.names is None:
        dst[...] = src
        return

    for name in dst.dtype.names:
        if name not in src.dtype.names:
            if zero_unassigned:
                dst[name] = 0
        else:
            assign_fields_by_name(dst[name], src[name],
                                  zero_unassigned)

def _require_fields_dispatcher(array, required_dtype):
    return (array,)

@array_function_dispatch(_require_fields_dispatcher)
def require_fields(array, required_dtype):
    """
    Casts a structured array to a new dtype using assignment by field-name.

    This function assigns from the old to the new array by name, so the
    value of a field in the output array is the value of the field with the
    same name in the source array. This has the effect of creating a new
    ndarray containing only the fields "required" by the required_dtype.

    If a field name in the required_dtype does not exist in the
    input array, that field is created and set to 0 in the output array.

    Parameters
    ----------
    a : ndarray
       array to cast
    required_dtype : dtype
       datatype for output array

    Returns
    -------
    out : ndarray
        array with the new dtype, with field values copied from the fields in
        the input array with the same name

    Examples
    --------
    >>> import numpy as np

    >>> from numpy.lib import recfunctions as rfn
    >>> a = np.ones(4, dtype=[('a', 'i4'), ('b', 'f8'), ('c', 'u1')])
    >>> rfn.require_fields(a, [('b', 'f4'), ('c', 'u1')])
    array([(1., 1), (1., 1), (1., 1), (1., 1)],
      dtype=[('b', '<f4'), ('c', 'u1')])
    >>> rfn.require_fields(a, [('b', 'f4'), ('newf', 'u1')])
    array([(1., 0), (1., 0), (1., 0), (1., 0)],
      dtype=[('b', '<f4'), ('newf', 'u1')])

    """
    out = np.empty(array.shape, dtype=required_dtype)
    assign_fields_by_name(out, array)
    return out


def _stack_arrays_dispatcher(arrays, defaults=None, usemask=None,
                             asrecarray=None, autoconvert=None):
    return arrays


@array_function_dispatch(_stack_arrays_dispatcher)
def stack_arrays(arrays, defaults=None, usemask=True, asrecarray=False,
                 autoconvert=False):
    """
    Superposes arrays fields by fields

    Parameters
    ----------
    arrays : array or sequence
        Sequence of input arrays.
    defaults : dictionary, optional
        Dictionary mapping field names to the corresponding default values.
    usemask : {True, False}, optional
        Whether to return a MaskedArray (or MaskedRecords is
        `asrecarray==True`) or a ndarray.
    asrecarray : {False, True}, optional
        Whether to return a recarray (or MaskedRecords if `usemask==True`)
        or just a flexible-type ndarray.
    autoconvert : {False, True}, optional
        Whether automatically cast the type of the field to the maximum.

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.lib import recfunctions as rfn
    >>> x = np.array([1, 2,])
    >>> rfn.stack_arrays(x) is x
    True
    >>> z = np.array([('A', 1), ('B', 2)], dtype=[('A', '|S3'), ('B', float)])
    >>> zz = np.array([('a', 10., 100.), ('b', 20., 200.), ('c', 30., 300.)],
    ...   dtype=[('A', '|S3'), ('B', np.double), ('C', np.double)])
    >>> test = rfn.stack_arrays((z,zz))
    >>> test
    masked_array(data=[(b'A', 1.0, --), (b'B', 2.0, --), (b'a', 10.0, 100.0),
                       (b'b', 20.0, 200.0), (b'c', 30.0, 300.0)],
                 mask=[(False, False,  True), (False, False,  True),
                       (False, False, False), (False, False, False),
                       (False, False, False)],
           fill_value=(b'N/A', 1e+20, 1e+20),
                dtype=[('A', 'S3'), ('B', '<f8'), ('C', '<f8')])

    """
    if isinstance(arrays, np.ndarray):
        return arrays
    elif len(arrays) == 1:
        return arrays[0]
    seqarrays = [np.asanyarray(a).ravel() for a in arrays]
    nrecords = [len(a) for a in seqarrays]
    ndtype = [a.dtype for a in seqarrays]
    fldnames = [d.names for d in ndtype]
    #
    dtype_l = ndtype[0]
    newdescr = _get_fieldspec(dtype_l)
    names = [n for n, d in newdescr]
    for dtype_n in ndtype[1:]:
        for fname, fdtype in _get_fieldspec(dtype_n):
            if fname not in names:
                newdescr.append((fname, fdtype))
                names.append(fname)
            else:
                nameidx = names.index(fname)
                _, cdtype = newdescr[nameidx]
                if autoconvert:
                    newdescr[nameidx] = (fname, max(fdtype, cdtype))
                elif fdtype != cdtype:
                    raise TypeError(f"Incompatible type '{cdtype}' <> '{fdtype}'")
    # Only one field: use concatenate
    if len(newdescr) == 1:
        output = ma.concatenate(seqarrays)
    else:
        #
        output = ma.masked_all((np.sum(nrecords),), newdescr)
        offset = np.cumsum(np.r_[0, nrecords])
        seen = []
        for (a, n, i, j) in zip(seqarrays, fldnames, offset[:-1], offset[1:]):
            names = a.dtype.names
            if names is None:
                output[f'f{len(seen)}'][i:j] = a
            else:
                for name in n:
                    output[name][i:j] = a[name]
                    if name not in seen:
                        seen.append(name)
    #
    return _fix_output(_fix_defaults(output, defaults),
                       usemask=usemask, asrecarray=asrecarray)


def _find_duplicates_dispatcher(
        a, key=None, ignoremask=None, return_index=None):
    return (a,)


@array_function_dispatch(_find_duplicates_dispatcher)
def find_duplicates(a, key=None, ignoremask=True, return_index=False):
    """
    Find the duplicates in a structured array along a given key

    Parameters
    ----------
    a : array-like
        Input array
    key : {string, None}, optional
        Name of the fields along which to check the duplicates.
        If None, the search is performed by records
    ignoremask : {True, False}, optional
        Whether masked data should be discarded or considered as duplicates.
    return_index : {False, True}, optional
        Whether to return the indices of the duplicated values.

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.lib import recfunctions as rfn
    >>> ndtype = [('a', int)]
    >>> a = np.ma.array([1, 1, 1, 2, 2, 3, 3],
    ...         mask=[0, 0, 1, 0, 0, 0, 1]).view(ndtype)
    >>> rfn.find_duplicates(a, ignoremask=True, return_index=True)
    (masked_array(data=[(1,), (1,), (2,), (2,)],
                 mask=[(False,), (False,), (False,), (False,)],
           fill_value=(999999,),
                dtype=[('a', '<i8')]), array([0, 1, 3, 4]))
    """
    a = np.asanyarray(a).ravel()
    # Get a dictionary of fields
    fields = get_fieldstructure(a.dtype)
    # Get the sorting data (by selecting the corresponding field)
    base = a
    if key:
        for f in fields[key]:
            base = base[f]
        base = base[key]
    # Get the sorting indices and the sorted data
    sortidx = base.argsort()
    sortedbase = base[sortidx]
    sorteddata = sortedbase.filled()
    # Compare the sorting data
    flag = (sorteddata[:-1] == sorteddata[1:])
    # If masked data must be ignored, set the flag to false where needed
    if ignoremask:
        sortedmask = sortedbase.recordmask
        flag[sortedmask[1:]] = False
    flag = np.concatenate(([False], flag))
    # We need to take the point on the left as well (else we're missing it)
    flag[:-1] = flag[:-1] + flag[1:]
    duplicates = a[sortidx][flag]
    if return_index:
        return (duplicates, sortidx[flag])
    else:
        return duplicates


def _join_by_dispatcher(
        key, r1, r2, jointype=None, r1postfix=None, r2postfix=None,
        defaults=None, usemask=None, asrecarray=None):
    return (r1, r2)


@array_function_dispatch(_join_by_dispatcher)
def join_by(key, r1, r2, jointype='inner', r1postfix='1', r2postfix='2',
            defaults=None, usemask=True, asrecarray=False):
    """
    Join arrays `r1` and `r2` on key `key`.

    The key should be either a string or a sequence of string corresponding
    to the fields used to join the array.  An exception is raised if the
    `key` field cannot be found in the two input arrays.  Neither `r1` nor
    `r2` should have any duplicates along `key`: the presence of duplicates
    will make the output quite unreliable. Note that duplicates are not
    looked for by the algorithm.

    Parameters
    ----------
    key : {string, sequence}
        A string or a sequence of strings corresponding to the fields used
        for comparison.
    r1, r2 : arrays
        Structured arrays.
    jointype : {'inner', 'outer', 'leftouter'}, optional
        If 'inner', returns the elements common to both r1 and r2.
        If 'outer', returns the common elements as well as the elements of
        r1 not in r2 and the elements of not in r2.
        If 'leftouter', returns the common elements and the elements of r1
        not in r2.
    r1postfix : string, optional
        String appended to the names of the fields of r1 that are present
        in r2 but absent of the key.
    r2postfix : string, optional
        String appended to the names of the fields of r2 that are present
        in r1 but absent of the key.
    defaults : {dictionary}, optional
        Dictionary mapping field names to the corresponding default values.
    usemask : {True, False}, optional
        Whether to return a MaskedArray (or MaskedRecords is
        `asrecarray==True`) or a ndarray.
    asrecarray : {False, True}, optional
        Whether to return a recarray (or MaskedRecords if `usemask==True`)
        or just a flexible-type ndarray.

    Notes
    -----
    * The output is sorted along the key.
    * A temporary array is formed by dropping the fields not in the key for
      the two arrays and concatenating the result. This array is then
      sorted, and the common entries selected. The output is constructed by
      filling the fields with the selected entries. Matching is not
      preserved if there are some duplicates...

    """
    # Check jointype
    if jointype not in ('inner', 'outer', 'leftouter'):
        raise ValueError(
                "The 'jointype' argument should be in 'inner', "
                "'outer' or 'leftouter' (got '%s' instead)" % jointype
                )
    # If we have a single key, put it in a tuple
    if isinstance(key, str):
        key = (key,)

    # Check the keys
    if len(set(key)) != len(key):
        dup = next(x for n, x in enumerate(key) if x in key[n + 1:])
        raise ValueError(f"duplicate join key {dup!r}")
    for name in key:
        if name not in r1.dtype.names:
            raise ValueError(f'r1 does not have key field {name!r}')
        if name not in r2.dtype.names:
            raise ValueError(f'r2 does not have key field {name!r}')

    # Make sure we work with ravelled arrays
    r1 = r1.ravel()
    r2 = r2.ravel()
    (nb1, nb2) = (len(r1), len(r2))
    (r1names, r2names) = (r1.dtype.names, r2.dtype.names)

    # Check the names for collision
    collisions = (set(r1names) & set(r2names)) - set(key)
    if collisions and not (r1postfix or r2postfix):
        msg = "r1 and r2 contain common names, r1postfix and r2postfix "
        msg += "can't both be empty"
        raise ValueError(msg)

    # Make temporary arrays of just the keys
    #  (use order of keys in `r1` for back-compatibility)
    key1 = [n for n in r1names if n in key]
    r1k = _keep_fields(r1, key1)
    r2k = _keep_fields(r2, key1)

    # Concatenate the two arrays for comparison
    aux = ma.concatenate((r1k, r2k))
    idx_sort = aux.argsort(order=key)
    aux = aux[idx_sort]
    #
    # Get the common keys
    flag_in = ma.concatenate(([False], aux[1:] == aux[:-1]))
    flag_in[:-1] = flag_in[1:] + flag_in[:-1]
    idx_in = idx_sort[flag_in]
    idx_1 = idx_in[(idx_in < nb1)]
    idx_2 = idx_in[(idx_in >= nb1)] - nb1
    (r1cmn, r2cmn) = (len(idx_1), len(idx_2))
    if jointype == 'inner':
        (r1spc, r2spc) = (0, 0)
    elif jointype == 'outer':
        idx_out = idx_sort[~flag_in]
        idx_1 = np.concatenate((idx_1, idx_out[(idx_out < nb1)]))
        idx_2 = np.concatenate((idx_2, idx_out[(idx_out >= nb1)] - nb1))
        (r1spc, r2spc) = (len(idx_1) - r1cmn, len(idx_2) - r2cmn)
    elif jointype == 'leftouter':
        idx_out = idx_sort[~flag_in]
        idx_1 = np.concatenate((idx_1, idx_out[(idx_out < nb1)]))
        (r1spc, r2spc) = (len(idx_1) - r1cmn, 0)
    # Select the entries from each input
    (s1, s2) = (r1[idx_1], r2[idx_2])
    #
    # Build the new description of the output array .......
    # Start with the key fields
    ndtype = _get_fieldspec(r1k.dtype)

    # Add the fields from r1
    for fname, fdtype in _get_fieldspec(r1.dtype):
        if fname not in key:
            ndtype.append((fname, fdtype))

    # Add the fields from r2
    for fname, fdtype in _get_fieldspec(r2.dtype):
        # Have we seen the current name already ?
        # we need to rebuild this list every time
        names = [name for name, dtype in ndtype]
        try:
            nameidx = names.index(fname)
        except ValueError:
            #... we haven't: just add the description to the current list
            ndtype.append((fname, fdtype))
        else:
            # collision
            _, cdtype = ndtype[nameidx]
            if fname in key:
                # The current field is part of the key: take the largest dtype
                ndtype[nameidx] = (fname, max(fdtype, cdtype))
            else:
                # The current field is not part of the key: add the suffixes,
                # and place the new field adjacent to the old one
                ndtype[nameidx:nameidx + 1] = [
                    (fname + r1postfix, cdtype),
                    (fname + r2postfix, fdtype)
                ]
    # Rebuild a dtype from the new fields
    ndtype = np.dtype(ndtype)
    # Find the largest nb of common fields :
    # r1cmn and r2cmn should be equal, but...
    cmn = max(r1cmn, r2cmn)
    # Construct an empty array
    output = ma.masked_all((cmn + r1spc + r2spc,), dtype=ndtype)
    names = output.dtype.names
    for f in r1names:
        selected = s1[f]
        if f not in names or (f in r2names and not r2postfix and f not in key):
            f += r1postfix
        current = output[f]
        current[:r1cmn] = selected[:r1cmn]
        if jointype in ('outer', 'leftouter'):
            current[cmn:cmn + r1spc] = selected[r1cmn:]
    for f in r2names:
        selected = s2[f]
        if f not in names or (f in r1names and not r1postfix and f not in key):
            f += r2postfix
        current = output[f]
        current[:r2cmn] = selected[:r2cmn]
        if (jointype == 'outer') and r2spc:
            current[-r2spc:] = selected[r2cmn:]
    # Sort and finalize the output
    output.sort(order=key)
    kwargs = {'usemask': usemask, 'asrecarray': asrecarray}
    return _fix_output(_fix_defaults(output, defaults), **kwargs)


def _rec_join_dispatcher(
        key, r1, r2, jointype=None, r1postfix=None, r2postfix=None,
        defaults=None):
    return (r1, r2)


@array_function_dispatch(_rec_join_dispatcher)
def rec_join(key, r1, r2, jointype='inner', r1postfix='1', r2postfix='2',
             defaults=None):
    """
    Join arrays `r1` and `r2` on keys.
    Alternative to join_by, that always returns a np.recarray.

    See Also
    --------
    join_by : equivalent function
    """
    kwargs = {'jointype': jointype, 'r1postfix': r1postfix, 'r2postfix': r2postfix,
                  'defaults': defaults, 'usemask': False, 'asrecarray': True}
    return join_by(key, r1, r2, **kwargs)


del array_function_dispatch

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\Demos\app\dlgappdemo.py ===
# dlgappdemo - a demo of a dialog application.
# This is a demonstration of both a custom "application" module,
# and a Python program in a dialog box.
#
# NOTE:  You CAN NOT import this module from either PythonWin or Python.
# This module must be specified on the commandline to PythonWin only.
# eg, PythonWin /app dlgappdemo.py

import sys

import win32ui
from pywin.framework import dlgappcore


class TestDialogApp(dlgappcore.DialogApp):
    def CreateDialog(self):
        return TestAppDialog()


class TestAppDialog(dlgappcore.AppDialog):
    def __init__(self):
        self.edit = None
        dlgappcore.AppDialog.__init__(self, win32ui.IDD_LARGE_EDIT)

    def OnInitDialog(self):
        self.SetWindowText("Test dialog application")
        self.edit = self.GetDlgItem(win32ui.IDC_EDIT1)
        print("Hello from Python")
        print("args are:", end=" ")
        for arg in sys.argv:
            print(arg)
        return 1

    def PreDoModal(self):
        sys.stdout = sys.stderr = self

    def write(self, str):
        if self.edit:
            self.edit.SetSel(-2)
            # translate \n to \n\r
            self.edit.ReplaceSel(str.replace("\n", "\r\n"))
        else:
            win32ui.OutputDebug("dlgapp - no edit control! >>\n%s\n<<\n" % str)


app = TestDialogApp()

if __name__ == "__main__":
    import demoutils

    demoutils.NeedApp()

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pythonwin\pywin\Demos\app\dlgappdemo.py ===
# dlgappdemo - a demo of a dialog application.
# This is a demonstration of both a custom "application" module,
# and a Python program in a dialog box.
#
# NOTE:  You CAN NOT import this module from either PythonWin or Python.
# This module must be specified on the commandline to PythonWin only.
# eg, PythonWin /app dlgappdemo.py

import sys

import win32ui
from pywin.framework import dlgappcore


class TestDialogApp(dlgappcore.DialogApp):
    def CreateDialog(self):
        return TestAppDialog()


class TestAppDialog(dlgappcore.AppDialog):
    def __init__(self):
        self.edit = None
        dlgappcore.AppDialog.__init__(self, win32ui.IDD_LARGE_EDIT)

    def OnInitDialog(self):
        self.SetWindowText("Test dialog application")
        self.edit = self.GetDlgItem(win32ui.IDC_EDIT1)
        print("Hello from Python")
        print("args are:", end=" ")
        for arg in sys.argv:
            print(arg)
        return 1

    def PreDoModal(self):
        sys.stdout = sys.stderr = self

    def write(self, str):
        if self.edit:
            self.edit.SetSel(-2)
            # translate \n to \n\r
            self.edit.ReplaceSel(str.replace("\n", "\r\n"))
        else:
            win32ui.OutputDebug("dlgapp - no edit control! >>\n%s\n<<\n" % str)


app = TestDialogApp()

if __name__ == "__main__":
    import demoutils

    demoutils.NeedApp()

# === NexusCore/app\__init__.py ===
# フォルダ: app
# ファイル名: __init__.py
# メモ: FlaskのSECRET_KEYをハードコーディングから環境変数読み込みに変更し、セキュリティを向上させました。
#      他の設定値も併せて環境変数から読み込めるように改良しています。

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
# これにより、.envファイルに記述した設定がos.getenv()で利用可能になります。
load_dotenv()

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)

    # --- 基本設定 ---
    # ◀️ ハードコーディングされた秘密鍵を環境変数から読み込むように修正
    #    os.getenvの第2引数は、環境変数が設定されていない場合のデフォルト値です。
    #    本番環境では必ず強固なキーを環境変数に設定してください。
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "a-very-secret-key-for-development-only")
    
    # データベースのURIも環境変数から取得するように変更
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URI", "sqlite:///db.sqlite3")

    # --- Celery 用設定 ---
    # Celeryの接続情報も環境変数から取得するように変更
    app.config.from_mapping(
        CELERY=dict(
            broker_url=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
            result_backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
            task_ignore_result=True,
        )
    )

    # --- 拡張機能の初期化 ---
    db.init_app(app)

    # Blueprint の登録（ここで１回だけ）
    from .routes import bp as main_bp
    app.register_blueprint(main_bp)

    # Celery を紐付け
    from .extensions import celery_init_app
    celery_init_app(app)

    return app

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\app\__init__.py ===
# フォルダ: app
# ファイル名: __init__.py
# メモ: FlaskのSECRET_KEYをハードコーディングから環境変数読み込みに変更し、セキュリティを向上させました。
#      他の設定値も併せて環境変数から読み込めるように改良しています。

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
# これにより、.envファイルに記述した設定がos.getenv()で利用可能になります。
load_dotenv()

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)

    # --- 基本設定 ---
    # ◀️ ハードコーディングされた秘密鍵を環境変数から読み込むように修正
    #    os.getenvの第2引数は、環境変数が設定されていない場合のデフォルト値です。
    #    本番環境では必ず強固なキーを環境変数に設定してください。
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "a-very-secret-key-for-development-only")
    
    # データベースのURIも環境変数から取得するように変更
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URI", "sqlite:///db.sqlite3")

    # --- Celery 用設定 ---
    # Celeryの接続情報も環境変数から取得するように変更
    app.config.from_mapping(
        CELERY=dict(
            broker_url=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
            result_backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
            task_ignore_result=True,
        )
    )

    # --- 拡張機能の初期化 ---
    db.init_app(app)

    # Blueprint の登録（ここで１回だけ）
    from .routes import bp as main_bp
    app.register_blueprint(main_bp)

    # Celery を紐付け
    from .extensions import celery_init_app
    celery_init_app(app)

    return app

# === NexusCore/src\gradio_app\auto_revision_runner.py ===
# auto_revision_runner.py
import os
import sys
import time
import json
from datetime import datetime
from revision_loop import generate_prompt, extract_code_and_reason, call_gpt, run_pytest, save_file, read_file, save_patch_history

SANDBOX_DIR = "../sandbox_output"
SAMPLE_FILE = os.path.join(SANDBOX_DIR, "sample.py")
TEST_FILE = os.path.join(SANDBOX_DIR, "test_sample.py")

MAX_RETRIES = 5

def auto_loop(user_instruction=""):
    retry_count = 0

    while retry_count < MAX_RETRIES:
        print(f"\n🔁 [Attempt {retry_count + 1}/{MAX_RETRIES}] Generating revision...")

        version_summary = f"自動反復試行 {retry_count + 1} 回目"
        history = f"試行回数: {retry_count}"
        failed_tests = read_file(os.path.join(SANDBOX_DIR, "test_result.log")) if os.path.exists(os.path.join(SANDBOX_DIR, "test_result.log")) else ""

        prompt = generate_prompt("sample.py", "test_sample.py", version_summary, history, failed_tests, user_instruction)
        gpt_response = call_gpt(prompt)
        code, reason = extract_code_and_reason(gpt_response)

        save_file(SAMPLE_FILE, code)
        save_patch_history(code, reason, prompt)

        result = run_pytest()
        print("🧪 テスト結果:\n", result)

        if "failed" not in result.lower():
            print(f"\n✅ テストに成功しました（{retry_count+1} 回目）")
            break
        else:
            print("❌ テスト失敗、再修正を試みます…")

        retry_count += 1

    if retry_count == MAX_RETRIES:
        print(f"\n⚠️ 最大試行回数 {MAX_RETRIES} に達しました。テスト未合格。")

if __name__ == "__main__":
    # 任意で命令文を指定可能（なければ空文字）
    user_instruction = "assert文を満たすよう修正してください"
    auto_loop(user_instruction)

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\gradio_app\auto_revision_runner.py ===
# auto_revision_runner.py
import os
import sys
import time
import json
from datetime import datetime
from revision_loop import generate_prompt, extract_code_and_reason, call_gpt, run_pytest, save_file, read_file, save_patch_history

SANDBOX_DIR = "../sandbox_output"
SAMPLE_FILE = os.path.join(SANDBOX_DIR, "sample.py")
TEST_FILE = os.path.join(SANDBOX_DIR, "test_sample.py")

MAX_RETRIES = 5

def auto_loop(user_instruction=""):
    retry_count = 0

    while retry_count < MAX_RETRIES:
        print(f"\n🔁 [Attempt {retry_count + 1}/{MAX_RETRIES}] Generating revision...")

        version_summary = f"自動反復試行 {retry_count + 1} 回目"
        history = f"試行回数: {retry_count}"
        failed_tests = read_file(os.path.join(SANDBOX_DIR, "test_result.log")) if os.path.exists(os.path.join(SANDBOX_DIR, "test_result.log")) else ""

        prompt = generate_prompt("sample.py", "test_sample.py", version_summary, history, failed_tests, user_instruction)
        gpt_response = call_gpt(prompt)
        code, reason = extract_code_and_reason(gpt_response)

        save_file(SAMPLE_FILE, code)
        save_patch_history(code, reason, prompt)

        result = run_pytest()
        print("🧪 テスト結果:\n", result)

        if "failed" not in result.lower():
            print(f"\n✅ テストに成功しました（{retry_count+1} 回目）")
            break
        else:
            print("❌ テスト失敗、再修正を試みます…")

        retry_count += 1

    if retry_count == MAX_RETRIES:
        print(f"\n⚠️ 最大試行回数 {MAX_RETRIES} に達しました。テスト未合格。")

if __name__ == "__main__":
    # 任意で命令文を指定可能（なければ空文字）
    user_instruction = "assert文を満たすよう修正してください"
    auto_loop(user_instruction)

# === NexusCore/my-crm-app\app\__init__.py ===
# ==============================================================================
# フォルダ: my-crm-app/app
# ファイル名: __init__.py
# メモ: アプリケーションの心臓部。ハードコードされた設定を排除し、
#      config.pyからすべての設定を読み込むように修正。
#      これにより、設定の一元管理アーキテクチャが完成します。
# ==============================================================================
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# --- ★★★ ここからが最重要修正点 ★★★ ---
# 1. 親ディレクトリにあるconfig.pyからConfigクラスをインポート
from config import Config
# --- ★★★ ここまで ★★★ ---

# SQLAlchemyのインスタンスを作成
db = SQLAlchemy()

def create_app(config_class=Config):
    """
    アプリケーションファクトリ関数。
    Flaskアプリケーションのインスタンスを生成し、設定を読み込み、
    拡張機能とブループリントを初期化します。
    """
    app = Flask(__name__, instance_relative_config=True)

    # --- ★★★ ここからが最重要修正点 ★★★ ---
    # 2. config.pyのConfigクラスから設定を読み込む
    app.config.from_object(config_class)
    # --- ★★★ ここまで ★★★ ---

    # instanceフォルダが存在することを確認（DBファイルなどが保存される）
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # 拡張機能（データベース）をアプリケーションに登録
    db.init_app(app)

    # --- ★★★ ここからが最重要修正点 ★★★ ---
    # 3. routes.pyで定義したBlueprintをアプリケーションに登録
    from . import routes
    app.register_blueprint(routes.bp)
    # --- ★★★ ここまで ★★★ ---
    
    return app

# === NexusCore/src\code_interpreter\gradio_test_runner.py ===
import os
import subprocess

def save_test_and_run(test_code: str, filename: str = "test_sample.py", work_dir: str = "."):
    """
    `test_code`を指定されたディレクトリに保存し、その後pytestで自動実行します。

    Parameters:
    - test_code (str): 保存するテストコード（pytest形式）
    - filename (str): 保存するファイル名（デフォルト: test_sample.py）
    - work_dir (str): 保存・実行するディレクトリパス（デフォルト: カレント）

    Returns:
    - dict: {'file': ファイルパス, 'result': pytest実行結果, 'exit_code': 終了コード}
    """
    filepath = os.path.join(work_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(test_code)

    print(f"✅ テストコードを {filepath} に保存しました。")

    try:
        result = subprocess.run(
            ["pytest", filename],
            cwd=work_dir,
            capture_output=True,
            text=True
        )
        print("🧪 pytest 実行結果:")
        print(result.stdout)
        if result.stderr:
            print("⚠️ stderr:")
            print(result.stderr)

        return {
            "file": filepath,
            "result": result.stdout,
            "exit_code": result.returncode
        }

    except Exception as e:
        print(f"❌ エラー: {e}")
        return {
            "file": filepath,
            "result": str(e),
            "exit_code": -1
        }

# === NexusCore/src\utils\vcs.py ===
import git
from datetime import datetime

class GitController:
    """
    Gitリポジトリの操作を管理するクラス。
    """
    def __init__(self, repo_path='.'):
        """
        指定されたパスのリポジトリを初期化します。
        リポジトリが存在しない場合はエラーを送出します。
        """
        try:
            self.repo = git.Repo(repo_path, search_parent_directories=True)
            print(f"✅ Gitリポジトリを正常に読み込みました: {self.repo.working_dir}")
        except git.InvalidGitRepositoryError:
            print(f"❌ エラー: '{repo_path}' は有効なGitリポジトリではありません。")
            # プロジェクトをGitで初期化することも可能
            # self.repo = git.Repo.init(repo_path)
            # print(f"リポジトリを新規作成しました: {repo_path}")
            raise

    def commit_changes(self, file_paths: list, message: str) -> str | None:
        """
        指定されたファイルをステージングし、コミットします。
        
        Args:
            file_paths: コミット対象のファイルパスのリスト。
            message: コミットメッセージ。
        
        Returns:
            成功した場合はコミットハッシュ、失敗した場合はNone。
        """
        try:
            # ファイルの変更があるか確認
            if not self.repo.is_dirty(path=file_paths):
                print("ℹ️ コミット対象のファイルの変更がありません。")
                return None

            print(f"以下のファイルをステージングします: {file_paths}")
            self.repo.index.add(file_paths)
            
            commit = self.repo.index.commit(message)
            print(f"✅ 正常にコミットされました: {commit.hexsha}")
            return commit.hexsha
        except Exception as e:
            print(f"❌ Gitコミット中にエラーが発生しました: {e}")
            return None

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\my-crm-app\app\__init__.py ===
# ==============================================================================
# フォルダ: my-crm-app/app
# ファイル名: __init__.py
# メモ: アプリケーションの心臓部。ハードコードされた設定を排除し、
#      config.pyからすべての設定を読み込むように修正。
#      これにより、設定の一元管理アーキテクチャが完成します。
# ==============================================================================
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# --- ★★★ ここからが最重要修正点 ★★★ ---
# 1. 親ディレクトリにあるconfig.pyからConfigクラスをインポート
from config import Config
# --- ★★★ ここまで ★★★ ---

# SQLAlchemyのインスタンスを作成
db = SQLAlchemy()

def create_app(config_class=Config):
    """
    アプリケーションファクトリ関数。
    Flaskアプリケーションのインスタンスを生成し、設定を読み込み、
    拡張機能とブループリントを初期化します。
    """
    app = Flask(__name__, instance_relative_config=True)

    # --- ★★★ ここからが最重要修正点 ★★★ ---
    # 2. config.pyのConfigクラスから設定を読み込む
    app.config.from_object(config_class)
    # --- ★★★ ここまで ★★★ ---

    # instanceフォルダが存在することを確認（DBファイルなどが保存される）
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # 拡張機能（データベース）をアプリケーションに登録
    db.init_app(app)

    # --- ★★★ ここからが最重要修正点 ★★★ ---
    # 3. routes.pyで定義したBlueprintをアプリケーションに登録
    from . import routes
    app.register_blueprint(routes.bp)
    # --- ★★★ ここまで ★★★ ---
    
    return app

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\code_interpreter\gradio_test_runner.py ===
import os
import subprocess

def save_test_and_run(test_code: str, filename: str = "test_sample.py", work_dir: str = "."):
    """
    `test_code`を指定されたディレクトリに保存し、その後pytestで自動実行します。

    Parameters:
    - test_code (str): 保存するテストコード（pytest形式）
    - filename (str): 保存するファイル名（デフォルト: test_sample.py）
    - work_dir (str): 保存・実行するディレクトリパス（デフォルト: カレント）

    Returns:
    - dict: {'file': ファイルパス, 'result': pytest実行結果, 'exit_code': 終了コード}
    """
    filepath = os.path.join(work_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(test_code)

    print(f"✅ テストコードを {filepath} に保存しました。")

    try:
        result = subprocess.run(
            ["pytest", filename],
            cwd=work_dir,
            capture_output=True,
            text=True
        )
        print("🧪 pytest 実行結果:")
        print(result.stdout)
        if result.stderr:
            print("⚠️ stderr:")
            print(result.stderr)

        return {
            "file": filepath,
            "result": result.stdout,
            "exit_code": result.returncode
        }

    except Exception as e:
        print(f"❌ エラー: {e}")
        return {
            "file": filepath,
            "result": str(e),
            "exit_code": -1
        }

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\utils\vcs.py ===
import git
from datetime import datetime

class GitController:
    """
    Gitリポジトリの操作を管理するクラス。
    """
    def __init__(self, repo_path='.'):
        """
        指定されたパスのリポジトリを初期化します。
        リポジトリが存在しない場合はエラーを送出します。
        """
        try:
            self.repo = git.Repo(repo_path, search_parent_directories=True)
            print(f"✅ Gitリポジトリを正常に読み込みました: {self.repo.working_dir}")
        except git.InvalidGitRepositoryError:
            print(f"❌ エラー: '{repo_path}' は有効なGitリポジトリではありません。")
            # プロジェクトをGitで初期化することも可能
            # self.repo = git.Repo.init(repo_path)
            # print(f"リポジトリを新規作成しました: {repo_path}")
            raise

    def commit_changes(self, file_paths: list, message: str) -> str | None:
        """
        指定されたファイルをステージングし、コミットします。
        
        Args:
            file_paths: コミット対象のファイルパスのリスト。
            message: コミットメッセージ。
        
        Returns:
            成功した場合はコミットハッシュ、失敗した場合はNone。
        """
        try:
            # ファイルの変更があるか確認
            if not self.repo.is_dirty(path=file_paths):
                print("ℹ️ コミット対象のファイルの変更がありません。")
                return None

            print(f"以下のファイルをステージングします: {file_paths}")
            self.repo.index.add(file_paths)
            
            commit = self.repo.index.commit(message)
            print(f"✅ 正常にコミットされました: {commit.hexsha}")
            return commit.hexsha
        except Exception as e:
            print(f"❌ Gitコミット中にエラーが発生しました: {e}")
            return None

# === NexusCore/openenv\Lib\site-packages\win32\lib\commctrl.py ===
# Generated by h2py from CommCtrl.h
WM_USER = 1024
ICC_LISTVIEW_CLASSES = 1  # listview, header
ICC_TREEVIEW_CLASSES = 2  # treeview, tooltips
ICC_BAR_CLASSES = 4  # toolbar, statusbar, trackbar, tooltips
ICC_TAB_CLASSES = 8  # tab, tooltips
ICC_UPDOWN_CLASS = 16  # updown
ICC_PROGRESS_CLASS = 32  # progress
ICC_HOTKEY_CLASS = 64  # hotkey
ICC_ANIMATE_CLASS = 128  # animate
ICC_WIN95_CLASSES = 255
ICC_DATE_CLASSES = 256  # month picker, date picker, time picker, updown
ICC_USEREX_CLASSES = 512  # comboex
ICC_COOL_CLASSES = 1024  # rebar (coolbar) control
ICC_INTERNET_CLASSES = 2048
ICC_PAGESCROLLER_CLASS = 4096  # page scroller
ICC_NATIVEFNTCTL_CLASS = 8192  # native font control
ODT_HEADER = 100
ODT_TAB = 101
ODT_LISTVIEW = 102
PY_0U = 0
NM_FIRST = PY_0U  # generic to all controls
NM_LAST = PY_0U - 99
LVN_FIRST = PY_0U - 100  # listview
LVN_LAST = PY_0U - 199
HDN_FIRST = PY_0U - 300  # header
HDN_LAST = PY_0U - 399
TVN_FIRST = PY_0U - 400  # treeview
TVN_LAST = PY_0U - 499
TTN_FIRST = PY_0U - 520  # tooltips
TTN_LAST = PY_0U - 549
TCN_FIRST = PY_0U - 550  # tab control
TCN_LAST = PY_0U - 580
CDN_FIRST = PY_0U - 601  # common dialog (new)
CDN_LAST = PY_0U - 699
TBN_FIRST = PY_0U - 700  # toolbar
TBN_LAST = PY_0U - 720
UDN_FIRST = PY_0U - 721  # updown
UDN_LAST = PY_0U - 740
MCN_FIRST = PY_0U - 750  # monthcal
MCN_LAST = PY_0U - 759
DTN_FIRST = PY_0U - 760  # datetimepick
DTN_LAST = PY_0U - 799
CBEN_FIRST = PY_0U - 800  # combo box ex
CBEN_LAST = PY_0U - 830
RBN_FIRST = PY_0U - 831  # rebar
RBN_LAST = PY_0U - 859
IPN_FIRST = PY_0U - 860  # internet address
IPN_LAST = PY_0U - 879  # internet address
SBN_FIRST = PY_0U - 880  # status bar
SBN_LAST = PY_0U - 899
PGN_FIRST = PY_0U - 900  # Pager Control
PGN_LAST = PY_0U - 950
LVM_FIRST = 4096  # ListView messages
TV_FIRST = 4352  # TreeView messages
HDM_FIRST = 4608  # Header messages
TCM_FIRST = 4864  # Tab control messages
PGM_FIRST = 5120  # Pager control messages
CCM_FIRST = 8192  # Common control shared messages
CCM_SETBKCOLOR = CCM_FIRST + 1  # lParam is bkColor
CCM_SETCOLORSCHEME = CCM_FIRST + 2  # lParam is color scheme
CCM_GETCOLORSCHEME = CCM_FIRST + 3  # fills in COLORSCHEME pointed to by lParam
CCM_GETDROPTARGET = CCM_FIRST + 4
CCM_SETUNICODEFORMAT = CCM_FIRST + 5
CCM_GETUNICODEFORMAT = CCM_FIRST + 6
INFOTIPSIZE = 1024
NM_OUTOFMEMORY = NM_FIRST - 1
NM_CLICK = NM_FIRST - 2  # uses NMCLICK struct
NM_DBLCLK = NM_FIRST - 3
NM_RETURN = NM_FIRST - 4
NM_RCLICK = NM_FIRST - 5  # uses NMCLICK struct
NM_RDBLCLK = NM_FIRST - 6
NM_SETFOCUS = NM_FIRST - 7
NM_KILLFOCUS = NM_FIRST - 8
NM_CUSTOMDRAW = NM_FIRST - 12
NM_HOVER = NM_FIRST - 13
NM_NCHITTEST = NM_FIRST - 14  # uses NMMOUSE struct
NM_KEYDOWN = NM_FIRST - 15  # uses NMKEY struct
NM_RELEASEDCAPTURE = NM_FIRST - 16
NM_SETCURSOR = NM_FIRST - 17  # uses NMMOUSE struct
NM_CHAR = NM_FIRST - 18  # uses NMCHAR struct
MSGF_COMMCTRL_BEGINDRAG = 16896
MSGF_COMMCTRL_SIZEHEADER = 16897
MSGF_COMMCTRL_DRAGSELECT = 16898
MSGF_COMMCTRL_TOOLBARCUST = 16899
CDRF_DODEFAULT = 0
CDRF_NEWFONT = 2
CDRF_SKIPDEFAULT = 4
CDRF_NOTIFYPOSTPAINT = 16
CDRF_NOTIFYITEMDRAW = 32
CDRF_NOTIFYSUBITEMDRAW = 32  # flags are the same, we can distinguish by context
CDRF_NOTIFYPOSTERASE = 64
CDDS_PREPAINT = 1
CDDS_POSTPAINT = 2
CDDS_PREERASE = 3
CDDS_POSTERASE = 4
CDDS_ITEM = 65536
CDDS_ITEMPREPAINT = CDDS_ITEM | CDDS_PREPAINT
CDDS_ITEMPOSTPAINT = CDDS_ITEM | CDDS_POSTPAINT
CDDS_ITEMPREERASE = CDDS_ITEM | CDDS_PREERASE
CDDS_ITEMPOSTERASE = CDDS_ITEM | CDDS_POSTERASE
CDDS_SUBITEM = 131072
CDIS_SELECTED = 1
CDIS_GRAYED = 2
CDIS_DISABLED = 4
CDIS_CHECKED = 8
CDIS_FOCUS = 16
CDIS_DEFAULT = 32
CDIS_HOT = 64
CDIS_MARKED = 128
CDIS_INDETERMINATE = 256
CLR_NONE = -1  # 0xFFFFFFFFL
CLR_DEFAULT = -16777216  # 0xFF000000L
ILC_MASK = 1
ILC_COLOR = 0
ILC_COLORDDB = 254
ILC_COLOR4 = 4
ILC_COLOR8 = 8
ILC_COLOR16 = 16
ILC_COLOR24 = 24
ILC_COLOR32 = 32
ILC_PALETTE = 2048  # (not implemented)
ILD_NORMAL = 0
ILD_TRANSPARENT = 1
ILD_MASK = 16
ILD_IMAGE = 32
ILD_ROP = 64
ILD_BLEND25 = 2
ILD_BLEND50 = 4
ILD_OVERLAYMASK = 3840
ILD_SELECTED = ILD_BLEND50
ILD_FOCUS = ILD_BLEND25
ILD_BLEND = ILD_BLEND50
CLR_HILIGHT = CLR_DEFAULT
ILCF_MOVE = 0
ILCF_SWAP = 1
WC_HEADERA = "SysHeader32"
WC_HEADER = WC_HEADERA
HDS_HORZ = 0
HDS_BUTTONS = 2
HDS_HOTTRACK = 4
HDS_HIDDEN = 8
HDS_DRAGDROP = 64
HDS_FULLDRAG = 128
HDI_WIDTH = 1
HDI_HEIGHT = HDI_WIDTH
HDI_TEXT = 2
HDI_FORMAT = 4
HDI_LPARAM = 8
HDI_BITMAP = 16
HDI_IMAGE = 32
HDI_DI_SETITEM = 64
HDI_ORDER = 128
HDF_LEFT = 0
HDF_RIGHT = 1
HDF_CENTER = 2
HDF_JUSTIFYMASK = 3
HDF_RTLREADING = 4
HDF_OWNERDRAW = 32768
HDF_STRING = 16384
HDF_BITMAP = 8192
HDF_BITMAP_ON_RIGHT = 4096
HDF_IMAGE = 2048
HDM_GETITEMCOUNT = HDM_FIRST + 0
HDM_INSERTITEMA = HDM_FIRST + 1
HDM_INSERTITEMW = HDM_FIRST + 10
HDM_INSERTITEM = HDM_INSERTITEMA
HDM_DELETEITEM = HDM_FIRST + 2
HDM_GETITEMA = HDM_FIRST + 3
HDM_GETITEMW = HDM_FIRST + 11
HDM_GETITEM = HDM_GETITEMA
HDM_SETITEMA = HDM_FIRST + 4
HDM_SETITEMW = HDM_FIRST + 12
HDM_SETITEM = HDM_SETITEMA
HDM_LAYOUT = HDM_FIRST + 5
HHT_NOWHERE = 1
HHT_ONHEADER = 2
HHT_ONDIVIDER = 4
HHT_ONDIVOPEN = 8
HHT_ABOVE = 256
HHT_BELOW = 512
HHT_TORIGHT = 1024
HHT_TOLEFT = 2048
HDM_HITTEST = HDM_FIRST + 6
HDM_GETITEMRECT = HDM_FIRST + 7
HDM_SETIMAGELIST = HDM_FIRST + 8
HDM_GETIMAGELIST = HDM_FIRST + 9
HDM_ORDERTOINDEX = HDM_FIRST + 15
HDM_CREATEDRAGIMAGE = HDM_FIRST + 16  # wparam = which item (by index)
HDM_GETORDERARRAY = HDM_FIRST + 17
HDM_SETORDERARRAY = HDM_FIRST + 18
HDM_SETHOTDIVIDER = HDM_FIRST + 19
HDM_SETUNICODEFORMAT = CCM_SETUNICODEFORMAT
HDM_GETUNICODEFORMAT = CCM_GETUNICODEFORMAT
HDN_ITEMCHANGINGA = HDN_FIRST - 0
HDN_ITEMCHANGINGW = HDN_FIRST - 20
HDN_ITEMCHANGEDA = HDN_FIRST - 1
HDN_ITEMCHANGEDW = HDN_FIRST - 21
HDN_ITEMCLICKA = HDN_FIRST - 2
HDN_ITEMCLICKW = HDN_FIRST - 22
HDN_ITEMDBLCLICKA = HDN_FIRST - 3
HDN_ITEMDBLCLICKW = HDN_FIRST - 23
HDN_DIVIDERDBLCLICKA = HDN_FIRST - 5
HDN_DIVIDERDBLCLICKW = HDN_FIRST - 25
HDN_BEGINTRACKA = HDN_FIRST - 6
HDN_BEGINTRACKW = HDN_FIRST - 26
HDN_ENDTRACKA = HDN_FIRST - 7
HDN_ENDTRACKW = HDN_FIRST - 27
HDN_TRACKA = HDN_FIRST - 8
HDN_TRACKW = HDN_FIRST - 28
HDN_GETDISPINFOA = HDN_FIRST - 9
HDN_GETDISPINFOW = HDN_FIRST - 29
HDN_BEGINDRAG = HDN_FIRST - 10
HDN_ENDDRAG = HDN_FIRST - 11
HDN_ITEMCHANGING = HDN_ITEMCHANGINGA
HDN_ITEMCHANGED = HDN_ITEMCHANGEDA
HDN_ITEMCLICK = HDN_ITEMCLICKA
HDN_ITEMDBLCLICK = HDN_ITEMDBLCLICKA
HDN_DIVIDERDBLCLICK = HDN_DIVIDERDBLCLICKA
HDN_BEGINTRACK = HDN_BEGINTRACKA
HDN_ENDTRACK = HDN_ENDTRACKA
HDN_TRACK = HDN_TRACKA
HDN_GETDISPINFO = HDN_GETDISPINFOA
TOOLBARCLASSNAMEA = "ToolbarWindow32"
TOOLBARCLASSNAME = TOOLBARCLASSNAMEA
CMB_MASKED = 2
TBSTATE_CHECKED = 1
TBSTATE_PRESSED = 2
TBSTATE_ENABLED = 4
TBSTATE_HIDDEN = 8
TBSTATE_INDETERMINATE = 16
TBSTATE_WRAP = 32
TBSTATE_ELLIPSES = 64
TBSTATE_MARKED = 128
TBSTYLE_BUTTON = 0
TBSTYLE_SEP = 1
TBSTYLE_CHECK = 2
TBSTYLE_GROUP = 4
TBSTYLE_CHECKGROUP = TBSTYLE_GROUP | TBSTYLE_CHECK
TBSTYLE_DROPDOWN = 8
TBSTYLE_AUTOSIZE = 16  # automatically calculate the cx of the button
TBSTYLE_NOPREFIX = 32  # if this button should not have accel prefix
TBSTYLE_TOOLTIPS = 256
TBSTYLE_WRAPABLE = 512
TBSTYLE_ALTDRAG = 1024
TBSTYLE_FLAT = 2048
TBSTYLE_LIST = 4096
TBSTYLE_CUSTOMERASE = 8192
TBSTYLE_REGISTERDROP = 16384
TBSTYLE_TRANSPARENT = 32768
TBSTYLE_EX_DRAWDDARROWS = 1
BTNS_BUTTON = TBSTYLE_BUTTON
BTNS_SEP = TBSTYLE_SEP  # 0x0001
BTNS_CHECK = TBSTYLE_CHECK  # 0x0002
BTNS_GROUP = TBSTYLE_GROUP  # 0x0004
BTNS_CHECKGROUP = TBSTYLE_CHECKGROUP  # (TBSTYLE_GROUP | TBSTYLE_CHECK)
BTNS_DROPDOWN = TBSTYLE_DROPDOWN  # 0x0008
BTNS_AUTOSIZE = TBSTYLE_AUTOSIZE  # 0x0010; automatically calculate the cx of the button
BTNS_NOPREFIX = TBSTYLE_NOPREFIX  # 0x0020; this button should not have accel prefix
BTNS_SHOWTEXT = (
    64  # 0x0040              // ignored unless TBSTYLE_EX_MIXEDBUTTONS is set
)
BTNS_WHOLEDROPDOWN = (
    128  # 0x0080          // draw drop-down arrow, but without split arrow section
)
TBCDRF_NOEDGES = 65536  # Don't draw button edges
TBCDRF_HILITEHOTTRACK = 131072  # Use color of the button bk when hottracked
TBCDRF_NOOFFSET = 262144  # Don't offset button if pressed
TBCDRF_NOMARK = 524288  # Don't draw default highlight of image/text for TBSTATE_MARKED
TBCDRF_NOETCHEDEFFECT = 1048576  # Don't draw etched effect for disabled items
TB_ENABLEBUTTON = WM_USER + 1
TB_CHECKBUTTON = WM_USER + 2
TB_PRESSBUTTON = WM_USER + 3
TB_HIDEBUTTON = WM_USER + 4
TB_INDETERMINATE = WM_USER + 5
TB_MARKBUTTON = WM_USER + 6
TB_ISBUTTONENABLED = WM_USER + 9
TB_ISBUTTONCHECKED = WM_USER + 10
TB_ISBUTTONPRESSED = WM_USER + 11
TB_ISBUTTONHIDDEN = WM_USER + 12
TB_ISBUTTONINDETERMINATE = WM_USER + 13
TB_ISBUTTONHIGHLIGHTED = WM_USER + 14
TB_SETSTATE = WM_USER + 17
TB_GETSTATE = WM_USER + 18
TB_ADDBITMAP = WM_USER + 19
HINST_COMMCTRL = -1
IDB_STD_SMALL_COLOR = 0
IDB_STD_LARGE_COLOR = 1
IDB_VIEW_SMALL_COLOR = 4
IDB_VIEW_LARGE_COLOR = 5
IDB_HIST_SMALL_COLOR = 8
IDB_HIST_LARGE_COLOR = 9
STD_CUT = 0
STD_COPY = 1
STD_PASTE = 2
STD_UNDO = 3
STD_REDOW = 4
STD_DELETE = 5
STD_FILENEW = 6
STD_FILEOPEN = 7
STD_FILESAVE = 8
STD_PRINTPRE = 9
STD_PROPERTIES = 10
STD_HELP = 11
STD_FIND = 12
STD_REPLACE = 13
STD_PRINT = 14
VIEW_LARGEICONS = 0
VIEW_SMALLICONS = 1
VIEW_LIST = 2
VIEW_DETAILS = 3
VIEW_SORTNAME = 4
VIEW_SORTSIZE = 5
VIEW_SORTDATE = 6
VIEW_SORTTYPE = 7
VIEW_PARENTFOLDER = 8
VIEW_NETCONNECT = 9
VIEW_NETDISCONNECT = 10
VIEW_NEWFOLDER = 11
VIEW_VIEWMENU = 12
HIST_BACK = 0
HIST_FORWARD = 1
HIST_FAVORITES = 2
HIST_ADDTOFAVORITES = 3
HIST_VIEWTREE = 4
TB_ADDBUTTONSA = WM_USER + 20
TB_INSERTBUTTONA = WM_USER + 21
TB_ADDBUTTONS = WM_USER + 20
TB_INSERTBUTTON = WM_USER + 21
TB_DELETEBUTTON = WM_USER + 22
TB_GETBUTTON = WM_USER + 23
TB_BUTTONCOUNT = WM_USER + 24
TB_COMMANDTOINDEX = WM_USER + 25
TB_SAVERESTOREA = WM_USER + 26
TB_SAVERESTOREW = WM_USER + 76
TB_CUSTOMIZE = WM_USER + 27
TB_ADDSTRINGA = WM_USER + 28
TB_ADDSTRINGW = WM_USER + 77
TB_GETITEMRECT = WM_USER + 29
TB_BUTTONSTRUCTSIZE = WM_USER + 30
TB_SETBUTTONSIZE = WM_USER + 31
TB_SETBITMAPSIZE = WM_USER + 32
TB_AUTOSIZE = WM_USER + 33
TB_GETTOOLTIPS = WM_USER + 35
TB_SETTOOLTIPS = WM_USER + 36
TB_SETPARENT = WM_USER + 37
TB_SETROWS = WM_USER + 39
TB_GETROWS = WM_USER + 40
TB_SETCMDID = WM_USER + 42
TB_CHANGEBITMAP = WM_USER + 43
TB_GETBITMAP = WM_USER + 44
TB_GETBUTTONTEXTA = WM_USER + 45
TB_GETBUTTONTEXTW = WM_USER + 75
TB_REPLACEBITMAP = WM_USER + 46
TB_SETINDENT = WM_USER + 47
TB_SETIMAGELIST = WM_USER + 48
TB_GETIMAGELIST = WM_USER + 49
TB_LOADIMAGES = WM_USER + 50
TB_GETRECT = WM_USER + 51  # wParam is the Cmd instead of index
TB_SETHOTIMAGELIST = WM_USER + 52
TB_GETHOTIMAGELIST = WM_USER + 53
TB_SETDISABLEDIMAGELIST = WM_USER + 54
TB_GETDISABLEDIMAGELIST = WM_USER + 55
TB_SETSTYLE = WM_USER + 56
TB_GETSTYLE = WM_USER + 57
TB_GETBUTTONSIZE = WM_USER + 58
TB_SETBUTTONWIDTH = WM_USER + 59
TB_SETMAXTEXTROWS = WM_USER + 60
TB_GETTEXTROWS = WM_USER + 61
TB_GETBUTTONTEXT = TB_GETBUTTONTEXTA
TB_SAVERESTORE = TB_SAVERESTOREA
TB_ADDSTRING = TB_ADDSTRINGA
TB_GETOBJECT = WM_USER + 62  # wParam == IID, lParam void **ppv
TB_GETHOTITEM = WM_USER + 71
TB_SETHOTITEM = WM_USER + 72  # wParam == iHotItem
TB_SETANCHORHIGHLIGHT = WM_USER + 73  # wParam == TRUE/FALSE
TB_GETANCHORHIGHLIGHT = WM_USER + 74
TB_MAPACCELERATORA = WM_USER + 78  # wParam == ch, lParam int * pidBtn
TBIMHT_AFTER = 1  # TRUE = insert After iButton, otherwise before
TBIMHT_BACKGROUND = 2  # TRUE iff missed buttons completely
TB_GETINSERTMARK = WM_USER + 79  # lParam == LPTBINSERTMARK
TB_SETINSERTMARK = WM_USER + 80  # lParam == LPTBINSERTMARK
TB_INSERTMARKHITTEST = WM_USER + 81  # wParam == LPPOINT lParam == LPTBINSERTMARK
TB_MOVEBUTTON = WM_USER + 82
TB_GETMAXSIZE = WM_USER + 83  # lParam == LPSIZE
TB_SETEXTENDEDSTYLE = WM_USER + 84  # For TBSTYLE_EX_*
TB_GETEXTENDEDSTYLE = WM_USER + 85  # For TBSTYLE_EX_*
TB_GETPADDING = WM_USER + 86
TB_SETPADDING = WM_USER + 87
TB_SETINSERTMARKCOLOR = WM_USER + 88
TB_GETINSERTMARKCOLOR = WM_USER + 89
TB_SETCOLORSCHEME = CCM_SETCOLORSCHEME  # lParam is color scheme
TB_GETCOLORSCHEME = CCM_GETCOLORSCHEME  # fills in COLORSCHEME pointed to by lParam
TB_SETUNICODEFORMAT = CCM_SETUNICODEFORMAT
TB_GETUNICODEFORMAT = CCM_GETUNICODEFORMAT
TB_MAPACCELERATORW = WM_USER + 90  # wParam == ch, lParam int * pidBtn
TB_MAPACCELERATOR = TB_MAPACCELERATORA
TBBF_LARGE = 1
TB_GETBITMAPFLAGS = WM_USER + 41
TBIF_IMAGE = 1
TBIF_TEXT = 2
TBIF_STATE = 4
TBIF_STYLE = 8
TBIF_LPARAM = 16
TBIF_COMMAND = 32
TBIF_SIZE = 64
TB_GETBUTTONINFOW = WM_USER + 63
TB_SETBUTTONINFOW = WM_USER + 64
TB_GETBUTTONINFOA = WM_USER + 65
TB_SETBUTTONINFOA = WM_USER + 66
TB_INSERTBUTTONW = WM_USER + 67
TB_ADDBUTTONSW = WM_USER + 68
TB_HITTEST = WM_USER + 69
TB_SETDRAWTEXTFLAGS = WM_USER + 70  # wParam == mask lParam == bit values
TBN_GETBUTTONINFOA = TBN_FIRST - 0
TBN_GETBUTTONINFOW = TBN_FIRST - 20
TBN_BEGINDRAG = TBN_FIRST - 1
TBN_ENDDRAG = TBN_FIRST - 2
TBN_BEGINADJUST = TBN_FIRST - 3
TBN_ENDADJUST = TBN_FIRST - 4
TBN_RESET = TBN_FIRST - 5
TBN_QUERYINSERT = TBN_FIRST - 6
TBN_QUERYDELETE = TBN_FIRST - 7
TBN_TOOLBARCHANGE = TBN_FIRST - 8
TBN_CUSTHELP = TBN_FIRST - 9
TBN_DROPDOWN = TBN_FIRST - 10
TBN_GETOBJECT = TBN_FIRST - 12
HICF_OTHER = 0
HICF_MOUSE = 1  # Triggered by mouse
HICF_ARROWKEYS = 2  # Triggered by arrow keys
HICF_ACCELERATOR = 4  # Triggered by accelerator
HICF_DUPACCEL = 8  # This accelerator is not unique
HICF_ENTERING = 16  # idOld is invalid
HICF_LEAVING = 32  # idNew is invalid
HICF_RESELECT = 64  # hot item reselected
TBN_HOTITEMCHANGE = TBN_FIRST - 13
TBN_DRAGOUT = (
    TBN_FIRST - 14
)  # this is sent when the user clicks down on a button then drags off the button
TBN_DELETINGBUTTON = TBN_FIRST - 15  # uses TBNOTIFY
TBN_GETDISPINFOA = (
    TBN_FIRST - 16
)  # This is sent when the  toolbar needs  some display information
TBN_GETDISPINFOW = (
    TBN_FIRST - 17
)  # This is sent when the  toolbar needs  some display information
TBN_GETINFOTIPA = TBN_FIRST - 18
TBN_GETINFOTIPW = TBN_FIRST - 19
TBN_GETINFOTIP = TBN_GETINFOTIPA
TBNF_IMAGE = 1
TBNF_TEXT = 2
TBNF_DI_SETITEM = 268435456
TBN_GETDISPINFO = TBN_GETDISPINFOA
TBDDRET_DEFAULT = 0
TBDDRET_NODEFAULT = 1
TBDDRET_TREATPRESSED = 2  # Treat as a standard press button
TBN_GETBUTTONINFO = TBN_GETBUTTONINFOA
REBARCLASSNAMEA = "ReBarWindow32"
REBARCLASSNAME = REBARCLASSNAMEA
RBIM_IMAGELIST = 1
RBS_TOOLTIPS = 256
RBS_VARHEIGHT = 512
RBS_BANDBORDERS = 1024
RBS_FIXEDORDER = 2048
RBS_REGISTERDROP = 4096
RBS_AUTOSIZE = 8192
RBS_VERTICALGRIPPER = (
    16384  # this always has the vertical gripper (default for horizontal mode)
)
RBS_DBLCLKTOGGLE = 32768
RBBS_BREAK = 1  # break to new line
RBBS_FIXEDSIZE = 2  # band can't be sized
RBBS_CHILDEDGE = 4  # edge around top & bottom of child window
RBBS_HIDDEN = 8  # don't show
RBBS_NOVERT = 16  # don't show when vertical
RBBS_FIXEDBMP = 32  # bitmap doesn't move during band resize
RBBS_VARIABLEHEIGHT = 64  # allow autosizing of this child vertically
RBBS_GRIPPERALWAYS = 128  # always show the gripper
RBBS_NOGRIPPER = 256  # never show the gripper
RBBIM_STYLE = 1
RBBIM_COLORS = 2
RBBIM_TEXT = 4
RBBIM_IMAGE = 8
RBBIM_CHILD = 16
RBBIM_CHILDSIZE = 32
RBBIM_SIZE = 64
RBBIM_BACKGROUND = 128
RBBIM_ID = 256
RBBIM_IDEALSIZE = 512
RBBIM_LPARAM = 1024
RB_INSERTBANDA = WM_USER + 1
RB_DELETEBAND = WM_USER + 2
RB_GETBARINFO = WM_USER + 3
RB_SETBARINFO = WM_USER + 4
RB_SETBANDINFOA = WM_USER + 6
RB_SETPARENT = WM_USER + 7
RB_HITTEST = WM_USER + 8
RB_GETRECT = WM_USER + 9
RB_INSERTBANDW = WM_USER + 10
RB_SETBANDINFOW = WM_USER + 11
RB_GETBANDCOUNT = WM_USER + 12
RB_GETROWCOUNT = WM_USER + 13
RB_GETROWHEIGHT = WM_USER + 14
RB_IDTOINDEX = WM_USER + 16  # wParam == id
RB_GETTOOLTIPS = WM_USER + 17
RB_SETTOOLTIPS = WM_USER + 18
RB_SETBKCOLOR = WM_USER + 19  # sets the default BK color
RB_GETBKCOLOR = WM_USER + 20  # defaults to CLR_NONE
RB_SETTEXTCOLOR = WM_USER + 21
RB_GETTEXTCOLOR = WM_USER + 22  # defaults to 0x00000000
RB_SIZETORECT = (
    WM_USER + 23
)  # resize the rebar/break bands and such to this rect (lparam)
RB_SETCOLORSCHEME = CCM_SETCOLORSCHEME  # lParam is color scheme
RB_GETCOLORSCHEME = CCM_GETCOLORSCHEME  # fills in COLORSCHEME pointed to by lParam
RB_INSERTBAND = RB_INSERTBANDA
RB_SETBANDINFO = RB_SETBANDINFOA
RB_BEGINDRAG = WM_USER + 24
RB_ENDDRAG = WM_USER + 25
RB_DRAGMOVE = WM_USER + 26
RB_GETBARHEIGHT = WM_USER + 27
RB_GETBANDINFOW = WM_USER + 28
RB_GETBANDINFOA = WM_USER + 29
RB_GETBANDINFO = RB_GETBANDINFOA
RB_MINIMIZEBAND = WM_USER + 30
RB_MAXIMIZEBAND = WM_USER + 31
RB_GETDROPTARGET = CCM_GETDROPTARGET
RB_GETBANDBORDERS = (
    WM_USER + 34
)  # returns in lparam = lprc the amount of edges added to band wparam
RB_SHOWBAND = WM_USER + 35  # show/hide band
RB_SETPALETTE = WM_USER + 37
RB_GETPALETTE = WM_USER + 38
RB_MOVEBAND = WM_USER + 39
RB_SETUNICODEFORMAT = CCM_SETUNICODEFORMAT
RB_GETUNICODEFORMAT = CCM_GETUNICODEFORMAT
RBN_HEIGHTCHANGE = RBN_FIRST - 0
RBN_GETOBJECT = RBN_FIRST - 1
RBN_LAYOUTCHANGED = RBN_FIRST - 2
RBN_AUTOSIZE = RBN_FIRST - 3
RBN_BEGINDRAG = RBN_FIRST - 4
RBN_ENDDRAG = RBN_FIRST - 5
RBN_DELETINGBAND = RBN_FIRST - 6  # Uses NMREBAR
RBN_DELETEDBAND = RBN_FIRST - 7  # Uses NMREBAR
RBN_CHILDSIZE = RBN_FIRST - 8
RBNM_ID = 1
RBNM_STYLE = 2
RBNM_LPARAM = 4
RBHT_NOWHERE = 1
RBHT_CAPTION = 2
RBHT_CLIENT = 3
RBHT_GRABBER = 4
TOOLTIPS_CLASSA = "tooltips_class32"
TOOLTIPS_CLASS = TOOLTIPS_CLASSA
TTS_ALWAYSTIP = 1
TTS_NOPREFIX = 2
TTF_IDISHWND = 1
TTF_CENTERTIP = 2
TTF_RTLREADING = 4
TTF_SUBCLASS = 16
TTF_TRACK = 32
TTF_ABSOLUTE = 128
TTF_TRANSPARENT = 256
TTF_DI_SETITEM = 32768  # valid only on the TTN_NEEDTEXT callback
TTDT_AUTOMATIC = 0
TTDT_RESHOW = 1
TTDT_AUTOPOP = 2
TTDT_INITIAL = 3
TTM_ACTIVATE = WM_USER + 1
TTM_SETDELAYTIME = WM_USER + 3
TTM_ADDTOOLA = WM_USER + 4
TTM_ADDTOOLW = WM_USER + 50
TTM_DELTOOLA = WM_USER + 5
TTM_DELTOOLW = WM_USER + 51
TTM_NEWTOOLRECTA = WM_USER + 6
TTM_NEWTOOLRECTW = WM_USER + 52
TTM_RELAYEVENT = WM_USER + 7
TTM_GETTOOLINFOA = WM_USER + 8
TTM_GETTOOLINFOW = WM_USER + 53
TTM_SETTOOLINFOA = WM_USER + 9
TTM_SETTOOLINFOW = WM_USER + 54
TTM_HITTESTA = WM_USER + 10
TTM_HITTESTW = WM_USER + 55
TTM_GETTEXTA = WM_USER + 11
TTM_GETTEXTW = WM_USER + 56
TTM_UPDATETIPTEXTA = WM_USER + 12
TTM_UPDATETIPTEXTW = WM_USER + 57
TTM_GETTOOLCOUNT = WM_USER + 13
TTM_ENUMTOOLSA = WM_USER + 14
TTM_ENUMTOOLSW = WM_USER + 58
TTM_GETCURRENTTOOLA = WM_USER + 15
TTM_GETCURRENTTOOLW = WM_USER + 59
TTM_WINDOWFROMPOINT = WM_USER + 16
TTM_TRACKACTIVATE = WM_USER + 17  # wParam = TRUE/FALSE start end  lparam = LPTOOLINFO
TTM_TRACKPOSITION = WM_USER + 18  # lParam = dwPos
TTM_SETTIPBKCOLOR = WM_USER + 19
TTM_SETTIPTEXTCOLOR = WM_USER + 20
TTM_GETDELAYTIME = WM_USER + 21
TTM_GETTIPBKCOLOR = WM_USER + 22
TTM_GETTIPTEXTCOLOR = WM_USER + 23
TTM_SETMAXTIPWIDTH = WM_USER + 24
TTM_GETMAXTIPWIDTH = WM_USER + 25
TTM_SETMARGIN = WM_USER + 26  # lParam = lprc
TTM_GETMARGIN = WM_USER + 27  # lParam = lprc
TTM_POP = WM_USER + 28
TTM_UPDATE = WM_USER + 29
TTM_ADDTOOL = TTM_ADDTOOLA
TTM_DELTOOL = TTM_DELTOOLA
TTM_NEWTOOLRECT = TTM_NEWTOOLRECTA
TTM_GETTOOLINFO = TTM_GETTOOLINFOA
TTM_SETTOOLINFO = TTM_SETTOOLINFOA
TTM_HITTEST = TTM_HITTESTA
TTM_GETTEXT = TTM_GETTEXTA
TTM_UPDATETIPTEXT = TTM_UPDATETIPTEXTA
TTM_ENUMTOOLS = TTM_ENUMTOOLSA
TTM_GETCURRENTTOOL = TTM_GETCURRENTTOOLA
TTN_GETDISPINFOA = TTN_FIRST - 0
TTN_GETDISPINFOW = TTN_FIRST - 10
TTN_SHOW = TTN_FIRST - 1
TTN_POP = TTN_FIRST - 2
TTN_GETDISPINFO = TTN_GETDISPINFOA
TTN_NEEDTEXT = TTN_GETDISPINFO
TTN_NEEDTEXTA = TTN_GETDISPINFOA
TTN_NEEDTEXTW = TTN_GETDISPINFOW
SBARS_SIZEGRIP = 256
SBARS_TOOLTIPS = 2048
STATUSCLASSNAMEA = "msctls_statusbar32"
STATUSCLASSNAME = STATUSCLASSNAMEA
SB_SETTEXTA = WM_USER + 1
SB_SETTEXTW = WM_USER + 11
SB_GETTEXTA = WM_USER + 2
SB_GETTEXTW = WM_USER + 13
SB_GETTEXTLENGTHA = WM_USER + 3
SB_GETTEXTLENGTHW = WM_USER + 12
SB_GETTEXT = SB_GETTEXTA
SB_SETTEXT = SB_SETTEXTA
SB_GETTEXTLENGTH = SB_GETTEXTLENGTHA
SB_SETPARTS = WM_USER + 4
SB_GETPARTS = WM_USER + 6
SB_GETBORDERS = WM_USER + 7
SB_SETMINHEIGHT = WM_USER + 8
SB_SIMPLE = WM_USER + 9
SB_GETRECT = WM_USER + 10
SB_ISSIMPLE = WM_USER + 14
SB_SETICON = WM_USER + 15
SB_SETTIPTEXTA = WM_USER + 16
SB_SETTIPTEXTW = WM_USER + 17
SB_GETTIPTEXTA = WM_USER + 18
SB_GETTIPTEXTW = WM_USER + 19
SB_GETICON = WM_USER + 20
SB_SETTIPTEXT = SB_SETTIPTEXTA
SB_GETTIPTEXT = SB_GETTIPTEXTA
SB_SETUNICODEFORMAT = CCM_SETUNICODEFORMAT
SB_GETUNICODEFORMAT = CCM_GETUNICODEFORMAT
SBT_OWNERDRAW = 4096
SBT_NOBORDERS = 256
SBT_POPOUT = 512
SBT_RTLREADING = 1024
SBT_NOTABPARSING = 2048
SBT_TOOLTIPS = 2048
SB_SETBKCOLOR = CCM_SETBKCOLOR  # lParam = bkColor
SBN_SIMPLEMODECHANGE = SBN_FIRST - 0
TRACKBAR_CLASSA = "msctls_trackbar32"
TRACKBAR_CLASS = TRACKBAR_CLASSA
TBS_AUTOTICKS = 1
TBS_VERT = 2
TBS_HORZ = 0
TBS_TOP = 4
TBS_BOTTOM = 0
TBS_LEFT = 4
TBS_RIGHT = 0
TBS_BOTH = 8
TBS_NOTICKS = 16
TBS_ENABLESELRANGE = 32
TBS_FIXEDLENGTH = 64
TBS_NOTHUMB = 128
TBS_TOOLTIPS = 256
TBM_GETPOS = WM_USER
TBM_GETRANGEMIN = WM_USER + 1
TBM_GETRANGEMAX = WM_USER + 2
TBM_GETTIC = WM_USER + 3
TBM_SETTIC = WM_USER + 4
TBM_SETPOS = WM_USER + 5
TBM_SETRANGE = WM_USER + 6
TBM_SETRANGEMIN = WM_USER + 7
TBM_SETRANGEMAX = WM_USER + 8
TBM_CLEARTICS = WM_USER + 9
TBM_SETSEL = WM_USER + 10
TBM_SETSELSTART = WM_USER + 11
TBM_SETSELEND = WM_USER + 12
TBM_GETPTICS = WM_USER + 14
TBM_GETTICPOS = WM_USER + 15
TBM_GETNUMTICS = WM_USER + 16
TBM_GETSELSTART = WM_USER + 17
TBM_GETSELEND = WM_USER + 18
TBM_CLEARSEL = WM_USER + 19
TBM_SETTICFREQ = WM_USER + 20
TBM_SETPAGESIZE = WM_USER + 21
TBM_GETPAGESIZE = WM_USER + 22
TBM_SETLINESIZE = WM_USER + 23
TBM_GETLINESIZE = WM_USER + 24
TBM_GETTHUMBRECT = WM_USER + 25
TBM_GETCHANNELRECT = WM_USER + 26
TBM_SETTHUMBLENGTH = WM_USER + 27
TBM_GETTHUMBLENGTH = WM_USER + 28
TBM_SETTOOLTIPS = WM_USER + 29
TBM_GETTOOLTIPS = WM_USER + 30
TBM_SETTIPSIDE = WM_USER + 31
TBTS_TOP = 0
TBTS_LEFT = 1
TBTS_BOTTOM = 2
TBTS_RIGHT = 3
TBM_SETBUDDY = WM_USER + 32  # wparam = BOOL fLeft; (or right)
TBM_GETBUDDY = WM_USER + 33  # wparam = BOOL fLeft; (or right)
TBM_SETUNICODEFORMAT = CCM_SETUNICODEFORMAT
TBM_GETUNICODEFORMAT = CCM_GETUNICODEFORMAT
TB_LINEUP = 0
TB_LINEDOWN = 1
TB_PAGEUP = 2
TB_PAGEDOWN = 3
TB_THUMBPOSITION = 4
TB_THUMBTRACK = 5
TB_TOP = 6
TB_BOTTOM = 7
TB_ENDTRACK = 8
TBCD_TICS = 1
TBCD_THUMB = 2
TBCD_CHANNEL = 3
DL_BEGINDRAG = WM_USER + 133
DL_DRAGGING = WM_USER + 134
DL_DROPPED = WM_USER + 135
DL_CANCELDRAG = WM_USER + 136
DL_CURSORSET = 0
DL_STOPCURSOR = 1
DL_COPYCURSOR = 2
DL_MOVECURSOR = 3
DRAGLISTMSGSTRING = "commctrl_DragListMsg"
UPDOWN_CLASSA = "msctls_updown32"
UPDOWN_CLASS = UPDOWN_CLASSA
UD_MAXVAL = 32767
UD_MINVAL = -UD_MAXVAL
UDS_WRAP = 1
UDS_SETBUDDYINT = 2
UDS_ALIGNRIGHT = 4
UDS_ALIGNLEFT = 8
UDS_AUTOBUDDY = 16
UDS_ARROWKEYS = 32
UDS_HORZ = 64
UDS_NOTHOUSANDS = 128
UDS_HOTTRACK = 256
UDM_SETRANGE = WM_USER + 101
UDM_GETRANGE = WM_USER + 102
UDM_SETPOS = WM_USER + 103
UDM_GETPOS = WM_USER + 104
UDM_SETBUDDY = WM_USER + 105
UDM_GETBUDDY = WM_USER + 106
UDM_SETACCEL = WM_USER + 107
UDM_GETACCEL = WM_USER + 108
UDM_SETBASE = WM_USER + 109
UDM_GETBASE = WM_USER + 110
UDM_SETRANGE32 = WM_USER + 111
UDM_GETRANGE32 = WM_USER + 112  # wParam & lParam are LPINT
UDM_SETUNICODEFORMAT = CCM_SETUNICODEFORMAT
UDM_GETUNICODEFORMAT = CCM_GETUNICODEFORMAT
UDN_DELTAPOS = UDN_FIRST - 1
PROGRESS_CLASSA = "msctls_progress32"
PROGRESS_CLASS = PROGRESS_CLASSA
PBS_SMOOTH = 1
PBS_VERTICAL = 4
PBM_SETRANGE = WM_USER + 1
PBM_SETPOS = WM_USER + 2
PBM_DELTAPOS = WM_USER + 3
PBM_SETSTEP = WM_USER + 4
PBM_STEPIT = WM_USER + 5
PBM_SETRANGE32 = WM_USER + 6  # lParam = high, wParam = low
PBM_GETRANGE = (
    WM_USER + 7
)  # wParam = return (TRUE ? low : high). lParam = PPBRANGE or NULL
PBM_GETPOS = WM_USER + 8
PBM_SETBARCOLOR = WM_USER + 9  # lParam = bar color
PBM_SETBKCOLOR = CCM_SETBKCOLOR  # lParam = bkColor
HOTKEYF_SHIFT = 1
HOTKEYF_CONTROL = 2
HOTKEYF_ALT = 4
HOTKEYF_EXT = 8
HKCOMB_NONE = 1
HKCOMB_S = 2
HKCOMB_C = 4
HKCOMB_A = 8
HKCOMB_SC = 16
HKCOMB_SA = 32
HKCOMB_CA = 64
HKCOMB_SCA = 128
HKM_SETHOTKEY = WM_USER + 1
HKM_GETHOTKEY = WM_USER + 2
HKM_SETRULES = WM_USER + 3
HOTKEY_CLASSA = "msctls_hotkey32"
HOTKEY_CLASS = HOTKEY_CLASSA
CCS_TOP = 0x00000001
CCS_NOMOVEY = 0x00000002
CCS_BOTTOM = 0x00000003
CCS_NORESIZE = 0x00000004
CCS_NOPARENTALIGN = 0x00000008
CCS_ADJUSTABLE = 0x00000020
CCS_NODIVIDER = 0x00000040
CCS_VERT = 0x00000080
CCS_LEFT = CCS_VERT | CCS_TOP
CCS_RIGHT = CCS_VERT | CCS_BOTTOM
CCS_NOMOVEX = CCS_VERT | CCS_NOMOVEY
WC_LISTVIEWA = "SysListView32"
WC_LISTVIEW = WC_LISTVIEWA
LVS_ICON = 0
LVS_REPORT = 1
LVS_SMALLICON = 2
LVS_LIST = 3
LVS_TYPEMASK = 3
LVS_SINGLESEL = 4
LVS_SHOWSELALWAYS = 8
LVS_SORTASCENDING = 16
LVS_SORTDESCENDING = 32
LVS_SHAREIMAGELISTS = 64
LVS_NOLABELWRAP = 128
LVS_AUTOARRANGE = 256
LVS_EDITLABELS = 512
LVS_OWNERDATA = 4096
LVS_NOSCROLL = 8192
LVS_TYPESTYLEMASK = 64512
LVS_ALIGNTOP = 0
LVS_ALIGNLEFT = 2048
LVS_ALIGNMASK = 3072
LVS_OWNERDRAWFIXED = 1024
LVS_NOCOLUMNHEADER = 16384
LVS_NOSORTHEADER = 32768
LVM_SETUNICODEFORMAT = CCM_SETUNICODEFORMAT
LVM_GETUNICODEFORMAT = CCM_GETUNICODEFORMAT
LVM_GETBKCOLOR = LVM_FIRST + 0
LVM_SETBKCOLOR = LVM_FIRST + 1
LVM_GETIMAGELIST = LVM_FIRST + 2
LVSIL_NORMAL = 0
LVSIL_SMALL = 1
LVSIL_STATE = 2
LVM_SETIMAGELIST = LVM_FIRST + 3
LVM_GETITEMCOUNT = LVM_FIRST + 4
LVIF_TEXT = 1
LVIF_IMAGE = 2
LVIF_PARAM = 4
LVIF_STATE = 8
LVIF_INDENT = 16
LVIF_NORECOMPUTE = 2048
LVIS_FOCUSED = 1
LVIS_SELECTED = 2
LVIS_CUT = 4
LVIS_DROPHILITED = 8
LVIS_ACTIVATING = 32
LVIS_OVERLAYMASK = 3840
LVIS_STATEIMAGEMASK = 61440
I_INDENTCALLBACK = -1
LPSTR_TEXTCALLBACKA = -1
LPSTR_TEXTCALLBACK = LPSTR_TEXTCALLBACKA
I_IMAGECALLBACK = -1
LVM_GETITEMA = LVM_FIRST + 5
LVM_GETITEMW = LVM_FIRST + 75
LVM_GETITEM = LVM_GETITEMA
LVM_SETITEMA = LVM_FIRST + 6
LVM_SETITEMW = LVM_FIRST + 76
LVM_SETITEM = LVM_SETITEMA
LVM_INSERTITEMA = LVM_FIRST + 7
LVM_INSERTITEMW = LVM_FIRST + 77
LVM_INSERTITEM = LVM_INSERTITEMA
LVM_DELETEITEM = LVM_FIRST + 8
LVM_DELETEALLITEMS = LVM_FIRST + 9
LVM_GETCALLBACKMASK = LVM_FIRST + 10
LVM_SETCALLBACKMASK = LVM_FIRST + 11
LVNI_ALL = 0
LVNI_FOCUSED = 1
LVNI_SELECTED = 2
LVNI_CUT = 4
LVNI_DROPHILITED = 8
LVNI_ABOVE = 256
LVNI_BELOW = 512
LVNI_TOLEFT = 1024
LVNI_TORIGHT = 2048
LVM_GETNEXTITEM = LVM_FIRST + 12
LVFI_PARAM = 1
LVFI_STRING = 2
LVFI_PARTIAL = 8
LVFI_WRAP = 32
LVFI_NEARESTXY = 64
LVM_FINDITEMA = LVM_FIRST + 13
LVM_FINDITEMW = LVM_FIRST + 83
LVM_FINDITEM = LVM_FINDITEMA
LVIR_BOUNDS = 0
LVIR_ICON = 1
LVIR_LABEL = 2
LVIR_SELECTBOUNDS = 3
LVM_GETITEMRECT = LVM_FIRST + 14
LVM_SETITEMPOSITION = LVM_FIRST + 15
LVM_GETITEMPOSITION = LVM_FIRST + 16
LVM_GETSTRINGWIDTHA = LVM_FIRST + 17
LVM_GETSTRINGWIDTHW = LVM_FIRST + 87
LVM_GETSTRINGWIDTH = LVM_GETSTRINGWIDTHA
LVHT_NOWHERE = 1
LVHT_ONITEMICON = 2
LVHT_ONITEMLABEL = 4
LVHT_ONITEMSTATEICON = 8
LVHT_ONITEM = LVHT_ONITEMICON | LVHT_ONITEMLABEL | LVHT_ONITEMSTATEICON
LVHT_ABOVE = 8
LVHT_BELOW = 16
LVHT_TORIGHT = 32
LVHT_TOLEFT = 64
LVM_HITTEST = LVM_FIRST + 18
LVM_ENSUREVISIBLE = LVM_FIRST + 19
LVM_SCROLL = LVM_FIRST + 20
LVM_REDRAWITEMS = LVM_FIRST + 21
LVA_DEFAULT = 0
LVA_ALIGNLEFT = 1
LVA_ALIGNTOP = 2
LVA_SNAPTOGRID = 5
LVM_ARRANGE = LVM_FIRST + 22
LVM_EDITLABELA = LVM_FIRST + 23
LVM_EDITLABELW = LVM_FIRST + 118
LVM_EDITLABEL = LVM_EDITLABELA
LVM_GETEDITCONTROL = LVM_FIRST + 24
LVCF_FMT = 1
LVCF_WIDTH = 2
LVCF_TEXT = 4
LVCF_SUBITEM = 8
LVCF_IMAGE = 16
LVCF_ORDER = 32
LVCFMT_LEFT = 0
LVCFMT_RIGHT = 1
LVCFMT_CENTER = 2
LVCFMT_JUSTIFYMASK = 3
LVCFMT_IMAGE = 2048
LVCFMT_BITMAP_ON_RIGHT = 4096
LVCFMT_COL_HAS_IMAGES = 32768
LVM_GETCOLUMNA = LVM_FIRST + 25
LVM_GETCOLUMNW = LVM_FIRST + 95
LVM_GETCOLUMN = LVM_GETCOLUMNA
LVM_SETCOLUMNA = LVM_FIRST + 26
LVM_SETCOLUMNW = LVM_FIRST + 96
LVM_SETCOLUMN = LVM_SETCOLUMNA
LVM_INSERTCOLUMNA = LVM_FIRST + 27
LVM_INSERTCOLUMNW = LVM_FIRST + 97
LVM_INSERTCOLUMN = LVM_INSERTCOLUMNA
LVM_DELETECOLUMN = LVM_FIRST + 28
LVM_GETCOLUMNWIDTH = LVM_FIRST + 29
LVSCW_AUTOSIZE = -1
LVSCW_AUTOSIZE_USEHEADER = -2
LVM_SETCOLUMNWIDTH = LVM_FIRST + 30
LVM_GETHEADER = LVM_FIRST + 31
LVM_CREATEDRAGIMAGE = LVM_FIRST + 33
LVM_GETVIEWRECT = LVM_FIRST + 34
LVM_GETTEXTCOLOR = LVM_FIRST + 35
LVM_SETTEXTCOLOR = LVM_FIRST + 36
LVM_GETTEXTBKCOLOR = LVM_FIRST + 37
LVM_SETTEXTBKCOLOR = LVM_FIRST + 38
LVM_GETTOPINDEX = LVM_FIRST + 39
LVM_GETCOUNTPERPAGE = LVM_FIRST + 40
LVM_GETORIGIN = LVM_FIRST + 41
LVM_UPDATE = LVM_FIRST + 42
LVM_SETITEMSTATE = LVM_FIRST + 43
LVM_GETITEMSTATE = LVM_FIRST + 44
LVM_GETITEMTEXTA = LVM_FIRST + 45
LVM_GETITEMTEXTW = LVM_FIRST + 115
LVM_GETITEMTEXT = LVM_GETITEMTEXTA
LVM_SETITEMTEXTA = LVM_FIRST + 46
LVM_SETITEMTEXTW = LVM_FIRST + 116
LVM_SETITEMTEXT = LVM_SETITEMTEXTA
LVSICF_NOINVALIDATEALL = 1
LVSICF_NOSCROLL = 2
LVM_SETITEMCOUNT = LVM_FIRST + 47
LVM_SORTITEMS = LVM_FIRST + 48
LVM_SETITEMPOSITION32 = LVM_FIRST + 49
LVM_GETSELECTEDCOUNT = LVM_FIRST + 50
LVM_GETITEMSPACING = LVM_FIRST + 51
LVM_GETISEARCHSTRINGA = LVM_FIRST + 52
LVM_GETISEARCHSTRINGW = LVM_FIRST + 117
LVM_GETISEARCHSTRING = LVM_GETISEARCHSTRINGA
LVM_SETICONSPACING = LVM_FIRST + 53
LVM_SETEXTENDEDLISTVIEWSTYLE = LVM_FIRST + 54  # optional wParam == mask
LVM_GETEXTENDEDLISTVIEWSTYLE = LVM_FIRST + 55
LVS_EX_GRIDLINES = 1
LVS_EX_SUBITEMIMAGES = 2
LVS_EX_CHECKBOXES = 4
LVS_EX_TRACKSELECT = 8
LVS_EX_HEADERDRAGDROP = 16
LVS_EX_FULLROWSELECT = 32  # applies to report mode only
LVS_EX_ONECLICKACTIVATE = 64
LVS_EX_TWOCLICKACTIVATE = 128
LVS_EX_FLATSB = 256
LVS_EX_REGIONAL = 512
LVS_EX_INFOTIP = 1024  # listview does InfoTips for you
LVS_EX_UNDERLINEHOT = 2048
LVS_EX_UNDERLINECOLD = 4096
LVS_EX_MULTIWORKAREAS = 8192
LVM_GETSUBITEMRECT = LVM_FIRST + 56
LVM_SUBITEMHITTEST = LVM_FIRST + 57
LVM_SETCOLUMNORDERARRAY = LVM_FIRST + 58
LVM_GETCOLUMNORDERARRAY = LVM_FIRST + 59
LVM_SETHOTITEM = LVM_FIRST + 60
LVM_GETHOTITEM = LVM_FIRST + 61
LVM_SETHOTCURSOR = LVM_FIRST + 62
LVM_GETHOTCURSOR = LVM_FIRST + 63
LVM_APPROXIMATEVIEWRECT = LVM_FIRST + 64
LV_MAX_WORKAREAS = 16
LVM_SETWORKAREAS = LVM_FIRST + 65
LVM_GETWORKAREAS = LVM_FIRST + 70
LVM_GETNUMBEROFWORKAREAS = LVM_FIRST + 73
LVM_GETSELECTIONMARK = LVM_FIRST + 66
LVM_SETSELECTIONMARK = LVM_FIRST + 67
LVM_SETHOVERTIME = LVM_FIRST + 71
LVM_GETHOVERTIME = LVM_FIRST + 72
LVM_SETTOOLTIPS = LVM_FIRST + 74
LVM_GETTOOLTIPS = LVM_FIRST + 78
LVBKIF_SOURCE_NONE = 0
LVBKIF_SOURCE_HBITMAP = 1
LVBKIF_SOURCE_URL = 2
LVBKIF_SOURCE_MASK = 3
LVBKIF_STYLE_NORMAL = 0
LVBKIF_STYLE_TILE = 16
LVBKIF_STYLE_MASK = 16
LVM_SETBKIMAGEA = LVM_FIRST + 68
LVM_SETBKIMAGEW = LVM_FIRST + 138
LVM_GETBKIMAGEA = LVM_FIRST + 69
LVM_GETBKIMAGEW = LVM_FIRST + 139
LVKF_ALT = 1
LVKF_CONTROL = 2
LVKF_SHIFT = 4
LVN_ITEMCHANGING = LVN_FIRST - 0
LVN_ITEMCHANGED = LVN_FIRST - 1
LVN_INSERTITEM = LVN_FIRST - 2
LVN_DELETEITEM = LVN_FIRST - 3
LVN_DELETEALLITEMS = LVN_FIRST - 4
LVN_BEGINLABELEDITA = LVN_FIRST - 5
LVN_BEGINLABELEDITW = LVN_FIRST - 75
LVN_ENDLABELEDITA = LVN_FIRST - 6
LVN_ENDLABELEDITW = LVN_FIRST - 76
LVN_COLUMNCLICK = LVN_FIRST - 8
LVN_BEGINDRAG = LVN_FIRST - 9
LVN_BEGINRDRAG = LVN_FIRST - 11
LVN_ODCACHEHINT = LVN_FIRST - 13
LVN_ODFINDITEMA = LVN_FIRST - 52
LVN_ODFINDITEMW = LVN_FIRST - 79
LVN_ITEMACTIVATE = LVN_FIRST - 14
LVN_ODSTATECHANGED = LVN_FIRST - 15
LVN_ODFINDITEM = LVN_ODFINDITEMA
LVN_HOTTRACK = LVN_FIRST - 21
LVN_GETDISPINFOA = LVN_FIRST - 50
LVN_GETDISPINFOW = LVN_FIRST - 77
LVN_SETDISPINFOA = LVN_FIRST - 51
LVN_SETDISPINFOW = LVN_FIRST - 78
LVN_BEGINLABELEDIT = LVN_BEGINLABELEDITA
LVN_ENDLABELEDIT = LVN_ENDLABELEDITA
LVN_GETDISPINFO = LVN_GETDISPINFOA
LVN_SETDISPINFO = LVN_SETDISPINFOA
LVIF_DI_SETITEM = 4096
LVN_KEYDOWN = LVN_FIRST - 55
LVN_MARQUEEBEGIN = LVN_FIRST - 56
LVGIT_UNFOLDED = 1
LVN_GETINFOTIPA = LVN_FIRST - 57
LVN_GETINFOTIPW = LVN_FIRST - 58
LVN_GETINFOTIP = LVN_GETINFOTIPA
WC_TREEVIEWA = "SysTreeView32"
WC_TREEVIEW = WC_TREEVIEWA
TVS_HASBUTTONS = 1
TVS_HASLINES = 2
TVS_LINESATROOT = 4
TVS_EDITLABELS = 8
TVS_DISABLEDRAGDROP = 16
TVS_SHOWSELALWAYS = 32
TVS_RTLREADING = 64
TVS_NOTOOLTIPS = 128
TVS_CHECKBOXES = 256
TVS_TRACKSELECT = 512
TVS_SINGLEEXPAND = 1024
TVS_INFOTIP = 2048
TVS_FULLROWSELECT = 4096
TVS_NOSCROLL = 8192
TVS_NONEVENHEIGHT = 16384
TVIF_TEXT = 1
TVIF_IMAGE = 2
TVIF_PARAM = 4
TVIF_STATE = 8
TVIF_HANDLE = 16
TVIF_SELECTEDIMAGE = 32
TVIF_CHILDREN = 64
TVIF_INTEGRAL = 128
TVIS_SELECTED = 2
TVIS_CUT = 4
TVIS_DROPHILITED = 8
TVIS_BOLD = 16
TVIS_EXPANDED = 32
TVIS_EXPANDEDONCE = 64
TVIS_EXPANDPARTIAL = 128
TVIS_OVERLAYMASK = 3840
TVIS_STATEIMAGEMASK = 61440
TVIS_USERMASK = 61440
I_CHILDRENCALLBACK = -1
TVI_ROOT = -65536
TVI_FIRST = -65535
TVI_LAST = -65534
TVI_SORT = -65533
TVM_INSERTITEMA = TV_FIRST + 0
TVM_INSERTITEMW = TV_FIRST + 50
TVM_INSERTITEM = TVM_INSERTITEMA
TVM_DELETEITEM = TV_FIRST + 1
TVM_EXPAND = TV_FIRST + 2
TVE_COLLAPSE = 1
TVE_EXPAND = 2
TVE_TOGGLE = 3
TVE_EXPANDPARTIAL = 16384
TVE_COLLAPSERESET = 32768
TVM_GETITEMRECT = TV_FIRST + 4
TVM_GETCOUNT = TV_FIRST + 5
TVM_GETINDENT = TV_FIRST + 6
TVM_SETINDENT = TV_FIRST + 7
TVM_GETIMAGELIST = TV_FIRST + 8
TVSIL_NORMAL = 0
TVSIL_STATE = 2
TVM_SETIMAGELIST = TV_FIRST + 9
TVM_GETNEXTITEM = TV_FIRST + 10
TVGN_ROOT = 0
TVGN_NEXT = 1
TVGN_PREVIOUS = 2
TVGN_PARENT = 3
TVGN_CHILD = 4
TVGN_FIRSTVISIBLE = 5
TVGN_NEXTVISIBLE = 6
TVGN_PREVIOUSVISIBLE = 7
TVGN_DROPHILITE = 8
TVGN_CARET = 9
TVGN_LASTVISIBLE = 10
TVM_SELECTITEM = TV_FIRST + 11
TVM_GETITEMA = TV_FIRST + 12
TVM_GETITEMW = TV_FIRST + 62
TVM_GETITEM = TVM_GETITEMA
TVM_SETITEMA = TV_FIRST + 13
TVM_SETITEMW = TV_FIRST + 63
TVM_SETITEM = TVM_SETITEMA
TVM_EDITLABELA = TV_FIRST + 14
TVM_EDITLABELW = TV_FIRST + 65
TVM_EDITLABEL = TVM_EDITLABELA
TVM_GETEDITCONTROL = TV_FIRST + 15
TVM_GETVISIBLECOUNT = TV_FIRST + 16
TVM_HITTEST = TV_FIRST + 17
TVHT_NOWHERE = 1
TVHT_ONITEMICON = 2
TVHT_ONITEMLABEL = 4
TVHT_ONITEMINDENT = 8
TVHT_ONITEMBUTTON = 16
TVHT_ONITEMRIGHT = 32
TVHT_ONITEMSTATEICON = 64
TVHT_ABOVE = 256
TVHT_BELOW = 512
TVHT_TORIGHT = 1024
TVHT_TOLEFT = 2048
TVHT_ONITEM = TVHT_ONITEMICON | TVHT_ONITEMLABEL | TVHT_ONITEMSTATEICON
TVM_CREATEDRAGIMAGE = TV_FIRST + 18
TVM_SORTCHILDREN = TV_FIRST + 19
TVM_ENSUREVISIBLE = TV_FIRST + 20
TVM_SORTCHILDRENCB = TV_FIRST + 21
TVM_ENDEDITLABELNOW = TV_FIRST + 22
TVM_GETISEARCHSTRINGA = TV_FIRST + 23
TVM_GETISEARCHSTRINGW = TV_FIRST + 64
TVM_GETISEARCHSTRING = TVM_GETISEARCHSTRINGA
TVM_SETTOOLTIPS = TV_FIRST + 24
TVM_GETTOOLTIPS = TV_FIRST + 25
TVM_SETINSERTMARK = TV_FIRST + 26
TVM_SETUNICODEFORMAT = CCM_SETUNICODEFORMAT
TVM_GETUNICODEFORMAT = CCM_GETUNICODEFORMAT
TVM_SETITEMHEIGHT = TV_FIRST + 27
TVM_GETITEMHEIGHT = TV_FIRST + 28
TVM_SETBKCOLOR = TV_FIRST + 29
TVM_SETTEXTCOLOR = TV_FIRST + 30
TVM_GETBKCOLOR = TV_FIRST + 31
TVM_GETTEXTCOLOR = TV_FIRST + 32
TVM_SETSCROLLTIME = TV_FIRST + 33
TVM_GETSCROLLTIME = TV_FIRST + 34
TVM_SETINSERTMARKCOLOR = TV_FIRST + 37
TVM_GETINSERTMARKCOLOR = TV_FIRST + 38
TVN_SELCHANGINGA = TVN_FIRST - 1
TVN_SELCHANGINGW = TVN_FIRST - 50
TVN_SELCHANGEDA = TVN_FIRST - 2
TVN_SELCHANGEDW = TVN_FIRST - 51
TVC_UNKNOWN = 0
TVC_BYMOUSE = 1
TVC_BYKEYBOARD = 2
TVN_GETDISPINFOA = TVN_FIRST - 3
TVN_GETDISPINFOW = TVN_FIRST - 52
TVN_SETDISPINFOA = TVN_FIRST - 4
TVN_SETDISPINFOW = TVN_FIRST - 53
TVIF_DI_SETITEM = 4096
TVN_ITEMEXPANDINGA = TVN_FIRST - 5
TVN_ITEMEXPANDINGW = TVN_FIRST - 54
TVN_ITEMEXPANDEDA = TVN_FIRST - 6
TVN_ITEMEXPANDEDW = TVN_FIRST - 55
TVN_BEGINDRAGA = TVN_FIRST - 7
TVN_BEGINDRAGW = TVN_FIRST - 56
TVN_BEGINRDRAGA = TVN_FIRST - 8
TVN_BEGINRDRAGW = TVN_FIRST - 57
TVN_DELETEITEMA = TVN_FIRST - 9
TVN_DELETEITEMW = TVN_FIRST - 58
TVN_BEGINLABELEDITA = TVN_FIRST - 10
TVN_BEGINLABELEDITW = TVN_FIRST - 59
TVN_ENDLABELEDITA = TVN_FIRST - 11
TVN_ENDLABELEDITW = TVN_FIRST - 60
TVN_KEYDOWN = TVN_FIRST - 12
TVN_GETINFOTIPA = TVN_FIRST - 13
TVN_GETINFOTIPW = TVN_FIRST - 14
TVN_SINGLEEXPAND = TVN_FIRST - 15
TVN_SELCHANGING = TVN_SELCHANGINGA
TVN_SELCHANGED = TVN_SELCHANGEDA
TVN_GETDISPINFO = TVN_GETDISPINFOA
TVN_SETDISPINFO = TVN_SETDISPINFOA
TVN_ITEMEXPANDING = TVN_ITEMEXPANDINGA
TVN_ITEMEXPANDED = TVN_ITEMEXPANDEDA
TVN_BEGINDRAG = TVN_BEGINDRAGA
TVN_BEGINRDRAG = TVN_BEGINRDRAGA
TVN_DELETEITEM = TVN_DELETEITEMA
TVN_BEGINLABELEDIT = TVN_BEGINLABELEDITA
TVN_ENDLABELEDIT = TVN_ENDLABELEDITA
TVN_GETINFOTIP = TVN_GETINFOTIPA
TVCDRF_NOIMAGES = 65536
WC_COMBOBOXEXA = "ComboBoxEx32"
WC_COMBOBOXEX = WC_COMBOBOXEXA
CBEIF_TEXT = 1
CBEIF_IMAGE = 2
CBEIF_SELECTEDIMAGE = 4
CBEIF_OVERLAY = 8
CBEIF_INDENT = 16
CBEIF_LPARAM = 32
CBEIF_DI_SETITEM = 268435456
CBEM_INSERTITEMA = WM_USER + 1
CBEM_SETIMAGELIST = WM_USER + 2
CBEM_GETIMAGELIST = WM_USER + 3
CBEM_GETITEMA = WM_USER + 4
CBEM_SETITEMA = WM_USER + 5
# CBEM_DELETEITEM = CB_DELETESTRING
CBEM_GETCOMBOCONTROL = WM_USER + 6
CBEM_GETEDITCONTROL = WM_USER + 7
CBEM_SETEXSTYLE = WM_USER + 8  # use  SETEXTENDEDSTYLE instead
CBEM_SETEXTENDEDSTYLE = WM_USER + 14  # lparam == new style, wParam (optional) == mask
CBEM_GETEXSTYLE = WM_USER + 9  # use GETEXTENDEDSTYLE instead
CBEM_GETEXTENDEDSTYLE = WM_USER + 9
CBEM_SETUNICODEFORMAT = CCM_SETUNICODEFORMAT
CBEM_GETUNICODEFORMAT = CCM_GETUNICODEFORMAT
CBEM_HASEDITCHANGED = WM_USER + 10
CBEM_INSERTITEMW = WM_USER + 11
CBEM_SETITEMW = WM_USER + 12
CBEM_GETITEMW = WM_USER + 13
CBEM_INSERTITEM = CBEM_INSERTITEMA
CBEM_SETITEM = CBEM_SETITEMA
CBEM_GETITEM = CBEM_GETITEMA
CBES_EX_NOEDITIMAGE = 1
CBES_EX_NOEDITIMAGEINDENT = 2
CBES_EX_PATHWORDBREAKPROC = 4
CBES_EX_NOSIZELIMIT = 8
CBES_EX_CASESENSITIVE = 16
CBEN_GETDISPINFO = CBEN_FIRST - 0
CBEN_GETDISPINFOA = CBEN_FIRST - 0
CBEN_INSERTITEM = CBEN_FIRST - 1
CBEN_DELETEITEM = CBEN_FIRST - 2
CBEN_BEGINEDIT = CBEN_FIRST - 4
CBEN_ENDEDITA = CBEN_FIRST - 5
CBEN_ENDEDITW = CBEN_FIRST - 6
CBEN_GETDISPINFOW = CBEN_FIRST - 7
CBEN_DRAGBEGINA = CBEN_FIRST - 8
CBEN_DRAGBEGINW = CBEN_FIRST - 9
CBEN_DRAGBEGIN = CBEN_DRAGBEGINA
CBEN_ENDEDIT = CBEN_ENDEDITA
CBENF_KILLFOCUS = 1
CBENF_RETURN = 2
CBENF_ESCAPE = 3
CBENF_DROPDOWN = 4
CBEMAXSTRLEN = 260
WC_TABCONTROLA = "SysTabControl32"
WC_TABCONTROL = WC_TABCONTROLA
TCS_SCROLLOPPOSITE = 1  # assumes multiline tab
TCS_BOTTOM = 2
TCS_RIGHT = 2
TCS_MULTISELECT = 4  # allow multi-select in button mode
TCS_FLATBUTTONS = 8
TCS_FORCEICONLEFT = 16
TCS_FORCELABELLEFT = 32
TCS_HOTTRACK = 64
TCS_VERTICAL = 128
TCS_TABS = 0
TCS_BUTTONS = 256
TCS_SINGLELINE = 0
TCS_MULTILINE = 512
TCS_RIGHTJUSTIFY = 0
TCS_FIXEDWIDTH = 1024
TCS_RAGGEDRIGHT = 2048
TCS_FOCUSONBUTTONDOWN = 4096
TCS_OWNERDRAWFIXED = 8192
TCS_TOOLTIPS = 16384
TCS_FOCUSNEVER = 32768
TCS_EX_FLATSEPARATORS = 1
TCS_EX_REGISTERDROP = 2
TCM_GETIMAGELIST = TCM_FIRST + 2
TCM_SETIMAGELIST = TCM_FIRST + 3
TCM_GETITEMCOUNT = TCM_FIRST + 4
TCIF_TEXT = 1
TCIF_IMAGE = 2
TCIF_RTLREADING = 4
TCIF_PARAM = 8
TCIF_STATE = 16
TCIS_BUTTONPRESSED = 1
TCIS_HIGHLIGHTED = 2
TCM_GETITEMA = TCM_FIRST + 5
TCM_GETITEMW = TCM_FIRST + 60
TCM_GETITEM = TCM_GETITEMA
TCM_SETITEMA = TCM_FIRST + 6
TCM_SETITEMW = TCM_FIRST + 61
TCM_SETITEM = TCM_SETITEMA
TCM_INSERTITEMA = TCM_FIRST + 7
TCM_INSERTITEMW = TCM_FIRST + 62
TCM_INSERTITEM = TCM_INSERTITEMA
TCM_DELETEITEM = TCM_FIRST + 8
TCM_DELETEALLITEMS = TCM_FIRST + 9
TCM_GETITEMRECT = TCM_FIRST + 10
TCM_GETCURSEL = TCM_FIRST + 11
TCM_SETCURSEL = TCM_FIRST + 12
TCHT_NOWHERE = 1
TCHT_ONITEMICON = 2
TCHT_ONITEMLABEL = 4
TCHT_ONITEM = TCHT_ONITEMICON | TCHT_ONITEMLABEL
TCM_HITTEST = TCM_FIRST + 13
TCM_SETITEMEXTRA = TCM_FIRST + 14
TCM_ADJUSTRECT = TCM_FIRST + 40
TCM_SETITEMSIZE = TCM_FIRST + 41
TCM_REMOVEIMAGE = TCM_FIRST + 42
TCM_SETPADDING = TCM_FIRST + 43
TCM_GETROWCOUNT = TCM_FIRST + 44
TCM_GETTOOLTIPS = TCM_FIRST + 45
TCM_SETTOOLTIPS = TCM_FIRST + 46
TCM_GETCURFOCUS = TCM_FIRST + 47
TCM_SETCURFOCUS = TCM_FIRST + 48
TCM_SETMINTABWIDTH = TCM_FIRST + 49
TCM_DESELECTALL = TCM_FIRST + 50
TCM_HIGHLIGHTITEM = TCM_FIRST + 51
TCM_SETEXTENDEDSTYLE = TCM_FIRST + 52  # optional wParam == mask
TCM_GETEXTENDEDSTYLE = TCM_FIRST + 53
TCM_SETUNICODEFORMAT = CCM_SETUNICODEFORMAT
TCM_GETUNICODEFORMAT = CCM_GETUNICODEFORMAT
TCN_KEYDOWN = TCN_FIRST - 0
ANIMATE_CLASSA = "SysAnimate32"
ANIMATE_CLASS = ANIMATE_CLASSA
ACS_CENTER = 1
ACS_TRANSPARENT = 2
ACS_AUTOPLAY = 4
ACS_TIMER = 8  # don't use threads... use timers
ACM_OPENA = WM_USER + 100
ACM_OPENW = WM_USER + 103
ACM_OPEN = ACM_OPENA
ACM_PLAY = WM_USER + 101
ACM_STOP = WM_USER + 102
ACN_START = 1
ACN_STOP = 2
MONTHCAL_CLASSA = "SysMonthCal32"
MONTHCAL_CLASS = MONTHCAL_CLASSA
MCM_FIRST = 4096
MCM_GETCURSEL = MCM_FIRST + 1
MCM_SETCURSEL = MCM_FIRST + 2
MCM_GETMAXSELCOUNT = MCM_FIRST + 3
MCM_SETMAXSELCOUNT = MCM_FIRST + 4
MCM_GETSELRANGE = MCM_FIRST + 5
MCM_SETSELRANGE = MCM_FIRST + 6
MCM_GETMONTHRANGE = MCM_FIRST + 7
MCM_SETDAYSTATE = MCM_FIRST + 8
MCM_GETMINREQRECT = MCM_FIRST + 9
MCM_SETCOLOR = MCM_FIRST + 10
MCM_GETCOLOR = MCM_FIRST + 11
MCSC_BACKGROUND = 0  # the background color (between months)
MCSC_TEXT = 1  # the dates
MCSC_TITLEBK = 2  # background of the title
MCSC_TITLETEXT = 3
MCSC_MONTHBK = 4  # background within the month cal
MCSC_TRAILINGTEXT = 5  # the text color of header & trailing days
MCM_SETTODAY = MCM_FIRST + 12
MCM_GETTODAY = MCM_FIRST + 13
MCM_HITTEST = MCM_FIRST + 14
MCHT_TITLE = 65536
MCHT_CALENDAR = 131072
MCHT_TODAYLINK = 196608
MCHT_NEXT = 16777216  # these indicate that hitting
MCHT_PREV = 33554432  # here will go to the next/prev month
MCHT_NOWHERE = 0
MCHT_TITLEBK = MCHT_TITLE
MCHT_TITLEMONTH = MCHT_TITLE | 1
MCHT_TITLEYEAR = MCHT_TITLE | 2
MCHT_TITLEBTNNEXT = MCHT_TITLE | MCHT_NEXT | 3
MCHT_TITLEBTNPREV = MCHT_TITLE | MCHT_PREV | 3
MCHT_CALENDARBK = MCHT_CALENDAR
MCHT_CALENDARDATE = MCHT_CALENDAR | 1
MCHT_CALENDARDATENEXT = MCHT_CALENDARDATE | MCHT_NEXT
MCHT_CALENDARDATEPREV = MCHT_CALENDARDATE | MCHT_PREV
MCHT_CALENDARDAY = MCHT_CALENDAR | 2
MCHT_CALENDARWEEKNUM = MCHT_CALENDAR | 3
MCM_SETFIRSTDAYOFWEEK = MCM_FIRST + 15
MCM_GETFIRSTDAYOFWEEK = MCM_FIRST + 16
MCM_GETRANGE = MCM_FIRST + 17
MCM_SETRANGE = MCM_FIRST + 18
MCM_GETMONTHDELTA = MCM_FIRST + 19
MCM_SETMONTHDELTA = MCM_FIRST + 20
MCM_GETMAXTODAYWIDTH = MCM_FIRST + 21
MCM_SETUNICODEFORMAT = CCM_SETUNICODEFORMAT
MCM_GETUNICODEFORMAT = CCM_GETUNICODEFORMAT
MCN_SELCHANGE = MCN_FIRST + 1
MCN_GETDAYSTATE = MCN_FIRST + 3
MCN_SELECT = MCN_FIRST + 4
MCS_DAYSTATE = 1
MCS_MULTISELECT = 2
MCS_WEEKNUMBERS = 4
MCS_NOTODAYCIRCLE = 8
MCS_NOTODAY = 8
GMR_VISIBLE = 0  # visible portion of display
GMR_DAYSTATE = 1  # above plus the grayed out parts of
DATETIMEPICK_CLASSA = "SysDateTimePick32"
DATETIMEPICK_CLASS = DATETIMEPICK_CLASSA
DTM_FIRST = 4096
DTM_GETSYSTEMTIME = DTM_FIRST + 1
DTM_SETSYSTEMTIME = DTM_FIRST + 2
DTM_GETRANGE = DTM_FIRST + 3
DTM_SETRANGE = DTM_FIRST + 4
DTM_SETFORMATA = DTM_FIRST + 5
DTM_SETFORMATW = DTM_FIRST + 50
DTM_SETFORMAT = DTM_SETFORMATA
DTM_SETMCCOLOR = DTM_FIRST + 6
DTM_GETMCCOLOR = DTM_FIRST + 7
DTM_GETMONTHCAL = DTM_FIRST + 8
DTM_SETMCFONT = DTM_FIRST + 9
DTM_GETMCFONT = DTM_FIRST + 10
DTS_UPDOWN = 1  # use UPDOWN instead of MONTHCAL
DTS_SHOWNONE = 2  # allow a NONE selection
DTS_SHORTDATEFORMAT = (
    0  # use the short date format (app must forward WM_WININICHANGE messages)
)
DTS_LONGDATEFORMAT = (
    4  # use the long date format (app must forward WM_WININICHANGE messages)
)
DTS_TIMEFORMAT = 9  # use the time format (app must forward WM_WININICHANGE messages)
DTS_APPCANPARSE = 16  # allow user entered strings (app MUST respond to DTN_USERSTRING)
DTS_RIGHTALIGN = 32  # right-align popup instead of left-align it
DTN_DATETIMECHANGE = DTN_FIRST + 1  # the systemtime has changed
DTN_USERSTRINGA = DTN_FIRST + 2  # the user has entered a string
DTN_USERSTRINGW = DTN_FIRST + 15
DTN_USERSTRING = DTN_USERSTRINGW
DTN_WMKEYDOWNA = DTN_FIRST + 3  # modify keydown on app format field (X)
DTN_WMKEYDOWNW = DTN_FIRST + 16
DTN_WMKEYDOWN = DTN_WMKEYDOWNA
DTN_FORMATA = DTN_FIRST + 4  # query display for app format field (X)
DTN_FORMATW = DTN_FIRST + 17
DTN_FORMAT = DTN_FORMATA
DTN_FORMATQUERYA = DTN_FIRST + 5  # query formatting info for app format field (X)
DTN_FORMATQUERYW = DTN_FIRST + 18
DTN_FORMATQUERY = DTN_FORMATQUERYA
DTN_DROPDOWN = DTN_FIRST + 6  # MonthCal has dropped down
DTN_CLOSEUP = DTN_FIRST + 7  # MonthCal is popping up
GDTR_MIN = 1
GDTR_MAX = 2
GDT_ERROR = -1
GDT_VALID = 0
GDT_NONE = 1
IPM_CLEARADDRESS = WM_USER + 100  # no parameters
IPM_SETADDRESS = WM_USER + 101  # lparam = TCP/IP address
IPM_GETADDRESS = (
    WM_USER + 102
)  # lresult = # of non black fields.  lparam = LPDWORD for TCP/IP address
IPM_SETRANGE = WM_USER + 103  # wparam = field, lparam = range
IPM_SETFOCUS = WM_USER + 104  # wparam = field
IPM_ISBLANK = WM_USER + 105  # no parameters
WC_IPADDRESSA = "SysIPAddress32"
WC_IPADDRESS = WC_IPADDRESSA
IPN_FIELDCHANGED = IPN_FIRST - 0
WC_PAGESCROLLERA = "SysPager"
WC_PAGESCROLLER = WC_PAGESCROLLERA
PGS_VERT = 0
PGS_HORZ = 1
PGS_AUTOSCROLL = 2
PGS_DRAGNDROP = 4
PGF_INVISIBLE = 0  # Scroll button is not visible
PGF_NORMAL = 1  # Scroll button is in normal state
PGF_GRAYED = 2  # Scroll button is in grayed state
PGF_DEPRESSED = 4  # Scroll button is in depressed state
PGF_HOT = 8  # Scroll button is in hot state
PGB_TOPORLEFT = 0
PGB_BOTTOMORRIGHT = 1
PGM_SETCHILD = PGM_FIRST + 1  # lParam == hwnd
PGM_RECALCSIZE = PGM_FIRST + 2
PGM_FORWARDMOUSE = PGM_FIRST + 3
PGM_SETBKCOLOR = PGM_FIRST + 4
PGM_GETBKCOLOR = PGM_FIRST + 5
PGM_SETBORDER = PGM_FIRST + 6
PGM_GETBORDER = PGM_FIRST + 7
PGM_SETPOS = PGM_FIRST + 8
PGM_GETPOS = PGM_FIRST + 9
PGM_SETBUTTONSIZE = PGM_FIRST + 10
PGM_GETBUTTONSIZE = PGM_FIRST + 11
PGM_GETBUTTONSTATE = PGM_FIRST + 12
PGM_GETDROPTARGET = CCM_GETDROPTARGET
PGN_SCROLL = PGN_FIRST - 1
PGF_SCROLLUP = 1
PGF_SCROLLDOWN = 2
PGF_SCROLLLEFT = 4
PGF_SCROLLRIGHT = 8
PGK_SHIFT = 1
PGK_CONTROL = 2
PGK_MENU = 4
PGN_CALCSIZE = PGN_FIRST - 2
PGF_CALCWIDTH = 1
PGF_CALCHEIGHT = 2
WC_NATIVEFONTCTLA = "NativeFontCtl"
WC_NATIVEFONTCTL = WC_NATIVEFONTCTLA
NFS_EDIT = 1
NFS_STATIC = 2
NFS_LISTCOMBO = 4
NFS_BUTTON = 8
NFS_ALL = 16
WM_MOUSEHOVER = 673
WM_MOUSELEAVE = 675
TME_HOVER = 1
TME_LEAVE = 2
TME_QUERY = 1073741824
TME_CANCEL = -2147483648
HOVER_DEFAULT = -1
WSB_PROP_CYVSCROLL = 0x00000001
WSB_PROP_CXHSCROLL = 0x00000002
WSB_PROP_CYHSCROLL = 0x00000004
WSB_PROP_CXVSCROLL = 0x00000008
WSB_PROP_CXHTHUMB = 0x00000010
WSB_PROP_CYVTHUMB = 0x00000020
WSB_PROP_VBKGCOLOR = 0x00000040
WSB_PROP_HBKGCOLOR = 0x00000080
WSB_PROP_VSTYLE = 0x00000100
WSB_PROP_HSTYLE = 0x00000200
WSB_PROP_WINSTYLE = 0x00000400
WSB_PROP_PALETTE = 0x00000800
WSB_PROP_MASK = 0x00000FFF
FSB_FLAT_MODE = 2
FSB_ENCARTA_MODE = 1
FSB_REGULAR_MODE = 0


def INDEXTOOVERLAYMASK(i):
    return i << 8


def INDEXTOSTATEIMAGEMASK(i):
    return i << 12

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\win32\lib\commctrl.py ===
# Generated by h2py from CommCtrl.h
WM_USER = 1024
ICC_LISTVIEW_CLASSES = 1  # listview, header
ICC_TREEVIEW_CLASSES = 2  # treeview, tooltips
ICC_BAR_CLASSES = 4  # toolbar, statusbar, trackbar, tooltips
ICC_TAB_CLASSES = 8  # tab, tooltips
ICC_UPDOWN_CLASS = 16  # updown
ICC_PROGRESS_CLASS = 32  # progress
ICC_HOTKEY_CLASS = 64  # hotkey
ICC_ANIMATE_CLASS = 128  # animate
ICC_WIN95_CLASSES = 255
ICC_DATE_CLASSES = 256  # month picker, date picker, time picker, updown
ICC_USEREX_CLASSES = 512  # comboex
ICC_COOL_CLASSES = 1024  # rebar (coolbar) control
ICC_INTERNET_CLASSES = 2048
ICC_PAGESCROLLER_CLASS = 4096  # page scroller
ICC_NATIVEFNTCTL_CLASS = 8192  # native font control
ODT_HEADER = 100
ODT_TAB = 101
ODT_LISTVIEW = 102
PY_0U = 0
NM_FIRST = PY_0U  # generic to all controls
NM_LAST = PY_0U - 99
LVN_FIRST = PY_0U - 100  # listview
LVN_LAST = PY_0U - 199
HDN_FIRST = PY_0U - 300  # header
HDN_LAST = PY_0U - 399
TVN_FIRST = PY_0U - 400  # treeview
TVN_LAST = PY_0U - 499
TTN_FIRST = PY_0U - 520  # tooltips
TTN_LAST = PY_0U - 549
TCN_FIRST = PY_0U - 550  # tab control
TCN_LAST = PY_0U - 580
CDN_FIRST = PY_0U - 601  # common dialog (new)
CDN_LAST = PY_0U - 699
TBN_FIRST = PY_0U - 700  # toolbar
TBN_LAST = PY_0U - 720
UDN_FIRST = PY_0U - 721  # updown
UDN_LAST = PY_0U - 740
MCN_FIRST = PY_0U - 750  # monthcal
MCN_LAST = PY_0U - 759
DTN_FIRST = PY_0U - 760  # datetimepick
DTN_LAST = PY_0U - 799
CBEN_FIRST = PY_0U - 800  # combo box ex
CBEN_LAST = PY_0U - 830
RBN_FIRST = PY_0U - 831  # rebar
RBN_LAST = PY_0U - 859
IPN_FIRST = PY_0U - 860  # internet address
IPN_LAST = PY_0U - 879  # internet address
SBN_FIRST = PY_0U - 880  # status bar
SBN_LAST = PY_0U - 899
PGN_FIRST = PY_0U - 900  # Pager Control
PGN_LAST = PY_0U - 950
LVM_FIRST = 4096  # ListView messages
TV_FIRST = 4352  # TreeView messages
HDM_FIRST = 4608  # Header messages
TCM_FIRST = 4864  # Tab control messages
PGM_FIRST = 5120  # Pager control messages
CCM_FIRST = 8192  # Common control shared messages
CCM_SETBKCOLOR = CCM_FIRST + 1  # lParam is bkColor
CCM_SETCOLORSCHEME = CCM_FIRST + 2  # lParam is color scheme
CCM_GETCOLORSCHEME = CCM_FIRST + 3  # fills in COLORSCHEME pointed to by lParam
CCM_GETDROPTARGET = CCM_FIRST + 4
CCM_SETUNICODEFORMAT = CCM_FIRST + 5
CCM_GETUNICODEFORMAT = CCM_FIRST + 6
INFOTIPSIZE = 1024
NM_OUTOFMEMORY = NM_FIRST - 1
NM_CLICK = NM_FIRST - 2  # uses NMCLICK struct
NM_DBLCLK = NM_FIRST - 3
NM_RETURN = NM_FIRST - 4
NM_RCLICK = NM_FIRST - 5  # uses NMCLICK struct
NM_RDBLCLK = NM_FIRST - 6
NM_SETFOCUS = NM_FIRST - 7
NM_KILLFOCUS = NM_FIRST - 8
NM_CUSTOMDRAW = NM_FIRST - 12
NM_HOVER = NM_FIRST - 13
NM_NCHITTEST = NM_FIRST - 14  # uses NMMOUSE struct
NM_KEYDOWN = NM_FIRST - 15  # uses NMKEY struct
NM_RELEASEDCAPTURE = NM_FIRST - 16
NM_SETCURSOR = NM_FIRST - 17  # uses NMMOUSE struct
NM_CHAR = NM_FIRST - 18  # uses NMCHAR struct
MSGF_COMMCTRL_BEGINDRAG = 16896
MSGF_COMMCTRL_SIZEHEADER = 16897
MSGF_COMMCTRL_DRAGSELECT = 16898
MSGF_COMMCTRL_TOOLBARCUST = 16899
CDRF_DODEFAULT = 0
CDRF_NEWFONT = 2
CDRF_SKIPDEFAULT = 4
CDRF_NOTIFYPOSTPAINT = 16
CDRF_NOTIFYITEMDRAW = 32
CDRF_NOTIFYSUBITEMDRAW = 32  # flags are the same, we can distinguish by context
CDRF_NOTIFYPOSTERASE = 64
CDDS_PREPAINT = 1
CDDS_POSTPAINT = 2
CDDS_PREERASE = 3
CDDS_POSTERASE = 4
CDDS_ITEM = 65536
CDDS_ITEMPREPAINT = CDDS_ITEM | CDDS_PREPAINT
CDDS_ITEMPOSTPAINT = CDDS_ITEM | CDDS_POSTPAINT
CDDS_ITEMPREERASE = CDDS_ITEM | CDDS_PREERASE
CDDS_ITEMPOSTERASE = CDDS_ITEM | CDDS_POSTERASE
CDDS_SUBITEM = 131072
CDIS_SELECTED = 1
CDIS_GRAYED = 2
CDIS_DISABLED = 4
CDIS_CHECKED = 8
CDIS_FOCUS = 16
CDIS_DEFAULT = 32
CDIS_HOT = 64
CDIS_MARKED = 128
CDIS_INDETERMINATE = 256
CLR_NONE = -1  # 0xFFFFFFFFL
CLR_DEFAULT = -16777216  # 0xFF000000L
ILC_MASK = 1
ILC_COLOR = 0
ILC_COLORDDB = 254
ILC_COLOR4 = 4
ILC_COLOR8 = 8
ILC_COLOR16 = 16
ILC_COLOR24 = 24
ILC_COLOR32 = 32
ILC_PALETTE = 2048  # (not implemented)
ILD_NORMAL = 0
ILD_TRANSPARENT = 1
ILD_MASK = 16
ILD_IMAGE = 32
ILD_ROP = 64
ILD_BLEND25 = 2
ILD_BLEND50 = 4
ILD_OVERLAYMASK = 3840
ILD_SELECTED = ILD_BLEND50
ILD_FOCUS = ILD_BLEND25
ILD_BLEND = ILD_BLEND50
CLR_HILIGHT = CLR_DEFAULT
ILCF_MOVE = 0
ILCF_SWAP = 1
WC_HEADERA = "SysHeader32"
WC_HEADER = WC_HEADERA
HDS_HORZ = 0
HDS_BUTTONS = 2
HDS_HOTTRACK = 4
HDS_HIDDEN = 8
HDS_DRAGDROP = 64
HDS_FULLDRAG = 128
HDI_WIDTH = 1
HDI_HEIGHT = HDI_WIDTH
HDI_TEXT = 2
HDI_FORMAT = 4
HDI_LPARAM = 8
HDI_BITMAP = 16
HDI_IMAGE = 32
HDI_DI_SETITEM = 64
HDI_ORDER = 128
HDF_LEFT = 0
HDF_RIGHT = 1
HDF_CENTER = 2
HDF_JUSTIFYMASK = 3
HDF_RTLREADING = 4
HDF_OWNERDRAW = 32768
HDF_STRING = 16384
HDF_BITMAP = 8192
HDF_BITMAP_ON_RIGHT = 4096
HDF_IMAGE = 2048
HDM_GETITEMCOUNT = HDM_FIRST + 0
HDM_INSERTITEMA = HDM_FIRST + 1
HDM_INSERTITEMW = HDM_FIRST + 10
HDM_INSERTITEM = HDM_INSERTITEMA
HDM_DELETEITEM = HDM_FIRST + 2
HDM_GETITEMA = HDM_FIRST + 3
HDM_GETITEMW = HDM_FIRST + 11
HDM_GETITEM = HDM_GETITEMA
HDM_SETITEMA = HDM_FIRST + 4
HDM_SETITEMW = HDM_FIRST + 12
HDM_SETITEM = HDM_SETITEMA
HDM_LAYOUT = HDM_FIRST + 5
HHT_NOWHERE = 1
HHT_ONHEADER = 2
HHT_ONDIVIDER = 4
HHT_ONDIVOPEN = 8
HHT_ABOVE = 256
HHT_BELOW = 512
HHT_TORIGHT = 1024
HHT_TOLEFT = 2048
HDM_HITTEST = HDM_FIRST + 6
HDM_GETITEMRECT = HDM_FIRST + 7
HDM_SETIMAGELIST = HDM_FIRST + 8
HDM_GETIMAGELIST = HDM_FIRST + 9
HDM_ORDERTOINDEX = HDM_FIRST + 15
HDM_CREATEDRAGIMAGE = HDM_FIRST + 16  # wparam = which item (by index)
HDM_GETORDERARRAY = HDM_FIRST + 17
HDM_SETORDERARRAY = HDM_FIRST + 18
HDM_SETHOTDIVIDER = HDM_FIRST + 19
HDM_SETUNICODEFORMAT = CCM_SETUNICODEFORMAT
HDM_GETUNICODEFORMAT = CCM_GETUNICODEFORMAT
HDN_ITEMCHANGINGA = HDN_FIRST - 0
HDN_ITEMCHANGINGW = HDN_FIRST - 20
HDN_ITEMCHANGEDA = HDN_FIRST - 1
HDN_ITEMCHANGEDW = HDN_FIRST - 21
HDN_ITEMCLICKA = HDN_FIRST - 2
HDN_ITEMCLICKW = HDN_FIRST - 22
HDN_ITEMDBLCLICKA = HDN_FIRST - 3
HDN_ITEMDBLCLICKW = HDN_FIRST - 23
HDN_DIVIDERDBLCLICKA = HDN_FIRST - 5
HDN_DIVIDERDBLCLICKW = HDN_FIRST - 25
HDN_BEGINTRACKA = HDN_FIRST - 6
HDN_BEGINTRACKW = HDN_FIRST - 26
HDN_ENDTRACKA = HDN_FIRST - 7
HDN_ENDTRACKW = HDN_FIRST - 27
HDN_TRACKA = HDN_FIRST - 8
HDN_TRACKW = HDN_FIRST - 28
HDN_GETDISPINFOA = HDN_FIRST - 9
HDN_GETDISPINFOW = HDN_FIRST - 29
HDN_BEGINDRAG = HDN_FIRST - 10
HDN_ENDDRAG = HDN_FIRST - 11
HDN_ITEMCHANGING = HDN_ITEMCHANGINGA
HDN_ITEMCHANGED = HDN_ITEMCHANGEDA
HDN_ITEMCLICK = HDN_ITEMCLICKA
HDN_ITEMDBLCLICK = HDN_ITEMDBLCLICKA
HDN_DIVIDERDBLCLICK = HDN_DIVIDERDBLCLICKA
HDN_BEGINTRACK = HDN_BEGINTRACKA
HDN_ENDTRACK = HDN_ENDTRACKA
HDN_TRACK = HDN_TRACKA
HDN_GETDISPINFO = HDN_GETDISPINFOA
TOOLBARCLASSNAMEA = "ToolbarWindow32"
TOOLBARCLASSNAME = TOOLBARCLASSNAMEA
CMB_MASKED = 2
TBSTATE_CHECKED = 1
TBSTATE_PRESSED = 2
TBSTATE_ENABLED = 4
TBSTATE_HIDDEN = 8
TBSTATE_INDETERMINATE = 16
TBSTATE_WRAP = 32
TBSTATE_ELLIPSES = 64
TBSTATE_MARKED = 128
TBSTYLE_BUTTON = 0
TBSTYLE_SEP = 1
TBSTYLE_CHECK = 2
TBSTYLE_GROUP = 4
TBSTYLE_CHECKGROUP = TBSTYLE_GROUP | TBSTYLE_CHECK
TBSTYLE_DROPDOWN = 8
TBSTYLE_AUTOSIZE = 16  # automatically calculate the cx of the button
TBSTYLE_NOPREFIX = 32  # if this button should not have accel prefix
TBSTYLE_TOOLTIPS = 256
TBSTYLE_WRAPABLE = 512
TBSTYLE_ALTDRAG = 1024
TBSTYLE_FLAT = 2048
TBSTYLE_LIST = 4096
TBSTYLE_CUSTOMERASE = 8192
TBSTYLE_REGISTERDROP = 16384
TBSTYLE_TRANSPARENT = 32768
TBSTYLE_EX_DRAWDDARROWS = 1
BTNS_BUTTON = TBSTYLE_BUTTON
BTNS_SEP = TBSTYLE_SEP  # 0x0001
BTNS_CHECK = TBSTYLE_CHECK  # 0x0002
BTNS_GROUP = TBSTYLE_GROUP  # 0x0004
BTNS_CHECKGROUP = TBSTYLE_CHECKGROUP  # (TBSTYLE_GROUP | TBSTYLE_CHECK)
BTNS_DROPDOWN = TBSTYLE_DROPDOWN  # 0x0008
BTNS_AUTOSIZE = TBSTYLE_AUTOSIZE  # 0x0010; automatically calculate the cx of the button
BTNS_NOPREFIX = TBSTYLE_NOPREFIX  # 0x0020; this button should not have accel prefix
BTNS_SHOWTEXT = (
    64  # 0x0040              // ignored unless TBSTYLE_EX_MIXEDBUTTONS is set
)
BTNS_WHOLEDROPDOWN = (
    128  # 0x0080          // draw drop-down arrow, but without split arrow section
)
TBCDRF_NOEDGES = 65536  # Don't draw button edges
TBCDRF_HILITEHOTTRACK = 131072  # Use color of the button bk when hottracked
TBCDRF_NOOFFSET = 262144  # Don't offset button if pressed
TBCDRF_NOMARK = 524288  # Don't draw default highlight of image/text for TBSTATE_MARKED
TBCDRF_NOETCHEDEFFECT = 1048576  # Don't draw etched effect for disabled items
TB_ENABLEBUTTON = WM_USER + 1
TB_CHECKBUTTON = WM_USER + 2
TB_PRESSBUTTON = WM_USER + 3
TB_HIDEBUTTON = WM_USER + 4
TB_INDETERMINATE = WM_USER + 5
TB_MARKBUTTON = WM_USER + 6
TB_ISBUTTONENABLED = WM_USER + 9
TB_ISBUTTONCHECKED = WM_USER + 10
TB_ISBUTTONPRESSED = WM_USER + 11
TB_ISBUTTONHIDDEN = WM_USER + 12
TB_ISBUTTONINDETERMINATE = WM_USER + 13
TB_ISBUTTONHIGHLIGHTED = WM_USER + 14
TB_SETSTATE = WM_USER + 17
TB_GETSTATE = WM_USER + 18
TB_ADDBITMAP = WM_USER + 19
HINST_COMMCTRL = -1
IDB_STD_SMALL_COLOR = 0
IDB_STD_LARGE_COLOR = 1
IDB_VIEW_SMALL_COLOR = 4
IDB_VIEW_LARGE_COLOR = 5
IDB_HIST_SMALL_COLOR = 8
IDB_HIST_LARGE_COLOR = 9
STD_CUT = 0
STD_COPY = 1
STD_PASTE = 2
STD_UNDO = 3
STD_REDOW = 4
STD_DELETE = 5
STD_FILENEW = 6
STD_FILEOPEN = 7
STD_FILESAVE = 8
STD_PRINTPRE = 9
STD_PROPERTIES = 10
STD_HELP = 11
STD_FIND = 12
STD_REPLACE = 13
STD_PRINT = 14
VIEW_LARGEICONS = 0
VIEW_SMALLICONS = 1
VIEW_LIST = 2
VIEW_DETAILS = 3
VIEW_SORTNAME = 4
VIEW_SORTSIZE = 5
VIEW_SORTDATE = 6
VIEW_SORTTYPE = 7
VIEW_PARENTFOLDER = 8
VIEW_NETCONNECT = 9
VIEW_NETDISCONNECT = 10
VIEW_NEWFOLDER = 11
VIEW_VIEWMENU = 12
HIST_BACK = 0
HIST_FORWARD = 1
HIST_FAVORITES = 2
HIST_ADDTOFAVORITES = 3
HIST_VIEWTREE = 4
TB_ADDBUTTONSA = WM_USER + 20
TB_INSERTBUTTONA = WM_USER + 21
TB_ADDBUTTONS = WM_USER + 20
TB_INSERTBUTTON = WM_USER + 21
TB_DELETEBUTTON = WM_USER + 22
TB_GETBUTTON = WM_USER + 23
TB_BUTTONCOUNT = WM_USER + 24
TB_COMMANDTOINDEX = WM_USER + 25
TB_SAVERESTOREA = WM_USER + 26
TB_SAVERESTOREW = WM_USER + 76
TB_CUSTOMIZE = WM_USER + 27
TB_ADDSTRINGA = WM_USER + 28
TB_ADDSTRINGW = WM_USER + 77
TB_GETITEMRECT = WM_USER + 29
TB_BUTTONSTRUCTSIZE = WM_USER + 30
TB_SETBUTTONSIZE = WM_USER + 31
TB_SETBITMAPSIZE = WM_USER + 32
TB_AUTOSIZE = WM_USER + 33
TB_GETTOOLTIPS = WM_USER + 35
TB_SETTOOLTIPS = WM_USER + 36
TB_SETPARENT = WM_USER + 37
TB_SETROWS = WM_USER + 39
TB_GETROWS = WM_USER + 40
TB_SETCMDID = WM_USER + 42
TB_CHANGEBITMAP = WM_USER + 43
TB_GETBITMAP = WM_USER + 44
TB_GETBUTTONTEXTA = WM_USER + 45
TB_GETBUTTONTEXTW = WM_USER + 75
TB_REPLACEBITMAP = WM_USER + 46
TB_SETINDENT = WM_USER + 47
TB_SETIMAGELIST = WM_USER + 48
TB_GETIMAGELIST = WM_USER + 49
TB_LOADIMAGES = WM_USER + 50
TB_GETRECT = WM_USER + 51  # wParam is the Cmd instead of index
TB_SETHOTIMAGELIST = WM_USER + 52
TB_GETHOTIMAGELIST = WM_USER + 53
TB_SETDISABLEDIMAGELIST = WM_USER + 54
TB_GETDISABLEDIMAGELIST = WM_USER + 55
TB_SETSTYLE = WM_USER + 56
TB_GETSTYLE = WM_USER + 57
TB_GETBUTTONSIZE = WM_USER + 58
TB_SETBUTTONWIDTH = WM_USER + 59
TB_SETMAXTEXTROWS = WM_USER + 60
TB_GETTEXTROWS = WM_USER + 61
TB_GETBUTTONTEXT = TB_GETBUTTONTEXTA
TB_SAVERESTORE = TB_SAVERESTOREA
TB_ADDSTRING = TB_ADDSTRINGA
TB_GETOBJECT = WM_USER + 62  # wParam == IID, lParam void **ppv
TB_GETHOTITEM = WM_USER + 71
TB_SETHOTITEM = WM_USER + 72  # wParam == iHotItem
TB_SETANCHORHIGHLIGHT = WM_USER + 73  # wParam == TRUE/FALSE
TB_GETANCHORHIGHLIGHT = WM_USER + 74
TB_MAPACCELERATORA = WM_USER + 78  # wParam == ch, lParam int * pidBtn
TBIMHT_AFTER = 1  # TRUE = insert After iButton, otherwise before
TBIMHT_BACKGROUND = 2  # TRUE iff missed buttons completely
TB_GETINSERTMARK = WM_USER + 79  # lParam == LPTBINSERTMARK
TB_SETINSERTMARK = WM_USER + 80  # lParam == LPTBINSERTMARK
TB_INSERTMARKHITTEST = WM_USER + 81  # wParam == LPPOINT lParam == LPTBINSERTMARK
TB_MOVEBUTTON = WM_USER + 82
TB_GETMAXSIZE = WM_USER + 83  # lParam == LPSIZE
TB_SETEXTENDEDSTYLE = WM_USER + 84  # For TBSTYLE_EX_*
TB_GETEXTENDEDSTYLE = WM_USER + 85  # For TBSTYLE_EX_*
TB_GETPADDING = WM_USER + 86
TB_SETPADDING = WM_USER + 87
TB_SETINSERTMARKCOLOR = WM_USER + 88
TB_GETINSERTMARKCOLOR = WM_USER + 89
TB_SETCOLORSCHEME = CCM_SETCOLORSCHEME  # lParam is color scheme
TB_GETCOLORSCHEME = CCM_GETCOLORSCHEME  # fills in COLORSCHEME pointed to by lParam
TB_SETUNICODEFORMAT = CCM_SETUNICODEFORMAT
TB_GETUNICODEFORMAT = CCM_GETUNICODEFORMAT
TB_MAPACCELERATORW = WM_USER + 90  # wParam == ch, lParam int * pidBtn
TB_MAPACCELERATOR = TB_MAPACCELERATORA
TBBF_LARGE = 1
TB_GETBITMAPFLAGS = WM_USER + 41
TBIF_IMAGE = 1
TBIF_TEXT = 2
TBIF_STATE = 4
TBIF_STYLE = 8
TBIF_LPARAM = 16
TBIF_COMMAND = 32
TBIF_SIZE = 64
TB_GETBUTTONINFOW = WM_USER + 63
TB_SETBUTTONINFOW = WM_USER + 64
TB_GETBUTTONINFOA = WM_USER + 65
TB_SETBUTTONINFOA = WM_USER + 66
TB_INSERTBUTTONW = WM_USER + 67
TB_ADDBUTTONSW = WM_USER + 68
TB_HITTEST = WM_USER + 69
TB_SETDRAWTEXTFLAGS = WM_USER + 70  # wParam == mask lParam == bit values
TBN_GETBUTTONINFOA = TBN_FIRST - 0
TBN_GETBUTTONINFOW = TBN_FIRST - 20
TBN_BEGINDRAG = TBN_FIRST - 1
TBN_ENDDRAG = TBN_FIRST - 2
TBN_BEGINADJUST = TBN_FIRST - 3
TBN_ENDADJUST = TBN_FIRST - 4
TBN_RESET = TBN_FIRST - 5
TBN_QUERYINSERT = TBN_FIRST - 6
TBN_QUERYDELETE = TBN_FIRST - 7
TBN_TOOLBARCHANGE = TBN_FIRST - 8
TBN_CUSTHELP = TBN_FIRST - 9
TBN_DROPDOWN = TBN_FIRST - 10
TBN_GETOBJECT = TBN_FIRST - 12
HICF_OTHER = 0
HICF_MOUSE = 1  # Triggered by mouse
HICF_ARROWKEYS = 2  # Triggered by arrow keys
HICF_ACCELERATOR = 4  # Triggered by accelerator
HICF_DUPACCEL = 8  # This accelerator is not unique
HICF_ENTERING = 16  # idOld is invalid
HICF_LEAVING = 32  # idNew is invalid
HICF_RESELECT = 64  # hot item reselected
TBN_HOTITEMCHANGE = TBN_FIRST - 13
TBN_DRAGOUT = (
    TBN_FIRST - 14
)  # this is sent when the user clicks down on a button then drags off the button
TBN_DELETINGBUTTON = TBN_FIRST - 15  # uses TBNOTIFY
TBN_GETDISPINFOA = (
    TBN_FIRST - 16
)  # This is sent when the  toolbar needs  some display information
TBN_GETDISPINFOW = (
    TBN_FIRST - 17
)  # This is sent when the  toolbar needs  some display information
TBN_GETINFOTIPA = TBN_FIRST - 18
TBN_GETINFOTIPW = TBN_FIRST - 19
TBN_GETINFOTIP = TBN_GETINFOTIPA
TBNF_IMAGE = 1
TBNF_TEXT = 2
TBNF_DI_SETITEM = 268435456
TBN_GETDISPINFO = TBN_GETDISPINFOA
TBDDRET_DEFAULT = 0
TBDDRET_NODEFAULT = 1
TBDDRET_TREATPRESSED = 2  # Treat as a standard press button
TBN_GETBUTTONINFO = TBN_GETBUTTONINFOA
REBARCLASSNAMEA = "ReBarWindow32"
REBARCLASSNAME = REBARCLASSNAMEA
RBIM_IMAGELIST = 1
RBS_TOOLTIPS = 256
RBS_VARHEIGHT = 512
RBS_BANDBORDERS = 1024
RBS_FIXEDORDER = 2048
RBS_REGISTERDROP = 4096
RBS_AUTOSIZE = 8192
RBS_VERTICALGRIPPER = (
    16384  # this always has the vertical gripper (default for horizontal mode)
)
RBS_DBLCLKTOGGLE = 32768
RBBS_BREAK = 1  # break to new line
RBBS_FIXEDSIZE = 2  # band can't be sized
RBBS_CHILDEDGE = 4  # edge around top & bottom of child window
RBBS_HIDDEN = 8  # don't show
RBBS_NOVERT = 16  # don't show when vertical
RBBS_FIXEDBMP = 32  # bitmap doesn't move during band resize
RBBS_VARIABLEHEIGHT = 64  # allow autosizing of this child vertically
RBBS_GRIPPERALWAYS = 128  # always show the gripper
RBBS_NOGRIPPER = 256  # never show the gripper
RBBIM_STYLE = 1
RBBIM_COLORS = 2
RBBIM_TEXT = 4
RBBIM_IMAGE = 8
RBBIM_CHILD = 16
RBBIM_CHILDSIZE = 32
RBBIM_SIZE = 64
RBBIM_BACKGROUND = 128
RBBIM_ID = 256
RBBIM_IDEALSIZE = 512
RBBIM_LPARAM = 1024
RB_INSERTBANDA = WM_USER + 1
RB_DELETEBAND = WM_USER + 2
RB_GETBARINFO = WM_USER + 3
RB_SETBARINFO = WM_USER + 4
RB_SETBANDINFOA = WM_USER + 6
RB_SETPARENT = WM_USER + 7
RB_HITTEST = WM_USER + 8
RB_GETRECT = WM_USER + 9
RB_INSERTBANDW = WM_USER + 10
RB_SETBANDINFOW = WM_USER + 11
RB_GETBANDCOUNT = WM_USER + 12
RB_GETROWCOUNT = WM_USER + 13
RB_GETROWHEIGHT = WM_USER + 14
RB_IDTOINDEX = WM_USER + 16  # wParam == id
RB_GETTOOLTIPS = WM_USER + 17
RB_SETTOOLTIPS = WM_USER + 18
RB_SETBKCOLOR = WM_USER + 19  # sets the default BK color
RB_GETBKCOLOR = WM_USER + 20  # defaults to CLR_NONE
RB_SETTEXTCOLOR = WM_USER + 21
RB_GETTEXTCOLOR = WM_USER + 22  # defaults to 0x00000000
RB_SIZETORECT = (
    WM_USER + 23
)  # resize the rebar/break bands and such to this rect (lparam)
RB_SETCOLORSCHEME = CCM_SETCOLORSCHEME  # lParam is color scheme
RB_GETCOLORSCHEME = CCM_GETCOLORSCHEME  # fills in COLORSCHEME pointed to by lParam
RB_INSERTBAND = RB_INSERTBANDA
RB_SETBANDINFO = RB_SETBANDINFOA
RB_BEGINDRAG = WM_USER + 24
RB_ENDDRAG = WM_USER + 25
RB_DRAGMOVE = WM_USER + 26
RB_GETBARHEIGHT = WM_USER + 27
RB_GETBANDINFOW = WM_USER + 28
RB_GETBANDINFOA = WM_USER + 29
RB_GETBANDINFO = RB_GETBANDINFOA
RB_MINIMIZEBAND = WM_USER + 30
RB_MAXIMIZEBAND = WM_USER + 31
RB_GETDROPTARGET = CCM_GETDROPTARGET
RB_GETBANDBORDERS = (
    WM_USER + 34
)  # returns in lparam = lprc the amount of edges added to band wparam
RB_SHOWBAND = WM_USER + 35  # show/hide band
RB_SETPALETTE = WM_USER + 37
RB_GETPALETTE = WM_USER + 38
RB_MOVEBAND = WM_USER + 39
RB_SETUNICODEFORMAT = CCM_SETUNICODEFORMAT
RB_GETUNICODEFORMAT = CCM_GETUNICODEFORMAT
RBN_HEIGHTCHANGE = RBN_FIRST - 0
RBN_GETOBJECT = RBN_FIRST - 1
RBN_LAYOUTCHANGED = RBN_FIRST - 2
RBN_AUTOSIZE = RBN_FIRST - 3
RBN_BEGINDRAG = RBN_FIRST - 4
RBN_ENDDRAG = RBN_FIRST - 5
RBN_DELETINGBAND = RBN_FIRST - 6  # Uses NMREBAR
RBN_DELETEDBAND = RBN_FIRST - 7  # Uses NMREBAR
RBN_CHILDSIZE = RBN_FIRST - 8
RBNM_ID = 1
RBNM_STYLE = 2
RBNM_LPARAM = 4
RBHT_NOWHERE = 1
RBHT_CAPTION = 2
RBHT_CLIENT = 3
RBHT_GRABBER = 4
TOOLTIPS_CLASSA = "tooltips_class32"
TOOLTIPS_CLASS = TOOLTIPS_CLASSA
TTS_ALWAYSTIP = 1
TTS_NOPREFIX = 2
TTF_IDISHWND = 1
TTF_CENTERTIP = 2
TTF_RTLREADING = 4
TTF_SUBCLASS = 16
TTF_TRACK = 32
TTF_ABSOLUTE = 128
TTF_TRANSPARENT = 256
TTF_DI_SETITEM = 32768  # valid only on the TTN_NEEDTEXT callback
TTDT_AUTOMATIC = 0
TTDT_RESHOW = 1
TTDT_AUTOPOP = 2
TTDT_INITIAL = 3
TTM_ACTIVATE = WM_USER + 1
TTM_SETDELAYTIME = WM_USER + 3
TTM_ADDTOOLA = WM_USER + 4
TTM_ADDTOOLW = WM_USER + 50
TTM_DELTOOLA = WM_USER + 5
TTM_DELTOOLW = WM_USER + 51
TTM_NEWTOOLRECTA = WM_USER + 6
TTM_NEWTOOLRECTW = WM_USER + 52
TTM_RELAYEVENT = WM_USER + 7
TTM_GETTOOLINFOA = WM_USER + 8
TTM_GETTOOLINFOW = WM_USER + 53
TTM_SETTOOLINFOA = WM_USER + 9
TTM_SETTOOLINFOW = WM_USER + 54
TTM_HITTESTA = WM_USER + 10
TTM_HITTESTW = WM_USER + 55
TTM_GETTEXTA = WM_USER + 11
TTM_GETTEXTW = WM_USER + 56
TTM_UPDATETIPTEXTA = WM_USER + 12
TTM_UPDATETIPTEXTW = WM_USER + 57
TTM_GETTOOLCOUNT = WM_USER + 13
TTM_ENUMTOOLSA = WM_USER + 14
TTM_ENUMTOOLSW = WM_USER + 58
TTM_GETCURRENTTOOLA = WM_USER + 15
TTM_GETCURRENTTOOLW = WM_USER + 59
TTM_WINDOWFROMPOINT = WM_USER + 16
TTM_TRACKACTIVATE = WM_USER + 17  # wParam = TRUE/FALSE start end  lparam = LPTOOLINFO
TTM_TRACKPOSITION = WM_USER + 18  # lParam = dwPos
TTM_SETTIPBKCOLOR = WM_USER + 19
TTM_SETTIPTEXTCOLOR = WM_USER + 20
TTM_GETDELAYTIME = WM_USER + 21
TTM_GETTIPBKCOLOR = WM_USER + 22
TTM_GETTIPTEXTCOLOR = WM_USER + 23
TTM_SETMAXTIPWIDTH = WM_USER + 24
TTM_GETMAXTIPWIDTH = WM_USER + 25
TTM_SETMARGIN = WM_USER + 26  # lParam = lprc
TTM_GETMARGIN = WM_USER + 27  # lParam = lprc
TTM_POP = WM_USER + 28
TTM_UPDATE = WM_USER + 29
TTM_ADDTOOL = TTM_ADDTOOLA
TTM_DELTOOL = TTM_DELTOOLA
TTM_NEWTOOLRECT = TTM_NEWTOOLRECTA
TTM_GETTOOLINFO = TTM_GETTOOLINFOA
TTM_SETTOOLINFO = TTM_SETTOOLINFOA
TTM_HITTEST = TTM_HITTESTA
TTM_GETTEXT = TTM_GETTEXTA
TTM_UPDATETIPTEXT = TTM_UPDATETIPTEXTA
TTM_ENUMTOOLS = TTM_ENUMTOOLSA
TTM_GETCURRENTTOOL = TTM_GETCURRENTTOOLA
TTN_GETDISPINFOA = TTN_FIRST - 0
TTN_GETDISPINFOW = TTN_FIRST - 10
TTN_SHOW = TTN_FIRST - 1
TTN_POP = TTN_FIRST - 2
TTN_GETDISPINFO = TTN_GETDISPINFOA
TTN_NEEDTEXT = TTN_GETDISPINFO
TTN_NEEDTEXTA = TTN_GETDISPINFOA
TTN_NEEDTEXTW = TTN_GETDISPINFOW
SBARS_SIZEGRIP = 256
SBARS_TOOLTIPS = 2048
STATUSCLASSNAMEA = "msctls_statusbar32"
STATUSCLASSNAME = STATUSCLASSNAMEA
SB_SETTEXTA = WM_USER + 1
SB_SETTEXTW = WM_USER + 11
SB_GETTEXTA = WM_USER + 2
SB_GETTEXTW = WM_USER + 13
SB_GETTEXTLENGTHA = WM_USER + 3
SB_GETTEXTLENGTHW = WM_USER + 12
SB_GETTEXT = SB_GETTEXTA
SB_SETTEXT = SB_SETTEXTA
SB_GETTEXTLENGTH = SB_GETTEXTLENGTHA
SB_SETPARTS = WM_USER + 4
SB_GETPARTS = WM_USER + 6
SB_GETBORDERS = WM_USER + 7
SB_SETMINHEIGHT = WM_USER + 8
SB_SIMPLE = WM_USER + 9
SB_GETRECT = WM_USER + 10
SB_ISSIMPLE = WM_USER + 14
SB_SETICON = WM_USER + 15
SB_SETTIPTEXTA = WM_USER + 16
SB_SETTIPTEXTW = WM_USER + 17
SB_GETTIPTEXTA = WM_USER + 18
SB_GETTIPTEXTW = WM_USER + 19
SB_GETICON = WM_USER + 20
SB_SETTIPTEXT = SB_SETTIPTEXTA
SB_GETTIPTEXT = SB_GETTIPTEXTA
SB_SETUNICODEFORMAT = CCM_SETUNICODEFORMAT
SB_GETUNICODEFORMAT = CCM_GETUNICODEFORMAT
SBT_OWNERDRAW = 4096
SBT_NOBORDERS = 256
SBT_POPOUT = 512
SBT_RTLREADING = 1024
SBT_NOTABPARSING = 2048
SBT_TOOLTIPS = 2048
SB_SETBKCOLOR = CCM_SETBKCOLOR  # lParam = bkColor
SBN_SIMPLEMODECHANGE = SBN_FIRST - 0
TRACKBAR_CLASSA = "msctls_trackbar32"
TRACKBAR_CLASS = TRACKBAR_CLASSA
TBS_AUTOTICKS = 1
TBS_VERT = 2
TBS_HORZ = 0
TBS_TOP = 4
TBS_BOTTOM = 0
TBS_LEFT = 4
TBS_RIGHT = 0
TBS_BOTH = 8
TBS_NOTICKS = 16
TBS_ENABLESELRANGE = 32
TBS_FIXEDLENGTH = 64
TBS_NOTHUMB = 128
TBS_TOOLTIPS = 256
TBM_GETPOS = WM_USER
TBM_GETRANGEMIN = WM_USER + 1
TBM_GETRANGEMAX = WM_USER + 2
TBM_GETTIC = WM_USER + 3
TBM_SETTIC = WM_USER + 4
TBM_SETPOS = WM_USER + 5
TBM_SETRANGE = WM_USER + 6
TBM_SETRANGEMIN = WM_USER + 7
TBM_SETRANGEMAX = WM_USER + 8
TBM_CLEARTICS = WM_USER + 9
TBM_SETSEL = WM_USER + 10
TBM_SETSELSTART = WM_USER + 11
TBM_SETSELEND = WM_USER + 12
TBM_GETPTICS = WM_USER + 14
TBM_GETTICPOS = WM_USER + 15
TBM_GETNUMTICS = WM_USER + 16
TBM_GETSELSTART = WM_USER + 17
TBM_GETSELEND = WM_USER + 18
TBM_CLEARSEL = WM_USER + 19
TBM_SETTICFREQ = WM_USER + 20
TBM_SETPAGESIZE = WM_USER + 21
TBM_GETPAGESIZE = WM_USER + 22
TBM_SETLINESIZE = WM_USER + 23
TBM_GETLINESIZE = WM_USER + 24
TBM_GETTHUMBRECT = WM_USER + 25
TBM_GETCHANNELRECT = WM_USER + 26
TBM_SETTHUMBLENGTH = WM_USER + 27
TBM_GETTHUMBLENGTH = WM_USER + 28
TBM_SETTOOLTIPS = WM_USER + 29
TBM_GETTOOLTIPS = WM_USER + 30
TBM_SETTIPSIDE = WM_USER + 31
TBTS_TOP = 0
TBTS_LEFT = 1
TBTS_BOTTOM = 2
TBTS_RIGHT = 3
TBM_SETBUDDY = WM_USER + 32  # wparam = BOOL fLeft; (or right)
TBM_GETBUDDY = WM_USER + 33  # wparam = BOOL fLeft; (or right)
TBM_SETUNICODEFORMAT = CCM_SETUNICODEFORMAT
TBM_GETUNICODEFORMAT = CCM_GETUNICODEFORMAT
TB_LINEUP = 0
TB_LINEDOWN = 1
TB_PAGEUP = 2
TB_PAGEDOWN = 3
TB_THUMBPOSITION = 4
TB_THUMBTRACK = 5
TB_TOP = 6
TB_BOTTOM = 7
TB_ENDTRACK = 8
TBCD_TICS = 1
TBCD_THUMB = 2
TBCD_CHANNEL = 3
DL_BEGINDRAG = WM_USER + 133
DL_DRAGGING = WM_USER + 134
DL_DROPPED = WM_USER + 135
DL_CANCELDRAG = WM_USER + 136
DL_CURSORSET = 0
DL_STOPCURSOR = 1
DL_COPYCURSOR = 2
DL_MOVECURSOR = 3
DRAGLISTMSGSTRING = "commctrl_DragListMsg"
UPDOWN_CLASSA = "msctls_updown32"
UPDOWN_CLASS = UPDOWN_CLASSA
UD_MAXVAL = 32767
UD_MINVAL = -UD_MAXVAL
UDS_WRAP = 1
UDS_SETBUDDYINT = 2
UDS_ALIGNRIGHT = 4
UDS_ALIGNLEFT = 8
UDS_AUTOBUDDY = 16
UDS_ARROWKEYS = 32
UDS_HORZ = 64
UDS_NOTHOUSANDS = 128
UDS_HOTTRACK = 256
UDM_SETRANGE = WM_USER + 101
UDM_GETRANGE = WM_USER + 102
UDM_SETPOS = WM_USER + 103
UDM_GETPOS = WM_USER + 104
UDM_SETBUDDY = WM_USER + 105
UDM_GETBUDDY = WM_USER + 106
UDM_SETACCEL = WM_USER + 107
UDM_GETACCEL = WM_USER + 108
UDM_SETBASE = WM_USER + 109
UDM_GETBASE = WM_USER + 110
UDM_SETRANGE32 = WM_USER + 111
UDM_GETRANGE32 = WM_USER + 112  # wParam & lParam are LPINT
UDM_SETUNICODEFORMAT = CCM_SETUNICODEFORMAT
UDM_GETUNICODEFORMAT = CCM_GETUNICODEFORMAT
UDN_DELTAPOS = UDN_FIRST - 1
PROGRESS_CLASSA = "msctls_progress32"
PROGRESS_CLASS = PROGRESS_CLASSA
PBS_SMOOTH = 1
PBS_VERTICAL = 4
PBM_SETRANGE = WM_USER + 1
PBM_SETPOS = WM_USER + 2
PBM_DELTAPOS = WM_USER + 3
PBM_SETSTEP = WM_USER + 4
PBM_STEPIT = WM_USER + 5
PBM_SETRANGE32 = WM_USER + 6  # lParam = high, wParam = low
PBM_GETRANGE = (
    WM_USER + 7
)  # wParam = return (TRUE ? low : high). lParam = PPBRANGE or NULL
PBM_GETPOS = WM_USER + 8
PBM_SETBARCOLOR = WM_USER + 9  # lParam = bar color
PBM_SETBKCOLOR = CCM_SETBKCOLOR  # lParam = bkColor
HOTKEYF_SHIFT = 1
HOTKEYF_CONTROL = 2
HOTKEYF_ALT = 4
HOTKEYF_EXT = 8
HKCOMB_NONE = 1
HKCOMB_S = 2
HKCOMB_C = 4
HKCOMB_A = 8
HKCOMB_SC = 16
HKCOMB_SA = 32
HKCOMB_CA = 64
HKCOMB_SCA = 128
HKM_SETHOTKEY = WM_USER + 1
HKM_GETHOTKEY = WM_USER + 2
HKM_SETRULES = WM_USER + 3
HOTKEY_CLASSA = "msctls_hotkey32"
HOTKEY_CLASS = HOTKEY_CLASSA
CCS_TOP = 0x00000001
CCS_NOMOVEY = 0x00000002
CCS_BOTTOM = 0x00000003
CCS_NORESIZE = 0x00000004
CCS_NOPARENTALIGN = 0x00000008
CCS_ADJUSTABLE = 0x00000020
CCS_NODIVIDER = 0x00000040
CCS_VERT = 0x00000080
CCS_LEFT = CCS_VERT | CCS_TOP
CCS_RIGHT = CCS_VERT | CCS_BOTTOM
CCS_NOMOVEX = CCS_VERT | CCS_NOMOVEY
WC_LISTVIEWA = "SysListView32"
WC_LISTVIEW = WC_LISTVIEWA
LVS_ICON = 0
LVS_REPORT = 1
LVS_SMALLICON = 2
LVS_LIST = 3
LVS_TYPEMASK = 3
LVS_SINGLESEL = 4
LVS_SHOWSELALWAYS = 8
LVS_SORTASCENDING = 16
LVS_SORTDESCENDING = 32
LVS_SHAREIMAGELISTS = 64
LVS_NOLABELWRAP = 128
LVS_AUTOARRANGE = 256
LVS_EDITLABELS = 512
LVS_OWNERDATA = 4096
LVS_NOSCROLL = 8192
LVS_TYPESTYLEMASK = 64512
LVS_ALIGNTOP = 0
LVS_ALIGNLEFT = 2048
LVS_ALIGNMASK = 3072
LVS_OWNERDRAWFIXED = 1024
LVS_NOCOLUMNHEADER = 16384
LVS_NOSORTHEADER = 32768
LVM_SETUNICODEFORMAT = CCM_SETUNICODEFORMAT
LVM_GETUNICODEFORMAT = CCM_GETUNICODEFORMAT
LVM_GETBKCOLOR = LVM_FIRST + 0
LVM_SETBKCOLOR = LVM_FIRST + 1
LVM_GETIMAGELIST = LVM_FIRST + 2
LVSIL_NORMAL = 0
LVSIL_SMALL = 1
LVSIL_STATE = 2
LVM_SETIMAGELIST = LVM_FIRST + 3
LVM_GETITEMCOUNT = LVM_FIRST + 4
LVIF_TEXT = 1
LVIF_IMAGE = 2
LVIF_PARAM = 4
LVIF_STATE = 8
LVIF_INDENT = 16
LVIF_NORECOMPUTE = 2048
LVIS_FOCUSED = 1
LVIS_SELECTED = 2
LVIS_CUT = 4
LVIS_DROPHILITED = 8
LVIS_ACTIVATING = 32
LVIS_OVERLAYMASK = 3840
LVIS_STATEIMAGEMASK = 61440
I_INDENTCALLBACK = -1
LPSTR_TEXTCALLBACKA = -1
LPSTR_TEXTCALLBACK = LPSTR_TEXTCALLBACKA
I_IMAGECALLBACK = -1
LVM_GETITEMA = LVM_FIRST + 5
LVM_GETITEMW = LVM_FIRST + 75
LVM_GETITEM = LVM_GETITEMA
LVM_SETITEMA = LVM_FIRST + 6
LVM_SETITEMW = LVM_FIRST + 76
LVM_SETITEM = LVM_SETITEMA
LVM_INSERTITEMA = LVM_FIRST + 7
LVM_INSERTITEMW = LVM_FIRST + 77
LVM_INSERTITEM = LVM_INSERTITEMA
LVM_DELETEITEM = LVM_FIRST + 8
LVM_DELETEALLITEMS = LVM_FIRST + 9
LVM_GETCALLBACKMASK = LVM_FIRST + 10
LVM_SETCALLBACKMASK = LVM_FIRST + 11
LVNI_ALL = 0
LVNI_FOCUSED = 1
LVNI_SELECTED = 2
LVNI_CUT = 4
LVNI_DROPHILITED = 8
LVNI_ABOVE = 256
LVNI_BELOW = 512
LVNI_TOLEFT = 1024
LVNI_TORIGHT = 2048
LVM_GETNEXTITEM = LVM_FIRST + 12
LVFI_PARAM = 1
LVFI_STRING = 2
LVFI_PARTIAL = 8
LVFI_WRAP = 32
LVFI_NEARESTXY = 64
LVM_FINDITEMA = LVM_FIRST + 13
LVM_FINDITEMW = LVM_FIRST + 83
LVM_FINDITEM = LVM_FINDITEMA
LVIR_BOUNDS = 0
LVIR_ICON = 1
LVIR_LABEL = 2
LVIR_SELECTBOUNDS = 3
LVM_GETITEMRECT = LVM_FIRST + 14
LVM_SETITEMPOSITION = LVM_FIRST + 15
LVM_GETITEMPOSITION = LVM_FIRST + 16
LVM_GETSTRINGWIDTHA = LVM_FIRST + 17
LVM_GETSTRINGWIDTHW = LVM_FIRST + 87
LVM_GETSTRINGWIDTH = LVM_GETSTRINGWIDTHA
LVHT_NOWHERE = 1
LVHT_ONITEMICON = 2
LVHT_ONITEMLABEL = 4
LVHT_ONITEMSTATEICON = 8
LVHT_ONITEM = LVHT_ONITEMICON | LVHT_ONITEMLABEL | LVHT_ONITEMSTATEICON
LVHT_ABOVE = 8
LVHT_BELOW = 16
LVHT_TORIGHT = 32
LVHT_TOLEFT = 64
LVM_HITTEST = LVM_FIRST + 18
LVM_ENSUREVISIBLE = LVM_FIRST + 19
LVM_SCROLL = LVM_FIRST + 20
LVM_REDRAWITEMS = LVM_FIRST + 21
LVA_DEFAULT = 0
LVA_ALIGNLEFT = 1
LVA_ALIGNTOP = 2
LVA_SNAPTOGRID = 5
LVM_ARRANGE = LVM_FIRST + 22
LVM_EDITLABELA = LVM_FIRST + 23
LVM_EDITLABELW = LVM_FIRST + 118
LVM_EDITLABEL = LVM_EDITLABELA
LVM_GETEDITCONTROL = LVM_FIRST + 24
LVCF_FMT = 1
LVCF_WIDTH = 2
LVCF_TEXT = 4
LVCF_SUBITEM = 8
LVCF_IMAGE = 16
LVCF_ORDER = 32
LVCFMT_LEFT = 0
LVCFMT_RIGHT = 1
LVCFMT_CENTER = 2
LVCFMT_JUSTIFYMASK = 3
LVCFMT_IMAGE = 2048
LVCFMT_BITMAP_ON_RIGHT = 4096
LVCFMT_COL_HAS_IMAGES = 32768
LVM_GETCOLUMNA = LVM_FIRST + 25
LVM_GETCOLUMNW = LVM_FIRST + 95
LVM_GETCOLUMN = LVM_GETCOLUMNA
LVM_SETCOLUMNA = LVM_FIRST + 26
LVM_SETCOLUMNW = LVM_FIRST + 96
LVM_SETCOLUMN = LVM_SETCOLUMNA
LVM_INSERTCOLUMNA = LVM_FIRST + 27
LVM_INSERTCOLUMNW = LVM_FIRST + 97
LVM_INSERTCOLUMN = LVM_INSERTCOLUMNA
LVM_DELETECOLUMN = LVM_FIRST + 28
LVM_GETCOLUMNWIDTH = LVM_FIRST + 29
LVSCW_AUTOSIZE = -1
LVSCW_AUTOSIZE_USEHEADER = -2
LVM_SETCOLUMNWIDTH = LVM_FIRST + 30
LVM_GETHEADER = LVM_FIRST + 31
LVM_CREATEDRAGIMAGE = LVM_FIRST + 33
LVM_GETVIEWRECT = LVM_FIRST + 34
LVM_GETTEXTCOLOR = LVM_FIRST + 35
LVM_SETTEXTCOLOR = LVM_FIRST + 36
LVM_GETTEXTBKCOLOR = LVM_FIRST + 37
LVM_SETTEXTBKCOLOR = LVM_FIRST + 38
LVM_GETTOPINDEX = LVM_FIRST + 39
LVM_GETCOUNTPERPAGE = LVM_FIRST + 40
LVM_GETORIGIN = LVM_FIRST + 41
LVM_UPDATE = LVM_FIRST + 42
LVM_SETITEMSTATE = LVM_FIRST + 43
LVM_GETITEMSTATE = LVM_FIRST + 44
LVM_GETITEMTEXTA = LVM_FIRST + 45
LVM_GETITEMTEXTW = LVM_FIRST + 115
LVM_GETITEMTEXT = LVM_GETITEMTEXTA
LVM_SETITEMTEXTA = LVM_FIRST + 46
LVM_SETITEMTEXTW = LVM_FIRST + 116
LVM_SETITEMTEXT = LVM_SETITEMTEXTA
LVSICF_NOINVALIDATEALL = 1
LVSICF_NOSCROLL = 2
LVM_SETITEMCOUNT = LVM_FIRST + 47
LVM_SORTITEMS = LVM_FIRST + 48
LVM_SETITEMPOSITION32 = LVM_FIRST + 49
LVM_GETSELECTEDCOUNT = LVM_FIRST + 50
LVM_GETITEMSPACING = LVM_FIRST + 51
LVM_GETISEARCHSTRINGA = LVM_FIRST + 52
LVM_GETISEARCHSTRINGW = LVM_FIRST + 117
LVM_GETISEARCHSTRING = LVM_GETISEARCHSTRINGA
LVM_SETICONSPACING = LVM_FIRST + 53
LVM_SETEXTENDEDLISTVIEWSTYLE = LVM_FIRST + 54  # optional wParam == mask
LVM_GETEXTENDEDLISTVIEWSTYLE = LVM_FIRST + 55
LVS_EX_GRIDLINES = 1
LVS_EX_SUBITEMIMAGES = 2
LVS_EX_CHECKBOXES = 4
LVS_EX_TRACKSELECT = 8
LVS_EX_HEADERDRAGDROP = 16
LVS_EX_FULLROWSELECT = 32  # applies to report mode only
LVS_EX_ONECLICKACTIVATE = 64
LVS_EX_TWOCLICKACTIVATE = 128
LVS_EX_FLATSB = 256
LVS_EX_REGIONAL = 512
LVS_EX_INFOTIP = 1024  # listview does InfoTips for you
LVS_EX_UNDERLINEHOT = 2048
LVS_EX_UNDERLINECOLD = 4096
LVS_EX_MULTIWORKAREAS = 8192
LVM_GETSUBITEMRECT = LVM_FIRST + 56
LVM_SUBITEMHITTEST = LVM_FIRST + 57
LVM_SETCOLUMNORDERARRAY = LVM_FIRST + 58
LVM_GETCOLUMNORDERARRAY = LVM_FIRST + 59
LVM_SETHOTITEM = LVM_FIRST + 60
LVM_GETHOTITEM = LVM_FIRST + 61
LVM_SETHOTCURSOR = LVM_FIRST + 62
LVM_GETHOTCURSOR = LVM_FIRST + 63
LVM_APPROXIMATEVIEWRECT = LVM_FIRST + 64
LV_MAX_WORKAREAS = 16
LVM_SETWORKAREAS = LVM_FIRST + 65
LVM_GETWORKAREAS = LVM_FIRST + 70
LVM_GETNUMBEROFWORKAREAS = LVM_FIRST + 73
LVM_GETSELECTIONMARK = LVM_FIRST + 66
LVM_SETSELECTIONMARK = LVM_FIRST + 67
LVM_SETHOVERTIME = LVM_FIRST + 71
LVM_GETHOVERTIME = LVM_FIRST + 72
LVM_SETTOOLTIPS = LVM_FIRST + 74
LVM_GETTOOLTIPS = LVM_FIRST + 78
LVBKIF_SOURCE_NONE = 0
LVBKIF_SOURCE_HBITMAP = 1
LVBKIF_SOURCE_URL = 2
LVBKIF_SOURCE_MASK = 3
LVBKIF_STYLE_NORMAL = 0
LVBKIF_STYLE_TILE = 16
LVBKIF_STYLE_MASK = 16
LVM_SETBKIMAGEA = LVM_FIRST + 68
LVM_SETBKIMAGEW = LVM_FIRST + 138
LVM_GETBKIMAGEA = LVM_FIRST + 69
LVM_GETBKIMAGEW = LVM_FIRST + 139
LVKF_ALT = 1
LVKF_CONTROL = 2
LVKF_SHIFT = 4
LVN_ITEMCHANGING = LVN_FIRST - 0
LVN_ITEMCHANGED = LVN_FIRST - 1
LVN_INSERTITEM = LVN_FIRST - 2
LVN_DELETEITEM = LVN_FIRST - 3
LVN_DELETEALLITEMS = LVN_FIRST - 4
LVN_BEGINLABELEDITA = LVN_FIRST - 5
LVN_BEGINLABELEDITW = LVN_FIRST - 75
LVN_ENDLABELEDITA = LVN_FIRST - 6
LVN_ENDLABELEDITW = LVN_FIRST - 76
LVN_COLUMNCLICK = LVN_FIRST - 8
LVN_BEGINDRAG = LVN_FIRST - 9
LVN_BEGINRDRAG = LVN_FIRST - 11
LVN_ODCACHEHINT = LVN_FIRST - 13
LVN_ODFINDITEMA = LVN_FIRST - 52
LVN_ODFINDITEMW = LVN_FIRST - 79
LVN_ITEMACTIVATE = LVN_FIRST - 14
LVN_ODSTATECHANGED = LVN_FIRST - 15
LVN_ODFINDITEM = LVN_ODFINDITEMA
LVN_HOTTRACK = LVN_FIRST - 21
LVN_GETDISPINFOA = LVN_FIRST - 50
LVN_GETDISPINFOW = LVN_FIRST - 77
LVN_SETDISPINFOA = LVN_FIRST - 51
LVN_SETDISPINFOW = LVN_FIRST - 78
LVN_BEGINLABELEDIT = LVN_BEGINLABELEDITA
LVN_ENDLABELEDIT = LVN_ENDLABELEDITA
LVN_GETDISPINFO = LVN_GETDISPINFOA
LVN_SETDISPINFO = LVN_SETDISPINFOA
LVIF_DI_SETITEM = 4096
LVN_KEYDOWN = LVN_FIRST - 55
LVN_MARQUEEBEGIN = LVN_FIRST - 56
LVGIT_UNFOLDED = 1
LVN_GETINFOTIPA = LVN_FIRST - 57
LVN_GETINFOTIPW = LVN_FIRST - 58
LVN_GETINFOTIP = LVN_GETINFOTIPA
WC_TREEVIEWA = "SysTreeView32"
WC_TREEVIEW = WC_TREEVIEWA
TVS_HASBUTTONS = 1
TVS_HASLINES = 2
TVS_LINESATROOT = 4
TVS_EDITLABELS = 8
TVS_DISABLEDRAGDROP = 16
TVS_SHOWSELALWAYS = 32
TVS_RTLREADING = 64
TVS_NOTOOLTIPS = 128
TVS_CHECKBOXES = 256
TVS_TRACKSELECT = 512
TVS_SINGLEEXPAND = 1024
TVS_INFOTIP = 2048
TVS_FULLROWSELECT = 4096
TVS_NOSCROLL = 8192
TVS_NONEVENHEIGHT = 16384
TVIF_TEXT = 1
TVIF_IMAGE = 2
TVIF_PARAM = 4
TVIF_STATE = 8
TVIF_HANDLE = 16
TVIF_SELECTEDIMAGE = 32
TVIF_CHILDREN = 64
TVIF_INTEGRAL = 128
TVIS_SELECTED = 2
TVIS_CUT = 4
TVIS_DROPHILITED = 8
TVIS_BOLD = 16
TVIS_EXPANDED = 32
TVIS_EXPANDEDONCE = 64
TVIS_EXPANDPARTIAL = 128
TVIS_OVERLAYMASK = 3840
TVIS_STATEIMAGEMASK = 61440
TVIS_USERMASK = 61440
I_CHILDRENCALLBACK = -1
TVI_ROOT = -65536
TVI_FIRST = -65535
TVI_LAST = -65534
TVI_SORT = -65533
TVM_INSERTITEMA = TV_FIRST + 0
TVM_INSERTITEMW = TV_FIRST + 50
TVM_INSERTITEM = TVM_INSERTITEMA
TVM_DELETEITEM = TV_FIRST + 1
TVM_EXPAND = TV_FIRST + 2
TVE_COLLAPSE = 1
TVE_EXPAND = 2
TVE_TOGGLE = 3
TVE_EXPANDPARTIAL = 16384
TVE_COLLAPSERESET = 32768
TVM_GETITEMRECT = TV_FIRST + 4
TVM_GETCOUNT = TV_FIRST + 5
TVM_GETINDENT = TV_FIRST + 6
TVM_SETINDENT = TV_FIRST + 7
TVM_GETIMAGELIST = TV_FIRST + 8
TVSIL_NORMAL = 0
TVSIL_STATE = 2
TVM_SETIMAGELIST = TV_FIRST + 9
TVM_GETNEXTITEM = TV_FIRST + 10
TVGN_ROOT = 0
TVGN_NEXT = 1
TVGN_PREVIOUS = 2
TVGN_PARENT = 3
TVGN_CHILD = 4
TVGN_FIRSTVISIBLE = 5
TVGN_NEXTVISIBLE = 6
TVGN_PREVIOUSVISIBLE = 7
TVGN_DROPHILITE = 8
TVGN_CARET = 9
TVGN_LASTVISIBLE = 10
TVM_SELECTITEM = TV_FIRST + 11
TVM_GETITEMA = TV_FIRST + 12
TVM_GETITEMW = TV_FIRST + 62
TVM_GETITEM = TVM_GETITEMA
TVM_SETITEMA = TV_FIRST + 13
TVM_SETITEMW = TV_FIRST + 63
TVM_SETITEM = TVM_SETITEMA
TVM_EDITLABELA = TV_FIRST + 14
TVM_EDITLABELW = TV_FIRST + 65
TVM_EDITLABEL = TVM_EDITLABELA
TVM_GETEDITCONTROL = TV_FIRST + 15
TVM_GETVISIBLECOUNT = TV_FIRST + 16
TVM_HITTEST = TV_FIRST + 17
TVHT_NOWHERE = 1
TVHT_ONITEMICON = 2
TVHT_ONITEMLABEL = 4
TVHT_ONITEMINDENT = 8
TVHT_ONITEMBUTTON = 16
TVHT_ONITEMRIGHT = 32
TVHT_ONITEMSTATEICON = 64
TVHT_ABOVE = 256
TVHT_BELOW = 512
TVHT_TORIGHT = 1024
TVHT_TOLEFT = 2048
TVHT_ONITEM = TVHT_ONITEMICON | TVHT_ONITEMLABEL | TVHT_ONITEMSTATEICON
TVM_CREATEDRAGIMAGE = TV_FIRST + 18
TVM_SORTCHILDREN = TV_FIRST + 19
TVM_ENSUREVISIBLE = TV_FIRST + 20
TVM_SORTCHILDRENCB = TV_FIRST + 21
TVM_ENDEDITLABELNOW = TV_FIRST + 22
TVM_GETISEARCHSTRINGA = TV_FIRST + 23
TVM_GETISEARCHSTRINGW = TV_FIRST + 64
TVM_GETISEARCHSTRING = TVM_GETISEARCHSTRINGA
TVM_SETTOOLTIPS = TV_FIRST + 24
TVM_GETTOOLTIPS = TV_FIRST + 25
TVM_SETINSERTMARK = TV_FIRST + 26
TVM_SETUNICODEFORMAT = CCM_SETUNICODEFORMAT
TVM_GETUNICODEFORMAT = CCM_GETUNICODEFORMAT
TVM_SETITEMHEIGHT = TV_FIRST + 27
TVM_GETITEMHEIGHT = TV_FIRST + 28
TVM_SETBKCOLOR = TV_FIRST + 29
TVM_SETTEXTCOLOR = TV_FIRST + 30
TVM_GETBKCOLOR = TV_FIRST + 31
TVM_GETTEXTCOLOR = TV_FIRST + 32
TVM_SETSCROLLTIME = TV_FIRST + 33
TVM_GETSCROLLTIME = TV_FIRST + 34
TVM_SETINSERTMARKCOLOR = TV_FIRST + 37
TVM_GETINSERTMARKCOLOR = TV_FIRST + 38
TVN_SELCHANGINGA = TVN_FIRST - 1
TVN_SELCHANGINGW = TVN_FIRST - 50
TVN_SELCHANGEDA = TVN_FIRST - 2
TVN_SELCHANGEDW = TVN_FIRST - 51
TVC_UNKNOWN = 0
TVC_BYMOUSE = 1
TVC_BYKEYBOARD = 2
TVN_GETDISPINFOA = TVN_FIRST - 3
TVN_GETDISPINFOW = TVN_FIRST - 52
TVN_SETDISPINFOA = TVN_FIRST - 4
TVN_SETDISPINFOW = TVN_FIRST - 53
TVIF_DI_SETITEM = 4096
TVN_ITEMEXPANDINGA = TVN_FIRST - 5
TVN_ITEMEXPANDINGW = TVN_FIRST - 54
TVN_ITEMEXPANDEDA = TVN_FIRST - 6
TVN_ITEMEXPANDEDW = TVN_FIRST - 55
TVN_BEGINDRAGA = TVN_FIRST - 7
TVN_BEGINDRAGW = TVN_FIRST - 56
TVN_BEGINRDRAGA = TVN_FIRST - 8
TVN_BEGINRDRAGW = TVN_FIRST - 57
TVN_DELETEITEMA = TVN_FIRST - 9
TVN_DELETEITEMW = TVN_FIRST - 58
TVN_BEGINLABELEDITA = TVN_FIRST - 10
TVN_BEGINLABELEDITW = TVN_FIRST - 59
TVN_ENDLABELEDITA = TVN_FIRST - 11
TVN_ENDLABELEDITW = TVN_FIRST - 60
TVN_KEYDOWN = TVN_FIRST - 12
TVN_GETINFOTIPA = TVN_FIRST - 13
TVN_GETINFOTIPW = TVN_FIRST - 14
TVN_SINGLEEXPAND = TVN_FIRST - 15
TVN_SELCHANGING = TVN_SELCHANGINGA
TVN_SELCHANGED = TVN_SELCHANGEDA
TVN_GETDISPINFO = TVN_GETDISPINFOA
TVN_SETDISPINFO = TVN_SETDISPINFOA
TVN_ITEMEXPANDING = TVN_ITEMEXPANDINGA
TVN_ITEMEXPANDED = TVN_ITEMEXPANDEDA
TVN_BEGINDRAG = TVN_BEGINDRAGA
TVN_BEGINRDRAG = TVN_BEGINRDRAGA
TVN_DELETEITEM = TVN_DELETEITEMA
TVN_BEGINLABELEDIT = TVN_BEGINLABELEDITA
TVN_ENDLABELEDIT = TVN_ENDLABELEDITA
TVN_GETINFOTIP = TVN_GETINFOTIPA
TVCDRF_NOIMAGES = 65536
WC_COMBOBOXEXA = "ComboBoxEx32"
WC_COMBOBOXEX = WC_COMBOBOXEXA
CBEIF_TEXT = 1
CBEIF_IMAGE = 2
CBEIF_SELECTEDIMAGE = 4
CBEIF_OVERLAY = 8
CBEIF_INDENT = 16
CBEIF_LPARAM = 32
CBEIF_DI_SETITEM = 268435456
CBEM_INSERTITEMA = WM_USER + 1
CBEM_SETIMAGELIST = WM_USER + 2
CBEM_GETIMAGELIST = WM_USER + 3
CBEM_GETITEMA = WM_USER + 4
CBEM_SETITEMA = WM_USER + 5
# CBEM_DELETEITEM = CB_DELETESTRING
CBEM_GETCOMBOCONTROL = WM_USER + 6
CBEM_GETEDITCONTROL = WM_USER + 7
CBEM_SETEXSTYLE = WM_USER + 8  # use  SETEXTENDEDSTYLE instead
CBEM_SETEXTENDEDSTYLE = WM_USER + 14  # lparam == new style, wParam (optional) == mask
CBEM_GETEXSTYLE = WM_USER + 9  # use GETEXTENDEDSTYLE instead
CBEM_GETEXTENDEDSTYLE = WM_USER + 9
CBEM_SETUNICODEFORMAT = CCM_SETUNICODEFORMAT
CBEM_GETUNICODEFORMAT = CCM_GETUNICODEFORMAT
CBEM_HASEDITCHANGED = WM_USER + 10
CBEM_INSERTITEMW = WM_USER + 11
CBEM_SETITEMW = WM_USER + 12
CBEM_GETITEMW = WM_USER + 13
CBEM_INSERTITEM = CBEM_INSERTITEMA
CBEM_SETITEM = CBEM_SETITEMA
CBEM_GETITEM = CBEM_GETITEMA
CBES_EX_NOEDITIMAGE = 1
CBES_EX_NOEDITIMAGEINDENT = 2
CBES_EX_PATHWORDBREAKPROC = 4
CBES_EX_NOSIZELIMIT = 8
CBES_EX_CASESENSITIVE = 16
CBEN_GETDISPINFO = CBEN_FIRST - 0
CBEN_GETDISPINFOA = CBEN_FIRST - 0
CBEN_INSERTITEM = CBEN_FIRST - 1
CBEN_DELETEITEM = CBEN_FIRST - 2
CBEN_BEGINEDIT = CBEN_FIRST - 4
CBEN_ENDEDITA = CBEN_FIRST - 5
CBEN_ENDEDITW = CBEN_FIRST - 6
CBEN_GETDISPINFOW = CBEN_FIRST - 7
CBEN_DRAGBEGINA = CBEN_FIRST - 8
CBEN_DRAGBEGINW = CBEN_FIRST - 9
CBEN_DRAGBEGIN = CBEN_DRAGBEGINA
CBEN_ENDEDIT = CBEN_ENDEDITA
CBENF_KILLFOCUS = 1
CBENF_RETURN = 2
CBENF_ESCAPE = 3
CBENF_DROPDOWN = 4
CBEMAXSTRLEN = 260
WC_TABCONTROLA = "SysTabControl32"
WC_TABCONTROL = WC_TABCONTROLA
TCS_SCROLLOPPOSITE = 1  # assumes multiline tab
TCS_BOTTOM = 2
TCS_RIGHT = 2
TCS_MULTISELECT = 4  # allow multi-select in button mode
TCS_FLATBUTTONS = 8
TCS_FORCEICONLEFT = 16
TCS_FORCELABELLEFT = 32
TCS_HOTTRACK = 64
TCS_VERTICAL = 128
TCS_TABS = 0
TCS_BUTTONS = 256
TCS_SINGLELINE = 0
TCS_MULTILINE = 512
TCS_RIGHTJUSTIFY = 0
TCS_FIXEDWIDTH = 1024
TCS_RAGGEDRIGHT = 2048
TCS_FOCUSONBUTTONDOWN = 4096
TCS_OWNERDRAWFIXED = 8192
TCS_TOOLTIPS = 16384
TCS_FOCUSNEVER = 32768
TCS_EX_FLATSEPARATORS = 1
TCS_EX_REGISTERDROP = 2
TCM_GETIMAGELIST = TCM_FIRST + 2
TCM_SETIMAGELIST = TCM_FIRST + 3
TCM_GETITEMCOUNT = TCM_FIRST + 4
TCIF_TEXT = 1
TCIF_IMAGE = 2
TCIF_RTLREADING = 4
TCIF_PARAM = 8
TCIF_STATE = 16
TCIS_BUTTONPRESSED = 1
TCIS_HIGHLIGHTED = 2
TCM_GETITEMA = TCM_FIRST + 5
TCM_GETITEMW = TCM_FIRST + 60
TCM_GETITEM = TCM_GETITEMA
TCM_SETITEMA = TCM_FIRST + 6
TCM_SETITEMW = TCM_FIRST + 61
TCM_SETITEM = TCM_SETITEMA
TCM_INSERTITEMA = TCM_FIRST + 7
TCM_INSERTITEMW = TCM_FIRST + 62
TCM_INSERTITEM = TCM_INSERTITEMA
TCM_DELETEITEM = TCM_FIRST + 8
TCM_DELETEALLITEMS = TCM_FIRST + 9
TCM_GETITEMRECT = TCM_FIRST + 10
TCM_GETCURSEL = TCM_FIRST + 11
TCM_SETCURSEL = TCM_FIRST + 12
TCHT_NOWHERE = 1
TCHT_ONITEMICON = 2
TCHT_ONITEMLABEL = 4
TCHT_ONITEM = TCHT_ONITEMICON | TCHT_ONITEMLABEL
TCM_HITTEST = TCM_FIRST + 13
TCM_SETITEMEXTRA = TCM_FIRST + 14
TCM_ADJUSTRECT = TCM_FIRST + 40
TCM_SETITEMSIZE = TCM_FIRST + 41
TCM_REMOVEIMAGE = TCM_FIRST + 42
TCM_SETPADDING = TCM_FIRST + 43
TCM_GETROWCOUNT = TCM_FIRST + 44
TCM_GETTOOLTIPS = TCM_FIRST + 45
TCM_SETTOOLTIPS = TCM_FIRST + 46
TCM_GETCURFOCUS = TCM_FIRST + 47
TCM_SETCURFOCUS = TCM_FIRST + 48
TCM_SETMINTABWIDTH = TCM_FIRST + 49
TCM_DESELECTALL = TCM_FIRST + 50
TCM_HIGHLIGHTITEM = TCM_FIRST + 51
TCM_SETEXTENDEDSTYLE = TCM_FIRST + 52  # optional wParam == mask
TCM_GETEXTENDEDSTYLE = TCM_FIRST + 53
TCM_SETUNICODEFORMAT = CCM_SETUNICODEFORMAT
TCM_GETUNICODEFORMAT = CCM_GETUNICODEFORMAT
TCN_KEYDOWN = TCN_FIRST - 0
ANIMATE_CLASSA = "SysAnimate32"
ANIMATE_CLASS = ANIMATE_CLASSA
ACS_CENTER = 1
ACS_TRANSPARENT = 2
ACS_AUTOPLAY = 4
ACS_TIMER = 8  # don't use threads... use timers
ACM_OPENA = WM_USER + 100
ACM_OPENW = WM_USER + 103
ACM_OPEN = ACM_OPENA
ACM_PLAY = WM_USER + 101
ACM_STOP = WM_USER + 102
ACN_START = 1
ACN_STOP = 2
MONTHCAL_CLASSA = "SysMonthCal32"
MONTHCAL_CLASS = MONTHCAL_CLASSA
MCM_FIRST = 4096
MCM_GETCURSEL = MCM_FIRST + 1
MCM_SETCURSEL = MCM_FIRST + 2
MCM_GETMAXSELCOUNT = MCM_FIRST + 3
MCM_SETMAXSELCOUNT = MCM_FIRST + 4
MCM_GETSELRANGE = MCM_FIRST + 5
MCM_SETSELRANGE = MCM_FIRST + 6
MCM_GETMONTHRANGE = MCM_FIRST + 7
MCM_SETDAYSTATE = MCM_FIRST + 8
MCM_GETMINREQRECT = MCM_FIRST + 9
MCM_SETCOLOR = MCM_FIRST + 10
MCM_GETCOLOR = MCM_FIRST + 11
MCSC_BACKGROUND = 0  # the background color (between months)
MCSC_TEXT = 1  # the dates
MCSC_TITLEBK = 2  # background of the title
MCSC_TITLETEXT = 3
MCSC_MONTHBK = 4  # background within the month cal
MCSC_TRAILINGTEXT = 5  # the text color of header & trailing days
MCM_SETTODAY = MCM_FIRST + 12
MCM_GETTODAY = MCM_FIRST + 13
MCM_HITTEST = MCM_FIRST + 14
MCHT_TITLE = 65536
MCHT_CALENDAR = 131072
MCHT_TODAYLINK = 196608
MCHT_NEXT = 16777216  # these indicate that hitting
MCHT_PREV = 33554432  # here will go to the next/prev month
MCHT_NOWHERE = 0
MCHT_TITLEBK = MCHT_TITLE
MCHT_TITLEMONTH = MCHT_TITLE | 1
MCHT_TITLEYEAR = MCHT_TITLE | 2
MCHT_TITLEBTNNEXT = MCHT_TITLE | MCHT_NEXT | 3
MCHT_TITLEBTNPREV = MCHT_TITLE | MCHT_PREV | 3
MCHT_CALENDARBK = MCHT_CALENDAR
MCHT_CALENDARDATE = MCHT_CALENDAR | 1
MCHT_CALENDARDATENEXT = MCHT_CALENDARDATE | MCHT_NEXT
MCHT_CALENDARDATEPREV = MCHT_CALENDARDATE | MCHT_PREV
MCHT_CALENDARDAY = MCHT_CALENDAR | 2
MCHT_CALENDARWEEKNUM = MCHT_CALENDAR | 3
MCM_SETFIRSTDAYOFWEEK = MCM_FIRST + 15
MCM_GETFIRSTDAYOFWEEK = MCM_FIRST + 16
MCM_GETRANGE = MCM_FIRST + 17
MCM_SETRANGE = MCM_FIRST + 18
MCM_GETMONTHDELTA = MCM_FIRST + 19
MCM_SETMONTHDELTA = MCM_FIRST + 20
MCM_GETMAXTODAYWIDTH = MCM_FIRST + 21
MCM_SETUNICODEFORMAT = CCM_SETUNICODEFORMAT
MCM_GETUNICODEFORMAT = CCM_GETUNICODEFORMAT
MCN_SELCHANGE = MCN_FIRST + 1
MCN_GETDAYSTATE = MCN_FIRST + 3
MCN_SELECT = MCN_FIRST + 4
MCS_DAYSTATE = 1
MCS_MULTISELECT = 2
MCS_WEEKNUMBERS = 4
MCS_NOTODAYCIRCLE = 8
MCS_NOTODAY = 8
GMR_VISIBLE = 0  # visible portion of display
GMR_DAYSTATE = 1  # above plus the grayed out parts of
DATETIMEPICK_CLASSA = "SysDateTimePick32"
DATETIMEPICK_CLASS = DATETIMEPICK_CLASSA
DTM_FIRST = 4096
DTM_GETSYSTEMTIME = DTM_FIRST + 1
DTM_SETSYSTEMTIME = DTM_FIRST + 2
DTM_GETRANGE = DTM_FIRST + 3
DTM_SETRANGE = DTM_FIRST + 4
DTM_SETFORMATA = DTM_FIRST + 5
DTM_SETFORMATW = DTM_FIRST + 50
DTM_SETFORMAT = DTM_SETFORMATA
DTM_SETMCCOLOR = DTM_FIRST + 6
DTM_GETMCCOLOR = DTM_FIRST + 7
DTM_GETMONTHCAL = DTM_FIRST + 8
DTM_SETMCFONT = DTM_FIRST + 9
DTM_GETMCFONT = DTM_FIRST + 10
DTS_UPDOWN = 1  # use UPDOWN instead of MONTHCAL
DTS_SHOWNONE = 2  # allow a NONE selection
DTS_SHORTDATEFORMAT = (
    0  # use the short date format (app must forward WM_WININICHANGE messages)
)
DTS_LONGDATEFORMAT = (
    4  # use the long date format (app must forward WM_WININICHANGE messages)
)
DTS_TIMEFORMAT = 9  # use the time format (app must forward WM_WININICHANGE messages)
DTS_APPCANPARSE = 16  # allow user entered strings (app MUST respond to DTN_USERSTRING)
DTS_RIGHTALIGN = 32  # right-align popup instead of left-align it
DTN_DATETIMECHANGE = DTN_FIRST + 1  # the systemtime has changed
DTN_USERSTRINGA = DTN_FIRST + 2  # the user has entered a string
DTN_USERSTRINGW = DTN_FIRST + 15
DTN_USERSTRING = DTN_USERSTRINGW
DTN_WMKEYDOWNA = DTN_FIRST + 3  # modify keydown on app format field (X)
DTN_WMKEYDOWNW = DTN_FIRST + 16
DTN_WMKEYDOWN = DTN_WMKEYDOWNA
DTN_FORMATA = DTN_FIRST + 4  # query display for app format field (X)
DTN_FORMATW = DTN_FIRST + 17
DTN_FORMAT = DTN_FORMATA
DTN_FORMATQUERYA = DTN_FIRST + 5  # query formatting info for app format field (X)
DTN_FORMATQUERYW = DTN_FIRST + 18
DTN_FORMATQUERY = DTN_FORMATQUERYA
DTN_DROPDOWN = DTN_FIRST + 6  # MonthCal has dropped down
DTN_CLOSEUP = DTN_FIRST + 7  # MonthCal is popping up
GDTR_MIN = 1
GDTR_MAX = 2
GDT_ERROR = -1
GDT_VALID = 0
GDT_NONE = 1
IPM_CLEARADDRESS = WM_USER + 100  # no parameters
IPM_SETADDRESS = WM_USER + 101  # lparam = TCP/IP address
IPM_GETADDRESS = (
    WM_USER + 102
)  # lresult = # of non black fields.  lparam = LPDWORD for TCP/IP address
IPM_SETRANGE = WM_USER + 103  # wparam = field, lparam = range
IPM_SETFOCUS = WM_USER + 104  # wparam = field
IPM_ISBLANK = WM_USER + 105  # no parameters
WC_IPADDRESSA = "SysIPAddress32"
WC_IPADDRESS = WC_IPADDRESSA
IPN_FIELDCHANGED = IPN_FIRST - 0
WC_PAGESCROLLERA = "SysPager"
WC_PAGESCROLLER = WC_PAGESCROLLERA
PGS_VERT = 0
PGS_HORZ = 1
PGS_AUTOSCROLL = 2
PGS_DRAGNDROP = 4
PGF_INVISIBLE = 0  # Scroll button is not visible
PGF_NORMAL = 1  # Scroll button is in normal state
PGF_GRAYED = 2  # Scroll button is in grayed state
PGF_DEPRESSED = 4  # Scroll button is in depressed state
PGF_HOT = 8  # Scroll button is in hot state
PGB_TOPORLEFT = 0
PGB_BOTTOMORRIGHT = 1
PGM_SETCHILD = PGM_FIRST + 1  # lParam == hwnd
PGM_RECALCSIZE = PGM_FIRST + 2
PGM_FORWARDMOUSE = PGM_FIRST + 3
PGM_SETBKCOLOR = PGM_FIRST + 4
PGM_GETBKCOLOR = PGM_FIRST + 5
PGM_SETBORDER = PGM_FIRST + 6
PGM_GETBORDER = PGM_FIRST + 7
PGM_SETPOS = PGM_FIRST + 8
PGM_GETPOS = PGM_FIRST + 9
PGM_SETBUTTONSIZE = PGM_FIRST + 10
PGM_GETBUTTONSIZE = PGM_FIRST + 11
PGM_GETBUTTONSTATE = PGM_FIRST + 12
PGM_GETDROPTARGET = CCM_GETDROPTARGET
PGN_SCROLL = PGN_FIRST - 1
PGF_SCROLLUP = 1
PGF_SCROLLDOWN = 2
PGF_SCROLLLEFT = 4
PGF_SCROLLRIGHT = 8
PGK_SHIFT = 1
PGK_CONTROL = 2
PGK_MENU = 4
PGN_CALCSIZE = PGN_FIRST - 2
PGF_CALCWIDTH = 1
PGF_CALCHEIGHT = 2
WC_NATIVEFONTCTLA = "NativeFontCtl"
WC_NATIVEFONTCTL = WC_NATIVEFONTCTLA
NFS_EDIT = 1
NFS_STATIC = 2
NFS_LISTCOMBO = 4
NFS_BUTTON = 8
NFS_ALL = 16
WM_MOUSEHOVER = 673
WM_MOUSELEAVE = 675
TME_HOVER = 1
TME_LEAVE = 2
TME_QUERY = 1073741824
TME_CANCEL = -2147483648
HOVER_DEFAULT = -1
WSB_PROP_CYVSCROLL = 0x00000001
WSB_PROP_CXHSCROLL = 0x00000002
WSB_PROP_CYHSCROLL = 0x00000004
WSB_PROP_CXVSCROLL = 0x00000008
WSB_PROP_CXHTHUMB = 0x00000010
WSB_PROP_CYVTHUMB = 0x00000020
WSB_PROP_VBKGCOLOR = 0x00000040
WSB_PROP_HBKGCOLOR = 0x00000080
WSB_PROP_VSTYLE = 0x00000100
WSB_PROP_HSTYLE = 0x00000200
WSB_PROP_WINSTYLE = 0x00000400
WSB_PROP_PALETTE = 0x00000800
WSB_PROP_MASK = 0x00000FFF
FSB_FLAT_MODE = 2
FSB_ENCARTA_MODE = 1
FSB_REGULAR_MODE = 0


def INDEXTOOVERLAYMASK(i):
    return i << 8


def INDEXTOSTATEIMAGEMASK(i):
    return i << 12

# === NexusCore/openenv\Lib\site-packages\nltk\app\__init__.py ===
# Natural Language Toolkit: Applications package
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
#         Steven Bird <stevenbird1@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Interactive NLTK Applications:

chartparser:  Chart Parser
chunkparser:  Regular-Expression Chunk Parser
collocations: Find collocations in text
concordance:  Part-of-speech concordancer
nemo:         Finding (and Replacing) Nemo regular expression tool
rdparser:     Recursive Descent Parser
srparser:     Shift-Reduce Parser
wordnet:      WordNet Browser
"""


# Import Tkinter-based modules if Tkinter is installed
try:
    import tkinter
except ImportError:
    import warnings

    warnings.warn("nltk.app package not loaded (please install Tkinter library).")
else:
    from nltk.app.chartparser_app import app as chartparser
    from nltk.app.chunkparser_app import app as chunkparser
    from nltk.app.collocations_app import app as collocations
    from nltk.app.concordance_app import app as concordance
    from nltk.app.nemo_app import app as nemo
    from nltk.app.rdparser_app import app as rdparser
    from nltk.app.srparser_app import app as srparser
    from nltk.app.wordnet_app import app as wordnet

    try:
        from matplotlib import pylab
    except ImportError:
        import warnings

        warnings.warn("nltk.app.wordfreq not loaded (requires the matplotlib library).")
    else:
        from nltk.app.wordfreq_app import app as wordfreq

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\nltk\app\__init__.py ===
# Natural Language Toolkit: Applications package
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
#         Steven Bird <stevenbird1@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Interactive NLTK Applications:

chartparser:  Chart Parser
chunkparser:  Regular-Expression Chunk Parser
collocations: Find collocations in text
concordance:  Part-of-speech concordancer
nemo:         Finding (and Replacing) Nemo regular expression tool
rdparser:     Recursive Descent Parser
srparser:     Shift-Reduce Parser
wordnet:      WordNet Browser
"""


# Import Tkinter-based modules if Tkinter is installed
try:
    import tkinter
except ImportError:
    import warnings

    warnings.warn("nltk.app package not loaded (please install Tkinter library).")
else:
    from nltk.app.chartparser_app import app as chartparser
    from nltk.app.chunkparser_app import app as chunkparser
    from nltk.app.collocations_app import app as collocations
    from nltk.app.concordance_app import app as concordance
    from nltk.app.nemo_app import app as nemo
    from nltk.app.rdparser_app import app as rdparser
    from nltk.app.srparser_app import app as srparser
    from nltk.app.wordnet_app import app as wordnet

    try:
        from matplotlib import pylab
    except ImportError:
        import warnings

        warnings.warn("nltk.app.wordfreq not loaded (requires the matplotlib library).")
    else:
        from nltk.app.wordfreq_app import app as wordfreq

# === NexusCore/src\history_manager.py ===
# ファイル名: history_manager.py
import json
import os
from datetime import datetime
from typing import List, Dict, Any

class HistoryManager:
    def __init__(self, history_dir="history", prefix="history_"):
        self.history_dir = history_dir
        self.prefix = prefix
        os.makedirs(history_dir, exist_ok=True)
        self.history_path = self._generate_new_path()
        self.state_history: List[Dict[str, Any]] = []
        self.current_index: int = -1

    def _generate_new_path(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(self.history_dir, f"{self.prefix}{timestamp}.json")

    def add_state(self, state: Dict[str, Any]):
        # 未来の履歴を切り捨ててから追加
        self.state_history = self.state_history[:self.current_index + 1]
        self.state_history.append(state)
        self.current_index += 1
        self.save_history()

    def rollback(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.save_history()
            return self.state_history[self.current_index]
        else:
            print("Already at oldest state")
            return self.state_history[0] if self.state_history else None

    def get_current_state(self):
        if self.current_index >= 0:
            return self.state_history[self.current_index]
        return None

    def save_history(self):
        with open(self.history_path, "w", encoding="utf-8") as f:
            json.dump({
                "history": self.state_history,
                "current_index": self.current_index
            }, f, ensure_ascii=False, indent=2)

# === NexusCore/exported_projects\app_20250703_223016\app\models.py ===
# app/models.py
from app import db
from datetime import datetime

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    brand = db.Column(db.String(128))
    purchase_price = db.Column(db.Float, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
    supplier_url = db.Column(db.String(500))
    image_url = db.Column(db.String(500))
    stock_status = db.Column(db.Boolean, default=True)
    profit = db.Column(db.Float)
    listings = db.relationship('Listing', backref='product', lazy='dynamic')

    # 経費項目
    transaction_fee = db.Column(db.Float, default=0.0)
    shipping_cost = db.Column(db.Float, default=0.0)
    customs_duty = db.Column(db.Float, default=0.0)
    procurement_fee = db.Column(db.Float, default=0.0)

    def calculate_profit(self, fee_rate=0.15):
        """None対策済みの利益計算式"""
        calculated_profit = (
            (self.selling_price or 0) 
            - (self.purchase_price or 0)
            - ((self.selling_price or 0) * fee_rate)
            - (self.transaction_fee or 0)
            - (self.shipping_cost or 0)
            - (self.customs_duty or 0)
            - (self.procurement_fee or 0)
        )
        self.profit = calculated_profit
        return calculated_profit

    def __repr__(self):
        return f"<Product {self.name}>"

class Listing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(50), nullable=False)
    fee_rate = db.Column(db.Float)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    listing_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

# === NexusCore/exported_projects\project_export_m73owrzi\app\models.py ===
# app/models.py
from app import db
from datetime import datetime

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    brand = db.Column(db.String(128))
    purchase_price = db.Column(db.Float, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
    supplier_url = db.Column(db.String(500))
    image_url = db.Column(db.String(500))
    stock_status = db.Column(db.Boolean, default=True)
    profit = db.Column(db.Float)
    listings = db.relationship('Listing', backref='product', lazy='dynamic')

    # 経費項目
    transaction_fee = db.Column(db.Float, default=0.0)
    shipping_cost = db.Column(db.Float, default=0.0)
    customs_duty = db.Column(db.Float, default=0.0)
    procurement_fee = db.Column(db.Float, default=0.0)

    def calculate_profit(self, fee_rate=0.15):
        """None対策済みの利益計算式"""
        calculated_profit = (
            (self.selling_price or 0) 
            - (self.purchase_price or 0)
            - ((self.selling_price or 0) * fee_rate)
            - (self.transaction_fee or 0)
            - (self.shipping_cost or 0)
            - (self.customs_duty or 0)
            - (self.procurement_fee or 0)
        )
        self.profit = calculated_profit
        return calculated_profit

    def __repr__(self):
        return f"<Product {self.name}>"

class Listing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(50), nullable=False)
    fee_rate = db.Column(db.Float)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    listing_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

# === NexusCore/exported_projects\project_export_xb_l70t8\app\models.py ===
# app/models.py
from app import db
from datetime import datetime

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    brand = db.Column(db.String(128))
    purchase_price = db.Column(db.Float, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
    supplier_url = db.Column(db.String(500))
    image_url = db.Column(db.String(500))
    stock_status = db.Column(db.Boolean, default=True)
    profit = db.Column(db.Float)
    listings = db.relationship('Listing', backref='product', lazy='dynamic')

    # 経費項目
    transaction_fee = db.Column(db.Float, default=0.0)
    shipping_cost = db.Column(db.Float, default=0.0)
    customs_duty = db.Column(db.Float, default=0.0)
    procurement_fee = db.Column(db.Float, default=0.0)

    def calculate_profit(self, fee_rate=0.15):
        """None対策済みの利益計算式"""
        calculated_profit = (
            (self.selling_price or 0) 
            - (self.purchase_price or 0)
            - ((self.selling_price or 0) * fee_rate)
            - (self.transaction_fee or 0)
            - (self.shipping_cost or 0)
            - (self.customs_duty or 0)
            - (self.procurement_fee or 0)
        )
        self.profit = calculated_profit
        return calculated_profit

    def __repr__(self):
        return f"<Product {self.name}>"

class Listing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(50), nullable=False)
    fee_rate = db.Column(db.Float)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    listing_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

# === NexusCore/exported_projects\project_export_y7xxp1v8\app\models.py ===
# app/models.py
from app import db
from datetime import datetime

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    brand = db.Column(db.String(128))
    purchase_price = db.Column(db.Float, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
    supplier_url = db.Column(db.String(500))
    image_url = db.Column(db.String(500))
    stock_status = db.Column(db.Boolean, default=True)
    profit = db.Column(db.Float)
    listings = db.relationship('Listing', backref='product', lazy='dynamic')

    # 経費項目
    transaction_fee = db.Column(db.Float, default=0.0)
    shipping_cost = db.Column(db.Float, default=0.0)
    customs_duty = db.Column(db.Float, default=0.0)
    procurement_fee = db.Column(db.Float, default=0.0)

    def calculate_profit(self, fee_rate=0.15):
        """None対策済みの利益計算式"""
        calculated_profit = (
            (self.selling_price or 0) 
            - (self.purchase_price or 0)
            - ((self.selling_price or 0) * fee_rate)
            - (self.transaction_fee or 0)
            - (self.shipping_cost or 0)
            - (self.customs_duty or 0)
            - (self.procurement_fee or 0)
        )
        self.profit = calculated_profit
        return calculated_profit

    def __repr__(self):
        return f"<Product {self.name}>"

class Listing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(50), nullable=False)
    fee_rate = db.Column(db.Float)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    listing_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\history_manager.py ===
# ファイル名: history_manager.py
import json
import os
from datetime import datetime
from typing import List, Dict, Any

class HistoryManager:
    def __init__(self, history_dir="history", prefix="history_"):
        self.history_dir = history_dir
        self.prefix = prefix
        os.makedirs(history_dir, exist_ok=True)
        self.history_path = self._generate_new_path()
        self.state_history: List[Dict[str, Any]] = []
        self.current_index: int = -1

    def _generate_new_path(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(self.history_dir, f"{self.prefix}{timestamp}.json")

    def add_state(self, state: Dict[str, Any]):
        # 未来の履歴を切り捨ててから追加
        self.state_history = self.state_history[:self.current_index + 1]
        self.state_history.append(state)
        self.current_index += 1
        self.save_history()

    def rollback(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.save_history()
            return self.state_history[self.current_index]
        else:
            print("Already at oldest state")
            return self.state_history[0] if self.state_history else None

    def get_current_state(self):
        if self.current_index >= 0:
            return self.state_history[self.current_index]
        return None

    def save_history(self):
        with open(self.history_path, "w", encoding="utf-8") as f:
            json.dump({
                "history": self.state_history,
                "current_index": self.current_index
            }, f, ensure_ascii=False, indent=2)

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\exported_projects\app_20250703_223016\app\models.py ===
# app/models.py
from app import db
from datetime import datetime

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    brand = db.Column(db.String(128))
    purchase_price = db.Column(db.Float, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
    supplier_url = db.Column(db.String(500))
    image_url = db.Column(db.String(500))
    stock_status = db.Column(db.Boolean, default=True)
    profit = db.Column(db.Float)
    listings = db.relationship('Listing', backref='product', lazy='dynamic')

    # 経費項目
    transaction_fee = db.Column(db.Float, default=0.0)
    shipping_cost = db.Column(db.Float, default=0.0)
    customs_duty = db.Column(db.Float, default=0.0)
    procurement_fee = db.Column(db.Float, default=0.0)

    def calculate_profit(self, fee_rate=0.15):
        """None対策済みの利益計算式"""
        calculated_profit = (
            (self.selling_price or 0) 
            - (self.purchase_price or 0)
            - ((self.selling_price or 0) * fee_rate)
            - (self.transaction_fee or 0)
            - (self.shipping_cost or 0)
            - (self.customs_duty or 0)
            - (self.procurement_fee or 0)
        )
        self.profit = calculated_profit
        return calculated_profit

    def __repr__(self):
        return f"<Product {self.name}>"

class Listing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(50), nullable=False)
    fee_rate = db.Column(db.Float)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    listing_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\exported_projects\project_export_m73owrzi\app\models.py ===
# app/models.py
from app import db
from datetime import datetime

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    brand = db.Column(db.String(128))
    purchase_price = db.Column(db.Float, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
    supplier_url = db.Column(db.String(500))
    image_url = db.Column(db.String(500))
    stock_status = db.Column(db.Boolean, default=True)
    profit = db.Column(db.Float)
    listings = db.relationship('Listing', backref='product', lazy='dynamic')

    # 経費項目
    transaction_fee = db.Column(db.Float, default=0.0)
    shipping_cost = db.Column(db.Float, default=0.0)
    customs_duty = db.Column(db.Float, default=0.0)
    procurement_fee = db.Column(db.Float, default=0.0)

    def calculate_profit(self, fee_rate=0.15):
        """None対策済みの利益計算式"""
        calculated_profit = (
            (self.selling_price or 0) 
            - (self.purchase_price or 0)
            - ((self.selling_price or 0) * fee_rate)
            - (self.transaction_fee or 0)
            - (self.shipping_cost or 0)
            - (self.customs_duty or 0)
            - (self.procurement_fee or 0)
        )
        self.profit = calculated_profit
        return calculated_profit

    def __repr__(self):
        return f"<Product {self.name}>"

class Listing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(50), nullable=False)
    fee_rate = db.Column(db.Float)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    listing_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\exported_projects\project_export_xb_l70t8\app\models.py ===
# app/models.py
from app import db
from datetime import datetime

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    brand = db.Column(db.String(128))
    purchase_price = db.Column(db.Float, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
    supplier_url = db.Column(db.String(500))
    image_url = db.Column(db.String(500))
    stock_status = db.Column(db.Boolean, default=True)
    profit = db.Column(db.Float)
    listings = db.relationship('Listing', backref='product', lazy='dynamic')

    # 経費項目
    transaction_fee = db.Column(db.Float, default=0.0)
    shipping_cost = db.Column(db.Float, default=0.0)
    customs_duty = db.Column(db.Float, default=0.0)
    procurement_fee = db.Column(db.Float, default=0.0)

    def calculate_profit(self, fee_rate=0.15):
        """None対策済みの利益計算式"""
        calculated_profit = (
            (self.selling_price or 0) 
            - (self.purchase_price or 0)
            - ((self.selling_price or 0) * fee_rate)
            - (self.transaction_fee or 0)
            - (self.shipping_cost or 0)
            - (self.customs_duty or 0)
            - (self.procurement_fee or 0)
        )
        self.profit = calculated_profit
        return calculated_profit

    def __repr__(self):
        return f"<Product {self.name}>"

class Listing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(50), nullable=False)
    fee_rate = db.Column(db.Float)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    listing_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\exported_projects\project_export_y7xxp1v8\app\models.py ===
# app/models.py
from app import db
from datetime import datetime

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    brand = db.Column(db.String(128))
    purchase_price = db.Column(db.Float, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
    supplier_url = db.Column(db.String(500))
    image_url = db.Column(db.String(500))
    stock_status = db.Column(db.Boolean, default=True)
    profit = db.Column(db.Float)
    listings = db.relationship('Listing', backref='product', lazy='dynamic')

    # 経費項目
    transaction_fee = db.Column(db.Float, default=0.0)
    shipping_cost = db.Column(db.Float, default=0.0)
    customs_duty = db.Column(db.Float, default=0.0)
    procurement_fee = db.Column(db.Float, default=0.0)

    def calculate_profit(self, fee_rate=0.15):
        """None対策済みの利益計算式"""
        calculated_profit = (
            (self.selling_price or 0) 
            - (self.purchase_price or 0)
            - ((self.selling_price or 0) * fee_rate)
            - (self.transaction_fee or 0)
            - (self.shipping_cost or 0)
            - (self.customs_duty or 0)
            - (self.procurement_fee or 0)
        )
        self.profit = calculated_profit
        return calculated_profit

    def __repr__(self):
        return f"<Product {self.name}>"

class Listing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(50), nullable=False)
    fee_rate = db.Column(db.Float)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    listing_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

# === NexusCore/openenv\Lib\site-packages\numpy\lib\_polynomial_impl.py ===
"""
Functions to operate on polynomials.

"""
__all__ = ['poly', 'roots', 'polyint', 'polyder', 'polyadd',
           'polysub', 'polymul', 'polydiv', 'polyval', 'poly1d',
           'polyfit']

import functools
import re
import warnings

import numpy._core.numeric as NX
from numpy._core import (
    abs,
    array,
    atleast_1d,
    dot,
    finfo,
    hstack,
    isscalar,
    ones,
    overrides,
)
from numpy._utils import set_module
from numpy.exceptions import RankWarning
from numpy.lib._function_base_impl import trim_zeros
from numpy.lib._twodim_base_impl import diag, vander
from numpy.lib._type_check_impl import imag, iscomplex, mintypecode, real
from numpy.linalg import eigvals, inv, lstsq

array_function_dispatch = functools.partial(
    overrides.array_function_dispatch, module='numpy')


def _poly_dispatcher(seq_of_zeros):
    return seq_of_zeros


@array_function_dispatch(_poly_dispatcher)
def poly(seq_of_zeros):
    """
    Find the coefficients of a polynomial with the given sequence of roots.

    .. note::
       This forms part of the old polynomial API. Since version 1.4, the
       new polynomial API defined in `numpy.polynomial` is preferred.
       A summary of the differences can be found in the
       :doc:`transition guide </reference/routines.polynomials>`.

    Returns the coefficients of the polynomial whose leading coefficient
    is one for the given sequence of zeros (multiple roots must be included
    in the sequence as many times as their multiplicity; see Examples).
    A square matrix (or array, which will be treated as a matrix) can also
    be given, in which case the coefficients of the characteristic polynomial
    of the matrix are returned.

    Parameters
    ----------
    seq_of_zeros : array_like, shape (N,) or (N, N)
        A sequence of polynomial roots, or a square array or matrix object.

    Returns
    -------
    c : ndarray
        1D array of polynomial coefficients from highest to lowest degree:

        ``c[0] * x**(N) + c[1] * x**(N-1) + ... + c[N-1] * x + c[N]``
        where c[0] always equals 1.

    Raises
    ------
    ValueError
        If input is the wrong shape (the input must be a 1-D or square
        2-D array).

    See Also
    --------
    polyval : Compute polynomial values.
    roots : Return the roots of a polynomial.
    polyfit : Least squares polynomial fit.
    poly1d : A one-dimensional polynomial class.

    Notes
    -----
    Specifying the roots of a polynomial still leaves one degree of
    freedom, typically represented by an undetermined leading
    coefficient. [1]_ In the case of this function, that coefficient -
    the first one in the returned array - is always taken as one. (If
    for some reason you have one other point, the only automatic way
    presently to leverage that information is to use ``polyfit``.)

    The characteristic polynomial, :math:`p_a(t)`, of an `n`-by-`n`
    matrix **A** is given by

    :math:`p_a(t) = \\mathrm{det}(t\\, \\mathbf{I} - \\mathbf{A})`,

    where **I** is the `n`-by-`n` identity matrix. [2]_

    References
    ----------
    .. [1] M. Sullivan and M. Sullivan, III, "Algebra and Trigonometry,
       Enhanced With Graphing Utilities," Prentice-Hall, pg. 318, 1996.

    .. [2] G. Strang, "Linear Algebra and Its Applications, 2nd Edition,"
       Academic Press, pg. 182, 1980.

    Examples
    --------

    Given a sequence of a polynomial's zeros:

    >>> import numpy as np

    >>> np.poly((0, 0, 0)) # Multiple root example
    array([1., 0., 0., 0.])

    The line above represents z**3 + 0*z**2 + 0*z + 0.

    >>> np.poly((-1./2, 0, 1./2))
    array([ 1.  ,  0.  , -0.25,  0.  ])

    The line above represents z**3 - z/4

    >>> np.poly((np.random.random(1)[0], 0, np.random.random(1)[0]))
    array([ 1.        , -0.77086955,  0.08618131,  0.        ]) # random

    Given a square array object:

    >>> P = np.array([[0, 1./3], [-1./2, 0]])
    >>> np.poly(P)
    array([1.        , 0.        , 0.16666667])

    Note how in all cases the leading coefficient is always 1.

    """
    seq_of_zeros = atleast_1d(seq_of_zeros)
    sh = seq_of_zeros.shape

    if len(sh) == 2 and sh[0] == sh[1] and sh[0] != 0:
        seq_of_zeros = eigvals(seq_of_zeros)
    elif len(sh) == 1:
        dt = seq_of_zeros.dtype
        # Let object arrays slip through, e.g. for arbitrary precision
        if dt != object:
            seq_of_zeros = seq_of_zeros.astype(mintypecode(dt.char))
    else:
        raise ValueError("input must be 1d or non-empty square 2d array.")

    if len(seq_of_zeros) == 0:
        return 1.0
    dt = seq_of_zeros.dtype
    a = ones((1,), dtype=dt)
    for zero in seq_of_zeros:
        a = NX.convolve(a, array([1, -zero], dtype=dt), mode='full')

    if issubclass(a.dtype.type, NX.complexfloating):
        # if complex roots are all complex conjugates, the roots are real.
        roots = NX.asarray(seq_of_zeros, complex)
        if NX.all(NX.sort(roots) == NX.sort(roots.conjugate())):
            a = a.real.copy()

    return a


def _roots_dispatcher(p):
    return p


@array_function_dispatch(_roots_dispatcher)
def roots(p):
    """
    Return the roots of a polynomial with coefficients given in p.

    .. note::
       This forms part of the old polynomial API. Since version 1.4, the
       new polynomial API defined in `numpy.polynomial` is preferred.
       A summary of the differences can be found in the
       :doc:`transition guide </reference/routines.polynomials>`.

    The values in the rank-1 array `p` are coefficients of a polynomial.
    If the length of `p` is n+1 then the polynomial is described by::

      p[0] * x**n + p[1] * x**(n-1) + ... + p[n-1]*x + p[n]

    Parameters
    ----------
    p : array_like
        Rank-1 array of polynomial coefficients.

    Returns
    -------
    out : ndarray
        An array containing the roots of the polynomial.

    Raises
    ------
    ValueError
        When `p` cannot be converted to a rank-1 array.

    See also
    --------
    poly : Find the coefficients of a polynomial with a given sequence
           of roots.
    polyval : Compute polynomial values.
    polyfit : Least squares polynomial fit.
    poly1d : A one-dimensional polynomial class.

    Notes
    -----
    The algorithm relies on computing the eigenvalues of the
    companion matrix [1]_.

    References
    ----------
    .. [1] R. A. Horn & C. R. Johnson, *Matrix Analysis*.  Cambridge, UK:
        Cambridge University Press, 1999, pp. 146-7.

    Examples
    --------
    >>> import numpy as np
    >>> coeff = [3.2, 2, 1]
    >>> np.roots(coeff)
    array([-0.3125+0.46351241j, -0.3125-0.46351241j])

    """
    # If input is scalar, this makes it an array
    p = atleast_1d(p)
    if p.ndim != 1:
        raise ValueError("Input must be a rank-1 array.")

    # find non-zero array entries
    non_zero = NX.nonzero(NX.ravel(p))[0]

    # Return an empty array if polynomial is all zeros
    if len(non_zero) == 0:
        return NX.array([])

    # find the number of trailing zeros -- this is the number of roots at 0.
    trailing_zeros = len(p) - non_zero[-1] - 1

    # strip leading and trailing zeros
    p = p[int(non_zero[0]):int(non_zero[-1]) + 1]

    # casting: if incoming array isn't floating point, make it floating point.
    if not issubclass(p.dtype.type, (NX.floating, NX.complexfloating)):
        p = p.astype(float)

    N = len(p)
    if N > 1:
        # build companion matrix and find its eigenvalues (the roots)
        A = diag(NX.ones((N - 2,), p.dtype), -1)
        A[0, :] = -p[1:] / p[0]
        roots = eigvals(A)
    else:
        roots = NX.array([])

    # tack any zeros onto the back of the array
    roots = hstack((roots, NX.zeros(trailing_zeros, roots.dtype)))
    return roots


def _polyint_dispatcher(p, m=None, k=None):
    return (p,)


@array_function_dispatch(_polyint_dispatcher)
def polyint(p, m=1, k=None):
    """
    Return an antiderivative (indefinite integral) of a polynomial.

    .. note::
       This forms part of the old polynomial API. Since version 1.4, the
       new polynomial API defined in `numpy.polynomial` is preferred.
       A summary of the differences can be found in the
       :doc:`transition guide </reference/routines.polynomials>`.

    The returned order `m` antiderivative `P` of polynomial `p` satisfies
    :math:`\\frac{d^m}{dx^m}P(x) = p(x)` and is defined up to `m - 1`
    integration constants `k`. The constants determine the low-order
    polynomial part

    .. math:: \\frac{k_{m-1}}{0!} x^0 + \\ldots + \\frac{k_0}{(m-1)!}x^{m-1}

    of `P` so that :math:`P^{(j)}(0) = k_{m-j-1}`.

    Parameters
    ----------
    p : array_like or poly1d
        Polynomial to integrate.
        A sequence is interpreted as polynomial coefficients, see `poly1d`.
    m : int, optional
        Order of the antiderivative. (Default: 1)
    k : list of `m` scalars or scalar, optional
        Integration constants. They are given in the order of integration:
        those corresponding to highest-order terms come first.

        If ``None`` (default), all constants are assumed to be zero.
        If `m = 1`, a single scalar can be given instead of a list.

    See Also
    --------
    polyder : derivative of a polynomial
    poly1d.integ : equivalent method

    Examples
    --------

    The defining property of the antiderivative:

    >>> import numpy as np

    >>> p = np.poly1d([1,1,1])
    >>> P = np.polyint(p)
    >>> P
     poly1d([ 0.33333333,  0.5       ,  1.        ,  0.        ]) # may vary
    >>> np.polyder(P) == p
    True

    The integration constants default to zero, but can be specified:

    >>> P = np.polyint(p, 3)
    >>> P(0)
    0.0
    >>> np.polyder(P)(0)
    0.0
    >>> np.polyder(P, 2)(0)
    0.0
    >>> P = np.polyint(p, 3, k=[6,5,3])
    >>> P
    poly1d([ 0.01666667,  0.04166667,  0.16666667,  3. ,  5. ,  3. ]) # may vary

    Note that 3 = 6 / 2!, and that the constants are given in the order of
    integrations. Constant of the highest-order polynomial term comes first:

    >>> np.polyder(P, 2)(0)
    6.0
    >>> np.polyder(P, 1)(0)
    5.0
    >>> P(0)
    3.0

    """
    m = int(m)
    if m < 0:
        raise ValueError("Order of integral must be positive (see polyder)")
    if k is None:
        k = NX.zeros(m, float)
    k = atleast_1d(k)
    if len(k) == 1 and m > 1:
        k = k[0] * NX.ones(m, float)
    if len(k) < m:
        raise ValueError(
              "k must be a scalar or a rank-1 array of length 1 or >m.")

    truepoly = isinstance(p, poly1d)
    p = NX.asarray(p)
    if m == 0:
        if truepoly:
            return poly1d(p)
        return p
    else:
        # Note: this must work also with object and integer arrays
        y = NX.concatenate((p.__truediv__(NX.arange(len(p), 0, -1)), [k[0]]))
        val = polyint(y, m - 1, k=k[1:])
        if truepoly:
            return poly1d(val)
        return val


def _polyder_dispatcher(p, m=None):
    return (p,)


@array_function_dispatch(_polyder_dispatcher)
def polyder(p, m=1):
    """
    Return the derivative of the specified order of a polynomial.

    .. note::
       This forms part of the old polynomial API. Since version 1.4, the
       new polynomial API defined in `numpy.polynomial` is preferred.
       A summary of the differences can be found in the
       :doc:`transition guide </reference/routines.polynomials>`.

    Parameters
    ----------
    p : poly1d or sequence
        Polynomial to differentiate.
        A sequence is interpreted as polynomial coefficients, see `poly1d`.
    m : int, optional
        Order of differentiation (default: 1)

    Returns
    -------
    der : poly1d
        A new polynomial representing the derivative.

    See Also
    --------
    polyint : Anti-derivative of a polynomial.
    poly1d : Class for one-dimensional polynomials.

    Examples
    --------

    The derivative of the polynomial :math:`x^3 + x^2 + x^1 + 1` is:

    >>> import numpy as np

    >>> p = np.poly1d([1,1,1,1])
    >>> p2 = np.polyder(p)
    >>> p2
    poly1d([3, 2, 1])

    which evaluates to:

    >>> p2(2.)
    17.0

    We can verify this, approximating the derivative with
    ``(f(x + h) - f(x))/h``:

    >>> (p(2. + 0.001) - p(2.)) / 0.001
    17.007000999997857

    The fourth-order derivative of a 3rd-order polynomial is zero:

    >>> np.polyder(p, 2)
    poly1d([6, 2])
    >>> np.polyder(p, 3)
    poly1d([6])
    >>> np.polyder(p, 4)
    poly1d([0])

    """
    m = int(m)
    if m < 0:
        raise ValueError("Order of derivative must be positive (see polyint)")

    truepoly = isinstance(p, poly1d)
    p = NX.asarray(p)
    n = len(p) - 1
    y = p[:-1] * NX.arange(n, 0, -1)
    if m == 0:
        val = p
    else:
        val = polyder(y, m - 1)
    if truepoly:
        val = poly1d(val)
    return val


def _polyfit_dispatcher(x, y, deg, rcond=None, full=None, w=None, cov=None):
    return (x, y, w)


@array_function_dispatch(_polyfit_dispatcher)
def polyfit(x, y, deg, rcond=None, full=False, w=None, cov=False):
    """
    Least squares polynomial fit.

    .. note::
       This forms part of the old polynomial API. Since version 1.4, the
       new polynomial API defined in `numpy.polynomial` is preferred.
       A summary of the differences can be found in the
       :doc:`transition guide </reference/routines.polynomials>`.

    Fit a polynomial ``p(x) = p[0] * x**deg + ... + p[deg]`` of degree `deg`
    to points `(x, y)`. Returns a vector of coefficients `p` that minimises
    the squared error in the order `deg`, `deg-1`, ... `0`.

    The `Polynomial.fit <numpy.polynomial.polynomial.Polynomial.fit>` class
    method is recommended for new code as it is more stable numerically. See
    the documentation of the method for more information.

    Parameters
    ----------
    x : array_like, shape (M,)
        x-coordinates of the M sample points ``(x[i], y[i])``.
    y : array_like, shape (M,) or (M, K)
        y-coordinates of the sample points. Several data sets of sample
        points sharing the same x-coordinates can be fitted at once by
        passing in a 2D-array that contains one dataset per column.
    deg : int
        Degree of the fitting polynomial
    rcond : float, optional
        Relative condition number of the fit. Singular values smaller than
        this relative to the largest singular value will be ignored. The
        default value is len(x)*eps, where eps is the relative precision of
        the float type, about 2e-16 in most cases.
    full : bool, optional
        Switch determining nature of return value. When it is False (the
        default) just the coefficients are returned, when True diagnostic
        information from the singular value decomposition is also returned.
    w : array_like, shape (M,), optional
        Weights. If not None, the weight ``w[i]`` applies to the unsquared
        residual ``y[i] - y_hat[i]`` at ``x[i]``. Ideally the weights are
        chosen so that the errors of the products ``w[i]*y[i]`` all have the
        same variance.  When using inverse-variance weighting, use
        ``w[i] = 1/sigma(y[i])``.  The default value is None.
    cov : bool or str, optional
        If given and not `False`, return not just the estimate but also its
        covariance matrix. By default, the covariance are scaled by
        chi2/dof, where dof = M - (deg + 1), i.e., the weights are presumed
        to be unreliable except in a relative sense and everything is scaled
        such that the reduced chi2 is unity. This scaling is omitted if
        ``cov='unscaled'``, as is relevant for the case that the weights are
        w = 1/sigma, with sigma known to be a reliable estimate of the
        uncertainty.

    Returns
    -------
    p : ndarray, shape (deg + 1,) or (deg + 1, K)
        Polynomial coefficients, highest power first.  If `y` was 2-D, the
        coefficients for `k`-th data set are in ``p[:,k]``.

    residuals, rank, singular_values, rcond
        These values are only returned if ``full == True``

        - residuals -- sum of squared residuals of the least squares fit
        - rank -- the effective rank of the scaled Vandermonde
           coefficient matrix
        - singular_values -- singular values of the scaled Vandermonde
           coefficient matrix
        - rcond -- value of `rcond`.

        For more details, see `numpy.linalg.lstsq`.

    V : ndarray, shape (deg + 1, deg + 1) or (deg + 1, deg + 1, K)
        Present only if ``full == False`` and ``cov == True``.  The covariance
        matrix of the polynomial coefficient estimates.  The diagonal of
        this matrix are the variance estimates for each coefficient.  If y
        is a 2-D array, then the covariance matrix for the `k`-th data set
        are in ``V[:,:,k]``


    Warns
    -----
    RankWarning
        The rank of the coefficient matrix in the least-squares fit is
        deficient. The warning is only raised if ``full == False``.

        The warnings can be turned off by

        >>> import warnings
        >>> warnings.simplefilter('ignore', np.exceptions.RankWarning)

    See Also
    --------
    polyval : Compute polynomial values.
    linalg.lstsq : Computes a least-squares fit.
    scipy.interpolate.UnivariateSpline : Computes spline fits.

    Notes
    -----
    The solution minimizes the squared error

    .. math::
        E = \\sum_{j=0}^k |p(x_j) - y_j|^2

    in the equations::

        x[0]**n * p[0] + ... + x[0] * p[n-1] + p[n] = y[0]
        x[1]**n * p[0] + ... + x[1] * p[n-1] + p[n] = y[1]
        ...
        x[k]**n * p[0] + ... + x[k] * p[n-1] + p[n] = y[k]

    The coefficient matrix of the coefficients `p` is a Vandermonde matrix.

    `polyfit` issues a `~exceptions.RankWarning` when the least-squares fit is
    badly conditioned. This implies that the best fit is not well-defined due
    to numerical error. The results may be improved by lowering the polynomial
    degree or by replacing `x` by `x` - `x`.mean(). The `rcond` parameter
    can also be set to a value smaller than its default, but the resulting
    fit may be spurious: including contributions from the small singular
    values can add numerical noise to the result.

    Note that fitting polynomial coefficients is inherently badly conditioned
    when the degree of the polynomial is large or the interval of sample points
    is badly centered. The quality of the fit should always be checked in these
    cases. When polynomial fits are not satisfactory, splines may be a good
    alternative.

    References
    ----------
    .. [1] Wikipedia, "Curve fitting",
           https://en.wikipedia.org/wiki/Curve_fitting
    .. [2] Wikipedia, "Polynomial interpolation",
           https://en.wikipedia.org/wiki/Polynomial_interpolation

    Examples
    --------
    >>> import numpy as np
    >>> import warnings
    >>> x = np.array([0.0, 1.0, 2.0, 3.0,  4.0,  5.0])
    >>> y = np.array([0.0, 0.8, 0.9, 0.1, -0.8, -1.0])
    >>> z = np.polyfit(x, y, 3)
    >>> z
    array([ 0.08703704, -0.81349206,  1.69312169, -0.03968254]) # may vary

    It is convenient to use `poly1d` objects for dealing with polynomials:

    >>> p = np.poly1d(z)
    >>> p(0.5)
    0.6143849206349179 # may vary
    >>> p(3.5)
    -0.34732142857143039 # may vary
    >>> p(10)
    22.579365079365115 # may vary

    High-order polynomials may oscillate wildly:

    >>> with warnings.catch_warnings():
    ...     warnings.simplefilter('ignore', np.exceptions.RankWarning)
    ...     p30 = np.poly1d(np.polyfit(x, y, 30))
    ...
    >>> p30(4)
    -0.80000000000000204 # may vary
    >>> p30(5)
    -0.99999999999999445 # may vary
    >>> p30(4.5)
    -0.10547061179440398 # may vary

    Illustration:

    >>> import matplotlib.pyplot as plt
    >>> xp = np.linspace(-2, 6, 100)
    >>> _ = plt.plot(x, y, '.', xp, p(xp), '-', xp, p30(xp), '--')
    >>> plt.ylim(-2,2)
    (-2, 2)
    >>> plt.show()

    """
    order = int(deg) + 1
    x = NX.asarray(x) + 0.0
    y = NX.asarray(y) + 0.0

    # check arguments.
    if deg < 0:
        raise ValueError("expected deg >= 0")
    if x.ndim != 1:
        raise TypeError("expected 1D vector for x")
    if x.size == 0:
        raise TypeError("expected non-empty vector for x")
    if y.ndim < 1 or y.ndim > 2:
        raise TypeError("expected 1D or 2D array for y")
    if x.shape[0] != y.shape[0]:
        raise TypeError("expected x and y to have same length")

    # set rcond
    if rcond is None:
        rcond = len(x) * finfo(x.dtype).eps

    # set up least squares equation for powers of x
    lhs = vander(x, order)
    rhs = y

    # apply weighting
    if w is not None:
        w = NX.asarray(w) + 0.0
        if w.ndim != 1:
            raise TypeError("expected a 1-d array for weights")
        if w.shape[0] != y.shape[0]:
            raise TypeError("expected w and y to have the same length")
        lhs *= w[:, NX.newaxis]
        if rhs.ndim == 2:
            rhs *= w[:, NX.newaxis]
        else:
            rhs *= w

    # scale lhs to improve condition number and solve
    scale = NX.sqrt((lhs * lhs).sum(axis=0))
    lhs /= scale
    c, resids, rank, s = lstsq(lhs, rhs, rcond)
    c = (c.T / scale).T  # broadcast scale coefficients

    # warn on rank reduction, which indicates an ill conditioned matrix
    if rank != order and not full:
        msg = "Polyfit may be poorly conditioned"
        warnings.warn(msg, RankWarning, stacklevel=2)

    if full:
        return c, resids, rank, s, rcond
    elif cov:
        Vbase = inv(dot(lhs.T, lhs))
        Vbase /= NX.outer(scale, scale)
        if cov == "unscaled":
            fac = 1
        else:
            if len(x) <= order:
                raise ValueError("the number of data points must exceed order "
                                 "to scale the covariance matrix")
            # note, this used to be: fac = resids / (len(x) - order - 2.0)
            # it was decided that the "- 2" (originally justified by "Bayesian
            # uncertainty analysis") is not what the user expects
            # (see gh-11196 and gh-11197)
            fac = resids / (len(x) - order)
        if y.ndim == 1:
            return c, Vbase * fac
        else:
            return c, Vbase[:, :, NX.newaxis] * fac
    else:
        return c


def _polyval_dispatcher(p, x):
    return (p, x)


@array_function_dispatch(_polyval_dispatcher)
def polyval(p, x):
    """
    Evaluate a polynomial at specific values.

    .. note::
       This forms part of the old polynomial API. Since version 1.4, the
       new polynomial API defined in `numpy.polynomial` is preferred.
       A summary of the differences can be found in the
       :doc:`transition guide </reference/routines.polynomials>`.

    If `p` is of length N, this function returns the value::

        p[0]*x**(N-1) + p[1]*x**(N-2) + ... + p[N-2]*x + p[N-1]

    If `x` is a sequence, then ``p(x)`` is returned for each element of ``x``.
    If `x` is another polynomial then the composite polynomial ``p(x(t))``
    is returned.

    Parameters
    ----------
    p : array_like or poly1d object
       1D array of polynomial coefficients (including coefficients equal
       to zero) from highest degree to the constant term, or an
       instance of poly1d.
    x : array_like or poly1d object
       A number, an array of numbers, or an instance of poly1d, at
       which to evaluate `p`.

    Returns
    -------
    values : ndarray or poly1d
       If `x` is a poly1d instance, the result is the composition of the two
       polynomials, i.e., `x` is "substituted" in `p` and the simplified
       result is returned. In addition, the type of `x` - array_like or
       poly1d - governs the type of the output: `x` array_like => `values`
       array_like, `x` a poly1d object => `values` is also.

    See Also
    --------
    poly1d: A polynomial class.

    Notes
    -----
    Horner's scheme [1]_ is used to evaluate the polynomial. Even so,
    for polynomials of high degree the values may be inaccurate due to
    rounding errors. Use carefully.

    If `x` is a subtype of `ndarray` the return value will be of the same type.

    References
    ----------
    .. [1] I. N. Bronshtein, K. A. Semendyayev, and K. A. Hirsch (Eng.
       trans. Ed.), *Handbook of Mathematics*, New York, Van Nostrand
       Reinhold Co., 1985, pg. 720.

    Examples
    --------
    >>> import numpy as np
    >>> np.polyval([3,0,1], 5)  # 3 * 5**2 + 0 * 5**1 + 1
    76
    >>> np.polyval([3,0,1], np.poly1d(5))
    poly1d([76])
    >>> np.polyval(np.poly1d([3,0,1]), 5)
    76
    >>> np.polyval(np.poly1d([3,0,1]), np.poly1d(5))
    poly1d([76])

    """
    p = NX.asarray(p)
    if isinstance(x, poly1d):
        y = 0
    else:
        x = NX.asanyarray(x)
        y = NX.zeros_like(x)
    for pv in p:
        y = y * x + pv
    return y


def _binary_op_dispatcher(a1, a2):
    return (a1, a2)


@array_function_dispatch(_binary_op_dispatcher)
def polyadd(a1, a2):
    """
    Find the sum of two polynomials.

    .. note::
       This forms part of the old polynomial API. Since version 1.4, the
       new polynomial API defined in `numpy.polynomial` is preferred.
       A summary of the differences can be found in the
       :doc:`transition guide </reference/routines.polynomials>`.

    Returns the polynomial resulting from the sum of two input polynomials.
    Each input must be either a poly1d object or a 1D sequence of polynomial
    coefficients, from highest to lowest degree.

    Parameters
    ----------
    a1, a2 : array_like or poly1d object
        Input polynomials.

    Returns
    -------
    out : ndarray or poly1d object
        The sum of the inputs. If either input is a poly1d object, then the
        output is also a poly1d object. Otherwise, it is a 1D array of
        polynomial coefficients from highest to lowest degree.

    See Also
    --------
    poly1d : A one-dimensional polynomial class.
    poly, polyadd, polyder, polydiv, polyfit, polyint, polysub, polyval

    Examples
    --------
    >>> import numpy as np
    >>> np.polyadd([1, 2], [9, 5, 4])
    array([9, 6, 6])

    Using poly1d objects:

    >>> p1 = np.poly1d([1, 2])
    >>> p2 = np.poly1d([9, 5, 4])
    >>> print(p1)
    1 x + 2
    >>> print(p2)
       2
    9 x + 5 x + 4
    >>> print(np.polyadd(p1, p2))
       2
    9 x + 6 x + 6

    """
    truepoly = (isinstance(a1, poly1d) or isinstance(a2, poly1d))
    a1 = atleast_1d(a1)
    a2 = atleast_1d(a2)
    diff = len(a2) - len(a1)
    if diff == 0:
        val = a1 + a2
    elif diff > 0:
        zr = NX.zeros(diff, a1.dtype)
        val = NX.concatenate((zr, a1)) + a2
    else:
        zr = NX.zeros(abs(diff), a2.dtype)
        val = a1 + NX.concatenate((zr, a2))
    if truepoly:
        val = poly1d(val)
    return val


@array_function_dispatch(_binary_op_dispatcher)
def polysub(a1, a2):
    """
    Difference (subtraction) of two polynomials.

    .. note::
       This forms part of the old polynomial API. Since version 1.4, the
       new polynomial API defined in `numpy.polynomial` is preferred.
       A summary of the differences can be found in the
       :doc:`transition guide </reference/routines.polynomials>`.

    Given two polynomials `a1` and `a2`, returns ``a1 - a2``.
    `a1` and `a2` can be either array_like sequences of the polynomials'
    coefficients (including coefficients equal to zero), or `poly1d` objects.

    Parameters
    ----------
    a1, a2 : array_like or poly1d
        Minuend and subtrahend polynomials, respectively.

    Returns
    -------
    out : ndarray or poly1d
        Array or `poly1d` object of the difference polynomial's coefficients.

    See Also
    --------
    polyval, polydiv, polymul, polyadd

    Examples
    --------

    .. math:: (2 x^2 + 10 x - 2) - (3 x^2 + 10 x -4) = (-x^2 + 2)

    >>> import numpy as np

    >>> np.polysub([2, 10, -2], [3, 10, -4])
    array([-1,  0,  2])

    """
    truepoly = (isinstance(a1, poly1d) or isinstance(a2, poly1d))
    a1 = atleast_1d(a1)
    a2 = atleast_1d(a2)
    diff = len(a2) - len(a1)
    if diff == 0:
        val = a1 - a2
    elif diff > 0:
        zr = NX.zeros(diff, a1.dtype)
        val = NX.concatenate((zr, a1)) - a2
    else:
        zr = NX.zeros(abs(diff), a2.dtype)
        val = a1 - NX.concatenate((zr, a2))
    if truepoly:
        val = poly1d(val)
    return val


@array_function_dispatch(_binary_op_dispatcher)
def polymul(a1, a2):
    """
    Find the product of two polynomials.

    .. note::
       This forms part of the old polynomial API. Since version 1.4, the
       new polynomial API defined in `numpy.polynomial` is preferred.
       A summary of the differences can be found in the
       :doc:`transition guide </reference/routines.polynomials>`.

    Finds the polynomial resulting from the multiplication of the two input
    polynomials. Each input must be either a poly1d object or a 1D sequence
    of polynomial coefficients, from highest to lowest degree.

    Parameters
    ----------
    a1, a2 : array_like or poly1d object
        Input polynomials.

    Returns
    -------
    out : ndarray or poly1d object
        The polynomial resulting from the multiplication of the inputs. If
        either inputs is a poly1d object, then the output is also a poly1d
        object. Otherwise, it is a 1D array of polynomial coefficients from
        highest to lowest degree.

    See Also
    --------
    poly1d : A one-dimensional polynomial class.
    poly, polyadd, polyder, polydiv, polyfit, polyint, polysub, polyval
    convolve : Array convolution. Same output as polymul, but has parameter
               for overlap mode.

    Examples
    --------
    >>> import numpy as np
    >>> np.polymul([1, 2, 3], [9, 5, 1])
    array([ 9, 23, 38, 17,  3])

    Using poly1d objects:

    >>> p1 = np.poly1d([1, 2, 3])
    >>> p2 = np.poly1d([9, 5, 1])
    >>> print(p1)
       2
    1 x + 2 x + 3
    >>> print(p2)
       2
    9 x + 5 x + 1
    >>> print(np.polymul(p1, p2))
       4      3      2
    9 x + 23 x + 38 x + 17 x + 3

    """
    truepoly = (isinstance(a1, poly1d) or isinstance(a2, poly1d))
    a1, a2 = poly1d(a1), poly1d(a2)
    val = NX.convolve(a1, a2)
    if truepoly:
        val = poly1d(val)
    return val


def _polydiv_dispatcher(u, v):
    return (u, v)


@array_function_dispatch(_polydiv_dispatcher)
def polydiv(u, v):
    """
    Returns the quotient and remainder of polynomial division.

    .. note::
       This forms part of the old polynomial API. Since version 1.4, the
       new polynomial API defined in `numpy.polynomial` is preferred.
       A summary of the differences can be found in the
       :doc:`transition guide </reference/routines.polynomials>`.

    The input arrays are the coefficients (including any coefficients
    equal to zero) of the "numerator" (dividend) and "denominator"
    (divisor) polynomials, respectively.

    Parameters
    ----------
    u : array_like or poly1d
        Dividend polynomial's coefficients.

    v : array_like or poly1d
        Divisor polynomial's coefficients.

    Returns
    -------
    q : ndarray
        Coefficients, including those equal to zero, of the quotient.
    r : ndarray
        Coefficients, including those equal to zero, of the remainder.

    See Also
    --------
    poly, polyadd, polyder, polydiv, polyfit, polyint, polymul, polysub
    polyval

    Notes
    -----
    Both `u` and `v` must be 0-d or 1-d (ndim = 0 or 1), but `u.ndim` need
    not equal `v.ndim`. In other words, all four possible combinations -
    ``u.ndim = v.ndim = 0``, ``u.ndim = v.ndim = 1``,
    ``u.ndim = 1, v.ndim = 0``, and ``u.ndim = 0, v.ndim = 1`` - work.

    Examples
    --------

    .. math:: \\frac{3x^2 + 5x + 2}{2x + 1} = 1.5x + 1.75, remainder 0.25

    >>> import numpy as np

    >>> x = np.array([3.0, 5.0, 2.0])
    >>> y = np.array([2.0, 1.0])
    >>> np.polydiv(x, y)
    (array([1.5 , 1.75]), array([0.25]))

    """
    truepoly = (isinstance(u, poly1d) or isinstance(v, poly1d))
    u = atleast_1d(u) + 0.0
    v = atleast_1d(v) + 0.0
    # w has the common type
    w = u[0] + v[0]
    m = len(u) - 1
    n = len(v) - 1
    scale = 1. / v[0]
    q = NX.zeros((max(m - n + 1, 1),), w.dtype)
    r = u.astype(w.dtype)
    for k in range(m - n + 1):
        d = scale * r[k]
        q[k] = d
        r[k:k + n + 1] -= d * v
    while NX.allclose(r[0], 0, rtol=1e-14) and (r.shape[-1] > 1):
        r = r[1:]
    if truepoly:
        return poly1d(q), poly1d(r)
    return q, r


_poly_mat = re.compile(r"\*\*([0-9]*)")
def _raise_power(astr, wrap=70):
    n = 0
    line1 = ''
    line2 = ''
    output = ' '
    while True:
        mat = _poly_mat.search(astr, n)
        if mat is None:
            break
        span = mat.span()
        power = mat.groups()[0]
        partstr = astr[n:span[0]]
        n = span[1]
        toadd2 = partstr + ' ' * (len(power) - 1)
        toadd1 = ' ' * (len(partstr) - 1) + power
        if ((len(line2) + len(toadd2) > wrap) or
                (len(line1) + len(toadd1) > wrap)):
            output += line1 + "\n" + line2 + "\n "
            line1 = toadd1
            line2 = toadd2
        else:
            line2 += partstr + ' ' * (len(power) - 1)
            line1 += ' ' * (len(partstr) - 1) + power
    output += line1 + "\n" + line2
    return output + astr[n:]


@set_module('numpy')
class poly1d:
    """
    A one-dimensional polynomial class.

    .. note::
       This forms part of the old polynomial API. Since version 1.4, the
       new polynomial API defined in `numpy.polynomial` is preferred.
       A summary of the differences can be found in the
       :doc:`transition guide </reference/routines.polynomials>`.

    A convenience class, used to encapsulate "natural" operations on
    polynomials so that said operations may take on their customary
    form in code (see Examples).

    Parameters
    ----------
    c_or_r : array_like
        The polynomial's coefficients, in decreasing powers, or if
        the value of the second parameter is True, the polynomial's
        roots (values where the polynomial evaluates to 0).  For example,
        ``poly1d([1, 2, 3])`` returns an object that represents
        :math:`x^2 + 2x + 3`, whereas ``poly1d([1, 2, 3], True)`` returns
        one that represents :math:`(x-1)(x-2)(x-3) = x^3 - 6x^2 + 11x -6`.
    r : bool, optional
        If True, `c_or_r` specifies the polynomial's roots; the default
        is False.
    variable : str, optional
        Changes the variable used when printing `p` from `x` to `variable`
        (see Examples).

    Examples
    --------
    >>> import numpy as np

    Construct the polynomial :math:`x^2 + 2x + 3`:

    >>> import numpy as np

    >>> p = np.poly1d([1, 2, 3])
    >>> print(np.poly1d(p))
       2
    1 x + 2 x + 3

    Evaluate the polynomial at :math:`x = 0.5`:

    >>> p(0.5)
    4.25

    Find the roots:

    >>> p.r
    array([-1.+1.41421356j, -1.-1.41421356j])
    >>> p(p.r)
    array([ -4.44089210e-16+0.j,  -4.44089210e-16+0.j]) # may vary

    These numbers in the previous line represent (0, 0) to machine precision

    Show the coefficients:

    >>> p.c
    array([1, 2, 3])

    Display the order (the leading zero-coefficients are removed):

    >>> p.order
    2

    Show the coefficient of the k-th power in the polynomial
    (which is equivalent to ``p.c[-(i+1)]``):

    >>> p[1]
    2

    Polynomials can be added, subtracted, multiplied, and divided
    (returns quotient and remainder):

    >>> p * p
    poly1d([ 1,  4, 10, 12,  9])

    >>> (p**3 + 4) / p
    (poly1d([ 1.,  4., 10., 12.,  9.]), poly1d([4.]))

    ``asarray(p)`` gives the coefficient array, so polynomials can be
    used in all functions that accept arrays:

    >>> p**2 # square of polynomial
    poly1d([ 1,  4, 10, 12,  9])

    >>> np.square(p) # square of individual coefficients
    array([1, 4, 9])

    The variable used in the string representation of `p` can be modified,
    using the `variable` parameter:

    >>> p = np.poly1d([1,2,3], variable='z')
    >>> print(p)
       2
    1 z + 2 z + 3

    Construct a polynomial from its roots:

    >>> np.poly1d([1, 2], True)
    poly1d([ 1., -3.,  2.])

    This is the same polynomial as obtained by:

    >>> np.poly1d([1, -1]) * np.poly1d([1, -2])
    poly1d([ 1, -3,  2])

    """
    __hash__ = None

    @property
    def coeffs(self):
        """ The polynomial coefficients """
        return self._coeffs

    @coeffs.setter
    def coeffs(self, value):
        # allowing this makes p.coeffs *= 2 legal
        if value is not self._coeffs:
            raise AttributeError("Cannot set attribute")

    @property
    def variable(self):
        """ The name of the polynomial variable """
        return self._variable

    # calculated attributes
    @property
    def order(self):
        """ The order or degree of the polynomial """
        return len(self._coeffs) - 1

    @property
    def roots(self):
        """ The roots of the polynomial, where self(x) == 0 """
        return roots(self._coeffs)

    # our internal _coeffs property need to be backed by __dict__['coeffs'] for
    # scipy to work correctly.
    @property
    def _coeffs(self):
        return self.__dict__['coeffs']

    @_coeffs.setter
    def _coeffs(self, coeffs):
        self.__dict__['coeffs'] = coeffs

    # alias attributes
    r = roots
    c = coef = coefficients = coeffs
    o = order

    def __init__(self, c_or_r, r=False, variable=None):
        if isinstance(c_or_r, poly1d):
            self._variable = c_or_r._variable
            self._coeffs = c_or_r._coeffs

            if set(c_or_r.__dict__) - set(self.__dict__):
                msg = ("In the future extra properties will not be copied "
                       "across when constructing one poly1d from another")
                warnings.warn(msg, FutureWarning, stacklevel=2)
                self.__dict__.update(c_or_r.__dict__)

            if variable is not None:
                self._variable = variable
            return
        if r:
            c_or_r = poly(c_or_r)
        c_or_r = atleast_1d(c_or_r)
        if c_or_r.ndim > 1:
            raise ValueError("Polynomial must be 1d only.")
        c_or_r = trim_zeros(c_or_r, trim='f')
        if len(c_or_r) == 0:
            c_or_r = NX.array([0], dtype=c_or_r.dtype)
        self._coeffs = c_or_r
        if variable is None:
            variable = 'x'
        self._variable = variable

    def __array__(self, t=None, copy=None):
        if t:
            return NX.asarray(self.coeffs, t, copy=copy)
        else:
            return NX.asarray(self.coeffs, copy=copy)

    def __repr__(self):
        vals = repr(self.coeffs)
        vals = vals[6:-1]
        return f"poly1d({vals})"

    def __len__(self):
        return self.order

    def __str__(self):
        thestr = "0"
        var = self.variable

        # Remove leading zeros
        coeffs = self.coeffs[NX.logical_or.accumulate(self.coeffs != 0)]
        N = len(coeffs) - 1

        def fmt_float(q):
            s = f'{q:.4g}'
            s = s.removesuffix('.0000')
            return s

        for k, coeff in enumerate(coeffs):
            if not iscomplex(coeff):
                coefstr = fmt_float(real(coeff))
            elif real(coeff) == 0:
                coefstr = f'{fmt_float(imag(coeff))}j'
            else:
                coefstr = f'({fmt_float(real(coeff))} + {fmt_float(imag(coeff))}j)'

            power = (N - k)
            if power == 0:
                if coefstr != '0':
                    newstr = f'{coefstr}'
                elif k == 0:
                    newstr = '0'
                else:
                    newstr = ''
            elif power == 1:
                if coefstr == '0':
                    newstr = ''
                elif coefstr == 'b':
                    newstr = var
                else:
                    newstr = f'{coefstr} {var}'
            elif coefstr == '0':
                newstr = ''
            elif coefstr == 'b':
                newstr = '%s**%d' % (var, power,)
            else:
                newstr = '%s %s**%d' % (coefstr, var, power)

            if k > 0:
                if newstr != '':
                    if newstr.startswith('-'):
                        thestr = f"{thestr} - {newstr[1:]}"
                    else:
                        thestr = f"{thestr} + {newstr}"
            else:
                thestr = newstr
        return _raise_power(thestr)

    def __call__(self, val):
        return polyval(self.coeffs, val)

    def __neg__(self):
        return poly1d(-self.coeffs)

    def __pos__(self):
        return self

    def __mul__(self, other):
        if isscalar(other):
            return poly1d(self.coeffs * other)
        else:
            other = poly1d(other)
            return poly1d(polymul(self.coeffs, other.coeffs))

    def __rmul__(self, other):
        if isscalar(other):
            return poly1d(other * self.coeffs)
        else:
            other = poly1d(other)
            return poly1d(polymul(self.coeffs, other.coeffs))

    def __add__(self, other):
        other = poly1d(other)
        return poly1d(polyadd(self.coeffs, other.coeffs))

    def __radd__(self, other):
        other = poly1d(other)
        return poly1d(polyadd(self.coeffs, other.coeffs))

    def __pow__(self, val):
        if not isscalar(val) or int(val) != val or val < 0:
            raise ValueError("Power to non-negative integers only.")
        res = [1]
        for _ in range(val):
            res = polymul(self.coeffs, res)
        return poly1d(res)

    def __sub__(self, other):
        other = poly1d(other)
        return poly1d(polysub(self.coeffs, other.coeffs))

    def __rsub__(self, other):
        other = poly1d(other)
        return poly1d(polysub(other.coeffs, self.coeffs))

    def __truediv__(self, other):
        if isscalar(other):
            return poly1d(self.coeffs / other)
        else:
            other = poly1d(other)
            return polydiv(self, other)

    def __rtruediv__(self, other):
        if isscalar(other):
            return poly1d(other / self.coeffs)
        else:
            other = poly1d(other)
            return polydiv(other, self)

    def __eq__(self, other):
        if not isinstance(other, poly1d):
            return NotImplemented
        if self.coeffs.shape != other.coeffs.shape:
            return False
        return (self.coeffs == other.coeffs).all()

    def __ne__(self, other):
        if not isinstance(other, poly1d):
            return NotImplemented
        return not self.__eq__(other)

    def __getitem__(self, val):
        ind = self.order - val
        if val > self.order:
            return self.coeffs.dtype.type(0)
        if val < 0:
            return self.coeffs.dtype.type(0)
        return self.coeffs[ind]

    def __setitem__(self, key, val):
        ind = self.order - key
        if key < 0:
            raise ValueError("Does not support negative powers.")
        if key > self.order:
            zr = NX.zeros(key - self.order, self.coeffs.dtype)
            self._coeffs = NX.concatenate((zr, self.coeffs))
            ind = 0
        self._coeffs[ind] = val

    def __iter__(self):
        return iter(self.coeffs)

    def integ(self, m=1, k=0):
        """
        Return an antiderivative (indefinite integral) of this polynomial.

        Refer to `polyint` for full documentation.

        See Also
        --------
        polyint : equivalent function

        """
        return poly1d(polyint(self.coeffs, m=m, k=k))

    def deriv(self, m=1):
        """
        Return a derivative of this polynomial.

        Refer to `polyder` for full documentation.

        See Also
        --------
        polyder : equivalent function

        """
        return poly1d(polyder(self.coeffs, m=m))

# Stuff to do on module import


warnings.simplefilter('always', RankWarning)

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\_polynomial_impl.py ===
"""
Functions to operate on polynomials.

"""
__all__ = ['poly', 'roots', 'polyint', 'polyder', 'polyadd',
           'polysub', 'polymul', 'polydiv', 'polyval', 'poly1d',
           'polyfit']

import functools
import re
import warnings

import numpy._core.numeric as NX
from numpy._core import (
    abs,
    array,
    atleast_1d,
    dot,
    finfo,
    hstack,
    isscalar,
    ones,
    overrides,
)
from numpy._utils import set_module
from numpy.exceptions import RankWarning
from numpy.lib._function_base_impl import trim_zeros
from numpy.lib._twodim_base_impl import diag, vander
from numpy.lib._type_check_impl import imag, iscomplex, mintypecode, real
from numpy.linalg import eigvals, inv, lstsq

array_function_dispatch = functools.partial(
    overrides.array_function_dispatch, module='numpy')


def _poly_dispatcher(seq_of_zeros):
    return seq_of_zeros


@array_function_dispatch(_poly_dispatcher)
def poly(seq_of_zeros):
    """
    Find the coefficients of a polynomial with the given sequence of roots.

    .. note::
       This forms part of the old polynomial API. Since version 1.4, the
       new polynomial API defined in `numpy.polynomial` is preferred.
       A summary of the differences can be found in the
       :doc:`transition guide </reference/routines.polynomials>`.

    Returns the coefficients of the polynomial whose leading coefficient
    is one for the given sequence of zeros (multiple roots must be included
    in the sequence as many times as their multiplicity; see Examples).
    A square matrix (or array, which will be treated as a matrix) can also
    be given, in which case the coefficients of the characteristic polynomial
    of the matrix are returned.

    Parameters
    ----------
    seq_of_zeros : array_like, shape (N,) or (N, N)
        A sequence of polynomial roots, or a square array or matrix object.

    Returns
    -------
    c : ndarray
        1D array of polynomial coefficients from highest to lowest degree:

        ``c[0] * x**(N) + c[1] * x**(N-1) + ... + c[N-1] * x + c[N]``
        where c[0] always equals 1.

    Raises
    ------
    ValueError
        If input is the wrong shape (the input must be a 1-D or square
        2-D array).

    See Also
    --------
    polyval : Compute polynomial values.
    roots : Return the roots of a polynomial.
    polyfit : Least squares polynomial fit.
    poly1d : A one-dimensional polynomial class.

    Notes
    -----
    Specifying the roots of a polynomial still leaves one degree of
    freedom, typically represented by an undetermined leading
    coefficient. [1]_ In the case of this function, that coefficient -
    the first one in the returned array - is always taken as one. (If
    for some reason you have one other point, the only automatic way
    presently to leverage that information is to use ``polyfit``.)

    The characteristic polynomial, :math:`p_a(t)`, of an `n`-by-`n`
    matrix **A** is given by

    :math:`p_a(t) = \\mathrm{det}(t\\, \\mathbf{I} - \\mathbf{A})`,

    where **I** is the `n`-by-`n` identity matrix. [2]_

    References
    ----------
    .. [1] M. Sullivan and M. Sullivan, III, "Algebra and Trigonometry,
       Enhanced With Graphing Utilities," Prentice-Hall, pg. 318, 1996.

    .. [2] G. Strang, "Linear Algebra and Its Applications, 2nd Edition,"
       Academic Press, pg. 182, 1980.

    Examples
    --------

    Given a sequence of a polynomial's zeros:

    >>> import numpy as np

    >>> np.poly((0, 0, 0)) # Multiple root example
    array([1., 0., 0., 0.])

    The line above represents z**3 + 0*z**2 + 0*z + 0.

    >>> np.poly((-1./2, 0, 1./2))
    array([ 1.  ,  0.  , -0.25,  0.  ])

    The line above represents z**3 - z/4

    >>> np.poly((np.random.random(1)[0], 0, np.random.random(1)[0]))
    array([ 1.        , -0.77086955,  0.08618131,  0.        ]) # random

    Given a square array object:

    >>> P = np.array([[0, 1./3], [-1./2, 0]])
    >>> np.poly(P)
    array([1.        , 0.        , 0.16666667])

    Note how in all cases the leading coefficient is always 1.

    """
    seq_of_zeros = atleast_1d(seq_of_zeros)
    sh = seq_of_zeros.shape

    if len(sh) == 2 and sh[0] == sh[1] and sh[0] != 0:
        seq_of_zeros = eigvals(seq_of_zeros)
    elif len(sh) == 1:
        dt = seq_of_zeros.dtype
        # Let object arrays slip through, e.g. for arbitrary precision
        if dt != object:
            seq_of_zeros = seq_of_zeros.astype(mintypecode(dt.char))
    else:
        raise ValueError("input must be 1d or non-empty square 2d array.")

    if len(seq_of_zeros) == 0:
        return 1.0
    dt = seq_of_zeros.dtype
    a = ones((1,), dtype=dt)
    for zero in seq_of_zeros:
        a = NX.convolve(a, array([1, -zero], dtype=dt), mode='full')

    if issubclass(a.dtype.type, NX.complexfloating):
        # if complex roots are all complex conjugates, the roots are real.
        roots = NX.asarray(seq_of_zeros, complex)
        if NX.all(NX.sort(roots) == NX.sort(roots.conjugate())):
            a = a.real.copy()

    return a


def _roots_dispatcher(p):
    return p


@array_function_dispatch(_roots_dispatcher)
def roots(p):
    """
    Return the roots of a polynomial with coefficients given in p.

    .. note::
       This forms part of the old polynomial API. Since version 1.4, the
       new polynomial API defined in `numpy.polynomial` is preferred.
       A summary of the differences can be found in the
       :doc:`transition guide </reference/routines.polynomials>`.

    The values in the rank-1 array `p` are coefficients of a polynomial.
    If the length of `p` is n+1 then the polynomial is described by::

      p[0] * x**n + p[1] * x**(n-1) + ... + p[n-1]*x + p[n]

    Parameters
    ----------
    p : array_like
        Rank-1 array of polynomial coefficients.

    Returns
    -------
    out : ndarray
        An array containing the roots of the polynomial.

    Raises
    ------
    ValueError
        When `p` cannot be converted to a rank-1 array.

    See also
    --------
    poly : Find the coefficients of a polynomial with a given sequence
           of roots.
    polyval : Compute polynomial values.
    polyfit : Least squares polynomial fit.
    poly1d : A one-dimensional polynomial class.

    Notes
    -----
    The algorithm relies on computing the eigenvalues of the
    companion matrix [1]_.

    References
    ----------
    .. [1] R. A. Horn & C. R. Johnson, *Matrix Analysis*.  Cambridge, UK:
        Cambridge University Press, 1999, pp. 146-7.

    Examples
    --------
    >>> import numpy as np
    >>> coeff = [3.2, 2, 1]
    >>> np.roots(coeff)
    array([-0.3125+0.46351241j, -0.3125-0.46351241j])

    """
    # If input is scalar, this makes it an array
    p = atleast_1d(p)
    if p.ndim != 1:
        raise ValueError("Input must be a rank-1 array.")

    # find non-zero array entries
    non_zero = NX.nonzero(NX.ravel(p))[0]

    # Return an empty array if polynomial is all zeros
    if len(non_zero) == 0:
        return NX.array([])

    # find the number of trailing zeros -- this is the number of roots at 0.
    trailing_zeros = len(p) - non_zero[-1] - 1

    # strip leading and trailing zeros
    p = p[int(non_zero[0]):int(non_zero[-1]) + 1]

    # casting: if incoming array isn't floating point, make it floating point.
    if not issubclass(p.dtype.type, (NX.floating, NX.complexfloating)):
        p = p.astype(float)

    N = len(p)
    if N > 1:
        # build companion matrix and find its eigenvalues (the roots)
        A = diag(NX.ones((N - 2,), p.dtype), -1)
        A[0, :] = -p[1:] / p[0]
        roots = eigvals(A)
    else:
        roots = NX.array([])

    # tack any zeros onto the back of the array
    roots = hstack((roots, NX.zeros(trailing_zeros, roots.dtype)))
    return roots


def _polyint_dispatcher(p, m=None, k=None):
    return (p,)


@array_function_dispatch(_polyint_dispatcher)
def polyint(p, m=1, k=None):
    """
    Return an antiderivative (indefinite integral) of a polynomial.

    .. note::
       This forms part of the old polynomial API. Since version 1.4, the
       new polynomial API defined in `numpy.polynomial` is preferred.
       A summary of the differences can be found in the
       :doc:`transition guide </reference/routines.polynomials>`.

    The returned order `m` antiderivative `P` of polynomial `p` satisfies
    :math:`\\frac{d^m}{dx^m}P(x) = p(x)` and is defined up to `m - 1`
    integration constants `k`. The constants determine the low-order
    polynomial part

    .. math:: \\frac{k_{m-1}}{0!} x^0 + \\ldots + \\frac{k_0}{(m-1)!}x^{m-1}

    of `P` so that :math:`P^{(j)}(0) = k_{m-j-1}`.

    Parameters
    ----------
    p : array_like or poly1d
        Polynomial to integrate.
        A sequence is interpreted as polynomial coefficients, see `poly1d`.
    m : int, optional
        Order of the antiderivative. (Default: 1)
    k : list of `m` scalars or scalar, optional
        Integration constants. They are given in the order of integration:
        those corresponding to highest-order terms come first.

        If ``None`` (default), all constants are assumed to be zero.
        If `m = 1`, a single scalar can be given instead of a list.

    See Also
    --------
    polyder : derivative of a polynomial
    poly1d.integ : equivalent method

    Examples
    --------

    The defining property of the antiderivative:

    >>> import numpy as np

    >>> p = np.poly1d([1,1,1])
    >>> P = np.polyint(p)
    >>> P
     poly1d([ 0.33333333,  0.5       ,  1.        ,  0.        ]) # may vary
    >>> np.polyder(P) == p
    True

    The integration constants default to zero, but can be specified:

    >>> P = np.polyint(p, 3)
    >>> P(0)
    0.0
    >>> np.polyder(P)(0)
    0.0
    >>> np.polyder(P, 2)(0)
    0.0
    >>> P = np.polyint(p, 3, k=[6,5,3])
    >>> P
    poly1d([ 0.01666667,  0.04166667,  0.16666667,  3. ,  5. ,  3. ]) # may vary

    Note that 3 = 6 / 2!, and that the constants are given in the order of
    integrations. Constant of the highest-order polynomial term comes first:

    >>> np.polyder(P, 2)(0)
    6.0
    >>> np.polyder(P, 1)(0)
    5.0
    >>> P(0)
    3.0

    """
    m = int(m)
    if m < 0:
        raise ValueError("Order of integral must be positive (see polyder)")
    if k is None:
        k = NX.zeros(m, float)
    k = atleast_1d(k)
    if len(k) == 1 and m > 1:
        k = k[0] * NX.ones(m, float)
    if len(k) < m:
        raise ValueError(
              "k must be a scalar or a rank-1 array of length 1 or >m.")

    truepoly = isinstance(p, poly1d)
    p = NX.asarray(p)
    if m == 0:
        if truepoly:
            return poly1d(p)
        return p
    else:
        # Note: this must work also with object and integer arrays
        y = NX.concatenate((p.__truediv__(NX.arange(len(p), 0, -1)), [k[0]]))
        val = polyint(y, m - 1, k=k[1:])
        if truepoly:
            return poly1d(val)
        return val


def _polyder_dispatcher(p, m=None):
    return (p,)


@array_function_dispatch(_polyder_dispatcher)
def polyder(p, m=1):
    """
    Return the derivative of the specified order of a polynomial.

    .. note::
       This forms part of the old polynomial API. Since version 1.4, the
       new polynomial API defined in `numpy.polynomial` is preferred.
       A summary of the differences can be found in the
       :doc:`transition guide </reference/routines.polynomials>`.

    Parameters
    ----------
    p : poly1d or sequence
        Polynomial to differentiate.
        A sequence is interpreted as polynomial coefficients, see `poly1d`.
    m : int, optional
        Order of differentiation (default: 1)

    Returns
    -------
    der : poly1d
        A new polynomial representing the derivative.

    See Also
    --------
    polyint : Anti-derivative of a polynomial.
    poly1d : Class for one-dimensional polynomials.

    Examples
    --------

    The derivative of the polynomial :math:`x^3 + x^2 + x^1 + 1` is:

    >>> import numpy as np

    >>> p = np.poly1d([1,1,1,1])
    >>> p2 = np.polyder(p)
    >>> p2
    poly1d([3, 2, 1])

    which evaluates to:

    >>> p2(2.)
    17.0

    We can verify this, approximating the derivative with
    ``(f(x + h) - f(x))/h``:

    >>> (p(2. + 0.001) - p(2.)) / 0.001
    17.007000999997857

    The fourth-order derivative of a 3rd-order polynomial is zero:

    >>> np.polyder(p, 2)
    poly1d([6, 2])
    >>> np.polyder(p, 3)
    poly1d([6])
    >>> np.polyder(p, 4)
    poly1d([0])

    """
    m = int(m)
    if m < 0:
        raise ValueError("Order of derivative must be positive (see polyint)")

    truepoly = isinstance(p, poly1d)
    p = NX.asarray(p)
    n = len(p) - 1
    y = p[:-1] * NX.arange(n, 0, -1)
    if m == 0:
        val = p
    else:
        val = polyder(y, m - 1)
    if truepoly:
        val = poly1d(val)
    return val


def _polyfit_dispatcher(x, y, deg, rcond=None, full=None, w=None, cov=None):
    return (x, y, w)


@array_function_dispatch(_polyfit_dispatcher)
def polyfit(x, y, deg, rcond=None, full=False, w=None, cov=False):
    """
    Least squares polynomial fit.

    .. note::
       This forms part of the old polynomial API. Since version 1.4, the
       new polynomial API defined in `numpy.polynomial` is preferred.
       A summary of the differences can be found in the
       :doc:`transition guide </reference/routines.polynomials>`.

    Fit a polynomial ``p(x) = p[0] * x**deg + ... + p[deg]`` of degree `deg`
    to points `(x, y)`. Returns a vector of coefficients `p` that minimises
    the squared error in the order `deg`, `deg-1`, ... `0`.

    The `Polynomial.fit <numpy.polynomial.polynomial.Polynomial.fit>` class
    method is recommended for new code as it is more stable numerically. See
    the documentation of the method for more information.

    Parameters
    ----------
    x : array_like, shape (M,)
        x-coordinates of the M sample points ``(x[i], y[i])``.
    y : array_like, shape (M,) or (M, K)
        y-coordinates of the sample points. Several data sets of sample
        points sharing the same x-coordinates can be fitted at once by
        passing in a 2D-array that contains one dataset per column.
    deg : int
        Degree of the fitting polynomial
    rcond : float, optional
        Relative condition number of the fit. Singular values smaller than
        this relative to the largest singular value will be ignored. The
        default value is len(x)*eps, where eps is the relative precision of
        the float type, about 2e-16 in most cases.
    full : bool, optional
        Switch determining nature of return value. When it is False (the
        default) just the coefficients are returned, when True diagnostic
        information from the singular value decomposition is also returned.
    w : array_like, shape (M,), optional
        Weights. If not None, the weight ``w[i]`` applies to the unsquared
        residual ``y[i] - y_hat[i]`` at ``x[i]``. Ideally the weights are
        chosen so that the errors of the products ``w[i]*y[i]`` all have the
        same variance.  When using inverse-variance weighting, use
        ``w[i] = 1/sigma(y[i])``.  The default value is None.
    cov : bool or str, optional
        If given and not `False`, return not just the estimate but also its
        covariance matrix. By default, the covariance are scaled by
        chi2/dof, where dof = M - (deg + 1), i.e., the weights are presumed
        to be unreliable except in a relative sense and everything is scaled
        such that the reduced chi2 is unity. This scaling is omitted if
        ``cov='unscaled'``, as is relevant for the case that the weights are
        w = 1/sigma, with sigma known to be a reliable estimate of the
        uncertainty.

    Returns
    -------
    p : ndarray, shape (deg + 1,) or (deg + 1, K)
        Polynomial coefficients, highest power first.  If `y` was 2-D, the
        coefficients for `k`-th data set are in ``p[:,k]``.

    residuals, rank, singular_values, rcond
        These values are only returned if ``full == True``

        - residuals -- sum of squared residuals of the least squares fit
        - rank -- the effective rank of the scaled Vandermonde
           coefficient matrix
        - singular_values -- singular values of the scaled Vandermonde
           coefficient matrix
        - rcond -- value of `rcond`.

        For more details, see `numpy.linalg.lstsq`.

    V : ndarray, shape (deg + 1, deg + 1) or (deg + 1, deg + 1, K)
        Present only if ``full == False`` and ``cov == True``.  The covariance
        matrix of the polynomial coefficient estimates.  The diagonal of
        this matrix are the variance estimates for each coefficient.  If y
        is a 2-D array, then the covariance matrix for the `k`-th data set
        are in ``V[:,:,k]``


    Warns
    -----
    RankWarning
        The rank of the coefficient matrix in the least-squares fit is
        deficient. The warning is only raised if ``full == False``.

        The warnings can be turned off by

        >>> import warnings
        >>> warnings.simplefilter('ignore', np.exceptions.RankWarning)

    See Also
    --------
    polyval : Compute polynomial values.
    linalg.lstsq : Computes a least-squares fit.
    scipy.interpolate.UnivariateSpline : Computes spline fits.

    Notes
    -----
    The solution minimizes the squared error

    .. math::
        E = \\sum_{j=0}^k |p(x_j) - y_j|^2

    in the equations::

        x[0]**n * p[0] + ... + x[0] * p[n-1] + p[n] = y[0]
        x[1]**n * p[0] + ... + x[1] * p[n-1] + p[n] = y[1]
        ...
        x[k]**n * p[0] + ... + x[k] * p[n-1] + p[n] = y[k]

    The coefficient matrix of the coefficients `p` is a Vandermonde matrix.

    `polyfit` issues a `~exceptions.RankWarning` when the least-squares fit is
    badly conditioned. This implies that the best fit is not well-defined due
    to numerical error. The results may be improved by lowering the polynomial
    degree or by replacing `x` by `x` - `x`.mean(). The `rcond` parameter
    can also be set to a value smaller than its default, but the resulting
    fit may be spurious: including contributions from the small singular
    values can add numerical noise to the result.

    Note that fitting polynomial coefficients is inherently badly conditioned
    when the degree of the polynomial is large or the interval of sample points
    is badly centered. The quality of the fit should always be checked in these
    cases. When polynomial fits are not satisfactory, splines may be a good
    alternative.

    References
    ----------
    .. [1] Wikipedia, "Curve fitting",
           https://en.wikipedia.org/wiki/Curve_fitting
    .. [2] Wikipedia, "Polynomial interpolation",
           https://en.wikipedia.org/wiki/Polynomial_interpolation

    Examples
    --------
    >>> import numpy as np
    >>> import warnings
    >>> x = np.array([0.0, 1.0, 2.0, 3.0,  4.0,  5.0])
    >>> y = np.array([0.0, 0.8, 0.9, 0.1, -0.8, -1.0])
    >>> z = np.polyfit(x, y, 3)
    >>> z
    array([ 0.08703704, -0.81349206,  1.69312169, -0.03968254]) # may vary

    It is convenient to use `poly1d` objects for dealing with polynomials:

    >>> p = np.poly1d(z)
    >>> p(0.5)
    0.6143849206349179 # may vary
    >>> p(3.5)
    -0.34732142857143039 # may vary
    >>> p(10)
    22.579365079365115 # may vary

    High-order polynomials may oscillate wildly:

    >>> with warnings.catch_warnings():
    ...     warnings.simplefilter('ignore', np.exceptions.RankWarning)
    ...     p30 = np.poly1d(np.polyfit(x, y, 30))
    ...
    >>> p30(4)
    -0.80000000000000204 # may vary
    >>> p30(5)
    -0.99999999999999445 # may vary
    >>> p30(4.5)
    -0.10547061179440398 # may vary

    Illustration:

    >>> import matplotlib.pyplot as plt
    >>> xp = np.linspace(-2, 6, 100)
    >>> _ = plt.plot(x, y, '.', xp, p(xp), '-', xp, p30(xp), '--')
    >>> plt.ylim(-2,2)
    (-2, 2)
    >>> plt.show()

    """
    order = int(deg) + 1
    x = NX.asarray(x) + 0.0
    y = NX.asarray(y) + 0.0

    # check arguments.
    if deg < 0:
        raise ValueError("expected deg >= 0")
    if x.ndim != 1:
        raise TypeError("expected 1D vector for x")
    if x.size == 0:
        raise TypeError("expected non-empty vector for x")
    if y.ndim < 1 or y.ndim > 2:
        raise TypeError("expected 1D or 2D array for y")
    if x.shape[0] != y.shape[0]:
        raise TypeError("expected x and y to have same length")

    # set rcond
    if rcond is None:
        rcond = len(x) * finfo(x.dtype).eps

    # set up least squares equation for powers of x
    lhs = vander(x, order)
    rhs = y

    # apply weighting
    if w is not None:
        w = NX.asarray(w) + 0.0
        if w.ndim != 1:
            raise TypeError("expected a 1-d array for weights")
        if w.shape[0] != y.shape[0]:
            raise TypeError("expected w and y to have the same length")
        lhs *= w[:, NX.newaxis]
        if rhs.ndim == 2:
            rhs *= w[:, NX.newaxis]
        else:
            rhs *= w

    # scale lhs to improve condition number and solve
    scale = NX.sqrt((lhs * lhs).sum(axis=0))
    lhs /= scale
    c, resids, rank, s = lstsq(lhs, rhs, rcond)
    c = (c.T / scale).T  # broadcast scale coefficients

    # warn on rank reduction, which indicates an ill conditioned matrix
    if rank != order and not full:
        msg = "Polyfit may be poorly conditioned"
        warnings.warn(msg, RankWarning, stacklevel=2)

    if full:
        return c, resids, rank, s, rcond
    elif cov:
        Vbase = inv(dot(lhs.T, lhs))
        Vbase /= NX.outer(scale, scale)
        if cov == "unscaled":
            fac = 1
        else:
            if len(x) <= order:
                raise ValueError("the number of data points must exceed order "
                                 "to scale the covariance matrix")
            # note, this used to be: fac = resids / (len(x) - order - 2.0)
            # it was decided that the "- 2" (originally justified by "Bayesian
            # uncertainty analysis") is not what the user expects
            # (see gh-11196 and gh-11197)
            fac = resids / (len(x) - order)
        if y.ndim == 1:
            return c, Vbase * fac
        else:
            return c, Vbase[:, :, NX.newaxis] * fac
    else:
        return c


def _polyval_dispatcher(p, x):
    return (p, x)


@array_function_dispatch(_polyval_dispatcher)
def polyval(p, x):
    """
    Evaluate a polynomial at specific values.

    .. note::
       This forms part of the old polynomial API. Since version 1.4, the
       new polynomial API defined in `numpy.polynomial` is preferred.
       A summary of the differences can be found in the
       :doc:`transition guide </reference/routines.polynomials>`.

    If `p` is of length N, this function returns the value::

        p[0]*x**(N-1) + p[1]*x**(N-2) + ... + p[N-2]*x + p[N-1]

    If `x` is a sequence, then ``p(x)`` is returned for each element of ``x``.
    If `x` is another polynomial then the composite polynomial ``p(x(t))``
    is returned.

    Parameters
    ----------
    p : array_like or poly1d object
       1D array of polynomial coefficients (including coefficients equal
       to zero) from highest degree to the constant term, or an
       instance of poly1d.
    x : array_like or poly1d object
       A number, an array of numbers, or an instance of poly1d, at
       which to evaluate `p`.

    Returns
    -------
    values : ndarray or poly1d
       If `x` is a poly1d instance, the result is the composition of the two
       polynomials, i.e., `x` is "substituted" in `p` and the simplified
       result is returned. In addition, the type of `x` - array_like or
       poly1d - governs the type of the output: `x` array_like => `values`
       array_like, `x` a poly1d object => `values` is also.

    See Also
    --------
    poly1d: A polynomial class.

    Notes
    -----
    Horner's scheme [1]_ is used to evaluate the polynomial. Even so,
    for polynomials of high degree the values may be inaccurate due to
    rounding errors. Use carefully.

    If `x` is a subtype of `ndarray` the return value will be of the same type.

    References
    ----------
    .. [1] I. N. Bronshtein, K. A. Semendyayev, and K. A. Hirsch (Eng.
       trans. Ed.), *Handbook of Mathematics*, New York, Van Nostrand
       Reinhold Co., 1985, pg. 720.

    Examples
    --------
    >>> import numpy as np
    >>> np.polyval([3,0,1], 5)  # 3 * 5**2 + 0 * 5**1 + 1
    76
    >>> np.polyval([3,0,1], np.poly1d(5))
    poly1d([76])
    >>> np.polyval(np.poly1d([3,0,1]), 5)
    76
    >>> np.polyval(np.poly1d([3,0,1]), np.poly1d(5))
    poly1d([76])

    """
    p = NX.asarray(p)
    if isinstance(x, poly1d):
        y = 0
    else:
        x = NX.asanyarray(x)
        y = NX.zeros_like(x)
    for pv in p:
        y = y * x + pv
    return y


def _binary_op_dispatcher(a1, a2):
    return (a1, a2)


@array_function_dispatch(_binary_op_dispatcher)
def polyadd(a1, a2):
    """
    Find the sum of two polynomials.

    .. note::
       This forms part of the old polynomial API. Since version 1.4, the
       new polynomial API defined in `numpy.polynomial` is preferred.
       A summary of the differences can be found in the
       :doc:`transition guide </reference/routines.polynomials>`.

    Returns the polynomial resulting from the sum of two input polynomials.
    Each input must be either a poly1d object or a 1D sequence of polynomial
    coefficients, from highest to lowest degree.

    Parameters
    ----------
    a1, a2 : array_like or poly1d object
        Input polynomials.

    Returns
    -------
    out : ndarray or poly1d object
        The sum of the inputs. If either input is a poly1d object, then the
        output is also a poly1d object. Otherwise, it is a 1D array of
        polynomial coefficients from highest to lowest degree.

    See Also
    --------
    poly1d : A one-dimensional polynomial class.
    poly, polyadd, polyder, polydiv, polyfit, polyint, polysub, polyval

    Examples
    --------
    >>> import numpy as np
    >>> np.polyadd([1, 2], [9, 5, 4])
    array([9, 6, 6])

    Using poly1d objects:

    >>> p1 = np.poly1d([1, 2])
    >>> p2 = np.poly1d([9, 5, 4])
    >>> print(p1)
    1 x + 2
    >>> print(p2)
       2
    9 x + 5 x + 4
    >>> print(np.polyadd(p1, p2))
       2
    9 x + 6 x + 6

    """
    truepoly = (isinstance(a1, poly1d) or isinstance(a2, poly1d))
    a1 = atleast_1d(a1)
    a2 = atleast_1d(a2)
    diff = len(a2) - len(a1)
    if diff == 0:
        val = a1 + a2
    elif diff > 0:
        zr = NX.zeros(diff, a1.dtype)
        val = NX.concatenate((zr, a1)) + a2
    else:
        zr = NX.zeros(abs(diff), a2.dtype)
        val = a1 + NX.concatenate((zr, a2))
    if truepoly:
        val = poly1d(val)
    return val


@array_function_dispatch(_binary_op_dispatcher)
def polysub(a1, a2):
    """
    Difference (subtraction) of two polynomials.

    .. note::
       This forms part of the old polynomial API. Since version 1.4, the
       new polynomial API defined in `numpy.polynomial` is preferred.
       A summary of the differences can be found in the
       :doc:`transition guide </reference/routines.polynomials>`.

    Given two polynomials `a1` and `a2`, returns ``a1 - a2``.
    `a1` and `a2` can be either array_like sequences of the polynomials'
    coefficients (including coefficients equal to zero), or `poly1d` objects.

    Parameters
    ----------
    a1, a2 : array_like or poly1d
        Minuend and subtrahend polynomials, respectively.

    Returns
    -------
    out : ndarray or poly1d
        Array or `poly1d` object of the difference polynomial's coefficients.

    See Also
    --------
    polyval, polydiv, polymul, polyadd

    Examples
    --------

    .. math:: (2 x^2 + 10 x - 2) - (3 x^2 + 10 x -4) = (-x^2 + 2)

    >>> import numpy as np

    >>> np.polysub([2, 10, -2], [3, 10, -4])
    array([-1,  0,  2])

    """
    truepoly = (isinstance(a1, poly1d) or isinstance(a2, poly1d))
    a1 = atleast_1d(a1)
    a2 = atleast_1d(a2)
    diff = len(a2) - len(a1)
    if diff == 0:
        val = a1 - a2
    elif diff > 0:
        zr = NX.zeros(diff, a1.dtype)
        val = NX.concatenate((zr, a1)) - a2
    else:
        zr = NX.zeros(abs(diff), a2.dtype)
        val = a1 - NX.concatenate((zr, a2))
    if truepoly:
        val = poly1d(val)
    return val


@array_function_dispatch(_binary_op_dispatcher)
def polymul(a1, a2):
    """
    Find the product of two polynomials.

    .. note::
       This forms part of the old polynomial API. Since version 1.4, the
       new polynomial API defined in `numpy.polynomial` is preferred.
       A summary of the differences can be found in the
       :doc:`transition guide </reference/routines.polynomials>`.

    Finds the polynomial resulting from the multiplication of the two input
    polynomials. Each input must be either a poly1d object or a 1D sequence
    of polynomial coefficients, from highest to lowest degree.

    Parameters
    ----------
    a1, a2 : array_like or poly1d object
        Input polynomials.

    Returns
    -------
    out : ndarray or poly1d object
        The polynomial resulting from the multiplication of the inputs. If
        either inputs is a poly1d object, then the output is also a poly1d
        object. Otherwise, it is a 1D array of polynomial coefficients from
        highest to lowest degree.

    See Also
    --------
    poly1d : A one-dimensional polynomial class.
    poly, polyadd, polyder, polydiv, polyfit, polyint, polysub, polyval
    convolve : Array convolution. Same output as polymul, but has parameter
               for overlap mode.

    Examples
    --------
    >>> import numpy as np
    >>> np.polymul([1, 2, 3], [9, 5, 1])
    array([ 9, 23, 38, 17,  3])

    Using poly1d objects:

    >>> p1 = np.poly1d([1, 2, 3])
    >>> p2 = np.poly1d([9, 5, 1])
    >>> print(p1)
       2
    1 x + 2 x + 3
    >>> print(p2)
       2
    9 x + 5 x + 1
    >>> print(np.polymul(p1, p2))
       4      3      2
    9 x + 23 x + 38 x + 17 x + 3

    """
    truepoly = (isinstance(a1, poly1d) or isinstance(a2, poly1d))
    a1, a2 = poly1d(a1), poly1d(a2)
    val = NX.convolve(a1, a2)
    if truepoly:
        val = poly1d(val)
    return val


def _polydiv_dispatcher(u, v):
    return (u, v)


@array_function_dispatch(_polydiv_dispatcher)
def polydiv(u, v):
    """
    Returns the quotient and remainder of polynomial division.

    .. note::
       This forms part of the old polynomial API. Since version 1.4, the
       new polynomial API defined in `numpy.polynomial` is preferred.
       A summary of the differences can be found in the
       :doc:`transition guide </reference/routines.polynomials>`.

    The input arrays are the coefficients (including any coefficients
    equal to zero) of the "numerator" (dividend) and "denominator"
    (divisor) polynomials, respectively.

    Parameters
    ----------
    u : array_like or poly1d
        Dividend polynomial's coefficients.

    v : array_like or poly1d
        Divisor polynomial's coefficients.

    Returns
    -------
    q : ndarray
        Coefficients, including those equal to zero, of the quotient.
    r : ndarray
        Coefficients, including those equal to zero, of the remainder.

    See Also
    --------
    poly, polyadd, polyder, polydiv, polyfit, polyint, polymul, polysub
    polyval

    Notes
    -----
    Both `u` and `v` must be 0-d or 1-d (ndim = 0 or 1), but `u.ndim` need
    not equal `v.ndim`. In other words, all four possible combinations -
    ``u.ndim = v.ndim = 0``, ``u.ndim = v.ndim = 1``,
    ``u.ndim = 1, v.ndim = 0``, and ``u.ndim = 0, v.ndim = 1`` - work.

    Examples
    --------

    .. math:: \\frac{3x^2 + 5x + 2}{2x + 1} = 1.5x + 1.75, remainder 0.25

    >>> import numpy as np

    >>> x = np.array([3.0, 5.0, 2.0])
    >>> y = np.array([2.0, 1.0])
    >>> np.polydiv(x, y)
    (array([1.5 , 1.75]), array([0.25]))

    """
    truepoly = (isinstance(u, poly1d) or isinstance(v, poly1d))
    u = atleast_1d(u) + 0.0
    v = atleast_1d(v) + 0.0
    # w has the common type
    w = u[0] + v[0]
    m = len(u) - 1
    n = len(v) - 1
    scale = 1. / v[0]
    q = NX.zeros((max(m - n + 1, 1),), w.dtype)
    r = u.astype(w.dtype)
    for k in range(m - n + 1):
        d = scale * r[k]
        q[k] = d
        r[k:k + n + 1] -= d * v
    while NX.allclose(r[0], 0, rtol=1e-14) and (r.shape[-1] > 1):
        r = r[1:]
    if truepoly:
        return poly1d(q), poly1d(r)
    return q, r


_poly_mat = re.compile(r"\*\*([0-9]*)")
def _raise_power(astr, wrap=70):
    n = 0
    line1 = ''
    line2 = ''
    output = ' '
    while True:
        mat = _poly_mat.search(astr, n)
        if mat is None:
            break
        span = mat.span()
        power = mat.groups()[0]
        partstr = astr[n:span[0]]
        n = span[1]
        toadd2 = partstr + ' ' * (len(power) - 1)
        toadd1 = ' ' * (len(partstr) - 1) + power
        if ((len(line2) + len(toadd2) > wrap) or
                (len(line1) + len(toadd1) > wrap)):
            output += line1 + "\n" + line2 + "\n "
            line1 = toadd1
            line2 = toadd2
        else:
            line2 += partstr + ' ' * (len(power) - 1)
            line1 += ' ' * (len(partstr) - 1) + power
    output += line1 + "\n" + line2
    return output + astr[n:]


@set_module('numpy')
class poly1d:
    """
    A one-dimensional polynomial class.

    .. note::
       This forms part of the old polynomial API. Since version 1.4, the
       new polynomial API defined in `numpy.polynomial` is preferred.
       A summary of the differences can be found in the
       :doc:`transition guide </reference/routines.polynomials>`.

    A convenience class, used to encapsulate "natural" operations on
    polynomials so that said operations may take on their customary
    form in code (see Examples).

    Parameters
    ----------
    c_or_r : array_like
        The polynomial's coefficients, in decreasing powers, or if
        the value of the second parameter is True, the polynomial's
        roots (values where the polynomial evaluates to 0).  For example,
        ``poly1d([1, 2, 3])`` returns an object that represents
        :math:`x^2 + 2x + 3`, whereas ``poly1d([1, 2, 3], True)`` returns
        one that represents :math:`(x-1)(x-2)(x-3) = x^3 - 6x^2 + 11x -6`.
    r : bool, optional
        If True, `c_or_r` specifies the polynomial's roots; the default
        is False.
    variable : str, optional
        Changes the variable used when printing `p` from `x` to `variable`
        (see Examples).

    Examples
    --------
    >>> import numpy as np

    Construct the polynomial :math:`x^2 + 2x + 3`:

    >>> import numpy as np

    >>> p = np.poly1d([1, 2, 3])
    >>> print(np.poly1d(p))
       2
    1 x + 2 x + 3

    Evaluate the polynomial at :math:`x = 0.5`:

    >>> p(0.5)
    4.25

    Find the roots:

    >>> p.r
    array([-1.+1.41421356j, -1.-1.41421356j])
    >>> p(p.r)
    array([ -4.44089210e-16+0.j,  -4.44089210e-16+0.j]) # may vary

    These numbers in the previous line represent (0, 0) to machine precision

    Show the coefficients:

    >>> p.c
    array([1, 2, 3])

    Display the order (the leading zero-coefficients are removed):

    >>> p.order
    2

    Show the coefficient of the k-th power in the polynomial
    (which is equivalent to ``p.c[-(i+1)]``):

    >>> p[1]
    2

    Polynomials can be added, subtracted, multiplied, and divided
    (returns quotient and remainder):

    >>> p * p
    poly1d([ 1,  4, 10, 12,  9])

    >>> (p**3 + 4) / p
    (poly1d([ 1.,  4., 10., 12.,  9.]), poly1d([4.]))

    ``asarray(p)`` gives the coefficient array, so polynomials can be
    used in all functions that accept arrays:

    >>> p**2 # square of polynomial
    poly1d([ 1,  4, 10, 12,  9])

    >>> np.square(p) # square of individual coefficients
    array([1, 4, 9])

    The variable used in the string representation of `p` can be modified,
    using the `variable` parameter:

    >>> p = np.poly1d([1,2,3], variable='z')
    >>> print(p)
       2
    1 z + 2 z + 3

    Construct a polynomial from its roots:

    >>> np.poly1d([1, 2], True)
    poly1d([ 1., -3.,  2.])

    This is the same polynomial as obtained by:

    >>> np.poly1d([1, -1]) * np.poly1d([1, -2])
    poly1d([ 1, -3,  2])

    """
    __hash__ = None

    @property
    def coeffs(self):
        """ The polynomial coefficients """
        return self._coeffs

    @coeffs.setter
    def coeffs(self, value):
        # allowing this makes p.coeffs *= 2 legal
        if value is not self._coeffs:
            raise AttributeError("Cannot set attribute")

    @property
    def variable(self):
        """ The name of the polynomial variable """
        return self._variable

    # calculated attributes
    @property
    def order(self):
        """ The order or degree of the polynomial """
        return len(self._coeffs) - 1

    @property
    def roots(self):
        """ The roots of the polynomial, where self(x) == 0 """
        return roots(self._coeffs)

    # our internal _coeffs property need to be backed by __dict__['coeffs'] for
    # scipy to work correctly.
    @property
    def _coeffs(self):
        return self.__dict__['coeffs']

    @_coeffs.setter
    def _coeffs(self, coeffs):
        self.__dict__['coeffs'] = coeffs

    # alias attributes
    r = roots
    c = coef = coefficients = coeffs
    o = order

    def __init__(self, c_or_r, r=False, variable=None):
        if isinstance(c_or_r, poly1d):
            self._variable = c_or_r._variable
            self._coeffs = c_or_r._coeffs

            if set(c_or_r.__dict__) - set(self.__dict__):
                msg = ("In the future extra properties will not be copied "
                       "across when constructing one poly1d from another")
                warnings.warn(msg, FutureWarning, stacklevel=2)
                self.__dict__.update(c_or_r.__dict__)

            if variable is not None:
                self._variable = variable
            return
        if r:
            c_or_r = poly(c_or_r)
        c_or_r = atleast_1d(c_or_r)
        if c_or_r.ndim > 1:
            raise ValueError("Polynomial must be 1d only.")
        c_or_r = trim_zeros(c_or_r, trim='f')
        if len(c_or_r) == 0:
            c_or_r = NX.array([0], dtype=c_or_r.dtype)
        self._coeffs = c_or_r
        if variable is None:
            variable = 'x'
        self._variable = variable

    def __array__(self, t=None, copy=None):
        if t:
            return NX.asarray(self.coeffs, t, copy=copy)
        else:
            return NX.asarray(self.coeffs, copy=copy)

    def __repr__(self):
        vals = repr(self.coeffs)
        vals = vals[6:-1]
        return f"poly1d({vals})"

    def __len__(self):
        return self.order

    def __str__(self):
        thestr = "0"
        var = self.variable

        # Remove leading zeros
        coeffs = self.coeffs[NX.logical_or.accumulate(self.coeffs != 0)]
        N = len(coeffs) - 1

        def fmt_float(q):
            s = f'{q:.4g}'
            s = s.removesuffix('.0000')
            return s

        for k, coeff in enumerate(coeffs):
            if not iscomplex(coeff):
                coefstr = fmt_float(real(coeff))
            elif real(coeff) == 0:
                coefstr = f'{fmt_float(imag(coeff))}j'
            else:
                coefstr = f'({fmt_float(real(coeff))} + {fmt_float(imag(coeff))}j)'

            power = (N - k)
            if power == 0:
                if coefstr != '0':
                    newstr = f'{coefstr}'
                elif k == 0:
                    newstr = '0'
                else:
                    newstr = ''
            elif power == 1:
                if coefstr == '0':
                    newstr = ''
                elif coefstr == 'b':
                    newstr = var
                else:
                    newstr = f'{coefstr} {var}'
            elif coefstr == '0':
                newstr = ''
            elif coefstr == 'b':
                newstr = '%s**%d' % (var, power,)
            else:
                newstr = '%s %s**%d' % (coefstr, var, power)

            if k > 0:
                if newstr != '':
                    if newstr.startswith('-'):
                        thestr = f"{thestr} - {newstr[1:]}"
                    else:
                        thestr = f"{thestr} + {newstr}"
            else:
                thestr = newstr
        return _raise_power(thestr)

    def __call__(self, val):
        return polyval(self.coeffs, val)

    def __neg__(self):
        return poly1d(-self.coeffs)

    def __pos__(self):
        return self

    def __mul__(self, other):
        if isscalar(other):
            return poly1d(self.coeffs * other)
        else:
            other = poly1d(other)
            return poly1d(polymul(self.coeffs, other.coeffs))

    def __rmul__(self, other):
        if isscalar(other):
            return poly1d(other * self.coeffs)
        else:
            other = poly1d(other)
            return poly1d(polymul(self.coeffs, other.coeffs))

    def __add__(self, other):
        other = poly1d(other)
        return poly1d(polyadd(self.coeffs, other.coeffs))

    def __radd__(self, other):
        other = poly1d(other)
        return poly1d(polyadd(self.coeffs, other.coeffs))

    def __pow__(self, val):
        if not isscalar(val) or int(val) != val or val < 0:
            raise ValueError("Power to non-negative integers only.")
        res = [1]
        for _ in range(val):
            res = polymul(self.coeffs, res)
        return poly1d(res)

    def __sub__(self, other):
        other = poly1d(other)
        return poly1d(polysub(self.coeffs, other.coeffs))

    def __rsub__(self, other):
        other = poly1d(other)
        return poly1d(polysub(other.coeffs, self.coeffs))

    def __truediv__(self, other):
        if isscalar(other):
            return poly1d(self.coeffs / other)
        else:
            other = poly1d(other)
            return polydiv(self, other)

    def __rtruediv__(self, other):
        if isscalar(other):
            return poly1d(other / self.coeffs)
        else:
            other = poly1d(other)
            return polydiv(other, self)

    def __eq__(self, other):
        if not isinstance(other, poly1d):
            return NotImplemented
        if self.coeffs.shape != other.coeffs.shape:
            return False
        return (self.coeffs == other.coeffs).all()

    def __ne__(self, other):
        if not isinstance(other, poly1d):
            return NotImplemented
        return not self.__eq__(other)

    def __getitem__(self, val):
        ind = self.order - val
        if val > self.order:
            return self.coeffs.dtype.type(0)
        if val < 0:
            return self.coeffs.dtype.type(0)
        return self.coeffs[ind]

    def __setitem__(self, key, val):
        ind = self.order - key
        if key < 0:
            raise ValueError("Does not support negative powers.")
        if key > self.order:
            zr = NX.zeros(key - self.order, self.coeffs.dtype)
            self._coeffs = NX.concatenate((zr, self.coeffs))
            ind = 0
        self._coeffs[ind] = val

    def __iter__(self):
        return iter(self.coeffs)

    def integ(self, m=1, k=0):
        """
        Return an antiderivative (indefinite integral) of this polynomial.

        Refer to `polyint` for full documentation.

        See Also
        --------
        polyint : equivalent function

        """
        return poly1d(polyint(self.coeffs, m=m, k=k))

    def deriv(self, m=1):
        """
        Return a derivative of this polynomial.

        Refer to `polyder` for full documentation.

        See Also
        --------
        polyder : equivalent function

        """
        return poly1d(polyder(self.coeffs, m=m))

# Stuff to do on module import


warnings.simplefilter('always', RankWarning)

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\workspace\crm_project\app\main.py ===
def create_customer(name: str, email: str, phone: str, address: str) -> int:
    """顧客を作成する。

    Args:
        name (str): 顧客名
        email (str): 顧客のメールアドレス
        phone (str): 顧客の電話番号
        address (str): 顧客の住所

    Returns:
        int: 作成された顧客のID
    """

    # 顧客情報を辞書に格納
    customer_data = {
        "name": name,
        "email": email,
        "phone": phone,
        "address": address,
    }

    # ここでは、データベースやその他の永続化メカニズムに顧客情報を保存する処理を想定しています。
    # この例では、簡略化のため、ダミーの顧客IDを返しています。
    # 実際のアプリケーションでは、データベース操作を行い、生成されたIDを返す必要があります。

    # ダミーの顧客IDを生成 (実際のアプリケーションでは、データベースから取得)
    customer_id = len(customer_data)  # これは例です。実際のID生成ロジックに置き換えてください。

    # 将来的には、データベースへの保存処理などをここに実装

    return customer_id


create_customer_function_info = {
    "name": "create_customer",
    "description": "顧客を作成する。",
    "args": [
        {"name": "name", "type": "str", "description": "顧客名"},
        {"name": "email", "type": "str", "description": "顧客のメールアドレス"},
        {"name": "phone", "type": "str", "description": "顧客の電話番号"},
        {"name": "address", "type": "str", "description": "顧客の住所"},
    ],
    "returns": {"type": "int", "description": "作成された顧客のID"},
}

# === NexusCore/workspace\crm_project\app\main.py ===
def create_customer(name: str, email: str, phone: str, address: str) -> int:
    """顧客を作成する。

    Args:
        name (str): 顧客名
        email (str): 顧客のメールアドレス
        phone (str): 顧客の電話番号
        address (str): 顧客の住所

    Returns:
        int: 作成された顧客のID
    """

    # 顧客情報を辞書に格納
    customer_data = {
        "name": name,
        "email": email,
        "phone": phone,
        "address": address,
    }

    # ここでは、データベースやその他の永続化メカニズムに顧客情報を保存する処理を想定しています。
    # この例では、簡略化のため、ダミーの顧客IDを返しています。
    # 実際のアプリケーションでは、データベース操作を行い、生成されたIDを返す必要があります。

    # ダミーの顧客IDを生成 (実際のアプリケーションでは、データベースから取得)
    customer_id = len(customer_data)  # これは例です。実際のID生成ロジックに置き換えてください。

    # 将来的には、データベースへの保存処理などをここに実装

    return customer_id


create_customer_function_info = {
    "name": "create_customer",
    "description": "顧客を作成する。",
    "args": [
        {"name": "name", "type": "str", "description": "顧客名"},
        {"name": "email", "type": "str", "description": "顧客のメールアドレス"},
        {"name": "phone", "type": "str", "description": "顧客の電話番号"},
        {"name": "address", "type": "str", "description": "顧客の住所"},
    ],
    "returns": {"type": "int", "description": "作成された顧客のID"},
}

# === NexusCore/openenv\Lib\site-packages\numpy\lib\tests\test_nanfunctions.py ===
import inspect
import warnings
from functools import partial

import pytest

import numpy as np
from numpy._core.numeric import normalize_axis_tuple
from numpy.exceptions import AxisError, ComplexWarning
from numpy.lib._nanfunctions_impl import _nan_mask, _replace_nan
from numpy.testing import (
    assert_,
    assert_almost_equal,
    assert_array_equal,
    assert_equal,
    assert_raises,
    assert_raises_regex,
    suppress_warnings,
)

# Test data
_ndat = np.array([[0.6244, np.nan, 0.2692, 0.0116, np.nan, 0.1170],
                  [0.5351, -0.9403, np.nan, 0.2100, 0.4759, 0.2833],
                  [np.nan, np.nan, np.nan, 0.1042, np.nan, -0.5954],
                  [0.1610, np.nan, np.nan, 0.1859, 0.3146, np.nan]])


# Rows of _ndat with nans removed
_rdat = [np.array([0.6244, 0.2692, 0.0116, 0.1170]),
         np.array([0.5351, -0.9403, 0.2100, 0.4759, 0.2833]),
         np.array([0.1042, -0.5954]),
         np.array([0.1610, 0.1859, 0.3146])]

# Rows of _ndat with nans converted to ones
_ndat_ones = np.array([[0.6244, 1.0, 0.2692, 0.0116, 1.0, 0.1170],
                       [0.5351, -0.9403, 1.0, 0.2100, 0.4759, 0.2833],
                       [1.0, 1.0, 1.0, 0.1042, 1.0, -0.5954],
                       [0.1610, 1.0, 1.0, 0.1859, 0.3146, 1.0]])

# Rows of _ndat with nans converted to zeros
_ndat_zeros = np.array([[0.6244, 0.0, 0.2692, 0.0116, 0.0, 0.1170],
                        [0.5351, -0.9403, 0.0, 0.2100, 0.4759, 0.2833],
                        [0.0, 0.0, 0.0, 0.1042, 0.0, -0.5954],
                        [0.1610, 0.0, 0.0, 0.1859, 0.3146, 0.0]])


class TestSignatureMatch:
    NANFUNCS = {
        np.nanmin: np.amin,
        np.nanmax: np.amax,
        np.nanargmin: np.argmin,
        np.nanargmax: np.argmax,
        np.nansum: np.sum,
        np.nanprod: np.prod,
        np.nancumsum: np.cumsum,
        np.nancumprod: np.cumprod,
        np.nanmean: np.mean,
        np.nanmedian: np.median,
        np.nanpercentile: np.percentile,
        np.nanquantile: np.quantile,
        np.nanvar: np.var,
        np.nanstd: np.std,
    }
    IDS = [k.__name__ for k in NANFUNCS]

    @staticmethod
    def get_signature(func, default="..."):
        """Construct a signature and replace all default parameter-values."""
        prm_list = []
        signature = inspect.signature(func)
        for prm in signature.parameters.values():
            if prm.default is inspect.Parameter.empty:
                prm_list.append(prm)
            else:
                prm_list.append(prm.replace(default=default))
        return inspect.Signature(prm_list)

    @pytest.mark.parametrize("nan_func,func", NANFUNCS.items(), ids=IDS)
    def test_signature_match(self, nan_func, func):
        # Ignore the default parameter-values as they can sometimes differ
        # between the two functions (*e.g.* one has `False` while the other
        # has `np._NoValue`)
        signature = self.get_signature(func)
        nan_signature = self.get_signature(nan_func)
        np.testing.assert_equal(signature, nan_signature)

    def test_exhaustiveness(self):
        """Validate that all nan functions are actually tested."""
        np.testing.assert_equal(
            set(self.IDS), set(np.lib._nanfunctions_impl.__all__)
        )


class TestNanFunctions_MinMax:

    nanfuncs = [np.nanmin, np.nanmax]
    stdfuncs = [np.min, np.max]

    def test_mutation(self):
        # Check that passed array is not modified.
        ndat = _ndat.copy()
        for f in self.nanfuncs:
            f(ndat)
            assert_equal(ndat, _ndat)

    def test_keepdims(self):
        mat = np.eye(3)
        for nf, rf in zip(self.nanfuncs, self.stdfuncs):
            for axis in [None, 0, 1]:
                tgt = rf(mat, axis=axis, keepdims=True)
                res = nf(mat, axis=axis, keepdims=True)
                assert_(res.ndim == tgt.ndim)

    def test_out(self):
        mat = np.eye(3)
        for nf, rf in zip(self.nanfuncs, self.stdfuncs):
            resout = np.zeros(3)
            tgt = rf(mat, axis=1)
            res = nf(mat, axis=1, out=resout)
            assert_almost_equal(res, resout)
            assert_almost_equal(res, tgt)

    def test_dtype_from_input(self):
        codes = 'efdgFDG'
        for nf, rf in zip(self.nanfuncs, self.stdfuncs):
            for c in codes:
                mat = np.eye(3, dtype=c)
                tgt = rf(mat, axis=1).dtype.type
                res = nf(mat, axis=1).dtype.type
                assert_(res is tgt)
                # scalar case
                tgt = rf(mat, axis=None).dtype.type
                res = nf(mat, axis=None).dtype.type
                assert_(res is tgt)

    def test_result_values(self):
        for nf, rf in zip(self.nanfuncs, self.stdfuncs):
            tgt = [rf(d) for d in _rdat]
            res = nf(_ndat, axis=1)
            assert_almost_equal(res, tgt)

    @pytest.mark.parametrize("axis", [None, 0, 1])
    @pytest.mark.parametrize("dtype", np.typecodes["AllFloat"])
    @pytest.mark.parametrize("array", [
        np.array(np.nan),
        np.full((3, 3), np.nan),
    ], ids=["0d", "2d"])
    def test_allnans(self, axis, dtype, array):
        if axis is not None and array.ndim == 0:
            pytest.skip("`axis != None` not supported for 0d arrays")

        array = array.astype(dtype)
        match = "All-NaN slice encountered"
        for func in self.nanfuncs:
            with pytest.warns(RuntimeWarning, match=match):
                out = func(array, axis=axis)
            assert np.isnan(out).all()
            assert out.dtype == array.dtype

    def test_masked(self):
        mat = np.ma.fix_invalid(_ndat)
        msk = mat._mask.copy()
        for f in [np.nanmin]:
            res = f(mat, axis=1)
            tgt = f(_ndat, axis=1)
            assert_equal(res, tgt)
            assert_equal(mat._mask, msk)
            assert_(not np.isinf(mat).any())

    def test_scalar(self):
        for f in self.nanfuncs:
            assert_(f(0.) == 0.)

    def test_subclass(self):
        class MyNDArray(np.ndarray):
            pass

        # Check that it works and that type and
        # shape are preserved
        mine = np.eye(3).view(MyNDArray)
        for f in self.nanfuncs:
            res = f(mine, axis=0)
            assert_(isinstance(res, MyNDArray))
            assert_(res.shape == (3,))
            res = f(mine, axis=1)
            assert_(isinstance(res, MyNDArray))
            assert_(res.shape == (3,))
            res = f(mine)
            assert_(res.shape == ())

        # check that rows of nan are dealt with for subclasses (#4628)
        mine[1] = np.nan
        for f in self.nanfuncs:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always')
                res = f(mine, axis=0)
                assert_(isinstance(res, MyNDArray))
                assert_(not np.any(np.isnan(res)))
                assert_(len(w) == 0)

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always')
                res = f(mine, axis=1)
                assert_(isinstance(res, MyNDArray))
                assert_(np.isnan(res[1]) and not np.isnan(res[0])
                        and not np.isnan(res[2]))
                assert_(len(w) == 1, 'no warning raised')
                assert_(issubclass(w[0].category, RuntimeWarning))

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always')
                res = f(mine)
                assert_(res.shape == ())
                assert_(res != np.nan)
                assert_(len(w) == 0)

    def test_object_array(self):
        arr = np.array([[1.0, 2.0], [np.nan, 4.0], [np.nan, np.nan]], dtype=object)
        assert_equal(np.nanmin(arr), 1.0)
        assert_equal(np.nanmin(arr, axis=0), [1.0, 2.0])

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            # assert_equal does not work on object arrays of nan
            assert_equal(list(np.nanmin(arr, axis=1)), [1.0, 4.0, np.nan])
            assert_(len(w) == 1, 'no warning raised')
            assert_(issubclass(w[0].category, RuntimeWarning))

    @pytest.mark.parametrize("dtype", np.typecodes["AllFloat"])
    def test_initial(self, dtype):
        class MyNDArray(np.ndarray):
            pass

        ar = np.arange(9).astype(dtype)
        ar[:5] = np.nan

        for f in self.nanfuncs:
            initial = 100 if f is np.nanmax else 0

            ret1 = f(ar, initial=initial)
            assert ret1.dtype == dtype
            assert ret1 == initial

            ret2 = f(ar.view(MyNDArray), initial=initial)
            assert ret2.dtype == dtype
            assert ret2 == initial

    @pytest.mark.parametrize("dtype", np.typecodes["AllFloat"])
    def test_where(self, dtype):
        class MyNDArray(np.ndarray):
            pass

        ar = np.arange(9).reshape(3, 3).astype(dtype)
        ar[0, :] = np.nan
        where = np.ones_like(ar, dtype=np.bool)
        where[:, 0] = False

        for f in self.nanfuncs:
            reference = 4 if f is np.nanmin else 8

            ret1 = f(ar, where=where, initial=5)
            assert ret1.dtype == dtype
            assert ret1 == reference

            ret2 = f(ar.view(MyNDArray), where=where, initial=5)
            assert ret2.dtype == dtype
            assert ret2 == reference


class TestNanFunctions_ArgminArgmax:

    nanfuncs = [np.nanargmin, np.nanargmax]

    def test_mutation(self):
        # Check that passed array is not modified.
        ndat = _ndat.copy()
        for f in self.nanfuncs:
            f(ndat)
            assert_equal(ndat, _ndat)

    def test_result_values(self):
        for f, fcmp in zip(self.nanfuncs, [np.greater, np.less]):
            for row in _ndat:
                with suppress_warnings() as sup:
                    sup.filter(RuntimeWarning, "invalid value encountered in")
                    ind = f(row)
                    val = row[ind]
                    # comparing with NaN is tricky as the result
                    # is always false except for NaN != NaN
                    assert_(not np.isnan(val))
                    assert_(not fcmp(val, row).any())
                    assert_(not np.equal(val, row[:ind]).any())

    @pytest.mark.parametrize("axis", [None, 0, 1])
    @pytest.mark.parametrize("dtype", np.typecodes["AllFloat"])
    @pytest.mark.parametrize("array", [
        np.array(np.nan),
        np.full((3, 3), np.nan),
    ], ids=["0d", "2d"])
    def test_allnans(self, axis, dtype, array):
        if axis is not None and array.ndim == 0:
            pytest.skip("`axis != None` not supported for 0d arrays")

        array = array.astype(dtype)
        for func in self.nanfuncs:
            with pytest.raises(ValueError, match="All-NaN slice encountered"):
                func(array, axis=axis)

    def test_empty(self):
        mat = np.zeros((0, 3))
        for f in self.nanfuncs:
            for axis in [0, None]:
                assert_raises_regex(
                        ValueError,
                        "attempt to get argm.. of an empty sequence",
                        f, mat, axis=axis)
            for axis in [1]:
                res = f(mat, axis=axis)
                assert_equal(res, np.zeros(0))

    def test_scalar(self):
        for f in self.nanfuncs:
            assert_(f(0.) == 0.)

    def test_subclass(self):
        class MyNDArray(np.ndarray):
            pass

        # Check that it works and that type and
        # shape are preserved
        mine = np.eye(3).view(MyNDArray)
        for f in self.nanfuncs:
            res = f(mine, axis=0)
            assert_(isinstance(res, MyNDArray))
            assert_(res.shape == (3,))
            res = f(mine, axis=1)
            assert_(isinstance(res, MyNDArray))
            assert_(res.shape == (3,))
            res = f(mine)
            assert_(res.shape == ())

    @pytest.mark.parametrize("dtype", np.typecodes["AllFloat"])
    def test_keepdims(self, dtype):
        ar = np.arange(9).astype(dtype)
        ar[:5] = np.nan

        for f in self.nanfuncs:
            reference = 5 if f is np.nanargmin else 8
            ret = f(ar, keepdims=True)
            assert ret.ndim == ar.ndim
            assert ret == reference

    @pytest.mark.parametrize("dtype", np.typecodes["AllFloat"])
    def test_out(self, dtype):
        ar = np.arange(9).astype(dtype)
        ar[:5] = np.nan

        for f in self.nanfuncs:
            out = np.zeros((), dtype=np.intp)
            reference = 5 if f is np.nanargmin else 8
            ret = f(ar, out=out)
            assert ret is out
            assert ret == reference


_TEST_ARRAYS = {
    "0d": np.array(5),
    "1d": np.array([127, 39, 93, 87, 46])
}
for _v in _TEST_ARRAYS.values():
    _v.setflags(write=False)


@pytest.mark.parametrize(
    "dtype",
    np.typecodes["AllInteger"] + np.typecodes["AllFloat"] + "O",
)
@pytest.mark.parametrize("mat", _TEST_ARRAYS.values(), ids=_TEST_ARRAYS.keys())
class TestNanFunctions_NumberTypes:
    nanfuncs = {
        np.nanmin: np.min,
        np.nanmax: np.max,
        np.nanargmin: np.argmin,
        np.nanargmax: np.argmax,
        np.nansum: np.sum,
        np.nanprod: np.prod,
        np.nancumsum: np.cumsum,
        np.nancumprod: np.cumprod,
        np.nanmean: np.mean,
        np.nanmedian: np.median,
        np.nanvar: np.var,
        np.nanstd: np.std,
    }
    nanfunc_ids = [i.__name__ for i in nanfuncs]

    @pytest.mark.parametrize("nanfunc,func", nanfuncs.items(), ids=nanfunc_ids)
    @np.errstate(over="ignore")
    def test_nanfunc(self, mat, dtype, nanfunc, func):
        mat = mat.astype(dtype)
        tgt = func(mat)
        out = nanfunc(mat)

        assert_almost_equal(out, tgt)
        if dtype == "O":
            assert type(out) is type(tgt)
        else:
            assert out.dtype == tgt.dtype

    @pytest.mark.parametrize(
        "nanfunc,func",
        [(np.nanquantile, np.quantile), (np.nanpercentile, np.percentile)],
        ids=["nanquantile", "nanpercentile"],
    )
    def test_nanfunc_q(self, mat, dtype, nanfunc, func):
        mat = mat.astype(dtype)
        if mat.dtype.kind == "c":
            assert_raises(TypeError, func, mat, q=1)
            assert_raises(TypeError, nanfunc, mat, q=1)

        else:
            tgt = func(mat, q=1)
            out = nanfunc(mat, q=1)

            assert_almost_equal(out, tgt)

            if dtype == "O":
                assert type(out) is type(tgt)
            else:
                assert out.dtype == tgt.dtype

    @pytest.mark.parametrize(
        "nanfunc,func",
        [(np.nanvar, np.var), (np.nanstd, np.std)],
        ids=["nanvar", "nanstd"],
    )
    def test_nanfunc_ddof(self, mat, dtype, nanfunc, func):
        mat = mat.astype(dtype)
        tgt = func(mat, ddof=0.5)
        out = nanfunc(mat, ddof=0.5)

        assert_almost_equal(out, tgt)
        if dtype == "O":
            assert type(out) is type(tgt)
        else:
            assert out.dtype == tgt.dtype

    @pytest.mark.parametrize(
        "nanfunc", [np.nanvar, np.nanstd]
    )
    def test_nanfunc_correction(self, mat, dtype, nanfunc):
        mat = mat.astype(dtype)
        assert_almost_equal(
            nanfunc(mat, correction=0.5), nanfunc(mat, ddof=0.5)
        )

        err_msg = "ddof and correction can't be provided simultaneously."
        with assert_raises_regex(ValueError, err_msg):
            nanfunc(mat, ddof=0.5, correction=0.5)

        with assert_raises_regex(ValueError, err_msg):
            nanfunc(mat, ddof=1, correction=0)


class SharedNanFunctionsTestsMixin:
    def test_mutation(self):
        # Check that passed array is not modified.
        ndat = _ndat.copy()
        for f in self.nanfuncs:
            f(ndat)
            assert_equal(ndat, _ndat)

    def test_keepdims(self):
        mat = np.eye(3)
        for nf, rf in zip(self.nanfuncs, self.stdfuncs):
            for axis in [None, 0, 1]:
                tgt = rf(mat, axis=axis, keepdims=True)
                res = nf(mat, axis=axis, keepdims=True)
                assert_(res.ndim == tgt.ndim)

    def test_out(self):
        mat = np.eye(3)
        for nf, rf in zip(self.nanfuncs, self.stdfuncs):
            resout = np.zeros(3)
            tgt = rf(mat, axis=1)
            res = nf(mat, axis=1, out=resout)
            assert_almost_equal(res, resout)
            assert_almost_equal(res, tgt)

    def test_dtype_from_dtype(self):
        mat = np.eye(3)
        codes = 'efdgFDG'
        for nf, rf in zip(self.nanfuncs, self.stdfuncs):
            for c in codes:
                with suppress_warnings() as sup:
                    if nf in {np.nanstd, np.nanvar} and c in 'FDG':
                        # Giving the warning is a small bug, see gh-8000
                        sup.filter(ComplexWarning)
                    tgt = rf(mat, dtype=np.dtype(c), axis=1).dtype.type
                    res = nf(mat, dtype=np.dtype(c), axis=1).dtype.type
                    assert_(res is tgt)
                    # scalar case
                    tgt = rf(mat, dtype=np.dtype(c), axis=None).dtype.type
                    res = nf(mat, dtype=np.dtype(c), axis=None).dtype.type
                    assert_(res is tgt)

    def test_dtype_from_char(self):
        mat = np.eye(3)
        codes = 'efdgFDG'
        for nf, rf in zip(self.nanfuncs, self.stdfuncs):
            for c in codes:
                with suppress_warnings() as sup:
                    if nf in {np.nanstd, np.nanvar} and c in 'FDG':
                        # Giving the warning is a small bug, see gh-8000
                        sup.filter(ComplexWarning)
                    tgt = rf(mat, dtype=c, axis=1).dtype.type
                    res = nf(mat, dtype=c, axis=1).dtype.type
                    assert_(res is tgt)
                    # scalar case
                    tgt = rf(mat, dtype=c, axis=None).dtype.type
                    res = nf(mat, dtype=c, axis=None).dtype.type
                    assert_(res is tgt)

    def test_dtype_from_input(self):
        codes = 'efdgFDG'
        for nf, rf in zip(self.nanfuncs, self.stdfuncs):
            for c in codes:
                mat = np.eye(3, dtype=c)
                tgt = rf(mat, axis=1).dtype.type
                res = nf(mat, axis=1).dtype.type
                assert_(res is tgt, f"res {res}, tgt {tgt}")
                # scalar case
                tgt = rf(mat, axis=None).dtype.type
                res = nf(mat, axis=None).dtype.type
                assert_(res is tgt)

    def test_result_values(self):
        for nf, rf in zip(self.nanfuncs, self.stdfuncs):
            tgt = [rf(d) for d in _rdat]
            res = nf(_ndat, axis=1)
            assert_almost_equal(res, tgt)

    def test_scalar(self):
        for f in self.nanfuncs:
            assert_(f(0.) == 0.)

    def test_subclass(self):
        class MyNDArray(np.ndarray):
            pass

        # Check that it works and that type and
        # shape are preserved
        array = np.eye(3)
        mine = array.view(MyNDArray)
        for f in self.nanfuncs:
            expected_shape = f(array, axis=0).shape
            res = f(mine, axis=0)
            assert_(isinstance(res, MyNDArray))
            assert_(res.shape == expected_shape)
            expected_shape = f(array, axis=1).shape
            res = f(mine, axis=1)
            assert_(isinstance(res, MyNDArray))
            assert_(res.shape == expected_shape)
            expected_shape = f(array).shape
            res = f(mine)
            assert_(isinstance(res, MyNDArray))
            assert_(res.shape == expected_shape)


class TestNanFunctions_SumProd(SharedNanFunctionsTestsMixin):

    nanfuncs = [np.nansum, np.nanprod]
    stdfuncs = [np.sum, np.prod]

    @pytest.mark.parametrize("axis", [None, 0, 1])
    @pytest.mark.parametrize("dtype", np.typecodes["AllFloat"])
    @pytest.mark.parametrize("array", [
        np.array(np.nan),
        np.full((3, 3), np.nan),
    ], ids=["0d", "2d"])
    def test_allnans(self, axis, dtype, array):
        if axis is not None and array.ndim == 0:
            pytest.skip("`axis != None` not supported for 0d arrays")

        array = array.astype(dtype)
        for func, identity in zip(self.nanfuncs, [0, 1]):
            out = func(array, axis=axis)
            assert np.all(out == identity)
            assert out.dtype == array.dtype

    def test_empty(self):
        for f, tgt_value in zip([np.nansum, np.nanprod], [0, 1]):
            mat = np.zeros((0, 3))
            tgt = [tgt_value] * 3
            res = f(mat, axis=0)
            assert_equal(res, tgt)
            tgt = []
            res = f(mat, axis=1)
            assert_equal(res, tgt)
            tgt = tgt_value
            res = f(mat, axis=None)
            assert_equal(res, tgt)

    @pytest.mark.parametrize("dtype", np.typecodes["AllFloat"])
    def test_initial(self, dtype):
        ar = np.arange(9).astype(dtype)
        ar[:5] = np.nan

        for f in self.nanfuncs:
            reference = 28 if f is np.nansum else 3360
            ret = f(ar, initial=2)
            assert ret.dtype == dtype
            assert ret == reference

    @pytest.mark.parametrize("dtype", np.typecodes["AllFloat"])
    def test_where(self, dtype):
        ar = np.arange(9).reshape(3, 3).astype(dtype)
        ar[0, :] = np.nan
        where = np.ones_like(ar, dtype=np.bool)
        where[:, 0] = False

        for f in self.nanfuncs:
            reference = 26 if f is np.nansum else 2240
            ret = f(ar, where=where, initial=2)
            assert ret.dtype == dtype
            assert ret == reference


class TestNanFunctions_CumSumProd(SharedNanFunctionsTestsMixin):

    nanfuncs = [np.nancumsum, np.nancumprod]
    stdfuncs = [np.cumsum, np.cumprod]

    @pytest.mark.parametrize("axis", [None, 0, 1])
    @pytest.mark.parametrize("dtype", np.typecodes["AllFloat"])
    @pytest.mark.parametrize("array", [
        np.array(np.nan),
        np.full((3, 3), np.nan)
    ], ids=["0d", "2d"])
    def test_allnans(self, axis, dtype, array):
        if axis is not None and array.ndim == 0:
            pytest.skip("`axis != None` not supported for 0d arrays")

        array = array.astype(dtype)
        for func, identity in zip(self.nanfuncs, [0, 1]):
            out = func(array)
            assert np.all(out == identity)
            assert out.dtype == array.dtype

    def test_empty(self):
        for f, tgt_value in zip(self.nanfuncs, [0, 1]):
            mat = np.zeros((0, 3))
            tgt = tgt_value * np.ones((0, 3))
            res = f(mat, axis=0)
            assert_equal(res, tgt)
            tgt = mat
            res = f(mat, axis=1)
            assert_equal(res, tgt)
            tgt = np.zeros(0)
            res = f(mat, axis=None)
            assert_equal(res, tgt)

    def test_keepdims(self):
        for f, g in zip(self.nanfuncs, self.stdfuncs):
            mat = np.eye(3)
            for axis in [None, 0, 1]:
                tgt = f(mat, axis=axis, out=None)
                res = g(mat, axis=axis, out=None)
                assert_(res.ndim == tgt.ndim)

        for f in self.nanfuncs:
            d = np.ones((3, 5, 7, 11))
            # Randomly set some elements to NaN:
            rs = np.random.RandomState(0)
            d[rs.rand(*d.shape) < 0.5] = np.nan
            res = f(d, axis=None)
            assert_equal(res.shape, (1155,))
            for axis in np.arange(4):
                res = f(d, axis=axis)
                assert_equal(res.shape, (3, 5, 7, 11))

    def test_result_values(self):
        for axis in (-2, -1, 0, 1, None):
            tgt = np.cumprod(_ndat_ones, axis=axis)
            res = np.nancumprod(_ndat, axis=axis)
            assert_almost_equal(res, tgt)
            tgt = np.cumsum(_ndat_zeros, axis=axis)
            res = np.nancumsum(_ndat, axis=axis)
            assert_almost_equal(res, tgt)

    def test_out(self):
        mat = np.eye(3)
        for nf, rf in zip(self.nanfuncs, self.stdfuncs):
            resout = np.eye(3)
            for axis in (-2, -1, 0, 1):
                tgt = rf(mat, axis=axis)
                res = nf(mat, axis=axis, out=resout)
                assert_almost_equal(res, resout)
                assert_almost_equal(res, tgt)


class TestNanFunctions_MeanVarStd(SharedNanFunctionsTestsMixin):

    nanfuncs = [np.nanmean, np.nanvar, np.nanstd]
    stdfuncs = [np.mean, np.var, np.std]

    def test_dtype_error(self):
        for f in self.nanfuncs:
            for dtype in [np.bool, np.int_, np.object_]:
                assert_raises(TypeError, f, _ndat, axis=1, dtype=dtype)

    def test_out_dtype_error(self):
        for f in self.nanfuncs:
            for dtype in [np.bool, np.int_, np.object_]:
                out = np.empty(_ndat.shape[0], dtype=dtype)
                assert_raises(TypeError, f, _ndat, axis=1, out=out)

    def test_ddof(self):
        nanfuncs = [np.nanvar, np.nanstd]
        stdfuncs = [np.var, np.std]
        for nf, rf in zip(nanfuncs, stdfuncs):
            for ddof in [0, 1]:
                tgt = [rf(d, ddof=ddof) for d in _rdat]
                res = nf(_ndat, axis=1, ddof=ddof)
                assert_almost_equal(res, tgt)

    def test_ddof_too_big(self):
        nanfuncs = [np.nanvar, np.nanstd]
        stdfuncs = [np.var, np.std]
        dsize = [len(d) for d in _rdat]
        for nf, rf in zip(nanfuncs, stdfuncs):
            for ddof in range(5):
                with suppress_warnings() as sup:
                    sup.record(RuntimeWarning)
                    sup.filter(ComplexWarning)
                    tgt = [ddof >= d for d in dsize]
                    res = nf(_ndat, axis=1, ddof=ddof)
                    assert_equal(np.isnan(res), tgt)
                    if any(tgt):
                        assert_(len(sup.log) == 1)
                    else:
                        assert_(len(sup.log) == 0)

    @pytest.mark.parametrize("axis", [None, 0, 1])
    @pytest.mark.parametrize("dtype", np.typecodes["AllFloat"])
    @pytest.mark.parametrize("array", [
        np.array(np.nan),
        np.full((3, 3), np.nan),
    ], ids=["0d", "2d"])
    def test_allnans(self, axis, dtype, array):
        if axis is not None and array.ndim == 0:
            pytest.skip("`axis != None` not supported for 0d arrays")

        array = array.astype(dtype)
        match = "(Degrees of freedom <= 0 for slice.)|(Mean of empty slice)"
        for func in self.nanfuncs:
            with pytest.warns(RuntimeWarning, match=match):
                out = func(array, axis=axis)
            assert np.isnan(out).all()

            # `nanvar` and `nanstd` convert complex inputs to their
            # corresponding floating dtype
            if func is np.nanmean:
                assert out.dtype == array.dtype
            else:
                assert out.dtype == np.abs(array).dtype

    def test_empty(self):
        mat = np.zeros((0, 3))
        for f in self.nanfuncs:
            for axis in [0, None]:
                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter('always')
                    assert_(np.isnan(f(mat, axis=axis)).all())
                    assert_(len(w) == 1)
                    assert_(issubclass(w[0].category, RuntimeWarning))
            for axis in [1]:
                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter('always')
                    assert_equal(f(mat, axis=axis), np.zeros([]))
                    assert_(len(w) == 0)

    @pytest.mark.parametrize("dtype", np.typecodes["AllFloat"])
    def test_where(self, dtype):
        ar = np.arange(9).reshape(3, 3).astype(dtype)
        ar[0, :] = np.nan
        where = np.ones_like(ar, dtype=np.bool)
        where[:, 0] = False

        for f, f_std in zip(self.nanfuncs, self.stdfuncs):
            reference = f_std(ar[where][2:])
            dtype_reference = dtype if f is np.nanmean else ar.real.dtype

            ret = f(ar, where=where)
            assert ret.dtype == dtype_reference
            np.testing.assert_allclose(ret, reference)

    def test_nanstd_with_mean_keyword(self):
        # Setting the seed to make the test reproducible
        rng = np.random.RandomState(1234)
        A = rng.randn(10, 20, 5) + 0.5
        A[:, 5, :] = np.nan

        mean_out = np.zeros((10, 1, 5))
        std_out = np.zeros((10, 1, 5))

        mean = np.nanmean(A,
                       out=mean_out,
                       axis=1,
                       keepdims=True)

        # The returned  object should be the object specified during calling
        assert mean_out is mean

        std = np.nanstd(A,
                     out=std_out,
                     axis=1,
                     keepdims=True,
                     mean=mean)

        # The returned  object should be the object specified during calling
        assert std_out is std

        # Shape of returned mean and std should be same
        assert std.shape == mean.shape
        assert std.shape == (10, 1, 5)

        # Output should be the same as from the individual algorithms
        std_old = np.nanstd(A, axis=1, keepdims=True)

        assert std_old.shape == mean.shape
        assert_almost_equal(std, std_old)


_TIME_UNITS = (
    "Y", "M", "W", "D", "h", "m", "s", "ms", "us", "ns", "ps", "fs", "as"
)

# All `inexact` + `timdelta64` type codes
_TYPE_CODES = list(np.typecodes["AllFloat"])
_TYPE_CODES += [f"m8[{unit}]" for unit in _TIME_UNITS]


class TestNanFunctions_Median:

    def test_mutation(self):
        # Check that passed array is not modified.
        ndat = _ndat.copy()
        np.nanmedian(ndat)
        assert_equal(ndat, _ndat)

    def test_keepdims(self):
        mat = np.eye(3)
        for axis in [None, 0, 1]:
            tgt = np.median(mat, axis=axis, out=None, overwrite_input=False)
            res = np.nanmedian(mat, axis=axis, out=None, overwrite_input=False)
            assert_(res.ndim == tgt.ndim)

        d = np.ones((3, 5, 7, 11))
        # Randomly set some elements to NaN:
        w = np.random.random((4, 200)) * np.array(d.shape)[:, None]
        w = w.astype(np.intp)
        d[tuple(w)] = np.nan
        with suppress_warnings() as sup:
            sup.filter(RuntimeWarning)
            res = np.nanmedian(d, axis=None, keepdims=True)
            assert_equal(res.shape, (1, 1, 1, 1))
            res = np.nanmedian(d, axis=(0, 1), keepdims=True)
            assert_equal(res.shape, (1, 1, 7, 11))
            res = np.nanmedian(d, axis=(0, 3), keepdims=True)
            assert_equal(res.shape, (1, 5, 7, 1))
            res = np.nanmedian(d, axis=(1,), keepdims=True)
            assert_equal(res.shape, (3, 1, 7, 11))
            res = np.nanmedian(d, axis=(0, 1, 2, 3), keepdims=True)
            assert_equal(res.shape, (1, 1, 1, 1))
            res = np.nanmedian(d, axis=(0, 1, 3), keepdims=True)
            assert_equal(res.shape, (1, 1, 7, 1))

    @pytest.mark.parametrize(
        argnames='axis',
        argvalues=[
            None,
            1,
            (1, ),
            (0, 1),
            (-3, -1),
        ]
    )
    @pytest.mark.filterwarnings("ignore:All-NaN slice:RuntimeWarning")
    def test_keepdims_out(self, axis):
        d = np.ones((3, 5, 7, 11))
        # Randomly set some elements to NaN:
        w = np.random.random((4, 200)) * np.array(d.shape)[:, None]
        w = w.astype(np.intp)
        d[tuple(w)] = np.nan
        if axis is None:
            shape_out = (1,) * d.ndim
        else:
            axis_norm = normalize_axis_tuple(axis, d.ndim)
            shape_out = tuple(
                1 if i in axis_norm else d.shape[i] for i in range(d.ndim))
        out = np.empty(shape_out)
        result = np.nanmedian(d, axis=axis, keepdims=True, out=out)
        assert result is out
        assert_equal(result.shape, shape_out)

    def test_out(self):
        mat = np.random.rand(3, 3)
        nan_mat = np.insert(mat, [0, 2], np.nan, axis=1)
        resout = np.zeros(3)
        tgt = np.median(mat, axis=1)
        res = np.nanmedian(nan_mat, axis=1, out=resout)
        assert_almost_equal(res, resout)
        assert_almost_equal(res, tgt)
        # 0-d output:
        resout = np.zeros(())
        tgt = np.median(mat, axis=None)
        res = np.nanmedian(nan_mat, axis=None, out=resout)
        assert_almost_equal(res, resout)
        assert_almost_equal(res, tgt)
        res = np.nanmedian(nan_mat, axis=(0, 1), out=resout)
        assert_almost_equal(res, resout)
        assert_almost_equal(res, tgt)

    def test_small_large(self):
        # test the small and large code paths, current cutoff 400 elements
        for s in [5, 20, 51, 200, 1000]:
            d = np.random.randn(4, s)
            # Randomly set some elements to NaN:
            w = np.random.randint(0, d.size, size=d.size // 5)
            d.ravel()[w] = np.nan
            d[:, 0] = 1.  # ensure at least one good value
            # use normal median without nans to compare
            tgt = []
            for x in d:
                nonan = np.compress(~np.isnan(x), x)
                tgt.append(np.median(nonan, overwrite_input=True))

            assert_array_equal(np.nanmedian(d, axis=-1), tgt)

    def test_result_values(self):
        tgt = [np.median(d) for d in _rdat]
        res = np.nanmedian(_ndat, axis=1)
        assert_almost_equal(res, tgt)

    @pytest.mark.parametrize("axis", [None, 0, 1])
    @pytest.mark.parametrize("dtype", _TYPE_CODES)
    def test_allnans(self, dtype, axis):
        mat = np.full((3, 3), np.nan).astype(dtype)
        with suppress_warnings() as sup:
            sup.record(RuntimeWarning)

            output = np.nanmedian(mat, axis=axis)
            assert output.dtype == mat.dtype
            assert np.isnan(output).all()

            if axis is None:
                assert_(len(sup.log) == 1)
            else:
                assert_(len(sup.log) == 3)

            # Check scalar
            scalar = np.array(np.nan).astype(dtype)[()]
            output_scalar = np.nanmedian(scalar)
            assert output_scalar.dtype == scalar.dtype
            assert np.isnan(output_scalar)

            if axis is None:
                assert_(len(sup.log) == 2)
            else:
                assert_(len(sup.log) == 4)

    def test_empty(self):
        mat = np.zeros((0, 3))
        for axis in [0, None]:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always')
                assert_(np.isnan(np.nanmedian(mat, axis=axis)).all())
                assert_(len(w) == 1)
                assert_(issubclass(w[0].category, RuntimeWarning))
        for axis in [1]:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always')
                assert_equal(np.nanmedian(mat, axis=axis), np.zeros([]))
                assert_(len(w) == 0)

    def test_scalar(self):
        assert_(np.nanmedian(0.) == 0.)

    def test_extended_axis_invalid(self):
        d = np.ones((3, 5, 7, 11))
        assert_raises(AxisError, np.nanmedian, d, axis=-5)
        assert_raises(AxisError, np.nanmedian, d, axis=(0, -5))
        assert_raises(AxisError, np.nanmedian, d, axis=4)
        assert_raises(AxisError, np.nanmedian, d, axis=(0, 4))
        assert_raises(ValueError, np.nanmedian, d, axis=(1, 1))

    def test_float_special(self):
        with suppress_warnings() as sup:
            sup.filter(RuntimeWarning)
            for inf in [np.inf, -np.inf]:
                a = np.array([[inf,  np.nan], [np.nan, np.nan]])
                assert_equal(np.nanmedian(a, axis=0), [inf,  np.nan])
                assert_equal(np.nanmedian(a, axis=1), [inf,  np.nan])
                assert_equal(np.nanmedian(a), inf)

                # minimum fill value check
                a = np.array([[np.nan, np.nan, inf],
                             [np.nan, np.nan, inf]])
                assert_equal(np.nanmedian(a), inf)
                assert_equal(np.nanmedian(a, axis=0), [np.nan, np.nan, inf])
                assert_equal(np.nanmedian(a, axis=1), inf)

                # no mask path
                a = np.array([[inf, inf], [inf, inf]])
                assert_equal(np.nanmedian(a, axis=1), inf)

                a = np.array([[inf, 7, -inf, -9],
                              [-10, np.nan, np.nan, 5],
                              [4, np.nan, np.nan, inf]],
                              dtype=np.float32)
                if inf > 0:
                    assert_equal(np.nanmedian(a, axis=0), [4., 7., -inf, 5.])
                    assert_equal(np.nanmedian(a), 4.5)
                else:
                    assert_equal(np.nanmedian(a, axis=0), [-10., 7., -inf, -9.])
                    assert_equal(np.nanmedian(a), -2.5)
                assert_equal(np.nanmedian(a, axis=-1), [-1., -2.5, inf])

                for i in range(10):
                    for j in range(1, 10):
                        a = np.array([([np.nan] * i) + ([inf] * j)] * 2)
                        assert_equal(np.nanmedian(a), inf)
                        assert_equal(np.nanmedian(a, axis=1), inf)
                        assert_equal(np.nanmedian(a, axis=0),
                                     ([np.nan] * i) + [inf] * j)

                        a = np.array([([np.nan] * i) + ([-inf] * j)] * 2)
                        assert_equal(np.nanmedian(a), -inf)
                        assert_equal(np.nanmedian(a, axis=1), -inf)
                        assert_equal(np.nanmedian(a, axis=0),
                                     ([np.nan] * i) + [-inf] * j)


class TestNanFunctions_Percentile:

    def test_mutation(self):
        # Check that passed array is not modified.
        ndat = _ndat.copy()
        np.nanpercentile(ndat, 30)
        assert_equal(ndat, _ndat)

    def test_keepdims(self):
        mat = np.eye(3)
        for axis in [None, 0, 1]:
            tgt = np.percentile(mat, 70, axis=axis, out=None,
                                overwrite_input=False)
            res = np.nanpercentile(mat, 70, axis=axis, out=None,
                                   overwrite_input=False)
            assert_(res.ndim == tgt.ndim)

        d = np.ones((3, 5, 7, 11))
        # Randomly set some elements to NaN:
        w = np.random.random((4, 200)) * np.array(d.shape)[:, None]
        w = w.astype(np.intp)
        d[tuple(w)] = np.nan
        with suppress_warnings() as sup:
            sup.filter(RuntimeWarning)
            res = np.nanpercentile(d, 90, axis=None, keepdims=True)
            assert_equal(res.shape, (1, 1, 1, 1))
            res = np.nanpercentile(d, 90, axis=(0, 1), keepdims=True)
            assert_equal(res.shape, (1, 1, 7, 11))
            res = np.nanpercentile(d, 90, axis=(0, 3), keepdims=True)
            assert_equal(res.shape, (1, 5, 7, 1))
            res = np.nanpercentile(d, 90, axis=(1,), keepdims=True)
            assert_equal(res.shape, (3, 1, 7, 11))
            res = np.nanpercentile(d, 90, axis=(0, 1, 2, 3), keepdims=True)
            assert_equal(res.shape, (1, 1, 1, 1))
            res = np.nanpercentile(d, 90, axis=(0, 1, 3), keepdims=True)
            assert_equal(res.shape, (1, 1, 7, 1))

    @pytest.mark.parametrize('q', [7, [1, 7]])
    @pytest.mark.parametrize(
        argnames='axis',
        argvalues=[
            None,
            1,
            (1,),
            (0, 1),
            (-3, -1),
        ]
    )
    @pytest.mark.filterwarnings("ignore:All-NaN slice:RuntimeWarning")
    def test_keepdims_out(self, q, axis):
        d = np.ones((3, 5, 7, 11))
        # Randomly set some elements to NaN:
        w = np.random.random((4, 200)) * np.array(d.shape)[:, None]
        w = w.astype(np.intp)
        d[tuple(w)] = np.nan
        if axis is None:
            shape_out = (1,) * d.ndim
        else:
            axis_norm = normalize_axis_tuple(axis, d.ndim)
            shape_out = tuple(
                1 if i in axis_norm else d.shape[i] for i in range(d.ndim))
        shape_out = np.shape(q) + shape_out

        out = np.empty(shape_out)
        result = np.nanpercentile(d, q, axis=axis, keepdims=True, out=out)
        assert result is out
        assert_equal(result.shape, shape_out)

    @pytest.mark.parametrize("weighted", [False, True])
    def test_out(self, weighted):
        mat = np.random.rand(3, 3)
        nan_mat = np.insert(mat, [0, 2], np.nan, axis=1)
        resout = np.zeros(3)
        if weighted:
            w_args = {"weights": np.ones_like(mat), "method": "inverted_cdf"}
            nan_w_args = {
                "weights": np.ones_like(nan_mat), "method": "inverted_cdf"
            }
        else:
            w_args = {}
            nan_w_args = {}
        tgt = np.percentile(mat, 42, axis=1, **w_args)
        res = np.nanpercentile(nan_mat, 42, axis=1, out=resout, **nan_w_args)
        assert_almost_equal(res, resout)
        assert_almost_equal(res, tgt)
        # 0-d output:
        resout = np.zeros(())
        tgt = np.percentile(mat, 42, axis=None, **w_args)
        res = np.nanpercentile(
            nan_mat, 42, axis=None, out=resout, **nan_w_args
        )
        assert_almost_equal(res, resout)
        assert_almost_equal(res, tgt)
        res = np.nanpercentile(
            nan_mat, 42, axis=(0, 1), out=resout, **nan_w_args
        )
        assert_almost_equal(res, resout)
        assert_almost_equal(res, tgt)

    def test_complex(self):
        arr_c = np.array([0.5 + 3.0j, 2.1 + 0.5j, 1.6 + 2.3j], dtype='G')
        assert_raises(TypeError, np.nanpercentile, arr_c, 0.5)
        arr_c = np.array([0.5 + 3.0j, 2.1 + 0.5j, 1.6 + 2.3j], dtype='D')
        assert_raises(TypeError, np.nanpercentile, arr_c, 0.5)
        arr_c = np.array([0.5 + 3.0j, 2.1 + 0.5j, 1.6 + 2.3j], dtype='F')
        assert_raises(TypeError, np.nanpercentile, arr_c, 0.5)

    @pytest.mark.parametrize("weighted", [False, True])
    @pytest.mark.parametrize("use_out", [False, True])
    def test_result_values(self, weighted, use_out):
        if weighted:
            percentile = partial(np.percentile, method="inverted_cdf")
            nanpercentile = partial(np.nanpercentile, method="inverted_cdf")

            def gen_weights(d):
                return np.ones_like(d)

        else:
            percentile = np.percentile
            nanpercentile = np.nanpercentile

            def gen_weights(d):
                return None

        tgt = [percentile(d, 28, weights=gen_weights(d)) for d in _rdat]
        out = np.empty_like(tgt) if use_out else None
        res = nanpercentile(_ndat, 28, axis=1,
                            weights=gen_weights(_ndat), out=out)
        assert_almost_equal(res, tgt)
        # Transpose the array to fit the output convention of numpy.percentile
        tgt = np.transpose([percentile(d, (28, 98), weights=gen_weights(d))
                            for d in _rdat])
        out = np.empty_like(tgt) if use_out else None
        res = nanpercentile(_ndat, (28, 98), axis=1,
                            weights=gen_weights(_ndat), out=out)
        assert_almost_equal(res, tgt)

    @pytest.mark.parametrize("axis", [None, 0, 1])
    @pytest.mark.parametrize("dtype", np.typecodes["Float"])
    @pytest.mark.parametrize("array", [
        np.array(np.nan),
        np.full((3, 3), np.nan),
    ], ids=["0d", "2d"])
    def test_allnans(self, axis, dtype, array):
        if axis is not None and array.ndim == 0:
            pytest.skip("`axis != None` not supported for 0d arrays")

        array = array.astype(dtype)
        with pytest.warns(RuntimeWarning, match="All-NaN slice encountered"):
            out = np.nanpercentile(array, 60, axis=axis)
        assert np.isnan(out).all()
        assert out.dtype == array.dtype

    def test_empty(self):
        mat = np.zeros((0, 3))
        for axis in [0, None]:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always')
                assert_(np.isnan(np.nanpercentile(mat, 40, axis=axis)).all())
                assert_(len(w) == 1)
                assert_(issubclass(w[0].category, RuntimeWarning))
        for axis in [1]:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always')
                assert_equal(np.nanpercentile(mat, 40, axis=axis), np.zeros([]))
                assert_(len(w) == 0)

    def test_scalar(self):
        assert_equal(np.nanpercentile(0., 100), 0.)
        a = np.arange(6)
        r = np.nanpercentile(a, 50, axis=0)
        assert_equal(r, 2.5)
        assert_(np.isscalar(r))

    def test_extended_axis_invalid(self):
        d = np.ones((3, 5, 7, 11))
        assert_raises(AxisError, np.nanpercentile, d, q=5, axis=-5)
        assert_raises(AxisError, np.nanpercentile, d, q=5, axis=(0, -5))
        assert_raises(AxisError, np.nanpercentile, d, q=5, axis=4)
        assert_raises(AxisError, np.nanpercentile, d, q=5, axis=(0, 4))
        assert_raises(ValueError, np.nanpercentile, d, q=5, axis=(1, 1))

    def test_multiple_percentiles(self):
        perc = [50, 100]
        mat = np.ones((4, 3))
        nan_mat = np.nan * mat
        # For checking consistency in higher dimensional case
        large_mat = np.ones((3, 4, 5))
        large_mat[:, 0:2:4, :] = 0
        large_mat[:, :, 3:] *= 2
        for axis in [None, 0, 1]:
            for keepdim in [False, True]:
                with suppress_warnings() as sup:
                    sup.filter(RuntimeWarning, "All-NaN slice encountered")
                    val = np.percentile(mat, perc, axis=axis, keepdims=keepdim)
                    nan_val = np.nanpercentile(nan_mat, perc, axis=axis,
                                               keepdims=keepdim)
                    assert_equal(nan_val.shape, val.shape)

                    val = np.percentile(large_mat, perc, axis=axis,
                                        keepdims=keepdim)
                    nan_val = np.nanpercentile(large_mat, perc, axis=axis,
                                               keepdims=keepdim)
                    assert_equal(nan_val, val)

        megamat = np.ones((3, 4, 5, 6))
        assert_equal(
            np.nanpercentile(megamat, perc, axis=(1, 2)).shape, (2, 3, 6)
        )

    @pytest.mark.parametrize("nan_weight", [0, 1, 2, 3, 1e200])
    def test_nan_value_with_weight(self, nan_weight):
        x = [1, np.nan, 2, 3]
        result = np.float64(2.0)
        q_unweighted = np.nanpercentile(x, 50, method="inverted_cdf")
        assert_equal(q_unweighted, result)

        # The weight value at the nan position should not matter.
        w = [1.0, nan_weight, 1.0, 1.0]
        q_weighted = np.nanpercentile(x, 50, weights=w, method="inverted_cdf")
        assert_equal(q_weighted, result)

    @pytest.mark.parametrize("axis", [0, 1, 2])
    def test_nan_value_with_weight_ndim(self, axis):
        # Create a multi-dimensional array to test
        np.random.seed(1)
        x_no_nan = np.random.random(size=(100, 99, 2))
        # Set some places to NaN (not particularly smart) so there is always
        # some non-Nan.
        x = x_no_nan.copy()
        x[np.arange(99), np.arange(99), 0] = np.nan

        p = np.array([[20., 50., 30], [70, 33, 80]])

        # We just use ones as weights, but replace it with 0 or 1e200 at the
        # NaN positions below.
        weights = np.ones_like(x)

        # For comparison use weighted normal percentile with nan weights at
        # 0 (and no NaNs); not sure this is strictly identical but should be
        # sufficiently so (if a percentile lies exactly on a 0 value).
        weights[np.isnan(x)] = 0
        p_expected = np.percentile(
            x_no_nan, p, axis=axis, weights=weights, method="inverted_cdf")

        p_unweighted = np.nanpercentile(
            x, p, axis=axis, method="inverted_cdf")
        # The normal and unweighted versions should be identical:
        assert_equal(p_unweighted, p_expected)

        weights[np.isnan(x)] = 1e200  # huge value, shouldn't matter
        p_weighted = np.nanpercentile(
            x, p, axis=axis, weights=weights, method="inverted_cdf")
        assert_equal(p_weighted, p_expected)
        # Also check with out passed:
        out = np.empty_like(p_weighted)
        res = np.nanpercentile(
            x, p, axis=axis, weights=weights, out=out, method="inverted_cdf")

        assert res is out
        assert_equal(out, p_expected)


class TestNanFunctions_Quantile:
    # most of this is already tested by TestPercentile

    @pytest.mark.parametrize("weighted", [False, True])
    def test_regression(self, weighted):
        ar = np.arange(24).reshape(2, 3, 4).astype(float)
        ar[0][1] = np.nan
        if weighted:
            w_args = {"weights": np.ones_like(ar), "method": "inverted_cdf"}
        else:
            w_args = {}

        assert_equal(np.nanquantile(ar, q=0.5, **w_args),
                     np.nanpercentile(ar, q=50, **w_args))
        assert_equal(np.nanquantile(ar, q=0.5, axis=0, **w_args),
                     np.nanpercentile(ar, q=50, axis=0, **w_args))
        assert_equal(np.nanquantile(ar, q=0.5, axis=1, **w_args),
                     np.nanpercentile(ar, q=50, axis=1, **w_args))
        assert_equal(np.nanquantile(ar, q=[0.5], axis=1, **w_args),
                     np.nanpercentile(ar, q=[50], axis=1, **w_args))
        assert_equal(np.nanquantile(ar, q=[0.25, 0.5, 0.75], axis=1, **w_args),
                     np.nanpercentile(ar, q=[25, 50, 75], axis=1, **w_args))

    def test_basic(self):
        x = np.arange(8) * 0.5
        assert_equal(np.nanquantile(x, 0), 0.)
        assert_equal(np.nanquantile(x, 1), 3.5)
        assert_equal(np.nanquantile(x, 0.5), 1.75)

    def test_complex(self):
        arr_c = np.array([0.5 + 3.0j, 2.1 + 0.5j, 1.6 + 2.3j], dtype='G')
        assert_raises(TypeError, np.nanquantile, arr_c, 0.5)
        arr_c = np.array([0.5 + 3.0j, 2.1 + 0.5j, 1.6 + 2.3j], dtype='D')
        assert_raises(TypeError, np.nanquantile, arr_c, 0.5)
        arr_c = np.array([0.5 + 3.0j, 2.1 + 0.5j, 1.6 + 2.3j], dtype='F')
        assert_raises(TypeError, np.nanquantile, arr_c, 0.5)

    def test_no_p_overwrite(self):
        # this is worth retesting, because quantile does not make a copy
        p0 = np.array([0, 0.75, 0.25, 0.5, 1.0])
        p = p0.copy()
        np.nanquantile(np.arange(100.), p, method="midpoint")
        assert_array_equal(p, p0)

        p0 = p0.tolist()
        p = p.tolist()
        np.nanquantile(np.arange(100.), p, method="midpoint")
        assert_array_equal(p, p0)

    @pytest.mark.parametrize("axis", [None, 0, 1])
    @pytest.mark.parametrize("dtype", np.typecodes["Float"])
    @pytest.mark.parametrize("array", [
        np.array(np.nan),
        np.full((3, 3), np.nan),
    ], ids=["0d", "2d"])
    def test_allnans(self, axis, dtype, array):
        if axis is not None and array.ndim == 0:
            pytest.skip("`axis != None` not supported for 0d arrays")

        array = array.astype(dtype)
        with pytest.warns(RuntimeWarning, match="All-NaN slice encountered"):
            out = np.nanquantile(array, 1, axis=axis)
        assert np.isnan(out).all()
        assert out.dtype == array.dtype

@pytest.mark.parametrize("arr, expected", [
    # array of floats with some nans
    (np.array([np.nan, 5.0, np.nan, np.inf]),
     np.array([False, True, False, True])),
    # int64 array that can't possibly have nans
    (np.array([1, 5, 7, 9], dtype=np.int64),
     True),
    # bool array that can't possibly have nans
    (np.array([False, True, False, True]),
     True),
    # 2-D complex array with nans
    (np.array([[np.nan, 5.0],
               [np.nan, np.inf]], dtype=np.complex64),
     np.array([[False, True],
               [False, True]])),
    ])
def test__nan_mask(arr, expected):
    for out in [None, np.empty(arr.shape, dtype=np.bool)]:
        actual = _nan_mask(arr, out=out)
        assert_equal(actual, expected)
        # the above won't distinguish between True proper
        # and an array of True values; we want True proper
        # for types that can't possibly contain NaN
        if type(expected) is not np.ndarray:
            assert actual is True


def test__replace_nan():
    """ Test that _replace_nan returns the original array if there are no
    NaNs, not a copy.
    """
    for dtype in [np.bool, np.int32, np.int64]:
        arr = np.array([0, 1], dtype=dtype)
        result, mask = _replace_nan(arr, 0)
        assert mask is None
        # do not make a copy if there are no nans
        assert result is arr

    for dtype in [np.float32, np.float64]:
        arr = np.array([0, 1], dtype=dtype)
        result, mask = _replace_nan(arr, 2)
        assert (mask == False).all()
        # mask is not None, so we make a copy
        assert result is not arr
        assert_equal(result, arr)

        arr_nan = np.array([0, 1, np.nan], dtype=dtype)
        result_nan, mask_nan = _replace_nan(arr_nan, 2)
        assert_equal(mask_nan, np.array([False, False, True]))
        assert result_nan is not arr_nan
        assert_equal(result_nan, np.array([0, 1, 2]))
        assert np.isnan(arr_nan[-1])


def test_memmap_takes_fast_route(tmpdir):
    # We want memory mapped arrays to take the fast route through nanmax,
    # which avoids creating a mask by using fmax.reduce (see gh-28721). So we
    # check that on bad input, the error is from fmax (rather than maximum).
    a = np.arange(10., dtype=float)
    with open(tmpdir.join("data.bin"), "w+b") as fh:
        fh.write(a.tobytes())
        mm = np.memmap(fh, dtype=a.dtype, shape=a.shape)
        with pytest.raises(ValueError, match="reduction operation fmax"):
            np.nanmax(mm, out=np.zeros(2))
        # For completeness, same for nanmin.
        with pytest.raises(ValueError, match="reduction operation fmin"):
            np.nanmin(mm, out=np.zeros(2))