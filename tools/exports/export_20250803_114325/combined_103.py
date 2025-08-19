
# === NexusCore/openenv\Lib\site-packages\cffi\backend_ctypes.py ===
import ctypes, ctypes.util, operator, sys
from . import model

if sys.version_info < (3,):
    bytechr = chr
else:
    unicode = str
    long = int
    xrange = range
    bytechr = lambda num: bytes([num])

class CTypesType(type):
    pass

class CTypesData(object):
    __metaclass__ = CTypesType
    __slots__ = ['__weakref__']
    __name__ = '<cdata>'

    def __init__(self, *args):
        raise TypeError("cannot instantiate %r" % (self.__class__,))

    @classmethod
    def _newp(cls, init):
        raise TypeError("expected a pointer or array ctype, got '%s'"
                        % (cls._get_c_name(),))

    @staticmethod
    def _to_ctypes(value):
        raise TypeError

    @classmethod
    def _arg_to_ctypes(cls, *value):
        try:
            ctype = cls._ctype
        except AttributeError:
            raise TypeError("cannot create an instance of %r" % (cls,))
        if value:
            res = cls._to_ctypes(*value)
            if not isinstance(res, ctype):
                res = cls._ctype(res)
        else:
            res = cls._ctype()
        return res

    @classmethod
    def _create_ctype_obj(cls, init):
        if init is None:
            return cls._arg_to_ctypes()
        else:
            return cls._arg_to_ctypes(init)

    @staticmethod
    def _from_ctypes(ctypes_value):
        raise TypeError

    @classmethod
    def _get_c_name(cls, replace_with=''):
        return cls._reftypename.replace(' &', replace_with)

    @classmethod
    def _fix_class(cls):
        cls.__name__ = 'CData<%s>' % (cls._get_c_name(),)
        cls.__qualname__ = 'CData<%s>' % (cls._get_c_name(),)
        cls.__module__ = 'ffi'

    def _get_own_repr(self):
        raise NotImplementedError

    def _addr_repr(self, address):
        if address == 0:
            return 'NULL'
        else:
            if address < 0:
                address += 1 << (8*ctypes.sizeof(ctypes.c_void_p))
            return '0x%x' % address

    def __repr__(self, c_name=None):
        own = self._get_own_repr()
        return '<cdata %r %s>' % (c_name or self._get_c_name(), own)

    def _convert_to_address(self, BClass):
        if BClass is None:
            raise TypeError("cannot convert %r to an address" % (
                self._get_c_name(),))
        else:
            raise TypeError("cannot convert %r to %r" % (
                self._get_c_name(), BClass._get_c_name()))

    @classmethod
    def _get_size(cls):
        return ctypes.sizeof(cls._ctype)

    def _get_size_of_instance(self):
        return ctypes.sizeof(self._ctype)

    @classmethod
    def _cast_from(cls, source):
        raise TypeError("cannot cast to %r" % (cls._get_c_name(),))

    def _cast_to_integer(self):
        return self._convert_to_address(None)

    @classmethod
    def _alignment(cls):
        return ctypes.alignment(cls._ctype)

    def __iter__(self):
        raise TypeError("cdata %r does not support iteration" % (
            self._get_c_name()),)

    def _make_cmp(name):
        cmpfunc = getattr(operator, name)
        def cmp(self, other):
            v_is_ptr = not isinstance(self, CTypesGenericPrimitive)
            w_is_ptr = (isinstance(other, CTypesData) and
                           not isinstance(other, CTypesGenericPrimitive))
            if v_is_ptr and w_is_ptr:
                return cmpfunc(self._convert_to_address(None),
                               other._convert_to_address(None))
            elif v_is_ptr or w_is_ptr:
                return NotImplemented
            else:
                if isinstance(self, CTypesGenericPrimitive):
                    self = self._value
                if isinstance(other, CTypesGenericPrimitive):
                    other = other._value
                return cmpfunc(self, other)
        cmp.func_name = name
        return cmp

    __eq__ = _make_cmp('__eq__')
    __ne__ = _make_cmp('__ne__')
    __lt__ = _make_cmp('__lt__')
    __le__ = _make_cmp('__le__')
    __gt__ = _make_cmp('__gt__')
    __ge__ = _make_cmp('__ge__')

    def __hash__(self):
        return hash(self._convert_to_address(None))

    def _to_string(self, maxlen):
        raise TypeError("string(): %r" % (self,))


class CTypesGenericPrimitive(CTypesData):
    __slots__ = []

    def __hash__(self):
        return hash(self._value)

    def _get_own_repr(self):
        return repr(self._from_ctypes(self._value))


class CTypesGenericArray(CTypesData):
    __slots__ = []

    @classmethod
    def _newp(cls, init):
        return cls(init)

    def __iter__(self):
        for i in xrange(len(self)):
            yield self[i]

    def _get_own_repr(self):
        return self._addr_repr(ctypes.addressof(self._blob))


class CTypesGenericPtr(CTypesData):
    __slots__ = ['_address', '_as_ctype_ptr']
    _automatic_casts = False
    kind = "pointer"

    @classmethod
    def _newp(cls, init):
        return cls(init)

    @classmethod
    def _cast_from(cls, source):
        if source is None:
            address = 0
        elif isinstance(source, CTypesData):
            address = source._cast_to_integer()
        elif isinstance(source, (int, long)):
            address = source
        else:
            raise TypeError("bad type for cast to %r: %r" %
                            (cls, type(source).__name__))
        return cls._new_pointer_at(address)

    @classmethod
    def _new_pointer_at(cls, address):
        self = cls.__new__(cls)
        self._address = address
        self._as_ctype_ptr = ctypes.cast(address, cls._ctype)
        return self

    def _get_own_repr(self):
        try:
            return self._addr_repr(self._address)
        except AttributeError:
            return '???'

    def _cast_to_integer(self):
        return self._address

    def __nonzero__(self):
        return bool(self._address)
    __bool__ = __nonzero__

    @classmethod
    def _to_ctypes(cls, value):
        if not isinstance(value, CTypesData):
            raise TypeError("unexpected %s object" % type(value).__name__)
        address = value._convert_to_address(cls)
        return ctypes.cast(address, cls._ctype)

    @classmethod
    def _from_ctypes(cls, ctypes_ptr):
        address = ctypes.cast(ctypes_ptr, ctypes.c_void_p).value or 0
        return cls._new_pointer_at(address)

    @classmethod
    def _initialize(cls, ctypes_ptr, value):
        if value:
            ctypes_ptr.contents = cls._to_ctypes(value).contents

    def _convert_to_address(self, BClass):
        if (BClass in (self.__class__, None) or BClass._automatic_casts
            or self._automatic_casts):
            return self._address
        else:
            return CTypesData._convert_to_address(self, BClass)


class CTypesBaseStructOrUnion(CTypesData):
    __slots__ = ['_blob']

    @classmethod
    def _create_ctype_obj(cls, init):
        # may be overridden
        raise TypeError("cannot instantiate opaque type %s" % (cls,))

    def _get_own_repr(self):
        return self._addr_repr(ctypes.addressof(self._blob))

    @classmethod
    def _offsetof(cls, fieldname):
        return getattr(cls._ctype, fieldname).offset

    def _convert_to_address(self, BClass):
        if getattr(BClass, '_BItem', None) is self.__class__:
            return ctypes.addressof(self._blob)
        else:
            return CTypesData._convert_to_address(self, BClass)

    @classmethod
    def _from_ctypes(cls, ctypes_struct_or_union):
        self = cls.__new__(cls)
        self._blob = ctypes_struct_or_union
        return self

    @classmethod
    def _to_ctypes(cls, value):
        return value._blob

    def __repr__(self, c_name=None):
        return CTypesData.__repr__(self, c_name or self._get_c_name(' &'))


class CTypesBackend(object):

    PRIMITIVE_TYPES = {
        'char': ctypes.c_char,
        'short': ctypes.c_short,
        'int': ctypes.c_int,
        'long': ctypes.c_long,
        'long long': ctypes.c_longlong,
        'signed char': ctypes.c_byte,
        'unsigned char': ctypes.c_ubyte,
        'unsigned short': ctypes.c_ushort,
        'unsigned int': ctypes.c_uint,
        'unsigned long': ctypes.c_ulong,
        'unsigned long long': ctypes.c_ulonglong,
        'float': ctypes.c_float,
        'double': ctypes.c_double,
        '_Bool': ctypes.c_bool,
        }

    for _name in ['unsigned long long', 'unsigned long',
                  'unsigned int', 'unsigned short', 'unsigned char']:
        _size = ctypes.sizeof(PRIMITIVE_TYPES[_name])
        PRIMITIVE_TYPES['uint%d_t' % (8*_size)] = PRIMITIVE_TYPES[_name]
        if _size == ctypes.sizeof(ctypes.c_void_p):
            PRIMITIVE_TYPES['uintptr_t'] = PRIMITIVE_TYPES[_name]
        if _size == ctypes.sizeof(ctypes.c_size_t):
            PRIMITIVE_TYPES['size_t'] = PRIMITIVE_TYPES[_name]

    for _name in ['long long', 'long', 'int', 'short', 'signed char']:
        _size = ctypes.sizeof(PRIMITIVE_TYPES[_name])
        PRIMITIVE_TYPES['int%d_t' % (8*_size)] = PRIMITIVE_TYPES[_name]
        if _size == ctypes.sizeof(ctypes.c_void_p):
            PRIMITIVE_TYPES['intptr_t'] = PRIMITIVE_TYPES[_name]
            PRIMITIVE_TYPES['ptrdiff_t'] = PRIMITIVE_TYPES[_name]
        if _size == ctypes.sizeof(ctypes.c_size_t):
            PRIMITIVE_TYPES['ssize_t'] = PRIMITIVE_TYPES[_name]


    def __init__(self):
        self.RTLD_LAZY = 0   # not supported anyway by ctypes
        self.RTLD_NOW  = 0
        self.RTLD_GLOBAL = ctypes.RTLD_GLOBAL
        self.RTLD_LOCAL = ctypes.RTLD_LOCAL

    def set_ffi(self, ffi):
        self.ffi = ffi

    def _get_types(self):
        return CTypesData, CTypesType

    def load_library(self, path, flags=0):
        cdll = ctypes.CDLL(path, flags)
        return CTypesLibrary(self, cdll)

    def new_void_type(self):
        class CTypesVoid(CTypesData):
            __slots__ = []
            _reftypename = 'void &'
            @staticmethod
            def _from_ctypes(novalue):
                return None
            @staticmethod
            def _to_ctypes(novalue):
                if novalue is not None:
                    raise TypeError("None expected, got %s object" %
                                    (type(novalue).__name__,))
                return None
        CTypesVoid._fix_class()
        return CTypesVoid

    def new_primitive_type(self, name):
        if name == 'wchar_t':
            raise NotImplementedError(name)
        ctype = self.PRIMITIVE_TYPES[name]
        if name == 'char':
            kind = 'char'
        elif name in ('float', 'double'):
            kind = 'float'
        else:
            if name in ('signed char', 'unsigned char'):
                kind = 'byte'
            elif name == '_Bool':
                kind = 'bool'
            else:
                kind = 'int'
            is_signed = (ctype(-1).value == -1)
        #
        def _cast_source_to_int(source):
            if isinstance(source, (int, long, float)):
                source = int(source)
            elif isinstance(source, CTypesData):
                source = source._cast_to_integer()
            elif isinstance(source, bytes):
                source = ord(source)
            elif source is None:
                source = 0
            else:
                raise TypeError("bad type for cast to %r: %r" %
                                (CTypesPrimitive, type(source).__name__))
            return source
        #
        kind1 = kind
        class CTypesPrimitive(CTypesGenericPrimitive):
            __slots__ = ['_value']
            _ctype = ctype
            _reftypename = '%s &' % name
            kind = kind1

            def __init__(self, value):
                self._value = value

            @staticmethod
            def _create_ctype_obj(init):
                if init is None:
                    return ctype()
                return ctype(CTypesPrimitive._to_ctypes(init))

            if kind == 'int' or kind == 'byte':
                @classmethod
                def _cast_from(cls, source):
                    source = _cast_source_to_int(source)
                    source = ctype(source).value     # cast within range
                    return cls(source)
                def __int__(self):
                    return self._value

            if kind == 'bool':
                @classmethod
                def _cast_from(cls, source):
                    if not isinstance(source, (int, long, float)):
                        source = _cast_source_to_int(source)
                    return cls(bool(source))
                def __int__(self):
                    return int(self._value)

            if kind == 'char':
                @classmethod
                def _cast_from(cls, source):
                    source = _cast_source_to_int(source)
                    source = bytechr(source & 0xFF)
                    return cls(source)
                def __int__(self):
                    return ord(self._value)

            if kind == 'float':
                @classmethod
                def _cast_from(cls, source):
                    if isinstance(source, float):
                        pass
                    elif isinstance(source, CTypesGenericPrimitive):
                        if hasattr(source, '__float__'):
                            source = float(source)
                        else:
                            source = int(source)
                    else:
                        source = _cast_source_to_int(source)
                    source = ctype(source).value     # fix precision
                    return cls(source)
                def __int__(self):
                    return int(self._value)
                def __float__(self):
                    return self._value

            _cast_to_integer = __int__

            if kind == 'int' or kind == 'byte' or kind == 'bool':
                @staticmethod
                def _to_ctypes(x):
                    if not isinstance(x, (int, long)):
                        if isinstance(x, CTypesData):
                            x = int(x)
                        else:
                            raise TypeError("integer expected, got %s" %
                                            type(x).__name__)
                    if ctype(x).value != x:
                        if not is_signed and x < 0:
                            raise OverflowError("%s: negative integer" % name)
                        else:
                            raise OverflowError("%s: integer out of bounds"
                                                % name)
                    return x

            if kind == 'char':
                @staticmethod
                def _to_ctypes(x):
                    if isinstance(x, bytes) and len(x) == 1:
                        return x
                    if isinstance(x, CTypesPrimitive):    # <CData <char>>
                        return x._value
                    raise TypeError("character expected, got %s" %
                                    type(x).__name__)
                def __nonzero__(self):
                    return ord(self._value) != 0
            else:
                def __nonzero__(self):
                    return self._value != 0
            __bool__ = __nonzero__

            if kind == 'float':
                @staticmethod
                def _to_ctypes(x):
                    if not isinstance(x, (int, long, float, CTypesData)):
                        raise TypeError("float expected, got %s" %
                                        type(x).__name__)
                    return ctype(x).value

            @staticmethod
            def _from_ctypes(value):
                return getattr(value, 'value', value)

            @staticmethod
            def _initialize(blob, init):
                blob.value = CTypesPrimitive._to_ctypes(init)

            if kind == 'char':
                def _to_string(self, maxlen):
                    return self._value
            if kind == 'byte':
                def _to_string(self, maxlen):
                    return chr(self._value & 0xff)
        #
        CTypesPrimitive._fix_class()
        return CTypesPrimitive

    def new_pointer_type(self, BItem):
        getbtype = self.ffi._get_cached_btype
        if BItem is getbtype(model.PrimitiveType('char')):
            kind = 'charp'
        elif BItem in (getbtype(model.PrimitiveType('signed char')),
                       getbtype(model.PrimitiveType('unsigned char'))):
            kind = 'bytep'
        elif BItem is getbtype(model.void_type):
            kind = 'voidp'
        else:
            kind = 'generic'
        #
        class CTypesPtr(CTypesGenericPtr):
            __slots__ = ['_own']
            if kind == 'charp':
                __slots__ += ['__as_strbuf']
            _BItem = BItem
            if hasattr(BItem, '_ctype'):
                _ctype = ctypes.POINTER(BItem._ctype)
                _bitem_size = ctypes.sizeof(BItem._ctype)
            else:
                _ctype = ctypes.c_void_p
            if issubclass(BItem, CTypesGenericArray):
                _reftypename = BItem._get_c_name('(* &)')
            else:
                _reftypename = BItem._get_c_name(' * &')

            def __init__(self, init):
                ctypeobj = BItem._create_ctype_obj(init)
                if kind == 'charp':
                    self.__as_strbuf = ctypes.create_string_buffer(
                        ctypeobj.value + b'\x00')
                    self._as_ctype_ptr = ctypes.cast(
                        self.__as_strbuf, self._ctype)
                else:
                    self._as_ctype_ptr = ctypes.pointer(ctypeobj)
                self._address = ctypes.cast(self._as_ctype_ptr,
                                            ctypes.c_void_p).value
                self._own = True

            def __add__(self, other):
                if isinstance(other, (int, long)):
                    return self._new_pointer_at(self._address +
                                                other * self._bitem_size)
                else:
                    return NotImplemented

            def __sub__(self, other):
                if isinstance(other, (int, long)):
                    return self._new_pointer_at(self._address -
                                                other * self._bitem_size)
                elif type(self) is type(other):
                    return (self._address - other._address) // self._bitem_size
                else:
                    return NotImplemented

            def __getitem__(self, index):
                if getattr(self, '_own', False) and index != 0:
                    raise IndexError
                return BItem._from_ctypes(self._as_ctype_ptr[index])

            def __setitem__(self, index, value):
                self._as_ctype_ptr[index] = BItem._to_ctypes(value)

            if kind == 'charp' or kind == 'voidp':
                @classmethod
                def _arg_to_ctypes(cls, *value):
                    if value and isinstance(value[0], bytes):
                        return ctypes.c_char_p(value[0])
                    else:
                        return super(CTypesPtr, cls)._arg_to_ctypes(*value)

            if kind == 'charp' or kind == 'bytep':
                def _to_string(self, maxlen):
                    if maxlen < 0:
                        maxlen = sys.maxsize
                    p = ctypes.cast(self._as_ctype_ptr,
                                    ctypes.POINTER(ctypes.c_char))
                    n = 0
                    while n < maxlen and p[n] != b'\x00':
                        n += 1
                    return b''.join([p[i] for i in range(n)])

            def _get_own_repr(self):
                if getattr(self, '_own', False):
                    return 'owning %d bytes' % (
                        ctypes.sizeof(self._as_ctype_ptr.contents),)
                return super(CTypesPtr, self)._get_own_repr()
        #
        if (BItem is self.ffi._get_cached_btype(model.void_type) or
            BItem is self.ffi._get_cached_btype(model.PrimitiveType('char'))):
            CTypesPtr._automatic_casts = True
        #
        CTypesPtr._fix_class()
        return CTypesPtr

    def new_array_type(self, CTypesPtr, length):
        if length is None:
            brackets = ' &[]'
        else:
            brackets = ' &[%d]' % length
        BItem = CTypesPtr._BItem
        getbtype = self.ffi._get_cached_btype
        if BItem is getbtype(model.PrimitiveType('char')):
            kind = 'char'
        elif BItem in (getbtype(model.PrimitiveType('signed char')),
                       getbtype(model.PrimitiveType('unsigned char'))):
            kind = 'byte'
        else:
            kind = 'generic'
        #
        class CTypesArray(CTypesGenericArray):
            __slots__ = ['_blob', '_own']
            if length is not None:
                _ctype = BItem._ctype * length
            else:
                __slots__.append('_ctype')
            _reftypename = BItem._get_c_name(brackets)
            _declared_length = length
            _CTPtr = CTypesPtr

            def __init__(self, init):
                if length is None:
                    if isinstance(init, (int, long)):
                        len1 = init
                        init = None
                    elif kind == 'char' and isinstance(init, bytes):
                        len1 = len(init) + 1    # extra null
                    else:
                        init = tuple(init)
                        len1 = len(init)
                    self._ctype = BItem._ctype * len1
                self._blob = self._ctype()
                self._own = True
                if init is not None:
                    self._initialize(self._blob, init)

            @staticmethod
            def _initialize(blob, init):
                if isinstance(init, bytes):
                    init = [init[i:i+1] for i in range(len(init))]
                else:
                    if isinstance(init, CTypesGenericArray):
                        if (len(init) != len(blob) or
                            not isinstance(init, CTypesArray)):
                            raise TypeError("length/type mismatch: %s" % (init,))
                    init = tuple(init)
                if len(init) > len(blob):
                    raise IndexError("too many initializers")
                addr = ctypes.cast(blob, ctypes.c_void_p).value
                PTR = ctypes.POINTER(BItem._ctype)
                itemsize = ctypes.sizeof(BItem._ctype)
                for i, value in enumerate(init):
                    p = ctypes.cast(addr + i * itemsize, PTR)
                    BItem._initialize(p.contents, value)

            def __len__(self):
                return len(self._blob)

            def __getitem__(self, index):
                if not (0 <= index < len(self._blob)):
                    raise IndexError
                return BItem._from_ctypes(self._blob[index])

            def __setitem__(self, index, value):
                if not (0 <= index < len(self._blob)):
                    raise IndexError
                self._blob[index] = BItem._to_ctypes(value)

            if kind == 'char' or kind == 'byte':
                def _to_string(self, maxlen):
                    if maxlen < 0:
                        maxlen = len(self._blob)
                    p = ctypes.cast(self._blob,
                                    ctypes.POINTER(ctypes.c_char))
                    n = 0
                    while n < maxlen and p[n] != b'\x00':
                        n += 1
                    return b''.join([p[i] for i in range(n)])

            def _get_own_repr(self):
                if getattr(self, '_own', False):
                    return 'owning %d bytes' % (ctypes.sizeof(self._blob),)
                return super(CTypesArray, self)._get_own_repr()

            def _convert_to_address(self, BClass):
                if BClass in (CTypesPtr, None) or BClass._automatic_casts:
                    return ctypes.addressof(self._blob)
                else:
                    return CTypesData._convert_to_address(self, BClass)

            @staticmethod
            def _from_ctypes(ctypes_array):
                self = CTypesArray.__new__(CTypesArray)
                self._blob = ctypes_array
                return self

            @staticmethod
            def _arg_to_ctypes(value):
                return CTypesPtr._arg_to_ctypes(value)

            def __add__(self, other):
                if isinstance(other, (int, long)):
                    return CTypesPtr._new_pointer_at(
                        ctypes.addressof(self._blob) +
                        other * ctypes.sizeof(BItem._ctype))
                else:
                    return NotImplemented

            @classmethod
            def _cast_from(cls, source):
                raise NotImplementedError("casting to %r" % (
                    cls._get_c_name(),))
        #
        CTypesArray._fix_class()
        return CTypesArray

    def _new_struct_or_union(self, kind, name, base_ctypes_class):
        #
        class struct_or_union(base_ctypes_class):
            pass
        struct_or_union.__name__ = '%s_%s' % (kind, name)
        kind1 = kind
        #
        class CTypesStructOrUnion(CTypesBaseStructOrUnion):
            __slots__ = ['_blob']
            _ctype = struct_or_union
            _reftypename = '%s &' % (name,)
            _kind = kind = kind1
        #
        CTypesStructOrUnion._fix_class()
        return CTypesStructOrUnion

    def new_struct_type(self, name):
        return self._new_struct_or_union('struct', name, ctypes.Structure)

    def new_union_type(self, name):
        return self._new_struct_or_union('union', name, ctypes.Union)

    def complete_struct_or_union(self, CTypesStructOrUnion, fields, tp,
                                 totalsize=-1, totalalignment=-1, sflags=0,
                                 pack=0):
        if totalsize >= 0 or totalalignment >= 0:
            raise NotImplementedError("the ctypes backend of CFFI does not support "
                                      "structures completed by verify(); please "
                                      "compile and install the _cffi_backend module.")
        struct_or_union = CTypesStructOrUnion._ctype
        fnames = [fname for (fname, BField, bitsize) in fields]
        btypes = [BField for (fname, BField, bitsize) in fields]
        bitfields = [bitsize for (fname, BField, bitsize) in fields]
        #
        bfield_types = {}
        cfields = []
        for (fname, BField, bitsize) in fields:
            if bitsize < 0:
                cfields.append((fname, BField._ctype))
                bfield_types[fname] = BField
            else:
                cfields.append((fname, BField._ctype, bitsize))
                bfield_types[fname] = Ellipsis
        if sflags & 8:
            struct_or_union._pack_ = 1
        elif pack:
            struct_or_union._pack_ = pack
        struct_or_union._fields_ = cfields
        CTypesStructOrUnion._bfield_types = bfield_types
        #
        @staticmethod
        def _create_ctype_obj(init):
            result = struct_or_union()
            if init is not None:
                initialize(result, init)
            return result
        CTypesStructOrUnion._create_ctype_obj = _create_ctype_obj
        #
        def initialize(blob, init):
            if is_union:
                if len(init) > 1:
                    raise ValueError("union initializer: %d items given, but "
                                    "only one supported (use a dict if needed)"
                                     % (len(init),))
            if not isinstance(init, dict):
                if isinstance(init, (bytes, unicode)):
                    raise TypeError("union initializer: got a str")
                init = tuple(init)
                if len(init) > len(fnames):
                    raise ValueError("too many values for %s initializer" %
                                     CTypesStructOrUnion._get_c_name())
                init = dict(zip(fnames, init))
            addr = ctypes.addressof(blob)
            for fname, value in init.items():
                BField, bitsize = name2fieldtype[fname]
                assert bitsize < 0, \
                       "not implemented: initializer with bit fields"
                offset = CTypesStructOrUnion._offsetof(fname)
                PTR = ctypes.POINTER(BField._ctype)
                p = ctypes.cast(addr + offset, PTR)
                BField._initialize(p.contents, value)
        is_union = CTypesStructOrUnion._kind == 'union'
        name2fieldtype = dict(zip(fnames, zip(btypes, bitfields)))
        #
        for fname, BField, bitsize in fields:
            if fname == '':
                raise NotImplementedError("nested anonymous structs/unions")
            if hasattr(CTypesStructOrUnion, fname):
                raise ValueError("the field name %r conflicts in "
                                 "the ctypes backend" % fname)
            if bitsize < 0:
                def getter(self, fname=fname, BField=BField,
                           offset=CTypesStructOrUnion._offsetof(fname),
                           PTR=ctypes.POINTER(BField._ctype)):
                    addr = ctypes.addressof(self._blob)
                    p = ctypes.cast(addr + offset, PTR)
                    return BField._from_ctypes(p.contents)
                def setter(self, value, fname=fname, BField=BField):
                    setattr(self._blob, fname, BField._to_ctypes(value))
                #
                if issubclass(BField, CTypesGenericArray):
                    setter = None
                    if BField._declared_length == 0:
                        def getter(self, fname=fname, BFieldPtr=BField._CTPtr,
                                   offset=CTypesStructOrUnion._offsetof(fname),
                                   PTR=ctypes.POINTER(BField._ctype)):
                            addr = ctypes.addressof(self._blob)
                            p = ctypes.cast(addr + offset, PTR)
                            return BFieldPtr._from_ctypes(p)
                #
            else:
                def getter(self, fname=fname, BField=BField):
                    return BField._from_ctypes(getattr(self._blob, fname))
                def setter(self, value, fname=fname, BField=BField):
                    # xxx obscure workaround
                    value = BField._to_ctypes(value)
                    oldvalue = getattr(self._blob, fname)
                    setattr(self._blob, fname, value)
                    if value != getattr(self._blob, fname):
                        setattr(self._blob, fname, oldvalue)
                        raise OverflowError("value too large for bitfield")
            setattr(CTypesStructOrUnion, fname, property(getter, setter))
        #
        CTypesPtr = self.ffi._get_cached_btype(model.PointerType(tp))
        for fname in fnames:
            if hasattr(CTypesPtr, fname):
                raise ValueError("the field name %r conflicts in "
                                 "the ctypes backend" % fname)
            def getter(self, fname=fname):
                return getattr(self[0], fname)
            def setter(self, value, fname=fname):
                setattr(self[0], fname, value)
            setattr(CTypesPtr, fname, property(getter, setter))

    def new_function_type(self, BArgs, BResult, has_varargs):
        nameargs = [BArg._get_c_name() for BArg in BArgs]
        if has_varargs:
            nameargs.append('...')
        nameargs = ', '.join(nameargs)
        #
        class CTypesFunctionPtr(CTypesGenericPtr):
            __slots__ = ['_own_callback', '_name']
            _ctype = ctypes.CFUNCTYPE(getattr(BResult, '_ctype', None),
                                      *[BArg._ctype for BArg in BArgs],
                                      use_errno=True)
            _reftypename = BResult._get_c_name('(* &)(%s)' % (nameargs,))

            def __init__(self, init, error=None):
                # create a callback to the Python callable init()
                import traceback
                assert not has_varargs, "varargs not supported for callbacks"
                if getattr(BResult, '_ctype', None) is not None:
                    error = BResult._from_ctypes(
                        BResult._create_ctype_obj(error))
                else:
                    error = None
                def callback(*args):
                    args2 = []
                    for arg, BArg in zip(args, BArgs):
                        args2.append(BArg._from_ctypes(arg))
                    try:
                        res2 = init(*args2)
                        res2 = BResult._to_ctypes(res2)
                    except:
                        traceback.print_exc()
                        res2 = error
                    if issubclass(BResult, CTypesGenericPtr):
                        if res2:
                            res2 = ctypes.cast(res2, ctypes.c_void_p).value
                                # .value: http://bugs.python.org/issue1574593
                        else:
                            res2 = None
                    #print repr(res2)
                    return res2
                if issubclass(BResult, CTypesGenericPtr):
                    # The only pointers callbacks can return are void*s:
                    # http://bugs.python.org/issue5710
                    callback_ctype = ctypes.CFUNCTYPE(
                        ctypes.c_void_p,
                        *[BArg._ctype for BArg in BArgs],
                        use_errno=True)
                else:
                    callback_ctype = CTypesFunctionPtr._ctype
                self._as_ctype_ptr = callback_ctype(callback)
                self._address = ctypes.cast(self._as_ctype_ptr,
                                            ctypes.c_void_p).value
                self._own_callback = init

            @staticmethod
            def _initialize(ctypes_ptr, value):
                if value:
                    raise NotImplementedError("ctypes backend: not supported: "
                                          "initializers for function pointers")

            def __repr__(self):
                c_name = getattr(self, '_name', None)
                if c_name:
                    i = self._reftypename.index('(* &)')
                    if self._reftypename[i-1] not in ' )*':
                        c_name = ' ' + c_name
                    c_name = self._reftypename.replace('(* &)', c_name)
                return CTypesData.__repr__(self, c_name)

            def _get_own_repr(self):
                if getattr(self, '_own_callback', None) is not None:
                    return 'calling %r' % (self._own_callback,)
                return super(CTypesFunctionPtr, self)._get_own_repr()

            def __call__(self, *args):
                if has_varargs:
                    assert len(args) >= len(BArgs)
                    extraargs = args[len(BArgs):]
                    args = args[:len(BArgs)]
                else:
                    assert len(args) == len(BArgs)
                ctypes_args = []
                for arg, BArg in zip(args, BArgs):
                    ctypes_args.append(BArg._arg_to_ctypes(arg))
                if has_varargs:
                    for i, arg in enumerate(extraargs):
                        if arg is None:
                            ctypes_args.append(ctypes.c_void_p(0))  # NULL
                            continue
                        if not isinstance(arg, CTypesData):
                            raise TypeError(
                                "argument %d passed in the variadic part "
                                "needs to be a cdata object (got %s)" %
                                (1 + len(BArgs) + i, type(arg).__name__))
                        ctypes_args.append(arg._arg_to_ctypes(arg))
                result = self._as_ctype_ptr(*ctypes_args)
                return BResult._from_ctypes(result)
        #
        CTypesFunctionPtr._fix_class()
        return CTypesFunctionPtr

    def new_enum_type(self, name, enumerators, enumvalues, CTypesInt):
        assert isinstance(name, str)
        reverse_mapping = dict(zip(reversed(enumvalues),
                                   reversed(enumerators)))
        #
        class CTypesEnum(CTypesInt):
            __slots__ = []
            _reftypename = '%s &' % name

            def _get_own_repr(self):
                value = self._value
                try:
                    return '%d: %s' % (value, reverse_mapping[value])
                except KeyError:
                    return str(value)

            def _to_string(self, maxlen):
                value = self._value
                try:
                    return reverse_mapping[value]
                except KeyError:
                    return str(value)
        #
        CTypesEnum._fix_class()
        return CTypesEnum

    def get_errno(self):
        return ctypes.get_errno()

    def set_errno(self, value):
        ctypes.set_errno(value)

    def string(self, b, maxlen=-1):
        return b._to_string(maxlen)

    def buffer(self, bptr, size=-1):
        raise NotImplementedError("buffer() with ctypes backend")

    def sizeof(self, cdata_or_BType):
        if isinstance(cdata_or_BType, CTypesData):
            return cdata_or_BType._get_size_of_instance()
        else:
            assert issubclass(cdata_or_BType, CTypesData)
            return cdata_or_BType._get_size()

    def alignof(self, BType):
        assert issubclass(BType, CTypesData)
        return BType._alignment()

    def newp(self, BType, source):
        if not issubclass(BType, CTypesData):
            raise TypeError
        return BType._newp(source)

    def cast(self, BType, source):
        return BType._cast_from(source)

    def callback(self, BType, source, error, onerror):
        assert onerror is None   # XXX not implemented
        return BType(source, error)

    _weakref_cache_ref = None

    def gcp(self, cdata, destructor, size=0):
        if self._weakref_cache_ref is None:
            import weakref
            class MyRef(weakref.ref):
                def __eq__(self, other):
                    myref = self()
                    return self is other or (
                        myref is not None and myref is other())
                def __ne__(self, other):
                    return not (self == other)
                def __hash__(self):
                    try:
                        return self._hash
                    except AttributeError:
                        self._hash = hash(self())
                        return self._hash
            self._weakref_cache_ref = {}, MyRef
        weak_cache, MyRef = self._weakref_cache_ref

        if destructor is None:
            try:
                del weak_cache[MyRef(cdata)]
            except KeyError:
                raise TypeError("Can remove destructor only on a object "
                                "previously returned by ffi.gc()")
            return None

        def remove(k):
            cdata, destructor = weak_cache.pop(k, (None, None))
            if destructor is not None:
                destructor(cdata)

        new_cdata = self.cast(self.typeof(cdata), cdata)
        assert new_cdata is not cdata
        weak_cache[MyRef(new_cdata, remove)] = (cdata, destructor)
        return new_cdata

    typeof = type

    def getcname(self, BType, replace_with):
        return BType._get_c_name(replace_with)

    def typeoffsetof(self, BType, fieldname, num=0):
        if isinstance(fieldname, str):
            if num == 0 and issubclass(BType, CTypesGenericPtr):
                BType = BType._BItem
            if not issubclass(BType, CTypesBaseStructOrUnion):
                raise TypeError("expected a struct or union ctype")
            BField = BType._bfield_types[fieldname]
            if BField is Ellipsis:
                raise TypeError("not supported for bitfields")
            return (BField, BType._offsetof(fieldname))
        elif isinstance(fieldname, (int, long)):
            if issubclass(BType, CTypesGenericArray):
                BType = BType._CTPtr
            if not issubclass(BType, CTypesGenericPtr):
                raise TypeError("expected an array or ptr ctype")
            BItem = BType._BItem
            offset = BItem._get_size() * fieldname
            if offset > sys.maxsize:
                raise OverflowError
            return (BItem, offset)
        else:
            raise TypeError(type(fieldname))

    def rawaddressof(self, BTypePtr, cdata, offset=None):
        if isinstance(cdata, CTypesBaseStructOrUnion):
            ptr = ctypes.pointer(type(cdata)._to_ctypes(cdata))
        elif isinstance(cdata, CTypesGenericPtr):
            if offset is None or not issubclass(type(cdata)._BItem,
                                                CTypesBaseStructOrUnion):
                raise TypeError("unexpected cdata type")
            ptr = type(cdata)._to_ctypes(cdata)
        elif isinstance(cdata, CTypesGenericArray):
            ptr = type(cdata)._to_ctypes(cdata)
        else:
            raise TypeError("expected a <cdata 'struct-or-union'>")
        if offset:
            ptr = ctypes.cast(
                ctypes.c_void_p(
                    ctypes.cast(ptr, ctypes.c_void_p).value + offset),
                type(ptr))
        return BTypePtr._from_ctypes(ptr)


class CTypesLibrary(object):

    def __init__(self, backend, cdll):
        self.backend = backend
        self.cdll = cdll

    def load_function(self, BType, name):
        c_func = getattr(self.cdll, name)
        funcobj = BType._from_ctypes(c_func)
        funcobj._name = name
        return funcobj

    def read_variable(self, BType, name):
        try:
            ctypes_obj = BType._ctype.in_dll(self.cdll, name)
        except AttributeError as e:
            raise NotImplementedError(e)
        return BType._from_ctypes(ctypes_obj)

    def write_variable(self, BType, name, value):
        new_ctypes_obj = BType._to_ctypes(value)
        ctypes_obj = BType._ctype.in_dll(self.cdll, name)
        ctypes.memmove(ctypes.addressof(ctypes_obj),
                       ctypes.addressof(new_ctypes_obj),
                       ctypes.sizeof(BType._ctype))

# === NexusCore/openenv\Lib\site-packages\setuptools\dist.py ===
from __future__ import annotations

import functools
import io
import itertools
import numbers
import os
import re
import sys
from collections.abc import Iterable, Iterator, MutableMapping, Sequence
from glob import glob
from pathlib import Path
from typing import TYPE_CHECKING, Any, Union

from more_itertools import partition, unique_everseen
from packaging.markers import InvalidMarker, Marker
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import Version

from . import (
    _entry_points,
    _reqs,
    _static,
    command as _,  # noqa: F401 # imported for side-effects
)
from ._importlib import metadata
from ._normalization import _canonicalize_license_expression
from ._path import StrPath
from ._reqs import _StrOrIter
from .config import pyprojecttoml, setupcfg
from .discovery import ConfigDiscovery
from .errors import InvalidConfigError
from .monkey import get_unpatched
from .warnings import InformationOnly, SetuptoolsDeprecationWarning

import distutils.cmd
import distutils.command
import distutils.core
import distutils.dist
import distutils.log
from distutils.debug import DEBUG
from distutils.errors import DistutilsOptionError, DistutilsSetupError
from distutils.fancy_getopt import translate_longopt
from distutils.util import strtobool

if TYPE_CHECKING:
    from typing_extensions import TypeAlias


__all__ = ['Distribution']

_sequence = tuple, list
"""
:meta private:

Supported iterable types that are known to be:
- ordered (which `set` isn't)
- not match a str (which `Sequence[str]` does)
- not imply a nested type (like `dict`)
for use with `isinstance`.
"""
_Sequence: TypeAlias = Union[tuple[str, ...], list[str]]
# This is how stringifying _Sequence would look in Python 3.10
_sequence_type_repr = "tuple[str, ...] | list[str]"
_OrderedStrSequence: TypeAlias = Union[str, dict[str, Any], Sequence[str]]
"""
:meta private:
Avoid single-use iterable. Disallow sets.
A poor approximation of an OrderedSequence (dict doesn't match a Sequence).
"""


def __getattr__(name: str) -> Any:  # pragma: no cover
    if name == "sequence":
        SetuptoolsDeprecationWarning.emit(
            "`setuptools.dist.sequence` is an internal implementation detail.",
            "Please define your own `sequence = tuple, list` instead.",
            due_date=(2025, 8, 28),  # Originally added on 2024-08-27
        )
        return _sequence
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def check_importable(dist, attr, value):
    try:
        ep = metadata.EntryPoint(value=value, name=None, group=None)
        assert not ep.extras
    except (TypeError, ValueError, AttributeError, AssertionError) as e:
        raise DistutilsSetupError(
            f"{attr!r} must be importable 'module:attrs' string (got {value!r})"
        ) from e


def assert_string_list(dist, attr: str, value: _Sequence) -> None:
    """Verify that value is a string list"""
    try:
        # verify that value is a list or tuple to exclude unordered
        # or single-use iterables
        assert isinstance(value, _sequence)
        # verify that elements of value are strings
        assert ''.join(value) != value
    except (TypeError, ValueError, AttributeError, AssertionError) as e:
        raise DistutilsSetupError(
            f"{attr!r} must be of type <{_sequence_type_repr}> (got {value!r})"
        ) from e


def check_nsp(dist, attr, value):
    """Verify that namespace packages are valid"""
    ns_packages = value
    assert_string_list(dist, attr, ns_packages)
    for nsp in ns_packages:
        if not dist.has_contents_for(nsp):
            raise DistutilsSetupError(
                f"Distribution contains no modules or packages for namespace package {nsp!r}"
            )
        parent, _sep, _child = nsp.rpartition('.')
        if parent and parent not in ns_packages:
            distutils.log.warn(
                "WARNING: %r is declared as a package namespace, but %r"
                " is not: please correct this in setup.py",
                nsp,
                parent,
            )
        SetuptoolsDeprecationWarning.emit(
            "The namespace_packages parameter is deprecated.",
            "Please replace its usage with implicit namespaces (PEP 420).",
            see_docs="references/keywords.html#keyword-namespace-packages",
            # TODO: define due_date, it may break old packages that are no longer
            # maintained (e.g. sphinxcontrib extensions) when installed from source.
            # Warning officially introduced in May 2022, however the deprecation
            # was mentioned much earlier in the docs (May 2020, see #2149).
        )


def check_extras(dist, attr, value):
    """Verify that extras_require mapping is valid"""
    try:
        list(itertools.starmap(_check_extra, value.items()))
    except (TypeError, ValueError, AttributeError) as e:
        raise DistutilsSetupError(
            "'extras_require' must be a dictionary whose values are "
            "strings or lists of strings containing valid project/version "
            "requirement specifiers."
        ) from e


def _check_extra(extra, reqs):
    _name, _sep, marker = extra.partition(':')
    try:
        _check_marker(marker)
    except InvalidMarker:
        msg = f"Invalid environment marker: {marker} ({extra!r})"
        raise DistutilsSetupError(msg) from None
    list(_reqs.parse(reqs))


def _check_marker(marker):
    if not marker:
        return
    m = Marker(marker)
    m.evaluate()


def assert_bool(dist, attr, value):
    """Verify that value is True, False, 0, or 1"""
    if bool(value) != value:
        raise DistutilsSetupError(f"{attr!r} must be a boolean value (got {value!r})")


def invalid_unless_false(dist, attr, value):
    if not value:
        DistDeprecationWarning.emit(f"{attr} is ignored.")
        # TODO: should there be a `due_date` here?
        return
    raise DistutilsSetupError(f"{attr} is invalid.")


def check_requirements(dist, attr: str, value: _OrderedStrSequence) -> None:
    """Verify that install_requires is a valid requirements list"""
    try:
        list(_reqs.parse(value))
        if isinstance(value, set):
            raise TypeError("Unordered types are not allowed")
    except (TypeError, ValueError) as error:
        msg = (
            f"{attr!r} must be a string or iterable of strings "
            f"containing valid project/version requirement specifiers; {error}"
        )
        raise DistutilsSetupError(msg) from error


def check_specifier(dist, attr, value):
    """Verify that value is a valid version specifier"""
    try:
        SpecifierSet(value)
    except (InvalidSpecifier, AttributeError) as error:
        msg = f"{attr!r} must be a string containing valid version specifiers; {error}"
        raise DistutilsSetupError(msg) from error


def check_entry_points(dist, attr, value):
    """Verify that entry_points map is parseable"""
    try:
        _entry_points.load(value)
    except Exception as e:
        raise DistutilsSetupError(e) from e


def check_package_data(dist, attr, value):
    """Verify that value is a dictionary of package names to glob lists"""
    if not isinstance(value, dict):
        raise DistutilsSetupError(
            f"{attr!r} must be a dictionary mapping package names to lists of "
            "string wildcard patterns"
        )
    for k, v in value.items():
        if not isinstance(k, str):
            raise DistutilsSetupError(
                f"keys of {attr!r} dict must be strings (got {k!r})"
            )
        assert_string_list(dist, f'values of {attr!r} dict', v)


def check_packages(dist, attr, value):
    for pkgname in value:
        if not re.match(r'\w+(\.\w+)*', pkgname):
            distutils.log.warn(
                "WARNING: %r not a valid package name; please use only "
                ".-separated package names in setup.py",
                pkgname,
            )


if TYPE_CHECKING:
    # Work around a mypy issue where type[T] can't be used as a base: https://github.com/python/mypy/issues/10962
    from distutils.core import Distribution as _Distribution
else:
    _Distribution = get_unpatched(distutils.core.Distribution)


class Distribution(_Distribution):
    """Distribution with support for tests and package data

    This is an enhanced version of 'distutils.dist.Distribution' that
    effectively adds the following new optional keyword arguments to 'setup()':

     'install_requires' -- a string or sequence of strings specifying project
        versions that the distribution requires when installed, in the format
        used by 'pkg_resources.require()'.  They will be installed
        automatically when the package is installed.  If you wish to use
        packages that are not available in PyPI, or want to give your users an
        alternate download location, you can add a 'find_links' option to the
        '[easy_install]' section of your project's 'setup.cfg' file, and then
        setuptools will scan the listed web pages for links that satisfy the
        requirements.

     'extras_require' -- a dictionary mapping names of optional "extras" to the
        additional requirement(s) that using those extras incurs. For example,
        this::

            extras_require = dict(reST = ["docutils>=0.3", "reSTedit"])

        indicates that the distribution can optionally provide an extra
        capability called "reST", but it can only be used if docutils and
        reSTedit are installed.  If the user installs your package using
        EasyInstall and requests one of your extras, the corresponding
        additional requirements will be installed if needed.

     'package_data' -- a dictionary mapping package names to lists of filenames
        or globs to use to find data files contained in the named packages.
        If the dictionary has filenames or globs listed under '""' (the empty
        string), those names will be searched for in every package, in addition
        to any names for the specific package.  Data files found using these
        names/globs will be installed along with the package, in the same
        location as the package.  Note that globs are allowed to reference
        the contents of non-package subdirectories, as long as you use '/' as
        a path separator.  (Globs are automatically converted to
        platform-specific paths at runtime.)

    In addition to these new keywords, this class also has several new methods
    for manipulating the distribution's contents.  For example, the 'include()'
    and 'exclude()' methods can be thought of as in-place add and subtract
    commands that add or remove packages, modules, extensions, and so on from
    the distribution.
    """

    _DISTUTILS_UNSUPPORTED_METADATA = {
        'long_description_content_type': lambda: None,
        'project_urls': dict,
        'provides_extras': dict,  # behaves like an ordered set
        'license_expression': lambda: None,
        'license_file': lambda: None,
        'license_files': lambda: None,
        'install_requires': list,
        'extras_require': dict,
    }

    # Used by build_py, editable_wheel and install_lib commands for legacy namespaces
    namespace_packages: list[str]  #: :meta private: DEPRECATED

    # Any: Dynamic assignment results in Incompatible types in assignment
    def __init__(self, attrs: MutableMapping[str, Any] | None = None) -> None:
        have_package_data = hasattr(self, "package_data")
        if not have_package_data:
            self.package_data: dict[str, list[str]] = {}
        attrs = attrs or {}
        self.dist_files: list[tuple[str, str, str]] = []
        self.include_package_data: bool | None = None
        self.exclude_package_data: dict[str, list[str]] | None = None
        # Filter-out setuptools' specific options.
        self.src_root: str | None = attrs.pop("src_root", None)
        self.dependency_links: list[str] = attrs.pop('dependency_links', [])
        self.setup_requires: list[str] = attrs.pop('setup_requires', [])
        for ep in metadata.entry_points(group='distutils.setup_keywords'):
            vars(self).setdefault(ep.name, None)

        metadata_only = set(self._DISTUTILS_UNSUPPORTED_METADATA)
        metadata_only -= {"install_requires", "extras_require"}
        dist_attrs = {k: v for k, v in attrs.items() if k not in metadata_only}
        _Distribution.__init__(self, dist_attrs)

        # Private API (setuptools-use only, not restricted to Distribution)
        # Stores files that are referenced by the configuration and need to be in the
        # sdist (e.g. `version = file: VERSION.txt`)
        self._referenced_files = set[str]()

        self.set_defaults = ConfigDiscovery(self)

        self._set_metadata_defaults(attrs)

        self.metadata.version = self._normalize_version(self.metadata.version)
        self._finalize_requires()

    def _validate_metadata(self):
        required = {"name"}
        provided = {
            key
            for key in vars(self.metadata)
            if getattr(self.metadata, key, None) is not None
        }
        missing = required - provided

        if missing:
            msg = f"Required package metadata is missing: {missing}"
            raise DistutilsSetupError(msg)

    def _set_metadata_defaults(self, attrs):
        """
        Fill-in missing metadata fields not supported by distutils.
        Some fields may have been set by other tools (e.g. pbr).
        Those fields (vars(self.metadata)) take precedence to
        supplied attrs.
        """
        for option, default in self._DISTUTILS_UNSUPPORTED_METADATA.items():
            vars(self.metadata).setdefault(option, attrs.get(option, default()))

    @staticmethod
    def _normalize_version(version):
        from . import sic

        if isinstance(version, numbers.Number):
            # Some people apparently take "version number" too literally :)
            version = str(version)
        elif isinstance(version, sic) or version is None:
            return version

        normalized = str(Version(version))
        if version != normalized:
            InformationOnly.emit(f"Normalizing '{version}' to '{normalized}'")
            return normalized
        return version

    def _finalize_requires(self):
        """
        Set `metadata.python_requires` and fix environment markers
        in `install_requires` and `extras_require`.
        """
        if getattr(self, 'python_requires', None):
            self.metadata.python_requires = self.python_requires

        self._normalize_requires()
        self.metadata.install_requires = self.install_requires
        self.metadata.extras_require = self.extras_require

        if self.extras_require:
            for extra in self.extras_require.keys():
                # Setuptools allows a weird "<name>:<env markers> syntax for extras
                extra = extra.split(':')[0]
                if extra:
                    self.metadata.provides_extras.setdefault(extra)

    def _normalize_requires(self):
        """Make sure requirement-related attributes exist and are normalized"""
        install_requires = getattr(self, "install_requires", None) or []
        extras_require = getattr(self, "extras_require", None) or {}

        # Preserve the "static"-ness of values parsed from config files
        list_ = _static.List if _static.is_static(install_requires) else list
        self.install_requires = list_(map(str, _reqs.parse(install_requires)))

        dict_ = _static.Dict if _static.is_static(extras_require) else dict
        self.extras_require = dict_(
            (k, list(map(str, _reqs.parse(v or [])))) for k, v in extras_require.items()
        )

    def _finalize_license_expression(self) -> None:
        """
        Normalize license and license_expression.
        >>> dist = Distribution({"license_expression": _static.Str("mit aNd  gpl-3.0-OR-later")})
        >>> _static.is_static(dist.metadata.license_expression)
        True
        >>> dist._finalize_license_expression()
        >>> _static.is_static(dist.metadata.license_expression)  # preserve "static-ness"
        True
        >>> print(dist.metadata.license_expression)
        MIT AND GPL-3.0-or-later
        """
        classifiers = self.metadata.get_classifiers()
        license_classifiers = [cl for cl in classifiers if cl.startswith("License :: ")]

        license_expr = self.metadata.license_expression
        if license_expr:
            str_ = _static.Str if _static.is_static(license_expr) else str
            normalized = str_(_canonicalize_license_expression(license_expr))
            if license_expr != normalized:
                InformationOnly.emit(f"Normalizing '{license_expr}' to '{normalized}'")
                self.metadata.license_expression = normalized
            if license_classifiers:
                raise InvalidConfigError(
                    "License classifiers have been superseded by license expressions "
                    "(see https://peps.python.org/pep-0639/). Please remove:\n\n"
                    + "\n".join(license_classifiers),
                )
        elif license_classifiers:
            pypa_guides = "guides/writing-pyproject-toml/#license"
            SetuptoolsDeprecationWarning.emit(
                "License classifiers are deprecated.",
                "Please consider removing the following classifiers in favor of a "
                "SPDX license expression:\n\n" + "\n".join(license_classifiers),
                see_url=f"https://packaging.python.org/en/latest/{pypa_guides}",
                # Warning introduced on 2025-02-17
                # TODO: Should we add a due date? It may affect old/unmaintained
                #       packages in the ecosystem and cause problems...
            )

    def _finalize_license_files(self) -> None:
        """Compute names of all license files which should be included."""
        license_files: list[str] | None = self.metadata.license_files
        patterns = license_files or []

        license_file: str | None = self.metadata.license_file
        if license_file and license_file not in patterns:
            patterns.append(license_file)

        if license_files is None and license_file is None:
            # Default patterns match the ones wheel uses
            # See https://wheel.readthedocs.io/en/stable/user_guide.html
            # -> 'Including license files in the generated wheel file'
            patterns = ['LICEN[CS]E*', 'COPYING*', 'NOTICE*', 'AUTHORS*']
            files = self._expand_patterns(patterns, enforce_match=False)
        else:  # Patterns explicitly given by the user
            files = self._expand_patterns(patterns, enforce_match=True)

        self.metadata.license_files = list(unique_everseen(files))

    @classmethod
    def _expand_patterns(
        cls, patterns: list[str], enforce_match: bool = True
    ) -> Iterator[str]:
        """
        >>> getfixture('sample_project_cwd')
        >>> list(Distribution._expand_patterns(['LICENSE.txt']))
        ['LICENSE.txt']
        >>> list(Distribution._expand_patterns(['pyproject.toml', 'LIC*']))
        ['pyproject.toml', 'LICENSE.txt']
        >>> list(Distribution._expand_patterns(['src/**/*.dat']))
        ['src/sample/package_data.dat']
        """
        return (
            path.replace(os.sep, "/")
            for pattern in patterns
            for path in sorted(cls._find_pattern(pattern, enforce_match))
            if not path.endswith('~') and os.path.isfile(path)
        )

    @staticmethod
    def _find_pattern(pattern: str, enforce_match: bool = True) -> list[str]:
        r"""
        >>> getfixture('sample_project_cwd')
        >>> Distribution._find_pattern("LICENSE.txt")
        ['LICENSE.txt']
        >>> Distribution._find_pattern("/LICENSE.MIT")
        Traceback (most recent call last):
        ...
        setuptools.errors.InvalidConfigError: Pattern '/LICENSE.MIT' should be relative...
        >>> Distribution._find_pattern("../LICENSE.MIT")
        Traceback (most recent call last):
        ...
        setuptools.warnings.SetuptoolsDeprecationWarning: ...Pattern '../LICENSE.MIT' cannot contain '..'...
        >>> Distribution._find_pattern("LICEN{CSE*")
        Traceback (most recent call last):
        ...
        setuptools.warnings.SetuptoolsDeprecationWarning: ...Pattern 'LICEN{CSE*' contains invalid characters...
        """
        pypa_guides = "specifications/glob-patterns/"
        if ".." in pattern:
            SetuptoolsDeprecationWarning.emit(
                f"Pattern {pattern!r} cannot contain '..'",
                """
                Please ensure the files specified are contained by the root
                of the Python package (normally marked by `pyproject.toml`).
                """,
                see_url=f"https://packaging.python.org/en/latest/{pypa_guides}",
                due_date=(2026, 3, 20),  # Introduced in 2025-03-20
                # Replace with InvalidConfigError after deprecation
            )
        if pattern.startswith((os.sep, "/")) or ":\\" in pattern:
            raise InvalidConfigError(
                f"Pattern {pattern!r} should be relative and must not start with '/'"
            )
        if re.match(r'^[\w\-\.\/\*\?\[\]]+$', pattern) is None:
            SetuptoolsDeprecationWarning.emit(
                "Please provide a valid glob pattern.",
                "Pattern {pattern!r} contains invalid characters.",
                pattern=pattern,
                see_url=f"https://packaging.python.org/en/latest/{pypa_guides}",
                due_date=(2026, 3, 20),  # Introduced in 2025-02-20
            )

        found = glob(pattern, recursive=True)

        if enforce_match and not found:
            SetuptoolsDeprecationWarning.emit(
                "Cannot find any files for the given pattern.",
                "Pattern {pattern!r} did not match any files.",
                pattern=pattern,
                due_date=(2026, 3, 20),  # Introduced in 2025-02-20
                # PEP 639 requires us to error, but as a transition period
                # we will only issue a warning to give people time to prepare.
                # After the transition, this should raise an InvalidConfigError.
            )
        return found

    # FIXME: 'Distribution._parse_config_files' is too complex (14)
    def _parse_config_files(self, filenames=None):  # noqa: C901
        """
        Adapted from distutils.dist.Distribution.parse_config_files,
        this method provides the same functionality in subtly-improved
        ways.
        """
        from configparser import ConfigParser

        # Ignore install directory options if we have a venv
        ignore_options = (
            []
            if sys.prefix == sys.base_prefix
            else [
                'install-base',
                'install-platbase',
                'install-lib',
                'install-platlib',
                'install-purelib',
                'install-headers',
                'install-scripts',
                'install-data',
                'prefix',
                'exec-prefix',
                'home',
                'user',
                'root',
            ]
        )

        ignore_options = frozenset(ignore_options)

        if filenames is None:
            filenames = self.find_config_files()

        if DEBUG:
            self.announce("Distribution.parse_config_files():")

        parser = ConfigParser()
        parser.optionxform = str
        for filename in filenames:
            with open(filename, encoding='utf-8') as reader:
                if DEBUG:
                    self.announce("  reading {filename}".format(**locals()))
                parser.read_file(reader)
            for section in parser.sections():
                options = parser.options(section)
                opt_dict = self.get_option_dict(section)

                for opt in options:
                    if opt == '__name__' or opt in ignore_options:
                        continue

                    val = parser.get(section, opt)
                    opt = self._enforce_underscore(opt, section)
                    opt = self._enforce_option_lowercase(opt, section)
                    opt_dict[opt] = (filename, val)

            # Make the ConfigParser forget everything (so we retain
            # the original filenames that options come from)
            parser.__init__()

        if 'global' not in self.command_options:
            return

        # If there was a "global" section in the config file, use it
        # to set Distribution options.

        for opt, (src, val) in self.command_options['global'].items():
            alias = self.negative_opt.get(opt)
            if alias:
                val = not strtobool(val)
            elif opt in ('verbose', 'dry_run'):  # ugh!
                val = strtobool(val)

            try:
                setattr(self, alias or opt, val)
            except ValueError as e:
                raise DistutilsOptionError(e) from e

    def _enforce_underscore(self, opt: str, section: str) -> str:
        if "-" not in opt or self._skip_setupcfg_normalization(section):
            return opt

        underscore_opt = opt.replace('-', '_')
        affected = f"(Affected: {self.metadata.name})." if self.metadata.name else ""
        SetuptoolsDeprecationWarning.emit(
            f"Invalid dash-separated key {opt!r} in {section!r} (setup.cfg), "
            f"please use the underscore name {underscore_opt!r} instead.",
            f"""
            Usage of dash-separated {opt!r} will not be supported in future
            versions. Please use the underscore name {underscore_opt!r} instead.
            {affected}
            """,
            see_docs="userguide/declarative_config.html",
            due_date=(2026, 3, 3),
            # Warning initially introduced in 3 Mar 2021
        )
        return underscore_opt

    def _enforce_option_lowercase(self, opt: str, section: str) -> str:
        if opt.islower() or self._skip_setupcfg_normalization(section):
            return opt

        lowercase_opt = opt.lower()
        affected = f"(Affected: {self.metadata.name})." if self.metadata.name else ""
        SetuptoolsDeprecationWarning.emit(
            f"Invalid uppercase key {opt!r} in {section!r} (setup.cfg), "
            f"please use lowercase {lowercase_opt!r} instead.",
            f"""
            Usage of uppercase key {opt!r} in {section!r} will not be supported in
            future versions. Please use lowercase {lowercase_opt!r} instead.
            {affected}
            """,
            see_docs="userguide/declarative_config.html",
            due_date=(2026, 3, 3),
            # Warning initially introduced in 6 Mar 2021
        )
        return lowercase_opt

    def _skip_setupcfg_normalization(self, section: str) -> bool:
        skip = (
            'options.extras_require',
            'options.data_files',
            'options.entry_points',
            'options.package_data',
            'options.exclude_package_data',
        )
        return section in skip or not self._is_setuptools_section(section)

    def _is_setuptools_section(self, section: str) -> bool:
        return (
            section == "metadata"
            or section.startswith("options")
            or section in _setuptools_commands()
        )

    # FIXME: 'Distribution._set_command_options' is too complex (14)
    def _set_command_options(self, command_obj, option_dict=None):  # noqa: C901
        """
        Set the options for 'command_obj' from 'option_dict'.  Basically
        this means copying elements of a dictionary ('option_dict') to
        attributes of an instance ('command').

        'command_obj' must be a Command instance.  If 'option_dict' is not
        supplied, uses the standard option dictionary for this command
        (from 'self.command_options').

        (Adopted from distutils.dist.Distribution._set_command_options)
        """
        command_name = command_obj.get_command_name()
        if option_dict is None:
            option_dict = self.get_option_dict(command_name)

        if DEBUG:
            self.announce(f"  setting options for '{command_name}' command:")
        for option, (source, value) in option_dict.items():
            if DEBUG:
                self.announce(f"    {option} = {value} (from {source})")
            try:
                bool_opts = [translate_longopt(o) for o in command_obj.boolean_options]
            except AttributeError:
                bool_opts = []
            try:
                neg_opt = command_obj.negative_opt
            except AttributeError:
                neg_opt = {}

            try:
                is_string = isinstance(value, str)
                if option in neg_opt and is_string:
                    setattr(command_obj, neg_opt[option], not strtobool(value))
                elif option in bool_opts and is_string:
                    setattr(command_obj, option, strtobool(value))
                elif hasattr(command_obj, option):
                    setattr(command_obj, option, value)
                else:
                    raise DistutilsOptionError(
                        f"error in {source}: command '{command_name}' has no such option '{option}'"
                    )
            except ValueError as e:
                raise DistutilsOptionError(e) from e

    def _get_project_config_files(self, filenames: Iterable[StrPath] | None):
        """Add default file and split between INI and TOML"""
        tomlfiles = []
        standard_project_metadata = Path(self.src_root or os.curdir, "pyproject.toml")
        if filenames is not None:
            parts = partition(lambda f: Path(f).suffix == ".toml", filenames)
            filenames = list(parts[0])  # 1st element => predicate is False
            tomlfiles = list(parts[1])  # 2nd element => predicate is True
        elif standard_project_metadata.exists():
            tomlfiles = [standard_project_metadata]
        return filenames, tomlfiles

    def parse_config_files(
        self,
        filenames: Iterable[StrPath] | None = None,
        ignore_option_errors: bool = False,
    ) -> None:
        """Parses configuration files from various levels
        and loads configuration.
        """
        inifiles, tomlfiles = self._get_project_config_files(filenames)

        self._parse_config_files(filenames=inifiles)

        setupcfg.parse_configuration(
            self, self.command_options, ignore_option_errors=ignore_option_errors
        )
        for filename in tomlfiles:
            pyprojecttoml.apply_configuration(self, filename, ignore_option_errors)

        self._finalize_requires()
        self._finalize_license_expression()
        self._finalize_license_files()

    def fetch_build_eggs(self, requires: _StrOrIter) -> list[metadata.Distribution]:
        """Resolve pre-setup requirements"""
        from .installer import _fetch_build_eggs

        return _fetch_build_eggs(self, requires)

    def finalize_options(self) -> None:
        """
        Allow plugins to apply arbitrary operations to the
        distribution. Each hook may optionally define a 'order'
        to influence the order of execution. Smaller numbers
        go first and the default is 0.
        """
        group = 'setuptools.finalize_distribution_options'

        def by_order(hook):
            return getattr(hook, 'order', 0)

        defined = metadata.entry_points(group=group)
        filtered = itertools.filterfalse(self._removed, defined)
        loaded = map(lambda e: e.load(), filtered)
        for ep in sorted(loaded, key=by_order):
            ep(self)

    @staticmethod
    def _removed(ep):
        """
        When removing an entry point, if metadata is loaded
        from an older version of Setuptools, that removed
        entry point will attempt to be loaded and will fail.
        See #2765 for more details.
        """
        removed = {
            # removed 2021-09-05
            '2to3_doctests',
        }
        return ep.name in removed

    def _finalize_setup_keywords(self):
        for ep in metadata.entry_points(group='distutils.setup_keywords'):
            value = getattr(self, ep.name, None)
            if value is not None:
                ep.load()(self, ep.name, value)

    def get_egg_cache_dir(self):
        from . import windows_support

        egg_cache_dir = os.path.join(os.curdir, '.eggs')
        if not os.path.exists(egg_cache_dir):
            os.mkdir(egg_cache_dir)
            windows_support.hide_file(egg_cache_dir)
            readme_txt_filename = os.path.join(egg_cache_dir, 'README.txt')
            with open(readme_txt_filename, 'w', encoding="utf-8") as f:
                f.write(
                    'This directory contains eggs that were downloaded '
                    'by setuptools to build, test, and run plug-ins.\n\n'
                )
                f.write(
                    'This directory caches those eggs to prevent '
                    'repeated downloads.\n\n'
                )
                f.write('However, it is safe to delete this directory.\n\n')

        return egg_cache_dir

    def fetch_build_egg(self, req):
        """Fetch an egg needed for building"""
        from .installer import fetch_build_egg

        return fetch_build_egg(self, req)

    def get_command_class(self, command: str) -> type[distutils.cmd.Command]:  # type: ignore[override] # Not doing complex overrides yet
        """Pluggable version of get_command_class()"""
        if command in self.cmdclass:
            return self.cmdclass[command]

        # Special case bdist_wheel so it's never loaded from "wheel"
        if command == 'bdist_wheel':
            from .command.bdist_wheel import bdist_wheel

            return bdist_wheel

        eps = metadata.entry_points(group='distutils.commands', name=command)
        for ep in eps:
            self.cmdclass[command] = cmdclass = ep.load()
            return cmdclass
        else:
            return _Distribution.get_command_class(self, command)

    def print_commands(self):
        for ep in metadata.entry_points(group='distutils.commands'):
            if ep.name not in self.cmdclass:
                cmdclass = ep.load()
                self.cmdclass[ep.name] = cmdclass
        return _Distribution.print_commands(self)

    def get_command_list(self):
        for ep in metadata.entry_points(group='distutils.commands'):
            if ep.name not in self.cmdclass:
                cmdclass = ep.load()
                self.cmdclass[ep.name] = cmdclass
        return _Distribution.get_command_list(self)

    def include(self, **attrs) -> None:
        """Add items to distribution that are named in keyword arguments

        For example, 'dist.include(py_modules=["x"])' would add 'x' to
        the distribution's 'py_modules' attribute, if it was not already
        there.

        Currently, this method only supports inclusion for attributes that are
        lists or tuples.  If you need to add support for adding to other
        attributes in this or a subclass, you can add an '_include_X' method,
        where 'X' is the name of the attribute.  The method will be called with
        the value passed to 'include()'.  So, 'dist.include(foo={"bar":"baz"})'
        will try to call 'dist._include_foo({"bar":"baz"})', which can then
        handle whatever special inclusion logic is needed.
        """
        for k, v in attrs.items():
            include = getattr(self, '_include_' + k, None)
            if include:
                include(v)
            else:
                self._include_misc(k, v)

    def exclude_package(self, package: str) -> None:
        """Remove packages, modules, and extensions in named package"""

        pfx = package + '.'
        if self.packages:
            self.packages = [
                p for p in self.packages if p != package and not p.startswith(pfx)
            ]

        if self.py_modules:
            self.py_modules = [
                p for p in self.py_modules if p != package and not p.startswith(pfx)
            ]

        if self.ext_modules:
            self.ext_modules = [
                p
                for p in self.ext_modules
                if p.name != package and not p.name.startswith(pfx)
            ]

    def has_contents_for(self, package: str) -> bool:
        """Return true if 'exclude_package(package)' would do something"""

        pfx = package + '.'

        for p in self.iter_distribution_names():
            if p == package or p.startswith(pfx):
                return True

        return False

    def _exclude_misc(self, name: str, value: _Sequence) -> None:
        """Handle 'exclude()' for list/tuple attrs without a special handler"""
        if not isinstance(value, _sequence):
            raise DistutilsSetupError(
                f"{name}: setting must be of type <{_sequence_type_repr}> (got {value!r})"
            )
        try:
            old = getattr(self, name)
        except AttributeError as e:
            raise DistutilsSetupError(f"{name}: No such distribution setting") from e
        if old is not None and not isinstance(old, _sequence):
            raise DistutilsSetupError(
                name + ": this setting cannot be changed via include/exclude"
            )
        elif old:
            setattr(self, name, [item for item in old if item not in value])

    def _include_misc(self, name: str, value: _Sequence) -> None:
        """Handle 'include()' for list/tuple attrs without a special handler"""

        if not isinstance(value, _sequence):
            raise DistutilsSetupError(
                f"{name}: setting must be of type <{_sequence_type_repr}> (got {value!r})"
            )
        try:
            old = getattr(self, name)
        except AttributeError as e:
            raise DistutilsSetupError(f"{name}: No such distribution setting") from e
        if old is None:
            setattr(self, name, value)
        elif not isinstance(old, _sequence):
            raise DistutilsSetupError(
                name + ": this setting cannot be changed via include/exclude"
            )
        else:
            new = [item for item in value if item not in old]
            setattr(self, name, list(old) + new)

    def exclude(self, **attrs) -> None:
        """Remove items from distribution that are named in keyword arguments

        For example, 'dist.exclude(py_modules=["x"])' would remove 'x' from
        the distribution's 'py_modules' attribute.  Excluding packages uses
        the 'exclude_package()' method, so all of the package's contained
        packages, modules, and extensions are also excluded.

        Currently, this method only supports exclusion from attributes that are
        lists or tuples.  If you need to add support for excluding from other
        attributes in this or a subclass, you can add an '_exclude_X' method,
        where 'X' is the name of the attribute.  The method will be called with
        the value passed to 'exclude()'.  So, 'dist.exclude(foo={"bar":"baz"})'
        will try to call 'dist._exclude_foo({"bar":"baz"})', which can then
        handle whatever special exclusion logic is needed.
        """
        for k, v in attrs.items():
            exclude = getattr(self, '_exclude_' + k, None)
            if exclude:
                exclude(v)
            else:
                self._exclude_misc(k, v)

    def _exclude_packages(self, packages: _Sequence) -> None:
        if not isinstance(packages, _sequence):
            raise DistutilsSetupError(
                f"packages: setting must be of type <{_sequence_type_repr}> (got {packages!r})"
            )
        list(map(self.exclude_package, packages))

    def _parse_command_opts(self, parser, args):
        # Remove --with-X/--without-X options when processing command args
        self.global_options = self.__class__.global_options
        self.negative_opt = self.__class__.negative_opt

        # First, expand any aliases
        command = args[0]
        aliases = self.get_option_dict('aliases')
        while command in aliases:
            _src, alias = aliases[command]
            del aliases[command]  # ensure each alias can expand only once!
            import shlex

            args[:1] = shlex.split(alias, True)
            command = args[0]

        nargs = _Distribution._parse_command_opts(self, parser, args)

        # Handle commands that want to consume all remaining arguments
        cmd_class = self.get_command_class(command)
        if getattr(cmd_class, 'command_consumes_arguments', None):
            self.get_option_dict(command)['args'] = ("command line", nargs)
            if nargs is not None:
                return []

        return nargs

    def get_cmdline_options(self) -> dict[str, dict[str, str | None]]:
        """Return a '{cmd: {opt:val}}' map of all command-line options

        Option names are all long, but do not include the leading '--', and
        contain dashes rather than underscores.  If the option doesn't take
        an argument (e.g. '--quiet'), the 'val' is 'None'.

        Note that options provided by config files are intentionally excluded.
        """

        d: dict[str, dict[str, str | None]] = {}

        for cmd, opts in self.command_options.items():
            val: str | None
            for opt, (src, val) in opts.items():
                if src != "command line":
                    continue

                opt = opt.replace('_', '-')

                if val == 0:
                    cmdobj = self.get_command_obj(cmd)
                    neg_opt = self.negative_opt.copy()
                    neg_opt.update(getattr(cmdobj, 'negative_opt', {}))
                    for neg, pos in neg_opt.items():
                        if pos == opt:
                            opt = neg
                            val = None
                            break
                    else:
                        raise AssertionError("Shouldn't be able to get here")

                elif val == 1:
                    val = None

                d.setdefault(cmd, {})[opt] = val

        return d

    def iter_distribution_names(self):
        """Yield all packages, modules, and extension names in distribution"""

        yield from self.packages or ()

        yield from self.py_modules or ()

        for ext in self.ext_modules or ():
            if isinstance(ext, tuple):
                name, _buildinfo = ext
            else:
                name = ext.name
            if name.endswith('module'):
                name = name[:-6]
            yield name

    def handle_display_options(self, option_order):
        """If there were any non-global "display-only" options
        (--help-commands or the metadata display options) on the command
        line, display the requested info and return true; else return
        false.
        """
        import sys

        if self.help_commands:
            return _Distribution.handle_display_options(self, option_order)

        # Stdout may be StringIO (e.g. in tests)
        if not isinstance(sys.stdout, io.TextIOWrapper):
            return _Distribution.handle_display_options(self, option_order)

        # Don't wrap stdout if utf-8 is already the encoding. Provides
        #  workaround for #334.
        if sys.stdout.encoding.lower() in ('utf-8', 'utf8'):
            return _Distribution.handle_display_options(self, option_order)

        # Print metadata in UTF-8 no matter the platform
        encoding = sys.stdout.encoding
        sys.stdout.reconfigure(encoding='utf-8')
        try:
            return _Distribution.handle_display_options(self, option_order)
        finally:
            sys.stdout.reconfigure(encoding=encoding)

    def run_command(self, command) -> None:
        self.set_defaults()
        # Postpone defaults until all explicit configuration is considered
        # (setup() args, config files, command line and plugins)

        super().run_command(command)


@functools.cache
def _setuptools_commands() -> set[str]:
    try:
        # Use older API for importlib.metadata compatibility
        entry_points = metadata.distribution('setuptools').entry_points
        eps: Iterable[str] = (ep.name for ep in entry_points)
    except metadata.PackageNotFoundError:
        # during bootstrapping, distribution doesn't exist
        eps = []
    return {*distutils.command.__all__, *eps}


class DistDeprecationWarning(SetuptoolsDeprecationWarning):
    """Class for warning about deprecations in dist in
    setuptools. Not ignored by default, unlike DeprecationWarning."""

# === NexusCore/openenv\Lib\site-packages\numpy\matrixlib\defmatrix.py ===
__all__ = ['matrix', 'bmat', 'asmatrix']

import ast
import sys
import warnings

import numpy._core.numeric as N
from numpy._core.numeric import concatenate, isscalar
from numpy._utils import set_module

# While not in __all__, matrix_power used to be defined here, so we import
# it for backward compatibility.
from numpy.linalg import matrix_power


def _convert_from_string(data):
    for char in '[]':
        data = data.replace(char, '')

    rows = data.split(';')
    newdata = []
    for count, row in enumerate(rows):
        trow = row.split(',')
        newrow = []
        for col in trow:
            temp = col.split()
            newrow.extend(map(ast.literal_eval, temp))
        if count == 0:
            Ncols = len(newrow)
        elif len(newrow) != Ncols:
            raise ValueError("Rows not the same size.")
        newdata.append(newrow)
    return newdata


@set_module('numpy')
def asmatrix(data, dtype=None):
    """
    Interpret the input as a matrix.

    Unlike `matrix`, `asmatrix` does not make a copy if the input is already
    a matrix or an ndarray.  Equivalent to ``matrix(data, copy=False)``.

    Parameters
    ----------
    data : array_like
        Input data.
    dtype : data-type
       Data-type of the output matrix.

    Returns
    -------
    mat : matrix
        `data` interpreted as a matrix.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.array([[1, 2], [3, 4]])

    >>> m = np.asmatrix(x)

    >>> x[0,0] = 5

    >>> m
    matrix([[5, 2],
            [3, 4]])

    """
    return matrix(data, dtype=dtype, copy=False)


@set_module('numpy')
class matrix(N.ndarray):
    """
    matrix(data, dtype=None, copy=True)

    Returns a matrix from an array-like object, or from a string of data.

    A matrix is a specialized 2-D array that retains its 2-D nature
    through operations.  It has certain special operators, such as ``*``
    (matrix multiplication) and ``**`` (matrix power).

    .. note:: It is no longer recommended to use this class, even for linear
              algebra. Instead use regular arrays. The class may be removed
              in the future.

    Parameters
    ----------
    data : array_like or string
       If `data` is a string, it is interpreted as a matrix with commas
       or spaces separating columns, and semicolons separating rows.
    dtype : data-type
       Data-type of the output matrix.
    copy : bool
       If `data` is already an `ndarray`, then this flag determines
       whether the data is copied (the default), or whether a view is
       constructed.

    See Also
    --------
    array

    Examples
    --------
    >>> import numpy as np
    >>> a = np.matrix('1 2; 3 4')
    >>> a
    matrix([[1, 2],
            [3, 4]])

    >>> np.matrix([[1, 2], [3, 4]])
    matrix([[1, 2],
            [3, 4]])

    """
    __array_priority__ = 10.0

    def __new__(subtype, data, dtype=None, copy=True):
        warnings.warn('the matrix subclass is not the recommended way to '
                      'represent matrices or deal with linear algebra (see '
                      'https://docs.scipy.org/doc/numpy/user/'
                      'numpy-for-matlab-users.html). '
                      'Please adjust your code to use regular ndarray.',
                      PendingDeprecationWarning, stacklevel=2)
        if isinstance(data, matrix):
            dtype2 = data.dtype
            if (dtype is None):
                dtype = dtype2
            if (dtype2 == dtype) and (not copy):
                return data
            return data.astype(dtype)

        if isinstance(data, N.ndarray):
            if dtype is None:
                intype = data.dtype
            else:
                intype = N.dtype(dtype)
            new = data.view(subtype)
            if intype != data.dtype:
                return new.astype(intype)
            if copy:
                return new.copy()
            else:
                return new

        if isinstance(data, str):
            data = _convert_from_string(data)

        # now convert data to an array
        copy = None if not copy else True
        arr = N.array(data, dtype=dtype, copy=copy)
        ndim = arr.ndim
        shape = arr.shape
        if (ndim > 2):
            raise ValueError("matrix must be 2-dimensional")
        elif ndim == 0:
            shape = (1, 1)
        elif ndim == 1:
            shape = (1, shape[0])

        order = 'C'
        if (ndim == 2) and arr.flags.fortran:
            order = 'F'

        if not (order or arr.flags.contiguous):
            arr = arr.copy()

        ret = N.ndarray.__new__(subtype, shape, arr.dtype,
                                buffer=arr,
                                order=order)
        return ret

    def __array_finalize__(self, obj):
        self._getitem = False
        if (isinstance(obj, matrix) and obj._getitem):
            return
        ndim = self.ndim
        if (ndim == 2):
            return
        if (ndim > 2):
            newshape = tuple(x for x in self.shape if x > 1)
            ndim = len(newshape)
            if ndim == 2:
                self.shape = newshape
                return
            elif (ndim > 2):
                raise ValueError("shape too large to be a matrix.")
        else:
            newshape = self.shape
        if ndim == 0:
            self.shape = (1, 1)
        elif ndim == 1:
            self.shape = (1, newshape[0])
        return

    def __getitem__(self, index):
        self._getitem = True

        try:
            out = N.ndarray.__getitem__(self, index)
        finally:
            self._getitem = False

        if not isinstance(out, N.ndarray):
            return out

        if out.ndim == 0:
            return out[()]
        if out.ndim == 1:
            sh = out.shape[0]
            # Determine when we should have a column array
            try:
                n = len(index)
            except Exception:
                n = 0
            if n > 1 and isscalar(index[1]):
                out.shape = (sh, 1)
            else:
                out.shape = (1, sh)
        return out

    def __mul__(self, other):
        if isinstance(other, (N.ndarray, list, tuple)):
            # This promotes 1-D vectors to row vectors
            return N.dot(self, asmatrix(other))
        if isscalar(other) or not hasattr(other, '__rmul__'):
            return N.dot(self, other)
        return NotImplemented

    def __rmul__(self, other):
        return N.dot(other, self)

    def __imul__(self, other):
        self[:] = self * other
        return self

    def __pow__(self, other):
        return matrix_power(self, other)

    def __ipow__(self, other):
        self[:] = self ** other
        return self

    def __rpow__(self, other):
        return NotImplemented

    def _align(self, axis):
        """A convenience function for operations that need to preserve axis
        orientation.
        """
        if axis is None:
            return self[0, 0]
        elif axis == 0:
            return self
        elif axis == 1:
            return self.transpose()
        else:
            raise ValueError("unsupported axis")

    def _collapse(self, axis):
        """A convenience function for operations that want to collapse
        to a scalar like _align, but are using keepdims=True
        """
        if axis is None:
            return self[0, 0]
        else:
            return self

    # Necessary because base-class tolist expects dimension
    #  reduction by x[0]
    def tolist(self):
        """
        Return the matrix as a (possibly nested) list.

        See `ndarray.tolist` for full documentation.

        See Also
        --------
        ndarray.tolist

        Examples
        --------
        >>> x = np.matrix(np.arange(12).reshape((3,4))); x
        matrix([[ 0,  1,  2,  3],
                [ 4,  5,  6,  7],
                [ 8,  9, 10, 11]])
        >>> x.tolist()
        [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11]]

        """
        return self.__array__().tolist()

    # To preserve orientation of result...
    def sum(self, axis=None, dtype=None, out=None):
        """
        Returns the sum of the matrix elements, along the given axis.

        Refer to `numpy.sum` for full documentation.

        See Also
        --------
        numpy.sum

        Notes
        -----
        This is the same as `ndarray.sum`, except that where an `ndarray` would
        be returned, a `matrix` object is returned instead.

        Examples
        --------
        >>> x = np.matrix([[1, 2], [4, 3]])
        >>> x.sum()
        10
        >>> x.sum(axis=1)
        matrix([[3],
                [7]])
        >>> x.sum(axis=1, dtype='float')
        matrix([[3.],
                [7.]])
        >>> out = np.zeros((2, 1), dtype='float')
        >>> x.sum(axis=1, dtype='float', out=np.asmatrix(out))
        matrix([[3.],
                [7.]])

        """
        return N.ndarray.sum(self, axis, dtype, out, keepdims=True)._collapse(axis)

    # To update docstring from array to matrix...
    def squeeze(self, axis=None):
        """
        Return a possibly reshaped matrix.

        Refer to `numpy.squeeze` for more documentation.

        Parameters
        ----------
        axis : None or int or tuple of ints, optional
            Selects a subset of the axes of length one in the shape.
            If an axis is selected with shape entry greater than one,
            an error is raised.

        Returns
        -------
        squeezed : matrix
            The matrix, but as a (1, N) matrix if it had shape (N, 1).

        See Also
        --------
        numpy.squeeze : related function

        Notes
        -----
        If `m` has a single column then that column is returned
        as the single row of a matrix.  Otherwise `m` is returned.
        The returned matrix is always either `m` itself or a view into `m`.
        Supplying an axis keyword argument will not affect the returned matrix
        but it may cause an error to be raised.

        Examples
        --------
        >>> c = np.matrix([[1], [2]])
        >>> c
        matrix([[1],
                [2]])
        >>> c.squeeze()
        matrix([[1, 2]])
        >>> r = c.T
        >>> r
        matrix([[1, 2]])
        >>> r.squeeze()
        matrix([[1, 2]])
        >>> m = np.matrix([[1, 2], [3, 4]])
        >>> m.squeeze()
        matrix([[1, 2],
                [3, 4]])

        """
        return N.ndarray.squeeze(self, axis=axis)

    # To update docstring from array to matrix...
    def flatten(self, order='C'):
        """
        Return a flattened copy of the matrix.

        All `N` elements of the matrix are placed into a single row.

        Parameters
        ----------
        order : {'C', 'F', 'A', 'K'}, optional
            'C' means to flatten in row-major (C-style) order. 'F' means to
            flatten in column-major (Fortran-style) order. 'A' means to
            flatten in column-major order if `m` is Fortran *contiguous* in
            memory, row-major order otherwise. 'K' means to flatten `m` in
            the order the elements occur in memory. The default is 'C'.

        Returns
        -------
        y : matrix
            A copy of the matrix, flattened to a `(1, N)` matrix where `N`
            is the number of elements in the original matrix.

        See Also
        --------
        ravel : Return a flattened array.
        flat : A 1-D flat iterator over the matrix.

        Examples
        --------
        >>> m = np.matrix([[1,2], [3,4]])
        >>> m.flatten()
        matrix([[1, 2, 3, 4]])
        >>> m.flatten('F')
        matrix([[1, 3, 2, 4]])

        """
        return N.ndarray.flatten(self, order=order)

    def mean(self, axis=None, dtype=None, out=None):
        """
        Returns the average of the matrix elements along the given axis.

        Refer to `numpy.mean` for full documentation.

        See Also
        --------
        numpy.mean

        Notes
        -----
        Same as `ndarray.mean` except that, where that returns an `ndarray`,
        this returns a `matrix` object.

        Examples
        --------
        >>> x = np.matrix(np.arange(12).reshape((3, 4)))
        >>> x
        matrix([[ 0,  1,  2,  3],
                [ 4,  5,  6,  7],
                [ 8,  9, 10, 11]])
        >>> x.mean()
        5.5
        >>> x.mean(0)
        matrix([[4., 5., 6., 7.]])
        >>> x.mean(1)
        matrix([[ 1.5],
                [ 5.5],
                [ 9.5]])

        """
        return N.ndarray.mean(self, axis, dtype, out, keepdims=True)._collapse(axis)

    def std(self, axis=None, dtype=None, out=None, ddof=0):
        """
        Return the standard deviation of the array elements along the given axis.

        Refer to `numpy.std` for full documentation.

        See Also
        --------
        numpy.std

        Notes
        -----
        This is the same as `ndarray.std`, except that where an `ndarray` would
        be returned, a `matrix` object is returned instead.

        Examples
        --------
        >>> x = np.matrix(np.arange(12).reshape((3, 4)))
        >>> x
        matrix([[ 0,  1,  2,  3],
                [ 4,  5,  6,  7],
                [ 8,  9, 10, 11]])
        >>> x.std()
        3.4520525295346629 # may vary
        >>> x.std(0)
        matrix([[ 3.26598632,  3.26598632,  3.26598632,  3.26598632]]) # may vary
        >>> x.std(1)
        matrix([[ 1.11803399],
                [ 1.11803399],
                [ 1.11803399]])

        """
        return N.ndarray.std(self, axis, dtype, out, ddof,
                             keepdims=True)._collapse(axis)

    def var(self, axis=None, dtype=None, out=None, ddof=0):
        """
        Returns the variance of the matrix elements, along the given axis.

        Refer to `numpy.var` for full documentation.

        See Also
        --------
        numpy.var

        Notes
        -----
        This is the same as `ndarray.var`, except that where an `ndarray` would
        be returned, a `matrix` object is returned instead.

        Examples
        --------
        >>> x = np.matrix(np.arange(12).reshape((3, 4)))
        >>> x
        matrix([[ 0,  1,  2,  3],
                [ 4,  5,  6,  7],
                [ 8,  9, 10, 11]])
        >>> x.var()
        11.916666666666666
        >>> x.var(0)
        matrix([[ 10.66666667,  10.66666667,  10.66666667,  10.66666667]]) # may vary
        >>> x.var(1)
        matrix([[1.25],
                [1.25],
                [1.25]])

        """
        return N.ndarray.var(self, axis, dtype, out, ddof,
                             keepdims=True)._collapse(axis)

    def prod(self, axis=None, dtype=None, out=None):
        """
        Return the product of the array elements over the given axis.

        Refer to `prod` for full documentation.

        See Also
        --------
        prod, ndarray.prod

        Notes
        -----
        Same as `ndarray.prod`, except, where that returns an `ndarray`, this
        returns a `matrix` object instead.

        Examples
        --------
        >>> x = np.matrix(np.arange(12).reshape((3,4))); x
        matrix([[ 0,  1,  2,  3],
                [ 4,  5,  6,  7],
                [ 8,  9, 10, 11]])
        >>> x.prod()
        0
        >>> x.prod(0)
        matrix([[  0,  45, 120, 231]])
        >>> x.prod(1)
        matrix([[   0],
                [ 840],
                [7920]])

        """
        return N.ndarray.prod(self, axis, dtype, out, keepdims=True)._collapse(axis)

    def any(self, axis=None, out=None):
        """
        Test whether any array element along a given axis evaluates to True.

        Refer to `numpy.any` for full documentation.

        Parameters
        ----------
        axis : int, optional
            Axis along which logical OR is performed
        out : ndarray, optional
            Output to existing array instead of creating new one, must have
            same shape as expected output

        Returns
        -------
            any : bool, ndarray
                Returns a single bool if `axis` is ``None``; otherwise,
                returns `ndarray`

        """
        return N.ndarray.any(self, axis, out, keepdims=True)._collapse(axis)

    def all(self, axis=None, out=None):
        """
        Test whether all matrix elements along a given axis evaluate to True.

        Parameters
        ----------
        See `numpy.all` for complete descriptions

        See Also
        --------
        numpy.all

        Notes
        -----
        This is the same as `ndarray.all`, but it returns a `matrix` object.

        Examples
        --------
        >>> x = np.matrix(np.arange(12).reshape((3,4))); x
        matrix([[ 0,  1,  2,  3],
                [ 4,  5,  6,  7],
                [ 8,  9, 10, 11]])
        >>> y = x[0]; y
        matrix([[0, 1, 2, 3]])
        >>> (x == y)
        matrix([[ True,  True,  True,  True],
                [False, False, False, False],
                [False, False, False, False]])
        >>> (x == y).all()
        False
        >>> (x == y).all(0)
        matrix([[False, False, False, False]])
        >>> (x == y).all(1)
        matrix([[ True],
                [False],
                [False]])

        """
        return N.ndarray.all(self, axis, out, keepdims=True)._collapse(axis)

    def max(self, axis=None, out=None):
        """
        Return the maximum value along an axis.

        Parameters
        ----------
        See `amax` for complete descriptions

        See Also
        --------
        amax, ndarray.max

        Notes
        -----
        This is the same as `ndarray.max`, but returns a `matrix` object
        where `ndarray.max` would return an ndarray.

        Examples
        --------
        >>> x = np.matrix(np.arange(12).reshape((3,4))); x
        matrix([[ 0,  1,  2,  3],
                [ 4,  5,  6,  7],
                [ 8,  9, 10, 11]])
        >>> x.max()
        11
        >>> x.max(0)
        matrix([[ 8,  9, 10, 11]])
        >>> x.max(1)
        matrix([[ 3],
                [ 7],
                [11]])

        """
        return N.ndarray.max(self, axis, out, keepdims=True)._collapse(axis)

    def argmax(self, axis=None, out=None):
        """
        Indexes of the maximum values along an axis.

        Return the indexes of the first occurrences of the maximum values
        along the specified axis.  If axis is None, the index is for the
        flattened matrix.

        Parameters
        ----------
        See `numpy.argmax` for complete descriptions

        See Also
        --------
        numpy.argmax

        Notes
        -----
        This is the same as `ndarray.argmax`, but returns a `matrix` object
        where `ndarray.argmax` would return an `ndarray`.

        Examples
        --------
        >>> x = np.matrix(np.arange(12).reshape((3,4))); x
        matrix([[ 0,  1,  2,  3],
                [ 4,  5,  6,  7],
                [ 8,  9, 10, 11]])
        >>> x.argmax()
        11
        >>> x.argmax(0)
        matrix([[2, 2, 2, 2]])
        >>> x.argmax(1)
        matrix([[3],
                [3],
                [3]])

        """
        return N.ndarray.argmax(self, axis, out)._align(axis)

    def min(self, axis=None, out=None):
        """
        Return the minimum value along an axis.

        Parameters
        ----------
        See `amin` for complete descriptions.

        See Also
        --------
        amin, ndarray.min

        Notes
        -----
        This is the same as `ndarray.min`, but returns a `matrix` object
        where `ndarray.min` would return an ndarray.

        Examples
        --------
        >>> x = -np.matrix(np.arange(12).reshape((3,4))); x
        matrix([[  0,  -1,  -2,  -3],
                [ -4,  -5,  -6,  -7],
                [ -8,  -9, -10, -11]])
        >>> x.min()
        -11
        >>> x.min(0)
        matrix([[ -8,  -9, -10, -11]])
        >>> x.min(1)
        matrix([[ -3],
                [ -7],
                [-11]])

        """
        return N.ndarray.min(self, axis, out, keepdims=True)._collapse(axis)

    def argmin(self, axis=None, out=None):
        """
        Indexes of the minimum values along an axis.

        Return the indexes of the first occurrences of the minimum values
        along the specified axis.  If axis is None, the index is for the
        flattened matrix.

        Parameters
        ----------
        See `numpy.argmin` for complete descriptions.

        See Also
        --------
        numpy.argmin

        Notes
        -----
        This is the same as `ndarray.argmin`, but returns a `matrix` object
        where `ndarray.argmin` would return an `ndarray`.

        Examples
        --------
        >>> x = -np.matrix(np.arange(12).reshape((3,4))); x
        matrix([[  0,  -1,  -2,  -3],
                [ -4,  -5,  -6,  -7],
                [ -8,  -9, -10, -11]])
        >>> x.argmin()
        11
        >>> x.argmin(0)
        matrix([[2, 2, 2, 2]])
        >>> x.argmin(1)
        matrix([[3],
                [3],
                [3]])

        """
        return N.ndarray.argmin(self, axis, out)._align(axis)

    def ptp(self, axis=None, out=None):
        """
        Peak-to-peak (maximum - minimum) value along the given axis.

        Refer to `numpy.ptp` for full documentation.

        See Also
        --------
        numpy.ptp

        Notes
        -----
        Same as `ndarray.ptp`, except, where that would return an `ndarray` object,
        this returns a `matrix` object.

        Examples
        --------
        >>> x = np.matrix(np.arange(12).reshape((3,4))); x
        matrix([[ 0,  1,  2,  3],
                [ 4,  5,  6,  7],
                [ 8,  9, 10, 11]])
        >>> x.ptp()
        11
        >>> x.ptp(0)
        matrix([[8, 8, 8, 8]])
        >>> x.ptp(1)
        matrix([[3],
                [3],
                [3]])

        """
        return N.ptp(self, axis, out)._align(axis)

    @property
    def I(self):  # noqa: E743
        """
        Returns the (multiplicative) inverse of invertible `self`.

        Parameters
        ----------
        None

        Returns
        -------
        ret : matrix object
            If `self` is non-singular, `ret` is such that ``ret * self`` ==
            ``self * ret`` == ``np.matrix(np.eye(self[0,:].size))`` all return
            ``True``.

        Raises
        ------
        numpy.linalg.LinAlgError: Singular matrix
            If `self` is singular.

        See Also
        --------
        linalg.inv

        Examples
        --------
        >>> m = np.matrix('[1, 2; 3, 4]'); m
        matrix([[1, 2],
                [3, 4]])
        >>> m.getI()
        matrix([[-2. ,  1. ],
                [ 1.5, -0.5]])
        >>> m.getI() * m
        matrix([[ 1.,  0.], # may vary
                [ 0.,  1.]])

        """
        M, N = self.shape
        if M == N:
            from numpy.linalg import inv as func
        else:
            from numpy.linalg import pinv as func
        return asmatrix(func(self))

    @property
    def A(self):
        """
        Return `self` as an `ndarray` object.

        Equivalent to ``np.asarray(self)``.

        Parameters
        ----------
        None

        Returns
        -------
        ret : ndarray
            `self` as an `ndarray`

        Examples
        --------
        >>> x = np.matrix(np.arange(12).reshape((3,4))); x
        matrix([[ 0,  1,  2,  3],
                [ 4,  5,  6,  7],
                [ 8,  9, 10, 11]])
        >>> x.getA()
        array([[ 0,  1,  2,  3],
               [ 4,  5,  6,  7],
               [ 8,  9, 10, 11]])

        """
        return self.__array__()

    @property
    def A1(self):
        """
        Return `self` as a flattened `ndarray`.

        Equivalent to ``np.asarray(x).ravel()``

        Parameters
        ----------
        None

        Returns
        -------
        ret : ndarray
            `self`, 1-D, as an `ndarray`

        Examples
        --------
        >>> x = np.matrix(np.arange(12).reshape((3,4))); x
        matrix([[ 0,  1,  2,  3],
                [ 4,  5,  6,  7],
                [ 8,  9, 10, 11]])
        >>> x.getA1()
        array([ 0,  1,  2, ...,  9, 10, 11])


        """
        return self.__array__().ravel()

    def ravel(self, order='C'):
        """
        Return a flattened matrix.

        Refer to `numpy.ravel` for more documentation.

        Parameters
        ----------
        order : {'C', 'F', 'A', 'K'}, optional
            The elements of `m` are read using this index order. 'C' means to
            index the elements in C-like order, with the last axis index
            changing fastest, back to the first axis index changing slowest.
            'F' means to index the elements in Fortran-like index order, with
            the first index changing fastest, and the last index changing
            slowest. Note that the 'C' and 'F' options take no account of the
            memory layout of the underlying array, and only refer to the order
            of axis indexing.  'A' means to read the elements in Fortran-like
            index order if `m` is Fortran *contiguous* in memory, C-like order
            otherwise.  'K' means to read the elements in the order they occur
            in memory, except for reversing the data when strides are negative.
            By default, 'C' index order is used.

        Returns
        -------
        ret : matrix
            Return the matrix flattened to shape `(1, N)` where `N`
            is the number of elements in the original matrix.
            A copy is made only if necessary.

        See Also
        --------
        matrix.flatten : returns a similar output matrix but always a copy
        matrix.flat : a flat iterator on the array.
        numpy.ravel : related function which returns an ndarray

        """
        return N.ndarray.ravel(self, order=order)

    @property
    def T(self):
        """
        Returns the transpose of the matrix.

        Does *not* conjugate!  For the complex conjugate transpose, use ``.H``.

        Parameters
        ----------
        None

        Returns
        -------
        ret : matrix object
            The (non-conjugated) transpose of the matrix.

        See Also
        --------
        transpose, getH

        Examples
        --------
        >>> m = np.matrix('[1, 2; 3, 4]')
        >>> m
        matrix([[1, 2],
                [3, 4]])
        >>> m.getT()
        matrix([[1, 3],
                [2, 4]])

        """
        return self.transpose()

    @property
    def H(self):
        """
        Returns the (complex) conjugate transpose of `self`.

        Equivalent to ``np.transpose(self)`` if `self` is real-valued.

        Parameters
        ----------
        None

        Returns
        -------
        ret : matrix object
            complex conjugate transpose of `self`

        Examples
        --------
        >>> x = np.matrix(np.arange(12).reshape((3,4)))
        >>> z = x - 1j*x; z
        matrix([[  0. +0.j,   1. -1.j,   2. -2.j,   3. -3.j],
                [  4. -4.j,   5. -5.j,   6. -6.j,   7. -7.j],
                [  8. -8.j,   9. -9.j,  10.-10.j,  11.-11.j]])
        >>> z.getH()
        matrix([[ 0. -0.j,  4. +4.j,  8. +8.j],
                [ 1. +1.j,  5. +5.j,  9. +9.j],
                [ 2. +2.j,  6. +6.j, 10.+10.j],
                [ 3. +3.j,  7. +7.j, 11.+11.j]])

        """
        if issubclass(self.dtype.type, N.complexfloating):
            return self.transpose().conjugate()
        else:
            return self.transpose()

    # kept for compatibility
    getT = T.fget
    getA = A.fget
    getA1 = A1.fget
    getH = H.fget
    getI = I.fget

def _from_string(str, gdict, ldict):
    rows = str.split(';')
    rowtup = []
    for row in rows:
        trow = row.split(',')
        newrow = []
        for x in trow:
            newrow.extend(x.split())
        trow = newrow
        coltup = []
        for col in trow:
            col = col.strip()
            try:
                thismat = ldict[col]
            except KeyError:
                try:
                    thismat = gdict[col]
                except KeyError as e:
                    raise NameError(f"name {col!r} is not defined") from None

            coltup.append(thismat)
        rowtup.append(concatenate(coltup, axis=-1))
    return concatenate(rowtup, axis=0)


@set_module('numpy')
def bmat(obj, ldict=None, gdict=None):
    """
    Build a matrix object from a string, nested sequence, or array.

    Parameters
    ----------
    obj : str or array_like
        Input data. If a string, variables in the current scope may be
        referenced by name.
    ldict : dict, optional
        A dictionary that replaces local operands in current frame.
        Ignored if `obj` is not a string or `gdict` is None.
    gdict : dict, optional
        A dictionary that replaces global operands in current frame.
        Ignored if `obj` is not a string.

    Returns
    -------
    out : matrix
        Returns a matrix object, which is a specialized 2-D array.

    See Also
    --------
    block :
        A generalization of this function for N-d arrays, that returns normal
        ndarrays.

    Examples
    --------
    >>> import numpy as np
    >>> A = np.asmatrix('1 1; 1 1')
    >>> B = np.asmatrix('2 2; 2 2')
    >>> C = np.asmatrix('3 4; 5 6')
    >>> D = np.asmatrix('7 8; 9 0')

    All the following expressions construct the same block matrix:

    >>> np.bmat([[A, B], [C, D]])
    matrix([[1, 1, 2, 2],
            [1, 1, 2, 2],
            [3, 4, 7, 8],
            [5, 6, 9, 0]])
    >>> np.bmat(np.r_[np.c_[A, B], np.c_[C, D]])
    matrix([[1, 1, 2, 2],
            [1, 1, 2, 2],
            [3, 4, 7, 8],
            [5, 6, 9, 0]])
    >>> np.bmat('A,B; C,D')
    matrix([[1, 1, 2, 2],
            [1, 1, 2, 2],
            [3, 4, 7, 8],
            [5, 6, 9, 0]])

    """
    if isinstance(obj, str):
        if gdict is None:
            # get previous frame
            frame = sys._getframe().f_back
            glob_dict = frame.f_globals
            loc_dict = frame.f_locals
        else:
            glob_dict = gdict
            loc_dict = ldict

        return matrix(_from_string(obj, glob_dict, loc_dict))

    if isinstance(obj, (tuple, list)):
        # [[A,B],[C,D]]
        arr_rows = []
        for row in obj:
            if isinstance(row, N.ndarray):  # not 2-d
                return matrix(concatenate(obj, axis=-1))
            else:
                arr_rows.append(concatenate(row, axis=-1))
        return matrix(concatenate(arr_rows, axis=0))
    if isinstance(obj, N.ndarray):
        return matrix(obj)

# === NexusCore/openenv\Lib\site-packages\trio\_tests\test_testing_raisesgroup.py ===
from __future__ import annotations

import re
import sys
from types import TracebackType
from typing import TYPE_CHECKING

import pytest

import trio
from trio.testing import Matcher, RaisesGroup
from trio.testing._raises_group import repr_callable

if sys.version_info < (3, 11):
    from exceptiongroup import BaseExceptionGroup, ExceptionGroup

if TYPE_CHECKING:
    from _pytest.python_api import RaisesContext


def wrap_escape(s: str) -> str:
    return "^" + re.escape(s) + "$"


def fails_raises_group(
    msg: str, add_prefix: bool = True
) -> RaisesContext[AssertionError]:
    assert (
        msg[-1] != "\n"
    ), "developer error, expected string should not end with newline"
    prefix = "Raised exception group did not match: " if add_prefix else ""
    return pytest.raises(AssertionError, match=wrap_escape(prefix + msg))


def test_raises_group() -> None:
    with pytest.raises(
        ValueError,
        match=wrap_escape(
            f'Invalid argument "{TypeError()!r}" must be exception type, Matcher, or RaisesGroup.',
        ),
    ):
        RaisesGroup(TypeError())  # type: ignore[call-overload]
    with RaisesGroup(ValueError):
        raise ExceptionGroup("foo", (ValueError(),))

    with (
        fails_raises_group("'SyntaxError' is not of type 'ValueError'"),
        RaisesGroup(ValueError),
    ):
        raise ExceptionGroup("foo", (SyntaxError(),))

    # multiple exceptions
    with RaisesGroup(ValueError, SyntaxError):
        raise ExceptionGroup("foo", (ValueError(), SyntaxError()))

    # order doesn't matter
    with RaisesGroup(SyntaxError, ValueError):
        raise ExceptionGroup("foo", (ValueError(), SyntaxError()))

    # nested exceptions
    with RaisesGroup(RaisesGroup(ValueError)):
        raise ExceptionGroup("foo", (ExceptionGroup("bar", (ValueError(),)),))

    with RaisesGroup(
        SyntaxError,
        RaisesGroup(ValueError),
        RaisesGroup(RuntimeError),
    ):
        raise ExceptionGroup(
            "foo",
            (
                SyntaxError(),
                ExceptionGroup("bar", (ValueError(),)),
                ExceptionGroup("", (RuntimeError(),)),
            ),
        )


def test_incorrect_number_exceptions() -> None:
    # We previously gave an error saying the number of exceptions was wrong,
    # but we now instead indicate excess/missing exceptions
    with (
        fails_raises_group(
            "1 matched exception. Unexpected exception(s): [RuntimeError()]"
        ),
        RaisesGroup(ValueError),
    ):
        raise ExceptionGroup("", (RuntimeError(), ValueError()))

    # will error if there's missing exceptions
    with (
        fails_raises_group(
            "1 matched exception. Too few exceptions raised, found no match for: ['SyntaxError']"
        ),
        RaisesGroup(ValueError, SyntaxError),
    ):
        raise ExceptionGroup("", (ValueError(),))

    with (
        fails_raises_group(
            "\n"
            "1 matched exception. \n"
            "Too few exceptions raised!\n"
            "The following expected exceptions did not find a match:\n"
            "  'ValueError'\n"
            "    It matches ValueError() which was paired with 'ValueError'"
        ),
        RaisesGroup(ValueError, ValueError),
    ):
        raise ExceptionGroup("", (ValueError(),))

    with (
        fails_raises_group(
            "\n"
            "1 matched exception. \n"
            "Unexpected exception(s)!\n"
            "The following raised exceptions did not find a match\n"
            "  ValueError():\n"
            "    It matches 'ValueError' which was paired with ValueError()"
        ),
        RaisesGroup(ValueError),
    ):
        raise ExceptionGroup("", (ValueError(), ValueError()))

    with (
        fails_raises_group(
            "\n"
            "1 matched exception. \n"
            "The following expected exceptions did not find a match:\n"
            "  'ValueError'\n"
            "    It matches ValueError() which was paired with 'ValueError'\n"
            "The following raised exceptions did not find a match\n"
            "  SyntaxError():\n"
            "    'SyntaxError' is not of type 'ValueError'"
        ),
        RaisesGroup(ValueError, ValueError),
    ):
        raise ExceptionGroup("", [ValueError(), SyntaxError()])


def test_flatten_subgroups() -> None:
    # loose semantics, as with expect*
    with RaisesGroup(ValueError, flatten_subgroups=True):
        raise ExceptionGroup("", (ExceptionGroup("", (ValueError(),)),))

    with RaisesGroup(ValueError, TypeError, flatten_subgroups=True):
        raise ExceptionGroup("", (ExceptionGroup("", (ValueError(), TypeError())),))
    with RaisesGroup(ValueError, TypeError, flatten_subgroups=True):
        raise ExceptionGroup("", [ExceptionGroup("", [ValueError()]), TypeError()])

    # mixed loose is possible if you want it to be at least N deep
    with RaisesGroup(RaisesGroup(ValueError, flatten_subgroups=True)):
        raise ExceptionGroup("", (ExceptionGroup("", (ValueError(),)),))
    with RaisesGroup(RaisesGroup(ValueError, flatten_subgroups=True)):
        raise ExceptionGroup(
            "",
            (ExceptionGroup("", (ExceptionGroup("", (ValueError(),)),)),),
        )

    # but not the other way around
    with pytest.raises(
        ValueError,
        match=r"^You cannot specify a nested structure inside a RaisesGroup with",
    ):
        RaisesGroup(RaisesGroup(ValueError), flatten_subgroups=True)  # type: ignore[call-overload]

    # flatten_subgroups is not sufficient to catch fully unwrapped
    with (
        fails_raises_group(
            "'ValueError' is not an exception group, but would match with `allow_unwrapped=True`"
        ),
        RaisesGroup(ValueError, flatten_subgroups=True),
    ):
        raise ValueError
    with (
        fails_raises_group(
            "RaisesGroup(ValueError, flatten_subgroups=True): 'ValueError' is not an exception group, but would match with `allow_unwrapped=True`"
        ),
        RaisesGroup(RaisesGroup(ValueError, flatten_subgroups=True)),
    ):
        raise ExceptionGroup("", (ValueError(),))

    # helpful suggestion if flatten_subgroups would make it pass
    with (
        fails_raises_group(
            "Raised exception group did not match: \n"
            "The following expected exceptions did not find a match:\n"
            "  'ValueError'\n"
            "  'TypeError'\n"
            "The following raised exceptions did not find a match\n"
            "  ExceptionGroup('', [ValueError(), TypeError()]):\n"
            "    Unexpected nested 'ExceptionGroup', expected 'ValueError'\n"
            "    Unexpected nested 'ExceptionGroup', expected 'TypeError'\n"
            "Did you mean to use `flatten_subgroups=True`?",
            add_prefix=False,
        ),
        RaisesGroup(ValueError, TypeError),
    ):
        raise ExceptionGroup("", [ExceptionGroup("", [ValueError(), TypeError()])])
    # but doesn't consider check (otherwise we'd break typing guarantees)
    with (
        fails_raises_group(
            "Raised exception group did not match: \n"
            "The following expected exceptions did not find a match:\n"
            "  'ValueError'\n"
            "  'TypeError'\n"
            "The following raised exceptions did not find a match\n"
            "  ExceptionGroup('', [ValueError(), TypeError()]):\n"
            "    Unexpected nested 'ExceptionGroup', expected 'ValueError'\n"
            "    Unexpected nested 'ExceptionGroup', expected 'TypeError'\n"
            "Did you mean to use `flatten_subgroups=True`?",
            add_prefix=False,
        ),
        RaisesGroup(
            ValueError,
            TypeError,
            check=lambda eg: len(eg.exceptions) == 1,
        ),
    ):
        raise ExceptionGroup("", [ExceptionGroup("", [ValueError(), TypeError()])])
    # correct number of exceptions, and flatten_subgroups would make it pass
    # This now doesn't print a repr of the caught exception at all, but that can be found in the traceback
    with (
        fails_raises_group(
            "Raised exception group did not match: Unexpected nested 'ExceptionGroup', expected 'ValueError'\n"
            "  Did you mean to use `flatten_subgroups=True`?",
            add_prefix=False,
        ),
        RaisesGroup(ValueError),
    ):
        raise ExceptionGroup("", [ExceptionGroup("", [ValueError()])])
    # correct number of exceptions, but flatten_subgroups wouldn't help, so we don't suggest it
    with (
        fails_raises_group("Unexpected nested 'ExceptionGroup', expected 'ValueError'"),
        RaisesGroup(ValueError),
    ):
        raise ExceptionGroup("", [ExceptionGroup("", [TypeError()])])

    # flatten_subgroups can be suggested if nested. This will implicitly ask the user to
    # do `RaisesGroup(RaisesGroup(ValueError, flatten_subgroups=True))` which is unlikely
    # to be what they actually want - but I don't think it's worth trying to special-case
    with (
        fails_raises_group(
            "RaisesGroup(ValueError): Unexpected nested 'ExceptionGroup', expected 'ValueError'\n"
            "  Did you mean to use `flatten_subgroups=True`?",
        ),
        RaisesGroup(RaisesGroup(ValueError)),
    ):
        raise ExceptionGroup(
            "",
            [ExceptionGroup("", [ExceptionGroup("", [ValueError()])])],
        )

    # Don't mention "unexpected nested" if expecting an ExceptionGroup.
    # Although it should perhaps be an error to specify `RaisesGroup(ExceptionGroup)` in
    # favor of doing `RaisesGroup(RaisesGroup(...))`.
    with (
        fails_raises_group("'BaseExceptionGroup' is not of type 'ExceptionGroup'"),
        RaisesGroup(ExceptionGroup),
    ):
        raise BaseExceptionGroup("", [BaseExceptionGroup("", [KeyboardInterrupt()])])


def test_catch_unwrapped_exceptions() -> None:
    # Catches lone exceptions with strict=False
    # just as except* would
    with RaisesGroup(ValueError, allow_unwrapped=True):
        raise ValueError

    # expecting multiple unwrapped exceptions is not possible
    with pytest.raises(
        ValueError,
        match=r"^You cannot specify multiple exceptions with",
    ):
        RaisesGroup(SyntaxError, ValueError, allow_unwrapped=True)  # type: ignore[call-overload]
    # if users want one of several exception types they need to use a Matcher
    # (which the error message suggests)
    with RaisesGroup(
        Matcher(check=lambda e: isinstance(e, (SyntaxError, ValueError))),
        allow_unwrapped=True,
    ):
        raise ValueError

    # Unwrapped nested `RaisesGroup` is likely a user error, so we raise an error.
    with pytest.raises(ValueError, match="has no effect when expecting"):
        RaisesGroup(RaisesGroup(ValueError), allow_unwrapped=True)  # type: ignore[call-overload]

    # But it *can* be used to check for nesting level +- 1 if they move it to
    # the nested RaisesGroup. Users should probably use `Matcher`s instead though.
    with RaisesGroup(RaisesGroup(ValueError, allow_unwrapped=True)):
        raise ExceptionGroup("", [ExceptionGroup("", [ValueError()])])
    with RaisesGroup(RaisesGroup(ValueError, allow_unwrapped=True)):
        raise ExceptionGroup("", [ValueError()])

    # with allow_unwrapped=False (default) it will not be caught
    with (
        fails_raises_group(
            "'ValueError' is not an exception group, but would match with `allow_unwrapped=True`"
        ),
        RaisesGroup(ValueError),
    ):
        raise ValueError("value error text")

    # allow_unwrapped on its own won't match against nested groups
    with (
        fails_raises_group(
            "Unexpected nested 'ExceptionGroup', expected 'ValueError'\n"
            "  Did you mean to use `flatten_subgroups=True`?",
        ),
        RaisesGroup(ValueError, allow_unwrapped=True),
    ):
        raise ExceptionGroup("foo", [ExceptionGroup("bar", [ValueError()])])

    # you need both allow_unwrapped and flatten_subgroups to fully emulate except*
    with RaisesGroup(ValueError, allow_unwrapped=True, flatten_subgroups=True):
        raise ExceptionGroup("", [ExceptionGroup("", [ValueError()])])

    # code coverage
    with (
        fails_raises_group(
            "Raised exception (group) did not match: 'TypeError' is not of type 'ValueError'",
            add_prefix=False,
        ),
        RaisesGroup(ValueError, allow_unwrapped=True),
    ):
        raise TypeError("this text doesn't show up in the error message")
    with (
        fails_raises_group(
            "Raised exception (group) did not match: Matcher(ValueError): 'TypeError' is not of type 'ValueError'",
            add_prefix=False,
        ),
        RaisesGroup(Matcher(ValueError), allow_unwrapped=True),
    ):
        raise TypeError

    # check we don't suggest unwrapping with nested RaisesGroup
    with (
        fails_raises_group("'ValueError' is not an exception group"),
        RaisesGroup(RaisesGroup(ValueError)),
    ):
        raise ValueError


def test_match() -> None:
    # supports match string
    with RaisesGroup(ValueError, match="bar"):
        raise ExceptionGroup("bar", (ValueError(),))

    # now also works with ^$
    with RaisesGroup(ValueError, match="^bar$"):
        raise ExceptionGroup("bar", (ValueError(),))

    # it also includes notes
    with RaisesGroup(ValueError, match="my note"):
        e = ExceptionGroup("bar", (ValueError(),))
        e.add_note("my note")
        raise e

    # and technically you can match it all with ^$
    # but you're probably better off using a Matcher at that point
    with RaisesGroup(ValueError, match="^bar\nmy note$"):
        e = ExceptionGroup("bar", (ValueError(),))
        e.add_note("my note")
        raise e

    with (
        fails_raises_group(
            "Regex pattern 'foo' did not match 'bar' of 'ExceptionGroup'"
        ),
        RaisesGroup(ValueError, match="foo"),
    ):
        raise ExceptionGroup("bar", (ValueError(),))

    # Suggest a fix for easy pitfall of adding match to the RaisesGroup instead of
    # using a Matcher.
    # This requires a single expected & raised exception, the expected is a type,
    # and `isinstance(raised, expected_type)`.
    with (
        fails_raises_group(
            "Regex pattern 'foo' did not match 'bar' of 'ExceptionGroup', but matched the expected 'ValueError'. You might want RaisesGroup(Matcher(ValueError, match='foo'))"
        ),
        RaisesGroup(ValueError, match="foo"),
    ):
        raise ExceptionGroup("bar", [ValueError("foo")])


def test_check() -> None:
    exc = ExceptionGroup("", (ValueError(),))

    def is_exc(e: ExceptionGroup[ValueError]) -> bool:
        return e is exc

    is_exc_repr = repr_callable(is_exc)
    with RaisesGroup(ValueError, check=is_exc):
        raise exc

    with (
        fails_raises_group(f"check {is_exc_repr} did not return True"),
        RaisesGroup(ValueError, check=is_exc),
    ):
        raise ExceptionGroup("", (ValueError(),))


def test_unwrapped_match_check() -> None:
    def my_check(e: object) -> bool:  # pragma: no cover
        return True

    msg = (
        "`allow_unwrapped=True` bypasses the `match` and `check` parameters"
        " if the exception is unwrapped. If you intended to match/check the"
        " exception you should use a `Matcher` object. If you want to match/check"
        " the exceptiongroup when the exception *is* wrapped you need to"
        " do e.g. `if isinstance(exc.value, ExceptionGroup):"
        " assert RaisesGroup(...).matches(exc.value)` afterwards."
    )
    with pytest.raises(ValueError, match=re.escape(msg)):
        RaisesGroup(ValueError, allow_unwrapped=True, match="foo")  # type: ignore[call-overload]
    with pytest.raises(ValueError, match=re.escape(msg)):
        RaisesGroup(ValueError, allow_unwrapped=True, check=my_check)  # type: ignore[call-overload]

    # Users should instead use a Matcher
    rg = RaisesGroup(Matcher(ValueError, match="^foo$"), allow_unwrapped=True)
    with rg:
        raise ValueError("foo")
    with rg:
        raise ExceptionGroup("", [ValueError("foo")])

    # or if they wanted to match/check the group, do a conditional `.matches()`
    with RaisesGroup(ValueError, allow_unwrapped=True) as exc:
        raise ExceptionGroup("bar", [ValueError("foo")])
    if isinstance(exc.value, ExceptionGroup):  # pragma: no branch
        assert RaisesGroup(ValueError, match="bar").matches(exc.value)


def test_RaisesGroup_matches() -> None:
    rg = RaisesGroup(ValueError)
    assert not rg.matches(None)
    assert not rg.matches(ValueError())
    assert rg.matches(ExceptionGroup("", (ValueError(),)))


def test_message() -> None:
    def check_message(
        message: str,
        body: RaisesGroup[BaseException],
    ) -> None:
        with (
            pytest.raises(
                AssertionError,
                match=f"^DID NOT RAISE any exception, expected {re.escape(message)}$",
            ),
            body,
        ):
            ...

    # basic
    check_message("ExceptionGroup(ValueError)", RaisesGroup(ValueError))
    # multiple exceptions
    check_message(
        "ExceptionGroup(ValueError, ValueError)",
        RaisesGroup(ValueError, ValueError),
    )
    # nested
    check_message(
        "ExceptionGroup(ExceptionGroup(ValueError))",
        RaisesGroup(RaisesGroup(ValueError)),
    )

    # Matcher
    check_message(
        "ExceptionGroup(Matcher(ValueError, match='my_str'))",
        RaisesGroup(Matcher(ValueError, "my_str")),
    )
    check_message(
        "ExceptionGroup(Matcher(match='my_str'))",
        RaisesGroup(Matcher(match="my_str")),
    )

    # BaseExceptionGroup
    check_message(
        "BaseExceptionGroup(KeyboardInterrupt)",
        RaisesGroup(KeyboardInterrupt),
    )
    # BaseExceptionGroup with type inside Matcher
    check_message(
        "BaseExceptionGroup(Matcher(KeyboardInterrupt))",
        RaisesGroup(Matcher(KeyboardInterrupt)),
    )
    # Base-ness transfers to parent containers
    check_message(
        "BaseExceptionGroup(BaseExceptionGroup(KeyboardInterrupt))",
        RaisesGroup(RaisesGroup(KeyboardInterrupt)),
    )
    # but not to child containers
    check_message(
        "BaseExceptionGroup(BaseExceptionGroup(KeyboardInterrupt), ExceptionGroup(ValueError))",
        RaisesGroup(RaisesGroup(KeyboardInterrupt), RaisesGroup(ValueError)),
    )


def test_assert_message() -> None:
    # the message does not need to list all parameters to RaisesGroup, nor all exceptions
    # in the exception group, as those are both visible in the traceback.
    # first fails to match
    with (
        fails_raises_group("'TypeError' is not of type 'ValueError'"),
        RaisesGroup(ValueError),
    ):
        raise ExceptionGroup("a", [TypeError()])
    with (
        fails_raises_group(
            "Raised exception group did not match: \n"
            "The following expected exceptions did not find a match:\n"
            "  RaisesGroup(ValueError)\n"
            "  RaisesGroup(ValueError, match='a')\n"
            "The following raised exceptions did not find a match\n"
            "  ExceptionGroup('', [RuntimeError()]):\n"
            "    RaisesGroup(ValueError): 'RuntimeError' is not of type 'ValueError'\n"
            "    RaisesGroup(ValueError, match='a'): Regex pattern 'a' did not match '' of 'ExceptionGroup'\n"
            "  RuntimeError():\n"
            "    RaisesGroup(ValueError): 'RuntimeError' is not an exception group\n"
            "    RaisesGroup(ValueError, match='a'): 'RuntimeError' is not an exception group",
            add_prefix=False,  # to see the full structure
        ),
        RaisesGroup(RaisesGroup(ValueError), RaisesGroup(ValueError, match="a")),
    ):
        raise ExceptionGroup(
            "",
            [ExceptionGroup("", [RuntimeError()]), RuntimeError()],
        )

    with (
        fails_raises_group(
            "Raised exception group did not match: \n"
            "2 matched exceptions. \n"
            "The following expected exceptions did not find a match:\n"
            "  RaisesGroup(RuntimeError)\n"
            "  RaisesGroup(ValueError)\n"
            "The following raised exceptions did not find a match\n"
            "  RuntimeError():\n"
            # "    'RuntimeError' is not of type 'ValueError'\n"
            # "    Matcher(TypeError): 'RuntimeError' is not of type 'TypeError'\n"
            "    RaisesGroup(RuntimeError): 'RuntimeError' is not an exception group, but would match with `allow_unwrapped=True`\n"
            "    RaisesGroup(ValueError): 'RuntimeError' is not an exception group\n"
            "  ValueError('bar'):\n"
            "    It matches 'ValueError' which was paired with ValueError('foo')\n"
            "    RaisesGroup(RuntimeError): 'ValueError' is not an exception group\n"
            "    RaisesGroup(ValueError): 'ValueError' is not an exception group, but would match with `allow_unwrapped=True`",
            add_prefix=False,  # to see the full structure
        ),
        RaisesGroup(
            ValueError,
            Matcher(TypeError),
            RaisesGroup(RuntimeError),
            RaisesGroup(ValueError),
        ),
    ):
        raise ExceptionGroup(
            "a",
            [RuntimeError(), TypeError(), ValueError("foo"), ValueError("bar")],
        )

    with (
        fails_raises_group(
            "1 matched exception. 'AssertionError' is not of type 'TypeError'"
        ),
        RaisesGroup(ValueError, TypeError),
    ):
        raise ExceptionGroup("a", [ValueError(), AssertionError()])

    with (
        fails_raises_group(
            "Matcher(ValueError): 'TypeError' is not of type 'ValueError'"
        ),
        RaisesGroup(Matcher(ValueError)),
    ):
        raise ExceptionGroup("a", [TypeError()])

    # suggest escaping
    with (
        fails_raises_group(
            "Raised exception group did not match: Regex pattern 'h(ell)o' did not match 'h(ell)o' of 'ExceptionGroup'\n"
            "  Did you mean to `re.escape()` the regex?",
            add_prefix=False,  # to see the full structure
        ),
        RaisesGroup(ValueError, match="h(ell)o"),
    ):
        raise ExceptionGroup("h(ell)o", [ValueError()])
    with (
        fails_raises_group(
            "Matcher(match='h(ell)o'): Regex pattern 'h(ell)o' did not match 'h(ell)o'\n"
            "  Did you mean to `re.escape()` the regex?",
        ),
        RaisesGroup(Matcher(match="h(ell)o")),
    ):
        raise ExceptionGroup("", [ValueError("h(ell)o")])

    with (
        fails_raises_group(
            "Raised exception group did not match: \n"
            "The following expected exceptions did not find a match:\n"
            "  'ValueError'\n"
            "  'ValueError'\n"
            "  'ValueError'\n"
            "  'ValueError'\n"
            "The following raised exceptions did not find a match\n"
            "  ExceptionGroup('', [ValueError(), TypeError()]):\n"
            "    Unexpected nested 'ExceptionGroup', expected 'ValueError'\n"
            "    Unexpected nested 'ExceptionGroup', expected 'ValueError'\n"
            "    Unexpected nested 'ExceptionGroup', expected 'ValueError'\n"
            "    Unexpected nested 'ExceptionGroup', expected 'ValueError'",
            add_prefix=False,  # to see the full structure
        ),
        RaisesGroup(ValueError, ValueError, ValueError, ValueError),
    ):
        raise ExceptionGroup("", [ExceptionGroup("", [ValueError(), TypeError()])])


def test_message_indent() -> None:
    with (
        fails_raises_group(
            "Raised exception group did not match: \n"
            "The following expected exceptions did not find a match:\n"
            "  RaisesGroup(ValueError, ValueError)\n"
            "  'ValueError'\n"
            "The following raised exceptions did not find a match\n"
            "  ExceptionGroup('', [TypeError(), RuntimeError()]):\n"
            "    RaisesGroup(ValueError, ValueError): \n"
            "      The following expected exceptions did not find a match:\n"
            "        'ValueError'\n"
            "        'ValueError'\n"
            "      The following raised exceptions did not find a match\n"
            "        TypeError():\n"
            "          'TypeError' is not of type 'ValueError'\n"
            "          'TypeError' is not of type 'ValueError'\n"
            "        RuntimeError():\n"
            "          'RuntimeError' is not of type 'ValueError'\n"
            "          'RuntimeError' is not of type 'ValueError'\n"
            # TODO: this line is not great, should maybe follow the same format as the other and say
            # 'ValueError': Unexpected nested 'ExceptionGroup' (?)
            "    Unexpected nested 'ExceptionGroup', expected 'ValueError'\n"
            "  TypeError():\n"
            "    RaisesGroup(ValueError, ValueError): 'TypeError' is not an exception group\n"
            "    'TypeError' is not of type 'ValueError'",
            add_prefix=False,
        ),
        RaisesGroup(
            RaisesGroup(ValueError, ValueError),
            ValueError,
        ),
    ):
        raise ExceptionGroup(
            "",
            [
                ExceptionGroup("", [TypeError(), RuntimeError()]),
                TypeError(),
            ],
        )
    with (
        fails_raises_group(
            "Raised exception group did not match: \n"
            "RaisesGroup(ValueError, ValueError): \n"
            "  The following expected exceptions did not find a match:\n"
            "    'ValueError'\n"
            "    'ValueError'\n"
            "  The following raised exceptions did not find a match\n"
            "    TypeError():\n"
            "      'TypeError' is not of type 'ValueError'\n"
            "      'TypeError' is not of type 'ValueError'\n"
            "    RuntimeError():\n"
            "      'RuntimeError' is not of type 'ValueError'\n"
            "      'RuntimeError' is not of type 'ValueError'",
            add_prefix=False,
        ),
        RaisesGroup(
            RaisesGroup(ValueError, ValueError),
        ),
    ):
        raise ExceptionGroup(
            "",
            [
                ExceptionGroup("", [TypeError(), RuntimeError()]),
            ],
        )


def test_suggestion_on_nested_and_brief_error() -> None:
    # Make sure "Did you mean" suggestion gets indented iff it follows a single-line error
    with (
        fails_raises_group(
            "\n"
            "The following expected exceptions did not find a match:\n"
            "  RaisesGroup(ValueError)\n"
            "  'ValueError'\n"
            "The following raised exceptions did not find a match\n"
            "  ExceptionGroup('', [ExceptionGroup('', [ValueError()])]):\n"
            "    RaisesGroup(ValueError): Unexpected nested 'ExceptionGroup', expected 'ValueError'\n"
            "      Did you mean to use `flatten_subgroups=True`?\n"
            "    Unexpected nested 'ExceptionGroup', expected 'ValueError'",
        ),
        RaisesGroup(RaisesGroup(ValueError), ValueError),
    ):
        raise ExceptionGroup(
            "",
            [ExceptionGroup("", [ExceptionGroup("", [ValueError()])])],
        )
    # if indented here it would look like another raised exception
    with (
        fails_raises_group(
            "\n"
            "The following expected exceptions did not find a match:\n"
            "  RaisesGroup(ValueError, ValueError)\n"
            "  'ValueError'\n"
            "The following raised exceptions did not find a match\n"
            "  ExceptionGroup('', [ValueError(), ExceptionGroup('', [ValueError()])]):\n"
            "    RaisesGroup(ValueError, ValueError): \n"
            "      1 matched exception. \n"
            "      The following expected exceptions did not find a match:\n"
            "        'ValueError'\n"
            "          It matches ValueError() which was paired with 'ValueError'\n"
            "      The following raised exceptions did not find a match\n"
            "        ExceptionGroup('', [ValueError()]):\n"
            "          Unexpected nested 'ExceptionGroup', expected 'ValueError'\n"
            "      Did you mean to use `flatten_subgroups=True`?\n"
            "    Unexpected nested 'ExceptionGroup', expected 'ValueError'"
        ),
        RaisesGroup(RaisesGroup(ValueError, ValueError), ValueError),
    ):
        raise ExceptionGroup(
            "",
            [ExceptionGroup("", [ValueError(), ExceptionGroup("", [ValueError()])])],
        )

    # re.escape always comes after single-line errors
    with (
        fails_raises_group(
            "\n"
            "The following expected exceptions did not find a match:\n"
            "  RaisesGroup(Exception, match='^hello')\n"
            "  'ValueError'\n"
            "The following raised exceptions did not find a match\n"
            "  ExceptionGroup('^hello', [Exception()]):\n"
            "    RaisesGroup(Exception, match='^hello'): Regex pattern '^hello' did not match '^hello' of 'ExceptionGroup'\n"
            "      Did you mean to `re.escape()` the regex?\n"
            "    Unexpected nested 'ExceptionGroup', expected 'ValueError'"
        ),
        RaisesGroup(RaisesGroup(Exception, match="^hello"), ValueError),
    ):
        raise ExceptionGroup("", [ExceptionGroup("^hello", [Exception()])])


def test_assert_message_nested() -> None:
    # we only get one instance of aaaaaaaaaa... and bbbbbb..., but we do get multiple instances of ccccc... and dddddd..
    # but I think this now only prints the full repr when that is necessary to disambiguate exceptions
    with (
        fails_raises_group(
            "Raised exception group did not match: \n"
            "The following expected exceptions did not find a match:\n"
            "  RaisesGroup(ValueError)\n"
            "  RaisesGroup(RaisesGroup(ValueError))\n"
            "  RaisesGroup(Matcher(TypeError, match='foo'))\n"
            "  RaisesGroup(TypeError, ValueError)\n"
            "The following raised exceptions did not find a match\n"
            "  TypeError('aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'):\n"
            "    RaisesGroup(ValueError): 'TypeError' is not an exception group\n"
            "    RaisesGroup(RaisesGroup(ValueError)): 'TypeError' is not an exception group\n"
            "    RaisesGroup(Matcher(TypeError, match='foo')): 'TypeError' is not an exception group\n"
            "    RaisesGroup(TypeError, ValueError): 'TypeError' is not an exception group\n"
            "  ExceptionGroup('Exceptions from Trio nursery', [TypeError('bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb')]):\n"
            "    RaisesGroup(ValueError): 'TypeError' is not of type 'ValueError'\n"
            "    RaisesGroup(RaisesGroup(ValueError)): RaisesGroup(ValueError): 'TypeError' is not an exception group\n"
            "    RaisesGroup(Matcher(TypeError, match='foo')): Matcher(TypeError, match='foo'): Regex pattern 'foo' did not match 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'\n"
            "    RaisesGroup(TypeError, ValueError): 1 matched exception. Too few exceptions raised, found no match for: ['ValueError']\n"
            "  ExceptionGroup('Exceptions from Trio nursery', [TypeError('cccccccccccccccccccccccccccccccccccccccc'), TypeError('dddddddddddddddddddddddddddddddddddddddd')]):\n"
            "    RaisesGroup(ValueError): \n"
            "      The following expected exceptions did not find a match:\n"
            "        'ValueError'\n"
            "      The following raised exceptions did not find a match\n"
            "        TypeError('cccccccccccccccccccccccccccccccccccccccc'):\n"
            "          'TypeError' is not of type 'ValueError'\n"
            "        TypeError('dddddddddddddddddddddddddddddddddddddddd'):\n"
            "          'TypeError' is not of type 'ValueError'\n"
            "    RaisesGroup(RaisesGroup(ValueError)): \n"
            "      The following expected exceptions did not find a match:\n"
            "        RaisesGroup(ValueError)\n"
            "      The following raised exceptions did not find a match\n"
            "        TypeError('cccccccccccccccccccccccccccccccccccccccc'):\n"
            "          RaisesGroup(ValueError): 'TypeError' is not an exception group\n"
            "        TypeError('dddddddddddddddddddddddddddddddddddddddd'):\n"
            "          RaisesGroup(ValueError): 'TypeError' is not an exception group\n"
            "    RaisesGroup(Matcher(TypeError, match='foo')): \n"
            "      The following expected exceptions did not find a match:\n"
            "        Matcher(TypeError, match='foo')\n"
            "      The following raised exceptions did not find a match\n"
            "        TypeError('cccccccccccccccccccccccccccccccccccccccc'):\n"
            "          Matcher(TypeError, match='foo'): Regex pattern 'foo' did not match 'cccccccccccccccccccccccccccccccccccccccc'\n"
            "        TypeError('dddddddddddddddddddddddddddddddddddddddd'):\n"
            "          Matcher(TypeError, match='foo'): Regex pattern 'foo' did not match 'dddddddddddddddddddddddddddddddddddddddd'\n"
            "    RaisesGroup(TypeError, ValueError): \n"
            "      1 matched exception. \n"
            "      The following expected exceptions did not find a match:\n"
            "        'ValueError'\n"
            "      The following raised exceptions did not find a match\n"
            "        TypeError('dddddddddddddddddddddddddddddddddddddddd'):\n"
            "          It matches 'TypeError' which was paired with TypeError('cccccccccccccccccccccccccccccccccccccccc')\n"
            "          'TypeError' is not of type 'ValueError'",
            add_prefix=False,  # to see the full structure
        ),
        RaisesGroup(
            RaisesGroup(ValueError),
            RaisesGroup(RaisesGroup(ValueError)),
            RaisesGroup(Matcher(TypeError, match="foo")),
            RaisesGroup(TypeError, ValueError),
        ),
    ):
        raise ExceptionGroup(
            "",
            [
                TypeError("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"),
                ExceptionGroup(
                    "Exceptions from Trio nursery",
                    [TypeError("bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")],
                ),
                ExceptionGroup(
                    "Exceptions from Trio nursery",
                    [
                        TypeError("cccccccccccccccccccccccccccccccccccccccc"),
                        TypeError("dddddddddddddddddddddddddddddddddddddddd"),
                    ],
                ),
            ],
        )


@pytest.mark.skipif(
    "hypothesis" in sys.modules,
    reason="hypothesis may have monkeypatched _check_repr",
)
def test_check_no_patched_repr() -> None:
    # We make `_check_repr` monkeypatchable to avoid this very ugly and verbose
    # repr. The other tests that use `check` make use of `_check_repr` so they'll
    # continue passing in case it is patched - but we have this one test that
    # demonstrates just how nasty it gets otherwise.
    with (
        pytest.raises(
            AssertionError,
            match=(
                r"^Raised exception group did not match: \n"
                r"The following expected exceptions did not find a match:\n"
                r"  Matcher\(check=<function test_check_no_patched_repr.<locals>.<lambda> at .*>\)\n"
                r"  'TypeError'\n"
                r"The following raised exceptions did not find a match\n"
                r"  ValueError\('foo'\):\n"
                r"    Matcher\(check=<function test_check_no_patched_repr.<locals>.<lambda> at .*>\): check did not return True\n"
                r"    'ValueError' is not of type 'TypeError'\n"
                r"  ValueError\('bar'\):\n"
                r"    Matcher\(check=<function test_check_no_patched_repr.<locals>.<lambda> at .*>\): check did not return True\n"
                r"    'ValueError' is not of type 'TypeError'$"
            ),
        ),
        RaisesGroup(Matcher(check=lambda x: False), TypeError),
    ):
        raise ExceptionGroup("", [ValueError("foo"), ValueError("bar")])


def test_misordering_example() -> None:
    with (
        fails_raises_group(
            "\n"
            "3 matched exceptions. \n"
            "The following expected exceptions did not find a match:\n"
            "  Matcher(ValueError, match='foo')\n"
            "    It matches ValueError('foo') which was paired with 'ValueError'\n"
            "    It matches ValueError('foo') which was paired with 'ValueError'\n"
            "    It matches ValueError('foo') which was paired with 'ValueError'\n"
            "The following raised exceptions did not find a match\n"
            "  ValueError('bar'):\n"
            "    It matches 'ValueError' which was paired with ValueError('foo')\n"
            "    It matches 'ValueError' which was paired with ValueError('foo')\n"
            "    It matches 'ValueError' which was paired with ValueError('foo')\n"
            "    Matcher(ValueError, match='foo'): Regex pattern 'foo' did not match 'bar'\n"
            "There exist a possible match when attempting an exhaustive check, but RaisesGroup uses a greedy algorithm. Please make your expected exceptions more stringent with `Matcher` etc so the greedy algorithm can function."
        ),
        RaisesGroup(
            ValueError, ValueError, ValueError, Matcher(ValueError, match="foo")
        ),
    ):
        raise ExceptionGroup(
            "",
            [
                ValueError("foo"),
                ValueError("foo"),
                ValueError("foo"),
                ValueError("bar"),
            ],
        )


def test_brief_error_on_one_fail() -> None:
    """if only one raised and one expected fail to match up, we print a full table iff
    the raised exception would match one of the expected that previously got matched"""
    # no also-matched
    with (
        fails_raises_group(
            "1 matched exception. 'TypeError' is not of type 'RuntimeError'"
        ),
        RaisesGroup(ValueError, RuntimeError),
    ):
        raise ExceptionGroup("", [ValueError(), TypeError()])

    # raised would match an expected
    with (
        fails_raises_group(
            "\n"
            "1 matched exception. \n"
            "The following expected exceptions did not find a match:\n"
            "  'RuntimeError'\n"
            "The following raised exceptions did not find a match\n"
            "  TypeError():\n"
            "    It matches 'Exception' which was paired with ValueError()\n"
            "    'TypeError' is not of type 'RuntimeError'"
        ),
        RaisesGroup(Exception, RuntimeError),
    ):
        raise ExceptionGroup("", [ValueError(), TypeError()])

    # expected would match a raised
    with (
        fails_raises_group(
            "\n"
            "1 matched exception. \n"
            "The following expected exceptions did not find a match:\n"
            "  'ValueError'\n"
            "    It matches ValueError() which was paired with 'ValueError'\n"
            "The following raised exceptions did not find a match\n"
            "  TypeError():\n"
            "    'TypeError' is not of type 'ValueError'"
        ),
        RaisesGroup(ValueError, ValueError),
    ):
        raise ExceptionGroup("", [ValueError(), TypeError()])


def test_identity_oopsies() -> None:
    # it's both possible to have several instances of the same exception in the same group
    # and to expect multiple of the same type
    # this previously messed up the logic

    with (
        fails_raises_group(
            "3 matched exceptions. 'RuntimeError' is not of type 'TypeError'"
        ),
        RaisesGroup(ValueError, ValueError, ValueError, TypeError),
    ):
        raise ExceptionGroup(
            "", [ValueError(), ValueError(), ValueError(), RuntimeError()]
        )

    e = ValueError("foo")
    m = Matcher(match="bar")
    with (
        fails_raises_group(
            "\n"
            "The following expected exceptions did not find a match:\n"
            "  Matcher(match='bar')\n"
            "  Matcher(match='bar')\n"
            "  Matcher(match='bar')\n"
            "The following raised exceptions did not find a match\n"
            "  ValueError('foo'):\n"
            "    Matcher(match='bar'): Regex pattern 'bar' did not match 'foo'\n"
            "    Matcher(match='bar'): Regex pattern 'bar' did not match 'foo'\n"
            "    Matcher(match='bar'): Regex pattern 'bar' did not match 'foo'\n"
            "  ValueError('foo'):\n"
            "    Matcher(match='bar'): Regex pattern 'bar' did not match 'foo'\n"
            "    Matcher(match='bar'): Regex pattern 'bar' did not match 'foo'\n"
            "    Matcher(match='bar'): Regex pattern 'bar' did not match 'foo'\n"
            "  ValueError('foo'):\n"
            "    Matcher(match='bar'): Regex pattern 'bar' did not match 'foo'\n"
            "    Matcher(match='bar'): Regex pattern 'bar' did not match 'foo'\n"
            "    Matcher(match='bar'): Regex pattern 'bar' did not match 'foo'"
        ),
        RaisesGroup(m, m, m),
    ):
        raise ExceptionGroup("", [e, e, e])


def test_matcher() -> None:
    with pytest.raises(
        ValueError,
        match=r"^You must specify at least one parameter to match on.$",
    ):
        Matcher()  # type: ignore[call-overload]
    with pytest.raises(
        ValueError,
        match=f"^exception_type {re.escape(repr(object))} must be a subclass of BaseException$",
    ):
        Matcher(object)  # type: ignore[type-var]

    with RaisesGroup(Matcher(ValueError)):
        raise ExceptionGroup("", (ValueError(),))
    with (
        fails_raises_group(
            "Matcher(TypeError): 'ValueError' is not of type 'TypeError'"
        ),
        RaisesGroup(Matcher(TypeError)),
    ):
        raise ExceptionGroup("", (ValueError(),))


def test_matcher_match() -> None:
    with RaisesGroup(Matcher(ValueError, "foo")):
        raise ExceptionGroup("", (ValueError("foo"),))
    with (
        fails_raises_group(
            "Matcher(ValueError, match='foo'): Regex pattern 'foo' did not match 'bar'"
        ),
        RaisesGroup(Matcher(ValueError, "foo")),
    ):
        raise ExceptionGroup("", (ValueError("bar"),))

    # Can be used without specifying the type
    with RaisesGroup(Matcher(match="foo")):
        raise ExceptionGroup("", (ValueError("foo"),))
    with (
        fails_raises_group(
            "Matcher(match='foo'): Regex pattern 'foo' did not match 'bar'"
        ),
        RaisesGroup(Matcher(match="foo")),
    ):
        raise ExceptionGroup("", (ValueError("bar"),))

    # check ^$
    with RaisesGroup(Matcher(ValueError, match="^bar$")):
        raise ExceptionGroup("", [ValueError("bar")])
    with (
        fails_raises_group(
            "Matcher(ValueError, match='^bar$'): Regex pattern '^bar$' did not match 'barr'"
        ),
        RaisesGroup(Matcher(ValueError, match="^bar$")),
    ):
        raise ExceptionGroup("", [ValueError("barr")])


def test_Matcher_check() -> None:
    def check_oserror_and_errno_is_5(e: BaseException) -> bool:
        return isinstance(e, OSError) and e.errno == 5

    with RaisesGroup(Matcher(check=check_oserror_and_errno_is_5)):
        raise ExceptionGroup("", (OSError(5, ""),))

    # specifying exception_type narrows the parameter type to the callable
    def check_errno_is_5(e: OSError) -> bool:
        return e.errno == 5

    with RaisesGroup(Matcher(OSError, check=check_errno_is_5)):
        raise ExceptionGroup("", (OSError(5, ""),))

    # avoid printing overly verbose repr multiple times
    with (
        fails_raises_group(
            f"Matcher(OSError, check={check_errno_is_5!r}): check did not return True"
        ),
        RaisesGroup(Matcher(OSError, check=check_errno_is_5)),
    ):
        raise ExceptionGroup("", (OSError(6, ""),))

    # in nested cases you still get it multiple times though
    # to address this you'd need logic in Matcher.__repr__ and RaisesGroup.__repr__
    with (
        fails_raises_group(
            f"RaisesGroup(Matcher(OSError, check={check_errno_is_5!r})): Matcher(OSError, check={check_errno_is_5!r}): check did not return True"
        ),
        RaisesGroup(RaisesGroup(Matcher(OSError, check=check_errno_is_5))),
    ):
        raise ExceptionGroup("", [ExceptionGroup("", [OSError(6, "")])])


def test_matcher_tostring() -> None:
    assert str(Matcher(ValueError)) == "Matcher(ValueError)"
    assert str(Matcher(match="[a-z]")) == "Matcher(match='[a-z]')"
    pattern_no_flags = re.compile(r"noflag", 0)
    assert str(Matcher(match=pattern_no_flags)) == "Matcher(match='noflag')"
    pattern_flags = re.compile(r"noflag", re.IGNORECASE)
    assert str(Matcher(match=pattern_flags)) == f"Matcher(match={pattern_flags!r})"
    assert (
        str(Matcher(ValueError, match="re", check=bool))
        == f"Matcher(ValueError, match='re', check={bool!r})"
    )


def test_raisesgroup_tostring() -> None:
    def check_str_and_repr(s: str) -> None:
        evaled = eval(s)
        assert s == str(evaled) == repr(evaled)

    check_str_and_repr("RaisesGroup(ValueError)")
    check_str_and_repr("RaisesGroup(RaisesGroup(ValueError))")
    check_str_and_repr("RaisesGroup(Matcher(ValueError))")
    check_str_and_repr("RaisesGroup(ValueError, allow_unwrapped=True)")
    check_str_and_repr("RaisesGroup(ValueError, match='aoeu')")

    assert (
        str(RaisesGroup(ValueError, match="[a-z]", check=bool))
        == f"RaisesGroup(ValueError, match='[a-z]', check={bool!r})"
    )


def test__ExceptionInfo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        trio.testing._raises_group,
        "ExceptionInfo",
        trio.testing._raises_group._ExceptionInfo,
    )
    with trio.testing.RaisesGroup(ValueError) as excinfo:
        raise ExceptionGroup("", (ValueError("hello"),))
    assert excinfo.type is ExceptionGroup
    assert excinfo.value.exceptions[0].args == ("hello",)
    assert isinstance(excinfo.tb, TracebackType)

# === NexusCore/openenv\Lib\site-packages\mpl_toolkits\axisartist\axis_artist.py ===
"""
The :mod:`.axis_artist` module implements custom artists to draw axis elements
(axis lines and labels, tick lines and labels, grid lines).

Axis lines and labels and tick lines and labels are managed by the `AxisArtist`
class; grid lines are managed by the `GridlinesCollection` class.

There is one `AxisArtist` per Axis; it can be accessed through
the ``axis`` dictionary of the parent Axes (which should be a
`mpl_toolkits.axislines.Axes`), e.g. ``ax.axis["bottom"]``.

Children of the AxisArtist are accessed as attributes: ``.line`` and ``.label``
for the axis line and label, ``.major_ticks``, ``.major_ticklabels``,
``.minor_ticks``, ``.minor_ticklabels`` for the tick lines and labels (e.g.
``ax.axis["bottom"].line``).

Children properties (colors, fonts, line widths, etc.) can be set using
setters, e.g. ::

  # Make the major ticks of the bottom axis red.
  ax.axis["bottom"].major_ticks.set_color("red")

However, things like the locations of ticks, and their ticklabels need to be
changed from the side of the grid_helper.

axis_direction
--------------

`AxisArtist`, `AxisLabel`, `TickLabels` have an *axis_direction* attribute,
which adjusts the location, angle, etc. The *axis_direction* must be one of
"left", "right", "bottom", "top", and follows the Matplotlib convention for
rectangular axis.

For example, for the *bottom* axis (the left and right is relative to the
direction of the increasing coordinate),

* ticklabels and axislabel are on the right
* ticklabels and axislabel have text angle of 0
* ticklabels are baseline, center-aligned
* axislabel is top, center-aligned

The text angles are actually relative to (90 + angle of the direction to the
ticklabel), which gives 0 for bottom axis.

=================== ====== ======== ====== ========
Property            left   bottom   right  top
=================== ====== ======== ====== ========
ticklabel location  left   right    right  left
axislabel location  left   right    right  left
ticklabel angle     90     0        -90    180
axislabel angle     180    0        0      180
ticklabel va        center baseline center baseline
axislabel va        center top      center bottom
ticklabel ha        right  center   right  center
axislabel ha        right  center   right  center
=================== ====== ======== ====== ========

Ticks are by default direct opposite side of the ticklabels. To make ticks to
the same side of the ticklabels, ::

  ax.axis["bottom"].major_ticks.set_tick_out(True)

The following attributes can be customized (use the ``set_xxx`` methods):

* `Ticks`: ticksize, tick_out
* `TickLabels`: pad
* `AxisLabel`: pad
"""

# FIXME :
# angles are given in data coordinate - need to convert it to canvas coordinate


from operator import methodcaller

import numpy as np

import matplotlib as mpl
from matplotlib import _api, cbook
import matplotlib.artist as martist
import matplotlib.colors as mcolors
import matplotlib.text as mtext
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from matplotlib.patches import PathPatch
from matplotlib.path import Path
from matplotlib.transforms import (
    Affine2D, Bbox, IdentityTransform, ScaledTranslation)

from .axisline_style import AxislineStyle


class AttributeCopier:
    def get_ref_artist(self):
        """
        Return the underlying artist that actually defines some properties
        (e.g., color) of this artist.
        """
        raise RuntimeError("get_ref_artist must overridden")

    def get_attribute_from_ref_artist(self, attr_name):
        getter = methodcaller("get_" + attr_name)
        prop = getter(super())
        return getter(self.get_ref_artist()) if prop == "auto" else prop


class Ticks(AttributeCopier, Line2D):
    """
    Ticks are derived from `.Line2D`, and note that ticks themselves
    are markers. Thus, you should use set_mec, set_mew, etc.

    To change the tick size (length), you need to use
    `set_ticksize`. To change the direction of the ticks (ticks are
    in opposite direction of ticklabels by default), use
    ``set_tick_out(False)``
    """

    def __init__(self, ticksize, tick_out=False, *, axis=None, **kwargs):
        self._ticksize = ticksize
        self.locs_angles_labels = []

        self.set_tick_out(tick_out)

        self._axis = axis
        if self._axis is not None:
            if "color" not in kwargs:
                kwargs["color"] = "auto"
            if "mew" not in kwargs and "markeredgewidth" not in kwargs:
                kwargs["markeredgewidth"] = "auto"

        Line2D.__init__(self, [0.], [0.], **kwargs)
        self.set_snap(True)

    def get_ref_artist(self):
        # docstring inherited
        return self._axis.majorTicks[0].tick1line

    def set_color(self, color):
        # docstring inherited
        # Unlike the base Line2D.set_color, this also supports "auto".
        if not cbook._str_equal(color, "auto"):
            mcolors._check_color_like(color=color)
        self._color = color
        self.stale = True

    def get_color(self):
        return self.get_attribute_from_ref_artist("color")

    def get_markeredgecolor(self):
        return self.get_attribute_from_ref_artist("markeredgecolor")

    def get_markeredgewidth(self):
        return self.get_attribute_from_ref_artist("markeredgewidth")

    def set_tick_out(self, b):
        """Set whether ticks are drawn inside or outside the axes."""
        self._tick_out = b

    def get_tick_out(self):
        """Return whether ticks are drawn inside or outside the axes."""
        return self._tick_out

    def set_ticksize(self, ticksize):
        """Set length of the ticks in points."""
        self._ticksize = ticksize

    def get_ticksize(self):
        """Return length of the ticks in points."""
        return self._ticksize

    def set_locs_angles(self, locs_angles):
        self.locs_angles = locs_angles

    _tickvert_path = Path([[0., 0.], [1., 0.]])

    def draw(self, renderer):
        if not self.get_visible():
            return

        gc = renderer.new_gc()
        gc.set_foreground(self.get_markeredgecolor())
        gc.set_linewidth(self.get_markeredgewidth())
        gc.set_alpha(self._alpha)

        path_trans = self.get_transform()
        marker_transform = (Affine2D()
                            .scale(renderer.points_to_pixels(self._ticksize)))
        if self.get_tick_out():
            marker_transform.rotate_deg(180)

        for loc, angle in self.locs_angles:
            locs = path_trans.transform_non_affine(np.array([loc]))
            if self.axes and not self.axes.viewLim.contains(*locs[0]):
                continue
            renderer.draw_markers(
                gc, self._tickvert_path,
                marker_transform + Affine2D().rotate_deg(angle),
                Path(locs), path_trans.get_affine())

        gc.restore()


class LabelBase(mtext.Text):
    """
    A base class for `.AxisLabel` and `.TickLabels`. The position and
    angle of the text are calculated by the offset_ref_angle,
    text_ref_angle, and offset_radius attributes.
    """

    def __init__(self, *args, **kwargs):
        self.locs_angles_labels = []
        self._ref_angle = 0
        self._offset_radius = 0.

        super().__init__(*args, **kwargs)

        self.set_rotation_mode("anchor")
        self._text_follow_ref_angle = True

    @property
    def _text_ref_angle(self):
        if self._text_follow_ref_angle:
            return self._ref_angle + 90
        else:
            return 0

    @property
    def _offset_ref_angle(self):
        return self._ref_angle

    _get_opposite_direction = {"left": "right",
                               "right": "left",
                               "top": "bottom",
                               "bottom": "top"}.__getitem__

    def draw(self, renderer):
        if not self.get_visible():
            return

        # save original and adjust some properties
        tr = self.get_transform()
        angle_orig = self.get_rotation()
        theta = np.deg2rad(self._offset_ref_angle)
        dd = self._offset_radius
        dx, dy = dd * np.cos(theta), dd * np.sin(theta)

        self.set_transform(tr + Affine2D().translate(dx, dy))
        self.set_rotation(self._text_ref_angle + angle_orig)
        super().draw(renderer)
        # restore original properties
        self.set_transform(tr)
        self.set_rotation(angle_orig)

    def get_window_extent(self, renderer=None):
        if renderer is None:
            renderer = self.get_figure(root=True)._get_renderer()

        # save original and adjust some properties
        tr = self.get_transform()
        angle_orig = self.get_rotation()
        theta = np.deg2rad(self._offset_ref_angle)
        dd = self._offset_radius
        dx, dy = dd * np.cos(theta), dd * np.sin(theta)

        self.set_transform(tr + Affine2D().translate(dx, dy))
        self.set_rotation(self._text_ref_angle + angle_orig)
        bbox = super().get_window_extent(renderer).frozen()
        # restore original properties
        self.set_transform(tr)
        self.set_rotation(angle_orig)

        return bbox


class AxisLabel(AttributeCopier, LabelBase):
    """
    Axis label. Derived from `.Text`. The position of the text is updated
    in the fly, so changing text position has no effect. Otherwise, the
    properties can be changed as a normal `.Text`.

    To change the pad between tick labels and axis label, use `set_pad`.
    """

    def __init__(self, *args, axis_direction="bottom", axis=None, **kwargs):
        self._axis = axis
        self._pad = 5
        self._external_pad = 0  # in pixels
        LabelBase.__init__(self, *args, **kwargs)
        self.set_axis_direction(axis_direction)

    def set_pad(self, pad):
        """
        Set the internal pad in points.

        The actual pad will be the sum of the internal pad and the
        external pad (the latter is set automatically by the `.AxisArtist`).

        Parameters
        ----------
        pad : float
            The internal pad in points.
        """
        self._pad = pad

    def get_pad(self):
        """
        Return the internal pad in points.

        See `.set_pad` for more details.
        """
        return self._pad

    def get_ref_artist(self):
        # docstring inherited
        return self._axis.label

    def get_text(self):
        # docstring inherited
        t = super().get_text()
        if t == "__from_axes__":
            return self._axis.label.get_text()
        return self._text

    _default_alignments = dict(left=("bottom", "center"),
                               right=("top", "center"),
                               bottom=("top", "center"),
                               top=("bottom", "center"))

    def set_default_alignment(self, d):
        """
        Set the default alignment. See `set_axis_direction` for details.

        Parameters
        ----------
        d : {"left", "bottom", "right", "top"}
        """
        va, ha = _api.check_getitem(self._default_alignments, d=d)
        self.set_va(va)
        self.set_ha(ha)

    _default_angles = dict(left=180,
                           right=0,
                           bottom=0,
                           top=180)

    def set_default_angle(self, d):
        """
        Set the default angle. See `set_axis_direction` for details.

        Parameters
        ----------
        d : {"left", "bottom", "right", "top"}
        """
        self.set_rotation(_api.check_getitem(self._default_angles, d=d))

    def set_axis_direction(self, d):
        """
        Adjust the text angle and text alignment of axis label
        according to the matplotlib convention.

        =====================    ========== ========= ========== ==========
        Property                 left       bottom    right      top
        =====================    ========== ========= ========== ==========
        axislabel angle          180        0         0          180
        axislabel va             center     top       center     bottom
        axislabel ha             right      center    right      center
        =====================    ========== ========= ========== ==========

        Note that the text angles are actually relative to (90 + angle
        of the direction to the ticklabel), which gives 0 for bottom
        axis.

        Parameters
        ----------
        d : {"left", "bottom", "right", "top"}
        """
        self.set_default_alignment(d)
        self.set_default_angle(d)

    def get_color(self):
        return self.get_attribute_from_ref_artist("color")

    def draw(self, renderer):
        if not self.get_visible():
            return

        self._offset_radius = \
            self._external_pad + renderer.points_to_pixels(self.get_pad())

        super().draw(renderer)

    def get_window_extent(self, renderer=None):
        if renderer is None:
            renderer = self.get_figure(root=True)._get_renderer()
        if not self.get_visible():
            return

        r = self._external_pad + renderer.points_to_pixels(self.get_pad())
        self._offset_radius = r

        bb = super().get_window_extent(renderer)

        return bb


class TickLabels(AxisLabel):  # mtext.Text
    """
    Tick labels. While derived from `.Text`, this single artist draws all
    ticklabels. As in `.AxisLabel`, the position of the text is updated
    in the fly, so changing text position has no effect. Otherwise,
    the properties can be changed as a normal `.Text`. Unlike the
    ticklabels of the mainline Matplotlib, properties of a single
    ticklabel alone cannot be modified.

    To change the pad between ticks and ticklabels, use `~.AxisLabel.set_pad`.
    """

    def __init__(self, *, axis_direction="bottom", **kwargs):
        super().__init__(**kwargs)
        self.set_axis_direction(axis_direction)
        self._axislabel_pad = 0

    def get_ref_artist(self):
        # docstring inherited
        return self._axis.get_ticklabels()[0]

    def set_axis_direction(self, label_direction):
        """
        Adjust the text angle and text alignment of ticklabels
        according to the Matplotlib convention.

        The *label_direction* must be one of [left, right, bottom, top].

        =====================    ========== ========= ========== ==========
        Property                 left       bottom    right      top
        =====================    ========== ========= ========== ==========
        ticklabel angle          90         0         -90        180
        ticklabel va             center     baseline  center     baseline
        ticklabel ha             right      center    right      center
        =====================    ========== ========= ========== ==========

        Note that the text angles are actually relative to (90 + angle
        of the direction to the ticklabel), which gives 0 for bottom
        axis.

        Parameters
        ----------
        label_direction : {"left", "bottom", "right", "top"}

        """
        self.set_default_alignment(label_direction)
        self.set_default_angle(label_direction)
        self._axis_direction = label_direction

    def invert_axis_direction(self):
        label_direction = self._get_opposite_direction(self._axis_direction)
        self.set_axis_direction(label_direction)

    def _get_ticklabels_offsets(self, renderer, label_direction):
        """
        Calculate the ticklabel offsets from the tick and their total heights.

        The offset only takes account the offset due to the vertical alignment
        of the ticklabels: if axis direction is bottom and va is 'top', it will
        return 0; if va is 'baseline', it will return (height-descent).
        """
        whd_list = self.get_texts_widths_heights_descents(renderer)

        if not whd_list:
            return 0, 0

        r = 0
        va, ha = self.get_va(), self.get_ha()

        if label_direction == "left":
            pad = max(w for w, h, d in whd_list)
            if ha == "left":
                r = pad
            elif ha == "center":
                r = .5 * pad
        elif label_direction == "right":
            pad = max(w for w, h, d in whd_list)
            if ha == "right":
                r = pad
            elif ha == "center":
                r = .5 * pad
        elif label_direction == "bottom":
            pad = max(h for w, h, d in whd_list)
            if va == "bottom":
                r = pad
            elif va == "center":
                r = .5 * pad
            elif va == "baseline":
                max_ascent = max(h - d for w, h, d in whd_list)
                max_descent = max(d for w, h, d in whd_list)
                r = max_ascent
                pad = max_ascent + max_descent
        elif label_direction == "top":
            pad = max(h for w, h, d in whd_list)
            if va == "top":
                r = pad
            elif va == "center":
                r = .5 * pad
            elif va == "baseline":
                max_ascent = max(h - d for w, h, d in whd_list)
                max_descent = max(d for w, h, d in whd_list)
                r = max_descent
                pad = max_ascent + max_descent

        # r : offset
        # pad : total height of the ticklabels. This will be used to
        # calculate the pad for the axislabel.
        return r, pad

    _default_alignments = dict(left=("center", "right"),
                               right=("center", "left"),
                               bottom=("baseline", "center"),
                               top=("baseline", "center"))

    _default_angles = dict(left=90,
                           right=-90,
                           bottom=0,
                           top=180)

    def draw(self, renderer):
        if not self.get_visible():
            self._axislabel_pad = self._external_pad
            return

        r, total_width = self._get_ticklabels_offsets(renderer,
                                                      self._axis_direction)

        pad = self._external_pad + renderer.points_to_pixels(self.get_pad())
        self._offset_radius = r + pad

        for (x, y), a, l in self._locs_angles_labels:
            if not l.strip():
                continue
            self._ref_angle = a
            self.set_x(x)
            self.set_y(y)
            self.set_text(l)
            LabelBase.draw(self, renderer)

        # the value saved will be used to draw axislabel.
        self._axislabel_pad = total_width + pad

    def set_locs_angles_labels(self, locs_angles_labels):
        self._locs_angles_labels = locs_angles_labels

    def get_window_extents(self, renderer=None):
        if renderer is None:
            renderer = self.get_figure(root=True)._get_renderer()

        if not self.get_visible():
            self._axislabel_pad = self._external_pad
            return []

        bboxes = []

        r, total_width = self._get_ticklabels_offsets(renderer,
                                                      self._axis_direction)

        pad = self._external_pad + renderer.points_to_pixels(self.get_pad())
        self._offset_radius = r + pad

        for (x, y), a, l in self._locs_angles_labels:
            self._ref_angle = a
            self.set_x(x)
            self.set_y(y)
            self.set_text(l)
            bb = LabelBase.get_window_extent(self, renderer)
            bboxes.append(bb)

        # the value saved will be used to draw axislabel.
        self._axislabel_pad = total_width + pad

        return bboxes

    def get_texts_widths_heights_descents(self, renderer):
        """
        Return a list of ``(width, height, descent)`` tuples for ticklabels.

        Empty labels are left out.
        """
        whd_list = []
        for _loc, _angle, label in self._locs_angles_labels:
            if not label.strip():
                continue
            clean_line, ismath = self._preprocess_math(label)
            whd = mtext._get_text_metrics_with_cache(
                renderer, clean_line, self._fontproperties, ismath=ismath,
                dpi=self.get_figure(root=True).dpi)
            whd_list.append(whd)
        return whd_list


class GridlinesCollection(LineCollection):
    def __init__(self, *args, which="major", axis="both", **kwargs):
        """
        Collection of grid lines.

        Parameters
        ----------
        which : {"major", "minor"}
            Which grid to consider.
        axis : {"both", "x", "y"}
            Which axis to consider.
        *args, **kwargs
            Passed to `.LineCollection`.
        """
        self._which = which
        self._axis = axis
        super().__init__(*args, **kwargs)
        self.set_grid_helper(None)

    def set_which(self, which):
        """
        Select major or minor grid lines.

        Parameters
        ----------
        which : {"major", "minor"}
        """
        self._which = which

    def set_axis(self, axis):
        """
        Select axis.

        Parameters
        ----------
        axis : {"both", "x", "y"}
        """
        self._axis = axis

    def set_grid_helper(self, grid_helper):
        """
        Set grid helper.

        Parameters
        ----------
        grid_helper : `.GridHelperBase` subclass
        """
        self._grid_helper = grid_helper

    def draw(self, renderer):
        if self._grid_helper is not None:
            self._grid_helper.update_lim(self.axes)
            gl = self._grid_helper.get_gridlines(self._which, self._axis)
            self.set_segments([np.transpose(l) for l in gl])
        super().draw(renderer)


class AxisArtist(martist.Artist):
    """
    An artist which draws axis (a line along which the n-th axes coord
    is constant) line, ticks, tick labels, and axis label.
    """

    zorder = 2.5

    @property
    def LABELPAD(self):
        return self.label.get_pad()

    @LABELPAD.setter
    def LABELPAD(self, v):
        self.label.set_pad(v)

    def __init__(self, axes,
                 helper,
                 offset=None,
                 axis_direction="bottom",
                 **kwargs):
        """
        Parameters
        ----------
        axes : `mpl_toolkits.axisartist.axislines.Axes`
        helper : `~mpl_toolkits.axisartist.axislines.AxisArtistHelper`
        """
        # axes is also used to follow the axis attribute (tick color, etc).

        super().__init__(**kwargs)

        self.axes = axes

        self._axis_artist_helper = helper

        if offset is None:
            offset = (0, 0)
        self.offset_transform = ScaledTranslation(
            *offset,
            Affine2D().scale(1 / 72)  # points to inches.
            + self.axes.get_figure(root=False).dpi_scale_trans)

        if axis_direction in ["left", "right"]:
            self.axis = axes.yaxis
        else:
            self.axis = axes.xaxis

        self._axisline_style = None
        self._axis_direction = axis_direction

        self._init_line()
        self._init_ticks(**kwargs)
        self._init_offsetText(axis_direction)
        self._init_label()

        # axis direction
        self._ticklabel_add_angle = 0.
        self._axislabel_add_angle = 0.
        self.set_axis_direction(axis_direction)

    # axis direction

    def set_axis_direction(self, axis_direction):
        """
        Adjust the direction, text angle, and text alignment of tick labels
        and axis labels following the Matplotlib convention for the rectangle
        axes.

        The *axis_direction* must be one of [left, right, bottom, top].

        =====================    ========== ========= ========== ==========
        Property                 left       bottom    right      top
        =====================    ========== ========= ========== ==========
        ticklabel direction      "-"        "+"       "+"        "-"
        axislabel direction      "-"        "+"       "+"        "-"
        ticklabel angle          90         0         -90        180
        ticklabel va             center     baseline  center     baseline
        ticklabel ha             right      center    right      center
        axislabel angle          180        0         0          180
        axislabel va             center     top       center     bottom
        axislabel ha             right      center    right      center
        =====================    ========== ========= ========== ==========

        Note that the direction "+" and "-" are relative to the direction of
        the increasing coordinate. Also, the text angles are actually
        relative to (90 + angle of the direction to the ticklabel),
        which gives 0 for bottom axis.

        Parameters
        ----------
        axis_direction : {"left", "bottom", "right", "top"}
        """
        self.major_ticklabels.set_axis_direction(axis_direction)
        self.label.set_axis_direction(axis_direction)
        self._axis_direction = axis_direction
        if axis_direction in ["left", "top"]:
            self.set_ticklabel_direction("-")
            self.set_axislabel_direction("-")
        else:
            self.set_ticklabel_direction("+")
            self.set_axislabel_direction("+")

    def set_ticklabel_direction(self, tick_direction):
        r"""
        Adjust the direction of the tick labels.

        Note that the *tick_direction*\s '+' and '-' are relative to the
        direction of the increasing coordinate.

        Parameters
        ----------
        tick_direction : {"+", "-"}
        """
        self._ticklabel_add_angle = _api.check_getitem(
            {"+": 0, "-": 180}, tick_direction=tick_direction)

    def invert_ticklabel_direction(self):
        self._ticklabel_add_angle = (self._ticklabel_add_angle + 180) % 360
        self.major_ticklabels.invert_axis_direction()
        self.minor_ticklabels.invert_axis_direction()

    def set_axislabel_direction(self, label_direction):
        r"""
        Adjust the direction of the axis label.

        Note that the *label_direction*\s '+' and '-' are relative to the
        direction of the increasing coordinate.

        Parameters
        ----------
        label_direction : {"+", "-"}
        """
        self._axislabel_add_angle = _api.check_getitem(
            {"+": 0, "-": 180}, label_direction=label_direction)

    def get_transform(self):
        return self.axes.transAxes + self.offset_transform

    def get_helper(self):
        """
        Return axis artist helper instance.
        """
        return self._axis_artist_helper

    def set_axisline_style(self, axisline_style=None, **kwargs):
        """
        Set the axisline style.

        The new style is completely defined by the passed attributes. Existing
        style attributes are forgotten.

        Parameters
        ----------
        axisline_style : str or None
            The line style, e.g. '->', optionally followed by a comma-separated
            list of attributes. Alternatively, the attributes can be provided
            as keywords.

            If *None* this returns a string containing the available styles.

        Examples
        --------
        The following two commands are equal:

        >>> set_axisline_style("->,size=1.5")
        >>> set_axisline_style("->", size=1.5)
        """
        if axisline_style is None:
            return AxislineStyle.pprint_styles()

        if isinstance(axisline_style, AxislineStyle._Base):
            self._axisline_style = axisline_style
        else:
            self._axisline_style = AxislineStyle(axisline_style, **kwargs)

        self._init_line()

    def get_axisline_style(self):
        """Return the current axisline style."""
        return self._axisline_style

    def _init_line(self):
        """
        Initialize the *line* artist that is responsible to draw the axis line.
        """
        tran = (self._axis_artist_helper.get_line_transform(self.axes)
                + self.offset_transform)

        axisline_style = self.get_axisline_style()
        if axisline_style is None:
            self.line = PathPatch(
                self._axis_artist_helper.get_line(self.axes),
                color=mpl.rcParams['axes.edgecolor'],
                fill=False,
                linewidth=mpl.rcParams['axes.linewidth'],
                capstyle=mpl.rcParams['lines.solid_capstyle'],
                joinstyle=mpl.rcParams['lines.solid_joinstyle'],
                transform=tran)
        else:
            self.line = axisline_style(self, transform=tran)

    def _draw_line(self, renderer):
        self.line.set_path(self._axis_artist_helper.get_line(self.axes))
        if self.get_axisline_style() is not None:
            self.line.set_line_mutation_scale(self.major_ticklabels.get_size())
        self.line.draw(renderer)

    def _init_ticks(self, **kwargs):
        axis_name = self.axis.axis_name

        trans = (self._axis_artist_helper.get_tick_transform(self.axes)
                 + self.offset_transform)

        self.major_ticks = Ticks(
            kwargs.get(
                "major_tick_size",
                mpl.rcParams[f"{axis_name}tick.major.size"]),
            axis=self.axis, transform=trans)
        self.minor_ticks = Ticks(
            kwargs.get(
                "minor_tick_size",
                mpl.rcParams[f"{axis_name}tick.minor.size"]),
            axis=self.axis, transform=trans)

        size = mpl.rcParams[f"{axis_name}tick.labelsize"]
        self.major_ticklabels = TickLabels(
            axis=self.axis,
            axis_direction=self._axis_direction,
            figure=self.axes.get_figure(root=False),
            transform=trans,
            fontsize=size,
            pad=kwargs.get(
                "major_tick_pad", mpl.rcParams[f"{axis_name}tick.major.pad"]),
        )
        self.minor_ticklabels = TickLabels(
            axis=self.axis,
            axis_direction=self._axis_direction,
            figure=self.axes.get_figure(root=False),
            transform=trans,
            fontsize=size,
            pad=kwargs.get(
                "minor_tick_pad", mpl.rcParams[f"{axis_name}tick.minor.pad"]),
        )

    def _get_tick_info(self, tick_iter):
        """
        Return a pair of:

        - list of locs and angles for ticks
        - list of locs, angles and labels for ticklabels.
        """
        ticks_loc_angle = []
        ticklabels_loc_angle_label = []

        ticklabel_add_angle = self._ticklabel_add_angle

        for loc, angle_normal, angle_tangent, label in tick_iter:
            angle_label = angle_tangent - 90 + ticklabel_add_angle
            angle_tick = (angle_normal
                          if 90 <= (angle_label - angle_normal) % 360 <= 270
                          else angle_normal + 180)
            ticks_loc_angle.append([loc, angle_tick])
            ticklabels_loc_angle_label.append([loc, angle_label, label])

        return ticks_loc_angle, ticklabels_loc_angle_label

    def _update_ticks(self, renderer=None):
        # set extra pad for major and minor ticklabels: use ticksize of
        # majorticks even for minor ticks. not clear what is best.

        if renderer is None:
            renderer = self.get_figure(root=True)._get_renderer()

        dpi_cor = renderer.points_to_pixels(1.)
        if self.major_ticks.get_visible() and self.major_ticks.get_tick_out():
            ticklabel_pad = self.major_ticks._ticksize * dpi_cor
            self.major_ticklabels._external_pad = ticklabel_pad
            self.minor_ticklabels._external_pad = ticklabel_pad
        else:
            self.major_ticklabels._external_pad = 0
            self.minor_ticklabels._external_pad = 0

        majortick_iter, minortick_iter = \
            self._axis_artist_helper.get_tick_iterators(self.axes)

        tick_loc_angle, ticklabel_loc_angle_label = \
            self._get_tick_info(majortick_iter)
        self.major_ticks.set_locs_angles(tick_loc_angle)
        self.major_ticklabels.set_locs_angles_labels(ticklabel_loc_angle_label)

        tick_loc_angle, ticklabel_loc_angle_label = \
            self._get_tick_info(minortick_iter)
        self.minor_ticks.set_locs_angles(tick_loc_angle)
        self.minor_ticklabels.set_locs_angles_labels(ticklabel_loc_angle_label)

    def _draw_ticks(self, renderer):
        self._update_ticks(renderer)
        self.major_ticks.draw(renderer)
        self.major_ticklabels.draw(renderer)
        self.minor_ticks.draw(renderer)
        self.minor_ticklabels.draw(renderer)
        if (self.major_ticklabels.get_visible()
                or self.minor_ticklabels.get_visible()):
            self._draw_offsetText(renderer)

    _offsetText_pos = dict(left=(0, 1, "bottom", "right"),
                           right=(1, 1, "bottom", "left"),
                           bottom=(1, 0, "top", "right"),
                           top=(1, 1, "bottom", "right"))

    def _init_offsetText(self, direction):
        x, y, va, ha = self._offsetText_pos[direction]
        self.offsetText = mtext.Annotation(
            "",
            xy=(x, y), xycoords="axes fraction",
            xytext=(0, 0), textcoords="offset points",
            color=mpl.rcParams['xtick.color'],
            horizontalalignment=ha, verticalalignment=va,
        )
        self.offsetText.set_transform(IdentityTransform())
        self.axes._set_artist_props(self.offsetText)

    def _update_offsetText(self):
        self.offsetText.set_text(self.axis.major.formatter.get_offset())
        self.offsetText.set_size(self.major_ticklabels.get_size())
        offset = (self.major_ticklabels.get_pad()
                  + self.major_ticklabels.get_size()
                  + 2)
        self.offsetText.xyann = (0, offset)

    def _draw_offsetText(self, renderer):
        self._update_offsetText()
        self.offsetText.draw(renderer)

    def _init_label(self, **kwargs):
        tr = (self._axis_artist_helper.get_axislabel_transform(self.axes)
              + self.offset_transform)
        self.label = AxisLabel(
            0, 0, "__from_axes__",
            color="auto",
            fontsize=kwargs.get("labelsize", mpl.rcParams['axes.labelsize']),
            fontweight=mpl.rcParams['axes.labelweight'],
            axis=self.axis,
            transform=tr,
            axis_direction=self._axis_direction,
        )
        self.label.set_figure(self.axes.get_figure(root=False))
        labelpad = kwargs.get("labelpad", 5)
        self.label.set_pad(labelpad)

    def _update_label(self, renderer):
        if not self.label.get_visible():
            return

        if self._ticklabel_add_angle != self._axislabel_add_angle:
            if ((self.major_ticks.get_visible()
                 and not self.major_ticks.get_tick_out())
                or (self.minor_ticks.get_visible()
                    and not self.major_ticks.get_tick_out())):
                axislabel_pad = self.major_ticks._ticksize
            else:
                axislabel_pad = 0
        else:
            axislabel_pad = max(self.major_ticklabels._axislabel_pad,
                                self.minor_ticklabels._axislabel_pad)

        self.label._external_pad = axislabel_pad

        xy, angle_tangent = \
            self._axis_artist_helper.get_axislabel_pos_angle(self.axes)
        if xy is None:
            return

        angle_label = angle_tangent - 90

        x, y = xy
        self.label._ref_angle = angle_label + self._axislabel_add_angle
        self.label.set(x=x, y=y)

    def _draw_label(self, renderer):
        self._update_label(renderer)
        self.label.draw(renderer)

    def set_label(self, s):
        # docstring inherited
        self.label.set_text(s)

    def get_tightbbox(self, renderer=None):
        if not self.get_visible():
            return
        self._axis_artist_helper.update_lim(self.axes)
        self._update_ticks(renderer)
        self._update_label(renderer)

        self.line.set_path(self._axis_artist_helper.get_line(self.axes))
        if self.get_axisline_style() is not None:
            self.line.set_line_mutation_scale(self.major_ticklabels.get_size())

        bb = [
            *self.major_ticklabels.get_window_extents(renderer),
            *self.minor_ticklabels.get_window_extents(renderer),
            self.label.get_window_extent(renderer),
            self.offsetText.get_window_extent(renderer),
            self.line.get_window_extent(renderer),
        ]
        bb = [b for b in bb if b and (b.width != 0 or b.height != 0)]
        if bb:
            _bbox = Bbox.union(bb)
            return _bbox
        else:
            return None

    @martist.allow_rasterization
    def draw(self, renderer):
        # docstring inherited
        if not self.get_visible():
            return
        renderer.open_group(__name__, gid=self.get_gid())
        self._axis_artist_helper.update_lim(self.axes)
        self._draw_ticks(renderer)
        self._draw_line(renderer)
        self._draw_label(renderer)
        renderer.close_group(__name__)

    def toggle(self, all=None, ticks=None, ticklabels=None, label=None):
        """
        Toggle visibility of ticks, ticklabels, and (axis) label.
        To turn all off, ::

          axis.toggle(all=False)

        To turn all off but ticks on ::

          axis.toggle(all=False, ticks=True)

        To turn all on but (axis) label off ::

          axis.toggle(all=True, label=False)

        """
        if all:
            _ticks, _ticklabels, _label = True, True, True
        elif all is not None:
            _ticks, _ticklabels, _label = False, False, False
        else:
            _ticks, _ticklabels, _label = None, None, None

        if ticks is not None:
            _ticks = ticks
        if ticklabels is not None:
            _ticklabels = ticklabels
        if label is not None:
            _label = label

        if _ticks is not None:
            self.major_ticks.set_visible(_ticks)
            self.minor_ticks.set_visible(_ticks)
        if _ticklabels is not None:
            self.major_ticklabels.set_visible(_ticklabels)
            self.minor_ticklabels.set_visible(_ticklabels)
        if _label is not None:
            self.label.set_visible(_label)

# === NexusCore/openenv\Lib\site-packages\matplotlib\path.py ===
r"""
A module for dealing with the polylines used throughout Matplotlib.

The primary class for polyline handling in Matplotlib is `Path`.  Almost all
vector drawing makes use of `Path`\s somewhere in the drawing pipeline.

Whilst a `Path` instance itself cannot be drawn, some `.Artist` subclasses,
such as `.PathPatch` and `.PathCollection`, can be used for convenient `Path`
visualisation.
"""

import copy
from functools import lru_cache
from weakref import WeakValueDictionary

import numpy as np

import matplotlib as mpl
from . import _api, _path
from .cbook import _to_unmasked_float_array, simple_linear_interpolation
from .bezier import BezierSegment


class Path:
    """
    A series of possibly disconnected, possibly closed, line and curve
    segments.

    The underlying storage is made up of two parallel numpy arrays:

    - *vertices*: an (N, 2) float array of vertices
    - *codes*: an N-length `numpy.uint8` array of path codes, or None

    These two arrays always have the same length in the first
    dimension.  For example, to represent a cubic curve, you must
    provide three vertices and three `CURVE4` codes.

    The code types are:

    - `STOP`   :  1 vertex (ignored)
        A marker for the end of the entire path (currently not required and
        ignored)

    - `MOVETO` :  1 vertex
        Pick up the pen and move to the given vertex.

    - `LINETO` :  1 vertex
        Draw a line from the current position to the given vertex.

    - `CURVE3` :  1 control point, 1 endpoint
        Draw a quadratic Bézier curve from the current position, with the given
        control point, to the given end point.

    - `CURVE4` :  2 control points, 1 endpoint
        Draw a cubic Bézier curve from the current position, with the given
        control points, to the given end point.

    - `CLOSEPOLY` : 1 vertex (ignored)
        Draw a line segment to the start point of the current polyline.

    If *codes* is None, it is interpreted as a `MOVETO` followed by a series
    of `LINETO`.

    Users of Path objects should not access the vertices and codes arrays
    directly.  Instead, they should use `iter_segments` or `cleaned` to get the
    vertex/code pairs.  This helps, in particular, to consistently handle the
    case of *codes* being None.

    Some behavior of Path objects can be controlled by rcParams. See the
    rcParams whose keys start with 'path.'.

    .. note::

        The vertices and codes arrays should be treated as
        immutable -- there are a number of optimizations and assumptions
        made up front in the constructor that will not change when the
        data changes.
    """

    code_type = np.uint8

    # Path codes
    STOP = code_type(0)         # 1 vertex
    MOVETO = code_type(1)       # 1 vertex
    LINETO = code_type(2)       # 1 vertex
    CURVE3 = code_type(3)       # 2 vertices
    CURVE4 = code_type(4)       # 3 vertices
    CLOSEPOLY = code_type(79)   # 1 vertex

    #: A dictionary mapping Path codes to the number of vertices that the
    #: code expects.
    NUM_VERTICES_FOR_CODE = {STOP: 1,
                             MOVETO: 1,
                             LINETO: 1,
                             CURVE3: 2,
                             CURVE4: 3,
                             CLOSEPOLY: 1}

    def __init__(self, vertices, codes=None, _interpolation_steps=1,
                 closed=False, readonly=False):
        """
        Create a new path with the given vertices and codes.

        Parameters
        ----------
        vertices : (N, 2) array-like
            The path vertices, as an array, masked array or sequence of pairs.
            Masked values, if any, will be converted to NaNs, which are then
            handled correctly by the Agg PathIterator and other consumers of
            path data, such as :meth:`iter_segments`.
        codes : array-like or None, optional
            N-length array of integers representing the codes of the path.
            If not None, codes must be the same length as vertices.
            If None, *vertices* will be treated as a series of line segments.
        _interpolation_steps : int, optional
            Used as a hint to certain projections, such as Polar, that this
            path should be linearly interpolated immediately before drawing.
            This attribute is primarily an implementation detail and is not
            intended for public use.
        closed : bool, optional
            If *codes* is None and closed is True, vertices will be treated as
            line segments of a closed polygon.  Note that the last vertex will
            then be ignored (as the corresponding code will be set to
            `CLOSEPOLY`).
        readonly : bool, optional
            Makes the path behave in an immutable way and sets the vertices
            and codes as read-only arrays.
        """
        vertices = _to_unmasked_float_array(vertices)
        _api.check_shape((None, 2), vertices=vertices)

        if codes is not None and len(vertices):
            codes = np.asarray(codes, self.code_type)
            if codes.ndim != 1 or len(codes) != len(vertices):
                raise ValueError("'codes' must be a 1D list or array with the "
                                 "same length of 'vertices'. "
                                 f"Your vertices have shape {vertices.shape} "
                                 f"but your codes have shape {codes.shape}")
            if len(codes) and codes[0] != self.MOVETO:
                raise ValueError("The first element of 'code' must be equal "
                                 f"to 'MOVETO' ({self.MOVETO}).  "
                                 f"Your first code is {codes[0]}")
        elif closed and len(vertices):
            codes = np.empty(len(vertices), dtype=self.code_type)
            codes[0] = self.MOVETO
            codes[1:-1] = self.LINETO
            codes[-1] = self.CLOSEPOLY

        self._vertices = vertices
        self._codes = codes
        self._interpolation_steps = _interpolation_steps
        self._update_values()

        if readonly:
            self._vertices.flags.writeable = False
            if self._codes is not None:
                self._codes.flags.writeable = False
            self._readonly = True
        else:
            self._readonly = False

    @classmethod
    def _fast_from_codes_and_verts(cls, verts, codes, internals_from=None):
        """
        Create a Path instance without the expense of calling the constructor.

        Parameters
        ----------
        verts : array-like
        codes : array
        internals_from : Path or None
            If not None, another `Path` from which the attributes
            ``should_simplify``, ``simplify_threshold``, and
            ``interpolation_steps`` will be copied.  Note that ``readonly`` is
            never copied, and always set to ``False`` by this constructor.
        """
        pth = cls.__new__(cls)
        pth._vertices = _to_unmasked_float_array(verts)
        pth._codes = codes
        pth._readonly = False
        if internals_from is not None:
            pth._should_simplify = internals_from._should_simplify
            pth._simplify_threshold = internals_from._simplify_threshold
            pth._interpolation_steps = internals_from._interpolation_steps
        else:
            pth._should_simplify = True
            pth._simplify_threshold = mpl.rcParams['path.simplify_threshold']
            pth._interpolation_steps = 1
        return pth

    @classmethod
    def _create_closed(cls, vertices):
        """
        Create a closed polygonal path going through *vertices*.

        Unlike ``Path(..., closed=True)``, *vertices* should **not** end with
        an entry for the CLOSEPATH; this entry is added by `._create_closed`.
        """
        v = _to_unmasked_float_array(vertices)
        return cls(np.concatenate([v, v[:1]]), closed=True)

    def _update_values(self):
        self._simplify_threshold = mpl.rcParams['path.simplify_threshold']
        self._should_simplify = (
            self._simplify_threshold > 0 and
            mpl.rcParams['path.simplify'] and
            len(self._vertices) >= 128 and
            (self._codes is None or np.all(self._codes <= Path.LINETO))
        )

    @property
    def vertices(self):
        """The vertices of the `Path` as an (N, 2) array."""
        return self._vertices

    @vertices.setter
    def vertices(self, vertices):
        if self._readonly:
            raise AttributeError("Can't set vertices on a readonly Path")
        self._vertices = vertices
        self._update_values()

    @property
    def codes(self):
        """
        The list of codes in the `Path` as a 1D array.

        Each code is one of `STOP`, `MOVETO`, `LINETO`, `CURVE3`, `CURVE4` or
        `CLOSEPOLY`.  For codes that correspond to more than one vertex
        (`CURVE3` and `CURVE4`), that code will be repeated so that the length
        of `vertices` and `codes` is always the same.
        """
        return self._codes

    @codes.setter
    def codes(self, codes):
        if self._readonly:
            raise AttributeError("Can't set codes on a readonly Path")
        self._codes = codes
        self._update_values()

    @property
    def simplify_threshold(self):
        """
        The fraction of a pixel difference below which vertices will
        be simplified out.
        """
        return self._simplify_threshold

    @simplify_threshold.setter
    def simplify_threshold(self, threshold):
        self._simplify_threshold = threshold

    @property
    def should_simplify(self):
        """
        `True` if the vertices array should be simplified.
        """
        return self._should_simplify

    @should_simplify.setter
    def should_simplify(self, should_simplify):
        self._should_simplify = should_simplify

    @property
    def readonly(self):
        """
        `True` if the `Path` is read-only.
        """
        return self._readonly

    def copy(self):
        """
        Return a shallow copy of the `Path`, which will share the
        vertices and codes with the source `Path`.
        """
        return copy.copy(self)

    def __deepcopy__(self, memo=None):
        """
        Return a deepcopy of the `Path`.  The `Path` will not be
        readonly, even if the source `Path` is.
        """
        # Deepcopying arrays (vertices, codes) strips the writeable=False flag.
        p = copy.deepcopy(super(), memo)
        p._readonly = False
        return p

    deepcopy = __deepcopy__

    @classmethod
    def make_compound_path_from_polys(cls, XY):
        """
        Make a compound `Path` object to draw a number of polygons with equal
        numbers of sides.

        .. plot:: gallery/misc/histogram_path.py

        Parameters
        ----------
        XY : (numpolys, numsides, 2) array
        """
        # for each poly: 1 for the MOVETO, (numsides-1) for the LINETO, 1 for
        # the CLOSEPOLY; the vert for the closepoly is ignored but we still
        # need it to keep the codes aligned with the vertices
        numpolys, numsides, two = XY.shape
        if two != 2:
            raise ValueError("The third dimension of 'XY' must be 2")
        stride = numsides + 1
        nverts = numpolys * stride
        verts = np.zeros((nverts, 2))
        codes = np.full(nverts, cls.LINETO, dtype=cls.code_type)
        codes[0::stride] = cls.MOVETO
        codes[numsides::stride] = cls.CLOSEPOLY
        for i in range(numsides):
            verts[i::stride] = XY[:, i]
        return cls(verts, codes)

    @classmethod
    def make_compound_path(cls, *args):
        r"""
        Concatenate a list of `Path`\s into a single `Path`, removing all `STOP`\s.
        """
        if not args:
            return Path(np.empty([0, 2], dtype=np.float32))
        vertices = np.concatenate([path.vertices for path in args])
        codes = np.empty(len(vertices), dtype=cls.code_type)
        i = 0
        for path in args:
            size = len(path.vertices)
            if path.codes is None:
                if size:
                    codes[i] = cls.MOVETO
                    codes[i+1:i+size] = cls.LINETO
            else:
                codes[i:i+size] = path.codes
            i += size
        not_stop_mask = codes != cls.STOP  # Remove STOPs, as internal STOPs are a bug.
        return cls(vertices[not_stop_mask], codes[not_stop_mask])

    def __repr__(self):
        return f"Path({self.vertices!r}, {self.codes!r})"

    def __len__(self):
        return len(self.vertices)

    def iter_segments(self, transform=None, remove_nans=True, clip=None,
                      snap=False, stroke_width=1.0, simplify=None,
                      curves=True, sketch=None):
        """
        Iterate over all curve segments in the path.

        Each iteration returns a pair ``(vertices, code)``, where ``vertices``
        is a sequence of 1-3 coordinate pairs, and ``code`` is a `Path` code.

        Additionally, this method can provide a number of standard cleanups and
        conversions to the path.

        Parameters
        ----------
        transform : None or :class:`~matplotlib.transforms.Transform`
            If not None, the given affine transformation will be applied to the
            path.
        remove_nans : bool, optional
            Whether to remove all NaNs from the path and skip over them using
            MOVETO commands.
        clip : None or (float, float, float, float), optional
            If not None, must be a four-tuple (x1, y1, x2, y2)
            defining a rectangle in which to clip the path.
        snap : None or bool, optional
            If True, snap all nodes to pixels; if False, don't snap them.
            If None, snap if the path contains only segments
            parallel to the x or y axes, and no more than 1024 of them.
        stroke_width : float, optional
            The width of the stroke being drawn (used for path snapping).
        simplify : None or bool, optional
            Whether to simplify the path by removing vertices
            that do not affect its appearance.  If None, use the
            :attr:`should_simplify` attribute.  See also :rc:`path.simplify`
            and :rc:`path.simplify_threshold`.
        curves : bool, optional
            If True, curve segments will be returned as curve segments.
            If False, all curves will be converted to line segments.
        sketch : None or sequence, optional
            If not None, must be a 3-tuple of the form
            (scale, length, randomness), representing the sketch parameters.
        """
        if not len(self):
            return

        cleaned = self.cleaned(transform=transform,
                               remove_nans=remove_nans, clip=clip,
                               snap=snap, stroke_width=stroke_width,
                               simplify=simplify, curves=curves,
                               sketch=sketch)

        # Cache these object lookups for performance in the loop.
        NUM_VERTICES_FOR_CODE = self.NUM_VERTICES_FOR_CODE
        STOP = self.STOP

        vertices = iter(cleaned.vertices)
        codes = iter(cleaned.codes)
        for curr_vertices, code in zip(vertices, codes):
            if code == STOP:
                break
            extra_vertices = NUM_VERTICES_FOR_CODE[code] - 1
            if extra_vertices:
                for i in range(extra_vertices):
                    next(codes)
                    curr_vertices = np.append(curr_vertices, next(vertices))
            yield curr_vertices, code

    def iter_bezier(self, **kwargs):
        """
        Iterate over each Bézier curve (lines included) in a `Path`.

        Parameters
        ----------
        **kwargs
            Forwarded to `.iter_segments`.

        Yields
        ------
        B : `~matplotlib.bezier.BezierSegment`
            The Bézier curves that make up the current path. Note in particular
            that freestanding points are Bézier curves of order 0, and lines
            are Bézier curves of order 1 (with two control points).
        code : `~matplotlib.path.Path.code_type`
            The code describing what kind of curve is being returned.
            `MOVETO`, `LINETO`, `CURVE3`, and `CURVE4` correspond to
            Bézier curves with 1, 2, 3, and 4 control points (respectively).
            `CLOSEPOLY` is a `LINETO` with the control points correctly
            chosen based on the start/end points of the current stroke.
        """
        first_vert = None
        prev_vert = None
        for verts, code in self.iter_segments(**kwargs):
            if first_vert is None:
                if code != Path.MOVETO:
                    raise ValueError("Malformed path, must start with MOVETO.")
            if code == Path.MOVETO:  # a point is like "CURVE1"
                first_vert = verts
                yield BezierSegment(np.array([first_vert])), code
            elif code == Path.LINETO:  # "CURVE2"
                yield BezierSegment(np.array([prev_vert, verts])), code
            elif code == Path.CURVE3:
                yield BezierSegment(np.array([prev_vert, verts[:2],
                                              verts[2:]])), code
            elif code == Path.CURVE4:
                yield BezierSegment(np.array([prev_vert, verts[:2],
                                              verts[2:4], verts[4:]])), code
            elif code == Path.CLOSEPOLY:
                yield BezierSegment(np.array([prev_vert, first_vert])), code
            elif code == Path.STOP:
                return
            else:
                raise ValueError(f"Invalid Path.code_type: {code}")
            prev_vert = verts[-2:]

    def _iter_connected_components(self):
        """Return subpaths split at MOVETOs."""
        if self.codes is None:
            yield self
        else:
            idxs = np.append((self.codes == Path.MOVETO).nonzero()[0], len(self.codes))
            for sl in map(slice, idxs, idxs[1:]):
                yield Path._fast_from_codes_and_verts(
                    self.vertices[sl], self.codes[sl], self)

    def cleaned(self, transform=None, remove_nans=False, clip=None,
                *, simplify=False, curves=False,
                stroke_width=1.0, snap=False, sketch=None):
        """
        Return a new `Path` with vertices and codes cleaned according to the
        parameters.

        See Also
        --------
        Path.iter_segments : for details of the keyword arguments.
        """
        vertices, codes = _path.cleanup_path(
            self, transform, remove_nans, clip, snap, stroke_width, simplify,
            curves, sketch)
        pth = Path._fast_from_codes_and_verts(vertices, codes, self)
        if not simplify:
            pth._should_simplify = False
        return pth

    def transformed(self, transform):
        """
        Return a transformed copy of the path.

        See Also
        --------
        matplotlib.transforms.TransformedPath
            A specialized path class that will cache the transformed result and
            automatically update when the transform changes.
        """
        return Path(transform.transform(self.vertices), self.codes,
                    self._interpolation_steps)

    def contains_point(self, point, transform=None, radius=0.0):
        """
        Return whether the area enclosed by the path contains the given point.

        The path is always treated as closed; i.e. if the last code is not
        `CLOSEPOLY` an implicit segment connecting the last vertex to the first
        vertex is assumed.

        Parameters
        ----------
        point : (float, float)
            The point (x, y) to check.
        transform : `~matplotlib.transforms.Transform`, optional
            If not ``None``, *point* will be compared to ``self`` transformed
            by *transform*; i.e. for a correct check, *transform* should
            transform the path into the coordinate system of *point*.
        radius : float, default: 0
            Additional margin on the path in coordinates of *point*.
            The path is extended tangentially by *radius/2*; i.e. if you would
            draw the path with a linewidth of *radius*, all points on the line
            would still be considered to be contained in the area. Conversely,
            negative values shrink the area: Points on the imaginary line
            will be considered outside the area.

        Returns
        -------
        bool

        Notes
        -----
        The current algorithm has some limitations:

        - The result is undefined for points exactly at the boundary
          (i.e. at the path shifted by *radius/2*).
        - The result is undefined if there is no enclosed area, i.e. all
          vertices are on a straight line.
        - If bounding lines start to cross each other due to *radius* shift,
          the result is not guaranteed to be correct.
        """
        if transform is not None:
            transform = transform.frozen()
        # `point_in_path` does not handle nonlinear transforms, so we
        # transform the path ourselves.  If *transform* is affine, letting
        # `point_in_path` handle the transform avoids allocating an extra
        # buffer.
        if transform and not transform.is_affine:
            self = transform.transform_path(self)
            transform = None
        return _path.point_in_path(point[0], point[1], radius, self, transform)

    def contains_points(self, points, transform=None, radius=0.0):
        """
        Return whether the area enclosed by the path contains the given points.

        The path is always treated as closed; i.e. if the last code is not
        `CLOSEPOLY` an implicit segment connecting the last vertex to the first
        vertex is assumed.

        Parameters
        ----------
        points : (N, 2) array
            The points to check. Columns contain x and y values.
        transform : `~matplotlib.transforms.Transform`, optional
            If not ``None``, *points* will be compared to ``self`` transformed
            by *transform*; i.e. for a correct check, *transform* should
            transform the path into the coordinate system of *points*.
        radius : float, default: 0
            Additional margin on the path in coordinates of *points*.
            The path is extended tangentially by *radius/2*; i.e. if you would
            draw the path with a linewidth of *radius*, all points on the line
            would still be considered to be contained in the area. Conversely,
            negative values shrink the area: Points on the imaginary line
            will be considered outside the area.

        Returns
        -------
        length-N bool array

        Notes
        -----
        The current algorithm has some limitations:

        - The result is undefined for points exactly at the boundary
          (i.e. at the path shifted by *radius/2*).
        - The result is undefined if there is no enclosed area, i.e. all
          vertices are on a straight line.
        - If bounding lines start to cross each other due to *radius* shift,
          the result is not guaranteed to be correct.
        """
        if transform is not None:
            transform = transform.frozen()
        result = _path.points_in_path(points, radius, self, transform)
        return result.astype('bool')

    def contains_path(self, path, transform=None):
        """
        Return whether this (closed) path completely contains the given path.

        If *transform* is not ``None``, the path will be transformed before
        checking for containment.
        """
        if transform is not None:
            transform = transform.frozen()
        return _path.path_in_path(self, None, path, transform)

    def get_extents(self, transform=None, **kwargs):
        """
        Get Bbox of the path.

        Parameters
        ----------
        transform : `~matplotlib.transforms.Transform`, optional
            Transform to apply to path before computing extents, if any.
        **kwargs
            Forwarded to `.iter_bezier`.

        Returns
        -------
        matplotlib.transforms.Bbox
            The extents of the path Bbox([[xmin, ymin], [xmax, ymax]])
        """
        from .transforms import Bbox
        if transform is not None:
            self = transform.transform_path(self)
        if self.codes is None:
            xys = self.vertices
        elif len(np.intersect1d(self.codes, [Path.CURVE3, Path.CURVE4])) == 0:
            # Optimization for the straight line case.
            # Instead of iterating through each curve, consider
            # each line segment's end-points
            # (recall that STOP and CLOSEPOLY vertices are ignored)
            xys = self.vertices[np.isin(self.codes,
                                        [Path.MOVETO, Path.LINETO])]
        else:
            xys = []
            for curve, code in self.iter_bezier(**kwargs):
                # places where the derivative is zero can be extrema
                _, dzeros = curve.axis_aligned_extrema()
                # as can the ends of the curve
                xys.append(curve([0, *dzeros, 1]))
            xys = np.concatenate(xys)
        if len(xys):
            return Bbox([xys.min(axis=0), xys.max(axis=0)])
        else:
            return Bbox.null()

    def intersects_path(self, other, filled=True):
        """
        Return whether if this path intersects another given path.

        If *filled* is True, then this also returns True if one path completely
        encloses the other (i.e., the paths are treated as filled).
        """
        return _path.path_intersects_path(self, other, filled)

    def intersects_bbox(self, bbox, filled=True):
        """
        Return whether this path intersects a given `~.transforms.Bbox`.

        If *filled* is True, then this also returns True if the path completely
        encloses the `.Bbox` (i.e., the path is treated as filled).

        The bounding box is always considered filled.
        """
        return _path.path_intersects_rectangle(
            self, bbox.x0, bbox.y0, bbox.x1, bbox.y1, filled)

    def interpolated(self, steps):
        """
        Return a new path with each segment divided into *steps* parts.

        Codes other than `LINETO`, `MOVETO`, and `CLOSEPOLY` are not handled correctly.

        Parameters
        ----------
        steps : int
            The number of segments in the new path for each in the original.

        Returns
        -------
        Path
            The interpolated path.
        """
        if steps == 1 or len(self) == 0:
            return self

        if self.codes is not None and self.MOVETO in self.codes[1:]:
            return self.make_compound_path(
                *(p.interpolated(steps) for p in self._iter_connected_components()))

        if self.codes is not None and self.CLOSEPOLY in self.codes and not np.all(
                self.vertices[self.codes == self.CLOSEPOLY] == self.vertices[0]):
            vertices = self.vertices.copy()
            vertices[self.codes == self.CLOSEPOLY] = vertices[0]
        else:
            vertices = self.vertices

        vertices = simple_linear_interpolation(vertices, steps)
        codes = self.codes
        if codes is not None:
            new_codes = np.full((len(codes) - 1) * steps + 1, Path.LINETO,
                                dtype=self.code_type)
            new_codes[0::steps] = codes
        else:
            new_codes = None
        return Path(vertices, new_codes)

    def to_polygons(self, transform=None, width=0, height=0, closed_only=True):
        """
        Convert this path to a list of polygons or polylines.  Each
        polygon/polyline is an (N, 2) array of vertices.  In other words,
        each polygon has no `MOVETO` instructions or curves.  This
        is useful for displaying in backends that do not support
        compound paths or Bézier curves.

        If *width* and *height* are both non-zero then the lines will
        be simplified so that vertices outside of (0, 0), (width,
        height) will be clipped.

        The resulting polygons will be simplified if the
        :attr:`Path.should_simplify` attribute of the path is `True`.

        If *closed_only* is `True` (default), only closed polygons,
        with the last point being the same as the first point, will be
        returned.  Any unclosed polylines in the path will be
        explicitly closed.  If *closed_only* is `False`, any unclosed
        polygons in the path will be returned as unclosed polygons,
        and the closed polygons will be returned explicitly closed by
        setting the last point to the same as the first point.
        """
        if len(self.vertices) == 0:
            return []

        if transform is not None:
            transform = transform.frozen()

        if self.codes is None and (width == 0 or height == 0):
            vertices = self.vertices
            if closed_only:
                if len(vertices) < 3:
                    return []
                elif np.any(vertices[0] != vertices[-1]):
                    vertices = [*vertices, vertices[0]]

            if transform is None:
                return [vertices]
            else:
                return [transform.transform(vertices)]

        # Deal with the case where there are curves and/or multiple
        # subpaths (using extension code)
        return _path.convert_path_to_polygons(
            self, transform, width, height, closed_only)

    _unit_rectangle = None

    @classmethod
    def unit_rectangle(cls):
        """
        Return a `Path` instance of the unit rectangle from (0, 0) to (1, 1).
        """
        if cls._unit_rectangle is None:
            cls._unit_rectangle = cls([[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]],
                                      closed=True, readonly=True)
        return cls._unit_rectangle

    _unit_regular_polygons = WeakValueDictionary()

    @classmethod
    def unit_regular_polygon(cls, numVertices):
        """
        Return a :class:`Path` instance for a unit regular polygon with the
        given *numVertices* such that the circumscribing circle has radius 1.0,
        centered at (0, 0).
        """
        if numVertices <= 16:
            path = cls._unit_regular_polygons.get(numVertices)
        else:
            path = None
        if path is None:
            theta = ((2 * np.pi / numVertices) * np.arange(numVertices + 1)
                     # This initial rotation is to make sure the polygon always
                     # "points-up".
                     + np.pi / 2)
            verts = np.column_stack((np.cos(theta), np.sin(theta)))
            path = cls(verts, closed=True, readonly=True)
            if numVertices <= 16:
                cls._unit_regular_polygons[numVertices] = path
        return path

    _unit_regular_stars = WeakValueDictionary()

    @classmethod
    def unit_regular_star(cls, numVertices, innerCircle=0.5):
        """
        Return a :class:`Path` for a unit regular star with the given
        numVertices and radius of 1.0, centered at (0, 0).
        """
        if numVertices <= 16:
            path = cls._unit_regular_stars.get((numVertices, innerCircle))
        else:
            path = None
        if path is None:
            ns2 = numVertices * 2
            theta = (2*np.pi/ns2 * np.arange(ns2 + 1))
            # This initial rotation is to make sure the polygon always
            # "points-up"
            theta += np.pi / 2.0
            r = np.ones(ns2 + 1)
            r[1::2] = innerCircle
            verts = (r * np.vstack((np.cos(theta), np.sin(theta)))).T
            path = cls(verts, closed=True, readonly=True)
            if numVertices <= 16:
                cls._unit_regular_stars[(numVertices, innerCircle)] = path
        return path

    @classmethod
    def unit_regular_asterisk(cls, numVertices):
        """
        Return a :class:`Path` for a unit regular asterisk with the given
        numVertices and radius of 1.0, centered at (0, 0).
        """
        return cls.unit_regular_star(numVertices, 0.0)

    _unit_circle = None

    @classmethod
    def unit_circle(cls):
        """
        Return the readonly :class:`Path` of the unit circle.

        For most cases, :func:`Path.circle` will be what you want.
        """
        if cls._unit_circle is None:
            cls._unit_circle = cls.circle(center=(0, 0), radius=1,
                                          readonly=True)
        return cls._unit_circle

    @classmethod
    def circle(cls, center=(0., 0.), radius=1., readonly=False):
        """
        Return a `Path` representing a circle of a given radius and center.

        Parameters
        ----------
        center : (float, float), default: (0, 0)
            The center of the circle.
        radius : float, default: 1
            The radius of the circle.
        readonly : bool
            Whether the created path should have the "readonly" argument
            set when creating the Path instance.

        Notes
        -----
        The circle is approximated using 8 cubic Bézier curves, as described in

          Lancaster, Don.  `Approximating a Circle or an Ellipse Using Four
          Bezier Cubic Splines <https://www.tinaja.com/glib/ellipse4.pdf>`_.
        """
        MAGIC = 0.2652031
        SQRTHALF = np.sqrt(0.5)
        MAGIC45 = SQRTHALF * MAGIC

        vertices = np.array([[0.0, -1.0],

                             [MAGIC, -1.0],
                             [SQRTHALF-MAGIC45, -SQRTHALF-MAGIC45],
                             [SQRTHALF, -SQRTHALF],

                             [SQRTHALF+MAGIC45, -SQRTHALF+MAGIC45],
                             [1.0, -MAGIC],
                             [1.0, 0.0],

                             [1.0, MAGIC],
                             [SQRTHALF+MAGIC45, SQRTHALF-MAGIC45],
                             [SQRTHALF, SQRTHALF],

                             [SQRTHALF-MAGIC45, SQRTHALF+MAGIC45],
                             [MAGIC, 1.0],
                             [0.0, 1.0],

                             [-MAGIC, 1.0],
                             [-SQRTHALF+MAGIC45, SQRTHALF+MAGIC45],
                             [-SQRTHALF, SQRTHALF],

                             [-SQRTHALF-MAGIC45, SQRTHALF-MAGIC45],
                             [-1.0, MAGIC],
                             [-1.0, 0.0],

                             [-1.0, -MAGIC],
                             [-SQRTHALF-MAGIC45, -SQRTHALF+MAGIC45],
                             [-SQRTHALF, -SQRTHALF],

                             [-SQRTHALF+MAGIC45, -SQRTHALF-MAGIC45],
                             [-MAGIC, -1.0],
                             [0.0, -1.0],

                             [0.0, -1.0]],
                            dtype=float)

        codes = [cls.CURVE4] * 26
        codes[0] = cls.MOVETO
        codes[-1] = cls.CLOSEPOLY
        return Path(vertices * radius + center, codes, readonly=readonly)

    _unit_circle_righthalf = None

    @classmethod
    def unit_circle_righthalf(cls):
        """
        Return a `Path` of the right half of a unit circle.

        See `Path.circle` for the reference on the approximation used.
        """
        if cls._unit_circle_righthalf is None:
            MAGIC = 0.2652031
            SQRTHALF = np.sqrt(0.5)
            MAGIC45 = SQRTHALF * MAGIC

            vertices = np.array(
                [[0.0, -1.0],

                 [MAGIC, -1.0],
                 [SQRTHALF-MAGIC45, -SQRTHALF-MAGIC45],
                 [SQRTHALF, -SQRTHALF],

                 [SQRTHALF+MAGIC45, -SQRTHALF+MAGIC45],
                 [1.0, -MAGIC],
                 [1.0, 0.0],

                 [1.0, MAGIC],
                 [SQRTHALF+MAGIC45, SQRTHALF-MAGIC45],
                 [SQRTHALF, SQRTHALF],

                 [SQRTHALF-MAGIC45, SQRTHALF+MAGIC45],
                 [MAGIC, 1.0],
                 [0.0, 1.0],

                 [0.0, -1.0]],

                float)

            codes = np.full(14, cls.CURVE4, dtype=cls.code_type)
            codes[0] = cls.MOVETO
            codes[-1] = cls.CLOSEPOLY

            cls._unit_circle_righthalf = cls(vertices, codes, readonly=True)
        return cls._unit_circle_righthalf

    @classmethod
    def arc(cls, theta1, theta2, n=None, is_wedge=False):
        """
        Return a `Path` for the unit circle arc from angles *theta1* to
        *theta2* (in degrees).

        *theta2* is unwrapped to produce the shortest arc within 360 degrees.
        That is, if *theta2* > *theta1* + 360, the arc will be from *theta1* to
        *theta2* - 360 and not a full circle plus some extra overlap.

        If *n* is provided, it is the number of spline segments to make.
        If *n* is not provided, the number of spline segments is
        determined based on the delta between *theta1* and *theta2*.

           Masionobe, L.  2003.  `Drawing an elliptical arc using
           polylines, quadratic or cubic Bezier curves
           <https://web.archive.org/web/20190318044212/http://www.spaceroots.org/documents/ellipse/index.html>`_.
        """
        halfpi = np.pi * 0.5

        eta1 = theta1
        eta2 = theta2 - 360 * np.floor((theta2 - theta1) / 360)
        # Ensure 2pi range is not flattened to 0 due to floating-point errors,
        # but don't try to expand existing 0 range.
        if theta2 != theta1 and eta2 <= eta1:
            eta2 += 360
        eta1, eta2 = np.deg2rad([eta1, eta2])

        # number of curve segments to make
        if n is None:
            n = int(2 ** np.ceil((eta2 - eta1) / halfpi))
        if n < 1:
            raise ValueError("n must be >= 1 or None")

        deta = (eta2 - eta1) / n
        t = np.tan(0.5 * deta)
        alpha = np.sin(deta) * (np.sqrt(4.0 + 3.0 * t * t) - 1) / 3.0

        steps = np.linspace(eta1, eta2, n + 1, True)
        cos_eta = np.cos(steps)
        sin_eta = np.sin(steps)

        xA = cos_eta[:-1]
        yA = sin_eta[:-1]
        xA_dot = -yA
        yA_dot = xA

        xB = cos_eta[1:]
        yB = sin_eta[1:]
        xB_dot = -yB
        yB_dot = xB

        if is_wedge:
            length = n * 3 + 4
            vertices = np.zeros((length, 2), float)
            codes = np.full(length, cls.CURVE4, dtype=cls.code_type)
            vertices[1] = [xA[0], yA[0]]
            codes[0:2] = [cls.MOVETO, cls.LINETO]
            codes[-2:] = [cls.LINETO, cls.CLOSEPOLY]
            vertex_offset = 2
            end = length - 2
        else:
            length = n * 3 + 1
            vertices = np.empty((length, 2), float)
            codes = np.full(length, cls.CURVE4, dtype=cls.code_type)
            vertices[0] = [xA[0], yA[0]]
            codes[0] = cls.MOVETO
            vertex_offset = 1
            end = length

        vertices[vertex_offset:end:3, 0] = xA + alpha * xA_dot
        vertices[vertex_offset:end:3, 1] = yA + alpha * yA_dot
        vertices[vertex_offset+1:end:3, 0] = xB - alpha * xB_dot
        vertices[vertex_offset+1:end:3, 1] = yB - alpha * yB_dot
        vertices[vertex_offset+2:end:3, 0] = xB
        vertices[vertex_offset+2:end:3, 1] = yB

        return cls(vertices, codes, readonly=True)

    @classmethod
    def wedge(cls, theta1, theta2, n=None):
        """
        Return a `Path` for the unit circle wedge from angles *theta1* to
        *theta2* (in degrees).

        *theta2* is unwrapped to produce the shortest wedge within 360 degrees.
        That is, if *theta2* > *theta1* + 360, the wedge will be from *theta1*
        to *theta2* - 360 and not a full circle plus some extra overlap.

        If *n* is provided, it is the number of spline segments to make.
        If *n* is not provided, the number of spline segments is
        determined based on the delta between *theta1* and *theta2*.

        See `Path.arc` for the reference on the approximation used.
        """
        return cls.arc(theta1, theta2, n, True)

    @staticmethod
    @lru_cache(8)
    def hatch(hatchpattern, density=6):
        """
        Given a hatch specifier, *hatchpattern*, generates a `Path` that
        can be used in a repeated hatching pattern.  *density* is the
        number of lines per unit square.
        """
        from matplotlib.hatch import get_path
        return (get_path(hatchpattern, density)
                if hatchpattern is not None else None)

    def clip_to_bbox(self, bbox, inside=True):
        """
        Clip the path to the given bounding box.

        The path must be made up of one or more closed polygons.  This
        algorithm will not behave correctly for unclosed paths.

        If *inside* is `True`, clip to the inside of the box, otherwise
        to the outside of the box.
        """
        verts = _path.clip_path_to_rect(self, bbox, inside)
        paths = [Path(poly) for poly in verts]
        return self.make_compound_path(*paths)


def get_path_collection_extents(
        master_transform, paths, transforms, offsets, offset_transform):
    r"""
    Get bounding box of a `.PathCollection`\s internal objects.

    That is, given a sequence of `Path`\s, `.Transform`\s objects, and offsets, as found
    in a `.PathCollection`, return the bounding box that encapsulates all of them.

    Parameters
    ----------
    master_transform : `~matplotlib.transforms.Transform`
        Global transformation applied to all paths.
    paths : list of `Path`
    transforms : list of `~matplotlib.transforms.Affine2DBase`
        If non-empty, this overrides *master_transform*.
    offsets : (N, 2) array-like
    offset_transform : `~matplotlib.transforms.Affine2DBase`
        Transform applied to the offsets before offsetting the path.

    Notes
    -----
    The way that *paths*, *transforms* and *offsets* are combined follows the same
    method as for collections: each is iterated over independently, so if you have 3
    paths (A, B, C), 2 transforms (α, β) and 1 offset (O), their combinations are as
    follows:

    - (A, α, O)
    - (B, β, O)
    - (C, α, O)
    """
    from .transforms import Bbox
    if len(paths) == 0:
        raise ValueError("No paths provided")
    if len(offsets) == 0:
        raise ValueError("No offsets provided")
    extents, minpos = _path.get_path_collection_extents(
        master_transform, paths, np.atleast_3d(transforms),
        offsets, offset_transform)
    return Bbox.from_extents(*extents, minpos=minpos)

# === NexusCore/openenv\Lib\site-packages\pydantic\v1\main.py ===
import warnings
from abc import ABCMeta
from copy import deepcopy
from enum import Enum
from functools import partial
from pathlib import Path
from types import FunctionType, prepare_class, resolve_bases
from typing import (
    TYPE_CHECKING,
    AbstractSet,
    Any,
    Callable,
    ClassVar,
    Dict,
    List,
    Mapping,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    no_type_check,
    overload,
)

from typing_extensions import dataclass_transform

from pydantic.v1.class_validators import ValidatorGroup, extract_root_validators, extract_validators, inherit_validators
from pydantic.v1.config import BaseConfig, Extra, inherit_config, prepare_config
from pydantic.v1.error_wrappers import ErrorWrapper, ValidationError
from pydantic.v1.errors import ConfigError, DictError, ExtraError, MissingError
from pydantic.v1.fields import (
    MAPPING_LIKE_SHAPES,
    Field,
    ModelField,
    ModelPrivateAttr,
    PrivateAttr,
    Undefined,
    is_finalvar_with_default_val,
)
from pydantic.v1.json import custom_pydantic_encoder, pydantic_encoder
from pydantic.v1.parse import Protocol, load_file, load_str_bytes
from pydantic.v1.schema import default_ref_template, model_schema
from pydantic.v1.types import PyObject, StrBytes
from pydantic.v1.typing import (
    AnyCallable,
    get_args,
    get_origin,
    is_classvar,
    is_namedtuple,
    is_union,
    resolve_annotations,
    update_model_forward_refs,
)
from pydantic.v1.utils import (
    DUNDER_ATTRIBUTES,
    ROOT_KEY,
    ClassAttribute,
    GetterDict,
    Representation,
    ValueItems,
    generate_model_signature,
    is_valid_field,
    is_valid_private_name,
    lenient_issubclass,
    sequence_like,
    smart_deepcopy,
    unique_list,
    validate_field_name,
)

if TYPE_CHECKING:
    from inspect import Signature

    from pydantic.v1.class_validators import ValidatorListDict
    from pydantic.v1.types import ModelOrDc
    from pydantic.v1.typing import (
        AbstractSetIntStr,
        AnyClassMethod,
        CallableGenerator,
        DictAny,
        DictStrAny,
        MappingIntStrAny,
        ReprArgs,
        SetStr,
        TupleGenerator,
    )

    Model = TypeVar('Model', bound='BaseModel')

__all__ = 'BaseModel', 'create_model', 'validate_model'

_T = TypeVar('_T')


def validate_custom_root_type(fields: Dict[str, ModelField]) -> None:
    if len(fields) > 1:
        raise ValueError(f'{ROOT_KEY} cannot be mixed with other fields')


def generate_hash_function(frozen: bool) -> Optional[Callable[[Any], int]]:
    def hash_function(self_: Any) -> int:
        return hash(self_.__class__) + hash(tuple(self_.__dict__.values()))

    return hash_function if frozen else None


# If a field is of type `Callable`, its default value should be a function and cannot to ignored.
ANNOTATED_FIELD_UNTOUCHED_TYPES: Tuple[Any, ...] = (property, type, classmethod, staticmethod)
# When creating a `BaseModel` instance, we bypass all the methods, properties... added to the model
UNTOUCHED_TYPES: Tuple[Any, ...] = (FunctionType,) + ANNOTATED_FIELD_UNTOUCHED_TYPES
# Note `ModelMetaclass` refers to `BaseModel`, but is also used to *create* `BaseModel`, so we need to add this extra
# (somewhat hacky) boolean to keep track of whether we've created the `BaseModel` class yet, and therefore whether it's
# safe to refer to it. If it *hasn't* been created, we assume that the `__new__` call we're in the middle of is for
# the `BaseModel` class, since that's defined immediately after the metaclass.
_is_base_model_class_defined = False


@dataclass_transform(kw_only_default=True, field_specifiers=(Field,))
class ModelMetaclass(ABCMeta):
    @no_type_check  # noqa C901
    def __new__(mcs, name, bases, namespace, **kwargs):  # noqa C901
        fields: Dict[str, ModelField] = {}
        config = BaseConfig
        validators: 'ValidatorListDict' = {}

        pre_root_validators, post_root_validators = [], []
        private_attributes: Dict[str, ModelPrivateAttr] = {}
        base_private_attributes: Dict[str, ModelPrivateAttr] = {}
        slots: SetStr = namespace.get('__slots__', ())
        slots = {slots} if isinstance(slots, str) else set(slots)
        class_vars: SetStr = set()
        hash_func: Optional[Callable[[Any], int]] = None

        for base in reversed(bases):
            if _is_base_model_class_defined and issubclass(base, BaseModel) and base != BaseModel:
                fields.update(smart_deepcopy(base.__fields__))
                config = inherit_config(base.__config__, config)
                validators = inherit_validators(base.__validators__, validators)
                pre_root_validators += base.__pre_root_validators__
                post_root_validators += base.__post_root_validators__
                base_private_attributes.update(base.__private_attributes__)
                class_vars.update(base.__class_vars__)
                hash_func = base.__hash__

        resolve_forward_refs = kwargs.pop('__resolve_forward_refs__', True)
        allowed_config_kwargs: SetStr = {
            key
            for key in dir(config)
            if not (key.startswith('__') and key.endswith('__'))  # skip dunder methods and attributes
        }
        config_kwargs = {key: kwargs.pop(key) for key in kwargs.keys() & allowed_config_kwargs}
        config_from_namespace = namespace.get('Config')
        if config_kwargs and config_from_namespace:
            raise TypeError('Specifying config in two places is ambiguous, use either Config attribute or class kwargs')
        config = inherit_config(config_from_namespace, config, **config_kwargs)

        validators = inherit_validators(extract_validators(namespace), validators)
        vg = ValidatorGroup(validators)

        for f in fields.values():
            f.set_config(config)
            extra_validators = vg.get_validators(f.name)
            if extra_validators:
                f.class_validators.update(extra_validators)
                # re-run prepare to add extra validators
                f.populate_validators()

        prepare_config(config, name)

        untouched_types = ANNOTATED_FIELD_UNTOUCHED_TYPES

        def is_untouched(v: Any) -> bool:
            return isinstance(v, untouched_types) or v.__class__.__name__ == 'cython_function_or_method'

        if (namespace.get('__module__'), namespace.get('__qualname__')) != ('pydantic.main', 'BaseModel'):
            annotations = resolve_annotations(namespace.get('__annotations__', {}), namespace.get('__module__', None))
            # annotation only fields need to come first in fields
            for ann_name, ann_type in annotations.items():
                if is_classvar(ann_type):
                    class_vars.add(ann_name)
                elif is_finalvar_with_default_val(ann_type, namespace.get(ann_name, Undefined)):
                    class_vars.add(ann_name)
                elif is_valid_field(ann_name):
                    validate_field_name(bases, ann_name)
                    value = namespace.get(ann_name, Undefined)
                    allowed_types = get_args(ann_type) if is_union(get_origin(ann_type)) else (ann_type,)
                    if (
                        is_untouched(value)
                        and ann_type != PyObject
                        and not any(
                            lenient_issubclass(get_origin(allowed_type), Type) for allowed_type in allowed_types
                        )
                    ):
                        continue
                    fields[ann_name] = ModelField.infer(
                        name=ann_name,
                        value=value,
                        annotation=ann_type,
                        class_validators=vg.get_validators(ann_name),
                        config=config,
                    )
                elif ann_name not in namespace and config.underscore_attrs_are_private:
                    private_attributes[ann_name] = PrivateAttr()

            untouched_types = UNTOUCHED_TYPES + config.keep_untouched
            for var_name, value in namespace.items():
                can_be_changed = var_name not in class_vars and not is_untouched(value)
                if isinstance(value, ModelPrivateAttr):
                    if not is_valid_private_name(var_name):
                        raise NameError(
                            f'Private attributes "{var_name}" must not be a valid field name; '
                            f'Use sunder or dunder names, e. g. "_{var_name}" or "__{var_name}__"'
                        )
                    private_attributes[var_name] = value
                elif config.underscore_attrs_are_private and is_valid_private_name(var_name) and can_be_changed:
                    private_attributes[var_name] = PrivateAttr(default=value)
                elif is_valid_field(var_name) and var_name not in annotations and can_be_changed:
                    validate_field_name(bases, var_name)
                    inferred = ModelField.infer(
                        name=var_name,
                        value=value,
                        annotation=annotations.get(var_name, Undefined),
                        class_validators=vg.get_validators(var_name),
                        config=config,
                    )
                    if var_name in fields:
                        if lenient_issubclass(inferred.type_, fields[var_name].type_):
                            inferred.type_ = fields[var_name].type_
                        else:
                            raise TypeError(
                                f'The type of {name}.{var_name} differs from the new default value; '
                                f'if you wish to change the type of this field, please use a type annotation'
                            )
                    fields[var_name] = inferred

        _custom_root_type = ROOT_KEY in fields
        if _custom_root_type:
            validate_custom_root_type(fields)
        vg.check_for_unused()
        if config.json_encoders:
            json_encoder = partial(custom_pydantic_encoder, config.json_encoders)
        else:
            json_encoder = pydantic_encoder
        pre_rv_new, post_rv_new = extract_root_validators(namespace)

        if hash_func is None:
            hash_func = generate_hash_function(config.frozen)

        exclude_from_namespace = fields | private_attributes.keys() | {'__slots__'}
        new_namespace = {
            '__config__': config,
            '__fields__': fields,
            '__exclude_fields__': {
                name: field.field_info.exclude for name, field in fields.items() if field.field_info.exclude is not None
            }
            or None,
            '__include_fields__': {
                name: field.field_info.include for name, field in fields.items() if field.field_info.include is not None
            }
            or None,
            '__validators__': vg.validators,
            '__pre_root_validators__': unique_list(
                pre_root_validators + pre_rv_new,
                name_factory=lambda v: v.__name__,
            ),
            '__post_root_validators__': unique_list(
                post_root_validators + post_rv_new,
                name_factory=lambda skip_on_failure_and_v: skip_on_failure_and_v[1].__name__,
            ),
            '__schema_cache__': {},
            '__json_encoder__': staticmethod(json_encoder),
            '__custom_root_type__': _custom_root_type,
            '__private_attributes__': {**base_private_attributes, **private_attributes},
            '__slots__': slots | private_attributes.keys(),
            '__hash__': hash_func,
            '__class_vars__': class_vars,
            **{n: v for n, v in namespace.items() if n not in exclude_from_namespace},
        }

        cls = super().__new__(mcs, name, bases, new_namespace, **kwargs)
        # set __signature__ attr only for model class, but not for its instances
        cls.__signature__ = ClassAttribute('__signature__', generate_model_signature(cls.__init__, fields, config))

        if not _is_base_model_class_defined:
            # Cython does not understand the `if TYPE_CHECKING:` condition in the
            # BaseModel's body (where annotations are set), so clear them manually:
            getattr(cls, '__annotations__', {}).clear()

        if resolve_forward_refs:
            cls.__try_update_forward_refs__()

        # preserve `__set_name__` protocol defined in https://peps.python.org/pep-0487
        # for attributes not in `new_namespace` (e.g. private attributes)
        for name, obj in namespace.items():
            if name not in new_namespace:
                set_name = getattr(obj, '__set_name__', None)
                if callable(set_name):
                    set_name(cls, name)

        return cls

    def __instancecheck__(self, instance: Any) -> bool:
        """
        Avoid calling ABC _abc_subclasscheck unless we're pretty sure.

        See #3829 and python/cpython#92810
        """
        return hasattr(instance, '__post_root_validators__') and super().__instancecheck__(instance)


object_setattr = object.__setattr__


class BaseModel(Representation, metaclass=ModelMetaclass):
    if TYPE_CHECKING:
        # populated by the metaclass, defined here to help IDEs only
        __fields__: ClassVar[Dict[str, ModelField]] = {}
        __include_fields__: ClassVar[Optional[Mapping[str, Any]]] = None
        __exclude_fields__: ClassVar[Optional[Mapping[str, Any]]] = None
        __validators__: ClassVar[Dict[str, AnyCallable]] = {}
        __pre_root_validators__: ClassVar[List[AnyCallable]]
        __post_root_validators__: ClassVar[List[Tuple[bool, AnyCallable]]]
        __config__: ClassVar[Type[BaseConfig]] = BaseConfig
        __json_encoder__: ClassVar[Callable[[Any], Any]] = lambda x: x
        __schema_cache__: ClassVar['DictAny'] = {}
        __custom_root_type__: ClassVar[bool] = False
        __signature__: ClassVar['Signature']
        __private_attributes__: ClassVar[Dict[str, ModelPrivateAttr]]
        __class_vars__: ClassVar[SetStr]
        __fields_set__: ClassVar[SetStr] = set()

    Config = BaseConfig
    __slots__ = ('__dict__', '__fields_set__')
    __doc__ = ''  # Null out the Representation docstring

    def __init__(__pydantic_self__, **data: Any) -> None:
        """
        Create a new model by parsing and validating input data from keyword arguments.

        Raises ValidationError if the input data cannot be parsed to form a valid model.
        """
        # Uses something other than `self` the first arg to allow "self" as a settable attribute
        values, fields_set, validation_error = validate_model(__pydantic_self__.__class__, data)
        if validation_error:
            raise validation_error
        try:
            object_setattr(__pydantic_self__, '__dict__', values)
        except TypeError as e:
            raise TypeError(
                'Model values must be a dict; you may not have returned a dictionary from a root validator'
            ) from e
        object_setattr(__pydantic_self__, '__fields_set__', fields_set)
        __pydantic_self__._init_private_attributes()

    @no_type_check
    def __setattr__(self, name, value):  # noqa: C901 (ignore complexity)
        if name in self.__private_attributes__ or name in DUNDER_ATTRIBUTES:
            return object_setattr(self, name, value)

        if self.__config__.extra is not Extra.allow and name not in self.__fields__:
            raise ValueError(f'"{self.__class__.__name__}" object has no field "{name}"')
        elif not self.__config__.allow_mutation or self.__config__.frozen:
            raise TypeError(f'"{self.__class__.__name__}" is immutable and does not support item assignment')
        elif name in self.__fields__ and self.__fields__[name].final:
            raise TypeError(
                f'"{self.__class__.__name__}" object "{name}" field is final and does not support reassignment'
            )
        elif self.__config__.validate_assignment:
            new_values = {**self.__dict__, name: value}

            for validator in self.__pre_root_validators__:
                try:
                    new_values = validator(self.__class__, new_values)
                except (ValueError, TypeError, AssertionError) as exc:
                    raise ValidationError([ErrorWrapper(exc, loc=ROOT_KEY)], self.__class__)

            known_field = self.__fields__.get(name, None)
            if known_field:
                # We want to
                # - make sure validators are called without the current value for this field inside `values`
                # - keep other values (e.g. submodels) untouched (using `BaseModel.dict()` will change them into dicts)
                # - keep the order of the fields
                if not known_field.field_info.allow_mutation:
                    raise TypeError(f'"{known_field.name}" has allow_mutation set to False and cannot be assigned')
                dict_without_original_value = {k: v for k, v in self.__dict__.items() if k != name}
                value, error_ = known_field.validate(value, dict_without_original_value, loc=name, cls=self.__class__)
                if error_:
                    raise ValidationError([error_], self.__class__)
                else:
                    new_values[name] = value

            errors = []
            for skip_on_failure, validator in self.__post_root_validators__:
                if skip_on_failure and errors:
                    continue
                try:
                    new_values = validator(self.__class__, new_values)
                except (ValueError, TypeError, AssertionError) as exc:
                    errors.append(ErrorWrapper(exc, loc=ROOT_KEY))
            if errors:
                raise ValidationError(errors, self.__class__)

            # update the whole __dict__ as other values than just `value`
            # may be changed (e.g. with `root_validator`)
            object_setattr(self, '__dict__', new_values)
        else:
            self.__dict__[name] = value

        self.__fields_set__.add(name)

    def __getstate__(self) -> 'DictAny':
        private_attrs = ((k, getattr(self, k, Undefined)) for k in self.__private_attributes__)
        return {
            '__dict__': self.__dict__,
            '__fields_set__': self.__fields_set__,
            '__private_attribute_values__': {k: v for k, v in private_attrs if v is not Undefined},
        }

    def __setstate__(self, state: 'DictAny') -> None:
        object_setattr(self, '__dict__', state['__dict__'])
        object_setattr(self, '__fields_set__', state['__fields_set__'])
        for name, value in state.get('__private_attribute_values__', {}).items():
            object_setattr(self, name, value)

    def _init_private_attributes(self) -> None:
        for name, private_attr in self.__private_attributes__.items():
            default = private_attr.get_default()
            if default is not Undefined:
                object_setattr(self, name, default)

    def dict(
        self,
        *,
        include: Optional[Union['AbstractSetIntStr', 'MappingIntStrAny']] = None,
        exclude: Optional[Union['AbstractSetIntStr', 'MappingIntStrAny']] = None,
        by_alias: bool = False,
        skip_defaults: Optional[bool] = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
    ) -> 'DictStrAny':
        """
        Generate a dictionary representation of the model, optionally specifying which fields to include or exclude.

        """
        if skip_defaults is not None:
            warnings.warn(
                f'{self.__class__.__name__}.dict(): "skip_defaults" is deprecated and replaced by "exclude_unset"',
                DeprecationWarning,
            )
            exclude_unset = skip_defaults

        return dict(
            self._iter(
                to_dict=True,
                by_alias=by_alias,
                include=include,
                exclude=exclude,
                exclude_unset=exclude_unset,
                exclude_defaults=exclude_defaults,
                exclude_none=exclude_none,
            )
        )

    def json(
        self,
        *,
        include: Optional[Union['AbstractSetIntStr', 'MappingIntStrAny']] = None,
        exclude: Optional[Union['AbstractSetIntStr', 'MappingIntStrAny']] = None,
        by_alias: bool = False,
        skip_defaults: Optional[bool] = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        encoder: Optional[Callable[[Any], Any]] = None,
        models_as_dict: bool = True,
        **dumps_kwargs: Any,
    ) -> str:
        """
        Generate a JSON representation of the model, `include` and `exclude` arguments as per `dict()`.

        `encoder` is an optional function to supply as `default` to json.dumps(), other arguments as per `json.dumps()`.
        """
        if skip_defaults is not None:
            warnings.warn(
                f'{self.__class__.__name__}.json(): "skip_defaults" is deprecated and replaced by "exclude_unset"',
                DeprecationWarning,
            )
            exclude_unset = skip_defaults
        encoder = cast(Callable[[Any], Any], encoder or self.__json_encoder__)

        # We don't directly call `self.dict()`, which does exactly this with `to_dict=True`
        # because we want to be able to keep raw `BaseModel` instances and not as `dict`.
        # This allows users to write custom JSON encoders for given `BaseModel` classes.
        data = dict(
            self._iter(
                to_dict=models_as_dict,
                by_alias=by_alias,
                include=include,
                exclude=exclude,
                exclude_unset=exclude_unset,
                exclude_defaults=exclude_defaults,
                exclude_none=exclude_none,
            )
        )
        if self.__custom_root_type__:
            data = data[ROOT_KEY]
        return self.__config__.json_dumps(data, default=encoder, **dumps_kwargs)

    @classmethod
    def _enforce_dict_if_root(cls, obj: Any) -> Any:
        if cls.__custom_root_type__ and (
            not (isinstance(obj, dict) and obj.keys() == {ROOT_KEY})
            and not (isinstance(obj, BaseModel) and obj.__fields__.keys() == {ROOT_KEY})
            or cls.__fields__[ROOT_KEY].shape in MAPPING_LIKE_SHAPES
        ):
            return {ROOT_KEY: obj}
        else:
            return obj

    @classmethod
    def parse_obj(cls: Type['Model'], obj: Any) -> 'Model':
        obj = cls._enforce_dict_if_root(obj)
        if not isinstance(obj, dict):
            try:
                obj = dict(obj)
            except (TypeError, ValueError) as e:
                exc = TypeError(f'{cls.__name__} expected dict not {obj.__class__.__name__}')
                raise ValidationError([ErrorWrapper(exc, loc=ROOT_KEY)], cls) from e
        return cls(**obj)

    @classmethod
    def parse_raw(
        cls: Type['Model'],
        b: StrBytes,
        *,
        content_type: str = None,
        encoding: str = 'utf8',
        proto: Protocol = None,
        allow_pickle: bool = False,
    ) -> 'Model':
        try:
            obj = load_str_bytes(
                b,
                proto=proto,
                content_type=content_type,
                encoding=encoding,
                allow_pickle=allow_pickle,
                json_loads=cls.__config__.json_loads,
            )
        except (ValueError, TypeError, UnicodeDecodeError) as e:
            raise ValidationError([ErrorWrapper(e, loc=ROOT_KEY)], cls)
        return cls.parse_obj(obj)

    @classmethod
    def parse_file(
        cls: Type['Model'],
        path: Union[str, Path],
        *,
        content_type: str = None,
        encoding: str = 'utf8',
        proto: Protocol = None,
        allow_pickle: bool = False,
    ) -> 'Model':
        obj = load_file(
            path,
            proto=proto,
            content_type=content_type,
            encoding=encoding,
            allow_pickle=allow_pickle,
            json_loads=cls.__config__.json_loads,
        )
        return cls.parse_obj(obj)

    @classmethod
    def from_orm(cls: Type['Model'], obj: Any) -> 'Model':
        if not cls.__config__.orm_mode:
            raise ConfigError('You must have the config attribute orm_mode=True to use from_orm')
        obj = {ROOT_KEY: obj} if cls.__custom_root_type__ else cls._decompose_class(obj)
        m = cls.__new__(cls)
        values, fields_set, validation_error = validate_model(cls, obj)
        if validation_error:
            raise validation_error
        object_setattr(m, '__dict__', values)
        object_setattr(m, '__fields_set__', fields_set)
        m._init_private_attributes()
        return m

    @classmethod
    def construct(cls: Type['Model'], _fields_set: Optional['SetStr'] = None, **values: Any) -> 'Model':
        """
        Creates a new model setting __dict__ and __fields_set__ from trusted or pre-validated data.
        Default values are respected, but no other validation is performed.
        Behaves as if `Config.extra = 'allow'` was set since it adds all passed values
        """
        m = cls.__new__(cls)
        fields_values: Dict[str, Any] = {}
        for name, field in cls.__fields__.items():
            if field.alt_alias and field.alias in values:
                fields_values[name] = values[field.alias]
            elif name in values:
                fields_values[name] = values[name]
            elif not field.required:
                fields_values[name] = field.get_default()
        fields_values.update(values)
        object_setattr(m, '__dict__', fields_values)
        if _fields_set is None:
            _fields_set = set(values.keys())
        object_setattr(m, '__fields_set__', _fields_set)
        m._init_private_attributes()
        return m

    def _copy_and_set_values(self: 'Model', values: 'DictStrAny', fields_set: 'SetStr', *, deep: bool) -> 'Model':
        if deep:
            # chances of having empty dict here are quite low for using smart_deepcopy
            values = deepcopy(values)

        cls = self.__class__
        m = cls.__new__(cls)
        object_setattr(m, '__dict__', values)
        object_setattr(m, '__fields_set__', fields_set)
        for name in self.__private_attributes__:
            value = getattr(self, name, Undefined)
            if value is not Undefined:
                if deep:
                    value = deepcopy(value)
                object_setattr(m, name, value)

        return m

    def copy(
        self: 'Model',
        *,
        include: Optional[Union['AbstractSetIntStr', 'MappingIntStrAny']] = None,
        exclude: Optional[Union['AbstractSetIntStr', 'MappingIntStrAny']] = None,
        update: Optional['DictStrAny'] = None,
        deep: bool = False,
    ) -> 'Model':
        """
        Duplicate a model, optionally choose which fields to include, exclude and change.

        :param include: fields to include in new model
        :param exclude: fields to exclude from new model, as with values this takes precedence over include
        :param update: values to change/add in the new model. Note: the data is not validated before creating
            the new model: you should trust this data
        :param deep: set to `True` to make a deep copy of the model
        :return: new model instance
        """

        values = dict(
            self._iter(to_dict=False, by_alias=False, include=include, exclude=exclude, exclude_unset=False),
            **(update or {}),
        )

        # new `__fields_set__` can have unset optional fields with a set value in `update` kwarg
        if update:
            fields_set = self.__fields_set__ | update.keys()
        else:
            fields_set = set(self.__fields_set__)

        return self._copy_and_set_values(values, fields_set, deep=deep)

    @classmethod
    def schema(cls, by_alias: bool = True, ref_template: str = default_ref_template) -> 'DictStrAny':
        cached = cls.__schema_cache__.get((by_alias, ref_template))
        if cached is not None:
            return cached
        s = model_schema(cls, by_alias=by_alias, ref_template=ref_template)
        cls.__schema_cache__[(by_alias, ref_template)] = s
        return s

    @classmethod
    def schema_json(
        cls, *, by_alias: bool = True, ref_template: str = default_ref_template, **dumps_kwargs: Any
    ) -> str:
        from pydantic.v1.json import pydantic_encoder

        return cls.__config__.json_dumps(
            cls.schema(by_alias=by_alias, ref_template=ref_template), default=pydantic_encoder, **dumps_kwargs
        )

    @classmethod
    def __get_validators__(cls) -> 'CallableGenerator':
        yield cls.validate

    @classmethod
    def validate(cls: Type['Model'], value: Any) -> 'Model':
        if isinstance(value, cls):
            copy_on_model_validation = cls.__config__.copy_on_model_validation
            # whether to deep or shallow copy the model on validation, None means do not copy
            deep_copy: Optional[bool] = None
            if copy_on_model_validation not in {'deep', 'shallow', 'none'}:
                # Warn about deprecated behavior
                warnings.warn(
                    "`copy_on_model_validation` should be a string: 'deep', 'shallow' or 'none'", DeprecationWarning
                )
                if copy_on_model_validation:
                    deep_copy = False

            if copy_on_model_validation == 'shallow':
                # shallow copy
                deep_copy = False
            elif copy_on_model_validation == 'deep':
                # deep copy
                deep_copy = True

            if deep_copy is None:
                return value
            else:
                return value._copy_and_set_values(value.__dict__, value.__fields_set__, deep=deep_copy)

        value = cls._enforce_dict_if_root(value)

        if isinstance(value, dict):
            return cls(**value)
        elif cls.__config__.orm_mode:
            return cls.from_orm(value)
        else:
            try:
                value_as_dict = dict(value)
            except (TypeError, ValueError) as e:
                raise DictError() from e
            return cls(**value_as_dict)

    @classmethod
    def _decompose_class(cls: Type['Model'], obj: Any) -> GetterDict:
        if isinstance(obj, GetterDict):
            return obj
        return cls.__config__.getter_dict(obj)

    @classmethod
    @no_type_check
    def _get_value(
        cls,
        v: Any,
        to_dict: bool,
        by_alias: bool,
        include: Optional[Union['AbstractSetIntStr', 'MappingIntStrAny']],
        exclude: Optional[Union['AbstractSetIntStr', 'MappingIntStrAny']],
        exclude_unset: bool,
        exclude_defaults: bool,
        exclude_none: bool,
    ) -> Any:
        if isinstance(v, BaseModel):
            if to_dict:
                v_dict = v.dict(
                    by_alias=by_alias,
                    exclude_unset=exclude_unset,
                    exclude_defaults=exclude_defaults,
                    include=include,
                    exclude=exclude,
                    exclude_none=exclude_none,
                )
                if ROOT_KEY in v_dict:
                    return v_dict[ROOT_KEY]
                return v_dict
            else:
                return v.copy(include=include, exclude=exclude)

        value_exclude = ValueItems(v, exclude) if exclude else None
        value_include = ValueItems(v, include) if include else None

        if isinstance(v, dict):
            return {
                k_: cls._get_value(
                    v_,
                    to_dict=to_dict,
                    by_alias=by_alias,
                    exclude_unset=exclude_unset,
                    exclude_defaults=exclude_defaults,
                    include=value_include and value_include.for_element(k_),
                    exclude=value_exclude and value_exclude.for_element(k_),
                    exclude_none=exclude_none,
                )
                for k_, v_ in v.items()
                if (not value_exclude or not value_exclude.is_excluded(k_))
                and (not value_include or value_include.is_included(k_))
            }

        elif sequence_like(v):
            seq_args = (
                cls._get_value(
                    v_,
                    to_dict=to_dict,
                    by_alias=by_alias,
                    exclude_unset=exclude_unset,
                    exclude_defaults=exclude_defaults,
                    include=value_include and value_include.for_element(i),
                    exclude=value_exclude and value_exclude.for_element(i),
                    exclude_none=exclude_none,
                )
                for i, v_ in enumerate(v)
                if (not value_exclude or not value_exclude.is_excluded(i))
                and (not value_include or value_include.is_included(i))
            )

            return v.__class__(*seq_args) if is_namedtuple(v.__class__) else v.__class__(seq_args)

        elif isinstance(v, Enum) and getattr(cls.Config, 'use_enum_values', False):
            return v.value

        else:
            return v

    @classmethod
    def __try_update_forward_refs__(cls, **localns: Any) -> None:
        """
        Same as update_forward_refs but will not raise exception
        when forward references are not defined.
        """
        update_model_forward_refs(cls, cls.__fields__.values(), cls.__config__.json_encoders, localns, (NameError,))

    @classmethod
    def update_forward_refs(cls, **localns: Any) -> None:
        """
        Try to update ForwardRefs on fields based on this Model, globalns and localns.
        """
        update_model_forward_refs(cls, cls.__fields__.values(), cls.__config__.json_encoders, localns)

    def __iter__(self) -> 'TupleGenerator':
        """
        so `dict(model)` works
        """
        yield from self.__dict__.items()

    def _iter(
        self,
        to_dict: bool = False,
        by_alias: bool = False,
        include: Optional[Union['AbstractSetIntStr', 'MappingIntStrAny']] = None,
        exclude: Optional[Union['AbstractSetIntStr', 'MappingIntStrAny']] = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
    ) -> 'TupleGenerator':
        # Merge field set excludes with explicit exclude parameter with explicit overriding field set options.
        # The extra "is not None" guards are not logically necessary but optimizes performance for the simple case.
        if exclude is not None or self.__exclude_fields__ is not None:
            exclude = ValueItems.merge(self.__exclude_fields__, exclude)

        if include is not None or self.__include_fields__ is not None:
            include = ValueItems.merge(self.__include_fields__, include, intersect=True)

        allowed_keys = self._calculate_keys(
            include=include, exclude=exclude, exclude_unset=exclude_unset  # type: ignore
        )
        if allowed_keys is None and not (to_dict or by_alias or exclude_unset or exclude_defaults or exclude_none):
            # huge boost for plain _iter()
            yield from self.__dict__.items()
            return

        value_exclude = ValueItems(self, exclude) if exclude is not None else None
        value_include = ValueItems(self, include) if include is not None else None

        for field_key, v in self.__dict__.items():
            if (allowed_keys is not None and field_key not in allowed_keys) or (exclude_none and v is None):
                continue

            if exclude_defaults:
                model_field = self.__fields__.get(field_key)
                if not getattr(model_field, 'required', True) and getattr(model_field, 'default', _missing) == v:
                    continue

            if by_alias and field_key in self.__fields__:
                dict_key = self.__fields__[field_key].alias
            else:
                dict_key = field_key

            if to_dict or value_include or value_exclude:
                v = self._get_value(
                    v,
                    to_dict=to_dict,
                    by_alias=by_alias,
                    include=value_include and value_include.for_element(field_key),
                    exclude=value_exclude and value_exclude.for_element(field_key),
                    exclude_unset=exclude_unset,
                    exclude_defaults=exclude_defaults,
                    exclude_none=exclude_none,
                )
            yield dict_key, v

    def _calculate_keys(
        self,
        include: Optional['MappingIntStrAny'],
        exclude: Optional['MappingIntStrAny'],
        exclude_unset: bool,
        update: Optional['DictStrAny'] = None,
    ) -> Optional[AbstractSet[str]]:
        if include is None and exclude is None and exclude_unset is False:
            return None

        keys: AbstractSet[str]
        if exclude_unset:
            keys = self.__fields_set__.copy()
        else:
            keys = self.__dict__.keys()

        if include is not None:
            keys &= include.keys()

        if update:
            keys -= update.keys()

        if exclude:
            keys -= {k for k, v in exclude.items() if ValueItems.is_true(v)}

        return keys

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, BaseModel):
            return self.dict() == other.dict()
        else:
            return self.dict() == other

    def __repr_args__(self) -> 'ReprArgs':
        return [
            (k, v)
            for k, v in self.__dict__.items()
            if k not in DUNDER_ATTRIBUTES and (k not in self.__fields__ or self.__fields__[k].field_info.repr)
        ]


_is_base_model_class_defined = True


@overload
def create_model(
    __model_name: str,
    *,
    __config__: Optional[Type[BaseConfig]] = None,
    __base__: None = None,
    __module__: str = __name__,
    __validators__: Dict[str, 'AnyClassMethod'] = None,
    __cls_kwargs__: Dict[str, Any] = None,
    **field_definitions: Any,
) -> Type['BaseModel']:
    ...


@overload
def create_model(
    __model_name: str,
    *,
    __config__: Optional[Type[BaseConfig]] = None,
    __base__: Union[Type['Model'], Tuple[Type['Model'], ...]],
    __module__: str = __name__,
    __validators__: Dict[str, 'AnyClassMethod'] = None,
    __cls_kwargs__: Dict[str, Any] = None,
    **field_definitions: Any,
) -> Type['Model']:
    ...


def create_model(
    __model_name: str,
    *,
    __config__: Optional[Type[BaseConfig]] = None,
    __base__: Union[None, Type['Model'], Tuple[Type['Model'], ...]] = None,
    __module__: str = __name__,
    __validators__: Dict[str, 'AnyClassMethod'] = None,
    __cls_kwargs__: Dict[str, Any] = None,
    __slots__: Optional[Tuple[str, ...]] = None,
    **field_definitions: Any,
) -> Type['Model']:
    """
    Dynamically create a model.
    :param __model_name: name of the created model
    :param __config__: config class to use for the new model
    :param __base__: base class for the new model to inherit from
    :param __module__: module of the created model
    :param __validators__: a dict of method names and @validator class methods
    :param __cls_kwargs__: a dict for class creation
    :param __slots__: Deprecated, `__slots__` should not be passed to `create_model`
    :param field_definitions: fields of the model (or extra fields if a base is supplied)
        in the format `<name>=(<type>, <default default>)` or `<name>=<default value>, e.g.
        `foobar=(str, ...)` or `foobar=123`, or, for complex use-cases, in the format
        `<name>=<Field>` or `<name>=(<type>, <FieldInfo>)`, e.g.
        `foo=Field(datetime, default_factory=datetime.utcnow, alias='bar')` or
        `foo=(str, FieldInfo(title='Foo'))`
    """
    if __slots__ is not None:
        # __slots__ will be ignored from here on
        warnings.warn('__slots__ should not be passed to create_model', RuntimeWarning)

    if __base__ is not None:
        if __config__ is not None:
            raise ConfigError('to avoid confusion __config__ and __base__ cannot be used together')
        if not isinstance(__base__, tuple):
            __base__ = (__base__,)
    else:
        __base__ = (cast(Type['Model'], BaseModel),)

    __cls_kwargs__ = __cls_kwargs__ or {}

    fields = {}
    annotations = {}

    for f_name, f_def in field_definitions.items():
        if not is_valid_field(f_name):
            warnings.warn(f'fields may not start with an underscore, ignoring "{f_name}"', RuntimeWarning)
        if isinstance(f_def, tuple):
            try:
                f_annotation, f_value = f_def
            except ValueError as e:
                raise ConfigError(
                    'field definitions should either be a tuple of (<type>, <default>) or just a '
                    'default value, unfortunately this means tuples as '
                    'default values are not allowed'
                ) from e
        else:
            f_annotation, f_value = None, f_def

        if f_annotation:
            annotations[f_name] = f_annotation
        fields[f_name] = f_value

    namespace: 'DictStrAny' = {'__annotations__': annotations, '__module__': __module__}
    if __validators__:
        namespace.update(__validators__)
    namespace.update(fields)
    if __config__:
        namespace['Config'] = inherit_config(__config__, BaseConfig)
    resolved_bases = resolve_bases(__base__)
    meta, ns, kwds = prepare_class(__model_name, resolved_bases, kwds=__cls_kwargs__)
    if resolved_bases is not __base__:
        ns['__orig_bases__'] = __base__
    namespace.update(ns)
    return meta(__model_name, resolved_bases, namespace, **kwds)


_missing = object()


def validate_model(  # noqa: C901 (ignore complexity)
    model: Type[BaseModel], input_data: 'DictStrAny', cls: 'ModelOrDc' = None
) -> Tuple['DictStrAny', 'SetStr', Optional[ValidationError]]:
    """
    validate data against a model.
    """
    values = {}
    errors = []
    # input_data names, possibly alias
    names_used = set()
    # field names, never aliases
    fields_set = set()
    config = model.__config__
    check_extra = config.extra is not Extra.ignore
    cls_ = cls or model

    for validator in model.__pre_root_validators__:
        try:
            input_data = validator(cls_, input_data)
        except (ValueError, TypeError, AssertionError) as exc:
            return {}, set(), ValidationError([ErrorWrapper(exc, loc=ROOT_KEY)], cls_)

    for name, field in model.__fields__.items():
        value = input_data.get(field.alias, _missing)
        using_name = False
        if value is _missing and config.allow_population_by_field_name and field.alt_alias:
            value = input_data.get(field.name, _missing)
            using_name = True

        if value is _missing:
            if field.required:
                errors.append(ErrorWrapper(MissingError(), loc=field.alias))
                continue

            value = field.get_default()

            if not config.validate_all and not field.validate_always:
                values[name] = value
                continue
        else:
            fields_set.add(name)
            if check_extra:
                names_used.add(field.name if using_name else field.alias)

        v_, errors_ = field.validate(value, values, loc=field.alias, cls=cls_)
        if isinstance(errors_, ErrorWrapper):
            errors.append(errors_)
        elif isinstance(errors_, list):
            errors.extend(errors_)
        else:
            values[name] = v_

    if check_extra:
        if isinstance(input_data, GetterDict):
            extra = input_data.extra_keys() - names_used
        else:
            extra = input_data.keys() - names_used
        if extra:
            fields_set |= extra
            if config.extra is Extra.allow:
                for f in extra:
                    values[f] = input_data[f]
            else:
                for f in sorted(extra):
                    errors.append(ErrorWrapper(ExtraError(), loc=f))

    for skip_on_failure, validator in model.__post_root_validators__:
        if skip_on_failure and errors:
            continue
        try:
            values = validator(cls_, values)
        except (ValueError, TypeError, AssertionError) as exc:
            errors.append(ErrorWrapper(exc, loc=ROOT_KEY))

    if errors:
        return values, fields_set, ValidationError(errors, cls_)
    else:
        return values, fields_set, None

# === NexusCore/openenv\Lib\site-packages\litellm\integrations\opentelemetry.py ===
import os
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union, cast

import litellm
from litellm._logging import verbose_logger
from litellm.integrations.custom_logger import CustomLogger
from litellm.litellm_core_utils.safe_json_dumps import safe_dumps
from litellm.types.services import ServiceLoggerPayload
from litellm.types.utils import (
    ChatCompletionMessageToolCall,
    Function,
    StandardCallbackDynamicParams,
    StandardLoggingPayload,
)

if TYPE_CHECKING:
    from opentelemetry.sdk.trace.export import SpanExporter as _SpanExporter
    from opentelemetry.trace import Context as _Context
    from opentelemetry.trace import Span as _Span

    from litellm.proxy._types import (
        ManagementEndpointLoggingPayload as _ManagementEndpointLoggingPayload,
    )
    from litellm.proxy.proxy_server import UserAPIKeyAuth as _UserAPIKeyAuth

    Span = Union[_Span, Any]
    Context = Union[_Context, Any]
    SpanExporter = Union[_SpanExporter, Any]
    UserAPIKeyAuth = Union[_UserAPIKeyAuth, Any]
    ManagementEndpointLoggingPayload = Union[_ManagementEndpointLoggingPayload, Any]
else:
    Span = Any
    SpanExporter = Any
    UserAPIKeyAuth = Any
    ManagementEndpointLoggingPayload = Any
    Context = Any

LITELLM_TRACER_NAME = os.getenv("OTEL_TRACER_NAME", "litellm")
LITELLM_RESOURCE: Dict[Any, Any] = {
    "service.name": os.getenv("OTEL_SERVICE_NAME", "litellm"),
    "deployment.environment": os.getenv("OTEL_ENVIRONMENT_NAME", "production"),
    "model_id": os.getenv("OTEL_SERVICE_NAME", "litellm"),
}
RAW_REQUEST_SPAN_NAME = "raw_gen_ai_request"
LITELLM_REQUEST_SPAN_NAME = "litellm_request"


@dataclass
class OpenTelemetryConfig:
    exporter: Union[str, SpanExporter] = "console"
    endpoint: Optional[str] = None
    headers: Optional[str] = None

    @classmethod
    def from_env(cls):
        """
        OTEL_HEADERS=x-honeycomb-team=B85YgLm9****
        OTEL_EXPORTER="otlp_http"
        OTEL_ENDPOINT="https://api.honeycomb.io/v1/traces"

        OTEL_HEADERS gets sent as headers = {"x-honeycomb-team": "B85YgLm96******"}
        """
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
            InMemorySpanExporter,
        )

        exporter = os.getenv(
            "OTEL_EXPORTER_OTLP_PROTOCOL", os.getenv("OTEL_EXPORTER", "console")
        )
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", os.getenv("OTEL_ENDPOINT"))
        headers = os.getenv(
            "OTEL_EXPORTER_OTLP_HEADERS", os.getenv("OTEL_HEADERS")
        )  # example: OTEL_HEADERS=x-honeycomb-team=B85YgLm96***"

        if exporter == "in_memory":
            return cls(exporter=InMemorySpanExporter())
        return cls(
            exporter=exporter,
            endpoint=endpoint,
            headers=headers,  # example: OTEL_HEADERS=x-honeycomb-team=B85YgLm96***"
        )


class OpenTelemetry(CustomLogger):
    def __init__(
        self,
        config: Optional[OpenTelemetryConfig] = None,
        callback_name: Optional[str] = None,
        **kwargs,
    ):
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.trace import SpanKind

        if config is None:
            config = OpenTelemetryConfig.from_env()

        self.config = config
        self.OTEL_EXPORTER = self.config.exporter
        self.OTEL_ENDPOINT = self.config.endpoint
        self.OTEL_HEADERS = self.config.headers
        provider = TracerProvider(resource=Resource(attributes=LITELLM_RESOURCE))
        provider.add_span_processor(self._get_span_processor())
        self.callback_name = callback_name

        trace.set_tracer_provider(provider)
        self.tracer = trace.get_tracer(LITELLM_TRACER_NAME)

        self.span_kind = SpanKind

        _debug_otel = str(os.getenv("DEBUG_OTEL", "False")).lower()

        if _debug_otel == "true":
            # Set up logging
            import logging

            logging.basicConfig(level=logging.DEBUG)
            logging.getLogger(__name__)

            # Enable OpenTelemetry logging
            otel_exporter_logger = logging.getLogger("opentelemetry.sdk.trace.export")
            otel_exporter_logger.setLevel(logging.DEBUG)

        # init CustomLogger params
        super().__init__(**kwargs)
        self._init_otel_logger_on_litellm_proxy()

    def _init_otel_logger_on_litellm_proxy(self):
        """
        Initializes OpenTelemetry for litellm proxy server

        - Adds Otel as a service callback
        - Sets `proxy_server.open_telemetry_logger` to self
        """
        try:
            from litellm.proxy import proxy_server
        except ImportError:
            verbose_logger.warning(
                "Proxy Server is not installed. Skipping OpenTelemetry initialization."
            )
            return

        # Add Otel as a service callback
        if "otel" not in litellm.service_callback:
            litellm.service_callback.append("otel")
        setattr(proxy_server, "open_telemetry_logger", self)

    def log_success_event(self, kwargs, response_obj, start_time, end_time):
        self._handle_sucess(kwargs, response_obj, start_time, end_time)

    def log_failure_event(self, kwargs, response_obj, start_time, end_time):
        self._handle_failure(kwargs, response_obj, start_time, end_time)

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        self._handle_sucess(kwargs, response_obj, start_time, end_time)

    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time):
        self._handle_failure(kwargs, response_obj, start_time, end_time)

    async def async_service_success_hook(
        self,
        payload: ServiceLoggerPayload,
        parent_otel_span: Optional[Span] = None,
        start_time: Optional[Union[datetime, float]] = None,
        end_time: Optional[Union[datetime, float]] = None,
        event_metadata: Optional[dict] = None,
    ):
        from opentelemetry import trace
        from opentelemetry.trace import Status, StatusCode

        _start_time_ns = 0
        _end_time_ns = 0

        if isinstance(start_time, float):
            _start_time_ns = int(start_time * 1e9)
        else:
            _start_time_ns = self._to_ns(start_time)

        if isinstance(end_time, float):
            _end_time_ns = int(end_time * 1e9)
        else:
            _end_time_ns = self._to_ns(end_time)

        if parent_otel_span is not None:
            _span_name = payload.service
            service_logging_span = self.tracer.start_span(
                name=_span_name,
                context=trace.set_span_in_context(parent_otel_span),
                start_time=_start_time_ns,
            )
            self.safe_set_attribute(
                span=service_logging_span,
                key="call_type",
                value=payload.call_type,
            )
            self.safe_set_attribute(
                span=service_logging_span,
                key="service",
                value=payload.service.value,
            )

            if event_metadata:
                for key, value in event_metadata.items():
                    if value is None:
                        value = "None"
                    if isinstance(value, dict):
                        try:
                            value = str(value)
                        except Exception:
                            value = "litellm logging error - could_not_json_serialize"
                    self.safe_set_attribute(
                        span=service_logging_span,
                        key=key,
                        value=value,
                    )
            service_logging_span.set_status(Status(StatusCode.OK))
            service_logging_span.end(end_time=_end_time_ns)

    async def async_service_failure_hook(
        self,
        payload: ServiceLoggerPayload,
        error: Optional[str] = "",
        parent_otel_span: Optional[Span] = None,
        start_time: Optional[Union[datetime, float]] = None,
        end_time: Optional[Union[float, datetime]] = None,
        event_metadata: Optional[dict] = None,
    ):
        from opentelemetry import trace
        from opentelemetry.trace import Status, StatusCode

        _start_time_ns = 0
        _end_time_ns = 0

        if isinstance(start_time, float):
            _start_time_ns = int(int(start_time) * 1e9)
        else:
            _start_time_ns = self._to_ns(start_time)

        if isinstance(end_time, float):
            _end_time_ns = int(int(end_time) * 1e9)
        else:
            _end_time_ns = self._to_ns(end_time)

        if parent_otel_span is not None:
            _span_name = payload.service
            service_logging_span = self.tracer.start_span(
                name=_span_name,
                context=trace.set_span_in_context(parent_otel_span),
                start_time=_start_time_ns,
            )
            self.safe_set_attribute(
                span=service_logging_span,
                key="call_type",
                value=payload.call_type,
            )
            self.safe_set_attribute(
                span=service_logging_span,
                key="service",
                value=payload.service.value,
            )
            if error:
                self.safe_set_attribute(
                    span=service_logging_span,
                    key="error",
                    value=error,
                )
            if event_metadata:
                for key, value in event_metadata.items():
                    if isinstance(value, dict):
                        try:
                            value = str(value)
                        except Exception:
                            value = "litllm logging error - could_not_json_serialize"
                    self.safe_set_attribute(
                        span=service_logging_span,
                        key=key,
                        value=value,
                    )

            service_logging_span.set_status(Status(StatusCode.ERROR))
            service_logging_span.end(end_time=_end_time_ns)

    async def async_post_call_failure_hook(
        self,
        request_data: dict,
        original_exception: Exception,
        user_api_key_dict: UserAPIKeyAuth,
        traceback_str: Optional[str] = None,
    ):
        from opentelemetry import trace
        from opentelemetry.trace import Status, StatusCode

        parent_otel_span = user_api_key_dict.parent_otel_span
        if parent_otel_span is not None:
            parent_otel_span.set_status(Status(StatusCode.ERROR))
            _span_name = "Failed Proxy Server Request"

            # Exception Logging Child Span
            exception_logging_span = self.tracer.start_span(
                name=_span_name,
                context=trace.set_span_in_context(parent_otel_span),
            )
            self.safe_set_attribute(
                span=exception_logging_span,
                key="exception",
                value=str(original_exception),
            )
            exception_logging_span.set_status(Status(StatusCode.ERROR))
            exception_logging_span.end(end_time=self._to_ns(datetime.now()))

            # End Parent OTEL Sspan
            parent_otel_span.end(end_time=self._to_ns(datetime.now()))

    def _handle_sucess(self, kwargs, response_obj, start_time, end_time):
        from opentelemetry import trace
        from opentelemetry.trace import Status, StatusCode

        verbose_logger.debug(
            "OpenTelemetry Logger: Logging kwargs: %s, OTEL config settings=%s",
            kwargs,
            self.config,
        )
        _parent_context, parent_otel_span = self._get_span_context(kwargs)

        self._add_dynamic_span_processor_if_needed(kwargs)

        # Span 1: Requst sent to litellm SDK
        span = self.tracer.start_span(
            name=self._get_span_name(kwargs),
            start_time=self._to_ns(start_time),
            context=_parent_context,
        )
        span.set_status(Status(StatusCode.OK))
        self.set_attributes(span, kwargs, response_obj)

        if litellm.turn_off_message_logging is True:
            pass
        elif self.message_logging is not True:
            pass
        else:
            # Span 2: Raw Request / Response to LLM
            raw_request_span = self.tracer.start_span(
                name=RAW_REQUEST_SPAN_NAME,
                start_time=self._to_ns(start_time),
                context=trace.set_span_in_context(span),
            )

            raw_request_span.set_status(Status(StatusCode.OK))
            self.set_raw_request_attributes(raw_request_span, kwargs, response_obj)
            raw_request_span.end(end_time=self._to_ns(end_time))

        span.end(end_time=self._to_ns(end_time))

        # Create span for guardrail information
        self._create_guardrail_span(kwargs=kwargs, context=_parent_context)

        if parent_otel_span is not None:
            parent_otel_span.end(end_time=self._to_ns(datetime.now()))

    def _create_guardrail_span(
        self, kwargs: Optional[dict], context: Optional[Context]
    ):
        """
        Creates a span for Guardrail, if any guardrail information is present in standard_logging_object
        """
        # Create span for guardrail information
        kwargs = kwargs or {}
        standard_logging_payload: Optional[StandardLoggingPayload] = kwargs.get(
            "standard_logging_object"
        )
        if standard_logging_payload is None:
            return

        guardrail_information = standard_logging_payload.get("guardrail_information")
        if guardrail_information is None:
            return

        start_time_float = guardrail_information.get("start_time")
        end_time_float = guardrail_information.get("end_time")
        start_time_datetime = datetime.now()
        if start_time_float is not None:
            start_time_datetime = datetime.fromtimestamp(start_time_float)
        end_time_datetime = datetime.now()
        if end_time_float is not None:
            end_time_datetime = datetime.fromtimestamp(end_time_float)

        guardrail_span = self.tracer.start_span(
            name="guardrail",
            start_time=self._to_ns(start_time_datetime),
            context=context,
        )

        self.safe_set_attribute(
            span=guardrail_span,
            key="guardrail_name",
            value=guardrail_information.get("guardrail_name"),
        )

        self.safe_set_attribute(
            span=guardrail_span,
            key="guardrail_mode",
            value=guardrail_information.get("guardrail_mode"),
        )

        # Set masked_entity_count directly without conversion
        masked_entity_count = guardrail_information.get("masked_entity_count")
        if masked_entity_count is not None:
            guardrail_span.set_attribute(
                "masked_entity_count", safe_dumps(masked_entity_count)
            )

        self.safe_set_attribute(
            span=guardrail_span,
            key="guardrail_response",
            value=guardrail_information.get("guardrail_response"),
        )

        guardrail_span.end(end_time=self._to_ns(end_time_datetime))

    def _add_dynamic_span_processor_if_needed(self, kwargs):
        """
        Helper method to add a span processor with dynamic headers if needed.

        This allows for per-request configuration of telemetry exporters by
        extracting headers from standard_callback_dynamic_params.
        """
        from opentelemetry import trace

        standard_callback_dynamic_params: Optional[
            StandardCallbackDynamicParams
        ] = kwargs.get("standard_callback_dynamic_params")
        if not standard_callback_dynamic_params:
            return

        # Extract headers from dynamic params
        dynamic_headers = {}

        # Handle Arize headers
        if standard_callback_dynamic_params.get("arize_space_key"):
            dynamic_headers["space_key"] = standard_callback_dynamic_params.get(
                "arize_space_key"
            )
        if standard_callback_dynamic_params.get("arize_api_key"):
            dynamic_headers["api_key"] = standard_callback_dynamic_params.get(
                "arize_api_key"
            )

        # Only create a span processor if we have headers to use
        if len(dynamic_headers) > 0:
            from opentelemetry.sdk.trace import TracerProvider

            provider = trace.get_tracer_provider()
            if isinstance(provider, TracerProvider):
                span_processor = self._get_span_processor(
                    dynamic_headers=dynamic_headers
                )
                provider.add_span_processor(span_processor)

    def _handle_failure(self, kwargs, response_obj, start_time, end_time):
        from opentelemetry.trace import Status, StatusCode

        verbose_logger.debug(
            "OpenTelemetry Logger: Failure HandlerLogging kwargs: %s, OTEL config settings=%s",
            kwargs,
            self.config,
        )
        _parent_context, parent_otel_span = self._get_span_context(kwargs)

        # Span 1: Requst sent to litellm SDK
        span = self.tracer.start_span(
            name=self._get_span_name(kwargs),
            start_time=self._to_ns(start_time),
            context=_parent_context,
        )
        span.set_status(Status(StatusCode.ERROR))
        self.set_attributes(span, kwargs, response_obj)
        span.end(end_time=self._to_ns(end_time))

        # Create span for guardrail information
        self._create_guardrail_span(kwargs=kwargs, context=_parent_context)

        if parent_otel_span is not None:
            parent_otel_span.end(end_time=self._to_ns(datetime.now()))

    def set_tools_attributes(self, span: Span, tools):
        import json

        from litellm.proxy._types import SpanAttributes

        if not tools:
            return

        try:
            for i, tool in enumerate(tools):
                function = tool.get("function")
                if not function:
                    continue

                prefix = f"{SpanAttributes.LLM_REQUEST_FUNCTIONS.value}.{i}"
                self.safe_set_attribute(
                    span=span,
                    key=f"{prefix}.name",
                    value=function.get("name"),
                )
                self.safe_set_attribute(
                    span=span,
                    key=f"{prefix}.description",
                    value=function.get("description"),
                )
                self.safe_set_attribute(
                    span=span,
                    key=f"{prefix}.parameters",
                    value=json.dumps(function.get("parameters")),
                )
        except Exception as e:
            verbose_logger.error(
                "OpenTelemetry: Error setting tools attributes: %s", str(e)
            )
            pass

    def cast_as_primitive_value_type(self, value) -> Union[str, bool, int, float]:
        """
        Casts the value to a primitive OTEL type if it is not already a primitive type.

        OTEL supports - str, bool, int, float

        If it's not a primitive type, then it's converted to a string
        """
        if value is None:
            return ""
        if isinstance(value, (str, bool, int, float)):
            return value
        try:
            return str(value)
        except Exception:
            return ""

    @staticmethod
    def _tool_calls_kv_pair(
        tool_calls: List[ChatCompletionMessageToolCall],
    ) -> Dict[str, Any]:
        from litellm.proxy._types import SpanAttributes

        kv_pairs: Dict[str, Any] = {}
        for idx, tool_call in enumerate(tool_calls):
            _function = tool_call.get("function")
            if not _function:
                continue

            keys = Function.__annotations__.keys()
            for key in keys:
                _value = _function.get(key)
                if _value:
                    kv_pairs[
                        f"{SpanAttributes.LLM_COMPLETIONS.value}.{idx}.function_call.{key}"
                    ] = _value

        return kv_pairs

    def set_attributes(  # noqa: PLR0915
        self, span: Span, kwargs, response_obj: Optional[Any]
    ):
        try:
            if self.callback_name == "arize_phoenix":
                from litellm.integrations.arize.arize_phoenix import ArizePhoenixLogger

                ArizePhoenixLogger.set_arize_phoenix_attributes(
                    span, kwargs, response_obj
                )
                return
            elif self.callback_name == "langtrace":
                from litellm.integrations.langtrace import LangtraceAttributes

                LangtraceAttributes().set_langtrace_attributes(
                    span, kwargs, response_obj
                )
                return
            elif self.callback_name == "langfuse_otel":
                from litellm.integrations.langfuse.langfuse_otel import LangfuseOtelLogger

                LangfuseOtelLogger.set_langfuse_otel_attributes(
                    span, kwargs, response_obj
                )
                return
            from litellm.proxy._types import SpanAttributes

            optional_params = kwargs.get("optional_params", {})
            litellm_params = kwargs.get("litellm_params", {}) or {}
            standard_logging_payload: Optional[StandardLoggingPayload] = kwargs.get(
                "standard_logging_object"
            )
            if standard_logging_payload is None:
                raise ValueError("standard_logging_object not found in kwargs")

            # https://github.com/open-telemetry/semantic-conventions/blob/main/model/registry/gen-ai.yaml
            # Following Conventions here: https://github.com/open-telemetry/semantic-conventions/blob/main/docs/gen-ai/llm-spans.md
            #############################################
            ############ LLM CALL METADATA ##############
            #############################################
            metadata = standard_logging_payload["metadata"]
            for key, value in metadata.items():
                self.safe_set_attribute(
                    span=span, key="metadata.{}".format(key), value=value
                )

            #############################################
            ########## LLM Request Attributes ###########
            #############################################

            # The name of the LLM a request is being made to
            if kwargs.get("model"):
                self.safe_set_attribute(
                    span=span,
                    key=SpanAttributes.LLM_REQUEST_MODEL.value,
                    value=kwargs.get("model"),
                )

            # The LLM request type
            self.safe_set_attribute(
                span=span,
                key=SpanAttributes.LLM_REQUEST_TYPE.value,
                value=standard_logging_payload["call_type"],
            )

            # The Generative AI Provider: Azure, OpenAI, etc.
            self.safe_set_attribute(
                span=span,
                key=SpanAttributes.LLM_SYSTEM.value,
                value=litellm_params.get("custom_llm_provider", "Unknown"),
            )

            # The maximum number of tokens the LLM generates for a request.
            if optional_params.get("max_tokens"):
                self.safe_set_attribute(
                    span=span,
                    key=SpanAttributes.LLM_REQUEST_MAX_TOKENS.value,
                    value=optional_params.get("max_tokens"),
                )

            # The temperature setting for the LLM request.
            if optional_params.get("temperature"):
                self.safe_set_attribute(
                    span=span,
                    key=SpanAttributes.LLM_REQUEST_TEMPERATURE.value,
                    value=optional_params.get("temperature"),
                )

            # The top_p sampling setting for the LLM request.
            if optional_params.get("top_p"):
                self.safe_set_attribute(
                    span=span,
                    key=SpanAttributes.LLM_REQUEST_TOP_P.value,
                    value=optional_params.get("top_p"),
                )

            self.safe_set_attribute(
                span=span,
                key=SpanAttributes.LLM_IS_STREAMING.value,
                value=str(optional_params.get("stream", False)),
            )

            if optional_params.get("user"):
                self.safe_set_attribute(
                    span=span,
                    key=SpanAttributes.LLM_USER.value,
                    value=optional_params.get("user"),
                )

            # The unique identifier for the completion.
            if response_obj and response_obj.get("id"):
                self.safe_set_attribute(
                    span=span, key="gen_ai.response.id", value=response_obj.get("id")
                )

            # The model used to generate the response.
            if response_obj and response_obj.get("model"):
                self.safe_set_attribute(
                    span=span,
                    key=SpanAttributes.LLM_RESPONSE_MODEL.value,
                    value=response_obj.get("model"),
                )

            usage = response_obj and response_obj.get("usage")
            if usage:
                self.safe_set_attribute(
                    span=span,
                    key=SpanAttributes.LLM_USAGE_TOTAL_TOKENS.value,
                    value=usage.get("total_tokens"),
                )

                # The number of tokens used in the LLM response (completion).
                self.safe_set_attribute(
                    span=span,
                    key=SpanAttributes.LLM_USAGE_COMPLETION_TOKENS.value,
                    value=usage.get("completion_tokens"),
                )

                # The number of tokens used in the LLM prompt.
                self.safe_set_attribute(
                    span=span,
                    key=SpanAttributes.LLM_USAGE_PROMPT_TOKENS.value,
                    value=usage.get("prompt_tokens"),
                )

            ########################################################################
            ########## LLM Request Medssages / tools / content Attributes ###########
            #########################################################################

            if litellm.turn_off_message_logging is True:
                return
            if self.message_logging is not True:
                return

            if optional_params.get("tools"):
                tools = optional_params["tools"]
                self.set_tools_attributes(span, tools)

            if kwargs.get("messages"):
                for idx, prompt in enumerate(kwargs.get("messages")):
                    if prompt.get("role"):
                        self.safe_set_attribute(
                            span=span,
                            key=f"{SpanAttributes.LLM_PROMPTS.value}.{idx}.role",
                            value=prompt.get("role"),
                        )

                    if prompt.get("content"):
                        if not isinstance(prompt.get("content"), str):
                            prompt["content"] = str(prompt.get("content"))
                        self.safe_set_attribute(
                            span=span,
                            key=f"{SpanAttributes.LLM_PROMPTS.value}.{idx}.content",
                            value=prompt.get("content"),
                        )
            #############################################
            ########## LLM Response Attributes ##########
            #############################################
            if response_obj is not None:
                if response_obj.get("choices"):
                    for idx, choice in enumerate(response_obj.get("choices")):
                        if choice.get("finish_reason"):
                            self.safe_set_attribute(
                                span=span,
                                key=f"{SpanAttributes.LLM_COMPLETIONS.value}.{idx}.finish_reason",
                                value=choice.get("finish_reason"),
                            )
                        if choice.get("message"):
                            if choice.get("message").get("role"):
                                self.safe_set_attribute(
                                    span=span,
                                    key=f"{SpanAttributes.LLM_COMPLETIONS.value}.{idx}.role",
                                    value=choice.get("message").get("role"),
                                )
                            if choice.get("message").get("content"):
                                if not isinstance(
                                    choice.get("message").get("content"), str
                                ):
                                    choice["message"]["content"] = str(
                                        choice.get("message").get("content")
                                    )
                                self.safe_set_attribute(
                                    span=span,
                                    key=f"{SpanAttributes.LLM_COMPLETIONS.value}.{idx}.content",
                                    value=choice.get("message").get("content"),
                                )

                            message = choice.get("message")
                            tool_calls = message.get("tool_calls")
                            if tool_calls:
                                kv_pairs = OpenTelemetry._tool_calls_kv_pair(tool_calls)  # type: ignore
                                for key, value in kv_pairs.items():
                                    self.safe_set_attribute(
                                        span=span,
                                        key=key,
                                        value=value,
                                    )

        except Exception as e:
            verbose_logger.exception(
                "OpenTelemetry logging error in set_attributes %s", str(e)
            )

    def _cast_as_primitive_value_type(self, value) -> Union[str, bool, int, float]:
        """
        Casts the value to a primitive OTEL type if it is not already a primitive type.

        OTEL supports - str, bool, int, float

        If it's not a primitive type, then it's converted to a string
        """
        if value is None:
            return ""
        if isinstance(value, (str, bool, int, float)):
            return value
        try:
            return str(value)
        except Exception:
            return ""

    def safe_set_attribute(self, span: Span, key: str, value: Any):
        """
        Safely sets an attribute on the span, ensuring the value is a primitive type.
        """
        primitive_value = self._cast_as_primitive_value_type(value)
        span.set_attribute(key, primitive_value)

    def set_raw_request_attributes(self, span: Span, kwargs, response_obj):
        kwargs.get("optional_params", {})
        litellm_params = kwargs.get("litellm_params", {}) or {}
        custom_llm_provider = litellm_params.get("custom_llm_provider", "Unknown")

        _raw_response = kwargs.get("original_response")
        _additional_args = kwargs.get("additional_args", {}) or {}
        complete_input_dict = _additional_args.get("complete_input_dict")
        #############################################
        ########## LLM Request Attributes ###########
        #############################################

        # OTEL Attributes for the RAW Request to https://docs.anthropic.com/en/api/messages
        if complete_input_dict and isinstance(complete_input_dict, dict):
            for param, val in complete_input_dict.items():
                self.safe_set_attribute(
                    span=span, key=f"llm.{custom_llm_provider}.{param}", value=val
                )

        #############################################
        ########## LLM Response Attributes ##########
        #############################################
        if _raw_response and isinstance(_raw_response, str):
            # cast sr -> dict
            import json

            try:
                _raw_response = json.loads(_raw_response)
                for param, val in _raw_response.items():
                    self.safe_set_attribute(
                        span=span,
                        key=f"llm.{custom_llm_provider}.{param}",
                        value=val,
                    )
            except json.JSONDecodeError:
                verbose_logger.debug(
                    "litellm.integrations.opentelemetry.py::set_raw_request_attributes() - raw_response not json string - {}".format(
                        _raw_response
                    )
                )

                self.safe_set_attribute(
                    span=span,
                    key=f"llm.{custom_llm_provider}.stringified_raw_response",
                    value=_raw_response,
                )

    def _to_ns(self, dt):
        return int(dt.timestamp() * 1e9)

    def _get_span_name(self, kwargs):
        return LITELLM_REQUEST_SPAN_NAME

    def get_traceparent_from_header(self, headers):
        if headers is None:
            return None
        _traceparent = headers.get("traceparent", None)
        if _traceparent is None:
            return None

        from opentelemetry.trace.propagation.tracecontext import (
            TraceContextTextMapPropagator,
        )

        propagator = TraceContextTextMapPropagator()
        carrier = {"traceparent": _traceparent}
        _parent_context = propagator.extract(carrier=carrier)

        return _parent_context

    def _get_span_context(self, kwargs):
        from opentelemetry import trace
        from opentelemetry.trace.propagation.tracecontext import (
            TraceContextTextMapPropagator,
        )

        litellm_params = kwargs.get("litellm_params", {}) or {}
        proxy_server_request = litellm_params.get("proxy_server_request", {}) or {}
        headers = proxy_server_request.get("headers", {}) or {}
        traceparent = headers.get("traceparent", None)
        _metadata = litellm_params.get("metadata", {}) or {}
        parent_otel_span = _metadata.get("litellm_parent_otel_span", None)

        """
        Two way to use parents in opentelemetry
        - using the traceparent header
        - using the parent_otel_span in the [metadata][parent_otel_span]
        """
        if parent_otel_span is not None:
            return trace.set_span_in_context(parent_otel_span), parent_otel_span

        if traceparent is None:
            return None, None
        else:
            carrier = {"traceparent": traceparent}
            return TraceContextTextMapPropagator().extract(carrier=carrier), None

    def _get_span_processor(self, dynamic_headers: Optional[dict] = None):
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter as OTLPSpanExporterGRPC,
        )
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter as OTLPSpanExporterHTTP,
        )
        from opentelemetry.sdk.trace.export import (
            BatchSpanProcessor,
            ConsoleSpanExporter,
            SimpleSpanProcessor,
            SpanExporter,
        )

        verbose_logger.debug(
            "OpenTelemetry Logger, initializing span processor \nself.OTEL_EXPORTER: %s\nself.OTEL_ENDPOINT: %s\nself.OTEL_HEADERS: %s",
            self.OTEL_EXPORTER,
            self.OTEL_ENDPOINT,
            self.OTEL_HEADERS,
        )
        _split_otel_headers = OpenTelemetry._get_headers_dictionary(
            headers=dynamic_headers or self.OTEL_HEADERS
        )

        if hasattr(
            self.OTEL_EXPORTER, "export"
        ):  # Check if it has the export method that SpanExporter requires
            verbose_logger.debug(
                "OpenTelemetry: intiializing SpanExporter. Value of OTEL_EXPORTER: %s",
                self.OTEL_EXPORTER,
            )
            return SimpleSpanProcessor(cast(SpanExporter, self.OTEL_EXPORTER))

        if self.OTEL_EXPORTER == "console":
            verbose_logger.debug(
                "OpenTelemetry: intiializing console exporter. Value of OTEL_EXPORTER: %s",
                self.OTEL_EXPORTER,
            )
            return BatchSpanProcessor(ConsoleSpanExporter())
        elif (
            self.OTEL_EXPORTER == "otlp_http"
            or self.OTEL_EXPORTER == "http/protobuf"
            or self.OTEL_EXPORTER == "http/json"
        ):
            verbose_logger.debug(
                "OpenTelemetry: intiializing http exporter. Value of OTEL_EXPORTER: %s",
                self.OTEL_EXPORTER,
            )
            return BatchSpanProcessor(
                OTLPSpanExporterHTTP(
                    endpoint=self.OTEL_ENDPOINT, headers=_split_otel_headers
                ),
            )
        elif self.OTEL_EXPORTER == "otlp_grpc" or self.OTEL_EXPORTER == "grpc":
            verbose_logger.debug(
                "OpenTelemetry: intiializing grpc exporter. Value of OTEL_EXPORTER: %s",
                self.OTEL_EXPORTER,
            )
            return BatchSpanProcessor(
                OTLPSpanExporterGRPC(
                    endpoint=self.OTEL_ENDPOINT, headers=_split_otel_headers
                ),
            )
        else:
            verbose_logger.debug(
                "OpenTelemetry: intiializing console exporter. Value of OTEL_EXPORTER: %s",
                self.OTEL_EXPORTER,
            )
            return BatchSpanProcessor(ConsoleSpanExporter())

    @staticmethod
    def _get_headers_dictionary(headers: Optional[Union[str, dict]]) -> Dict[str, str]:
        """
        Convert a string or dictionary of headers into a dictionary of headers.
        """
        _split_otel_headers: Dict[str, str] = {}
        if headers:
            if isinstance(headers, str):
                # when passed HEADERS="x-honeycomb-team=B85YgLm96******"
                # Split only on first '=' occurrence
                parts = headers.split("=", 1)
                if len(parts) == 2:
                    _split_otel_headers = {parts[0]: parts[1]}
                else:
                    _split_otel_headers = {}
            elif isinstance(headers, dict):
                _split_otel_headers = headers
        return _split_otel_headers

    async def async_management_endpoint_success_hook(
        self,
        logging_payload: ManagementEndpointLoggingPayload,
        parent_otel_span: Optional[Span] = None,
    ):
        from opentelemetry import trace
        from opentelemetry.trace import Status, StatusCode

        _start_time_ns = 0
        _end_time_ns = 0

        start_time = logging_payload.start_time
        end_time = logging_payload.end_time

        if isinstance(start_time, float):
            _start_time_ns = int(start_time * 1e9)
        else:
            _start_time_ns = self._to_ns(start_time)

        if isinstance(end_time, float):
            _end_time_ns = int(end_time * 1e9)
        else:
            _end_time_ns = self._to_ns(end_time)

        if parent_otel_span is not None:
            _span_name = logging_payload.route
            management_endpoint_span = self.tracer.start_span(
                name=_span_name,
                context=trace.set_span_in_context(parent_otel_span),
                start_time=_start_time_ns,
            )

            _request_data = logging_payload.request_data
            if _request_data is not None:
                for key, value in _request_data.items():
                    self.safe_set_attribute(
                        span=management_endpoint_span,
                        key=f"request.{key}",
                        value=value,
                    )

            _response = logging_payload.response
            if _response is not None:
                for key, value in _response.items():
                    self.safe_set_attribute(
                        span=management_endpoint_span,
                        key=f"response.{key}",
                        value=value,
                    )

            management_endpoint_span.set_status(Status(StatusCode.OK))
            management_endpoint_span.end(end_time=_end_time_ns)

    async def async_management_endpoint_failure_hook(
        self,
        logging_payload: ManagementEndpointLoggingPayload,
        parent_otel_span: Optional[Span] = None,
    ):
        from opentelemetry import trace
        from opentelemetry.trace import Status, StatusCode

        _start_time_ns = 0
        _end_time_ns = 0

        start_time = logging_payload.start_time
        end_time = logging_payload.end_time

        if isinstance(start_time, float):
            _start_time_ns = int(int(start_time) * 1e9)
        else:
            _start_time_ns = self._to_ns(start_time)

        if isinstance(end_time, float):
            _end_time_ns = int(int(end_time) * 1e9)
        else:
            _end_time_ns = self._to_ns(end_time)

        if parent_otel_span is not None:
            _span_name = logging_payload.route
            management_endpoint_span = self.tracer.start_span(
                name=_span_name,
                context=trace.set_span_in_context(parent_otel_span),
                start_time=_start_time_ns,
            )

            _request_data = logging_payload.request_data
            if _request_data is not None:
                for key, value in _request_data.items():
                    self.safe_set_attribute(
                        span=management_endpoint_span,
                        key=f"request.{key}",
                        value=value,
                    )

            _exception = logging_payload.exception
            self.safe_set_attribute(
                span=management_endpoint_span,
                key="exception",
                value=str(_exception),
            )
            management_endpoint_span.set_status(Status(StatusCode.ERROR))
            management_endpoint_span.end(end_time=_end_time_ns)

    def create_litellm_proxy_request_started_span(
        self,
        start_time: datetime,
        headers: dict,
    ) -> Optional[Span]:
        """
        Create a span for the received proxy server request.
        """
        return self.tracer.start_span(
            name="Received Proxy Server Request",
            start_time=self._to_ns(start_time),
            context=self.get_traceparent_from_header(headers=headers),
            kind=self.span_kind.SERVER,
        )

# === NexusCore/openenv\Lib\site-packages\fsspec\asyn.py ===
import asyncio
import asyncio.events
import functools
import inspect
import io
import numbers
import os
import re
import threading
from contextlib import contextmanager
from glob import has_magic
from typing import TYPE_CHECKING, Iterable

from .callbacks import DEFAULT_CALLBACK
from .exceptions import FSTimeoutError
from .implementations.local import LocalFileSystem, make_path_posix, trailing_sep
from .spec import AbstractBufferedFile, AbstractFileSystem
from .utils import glob_translate, is_exception, other_paths

private = re.compile("_[^_]")
iothread = [None]  # dedicated fsspec IO thread
loop = [None]  # global event loop for any non-async instance
_lock = None  # global lock placeholder
get_running_loop = asyncio.get_running_loop


def get_lock():
    """Allocate or return a threading lock.

    The lock is allocated on first use to allow setting one lock per forked process.
    """
    global _lock
    if not _lock:
        _lock = threading.Lock()
    return _lock


def reset_lock():
    """Reset the global lock.

    This should be called only on the init of a forked process to reset the lock to
    None, enabling the new forked process to get a new lock.
    """
    global _lock

    iothread[0] = None
    loop[0] = None
    _lock = None


async def _runner(event, coro, result, timeout=None):
    timeout = timeout if timeout else None  # convert 0 or 0.0 to None
    if timeout is not None:
        coro = asyncio.wait_for(coro, timeout=timeout)
    try:
        result[0] = await coro
    except Exception as ex:
        result[0] = ex
    finally:
        event.set()


def sync(loop, func, *args, timeout=None, **kwargs):
    """
    Make loop run coroutine until it returns. Runs in other thread

    Examples
    --------
    >>> fsspec.asyn.sync(fsspec.asyn.get_loop(), func, *args,
                         timeout=timeout, **kwargs)
    """
    timeout = timeout if timeout else None  # convert 0 or 0.0 to None
    # NB: if the loop is not running *yet*, it is OK to submit work
    # and we will wait for it
    if loop is None or loop.is_closed():
        raise RuntimeError("Loop is not running")
    try:
        loop0 = asyncio.events.get_running_loop()
        if loop0 is loop:
            raise NotImplementedError("Calling sync() from within a running loop")
    except NotImplementedError:
        raise
    except RuntimeError:
        pass
    coro = func(*args, **kwargs)
    result = [None]
    event = threading.Event()
    asyncio.run_coroutine_threadsafe(_runner(event, coro, result, timeout), loop)
    while True:
        # this loops allows thread to get interrupted
        if event.wait(1):
            break
        if timeout is not None:
            timeout -= 1
            if timeout < 0:
                raise FSTimeoutError

    return_result = result[0]
    if isinstance(return_result, asyncio.TimeoutError):
        # suppress asyncio.TimeoutError, raise FSTimeoutError
        raise FSTimeoutError from return_result
    elif isinstance(return_result, BaseException):
        raise return_result
    else:
        return return_result


def sync_wrapper(func, obj=None):
    """Given a function, make so can be called in blocking contexts

    Leave obj=None if defining within a class. Pass the instance if attaching
    as an attribute of the instance.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        self = obj or args[0]
        return sync(self.loop, func, *args, **kwargs)

    return wrapper


@contextmanager
def _selector_policy():
    original_policy = asyncio.get_event_loop_policy()
    try:
        if os.name == "nt" and hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        yield
    finally:
        asyncio.set_event_loop_policy(original_policy)


def get_loop():
    """Create or return the default fsspec IO loop

    The loop will be running on a separate thread.
    """
    if loop[0] is None:
        with get_lock():
            # repeat the check just in case the loop got filled between the
            # previous two calls from another thread
            if loop[0] is None:
                with _selector_policy():
                    loop[0] = asyncio.new_event_loop()
                th = threading.Thread(target=loop[0].run_forever, name="fsspecIO")
                th.daemon = True
                th.start()
                iothread[0] = th
    return loop[0]


def reset_after_fork():
    global lock
    loop[0] = None
    iothread[0] = None
    lock = None


if hasattr(os, "register_at_fork"):
    # should be posix; this will do nothing for spawn or forkserver subprocesses
    os.register_at_fork(after_in_child=reset_after_fork)


if TYPE_CHECKING:
    import resource

    ResourceError = resource.error
else:
    try:
        import resource
    except ImportError:
        resource = None
        ResourceError = OSError
    else:
        ResourceError = getattr(resource, "error", OSError)

_DEFAULT_BATCH_SIZE = 128
_NOFILES_DEFAULT_BATCH_SIZE = 1280


def _get_batch_size(nofiles=False):
    from fsspec.config import conf

    if nofiles:
        if "nofiles_gather_batch_size" in conf:
            return conf["nofiles_gather_batch_size"]
    else:
        if "gather_batch_size" in conf:
            return conf["gather_batch_size"]
    if nofiles:
        return _NOFILES_DEFAULT_BATCH_SIZE
    if resource is None:
        return _DEFAULT_BATCH_SIZE

    try:
        soft_limit, _ = resource.getrlimit(resource.RLIMIT_NOFILE)
    except (ImportError, ValueError, ResourceError):
        return _DEFAULT_BATCH_SIZE

    if soft_limit == resource.RLIM_INFINITY:
        return -1
    else:
        return soft_limit // 8


def running_async() -> bool:
    """Being executed by an event loop?"""
    try:
        asyncio.get_running_loop()
        return True
    except RuntimeError:
        return False


async def _run_coros_in_chunks(
    coros,
    batch_size=None,
    callback=DEFAULT_CALLBACK,
    timeout=None,
    return_exceptions=False,
    nofiles=False,
):
    """Run the given coroutines in  chunks.

    Parameters
    ----------
    coros: list of coroutines to run
    batch_size: int or None
        Number of coroutines to submit/wait on simultaneously.
        If -1, then it will not be any throttling. If
        None, it will be inferred from _get_batch_size()
    callback: fsspec.callbacks.Callback instance
        Gets a relative_update when each coroutine completes
    timeout: number or None
        If given, each coroutine times out after this time. Note that, since
        there are multiple batches, the total run time of this function will in
        general be longer
    return_exceptions: bool
        Same meaning as in asyncio.gather
    nofiles: bool
        If inferring the batch_size, does this operation involve local files?
        If yes, you normally expect smaller batches.
    """

    if batch_size is None:
        batch_size = _get_batch_size(nofiles=nofiles)

    if batch_size == -1:
        batch_size = len(coros)

    assert batch_size > 0

    async def _run_coro(coro, i):
        try:
            return await asyncio.wait_for(coro, timeout=timeout), i
        except Exception as e:
            if not return_exceptions:
                raise
            return e, i
        finally:
            callback.relative_update(1)

    i = 0
    n = len(coros)
    results = [None] * n
    pending = set()

    while pending or i < n:
        while len(pending) < batch_size and i < n:
            pending.add(asyncio.ensure_future(_run_coro(coros[i], i)))
            i += 1

        if not pending:
            break

        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
        while done:
            result, k = await done.pop()
            results[k] = result

    return results


# these methods should be implemented as async by any async-able backend
async_methods = [
    "_ls",
    "_cat_file",
    "_get_file",
    "_put_file",
    "_rm_file",
    "_cp_file",
    "_pipe_file",
    "_expand_path",
    "_info",
    "_isfile",
    "_isdir",
    "_exists",
    "_walk",
    "_glob",
    "_find",
    "_du",
    "_size",
    "_mkdir",
    "_makedirs",
]


class AsyncFileSystem(AbstractFileSystem):
    """Async file operations, default implementations

    Passes bulk operations to asyncio.gather for concurrent operation.

    Implementations that have concurrent batch operations and/or async methods
    should inherit from this class instead of AbstractFileSystem. Docstrings are
    copied from the un-underscored method in AbstractFileSystem, if not given.
    """

    # note that methods do not have docstring here; they will be copied
    # for _* methods and inferred for overridden methods.

    async_impl = True
    mirror_sync_methods = True
    disable_throttling = False

    def __init__(self, *args, asynchronous=False, loop=None, batch_size=None, **kwargs):
        self.asynchronous = asynchronous
        self._pid = os.getpid()
        if not asynchronous:
            self._loop = loop or get_loop()
        else:
            self._loop = None
        self.batch_size = batch_size
        super().__init__(*args, **kwargs)

    @property
    def loop(self):
        if self._pid != os.getpid():
            raise RuntimeError("This class is not fork-safe")
        return self._loop

    async def _rm_file(self, path, **kwargs):
        raise NotImplementedError

    async def _rm(self, path, recursive=False, batch_size=None, **kwargs):
        # TODO: implement on_error
        batch_size = batch_size or self.batch_size
        path = await self._expand_path(path, recursive=recursive)
        return await _run_coros_in_chunks(
            [self._rm_file(p, **kwargs) for p in reversed(path)],
            batch_size=batch_size,
            nofiles=True,
        )

    async def _cp_file(self, path1, path2, **kwargs):
        raise NotImplementedError

    async def _mv_file(self, path1, path2):
        await self._cp_file(path1, path2)
        await self._rm_file(path1)

    async def _copy(
        self,
        path1,
        path2,
        recursive=False,
        on_error=None,
        maxdepth=None,
        batch_size=None,
        **kwargs,
    ):
        if on_error is None and recursive:
            on_error = "ignore"
        elif on_error is None:
            on_error = "raise"

        if isinstance(path1, list) and isinstance(path2, list):
            # No need to expand paths when both source and destination
            # are provided as lists
            paths1 = path1
            paths2 = path2
        else:
            source_is_str = isinstance(path1, str)
            paths1 = await self._expand_path(
                path1, maxdepth=maxdepth, recursive=recursive
            )
            if source_is_str and (not recursive or maxdepth is not None):
                # Non-recursive glob does not copy directories
                paths1 = [
                    p for p in paths1 if not (trailing_sep(p) or await self._isdir(p))
                ]
                if not paths1:
                    return

            source_is_file = len(paths1) == 1
            dest_is_dir = isinstance(path2, str) and (
                trailing_sep(path2) or await self._isdir(path2)
            )

            exists = source_is_str and (
                (has_magic(path1) and source_is_file)
                or (not has_magic(path1) and dest_is_dir and not trailing_sep(path1))
            )
            paths2 = other_paths(
                paths1,
                path2,
                exists=exists,
                flatten=not source_is_str,
            )

        batch_size = batch_size or self.batch_size
        coros = [self._cp_file(p1, p2, **kwargs) for p1, p2 in zip(paths1, paths2)]
        result = await _run_coros_in_chunks(
            coros, batch_size=batch_size, return_exceptions=True, nofiles=True
        )

        for ex in filter(is_exception, result):
            if on_error == "ignore" and isinstance(ex, FileNotFoundError):
                continue
            raise ex

    async def _pipe_file(self, path, value, mode="overwrite", **kwargs):
        raise NotImplementedError

    async def _pipe(self, path, value=None, batch_size=None, **kwargs):
        if isinstance(path, str):
            path = {path: value}
        batch_size = batch_size or self.batch_size
        return await _run_coros_in_chunks(
            [self._pipe_file(k, v, **kwargs) for k, v in path.items()],
            batch_size=batch_size,
            nofiles=True,
        )

    async def _process_limits(self, url, start, end):
        """Helper for "Range"-based _cat_file"""
        size = None
        suff = False
        if start is not None and start < 0:
            # if start is negative and end None, end is the "suffix length"
            if end is None:
                end = -start
                start = ""
                suff = True
            else:
                size = size or (await self._info(url))["size"]
                start = size + start
        elif start is None:
            start = 0
        if not suff:
            if end is not None and end < 0:
                if start is not None:
                    size = size or (await self._info(url))["size"]
                    end = size + end
            elif end is None:
                end = ""
            if isinstance(end, numbers.Integral):
                end -= 1  # bytes range is inclusive
        return f"bytes={start}-{end}"

    async def _cat_file(self, path, start=None, end=None, **kwargs):
        raise NotImplementedError

    async def _cat(
        self, path, recursive=False, on_error="raise", batch_size=None, **kwargs
    ):
        paths = await self._expand_path(path, recursive=recursive)
        coros = [self._cat_file(path, **kwargs) for path in paths]
        batch_size = batch_size or self.batch_size
        out = await _run_coros_in_chunks(
            coros, batch_size=batch_size, nofiles=True, return_exceptions=True
        )
        if on_error == "raise":
            ex = next(filter(is_exception, out), False)
            if ex:
                raise ex
        if (
            len(paths) > 1
            or isinstance(path, list)
            or paths[0] != self._strip_protocol(path)
        ):
            return {
                k: v
                for k, v in zip(paths, out)
                if on_error != "omit" or not is_exception(v)
            }
        else:
            return out[0]

    async def _cat_ranges(
        self,
        paths,
        starts,
        ends,
        max_gap=None,
        batch_size=None,
        on_error="return",
        **kwargs,
    ):
        """Get the contents of byte ranges from one or more files

        Parameters
        ----------
        paths: list
            A list of of filepaths on this filesystems
        starts, ends: int or list
            Bytes limits of the read. If using a single int, the same value will be
            used to read all the specified files.
        """
        # TODO: on_error
        if max_gap is not None:
            # use utils.merge_offset_ranges
            raise NotImplementedError
        if not isinstance(paths, list):
            raise TypeError
        if not isinstance(starts, Iterable):
            starts = [starts] * len(paths)
        if not isinstance(ends, Iterable):
            ends = [ends] * len(paths)
        if len(starts) != len(paths) or len(ends) != len(paths):
            raise ValueError
        coros = [
            self._cat_file(p, start=s, end=e, **kwargs)
            for p, s, e in zip(paths, starts, ends)
        ]
        batch_size = batch_size or self.batch_size
        return await _run_coros_in_chunks(
            coros, batch_size=batch_size, nofiles=True, return_exceptions=True
        )

    async def _put_file(self, lpath, rpath, mode="overwrite", **kwargs):
        raise NotImplementedError

    async def _put(
        self,
        lpath,
        rpath,
        recursive=False,
        callback=DEFAULT_CALLBACK,
        batch_size=None,
        maxdepth=None,
        **kwargs,
    ):
        """Copy file(s) from local.

        Copies a specific file or tree of files (if recursive=True). If rpath
        ends with a "/", it will be assumed to be a directory, and target files
        will go within.

        The put_file method will be called concurrently on a batch of files. The
        batch_size option can configure the amount of futures that can be executed
        at the same time. If it is -1, then all the files will be uploaded concurrently.
        The default can be set for this instance by passing "batch_size" in the
        constructor, or for all instances by setting the "gather_batch_size" key
        in ``fsspec.config.conf``, falling back to 1/8th of the system limit .
        """
        if isinstance(lpath, list) and isinstance(rpath, list):
            # No need to expand paths when both source and destination
            # are provided as lists
            rpaths = rpath
            lpaths = lpath
        else:
            source_is_str = isinstance(lpath, str)
            if source_is_str:
                lpath = make_path_posix(lpath)
            fs = LocalFileSystem()
            lpaths = fs.expand_path(lpath, recursive=recursive, maxdepth=maxdepth)
            if source_is_str and (not recursive or maxdepth is not None):
                # Non-recursive glob does not copy directories
                lpaths = [p for p in lpaths if not (trailing_sep(p) or fs.isdir(p))]
                if not lpaths:
                    return

            source_is_file = len(lpaths) == 1
            dest_is_dir = isinstance(rpath, str) and (
                trailing_sep(rpath) or await self._isdir(rpath)
            )

            rpath = self._strip_protocol(rpath)
            exists = source_is_str and (
                (has_magic(lpath) and source_is_file)
                or (not has_magic(lpath) and dest_is_dir and not trailing_sep(lpath))
            )
            rpaths = other_paths(
                lpaths,
                rpath,
                exists=exists,
                flatten=not source_is_str,
            )

        is_dir = {l: os.path.isdir(l) for l in lpaths}
        rdirs = [r for l, r in zip(lpaths, rpaths) if is_dir[l]]
        file_pairs = [(l, r) for l, r in zip(lpaths, rpaths) if not is_dir[l]]

        await asyncio.gather(*[self._makedirs(d, exist_ok=True) for d in rdirs])
        batch_size = batch_size or self.batch_size

        coros = []
        callback.set_size(len(file_pairs))
        for lfile, rfile in file_pairs:
            put_file = callback.branch_coro(self._put_file)
            coros.append(put_file(lfile, rfile, **kwargs))

        return await _run_coros_in_chunks(
            coros, batch_size=batch_size, callback=callback
        )

    async def _get_file(self, rpath, lpath, **kwargs):
        raise NotImplementedError

    async def _get(
        self,
        rpath,
        lpath,
        recursive=False,
        callback=DEFAULT_CALLBACK,
        maxdepth=None,
        **kwargs,
    ):
        """Copy file(s) to local.

        Copies a specific file or tree of files (if recursive=True). If lpath
        ends with a "/", it will be assumed to be a directory, and target files
        will go within. Can submit a list of paths, which may be glob-patterns
        and will be expanded.

        The get_file method will be called concurrently on a batch of files. The
        batch_size option can configure the amount of futures that can be executed
        at the same time. If it is -1, then all the files will be uploaded concurrently.
        The default can be set for this instance by passing "batch_size" in the
        constructor, or for all instances by setting the "gather_batch_size" key
        in ``fsspec.config.conf``, falling back to 1/8th of the system limit .
        """
        if isinstance(lpath, list) and isinstance(rpath, list):
            # No need to expand paths when both source and destination
            # are provided as lists
            rpaths = rpath
            lpaths = lpath
        else:
            source_is_str = isinstance(rpath, str)
            # First check for rpath trailing slash as _strip_protocol removes it.
            source_not_trailing_sep = source_is_str and not trailing_sep(rpath)
            rpath = self._strip_protocol(rpath)
            rpaths = await self._expand_path(
                rpath, recursive=recursive, maxdepth=maxdepth
            )
            if source_is_str and (not recursive or maxdepth is not None):
                # Non-recursive glob does not copy directories
                rpaths = [
                    p for p in rpaths if not (trailing_sep(p) or await self._isdir(p))
                ]
                if not rpaths:
                    return

            lpath = make_path_posix(lpath)
            source_is_file = len(rpaths) == 1
            dest_is_dir = isinstance(lpath, str) and (
                trailing_sep(lpath) or LocalFileSystem().isdir(lpath)
            )

            exists = source_is_str and (
                (has_magic(rpath) and source_is_file)
                or (not has_magic(rpath) and dest_is_dir and source_not_trailing_sep)
            )
            lpaths = other_paths(
                rpaths,
                lpath,
                exists=exists,
                flatten=not source_is_str,
            )

        [os.makedirs(os.path.dirname(lp), exist_ok=True) for lp in lpaths]
        batch_size = kwargs.pop("batch_size", self.batch_size)

        coros = []
        callback.set_size(len(lpaths))
        for lpath, rpath in zip(lpaths, rpaths):
            get_file = callback.branch_coro(self._get_file)
            coros.append(get_file(rpath, lpath, **kwargs))
        return await _run_coros_in_chunks(
            coros, batch_size=batch_size, callback=callback
        )

    async def _isfile(self, path):
        try:
            return (await self._info(path))["type"] == "file"
        except:  # noqa: E722
            return False

    async def _isdir(self, path):
        try:
            return (await self._info(path))["type"] == "directory"
        except OSError:
            return False

    async def _size(self, path):
        return (await self._info(path)).get("size", None)

    async def _sizes(self, paths, batch_size=None):
        batch_size = batch_size or self.batch_size
        return await _run_coros_in_chunks(
            [self._size(p) for p in paths], batch_size=batch_size
        )

    async def _exists(self, path, **kwargs):
        try:
            await self._info(path, **kwargs)
            return True
        except FileNotFoundError:
            return False

    async def _info(self, path, **kwargs):
        raise NotImplementedError

    async def _ls(self, path, detail=True, **kwargs):
        raise NotImplementedError

    async def _walk(self, path, maxdepth=None, on_error="omit", **kwargs):
        if maxdepth is not None and maxdepth < 1:
            raise ValueError("maxdepth must be at least 1")

        path = self._strip_protocol(path)
        full_dirs = {}
        dirs = {}
        files = {}

        detail = kwargs.pop("detail", False)
        try:
            listing = await self._ls(path, detail=True, **kwargs)
        except (FileNotFoundError, OSError) as e:
            if on_error == "raise":
                raise
            elif callable(on_error):
                on_error(e)
            if detail:
                yield path, {}, {}
            else:
                yield path, [], []
            return

        for info in listing:
            # each info name must be at least [path]/part , but here
            # we check also for names like [path]/part/
            pathname = info["name"].rstrip("/")
            name = pathname.rsplit("/", 1)[-1]
            if info["type"] == "directory" and pathname != path:
                # do not include "self" path
                full_dirs[name] = pathname
                dirs[name] = info
            elif pathname == path:
                # file-like with same name as give path
                files[""] = info
            else:
                files[name] = info

        if detail:
            yield path, dirs, files
        else:
            yield path, list(dirs), list(files)

        if maxdepth is not None:
            maxdepth -= 1
            if maxdepth < 1:
                return

        for d in dirs:
            async for _ in self._walk(
                full_dirs[d], maxdepth=maxdepth, detail=detail, **kwargs
            ):
                yield _

    async def _glob(self, path, maxdepth=None, **kwargs):
        if maxdepth is not None and maxdepth < 1:
            raise ValueError("maxdepth must be at least 1")

        import re

        seps = (os.path.sep, os.path.altsep) if os.path.altsep else (os.path.sep,)
        ends_with_sep = path.endswith(seps)  # _strip_protocol strips trailing slash
        path = self._strip_protocol(path)
        append_slash_to_dirname = ends_with_sep or path.endswith(
            tuple(sep + "**" for sep in seps)
        )
        idx_star = path.find("*") if path.find("*") >= 0 else len(path)
        idx_qmark = path.find("?") if path.find("?") >= 0 else len(path)
        idx_brace = path.find("[") if path.find("[") >= 0 else len(path)

        min_idx = min(idx_star, idx_qmark, idx_brace)

        detail = kwargs.pop("detail", False)

        if not has_magic(path):
            if await self._exists(path, **kwargs):
                if not detail:
                    return [path]
                else:
                    return {path: await self._info(path, **kwargs)}
            else:
                if not detail:
                    return []  # glob of non-existent returns empty
                else:
                    return {}
        elif "/" in path[:min_idx]:
            min_idx = path[:min_idx].rindex("/")
            root = path[: min_idx + 1]
            depth = path[min_idx + 1 :].count("/") + 1
        else:
            root = ""
            depth = path[min_idx + 1 :].count("/") + 1

        if "**" in path:
            if maxdepth is not None:
                idx_double_stars = path.find("**")
                depth_double_stars = path[idx_double_stars:].count("/") + 1
                depth = depth - depth_double_stars + maxdepth
            else:
                depth = None

        allpaths = await self._find(
            root, maxdepth=depth, withdirs=True, detail=True, **kwargs
        )

        pattern = glob_translate(path + ("/" if ends_with_sep else ""))
        pattern = re.compile(pattern)

        out = {
            p: info
            for p, info in sorted(allpaths.items())
            if pattern.match(
                p + "/"
                if append_slash_to_dirname and info["type"] == "directory"
                else p
            )
        }

        if detail:
            return out
        else:
            return list(out)

    async def _du(self, path, total=True, maxdepth=None, **kwargs):
        sizes = {}
        # async for?
        for f in await self._find(path, maxdepth=maxdepth, **kwargs):
            info = await self._info(f)
            sizes[info["name"]] = info["size"]
        if total:
            return sum(sizes.values())
        else:
            return sizes

    async def _find(self, path, maxdepth=None, withdirs=False, **kwargs):
        path = self._strip_protocol(path)
        out = {}
        detail = kwargs.pop("detail", False)

        # Add the root directory if withdirs is requested
        # This is needed for posix glob compliance
        if withdirs and path != "" and await self._isdir(path):
            out[path] = await self._info(path)

        # async for?
        async for _, dirs, files in self._walk(path, maxdepth, detail=True, **kwargs):
            if withdirs:
                files.update(dirs)
            out.update({info["name"]: info for name, info in files.items()})
        if not out and (await self._isfile(path)):
            # walk works on directories, but find should also return [path]
            # when path happens to be a file
            out[path] = {}
        names = sorted(out)
        if not detail:
            return names
        else:
            return {name: out[name] for name in names}

    async def _expand_path(self, path, recursive=False, maxdepth=None):
        if maxdepth is not None and maxdepth < 1:
            raise ValueError("maxdepth must be at least 1")

        if isinstance(path, str):
            out = await self._expand_path([path], recursive, maxdepth)
        else:
            out = set()
            path = [self._strip_protocol(p) for p in path]
            for p in path:  # can gather here
                if has_magic(p):
                    bit = set(await self._glob(p, maxdepth=maxdepth))
                    out |= bit
                    if recursive:
                        # glob call above expanded one depth so if maxdepth is defined
                        # then decrement it in expand_path call below. If it is zero
                        # after decrementing then avoid expand_path call.
                        if maxdepth is not None and maxdepth <= 1:
                            continue
                        out |= set(
                            await self._expand_path(
                                list(bit),
                                recursive=recursive,
                                maxdepth=maxdepth - 1 if maxdepth is not None else None,
                            )
                        )
                    continue
                elif recursive:
                    rec = set(await self._find(p, maxdepth=maxdepth, withdirs=True))
                    out |= rec
                if p not in out and (recursive is False or (await self._exists(p))):
                    # should only check once, for the root
                    out.add(p)
        if not out:
            raise FileNotFoundError(path)
        return sorted(out)

    async def _mkdir(self, path, create_parents=True, **kwargs):
        pass  # not necessary to implement, may not have directories

    async def _makedirs(self, path, exist_ok=False):
        pass  # not necessary to implement, may not have directories

    async def open_async(self, path, mode="rb", **kwargs):
        if "b" not in mode or kwargs.get("compression"):
            raise ValueError
        raise NotImplementedError


def mirror_sync_methods(obj):
    """Populate sync and async methods for obj

    For each method will create a sync version if the name refers to an async method
    (coroutine) and there is no override in the child class; will create an async
    method for the corresponding sync method if there is no implementation.

    Uses the methods specified in
    - async_methods: the set that an implementation is expected to provide
    - default_async_methods: that can be derived from their sync version in
      AbstractFileSystem
    - AsyncFileSystem: async-specific default coroutines
    """
    from fsspec import AbstractFileSystem

    for method in async_methods + dir(AsyncFileSystem):
        if not method.startswith("_"):
            continue
        smethod = method[1:]
        if private.match(method):
            isco = inspect.iscoroutinefunction(getattr(obj, method, None))
            unsync = getattr(getattr(obj, smethod, False), "__func__", None)
            is_default = unsync is getattr(AbstractFileSystem, smethod, "")
            if isco and is_default:
                mth = sync_wrapper(getattr(obj, method), obj=obj)
                setattr(obj, smethod, mth)
                if not mth.__doc__:
                    mth.__doc__ = getattr(
                        getattr(AbstractFileSystem, smethod, None), "__doc__", ""
                    )


class FSSpecCoroutineCancel(Exception):
    pass


def _dump_running_tasks(
    printout=True, cancel=True, exc=FSSpecCoroutineCancel, with_task=False
):
    import traceback

    tasks = [t for t in asyncio.tasks.all_tasks(loop[0]) if not t.done()]
    if printout:
        [task.print_stack() for task in tasks]
    out = [
        {
            "locals": task._coro.cr_frame.f_locals,
            "file": task._coro.cr_frame.f_code.co_filename,
            "firstline": task._coro.cr_frame.f_code.co_firstlineno,
            "linelo": task._coro.cr_frame.f_lineno,
            "stack": traceback.format_stack(task._coro.cr_frame),
            "task": task if with_task else None,
        }
        for task in tasks
    ]
    if cancel:
        for t in tasks:
            cbs = t._callbacks
            t.cancel()
            asyncio.futures.Future.set_exception(t, exc)
            asyncio.futures.Future.cancel(t)
            [cb[0](t) for cb in cbs]  # cancels any dependent concurrent.futures
            try:
                t._coro.throw(exc)  # exits coro, unless explicitly handled
            except exc:
                pass
    return out


class AbstractAsyncStreamedFile(AbstractBufferedFile):
    # no read buffering, and always auto-commit
    # TODO: readahead might still be useful here, but needs async version

    async def read(self, length=-1):
        """
        Return data from cache, or fetch pieces as necessary

        Parameters
        ----------
        length: int (-1)
            Number of bytes to read; if <0, all remaining bytes.
        """
        length = -1 if length is None else int(length)
        if self.mode != "rb":
            raise ValueError("File not in read mode")
        if length < 0:
            length = self.size - self.loc
        if self.closed:
            raise ValueError("I/O operation on closed file.")
        if length == 0:
            # don't even bother calling fetch
            return b""
        out = await self._fetch_range(self.loc, self.loc + length)
        self.loc += len(out)
        return out

    async def write(self, data):
        """
        Write data to buffer.

        Buffer only sent on flush() or if buffer is greater than
        or equal to blocksize.

        Parameters
        ----------
        data: bytes
            Set of bytes to be written.
        """
        if self.mode not in {"wb", "ab"}:
            raise ValueError("File not in write mode")
        if self.closed:
            raise ValueError("I/O operation on closed file.")
        if self.forced:
            raise ValueError("This file has been force-flushed, can only close")
        out = self.buffer.write(data)
        self.loc += out
        if self.buffer.tell() >= self.blocksize:
            await self.flush()
        return out

    async def close(self):
        """Close file

        Finalizes writes, discards cache
        """
        if getattr(self, "_unclosable", False):
            return
        if self.closed:
            return
        if self.mode == "rb":
            self.cache = None
        else:
            if not self.forced:
                await self.flush(force=True)

            if self.fs is not None:
                self.fs.invalidate_cache(self.path)
                self.fs.invalidate_cache(self.fs._parent(self.path))

        self.closed = True

    async def flush(self, force=False):
        if self.closed:
            raise ValueError("Flush on closed file")
        if force and self.forced:
            raise ValueError("Force flush cannot be called more than once")
        if force:
            self.forced = True

        if self.mode not in {"wb", "ab"}:
            # no-op to flush on read-mode
            return

        if not force and self.buffer.tell() < self.blocksize:
            # Defer write on small block
            return

        if self.offset is None:
            # Initialize a multipart upload
            self.offset = 0
            try:
                await self._initiate_upload()
            except:
                self.closed = True
                raise

        if await self._upload_chunk(final=force) is not False:
            self.offset += self.buffer.seek(0, 2)
            self.buffer = io.BytesIO()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def _fetch_range(self, start, end):
        raise NotImplementedError

    async def _initiate_upload(self):
        pass

    async def _upload_chunk(self, final=False):
        raise NotImplementedError