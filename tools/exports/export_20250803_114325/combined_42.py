
# === NexusCore/openenv\Lib\site-packages\pyasn1\type\univ.py ===
#
# This file is part of pyasn1 software.
#
# Copyright (c) 2005-2020, Ilya Etingof <etingof@gmail.com>
# License: https://pyasn1.readthedocs.io/en/latest/license.html
#
import math
import sys

from pyasn1 import error
from pyasn1.codec.ber import eoo
from pyasn1.compat import integer
from pyasn1.type import base
from pyasn1.type import constraint
from pyasn1.type import namedtype
from pyasn1.type import namedval
from pyasn1.type import tag
from pyasn1.type import tagmap

NoValue = base.NoValue
noValue = NoValue()

__all__ = ['Integer', 'Boolean', 'BitString', 'OctetString', 'Null',
           'ObjectIdentifier', 'Real', 'Enumerated',
           'SequenceOfAndSetOfBase', 'SequenceOf', 'SetOf',
           'SequenceAndSetBase', 'Sequence', 'Set', 'Choice', 'Any',
           'NoValue', 'noValue']

# "Simple" ASN.1 types (yet incomplete)


class Integer(base.SimpleAsn1Type):
    """Create |ASN.1| schema or value object.

    |ASN.1| class is based on :class:`~pyasn1.type.base.SimpleAsn1Type`, its
    objects are immutable and duck-type Python :class:`int` objects.

    Keyword Args
    ------------
    value: :class:`int`, :class:`str` or |ASN.1| object
        Python :class:`int` or :class:`str` literal or |ASN.1| class
        instance. If `value` is not given, schema object will be created.

    tagSet: :py:class:`~pyasn1.type.tag.TagSet`
        Object representing non-default ASN.1 tag(s)

    subtypeSpec: :py:class:`~pyasn1.type.constraint.ConstraintsIntersection`
        Object representing non-default ASN.1 subtype constraint(s). Constraints
        verification for |ASN.1| type occurs automatically on object
        instantiation.

    namedValues: :py:class:`~pyasn1.type.namedval.NamedValues`
        Object representing non-default symbolic aliases for numbers

    Raises
    ------
    ~pyasn1.error.ValueConstraintError, ~pyasn1.error.PyAsn1Error
        On constraint violation or bad initializer.

    Examples
    --------

    .. code-block:: python

        class ErrorCode(Integer):
            '''
            ASN.1 specification:

            ErrorCode ::=
                INTEGER { disk-full(1), no-disk(-1),
                          disk-not-formatted(2) }

            error ErrorCode ::= disk-full
            '''
            namedValues = NamedValues(
                ('disk-full', 1), ('no-disk', -1),
                ('disk-not-formatted', 2)
            )

        error = ErrorCode('disk-full')
    """
    #: Set (on class, not on instance) or return a
    #: :py:class:`~pyasn1.type.tag.TagSet` object representing ASN.1 tag(s)
    #: associated with |ASN.1| type.
    tagSet = tag.initTagSet(
        tag.Tag(tag.tagClassUniversal, tag.tagFormatSimple, 0x02)
    )

    #: Set (on class, not on instance) or return a
    #: :py:class:`~pyasn1.type.constraint.ConstraintsIntersection` object
    #: imposing constraints on |ASN.1| type initialization values.
    subtypeSpec = constraint.ConstraintsIntersection()

    #: Default :py:class:`~pyasn1.type.namedval.NamedValues` object
    #: representing symbolic aliases for numbers
    namedValues = namedval.NamedValues()

    # Optimization for faster codec lookup
    typeId = base.SimpleAsn1Type.getTypeId()

    def __init__(self, value=noValue, **kwargs):
        if 'namedValues' not in kwargs:
            kwargs['namedValues'] = self.namedValues

        base.SimpleAsn1Type.__init__(self, value, **kwargs)

    def __and__(self, value):
        return self.clone(self._value & value)

    def __rand__(self, value):
        return self.clone(value & self._value)

    def __or__(self, value):
        return self.clone(self._value | value)

    def __ror__(self, value):
        return self.clone(value | self._value)

    def __xor__(self, value):
        return self.clone(self._value ^ value)

    def __rxor__(self, value):
        return self.clone(value ^ self._value)

    def __lshift__(self, value):
        return self.clone(self._value << value)

    def __rshift__(self, value):
        return self.clone(self._value >> value)

    def __add__(self, value):
        return self.clone(self._value + value)

    def __radd__(self, value):
        return self.clone(value + self._value)

    def __sub__(self, value):
        return self.clone(self._value - value)

    def __rsub__(self, value):
        return self.clone(value - self._value)

    def __mul__(self, value):
        return self.clone(self._value * value)

    def __rmul__(self, value):
        return self.clone(value * self._value)

    def __mod__(self, value):
        return self.clone(self._value % value)

    def __rmod__(self, value):
        return self.clone(value % self._value)

    def __pow__(self, value, modulo=None):
        return self.clone(pow(self._value, value, modulo))

    def __rpow__(self, value):
        return self.clone(pow(value, self._value))

    def __floordiv__(self, value):
        return self.clone(self._value // value)

    def __rfloordiv__(self, value):
        return self.clone(value // self._value)

    def __truediv__(self, value):
        return Real(self._value / value)

    def __rtruediv__(self, value):
        return Real(value / self._value)

    def __divmod__(self, value):
        return self.clone(divmod(self._value, value))

    def __rdivmod__(self, value):
        return self.clone(divmod(value, self._value))

    __hash__ = base.SimpleAsn1Type.__hash__

    def __int__(self):
        return int(self._value)

    def __float__(self):
        return float(self._value)

    def __abs__(self):
        return self.clone(abs(self._value))

    def __index__(self):
        return int(self._value)

    def __pos__(self):
        return self.clone(+self._value)

    def __neg__(self):
        return self.clone(-self._value)

    def __invert__(self):
        return self.clone(~self._value)

    def __round__(self, n=0):
        r = round(self._value, n)
        if n:
            return self.clone(r)
        else:
            return r

    def __floor__(self):
        return math.floor(self._value)

    def __ceil__(self):
        return math.ceil(self._value)

    def __trunc__(self):
        return self.clone(math.trunc(self._value))

    def __lt__(self, value):
        return self._value < value

    def __le__(self, value):
        return self._value <= value

    def __eq__(self, value):
        return self._value == value

    def __ne__(self, value):
        return self._value != value

    def __gt__(self, value):
        return self._value > value

    def __ge__(self, value):
        return self._value >= value

    def prettyIn(self, value):
        try:
            return int(value)

        except ValueError:
            try:
                return self.namedValues[value]

            except KeyError as exc:
                raise error.PyAsn1Error(
                    'Can\'t coerce %r into integer: %s' % (value, exc)
                )

    def prettyOut(self, value):
        try:
            return str(self.namedValues[value])

        except KeyError:
            return str(value)

    # backward compatibility

    def getNamedValues(self):
        return self.namedValues


class Boolean(Integer):
    """Create |ASN.1| schema or value object.

    |ASN.1| class is based on :class:`~pyasn1.type.base.SimpleAsn1Type`, its
    objects are immutable and duck-type Python :class:`int` objects.

    Keyword Args
    ------------
    value: :class:`int`, :class:`str` or |ASN.1| object
        Python :class:`int` or :class:`str` literal or |ASN.1| class
        instance. If `value` is not given, schema object will be created.

    tagSet: :py:class:`~pyasn1.type.tag.TagSet`
        Object representing non-default ASN.1 tag(s)

    subtypeSpec: :py:class:`~pyasn1.type.constraint.ConstraintsIntersection`
        Object representing non-default ASN.1 subtype constraint(s).Constraints
        verification for |ASN.1| type occurs automatically on object
        instantiation.

    namedValues: :py:class:`~pyasn1.type.namedval.NamedValues`
        Object representing non-default symbolic aliases for numbers

    Raises
    ------
    ~pyasn1.error.ValueConstraintError, ~pyasn1.error.PyAsn1Error
        On constraint violation or bad initializer.

    Examples
    --------
    .. code-block:: python

        class RoundResult(Boolean):
            '''
            ASN.1 specification:

            RoundResult ::= BOOLEAN

            ok RoundResult ::= TRUE
            ko RoundResult ::= FALSE
            '''
        ok = RoundResult(True)
        ko = RoundResult(False)
    """
    #: Set (on class, not on instance) or return a
    #: :py:class:`~pyasn1.type.tag.TagSet` object representing ASN.1 tag(s)
    #: associated with |ASN.1| type.
    tagSet = tag.initTagSet(
        tag.Tag(tag.tagClassUniversal, tag.tagFormatSimple, 0x01),
    )

    #: Set (on class, not on instance) or return a
    #: :py:class:`~pyasn1.type.constraint.ConstraintsIntersection` object
    #: imposing constraints on |ASN.1| type initialization values.
    subtypeSpec = Integer.subtypeSpec + constraint.SingleValueConstraint(0, 1)

    #: Default :py:class:`~pyasn1.type.namedval.NamedValues` object
    #: representing symbolic aliases for numbers
    namedValues = namedval.NamedValues(('False', 0), ('True', 1))

    # Optimization for faster codec lookup
    typeId = Integer.getTypeId()


class SizedInteger(int):
    bitLength = leadingZeroBits = None

    def setBitLength(self, bitLength):
        self.bitLength = bitLength
        self.leadingZeroBits = max(bitLength - self.bit_length(), 0)
        return self

    def __len__(self):
        if self.bitLength is None:
            self.setBitLength(self.bit_length())

        return self.bitLength


class BitString(base.SimpleAsn1Type):
    """Create |ASN.1| schema or value object.

    |ASN.1| class is based on :class:`~pyasn1.type.base.SimpleAsn1Type`, its
    objects are immutable and duck-type both Python :class:`tuple` (as a tuple
    of bits) and :class:`int` objects.

    Keyword Args
    ------------
    value: :class:`int`, :class:`str` or |ASN.1| object
        Python :class:`int` or :class:`str` literal representing binary
        or hexadecimal number or sequence of integer bits or |ASN.1| object.
        If `value` is not given, schema object will be created.

    tagSet: :py:class:`~pyasn1.type.tag.TagSet`
        Object representing non-default ASN.1 tag(s)

    subtypeSpec: :py:class:`~pyasn1.type.constraint.ConstraintsIntersection`
        Object representing non-default ASN.1 subtype constraint(s). Constraints
        verification for |ASN.1| type occurs automatically on object
        instantiation.

    namedValues: :py:class:`~pyasn1.type.namedval.NamedValues`
        Object representing non-default symbolic aliases for numbers

    binValue: :py:class:`str`
        Binary string initializer to use instead of the *value*.
        Example: '10110011'.

    hexValue: :py:class:`str`
        Hexadecimal string initializer to use instead of the *value*.
        Example: 'DEADBEEF'.

    Raises
    ------
    ~pyasn1.error.ValueConstraintError, ~pyasn1.error.PyAsn1Error
        On constraint violation or bad initializer.

    Examples
    --------
    .. code-block:: python

        class Rights(BitString):
            '''
            ASN.1 specification:

            Rights ::= BIT STRING { user-read(0), user-write(1),
                                    group-read(2), group-write(3),
                                    other-read(4), other-write(5) }

            group1 Rights ::= { group-read, group-write }
            group2 Rights ::= '0011'B
            group3 Rights ::= '3'H
            '''
            namedValues = NamedValues(
                ('user-read', 0), ('user-write', 1),
                ('group-read', 2), ('group-write', 3),
                ('other-read', 4), ('other-write', 5)
            )

        group1 = Rights(('group-read', 'group-write'))
        group2 = Rights('0011')
        group3 = Rights(0x3)
    """
    #: Set (on class, not on instance) or return a
    #: :py:class:`~pyasn1.type.tag.TagSet` object representing ASN.1 tag(s)
    #: associated with |ASN.1| type.
    tagSet = tag.initTagSet(
        tag.Tag(tag.tagClassUniversal, tag.tagFormatSimple, 0x03)
    )

    #: Set (on class, not on instance) or return a
    #: :py:class:`~pyasn1.type.constraint.ConstraintsIntersection` object
    #: imposing constraints on |ASN.1| type initialization values.
    subtypeSpec = constraint.ConstraintsIntersection()

    #: Default :py:class:`~pyasn1.type.namedval.NamedValues` object
    #: representing symbolic aliases for numbers
    namedValues = namedval.NamedValues()

    # Optimization for faster codec lookup
    typeId = base.SimpleAsn1Type.getTypeId()

    defaultBinValue = defaultHexValue = noValue

    def __init__(self, value=noValue, **kwargs):
        if value is noValue:
            if kwargs:
                try:
                    value = self.fromBinaryString(kwargs.pop('binValue'), internalFormat=True)

                except KeyError:
                    pass

                try:
                    value = self.fromHexString(kwargs.pop('hexValue'), internalFormat=True)

                except KeyError:
                    pass

        if value is noValue:
            if self.defaultBinValue is not noValue:
                value = self.fromBinaryString(self.defaultBinValue, internalFormat=True)

            elif self.defaultHexValue is not noValue:
                value = self.fromHexString(self.defaultHexValue, internalFormat=True)

        if 'namedValues' not in kwargs:
            kwargs['namedValues'] = self.namedValues

        base.SimpleAsn1Type.__init__(self, value, **kwargs)

    def __str__(self):
        return self.asBinary()

    def __eq__(self, other):
        other = self.prettyIn(other)
        return self is other or self._value == other and len(self._value) == len(other)

    def __ne__(self, other):
        other = self.prettyIn(other)
        return self._value != other or len(self._value) != len(other)

    def __lt__(self, other):
        other = self.prettyIn(other)
        return len(self._value) < len(other) or len(self._value) == len(other) and self._value < other

    def __le__(self, other):
        other = self.prettyIn(other)
        return len(self._value) <= len(other) or len(self._value) == len(other) and self._value <= other

    def __gt__(self, other):
        other = self.prettyIn(other)
        return len(self._value) > len(other) or len(self._value) == len(other) and self._value > other

    def __ge__(self, other):
        other = self.prettyIn(other)
        return len(self._value) >= len(other) or len(self._value) == len(other) and self._value >= other

    # Immutable sequence object protocol

    def __len__(self):
        return len(self._value)

    def __getitem__(self, i):
        if i.__class__ is slice:
            return self.clone([self[x] for x in range(*i.indices(len(self)))])
        else:
            length = len(self._value) - 1
            if i > length or i < 0:
                raise IndexError('bit index out of range')
            return (self._value >> (length - i)) & 1

    def __iter__(self):
        length = len(self._value)
        while length:
            length -= 1
            yield (self._value >> length) & 1

    def __reversed__(self):
        return reversed(tuple(self))

    # arithmetic operators

    def __add__(self, value):
        value = self.prettyIn(value)
        return self.clone(SizedInteger(self._value << len(value) | value).setBitLength(len(self._value) + len(value)))

    def __radd__(self, value):
        value = self.prettyIn(value)
        return self.clone(SizedInteger(value << len(self._value) | self._value).setBitLength(len(self._value) + len(value)))

    def __mul__(self, value):
        bitString = self._value
        while value > 1:
            bitString <<= len(self._value)
            bitString |= self._value
            value -= 1
        return self.clone(bitString)

    def __rmul__(self, value):
        return self * value

    def __lshift__(self, count):
        return self.clone(SizedInteger(self._value << count).setBitLength(len(self._value) + count))

    def __rshift__(self, count):
        return self.clone(SizedInteger(self._value >> count).setBitLength(max(0, len(self._value) - count)))

    def __int__(self):
        return int(self._value)

    def __float__(self):
        return float(self._value)

    def asNumbers(self):
        """Get |ASN.1| value as a sequence of 8-bit integers.

        If |ASN.1| object length is not a multiple of 8, result
        will be left-padded with zeros.
        """
        return tuple(self.asOctets())

    def asOctets(self):
        """Get |ASN.1| value as a sequence of octets.

        If |ASN.1| object length is not a multiple of 8, result
        will be left-padded with zeros.
        """
        return integer.to_bytes(self._value, length=len(self))

    def asInteger(self):
        """Get |ASN.1| value as a single integer value.
        """
        return self._value

    def asBinary(self):
        """Get |ASN.1| value as a text string of bits.
        """
        binString = bin(self._value)[2:]
        return '0' * (len(self._value) - len(binString)) + binString

    @classmethod
    def fromHexString(cls, value, internalFormat=False, prepend=None):
        """Create a |ASN.1| object initialized from the hex string.

        Parameters
        ----------
        value: :class:`str`
            Text string like 'DEADBEEF'
        """
        try:
            value = SizedInteger(value, 16).setBitLength(len(value) * 4)

        except ValueError as exc:
            raise error.PyAsn1Error('%s.fromHexString() error: %s' % (cls.__name__, exc))

        if prepend is not None:
            value = SizedInteger(
                (SizedInteger(prepend) << len(value)) | value
            ).setBitLength(len(prepend) + len(value))

        if not internalFormat:
            value = cls(value)

        return value

    @classmethod
    def fromBinaryString(cls, value, internalFormat=False, prepend=None):
        """Create a |ASN.1| object initialized from a string of '0' and '1'.

        Parameters
        ----------
        value: :class:`str`
            Text string like '1010111'
        """
        try:
            value = SizedInteger(value or '0', 2).setBitLength(len(value))

        except ValueError as exc:
            raise error.PyAsn1Error('%s.fromBinaryString() error: %s' % (cls.__name__, exc))

        if prepend is not None:
            value = SizedInteger(
                (SizedInteger(prepend) << len(value)) | value
            ).setBitLength(len(prepend) + len(value))

        if not internalFormat:
            value = cls(value)

        return value

    @classmethod
    def fromOctetString(cls, value, internalFormat=False, prepend=None, padding=0):
        """Create a |ASN.1| object initialized from a string.

        Parameters
        ----------
        value: :class:`bytes`
            Text string like b'\\\\x01\\\\xff'
        """
        value = SizedInteger(int.from_bytes(bytes(value), 'big') >> padding).setBitLength(len(value) * 8 - padding)

        if prepend is not None:
            value = SizedInteger(
                (SizedInteger(prepend) << len(value)) | value
            ).setBitLength(len(prepend) + len(value))

        if not internalFormat:
            value = cls(value)

        return value

    def prettyIn(self, value):
        if isinstance(value, SizedInteger):
            return value
        elif isinstance(value, str):
            if not value:
                return SizedInteger(0).setBitLength(0)

            elif value[0] == '\'':  # "'1011'B" -- ASN.1 schema representation (deprecated)
                if value[-2:] == '\'B':
                    return self.fromBinaryString(value[1:-2], internalFormat=True)
                elif value[-2:] == '\'H':
                    return self.fromHexString(value[1:-2], internalFormat=True)
                else:
                    raise error.PyAsn1Error(
                        'Bad BIT STRING value notation %s' % (value,)
                    )

            elif self.namedValues and not value.isdigit():  # named bits like 'Urgent, Active'
                names = [x.strip() for x in value.split(',')]

                try:

                    bitPositions = [self.namedValues[name] for name in names]

                except KeyError:
                    raise error.PyAsn1Error('unknown bit name(s) in %r' % (names,))

                rightmostPosition = max(bitPositions)

                number = 0
                for bitPosition in bitPositions:
                    number |= 1 << (rightmostPosition - bitPosition)

                return SizedInteger(number).setBitLength(rightmostPosition + 1)

            elif value.startswith('0x'):
                return self.fromHexString(value[2:], internalFormat=True)

            elif value.startswith('0b'):
                return self.fromBinaryString(value[2:], internalFormat=True)

            else:  # assume plain binary string like '1011'
                return self.fromBinaryString(value, internalFormat=True)

        elif isinstance(value, (tuple, list)):
            return self.fromBinaryString(''.join([b and '1' or '0' for b in value]), internalFormat=True)

        elif isinstance(value, BitString):
            return SizedInteger(value).setBitLength(len(value))

        elif isinstance(value, int):
            return SizedInteger(value)

        else:
            raise error.PyAsn1Error(
                'Bad BitString initializer type \'%s\'' % (value,)
            )


class OctetString(base.SimpleAsn1Type):
    """Create |ASN.1| schema or value object.

    |ASN.1| class is based on :class:`~pyasn1.type.base.SimpleAsn1Type`, its
    objects are immutable and duck-type :class:`bytes`.
    When used in Unicode context, |ASN.1| type
    assumes "|encoding|" serialisation.

    Keyword Args
    ------------
    value: :class:`unicode`, :class:`str`, :class:`bytes` or |ASN.1| object
        :class:`bytes`, alternatively :class:`str`
        representing character string to be serialised into octets
        (note `encoding` parameter) or |ASN.1| object.
        If `value` is not given, schema object will be created.

    tagSet: :py:class:`~pyasn1.type.tag.TagSet`
        Object representing non-default ASN.1 tag(s)

    subtypeSpec: :py:class:`~pyasn1.type.constraint.ConstraintsIntersection`
        Object representing non-default ASN.1 subtype constraint(s). Constraints
        verification for |ASN.1| type occurs automatically on object
        instantiation.

    encoding: :py:class:`str`
        Unicode codec ID to encode/decode
        :class:`str` the payload when |ASN.1| object is used
        in text string context.

    binValue: :py:class:`str`
        Binary string initializer to use instead of the *value*.
        Example: '10110011'.

    hexValue: :py:class:`str`
        Hexadecimal string initializer to use instead of the *value*.
        Example: 'DEADBEEF'.

    Raises
    ------
    ~pyasn1.error.ValueConstraintError, ~pyasn1.error.PyAsn1Error
        On constraint violation or bad initializer.

    Examples
    --------
    .. code-block:: python

        class Icon(OctetString):
            '''
            ASN.1 specification:

            Icon ::= OCTET STRING

            icon1 Icon ::= '001100010011001000110011'B
            icon2 Icon ::= '313233'H
            '''
        icon1 = Icon.fromBinaryString('001100010011001000110011')
        icon2 = Icon.fromHexString('313233')
    """
    #: Set (on class, not on instance) or return a
    #: :py:class:`~pyasn1.type.tag.TagSet` object representing ASN.1 tag(s)
    #: associated with |ASN.1| type.
    tagSet = tag.initTagSet(
        tag.Tag(tag.tagClassUniversal, tag.tagFormatSimple, 0x04)
    )

    #: Set (on class, not on instance) or return a
    #: :py:class:`~pyasn1.type.constraint.ConstraintsIntersection` object
    #: imposing constraints on |ASN.1| type initialization values.
    subtypeSpec = constraint.ConstraintsIntersection()

    # Optimization for faster codec lookup
    typeId = base.SimpleAsn1Type.getTypeId()

    defaultBinValue = defaultHexValue = noValue
    encoding = 'iso-8859-1'

    def __init__(self, value=noValue, **kwargs):
        if kwargs:
            if value is noValue:
                try:
                    value = self.fromBinaryString(kwargs.pop('binValue'))

                except KeyError:
                    pass

                try:
                    value = self.fromHexString(kwargs.pop('hexValue'))

                except KeyError:
                    pass

        if value is noValue:
            if self.defaultBinValue is not noValue:
                value = self.fromBinaryString(self.defaultBinValue)

            elif self.defaultHexValue is not noValue:
                value = self.fromHexString(self.defaultHexValue)

        if 'encoding' not in kwargs:
            kwargs['encoding'] = self.encoding

        base.SimpleAsn1Type.__init__(self, value, **kwargs)

    def prettyIn(self, value):
        if isinstance(value, bytes):
            return value

        elif isinstance(value, str):
            try:
                return value.encode(self.encoding)

            except UnicodeEncodeError as exc:
                raise error.PyAsn1UnicodeEncodeError(
                    "Can't encode string '%s' with '%s' "
                    "codec" % (value, self.encoding), exc
                )
        elif isinstance(value, OctetString):  # a shortcut, bytes() would work the same way
            return value.asOctets()

        elif isinstance(value, base.SimpleAsn1Type):  # this mostly targets Integer objects
            return self.prettyIn(str(value))

        elif isinstance(value, (tuple, list)):
            return self.prettyIn(bytes(value))

        else:
            return bytes(value)

    def __str__(self):
        try:
            return self._value.decode(self.encoding)

        except UnicodeDecodeError as exc:
            raise error.PyAsn1UnicodeDecodeError(
                "Can't decode string '%s' with '%s' codec at "
                "'%s'" % (self._value, self.encoding,
                            self.__class__.__name__), exc
            )

    def __bytes__(self):
        return bytes(self._value)

    def asOctets(self):
        return bytes(self._value)

    def asNumbers(self):
        return tuple(self._value)

    #
    # Normally, `.prettyPrint()` is called from `__str__()`. Historically,
    # OctetString.prettyPrint() used to return hexified payload
    # representation in cases when non-printable content is present. At the
    # same time `str()` used to produce either octet-stream (Py2) or
    # text (Py3) representations.
    #
    # Therefore `OctetString.__str__()` -> `.prettyPrint()` call chain is
    # reversed to preserve the original behaviour.
    #
    # Eventually we should deprecate `.prettyPrint()` / `.prettyOut()` harness
    # and end up with just `__str__()` producing hexified representation while
    # both text and octet-stream representation should only be requested via
    # the `.asOctets()` method.
    #
    # Note: ASN.1 OCTET STRING is never mean to contain text!
    #

    def prettyOut(self, value):
        return value

    def prettyPrint(self, scope=0):
        # first see if subclass has its own .prettyOut()
        value = self.prettyOut(self._value)

        if value is not self._value:
            return value

        numbers = self.asNumbers()

        for x in numbers:
            # hexify if needed
            if x < 32 or x > 126:
                return '0x' + ''.join(('%.2x' % x for x in numbers))
        else:
            # this prevents infinite recursion
            return OctetString.__str__(self)

    @staticmethod
    def fromBinaryString(value):
        """Create a |ASN.1| object initialized from a string of '0' and '1'.

        Parameters
        ----------
        value: :class:`str`
            Text string like '1010111'
        """
        bitNo = 8
        byte = 0
        r = []
        for v in value:
            if bitNo:
                bitNo -= 1
            else:
                bitNo = 7
                r.append(byte)
                byte = 0
            if v in ('0', '1'):
                v = int(v)
            else:
                raise error.PyAsn1Error(
                    'Non-binary OCTET STRING initializer %s' % (v,)
                )
            byte |= v << bitNo

        r.append(byte)

        return bytes(r)

    @staticmethod
    def fromHexString(value):
        """Create a |ASN.1| object initialized from the hex string.

        Parameters
        ----------
        value: :class:`str`
            Text string like 'DEADBEEF'
        """
        r = []
        p = []
        for v in value:
            if p:
                r.append(int(p + v, 16))
                p = None
            else:
                p = v
        if p:
            r.append(int(p + '0', 16))

        return bytes(r)

    # Immutable sequence object protocol

    def __len__(self):
        return len(self._value)

    def __getitem__(self, i):
        if i.__class__ is slice:
            return self.clone(self._value[i])
        else:
            return self._value[i]

    def __iter__(self):
        return iter(self._value)

    def __contains__(self, value):
        return value in self._value

    def __add__(self, value):
        return self.clone(self._value + self.prettyIn(value))

    def __radd__(self, value):
        return self.clone(self.prettyIn(value) + self._value)

    def __mul__(self, value):
        return self.clone(self._value * value)

    def __rmul__(self, value):
        return self * value

    def __int__(self):
        return int(self._value)

    def __float__(self):
        return float(self._value)

    def __reversed__(self):
        return reversed(self._value)


class Null(OctetString):
    """Create |ASN.1| schema or value object.

    |ASN.1| class is based on :class:`~pyasn1.type.base.SimpleAsn1Type`, its
    objects are immutable and duck-type Python :class:`str` objects
    (always empty).

    Keyword Args
    ------------
    value: :class:`str` or |ASN.1| object
        Python empty :class:`str` literal or any object that evaluates to :obj:`False`
        If `value` is not given, schema object will be created.

    tagSet: :py:class:`~pyasn1.type.tag.TagSet`
        Object representing non-default ASN.1 tag(s)

    Raises
    ------
    ~pyasn1.error.ValueConstraintError, ~pyasn1.error.PyAsn1Error
        On constraint violation or bad initializer.

    Examples
    --------
    .. code-block:: python

        class Ack(Null):
            '''
            ASN.1 specification:

            Ack ::= NULL
            '''
        ack = Ack('')
    """

    #: Set (on class, not on instance) or return a
    #: :py:class:`~pyasn1.type.tag.TagSet` object representing ASN.1 tag(s)
    #: associated with |ASN.1| type.
    tagSet = tag.initTagSet(
        tag.Tag(tag.tagClassUniversal, tag.tagFormatSimple, 0x05)
    )
    subtypeSpec = OctetString.subtypeSpec + constraint.SingleValueConstraint(b'')

    # Optimization for faster codec lookup
    typeId = OctetString.getTypeId()

    def prettyIn(self, value):
        if value:
            return value

        return b''


class ObjectIdentifier(base.SimpleAsn1Type):
    """Create |ASN.1| schema or value object.

    |ASN.1| class is based on :class:`~pyasn1.type.base.SimpleAsn1Type`, its
    objects are immutable and duck-type Python :class:`tuple` objects
    (tuple of non-negative integers).

    Keyword Args
    ------------
    value: :class:`tuple`, :class:`str` or |ASN.1| object
        Python sequence of :class:`int` or :class:`str` literal or |ASN.1| object.
        If `value` is not given, schema object will be created.

    tagSet: :py:class:`~pyasn1.type.tag.TagSet`
        Object representing non-default ASN.1 tag(s)

    subtypeSpec: :py:class:`~pyasn1.type.constraint.ConstraintsIntersection`
        Object representing non-default ASN.1 subtype constraint(s). Constraints
        verification for |ASN.1| type occurs automatically on object
        instantiation.

    Raises
    ------
    ~pyasn1.error.ValueConstraintError, ~pyasn1.error.PyAsn1Error
        On constraint violation or bad initializer.

    Examples
    --------
    .. code-block:: python

        class ID(ObjectIdentifier):
            '''
            ASN.1 specification:

            ID ::= OBJECT IDENTIFIER

            id-edims ID ::= { joint-iso-itu-t mhs-motif(6) edims(7) }
            id-bp ID ::= { id-edims 11 }
            '''
        id_edims = ID('2.6.7')
        id_bp = id_edims + (11,)
    """
    #: Set (on class, not on instance) or return a
    #: :py:class:`~pyasn1.type.tag.TagSet` object representing ASN.1 tag(s)
    #: associated with |ASN.1| type.
    tagSet = tag.initTagSet(
        tag.Tag(tag.tagClassUniversal, tag.tagFormatSimple, 0x06)
    )

    #: Set (on class, not on instance) or return a
    #: :py:class:`~pyasn1.type.constraint.ConstraintsIntersection` object
    #: imposing constraints on |ASN.1| type initialization values.
    subtypeSpec = constraint.ConstraintsIntersection()

    # Optimization for faster codec lookup
    typeId = base.SimpleAsn1Type.getTypeId()

    def __add__(self, other):
        return self.clone(self._value + other)

    def __radd__(self, other):
        return self.clone(other + self._value)

    def asTuple(self):
        return self._value

    # Sequence object protocol

    def __len__(self):
        return len(self._value)

    def __getitem__(self, i):
        if i.__class__ is slice:
            return self.clone(self._value[i])
        else:
            return self._value[i]

    def __iter__(self):
        return iter(self._value)

    def __contains__(self, value):
        return value in self._value

    def index(self, suboid):
        return self._value.index(suboid)

    def isPrefixOf(self, other):
        """Indicate if this |ASN.1| object is a prefix of other |ASN.1| object.

        Parameters
        ----------
        other: |ASN.1| object
            |ASN.1| object

        Returns
        -------
        : :class:`bool`
            :obj:`True` if this |ASN.1| object is a parent (e.g. prefix) of the other |ASN.1| object
            or :obj:`False` otherwise.
        """
        l = len(self)
        if l <= len(other):
            if self._value[:l] == other[:l]:
                return True
        return False

    def prettyIn(self, value):
        if isinstance(value, ObjectIdentifier):
            return tuple(value)
        elif isinstance(value, str):
            if '-' in value:
                raise error.PyAsn1Error(
                    # sys.exc_info in case prettyIn was called while handling an exception
                    'Malformed Object ID %s at %s: %s' % (value, self.__class__.__name__, sys.exc_info()[1])
                )
            try:
                return tuple([int(subOid) for subOid in value.split('.') if subOid])
            except ValueError as exc:
                raise error.PyAsn1Error(
                    'Malformed Object ID %s at %s: %s' % (value, self.__class__.__name__, exc)
                )

        try:
            tupleOfInts = tuple([int(subOid) for subOid in value if subOid >= 0])

        except (ValueError, TypeError) as exc:
            raise error.PyAsn1Error(
                'Malformed Object ID %s at %s: %s' % (value, self.__class__.__name__, exc)
            )

        if len(tupleOfInts) == len(value):
            return tupleOfInts

        raise error.PyAsn1Error('Malformed Object ID %s at %s' % (value, self.__class__.__name__))

    def prettyOut(self, value):
        return '.'.join([str(x) for x in value])


class RelativeOID(base.SimpleAsn1Type):
    """Create |ASN.1| schema or value object.
    |ASN.1| class is based on :class:`~pyasn1.type.base.SimpleAsn1Type`, its
    objects are immutable and duck-type Python :class:`tuple` objects
    (tuple of non-negative integers).
    Keyword Args
    ------------
    value: :class:`tuple`, :class:`str` or |ASN.1| object
        Python sequence of :class:`int` or :class:`str` literal or |ASN.1| object.
        If `value` is not given, schema object will be created.
    tagSet: :py:class:`~pyasn1.type.tag.TagSet`
        Object representing non-default ASN.1 tag(s)
    subtypeSpec: :py:class:`~pyasn1.type.constraint.ConstraintsIntersection`
        Object representing non-default ASN.1 subtype constraint(s). Constraints
        verification for |ASN.1| type occurs automatically on object
        instantiation.
    Raises
    ------
    ~pyasn1.error.ValueConstraintError, ~pyasn1.error.PyAsn1Error
        On constraint violation or bad initializer.
    Examples
    --------
    .. code-block:: python
        class RelOID(RelativeOID):
            '''
            ASN.1 specification:
            id-pad-null RELATIVE-OID ::= { 0 }
            id-pad-once RELATIVE-OID ::= { 5 6 }
            id-pad-twice RELATIVE-OID ::= { 5 6 7 }
            '''
        id_pad_null = RelOID('0')
        id_pad_once = RelOID('5.6')
        id_pad_twice = id_pad_once + (7,)
    """
    #: Set (on class, not on instance) or return a
    #: :py:class:`~pyasn1.type.tag.TagSet` object representing ASN.1 tag(s)
    #: associated with |ASN.1| type.
    tagSet = tag.initTagSet(
        tag.Tag(tag.tagClassUniversal, tag.tagFormatSimple, 0x0d)
    )

    #: Set (on class, not on instance) or return a
    #: :py:class:`~pyasn1.type.constraint.ConstraintsIntersection` object
    #: imposing constraints on |ASN.1| type initialization values.
    subtypeSpec = constraint.ConstraintsIntersection()

    # Optimization for faster codec lookup
    typeId = base.SimpleAsn1Type.getTypeId()

    def __add__(self, other):
        return self.clone(self._value + other)

    def __radd__(self, other):
        return self.clone(other + self._value)

    def asTuple(self):
        return self._value

    # Sequence object protocol

    def __len__(self):
        return len(self._value)

    def __getitem__(self, i):
        if i.__class__ is slice:
            return self.clone(self._value[i])
        else:
            return self._value[i]

    def __iter__(self):
        return iter(self._value)

    def __contains__(self, value):
        return value in self._value

    def index(self, suboid):
        return self._value.index(suboid)

    def isPrefixOf(self, other):
        """Indicate if this |ASN.1| object is a prefix of other |ASN.1| object.
        Parameters
        ----------
        other: |ASN.1| object
            |ASN.1| object
        Returns
        -------
        : :class:`bool`
            :obj:`True` if this |ASN.1| object is a parent (e.g. prefix) of the other |ASN.1| object
            or :obj:`False` otherwise.
        """
        l = len(self)
        if l <= len(other):
            if self._value[:l] == other[:l]:
                return True
        return False

    def prettyIn(self, value):
        if isinstance(value, RelativeOID):
            return tuple(value)
        elif isinstance(value, str):
            if '-' in value:
                raise error.PyAsn1Error(
                    # sys.exc_info in case prettyIn was called while handling an exception
                    'Malformed RELATIVE-OID %s at %s: %s' % (value, self.__class__.__name__, sys.exc_info()[1])
                )
            try:
                return tuple([int(subOid) for subOid in value.split('.') if subOid])
            except ValueError as exc:
                raise error.PyAsn1Error(
                    'Malformed RELATIVE-OID %s at %s: %s' % (value, self.__class__.__name__, exc)
                )

        try:
            tupleOfInts = tuple([int(subOid) for subOid in value if subOid >= 0])

        except (ValueError, TypeError) as exc:
            raise error.PyAsn1Error(
                'Malformed RELATIVE-OID %s at %s: %s' % (value, self.__class__.__name__, exc)
            )

        if len(tupleOfInts) == len(value):
            return tupleOfInts

        raise error.PyAsn1Error('Malformed RELATIVE-OID %s at %s' % (value, self.__class__.__name__))

    def prettyOut(self, value):
        return '.'.join([str(x) for x in value])


class Real(base.SimpleAsn1Type):
    """Create |ASN.1| schema or value object.

    |ASN.1| class is based on :class:`~pyasn1.type.base.SimpleAsn1Type`, its
    objects are immutable and duck-type Python :class:`float` objects.
    Additionally, |ASN.1| objects behave like a :class:`tuple` in which case its
    elements are mantissa, base and exponent.

    Keyword Args
    ------------
    value: :class:`tuple`, :class:`float` or |ASN.1| object
        Python sequence of :class:`int` (representing mantissa, base and
        exponent) or :class:`float` instance or |ASN.1| object.
        If `value` is not given, schema object will be created.

    tagSet: :py:class:`~pyasn1.type.tag.TagSet`
        Object representing non-default ASN.1 tag(s)

    subtypeSpec: :py:class:`~pyasn1.type.constraint.ConstraintsIntersection`
        Object representing non-default ASN.1 subtype constraint(s). Constraints
        verification for |ASN.1| type occurs automatically on object
        instantiation.

    Raises
    ------
    ~pyasn1.error.ValueConstraintError, ~pyasn1.error.PyAsn1Error
        On constraint violation or bad initializer.

    Examples
    --------
    .. code-block:: python

        class Pi(Real):
            '''
            ASN.1 specification:

            Pi ::= REAL

            pi Pi ::= { mantissa 314159, base 10, exponent -5 }

            '''
        pi = Pi((314159, 10, -5))
    """
    binEncBase = None  # binEncBase = 16 is recommended for large numbers

    try:
        _plusInf = float('inf')
        _minusInf = float('-inf')
        _inf = _plusInf, _minusInf

    except ValueError:
        # Infinity support is platform and Python dependent
        _plusInf = _minusInf = None
        _inf = ()

    #: Set (on class, not on instance) or return a
    #: :py:class:`~pyasn1.type.tag.TagSet` object representing ASN.1 tag(s)
    #: associated with |ASN.1| type.
    tagSet = tag.initTagSet(
        tag.Tag(tag.tagClassUniversal, tag.tagFormatSimple, 0x09)
    )

    #: Set (on class, not on instance) or return a
    #: :py:class:`~pyasn1.type.constraint.ConstraintsIntersection` object
    #: imposing constraints on |ASN.1| type initialization values.
    subtypeSpec = constraint.ConstraintsIntersection()

    # Optimization for faster codec lookup
    typeId = base.SimpleAsn1Type.getTypeId()

    @staticmethod
    def __normalizeBase10(value):
        m, b, e = value
        while m and m % 10 == 0:
            m /= 10
            e += 1
        return m, b, e

    def prettyIn(self, value):
        if isinstance(value, tuple) and len(value) == 3:
            if (not isinstance(value[0], (int, float)) or
                    not isinstance(value[1], int) or
                    not isinstance(value[2], int)):
                raise error.PyAsn1Error('Lame Real value syntax: %s' % (value,))
            if (isinstance(value[0], float) and
                    self._inf and value[0] in self._inf):
                return value[0]
            if value[1] not in (2, 10):
                raise error.PyAsn1Error(
                    'Prohibited base for Real value: %s' % (value[1],)
                )
            if value[1] == 10:
                value = self.__normalizeBase10(value)
            return value
        elif isinstance(value, int):
            return self.__normalizeBase10((value, 10, 0))
        elif isinstance(value, float) or isinstance(value, str):
            if isinstance(value, str):
                try:
                    value = float(value)
                except ValueError:
                    raise error.PyAsn1Error(
                        'Bad real value syntax: %s' % (value,)
                    )
            if self._inf and value in self._inf:
                return value
            else:
                e = 0
                while int(value) != value:
                    value *= 10
                    e -= 1
                return self.__normalizeBase10((int(value), 10, e))
        elif isinstance(value, Real):
            return tuple(value)
        raise error.PyAsn1Error(
            'Bad real value syntax: %s' % (value,)
        )

    def prettyPrint(self, scope=0):
        try:
            return self.prettyOut(float(self))

        except OverflowError:
            return '<overflow>'

    @property
    def isPlusInf(self):
        """Indicate PLUS-INFINITY object value

        Returns
        -------
        : :class:`bool`
            :obj:`True` if calling object represents plus infinity
            or :obj:`False` otherwise.

        """
        return self._value == self._plusInf

    @property
    def isMinusInf(self):
        """Indicate MINUS-INFINITY object value

        Returns
        -------
        : :class:`bool`
            :obj:`True` if calling object represents minus infinity
            or :obj:`False` otherwise.
        """
        return self._value == self._minusInf

    @property
    def isInf(self):
        return self._value in self._inf

    def __add__(self, value):
        return self.clone(float(self) + value)

    def __radd__(self, value):
        return self + value

    def __mul__(self, value):
        return self.clone(float(self) * value)

    def __rmul__(self, value):
        return self * value

    def __sub__(self, value):
        return self.clone(float(self) - value)

    def __rsub__(self, value):
        return self.clone(value - float(self))

    def __mod__(self, value):
        return self.clone(float(self) % value)

    def __rmod__(self, value):
        return self.clone(value % float(self))

    def __pow__(self, value, modulo=None):
        return self.clone(pow(float(self), value, modulo))

    def __rpow__(self, value):
        return self.clone(pow(value, float(self)))

    def __truediv__(self, value):
        return self.clone(float(self) / value)

    def __rtruediv__(self, value):
        return self.clone(value / float(self))

    def __divmod__(self, value):
        return self.clone(float(self) // value)

    def __rdivmod__(self, value):
        return self.clone(value // float(self))

    def __int__(self):
        return int(float(self))

    def __float__(self):
        if self._value in self._inf:
            return self._value
        else:
            return float(
                self._value[0] * pow(self._value[1], self._value[2])
            )

    def __abs__(self):
        return self.clone(abs(float(self)))

    def __pos__(self):
        return self.clone(+float(self))

    def __neg__(self):
        return self.clone(-float(self))

    def __round__(self, n=0):
        r = round(float(self), n)
        if n:
            return self.clone(r)
        else:
            return r

    def __floor__(self):
        return self.clone(math.floor(float(self)))

    def __ceil__(self):
        return self.clone(math.ceil(float(self)))

    def __trunc__(self):
        return self.clone(math.trunc(float(self)))

    def __lt__(self, value):
        return float(self) < value

    def __le__(self, value):
        return float(self) <= value

    def __eq__(self, value):
        return float(self) == value

    def __ne__(self, value):
        return float(self) != value

    def __gt__(self, value):
        return float(self) > value

    def __ge__(self, value):
        return float(self) >= value

    def __bool__(self):
        return bool(float(self))

    __hash__ = base.SimpleAsn1Type.__hash__

    def __getitem__(self, idx):
        if self._value in self._inf:
            raise error.PyAsn1Error('Invalid infinite value operation')
        else:
            return self._value[idx]

    # compatibility stubs

    def isPlusInfinity(self):
        return self.isPlusInf

    def isMinusInfinity(self):
        return self.isMinusInf

    def isInfinity(self):
        return self.isInf


class Enumerated(Integer):
    """Create |ASN.1| schema or value object.

    |ASN.1| class is based on :class:`~pyasn1.type.base.SimpleAsn1Type`, its
    objects are immutable and duck-type Python :class:`int` objects.

    Keyword Args
    ------------
    value: :class:`int`, :class:`str` or |ASN.1| object
        Python :class:`int` or :class:`str` literal or |ASN.1| object.
        If `value` is not given, schema object will be created.

    tagSet: :py:class:`~pyasn1.type.tag.TagSet`
        Object representing non-default ASN.1 tag(s)

    subtypeSpec: :py:class:`~pyasn1.type.constraint.ConstraintsIntersection`
        Object representing non-default ASN.1 subtype constraint(s). Constraints
        verification for |ASN.1| type occurs automatically on object
        instantiation.

    namedValues: :py:class:`~pyasn1.type.namedval.NamedValues`
        Object representing non-default symbolic aliases for numbers

    Raises
    ------
    ~pyasn1.error.ValueConstraintError, ~pyasn1.error.PyAsn1Error
        On constraint violation or bad initializer.

    Examples
    --------

    .. code-block:: python

        class RadioButton(Enumerated):
            '''
            ASN.1 specification:

            RadioButton ::= ENUMERATED { button1(0), button2(1),
                                         button3(2) }

            selected-by-default RadioButton ::= button1
            '''
            namedValues = NamedValues(
                ('button1', 0), ('button2', 1),
                ('button3', 2)
            )

        selected_by_default = RadioButton('button1')
    """
    #: Set (on class, not on instance) or return a
    #: :py:class:`~pyasn1.type.tag.TagSet` object representing ASN.1 tag(s)
    #: associated with |ASN.1| type.
    tagSet = tag.initTagSet(
        tag.Tag(tag.tagClassUniversal, tag.tagFormatSimple, 0x0A)
    )

    #: Set (on class, not on instance) or return a
    #: :py:class:`~pyasn1.type.constraint.ConstraintsIntersection` object
    #: imposing constraints on |ASN.1| type initialization values.
    subtypeSpec = constraint.ConstraintsIntersection()

    # Optimization for faster codec lookup
    typeId = Integer.getTypeId()

    #: Default :py:class:`~pyasn1.type.namedval.NamedValues` object
    #: representing symbolic aliases for numbers
    namedValues = namedval.NamedValues()


# "Structured" ASN.1 types

class SequenceOfAndSetOfBase(base.ConstructedAsn1Type):
    """Create |ASN.1| schema or value object.

    |ASN.1| class is based on :class:`~pyasn1.type.base.ConstructedAsn1Type`,
    its objects are mutable and duck-type Python :class:`list` objects.

    Keyword Args
    ------------
    componentType : :py:class:`~pyasn1.type.base.PyAsn1Item` derivative
        A pyasn1 object representing ASN.1 type allowed within |ASN.1| type

    tagSet: :py:class:`~pyasn1.type.tag.TagSet`
        Object representing non-default ASN.1 tag(s)

    subtypeSpec: :py:class:`~pyasn1.type.constraint.ConstraintsIntersection`
        Object representing non-default ASN.1 subtype constraint(s). Constraints
        verification for |ASN.1| type can only occur on explicit
        `.isInconsistent` call.

    Examples
    --------

    .. code-block:: python

        class LotteryDraw(SequenceOf):  #  SetOf is similar
            '''
            ASN.1 specification:

            LotteryDraw ::= SEQUENCE OF INTEGER
            '''
            componentType = Integer()

        lotteryDraw = LotteryDraw()
        lotteryDraw.extend([123, 456, 789])
    """
    def __init__(self, *args, **kwargs):
        # support positional params for backward compatibility
        if args:
            for key, value in zip(('componentType', 'tagSet',
                                   'subtypeSpec'), args):
                if key in kwargs:
                    raise error.PyAsn1Error('Conflicting positional and keyword params!')
                kwargs['componentType'] = value

        self._componentValues = noValue

        base.ConstructedAsn1Type.__init__(self, **kwargs)

    # Python list protocol

    def __getitem__(self, idx):
        try:
            return self.getComponentByPosition(idx)

        except error.PyAsn1Error as exc:
            raise IndexError(exc)

    def __setitem__(self, idx, value):
        try:
            self.setComponentByPosition(idx, value)

        except error.PyAsn1Error as exc:
            raise IndexError(exc)

    def append(self, value):
        if self._componentValues is noValue:
            pos = 0

        else:
            pos = len(self._componentValues)

        self[pos] = value

    def count(self, value):
        return list(self._componentValues.values()).count(value)

    def extend(self, values):
        for value in values:
            self.append(value)

        if self._componentValues is noValue:
            self._componentValues = {}

    def index(self, value, start=0, stop=None):
        if stop is None:
            stop = len(self)

        indices, values = zip(*self._componentValues.items())

        # TODO: remove when Py2.5 support is gone
        values = list(values)

        try:
            return indices[values.index(value, start, stop)]

        except error.PyAsn1Error as exc:
            raise ValueError(exc)

    def reverse(self):
        self._componentValues.reverse()

    def sort(self, key=None, reverse=False):
        self._componentValues = dict(
            enumerate(sorted(self._componentValues.values(),
                             key=key, reverse=reverse)))

    def __len__(self):
        if self._componentValues is noValue or not self._componentValues:
            return 0

        return max(self._componentValues) + 1

    def __iter__(self):
        for idx in range(0, len(self)):
            yield self.getComponentByPosition(idx)

    def _cloneComponentValues(self, myClone, cloneValueFlag):
        for idx, componentValue in self._componentValues.items():
            if componentValue is not noValue:
                if isinstance(componentValue, base.ConstructedAsn1Type):
                    myClone.setComponentByPosition(
                        idx, componentValue.clone(cloneValueFlag=cloneValueFlag)
                    )
                else:
                    myClone.setComponentByPosition(idx, componentValue.clone())

    def getComponentByPosition(self, idx, default=noValue, instantiate=True):
        """Return |ASN.1| type component value by position.

        Equivalent to Python sequence subscription operation (e.g. `[]`).

        Parameters
        ----------
        idx : :class:`int`
            Component index (zero-based). Must either refer to an existing
            component or to N+1 component (if *componentType* is set). In the latter
            case a new component type gets instantiated and appended to the |ASN.1|
            sequence.

        Keyword Args
        ------------
        default: :class:`object`
            If set and requested component is a schema object, return the `default`
            object instead of the requested component.

        instantiate: :class:`bool`
            If :obj:`True` (default), inner component will be automatically instantiated.
            If :obj:`False` either existing component or the :class:`NoValue` object will be
            returned.

        Returns
        -------
        : :py:class:`~pyasn1.type.base.PyAsn1Item`
            Instantiate |ASN.1| component type or return existing component value

        Examples
        --------

        .. code-block:: python

            # can also be SetOf
            class MySequenceOf(SequenceOf):
                componentType = OctetString()

            s = MySequenceOf()

            # returns component #0 with `.isValue` property False
            s.getComponentByPosition(0)

            # returns None
            s.getComponentByPosition(0, default=None)

            s.clear()

            # returns noValue
            s.getComponentByPosition(0, instantiate=False)

            # sets component #0 to OctetString() ASN.1 schema
            # object and returns it
            s.getComponentByPosition(0, instantiate=True)

            # sets component #0 to ASN.1 value object
            s.setComponentByPosition(0, 'ABCD')

            # returns OctetString('ABCD') value object
            s.getComponentByPosition(0, instantiate=False)

            s.clear()

            # returns noValue
            s.getComponentByPosition(0, instantiate=False)
        """
        if isinstance(idx, slice):
            indices = tuple(range(len(self)))
            return [self.getComponentByPosition(subidx, default, instantiate)
                    for subidx in indices[idx]]

        if idx < 0:
            idx = len(self) + idx
            if idx < 0:
                raise error.PyAsn1Error(
                    'SequenceOf/SetOf index is out of range')

        try:
            componentValue = self._componentValues[idx]

        except (KeyError, error.PyAsn1Error):
            if not instantiate:
                return default

            self.setComponentByPosition(idx)

            componentValue = self._componentValues[idx]

        if default is noValue or componentValue.isValue:
            return componentValue
        else:
            return default

    def setComponentByPosition(self, idx, value=noValue,
                               verifyConstraints=True,
                               matchTags=True,
                               matchConstraints=True):
        """Assign |ASN.1| type component by position.

        Equivalent to Python sequence item assignment operation (e.g. `[]`)
        or list.append() (when idx == len(self)).

        Parameters
        ----------
        idx: :class:`int`
            Component index (zero-based). Must either refer to existing
            component or to N+1 component. In the latter case a new component
            type gets instantiated (if *componentType* is set, or given ASN.1
            object is taken otherwise) and appended to the |ASN.1| sequence.

        Keyword Args
        ------------
        value: :class:`object` or :py:class:`~pyasn1.type.base.PyAsn1Item` derivative
            A Python value to initialize |ASN.1| component with (if *componentType* is set)
            or ASN.1 value object to assign to |ASN.1| component.
            If `value` is not given, schema object will be set as a component.

        verifyConstraints: :class:`bool`
             If :obj:`False`, skip constraints validation

        matchTags: :class:`bool`
             If :obj:`False`, skip component tags matching

        matchConstraints: :class:`bool`
             If :obj:`False`, skip component constraints matching

        Returns
        -------
        self

        Raises
        ------
        ~pyasn1.error.ValueConstraintError, ~pyasn1.error.PyAsn1Error
            On constraint violation or bad initializer
        IndexError
            When idx > len(self)
        """
        if isinstance(idx, slice):
            indices = tuple(range(len(self)))
            startIdx = indices and indices[idx][0] or 0
            for subIdx, subValue in enumerate(value):
                self.setComponentByPosition(
                    startIdx + subIdx, subValue, verifyConstraints,
                    matchTags, matchConstraints)
            return self

        if idx < 0:
            idx = len(self) + idx
            if idx < 0:
                raise error.PyAsn1Error(
                    'SequenceOf/SetOf index is out of range')

        componentType = self.componentType

        if self._componentValues is noValue:
            componentValues = {}

        else:
            componentValues = self._componentValues

        currentValue = componentValues.get(idx, noValue)

        if value is noValue:
            if componentType is not None:
                value = componentType.clone()

            elif currentValue is noValue:
                raise error.PyAsn1Error('Component type not defined')

        elif not isinstance(value, base.Asn1Item):
            if (componentType is not None and
                    isinstance(componentType, base.SimpleAsn1Type)):
                value = componentType.clone(value=value)

            elif (currentValue is not noValue and
                    isinstance(currentValue, base.SimpleAsn1Type)):
                value = currentValue.clone(value=value)

            else:
                raise error.PyAsn1Error(
                    'Non-ASN.1 value %r and undefined component'
                    ' type at %r' % (value, self))

        elif componentType is not None and (matchTags or matchConstraints):
            subtypeChecker = (
                    self.strictConstraints and
                    componentType.isSameTypeWith or
                    componentType.isSuperTypeOf)

            if not subtypeChecker(value, verifyConstraints and matchTags,
                                  verifyConstraints and matchConstraints):
                # TODO: we should wrap componentType with UnnamedType to carry
                # additional properties associated with componentType
                if componentType.typeId != Any.typeId:
                    raise error.PyAsn1Error(
                        'Component value is tag-incompatible: %r vs '
                        '%r' % (value, componentType))

        componentValues[idx] = value

        self._componentValues = componentValues

        return self

    @property
    def componentTagMap(self):
        if self.componentType is not None:
            return self.componentType.tagMap

    @property
    def components(self):
        return [self._componentValues[idx]
                for idx in sorted(self._componentValues)]

    def clear(self):
        """Remove all components and become an empty |ASN.1| value object.

        Has the same effect on |ASN.1| object as it does on :class:`list`
        built-in.
        """
        self._componentValues = {}
        return self

    def reset(self):
        """Remove all components and become a |ASN.1| schema object.

        See :meth:`isValue` property for more information on the
        distinction between value and schema objects.
        """
        self._componentValues = noValue
        return self

    def prettyPrint(self, scope=0):
        scope += 1
        representation = self.__class__.__name__ + ':\n'

        if not self.isValue:
            return representation

        for idx, componentValue in enumerate(self):
            representation += ' ' * scope
            if (componentValue is noValue and
                    self.componentType is not None):
                representation += '<empty>'
            else:
                representation += componentValue.prettyPrint(scope)

        return representation

    def prettyPrintType(self, scope=0):
        scope += 1
        representation = '%s -> %s {\n' % (self.tagSet, self.__class__.__name__)
        if self.componentType is not None:
            representation += ' ' * scope
            representation += self.componentType.prettyPrintType(scope)
        return representation + '\n' + ' ' * (scope - 1) + '}'


    @property
    def isValue(self):
        """Indicate that |ASN.1| object represents ASN.1 value.

        If *isValue* is :obj:`False` then this object represents just ASN.1 schema.

        If *isValue* is :obj:`True` then, in addition to its ASN.1 schema features,
        this object can also be used like a Python built-in object
        (e.g. :class:`int`, :class:`str`, :class:`dict` etc.).

        Returns
        -------
        : :class:`bool`
            :obj:`False` if object represents just ASN.1 schema.
            :obj:`True` if object represents ASN.1 schema and can be used as a normal value.

        Note
        ----
        There is an important distinction between PyASN1 schema and value objects.
        The PyASN1 schema objects can only participate in ASN.1 schema-related
        operations (e.g. defining or testing the structure of the data). Most
        obvious uses of ASN.1 schema is to guide serialisation codecs whilst
        encoding/decoding serialised ASN.1 contents.

        The PyASN1 value objects can **additionally** participate in many operations
        involving regular Python objects (e.g. arithmetic, comprehension etc).
        """
        if self._componentValues is noValue:
            return False

        if len(self._componentValues) != len(self):
            return False

        for componentValue in self._componentValues.values():
            if componentValue is noValue or not componentValue.isValue:
                return False

        return True

    @property
    def isInconsistent(self):
        """Run necessary checks to ensure |ASN.1| object consistency.

        Default action is to verify |ASN.1| object against constraints imposed
        by `subtypeSpec`.

        Raises
        ------
        :py:class:`~pyasn1.error.PyAsn1tError` on any inconsistencies found
        """
        if self.componentType is noValue or not self.subtypeSpec:
            return False

        if self._componentValues is noValue:
            return True

        mapping = {}

        for idx, value in self._componentValues.items():
            # Absent fields are not in the mapping
            if value is noValue:
                continue

            mapping[idx] = value

        try:
            # Represent SequenceOf/SetOf as a bare dict to constraints chain
            self.subtypeSpec(mapping)

        except error.PyAsn1Error as exc:
            return exc

        return False

class SequenceOf(SequenceOfAndSetOfBase):
    __doc__ = SequenceOfAndSetOfBase.__doc__

    #: Set (on class, not on instance) or return a
    #: :py:class:`~pyasn1.type.tag.TagSet` object representing ASN.1 tag(s)
    #: associated with |ASN.1| type.
    tagSet = tag.initTagSet(
        tag.Tag(tag.tagClassUniversal, tag.tagFormatConstructed, 0x10)
    )

    #: Default :py:class:`~pyasn1.type.base.PyAsn1Item` derivative
    #: object representing ASN.1 type allowed within |ASN.1| type
    componentType = None

    #: Set (on class, not on instance) or return a
    #: :py:class:`~pyasn1.type.constraint.ConstraintsIntersection` object
    #: imposing constraints on |ASN.1| type initialization values.
    subtypeSpec = constraint.ConstraintsIntersection()

    # Disambiguation ASN.1 types identification
    typeId = SequenceOfAndSetOfBase.getTypeId()


class SetOf(SequenceOfAndSetOfBase):
    __doc__ = SequenceOfAndSetOfBase.__doc__

    #: Set (on class, not on instance) or return a
    #: :py:class:`~pyasn1.type.tag.TagSet` object representing ASN.1 tag(s)
    #: associated with |ASN.1| type.
    tagSet = tag.initTagSet(
        tag.Tag(tag.tagClassUniversal, tag.tagFormatConstructed, 0x11)
    )

    #: Default :py:class:`~pyasn1.type.base.PyAsn1Item` derivative
    #: object representing ASN.1 type allowed within |ASN.1| type
    componentType = None

    #: Set (on class, not on instance) or return a
    #: :py:class:`~pyasn1.type.constraint.ConstraintsIntersection` object
    #: imposing constraints on |ASN.1| type initialization values.
    subtypeSpec = constraint.ConstraintsIntersection()

    # Disambiguation ASN.1 types identification
    typeId = SequenceOfAndSetOfBase.getTypeId()


class SequenceAndSetBase(base.ConstructedAsn1Type):
    """Create |ASN.1| schema or value object.

    |ASN.1| class is based on :class:`~pyasn1.type.base.ConstructedAsn1Type`,
    its objects are mutable and duck-type Python :class:`dict` objects.

    Keyword Args
    ------------
    componentType: :py:class:`~pyasn1.type.namedtype.NamedType`
        Object holding named ASN.1 types allowed within this collection

    tagSet: :py:class:`~pyasn1.type.tag.TagSet`
        Object representing non-default ASN.1 tag(s)

    subtypeSpec: :py:class:`~pyasn1.type.constraint.ConstraintsIntersection`
        Object representing non-default ASN.1 subtype constraint(s).  Constraints
        verification for |ASN.1| type can only occur on explicit
        `.isInconsistent` call.

    Examples
    --------

    .. code-block:: python

        class Description(Sequence):  #  Set is similar
            '''
            ASN.1 specification:

            Description ::= SEQUENCE {
                surname    IA5String,
                first-name IA5String OPTIONAL,
                age        INTEGER DEFAULT 40
            }
            '''
            componentType = NamedTypes(
                NamedType('surname', IA5String()),
                OptionalNamedType('first-name', IA5String()),
                DefaultedNamedType('age', Integer(40))
            )

        descr = Description()
        descr['surname'] = 'Smith'
        descr['first-name'] = 'John'
    """
    #: Default :py:class:`~pyasn1.type.namedtype.NamedTypes`
    #: object representing named ASN.1 types allowed within |ASN.1| type
    componentType = namedtype.NamedTypes()


    class DynamicNames(object):
        """Fields names/positions mapping for component-less objects"""
        def __init__(self):
            self._keyToIdxMap = {}
            self._idxToKeyMap = {}

        def __len__(self):
            return len(self._keyToIdxMap)

        def __contains__(self, item):
            return item in self._keyToIdxMap or item in self._idxToKeyMap

        def __iter__(self):
            return (self._idxToKeyMap[idx] for idx in range(len(self._idxToKeyMap)))

        def __getitem__(self, item):
            try:
                return self._keyToIdxMap[item]

            except KeyError:
                return self._idxToKeyMap[item]

        def getNameByPosition(self, idx):
            try:
                return self._idxToKeyMap[idx]

            except KeyError:
                raise error.PyAsn1Error('Type position out of range')

        def getPositionByName(self, name):
            try:
                return self._keyToIdxMap[name]

            except KeyError:
                raise error.PyAsn1Error('Name %s not found' % (name,))

        def addField(self, idx):
            self._keyToIdxMap['field-%d' % idx] = idx
            self._idxToKeyMap[idx] = 'field-%d' % idx


    def __init__(self, **kwargs):
        base.ConstructedAsn1Type.__init__(self, **kwargs)
        self._componentTypeLen = len(self.componentType)
        if self._componentTypeLen:
            self._componentValues = []
        else:
            self._componentValues = noValue
        self._dynamicNames = self._componentTypeLen or self.DynamicNames()

    def __getitem__(self, idx):
        if isinstance(idx, str):
            try:
                return self.getComponentByName(idx)

            except error.PyAsn1Error as exc:
                # duck-typing dict
                raise KeyError(exc)

        else:
            try:
                return self.getComponentByPosition(idx)

            except error.PyAsn1Error as exc:
                # duck-typing list
                raise IndexError(exc)

    def __setitem__(self, idx, value):
        if isinstance(idx, str):
            try:
                self.setComponentByName(idx, value)

            except error.PyAsn1Error as exc:
                # duck-typing dict
                raise KeyError(exc)

        else:
            try:
                self.setComponentByPosition(idx, value)

            except error.PyAsn1Error as exc:
                # duck-typing list
                raise IndexError(exc)

    def __contains__(self, key):
        if self._componentTypeLen:
            return key in self.componentType
        else:
            return key in self._dynamicNames

    def __len__(self):
        return len(self._componentValues)

    def __iter__(self):
        return iter(self.componentType or self._dynamicNames)

    # Python dict protocol

    def values(self):
        for idx in range(self._componentTypeLen or len(self._dynamicNames)):
            yield self[idx]

    def keys(self):
        return iter(self)

    def items(self):
        for idx in range(self._componentTypeLen or len(self._dynamicNames)):
            if self._componentTypeLen:
                yield self.componentType[idx].name, self[idx]
            else:
                yield self._dynamicNames[idx], self[idx]

    def update(self, *iterValue, **mappingValue):
        for k, v in iterValue:
            self[k] = v
        for k in mappingValue:
            self[k] = mappingValue[k]

    def clear(self):
        """Remove all components and become an empty |ASN.1| value object.

        Has the same effect on |ASN.1| object as it does on :class:`dict`
        built-in.
        """
        self._componentValues = []
        self._dynamicNames = self.DynamicNames()
        return self

    def reset(self):
        """Remove all components and become a |ASN.1| schema object.

        See :meth:`isValue` property for more information on the
        distinction between value and schema objects.
        """
        self._componentValues = noValue
        self._dynamicNames = self.DynamicNames()
        return self

    @property
    def components(self):
        return self._componentValues

    def _cloneComponentValues(self, myClone, cloneValueFlag):
        if self._componentValues is noValue:
            return

        for idx, componentValue in enumerate(self._componentValues):
            if componentValue is not noValue:
                if isinstance(componentValue, base.ConstructedAsn1Type):
                    myClone.setComponentByPosition(
                        idx, componentValue.clone(cloneValueFlag=cloneValueFlag)
                    )
                else:
                    myClone.setComponentByPosition(idx, componentValue.clone())

    def getComponentByName(self, name, default=noValue, instantiate=True):
        """Returns |ASN.1| type component by name.

        Equivalent to Python :class:`dict` subscription operation (e.g. `[]`).

        Parameters
        ----------
        name: :class:`str`
            |ASN.1| type component name

        Keyword Args
        ------------
        default: :class:`object`
            If set and requested component is a schema object, return the `default`
            object instead of the requested component.

        instantiate: :class:`bool`
            If :obj:`True` (default), inner component will be automatically
            instantiated.
            If :obj:`False` either existing component or the :class:`NoValue`
            object will be returned.

        Returns
        -------
        : :py:class:`~pyasn1.type.base.PyAsn1Item`
            Instantiate |ASN.1| component type or return existing
            component value
        """
        if self._componentTypeLen:
            idx = self.componentType.getPositionByName(name)
        else:
            try:
                idx = self._dynamicNames.getPositionByName(name)

            except KeyError:
                raise error.PyAsn1Error('Name %s not found' % (name,))

        return self.getComponentByPosition(idx, default=default, instantiate=instantiate)

    def setComponentByName(self, name, value=noValue,
                           verifyConstraints=True,
                           matchTags=True,
                           matchConstraints=True):
        """Assign |ASN.1| type component by name.

        Equivalent to Python :class:`dict` item assignment operation (e.g. `[]`).

        Parameters
        ----------
        name: :class:`str`
            |ASN.1| type component name

        Keyword Args
        ------------
        value: :class:`object` or :py:class:`~pyasn1.type.base.PyAsn1Item` derivative
            A Python value to initialize |ASN.1| component with (if *componentType* is set)
            or ASN.1 value object to assign to |ASN.1| component.
            If `value` is not given, schema object will be set as a component.

        verifyConstraints: :class:`bool`
             If :obj:`False`, skip constraints validation

        matchTags: :class:`bool`
             If :obj:`False`, skip component tags matching

        matchConstraints: :class:`bool`
             If :obj:`False`, skip component constraints matching

        Returns
        -------
        self
        """
        if self._componentTypeLen:
            idx = self.componentType.getPositionByName(name)
        else:
            try:
                idx = self._dynamicNames.getPositionByName(name)

            except KeyError:
                raise error.PyAsn1Error('Name %s not found' % (name,))

        return self.setComponentByPosition(
            idx, value, verifyConstraints, matchTags, matchConstraints
        )

    def getComponentByPosition(self, idx, default=noValue, instantiate=True):
        """Returns |ASN.1| type component by index.

        Equivalent to Python sequence subscription operation (e.g. `[]`).

        Parameters
        ----------
        idx: :class:`int`
            Component index (zero-based). Must either refer to an existing
            component or (if *componentType* is set) new ASN.1 schema object gets
            instantiated.

        Keyword Args
        ------------
        default: :class:`object`
            If set and requested component is a schema object, return the `default`
            object instead of the requested component.

        instantiate: :class:`bool`
            If :obj:`True` (default), inner component will be automatically
            instantiated.
            If :obj:`False` either existing component or the :class:`NoValue`
            object will be returned.

        Returns
        -------
        : :py:class:`~pyasn1.type.base.PyAsn1Item`
            a PyASN1 object

        Examples
        --------

        .. code-block:: python

            # can also be Set
            class MySequence(Sequence):
                componentType = NamedTypes(
                    NamedType('id', OctetString())
                )

            s = MySequence()

            # returns component #0 with `.isValue` property False
            s.getComponentByPosition(0)

            # returns None
            s.getComponentByPosition(0, default=None)

            s.clear()

            # returns noValue
            s.getComponentByPosition(0, instantiate=False)

            # sets component #0 to OctetString() ASN.1 schema
            # object and returns it
            s.getComponentByPosition(0, instantiate=True)

            # sets component #0 to ASN.1 value object
            s.setComponentByPosition(0, 'ABCD')

            # returns OctetString('ABCD') value object
            s.getComponentByPosition(0, instantiate=False)

            s.clear()

            # returns noValue
            s.getComponentByPosition(0, instantiate=False)
        """
        try:
            if self._componentValues is noValue:
                componentValue = noValue

            else:
                componentValue = self._componentValues[idx]

        except IndexError:
            componentValue = noValue

        if not instantiate:
            if componentValue is noValue or not componentValue.isValue:
                return default
            else:
                return componentValue

        if componentValue is noValue:
            self.setComponentByPosition(idx)

        componentValue = self._componentValues[idx]

        if default is noValue or componentValue.isValue:
            return componentValue
        else:
            return default

    def setComponentByPosition(self, idx, value=noValue,
                               verifyConstraints=True,
                               matchTags=True,
                               matchConstraints=True):
        """Assign |ASN.1| type component by position.

        Equivalent to Python sequence item assignment operation (e.g. `[]`).

        Parameters
        ----------
        idx : :class:`int`
            Component index (zero-based). Must either refer to existing
            component (if *componentType* is set) or to N+1 component
            otherwise. In the latter case a new component of given ASN.1
            type gets instantiated and appended to |ASN.1| sequence.

        Keyword Args
        ------------
        value: :class:`object` or :py:class:`~pyasn1.type.base.PyAsn1Item` derivative
            A Python value to initialize |ASN.1| component with (if *componentType* is set)
            or ASN.1 value object to assign to |ASN.1| component.
            If `value` is not given, schema object will be set as a component.

        verifyConstraints : :class:`bool`
             If :obj:`False`, skip constraints validation

        matchTags: :class:`bool`
             If :obj:`False`, skip component tags matching

        matchConstraints: :class:`bool`
             If :obj:`False`, skip component constraints matching

        Returns
        -------
        self
        """
        componentType = self.componentType
        componentTypeLen = self._componentTypeLen

        if self._componentValues is noValue:
            componentValues = []

        else:
            componentValues = self._componentValues

        try:
            currentValue = componentValues[idx]

        except IndexError:
            currentValue = noValue
            if componentTypeLen:
                if componentTypeLen < idx:
                    raise error.PyAsn1Error('component index out of range')

                componentValues = [noValue] * componentTypeLen

        if value is noValue:
            if componentTypeLen:
                value = componentType.getTypeByPosition(idx)
                if isinstance(value, base.ConstructedAsn1Type):
                    value = value.clone(cloneValueFlag=componentType[idx].isDefaulted)

            elif currentValue is noValue:
                raise error.PyAsn1Error('Component type not defined')

        elif not isinstance(value, base.Asn1Item):
            if componentTypeLen:
                subComponentType = componentType.getTypeByPosition(idx)
                if isinstance(subComponentType, base.SimpleAsn1Type):
                    value = subComponentType.clone(value=value)

                else:
                    raise error.PyAsn1Error('%s can cast only scalar values' % componentType.__class__.__name__)

            elif currentValue is not noValue and isinstance(currentValue, base.SimpleAsn1Type):
                value = currentValue.clone(value=value)

            else:
                raise error.PyAsn1Error('%s undefined component type' % componentType.__class__.__name__)

        elif ((verifyConstraints or matchTags or matchConstraints) and
              componentTypeLen):
            subComponentType = componentType.getTypeByPosition(idx)
            if subComponentType is not noValue:
                subtypeChecker = (self.strictConstraints and
                                  subComponentType.isSameTypeWith or
                                  subComponentType.isSuperTypeOf)

                if not subtypeChecker(value, verifyConstraints and matchTags,
                                      verifyConstraints and matchConstraints):
                    if not componentType[idx].openType:
                        raise error.PyAsn1Error('Component value is tag-incompatible: %r vs %r' % (value, componentType))

        if componentTypeLen or idx in self._dynamicNames:
            componentValues[idx] = value

        elif len(componentValues) == idx:
            componentValues.append(value)
            self._dynamicNames.addField(idx)

        else:
            raise error.PyAsn1Error('Component index out of range')

        self._componentValues = componentValues

        return self

    @property
    def isValue(self):
        """Indicate that |ASN.1| object represents ASN.1 value.

        If *isValue* is :obj:`False` then this object represents just ASN.1 schema.

        If *isValue* is :obj:`True` then, in addition to its ASN.1 schema features,
        this object can also be used like a Python built-in object (e.g.
        :class:`int`, :class:`str`, :class:`dict` etc.).

        Returns
        -------
        : :class:`bool`
            :obj:`False` if object represents just ASN.1 schema.
            :obj:`True` if object represents ASN.1 schema and can be used as a
            normal value.

        Note
        ----
        There is an important distinction between PyASN1 schema and value objects.
        The PyASN1 schema objects can only participate in ASN.1 schema-related
        operations (e.g. defining or testing the structure of the data). Most
        obvious uses of ASN.1 schema is to guide serialisation codecs whilst
        encoding/decoding serialised ASN.1 contents.

        The PyASN1 value objects can **additionally** participate in many operations
        involving regular Python objects (e.g. arithmetic, comprehension etc).

        It is sufficient for |ASN.1| objects to have all non-optional and non-defaulted
        components being value objects to be considered as a value objects as a whole.
        In other words, even having one or more optional components not turned into
        value objects, |ASN.1| object is still considered as a value object. Defaulted
        components are normally value objects by default.
        """
        if self._componentValues is noValue:
            return False

        componentType = self.componentType

        if componentType:
            for idx, subComponentType in enumerate(componentType.namedTypes):
                if subComponentType.isDefaulted or subComponentType.isOptional:
                    continue

                if not self._componentValues:
                    return False

                componentValue = self._componentValues[idx]
                if componentValue is noValue or not componentValue.isValue:
                    return False

        else:
            for componentValue in self._componentValues:
                if componentValue is noValue or not componentValue.isValue:
                    return False

        return True

    @property
    def isInconsistent(self):
        """Run necessary checks to ensure |ASN.1| object consistency.

        Default action is to verify |ASN.1| object against constraints imposed
        by `subtypeSpec`.

        Raises
        ------
        :py:class:`~pyasn1.error.PyAsn1tError` on any inconsistencies found
        """
        if self.componentType is noValue or not self.subtypeSpec:
            return False

        if self._componentValues is noValue:
            return True

        mapping = {}

        for idx, value in enumerate(self._componentValues):
            # Absent fields are not in the mapping
            if value is noValue:
                continue

            name = self.componentType.getNameByPosition(idx)

            mapping[name] = value

        try:
            # Represent Sequence/Set as a bare dict to constraints chain
            self.subtypeSpec(mapping)

        except error.PyAsn1Error as exc:
            return exc

        return False

    def prettyPrint(self, scope=0):
        """Return an object representation string.

        Returns
        -------
        : :class:`str`
            Human-friendly object representation.
        """
        scope += 1
        representation = self.__class__.__name__ + ':\n'
        for idx, componentValue in enumerate(self._componentValues):
            if componentValue is not noValue and componentValue.isValue:
                representation += ' ' * scope
                if self.componentType:
                    representation += self.componentType.getNameByPosition(idx)
                else:
                    representation += self._dynamicNames.getNameByPosition(idx)
                representation = '%s=%s\n' % (
                    representation, componentValue.prettyPrint(scope)
                )
        return representation

    def prettyPrintType(self, scope=0):
        scope += 1
        representation = '%s -> %s {\n' % (self.tagSet, self.__class__.__name__)
        for idx, componentType in enumerate(self.componentType.values() or self._componentValues):
            representation += ' ' * scope
            if self.componentType:
                representation += '"%s"' % self.componentType.getNameByPosition(idx)
            else:
                representation += '"%s"' % self._dynamicNames.getNameByPosition(idx)
            representation = '%s = %s\n' % (
                representation, componentType.prettyPrintType(scope)
            )
        return representation + '\n' + ' ' * (scope - 1) + '}'

    # backward compatibility

    def setDefaultComponents(self):
        return self

    def getComponentType(self):
        if self._componentTypeLen:
            return self.componentType

    def getNameByPosition(self, idx):
        if self._componentTypeLen:
            return self.componentType[idx].name

class Sequence(SequenceAndSetBase):
    __doc__ = SequenceAndSetBase.__doc__

    #: Set (on class, not on instance) or return a
    #: :py:class:`~pyasn1.type.tag.TagSet` object representing ASN.1 tag(s)
    #: associated with |ASN.1| type.
    tagSet = tag.initTagSet(
        tag.Tag(tag.tagClassUniversal, tag.tagFormatConstructed, 0x10)
    )

    #: Set (on class, not on instance) or return a
    #: :py:class:`~pyasn1.type.constraint.ConstraintsIntersection` object
    #: imposing constraints on |ASN.1| type initialization values.
    subtypeSpec = constraint.ConstraintsIntersection()

    #: Default collection of ASN.1 types of component (e.g. :py:class:`~pyasn1.type.namedtype.NamedType`)
    #: object imposing size constraint on |ASN.1| objects
    componentType = namedtype.NamedTypes()

    # Disambiguation ASN.1 types identification
    typeId = SequenceAndSetBase.getTypeId()

    # backward compatibility

    def getComponentTagMapNearPosition(self, idx):
        if self.componentType:
            return self.componentType.getTagMapNearPosition(idx)

    def getComponentPositionNearType(self, tagSet, idx):
        if self.componentType:
            return self.componentType.getPositionNearType(tagSet, idx)
        else:
            return idx


class Set(SequenceAndSetBase):
    __doc__ = SequenceAndSetBase.__doc__

    #: Set (on class, not on instance) or return a
    #: :py:class:`~pyasn1.type.tag.TagSet` object representing ASN.1 tag(s)
    #: associated with |ASN.1| type.
    tagSet = tag.initTagSet(
        tag.Tag(tag.tagClassUniversal, tag.tagFormatConstructed, 0x11)
    )

    #: Default collection of ASN.1 types of component (e.g. :py:class:`~pyasn1.type.namedtype.NamedType`)
    #: object representing ASN.1 type allowed within |ASN.1| type
    componentType = namedtype.NamedTypes()

    #: Set (on class, not on instance) or return a
    #: :py:class:`~pyasn1.type.constraint.ConstraintsIntersection` object
    #: imposing constraints on |ASN.1| type initialization values.
    subtypeSpec = constraint.ConstraintsIntersection()

    # Disambiguation ASN.1 types identification
    typeId = SequenceAndSetBase.getTypeId()

    def getComponent(self, innerFlag=False):
        return self

    def getComponentByType(self, tagSet, default=noValue,
                           instantiate=True, innerFlag=False):
        """Returns |ASN.1| type component by ASN.1 tag.

        Parameters
        ----------
        tagSet : :py:class:`~pyasn1.type.tag.TagSet`
            Object representing ASN.1 tags to identify one of
            |ASN.1| object component

        Keyword Args
        ------------
        default: :class:`object`
            If set and requested component is a schema object, return the `default`
            object instead of the requested component.

        instantiate: :class:`bool`
            If :obj:`True` (default), inner component will be automatically
            instantiated.
            If :obj:`False` either existing component or the :class:`noValue`
            object will be returned.

        Returns
        -------
        : :py:class:`~pyasn1.type.base.PyAsn1Item`
            a pyasn1 object
        """
        componentValue = self.getComponentByPosition(
            self.componentType.getPositionByType(tagSet),
            default=default, instantiate=instantiate
        )
        if innerFlag and isinstance(componentValue, Set):
            # get inner component by inner tagSet
            return componentValue.getComponent(innerFlag=True)
        else:
            # get outer component by inner tagSet
            return componentValue

    def setComponentByType(self, tagSet, value=noValue,
                           verifyConstraints=True,
                           matchTags=True,
                           matchConstraints=True,
                           innerFlag=False):
        """Assign |ASN.1| type component by ASN.1 tag.

        Parameters
        ----------
        tagSet : :py:class:`~pyasn1.type.tag.TagSet`
            Object representing ASN.1 tags to identify one of
            |ASN.1| object component

        Keyword Args
        ------------
        value: :class:`object` or :py:class:`~pyasn1.type.base.PyAsn1Item` derivative
            A Python value to initialize |ASN.1| component with (if *componentType* is set)
            or ASN.1 value object to assign to |ASN.1| component.
            If `value` is not given, schema object will be set as a component.

        verifyConstraints : :class:`bool`
            If :obj:`False`, skip constraints validation

        matchTags: :class:`bool`
            If :obj:`False`, skip component tags matching

        matchConstraints: :class:`bool`
            If :obj:`False`, skip component constraints matching

        innerFlag: :class:`bool`
            If :obj:`True`, search for matching *tagSet* recursively.

        Returns
        -------
        self
        """
        idx = self.componentType.getPositionByType(tagSet)

        if innerFlag:  # set inner component by inner tagSet
            componentType = self.componentType.getTypeByPosition(idx)

            if componentType.tagSet:
                return self.setComponentByPosition(
                    idx, value, verifyConstraints, matchTags, matchConstraints
                )
            else:
                componentType = self.getComponentByPosition(idx)
                return componentType.setComponentByType(
                    tagSet, value, verifyConstraints, matchTags, matchConstraints, innerFlag=innerFlag
                )
        else:  # set outer component by inner tagSet
            return self.setComponentByPosition(
                idx, value, verifyConstraints, matchTags, matchConstraints
            )

    @property
    def componentTagMap(self):
        if self.componentType:
            return self.componentType.tagMapUnique


class Choice(Set):
    """Create |ASN.1| schema or value object.

    |ASN.1| class is based on :class:`~pyasn1.type.base.ConstructedAsn1Type`,
    its objects are mutable and duck-type Python :class:`list` objects.

    Keyword Args
    ------------
    componentType: :py:class:`~pyasn1.type.namedtype.NamedType`
        Object holding named ASN.1 types allowed within this collection

    tagSet: :py:class:`~pyasn1.type.tag.TagSet`
        Object representing non-default ASN.1 tag(s)

    subtypeSpec: :py:class:`~pyasn1.type.constraint.ConstraintsIntersection`
        Object representing non-default ASN.1 subtype constraint(s).  Constraints
        verification for |ASN.1| type can only occur on explicit
        `.isInconsistent` call.

    Examples
    --------

    .. code-block:: python

        class Afters(Choice):
            '''
            ASN.1 specification:

            Afters ::= CHOICE {
                cheese  [0] IA5String,
                dessert [1] IA5String
            }
            '''
            componentType = NamedTypes(
                NamedType('cheese', IA5String().subtype(
                    implicitTag=Tag(tagClassContext, tagFormatSimple, 0)
                ),
                NamedType('dessert', IA5String().subtype(
                    implicitTag=Tag(tagClassContext, tagFormatSimple, 1)
                )
            )

        afters = Afters()
        afters['cheese'] = 'Mascarpone'
    """
    #: Set (on class, not on instance) or return a
    #: :py:class:`~pyasn1.type.tag.TagSet` object representing ASN.1 tag(s)
    #: associated with |ASN.1| type.
    tagSet = tag.TagSet()  # untagged

    #: Default collection of ASN.1 types of component (e.g. :py:class:`~pyasn1.type.namedtype.NamedType`)
    #: object representing ASN.1 type allowed within |ASN.1| type
    componentType = namedtype.NamedTypes()

    #: Set (on class, not on instance) or return a
    #: :py:class:`~pyasn1.type.constraint.ConstraintsIntersection` object
    #: imposing constraints on |ASN.1| type initialization values.
    subtypeSpec = constraint.ConstraintsIntersection(
        constraint.ValueSizeConstraint(1, 1)
    )

    # Disambiguation ASN.1 types identification
    typeId = Set.getTypeId()

    _currentIdx = None

    def __eq__(self, other):
        if self._componentValues:
            return self._componentValues[self._currentIdx] == other
        return NotImplemented

    def __ne__(self, other):
        if self._componentValues:
            return self._componentValues[self._currentIdx] != other
        return NotImplemented

    def __lt__(self, other):
        if self._componentValues:
            return self._componentValues[self._currentIdx] < other
        return NotImplemented

    def __le__(self, other):
        if self._componentValues:
            return self._componentValues[self._currentIdx] <= other
        return NotImplemented

    def __gt__(self, other):
        if self._componentValues:
            return self._componentValues[self._currentIdx] > other
        return NotImplemented

    def __ge__(self, other):
        if self._componentValues:
            return self._componentValues[self._currentIdx] >= other
        return NotImplemented

    def __bool__(self):
        return bool(self._componentValues)

    def __len__(self):
        return self._currentIdx is not None and 1 or 0

    def __contains__(self, key):
        if self._currentIdx is None:
            return False
        return key == self.componentType[self._currentIdx].getName()

    def __iter__(self):
        if self._currentIdx is None:
            raise StopIteration
        yield self.componentType[self._currentIdx].getName()

    # Python dict protocol

    def values(self):
        if self._currentIdx is not None:
            yield self._componentValues[self._currentIdx]

    def keys(self):
        if self._currentIdx is not None:
            yield self.componentType[self._currentIdx].getName()

    def items(self):
        if self._currentIdx is not None:
            yield self.componentType[self._currentIdx].getName(), self[self._currentIdx]

    def checkConsistency(self):
        if self._currentIdx is None:
            raise error.PyAsn1Error('Component not chosen')

    def _cloneComponentValues(self, myClone, cloneValueFlag):
        try:
            component = self.getComponent()
        except error.PyAsn1Error:
            pass
        else:
            if isinstance(component, Choice):
                tagSet = component.effectiveTagSet
            else:
                tagSet = component.tagSet
            if isinstance(component, base.ConstructedAsn1Type):
                myClone.setComponentByType(
                    tagSet, component.clone(cloneValueFlag=cloneValueFlag)
                )
            else:
                myClone.setComponentByType(tagSet, component.clone())

    def getComponentByPosition(self, idx, default=noValue, instantiate=True):
        __doc__ = Set.__doc__

        if self._currentIdx is None or self._currentIdx != idx:
            return Set.getComponentByPosition(self, idx, default=default,
                                              instantiate=instantiate)

        return self._componentValues[idx]

    def setComponentByPosition(self, idx, value=noValue,
                               verifyConstraints=True,
                               matchTags=True,
                               matchConstraints=True):
        """Assign |ASN.1| type component by position.

        Equivalent to Python sequence item assignment operation (e.g. `[]`).

        Parameters
        ----------
        idx: :class:`int`
            Component index (zero-based). Must either refer to existing
            component or to N+1 component. In the latter case a new component
            type gets instantiated (if *componentType* is set, or given ASN.1
            object is taken otherwise) and appended to the |ASN.1| sequence.

        Keyword Args
        ------------
        value: :class:`object` or :py:class:`~pyasn1.type.base.PyAsn1Item` derivative
            A Python value to initialize |ASN.1| component with (if *componentType* is set)
            or ASN.1 value object to assign to |ASN.1| component. Once a new value is
            set to *idx* component, previous value is dropped.
            If `value` is not given, schema object will be set as a component.

        verifyConstraints : :class:`bool`
            If :obj:`False`, skip constraints validation

        matchTags: :class:`bool`
            If :obj:`False`, skip component tags matching

        matchConstraints: :class:`bool`
            If :obj:`False`, skip component constraints matching

        Returns
        -------
        self
        """
        oldIdx = self._currentIdx
        Set.setComponentByPosition(self, idx, value, verifyConstraints, matchTags, matchConstraints)
        self._currentIdx = idx
        if oldIdx is not None and oldIdx != idx:
            self._componentValues[oldIdx] = noValue
        return self

    @property
    def effectiveTagSet(self):
        """Return a :class:`~pyasn1.type.tag.TagSet` object of the currently initialized component or self (if |ASN.1| is tagged)."""
        if self.tagSet:
            return self.tagSet
        else:
            component = self.getComponent()
            return component.effectiveTagSet

    @property
    def tagMap(self):
        """"Return a :class:`~pyasn1.type.tagmap.TagMap` object mapping
            ASN.1 tags to ASN.1 objects contained within callee.
        """
        if self.tagSet:
            return Set.tagMap.fget(self)
        else:
            return self.componentType.tagMapUnique

    def getComponent(self, innerFlag=False):
        """Return currently assigned component of the |ASN.1| object.

        Returns
        -------
        : :py:class:`~pyasn1.type.base.PyAsn1Item`
            a PyASN1 object
        """
        if self._currentIdx is None:
            raise error.PyAsn1Error('Component not chosen')
        else:
            c = self._componentValues[self._currentIdx]
            if innerFlag and isinstance(c, Choice):
                return c.getComponent(innerFlag)
            else:
                return c

    def getName(self, innerFlag=False):
        """Return the name of currently assigned component of the |ASN.1| object.

        Returns
        -------
        : :py:class:`str`
            |ASN.1| component name
        """
        if self._currentIdx is None:
            raise error.PyAsn1Error('Component not chosen')
        else:
            if innerFlag:
                c = self._componentValues[self._currentIdx]
                if isinstance(c, Choice):
                    return c.getName(innerFlag)
            return self.componentType.getNameByPosition(self._currentIdx)

    @property
    def isValue(self):
        """Indicate that |ASN.1| object represents ASN.1 value.

        If *isValue* is :obj:`False` then this object represents just ASN.1 schema.

        If *isValue* is :obj:`True` then, in addition to its ASN.1 schema features,
        this object can also be used like a Python built-in object (e.g.
        :class:`int`, :class:`str`, :class:`dict` etc.).

        Returns
        -------
        : :class:`bool`
            :obj:`False` if object represents just ASN.1 schema.
            :obj:`True` if object represents ASN.1 schema and can be used as a normal
            value.

        Note
        ----
        There is an important distinction between PyASN1 schema and value objects.
        The PyASN1 schema objects can only participate in ASN.1 schema-related
        operations (e.g. defining or testing the structure of the data). Most
        obvious uses of ASN.1 schema is to guide serialisation codecs whilst
        encoding/decoding serialised ASN.1 contents.

        The PyASN1 value objects can **additionally** participate in many operations
        involving regular Python objects (e.g. arithmetic, comprehension etc).
        """
        if self._currentIdx is None:
            return False

        componentValue = self._componentValues[self._currentIdx]

        return componentValue is not noValue and componentValue.isValue

    def clear(self):
        self._currentIdx = None
        return Set.clear(self)

    # compatibility stubs

    def getMinTagSet(self):
        return self.minTagSet


class Any(OctetString):
    """Create |ASN.1| schema or value object.

    |ASN.1| class is based on :class:`~pyasn1.type.base.SimpleAsn1Type`,
    its objects are immutable and duck-type :class:`bytes`.
    When used in Unicode context, |ASN.1| type assumes
    "|encoding|" serialisation.

    Keyword Args
    ------------
    value: :class:`unicode`, :class:`str`, :class:`bytes` or |ASN.1| object
        :class:`bytes`, alternatively :class:`str`
        representing character string to be serialised into octets (note
        `encoding` parameter) or |ASN.1| object.
        If `value` is not given, schema object will be created.

    tagSet: :py:class:`~pyasn1.type.tag.TagSet`
        Object representing non-default ASN.1 tag(s)

    subtypeSpec: :py:class:`~pyasn1.type.constraint.ConstraintsIntersection`
        Object representing non-default ASN.1 subtype constraint(s). Constraints
        verification for |ASN.1| type occurs automatically on object
        instantiation.

    encoding: :py:class:`str`
        Unicode codec ID to encode/decode
        :class:`str` the payload when |ASN.1| object is used
        in text string context.

    binValue: :py:class:`str`
        Binary string initializer to use instead of the *value*.
        Example: '10110011'.

    hexValue: :py:class:`str`
        Hexadecimal string initializer to use instead of the *value*.
        Example: 'DEADBEEF'.

    Raises
    ------
    ~pyasn1.error.ValueConstraintError, ~pyasn1.error.PyAsn1Error
        On constraint violation or bad initializer.

    Examples
    --------
    .. code-block:: python

        class Error(Sequence):
            '''
            ASN.1 specification:

            Error ::= SEQUENCE {
                code      INTEGER,
                parameter ANY DEFINED BY code  -- Either INTEGER or REAL
            }
            '''
            componentType=NamedTypes(
                NamedType('code', Integer()),
                NamedType('parameter', Any(),
                          openType=OpenType('code', {1: Integer(),
                                                     2: Real()}))
            )

        error = Error()
        error['code'] = 1
        error['parameter'] = Integer(1234)
    """
    #: Set (on class, not on instance) or return a
    #: :py:class:`~pyasn1.type.tag.TagSet` object representing ASN.1 tag(s)
    #: associated with |ASN.1| type.
    tagSet = tag.TagSet()  # untagged

    #: Set (on class, not on instance) or return a
    #: :py:class:`~pyasn1.type.constraint.ConstraintsIntersection` object
    #: imposing constraints on |ASN.1| type initialization values.
    subtypeSpec = constraint.ConstraintsIntersection()

    # Disambiguation ASN.1 types identification
    typeId = OctetString.getTypeId()

    @property
    def tagMap(self):
        """"Return a :class:`~pyasn1.type.tagmap.TagMap` object mapping
            ASN.1 tags to ASN.1 objects contained within callee.
        """
        try:
            return self._tagMap

        except AttributeError:
            self._tagMap = tagmap.TagMap(
                {self.tagSet: self},
                {eoo.endOfOctets.tagSet: eoo.endOfOctets},
                self
            )

            return self._tagMap

# XXX
# coercion rules?

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\_php_builtins.py ===
"""
    pygments.lexers._php_builtins
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    This file loads the function names and their modules from the
    php webpage and generates itself.

    Run with `python -I` to regenerate.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

MODULES = {'APCu': ('apcu_add',
          'apcu_cache_info',
          'apcu_cas',
          'apcu_clear_cache',
          'apcu_dec',
          'apcu_delete',
          'apcu_enabled',
          'apcu_entry',
          'apcu_exists',
          'apcu_fetch',
          'apcu_inc',
          'apcu_key_info',
          'apcu_sma_info',
          'apcu_store'),
 'Aliases and deprecated Mysqli': ('mysqli_connect',
                                   'mysqli_execute',
                                   'mysqli_get_client_stats',
                                   'mysqli_get_links_stats',
                                   'mysqli_report'),
 'Apache': ('apache_child_terminate',
            'apache_get_modules',
            'apache_get_version',
            'apache_getenv',
            'apache_lookup_uri',
            'apache_note',
            'apache_request_headers',
            'apache_response_headers',
            'apache_setenv',
            'getallheaders',
            'virtual'),
 'Array': ('array_change_key_case',
           'array_chunk',
           'array_column',
           'array_combine',
           'array_count_values',
           'array_diff_assoc',
           'array_diff_key',
           'array_diff_uassoc',
           'array_diff_ukey',
           'array_diff',
           'array_fill_keys',
           'array_fill',
           'array_filter',
           'array_flip',
           'array_intersect_assoc',
           'array_intersect_key',
           'array_intersect_uassoc',
           'array_intersect_ukey',
           'array_intersect',
           'array_is_list',
           'array_key_exists',
           'array_key_first',
           'array_key_last',
           'array_keys',
           'array_map',
           'array_merge_recursive',
           'array_merge',
           'array_multisort',
           'array_pad',
           'array_pop',
           'array_product',
           'array_push',
           'array_rand',
           'array_reduce',
           'array_replace_recursive',
           'array_replace',
           'array_reverse',
           'array_search',
           'array_shift',
           'array_slice',
           'array_splice',
           'array_sum',
           'array_udiff_assoc',
           'array_udiff_uassoc',
           'array_udiff',
           'array_uintersect_assoc',
           'array_uintersect_uassoc',
           'array_uintersect',
           'array_unique',
           'array_unshift',
           'array_values',
           'array_walk_recursive',
           'array_walk',
           'array',
           'arsort',
           'asort',
           'compact',
           'count',
           'current',
           'each',
           'end',
           'extract',
           'in_array',
           'key_exists',
           'key',
           'krsort',
           'ksort',
           'list',
           'natcasesort',
           'natsort',
           'next',
           'pos',
           'prev',
           'range',
           'reset',
           'rsort',
           'shuffle',
           'sizeof',
           'sort',
           'uasort',
           'uksort',
           'usort'),
 'BC Math': ('bcadd',
             'bccomp',
             'bcdiv',
             'bcmod',
             'bcmul',
             'bcpow',
             'bcpowmod',
             'bcscale',
             'bcsqrt',
             'bcsub'),
 'Bzip2': ('bzclose',
           'bzcompress',
           'bzdecompress',
           'bzerrno',
           'bzerror',
           'bzerrstr',
           'bzflush',
           'bzopen',
           'bzread',
           'bzwrite'),
 'COM': ('com_create_guid',
         'com_event_sink',
         'com_get_active_object',
         'com_load_typelib',
         'com_message_pump',
         'com_print_typeinfo',
         'variant_abs',
         'variant_add',
         'variant_and',
         'variant_cast',
         'variant_cat',
         'variant_cmp',
         'variant_date_from_timestamp',
         'variant_date_to_timestamp',
         'variant_div',
         'variant_eqv',
         'variant_fix',
         'variant_get_type',
         'variant_idiv',
         'variant_imp',
         'variant_int',
         'variant_mod',
         'variant_mul',
         'variant_neg',
         'variant_not',
         'variant_or',
         'variant_pow',
         'variant_round',
         'variant_set_type',
         'variant_set',
         'variant_sub',
         'variant_xor'),
 'CSPRNG': ('random_bytes', 'random_int'),
 'CUBRID': ('cubrid_bind',
            'cubrid_close_prepare',
            'cubrid_close_request',
            'cubrid_col_get',
            'cubrid_col_size',
            'cubrid_column_names',
            'cubrid_column_types',
            'cubrid_commit',
            'cubrid_connect_with_url',
            'cubrid_connect',
            'cubrid_current_oid',
            'cubrid_disconnect',
            'cubrid_drop',
            'cubrid_error_code_facility',
            'cubrid_error_code',
            'cubrid_error_msg',
            'cubrid_execute',
            'cubrid_fetch',
            'cubrid_free_result',
            'cubrid_get_autocommit',
            'cubrid_get_charset',
            'cubrid_get_class_name',
            'cubrid_get_client_info',
            'cubrid_get_db_parameter',
            'cubrid_get_query_timeout',
            'cubrid_get_server_info',
            'cubrid_get',
            'cubrid_insert_id',
            'cubrid_is_instance',
            'cubrid_lob_close',
            'cubrid_lob_export',
            'cubrid_lob_get',
            'cubrid_lob_send',
            'cubrid_lob_size',
            'cubrid_lob2_bind',
            'cubrid_lob2_close',
            'cubrid_lob2_export',
            'cubrid_lob2_import',
            'cubrid_lob2_new',
            'cubrid_lob2_read',
            'cubrid_lob2_seek64',
            'cubrid_lob2_seek',
            'cubrid_lob2_size64',
            'cubrid_lob2_size',
            'cubrid_lob2_tell64',
            'cubrid_lob2_tell',
            'cubrid_lob2_write',
            'cubrid_lock_read',
            'cubrid_lock_write',
            'cubrid_move_cursor',
            'cubrid_next_result',
            'cubrid_num_cols',
            'cubrid_num_rows',
            'cubrid_pconnect_with_url',
            'cubrid_pconnect',
            'cubrid_prepare',
            'cubrid_put',
            'cubrid_rollback',
            'cubrid_schema',
            'cubrid_seq_drop',
            'cubrid_seq_insert',
            'cubrid_seq_put',
            'cubrid_set_add',
            'cubrid_set_autocommit',
            'cubrid_set_db_parameter',
            'cubrid_set_drop',
            'cubrid_set_query_timeout',
            'cubrid_version'),
 'Calendar': ('cal_days_in_month',
              'cal_from_jd',
              'cal_info',
              'cal_to_jd',
              'easter_date',
              'easter_days',
              'frenchtojd',
              'gregoriantojd',
              'jddayofweek',
              'jdmonthname',
              'jdtofrench',
              'jdtogregorian',
              'jdtojewish',
              'jdtojulian',
              'jdtounix',
              'jewishtojd',
              'juliantojd',
              'unixtojd'),
 'Classes/Object': ('__autoload',
                    'class_alias',
                    'class_exists',
                    'enum_exists',
                    'get_called_class',
                    'get_class_methods',
                    'get_class_vars',
                    'get_class',
                    'get_declared_classes',
                    'get_declared_interfaces',
                    'get_declared_traits',
                    'get_mangled_object_vars',
                    'get_object_vars',
                    'get_parent_class',
                    'interface_exists',
                    'is_a',
                    'is_subclass_of',
                    'method_exists',
                    'property_exists',
                    'trait_exists'),
 'Ctype': ('ctype_alnum',
           'ctype_alpha',
           'ctype_cntrl',
           'ctype_digit',
           'ctype_graph',
           'ctype_lower',
           'ctype_print',
           'ctype_punct',
           'ctype_space',
           'ctype_upper',
           'ctype_xdigit'),
 'DBA': ('dba_close',
         'dba_delete',
         'dba_exists',
         'dba_fetch',
         'dba_firstkey',
         'dba_handlers',
         'dba_insert',
         'dba_key_split',
         'dba_list',
         'dba_nextkey',
         'dba_open',
         'dba_optimize',
         'dba_popen',
         'dba_replace',
         'dba_sync'),
 'DOM': ('dom_import_simplexml',),
 'Date/Time': ('checkdate',
               'date_add',
               'date_create_from_format',
               'date_create_immutable_from_format',
               'date_create_immutable',
               'date_create',
               'date_date_set',
               'date_default_timezone_get',
               'date_default_timezone_set',
               'date_diff',
               'date_format',
               'date_get_last_errors',
               'date_interval_create_from_date_string',
               'date_interval_format',
               'date_isodate_set',
               'date_modify',
               'date_offset_get',
               'date_parse_from_format',
               'date_parse',
               'date_sub',
               'date_sun_info',
               'date_sunrise',
               'date_sunset',
               'date_time_set',
               'date_timestamp_get',
               'date_timestamp_set',
               'date_timezone_get',
               'date_timezone_set',
               'date',
               'getdate',
               'gettimeofday',
               'gmdate',
               'gmmktime',
               'gmstrftime',
               'idate',
               'localtime',
               'microtime',
               'mktime',
               'strftime',
               'strptime',
               'strtotime',
               'time',
               'timezone_abbreviations_list',
               'timezone_identifiers_list',
               'timezone_location_get',
               'timezone_name_from_abbr',
               'timezone_name_get',
               'timezone_offset_get',
               'timezone_open',
               'timezone_transitions_get',
               'timezone_version_get'),
 'Direct IO': ('dio_close',
               'dio_fcntl',
               'dio_open',
               'dio_read',
               'dio_seek',
               'dio_stat',
               'dio_tcsetattr',
               'dio_truncate',
               'dio_write'),
 'Directory': ('chdir',
               'chroot',
               'closedir',
               'dir',
               'getcwd',
               'opendir',
               'readdir',
               'rewinddir',
               'scandir'),
 'Eio': ('eio_busy',
         'eio_cancel',
         'eio_chmod',
         'eio_chown',
         'eio_close',
         'eio_custom',
         'eio_dup2',
         'eio_event_loop',
         'eio_fallocate',
         'eio_fchmod',
         'eio_fchown',
         'eio_fdatasync',
         'eio_fstat',
         'eio_fstatvfs',
         'eio_fsync',
         'eio_ftruncate',
         'eio_futime',
         'eio_get_event_stream',
         'eio_get_last_error',
         'eio_grp_add',
         'eio_grp_cancel',
         'eio_grp_limit',
         'eio_grp',
         'eio_init',
         'eio_link',
         'eio_lstat',
         'eio_mkdir',
         'eio_mknod',
         'eio_nop',
         'eio_npending',
         'eio_nready',
         'eio_nreqs',
         'eio_nthreads',
         'eio_open',
         'eio_poll',
         'eio_read',
         'eio_readahead',
         'eio_readdir',
         'eio_readlink',
         'eio_realpath',
         'eio_rename',
         'eio_rmdir',
         'eio_seek',
         'eio_sendfile',
         'eio_set_max_idle',
         'eio_set_max_parallel',
         'eio_set_max_poll_reqs',
         'eio_set_max_poll_time',
         'eio_set_min_parallel',
         'eio_stat',
         'eio_statvfs',
         'eio_symlink',
         'eio_sync_file_range',
         'eio_sync',
         'eio_syncfs',
         'eio_truncate',
         'eio_unlink',
         'eio_utime',
         'eio_write'),
 'Enchant': ('enchant_broker_describe',
             'enchant_broker_dict_exists',
             'enchant_broker_free_dict',
             'enchant_broker_free',
             'enchant_broker_get_dict_path',
             'enchant_broker_get_error',
             'enchant_broker_init',
             'enchant_broker_list_dicts',
             'enchant_broker_request_dict',
             'enchant_broker_request_pwl_dict',
             'enchant_broker_set_dict_path',
             'enchant_broker_set_ordering',
             'enchant_dict_add_to_personal',
             'enchant_dict_add_to_session',
             'enchant_dict_add',
             'enchant_dict_check',
             'enchant_dict_describe',
             'enchant_dict_get_error',
             'enchant_dict_is_added',
             'enchant_dict_is_in_session',
             'enchant_dict_quick_check',
             'enchant_dict_store_replacement',
             'enchant_dict_suggest'),
 'Error Handling': ('debug_backtrace',
                    'debug_print_backtrace',
                    'error_clear_last',
                    'error_get_last',
                    'error_log',
                    'error_reporting',
                    'restore_error_handler',
                    'restore_exception_handler',
                    'set_error_handler',
                    'set_exception_handler',
                    'trigger_error',
                    'user_error'),
 'Exif': ('exif_imagetype',
          'exif_read_data',
          'exif_tagname',
          'exif_thumbnail',
          'read_exif_data'),
 'Expect': ('expect_expectl', 'expect_popen'),
 'FDF': ('fdf_add_doc_javascript',
         'fdf_add_template',
         'fdf_close',
         'fdf_create',
         'fdf_enum_values',
         'fdf_errno',
         'fdf_error',
         'fdf_get_ap',
         'fdf_get_attachment',
         'fdf_get_encoding',
         'fdf_get_file',
         'fdf_get_flags',
         'fdf_get_opt',
         'fdf_get_status',
         'fdf_get_value',
         'fdf_get_version',
         'fdf_header',
         'fdf_next_field_name',
         'fdf_open_string',
         'fdf_open',
         'fdf_remove_item',
         'fdf_save_string',
         'fdf_save',
         'fdf_set_ap',
         'fdf_set_encoding',
         'fdf_set_file',
         'fdf_set_flags',
         'fdf_set_javascript_action',
         'fdf_set_on_import_javascript',
         'fdf_set_opt',
         'fdf_set_status',
         'fdf_set_submit_form_action',
         'fdf_set_target_frame',
         'fdf_set_value',
         'fdf_set_version'),
 'FPM': ('fastcgi_finish_request',),
 'FTP': ('ftp_alloc',
         'ftp_append',
         'ftp_cdup',
         'ftp_chdir',
         'ftp_chmod',
         'ftp_close',
         'ftp_connect',
         'ftp_delete',
         'ftp_exec',
         'ftp_fget',
         'ftp_fput',
         'ftp_get_option',
         'ftp_get',
         'ftp_login',
         'ftp_mdtm',
         'ftp_mkdir',
         'ftp_mlsd',
         'ftp_nb_continue',
         'ftp_nb_fget',
         'ftp_nb_fput',
         'ftp_nb_get',
         'ftp_nb_put',
         'ftp_nlist',
         'ftp_pasv',
         'ftp_put',
         'ftp_pwd',
         'ftp_quit',
         'ftp_raw',
         'ftp_rawlist',
         'ftp_rename',
         'ftp_rmdir',
         'ftp_set_option',
         'ftp_site',
         'ftp_size',
         'ftp_ssl_connect',
         'ftp_systype'),
 'Fann': ('fann_cascadetrain_on_data',
          'fann_cascadetrain_on_file',
          'fann_clear_scaling_params',
          'fann_copy',
          'fann_create_from_file',
          'fann_create_shortcut_array',
          'fann_create_shortcut',
          'fann_create_sparse_array',
          'fann_create_sparse',
          'fann_create_standard_array',
          'fann_create_standard',
          'fann_create_train_from_callback',
          'fann_create_train',
          'fann_descale_input',
          'fann_descale_output',
          'fann_descale_train',
          'fann_destroy_train',
          'fann_destroy',
          'fann_duplicate_train_data',
          'fann_get_activation_function',
          'fann_get_activation_steepness',
          'fann_get_bias_array',
          'fann_get_bit_fail_limit',
          'fann_get_bit_fail',
          'fann_get_cascade_activation_functions_count',
          'fann_get_cascade_activation_functions',
          'fann_get_cascade_activation_steepnesses_count',
          'fann_get_cascade_activation_steepnesses',
          'fann_get_cascade_candidate_change_fraction',
          'fann_get_cascade_candidate_limit',
          'fann_get_cascade_candidate_stagnation_epochs',
          'fann_get_cascade_max_cand_epochs',
          'fann_get_cascade_max_out_epochs',
          'fann_get_cascade_min_cand_epochs',
          'fann_get_cascade_min_out_epochs',
          'fann_get_cascade_num_candidate_groups',
          'fann_get_cascade_num_candidates',
          'fann_get_cascade_output_change_fraction',
          'fann_get_cascade_output_stagnation_epochs',
          'fann_get_cascade_weight_multiplier',
          'fann_get_connection_array',
          'fann_get_connection_rate',
          'fann_get_errno',
          'fann_get_errstr',
          'fann_get_layer_array',
          'fann_get_learning_momentum',
          'fann_get_learning_rate',
          'fann_get_MSE',
          'fann_get_network_type',
          'fann_get_num_input',
          'fann_get_num_layers',
          'fann_get_num_output',
          'fann_get_quickprop_decay',
          'fann_get_quickprop_mu',
          'fann_get_rprop_decrease_factor',
          'fann_get_rprop_delta_max',
          'fann_get_rprop_delta_min',
          'fann_get_rprop_delta_zero',
          'fann_get_rprop_increase_factor',
          'fann_get_sarprop_step_error_shift',
          'fann_get_sarprop_step_error_threshold_factor',
          'fann_get_sarprop_temperature',
          'fann_get_sarprop_weight_decay_shift',
          'fann_get_total_connections',
          'fann_get_total_neurons',
          'fann_get_train_error_function',
          'fann_get_train_stop_function',
          'fann_get_training_algorithm',
          'fann_init_weights',
          'fann_length_train_data',
          'fann_merge_train_data',
          'fann_num_input_train_data',
          'fann_num_output_train_data',
          'fann_print_error',
          'fann_randomize_weights',
          'fann_read_train_from_file',
          'fann_reset_errno',
          'fann_reset_errstr',
          'fann_reset_MSE',
          'fann_run',
          'fann_save_train',
          'fann_save',
          'fann_scale_input_train_data',
          'fann_scale_input',
          'fann_scale_output_train_data',
          'fann_scale_output',
          'fann_scale_train_data',
          'fann_scale_train',
          'fann_set_activation_function_hidden',
          'fann_set_activation_function_layer',
          'fann_set_activation_function_output',
          'fann_set_activation_function',
          'fann_set_activation_steepness_hidden',
          'fann_set_activation_steepness_layer',
          'fann_set_activation_steepness_output',
          'fann_set_activation_steepness',
          'fann_set_bit_fail_limit',
          'fann_set_callback',
          'fann_set_cascade_activation_functions',
          'fann_set_cascade_activation_steepnesses',
          'fann_set_cascade_candidate_change_fraction',
          'fann_set_cascade_candidate_limit',
          'fann_set_cascade_candidate_stagnation_epochs',
          'fann_set_cascade_max_cand_epochs',
          'fann_set_cascade_max_out_epochs',
          'fann_set_cascade_min_cand_epochs',
          'fann_set_cascade_min_out_epochs',
          'fann_set_cascade_num_candidate_groups',
          'fann_set_cascade_output_change_fraction',
          'fann_set_cascade_output_stagnation_epochs',
          'fann_set_cascade_weight_multiplier',
          'fann_set_error_log',
          'fann_set_input_scaling_params',
          'fann_set_learning_momentum',
          'fann_set_learning_rate',
          'fann_set_output_scaling_params',
          'fann_set_quickprop_decay',
          'fann_set_quickprop_mu',
          'fann_set_rprop_decrease_factor',
          'fann_set_rprop_delta_max',
          'fann_set_rprop_delta_min',
          'fann_set_rprop_delta_zero',
          'fann_set_rprop_increase_factor',
          'fann_set_sarprop_step_error_shift',
          'fann_set_sarprop_step_error_threshold_factor',
          'fann_set_sarprop_temperature',
          'fann_set_sarprop_weight_decay_shift',
          'fann_set_scaling_params',
          'fann_set_train_error_function',
          'fann_set_train_stop_function',
          'fann_set_training_algorithm',
          'fann_set_weight_array',
          'fann_set_weight',
          'fann_shuffle_train_data',
          'fann_subset_train_data',
          'fann_test_data',
          'fann_test',
          'fann_train_epoch',
          'fann_train_on_data',
          'fann_train_on_file',
          'fann_train'),
 'Fileinfo': ('finfo_buffer',
              'finfo_close',
              'finfo_file',
              'finfo_open',
              'finfo_set_flags',
              'mime_content_type'),
 'Filesystem': ('basename',
                'chgrp',
                'chmod',
                'chown',
                'clearstatcache',
                'copy',
                'dirname',
                'disk_free_space',
                'disk_total_space',
                'diskfreespace',
                'fclose',
                'fdatasync',
                'feof',
                'fflush',
                'fgetc',
                'fgetcsv',
                'fgets',
                'fgetss',
                'file_exists',
                'file_get_contents',
                'file_put_contents',
                'file',
                'fileatime',
                'filectime',
                'filegroup',
                'fileinode',
                'filemtime',
                'fileowner',
                'fileperms',
                'filesize',
                'filetype',
                'flock',
                'fnmatch',
                'fopen',
                'fpassthru',
                'fputcsv',
                'fputs',
                'fread',
                'fscanf',
                'fseek',
                'fstat',
                'fsync',
                'ftell',
                'ftruncate',
                'fwrite',
                'glob',
                'is_dir',
                'is_executable',
                'is_file',
                'is_link',
                'is_readable',
                'is_uploaded_file',
                'is_writable',
                'is_writeable',
                'lchgrp',
                'lchown',
                'link',
                'linkinfo',
                'lstat',
                'mkdir',
                'move_uploaded_file',
                'parse_ini_file',
                'parse_ini_string',
                'pathinfo',
                'pclose',
                'popen',
                'readfile',
                'readlink',
                'realpath_cache_get',
                'realpath_cache_size',
                'realpath',
                'rename',
                'rewind',
                'rmdir',
                'set_file_buffer',
                'stat',
                'symlink',
                'tempnam',
                'tmpfile',
                'touch',
                'umask',
                'unlink'),
 'Filter': ('filter_has_var',
            'filter_id',
            'filter_input_array',
            'filter_input',
            'filter_list',
            'filter_var_array',
            'filter_var'),
 'Firebird/InterBase': ('fbird_add_user',
                        'fbird_affected_rows',
                        'fbird_backup',
                        'fbird_blob_add',
                        'fbird_blob_cancel',
                        'fbird_blob_close',
                        'fbird_blob_create',
                        'fbird_blob_echo',
                        'fbird_blob_get',
                        'fbird_blob_import',
                        'fbird_blob_info',
                        'fbird_blob_open',
                        'fbird_close',
                        'fbird_commit_ret',
                        'fbird_commit',
                        'fbird_connect',
                        'fbird_db_info',
                        'fbird_delete_user',
                        'fbird_drop_db',
                        'fbird_errcode',
                        'fbird_errmsg',
                        'fbird_execute',
                        'fbird_fetch_assoc',
                        'fbird_fetch_object',
                        'fbird_fetch_row',
                        'fbird_field_info',
                        'fbird_free_event_handler',
                        'fbird_free_query',
                        'fbird_free_result',
                        'fbird_gen_id',
                        'fbird_maintain_db',
                        'fbird_modify_user',
                        'fbird_name_result',
                        'fbird_num_fields',
                        'fbird_num_params',
                        'fbird_param_info',
                        'fbird_pconnect',
                        'fbird_prepare',
                        'fbird_query',
                        'fbird_restore',
                        'fbird_rollback_ret',
                        'fbird_rollback',
                        'fbird_server_info',
                        'fbird_service_attach',
                        'fbird_service_detach',
                        'fbird_set_event_handler',
                        'fbird_trans',
                        'fbird_wait_event',
                        'ibase_add_user',
                        'ibase_affected_rows',
                        'ibase_backup',
                        'ibase_blob_add',
                        'ibase_blob_cancel',
                        'ibase_blob_close',
                        'ibase_blob_create',
                        'ibase_blob_echo',
                        'ibase_blob_get',
                        'ibase_blob_import',
                        'ibase_blob_info',
                        'ibase_blob_open',
                        'ibase_close',
                        'ibase_commit_ret',
                        'ibase_commit',
                        'ibase_connect',
                        'ibase_db_info',
                        'ibase_delete_user',
                        'ibase_drop_db',
                        'ibase_errcode',
                        'ibase_errmsg',
                        'ibase_execute',
                        'ibase_fetch_assoc',
                        'ibase_fetch_object',
                        'ibase_fetch_row',
                        'ibase_field_info',
                        'ibase_free_event_handler',
                        'ibase_free_query',
                        'ibase_free_result',
                        'ibase_gen_id',
                        'ibase_maintain_db',
                        'ibase_modify_user',
                        'ibase_name_result',
                        'ibase_num_fields',
                        'ibase_num_params',
                        'ibase_param_info',
                        'ibase_pconnect',
                        'ibase_prepare',
                        'ibase_query',
                        'ibase_restore',
                        'ibase_rollback_ret',
                        'ibase_rollback',
                        'ibase_server_info',
                        'ibase_service_attach',
                        'ibase_service_detach',
                        'ibase_set_event_handler',
                        'ibase_trans',
                        'ibase_wait_event'),
 'Function handling': ('call_user_func_array',
                       'call_user_func',
                       'create_function',
                       'forward_static_call_array',
                       'forward_static_call',
                       'func_get_arg',
                       'func_get_args',
                       'func_num_args',
                       'function_exists',
                       'get_defined_functions',
                       'register_shutdown_function',
                       'register_tick_function',
                       'unregister_tick_function'),
 'GD and Image': ('gd_info',
                  'getimagesize',
                  'getimagesizefromstring',
                  'image_type_to_extension',
                  'image_type_to_mime_type',
                  'image2wbmp',
                  'imageaffine',
                  'imageaffinematrixconcat',
                  'imageaffinematrixget',
                  'imagealphablending',
                  'imageantialias',
                  'imagearc',
                  'imageavif',
                  'imagebmp',
                  'imagechar',
                  'imagecharup',
                  'imagecolorallocate',
                  'imagecolorallocatealpha',
                  'imagecolorat',
                  'imagecolorclosest',
                  'imagecolorclosestalpha',
                  'imagecolorclosesthwb',
                  'imagecolordeallocate',
                  'imagecolorexact',
                  'imagecolorexactalpha',
                  'imagecolormatch',
                  'imagecolorresolve',
                  'imagecolorresolvealpha',
                  'imagecolorset',
                  'imagecolorsforindex',
                  'imagecolorstotal',
                  'imagecolortransparent',
                  'imageconvolution',
                  'imagecopy',
                  'imagecopymerge',
                  'imagecopymergegray',
                  'imagecopyresampled',
                  'imagecopyresized',
                  'imagecreate',
                  'imagecreatefromavif',
                  'imagecreatefrombmp',
                  'imagecreatefromgd2',
                  'imagecreatefromgd2part',
                  'imagecreatefromgd',
                  'imagecreatefromgif',
                  'imagecreatefromjpeg',
                  'imagecreatefrompng',
                  'imagecreatefromstring',
                  'imagecreatefromtga',
                  'imagecreatefromwbmp',
                  'imagecreatefromwebp',
                  'imagecreatefromxbm',
                  'imagecreatefromxpm',
                  'imagecreatetruecolor',
                  'imagecrop',
                  'imagecropauto',
                  'imagedashedline',
                  'imagedestroy',
                  'imageellipse',
                  'imagefill',
                  'imagefilledarc',
                  'imagefilledellipse',
                  'imagefilledpolygon',
                  'imagefilledrectangle',
                  'imagefilltoborder',
                  'imagefilter',
                  'imageflip',
                  'imagefontheight',
                  'imagefontwidth',
                  'imageftbbox',
                  'imagefttext',
                  'imagegammacorrect',
                  'imagegd2',
                  'imagegd',
                  'imagegetclip',
                  'imagegetinterpolation',
                  'imagegif',
                  'imagegrabscreen',
                  'imagegrabwindow',
                  'imageinterlace',
                  'imageistruecolor',
                  'imagejpeg',
                  'imagelayereffect',
                  'imageline',
                  'imageloadfont',
                  'imageopenpolygon',
                  'imagepalettecopy',
                  'imagepalettetotruecolor',
                  'imagepng',
                  'imagepolygon',
                  'imagerectangle',
                  'imageresolution',
                  'imagerotate',
                  'imagesavealpha',
                  'imagescale',
                  'imagesetbrush',
                  'imagesetclip',
                  'imagesetinterpolation',
                  'imagesetpixel',
                  'imagesetstyle',
                  'imagesetthickness',
                  'imagesettile',
                  'imagestring',
                  'imagestringup',
                  'imagesx',
                  'imagesy',
                  'imagetruecolortopalette',
                  'imagettfbbox',
                  'imagettftext',
                  'imagetypes',
                  'imagewbmp',
                  'imagewebp',
                  'imagexbm',
                  'iptcembed',
                  'iptcparse',
                  'jpeg2wbmp',
                  'png2wbmp'),
 'GMP': ('gmp_abs',
         'gmp_add',
         'gmp_and',
         'gmp_binomial',
         'gmp_clrbit',
         'gmp_cmp',
         'gmp_com',
         'gmp_div_q',
         'gmp_div_qr',
         'gmp_div_r',
         'gmp_div',
         'gmp_divexact',
         'gmp_export',
         'gmp_fact',
         'gmp_gcd',
         'gmp_gcdext',
         'gmp_hamdist',
         'gmp_import',
         'gmp_init',
         'gmp_intval',
         'gmp_invert',
         'gmp_jacobi',
         'gmp_kronecker',
         'gmp_lcm',
         'gmp_legendre',
         'gmp_mod',
         'gmp_mul',
         'gmp_neg',
         'gmp_nextprime',
         'gmp_or',
         'gmp_perfect_power',
         'gmp_perfect_square',
         'gmp_popcount',
         'gmp_pow',
         'gmp_powm',
         'gmp_prob_prime',
         'gmp_random_bits',
         'gmp_random_range',
         'gmp_random_seed',
         'gmp_random',
         'gmp_root',
         'gmp_rootrem',
         'gmp_scan0',
         'gmp_scan1',
         'gmp_setbit',
         'gmp_sign',
         'gmp_sqrt',
         'gmp_sqrtrem',
         'gmp_strval',
         'gmp_sub',
         'gmp_testbit',
         'gmp_xor'),
 'GeoIP': ('geoip_asnum_by_name',
           'geoip_continent_code_by_name',
           'geoip_country_code_by_name',
           'geoip_country_code3_by_name',
           'geoip_country_name_by_name',
           'geoip_database_info',
           'geoip_db_avail',
           'geoip_db_filename',
           'geoip_db_get_all_info',
           'geoip_domain_by_name',
           'geoip_id_by_name',
           'geoip_isp_by_name',
           'geoip_netspeedcell_by_name',
           'geoip_org_by_name',
           'geoip_record_by_name',
           'geoip_region_by_name',
           'geoip_region_name_by_code',
           'geoip_setup_custom_directory',
           'geoip_time_zone_by_country_and_region'),
 'Gettext': ('bind_textdomain_codeset',
             'bindtextdomain',
             'dcgettext',
             'dcngettext',
             'dgettext',
             'dngettext',
             'gettext',
             'ngettext',
             'textdomain'),
 'GnuPG': ('gnupg_adddecryptkey',
           'gnupg_addencryptkey',
           'gnupg_addsignkey',
           'gnupg_cleardecryptkeys',
           'gnupg_clearencryptkeys',
           'gnupg_clearsignkeys',
           'gnupg_decrypt',
           'gnupg_decryptverify',
           'gnupg_encrypt',
           'gnupg_encryptsign',
           'gnupg_export',
           'gnupg_getengineinfo',
           'gnupg_geterror',
           'gnupg_geterrorinfo',
           'gnupg_getprotocol',
           'gnupg_import',
           'gnupg_init',
           'gnupg_keyinfo',
           'gnupg_setarmor',
           'gnupg_seterrormode',
           'gnupg_setsignmode',
           'gnupg_sign',
           'gnupg_verify'),
 'Grapheme': ('grapheme_extract',
              'grapheme_stripos',
              'grapheme_stristr',
              'grapheme_strlen',
              'grapheme_strpos',
              'grapheme_strripos',
              'grapheme_strrpos',
              'grapheme_strstr',
              'grapheme_substr'),
 'Hash': ('hash_algos',
          'hash_copy',
          'hash_equals',
          'hash_file',
          'hash_final',
          'hash_hkdf',
          'hash_hmac_algos',
          'hash_hmac_file',
          'hash_hmac',
          'hash_init',
          'hash_pbkdf2',
          'hash_update_file',
          'hash_update_stream',
          'hash_update',
          'hash'),
 'IBM DB2': ('db2_autocommit',
             'db2_bind_param',
             'db2_client_info',
             'db2_close',
             'db2_column_privileges',
             'db2_columns',
             'db2_commit',
             'db2_conn_error',
             'db2_conn_errormsg',
             'db2_connect',
             'db2_cursor_type',
             'db2_escape_string',
             'db2_exec',
             'db2_execute',
             'db2_fetch_array',
             'db2_fetch_assoc',
             'db2_fetch_both',
             'db2_fetch_object',
             'db2_fetch_row',
             'db2_field_display_size',
             'db2_field_name',
             'db2_field_num',
             'db2_field_precision',
             'db2_field_scale',
             'db2_field_type',
             'db2_field_width',
             'db2_foreign_keys',
             'db2_free_result',
             'db2_free_stmt',
             'db2_get_option',
             'db2_last_insert_id',
             'db2_lob_read',
             'db2_next_result',
             'db2_num_fields',
             'db2_num_rows',
             'db2_pclose',
             'db2_pconnect',
             'db2_prepare',
             'db2_primary_keys',
             'db2_procedure_columns',
             'db2_procedures',
             'db2_result',
             'db2_rollback',
             'db2_server_info',
             'db2_set_option',
             'db2_special_columns',
             'db2_statistics',
             'db2_stmt_error',
             'db2_stmt_errormsg',
             'db2_table_privileges',
             'db2_tables'),
 'IDN': ('idn_to_ascii', 'idn_to_utf8'),
 'IMAP': ('imap_8bit',
          'imap_alerts',
          'imap_append',
          'imap_base64',
          'imap_binary',
          'imap_body',
          'imap_bodystruct',
          'imap_check',
          'imap_clearflag_full',
          'imap_close',
          'imap_create',
          'imap_createmailbox',
          'imap_delete',
          'imap_deletemailbox',
          'imap_errors',
          'imap_expunge',
          'imap_fetch_overview',
          'imap_fetchbody',
          'imap_fetchheader',
          'imap_fetchmime',
          'imap_fetchstructure',
          'imap_fetchtext',
          'imap_gc',
          'imap_get_quota',
          'imap_get_quotaroot',
          'imap_getacl',
          'imap_getmailboxes',
          'imap_getsubscribed',
          'imap_header',
          'imap_headerinfo',
          'imap_headers',
          'imap_last_error',
          'imap_list',
          'imap_listmailbox',
          'imap_listscan',
          'imap_listsubscribed',
          'imap_lsub',
          'imap_mail_compose',
          'imap_mail_copy',
          'imap_mail_move',
          'imap_mail',
          'imap_mailboxmsginfo',
          'imap_mime_header_decode',
          'imap_msgno',
          'imap_mutf7_to_utf8',
          'imap_num_msg',
          'imap_num_recent',
          'imap_open',
          'imap_ping',
          'imap_qprint',
          'imap_rename',
          'imap_renamemailbox',
          'imap_reopen',
          'imap_rfc822_parse_adrlist',
          'imap_rfc822_parse_headers',
          'imap_rfc822_write_address',
          'imap_savebody',
          'imap_scan',
          'imap_scanmailbox',
          'imap_search',
          'imap_set_quota',
          'imap_setacl',
          'imap_setflag_full',
          'imap_sort',
          'imap_status',
          'imap_subscribe',
          'imap_thread',
          'imap_timeout',
          'imap_uid',
          'imap_undelete',
          'imap_unsubscribe',
          'imap_utf7_decode',
          'imap_utf7_encode',
          'imap_utf8_to_mutf7',
          'imap_utf8'),
 'Igbinary': ('igbinary_serialize', 'igbinary_unserialize'),
 'Inotify': ('inotify_add_watch',
             'inotify_init',
             'inotify_queue_len',
             'inotify_read',
             'inotify_rm_watch'),
 'JSON': ('json_decode',
          'json_encode',
          'json_last_error_msg',
          'json_last_error'),
 'LDAP': ('ldap_8859_to_t61',
          'ldap_add_ext',
          'ldap_add',
          'ldap_bind_ext',
          'ldap_bind',
          'ldap_close',
          'ldap_compare',
          'ldap_connect',
          'ldap_control_paged_result_response',
          'ldap_control_paged_result',
          'ldap_count_entries',
          'ldap_count_references',
          'ldap_delete_ext',
          'ldap_delete',
          'ldap_dn2ufn',
          'ldap_err2str',
          'ldap_errno',
          'ldap_error',
          'ldap_escape',
          'ldap_exop_passwd',
          'ldap_exop_refresh',
          'ldap_exop_whoami',
          'ldap_exop',
          'ldap_explode_dn',
          'ldap_first_attribute',
          'ldap_first_entry',
          'ldap_first_reference',
          'ldap_free_result',
          'ldap_get_attributes',
          'ldap_get_dn',
          'ldap_get_entries',
          'ldap_get_option',
          'ldap_get_values_len',
          'ldap_get_values',
          'ldap_list',
          'ldap_mod_add_ext',
          'ldap_mod_add',
          'ldap_mod_del_ext',
          'ldap_mod_del',
          'ldap_mod_replace_ext',
          'ldap_mod_replace',
          'ldap_modify_batch',
          'ldap_modify',
          'ldap_next_attribute',
          'ldap_next_entry',
          'ldap_next_reference',
          'ldap_parse_exop',
          'ldap_parse_reference',
          'ldap_parse_result',
          'ldap_read',
          'ldap_rename_ext',
          'ldap_rename',
          'ldap_sasl_bind',
          'ldap_search',
          'ldap_set_option',
          'ldap_set_rebind_proc',
          'ldap_sort',
          'ldap_start_tls',
          'ldap_t61_to_8859',
          'ldap_unbind'),
 'LZF': ('lzf_compress', 'lzf_decompress', 'lzf_optimized_for'),
 'Mail': ('ezmlm_hash', 'mail'),
 'Mailparse': ('mailparse_determine_best_xfer_encoding',
               'mailparse_msg_create',
               'mailparse_msg_extract_part_file',
               'mailparse_msg_extract_part',
               'mailparse_msg_extract_whole_part_file',
               'mailparse_msg_free',
               'mailparse_msg_get_part_data',
               'mailparse_msg_get_part',
               'mailparse_msg_get_structure',
               'mailparse_msg_parse_file',
               'mailparse_msg_parse',
               'mailparse_rfc822_parse_addresses',
               'mailparse_stream_encode',
               'mailparse_uudecode_all'),
 'Math': ('abs',
          'acos',
          'acosh',
          'asin',
          'asinh',
          'atan2',
          'atan',
          'atanh',
          'base_convert',
          'bindec',
          'ceil',
          'cos',
          'cosh',
          'decbin',
          'dechex',
          'decoct',
          'deg2rad',
          'exp',
          'expm1',
          'fdiv',
          'floor',
          'fmod',
          'getrandmax',
          'hexdec',
          'hypot',
          'intdiv',
          'is_finite',
          'is_infinite',
          'is_nan',
          'lcg_value',
          'log10',
          'log1p',
          'log',
          'max',
          'min',
          'mt_getrandmax',
          'mt_rand',
          'mt_srand',
          'octdec',
          'pi',
          'pow',
          'rad2deg',
          'rand',
          'round',
          'sin',
          'sinh',
          'sqrt',
          'srand',
          'tan',
          'tanh'),
 'Mcrypt': ('mcrypt_create_iv',
            'mcrypt_decrypt',
            'mcrypt_enc_get_algorithms_name',
            'mcrypt_enc_get_block_size',
            'mcrypt_enc_get_iv_size',
            'mcrypt_enc_get_key_size',
            'mcrypt_enc_get_modes_name',
            'mcrypt_enc_get_supported_key_sizes',
            'mcrypt_enc_is_block_algorithm_mode',
            'mcrypt_enc_is_block_algorithm',
            'mcrypt_enc_is_block_mode',
            'mcrypt_enc_self_test',
            'mcrypt_encrypt',
            'mcrypt_generic_deinit',
            'mcrypt_generic_init',
            'mcrypt_generic',
            'mcrypt_get_block_size',
            'mcrypt_get_cipher_name',
            'mcrypt_get_iv_size',
            'mcrypt_get_key_size',
            'mcrypt_list_algorithms',
            'mcrypt_list_modes',
            'mcrypt_module_close',
            'mcrypt_module_get_algo_block_size',
            'mcrypt_module_get_algo_key_size',
            'mcrypt_module_get_supported_key_sizes',
            'mcrypt_module_is_block_algorithm_mode',
            'mcrypt_module_is_block_algorithm',
            'mcrypt_module_is_block_mode',
            'mcrypt_module_open',
            'mcrypt_module_self_test',
            'mdecrypt_generic'),
 'Memcache': ('memcache_debug',),
 'Mhash': ('mhash_count',
           'mhash_get_block_size',
           'mhash_get_hash_name',
           'mhash_keygen_s2k',
           'mhash'),
 'Misc.': ('connection_aborted',
           'connection_status',
           'constant',
           'define',
           'defined',
           'die',
           'eval',
           'exit',
           'get_browser',
           '__halt_compiler',
           'highlight_file',
           'highlight_string',
           'hrtime',
           'ignore_user_abort',
           'pack',
           'php_strip_whitespace',
           'sapi_windows_cp_conv',
           'sapi_windows_cp_get',
           'sapi_windows_cp_is_utf8',
           'sapi_windows_cp_set',
           'sapi_windows_generate_ctrl_event',
           'sapi_windows_set_ctrl_handler',
           'sapi_windows_vt100_support',
           'show_source',
           'sleep',
           'sys_getloadavg',
           'time_nanosleep',
           'time_sleep_until',
           'uniqid',
           'unpack',
           'usleep'),
 'Multibyte String': ('mb_check_encoding',
                      'mb_chr',
                      'mb_convert_case',
                      'mb_convert_encoding',
                      'mb_convert_kana',
                      'mb_convert_variables',
                      'mb_decode_mimeheader',
                      'mb_decode_numericentity',
                      'mb_detect_encoding',
                      'mb_detect_order',
                      'mb_encode_mimeheader',
                      'mb_encode_numericentity',
                      'mb_encoding_aliases',
                      'mb_ereg_match',
                      'mb_ereg_replace_callback',
                      'mb_ereg_replace',
                      'mb_ereg_search_getpos',
                      'mb_ereg_search_getregs',
                      'mb_ereg_search_init',
                      'mb_ereg_search_pos',
                      'mb_ereg_search_regs',
                      'mb_ereg_search_setpos',
                      'mb_ereg_search',
                      'mb_ereg',
                      'mb_eregi_replace',
                      'mb_eregi',
                      'mb_get_info',
                      'mb_http_input',
                      'mb_http_output',
                      'mb_internal_encoding',
                      'mb_language',
                      'mb_list_encodings',
                      'mb_ord',
                      'mb_output_handler',
                      'mb_parse_str',
                      'mb_preferred_mime_name',
                      'mb_regex_encoding',
                      'mb_regex_set_options',
                      'mb_scrub',
                      'mb_send_mail',
                      'mb_split',
                      'mb_str_split',
                      'mb_strcut',
                      'mb_strimwidth',
                      'mb_stripos',
                      'mb_stristr',
                      'mb_strlen',
                      'mb_strpos',
                      'mb_strrchr',
                      'mb_strrichr',
                      'mb_strripos',
                      'mb_strrpos',
                      'mb_strstr',
                      'mb_strtolower',
                      'mb_strtoupper',
                      'mb_strwidth',
                      'mb_substitute_character',
                      'mb_substr_count',
                      'mb_substr'),
 'MySQL': ('mysql_affected_rows',
           'mysql_client_encoding',
           'mysql_close',
           'mysql_connect',
           'mysql_create_db',
           'mysql_data_seek',
           'mysql_db_name',
           'mysql_db_query',
           'mysql_drop_db',
           'mysql_errno',
           'mysql_error',
           'mysql_escape_string',
           'mysql_fetch_array',
           'mysql_fetch_assoc',
           'mysql_fetch_field',
           'mysql_fetch_lengths',
           'mysql_fetch_object',
           'mysql_fetch_row',
           'mysql_field_flags',
           'mysql_field_len',
           'mysql_field_name',
           'mysql_field_seek',
           'mysql_field_table',
           'mysql_field_type',
           'mysql_free_result',
           'mysql_get_client_info',
           'mysql_get_host_info',
           'mysql_get_proto_info',
           'mysql_get_server_info',
           'mysql_info',
           'mysql_insert_id',
           'mysql_list_dbs',
           'mysql_list_fields',
           'mysql_list_processes',
           'mysql_list_tables',
           'mysql_num_fields',
           'mysql_num_rows',
           'mysql_pconnect',
           'mysql_ping',
           'mysql_query',
           'mysql_real_escape_string',
           'mysql_result',
           'mysql_select_db',
           'mysql_set_charset',
           'mysql_stat',
           'mysql_tablename',
           'mysql_thread_id',
           'mysql_unbuffered_query'),
 'Mysql_xdevapi': ('expression', 'getSession'),
 'Network': ('checkdnsrr',
             'closelog',
             'dns_check_record',
             'dns_get_mx',
             'dns_get_record',
             'fsockopen',
             'gethostbyaddr',
             'gethostbyname',
             'gethostbynamel',
             'gethostname',
             'getmxrr',
             'getprotobyname',
             'getprotobynumber',
             'getservbyname',
             'getservbyport',
             'header_register_callback',
             'header_remove',
             'header',
             'headers_list',
             'headers_sent',
             'http_response_code',
             'inet_ntop',
             'inet_pton',
             'ip2long',
             'long2ip',
             'net_get_interfaces',
             'openlog',
             'pfsockopen',
             'setcookie',
             'setrawcookie',
             'socket_get_status',
             'socket_set_blocking',
             'socket_set_timeout',
             'syslog'),
 'OAuth': ('oauth_get_sbs', 'oauth_urlencode'),
 'OCI8': ('oci_bind_array_by_name',
          'oci_bind_by_name',
          'oci_cancel',
          'oci_client_version',
          'oci_close',
          'oci_commit',
          'oci_connect',
          'oci_define_by_name',
          'oci_error',
          'oci_execute',
          'oci_fetch_all',
          'oci_fetch_array',
          'oci_fetch_assoc',
          'oci_fetch_object',
          'oci_fetch_row',
          'oci_fetch',
          'oci_field_is_null',
          'oci_field_name',
          'oci_field_precision',
          'oci_field_scale',
          'oci_field_size',
          'oci_field_type_raw',
          'oci_field_type',
          'oci_free_descriptor',
          'oci_free_statement',
          'oci_get_implicit_resultset',
          'oci_lob_copy',
          'oci_lob_is_equal',
          'oci_new_collection',
          'oci_new_connect',
          'oci_new_cursor',
          'oci_new_descriptor',
          'oci_num_fields',
          'oci_num_rows',
          'oci_parse',
          'oci_password_change',
          'oci_pconnect',
          'oci_register_taf_callback',
          'oci_result',
          'oci_rollback',
          'oci_server_version',
          'oci_set_action',
          'oci_set_call_timeout',
          'oci_set_client_identifier',
          'oci_set_client_info',
          'oci_set_db_operation',
          'oci_set_edition',
          'oci_set_module_name',
          'oci_set_prefetch_lob',
          'oci_set_prefetch',
          'oci_statement_type',
          'oci_unregister_taf_callback'),
 'ODBC': ('odbc_autocommit',
          'odbc_binmode',
          'odbc_close_all',
          'odbc_close',
          'odbc_columnprivileges',
          'odbc_columns',
          'odbc_commit',
          'odbc_connect',
          'odbc_cursor',
          'odbc_data_source',
          'odbc_do',
          'odbc_error',
          'odbc_errormsg',
          'odbc_exec',
          'odbc_execute',
          'odbc_fetch_array',
          'odbc_fetch_into',
          'odbc_fetch_object',
          'odbc_fetch_row',
          'odbc_field_len',
          'odbc_field_name',
          'odbc_field_num',
          'odbc_field_precision',
          'odbc_field_scale',
          'odbc_field_type',
          'odbc_foreignkeys',
          'odbc_free_result',
          'odbc_gettypeinfo',
          'odbc_longreadlen',
          'odbc_next_result',
          'odbc_num_fields',
          'odbc_num_rows',
          'odbc_pconnect',
          'odbc_prepare',
          'odbc_primarykeys',
          'odbc_procedurecolumns',
          'odbc_procedures',
          'odbc_result_all',
          'odbc_result',
          'odbc_rollback',
          'odbc_setoption',
          'odbc_specialcolumns',
          'odbc_statistics',
          'odbc_tableprivileges',
          'odbc_tables'),
 'OPcache': ('opcache_compile_file',
             'opcache_get_configuration',
             'opcache_get_status',
             'opcache_invalidate',
             'opcache_is_script_cached',
             'opcache_reset'),
 'OpenAL': ('openal_buffer_create',
            'openal_buffer_data',
            'openal_buffer_destroy',
            'openal_buffer_get',
            'openal_buffer_loadwav',
            'openal_context_create',
            'openal_context_current',
            'openal_context_destroy',
            'openal_context_process',
            'openal_context_suspend',
            'openal_device_close',
            'openal_device_open',
            'openal_listener_get',
            'openal_listener_set',
            'openal_source_create',
            'openal_source_destroy',
            'openal_source_get',
            'openal_source_pause',
            'openal_source_play',
            'openal_source_rewind',
            'openal_source_set',
            'openal_source_stop',
            'openal_stream'),
 'OpenSSL': ('openssl_cipher_iv_length',
             'openssl_cms_decrypt',
             'openssl_cms_encrypt',
             'openssl_cms_read',
             'openssl_cms_sign',
             'openssl_cms_verify',
             'openssl_csr_export_to_file',
             'openssl_csr_export',
             'openssl_csr_get_public_key',
             'openssl_csr_get_subject',
             'openssl_csr_new',
             'openssl_csr_sign',
             'openssl_decrypt',
             'openssl_dh_compute_key',
             'openssl_digest',
             'openssl_encrypt',
             'openssl_error_string',
             'openssl_free_key',
             'openssl_get_cert_locations',
             'openssl_get_cipher_methods',
             'openssl_get_curve_names',
             'openssl_get_md_methods',
             'openssl_get_privatekey',
             'openssl_get_publickey',
             'openssl_open',
             'openssl_pbkdf2',
             'openssl_pkcs12_export_to_file',
             'openssl_pkcs12_export',
             'openssl_pkcs12_read',
             'openssl_pkcs7_decrypt',
             'openssl_pkcs7_encrypt',
             'openssl_pkcs7_read',
             'openssl_pkcs7_sign',
             'openssl_pkcs7_verify',
             'openssl_pkey_derive',
             'openssl_pkey_export_to_file',
             'openssl_pkey_export',
             'openssl_pkey_free',
             'openssl_pkey_get_details',
             'openssl_pkey_get_private',
             'openssl_pkey_get_public',
             'openssl_pkey_new',
             'openssl_private_decrypt',
             'openssl_private_encrypt',
             'openssl_public_decrypt',
             'openssl_public_encrypt',
             'openssl_random_pseudo_bytes',
             'openssl_seal',
             'openssl_sign',
             'openssl_spki_export_challenge',
             'openssl_spki_export',
             'openssl_spki_new',
             'openssl_spki_verify',
             'openssl_verify',
             'openssl_x509_check_private_key',
             'openssl_x509_checkpurpose',
             'openssl_x509_export_to_file',
             'openssl_x509_export',
             'openssl_x509_fingerprint',
             'openssl_x509_free',
             'openssl_x509_parse',
             'openssl_x509_read',
             'openssl_x509_verify'),
 'Output Control': ('flush',
                    'ob_clean',
                    'ob_end_clean',
                    'ob_end_flush',
                    'ob_flush',
                    'ob_get_clean',
                    'ob_get_contents',
                    'ob_get_flush',
                    'ob_get_length',
                    'ob_get_level',
                    'ob_get_status',
                    'ob_gzhandler',
                    'ob_implicit_flush',
                    'ob_list_handlers',
                    'ob_start',
                    'output_add_rewrite_var',
                    'output_reset_rewrite_vars'),
 'PCNTL': ('pcntl_alarm',
           'pcntl_async_signals',
           'pcntl_errno',
           'pcntl_exec',
           'pcntl_fork',
           'pcntl_get_last_error',
           'pcntl_getpriority',
           'pcntl_setpriority',
           'pcntl_signal_dispatch',
           'pcntl_signal_get_handler',
           'pcntl_signal',
           'pcntl_sigprocmask',
           'pcntl_sigtimedwait',
           'pcntl_sigwaitinfo',
           'pcntl_strerror',
           'pcntl_wait',
           'pcntl_waitpid',
           'pcntl_wexitstatus',
           'pcntl_wifexited',
           'pcntl_wifsignaled',
           'pcntl_wifstopped',
           'pcntl_wstopsig',
           'pcntl_wtermsig'),
 'PCRE': ('preg_filter',
          'preg_grep',
          'preg_last_error_msg',
          'preg_last_error',
          'preg_match_all',
          'preg_match',
          'preg_quote',
          'preg_replace_callback_array',
          'preg_replace_callback',
          'preg_replace',
          'preg_split'),
 'PHP Options/Info': ('assert_options',
                      'assert',
                      'cli_get_process_title',
                      'cli_set_process_title',
                      'dl',
                      'extension_loaded',
                      'gc_collect_cycles',
                      'gc_disable',
                      'gc_enable',
                      'gc_enabled',
                      'gc_mem_caches',
                      'gc_status',
                      'get_cfg_var',
                      'get_current_user',
                      'get_defined_constants',
                      'get_extension_funcs',
                      'get_include_path',
                      'get_included_files',
                      'get_loaded_extensions',
                      'get_magic_quotes_gpc',
                      'get_magic_quotes_runtime',
                      'get_required_files',
                      'get_resources',
                      'getenv',
                      'getlastmod',
                      'getmygid',
                      'getmyinode',
                      'getmypid',
                      'getmyuid',
                      'getopt',
                      'getrusage',
                      'ini_alter',
                      'ini_get_all',
                      'ini_get',
                      'ini_restore',
                      'ini_set',
                      'memory_get_peak_usage',
                      'memory_get_usage',
                      'php_ini_loaded_file',
                      'php_ini_scanned_files',
                      'php_sapi_name',
                      'php_uname',
                      'phpcredits',
                      'phpinfo',
                      'phpversion',
                      'putenv',
                      'restore_include_path',
                      'set_include_path',
                      'set_time_limit',
                      'sys_get_temp_dir',
                      'version_compare',
                      'zend_thread_id',
                      'zend_version'),
 'POSIX': ('posix_access',
           'posix_ctermid',
           'posix_errno',
           'posix_get_last_error',
           'posix_getcwd',
           'posix_getegid',
           'posix_geteuid',
           'posix_getgid',
           'posix_getgrgid',
           'posix_getgrnam',
           'posix_getgroups',
           'posix_getlogin',
           'posix_getpgid',
           'posix_getpgrp',
           'posix_getpid',
           'posix_getppid',
           'posix_getpwnam',
           'posix_getpwuid',
           'posix_getrlimit',
           'posix_getsid',
           'posix_getuid',
           'posix_initgroups',
           'posix_isatty',
           'posix_kill',
           'posix_mkfifo',
           'posix_mknod',
           'posix_setegid',
           'posix_seteuid',
           'posix_setgid',
           'posix_setpgid',
           'posix_setrlimit',
           'posix_setsid',
           'posix_setuid',
           'posix_strerror',
           'posix_times',
           'posix_ttyname',
           'posix_uname'),
 'PS': ('ps_add_bookmark',
        'ps_add_launchlink',
        'ps_add_locallink',
        'ps_add_note',
        'ps_add_pdflink',
        'ps_add_weblink',
        'ps_arc',
        'ps_arcn',
        'ps_begin_page',
        'ps_begin_pattern',
        'ps_begin_template',
        'ps_circle',
        'ps_clip',
        'ps_close_image',
        'ps_close',
        'ps_closepath_stroke',
        'ps_closepath',
        'ps_continue_text',
        'ps_curveto',
        'ps_delete',
        'ps_end_page',
        'ps_end_pattern',
        'ps_end_template',
        'ps_fill_stroke',
        'ps_fill',
        'ps_findfont',
        'ps_get_buffer',
        'ps_get_parameter',
        'ps_get_value',
        'ps_hyphenate',
        'ps_include_file',
        'ps_lineto',
        'ps_makespotcolor',
        'ps_moveto',
        'ps_new',
        'ps_open_file',
        'ps_open_image_file',
        'ps_open_image',
        'ps_open_memory_image',
        'ps_place_image',
        'ps_rect',
        'ps_restore',
        'ps_rotate',
        'ps_save',
        'ps_scale',
        'ps_set_border_color',
        'ps_set_border_dash',
        'ps_set_border_style',
        'ps_set_info',
        'ps_set_parameter',
        'ps_set_text_pos',
        'ps_set_value',
        'ps_setcolor',
        'ps_setdash',
        'ps_setflat',
        'ps_setfont',
        'ps_setgray',
        'ps_setlinecap',
        'ps_setlinejoin',
        'ps_setlinewidth',
        'ps_setmiterlimit',
        'ps_setoverprintmode',
        'ps_setpolydash',
        'ps_shading_pattern',
        'ps_shading',
        'ps_shfill',
        'ps_show_boxed',
        'ps_show_xy2',
        'ps_show_xy',
        'ps_show2',
        'ps_show',
        'ps_string_geometry',
        'ps_stringwidth',
        'ps_stroke',
        'ps_symbol_name',
        'ps_symbol_width',
        'ps_symbol',
        'ps_translate'),
 'Password Hashing': ('password_algos',
                      'password_get_info',
                      'password_hash',
                      'password_needs_rehash',
                      'password_verify'),
 'PostgreSQL': ('pg_affected_rows',
                'pg_cancel_query',
                'pg_client_encoding',
                'pg_close',
                'pg_connect_poll',
                'pg_connect',
                'pg_connection_busy',
                'pg_connection_reset',
                'pg_connection_status',
                'pg_consume_input',
                'pg_convert',
                'pg_copy_from',
                'pg_copy_to',
                'pg_dbname',
                'pg_delete',
                'pg_end_copy',
                'pg_escape_bytea',
                'pg_escape_identifier',
                'pg_escape_literal',
                'pg_escape_string',
                'pg_execute',
                'pg_fetch_all_columns',
                'pg_fetch_all',
                'pg_fetch_array',
                'pg_fetch_assoc',
                'pg_fetch_object',
                'pg_fetch_result',
                'pg_fetch_row',
                'pg_field_is_null',
                'pg_field_name',
                'pg_field_num',
                'pg_field_prtlen',
                'pg_field_size',
                'pg_field_table',
                'pg_field_type_oid',
                'pg_field_type',
                'pg_flush',
                'pg_free_result',
                'pg_get_notify',
                'pg_get_pid',
                'pg_get_result',
                'pg_host',
                'pg_insert',
                'pg_last_error',
                'pg_last_notice',
                'pg_last_oid',
                'pg_lo_close',
                'pg_lo_create',
                'pg_lo_export',
                'pg_lo_import',
                'pg_lo_open',
                'pg_lo_read_all',
                'pg_lo_read',
                'pg_lo_seek',
                'pg_lo_tell',
                'pg_lo_truncate',
                'pg_lo_unlink',
                'pg_lo_write',
                'pg_meta_data',
                'pg_num_fields',
                'pg_num_rows',
                'pg_options',
                'pg_parameter_status',
                'pg_pconnect',
                'pg_ping',
                'pg_port',
                'pg_prepare',
                'pg_put_line',
                'pg_query_params',
                'pg_query',
                'pg_result_error_field',
                'pg_result_error',
                'pg_result_seek',
                'pg_result_status',
                'pg_select',
                'pg_send_execute',
                'pg_send_prepare',
                'pg_send_query_params',
                'pg_send_query',
                'pg_set_client_encoding',
                'pg_set_error_verbosity',
                'pg_socket',
                'pg_trace',
                'pg_transaction_status',
                'pg_tty',
                'pg_unescape_bytea',
                'pg_untrace',
                'pg_update',
                'pg_version'),
 'Program execution': ('escapeshellarg',
                       'escapeshellcmd',
                       'exec',
                       'passthru',
                       'proc_close',
                       'proc_get_status',
                       'proc_nice',
                       'proc_open',
                       'proc_terminate',
                       'shell_exec',
                       'system'),
 'Pspell': ('pspell_add_to_personal',
            'pspell_add_to_session',
            'pspell_check',
            'pspell_clear_session',
            'pspell_config_create',
            'pspell_config_data_dir',
            'pspell_config_dict_dir',
            'pspell_config_ignore',
            'pspell_config_mode',
            'pspell_config_personal',
            'pspell_config_repl',
            'pspell_config_runtogether',
            'pspell_config_save_repl',
            'pspell_new_config',
            'pspell_new_personal',
            'pspell_new',
            'pspell_save_wordlist',
            'pspell_store_replacement',
            'pspell_suggest'),
 'RRD': ('rrd_create',
         'rrd_error',
         'rrd_fetch',
         'rrd_first',
         'rrd_graph',
         'rrd_info',
         'rrd_last',
         'rrd_lastupdate',
         'rrd_restore',
         'rrd_tune',
         'rrd_update',
         'rrd_version',
         'rrd_xport',
         'rrdc_disconnect'),
 'Radius': ('radius_acct_open',
            'radius_add_server',
            'radius_auth_open',
            'radius_close',
            'radius_config',
            'radius_create_request',
            'radius_cvt_addr',
            'radius_cvt_int',
            'radius_cvt_string',
            'radius_demangle_mppe_key',
            'radius_demangle',
            'radius_get_attr',
            'radius_get_tagged_attr_data',
            'radius_get_tagged_attr_tag',
            'radius_get_vendor_attr',
            'radius_put_addr',
            'radius_put_attr',
            'radius_put_int',
            'radius_put_string',
            'radius_put_vendor_addr',
            'radius_put_vendor_attr',
            'radius_put_vendor_int',
            'radius_put_vendor_string',
            'radius_request_authenticator',
            'radius_salt_encrypt_attr',
            'radius_send_request',
            'radius_server_secret',
            'radius_strerror'),
 'Rar': ('rar_wrapper_cache_stats',),
 'Readline': ('readline_add_history',
              'readline_callback_handler_install',
              'readline_callback_handler_remove',
              'readline_callback_read_char',
              'readline_clear_history',
              'readline_completion_function',
              'readline_info',
              'readline_list_history',
              'readline_on_new_line',
              'readline_read_history',
              'readline_redisplay',
              'readline_write_history',
              'readline'),
 'Recode': ('recode_file', 'recode_string', 'recode'),
 'RpmInfo': ('rpmaddtag', 'rpmdbinfo', 'rpmdbsearch', 'rpminfo', 'rpmvercmp'),
 'SNMP': ('snmp_get_quick_print',
          'snmp_get_valueretrieval',
          'snmp_read_mib',
          'snmp_set_enum_print',
          'snmp_set_oid_numeric_print',
          'snmp_set_oid_output_format',
          'snmp_set_quick_print',
          'snmp_set_valueretrieval',
          'snmp2_get',
          'snmp2_getnext',
          'snmp2_real_walk',
          'snmp2_set',
          'snmp2_walk',
          'snmp3_get',
          'snmp3_getnext',
          'snmp3_real_walk',
          'snmp3_set',
          'snmp3_walk',
          'snmpget',
          'snmpgetnext',
          'snmprealwalk',
          'snmpset',
          'snmpwalk',
          'snmpwalkoid'),
 'SOAP': ('is_soap_fault', 'use_soap_error_handler'),
 'SPL': ('class_implements',
         'class_parents',
         'class_uses',
         'iterator_apply',
         'iterator_count',
         'iterator_to_array',
         'spl_autoload_call',
         'spl_autoload_extensions',
         'spl_autoload_functions',
         'spl_autoload_register',
         'spl_autoload_unregister',
         'spl_autoload',
         'spl_classes',
         'spl_object_hash',
         'spl_object_id'),
 'SQLSRV': ('sqlsrv_begin_transaction',
            'sqlsrv_cancel',
            'sqlsrv_client_info',
            'sqlsrv_close',
            'sqlsrv_commit',
            'sqlsrv_configure',
            'sqlsrv_connect',
            'sqlsrv_errors',
            'sqlsrv_execute',
            'sqlsrv_fetch_array',
            'sqlsrv_fetch_object',
            'sqlsrv_fetch',
            'sqlsrv_field_metadata',
            'sqlsrv_free_stmt',
            'sqlsrv_get_config',
            'sqlsrv_get_field',
            'sqlsrv_has_rows',
            'sqlsrv_next_result',
            'sqlsrv_num_fields',
            'sqlsrv_num_rows',
            'sqlsrv_prepare',
            'sqlsrv_query',
            'sqlsrv_rollback',
            'sqlsrv_rows_affected',
            'sqlsrv_send_stream_data',
            'sqlsrv_server_info'),
 'SSH2': ('ssh2_auth_agent',
          'ssh2_auth_hostbased_file',
          'ssh2_auth_none',
          'ssh2_auth_password',
          'ssh2_auth_pubkey_file',
          'ssh2_connect',
          'ssh2_disconnect',
          'ssh2_exec',
          'ssh2_fetch_stream',
          'ssh2_fingerprint',
          'ssh2_forward_accept',
          'ssh2_forward_listen',
          'ssh2_methods_negotiated',
          'ssh2_poll',
          'ssh2_publickey_add',
          'ssh2_publickey_init',
          'ssh2_publickey_list',
          'ssh2_publickey_remove',
          'ssh2_scp_recv',
          'ssh2_scp_send',
          'ssh2_send_eof',
          'ssh2_sftp_chmod',
          'ssh2_sftp_lstat',
          'ssh2_sftp_mkdir',
          'ssh2_sftp_readlink',
          'ssh2_sftp_realpath',
          'ssh2_sftp_rename',
          'ssh2_sftp_rmdir',
          'ssh2_sftp_stat',
          'ssh2_sftp_symlink',
          'ssh2_sftp_unlink',
          'ssh2_sftp',
          'ssh2_shell',
          'ssh2_tunnel'),
 'SVN': ('svn_add',
         'svn_auth_get_parameter',
         'svn_auth_set_parameter',
         'svn_blame',
         'svn_cat',
         'svn_checkout',
         'svn_cleanup',
         'svn_client_version',
         'svn_commit',
         'svn_delete',
         'svn_diff',
         'svn_export',
         'svn_fs_abort_txn',
         'svn_fs_apply_text',
         'svn_fs_begin_txn2',
         'svn_fs_change_node_prop',
         'svn_fs_check_path',
         'svn_fs_contents_changed',
         'svn_fs_copy',
         'svn_fs_delete',
         'svn_fs_dir_entries',
         'svn_fs_file_contents',
         'svn_fs_file_length',
         'svn_fs_is_dir',
         'svn_fs_is_file',
         'svn_fs_make_dir',
         'svn_fs_make_file',
         'svn_fs_node_created_rev',
         'svn_fs_node_prop',
         'svn_fs_props_changed',
         'svn_fs_revision_prop',
         'svn_fs_revision_root',
         'svn_fs_txn_root',
         'svn_fs_youngest_rev',
         'svn_import',
         'svn_log',
         'svn_ls',
         'svn_mkdir',
         'svn_repos_create',
         'svn_repos_fs_begin_txn_for_commit',
         'svn_repos_fs_commit_txn',
         'svn_repos_fs',
         'svn_repos_hotcopy',
         'svn_repos_open',
         'svn_repos_recover',
         'svn_revert',
         'svn_status',
         'svn_update'),
 'Scoutapm': ('scoutapm_get_calls', 'scoutapm_list_instrumented_functions'),
 'Seaslog': ('seaslog_get_author', 'seaslog_get_version'),
 'Semaphore': ('ftok',
               'msg_get_queue',
               'msg_queue_exists',
               'msg_receive',
               'msg_remove_queue',
               'msg_send',
               'msg_set_queue',
               'msg_stat_queue',
               'sem_acquire',
               'sem_get',
               'sem_release',
               'sem_remove',
               'shm_attach',
               'shm_detach',
               'shm_get_var',
               'shm_has_var',
               'shm_put_var',
               'shm_remove_var',
               'shm_remove'),
 'Session': ('session_abort',
             'session_cache_expire',
             'session_cache_limiter',
             'session_commit',
             'session_create_id',
             'session_decode',
             'session_destroy',
             'session_encode',
             'session_gc',
             'session_get_cookie_params',
             'session_id',
             'session_module_name',
             'session_name',
             'session_regenerate_id',
             'session_register_shutdown',
             'session_reset',
             'session_save_path',
             'session_set_cookie_params',
             'session_set_save_handler',
             'session_start',
             'session_status',
             'session_unset',
             'session_write_close'),
 'Shared Memory': ('shmop_close',
                   'shmop_delete',
                   'shmop_open',
                   'shmop_read',
                   'shmop_size',
                   'shmop_write'),
 'SimpleXML': ('simplexml_import_dom',
               'simplexml_load_file',
               'simplexml_load_string'),
 'Socket': ('socket_accept',
            'socket_addrinfo_bind',
            'socket_addrinfo_connect',
            'socket_addrinfo_explain',
            'socket_addrinfo_lookup',
            'socket_bind',
            'socket_clear_error',
            'socket_close',
            'socket_cmsg_space',
            'socket_connect',
            'socket_create_listen',
            'socket_create_pair',
            'socket_create',
            'socket_export_stream',
            'socket_get_option',
            'socket_getopt',
            'socket_getpeername',
            'socket_getsockname',
            'socket_import_stream',
            'socket_last_error',
            'socket_listen',
            'socket_read',
            'socket_recv',
            'socket_recvfrom',
            'socket_recvmsg',
            'socket_select',
            'socket_send',
            'socket_sendmsg',
            'socket_sendto',
            'socket_set_block',
            'socket_set_nonblock',
            'socket_set_option',
            'socket_setopt',
            'socket_shutdown',
            'socket_strerror',
            'socket_write',
            'socket_wsaprotocol_info_export',
            'socket_wsaprotocol_info_import',
            'socket_wsaprotocol_info_release'),
 'Sodium': ('sodium_add',
            'sodium_base642bin',
            'sodium_bin2base64',
            'sodium_bin2hex',
            'sodium_compare',
            'sodium_crypto_aead_aes256gcm_decrypt',
            'sodium_crypto_aead_aes256gcm_encrypt',
            'sodium_crypto_aead_aes256gcm_is_available',
            'sodium_crypto_aead_aes256gcm_keygen',
            'sodium_crypto_aead_chacha20poly1305_decrypt',
            'sodium_crypto_aead_chacha20poly1305_encrypt',
            'sodium_crypto_aead_chacha20poly1305_ietf_decrypt',
            'sodium_crypto_aead_chacha20poly1305_ietf_encrypt',
            'sodium_crypto_aead_chacha20poly1305_ietf_keygen',
            'sodium_crypto_aead_chacha20poly1305_keygen',
            'sodium_crypto_aead_xchacha20poly1305_ietf_decrypt',
            'sodium_crypto_aead_xchacha20poly1305_ietf_encrypt',
            'sodium_crypto_aead_xchacha20poly1305_ietf_keygen',
            'sodium_crypto_auth_keygen',
            'sodium_crypto_auth_verify',
            'sodium_crypto_auth',
            'sodium_crypto_box_keypair_from_secretkey_and_publickey',
            'sodium_crypto_box_keypair',
            'sodium_crypto_box_open',
            'sodium_crypto_box_publickey_from_secretkey',
            'sodium_crypto_box_publickey',
            'sodium_crypto_box_seal_open',
            'sodium_crypto_box_seal',
            'sodium_crypto_box_secretkey',
            'sodium_crypto_box_seed_keypair',
            'sodium_crypto_box',
            'sodium_crypto_generichash_final',
            'sodium_crypto_generichash_init',
            'sodium_crypto_generichash_keygen',
            'sodium_crypto_generichash_update',
            'sodium_crypto_generichash',
            'sodium_crypto_kdf_derive_from_key',
            'sodium_crypto_kdf_keygen',
            'sodium_crypto_kx_client_session_keys',
            'sodium_crypto_kx_keypair',
            'sodium_crypto_kx_publickey',
            'sodium_crypto_kx_secretkey',
            'sodium_crypto_kx_seed_keypair',
            'sodium_crypto_kx_server_session_keys',
            'sodium_crypto_pwhash_scryptsalsa208sha256_str_verify',
            'sodium_crypto_pwhash_scryptsalsa208sha256_str',
            'sodium_crypto_pwhash_scryptsalsa208sha256',
            'sodium_crypto_pwhash_str_needs_rehash',
            'sodium_crypto_pwhash_str_verify',
            'sodium_crypto_pwhash_str',
            'sodium_crypto_pwhash',
            'sodium_crypto_scalarmult_base',
            'sodium_crypto_scalarmult',
            'sodium_crypto_secretbox_keygen',
            'sodium_crypto_secretbox_open',
            'sodium_crypto_secretbox',
            'sodium_crypto_secretstream_xchacha20poly1305_init_pull',
            'sodium_crypto_secretstream_xchacha20poly1305_init_push',
            'sodium_crypto_secretstream_xchacha20poly1305_keygen',
            'sodium_crypto_secretstream_xchacha20poly1305_pull',
            'sodium_crypto_secretstream_xchacha20poly1305_push',
            'sodium_crypto_secretstream_xchacha20poly1305_rekey',
            'sodium_crypto_shorthash_keygen',
            'sodium_crypto_shorthash',
            'sodium_crypto_sign_detached',
            'sodium_crypto_sign_ed25519_pk_to_curve25519',
            'sodium_crypto_sign_ed25519_sk_to_curve25519',
            'sodium_crypto_sign_keypair_from_secretkey_and_publickey',
            'sodium_crypto_sign_keypair',
            'sodium_crypto_sign_open',
            'sodium_crypto_sign_publickey_from_secretkey',
            'sodium_crypto_sign_publickey',
            'sodium_crypto_sign_secretkey',
            'sodium_crypto_sign_seed_keypair',
            'sodium_crypto_sign_verify_detached',
            'sodium_crypto_sign',
            'sodium_crypto_stream_keygen',
            'sodium_crypto_stream_xor',
            'sodium_crypto_stream',
            'sodium_hex2bin',
            'sodium_increment',
            'sodium_memcmp',
            'sodium_memzero',
            'sodium_pad',
            'sodium_unpad'),
 'Solr': ('solr_get_version',),
 'Stomp': ('stomp_connect_error', 'stomp_version'),
 'Stream': ('stream_bucket_append',
            'stream_bucket_make_writeable',
            'stream_bucket_new',
            'stream_bucket_prepend',
            'stream_context_create',
            'stream_context_get_default',
            'stream_context_get_options',
            'stream_context_get_params',
            'stream_context_set_default',
            'stream_context_set_option',
            'stream_context_set_params',
            'stream_copy_to_stream',
            'stream_filter_append',
            'stream_filter_prepend',
            'stream_filter_register',
            'stream_filter_remove',
            'stream_get_contents',
            'stream_get_filters',
            'stream_get_line',
            'stream_get_meta_data',
            'stream_get_transports',
            'stream_get_wrappers',
            'stream_is_local',
            'stream_isatty',
            'stream_notification_callback',
            'stream_register_wrapper',
            'stream_resolve_include_path',
            'stream_select',
            'stream_set_blocking',
            'stream_set_chunk_size',
            'stream_set_read_buffer',
            'stream_set_timeout',
            'stream_set_write_buffer',
            'stream_socket_accept',
            'stream_socket_client',
            'stream_socket_enable_crypto',
            'stream_socket_get_name',
            'stream_socket_pair',
            'stream_socket_recvfrom',
            'stream_socket_sendto',
            'stream_socket_server',
            'stream_socket_shutdown',
            'stream_supports_lock',
            'stream_wrapper_register',
            'stream_wrapper_restore',
            'stream_wrapper_unregister'),
 'String': ('addcslashes',
            'addslashes',
            'bin2hex',
            'chop',
            'chr',
            'chunk_split',
            'convert_cyr_string',
            'convert_uudecode',
            'convert_uuencode',
            'count_chars',
            'crc32',
            'crypt',
            'echo',
            'explode',
            'fprintf',
            'get_html_translation_table',
            'hebrev',
            'hebrevc',
            'hex2bin',
            'html_entity_decode',
            'htmlentities',
            'htmlspecialchars_decode',
            'htmlspecialchars',
            'implode',
            'join',
            'lcfirst',
            'levenshtein',
            'localeconv',
            'ltrim',
            'md5_file',
            'md5',
            'metaphone',
            'money_format',
            'nl_langinfo',
            'nl2br',
            'number_format',
            'ord',
            'parse_str',
            'print',
            'printf',
            'quoted_printable_decode',
            'quoted_printable_encode',
            'quotemeta',
            'rtrim',
            'setlocale',
            'sha1_file',
            'sha1',
            'similar_text',
            'soundex',
            'sprintf',
            'sscanf',
            'str_contains',
            'str_ends_with',
            'str_getcsv',
            'str_ireplace',
            'str_pad',
            'str_repeat',
            'str_replace',
            'str_rot13',
            'str_shuffle',
            'str_split',
            'str_starts_with',
            'str_word_count',
            'strcasecmp',
            'strchr',
            'strcmp',
            'strcoll',
            'strcspn',
            'strip_tags',
            'stripcslashes',
            'stripos',
            'stripslashes',
            'stristr',
            'strlen',
            'strnatcasecmp',
            'strnatcmp',
            'strncasecmp',
            'strncmp',
            'strpbrk',
            'strpos',
            'strrchr',
            'strrev',
            'strripos',
            'strrpos',
            'strspn',
            'strstr',
            'strtok',
            'strtolower',
            'strtoupper',
            'strtr',
            'substr_compare',
            'substr_count',
            'substr_replace',
            'substr',
            'trim',
            'ucfirst',
            'ucwords',
            'vfprintf',
            'vprintf',
            'vsprintf',
            'wordwrap'),
 'Swoole': ('swoole_async_dns_lookup',
            'swoole_async_read',
            'swoole_async_readfile',
            'swoole_async_set',
            'swoole_async_write',
            'swoole_async_writefile',
            'swoole_clear_error',
            'swoole_client_select',
            'swoole_cpu_num',
            'swoole_errno',
            'swoole_error_log',
            'swoole_event_add',
            'swoole_event_defer',
            'swoole_event_del',
            'swoole_event_exit',
            'swoole_event_set',
            'swoole_event_wait',
            'swoole_event_write',
            'swoole_get_local_ip',
            'swoole_last_error',
            'swoole_load_module',
            'swoole_select',
            'swoole_set_process_name',
            'swoole_strerror',
            'swoole_timer_after',
            'swoole_timer_exists',
            'swoole_timer_tick',
            'swoole_version'),
 'TCP': ('tcpwrap_check',),
 'Taint': ('is_tainted', 'taint', 'untaint'),
 'Tidy': ('ob_tidyhandler',
          'tidy_access_count',
          'tidy_config_count',
          'tidy_error_count',
          'tidy_get_output',
          'tidy_warning_count'),
 'Tokenizer': ('token_get_all', 'token_name'),
 'Trader': ('trader_acos',
            'trader_ad',
            'trader_add',
            'trader_adosc',
            'trader_adx',
            'trader_adxr',
            'trader_apo',
            'trader_aroon',
            'trader_aroonosc',
            'trader_asin',
            'trader_atan',
            'trader_atr',
            'trader_avgprice',
            'trader_bbands',
            'trader_beta',
            'trader_bop',
            'trader_cci',
            'trader_cdl2crows',
            'trader_cdl3blackcrows',
            'trader_cdl3inside',
            'trader_cdl3linestrike',
            'trader_cdl3outside',
            'trader_cdl3starsinsouth',
            'trader_cdl3whitesoldiers',
            'trader_cdlabandonedbaby',
            'trader_cdladvanceblock',
            'trader_cdlbelthold',
            'trader_cdlbreakaway',
            'trader_cdlclosingmarubozu',
            'trader_cdlconcealbabyswall',
            'trader_cdlcounterattack',
            'trader_cdldarkcloudcover',
            'trader_cdldoji',
            'trader_cdldojistar',
            'trader_cdldragonflydoji',
            'trader_cdlengulfing',
            'trader_cdleveningdojistar',
            'trader_cdleveningstar',
            'trader_cdlgapsidesidewhite',
            'trader_cdlgravestonedoji',
            'trader_cdlhammer',
            'trader_cdlhangingman',
            'trader_cdlharami',
            'trader_cdlharamicross',
            'trader_cdlhighwave',
            'trader_cdlhikkake',
            'trader_cdlhikkakemod',
            'trader_cdlhomingpigeon',
            'trader_cdlidentical3crows',
            'trader_cdlinneck',
            'trader_cdlinvertedhammer',
            'trader_cdlkicking',
            'trader_cdlkickingbylength',
            'trader_cdlladderbottom',
            'trader_cdllongleggeddoji',
            'trader_cdllongline',
            'trader_cdlmarubozu',
            'trader_cdlmatchinglow',
            'trader_cdlmathold',
            'trader_cdlmorningdojistar',
            'trader_cdlmorningstar',
            'trader_cdlonneck',
            'trader_cdlpiercing',
            'trader_cdlrickshawman',
            'trader_cdlrisefall3methods',
            'trader_cdlseparatinglines',
            'trader_cdlshootingstar',
            'trader_cdlshortline',
            'trader_cdlspinningtop',
            'trader_cdlstalledpattern',
            'trader_cdlsticksandwich',
            'trader_cdltakuri',
            'trader_cdltasukigap',
            'trader_cdlthrusting',
            'trader_cdltristar',
            'trader_cdlunique3river',
            'trader_cdlupsidegap2crows',
            'trader_cdlxsidegap3methods',
            'trader_ceil',
            'trader_cmo',
            'trader_correl',
            'trader_cos',
            'trader_cosh',
            'trader_dema',
            'trader_div',
            'trader_dx',
            'trader_ema',
            'trader_errno',
            'trader_exp',
            'trader_floor',
            'trader_get_compat',
            'trader_get_unstable_period',
            'trader_ht_dcperiod',
            'trader_ht_dcphase',
            'trader_ht_phasor',
            'trader_ht_sine',
            'trader_ht_trendline',
            'trader_ht_trendmode',
            'trader_kama',
            'trader_linearreg_angle',
            'trader_linearreg_intercept',
            'trader_linearreg_slope',
            'trader_linearreg',
            'trader_ln',
            'trader_log10',
            'trader_ma',
            'trader_macd',
            'trader_macdext',
            'trader_macdfix',
            'trader_mama',
            'trader_mavp',
            'trader_max',
            'trader_maxindex',
            'trader_medprice',
            'trader_mfi',
            'trader_midpoint',
            'trader_midprice',
            'trader_min',
            'trader_minindex',
            'trader_minmax',
            'trader_minmaxindex',
            'trader_minus_di',
            'trader_minus_dm',
            'trader_mom',
            'trader_mult',
            'trader_natr',
            'trader_obv',
            'trader_plus_di',
            'trader_plus_dm',
            'trader_ppo',
            'trader_roc',
            'trader_rocp',
            'trader_rocr100',
            'trader_rocr',
            'trader_rsi',
            'trader_sar',
            'trader_sarext',
            'trader_set_compat',
            'trader_set_unstable_period',
            'trader_sin',
            'trader_sinh',
            'trader_sma',
            'trader_sqrt',
            'trader_stddev',
            'trader_stoch',
            'trader_stochf',
            'trader_stochrsi',
            'trader_sub',
            'trader_sum',
            'trader_t3',
            'trader_tan',
            'trader_tanh',
            'trader_tema',
            'trader_trange',
            'trader_trima',
            'trader_trix',
            'trader_tsf',
            'trader_typprice',
            'trader_ultosc',
            'trader_var',
            'trader_wclprice',
            'trader_willr',
            'trader_wma'),
 'URL': ('base64_decode',
         'base64_encode',
         'get_headers',
         'get_meta_tags',
         'http_build_query',
         'parse_url',
         'rawurldecode',
         'rawurlencode',
         'urldecode',
         'urlencode'),
 'Uopz': ('uopz_add_function',
          'uopz_allow_exit',
          'uopz_backup',
          'uopz_compose',
          'uopz_copy',
          'uopz_del_function',
          'uopz_delete',
          'uopz_extend',
          'uopz_flags',
          'uopz_function',
          'uopz_get_exit_status',
          'uopz_get_hook',
          'uopz_get_mock',
          'uopz_get_property',
          'uopz_get_return',
          'uopz_get_static',
          'uopz_implement',
          'uopz_overload',
          'uopz_redefine',
          'uopz_rename',
          'uopz_restore',
          'uopz_set_hook',
          'uopz_set_mock',
          'uopz_set_property',
          'uopz_set_return',
          'uopz_set_static',
          'uopz_undefine',
          'uopz_unset_hook',
          'uopz_unset_mock',
          'uopz_unset_return'),
 'Variable handling': ('boolval',
                       'debug_zval_dump',
                       'doubleval',
                       'empty',
                       'floatval',
                       'get_debug_type',
                       'get_defined_vars',
                       'get_resource_id',
                       'get_resource_type',
                       'gettype',
                       'intval',
                       'is_array',
                       'is_bool',
                       'is_callable',
                       'is_countable',
                       'is_double',
                       'is_float',
                       'is_int',
                       'is_integer',
                       'is_iterable',
                       'is_long',
                       'is_null',
                       'is_numeric',
                       'is_object',
                       'is_real',
                       'is_resource',
                       'is_scalar',
                       'is_string',
                       'isset',
                       'print_r',
                       'serialize',
                       'settype',
                       'strval',
                       'unserialize',
                       'unset',
                       'var_dump',
                       'var_export'),
 'WDDX': ('wddx_add_vars',
          'wddx_deserialize',
          'wddx_packet_end',
          'wddx_packet_start',
          'wddx_serialize_value',
          'wddx_serialize_vars'),
 'WinCache': ('wincache_fcache_fileinfo',
              'wincache_fcache_meminfo',
              'wincache_lock',
              'wincache_ocache_fileinfo',
              'wincache_ocache_meminfo',
              'wincache_refresh_if_changed',
              'wincache_rplist_fileinfo',
              'wincache_rplist_meminfo',
              'wincache_scache_info',
              'wincache_scache_meminfo',
              'wincache_ucache_add',
              'wincache_ucache_cas',
              'wincache_ucache_clear',
              'wincache_ucache_dec',
              'wincache_ucache_delete',
              'wincache_ucache_exists',
              'wincache_ucache_get',
              'wincache_ucache_inc',
              'wincache_ucache_info',
              'wincache_ucache_meminfo',
              'wincache_ucache_set',
              'wincache_unlock'),
 'XML Parser': ('utf8_decode',
                'utf8_encode',
                'xml_error_string',
                'xml_get_current_byte_index',
                'xml_get_current_column_number',
                'xml_get_current_line_number',
                'xml_get_error_code',
                'xml_parse_into_struct',
                'xml_parse',
                'xml_parser_create_ns',
                'xml_parser_create',
                'xml_parser_free',
                'xml_parser_get_option',
                'xml_parser_set_option',
                'xml_set_character_data_handler',
                'xml_set_default_handler',
                'xml_set_element_handler',
                'xml_set_end_namespace_decl_handler',
                'xml_set_external_entity_ref_handler',
                'xml_set_notation_decl_handler',
                'xml_set_object',
                'xml_set_processing_instruction_handler',
                'xml_set_start_namespace_decl_handler',
                'xml_set_unparsed_entity_decl_handler'),
 'XML-RPC': ('xmlrpc_decode_request',
             'xmlrpc_decode',
             'xmlrpc_encode_request',
             'xmlrpc_encode',
             'xmlrpc_get_type',
             'xmlrpc_is_fault',
             'xmlrpc_parse_method_descriptions',
             'xmlrpc_server_add_introspection_data',
             'xmlrpc_server_call_method',
             'xmlrpc_server_create',
             'xmlrpc_server_destroy',
             'xmlrpc_server_register_introspection_callback',
             'xmlrpc_server_register_method',
             'xmlrpc_set_type'),
 'Xhprof': ('xhprof_disable',
            'xhprof_enable',
            'xhprof_sample_disable',
            'xhprof_sample_enable'),
 'YAZ': ('yaz_addinfo',
         'yaz_ccl_conf',
         'yaz_ccl_parse',
         'yaz_close',
         'yaz_connect',
         'yaz_database',
         'yaz_element',
         'yaz_errno',
         'yaz_error',
         'yaz_es_result',
         'yaz_es',
         'yaz_get_option',
         'yaz_hits',
         'yaz_itemorder',
         'yaz_present',
         'yaz_range',
         'yaz_record',
         'yaz_scan_result',
         'yaz_scan',
         'yaz_schema',
         'yaz_search',
         'yaz_set_option',
         'yaz_sort',
         'yaz_syntax',
         'yaz_wait'),
 'Yaml': ('yaml_emit_file',
          'yaml_emit',
          'yaml_parse_file',
          'yaml_parse_url',
          'yaml_parse'),
 'Zip': ('zip_close',
         'zip_entry_close',
         'zip_entry_compressedsize',
         'zip_entry_compressionmethod',
         'zip_entry_filesize',
         'zip_entry_name',
         'zip_entry_open',
         'zip_entry_read',
         'zip_open',
         'zip_read'),
 'Zlib': ('deflate_add',
          'deflate_init',
          'gzclose',
          'gzcompress',
          'gzdecode',
          'gzdeflate',
          'gzencode',
          'gzeof',
          'gzfile',
          'gzgetc',
          'gzgets',
          'gzgetss',
          'gzinflate',
          'gzopen',
          'gzpassthru',
          'gzputs',
          'gzread',
          'gzrewind',
          'gzseek',
          'gztell',
          'gzuncompress',
          'gzwrite',
          'inflate_add',
          'inflate_get_read_len',
          'inflate_get_status',
          'inflate_init',
          'readgzfile',
          'zlib_decode',
          'zlib_encode',
          'zlib_get_coding_type'),
 'ZooKeeper': ('zookeeper_dispatch',),
 'cURL': ('curl_close',
          'curl_copy_handle',
          'curl_errno',
          'curl_error',
          'curl_escape',
          'curl_exec',
          'curl_file_create',
          'curl_getinfo',
          'curl_init',
          'curl_multi_add_handle',
          'curl_multi_close',
          'curl_multi_errno',
          'curl_multi_exec',
          'curl_multi_getcontent',
          'curl_multi_info_read',
          'curl_multi_init',
          'curl_multi_remove_handle',
          'curl_multi_select',
          'curl_multi_setopt',
          'curl_multi_strerror',
          'curl_pause',
          'curl_reset',
          'curl_setopt_array',
          'curl_setopt',
          'curl_share_close',
          'curl_share_errno',
          'curl_share_init',
          'curl_share_setopt',
          'curl_share_strerror',
          'curl_strerror',
          'curl_unescape',
          'curl_version'),
 'dBase': ('dbase_add_record',
           'dbase_close',
           'dbase_create',
           'dbase_delete_record',
           'dbase_get_header_info',
           'dbase_get_record_with_names',
           'dbase_get_record',
           'dbase_numfields',
           'dbase_numrecords',
           'dbase_open',
           'dbase_pack',
           'dbase_replace_record'),
 'iconv': ('iconv_get_encoding',
           'iconv_mime_decode_headers',
           'iconv_mime_decode',
           'iconv_mime_encode',
           'iconv_set_encoding',
           'iconv_strlen',
           'iconv_strpos',
           'iconv_strrpos',
           'iconv_substr',
           'iconv',
           'ob_iconv_handler'),
 'intl': ('intl_error_name',
          'intl_get_error_code',
          'intl_get_error_message',
          'intl_is_failure'),
 'libxml': ('libxml_clear_errors',
            'libxml_disable_entity_loader',
            'libxml_get_errors',
            'libxml_get_last_error',
            'libxml_set_external_entity_loader',
            'libxml_set_streams_context',
            'libxml_use_internal_errors'),
 'mqseries': ('mqseries_back',
              'mqseries_begin',
              'mqseries_close',
              'mqseries_cmit',
              'mqseries_conn',
              'mqseries_connx',
              'mqseries_disc',
              'mqseries_get',
              'mqseries_inq',
              'mqseries_open',
              'mqseries_put1',
              'mqseries_put',
              'mqseries_set',
              'mqseries_strerror'),
 'phpdbg': ('phpdbg_break_file',
            'phpdbg_break_function',
            'phpdbg_break_method',
            'phpdbg_break_next',
            'phpdbg_clear',
            'phpdbg_color',
            'phpdbg_end_oplog',
            'phpdbg_exec',
            'phpdbg_get_executable',
            'phpdbg_prompt',
            'phpdbg_start_oplog'),
 'runkit7': ('runkit7_constant_add',
             'runkit7_constant_redefine',
             'runkit7_constant_remove',
             'runkit7_function_add',
             'runkit7_function_copy',
             'runkit7_function_redefine',
             'runkit7_function_remove',
             'runkit7_function_rename',
             'runkit7_import',
             'runkit7_method_add',
             'runkit7_method_copy',
             'runkit7_method_redefine',
             'runkit7_method_remove',
             'runkit7_method_rename',
             'runkit7_object_id',
             'runkit7_superglobals',
             'runkit7_zval_inspect'),
 'ssdeep': ('ssdeep_fuzzy_compare',
            'ssdeep_fuzzy_hash_filename',
            'ssdeep_fuzzy_hash'),
 'var_representation': ('var_representation',),
 'win32service': ('win32_continue_service',
                  'win32_create_service',
                  'win32_delete_service',
                  'win32_get_last_control_message',
                  'win32_pause_service',
                  'win32_query_service_status',
                  'win32_send_custom_control',
                  'win32_set_service_exit_code',
                  'win32_set_service_exit_mode',
                  'win32_set_service_status',
                  'win32_start_service_ctrl_dispatcher',
                  'win32_start_service',
                  'win32_stop_service'),
 'xattr': ('xattr_get',
           'xattr_list',
           'xattr_remove',
           'xattr_set',
           'xattr_supported'),
 'xdiff': ('xdiff_file_bdiff_size',
           'xdiff_file_bdiff',
           'xdiff_file_bpatch',
           'xdiff_file_diff_binary',
           'xdiff_file_diff',
           'xdiff_file_merge3',
           'xdiff_file_patch_binary',
           'xdiff_file_patch',
           'xdiff_file_rabdiff',
           'xdiff_string_bdiff_size',
           'xdiff_string_bdiff',
           'xdiff_string_bpatch',
           'xdiff_string_diff_binary',
           'xdiff_string_diff',
           'xdiff_string_merge3',
           'xdiff_string_patch_binary',
           'xdiff_string_patch',
           'xdiff_string_rabdiff')}

if __name__ == '__main__':  # pragma: no cover
    import glob
    import os
    import pprint
    import re
    import shutil
    import tarfile
    from urllib.request import urlretrieve

    PHP_MANUAL_URL     = 'http://us3.php.net/distributions/manual/php_manual_en.tar.gz'
    PHP_MANUAL_DIR     = './php-chunked-xhtml/'
    PHP_REFERENCE_GLOB = 'ref.*'
    PHP_FUNCTION_RE    = r'<a href="function\..*?\.html">(.*?)</a>'
    PHP_MODULE_RE      = '<title>(.*?) Functions</title>'

    def get_php_functions():
        function_re = re.compile(PHP_FUNCTION_RE)
        module_re   = re.compile(PHP_MODULE_RE)
        modules     = {}

        for file in get_php_references():
            module = ''
            with open(file, encoding='utf-8') as f:
                for line in f:
                    if not module:
                        search = module_re.search(line)
                        if search:
                            module = search.group(1)
                            modules[module] = []

                    elif 'href="function.' in line:
                        for match in function_re.finditer(line):
                            fn = match.group(1)
                            if '»' not in fn and '«' not in fn and \
                               '::' not in fn and '\\' not in fn and \
                               fn not in modules[module]:
                                modules[module].append(fn)

            if module:
                # These are dummy manual pages, not actual functions
                if module == 'Filesystem':
                    modules[module].remove('delete')

                if not modules[module]:
                    del modules[module]

        for key in modules:
            modules[key] = tuple(modules[key])
        return modules

    def get_php_references():
        download = urlretrieve(PHP_MANUAL_URL)
        with tarfile.open(download[0]) as tar:
            tar.extractall()
        yield from glob.glob(f"{PHP_MANUAL_DIR}{PHP_REFERENCE_GLOB}")
        os.remove(download[0])

    def regenerate(filename, modules):
        with open(filename, encoding='utf-8') as fp:
            content = fp.read()

        header = content[:content.find('MODULES = {')]
        footer = content[content.find("if __name__ == '__main__':"):]

        with open(filename, 'w', encoding='utf-8') as fp:
            fp.write(header)
            fp.write(f'MODULES = {pprint.pformat(modules)}\n\n')
            fp.write(footer)

    def run():
        print('>> Downloading Function Index')
        modules = get_php_functions()
        total = sum(len(v) for v in modules.values())
        print('%d functions found' % total)
        regenerate(__file__, modules)
        shutil.rmtree(PHP_MANUAL_DIR)

    run()

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\matlab.py ===
"""
    pygments.lexers.matlab
    ~~~~~~~~~~~~~~~~~~~~~~

    Lexers for Matlab and related languages.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import Lexer, RegexLexer, bygroups, default, words, \
    do_insertions, include
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Generic, Whitespace

from pygments.lexers import _scilab_builtins

__all__ = ['MatlabLexer', 'MatlabSessionLexer', 'OctaveLexer', 'ScilabLexer']


class MatlabLexer(RegexLexer):
    """
    For Matlab source code.
    """
    name = 'Matlab'
    aliases = ['matlab']
    filenames = ['*.m']
    mimetypes = ['text/matlab']
    url = 'https://www.mathworks.com/products/matlab.html'
    version_added = '0.10'

    _operators = r'-|==|~=|<=|>=|<|>|&&|&|~|\|\|?|\.\*|\*|\+|\.\^|\^|\.\\|\./|/|\\'

    tokens = {
        'expressions': [
            # operators:
            (_operators, Operator),

            # numbers (must come before punctuation to handle `.5`; cannot use
            # `\b` due to e.g. `5. + .5`).  The negative lookahead on operators
            # avoids including the dot in `1./x` (the dot is part of `./`).
            (rf'(?<!\w)((\d+\.\d+)|(\d*\.\d+)|(\d+\.(?!{_operators})))'
             r'([eEf][+-]?\d+)?(?!\w)', Number.Float),
            (r'\b\d+[eEf][+-]?[0-9]+\b', Number.Float),
            (r'\b\d+\b', Number.Integer),

            # punctuation:
            (r'\[|\]|\(|\)|\{|\}|:|@|\.|,', Punctuation),
            (r'=|:|;', Punctuation),

            # quote can be transpose, instead of string:
            # (not great, but handles common cases...)
            (r'(?<=[\w)\].])\'+', Operator),

            (r'"(""|[^"])*"', String),

            (r'(?<![\w)\].])\'', String, 'string'),
            (r'[a-zA-Z_]\w*', Name),
            (r'\s+', Whitespace),
            (r'.', Text),
        ],
        'root': [
            # line starting with '!' is sent as a system command.  not sure what
            # label to use...
            (r'^!.*', String.Other),
            (r'%\{\s*\n', Comment.Multiline, 'blockcomment'),
            (r'%.*$', Comment),
            (r'(\s*^\s*)(function)\b', bygroups(Whitespace, Keyword), 'deffunc'),
            (r'(\s*^\s*)(properties)(\s+)(\()',
             bygroups(Whitespace, Keyword, Whitespace, Punctuation),
             ('defprops', 'propattrs')),
            (r'(\s*^\s*)(properties)\b',
             bygroups(Whitespace, Keyword), 'defprops'),

            # from 'iskeyword' on version 9.4 (R2018a):
            # Check that there is no preceding dot, as keywords are valid field
            # names.
            (words(('break', 'case', 'catch', 'classdef', 'continue',
                    'dynamicprops', 'else', 'elseif', 'end', 'for', 'function',
                    'global', 'if', 'methods', 'otherwise', 'parfor',
                    'persistent', 'return', 'spmd', 'switch',
                    'try', 'while'),
                   prefix=r'(?<!\.)(\s*)(', suffix=r')\b'),
             bygroups(Whitespace, Keyword)),

            (
                words(
                    [
                        # See https://mathworks.com/help/matlab/referencelist.html
                        # Below data from 2021-02-10T18:24:08Z
                        # for Matlab release R2020b
                        "BeginInvoke",
                        "COM",
                        "Combine",
                        "CombinedDatastore",
                        "EndInvoke",
                        "Execute",
                        "FactoryGroup",
                        "FactorySetting",
                        "Feval",
                        "FunctionTestCase",
                        "GetCharArray",
                        "GetFullMatrix",
                        "GetVariable",
                        "GetWorkspaceData",
                        "GraphPlot",
                        "H5.close",
                        "H5.garbage_collect",
                        "H5.get_libversion",
                        "H5.open",
                        "H5.set_free_list_limits",
                        "H5A.close",
                        "H5A.create",
                        "H5A.delete",
                        "H5A.get_info",
                        "H5A.get_name",
                        "H5A.get_space",
                        "H5A.get_type",
                        "H5A.iterate",
                        "H5A.open",
                        "H5A.open_by_idx",
                        "H5A.open_by_name",
                        "H5A.read",
                        "H5A.write",
                        "H5D.close",
                        "H5D.create",
                        "H5D.get_access_plist",
                        "H5D.get_create_plist",
                        "H5D.get_offset",
                        "H5D.get_space",
                        "H5D.get_space_status",
                        "H5D.get_storage_size",
                        "H5D.get_type",
                        "H5D.open",
                        "H5D.read",
                        "H5D.set_extent",
                        "H5D.vlen_get_buf_size",
                        "H5D.write",
                        "H5DS.attach_scale",
                        "H5DS.detach_scale",
                        "H5DS.get_label",
                        "H5DS.get_num_scales",
                        "H5DS.get_scale_name",
                        "H5DS.is_scale",
                        "H5DS.iterate_scales",
                        "H5DS.set_label",
                        "H5DS.set_scale",
                        "H5E.clear",
                        "H5E.get_major",
                        "H5E.get_minor",
                        "H5E.walk",
                        "H5F.close",
                        "H5F.create",
                        "H5F.flush",
                        "H5F.get_access_plist",
                        "H5F.get_create_plist",
                        "H5F.get_filesize",
                        "H5F.get_freespace",
                        "H5F.get_info",
                        "H5F.get_mdc_config",
                        "H5F.get_mdc_hit_rate",
                        "H5F.get_mdc_size",
                        "H5F.get_name",
                        "H5F.get_obj_count",
                        "H5F.get_obj_ids",
                        "H5F.is_hdf5",
                        "H5F.mount",
                        "H5F.open",
                        "H5F.reopen",
                        "H5F.set_mdc_config",
                        "H5F.unmount",
                        "H5G.close",
                        "H5G.create",
                        "H5G.get_info",
                        "H5G.open",
                        "H5I.dec_ref",
                        "H5I.get_file_id",
                        "H5I.get_name",
                        "H5I.get_ref",
                        "H5I.get_type",
                        "H5I.inc_ref",
                        "H5I.is_valid",
                        "H5L.copy",
                        "H5L.create_external",
                        "H5L.create_hard",
                        "H5L.create_soft",
                        "H5L.delete",
                        "H5L.exists",
                        "H5L.get_info",
                        "H5L.get_name_by_idx",
                        "H5L.get_val",
                        "H5L.iterate",
                        "H5L.iterate_by_name",
                        "H5L.move",
                        "H5L.visit",
                        "H5L.visit_by_name",
                        "H5ML.compare_values",
                        "H5ML.get_constant_names",
                        "H5ML.get_constant_value",
                        "H5ML.get_function_names",
                        "H5ML.get_mem_datatype",
                        "H5O.close",
                        "H5O.copy",
                        "H5O.get_comment",
                        "H5O.get_comment_by_name",
                        "H5O.get_info",
                        "H5O.link",
                        "H5O.open",
                        "H5O.open_by_idx",
                        "H5O.set_comment",
                        "H5O.set_comment_by_name",
                        "H5O.visit",
                        "H5O.visit_by_name",
                        "H5P.all_filters_avail",
                        "H5P.close",
                        "H5P.close_class",
                        "H5P.copy",
                        "H5P.create",
                        "H5P.equal",
                        "H5P.exist",
                        "H5P.fill_value_defined",
                        "H5P.get",
                        "H5P.get_alignment",
                        "H5P.get_alloc_time",
                        "H5P.get_attr_creation_order",
                        "H5P.get_attr_phase_change",
                        "H5P.get_btree_ratios",
                        "H5P.get_char_encoding",
                        "H5P.get_chunk",
                        "H5P.get_chunk_cache",
                        "H5P.get_class",
                        "H5P.get_class_name",
                        "H5P.get_class_parent",
                        "H5P.get_copy_object",
                        "H5P.get_create_intermediate_group",
                        "H5P.get_driver",
                        "H5P.get_edc_check",
                        "H5P.get_external",
                        "H5P.get_external_count",
                        "H5P.get_family_offset",
                        "H5P.get_fapl_core",
                        "H5P.get_fapl_family",
                        "H5P.get_fapl_multi",
                        "H5P.get_fclose_degree",
                        "H5P.get_fill_time",
                        "H5P.get_fill_value",
                        "H5P.get_filter",
                        "H5P.get_filter_by_id",
                        "H5P.get_gc_references",
                        "H5P.get_hyper_vector_size",
                        "H5P.get_istore_k",
                        "H5P.get_layout",
                        "H5P.get_libver_bounds",
                        "H5P.get_link_creation_order",
                        "H5P.get_link_phase_change",
                        "H5P.get_mdc_config",
                        "H5P.get_meta_block_size",
                        "H5P.get_multi_type",
                        "H5P.get_nfilters",
                        "H5P.get_nprops",
                        "H5P.get_sieve_buf_size",
                        "H5P.get_size",
                        "H5P.get_sizes",
                        "H5P.get_small_data_block_size",
                        "H5P.get_sym_k",
                        "H5P.get_userblock",
                        "H5P.get_version",
                        "H5P.isa_class",
                        "H5P.iterate",
                        "H5P.modify_filter",
                        "H5P.remove_filter",
                        "H5P.set",
                        "H5P.set_alignment",
                        "H5P.set_alloc_time",
                        "H5P.set_attr_creation_order",
                        "H5P.set_attr_phase_change",
                        "H5P.set_btree_ratios",
                        "H5P.set_char_encoding",
                        "H5P.set_chunk",
                        "H5P.set_chunk_cache",
                        "H5P.set_copy_object",
                        "H5P.set_create_intermediate_group",
                        "H5P.set_deflate",
                        "H5P.set_edc_check",
                        "H5P.set_external",
                        "H5P.set_family_offset",
                        "H5P.set_fapl_core",
                        "H5P.set_fapl_family",
                        "H5P.set_fapl_log",
                        "H5P.set_fapl_multi",
                        "H5P.set_fapl_sec2",
                        "H5P.set_fapl_split",
                        "H5P.set_fapl_stdio",
                        "H5P.set_fclose_degree",
                        "H5P.set_fill_time",
                        "H5P.set_fill_value",
                        "H5P.set_filter",
                        "H5P.set_fletcher32",
                        "H5P.set_gc_references",
                        "H5P.set_hyper_vector_size",
                        "H5P.set_istore_k",
                        "H5P.set_layout",
                        "H5P.set_libver_bounds",
                        "H5P.set_link_creation_order",
                        "H5P.set_link_phase_change",
                        "H5P.set_mdc_config",
                        "H5P.set_meta_block_size",
                        "H5P.set_multi_type",
                        "H5P.set_nbit",
                        "H5P.set_scaleoffset",
                        "H5P.set_shuffle",
                        "H5P.set_sieve_buf_size",
                        "H5P.set_sizes",
                        "H5P.set_small_data_block_size",
                        "H5P.set_sym_k",
                        "H5P.set_userblock",
                        "H5R.create",
                        "H5R.dereference",
                        "H5R.get_name",
                        "H5R.get_obj_type",
                        "H5R.get_region",
                        "H5S.close",
                        "H5S.copy",
                        "H5S.create",
                        "H5S.create_simple",
                        "H5S.extent_copy",
                        "H5S.get_select_bounds",
                        "H5S.get_select_elem_npoints",
                        "H5S.get_select_elem_pointlist",
                        "H5S.get_select_hyper_blocklist",
                        "H5S.get_select_hyper_nblocks",
                        "H5S.get_select_npoints",
                        "H5S.get_select_type",
                        "H5S.get_simple_extent_dims",
                        "H5S.get_simple_extent_ndims",
                        "H5S.get_simple_extent_npoints",
                        "H5S.get_simple_extent_type",
                        "H5S.is_simple",
                        "H5S.offset_simple",
                        "H5S.select_all",
                        "H5S.select_elements",
                        "H5S.select_hyperslab",
                        "H5S.select_none",
                        "H5S.select_valid",
                        "H5S.set_extent_none",
                        "H5S.set_extent_simple",
                        "H5T.array_create",
                        "H5T.close",
                        "H5T.commit",
                        "H5T.committed",
                        "H5T.copy",
                        "H5T.create",
                        "H5T.detect_class",
                        "H5T.enum_create",
                        "H5T.enum_insert",
                        "H5T.enum_nameof",
                        "H5T.enum_valueof",
                        "H5T.equal",
                        "H5T.get_array_dims",
                        "H5T.get_array_ndims",
                        "H5T.get_class",
                        "H5T.get_create_plist",
                        "H5T.get_cset",
                        "H5T.get_ebias",
                        "H5T.get_fields",
                        "H5T.get_inpad",
                        "H5T.get_member_class",
                        "H5T.get_member_index",
                        "H5T.get_member_name",
                        "H5T.get_member_offset",
                        "H5T.get_member_type",
                        "H5T.get_member_value",
                        "H5T.get_native_type",
                        "H5T.get_nmembers",
                        "H5T.get_norm",
                        "H5T.get_offset",
                        "H5T.get_order",
                        "H5T.get_pad",
                        "H5T.get_precision",
                        "H5T.get_sign",
                        "H5T.get_size",
                        "H5T.get_strpad",
                        "H5T.get_super",
                        "H5T.get_tag",
                        "H5T.insert",
                        "H5T.is_variable_str",
                        "H5T.lock",
                        "H5T.open",
                        "H5T.pack",
                        "H5T.set_cset",
                        "H5T.set_ebias",
                        "H5T.set_fields",
                        "H5T.set_inpad",
                        "H5T.set_norm",
                        "H5T.set_offset",
                        "H5T.set_order",
                        "H5T.set_pad",
                        "H5T.set_precision",
                        "H5T.set_sign",
                        "H5T.set_size",
                        "H5T.set_strpad",
                        "H5T.set_tag",
                        "H5T.vlen_create",
                        "H5Z.filter_avail",
                        "H5Z.get_filter_info",
                        "Inf",
                        "KeyValueDatastore",
                        "KeyValueStore",
                        "MException",
                        "MException.last",
                        "MaximizeCommandWindow",
                        "MemoizedFunction",
                        "MinimizeCommandWindow",
                        "NET",
                        "NET.Assembly",
                        "NET.GenericClass",
                        "NET.NetException",
                        "NET.addAssembly",
                        "NET.convertArray",
                        "NET.createArray",
                        "NET.createGeneric",
                        "NET.disableAutoRelease",
                        "NET.enableAutoRelease",
                        "NET.invokeGenericMethod",
                        "NET.isNETSupported",
                        "NET.setStaticProperty",
                        "NaN",
                        "NaT",
                        "OperationResult",
                        "PutCharArray",
                        "PutFullMatrix",
                        "PutWorkspaceData",
                        "PythonEnvironment",
                        "Quit",
                        "RandStream",
                        "ReleaseCompatibilityException",
                        "ReleaseCompatibilityResults",
                        "Remove",
                        "RemoveAll",
                        "Setting",
                        "SettingsGroup",
                        "TallDatastore",
                        "Test",
                        "TestResult",
                        "Tiff",
                        "TransformedDatastore",
                        "ValueIterator",
                        "VersionResults",
                        "VideoReader",
                        "VideoWriter",
                        "abs",
                        "accumarray",
                        "acos",
                        "acosd",
                        "acosh",
                        "acot",
                        "acotd",
                        "acoth",
                        "acsc",
                        "acscd",
                        "acsch",
                        "actxGetRunningServer",
                        "actxserver",
                        "add",
                        "addCause",
                        "addCorrection",
                        "addFile",
                        "addFolderIncludingChildFiles",
                        "addGroup",
                        "addLabel",
                        "addPath",
                        "addReference",
                        "addSetting",
                        "addShortcut",
                        "addShutdownFile",
                        "addStartupFile",
                        "addStyle",
                        "addToolbarExplorationButtons",
                        "addboundary",
                        "addcats",
                        "addedge",
                        "addevent",
                        "addlistener",
                        "addmulti",
                        "addnode",
                        "addpath",
                        "addpoints",
                        "addpref",
                        "addprop",
                        "addsample",
                        "addsampletocollection",
                        "addtodate",
                        "addts",
                        "addvars",
                        "adjacency",
                        "airy",
                        "align",
                        "alim",
                        "all",
                        "allchild",
                        "alpha",
                        "alphaShape",
                        "alphaSpectrum",
                        "alphaTriangulation",
                        "alphamap",
                        "alphanumericBoundary",
                        "alphanumericsPattern",
                        "amd",
                        "analyzeCodeCompatibility",
                        "ancestor",
                        "angle",
                        "animatedline",
                        "annotation",
                        "ans",
                        "any",
                        "appdesigner",
                        "append",
                        "area",
                        "arguments",
                        "array2table",
                        "array2timetable",
                        "arrayDatastore",
                        "arrayfun",
                        "asFewOfPattern",
                        "asManyOfPattern",
                        "ascii",
                        "asec",
                        "asecd",
                        "asech",
                        "asin",
                        "asind",
                        "asinh",
                        "assert",
                        "assignin",
                        "atan",
                        "atan2",
                        "atan2d",
                        "atand",
                        "atanh",
                        "audiodevinfo",
                        "audiodevreset",
                        "audioinfo",
                        "audioplayer",
                        "audioread",
                        "audiorecorder",
                        "audiowrite",
                        "autumn",
                        "axes",
                        "axis",
                        "axtoolbar",
                        "axtoolbarbtn",
                        "balance",
                        "bandwidth",
                        "bar",
                        "bar3",
                        "bar3h",
                        "barh",
                        "barycentricToCartesian",
                        "base2dec",
                        "batchStartupOptionUsed",
                        "bctree",
                        "beep",
                        "bench",
                        "besselh",
                        "besseli",
                        "besselj",
                        "besselk",
                        "bessely",
                        "beta",
                        "betainc",
                        "betaincinv",
                        "betaln",
                        "between",
                        "bfsearch",
                        "bicg",
                        "bicgstab",
                        "bicgstabl",
                        "biconncomp",
                        "bin2dec",
                        "binary",
                        "binscatter",
                        "bitand",
                        "bitcmp",
                        "bitget",
                        "bitnot",
                        "bitor",
                        "bitset",
                        "bitshift",
                        "bitxor",
                        "blanks",
                        "ble",
                        "blelist",
                        "blkdiag",
                        "bluetooth",
                        "bluetoothlist",
                        "bone",
                        "boundary",
                        "boundaryFacets",
                        "boundaryshape",
                        "boundingbox",
                        "bounds",
                        "box",
                        "boxchart",
                        "brighten",
                        "brush",
                        "bsxfun",
                        "bubblechart",
                        "bubblechart3",
                        "bubblelegend",
                        "bubblelim",
                        "bubblesize",
                        "builddocsearchdb",
                        "builtin",
                        "bvp4c",
                        "bvp5c",
                        "bvpget",
                        "bvpinit",
                        "bvpset",
                        "bvpxtend",
                        "caldays",
                        "caldiff",
                        "calendar",
                        "calendarDuration",
                        "calllib",
                        "calmonths",
                        "calquarters",
                        "calweeks",
                        "calyears",
                        "camdolly",
                        "cameratoolbar",
                        "camlight",
                        "camlookat",
                        "camorbit",
                        "campan",
                        "campos",
                        "camproj",
                        "camroll",
                        "camtarget",
                        "camup",
                        "camva",
                        "camzoom",
                        "canUseGPU",
                        "canUseParallelPool",
                        "cart2pol",
                        "cart2sph",
                        "cartesianToBarycentric",
                        "caseInsensitivePattern",
                        "caseSensitivePattern",
                        "cast",
                        "cat",
                        "categorical",
                        "categories",
                        "caxis",
                        "cd",
                        "cdf2rdf",
                        "cdfepoch",
                        "cdfinfo",
                        "cdflib",
                        "cdfread",
                        "ceil",
                        "cell",
                        "cell2mat",
                        "cell2struct",
                        "cell2table",
                        "celldisp",
                        "cellfun",
                        "cellplot",
                        "cellstr",
                        "centrality",
                        "centroid",
                        "cgs",
                        "char",
                        "characterListPattern",
                        "characteristic",
                        "checkcode",
                        "chol",
                        "cholupdate",
                        "choose",
                        "chooseContextMenu",
                        "circshift",
                        "circumcenter",
                        "cla",
                        "clabel",
                        "class",
                        "classUnderlying",
                        "clc",
                        "clear",
                        "clearAllMemoizedCaches",
                        "clearPersonalValue",
                        "clearTemporaryValue",
                        "clearpoints",
                        "clearvars",
                        "clf",
                        "clibArray",
                        "clibConvertArray",
                        "clibIsNull",
                        "clibIsReadOnly",
                        "clibRelease",
                        "clibgen.buildInterface",
                        "clibgen.generateLibraryDefinition",
                        "clipboard",
                        "clock",
                        "clone",
                        "close",
                        "closeFile",
                        "closereq",
                        "cmap2gray",
                        "cmpermute",
                        "cmunique",
                        "codeCompatibilityReport",
                        "colamd",
                        "collapse",
                        "colon",
                        "colorbar",
                        "colorcube",
                        "colormap",
                        "colororder",
                        "colperm",
                        "com.mathworks.engine.MatlabEngine",
                        "com.mathworks.matlab.types.CellStr",
                        "com.mathworks.matlab.types.Complex",
                        "com.mathworks.matlab.types.HandleObject",
                        "com.mathworks.matlab.types.Struct",
                        "combine",
                        "comet",
                        "comet3",
                        "compan",
                        "compass",
                        "complex",
                        "compose",
                        "computer",
                        "comserver",
                        "cond",
                        "condeig",
                        "condensation",
                        "condest",
                        "coneplot",
                        "configureCallback",
                        "configureTerminator",
                        "conj",
                        "conncomp",
                        "containers.Map",
                        "contains",
                        "containsrange",
                        "contour",
                        "contour3",
                        "contourc",
                        "contourf",
                        "contourslice",
                        "contrast",
                        "conv",
                        "conv2",
                        "convertCharsToStrings",
                        "convertContainedStringsToChars",
                        "convertStringsToChars",
                        "convertTo",
                        "convertvars",
                        "convexHull",
                        "convhull",
                        "convhulln",
                        "convn",
                        "cool",
                        "copper",
                        "copyHDU",
                        "copyfile",
                        "copygraphics",
                        "copyobj",
                        "corrcoef",
                        "cos",
                        "cosd",
                        "cosh",
                        "cospi",
                        "cot",
                        "cotd",
                        "coth",
                        "count",
                        "countcats",
                        "cov",
                        "cplxpair",
                        "cputime",
                        "createCategory",
                        "createFile",
                        "createImg",
                        "createLabel",
                        "createTbl",
                        "criticalAlpha",
                        "cross",
                        "csc",
                        "cscd",
                        "csch",
                        "ctranspose",
                        "cummax",
                        "cummin",
                        "cumprod",
                        "cumsum",
                        "cumtrapz",
                        "curl",
                        "currentProject",
                        "cylinder",
                        "daspect",
                        "dataTipInteraction",
                        "dataTipTextRow",
                        "datacursormode",
                        "datastore",
                        "datatip",
                        "date",
                        "datenum",
                        "dateshift",
                        "datestr",
                        "datetick",
                        "datetime",
                        "datevec",
                        "day",
                        "days",
                        "dbclear",
                        "dbcont",
                        "dbdown",
                        "dbmex",
                        "dbquit",
                        "dbstack",
                        "dbstatus",
                        "dbstep",
                        "dbstop",
                        "dbtype",
                        "dbup",
                        "dde23",
                        "ddeget",
                        "ddensd",
                        "ddesd",
                        "ddeset",
                        "deblank",
                        "dec2base",
                        "dec2bin",
                        "dec2hex",
                        "decic",
                        "decomposition",
                        "deconv",
                        "deg2rad",
                        "degree",
                        "del2",
                        "delaunay",
                        "delaunayTriangulation",
                        "delaunayn",
                        "delete",
                        "deleteCol",
                        "deleteFile",
                        "deleteHDU",
                        "deleteKey",
                        "deleteRecord",
                        "deleteRows",
                        "delevent",
                        "delimitedTextImportOptions",
                        "delsample",
                        "delsamplefromcollection",
                        "demo",
                        "descriptor",
                        "det",
                        "details",
                        "detectImportOptions",
                        "detrend",
                        "deval",
                        "dfsearch",
                        "diag",
                        "dialog",
                        "diary",
                        "diff",
                        "diffuse",
                        "digitBoundary",
                        "digitsPattern",
                        "digraph",
                        "dir",
                        "disableDefaultInteractivity",
                        "discretize",
                        "disp",
                        "display",
                        "dissect",
                        "distances",
                        "dither",
                        "divergence",
                        "dmperm",
                        "doc",
                        "docsearch",
                        "dos",
                        "dot",
                        "double",
                        "drag",
                        "dragrect",
                        "drawnow",
                        "dsearchn",
                        "duration",
                        "dynamicprops",
                        "echo",
                        "echodemo",
                        "echotcpip",
                        "edgeAttachments",
                        "edgecount",
                        "edges",
                        "edit",
                        "eig",
                        "eigs",
                        "ellipj",
                        "ellipke",
                        "ellipsoid",
                        "empty",
                        "enableDefaultInteractivity",
                        "enableLegacyExplorationModes",
                        "enableNETfromNetworkDrive",
                        "enableservice",
                        "endsWith",
                        "enumeration",
                        "eomday",
                        "eps",
                        "eq",
                        "equilibrate",
                        "erase",
                        "eraseBetween",
                        "erf",
                        "erfc",
                        "erfcinv",
                        "erfcx",
                        "erfinv",
                        "error",
                        "errorbar",
                        "errordlg",
                        "etime",
                        "etree",
                        "etreeplot",
                        "eval",
                        "evalc",
                        "evalin",
                        "event.ClassInstanceEvent",
                        "event.DynamicPropertyEvent",
                        "event.EventData",
                        "event.PropertyEvent",
                        "event.hasListener",
                        "event.listener",
                        "event.proplistener",
                        "eventlisteners",
                        "events",
                        "exceltime",
                        "exist",
                        "exit",
                        "exp",
                        "expand",
                        "expint",
                        "expm",
                        "expm1",
                        "export",
                        "export2wsdlg",
                        "exportapp",
                        "exportgraphics",
                        "exportsetupdlg",
                        "extract",
                        "extractAfter",
                        "extractBefore",
                        "extractBetween",
                        "eye",
                        "ezpolar",
                        "faceNormal",
                        "factor",
                        "factorial",
                        "false",
                        "fclose",
                        "fcontour",
                        "feather",
                        "featureEdges",
                        "feof",
                        "ferror",
                        "feval",
                        "fewerbins",
                        "fft",
                        "fft2",
                        "fftn",
                        "fftshift",
                        "fftw",
                        "fgetl",
                        "fgets",
                        "fieldnames",
                        "figure",
                        "figurepalette",
                        "fileDatastore",
                        "fileMode",
                        "fileName",
                        "fileattrib",
                        "filemarker",
                        "fileparts",
                        "fileread",
                        "filesep",
                        "fill",
                        "fill3",
                        "fillmissing",
                        "filloutliers",
                        "filter",
                        "filter2",
                        "fimplicit",
                        "fimplicit3",
                        "find",
                        "findCategory",
                        "findEvent",
                        "findFile",
                        "findLabel",
                        "findall",
                        "findedge",
                        "findfigs",
                        "findgroups",
                        "findnode",
                        "findobj",
                        "findprop",
                        "finish",
                        "fitsdisp",
                        "fitsinfo",
                        "fitsread",
                        "fitswrite",
                        "fix",
                        "fixedWidthImportOptions",
                        "flag",
                        "flintmax",
                        "flip",
                        "flipedge",
                        "fliplr",
                        "flipud",
                        "floor",
                        "flow",
                        "flush",
                        "fmesh",
                        "fminbnd",
                        "fminsearch",
                        "fopen",
                        "format",
                        "fplot",
                        "fplot3",
                        "fprintf",
                        "frame2im",
                        "fread",
                        "freeBoundary",
                        "freqspace",
                        "frewind",
                        "fscanf",
                        "fseek",
                        "fsurf",
                        "ftell",
                        "ftp",
                        "full",
                        "fullfile",
                        "func2str",
                        "function_handle",
                        "functions",
                        "functiontests",
                        "funm",
                        "fwrite",
                        "fzero",
                        "gallery",
                        "gamma",
                        "gammainc",
                        "gammaincinv",
                        "gammaln",
                        "gather",
                        "gca",
                        "gcbf",
                        "gcbo",
                        "gcd",
                        "gcf",
                        "gcmr",
                        "gco",
                        "genpath",
                        "geoaxes",
                        "geobasemap",
                        "geobubble",
                        "geodensityplot",
                        "geolimits",
                        "geoplot",
                        "geoscatter",
                        "geotickformat",
                        "get",
                        "getAColParms",
                        "getAxes",
                        "getBColParms",
                        "getColName",
                        "getColType",
                        "getColorbar",
                        "getConstantValue",
                        "getEqColType",
                        "getFileFormats",
                        "getHDUnum",
                        "getHDUtype",
                        "getHdrSpace",
                        "getImgSize",
                        "getImgType",
                        "getLayout",
                        "getLegend",
                        "getMockHistory",
                        "getNumCols",
                        "getNumHDUs",
                        "getNumInputs",
                        "getNumInputsImpl",
                        "getNumOutputs",
                        "getNumOutputsImpl",
                        "getNumRows",
                        "getOpenFiles",
                        "getProfiles",
                        "getPropertyGroupsImpl",
                        "getReport",
                        "getTimeStr",
                        "getVersion",
                        "getabstime",
                        "getappdata",
                        "getaudiodata",
                        "getdatasamples",
                        "getdatasamplesize",
                        "getenv",
                        "getfield",
                        "getframe",
                        "getinterpmethod",
                        "getnext",
                        "getpinstatus",
                        "getpixelposition",
                        "getplayer",
                        "getpoints",
                        "getpref",
                        "getqualitydesc",
                        "getrangefromclass",
                        "getsamples",
                        "getsampleusingtime",
                        "gettimeseriesnames",
                        "gettsafteratevent",
                        "gettsafterevent",
                        "gettsatevent",
                        "gettsbeforeatevent",
                        "gettsbeforeevent",
                        "gettsbetweenevents",
                        "getvaropts",
                        "ginput",
                        "gmres",
                        "gobjects",
                        "gplot",
                        "grabcode",
                        "gradient",
                        "graph",
                        "gray",
                        "grid",
                        "griddata",
                        "griddatan",
                        "griddedInterpolant",
                        "groot",
                        "groupcounts",
                        "groupfilter",
                        "groupsummary",
                        "grouptransform",
                        "gsvd",
                        "gtext",
                        "guidata",
                        "guide",
                        "guihandles",
                        "gunzip",
                        "gzip",
                        "h5create",
                        "h5disp",
                        "h5info",
                        "h5read",
                        "h5readatt",
                        "h5write",
                        "h5writeatt",
                        "hadamard",
                        "handle",
                        "hankel",
                        "hasFactoryValue",
                        "hasFrame",
                        "hasGroup",
                        "hasPersonalValue",
                        "hasSetting",
                        "hasTemporaryValue",
                        "hasdata",
                        "hasnext",
                        "hdfan",
                        "hdfdf24",
                        "hdfdfr8",
                        "hdfh",
                        "hdfhd",
                        "hdfhe",
                        "hdfhx",
                        "hdfinfo",
                        "hdfml",
                        "hdfpt",
                        "hdfread",
                        "hdfv",
                        "hdfvf",
                        "hdfvh",
                        "hdfvs",
                        "head",
                        "heatmap",
                        "height",
                        "help",
                        "helpdlg",
                        "hess",
                        "hex2dec",
                        "hex2num",
                        "hgexport",
                        "hggroup",
                        "hgtransform",
                        "hidden",
                        "highlight",
                        "hilb",
                        "histcounts",
                        "histcounts2",
                        "histogram",
                        "histogram2",
                        "hms",
                        "hold",
                        "holes",
                        "home",
                        "horzcat",
                        "hot",
                        "hour",
                        "hours",
                        "hover",
                        "hsv",
                        "hsv2rgb",
                        "hypot",
                        "i",
                        "ichol",
                        "idealfilter",
                        "idivide",
                        "ifft",
                        "ifft2",
                        "ifftn",
                        "ifftshift",
                        "ilu",
                        "im2double",
                        "im2frame",
                        "im2gray",
                        "im2java",
                        "imag",
                        "image",
                        "imageDatastore",
                        "imagesc",
                        "imapprox",
                        "imfinfo",
                        "imformats",
                        "imgCompress",
                        "import",
                        "importdata",
                        "imread",
                        "imresize",
                        "imshow",
                        "imtile",
                        "imwrite",
                        "inShape",
                        "incenter",
                        "incidence",
                        "ind2rgb",
                        "ind2sub",
                        "indegree",
                        "inedges",
                        "infoImpl",
                        "inmem",
                        "inner2outer",
                        "innerjoin",
                        "inpolygon",
                        "input",
                        "inputParser",
                        "inputdlg",
                        "inputname",
                        "insertATbl",
                        "insertAfter",
                        "insertBTbl",
                        "insertBefore",
                        "insertCol",
                        "insertImg",
                        "insertRows",
                        "int16",
                        "int2str",
                        "int32",
                        "int64",
                        "int8",
                        "integral",
                        "integral2",
                        "integral3",
                        "interp1",
                        "interp2",
                        "interp3",
                        "interpft",
                        "interpn",
                        "interpstreamspeed",
                        "intersect",
                        "intmax",
                        "intmin",
                        "inv",
                        "invhilb",
                        "ipermute",
                        "iqr",
                        "isCompressedImg",
                        "isConnected",
                        "isDiscreteStateSpecificationMutableImpl",
                        "isDone",
                        "isDoneImpl",
                        "isInactivePropertyImpl",
                        "isInputComplexityMutableImpl",
                        "isInputDataTypeMutableImpl",
                        "isInputSizeMutableImpl",
                        "isInterior",
                        "isKey",
                        "isLoaded",
                        "isLocked",
                        "isMATLABReleaseOlderThan",
                        "isPartitionable",
                        "isShuffleable",
                        "isStringScalar",
                        "isTunablePropertyDataTypeMutableImpl",
                        "isUnderlyingType",
                        "isa",
                        "isaUnderlying",
                        "isappdata",
                        "isbanded",
                        "isbetween",
                        "iscalendarduration",
                        "iscategorical",
                        "iscategory",
                        "iscell",
                        "iscellstr",
                        "ischange",
                        "ischar",
                        "iscolumn",
                        "iscom",
                        "isdag",
                        "isdatetime",
                        "isdiag",
                        "isdst",
                        "isduration",
                        "isempty",
                        "isenum",
                        "isequal",
                        "isequaln",
                        "isevent",
                        "isfield",
                        "isfile",
                        "isfinite",
                        "isfloat",
                        "isfolder",
                        "isgraphics",
                        "ishandle",
                        "ishermitian",
                        "ishold",
                        "ishole",
                        "isinf",
                        "isinteger",
                        "isinterface",
                        "isinterior",
                        "isisomorphic",
                        "isjava",
                        "iskeyword",
                        "isletter",
                        "islocalmax",
                        "islocalmin",
                        "islogical",
                        "ismac",
                        "ismatrix",
                        "ismember",
                        "ismembertol",
                        "ismethod",
                        "ismissing",
                        "ismultigraph",
                        "isnan",
                        "isnat",
                        "isnumeric",
                        "isobject",
                        "isocaps",
                        "isocolors",
                        "isomorphism",
                        "isonormals",
                        "isordinal",
                        "isosurface",
                        "isoutlier",
                        "ispc",
                        "isplaying",
                        "ispref",
                        "isprime",
                        "isprop",
                        "isprotected",
                        "isreal",
                        "isrecording",
                        "isregular",
                        "isrow",
                        "isscalar",
                        "issimplified",
                        "issorted",
                        "issortedrows",
                        "isspace",
                        "issparse",
                        "isstring",
                        "isstrprop",
                        "isstruct",
                        "isstudent",
                        "issymmetric",
                        "istable",
                        "istall",
                        "istimetable",
                        "istril",
                        "istriu",
                        "isundefined",
                        "isunix",
                        "isvalid",
                        "isvarname",
                        "isvector",
                        "isweekend",
                        "j",
                        "javaArray",
                        "javaMethod",
                        "javaMethodEDT",
                        "javaObject",
                        "javaObjectEDT",
                        "javaaddpath",
                        "javachk",
                        "javaclasspath",
                        "javarmpath",
                        "jet",
                        "join",
                        "jsondecode",
                        "jsonencode",
                        "juliandate",
                        "keyboard",
                        "keys",
                        "kron",
                        "labeledge",
                        "labelnode",
                        "lag",
                        "laplacian",
                        "lastwarn",
                        "layout",
                        "lcm",
                        "ldl",
                        "leapseconds",
                        "legend",
                        "legendre",
                        "length",
                        "letterBoundary",
                        "lettersPattern",
                        "lib.pointer",
                        "libfunctions",
                        "libfunctionsview",
                        "libisloaded",
                        "libpointer",
                        "libstruct",
                        "license",
                        "light",
                        "lightangle",
                        "lighting",
                        "lin2mu",
                        "line",
                        "lineBoundary",
                        "lines",
                        "linkaxes",
                        "linkdata",
                        "linkprop",
                        "linsolve",
                        "linspace",
                        "listModifiedFiles",
                        "listRequiredFiles",
                        "listdlg",
                        "listener",
                        "listfonts",
                        "load",
                        "loadObjectImpl",
                        "loadlibrary",
                        "loadobj",
                        "localfunctions",
                        "log",
                        "log10",
                        "log1p",
                        "log2",
                        "logical",
                        "loglog",
                        "logm",
                        "logspace",
                        "lookAheadBoundary",
                        "lookBehindBoundary",
                        "lookfor",
                        "lower",
                        "ls",
                        "lscov",
                        "lsqminnorm",
                        "lsqnonneg",
                        "lsqr",
                        "lu",
                        "magic",
                        "makehgtform",
                        "makima",
                        "mapreduce",
                        "mapreducer",
                        "maskedPattern",
                        "mat2cell",
                        "mat2str",
                        "matches",
                        "matchpairs",
                        "material",
                        "matfile",
                        "matlab.System",
                        "matlab.addons.disableAddon",
                        "matlab.addons.enableAddon",
                        "matlab.addons.install",
                        "matlab.addons.installedAddons",
                        "matlab.addons.isAddonEnabled",
                        "matlab.addons.toolbox.installToolbox",
                        "matlab.addons.toolbox.installedToolboxes",
                        "matlab.addons.toolbox.packageToolbox",
                        "matlab.addons.toolbox.toolboxVersion",
                        "matlab.addons.toolbox.uninstallToolbox",
                        "matlab.addons.uninstall",
                        "matlab.apputil.create",
                        "matlab.apputil.getInstalledAppInfo",
                        "matlab.apputil.install",
                        "matlab.apputil.package",
                        "matlab.apputil.run",
                        "matlab.apputil.uninstall",
                        "matlab.codetools.requiredFilesAndProducts",
                        "matlab.engine.FutureResult",
                        "matlab.engine.MatlabEngine",
                        "matlab.engine.connect_matlab",
                        "matlab.engine.engineName",
                        "matlab.engine.find_matlab",
                        "matlab.engine.isEngineShared",
                        "matlab.engine.shareEngine",
                        "matlab.engine.start_matlab",
                        "matlab.exception.JavaException",
                        "matlab.exception.PyException",
                        "matlab.graphics.chartcontainer.ChartContainer",
                        "matlab.graphics.chartcontainer.mixin.Colorbar",
                        "matlab.graphics.chartcontainer.mixin.Legend",
                        "matlab.io.Datastore",
                        "matlab.io.datastore.BlockedFileSet",
                        "matlab.io.datastore.DsFileReader",
                        "matlab.io.datastore.DsFileSet",
                        "matlab.io.datastore.FileSet",
                        "matlab.io.datastore.FileWritable",
                        "matlab.io.datastore.FoldersPropertyProvider",
                        "matlab.io.datastore.HadoopLocationBased",
                        "matlab.io.datastore.Partitionable",
                        "matlab.io.datastore.Shuffleable",
                        "matlab.io.hdf4.sd",
                        "matlab.io.hdfeos.gd",
                        "matlab.io.hdfeos.sw",
                        "matlab.io.saveVariablesToScript",
                        "matlab.lang.OnOffSwitchState",
                        "matlab.lang.correction.AppendArgumentsCorrection",
                        "matlab.lang.correction.ConvertToFunctionNotationCorrection",
                        "matlab.lang.correction.ReplaceIdentifierCorrection",
                        "matlab.lang.makeUniqueStrings",
                        "matlab.lang.makeValidName",
                        "matlab.mex.MexHost",
                        "matlab.mixin.Copyable",
                        "matlab.mixin.CustomDisplay",
                        "matlab.mixin.Heterogeneous",
                        "matlab.mixin.SetGet",
                        "matlab.mixin.SetGetExactNames",
                        "matlab.mixin.util.PropertyGroup",
                        "matlab.mock.AnyArguments",
                        "matlab.mock.InteractionHistory",
                        "matlab.mock.InteractionHistory.forMock",
                        "matlab.mock.MethodCallBehavior",
                        "matlab.mock.PropertyBehavior",
                        "matlab.mock.PropertyGetBehavior",
                        "matlab.mock.PropertySetBehavior",
                        "matlab.mock.TestCase",
                        "matlab.mock.actions.AssignOutputs",
                        "matlab.mock.actions.DoNothing",
                        "matlab.mock.actions.Invoke",
                        "matlab.mock.actions.ReturnStoredValue",
                        "matlab.mock.actions.StoreValue",
                        "matlab.mock.actions.ThrowException",
                        "matlab.mock.constraints.Occurred",
                        "matlab.mock.constraints.WasAccessed",
                        "matlab.mock.constraints.WasCalled",
                        "matlab.mock.constraints.WasSet",
                        "matlab.net.ArrayFormat",
                        "matlab.net.QueryParameter",
                        "matlab.net.URI",
                        "matlab.net.base64decode",
                        "matlab.net.base64encode",
                        "matlab.net.http.AuthInfo",
                        "matlab.net.http.AuthenticationScheme",
                        "matlab.net.http.Cookie",
                        "matlab.net.http.CookieInfo",
                        "matlab.net.http.Credentials",
                        "matlab.net.http.Disposition",
                        "matlab.net.http.HTTPException",
                        "matlab.net.http.HTTPOptions",
                        "matlab.net.http.HeaderField",
                        "matlab.net.http.LogRecord",
                        "matlab.net.http.MediaType",
                        "matlab.net.http.Message",
                        "matlab.net.http.MessageBody",
                        "matlab.net.http.MessageType",
                        "matlab.net.http.ProgressMonitor",
                        "matlab.net.http.ProtocolVersion",
                        "matlab.net.http.RequestLine",
                        "matlab.net.http.RequestMessage",
                        "matlab.net.http.RequestMethod",
                        "matlab.net.http.ResponseMessage",
                        "matlab.net.http.StartLine",
                        "matlab.net.http.StatusClass",
                        "matlab.net.http.StatusCode",
                        "matlab.net.http.StatusLine",
                        "matlab.net.http.field.AcceptField",
                        "matlab.net.http.field.AuthenticateField",
                        "matlab.net.http.field.AuthenticationInfoField",
                        "matlab.net.http.field.AuthorizationField",
                        "matlab.net.http.field.ContentDispositionField",
                        "matlab.net.http.field.ContentLengthField",
                        "matlab.net.http.field.ContentLocationField",
                        "matlab.net.http.field.ContentTypeField",
                        "matlab.net.http.field.CookieField",
                        "matlab.net.http.field.DateField",
                        "matlab.net.http.field.GenericField",
                        "matlab.net.http.field.GenericParameterizedField",
                        "matlab.net.http.field.HTTPDateField",
                        "matlab.net.http.field.IntegerField",
                        "matlab.net.http.field.LocationField",
                        "matlab.net.http.field.MediaRangeField",
                        "matlab.net.http.field.SetCookieField",
                        "matlab.net.http.field.URIReferenceField",
                        "matlab.net.http.io.BinaryConsumer",
                        "matlab.net.http.io.ContentConsumer",
                        "matlab.net.http.io.ContentProvider",
                        "matlab.net.http.io.FileConsumer",
                        "matlab.net.http.io.FileProvider",
                        "matlab.net.http.io.FormProvider",
                        "matlab.net.http.io.GenericConsumer",
                        "matlab.net.http.io.GenericProvider",
                        "matlab.net.http.io.ImageConsumer",
                        "matlab.net.http.io.ImageProvider",
                        "matlab.net.http.io.JSONConsumer",
                        "matlab.net.http.io.JSONProvider",
                        "matlab.net.http.io.MultipartConsumer",
                        "matlab.net.http.io.MultipartFormProvider",
                        "matlab.net.http.io.MultipartProvider",
                        "matlab.net.http.io.StringConsumer",
                        "matlab.net.http.io.StringProvider",
                        "matlab.perftest.FixedTimeExperiment",
                        "matlab.perftest.FrequentistTimeExperiment",
                        "matlab.perftest.TestCase",
                        "matlab.perftest.TimeExperiment",
                        "matlab.perftest.TimeResult",
                        "matlab.project.Project",
                        "matlab.project.convertDefinitionFiles",
                        "matlab.project.createProject",
                        "matlab.project.deleteProject",
                        "matlab.project.loadProject",
                        "matlab.project.rootProject",
                        "matlab.settings.FactoryGroup.createToolboxGroup",
                        "matlab.settings.SettingsFileUpgrader",
                        "matlab.settings.loadSettingsCompatibilityResults",
                        "matlab.settings.mustBeIntegerScalar",
                        "matlab.settings.mustBeLogicalScalar",
                        "matlab.settings.mustBeNumericScalar",
                        "matlab.settings.mustBeStringScalar",
                        "matlab.settings.reloadFactoryFile",
                        "matlab.system.mixin.FiniteSource",
                        "matlab.tall.blockMovingWindow",
                        "matlab.tall.movingWindow",
                        "matlab.tall.reduce",
                        "matlab.tall.transform",
                        "matlab.test.behavior.Missing",
                        "matlab.ui.componentcontainer.ComponentContainer",
                        "matlab.uitest.TestCase",
                        "matlab.uitest.TestCase.forInteractiveUse",
                        "matlab.uitest.unlock",
                        "matlab.unittest.Test",
                        "matlab.unittest.TestCase",
                        "matlab.unittest.TestResult",
                        "matlab.unittest.TestRunner",
                        "matlab.unittest.TestSuite",
                        "matlab.unittest.constraints.BooleanConstraint",
                        "matlab.unittest.constraints.Constraint",
                        "matlab.unittest.constraints.Tolerance",
                        "matlab.unittest.diagnostics.ConstraintDiagnostic",
                        "matlab.unittest.diagnostics.Diagnostic",
                        "matlab.unittest.fixtures.Fixture",
                        "matlab.unittest.measurement.DefaultMeasurementResult",
                        "matlab.unittest.measurement.MeasurementResult",
                        "matlab.unittest.measurement.chart.ComparisonPlot",
                        "matlab.unittest.plugins.OutputStream",
                        "matlab.unittest.plugins.Parallelizable",
                        "matlab.unittest.plugins.QualifyingPlugin",
                        "matlab.unittest.plugins.TestRunnerPlugin",
                        "matlab.wsdl.createWSDLClient",
                        "matlab.wsdl.setWSDLToolPath",
                        "matlabRelease",
                        "matlabrc",
                        "matlabroot",
                        "max",
                        "maxflow",
                        "maxk",
                        "mean",
                        "median",
                        "memmapfile",
                        "memoize",
                        "memory",
                        "mergecats",
                        "mergevars",
                        "mesh",
                        "meshc",
                        "meshgrid",
                        "meshz",
                        "meta.ArrayDimension",
                        "meta.DynamicProperty",
                        "meta.EnumeratedValue",
                        "meta.FixedDimension",
                        "meta.MetaData",
                        "meta.UnrestrictedDimension",
                        "meta.Validation",
                        "meta.abstractDetails",
                        "meta.class",
                        "meta.class.fromName",
                        "meta.event",
                        "meta.method",
                        "meta.package",
                        "meta.package.fromName",
                        "meta.package.getAllPackages",
                        "meta.property",
                        "metaclass",
                        "methods",
                        "methodsview",
                        "mex",
                        "mexext",
                        "mexhost",
                        "mfilename",
                        "mget",
                        "milliseconds",
                        "min",
                        "mink",
                        "minres",
                        "minspantree",
                        "minute",
                        "minutes",
                        "mislocked",
                        "missing",
                        "mkdir",
                        "mkpp",
                        "mldivide",
                        "mlintrpt",
                        "mlock",
                        "mmfileinfo",
                        "mod",
                        "mode",
                        "month",
                        "more",
                        "morebins",
                        "movAbsHDU",
                        "movNamHDU",
                        "movRelHDU",
                        "move",
                        "movefile",
                        "movegui",
                        "movevars",
                        "movie",
                        "movmad",
                        "movmax",
                        "movmean",
                        "movmedian",
                        "movmin",
                        "movprod",
                        "movstd",
                        "movsum",
                        "movvar",
                        "mpower",
                        "mput",
                        "mrdivide",
                        "msgbox",
                        "mtimes",
                        "mu2lin",
                        "multibandread",
                        "multibandwrite",
                        "munlock",
                        "mustBeA",
                        "mustBeFile",
                        "mustBeFinite",
                        "mustBeFloat",
                        "mustBeFolder",
                        "mustBeGreaterThan",
                        "mustBeGreaterThanOrEqual",
                        "mustBeInRange",
                        "mustBeInteger",
                        "mustBeLessThan",
                        "mustBeLessThanOrEqual",
                        "mustBeMember",
                        "mustBeNegative",
                        "mustBeNonNan",
                        "mustBeNonempty",
                        "mustBeNonmissing",
                        "mustBeNonnegative",
                        "mustBeNonpositive",
                        "mustBeNonsparse",
                        "mustBeNonzero",
                        "mustBeNonzeroLengthText",
                        "mustBeNumeric",
                        "mustBeNumericOrLogical",
                        "mustBePositive",
                        "mustBeReal",
                        "mustBeScalarOrEmpty",
                        "mustBeText",
                        "mustBeTextScalar",
                        "mustBeUnderlyingType",
                        "mustBeValidVariableName",
                        "mustBeVector",
                        "namedPattern",
                        "namedargs2cell",
                        "namelengthmax",
                        "nargin",
                        "narginchk",
                        "nargout",
                        "nargoutchk",
                        "native2unicode",
                        "nccreate",
                        "ncdisp",
                        "nchoosek",
                        "ncinfo",
                        "ncread",
                        "ncreadatt",
                        "ncwrite",
                        "ncwriteatt",
                        "ncwriteschema",
                        "ndgrid",
                        "ndims",
                        "nearest",
                        "nearestNeighbor",
                        "nearestvertex",
                        "neighbors",
                        "netcdf.abort",
                        "netcdf.close",
                        "netcdf.copyAtt",
                        "netcdf.create",
                        "netcdf.defDim",
                        "netcdf.defGrp",
                        "netcdf.defVar",
                        "netcdf.defVarChunking",
                        "netcdf.defVarDeflate",
                        "netcdf.defVarFill",
                        "netcdf.defVarFletcher32",
                        "netcdf.delAtt",
                        "netcdf.endDef",
                        "netcdf.getAtt",
                        "netcdf.getChunkCache",
                        "netcdf.getConstant",
                        "netcdf.getConstantNames",
                        "netcdf.getVar",
                        "netcdf.inq",
                        "netcdf.inqAtt",
                        "netcdf.inqAttID",
                        "netcdf.inqAttName",
                        "netcdf.inqDim",
                        "netcdf.inqDimID",
                        "netcdf.inqDimIDs",
                        "netcdf.inqFormat",
                        "netcdf.inqGrpName",
                        "netcdf.inqGrpNameFull",
                        "netcdf.inqGrpParent",
                        "netcdf.inqGrps",
                        "netcdf.inqLibVers",
                        "netcdf.inqNcid",
                        "netcdf.inqUnlimDims",
                        "netcdf.inqVar",
                        "netcdf.inqVarChunking",
                        "netcdf.inqVarDeflate",
                        "netcdf.inqVarFill",
                        "netcdf.inqVarFletcher32",
                        "netcdf.inqVarID",
                        "netcdf.inqVarIDs",
                        "netcdf.open",
                        "netcdf.putAtt",
                        "netcdf.putVar",
                        "netcdf.reDef",
                        "netcdf.renameAtt",
                        "netcdf.renameDim",
                        "netcdf.renameVar",
                        "netcdf.setChunkCache",
                        "netcdf.setDefaultFormat",
                        "netcdf.setFill",
                        "netcdf.sync",
                        "newline",
                        "newplot",
                        "nextpow2",
                        "nexttile",
                        "nnz",
                        "nonzeros",
                        "norm",
                        "normalize",
                        "normest",
                        "notify",
                        "now",
                        "nsidedpoly",
                        "nthroot",
                        "nufft",
                        "nufftn",
                        "null",
                        "num2cell",
                        "num2hex",
                        "num2ruler",
                        "num2str",
                        "numArgumentsFromSubscript",
                        "numRegions",
                        "numboundaries",
                        "numedges",
                        "numel",
                        "numnodes",
                        "numpartitions",
                        "numsides",
                        "nzmax",
                        "ode113",
                        "ode15i",
                        "ode15s",
                        "ode23",
                        "ode23s",
                        "ode23t",
                        "ode23tb",
                        "ode45",
                        "odeget",
                        "odeset",
                        "odextend",
                        "onCleanup",
                        "ones",
                        "open",
                        "openDiskFile",
                        "openFile",
                        "openProject",
                        "openfig",
                        "opengl",
                        "openvar",
                        "optimget",
                        "optimset",
                        "optionalPattern",
                        "ordeig",
                        "orderfields",
                        "ordqz",
                        "ordschur",
                        "orient",
                        "orth",
                        "outdegree",
                        "outedges",
                        "outerjoin",
                        "overlaps",
                        "overlapsrange",
                        "pack",
                        "pad",
                        "padecoef",
                        "pagectranspose",
                        "pagemtimes",
                        "pagetranspose",
                        "pan",
                        "panInteraction",
                        "parallelplot",
                        "pareto",
                        "parquetDatastore",
                        "parquetinfo",
                        "parquetread",
                        "parquetwrite",
                        "partition",
                        "parula",
                        "pascal",
                        "patch",
                        "path",
                        "pathsep",
                        "pathtool",
                        "pattern",
                        "pause",
                        "pbaspect",
                        "pcg",
                        "pchip",
                        "pcode",
                        "pcolor",
                        "pdepe",
                        "pdeval",
                        "peaks",
                        "perimeter",
                        "perl",
                        "perms",
                        "permute",
                        "pi",
                        "pie",
                        "pie3",
                        "pink",
                        "pinv",
                        "planerot",
                        "play",
                        "playblocking",
                        "plot",
                        "plot3",
                        "plotbrowser",
                        "plotedit",
                        "plotmatrix",
                        "plottools",
                        "plus",
                        "pointLocation",
                        "pol2cart",
                        "polaraxes",
                        "polarbubblechart",
                        "polarhistogram",
                        "polarplot",
                        "polarscatter",
                        "poly",
                        "polyarea",
                        "polybuffer",
                        "polyder",
                        "polyeig",
                        "polyfit",
                        "polyint",
                        "polyshape",
                        "polyval",
                        "polyvalm",
                        "posixtime",
                        "possessivePattern",
                        "pow2",
                        "ppval",
                        "predecessors",
                        "prefdir",
                        "preferences",
                        "press",
                        "preview",
                        "primes",
                        "print",
                        "printdlg",
                        "printopt",
                        "printpreview",
                        "prism",
                        "processInputSpecificationChangeImpl",
                        "processTunedPropertiesImpl",
                        "prod",
                        "profile",
                        "propedit",
                        "properties",
                        "propertyeditor",
                        "psi",
                        "publish",
                        "pwd",
                        "pyargs",
                        "pyenv",
                        "qmr",
                        "qr",
                        "qrdelete",
                        "qrinsert",
                        "qrupdate",
                        "quad2d",
                        "quadgk",
                        "quarter",
                        "questdlg",
                        "quit",
                        "quiver",
                        "quiver3",
                        "qz",
                        "rad2deg",
                        "rand",
                        "randi",
                        "randn",
                        "randperm",
                        "rank",
                        "rat",
                        "rats",
                        "rbbox",
                        "rcond",
                        "read",
                        "readATblHdr",
                        "readBTblHdr",
                        "readCard",
                        "readCol",
                        "readFrame",
                        "readImg",
                        "readKey",
                        "readKeyCmplx",
                        "readKeyDbl",
                        "readKeyLongLong",
                        "readKeyLongStr",
                        "readKeyUnit",
                        "readRecord",
                        "readall",
                        "readcell",
                        "readline",
                        "readlines",
                        "readmatrix",
                        "readstruct",
                        "readtable",
                        "readtimetable",
                        "readvars",
                        "real",
                        "reallog",
                        "realmax",
                        "realmin",
                        "realpow",
                        "realsqrt",
                        "record",
                        "recordblocking",
                        "rectangle",
                        "rectint",
                        "recycle",
                        "reducepatch",
                        "reducevolume",
                        "refresh",
                        "refreshSourceControl",
                        "refreshdata",
                        "regexp",
                        "regexpPattern",
                        "regexpi",
                        "regexprep",
                        "regexptranslate",
                        "regionZoomInteraction",
                        "regions",
                        "registerevent",
                        "regmatlabserver",
                        "rehash",
                        "relationaloperators",
                        "release",
                        "releaseImpl",
                        "reload",
                        "rem",
                        "remove",
                        "removeCategory",
                        "removeFile",
                        "removeGroup",
                        "removeLabel",
                        "removePath",
                        "removeReference",
                        "removeSetting",
                        "removeShortcut",
                        "removeShutdownFile",
                        "removeStartupFile",
                        "removeStyle",
                        "removeToolbarExplorationButtons",
                        "removecats",
                        "removets",
                        "removevars",
                        "rename",
                        "renamecats",
                        "renamevars",
                        "rendererinfo",
                        "reordercats",
                        "reordernodes",
                        "repelem",
                        "replace",
                        "replaceBetween",
                        "repmat",
                        "resample",
                        "rescale",
                        "reset",
                        "resetImpl",
                        "reshape",
                        "residue",
                        "restoredefaultpath",
                        "resume",
                        "rethrow",
                        "retime",
                        "reverse",
                        "rgb2gray",
                        "rgb2hsv",
                        "rgb2ind",
                        "rgbplot",
                        "ribbon",
                        "rlim",
                        "rmappdata",
                        "rmboundary",
                        "rmdir",
                        "rmedge",
                        "rmfield",
                        "rmholes",
                        "rmmissing",
                        "rmnode",
                        "rmoutliers",
                        "rmpath",
                        "rmpref",
                        "rmprop",
                        "rmslivers",
                        "rng",
                        "roots",
                        "rosser",
                        "rot90",
                        "rotate",
                        "rotate3d",
                        "rotateInteraction",
                        "round",
                        "rowfun",
                        "rows2vars",
                        "rref",
                        "rsf2csf",
                        "rtickangle",
                        "rtickformat",
                        "rticklabels",
                        "rticks",
                        "ruler2num",
                        "rulerPanInteraction",
                        "run",
                        "runChecks",
                        "runperf",
                        "runtests",
                        "save",
                        "saveObjectImpl",
                        "saveas",
                        "savefig",
                        "saveobj",
                        "savepath",
                        "scale",
                        "scatter",
                        "scatter3",
                        "scatteredInterpolant",
                        "scatterhistogram",
                        "schur",
                        "scroll",
                        "sec",
                        "secd",
                        "sech",
                        "second",
                        "seconds",
                        "semilogx",
                        "semilogy",
                        "sendmail",
                        "serialport",
                        "serialportlist",
                        "set",
                        "setBscale",
                        "setCompressionType",
                        "setDTR",
                        "setHCompScale",
                        "setHCompSmooth",
                        "setProperties",
                        "setRTS",
                        "setTileDim",
                        "setTscale",
                        "setabstime",
                        "setappdata",
                        "setcats",
                        "setdiff",
                        "setenv",
                        "setfield",
                        "setinterpmethod",
                        "setpixelposition",
                        "setpref",
                        "settimeseriesnames",
                        "settings",
                        "setuniformtime",
                        "setup",
                        "setupImpl",
                        "setvaropts",
                        "setvartype",
                        "setxor",
                        "sgtitle",
                        "shading",
                        "sheetnames",
                        "shg",
                        "shiftdim",
                        "shortestpath",
                        "shortestpathtree",
                        "showplottool",
                        "shrinkfaces",
                        "shuffle",
                        "sign",
                        "simplify",
                        "sin",
                        "sind",
                        "single",
                        "sinh",
                        "sinpi",
                        "size",
                        "slice",
                        "smooth3",
                        "smoothdata",
                        "snapnow",
                        "sort",
                        "sortboundaries",
                        "sortregions",
                        "sortrows",
                        "sortx",
                        "sorty",
                        "sound",
                        "soundsc",
                        "spalloc",
                        "sparse",
                        "spaugment",
                        "spconvert",
                        "spdiags",
                        "specular",
                        "speye",
                        "spfun",
                        "sph2cart",
                        "sphere",
                        "spinmap",
                        "spline",
                        "split",
                        "splitapply",
                        "splitlines",
                        "splitvars",
                        "spones",
                        "spparms",
                        "sprand",
                        "sprandn",
                        "sprandsym",
                        "sprank",
                        "spreadsheetDatastore",
                        "spreadsheetImportOptions",
                        "spring",
                        "sprintf",
                        "spy",
                        "sqrt",
                        "sqrtm",
                        "squeeze",
                        "ss2tf",
                        "sscanf",
                        "stack",
                        "stackedplot",
                        "stairs",
                        "standardizeMissing",
                        "start",
                        "startat",
                        "startsWith",
                        "startup",
                        "std",
                        "stem",
                        "stem3",
                        "step",
                        "stepImpl",
                        "stlread",
                        "stlwrite",
                        "stop",
                        "str2double",
                        "str2func",
                        "str2num",
                        "strcat",
                        "strcmp",
                        "strcmpi",
                        "stream2",
                        "stream3",
                        "streamline",
                        "streamparticles",
                        "streamribbon",
                        "streamslice",
                        "streamtube",
                        "strfind",
                        "string",
                        "strings",
                        "strip",
                        "strjoin",
                        "strjust",
                        "strlength",
                        "strncmp",
                        "strncmpi",
                        "strrep",
                        "strsplit",
                        "strtok",
                        "strtrim",
                        "struct",
                        "struct2cell",
                        "struct2table",
                        "structfun",
                        "sub2ind",
                        "subgraph",
                        "subplot",
                        "subsasgn",
                        "subscribe",
                        "subsindex",
                        "subspace",
                        "subsref",
                        "substruct",
                        "subtitle",
                        "subtract",
                        "subvolume",
                        "successors",
                        "sum",
                        "summary",
                        "summer",
                        "superclasses",
                        "surf",
                        "surf2patch",
                        "surface",
                        "surfaceArea",
                        "surfc",
                        "surfl",
                        "surfnorm",
                        "svd",
                        "svds",
                        "svdsketch",
                        "swapbytes",
                        "swarmchart",
                        "swarmchart3",
                        "sylvester",
                        "symamd",
                        "symbfact",
                        "symmlq",
                        "symrcm",
                        "synchronize",
                        "sysobjupdate",
                        "system",
                        "table",
                        "table2array",
                        "table2cell",
                        "table2struct",
                        "table2timetable",
                        "tabularTextDatastore",
                        "tail",
                        "tall",
                        "tallrng",
                        "tan",
                        "tand",
                        "tanh",
                        "tar",
                        "tcpclient",
                        "tempdir",
                        "tempname",
                        "testsuite",
                        "tetramesh",
                        "texlabel",
                        "text",
                        "textBoundary",
                        "textscan",
                        "textwrap",
                        "tfqmr",
                        "thetalim",
                        "thetatickformat",
                        "thetaticklabels",
                        "thetaticks",
                        "thingSpeakRead",
                        "thingSpeakWrite",
                        "throw",
                        "throwAsCaller",
                        "tic",
                        "tiledlayout",
                        "time",
                        "timeit",
                        "timeofday",
                        "timer",
                        "timerange",
                        "timerfind",
                        "timerfindall",
                        "timeseries",
                        "timetable",
                        "timetable2table",
                        "timezones",
                        "title",
                        "toc",
                        "todatenum",
                        "toeplitz",
                        "toolboxdir",
                        "topkrows",
                        "toposort",
                        "trace",
                        "transclosure",
                        "transform",
                        "translate",
                        "transpose",
                        "transreduction",
                        "trapz",
                        "treelayout",
                        "treeplot",
                        "triangulation",
                        "tril",
                        "trimesh",
                        "triplot",
                        "trisurf",
                        "triu",
                        "true",
                        "tscollection",
                        "tsdata.event",
                        "tsearchn",
                        "turbo",
                        "turningdist",
                        "type",
                        "typecast",
                        "tzoffset",
                        "uialert",
                        "uiaxes",
                        "uibutton",
                        "uibuttongroup",
                        "uicheckbox",
                        "uiconfirm",
                        "uicontextmenu",
                        "uicontrol",
                        "uidatepicker",
                        "uidropdown",
                        "uieditfield",
                        "uifigure",
                        "uigauge",
                        "uigetdir",
                        "uigetfile",
                        "uigetpref",
                        "uigridlayout",
                        "uihtml",
                        "uiimage",
                        "uiknob",
                        "uilabel",
                        "uilamp",
                        "uilistbox",
                        "uimenu",
                        "uint16",
                        "uint32",
                        "uint64",
                        "uint8",
                        "uiopen",
                        "uipanel",
                        "uiprogressdlg",
                        "uipushtool",
                        "uiputfile",
                        "uiradiobutton",
                        "uiresume",
                        "uisave",
                        "uisetcolor",
                        "uisetfont",
                        "uisetpref",
                        "uislider",
                        "uispinner",
                        "uistack",
                        "uistyle",
                        "uiswitch",
                        "uitab",
                        "uitabgroup",
                        "uitable",
                        "uitextarea",
                        "uitogglebutton",
                        "uitoggletool",
                        "uitoolbar",
                        "uitree",
                        "uitreenode",
                        "uiwait",
                        "uminus",
                        "underlyingType",
                        "underlyingValue",
                        "unicode2native",
                        "union",
                        "unique",
                        "uniquetol",
                        "unix",
                        "unloadlibrary",
                        "unmesh",
                        "unmkpp",
                        "unregisterallevents",
                        "unregisterevent",
                        "unstack",
                        "unsubscribe",
                        "untar",
                        "unwrap",
                        "unzip",
                        "update",
                        "updateDependencies",
                        "uplus",
                        "upper",
                        "usejava",
                        "userpath",
                        "validateFunctionSignaturesJSON",
                        "validateInputsImpl",
                        "validatePropertiesImpl",
                        "validateattributes",
                        "validatecolor",
                        "validatestring",
                        "values",
                        "vander",
                        "var",
                        "varargin",
                        "varargout",
                        "varfun",
                        "vartype",
                        "vecnorm",
                        "ver",
                        "verLessThan",
                        "version",
                        "vertcat",
                        "vertexAttachments",
                        "vertexNormal",
                        "view",
                        "viewmtx",
                        "visdiff",
                        "volume",
                        "volumebounds",
                        "voronoi",
                        "voronoiDiagram",
                        "voronoin",
                        "wait",
                        "waitbar",
                        "waitfor",
                        "waitforbuttonpress",
                        "warndlg",
                        "warning",
                        "waterfall",
                        "web",
                        "weboptions",
                        "webread",
                        "websave",
                        "webwrite",
                        "week",
                        "weekday",
                        "what",
                        "which",
                        "whitespaceBoundary",
                        "whitespacePattern",
                        "who",
                        "whos",
                        "width",
                        "wildcardPattern",
                        "wilkinson",
                        "winopen",
                        "winqueryreg",
                        "winter",
                        "withinrange",
                        "withtol",
                        "wordcloud",
                        "write",
                        "writeChecksum",
                        "writeCol",
                        "writeComment",
                        "writeDate",
                        "writeHistory",
                        "writeImg",
                        "writeKey",
                        "writeKeyUnit",
                        "writeVideo",
                        "writeall",
                        "writecell",
                        "writeline",
                        "writematrix",
                        "writestruct",
                        "writetable",
                        "writetimetable",
                        "xcorr",
                        "xcov",
                        "xlabel",
                        "xlim",
                        "xline",
                        "xmlread",
                        "xmlwrite",
                        "xor",
                        "xslt",
                        "xtickangle",
                        "xtickformat",
                        "xticklabels",
                        "xticks",
                        "year",
                        "years",
                        "ylabel",
                        "ylim",
                        "yline",
                        "ymd",
                        "ytickangle",
                        "ytickformat",
                        "yticklabels",
                        "yticks",
                        "yyaxis",
                        "yyyymmdd",
                        "zeros",
                        "zip",
                        "zlabel",
                        "zlim",
                        "zoom",
                        "zoomInteraction",
                        "ztickangle",
                        "ztickformat",
                        "zticklabels",
                        "zticks",
                    ],
                    prefix=r"(?<!\.)(",  # Exclude field names
                    suffix=r")\b"
                ),
                Name.Builtin
            ),

            # line continuation with following comment:
            (r'(\.\.\.)(.*)$', bygroups(Keyword, Comment)),

            # command form:
            # "How MATLAB Recognizes Command Syntax" specifies that an operator
            # is recognized if it is either surrounded by spaces or by no
            # spaces on both sides (this allows distinguishing `cd ./foo` from
            # `cd ./ foo`.).  Here, the regex checks that the first word in the
            # line is not followed by <spaces> and then
            # (equal | open-parenthesis | <operator><space> | <space>).
            (rf'(?:^|(?<=;))(\s*)(\w+)(\s+)(?!=|\(|{_operators}\s|\s)',
             bygroups(Whitespace, Name, Whitespace), 'commandargs'),

            include('expressions')
        ],
        'blockcomment': [
            (r'^\s*%\}', Comment.Multiline, '#pop'),
            (r'^.*\n', Comment.Multiline),
            (r'.', Comment.Multiline),
        ],
        'deffunc': [
            (r'(\s*)(?:(\S+)(\s*)(=)(\s*))?(.+)(\()(.*)(\))(\s*)',
             bygroups(Whitespace, Text, Whitespace, Punctuation,
                      Whitespace, Name.Function, Punctuation, Text,
                      Punctuation, Whitespace), '#pop'),
            # function with no args
            (r'(\s*)([a-zA-Z_]\w*)',
             bygroups(Whitespace, Name.Function), '#pop'),
        ],
        'propattrs': [
            (r'(\w+)(\s*)(=)(\s*)(\d+)',
             bygroups(Name.Builtin, Whitespace, Punctuation, Whitespace,
                      Number)),
            (r'(\w+)(\s*)(=)(\s*)([a-zA-Z]\w*)',
             bygroups(Name.Builtin, Whitespace, Punctuation, Whitespace,
                      Keyword)),
            (r',', Punctuation),
            (r'\)', Punctuation, '#pop'),
            (r'\s+', Whitespace),
            (r'.', Text),
        ],
        'defprops': [
            (r'%\{\s*\n', Comment.Multiline, 'blockcomment'),
            (r'%.*$', Comment),
            (r'(?<!\.)end\b', Keyword, '#pop'),
            include('expressions'),
        ],
        'string': [
            (r"[^']*'", String, '#pop'),
        ],
        'commandargs': [
            # If an equal sign or other operator is encountered, this
            # isn't a command. It might be a variable assignment or
            # comparison operation with multiple spaces before the
            # equal sign or operator
            (r"=", Punctuation, '#pop'),
            (_operators, Operator, '#pop'),
            (r"[ \t]+", Whitespace),
            ("'[^']*'", String),
            (r"[^';\s]+", String),
            (";", Punctuation, '#pop'),
            default('#pop'),
        ]
    }

    def analyse_text(text):
        # function declaration.
        first_non_comment = next((line for line in text.splitlines()
                                  if not re.match(r'^\s*%', text)), '').strip()
        if (first_non_comment.startswith('function')
                and '{' not in first_non_comment):
            return 1.
        # comment
        elif re.search(r'^\s*%', text, re.M):
            return 0.2
        # system cmd
        elif re.search(r'^!\w+', text, re.M):
            return 0.2


line_re  = re.compile('.*?\n')


class MatlabSessionLexer(Lexer):
    """
    For Matlab sessions.  Modeled after PythonConsoleLexer.
    Contributed by Ken Schutte <kschutte@csail.mit.edu>.
    """
    name = 'Matlab session'
    aliases = ['matlabsession']
    url = 'https://www.mathworks.com/products/matlab.html'
    version_added = '0.10'
    _example = "matlabsession/matlabsession_sample.txt"

    def get_tokens_unprocessed(self, text):
        mlexer = MatlabLexer(**self.options)

        curcode = ''
        insertions = []
        continuation = False

        for match in line_re.finditer(text):
            line = match.group()

            if line.startswith('>> '):
                insertions.append((len(curcode),
                                   [(0, Generic.Prompt, line[:3])]))
                curcode += line[3:]

            elif line.startswith('>>'):
                insertions.append((len(curcode),
                                   [(0, Generic.Prompt, line[:2])]))
                curcode += line[2:]

            elif line.startswith('???'):

                idx = len(curcode)

                # without is showing error on same line as before...?
                # line = "\n" + line
                token = (0, Generic.Traceback, line)
                insertions.append((idx, [token]))
            elif continuation and insertions:
                # line_start is the length of the most recent prompt symbol
                line_start = len(insertions[-1][-1][-1])
                # Set leading spaces with the length of the prompt to be a generic prompt
                # This keeps code aligned when prompts are removed, say with some Javascript
                if line.startswith(' '*line_start):
                    insertions.append(
                        (len(curcode), [(0, Generic.Prompt, line[:line_start])]))
                    curcode += line[line_start:]
                else:
                    curcode += line
            else:
                if curcode:
                    yield from do_insertions(
                        insertions, mlexer.get_tokens_unprocessed(curcode))
                    curcode = ''
                    insertions = []

                yield match.start(), Generic.Output, line

            # Does not allow continuation if a comment is included after the ellipses.
            # Continues any line that ends with ..., even comments (lines that start with %)
            if line.strip().endswith('...'):
                continuation = True
            else:
                continuation = False

        if curcode:  # or item:
            yield from do_insertions(
                insertions, mlexer.get_tokens_unprocessed(curcode))


class OctaveLexer(RegexLexer):
    """
    For GNU Octave source code.
    """
    name = 'Octave'
    url = 'https://www.gnu.org/software/octave/index'
    aliases = ['octave']
    filenames = ['*.m']
    mimetypes = ['text/octave']
    version_added = '1.5'

    # These lists are generated automatically.
    # Run the following in bash shell:
    #
    # First dump all of the Octave manual into a plain text file:
    #
    #   $ info octave --subnodes -o octave-manual
    #
    # Now grep through it:

    # for i in \
    #     "Built-in Function" "Command" "Function File" \
    #     "Loadable Function" "Mapping Function";
    # do
    #     perl -e '@name = qw('"$i"');
    #              print lc($name[0]),"_kw = [\n"';
    #
    #     perl -n -e 'print "\"$1\",\n" if /-- '"$i"': .* (\w*) \(/;' \
    #         octave-manual | sort | uniq ;
    #     echo "]" ;
    #     echo;
    # done

    # taken from Octave Mercurial changeset 8cc154f45e37 (30-jan-2011)

    builtin_kw = (
        "addlistener", "addpath", "addproperty", "all",
        "and", "any", "argnames", "argv", "assignin",
        "atexit", "autoload",
        "available_graphics_toolkits", "beep_on_error",
        "bitand", "bitmax", "bitor", "bitshift", "bitxor",
        "cat", "cell", "cellstr", "char", "class", "clc",
        "columns", "command_line_path",
        "completion_append_char", "completion_matches",
        "complex", "confirm_recursive_rmdir", "cputime",
        "crash_dumps_octave_core", "ctranspose", "cumprod",
        "cumsum", "debug_on_error", "debug_on_interrupt",
        "debug_on_warning", "default_save_options",
        "dellistener", "diag", "diff", "disp",
        "doc_cache_file", "do_string_escapes", "double",
        "drawnow", "e", "echo_executing_commands", "eps",
        "eq", "errno", "errno_list", "error", "eval",
        "evalin", "exec", "exist", "exit", "eye", "false",
        "fclear", "fclose", "fcntl", "fdisp", "feof",
        "ferror", "feval", "fflush", "fgetl", "fgets",
        "fieldnames", "file_in_loadpath", "file_in_path",
        "filemarker", "filesep", "find_dir_in_path",
        "fixed_point_format", "fnmatch", "fopen", "fork",
        "formula", "fprintf", "fputs", "fread", "freport",
        "frewind", "fscanf", "fseek", "fskipl", "ftell",
        "functions", "fwrite", "ge", "genpath", "get",
        "getegid", "getenv", "geteuid", "getgid",
        "getpgrp", "getpid", "getppid", "getuid", "glob",
        "gt", "gui_mode", "history_control",
        "history_file", "history_size",
        "history_timestamp_format_string", "home",
        "horzcat", "hypot", "ifelse",
        "ignore_function_time_stamp", "inferiorto",
        "info_file", "info_program", "inline", "input",
        "intmax", "intmin", "ipermute",
        "is_absolute_filename", "isargout", "isbool",
        "iscell", "iscellstr", "ischar", "iscomplex",
        "isempty", "isfield", "isfloat", "isglobal",
        "ishandle", "isieee", "isindex", "isinteger",
        "islogical", "ismatrix", "ismethod", "isnull",
        "isnumeric", "isobject", "isreal",
        "is_rooted_relative_filename", "issorted",
        "isstruct", "isvarname", "kbhit", "keyboard",
        "kill", "lasterr", "lasterror", "lastwarn",
        "ldivide", "le", "length", "link", "linspace",
        "logical", "lstat", "lt", "make_absolute_filename",
        "makeinfo_program", "max_recursion_depth", "merge",
        "methods", "mfilename", "minus", "mislocked",
        "mkdir", "mkfifo", "mkstemp", "mldivide", "mlock",
        "mouse_wheel_zoom", "mpower", "mrdivide", "mtimes",
        "munlock", "nargin", "nargout",
        "native_float_format", "ndims", "ne", "nfields",
        "nnz", "norm", "not", "numel", "nzmax",
        "octave_config_info", "octave_core_file_limit",
        "octave_core_file_name",
        "octave_core_file_options", "ones", "or",
        "output_max_field_width", "output_precision",
        "page_output_immediately", "page_screen_output",
        "path", "pathsep", "pause", "pclose", "permute",
        "pi", "pipe", "plus", "popen", "power",
        "print_empty_dimensions", "printf",
        "print_struct_array_contents", "prod",
        "program_invocation_name", "program_name",
        "putenv", "puts", "pwd", "quit", "rats", "rdivide",
        "readdir", "readlink", "read_readline_init_file",
        "realmax", "realmin", "rehash", "rename",
        "repelems", "re_read_readline_init_file", "reset",
        "reshape", "resize", "restoredefaultpath",
        "rethrow", "rmdir", "rmfield", "rmpath", "rows",
        "save_header_format_string", "save_precision",
        "saving_history", "scanf", "set", "setenv",
        "shell_cmd", "sighup_dumps_octave_core",
        "sigterm_dumps_octave_core", "silent_functions",
        "single", "size", "size_equal", "sizemax",
        "sizeof", "sleep", "source", "sparse_auto_mutate",
        "split_long_rows", "sprintf", "squeeze", "sscanf",
        "stat", "stderr", "stdin", "stdout", "strcmp",
        "strcmpi", "string_fill_char", "strncmp",
        "strncmpi", "struct", "struct_levels_to_print",
        "strvcat", "subsasgn", "subsref", "sum", "sumsq",
        "superiorto", "suppress_verbose_help_message",
        "symlink", "system", "tic", "tilde_expand",
        "times", "tmpfile", "tmpnam", "toc", "toupper",
        "transpose", "true", "typeinfo", "umask", "uminus",
        "uname", "undo_string_escapes", "unlink", "uplus",
        "upper", "usage", "usleep", "vec", "vectorize",
        "vertcat", "waitpid", "warning", "warranty",
        "whos_line_format", "yes_or_no", "zeros",
        "inf", "Inf", "nan", "NaN")

    command_kw = ("close", "load", "who", "whos")

    function_kw = (
        "accumarray", "accumdim", "acosd", "acotd",
        "acscd", "addtodate", "allchild", "ancestor",
        "anova", "arch_fit", "arch_rnd", "arch_test",
        "area", "arma_rnd", "arrayfun", "ascii", "asctime",
        "asecd", "asind", "assert", "atand",
        "autoreg_matrix", "autumn", "axes", "axis", "bar",
        "barh", "bartlett", "bartlett_test", "beep",
        "betacdf", "betainv", "betapdf", "betarnd",
        "bicgstab", "bicubic", "binary", "binocdf",
        "binoinv", "binopdf", "binornd", "bitcmp",
        "bitget", "bitset", "blackman", "blanks",
        "blkdiag", "bone", "box", "brighten", "calendar",
        "cast", "cauchy_cdf", "cauchy_inv", "cauchy_pdf",
        "cauchy_rnd", "caxis", "celldisp", "center", "cgs",
        "chisquare_test_homogeneity",
        "chisquare_test_independence", "circshift", "cla",
        "clabel", "clf", "clock", "cloglog", "closereq",
        "colon", "colorbar", "colormap", "colperm",
        "comet", "common_size", "commutation_matrix",
        "compan", "compare_versions", "compass",
        "computer", "cond", "condest", "contour",
        "contourc", "contourf", "contrast", "conv",
        "convhull", "cool", "copper", "copyfile", "cor",
        "corrcoef", "cor_test", "cosd", "cotd", "cov",
        "cplxpair", "cross", "cscd", "cstrcat", "csvread",
        "csvwrite", "ctime", "cumtrapz", "curl", "cut",
        "cylinder", "date", "datenum", "datestr",
        "datetick", "datevec", "dblquad", "deal",
        "deblank", "deconv", "delaunay", "delaunayn",
        "delete", "demo", "detrend", "diffpara", "diffuse",
        "dir", "discrete_cdf", "discrete_inv",
        "discrete_pdf", "discrete_rnd", "display",
        "divergence", "dlmwrite", "dos", "dsearch",
        "dsearchn", "duplication_matrix", "durbinlevinson",
        "ellipsoid", "empirical_cdf", "empirical_inv",
        "empirical_pdf", "empirical_rnd", "eomday",
        "errorbar", "etime", "etreeplot", "example",
        "expcdf", "expinv", "expm", "exppdf", "exprnd",
        "ezcontour", "ezcontourf", "ezmesh", "ezmeshc",
        "ezplot", "ezpolar", "ezsurf", "ezsurfc", "factor",
        "factorial", "fail", "fcdf", "feather", "fftconv",
        "fftfilt", "fftshift", "figure", "fileattrib",
        "fileparts", "fill", "findall", "findobj",
        "findstr", "finv", "flag", "flipdim", "fliplr",
        "flipud", "fpdf", "fplot", "fractdiff", "freqz",
        "freqz_plot", "frnd", "fsolve",
        "f_test_regression", "ftp", "fullfile", "fzero",
        "gamcdf", "gaminv", "gampdf", "gamrnd", "gca",
        "gcbf", "gcbo", "gcf", "genvarname", "geocdf",
        "geoinv", "geopdf", "geornd", "getfield", "ginput",
        "glpk", "gls", "gplot", "gradient",
        "graphics_toolkit", "gray", "grid", "griddata",
        "griddatan", "gtext", "gunzip", "gzip", "hadamard",
        "hamming", "hankel", "hanning", "hggroup",
        "hidden", "hilb", "hist", "histc", "hold", "hot",
        "hotelling_test", "housh", "hsv", "hurst",
        "hygecdf", "hygeinv", "hygepdf", "hygernd",
        "idivide", "ifftshift", "image", "imagesc",
        "imfinfo", "imread", "imshow", "imwrite", "index",
        "info", "inpolygon", "inputname", "interpft",
        "interpn", "intersect", "invhilb", "iqr", "isa",
        "isdefinite", "isdir", "is_duplicate_entry",
        "isequal", "isequalwithequalnans", "isfigure",
        "ishermitian", "ishghandle", "is_leap_year",
        "isletter", "ismac", "ismember", "ispc", "isprime",
        "isprop", "isscalar", "issquare", "isstrprop",
        "issymmetric", "isunix", "is_valid_file_id",
        "isvector", "jet", "kendall",
        "kolmogorov_smirnov_cdf",
        "kolmogorov_smirnov_test", "kruskal_wallis_test",
        "krylov", "kurtosis", "laplace_cdf", "laplace_inv",
        "laplace_pdf", "laplace_rnd", "legend", "legendre",
        "license", "line", "linkprop", "list_primes",
        "loadaudio", "loadobj", "logistic_cdf",
        "logistic_inv", "logistic_pdf", "logistic_rnd",
        "logit", "loglog", "loglogerr", "logm", "logncdf",
        "logninv", "lognpdf", "lognrnd", "logspace",
        "lookfor", "ls_command", "lsqnonneg", "magic",
        "mahalanobis", "manova", "matlabroot",
        "mcnemar_test", "mean", "meansq", "median", "menu",
        "mesh", "meshc", "meshgrid", "meshz", "mexext",
        "mget", "mkpp", "mode", "moment", "movefile",
        "mpoles", "mput", "namelengthmax", "nargchk",
        "nargoutchk", "nbincdf", "nbininv", "nbinpdf",
        "nbinrnd", "nchoosek", "ndgrid", "newplot", "news",
        "nonzeros", "normcdf", "normest", "norminv",
        "normpdf", "normrnd", "now", "nthroot", "null",
        "ocean", "ols", "onenormest", "optimget",
        "optimset", "orderfields", "orient", "orth",
        "pack", "pareto", "parseparams", "pascal", "patch",
        "pathdef", "pcg", "pchip", "pcolor", "pcr",
        "peaks", "periodogram", "perl", "perms", "pie",
        "pink", "planerot", "playaudio", "plot",
        "plotmatrix", "plotyy", "poisscdf", "poissinv",
        "poisspdf", "poissrnd", "polar", "poly",
        "polyaffine", "polyarea", "polyderiv", "polyfit",
        "polygcd", "polyint", "polyout", "polyreduce",
        "polyval", "polyvalm", "postpad", "powerset",
        "ppder", "ppint", "ppjumps", "ppplot", "ppval",
        "pqpnonneg", "prepad", "primes", "print",
        "print_usage", "prism", "probit", "qp", "qqplot",
        "quadcc", "quadgk", "quadl", "quadv", "quiver",
        "qzhess", "rainbow", "randi", "range", "rank",
        "ranks", "rat", "reallog", "realpow", "realsqrt",
        "record", "rectangle_lw", "rectangle_sw",
        "rectint", "refresh", "refreshdata",
        "regexptranslate", "repmat", "residue", "ribbon",
        "rindex", "roots", "rose", "rosser", "rotdim",
        "rref", "run", "run_count", "rundemos", "run_test",
        "runtests", "saveas", "saveaudio", "saveobj",
        "savepath", "scatter", "secd", "semilogx",
        "semilogxerr", "semilogy", "semilogyerr",
        "setaudio", "setdiff", "setfield", "setxor",
        "shading", "shift", "shiftdim", "sign_test",
        "sinc", "sind", "sinetone", "sinewave", "skewness",
        "slice", "sombrero", "sortrows", "spaugment",
        "spconvert", "spdiags", "spearman", "spectral_adf",
        "spectral_xdf", "specular", "speed", "spencer",
        "speye", "spfun", "sphere", "spinmap", "spline",
        "spones", "sprand", "sprandn", "sprandsym",
        "spring", "spstats", "spy", "sqp", "stairs",
        "statistics", "std", "stdnormal_cdf",
        "stdnormal_inv", "stdnormal_pdf", "stdnormal_rnd",
        "stem", "stft", "strcat", "strchr", "strjust",
        "strmatch", "strread", "strsplit", "strtok",
        "strtrim", "strtrunc", "structfun", "studentize",
        "subplot", "subsindex", "subspace", "substr",
        "substruct", "summer", "surf", "surface", "surfc",
        "surfl", "surfnorm", "svds", "swapbytes",
        "sylvester_matrix", "symvar", "synthesis", "table",
        "tand", "tar", "tcdf", "tempdir", "tempname",
        "test", "text", "textread", "textscan", "tinv",
        "title", "toeplitz", "tpdf", "trace", "trapz",
        "treelayout", "treeplot", "triangle_lw",
        "triangle_sw", "tril", "trimesh", "triplequad",
        "triplot", "trisurf", "triu", "trnd", "tsearchn",
        "t_test", "t_test_regression", "type", "unidcdf",
        "unidinv", "unidpdf", "unidrnd", "unifcdf",
        "unifinv", "unifpdf", "unifrnd", "union", "unique",
        "unix", "unmkpp", "unpack", "untabify", "untar",
        "unwrap", "unzip", "u_test", "validatestring",
        "vander", "var", "var_test", "vech", "ver",
        "version", "view", "voronoi", "voronoin",
        "waitforbuttonpress", "wavread", "wavwrite",
        "wblcdf", "wblinv", "wblpdf", "wblrnd", "weekday",
        "welch_test", "what", "white", "whitebg",
        "wienrnd", "wilcoxon_test", "wilkinson", "winter",
        "xlabel", "xlim", "ylabel", "yulewalker", "zip",
        "zlabel", "z_test")

    loadable_kw = (
        "airy", "amd", "balance", "besselh", "besseli",
        "besselj", "besselk", "bessely", "bitpack",
        "bsxfun", "builtin", "ccolamd", "cellfun",
        "cellslices", "chol", "choldelete", "cholinsert",
        "cholinv", "cholshift", "cholupdate", "colamd",
        "colloc", "convhulln", "convn", "csymamd",
        "cummax", "cummin", "daspk", "daspk_options",
        "dasrt", "dasrt_options", "dassl", "dassl_options",
        "dbclear", "dbdown", "dbstack", "dbstatus",
        "dbstop", "dbtype", "dbup", "dbwhere", "det",
        "dlmread", "dmperm", "dot", "eig", "eigs",
        "endgrent", "endpwent", "etree", "fft", "fftn",
        "fftw", "filter", "find", "full", "gcd",
        "getgrent", "getgrgid", "getgrnam", "getpwent",
        "getpwnam", "getpwuid", "getrusage", "givens",
        "gmtime", "gnuplot_binary", "hess", "ifft",
        "ifftn", "inv", "isdebugmode", "issparse", "kron",
        "localtime", "lookup", "lsode", "lsode_options",
        "lu", "luinc", "luupdate", "matrix_type", "max",
        "min", "mktime", "pinv", "qr", "qrdelete",
        "qrinsert", "qrshift", "qrupdate", "quad",
        "quad_options", "qz", "rand", "rande", "randg",
        "randn", "randp", "randperm", "rcond", "regexp",
        "regexpi", "regexprep", "schur", "setgrent",
        "setpwent", "sort", "spalloc", "sparse", "spparms",
        "sprank", "sqrtm", "strfind", "strftime",
        "strptime", "strrep", "svd", "svd_driver", "syl",
        "symamd", "symbfact", "symrcm", "time", "tsearch",
        "typecast", "urlread", "urlwrite")

    mapping_kw = (
        "abs", "acos", "acosh", "acot", "acoth", "acsc",
        "acsch", "angle", "arg", "asec", "asech", "asin",
        "asinh", "atan", "atanh", "beta", "betainc",
        "betaln", "bincoeff", "cbrt", "ceil", "conj", "cos",
        "cosh", "cot", "coth", "csc", "csch", "erf", "erfc",
        "erfcx", "erfinv", "exp", "finite", "fix", "floor",
        "fmod", "gamma", "gammainc", "gammaln", "imag",
        "isalnum", "isalpha", "isascii", "iscntrl",
        "isdigit", "isfinite", "isgraph", "isinf",
        "islower", "isna", "isnan", "isprint", "ispunct",
        "isspace", "isupper", "isxdigit", "lcm", "lgamma",
        "log", "lower", "mod", "real", "rem", "round",
        "roundb", "sec", "sech", "sign", "sin", "sinh",
        "sqrt", "tan", "tanh", "toascii", "tolower", "xor")

    builtin_consts = (
        "EDITOR", "EXEC_PATH", "I", "IMAGE_PATH", "NA",
        "OCTAVE_HOME", "OCTAVE_VERSION", "PAGER",
        "PAGER_FLAGS", "SEEK_CUR", "SEEK_END", "SEEK_SET",
        "SIG", "S_ISBLK", "S_ISCHR", "S_ISDIR", "S_ISFIFO",
        "S_ISLNK", "S_ISREG", "S_ISSOCK", "WCONTINUE",
        "WCOREDUMP", "WEXITSTATUS", "WIFCONTINUED",
        "WIFEXITED", "WIFSIGNALED", "WIFSTOPPED", "WNOHANG",
        "WSTOPSIG", "WTERMSIG", "WUNTRACED")

    tokens = {
        'root': [
            (r'%\{\s*\n', Comment.Multiline, 'percentblockcomment'),
            (r'#\{\s*\n', Comment.Multiline, 'hashblockcomment'),
            (r'[%#].*$', Comment),
            (r'^\s*function\b', Keyword, 'deffunc'),

            # from 'iskeyword' on hg changeset 8cc154f45e37
            (words((
                '__FILE__', '__LINE__', 'break', 'case', 'catch', 'classdef',
                'continue', 'do', 'else', 'elseif', 'end', 'end_try_catch',
                'end_unwind_protect', 'endclassdef', 'endevents', 'endfor',
                'endfunction', 'endif', 'endmethods', 'endproperties', 'endswitch',
                'endwhile', 'events', 'for', 'function', 'get', 'global', 'if',
                'methods', 'otherwise', 'persistent', 'properties', 'return',
                'set', 'static', 'switch', 'try', 'until', 'unwind_protect',
                'unwind_protect_cleanup', 'while'), suffix=r'\b'),
             Keyword),

            (words(builtin_kw + command_kw + function_kw + loadable_kw + mapping_kw,
                   suffix=r'\b'),  Name.Builtin),

            (words(builtin_consts, suffix=r'\b'), Name.Constant),

            # operators in Octave but not Matlab:
            (r'-=|!=|!|/=|--', Operator),
            # operators:
            (r'-|==|~=|<|>|<=|>=|&&|&|~|\|\|?', Operator),
            # operators in Octave but not Matlab requiring escape for re:
            (r'\*=|\+=|\^=|\/=|\\=|\*\*|\+\+|\.\*\*', Operator),
            # operators requiring escape for re:
            (r'\.\*|\*|\+|\.\^|\^|\.\\|\.\/|\/|\\', Operator),


            # punctuation:
            (r'[\[\](){}:@.,]', Punctuation),
            (r'=|:|;', Punctuation),

            (r'"[^"]*"', String),

            (r'(\d+\.\d*|\d*\.\d+)([eEf][+-]?[0-9]+)?', Number.Float),
            (r'\d+[eEf][+-]?[0-9]+', Number.Float),
            (r'\d+', Number.Integer),

            # quote can be transpose, instead of string:
            # (not great, but handles common cases...)
            (r'(?<=[\w)\].])\'+', Operator),
            (r'(?<![\w)\].])\'', String, 'string'),

            (r'[a-zA-Z_]\w*', Name),
            (r'\s+', Text),
            (r'.', Text),
        ],
        'percentblockcomment': [
            (r'^\s*%\}', Comment.Multiline, '#pop'),
            (r'^.*\n', Comment.Multiline),
            (r'.', Comment.Multiline),
        ],
        'hashblockcomment': [
            (r'^\s*#\}', Comment.Multiline, '#pop'),
            (r'^.*\n', Comment.Multiline),
            (r'.', Comment.Multiline),
        ],
        'string': [
            (r"[^']*'", String, '#pop'),
        ],
        'deffunc': [
            (r'(\s*)(?:(\S+)(\s*)(=)(\s*))?(.+)(\()(.*)(\))(\s*)',
             bygroups(Whitespace, Text, Whitespace, Punctuation,
                      Whitespace, Name.Function, Punctuation, Text,
                      Punctuation, Whitespace), '#pop'),
            # function with no args
            (r'(\s*)([a-zA-Z_]\w*)',
             bygroups(Whitespace, Name.Function), '#pop'),
        ],
    }

    def analyse_text(text):
        """Octave is quite hard to spot, and it looks like Matlab as well."""
        return 0


class ScilabLexer(RegexLexer):
    """
    For Scilab source code.
    """
    name = 'Scilab'
    url = 'https://www.scilab.org/'
    aliases = ['scilab']
    filenames = ['*.sci', '*.sce', '*.tst']
    mimetypes = ['text/scilab']
    version_added = '1.5'

    tokens = {
        'root': [
            (r'//.*?$', Comment.Single),
            (r'^\s*function\b', Keyword, 'deffunc'),

            (words((
                '__FILE__', '__LINE__', 'break', 'case', 'catch', 'classdef', 'continue', 'do', 'else',
                'elseif', 'end', 'end_try_catch', 'end_unwind_protect', 'endclassdef',
                'endevents', 'endfor', 'endfunction', 'endif', 'endmethods', 'endproperties',
                'endswitch', 'endwhile', 'events', 'for', 'function', 'get', 'global', 'if', 'methods',
                'otherwise', 'persistent', 'properties', 'return', 'set', 'static', 'switch', 'try',
                'until', 'unwind_protect', 'unwind_protect_cleanup', 'while'), suffix=r'\b'),
             Keyword),

            (words(_scilab_builtins.functions_kw +
                   _scilab_builtins.commands_kw +
                   _scilab_builtins.macros_kw, suffix=r'\b'), Name.Builtin),

            (words(_scilab_builtins.variables_kw, suffix=r'\b'), Name.Constant),

            # operators:
            (r'-|==|~=|<|>|<=|>=|&&|&|~|\|\|?', Operator),
            # operators requiring escape for re:
            (r'\.\*|\*|\+|\.\^|\^|\.\\|\.\/|\/|\\', Operator),

            # punctuation:
            (r'[\[\](){}@.,=:;]+', Punctuation),

            (r'"[^"]*"', String),

            # quote can be transpose, instead of string:
            # (not great, but handles common cases...)
            (r'(?<=[\w)\].])\'+', Operator),
            (r'(?<![\w)\].])\'', String, 'string'),

            (r'(\d+\.\d*|\d*\.\d+)([eEf][+-]?[0-9]+)?', Number.Float),
            (r'\d+[eEf][+-]?[0-9]+', Number.Float),
            (r'\d+', Number.Integer),

            (r'[a-zA-Z_]\w*', Name),
            (r'\s+', Whitespace),
            (r'.', Text),
        ],
        'string': [
            (r"[^']*'", String, '#pop'),
            (r'.', String, '#pop'),
        ],
        'deffunc': [
            (r'(\s*)(?:(\S+)(\s*)(=)(\s*))?(.+)(\()(.*)(\))(\s*)',
             bygroups(Whitespace, Text, Whitespace, Punctuation,
                      Whitespace, Name.Function, Punctuation, Text,
                      Punctuation, Whitespace), '#pop'),
            # function with no args
            (r'(\s*)([a-zA-Z_]\w*)', bygroups(Text, Name.Function), '#pop'),
        ],
    }

    # the following is needed to distinguish Scilab and GAP .tst files
    def analyse_text(text):
        score = 0.0

        # Scilab comments (don't appear in e.g. GAP code)
        if re.search(r"^\s*//", text):
            score += 0.1
        if re.search(r"^\s*/\*", text):
            score += 0.1

        return min(score, 1.0)

# === NexusCore/openenv\Lib\site-packages\anthropic\lib\bedrock\_beta.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from ..._compat import cached_property
from ..._resource import SyncAPIResource, AsyncAPIResource
from ._beta_messages import (
    Messages,
    AsyncMessages,
    MessagesWithRawResponse,
    AsyncMessagesWithRawResponse,
    MessagesWithStreamingResponse,
    AsyncMessagesWithStreamingResponse,
)

__all__ = ["Beta", "AsyncBeta"]


class Beta(SyncAPIResource):
    @cached_property
    def messages(self) -> Messages:
        return Messages(self._client)

    @cached_property
    def with_raw_response(self) -> BetaWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return the
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/anthropics/anthropic-sdk-python#accessing-raw-response-data-eg-headers
        """
        return BetaWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> BetaWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/anthropics/anthropic-sdk-python#with_streaming_response
        """
        return BetaWithStreamingResponse(self)


class AsyncBeta(AsyncAPIResource):
    @cached_property
    def messages(self) -> AsyncMessages:
        return AsyncMessages(self._client)

    @cached_property
    def with_raw_response(self) -> AsyncBetaWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return the
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/anthropics/anthropic-sdk-python#accessing-raw-response-data-eg-headers
        """
        return AsyncBetaWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncBetaWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/anthropics/anthropic-sdk-python#with_streaming_response
        """
        return AsyncBetaWithStreamingResponse(self)


class BetaWithRawResponse:
    def __init__(self, beta: Beta) -> None:
        self._beta = beta

    @cached_property
    def messages(self) -> MessagesWithRawResponse:
        return MessagesWithRawResponse(self._beta.messages)


class AsyncBetaWithRawResponse:
    def __init__(self, beta: AsyncBeta) -> None:
        self._beta = beta

    @cached_property
    def messages(self) -> AsyncMessagesWithRawResponse:
        return AsyncMessagesWithRawResponse(self._beta.messages)


class BetaWithStreamingResponse:
    def __init__(self, beta: Beta) -> None:
        self._beta = beta

    @cached_property
    def messages(self) -> MessagesWithStreamingResponse:
        return MessagesWithStreamingResponse(self._beta.messages)


class AsyncBetaWithStreamingResponse:
    def __init__(self, beta: AsyncBeta) -> None:
        self._beta = beta

    @cached_property
    def messages(self) -> AsyncMessagesWithStreamingResponse:
        return AsyncMessagesWithStreamingResponse(self._beta.messages)