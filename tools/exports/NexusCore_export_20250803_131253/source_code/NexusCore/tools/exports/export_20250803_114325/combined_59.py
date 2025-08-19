
# === NexusCore/openenv\Lib\site-packages\pyasn1\codec\ber\decoder.py ===
#
# This file is part of pyasn1 software.
#
# Copyright (c) 2005-2020, Ilya Etingof <etingof@gmail.com>
# License: https://pyasn1.readthedocs.io/en/latest/license.html
#
import io
import os
import sys
import warnings

from pyasn1 import debug
from pyasn1 import error
from pyasn1.codec.ber import eoo
from pyasn1.codec.streaming import asSeekableStream
from pyasn1.codec.streaming import isEndOfStream
from pyasn1.codec.streaming import peekIntoStream
from pyasn1.codec.streaming import readFromStream
from pyasn1.compat import _MISSING
from pyasn1.error import PyAsn1Error
from pyasn1.type import base
from pyasn1.type import char
from pyasn1.type import tag
from pyasn1.type import tagmap
from pyasn1.type import univ
from pyasn1.type import useful

__all__ = ['StreamingDecoder', 'Decoder', 'decode']

LOG = debug.registerLoggee(__name__, flags=debug.DEBUG_DECODER)

noValue = base.noValue

SubstrateUnderrunError = error.SubstrateUnderrunError


class AbstractPayloadDecoder(object):
    protoComponent = None

    def valueDecoder(self, substrate, asn1Spec,
                     tagSet=None, length=None, state=None,
                     decodeFun=None, substrateFun=None,
                     **options):
        """Decode value with fixed byte length.

        The decoder is allowed to consume as many bytes as necessary.
        """
        raise error.PyAsn1Error('SingleItemDecoder not implemented for %s' % (tagSet,))  # TODO: Seems more like an NotImplementedError?

    def indefLenValueDecoder(self, substrate, asn1Spec,
                             tagSet=None, length=None, state=None,
                             decodeFun=None, substrateFun=None,
                             **options):
        """Decode value with undefined length.

        The decoder is allowed to consume as many bytes as necessary.
        """
        raise error.PyAsn1Error('Indefinite length mode decoder not implemented for %s' % (tagSet,)) # TODO: Seems more like an NotImplementedError?

    @staticmethod
    def _passAsn1Object(asn1Object, options):
        if 'asn1Object' not in options:
            options['asn1Object'] = asn1Object

        return options


class AbstractSimplePayloadDecoder(AbstractPayloadDecoder):
    @staticmethod
    def substrateCollector(asn1Object, substrate, length, options):
        for chunk in readFromStream(substrate, length, options):
            yield chunk

    def _createComponent(self, asn1Spec, tagSet, value, **options):
        if options.get('native'):
            return value
        elif asn1Spec is None:
            return self.protoComponent.clone(value, tagSet=tagSet)
        elif value is noValue:
            return asn1Spec
        else:
            return asn1Spec.clone(value)


class RawPayloadDecoder(AbstractSimplePayloadDecoder):
    protoComponent = univ.Any('')

    def valueDecoder(self, substrate, asn1Spec,
                     tagSet=None, length=None, state=None,
                     decodeFun=None, substrateFun=None,
                     **options):
        if substrateFun:
            asn1Object = self._createComponent(asn1Spec, tagSet, '', **options)

            for chunk in substrateFun(asn1Object, substrate, length, options):
                yield chunk

            return

        for value in decodeFun(substrate, asn1Spec, tagSet, length, **options):
            yield value

    def indefLenValueDecoder(self, substrate, asn1Spec,
                             tagSet=None, length=None, state=None,
                             decodeFun=None, substrateFun=None,
                             **options):
        if substrateFun:
            asn1Object = self._createComponent(asn1Spec, tagSet, '', **options)

            for chunk in substrateFun(asn1Object, substrate, length, options):
                yield chunk

            return

        while True:
            for value in decodeFun(
                    substrate, asn1Spec, tagSet, length,
                    allowEoo=True, **options):

                if value is eoo.endOfOctets:
                    return

                yield value


rawPayloadDecoder = RawPayloadDecoder()


class IntegerPayloadDecoder(AbstractSimplePayloadDecoder):
    protoComponent = univ.Integer(0)

    def valueDecoder(self, substrate, asn1Spec,
                     tagSet=None, length=None, state=None,
                     decodeFun=None, substrateFun=None,
                     **options):

        if tagSet[0].tagFormat != tag.tagFormatSimple:
            raise error.PyAsn1Error('Simple tag format expected')

        for chunk in readFromStream(substrate, length, options):
            if isinstance(chunk, SubstrateUnderrunError):
                yield chunk

        if chunk:
            value = int.from_bytes(bytes(chunk), 'big', signed=True)

        else:
            value = 0

        yield self._createComponent(asn1Spec, tagSet, value, **options)


class BooleanPayloadDecoder(IntegerPayloadDecoder):
    protoComponent = univ.Boolean(0)

    def _createComponent(self, asn1Spec, tagSet, value, **options):
        return IntegerPayloadDecoder._createComponent(
            self, asn1Spec, tagSet, value and 1 or 0, **options)


class BitStringPayloadDecoder(AbstractSimplePayloadDecoder):
    protoComponent = univ.BitString(())
    supportConstructedForm = True

    def valueDecoder(self, substrate, asn1Spec,
                     tagSet=None, length=None, state=None,
                     decodeFun=None, substrateFun=None,
                     **options):

        if substrateFun:
            asn1Object = self._createComponent(asn1Spec, tagSet, noValue, **options)

            for chunk in substrateFun(asn1Object, substrate, length, options):
                yield chunk

            return

        if not length:
            raise error.PyAsn1Error('Empty BIT STRING substrate')

        for chunk in isEndOfStream(substrate):
            if isinstance(chunk, SubstrateUnderrunError):
                yield chunk

        if chunk:
            raise error.PyAsn1Error('Empty BIT STRING substrate')

        if tagSet[0].tagFormat == tag.tagFormatSimple:  # XXX what tag to check?

            for trailingBits in readFromStream(substrate, 1, options):
                if isinstance(trailingBits, SubstrateUnderrunError):
                    yield trailingBits

            trailingBits = ord(trailingBits)
            if trailingBits > 7:
                raise error.PyAsn1Error(
                    'Trailing bits overflow %s' % trailingBits
                )

            for chunk in readFromStream(substrate, length - 1, options):
                if isinstance(chunk, SubstrateUnderrunError):
                    yield chunk

            value = self.protoComponent.fromOctetString(
                chunk, internalFormat=True, padding=trailingBits)

            yield self._createComponent(asn1Spec, tagSet, value, **options)

            return

        if not self.supportConstructedForm:
            raise error.PyAsn1Error('Constructed encoding form prohibited '
                                    'at %s' % self.__class__.__name__)

        if LOG:
            LOG('assembling constructed serialization')

        # All inner fragments are of the same type, treat them as octet string
        substrateFun = self.substrateCollector

        bitString = self.protoComponent.fromOctetString(b'', internalFormat=True)

        current_position = substrate.tell()

        while substrate.tell() - current_position < length:
            for component in decodeFun(
                    substrate, self.protoComponent, substrateFun=substrateFun,
                    **options):
                if isinstance(component, SubstrateUnderrunError):
                    yield component

            trailingBits = component[0]
            if trailingBits > 7:
                raise error.PyAsn1Error(
                    'Trailing bits overflow %s' % trailingBits
                )

            bitString = self.protoComponent.fromOctetString(
                component[1:], internalFormat=True,
                prepend=bitString, padding=trailingBits
            )

        yield self._createComponent(asn1Spec, tagSet, bitString, **options)

    def indefLenValueDecoder(self, substrate, asn1Spec,
                             tagSet=None, length=None, state=None,
                             decodeFun=None, substrateFun=None,
                             **options):

        if substrateFun:
            asn1Object = self._createComponent(asn1Spec, tagSet, noValue, **options)

            for chunk in substrateFun(asn1Object, substrate, length, options):
                yield chunk

            return

        # All inner fragments are of the same type, treat them as octet string
        substrateFun = self.substrateCollector

        bitString = self.protoComponent.fromOctetString(b'', internalFormat=True)

        while True:  # loop over fragments

            for component in decodeFun(
                    substrate, self.protoComponent, substrateFun=substrateFun,
                    allowEoo=True, **options):

                if component is eoo.endOfOctets:
                    break

                if isinstance(component, SubstrateUnderrunError):
                    yield component

            if component is eoo.endOfOctets:
                break

            trailingBits = component[0]
            if trailingBits > 7:
                raise error.PyAsn1Error(
                    'Trailing bits overflow %s' % trailingBits
                )

            bitString = self.protoComponent.fromOctetString(
                component[1:], internalFormat=True,
                prepend=bitString, padding=trailingBits
            )

        yield self._createComponent(asn1Spec, tagSet, bitString, **options)


class OctetStringPayloadDecoder(AbstractSimplePayloadDecoder):
    protoComponent = univ.OctetString('')
    supportConstructedForm = True

    def valueDecoder(self, substrate, asn1Spec,
                     tagSet=None, length=None, state=None,
                     decodeFun=None, substrateFun=None,
                     **options):
        if substrateFun:
            asn1Object = self._createComponent(asn1Spec, tagSet, noValue, **options)

            for chunk in substrateFun(asn1Object, substrate, length, options):
                yield chunk

            return

        if tagSet[0].tagFormat == tag.tagFormatSimple:  # XXX what tag to check?
            for chunk in readFromStream(substrate, length, options):
                if isinstance(chunk, SubstrateUnderrunError):
                    yield chunk

            yield self._createComponent(asn1Spec, tagSet, chunk, **options)

            return

        if not self.supportConstructedForm:
            raise error.PyAsn1Error('Constructed encoding form prohibited at %s' % self.__class__.__name__)

        if LOG:
            LOG('assembling constructed serialization')

        # All inner fragments are of the same type, treat them as octet string
        substrateFun = self.substrateCollector

        header = b''

        original_position = substrate.tell()
        # head = popSubstream(substrate, length)
        while substrate.tell() - original_position < length:
            for component in decodeFun(
                    substrate, self.protoComponent, substrateFun=substrateFun,
                    **options):
                if isinstance(component, SubstrateUnderrunError):
                    yield component

            header += component

        yield self._createComponent(asn1Spec, tagSet, header, **options)

    def indefLenValueDecoder(self, substrate, asn1Spec,
                             tagSet=None, length=None, state=None,
                             decodeFun=None, substrateFun=None,
                             **options):
        if substrateFun and substrateFun is not self.substrateCollector:
            asn1Object = self._createComponent(asn1Spec, tagSet, noValue, **options)

            for chunk in substrateFun(asn1Object, substrate, length, options):
                yield chunk

            return

        # All inner fragments are of the same type, treat them as octet string
        substrateFun = self.substrateCollector

        header = b''

        while True:  # loop over fragments

            for component in decodeFun(
                    substrate, self.protoComponent, substrateFun=substrateFun,
                    allowEoo=True, **options):

                if isinstance(component, SubstrateUnderrunError):
                    yield component

                if component is eoo.endOfOctets:
                    break

            if component is eoo.endOfOctets:
                break

            header += component

        yield self._createComponent(asn1Spec, tagSet, header, **options)


class NullPayloadDecoder(AbstractSimplePayloadDecoder):
    protoComponent = univ.Null('')

    def valueDecoder(self, substrate, asn1Spec,
                     tagSet=None, length=None, state=None,
                     decodeFun=None, substrateFun=None,
                     **options):

        if tagSet[0].tagFormat != tag.tagFormatSimple:
            raise error.PyAsn1Error('Simple tag format expected')

        for chunk in readFromStream(substrate, length, options):
            if isinstance(chunk, SubstrateUnderrunError):
                yield chunk

        component = self._createComponent(asn1Spec, tagSet, '', **options)

        if chunk:
            raise error.PyAsn1Error('Unexpected %d-octet substrate for Null' % length)

        yield component


class ObjectIdentifierPayloadDecoder(AbstractSimplePayloadDecoder):
    protoComponent = univ.ObjectIdentifier(())

    def valueDecoder(self, substrate, asn1Spec,
                     tagSet=None, length=None, state=None,
                     decodeFun=None, substrateFun=None,
                     **options):
        if tagSet[0].tagFormat != tag.tagFormatSimple:
            raise error.PyAsn1Error('Simple tag format expected')

        for chunk in readFromStream(substrate, length, options):
            if isinstance(chunk, SubstrateUnderrunError):
                yield chunk

        if not chunk:
            raise error.PyAsn1Error('Empty substrate')

        oid = ()
        index = 0
        substrateLen = len(chunk)
        while index < substrateLen:
            subId = chunk[index]
            index += 1
            if subId < 128:
                oid += (subId,)
            elif subId > 128:
                # Construct subid from a number of octets
                nextSubId = subId
                subId = 0
                while nextSubId >= 128:
                    subId = (subId << 7) + (nextSubId & 0x7F)
                    if index >= substrateLen:
                        raise error.SubstrateUnderrunError(
                            'Short substrate for sub-OID past %s' % (oid,)
                        )
                    nextSubId = chunk[index]
                    index += 1
                oid += ((subId << 7) + nextSubId,)
            elif subId == 128:
                # ASN.1 spec forbids leading zeros (0x80) in OID
                # encoding, tolerating it opens a vulnerability. See
                # https://www.esat.kuleuven.be/cosic/publications/article-1432.pdf
                # page 7
                raise error.PyAsn1Error('Invalid octet 0x80 in OID encoding')

        # Decode two leading arcs
        if 0 <= oid[0] <= 39:
            oid = (0,) + oid
        elif 40 <= oid[0] <= 79:
            oid = (1, oid[0] - 40) + oid[1:]
        elif oid[0] >= 80:
            oid = (2, oid[0] - 80) + oid[1:]
        else:
            raise error.PyAsn1Error('Malformed first OID octet: %s' % chunk[0])

        yield self._createComponent(asn1Spec, tagSet, oid, **options)


class RelativeOIDPayloadDecoder(AbstractSimplePayloadDecoder):
    protoComponent = univ.RelativeOID(())

    def valueDecoder(self, substrate, asn1Spec,
                     tagSet=None, length=None, state=None,
                     decodeFun=None, substrateFun=None,
                     **options):
        if tagSet[0].tagFormat != tag.tagFormatSimple:
            raise error.PyAsn1Error('Simple tag format expected')

        for chunk in readFromStream(substrate, length, options):
            if isinstance(chunk, SubstrateUnderrunError):
                yield chunk

        if not chunk:
            raise error.PyAsn1Error('Empty substrate')

        reloid = ()
        index = 0
        substrateLen = len(chunk)
        while index < substrateLen:
            subId = chunk[index]
            index += 1
            if subId < 128:
                reloid += (subId,)
            elif subId > 128:
                # Construct subid from a number of octets
                nextSubId = subId
                subId = 0
                while nextSubId >= 128:
                    subId = (subId << 7) + (nextSubId & 0x7F)
                    if index >= substrateLen:
                        raise error.SubstrateUnderrunError(
                            'Short substrate for sub-OID past %s' % (reloid,)
                        )
                    nextSubId = chunk[index]
                    index += 1
                reloid += ((subId << 7) + nextSubId,)
            elif subId == 128:
                # ASN.1 spec forbids leading zeros (0x80) in OID
                # encoding, tolerating it opens a vulnerability. See
                # https://www.esat.kuleuven.be/cosic/publications/article-1432.pdf
                # page 7
                raise error.PyAsn1Error('Invalid octet 0x80 in RELATIVE-OID encoding')

        yield self._createComponent(asn1Spec, tagSet, reloid, **options)


class RealPayloadDecoder(AbstractSimplePayloadDecoder):
    protoComponent = univ.Real()

    def valueDecoder(self, substrate, asn1Spec,
                     tagSet=None, length=None, state=None,
                     decodeFun=None, substrateFun=None,
                     **options):
        if tagSet[0].tagFormat != tag.tagFormatSimple:
            raise error.PyAsn1Error('Simple tag format expected')

        for chunk in readFromStream(substrate, length, options):
            if isinstance(chunk, SubstrateUnderrunError):
                yield chunk

        if not chunk:
            yield self._createComponent(asn1Spec, tagSet, 0.0, **options)
            return

        fo = chunk[0]
        chunk = chunk[1:]
        if fo & 0x80:  # binary encoding
            if not chunk:
                raise error.PyAsn1Error("Incomplete floating-point value")

            if LOG:
                LOG('decoding binary encoded REAL')

            n = (fo & 0x03) + 1

            if n == 4:
                n = chunk[0]
                chunk = chunk[1:]

            eo, chunk = chunk[:n], chunk[n:]

            if not eo or not chunk:
                raise error.PyAsn1Error('Real exponent screwed')

            e = eo[0] & 0x80 and -1 or 0

            while eo:  # exponent
                e <<= 8
                e |= eo[0]
                eo = eo[1:]

            b = fo >> 4 & 0x03  # base bits

            if b > 2:
                raise error.PyAsn1Error('Illegal Real base')

            if b == 1:  # encbase = 8
                e *= 3

            elif b == 2:  # encbase = 16
                e *= 4
            p = 0

            while chunk:  # value
                p <<= 8
                p |= chunk[0]
                chunk = chunk[1:]

            if fo & 0x40:  # sign bit
                p = -p

            sf = fo >> 2 & 0x03  # scale bits
            p *= 2 ** sf
            value = (p, 2, e)

        elif fo & 0x40:  # infinite value
            if LOG:
                LOG('decoding infinite REAL')

            value = fo & 0x01 and '-inf' or 'inf'

        elif fo & 0xc0 == 0:  # character encoding
            if not chunk:
                raise error.PyAsn1Error("Incomplete floating-point value")

            if LOG:
                LOG('decoding character encoded REAL')

            try:
                if fo & 0x3 == 0x1:  # NR1
                    value = (int(chunk), 10, 0)

                elif fo & 0x3 == 0x2:  # NR2
                    value = float(chunk)

                elif fo & 0x3 == 0x3:  # NR3
                    value = float(chunk)

                else:
                    raise error.SubstrateUnderrunError(
                        'Unknown NR (tag %s)' % fo
                    )

            except ValueError:
                raise error.SubstrateUnderrunError(
                    'Bad character Real syntax'
                )

        else:
            raise error.SubstrateUnderrunError(
                'Unknown encoding (tag %s)' % fo
            )

        yield self._createComponent(asn1Spec, tagSet, value, **options)


class AbstractConstructedPayloadDecoder(AbstractPayloadDecoder):
    protoComponent = None


class ConstructedPayloadDecoderBase(AbstractConstructedPayloadDecoder):
    protoRecordComponent = None
    protoSequenceComponent = None

    def _getComponentTagMap(self, asn1Object, idx):
        raise NotImplementedError

    def _getComponentPositionByType(self, asn1Object, tagSet, idx):
        raise NotImplementedError

    def _decodeComponentsSchemaless(
            self, substrate, tagSet=None, decodeFun=None,
            length=None, **options):

        asn1Object = None

        components = []
        componentTypes = set()

        original_position = substrate.tell()

        while length == -1 or substrate.tell() < original_position + length:
            for component in decodeFun(substrate, **options):
                if isinstance(component, SubstrateUnderrunError):
                    yield component

            if length == -1 and component is eoo.endOfOctets:
                break

            components.append(component)
            componentTypes.add(component.tagSet)

            # Now we have to guess is it SEQUENCE/SET or SEQUENCE OF/SET OF
            # The heuristics is:
            # * 1+ components of different types -> likely SEQUENCE/SET
            # * otherwise -> likely SEQUENCE OF/SET OF
            if len(componentTypes) > 1:
                protoComponent = self.protoRecordComponent

            else:
                protoComponent = self.protoSequenceComponent

            asn1Object = protoComponent.clone(
                # construct tagSet from base tag from prototype ASN.1 object
                # and additional tags recovered from the substrate
                tagSet=tag.TagSet(protoComponent.tagSet.baseTag, *tagSet.superTags)
            )

        if LOG:
            LOG('guessed %r container type (pass `asn1Spec` to guide the '
                'decoder)' % asn1Object)

        for idx, component in enumerate(components):
            asn1Object.setComponentByPosition(
                idx, component,
                verifyConstraints=False,
                matchTags=False, matchConstraints=False
            )

        yield asn1Object

    def valueDecoder(self, substrate, asn1Spec,
                     tagSet=None, length=None, state=None,
                     decodeFun=None, substrateFun=None,
                     **options):
        if tagSet[0].tagFormat != tag.tagFormatConstructed:
            raise error.PyAsn1Error('Constructed tag format expected')

        original_position = substrate.tell()

        if substrateFun:
            if asn1Spec is not None:
                asn1Object = asn1Spec.clone()

            elif self.protoComponent is not None:
                asn1Object = self.protoComponent.clone(tagSet=tagSet)

            else:
                asn1Object = self.protoRecordComponent, self.protoSequenceComponent

            for chunk in substrateFun(asn1Object, substrate, length, options):
                yield chunk

            return

        if asn1Spec is None:
            for asn1Object in self._decodeComponentsSchemaless(
                    substrate, tagSet=tagSet, decodeFun=decodeFun,
                    length=length, **options):
                if isinstance(asn1Object, SubstrateUnderrunError):
                    yield asn1Object

            if substrate.tell() < original_position + length:
                if LOG:
                    for trailing in readFromStream(substrate, context=options):
                        if isinstance(trailing, SubstrateUnderrunError):
                            yield trailing

                    LOG('Unused trailing %d octets encountered: %s' % (
                        len(trailing), debug.hexdump(trailing)))

            yield asn1Object

            return

        asn1Object = asn1Spec.clone()
        asn1Object.clear()

        options = self._passAsn1Object(asn1Object, options)

        if asn1Spec.typeId in (univ.Sequence.typeId, univ.Set.typeId):

            namedTypes = asn1Spec.componentType

            isSetType = asn1Spec.typeId == univ.Set.typeId
            isDeterministic = not isSetType and not namedTypes.hasOptionalOrDefault

            if LOG:
                LOG('decoding %sdeterministic %s type %r chosen by type ID' % (
                    not isDeterministic and 'non-' or '', isSetType and 'SET' or '',
                    asn1Spec))

            seenIndices = set()
            idx = 0
            while substrate.tell() - original_position < length:
                if not namedTypes:
                    componentType = None

                elif isSetType:
                    componentType = namedTypes.tagMapUnique

                else:
                    try:
                        if isDeterministic:
                            componentType = namedTypes[idx].asn1Object

                        elif namedTypes[idx].isOptional or namedTypes[idx].isDefaulted:
                            componentType = namedTypes.getTagMapNearPosition(idx)

                        else:
                            componentType = namedTypes[idx].asn1Object

                    except IndexError:
                        raise error.PyAsn1Error(
                            'Excessive components decoded at %r' % (asn1Spec,)
                        )

                for component in decodeFun(substrate, componentType, **options):
                    if isinstance(component, SubstrateUnderrunError):
                        yield component

                if not isDeterministic and namedTypes:
                    if isSetType:
                        idx = namedTypes.getPositionByType(component.effectiveTagSet)

                    elif namedTypes[idx].isOptional or namedTypes[idx].isDefaulted:
                        idx = namedTypes.getPositionNearType(component.effectiveTagSet, idx)

                asn1Object.setComponentByPosition(
                    idx, component,
                    verifyConstraints=False,
                    matchTags=False, matchConstraints=False
                )

                seenIndices.add(idx)
                idx += 1

            if LOG:
                LOG('seen component indices %s' % seenIndices)

            if namedTypes:
                if not namedTypes.requiredComponents.issubset(seenIndices):
                    raise error.PyAsn1Error(
                        'ASN.1 object %s has uninitialized '
                        'components' % asn1Object.__class__.__name__)

                if  namedTypes.hasOpenTypes:

                    openTypes = options.get('openTypes', {})

                    if LOG:
                        LOG('user-specified open types map:')

                        for k, v in openTypes.items():
                            LOG('%s -> %r' % (k, v))

                    if openTypes or options.get('decodeOpenTypes', False):

                        for idx, namedType in enumerate(namedTypes.namedTypes):
                            if not namedType.openType:
                                continue

                            if namedType.isOptional and not asn1Object.getComponentByPosition(idx).isValue:
                                continue

                            governingValue = asn1Object.getComponentByName(
                                namedType.openType.name
                            )

                            try:
                                openType = openTypes[governingValue]

                            except KeyError:

                                if LOG:
                                    LOG('default open types map of component '
                                        '"%s.%s" governed by component "%s.%s"'
                                        ':' % (asn1Object.__class__.__name__,
                                               namedType.name,
                                               asn1Object.__class__.__name__,
                                               namedType.openType.name))

                                    for k, v in namedType.openType.items():
                                        LOG('%s -> %r' % (k, v))

                                try:
                                    openType = namedType.openType[governingValue]

                                except KeyError:
                                    if LOG:
                                        LOG('failed to resolve open type by governing '
                                            'value %r' % (governingValue,))
                                    continue

                            if LOG:
                                LOG('resolved open type %r by governing '
                                    'value %r' % (openType, governingValue))

                            containerValue = asn1Object.getComponentByPosition(idx)

                            if containerValue.typeId in (
                                    univ.SetOf.typeId, univ.SequenceOf.typeId):

                                for pos, containerElement in enumerate(
                                        containerValue):

                                    stream = asSeekableStream(containerValue[pos].asOctets())

                                    for component in decodeFun(stream, asn1Spec=openType, **options):
                                        if isinstance(component, SubstrateUnderrunError):
                                            yield component

                                    containerValue[pos] = component

                            else:
                                stream = asSeekableStream(asn1Object.getComponentByPosition(idx).asOctets())

                                for component in decodeFun(stream, asn1Spec=openType, **options):
                                    if isinstance(component, SubstrateUnderrunError):
                                        yield component

                                asn1Object.setComponentByPosition(idx, component)

            else:
                inconsistency = asn1Object.isInconsistent
                if inconsistency:
                    raise error.PyAsn1Error(
                        f"ASN.1 object {asn1Object.__class__.__name__} is inconsistent")

        else:
            componentType = asn1Spec.componentType

            if LOG:
                LOG('decoding type %r chosen by given `asn1Spec`' % componentType)

            idx = 0

            while substrate.tell() - original_position < length:
                for component in decodeFun(substrate, componentType, **options):
                    if isinstance(component, SubstrateUnderrunError):
                        yield component

                asn1Object.setComponentByPosition(
                    idx, component,
                    verifyConstraints=False,
                    matchTags=False, matchConstraints=False
                )

                idx += 1

        yield asn1Object

    def indefLenValueDecoder(self, substrate, asn1Spec,
                             tagSet=None, length=None, state=None,
                             decodeFun=None, substrateFun=None,
                             **options):
        if tagSet[0].tagFormat != tag.tagFormatConstructed:
            raise error.PyAsn1Error('Constructed tag format expected')

        if substrateFun is not None:
            if asn1Spec is not None:
                asn1Object = asn1Spec.clone()

            elif self.protoComponent is not None:
                asn1Object = self.protoComponent.clone(tagSet=tagSet)

            else:
                asn1Object = self.protoRecordComponent, self.protoSequenceComponent

            for chunk in substrateFun(asn1Object, substrate, length, options):
                yield chunk

            return

        if asn1Spec is None:
            for asn1Object in self._decodeComponentsSchemaless(
                    substrate, tagSet=tagSet, decodeFun=decodeFun,
                    length=length, **dict(options, allowEoo=True)):
                if isinstance(asn1Object, SubstrateUnderrunError):
                    yield asn1Object

            yield asn1Object

            return

        asn1Object = asn1Spec.clone()
        asn1Object.clear()

        options = self._passAsn1Object(asn1Object, options)

        if asn1Spec.typeId in (univ.Sequence.typeId, univ.Set.typeId):

            namedTypes = asn1Object.componentType

            isSetType = asn1Object.typeId == univ.Set.typeId
            isDeterministic = not isSetType and not namedTypes.hasOptionalOrDefault

            if LOG:
                LOG('decoding %sdeterministic %s type %r chosen by type ID' % (
                    not isDeterministic and 'non-' or '', isSetType and 'SET' or '',
                    asn1Spec))

            seenIndices = set()

            idx = 0

            while True:  # loop over components
                if len(namedTypes) <= idx:
                    asn1Spec = None

                elif isSetType:
                    asn1Spec = namedTypes.tagMapUnique

                else:
                    try:
                        if isDeterministic:
                            asn1Spec = namedTypes[idx].asn1Object

                        elif namedTypes[idx].isOptional or namedTypes[idx].isDefaulted:
                            asn1Spec = namedTypes.getTagMapNearPosition(idx)

                        else:
                            asn1Spec = namedTypes[idx].asn1Object

                    except IndexError:
                        raise error.PyAsn1Error(
                            'Excessive components decoded at %r' % (asn1Object,)
                        )

                for component in decodeFun(substrate, asn1Spec, allowEoo=True, **options):

                    if isinstance(component, SubstrateUnderrunError):
                        yield component

                    if component is eoo.endOfOctets:
                        break

                if component is eoo.endOfOctets:
                    break

                if not isDeterministic and namedTypes:
                    if isSetType:
                        idx = namedTypes.getPositionByType(component.effectiveTagSet)

                    elif namedTypes[idx].isOptional or namedTypes[idx].isDefaulted:
                        idx = namedTypes.getPositionNearType(component.effectiveTagSet, idx)

                asn1Object.setComponentByPosition(
                    idx, component,
                    verifyConstraints=False,
                    matchTags=False, matchConstraints=False
                )

                seenIndices.add(idx)
                idx += 1

            if LOG:
                LOG('seen component indices %s' % seenIndices)

            if namedTypes:
                if not namedTypes.requiredComponents.issubset(seenIndices):
                    raise error.PyAsn1Error(
                        'ASN.1 object %s has uninitialized '
                        'components' % asn1Object.__class__.__name__)

                if namedTypes.hasOpenTypes:

                    openTypes = options.get('openTypes', {})

                    if LOG:
                        LOG('user-specified open types map:')

                        for k, v in openTypes.items():
                            LOG('%s -> %r' % (k, v))

                    if openTypes or options.get('decodeOpenTypes', False):

                        for idx, namedType in enumerate(namedTypes.namedTypes):
                            if not namedType.openType:
                                continue

                            if namedType.isOptional and not asn1Object.getComponentByPosition(idx).isValue:
                                continue

                            governingValue = asn1Object.getComponentByName(
                                namedType.openType.name
                            )

                            try:
                                openType = openTypes[governingValue]

                            except KeyError:

                                if LOG:
                                    LOG('default open types map of component '
                                        '"%s.%s" governed by component "%s.%s"'
                                        ':' % (asn1Object.__class__.__name__,
                                               namedType.name,
                                               asn1Object.__class__.__name__,
                                               namedType.openType.name))

                                    for k, v in namedType.openType.items():
                                        LOG('%s -> %r' % (k, v))

                                try:
                                    openType = namedType.openType[governingValue]

                                except KeyError:
                                    if LOG:
                                        LOG('failed to resolve open type by governing '
                                            'value %r' % (governingValue,))
                                    continue

                            if LOG:
                                LOG('resolved open type %r by governing '
                                    'value %r' % (openType, governingValue))

                            containerValue = asn1Object.getComponentByPosition(idx)

                            if containerValue.typeId in (
                                    univ.SetOf.typeId, univ.SequenceOf.typeId):

                                for pos, containerElement in enumerate(
                                        containerValue):

                                    stream = asSeekableStream(containerValue[pos].asOctets())

                                    for component in decodeFun(stream, asn1Spec=openType,
                                                               **dict(options, allowEoo=True)):
                                        if isinstance(component, SubstrateUnderrunError):
                                            yield component

                                        if component is eoo.endOfOctets:
                                            break

                                    containerValue[pos] = component

                            else:
                                stream = asSeekableStream(asn1Object.getComponentByPosition(idx).asOctets())
                                for component in decodeFun(stream, asn1Spec=openType,
                                                           **dict(options, allowEoo=True)):
                                    if isinstance(component, SubstrateUnderrunError):
                                        yield component

                                    if component is eoo.endOfOctets:
                                        break

                                    asn1Object.setComponentByPosition(idx, component)

                else:
                    inconsistency = asn1Object.isInconsistent
                    if inconsistency:
                        raise error.PyAsn1Error(
                            f"ASN.1 object {asn1Object.__class__.__name__} is inconsistent")

        else:
            componentType = asn1Spec.componentType

            if LOG:
                LOG('decoding type %r chosen by given `asn1Spec`' % componentType)

            idx = 0

            while True:

                for component in decodeFun(
                        substrate, componentType, allowEoo=True, **options):

                    if isinstance(component, SubstrateUnderrunError):
                        yield component

                    if component is eoo.endOfOctets:
                        break

                if component is eoo.endOfOctets:
                    break

                asn1Object.setComponentByPosition(
                    idx, component,
                    verifyConstraints=False,
                    matchTags=False, matchConstraints=False
                )

                idx += 1

        yield asn1Object


class SequenceOrSequenceOfPayloadDecoder(ConstructedPayloadDecoderBase):
    protoRecordComponent = univ.Sequence()
    protoSequenceComponent = univ.SequenceOf()


class SequencePayloadDecoder(SequenceOrSequenceOfPayloadDecoder):
    protoComponent = univ.Sequence()


class SequenceOfPayloadDecoder(SequenceOrSequenceOfPayloadDecoder):
    protoComponent = univ.SequenceOf()


class SetOrSetOfPayloadDecoder(ConstructedPayloadDecoderBase):
    protoRecordComponent = univ.Set()
    protoSequenceComponent = univ.SetOf()


class SetPayloadDecoder(SetOrSetOfPayloadDecoder):
    protoComponent = univ.Set()


class SetOfPayloadDecoder(SetOrSetOfPayloadDecoder):
    protoComponent = univ.SetOf()


class ChoicePayloadDecoder(ConstructedPayloadDecoderBase):
    protoComponent = univ.Choice()

    def valueDecoder(self, substrate, asn1Spec,
                     tagSet=None, length=None, state=None,
                     decodeFun=None, substrateFun=None,
                     **options):
        if asn1Spec is None:
            asn1Object = self.protoComponent.clone(tagSet=tagSet)

        else:
            asn1Object = asn1Spec.clone()

        if substrateFun:
            for chunk in substrateFun(asn1Object, substrate, length, options):
                yield chunk

            return

        options = self._passAsn1Object(asn1Object, options)

        if asn1Object.tagSet == tagSet:
            if LOG:
                LOG('decoding %s as explicitly tagged CHOICE' % (tagSet,))

            for component in decodeFun(
                    substrate, asn1Object.componentTagMap, **options):
                if isinstance(component, SubstrateUnderrunError):
                    yield component

        else:
            if LOG:
                LOG('decoding %s as untagged CHOICE' % (tagSet,))

            for component in decodeFun(
                    substrate, asn1Object.componentTagMap, tagSet, length,
                    state, **options):
                if isinstance(component, SubstrateUnderrunError):
                    yield component

        effectiveTagSet = component.effectiveTagSet

        if LOG:
            LOG('decoded component %s, effective tag set %s' % (component, effectiveTagSet))

        asn1Object.setComponentByType(
            effectiveTagSet, component,
            verifyConstraints=False,
            matchTags=False, matchConstraints=False,
            innerFlag=False
        )

        yield asn1Object

    def indefLenValueDecoder(self, substrate, asn1Spec,
                             tagSet=None, length=None, state=None,
                             decodeFun=None, substrateFun=None,
                             **options):
        if asn1Spec is None:
            asn1Object = self.protoComponent.clone(tagSet=tagSet)

        else:
            asn1Object = asn1Spec.clone()

        if substrateFun:
            for chunk in substrateFun(asn1Object, substrate, length, options):
                yield chunk

            return

        options = self._passAsn1Object(asn1Object, options)

        isTagged = asn1Object.tagSet == tagSet

        if LOG:
            LOG('decoding %s as %stagged CHOICE' % (
                tagSet, isTagged and 'explicitly ' or 'un'))

        while True:

            if isTagged:
                iterator = decodeFun(
                    substrate, asn1Object.componentType.tagMapUnique,
                    **dict(options, allowEoo=True))

            else:
                iterator = decodeFun(
                    substrate, asn1Object.componentType.tagMapUnique,
                    tagSet, length, state, **dict(options, allowEoo=True))

            for component in iterator:

                if isinstance(component, SubstrateUnderrunError):
                    yield component

                if component is eoo.endOfOctets:
                    break

                effectiveTagSet = component.effectiveTagSet

                if LOG:
                    LOG('decoded component %s, effective tag set '
                        '%s' % (component, effectiveTagSet))

                asn1Object.setComponentByType(
                    effectiveTagSet, component,
                    verifyConstraints=False,
                    matchTags=False, matchConstraints=False,
                    innerFlag=False
                )

                if not isTagged:
                    break

            if not isTagged or component is eoo.endOfOctets:
                break

        yield asn1Object


class AnyPayloadDecoder(AbstractSimplePayloadDecoder):
    protoComponent = univ.Any()

    def valueDecoder(self, substrate, asn1Spec,
                     tagSet=None, length=None, state=None,
                     decodeFun=None, substrateFun=None,
                     **options):
        if asn1Spec is None:
            isUntagged = True

        elif asn1Spec.__class__ is tagmap.TagMap:
            isUntagged = tagSet not in asn1Spec.tagMap

        else:
            isUntagged = tagSet != asn1Spec.tagSet

        if isUntagged:
            fullPosition = substrate.markedPosition
            currentPosition = substrate.tell()

            substrate.seek(fullPosition, os.SEEK_SET)
            length += currentPosition - fullPosition

            if LOG:
                for chunk in peekIntoStream(substrate, length):
                    if isinstance(chunk, SubstrateUnderrunError):
                        yield chunk
                LOG('decoding as untagged ANY, substrate '
                    '%s' % debug.hexdump(chunk))

        if substrateFun:
            for chunk in substrateFun(
                    self._createComponent(asn1Spec, tagSet, noValue, **options),
                    substrate, length, options):
                yield chunk

            return

        for chunk in readFromStream(substrate, length, options):
            if isinstance(chunk, SubstrateUnderrunError):
                yield chunk

        yield self._createComponent(asn1Spec, tagSet, chunk, **options)

    def indefLenValueDecoder(self, substrate, asn1Spec,
                             tagSet=None, length=None, state=None,
                             decodeFun=None, substrateFun=None,
                             **options):
        if asn1Spec is None:
            isTagged = False

        elif asn1Spec.__class__ is tagmap.TagMap:
            isTagged = tagSet in asn1Spec.tagMap

        else:
            isTagged = tagSet == asn1Spec.tagSet

        if isTagged:
            # tagged Any type -- consume header substrate
            chunk = b''

            if LOG:
                LOG('decoding as tagged ANY')

        else:
            # TODO: Seems not to be tested
            fullPosition = substrate.markedPosition
            currentPosition = substrate.tell()

            substrate.seek(fullPosition, os.SEEK_SET)
            for chunk in readFromStream(substrate, currentPosition - fullPosition, options):
                if isinstance(chunk, SubstrateUnderrunError):
                    yield chunk

            if LOG:
                LOG('decoding as untagged ANY, header substrate %s' % debug.hexdump(chunk))

        # Any components do not inherit initial tag
        asn1Spec = self.protoComponent

        if substrateFun and substrateFun is not self.substrateCollector:
            asn1Object = self._createComponent(
                asn1Spec, tagSet, noValue, **options)

            for chunk in substrateFun(
                    asn1Object, chunk + substrate, length + len(chunk), options):
                yield chunk

            return

        if LOG:
            LOG('assembling constructed serialization')

        # All inner fragments are of the same type, treat them as octet string
        substrateFun = self.substrateCollector

        while True:  # loop over fragments

            for component in decodeFun(
                    substrate, asn1Spec, substrateFun=substrateFun,
                    allowEoo=True, **options):

                if isinstance(component, SubstrateUnderrunError):
                    yield component

                if component is eoo.endOfOctets:
                    break

            if component is eoo.endOfOctets:
                break

            chunk += component

        if substrateFun:
            yield chunk  # TODO: Weird

        else:
            yield self._createComponent(asn1Spec, tagSet, chunk, **options)


# character string types
class UTF8StringPayloadDecoder(OctetStringPayloadDecoder):
    protoComponent = char.UTF8String()


class NumericStringPayloadDecoder(OctetStringPayloadDecoder):
    protoComponent = char.NumericString()


class PrintableStringPayloadDecoder(OctetStringPayloadDecoder):
    protoComponent = char.PrintableString()


class TeletexStringPayloadDecoder(OctetStringPayloadDecoder):
    protoComponent = char.TeletexString()


class VideotexStringPayloadDecoder(OctetStringPayloadDecoder):
    protoComponent = char.VideotexString()


class IA5StringPayloadDecoder(OctetStringPayloadDecoder):
    protoComponent = char.IA5String()


class GraphicStringPayloadDecoder(OctetStringPayloadDecoder):
    protoComponent = char.GraphicString()


class VisibleStringPayloadDecoder(OctetStringPayloadDecoder):
    protoComponent = char.VisibleString()


class GeneralStringPayloadDecoder(OctetStringPayloadDecoder):
    protoComponent = char.GeneralString()


class UniversalStringPayloadDecoder(OctetStringPayloadDecoder):
    protoComponent = char.UniversalString()


class BMPStringPayloadDecoder(OctetStringPayloadDecoder):
    protoComponent = char.BMPString()


# "useful" types
class ObjectDescriptorPayloadDecoder(OctetStringPayloadDecoder):
    protoComponent = useful.ObjectDescriptor()


class GeneralizedTimePayloadDecoder(OctetStringPayloadDecoder):
    protoComponent = useful.GeneralizedTime()


class UTCTimePayloadDecoder(OctetStringPayloadDecoder):
    protoComponent = useful.UTCTime()


TAG_MAP = {
    univ.Integer.tagSet: IntegerPayloadDecoder(),
    univ.Boolean.tagSet: BooleanPayloadDecoder(),
    univ.BitString.tagSet: BitStringPayloadDecoder(),
    univ.OctetString.tagSet: OctetStringPayloadDecoder(),
    univ.Null.tagSet: NullPayloadDecoder(),
    univ.ObjectIdentifier.tagSet: ObjectIdentifierPayloadDecoder(),
    univ.RelativeOID.tagSet: RelativeOIDPayloadDecoder(),
    univ.Enumerated.tagSet: IntegerPayloadDecoder(),
    univ.Real.tagSet: RealPayloadDecoder(),
    univ.Sequence.tagSet: SequenceOrSequenceOfPayloadDecoder(),  # conflicts with SequenceOf
    univ.Set.tagSet: SetOrSetOfPayloadDecoder(),  # conflicts with SetOf
    univ.Choice.tagSet: ChoicePayloadDecoder(),  # conflicts with Any
    # character string types
    char.UTF8String.tagSet: UTF8StringPayloadDecoder(),
    char.NumericString.tagSet: NumericStringPayloadDecoder(),
    char.PrintableString.tagSet: PrintableStringPayloadDecoder(),
    char.TeletexString.tagSet: TeletexStringPayloadDecoder(),
    char.VideotexString.tagSet: VideotexStringPayloadDecoder(),
    char.IA5String.tagSet: IA5StringPayloadDecoder(),
    char.GraphicString.tagSet: GraphicStringPayloadDecoder(),
    char.VisibleString.tagSet: VisibleStringPayloadDecoder(),
    char.GeneralString.tagSet: GeneralStringPayloadDecoder(),
    char.UniversalString.tagSet: UniversalStringPayloadDecoder(),
    char.BMPString.tagSet: BMPStringPayloadDecoder(),
    # useful types
    useful.ObjectDescriptor.tagSet: ObjectDescriptorPayloadDecoder(),
    useful.GeneralizedTime.tagSet: GeneralizedTimePayloadDecoder(),
    useful.UTCTime.tagSet: UTCTimePayloadDecoder()
}

# Type-to-codec map for ambiguous ASN.1 types
TYPE_MAP = {
    univ.Set.typeId: SetPayloadDecoder(),
    univ.SetOf.typeId: SetOfPayloadDecoder(),
    univ.Sequence.typeId: SequencePayloadDecoder(),
    univ.SequenceOf.typeId: SequenceOfPayloadDecoder(),
    univ.Choice.typeId: ChoicePayloadDecoder(),
    univ.Any.typeId: AnyPayloadDecoder()
}

# Put in non-ambiguous types for faster codec lookup
for typeDecoder in TAG_MAP.values():
    if typeDecoder.protoComponent is not None:
        typeId = typeDecoder.protoComponent.__class__.typeId
        if typeId is not None and typeId not in TYPE_MAP:
            TYPE_MAP[typeId] = typeDecoder


(stDecodeTag,
 stDecodeLength,
 stGetValueDecoder,
 stGetValueDecoderByAsn1Spec,
 stGetValueDecoderByTag,
 stTryAsExplicitTag,
 stDecodeValue,
 stDumpRawValue,
 stErrorCondition,
 stStop) = [x for x in range(10)]


EOO_SENTINEL = bytes((0, 0))


class SingleItemDecoder(object):
    defaultErrorState = stErrorCondition
    #defaultErrorState = stDumpRawValue
    defaultRawDecoder = AnyPayloadDecoder()

    supportIndefLength = True

    TAG_MAP = TAG_MAP
    TYPE_MAP = TYPE_MAP

    def __init__(self, tagMap=_MISSING, typeMap=_MISSING, **ignored):
        self._tagMap = tagMap if tagMap is not _MISSING else self.TAG_MAP
        self._typeMap = typeMap if typeMap is not _MISSING else self.TYPE_MAP

        # Tag & TagSet objects caches
        self._tagCache = {}
        self._tagSetCache = {}

    def __call__(self, substrate, asn1Spec=None,
                 tagSet=None, length=None, state=stDecodeTag,
                 decodeFun=None, substrateFun=None,
                 **options):

        allowEoo = options.pop('allowEoo', False)

        if LOG:
            LOG('decoder called at scope %s with state %d, working with up '
                'to %s octets of substrate: '
                '%s' % (debug.scope, state, length, substrate))

        # Look for end-of-octets sentinel
        if allowEoo and self.supportIndefLength:

            for eoo_candidate in readFromStream(substrate, 2, options):
                if isinstance(eoo_candidate, SubstrateUnderrunError):
                    yield eoo_candidate

            if eoo_candidate == EOO_SENTINEL:
                if LOG:
                    LOG('end-of-octets sentinel found')
                yield eoo.endOfOctets
                return

            else:
                substrate.seek(-2, os.SEEK_CUR)

        tagMap = self._tagMap
        typeMap = self._typeMap
        tagCache = self._tagCache
        tagSetCache = self._tagSetCache

        value = noValue

        substrate.markedPosition = substrate.tell()

        while state is not stStop:

            if state is stDecodeTag:
                # Decode tag
                isShortTag = True

                for firstByte in readFromStream(substrate, 1, options):
                    if isinstance(firstByte, SubstrateUnderrunError):
                        yield firstByte

                firstOctet = ord(firstByte)

                try:
                    lastTag = tagCache[firstOctet]

                except KeyError:
                    integerTag = firstOctet
                    tagClass = integerTag & 0xC0
                    tagFormat = integerTag & 0x20
                    tagId = integerTag & 0x1F

                    if tagId == 0x1F:
                        isShortTag = False
                        lengthOctetIdx = 0
                        tagId = 0

                        while True:
                            for integerByte in readFromStream(substrate, 1, options):
                                if isinstance(integerByte, SubstrateUnderrunError):
                                    yield integerByte

                            if not integerByte:
                                raise error.SubstrateUnderrunError(
                                    'Short octet stream on long tag decoding'
                                )

                            integerTag = ord(integerByte)
                            lengthOctetIdx += 1
                            tagId <<= 7
                            tagId |= (integerTag & 0x7F)

                            if not integerTag & 0x80:
                                break

                    lastTag = tag.Tag(
                        tagClass=tagClass, tagFormat=tagFormat, tagId=tagId
                    )

                    if isShortTag:
                        # cache short tags
                        tagCache[firstOctet] = lastTag

                if tagSet is None:
                    if isShortTag:
                        try:
                            tagSet = tagSetCache[firstOctet]

                        except KeyError:
                            # base tag not recovered
                            tagSet = tag.TagSet((), lastTag)
                            tagSetCache[firstOctet] = tagSet
                    else:
                        tagSet = tag.TagSet((), lastTag)

                else:
                    tagSet = lastTag + tagSet

                state = stDecodeLength

                if LOG:
                    LOG('tag decoded into %s, decoding length' % tagSet)

            if state is stDecodeLength:
                # Decode length
                for firstOctet in readFromStream(substrate, 1, options):
                    if isinstance(firstOctet, SubstrateUnderrunError):
                        yield firstOctet

                firstOctet = ord(firstOctet)

                if firstOctet < 128:
                    length = firstOctet

                elif firstOctet > 128:
                    size = firstOctet & 0x7F
                    # encoded in size bytes
                    for encodedLength in readFromStream(substrate, size, options):
                        if isinstance(encodedLength, SubstrateUnderrunError):
                            yield encodedLength
                    encodedLength = list(encodedLength)
                    # missing check on maximum size, which shouldn't be a
                    # problem, we can handle more than is possible
                    if len(encodedLength) != size:
                        raise error.SubstrateUnderrunError(
                            '%s<%s at %s' % (size, len(encodedLength), tagSet)
                        )

                    length = 0
                    for lengthOctet in encodedLength:
                        length <<= 8
                        length |= lengthOctet
                    size += 1

                else:  # 128 means indefinite
                    length = -1

                if length == -1 and not self.supportIndefLength:
                    raise error.PyAsn1Error('Indefinite length encoding not supported by this codec')

                state = stGetValueDecoder

                if LOG:
                    LOG('value length decoded into %d' % length)

            if state is stGetValueDecoder:
                if asn1Spec is None:
                    state = stGetValueDecoderByTag

                else:
                    state = stGetValueDecoderByAsn1Spec
            #
            # There're two ways of creating subtypes in ASN.1 what influences
            # decoder operation. These methods are:
            # 1) Either base types used in or no IMPLICIT tagging has been
            #    applied on subtyping.
            # 2) Subtype syntax drops base type information (by means of
            #    IMPLICIT tagging.
            # The first case allows for complete tag recovery from substrate
            # while the second one requires original ASN.1 type spec for
            # decoding.
            #
            # In either case a set of tags (tagSet) is coming from substrate
            # in an incremental, tag-by-tag fashion (this is the case of
            # EXPLICIT tag which is most basic). Outermost tag comes first
            # from the wire.
            #
            if state is stGetValueDecoderByTag:
                try:
                    concreteDecoder = tagMap[tagSet]

                except KeyError:
                    concreteDecoder = None

                if concreteDecoder:
                    state = stDecodeValue

                else:
                    try:
                        concreteDecoder = tagMap[tagSet[:1]]

                    except KeyError:
                        concreteDecoder = None

                    if concreteDecoder:
                        state = stDecodeValue
                    else:
                        state = stTryAsExplicitTag

                if LOG:
                    LOG('codec %s chosen by a built-in type, decoding %s' % (concreteDecoder and concreteDecoder.__class__.__name__ or "<none>", state is stDecodeValue and 'value' or 'as explicit tag'))
                    debug.scope.push(concreteDecoder is None and '?' or concreteDecoder.protoComponent.__class__.__name__)

            if state is stGetValueDecoderByAsn1Spec:

                if asn1Spec.__class__ is tagmap.TagMap:
                    try:
                        chosenSpec = asn1Spec[tagSet]

                    except KeyError:
                        chosenSpec = None

                    if LOG:
                        LOG('candidate ASN.1 spec is a map of:')

                        for firstOctet, v in asn1Spec.presentTypes.items():
                            LOG('  %s -> %s' % (firstOctet, v.__class__.__name__))

                        if asn1Spec.skipTypes:
                            LOG('but neither of: ')
                            for firstOctet, v in asn1Spec.skipTypes.items():
                                LOG('  %s -> %s' % (firstOctet, v.__class__.__name__))
                        LOG('new candidate ASN.1 spec is %s, chosen by %s' % (chosenSpec is None and '<none>' or chosenSpec.prettyPrintType(), tagSet))

                elif tagSet == asn1Spec.tagSet or tagSet in asn1Spec.tagMap:
                    chosenSpec = asn1Spec
                    if LOG:
                        LOG('candidate ASN.1 spec is %s' % asn1Spec.__class__.__name__)

                else:
                    chosenSpec = None

                if chosenSpec is not None:
                    try:
                        # ambiguous type or just faster codec lookup
                        concreteDecoder = typeMap[chosenSpec.typeId]

                        if LOG:
                            LOG('value decoder chosen for an ambiguous type by type ID %s' % (chosenSpec.typeId,))

                    except KeyError:
                        # use base type for codec lookup to recover untagged types
                        baseTagSet = tag.TagSet(chosenSpec.tagSet.baseTag,  chosenSpec.tagSet.baseTag)
                        try:
                            # base type or tagged subtype
                            concreteDecoder = tagMap[baseTagSet]

                            if LOG:
                                LOG('value decoder chosen by base %s' % (baseTagSet,))

                        except KeyError:
                            concreteDecoder = None

                    if concreteDecoder:
                        asn1Spec = chosenSpec
                        state = stDecodeValue

                    else:
                        state = stTryAsExplicitTag

                else:
                    concreteDecoder = None
                    state = stTryAsExplicitTag

                if LOG:
                    LOG('codec %s chosen by ASN.1 spec, decoding %s' % (state is stDecodeValue and concreteDecoder.__class__.__name__ or "<none>", state is stDecodeValue and 'value' or 'as explicit tag'))
                    debug.scope.push(chosenSpec is None and '?' or chosenSpec.__class__.__name__)

            if state is stDecodeValue:
                if not options.get('recursiveFlag', True) and not substrateFun:  # deprecate this
                    def substrateFun(asn1Object, _substrate, _length, _options):
                        """Legacy hack to keep the recursiveFlag=False option supported.

                        The decode(..., substrateFun=userCallback) option was introduced in 0.1.4 as a generalization
                        of the old recursiveFlag=False option. Users should pass their callback instead of using
                        recursiveFlag.
                        """
                        yield asn1Object

                original_position = substrate.tell()

                if length == -1:  # indef length
                    for value in concreteDecoder.indefLenValueDecoder(
                            substrate, asn1Spec,
                            tagSet, length, stGetValueDecoder,
                            self, substrateFun, **options):
                        if isinstance(value, SubstrateUnderrunError):
                            yield value

                else:
                    for value in concreteDecoder.valueDecoder(
                            substrate, asn1Spec,
                            tagSet, length, stGetValueDecoder,
                            self, substrateFun, **options):
                        if isinstance(value, SubstrateUnderrunError):
                            yield value

                    bytesRead = substrate.tell() - original_position
                    if not substrateFun and bytesRead != length:
                        raise PyAsn1Error(
                            "Read %s bytes instead of expected %s." % (bytesRead, length))
                    elif substrateFun and bytesRead > length:
                        # custom substrateFun may be used for partial decoding, reading less is expected there
                        raise PyAsn1Error(
                            "Read %s bytes are more than expected %s." % (bytesRead, length))

                if LOG:
                   LOG('codec %s yields type %s, value:\n%s\n...' % (
                       concreteDecoder.__class__.__name__, value.__class__.__name__,
                       isinstance(value, base.Asn1Item) and value.prettyPrint() or value))

                state = stStop
                break

            if state is stTryAsExplicitTag:
                if (tagSet and
                        tagSet[0].tagFormat == tag.tagFormatConstructed and
                        tagSet[0].tagClass != tag.tagClassUniversal):
                    # Assume explicit tagging
                    concreteDecoder = rawPayloadDecoder
                    state = stDecodeValue

                else:
                    concreteDecoder = None
                    state = self.defaultErrorState

                if LOG:
                    LOG('codec %s chosen, decoding %s' % (concreteDecoder and concreteDecoder.__class__.__name__ or "<none>", state is stDecodeValue and 'value' or 'as failure'))

            if state is stDumpRawValue:
                concreteDecoder = self.defaultRawDecoder

                if LOG:
                    LOG('codec %s chosen, decoding value' % concreteDecoder.__class__.__name__)

                state = stDecodeValue

            if state is stErrorCondition:
                raise error.PyAsn1Error(
                    '%s not in asn1Spec: %r' % (tagSet, asn1Spec)
                )

        if LOG:
            debug.scope.pop()
            LOG('decoder left scope %s, call completed' % debug.scope)

        yield value


class StreamingDecoder(object):
    """Create an iterator that turns BER/CER/DER byte stream into ASN.1 objects.

    On each iteration, consume whatever BER/CER/DER serialization is
    available in the `substrate` stream-like object and turns it into
    one or more, possibly nested, ASN.1 objects.

    Parameters
    ----------
    substrate: :py:class:`file`, :py:class:`io.BytesIO`
        BER/CER/DER serialization in form of a byte stream

    Keyword Args
    ------------
    asn1Spec: :py:class:`~pyasn1.type.base.PyAsn1Item`
        A pyasn1 type object to act as a template guiding the decoder.
        Depending on the ASN.1 structure being decoded, `asn1Spec` may
        or may not be required. One of the reasons why `asn1Spec` may
        me required is that ASN.1 structure is encoded in the *IMPLICIT*
        tagging mode.

    Yields
    ------
    : :py:class:`~pyasn1.type.base.PyAsn1Item`, :py:class:`~pyasn1.error.SubstrateUnderrunError`
        Decoded ASN.1 object (possibly, nested) or
        :py:class:`~pyasn1.error.SubstrateUnderrunError` object indicating
        insufficient BER/CER/DER serialization on input to fully recover ASN.1
        objects from it.
        
        In the latter case the caller is advised to ensure some more data in
        the input stream, then call the iterator again. The decoder will resume
        the decoding process using the newly arrived data.

        The `context` property of :py:class:`~pyasn1.error.SubstrateUnderrunError`
        object might hold a reference to the partially populated ASN.1 object
        being reconstructed.

    Raises
    ------
    ~pyasn1.error.PyAsn1Error, ~pyasn1.error.EndOfStreamError
        `PyAsn1Error` on deserialization error, `EndOfStreamError` on
         premature stream closure.

    Examples
    --------
    Decode BER serialisation without ASN.1 schema

    .. code-block:: pycon

        >>> stream = io.BytesIO(
        ...    b'0\t\x02\x01\x01\x02\x01\x02\x02\x01\x03')
        >>>
        >>> for asn1Object in StreamingDecoder(stream):
        ...     print(asn1Object)
        >>>
        SequenceOf:
         1 2 3

    Decode BER serialisation with ASN.1 schema

    .. code-block:: pycon

        >>> stream = io.BytesIO(
        ...    b'0\t\x02\x01\x01\x02\x01\x02\x02\x01\x03')
        >>>
        >>> schema = SequenceOf(componentType=Integer())
        >>>
        >>> decoder = StreamingDecoder(stream, asn1Spec=schema)
        >>> for asn1Object in decoder:
        ...     print(asn1Object)
        >>>
        SequenceOf:
         1 2 3
    """

    SINGLE_ITEM_DECODER = SingleItemDecoder

    def __init__(self, substrate, asn1Spec=None, **options):
        self._singleItemDecoder = self.SINGLE_ITEM_DECODER(**options)
        self._substrate = asSeekableStream(substrate)
        self._asn1Spec = asn1Spec
        self._options = options

    def __iter__(self):
        while True:
            for asn1Object in self._singleItemDecoder(
                    self._substrate, self._asn1Spec, **self._options):
                yield asn1Object

            for chunk in isEndOfStream(self._substrate):
                if isinstance(chunk, SubstrateUnderrunError):
                    yield

                break

            if chunk:
                break


class Decoder(object):
    """Create a BER decoder object.

    Parse BER/CER/DER octet-stream into one, possibly nested, ASN.1 object.
    """
    STREAMING_DECODER = StreamingDecoder

    @classmethod
    def __call__(cls, substrate, asn1Spec=None, **options):
        """Turns BER/CER/DER octet stream into an ASN.1 object.

        Takes BER/CER/DER octet-stream in form of :py:class:`bytes`
        and decode it into an ASN.1 object
        (e.g. :py:class:`~pyasn1.type.base.PyAsn1Item` derivative) which
        may be a scalar or an arbitrary nested structure.

        Parameters
        ----------
        substrate: :py:class:`bytes`
            BER/CER/DER octet-stream to parse

        Keyword Args
        ------------
        asn1Spec: :py:class:`~pyasn1.type.base.PyAsn1Item`
            A pyasn1 type object (:py:class:`~pyasn1.type.base.PyAsn1Item`
            derivative) to act as a template guiding the decoder.
            Depending on the ASN.1 structure being decoded, `asn1Spec` may or
            may not be required. Most common reason for it to require is that
            ASN.1 structure is encoded in *IMPLICIT* tagging mode.

        substrateFun: :py:class:`Union[
                Callable[[pyasn1.type.base.PyAsn1Item, bytes, int],
                         Tuple[pyasn1.type.base.PyAsn1Item, bytes]],
                Callable[[pyasn1.type.base.PyAsn1Item, io.BytesIO, int, dict],
                         Generator[Union[pyasn1.type.base.PyAsn1Item,
                                         pyasn1.error.SubstrateUnderrunError],
                                   None, None]]
            ]`
            User callback meant to generalize special use cases like non-recursive or
            partial decoding. A 3-arg non-streaming variant is supported for backwards
            compatiblilty in addition to the newer 4-arg streaming variant.
            The callback will receive the uninitialized object recovered from substrate
            as 1st argument, the uninterpreted payload as 2nd argument, and the length
            of the uninterpreted payload as 3rd argument. The streaming variant will
            additionally receive the decode(..., **options) kwargs as 4th argument.
            The non-streaming variant shall return an object that will be propagated
            as decode() return value as 1st item, and the remainig payload for further
            decode passes as 2nd item.
            The streaming variant shall yield an object that will be propagated as
            decode() return value, and leave the remaining payload in the stream.

        Returns
        -------
        : :py:class:`tuple`
            A tuple of :py:class:`~pyasn1.type.base.PyAsn1Item` object
            recovered from BER/CER/DER substrate and the unprocessed trailing
            portion of the `substrate` (may be empty)

        Raises
        ------
        : :py:class:`~pyasn1.error.PyAsn1Error`
            :py:class:`~pyasn1.error.SubstrateUnderrunError` on insufficient
            input or :py:class:`~pyasn1.error.PyAsn1Error` on decoding error.

        Examples
        --------
        Decode BER/CER/DER serialisation without ASN.1 schema

        .. code-block:: pycon

           >>> s, unprocessed = decode(b'0\t\x02\x01\x01\x02\x01\x02\x02\x01\x03')
           >>> str(s)
           SequenceOf:
            1 2 3

        Decode BER/CER/DER serialisation with ASN.1 schema

        .. code-block:: pycon

           >>> seq = SequenceOf(componentType=Integer())
           >>> s, unprocessed = decode(
                b'0\t\x02\x01\x01\x02\x01\x02\x02\x01\x03', asn1Spec=seq)
           >>> str(s)
           SequenceOf:
            1 2 3

        """
        substrate = asSeekableStream(substrate)

        if "substrateFun" in options:
            origSubstrateFun = options["substrateFun"]

            def substrateFunWrapper(asn1Object, substrate, length, options=None):
                """Support both 0.4 and 0.5 style APIs.

                substrateFun API has changed in 0.5 for use with streaming decoders. To stay backwards compatible,
                we first try if we received a streaming user callback. If that fails,we assume we've received a
                non-streaming v0.4 user callback and convert it for streaming on the fly
                """
                try:
                    substrate_gen = origSubstrateFun(asn1Object, substrate, length, options)
                except TypeError as _value:
                    if _value.__traceback__.tb_next:
                        # Traceback depth > 1 means TypeError from inside user provided function
                        raise
                    # invariant maintained at Decoder.__call__ entry
                    assert isinstance(substrate, io.BytesIO)  # nosec assert_used
                    substrate_gen = Decoder._callSubstrateFunV4asV5(origSubstrateFun, asn1Object, substrate, length)
                for value in substrate_gen:
                    yield value

            options["substrateFun"] = substrateFunWrapper

        streamingDecoder = cls.STREAMING_DECODER(
            substrate, asn1Spec, **options)

        for asn1Object in streamingDecoder:
            if isinstance(asn1Object, SubstrateUnderrunError):
                raise error.SubstrateUnderrunError('Short substrate on input')

            try:
                tail = next(readFromStream(substrate))

            except error.EndOfStreamError:
                tail = b''

            return asn1Object, tail

    @staticmethod
    def _callSubstrateFunV4asV5(substrateFunV4, asn1Object, substrate, length):
        substrate_bytes = substrate.read()
        if length == -1:
            length = len(substrate_bytes)
        value, nextSubstrate = substrateFunV4(asn1Object, substrate_bytes, length)
        nbytes = substrate.write(nextSubstrate)
        substrate.truncate()
        substrate.seek(-nbytes, os.SEEK_CUR)
        yield value

#: Turns BER octet stream into an ASN.1 object.
#:
#: Takes BER octet-stream and decode it into an ASN.1 object
#: (e.g. :py:class:`~pyasn1.type.base.PyAsn1Item` derivative) which
#: may be a scalar or an arbitrary nested structure.
#:
#: Parameters
#: ----------
#: substrate: :py:class:`bytes`
#:     BER octet-stream
#:
#: Keyword Args
#: ------------
#: asn1Spec: any pyasn1 type object e.g. :py:class:`~pyasn1.type.base.PyAsn1Item` derivative
#:     A pyasn1 type object to act as a template guiding the decoder. Depending on the ASN.1 structure
#:     being decoded, *asn1Spec* may or may not be required. Most common reason for
#:     it to require is that ASN.1 structure is encoded in *IMPLICIT* tagging mode.
#:
#: Returns
#: -------
#: : :py:class:`tuple`
#:     A tuple of pyasn1 object recovered from BER substrate (:py:class:`~pyasn1.type.base.PyAsn1Item` derivative)
#:     and the unprocessed trailing portion of the *substrate* (may be empty)
#:
#: Raises
#: ------
#: ~pyasn1.error.PyAsn1Error, ~pyasn1.error.SubstrateUnderrunError
#:     On decoding errors
#:
#: Notes
#: -----
#: This function is deprecated. Please use :py:class:`Decoder` or
#: :py:class:`StreamingDecoder` class instance.
#:
#: Examples
#: --------
#: Decode BER serialisation without ASN.1 schema
#:
#: .. code-block:: pycon
#:
#:    >>> s, _ = decode(b'0\t\x02\x01\x01\x02\x01\x02\x02\x01\x03')
#:    >>> str(s)
#:    SequenceOf:
#:     1 2 3
#:
#: Decode BER serialisation with ASN.1 schema
#:
#: .. code-block:: pycon
#:
#:    >>> seq = SequenceOf(componentType=Integer())
#:    >>> s, _ = decode(b'0\t\x02\x01\x01\x02\x01\x02\x02\x01\x03', asn1Spec=seq)
#:    >>> str(s)
#:    SequenceOf:
#:     1 2 3
#:
decode = Decoder()

def __getattr__(attr: str):
    if newAttr := {"tagMap": "TAG_MAP", "typeMap": "TYPE_MAP"}.get(attr):
        warnings.warn(f"{attr} is deprecated. Please use {newAttr} instead.", DeprecationWarning)
        return globals()[newAttr]
    raise AttributeError(attr)

# === NexusCore/openenv\Lib\site-packages\openai\lib\_tools.py ===
from __future__ import annotations

from typing import Any, Dict, cast

import pydantic

from ._pydantic import to_strict_json_schema
from ..types.chat import ChatCompletionToolParam
from ..types.shared_params import FunctionDefinition
from ..types.responses.function_tool_param import FunctionToolParam as ResponsesFunctionToolParam


class PydanticFunctionTool(Dict[str, Any]):
    """Dictionary wrapper so we can pass the given base model
    throughout the entire request stack without having to special
    case it.
    """

    model: type[pydantic.BaseModel]

    def __init__(self, defn: FunctionDefinition, model: type[pydantic.BaseModel]) -> None:
        super().__init__(defn)
        self.model = model

    def cast(self) -> FunctionDefinition:
        return cast(FunctionDefinition, self)


class ResponsesPydanticFunctionTool(Dict[str, Any]):
    model: type[pydantic.BaseModel]

    def __init__(self, tool: ResponsesFunctionToolParam, model: type[pydantic.BaseModel]) -> None:
        super().__init__(tool)
        self.model = model

    def cast(self) -> ResponsesFunctionToolParam:
        return cast(ResponsesFunctionToolParam, self)


def pydantic_function_tool(
    model: type[pydantic.BaseModel],
    *,
    name: str | None = None,  # inferred from class name by default
    description: str | None = None,  # inferred from class docstring by default
) -> ChatCompletionToolParam:
    if description is None:
        # note: we intentionally don't use `.getdoc()` to avoid
        # including pydantic's docstrings
        description = model.__doc__

    function = PydanticFunctionTool(
        {
            "name": name or model.__name__,
            "strict": True,
            "parameters": to_strict_json_schema(model),
        },
        model,
    ).cast()

    if description is not None:
        function["description"] = description

    return {
        "type": "function",
        "function": function,
    }

# === NexusCore/openenv\Lib\site-packages\fontTools\feaLib\ast.py ===
from fontTools.feaLib.error import FeatureLibError
from fontTools.feaLib.location import FeatureLibLocation
from fontTools.misc.encodingTools import getEncoding
from fontTools.misc.textTools import byteord, tobytes
from collections import OrderedDict
import itertools

SHIFT = " " * 4

__all__ = [
    "Element",
    "FeatureFile",
    "Comment",
    "GlyphName",
    "GlyphClass",
    "GlyphClassName",
    "MarkClassName",
    "AnonymousBlock",
    "Block",
    "FeatureBlock",
    "NestedBlock",
    "LookupBlock",
    "GlyphClassDefinition",
    "GlyphClassDefStatement",
    "MarkClass",
    "MarkClassDefinition",
    "AlternateSubstStatement",
    "Anchor",
    "AnchorDefinition",
    "AttachStatement",
    "AxisValueLocationStatement",
    "BaseAxis",
    "CVParametersNameStatement",
    "ChainContextPosStatement",
    "ChainContextSubstStatement",
    "CharacterStatement",
    "ConditionsetStatement",
    "CursivePosStatement",
    "ElidedFallbackName",
    "ElidedFallbackNameID",
    "Expression",
    "FeatureNameStatement",
    "FeatureReferenceStatement",
    "FontRevisionStatement",
    "HheaField",
    "IgnorePosStatement",
    "IgnoreSubstStatement",
    "IncludeStatement",
    "LanguageStatement",
    "LanguageSystemStatement",
    "LigatureCaretByIndexStatement",
    "LigatureCaretByPosStatement",
    "LigatureSubstStatement",
    "LookupFlagStatement",
    "LookupReferenceStatement",
    "MarkBasePosStatement",
    "MarkLigPosStatement",
    "MarkMarkPosStatement",
    "MultipleSubstStatement",
    "NameRecord",
    "OS2Field",
    "PairPosStatement",
    "ReverseChainSingleSubstStatement",
    "ScriptStatement",
    "SinglePosStatement",
    "SingleSubstStatement",
    "SizeParameters",
    "Statement",
    "STATAxisValueStatement",
    "STATDesignAxisStatement",
    "STATNameStatement",
    "SubtableStatement",
    "TableBlock",
    "ValueRecord",
    "ValueRecordDefinition",
    "VheaField",
]


def deviceToString(device):
    if device is None:
        return "<device NULL>"
    else:
        return "<device %s>" % ", ".join("%d %d" % t for t in device)


fea_keywords = set(
    [
        "anchor",
        "anchordef",
        "anon",
        "anonymous",
        "by",
        "contour",
        "cursive",
        "device",
        "enum",
        "enumerate",
        "excludedflt",
        "exclude_dflt",
        "feature",
        "from",
        "ignore",
        "ignorebaseglyphs",
        "ignoreligatures",
        "ignoremarks",
        "include",
        "includedflt",
        "include_dflt",
        "language",
        "languagesystem",
        "lookup",
        "lookupflag",
        "mark",
        "markattachmenttype",
        "markclass",
        "nameid",
        "null",
        "parameters",
        "pos",
        "position",
        "required",
        "righttoleft",
        "reversesub",
        "rsub",
        "script",
        "sub",
        "substitute",
        "subtable",
        "table",
        "usemarkfilteringset",
        "useextension",
        "valuerecorddef",
        "base",
        "gdef",
        "head",
        "hhea",
        "name",
        "vhea",
        "vmtx",
    ]
)


def asFea(g):
    if hasattr(g, "asFea"):
        return g.asFea()
    elif isinstance(g, tuple) and len(g) == 2:
        return asFea(g[0]) + " - " + asFea(g[1])  # a range
    elif g.lower() in fea_keywords:
        return "\\" + g
    else:
        return g


class Element(object):
    """A base class representing "something" in a feature file."""

    def __init__(self, location=None):
        #: location of this element as a `FeatureLibLocation` object.
        if location and not isinstance(location, FeatureLibLocation):
            location = FeatureLibLocation(*location)
        self.location = location

    def build(self, builder):
        pass

    def asFea(self, indent=""):
        """Returns this element as a string of feature code. For block-type
        elements (such as :class:`FeatureBlock`), the `indent` string is
        added to the start of each line in the output."""
        raise NotImplementedError

    def __str__(self):
        return self.asFea()


class Statement(Element):
    pass


class Expression(Element):
    pass


class Comment(Element):
    """A comment in a feature file."""

    def __init__(self, text, location=None):
        super(Comment, self).__init__(location)
        #: Text of the comment
        self.text = text

    def asFea(self, indent=""):
        return self.text


class NullGlyph(Expression):
    """The NULL glyph, used in glyph deletion substitutions."""

    def __init__(self, location=None):
        Expression.__init__(self, location)
        #: The name itself as a string

    def glyphSet(self):
        """The glyphs in this class as a tuple of :class:`GlyphName` objects."""
        return ()

    def asFea(self, indent=""):
        return "NULL"


class GlyphName(Expression):
    """A single glyph name, such as ``cedilla``."""

    def __init__(self, glyph, location=None):
        Expression.__init__(self, location)
        #: The name itself as a string
        self.glyph = glyph

    def glyphSet(self):
        """The glyphs in this class as a tuple of :class:`GlyphName` objects."""
        return (self.glyph,)

    def asFea(self, indent=""):
        return asFea(self.glyph)


class GlyphClass(Expression):
    """A glyph class, such as ``[acute cedilla grave]``."""

    def __init__(self, glyphs=None, location=None):
        Expression.__init__(self, location)
        #: The list of glyphs in this class, as :class:`GlyphName` objects.
        self.glyphs = glyphs if glyphs is not None else []
        self.original = []
        self.curr = 0

    def glyphSet(self):
        """The glyphs in this class as a tuple of :class:`GlyphName` objects."""
        return tuple(self.glyphs)

    def asFea(self, indent=""):
        if len(self.original):
            if self.curr < len(self.glyphs):
                self.original.extend(self.glyphs[self.curr :])
                self.curr = len(self.glyphs)
            return "[" + " ".join(map(asFea, self.original)) + "]"
        else:
            return "[" + " ".join(map(asFea, self.glyphs)) + "]"

    def extend(self, glyphs):
        """Add a list of :class:`GlyphName` objects to the class."""
        self.glyphs.extend(glyphs)

    def append(self, glyph):
        """Add a single :class:`GlyphName` object to the class."""
        self.glyphs.append(glyph)

    def add_range(self, start, end, glyphs):
        """Add a range (e.g. ``A-Z``) to the class. ``start`` and ``end``
        are either :class:`GlyphName` objects or strings representing the
        start and end glyphs in the class, and ``glyphs`` is the full list of
        :class:`GlyphName` objects in the range."""
        if self.curr < len(self.glyphs):
            self.original.extend(self.glyphs[self.curr :])
        self.original.append((start, end))
        self.glyphs.extend(glyphs)
        self.curr = len(self.glyphs)

    def add_cid_range(self, start, end, glyphs):
        """Add a range to the class by glyph ID. ``start`` and ``end`` are the
        initial and final IDs, and ``glyphs`` is the full list of
        :class:`GlyphName` objects in the range."""
        if self.curr < len(self.glyphs):
            self.original.extend(self.glyphs[self.curr :])
        self.original.append(("\\{}".format(start), "\\{}".format(end)))
        self.glyphs.extend(glyphs)
        self.curr = len(self.glyphs)

    def add_class(self, gc):
        """Add glyphs from the given :class:`GlyphClassName` object to the
        class."""
        if self.curr < len(self.glyphs):
            self.original.extend(self.glyphs[self.curr :])
        self.original.append(gc)
        self.glyphs.extend(gc.glyphSet())
        self.curr = len(self.glyphs)


class GlyphClassName(Expression):
    """A glyph class name, such as ``@FRENCH_MARKS``. This must be instantiated
    with a :class:`GlyphClassDefinition` object."""

    def __init__(self, glyphclass, location=None):
        Expression.__init__(self, location)
        assert isinstance(glyphclass, GlyphClassDefinition)
        self.glyphclass = glyphclass

    def glyphSet(self):
        """The glyphs in this class as a tuple of :class:`GlyphName` objects."""
        return tuple(self.glyphclass.glyphSet())

    def asFea(self, indent=""):
        return "@" + self.glyphclass.name


class MarkClassName(Expression):
    """A mark class name, such as ``@FRENCH_MARKS`` defined with ``markClass``.
    This must be instantiated with a :class:`MarkClass` object."""

    def __init__(self, markClass, location=None):
        Expression.__init__(self, location)
        assert isinstance(markClass, MarkClass)
        self.markClass = markClass

    def glyphSet(self):
        """The glyphs in this class as a tuple of :class:`GlyphName` objects."""
        return self.markClass.glyphSet()

    def asFea(self, indent=""):
        return "@" + self.markClass.name


class AnonymousBlock(Statement):
    """An anonymous data block."""

    def __init__(self, tag, content, location=None):
        Statement.__init__(self, location)
        self.tag = tag  #: string containing the block's "tag"
        self.content = content  #: block data as string

    def asFea(self, indent=""):
        res = "anon {} {{\n".format(self.tag)
        res += self.content
        res += "}} {};\n\n".format(self.tag)
        return res


class Block(Statement):
    """A block of statements: feature, lookup, etc."""

    def __init__(self, location=None):
        Statement.__init__(self, location)
        self.statements = []  #: Statements contained in the block

    def build(self, builder):
        """When handed a 'builder' object of comparable interface to
        :class:`fontTools.feaLib.builder`, walks the statements in this
        block, calling the builder callbacks."""
        for s in self.statements:
            s.build(builder)

    def asFea(self, indent=""):
        indent += SHIFT
        return (
            indent
            + ("\n" + indent).join([s.asFea(indent=indent) for s in self.statements])
            + "\n"
        )


class FeatureFile(Block):
    """The top-level element of the syntax tree, containing the whole feature
    file in its ``statements`` attribute."""

    def __init__(self):
        Block.__init__(self, location=None)
        self.markClasses = {}  # name --> ast.MarkClass

    def asFea(self, indent=""):
        return "\n".join(s.asFea(indent=indent) for s in self.statements)


class FeatureBlock(Block):
    """A named feature block."""

    def __init__(self, name, use_extension=False, location=None):
        Block.__init__(self, location)
        self.name, self.use_extension = name, use_extension

    def build(self, builder):
        """Call the ``start_feature`` callback on the builder object, visit
        all the statements in this feature, and then call ``end_feature``."""
        builder.start_feature(self.location, self.name, self.use_extension)
        # language exclude_dflt statements modify builder.features_
        # limit them to this block with temporary builder.features_
        features = builder.features_
        builder.features_ = {}
        Block.build(self, builder)
        for key, value in builder.features_.items():
            features.setdefault(key, []).extend(value)
        builder.features_ = features
        builder.end_feature()

    def asFea(self, indent=""):
        res = indent + "feature %s " % self.name.strip()
        if self.use_extension:
            res += "useExtension "
        res += "{\n"
        res += Block.asFea(self, indent=indent)
        res += indent + "} %s;\n" % self.name.strip()
        return res


class NestedBlock(Block):
    """A block inside another block, for example when found inside a
    ``cvParameters`` block."""

    def __init__(self, tag, block_name, location=None):
        Block.__init__(self, location)
        self.tag = tag
        self.block_name = block_name

    def build(self, builder):
        Block.build(self, builder)
        if self.block_name == "ParamUILabelNameID":
            builder.add_to_cv_num_named_params(self.tag)

    def asFea(self, indent=""):
        res = "{}{} {{\n".format(indent, self.block_name)
        res += Block.asFea(self, indent=indent)
        res += "{}}};\n".format(indent)
        return res


class LookupBlock(Block):
    """A named lookup, containing ``statements``."""

    def __init__(self, name, use_extension=False, location=None):
        Block.__init__(self, location)
        self.name, self.use_extension = name, use_extension

    def build(self, builder):
        builder.start_lookup_block(self.location, self.name, self.use_extension)
        Block.build(self, builder)
        builder.end_lookup_block()

    def asFea(self, indent=""):
        res = "lookup {} ".format(self.name)
        if self.use_extension:
            res += "useExtension "
        res += "{\n"
        res += Block.asFea(self, indent=indent)
        res += "{}}} {};\n".format(indent, self.name)
        return res


class TableBlock(Block):
    """A ``table ... { }`` block."""

    def __init__(self, name, location=None):
        Block.__init__(self, location)
        self.name = name

    def asFea(self, indent=""):
        res = "table {} {{\n".format(self.name.strip())
        res += super(TableBlock, self).asFea(indent=indent)
        res += "}} {};\n".format(self.name.strip())
        return res


class GlyphClassDefinition(Statement):
    """Example: ``@UPPERCASE = [A-Z];``."""

    def __init__(self, name, glyphs, location=None):
        Statement.__init__(self, location)
        self.name = name  #: class name as a string, without initial ``@``
        self.glyphs = glyphs  #: a :class:`GlyphClass` object

    def glyphSet(self):
        """The glyphs in this class as a tuple of :class:`GlyphName` objects."""
        return tuple(self.glyphs.glyphSet())

    def asFea(self, indent=""):
        return "@" + self.name + " = " + self.glyphs.asFea() + ";"


class GlyphClassDefStatement(Statement):
    """Example: ``GlyphClassDef @UPPERCASE, [B], [C], [D];``. The parameters
    must be either :class:`GlyphClass` or :class:`GlyphClassName` objects, or
    ``None``."""

    def __init__(
        self, baseGlyphs, markGlyphs, ligatureGlyphs, componentGlyphs, location=None
    ):
        Statement.__init__(self, location)
        self.baseGlyphs, self.markGlyphs = (baseGlyphs, markGlyphs)
        self.ligatureGlyphs = ligatureGlyphs
        self.componentGlyphs = componentGlyphs

    def build(self, builder):
        """Calls the builder's ``add_glyphClassDef`` callback."""
        base = self.baseGlyphs.glyphSet() if self.baseGlyphs else tuple()
        liga = self.ligatureGlyphs.glyphSet() if self.ligatureGlyphs else tuple()
        mark = self.markGlyphs.glyphSet() if self.markGlyphs else tuple()
        comp = self.componentGlyphs.glyphSet() if self.componentGlyphs else tuple()
        builder.add_glyphClassDef(self.location, base, liga, mark, comp)

    def asFea(self, indent=""):
        return "GlyphClassDef {}, {}, {}, {};".format(
            self.baseGlyphs.asFea() if self.baseGlyphs else "",
            self.ligatureGlyphs.asFea() if self.ligatureGlyphs else "",
            self.markGlyphs.asFea() if self.markGlyphs else "",
            self.componentGlyphs.asFea() if self.componentGlyphs else "",
        )


class MarkClass(object):
    """One `or more` ``markClass`` statements for the same mark class.

    While glyph classes can be defined only once, the feature file format
    allows expanding mark classes with multiple definitions, each using
    different glyphs and anchors. The following are two ``MarkClassDefinitions``
    for the same ``MarkClass``::

        markClass [acute grave] <anchor 350 800> @FRENCH_ACCENTS;
        markClass [cedilla] <anchor 350 -200> @FRENCH_ACCENTS;

    The ``MarkClass`` object is therefore just a container for a list of
    :class:`MarkClassDefinition` statements.
    """

    def __init__(self, name):
        self.name = name
        self.definitions = []
        self.glyphs = OrderedDict()  # glyph --> ast.MarkClassDefinitions

    def addDefinition(self, definition):
        """Add a :class:`MarkClassDefinition` statement to this mark class."""
        assert isinstance(definition, MarkClassDefinition)
        self.definitions.append(definition)
        for glyph in definition.glyphSet():
            if glyph in self.glyphs:
                otherLoc = self.glyphs[glyph].location
                if otherLoc is None:
                    end = ""
                else:
                    end = f" at {otherLoc}"
                raise FeatureLibError(
                    "Glyph %s already defined%s" % (glyph, end), definition.location
                )
            self.glyphs[glyph] = definition

    def glyphSet(self):
        """The glyphs in this class as a tuple of :class:`GlyphName` objects."""
        return tuple(self.glyphs.keys())

    def asFea(self, indent=""):
        res = "\n".join(d.asFea() for d in self.definitions)
        return res


class MarkClassDefinition(Statement):
    """A single ``markClass`` statement. The ``markClass`` should be a
    :class:`MarkClass` object, the ``anchor`` an :class:`Anchor` object,
    and the ``glyphs`` parameter should be a `glyph-containing object`_ .

    Example:

        .. code:: python

            mc = MarkClass("FRENCH_ACCENTS")
            mc.addDefinition( MarkClassDefinition(mc, Anchor(350, 800),
                GlyphClass([ GlyphName("acute"), GlyphName("grave") ])
            ) )
            mc.addDefinition( MarkClassDefinition(mc, Anchor(350, -200),
                GlyphClass([ GlyphName("cedilla") ])
            ) )

            mc.asFea()
            # markClass [acute grave] <anchor 350 800> @FRENCH_ACCENTS;
            # markClass [cedilla] <anchor 350 -200> @FRENCH_ACCENTS;

    """

    def __init__(self, markClass, anchor, glyphs, location=None):
        Statement.__init__(self, location)
        assert isinstance(markClass, MarkClass)
        assert isinstance(anchor, Anchor) and isinstance(glyphs, Expression)
        self.markClass, self.anchor, self.glyphs = markClass, anchor, glyphs

    def glyphSet(self):
        """The glyphs in this class as a tuple of :class:`GlyphName` objects."""
        return self.glyphs.glyphSet()

    def asFea(self, indent=""):
        return "markClass {} {} @{};".format(
            self.glyphs.asFea(), self.anchor.asFea(), self.markClass.name
        )


class AlternateSubstStatement(Statement):
    """A ``sub ... from ...`` statement.

    ``glyph`` and ``replacement`` should be `glyph-containing objects`_.
    ``prefix`` and ``suffix`` should be lists of `glyph-containing objects`_."""

    def __init__(self, prefix, glyph, suffix, replacement, location=None):
        Statement.__init__(self, location)
        self.prefix, self.glyph, self.suffix = (prefix, glyph, suffix)
        self.replacement = replacement

    def build(self, builder):
        """Calls the builder's ``add_alternate_subst`` callback."""
        glyph = self.glyph.glyphSet()
        assert len(glyph) == 1, glyph
        glyph = list(glyph)[0]
        prefix = [p.glyphSet() for p in self.prefix]
        suffix = [s.glyphSet() for s in self.suffix]
        replacement = self.replacement.glyphSet()
        builder.add_alternate_subst(self.location, prefix, glyph, suffix, replacement)

    def asFea(self, indent=""):
        res = "sub "
        if len(self.prefix) or len(self.suffix):
            if len(self.prefix):
                res += " ".join(map(asFea, self.prefix)) + " "
            res += asFea(self.glyph) + "'"  # even though we really only use 1
            if len(self.suffix):
                res += " " + " ".join(map(asFea, self.suffix))
        else:
            res += asFea(self.glyph)
        res += " from "
        res += asFea(self.replacement)
        res += ";"
        return res


class Anchor(Expression):
    """An ``Anchor`` element, used inside a ``pos`` rule.

    If a ``name`` is given, this will be used in preference to the coordinates.
    Other values should be integer.
    """

    def __init__(
        self,
        x,
        y,
        name=None,
        contourpoint=None,
        xDeviceTable=None,
        yDeviceTable=None,
        location=None,
    ):
        Expression.__init__(self, location)
        self.name = name
        self.x, self.y, self.contourpoint = x, y, contourpoint
        self.xDeviceTable, self.yDeviceTable = xDeviceTable, yDeviceTable

    def asFea(self, indent=""):
        if self.name is not None:
            return "<anchor {}>".format(self.name)
        res = "<anchor {} {}".format(self.x, self.y)
        if self.contourpoint:
            res += " contourpoint {}".format(self.contourpoint)
        if self.xDeviceTable or self.yDeviceTable:
            res += " "
            res += deviceToString(self.xDeviceTable)
            res += " "
            res += deviceToString(self.yDeviceTable)
        res += ">"
        return res


class AnchorDefinition(Statement):
    """A named anchor definition. (2.e.viii). ``name`` should be a string."""

    def __init__(self, name, x, y, contourpoint=None, location=None):
        Statement.__init__(self, location)
        self.name, self.x, self.y, self.contourpoint = name, x, y, contourpoint

    def asFea(self, indent=""):
        res = "anchorDef {} {}".format(self.x, self.y)
        if self.contourpoint:
            res += " contourpoint {}".format(self.contourpoint)
        res += " {};".format(self.name)
        return res


class AttachStatement(Statement):
    """A ``GDEF`` table ``Attach`` statement."""

    def __init__(self, glyphs, contourPoints, location=None):
        Statement.__init__(self, location)
        self.glyphs = glyphs  #: A `glyph-containing object`_
        self.contourPoints = contourPoints  #: A list of integer contour points

    def build(self, builder):
        """Calls the builder's ``add_attach_points`` callback."""
        glyphs = self.glyphs.glyphSet()
        builder.add_attach_points(self.location, glyphs, self.contourPoints)

    def asFea(self, indent=""):
        return "Attach {} {};".format(
            self.glyphs.asFea(), " ".join(str(c) for c in self.contourPoints)
        )


class ChainContextPosStatement(Statement):
    r"""A chained contextual positioning statement.

    ``prefix``, ``glyphs``, and ``suffix`` should be lists of
    `glyph-containing objects`_ .

    ``lookups`` should be a list of elements representing what lookups
    to apply at each glyph position. Each element should be a
    :class:`LookupBlock` to apply a single chaining lookup at the given
    position, a list of :class:`LookupBlock`\ s to apply multiple
    lookups, or ``None`` to apply no lookup. The length of the outer
    list should equal the length of ``glyphs``; the inner lists can be
    of variable length."""

    def __init__(self, prefix, glyphs, suffix, lookups, location=None):
        Statement.__init__(self, location)
        self.prefix, self.glyphs, self.suffix = prefix, glyphs, suffix
        self.lookups = list(lookups)
        for i, lookup in enumerate(lookups):
            if lookup:
                try:
                    iter(lookup)
                except TypeError:
                    self.lookups[i] = [lookup]

    def build(self, builder):
        """Calls the builder's ``add_chain_context_pos`` callback."""
        prefix = [p.glyphSet() for p in self.prefix]
        glyphs = [g.glyphSet() for g in self.glyphs]
        suffix = [s.glyphSet() for s in self.suffix]
        builder.add_chain_context_pos(
            self.location, prefix, glyphs, suffix, self.lookups
        )

    def asFea(self, indent=""):
        res = "pos "
        if (
            len(self.prefix)
            or len(self.suffix)
            or any([x is not None for x in self.lookups])
        ):
            if len(self.prefix):
                res += " ".join(g.asFea() for g in self.prefix) + " "
            for i, g in enumerate(self.glyphs):
                res += g.asFea() + "'"
                if self.lookups[i]:
                    for lu in self.lookups[i]:
                        res += " lookup " + lu.name
                if i < len(self.glyphs) - 1:
                    res += " "
            if len(self.suffix):
                res += " " + " ".join(map(asFea, self.suffix))
        else:
            res += " ".join(map(asFea, self.glyphs))
        res += ";"
        return res


class ChainContextSubstStatement(Statement):
    r"""A chained contextual substitution statement.

    ``prefix``, ``glyphs``, and ``suffix`` should be lists of
    `glyph-containing objects`_ .

    ``lookups`` should be a list of elements representing what lookups
    to apply at each glyph position. Each element should be a
    :class:`LookupBlock` to apply a single chaining lookup at the given
    position, a list of :class:`LookupBlock`\ s to apply multiple
    lookups, or ``None`` to apply no lookup. The length of the outer
    list should equal the length of ``glyphs``; the inner lists can be
    of variable length."""

    def __init__(self, prefix, glyphs, suffix, lookups, location=None):
        Statement.__init__(self, location)
        self.prefix, self.glyphs, self.suffix = prefix, glyphs, suffix
        self.lookups = list(lookups)
        for i, lookup in enumerate(lookups):
            if lookup:
                try:
                    iter(lookup)
                except TypeError:
                    self.lookups[i] = [lookup]

    def build(self, builder):
        """Calls the builder's ``add_chain_context_subst`` callback."""
        prefix = [p.glyphSet() for p in self.prefix]
        glyphs = [g.glyphSet() for g in self.glyphs]
        suffix = [s.glyphSet() for s in self.suffix]
        builder.add_chain_context_subst(
            self.location, prefix, glyphs, suffix, self.lookups
        )

    def asFea(self, indent=""):
        res = "sub "
        if (
            len(self.prefix)
            or len(self.suffix)
            or any([x is not None for x in self.lookups])
        ):
            if len(self.prefix):
                res += " ".join(g.asFea() for g in self.prefix) + " "
            for i, g in enumerate(self.glyphs):
                res += g.asFea() + "'"
                if self.lookups[i]:
                    for lu in self.lookups[i]:
                        res += " lookup " + lu.name
                if i < len(self.glyphs) - 1:
                    res += " "
            if len(self.suffix):
                res += " " + " ".join(map(asFea, self.suffix))
        else:
            res += " ".join(map(asFea, self.glyphs))
        res += ";"
        return res


class CursivePosStatement(Statement):
    """A cursive positioning statement. Entry and exit anchors can either
    be :class:`Anchor` objects or ``None``."""

    def __init__(self, glyphclass, entryAnchor, exitAnchor, location=None):
        Statement.__init__(self, location)
        self.glyphclass = glyphclass
        self.entryAnchor, self.exitAnchor = entryAnchor, exitAnchor

    def build(self, builder):
        """Calls the builder object's ``add_cursive_pos`` callback."""
        builder.add_cursive_pos(
            self.location, self.glyphclass.glyphSet(), self.entryAnchor, self.exitAnchor
        )

    def asFea(self, indent=""):
        entry = self.entryAnchor.asFea() if self.entryAnchor else "<anchor NULL>"
        exit = self.exitAnchor.asFea() if self.exitAnchor else "<anchor NULL>"
        return "pos cursive {} {} {};".format(self.glyphclass.asFea(), entry, exit)


class FeatureReferenceStatement(Statement):
    """Example: ``feature salt;``"""

    def __init__(self, featureName, location=None):
        Statement.__init__(self, location)
        self.location, self.featureName = (location, featureName)

    def build(self, builder):
        """Calls the builder object's ``add_feature_reference`` callback."""
        builder.add_feature_reference(self.location, self.featureName)

    def asFea(self, indent=""):
        return "feature {};".format(self.featureName)


class IgnorePosStatement(Statement):
    """An ``ignore pos`` statement, containing `one or more` contexts to ignore.

    ``chainContexts`` should be a list of ``(prefix, glyphs, suffix)`` tuples,
    with each of ``prefix``, ``glyphs`` and ``suffix`` being
    `glyph-containing objects`_ ."""

    def __init__(self, chainContexts, location=None):
        Statement.__init__(self, location)
        self.chainContexts = chainContexts

    def build(self, builder):
        """Calls the builder object's ``add_chain_context_pos`` callback on each
        rule context."""
        for prefix, glyphs, suffix in self.chainContexts:
            prefix = [p.glyphSet() for p in prefix]
            glyphs = [g.glyphSet() for g in glyphs]
            suffix = [s.glyphSet() for s in suffix]
            builder.add_chain_context_pos(self.location, prefix, glyphs, suffix, [])

    def asFea(self, indent=""):
        contexts = []
        for prefix, glyphs, suffix in self.chainContexts:
            res = ""
            if len(prefix) or len(suffix):
                if len(prefix):
                    res += " ".join(map(asFea, prefix)) + " "
                res += " ".join(g.asFea() + "'" for g in glyphs)
                if len(suffix):
                    res += " " + " ".join(map(asFea, suffix))
            else:
                res += " ".join(map(asFea, glyphs))
            contexts.append(res)
        return "ignore pos " + ", ".join(contexts) + ";"


class IgnoreSubstStatement(Statement):
    """An ``ignore sub`` statement, containing `one or more` contexts to ignore.

    ``chainContexts`` should be a list of ``(prefix, glyphs, suffix)`` tuples,
    with each of ``prefix``, ``glyphs`` and ``suffix`` being
    `glyph-containing objects`_ ."""

    def __init__(self, chainContexts, location=None):
        Statement.__init__(self, location)
        self.chainContexts = chainContexts

    def build(self, builder):
        """Calls the builder object's ``add_chain_context_subst`` callback on
        each rule context."""
        for prefix, glyphs, suffix in self.chainContexts:
            prefix = [p.glyphSet() for p in prefix]
            glyphs = [g.glyphSet() for g in glyphs]
            suffix = [s.glyphSet() for s in suffix]
            builder.add_chain_context_subst(self.location, prefix, glyphs, suffix, [])

    def asFea(self, indent=""):
        contexts = []
        for prefix, glyphs, suffix in self.chainContexts:
            res = ""
            if len(prefix):
                res += " ".join(map(asFea, prefix)) + " "
            res += " ".join(g.asFea() + "'" for g in glyphs)
            if len(suffix):
                res += " " + " ".join(map(asFea, suffix))
            contexts.append(res)
        return "ignore sub " + ", ".join(contexts) + ";"


class IncludeStatement(Statement):
    """An ``include()`` statement."""

    def __init__(self, filename, location=None):
        super(IncludeStatement, self).__init__(location)
        self.filename = filename  #: String containing name of file to include

    def build(self):
        # TODO: consider lazy-loading the including parser/lexer?
        raise FeatureLibError(
            "Building an include statement is not implemented yet. "
            "Instead, use Parser(..., followIncludes=True) for building.",
            self.location,
        )

    def asFea(self, indent=""):
        return indent + "include(%s);" % self.filename


class LanguageStatement(Statement):
    """A ``language`` statement within a feature."""

    def __init__(self, language, include_default=True, required=False, location=None):
        Statement.__init__(self, location)
        assert len(language) == 4
        self.language = language  #: A four-character language tag
        self.include_default = include_default  #: If false, "exclude_dflt"
        self.required = required

    def build(self, builder):
        """Call the builder object's ``set_language`` callback."""
        builder.set_language(
            location=self.location,
            language=self.language,
            include_default=self.include_default,
            required=self.required,
        )

    def asFea(self, indent=""):
        res = "language {}".format(self.language.strip())
        if not self.include_default:
            res += " exclude_dflt"
        if self.required:
            res += " required"
        res += ";"
        return res


class LanguageSystemStatement(Statement):
    """A top-level ``languagesystem`` statement."""

    def __init__(self, script, language, location=None):
        Statement.__init__(self, location)
        self.script, self.language = (script, language)

    def build(self, builder):
        """Calls the builder object's ``add_language_system`` callback."""
        builder.add_language_system(self.location, self.script, self.language)

    def asFea(self, indent=""):
        return "languagesystem {} {};".format(self.script, self.language.strip())


class FontRevisionStatement(Statement):
    """A ``head`` table ``FontRevision`` statement. ``revision`` should be a
    number, and will be formatted to three significant decimal places."""

    def __init__(self, revision, location=None):
        Statement.__init__(self, location)
        self.revision = revision

    def build(self, builder):
        builder.set_font_revision(self.location, self.revision)

    def asFea(self, indent=""):
        return "FontRevision {:.3f};".format(self.revision)


class LigatureCaretByIndexStatement(Statement):
    """A ``GDEF`` table ``LigatureCaretByIndex`` statement. ``glyphs`` should be
    a `glyph-containing object`_, and ``carets`` should be a list of integers."""

    def __init__(self, glyphs, carets, location=None):
        Statement.__init__(self, location)
        self.glyphs, self.carets = (glyphs, carets)

    def build(self, builder):
        """Calls the builder object's ``add_ligatureCaretByIndex_`` callback."""
        glyphs = self.glyphs.glyphSet()
        builder.add_ligatureCaretByIndex_(self.location, glyphs, set(self.carets))

    def asFea(self, indent=""):
        return "LigatureCaretByIndex {} {};".format(
            self.glyphs.asFea(), " ".join(str(x) for x in self.carets)
        )


class LigatureCaretByPosStatement(Statement):
    """A ``GDEF`` table ``LigatureCaretByPos`` statement. ``glyphs`` should be
    a `glyph-containing object`_, and ``carets`` should be a list of integers."""

    def __init__(self, glyphs, carets, location=None):
        Statement.__init__(self, location)
        self.glyphs, self.carets = (glyphs, carets)

    def build(self, builder):
        """Calls the builder object's ``add_ligatureCaretByPos_`` callback."""
        glyphs = self.glyphs.glyphSet()
        builder.add_ligatureCaretByPos_(self.location, glyphs, set(self.carets))

    def asFea(self, indent=""):
        return "LigatureCaretByPos {} {};".format(
            self.glyphs.asFea(), " ".join(str(x) for x in self.carets)
        )


class LigatureSubstStatement(Statement):
    """A chained contextual substitution statement.

    ``prefix``, ``glyphs``, and ``suffix`` should be lists of
    `glyph-containing objects`_; ``replacement`` should be a single
    `glyph-containing object`_.

    If ``forceChain`` is True, this is expressed as a chaining rule
    (e.g. ``sub f' i' by f_i``) even when no context is given."""

    def __init__(self, prefix, glyphs, suffix, replacement, forceChain, location=None):
        Statement.__init__(self, location)
        self.prefix, self.glyphs, self.suffix = (prefix, glyphs, suffix)
        self.replacement, self.forceChain = replacement, forceChain

    def build(self, builder):
        prefix = [p.glyphSet() for p in self.prefix]
        glyphs = [g.glyphSet() for g in self.glyphs]
        suffix = [s.glyphSet() for s in self.suffix]
        builder.add_ligature_subst(
            self.location, prefix, glyphs, suffix, self.replacement, self.forceChain
        )

    def asFea(self, indent=""):
        res = "sub "
        if len(self.prefix) or len(self.suffix) or self.forceChain:
            if len(self.prefix):
                res += " ".join(g.asFea() for g in self.prefix) + " "
            res += " ".join(g.asFea() + "'" for g in self.glyphs)
            if len(self.suffix):
                res += " " + " ".join(g.asFea() for g in self.suffix)
        else:
            res += " ".join(g.asFea() for g in self.glyphs)
        res += " by "
        res += asFea(self.replacement)
        res += ";"
        return res


class LookupFlagStatement(Statement):
    """A ``lookupflag`` statement. The ``value`` should be an integer value
    representing the flags in use, but not including the ``markAttachment``
    class and ``markFilteringSet`` values, which must be specified as
    glyph-containing objects."""

    def __init__(
        self, value=0, markAttachment=None, markFilteringSet=None, location=None
    ):
        Statement.__init__(self, location)
        self.value = value
        self.markAttachment = markAttachment
        self.markFilteringSet = markFilteringSet

    def build(self, builder):
        """Calls the builder object's ``set_lookup_flag`` callback."""
        markAttach = None
        if self.markAttachment is not None:
            markAttach = self.markAttachment.glyphSet()
        markFilter = None
        if self.markFilteringSet is not None:
            markFilter = self.markFilteringSet.glyphSet()
        builder.set_lookup_flag(self.location, self.value, markAttach, markFilter)

    def asFea(self, indent=""):
        res = []
        flags = ["RightToLeft", "IgnoreBaseGlyphs", "IgnoreLigatures", "IgnoreMarks"]
        curr = 1
        for i in range(len(flags)):
            if self.value & curr != 0:
                res.append(flags[i])
            curr = curr << 1
        if self.markAttachment is not None:
            res.append("MarkAttachmentType {}".format(self.markAttachment.asFea()))
        if self.markFilteringSet is not None:
            res.append("UseMarkFilteringSet {}".format(self.markFilteringSet.asFea()))
        if not res:
            res = ["0"]
        return "lookupflag {};".format(" ".join(res))


class LookupReferenceStatement(Statement):
    """Represents a ``lookup ...;`` statement to include a lookup in a feature.

    The ``lookup`` should be a :class:`LookupBlock` object."""

    def __init__(self, lookup, location=None):
        Statement.__init__(self, location)
        self.location, self.lookup = (location, lookup)

    def build(self, builder):
        """Calls the builder object's ``add_lookup_call`` callback."""
        builder.add_lookup_call(self.lookup.name)

    def asFea(self, indent=""):
        return "lookup {};".format(self.lookup.name)


class MarkBasePosStatement(Statement):
    """A mark-to-base positioning rule. The ``base`` should be a
    `glyph-containing object`_. The ``marks`` should be a list of
    (:class:`Anchor`, :class:`MarkClass`) tuples."""

    def __init__(self, base, marks, location=None):
        Statement.__init__(self, location)
        self.base, self.marks = base, marks

    def build(self, builder):
        """Calls the builder object's ``add_mark_base_pos`` callback."""
        builder.add_mark_base_pos(self.location, self.base.glyphSet(), self.marks)

    def asFea(self, indent=""):
        res = "pos base {}".format(self.base.asFea())
        for a, m in self.marks:
            res += "\n" + indent + SHIFT + "{} mark @{}".format(a.asFea(), m.name)
        res += ";"
        return res


class MarkLigPosStatement(Statement):
    """A mark-to-ligature positioning rule. The ``ligatures`` must be a
    `glyph-containing object`_. The ``marks`` should be a list of lists: each
    element in the top-level list represents a component glyph, and is made
    up of a list of (:class:`Anchor`, :class:`MarkClass`) tuples representing
    mark attachment points for that position.

    Example::

        m1 = MarkClass("TOP_MARKS")
        m2 = MarkClass("BOTTOM_MARKS")
        # ... add definitions to mark classes...

        glyph = GlyphName("lam_meem_jeem")
        marks = [
            [ (Anchor(625,1800), m1) ], # Attachments on 1st component (lam)
            [ (Anchor(376,-378), m2) ], # Attachments on 2nd component (meem)
            [ ]                         # No attachments on the jeem
        ]
        mlp = MarkLigPosStatement(glyph, marks)

        mlp.asFea()
        # pos ligature lam_meem_jeem <anchor 625 1800> mark @TOP_MARKS
        # ligComponent <anchor 376 -378> mark @BOTTOM_MARKS;

    """

    def __init__(self, ligatures, marks, location=None):
        Statement.__init__(self, location)
        self.ligatures, self.marks = ligatures, marks

    def build(self, builder):
        """Calls the builder object's ``add_mark_lig_pos`` callback."""
        builder.add_mark_lig_pos(self.location, self.ligatures.glyphSet(), self.marks)

    def asFea(self, indent=""):
        res = "pos ligature {}".format(self.ligatures.asFea())
        ligs = []
        for l in self.marks:
            temp = ""
            if l is None or not len(l):
                temp = "\n" + indent + SHIFT * 2 + "<anchor NULL>"
            else:
                for a, m in l:
                    temp += (
                        "\n"
                        + indent
                        + SHIFT * 2
                        + "{} mark @{}".format(a.asFea(), m.name)
                    )
            ligs.append(temp)
        res += ("\n" + indent + SHIFT + "ligComponent").join(ligs)
        res += ";"
        return res


class MarkMarkPosStatement(Statement):
    """A mark-to-mark positioning rule. The ``baseMarks`` must be a
    `glyph-containing object`_. The ``marks`` should be a list of
    (:class:`Anchor`, :class:`MarkClass`) tuples."""

    def __init__(self, baseMarks, marks, location=None):
        Statement.__init__(self, location)
        self.baseMarks, self.marks = baseMarks, marks

    def build(self, builder):
        """Calls the builder object's ``add_mark_mark_pos`` callback."""
        builder.add_mark_mark_pos(self.location, self.baseMarks.glyphSet(), self.marks)

    def asFea(self, indent=""):
        res = "pos mark {}".format(self.baseMarks.asFea())
        for a, m in self.marks:
            res += "\n" + indent + SHIFT + "{} mark @{}".format(a.asFea(), m.name)
        res += ";"
        return res


class MultipleSubstStatement(Statement):
    """A multiple substitution statement.

    Args:
        prefix: a list of `glyph-containing objects`_.
        glyph: a single glyph-containing object.
        suffix: a list of glyph-containing objects.
        replacement: a list of glyph-containing objects.
        forceChain: If true, the statement is expressed as a chaining rule
            (e.g. ``sub f' i' by f_i``) even when no context is given.
    """

    def __init__(
        self, prefix, glyph, suffix, replacement, forceChain=False, location=None
    ):
        Statement.__init__(self, location)
        self.prefix, self.glyph, self.suffix = prefix, glyph, suffix
        self.replacement = replacement
        self.forceChain = forceChain

    def build(self, builder):
        """Calls the builder object's ``add_multiple_subst`` callback."""
        prefix = [p.glyphSet() for p in self.prefix]
        suffix = [s.glyphSet() for s in self.suffix]
        if hasattr(self.glyph, "glyphSet"):
            originals = self.glyph.glyphSet()
        else:
            originals = [self.glyph]
        count = len(originals)
        replaces = []
        for r in self.replacement:
            if hasattr(r, "glyphSet"):
                replace = r.glyphSet()
            else:
                replace = [r]
            if len(replace) == 1 and len(replace) != count:
                replace = replace * count
            replaces.append(replace)
        replaces = list(zip(*replaces))

        seen_originals = set()
        for i, original in enumerate(originals):
            if original not in seen_originals:
                seen_originals.add(original)
                builder.add_multiple_subst(
                    self.location,
                    prefix,
                    original,
                    suffix,
                    replaces and replaces[i] or (),
                    self.forceChain,
                )

    def asFea(self, indent=""):
        res = "sub "
        if len(self.prefix) or len(self.suffix) or self.forceChain:
            if len(self.prefix):
                res += " ".join(map(asFea, self.prefix)) + " "
            res += asFea(self.glyph) + "'"
            if len(self.suffix):
                res += " " + " ".join(map(asFea, self.suffix))
        else:
            res += asFea(self.glyph)
        replacement = self.replacement or [NullGlyph()]
        res += " by "
        res += " ".join(map(asFea, replacement))
        res += ";"
        return res


class PairPosStatement(Statement):
    """A pair positioning statement.

    ``glyphs1`` and ``glyphs2`` should be `glyph-containing objects`_.
    ``valuerecord1`` should be a :class:`ValueRecord` object;
    ``valuerecord2`` should be either a :class:`ValueRecord` object or ``None``.
    If ``enumerated`` is true, then this is expressed as an
    `enumerated pair <https://adobe-type-tools.github.io/afdko/OpenTypeFeatureFileSpecification.html#6.b.ii>`_.
    """

    def __init__(
        self,
        glyphs1,
        valuerecord1,
        glyphs2,
        valuerecord2,
        enumerated=False,
        location=None,
    ):
        Statement.__init__(self, location)
        self.enumerated = enumerated
        self.glyphs1, self.valuerecord1 = glyphs1, valuerecord1
        self.glyphs2, self.valuerecord2 = glyphs2, valuerecord2

    def build(self, builder):
        """Calls a callback on the builder object:

        * If the rule is enumerated, calls ``add_specific_pair_pos`` on each
          combination of first and second glyphs.
        * If the glyphs are both single :class:`GlyphName` objects, calls
          ``add_specific_pair_pos``.
        * Else, calls ``add_class_pair_pos``.
        """
        if self.enumerated:
            g = [self.glyphs1.glyphSet(), self.glyphs2.glyphSet()]
            seen_pair = False
            for glyph1, glyph2 in itertools.product(*g):
                seen_pair = True
                builder.add_specific_pair_pos(
                    self.location, glyph1, self.valuerecord1, glyph2, self.valuerecord2
                )
            if not seen_pair:
                raise FeatureLibError(
                    "Empty glyph class in positioning rule", self.location
                )
            return

        is_specific = isinstance(self.glyphs1, GlyphName) and isinstance(
            self.glyphs2, GlyphName
        )
        if is_specific:
            builder.add_specific_pair_pos(
                self.location,
                self.glyphs1.glyph,
                self.valuerecord1,
                self.glyphs2.glyph,
                self.valuerecord2,
            )
        else:
            builder.add_class_pair_pos(
                self.location,
                self.glyphs1.glyphSet(),
                self.valuerecord1,
                self.glyphs2.glyphSet(),
                self.valuerecord2,
            )

    def asFea(self, indent=""):
        res = "enum " if self.enumerated else ""
        if self.valuerecord2:
            res += "pos {} {} {} {};".format(
                self.glyphs1.asFea(),
                self.valuerecord1.asFea(),
                self.glyphs2.asFea(),
                self.valuerecord2.asFea(),
            )
        else:
            res += "pos {} {} {};".format(
                self.glyphs1.asFea(), self.glyphs2.asFea(), self.valuerecord1.asFea()
            )
        return res


class ReverseChainSingleSubstStatement(Statement):
    """A reverse chaining substitution statement. You don't see those every day.

    Note the unusual argument order: ``suffix`` comes `before` ``glyphs``.
    ``old_prefix``, ``old_suffix``, ``glyphs`` and ``replacements`` should be
    lists of `glyph-containing objects`_. ``glyphs`` and ``replacements`` should
    be one-item lists.
    """

    def __init__(self, old_prefix, old_suffix, glyphs, replacements, location=None):
        Statement.__init__(self, location)
        self.old_prefix, self.old_suffix = old_prefix, old_suffix
        self.glyphs = glyphs
        self.replacements = replacements

    def build(self, builder):
        prefix = [p.glyphSet() for p in self.old_prefix]
        suffix = [s.glyphSet() for s in self.old_suffix]
        originals = self.glyphs[0].glyphSet()
        replaces = self.replacements[0].glyphSet()
        if len(replaces) == 1:
            replaces = replaces * len(originals)
        builder.add_reverse_chain_single_subst(
            self.location, prefix, suffix, dict(zip(originals, replaces))
        )

    def asFea(self, indent=""):
        res = "rsub "
        if len(self.old_prefix) or len(self.old_suffix):
            if len(self.old_prefix):
                res += " ".join(asFea(g) for g in self.old_prefix) + " "
            res += " ".join(asFea(g) + "'" for g in self.glyphs)
            if len(self.old_suffix):
                res += " " + " ".join(asFea(g) for g in self.old_suffix)
        else:
            res += " ".join(map(asFea, self.glyphs))
        res += " by {};".format(" ".join(asFea(g) for g in self.replacements))
        return res


class SingleSubstStatement(Statement):
    """A single substitution statement.

    Note the unusual argument order: ``prefix`` and suffix come `after`
    the replacement ``glyphs``. ``prefix``, ``suffix``, ``glyphs`` and
    ``replace`` should be lists of `glyph-containing objects`_. ``glyphs`` and
    ``replace`` should be one-item lists.
    """

    def __init__(self, glyphs, replace, prefix, suffix, forceChain, location=None):
        Statement.__init__(self, location)
        self.prefix, self.suffix = prefix, suffix
        self.forceChain = forceChain
        self.glyphs = glyphs
        self.replacements = replace

    def build(self, builder):
        """Calls the builder object's ``add_single_subst`` callback."""
        prefix = [p.glyphSet() for p in self.prefix]
        suffix = [s.glyphSet() for s in self.suffix]
        originals = self.glyphs[0].glyphSet()
        replaces = self.replacements[0].glyphSet()
        if len(replaces) == 1:
            replaces = replaces * len(originals)
        builder.add_single_subst(
            self.location,
            prefix,
            suffix,
            OrderedDict(zip(originals, replaces)),
            self.forceChain,
        )

    def asFea(self, indent=""):
        res = "sub "
        if len(self.prefix) or len(self.suffix) or self.forceChain:
            if len(self.prefix):
                res += " ".join(asFea(g) for g in self.prefix) + " "
            res += " ".join(asFea(g) + "'" for g in self.glyphs)
            if len(self.suffix):
                res += " " + " ".join(asFea(g) for g in self.suffix)
        else:
            res += " ".join(asFea(g) for g in self.glyphs)
        res += " by {};".format(" ".join(asFea(g) for g in self.replacements))
        return res


class ScriptStatement(Statement):
    """A ``script`` statement."""

    def __init__(self, script, location=None):
        Statement.__init__(self, location)
        self.script = script  #: the script code

    def build(self, builder):
        """Calls the builder's ``set_script`` callback."""
        builder.set_script(self.location, self.script)

    def asFea(self, indent=""):
        return "script {};".format(self.script.strip())


class SinglePosStatement(Statement):
    """A single position statement. ``prefix`` and ``suffix`` should be
    lists of `glyph-containing objects`_.

    ``pos`` should be a one-element list containing a (`glyph-containing object`_,
    :class:`ValueRecord`) tuple."""

    def __init__(self, pos, prefix, suffix, forceChain, location=None):
        Statement.__init__(self, location)
        self.pos, self.prefix, self.suffix = pos, prefix, suffix
        self.forceChain = forceChain

    def build(self, builder):
        """Calls the builder object's ``add_single_pos`` callback."""
        prefix = [p.glyphSet() for p in self.prefix]
        suffix = [s.glyphSet() for s in self.suffix]
        pos = [(g.glyphSet(), value) for g, value in self.pos]
        builder.add_single_pos(self.location, prefix, suffix, pos, self.forceChain)

    def asFea(self, indent=""):
        res = "pos "
        if len(self.prefix) or len(self.suffix) or self.forceChain:
            if len(self.prefix):
                res += " ".join(map(asFea, self.prefix)) + " "
            res += " ".join(
                [
                    asFea(x[0])
                    + "'"
                    + ((" " + x[1].asFea()) if x[1] is not None else "")
                    for x in self.pos
                ]
            )
            if len(self.suffix):
                res += " " + " ".join(map(asFea, self.suffix))
        else:
            res += " ".join(
                [
                    asFea(x[0]) + " " + (x[1].asFea() if x[1] is not None else "")
                    for x in self.pos
                ]
            )
        res += ";"
        return res


class SubtableStatement(Statement):
    """Represents a subtable break."""

    def __init__(self, location=None):
        Statement.__init__(self, location)

    def build(self, builder):
        """Calls the builder objects's ``add_subtable_break`` callback."""
        builder.add_subtable_break(self.location)

    def asFea(self, indent=""):
        return "subtable;"


class ValueRecord(Expression):
    """Represents a value record."""

    def __init__(
        self,
        xPlacement=None,
        yPlacement=None,
        xAdvance=None,
        yAdvance=None,
        xPlaDevice=None,
        yPlaDevice=None,
        xAdvDevice=None,
        yAdvDevice=None,
        vertical=False,
        location=None,
    ):
        Expression.__init__(self, location)
        self.xPlacement, self.yPlacement = (xPlacement, yPlacement)
        self.xAdvance, self.yAdvance = (xAdvance, yAdvance)
        self.xPlaDevice, self.yPlaDevice = (xPlaDevice, yPlaDevice)
        self.xAdvDevice, self.yAdvDevice = (xAdvDevice, yAdvDevice)
        self.vertical = vertical

    def __eq__(self, other):
        return (
            self.xPlacement == other.xPlacement
            and self.yPlacement == other.yPlacement
            and self.xAdvance == other.xAdvance
            and self.yAdvance == other.yAdvance
            and self.xPlaDevice == other.xPlaDevice
            and self.xAdvDevice == other.xAdvDevice
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return (
            hash(self.xPlacement)
            ^ hash(self.yPlacement)
            ^ hash(self.xAdvance)
            ^ hash(self.yAdvance)
            ^ hash(self.xPlaDevice)
            ^ hash(self.yPlaDevice)
            ^ hash(self.xAdvDevice)
            ^ hash(self.yAdvDevice)
        )

    def asFea(self, indent=""):
        if not self:
            return "<NULL>"

        x, y = self.xPlacement, self.yPlacement
        xAdvance, yAdvance = self.xAdvance, self.yAdvance
        xPlaDevice, yPlaDevice = self.xPlaDevice, self.yPlaDevice
        xAdvDevice, yAdvDevice = self.xAdvDevice, self.yAdvDevice
        vertical = self.vertical

        # Try format A, if possible.
        if x is None and y is None:
            if xAdvance is None and vertical:
                return str(yAdvance)
            elif yAdvance is None and not vertical:
                return str(xAdvance)

        # Make any remaining None value 0 to avoid generating invalid records.
        x = x or 0
        y = y or 0
        xAdvance = xAdvance or 0
        yAdvance = yAdvance or 0

        # Try format B, if possible.
        if (
            xPlaDevice is None
            and yPlaDevice is None
            and xAdvDevice is None
            and yAdvDevice is None
        ):
            return "<%s %s %s %s>" % (x, y, xAdvance, yAdvance)

        # Last resort is format C.
        return "<%s %s %s %s %s %s %s %s>" % (
            x,
            y,
            xAdvance,
            yAdvance,
            deviceToString(xPlaDevice),
            deviceToString(yPlaDevice),
            deviceToString(xAdvDevice),
            deviceToString(yAdvDevice),
        )

    def __bool__(self):
        return any(
            getattr(self, v) is not None
            for v in [
                "xPlacement",
                "yPlacement",
                "xAdvance",
                "yAdvance",
                "xPlaDevice",
                "yPlaDevice",
                "xAdvDevice",
                "yAdvDevice",
            ]
        )

    __nonzero__ = __bool__


class ValueRecordDefinition(Statement):
    """Represents a named value record definition."""

    def __init__(self, name, value, location=None):
        Statement.__init__(self, location)
        self.name = name  #: Value record name as string
        self.value = value  #: :class:`ValueRecord` object

    def asFea(self, indent=""):
        return "valueRecordDef {} {};".format(self.value.asFea(), self.name)


def simplify_name_attributes(pid, eid, lid):
    if pid == 3 and eid == 1 and lid == 1033:
        return ""
    elif pid == 1 and eid == 0 and lid == 0:
        return "1"
    else:
        return "{} {} {}".format(pid, eid, lid)


class NameRecord(Statement):
    """Represents a name record. (`Section 9.e. <https://adobe-type-tools.github.io/afdko/OpenTypeFeatureFileSpecification.html#9.e>`_)"""

    def __init__(self, nameID, platformID, platEncID, langID, string, location=None):
        Statement.__init__(self, location)
        self.nameID = nameID  #: Name ID as integer (e.g. 9 for designer's name)
        self.platformID = platformID  #: Platform ID as integer
        self.platEncID = platEncID  #: Platform encoding ID as integer
        self.langID = langID  #: Language ID as integer
        self.string = string  #: Name record value

    def build(self, builder):
        """Calls the builder object's ``add_name_record`` callback."""
        builder.add_name_record(
            self.location,
            self.nameID,
            self.platformID,
            self.platEncID,
            self.langID,
            self.string,
        )

    def asFea(self, indent=""):
        def escape(c, escape_pattern):
            # Also escape U+0022 QUOTATION MARK and U+005C REVERSE SOLIDUS
            if c >= 0x20 and c <= 0x7E and c not in (0x22, 0x5C):
                return chr(c)
            else:
                return escape_pattern % c

        encoding = getEncoding(self.platformID, self.platEncID, self.langID)
        if encoding is None:
            raise FeatureLibError("Unsupported encoding", self.location)
        s = tobytes(self.string, encoding=encoding)
        if encoding == "utf_16_be":
            escaped_string = "".join(
                [
                    escape(byteord(s[i]) * 256 + byteord(s[i + 1]), r"\%04x")
                    for i in range(0, len(s), 2)
                ]
            )
        else:
            escaped_string = "".join([escape(byteord(b), r"\%02x") for b in s])
        plat = simplify_name_attributes(self.platformID, self.platEncID, self.langID)
        if plat != "":
            plat += " "
        return 'nameid {} {}"{}";'.format(self.nameID, plat, escaped_string)


class FeatureNameStatement(NameRecord):
    """Represents a ``sizemenuname`` or ``name`` statement."""

    def build(self, builder):
        """Calls the builder object's ``add_featureName`` callback."""
        NameRecord.build(self, builder)
        builder.add_featureName(self.nameID)

    def asFea(self, indent=""):
        if self.nameID == "size":
            tag = "sizemenuname"
        else:
            tag = "name"
        plat = simplify_name_attributes(self.platformID, self.platEncID, self.langID)
        if plat != "":
            plat += " "
        return '{} {}"{}";'.format(tag, plat, self.string)


class STATNameStatement(NameRecord):
    """Represents a STAT table ``name`` statement."""

    def asFea(self, indent=""):
        plat = simplify_name_attributes(self.platformID, self.platEncID, self.langID)
        if plat != "":
            plat += " "
        return 'name {}"{}";'.format(plat, self.string)


class SizeParameters(Statement):
    """A ``parameters`` statement."""

    def __init__(self, DesignSize, SubfamilyID, RangeStart, RangeEnd, location=None):
        Statement.__init__(self, location)
        self.DesignSize = DesignSize
        self.SubfamilyID = SubfamilyID
        self.RangeStart = RangeStart
        self.RangeEnd = RangeEnd

    def build(self, builder):
        """Calls the builder object's ``set_size_parameters`` callback."""
        builder.set_size_parameters(
            self.location,
            self.DesignSize,
            self.SubfamilyID,
            self.RangeStart,
            self.RangeEnd,
        )

    def asFea(self, indent=""):
        res = "parameters {:.1f} {}".format(self.DesignSize, self.SubfamilyID)
        if self.RangeStart != 0 or self.RangeEnd != 0:
            res += " {} {}".format(int(self.RangeStart * 10), int(self.RangeEnd * 10))
        return res + ";"


class CVParametersNameStatement(NameRecord):
    """Represent a name statement inside a ``cvParameters`` block."""

    def __init__(
        self, nameID, platformID, platEncID, langID, string, block_name, location=None
    ):
        NameRecord.__init__(
            self, nameID, platformID, platEncID, langID, string, location=location
        )
        self.block_name = block_name

    def build(self, builder):
        """Calls the builder object's ``add_cv_parameter`` callback."""
        item = ""
        if self.block_name == "ParamUILabelNameID":
            item = "_{}".format(builder.cv_num_named_params_.get(self.nameID, 0))
        builder.add_cv_parameter(self.nameID)
        self.nameID = (self.nameID, self.block_name + item)
        NameRecord.build(self, builder)

    def asFea(self, indent=""):
        plat = simplify_name_attributes(self.platformID, self.platEncID, self.langID)
        if plat != "":
            plat += " "
        return 'name {}"{}";'.format(plat, self.string)


class CharacterStatement(Statement):
    """
    Statement used in cvParameters blocks of Character Variant features (cvXX).
    The Unicode value may be written with either decimal or hexadecimal
    notation. The value must be preceded by '0x' if it is a hexadecimal value.
    The largest Unicode value allowed is 0xFFFFFF.
    """

    def __init__(self, character, tag, location=None):
        Statement.__init__(self, location)
        self.character = character
        self.tag = tag

    def build(self, builder):
        """Calls the builder object's ``add_cv_character`` callback."""
        builder.add_cv_character(self.character, self.tag)

    def asFea(self, indent=""):
        return "Character {:#x};".format(self.character)


class BaseAxis(Statement):
    """An axis definition, being either a ``VertAxis.BaseTagList/BaseScriptList``
    pair or a ``HorizAxis.BaseTagList/BaseScriptList`` pair."""

    def __init__(self, bases, scripts, vertical, minmax=None, location=None):
        Statement.__init__(self, location)
        self.bases = bases  #: A list of baseline tag names as strings
        self.scripts = scripts  #: A list of script record tuplets (script tag, default baseline tag, base coordinate)
        self.vertical = vertical  #: Boolean; VertAxis if True, HorizAxis if False
        self.minmax = []  #: A set of minmax record

    def build(self, builder):
        """Calls the builder object's ``set_base_axis`` callback."""
        builder.set_base_axis(self.bases, self.scripts, self.vertical, self.minmax)

    def asFea(self, indent=""):
        direction = "Vert" if self.vertical else "Horiz"
        scripts = [
            "{} {} {}".format(a[0], a[1], " ".join(map(str, a[2])))
            for a in self.scripts
        ]
        minmaxes = [
            "\n{}Axis.MinMax {} {} {}, {};".format(direction, a[0], a[1], a[2], a[3])
            for a in self.minmax
        ]
        return "{}Axis.BaseTagList {};\n{}{}Axis.BaseScriptList {};".format(
            direction, " ".join(self.bases), indent, direction, ", ".join(scripts)
        ) + "\n".join(minmaxes)


class OS2Field(Statement):
    """An entry in the ``OS/2`` table. Most ``values`` should be numbers or
    strings, apart from when the key is ``UnicodeRange``, ``CodePageRange``
    or ``Panose``, in which case it should be an array of integers."""

    def __init__(self, key, value, location=None):
        Statement.__init__(self, location)
        self.key = key
        self.value = value

    def build(self, builder):
        """Calls the builder object's ``add_os2_field`` callback."""
        builder.add_os2_field(self.key, self.value)

    def asFea(self, indent=""):
        def intarr2str(x):
            return " ".join(map(str, x))

        numbers = (
            "FSType",
            "TypoAscender",
            "TypoDescender",
            "TypoLineGap",
            "winAscent",
            "winDescent",
            "XHeight",
            "CapHeight",
            "WeightClass",
            "WidthClass",
            "LowerOpSize",
            "UpperOpSize",
        )
        ranges = ("UnicodeRange", "CodePageRange")
        keywords = dict([(x.lower(), [x, str]) for x in numbers])
        keywords.update([(x.lower(), [x, intarr2str]) for x in ranges])
        keywords["panose"] = ["Panose", intarr2str]
        keywords["vendor"] = ["Vendor", lambda y: '"{}"'.format(y)]
        if self.key in keywords:
            return "{} {};".format(
                keywords[self.key][0], keywords[self.key][1](self.value)
            )
        return ""  # should raise exception


class HheaField(Statement):
    """An entry in the ``hhea`` table."""

    def __init__(self, key, value, location=None):
        Statement.__init__(self, location)
        self.key = key
        self.value = value

    def build(self, builder):
        """Calls the builder object's ``add_hhea_field`` callback."""
        builder.add_hhea_field(self.key, self.value)

    def asFea(self, indent=""):
        fields = ("CaretOffset", "Ascender", "Descender", "LineGap")
        keywords = dict([(x.lower(), x) for x in fields])
        return "{} {};".format(keywords[self.key], self.value)


class VheaField(Statement):
    """An entry in the ``vhea`` table."""

    def __init__(self, key, value, location=None):
        Statement.__init__(self, location)
        self.key = key
        self.value = value

    def build(self, builder):
        """Calls the builder object's ``add_vhea_field`` callback."""
        builder.add_vhea_field(self.key, self.value)

    def asFea(self, indent=""):
        fields = ("VertTypoAscender", "VertTypoDescender", "VertTypoLineGap")
        keywords = dict([(x.lower(), x) for x in fields])
        return "{} {};".format(keywords[self.key], self.value)


class STATDesignAxisStatement(Statement):
    """A STAT table Design Axis

    Args:
        tag (str): a 4 letter axis tag
        axisOrder (int): an int
        names (list): a list of :class:`STATNameStatement` objects
    """

    def __init__(self, tag, axisOrder, names, location=None):
        Statement.__init__(self, location)
        self.tag = tag
        self.axisOrder = axisOrder
        self.names = names
        self.location = location

    def build(self, builder):
        builder.addDesignAxis(self, self.location)

    def asFea(self, indent=""):
        indent += SHIFT
        res = f"DesignAxis {self.tag} {self.axisOrder} {{ \n"
        res += ("\n" + indent).join([s.asFea(indent=indent) for s in self.names]) + "\n"
        res += "};"
        return res


class ElidedFallbackName(Statement):
    """STAT table ElidedFallbackName

    Args:
        names: a list of :class:`STATNameStatement` objects
    """

    def __init__(self, names, location=None):
        Statement.__init__(self, location)
        self.names = names
        self.location = location

    def build(self, builder):
        builder.setElidedFallbackName(self.names, self.location)

    def asFea(self, indent=""):
        indent += SHIFT
        res = "ElidedFallbackName { \n"
        res += ("\n" + indent).join([s.asFea(indent=indent) for s in self.names]) + "\n"
        res += "};"
        return res


class ElidedFallbackNameID(Statement):
    """STAT table ElidedFallbackNameID

    Args:
        value: an int pointing to an existing name table name ID
    """

    def __init__(self, value, location=None):
        Statement.__init__(self, location)
        self.value = value
        self.location = location

    def build(self, builder):
        builder.setElidedFallbackName(self.value, self.location)

    def asFea(self, indent=""):
        return f"ElidedFallbackNameID {self.value};"


class STATAxisValueStatement(Statement):
    """A STAT table Axis Value Record

    Args:
        names (list): a list of :class:`STATNameStatement` objects
        locations (list): a list of :class:`AxisValueLocationStatement` objects
        flags (int): an int
    """

    def __init__(self, names, locations, flags, location=None):
        Statement.__init__(self, location)
        self.names = names
        self.locations = locations
        self.flags = flags

    def build(self, builder):
        builder.addAxisValueRecord(self, self.location)

    def asFea(self, indent=""):
        res = "AxisValue {\n"
        for location in self.locations:
            res += location.asFea()

        for nameRecord in self.names:
            res += nameRecord.asFea()
            res += "\n"

        if self.flags:
            flags = ["OlderSiblingFontAttribute", "ElidableAxisValueName"]
            flagStrings = []
            curr = 1
            for i in range(len(flags)):
                if self.flags & curr != 0:
                    flagStrings.append(flags[i])
                curr = curr << 1
            res += f"flag {' '.join(flagStrings)};\n"
        res += "};"
        return res


class AxisValueLocationStatement(Statement):
    """
    A STAT table Axis Value Location

    Args:
        tag (str): a 4 letter axis tag
        values (list): a list of ints and/or floats
    """

    def __init__(self, tag, values, location=None):
        Statement.__init__(self, location)
        self.tag = tag
        self.values = values

    def asFea(self, res=""):
        res += f"location {self.tag} "
        res += f"{' '.join(str(i) for i in self.values)};\n"
        return res


class ConditionsetStatement(Statement):
    """
    A variable layout conditionset

    Args:
        name (str): the name of this conditionset
        conditions (dict): a dictionary mapping axis tags to a
            tuple of (min,max) userspace coordinates.
    """

    def __init__(self, name, conditions, location=None):
        Statement.__init__(self, location)
        self.name = name
        self.conditions = conditions

    def build(self, builder):
        builder.add_conditionset(self.location, self.name, self.conditions)

    def asFea(self, res="", indent=""):
        res += indent + f"conditionset {self.name} " + "{\n"
        for tag, (minvalue, maxvalue) in self.conditions.items():
            res += indent + SHIFT + f"{tag} {minvalue} {maxvalue};\n"
        res += indent + "}" + f" {self.name};\n"
        return res


class VariationBlock(Block):
    """A variation feature block, applicable in a given set of conditions."""

    def __init__(self, name, conditionset, use_extension=False, location=None):
        Block.__init__(self, location)
        self.name, self.conditionset, self.use_extension = (
            name,
            conditionset,
            use_extension,
        )

    def build(self, builder):
        """Call the ``start_feature`` callback on the builder object, visit
        all the statements in this feature, and then call ``end_feature``."""
        builder.start_feature(self.location, self.name, self.use_extension)
        if (
            self.conditionset != "NULL"
            and self.conditionset not in builder.conditionsets_
        ):
            raise FeatureLibError(
                f"variation block used undefined conditionset {self.conditionset}",
                self.location,
            )

        # language exclude_dflt statements modify builder.features_
        # limit them to this block with temporary builder.features_
        features = builder.features_
        builder.features_ = {}
        Block.build(self, builder)
        for key, value in builder.features_.items():
            items = builder.feature_variations_.setdefault(key, {}).setdefault(
                self.conditionset, []
            )
            items.extend(value)
            if key not in features:
                features[key] = []  # Ensure we make a feature record
        builder.features_ = features
        builder.end_feature()

    def asFea(self, indent=""):
        res = indent + "variation %s " % self.name.strip()
        res += self.conditionset + " "
        if self.use_extension:
            res += "useExtension "
        res += "{\n"
        res += Block.asFea(self, indent=indent)
        res += indent + "} %s;\n" % self.name.strip()
        return res

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v136\storage.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Storage (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import browser
from . import network
from . import page


class SerializedStorageKey(str):
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> SerializedStorageKey:
        return cls(json)

    def __repr__(self):
        return 'SerializedStorageKey({})'.format(super().__repr__())


class StorageType(enum.Enum):
    '''
    Enum of possible storage types.
    '''
    COOKIES = "cookies"
    FILE_SYSTEMS = "file_systems"
    INDEXEDDB = "indexeddb"
    LOCAL_STORAGE = "local_storage"
    SHADER_CACHE = "shader_cache"
    WEBSQL = "websql"
    SERVICE_WORKERS = "service_workers"
    CACHE_STORAGE = "cache_storage"
    INTEREST_GROUPS = "interest_groups"
    SHARED_STORAGE = "shared_storage"
    STORAGE_BUCKETS = "storage_buckets"
    ALL_ = "all"
    OTHER = "other"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class UsageForType:
    '''
    Usage for a storage type.
    '''
    #: Name of storage type.
    storage_type: StorageType

    #: Storage usage (bytes).
    usage: float

    def to_json(self):
        json = dict()
        json['storageType'] = self.storage_type.to_json()
        json['usage'] = self.usage
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            storage_type=StorageType.from_json(json['storageType']),
            usage=float(json['usage']),
        )


@dataclass
class TrustTokens:
    '''
    Pair of issuer origin and number of available (signed, but not used) Trust
    Tokens from that issuer.
    '''
    issuer_origin: str

    count: float

    def to_json(self):
        json = dict()
        json['issuerOrigin'] = self.issuer_origin
        json['count'] = self.count
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            issuer_origin=str(json['issuerOrigin']),
            count=float(json['count']),
        )


class InterestGroupAuctionId(str):
    '''
    Protected audience interest group auction identifier.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> InterestGroupAuctionId:
        return cls(json)

    def __repr__(self):
        return 'InterestGroupAuctionId({})'.format(super().__repr__())


class InterestGroupAccessType(enum.Enum):
    '''
    Enum of interest group access types.
    '''
    JOIN = "join"
    LEAVE = "leave"
    UPDATE = "update"
    LOADED = "loaded"
    BID = "bid"
    WIN = "win"
    ADDITIONAL_BID = "additionalBid"
    ADDITIONAL_BID_WIN = "additionalBidWin"
    TOP_LEVEL_BID = "topLevelBid"
    TOP_LEVEL_ADDITIONAL_BID = "topLevelAdditionalBid"
    CLEAR = "clear"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class InterestGroupAuctionEventType(enum.Enum):
    '''
    Enum of auction events.
    '''
    STARTED = "started"
    CONFIG_RESOLVED = "configResolved"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class InterestGroupAuctionFetchType(enum.Enum):
    '''
    Enum of network fetches auctions can do.
    '''
    BIDDER_JS = "bidderJs"
    BIDDER_WASM = "bidderWasm"
    SELLER_JS = "sellerJs"
    BIDDER_TRUSTED_SIGNALS = "bidderTrustedSignals"
    SELLER_TRUSTED_SIGNALS = "sellerTrustedSignals"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class SharedStorageAccessScope(enum.Enum):
    '''
    Enum of shared storage access scopes.
    '''
    WINDOW = "window"
    SHARED_STORAGE_WORKLET = "sharedStorageWorklet"
    PROTECTED_AUDIENCE_WORKLET = "protectedAudienceWorklet"
    HEADER = "header"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class SharedStorageAccessMethod(enum.Enum):
    '''
    Enum of shared storage access methods.
    '''
    ADD_MODULE = "addModule"
    CREATE_WORKLET = "createWorklet"
    SELECT_URL = "selectURL"
    RUN = "run"
    BATCH_UPDATE = "batchUpdate"
    SET_ = "set"
    APPEND = "append"
    DELETE = "delete"
    CLEAR = "clear"
    GET = "get"
    KEYS = "keys"
    VALUES = "values"
    ENTRIES = "entries"
    LENGTH = "length"
    REMAINING_BUDGET = "remainingBudget"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class SharedStorageEntry:
    '''
    Struct for a single key-value pair in an origin's shared storage.
    '''
    key: str

    value: str

    def to_json(self):
        json = dict()
        json['key'] = self.key
        json['value'] = self.value
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            key=str(json['key']),
            value=str(json['value']),
        )


@dataclass
class SharedStorageMetadata:
    '''
    Details for an origin's shared storage.
    '''
    #: Time when the origin's shared storage was last created.
    creation_time: network.TimeSinceEpoch

    #: Number of key-value pairs stored in origin's shared storage.
    length: int

    #: Current amount of bits of entropy remaining in the navigation budget.
    remaining_budget: float

    #: Total number of bytes stored as key-value pairs in origin's shared
    #: storage.
    bytes_used: int

    def to_json(self):
        json = dict()
        json['creationTime'] = self.creation_time.to_json()
        json['length'] = self.length
        json['remainingBudget'] = self.remaining_budget
        json['bytesUsed'] = self.bytes_used
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            creation_time=network.TimeSinceEpoch.from_json(json['creationTime']),
            length=int(json['length']),
            remaining_budget=float(json['remainingBudget']),
            bytes_used=int(json['bytesUsed']),
        )


@dataclass
class SharedStorageReportingMetadata:
    '''
    Pair of reporting metadata details for a candidate URL for ``selectURL()``.
    '''
    event_type: str

    reporting_url: str

    def to_json(self):
        json = dict()
        json['eventType'] = self.event_type
        json['reportingUrl'] = self.reporting_url
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            event_type=str(json['eventType']),
            reporting_url=str(json['reportingUrl']),
        )


@dataclass
class SharedStorageUrlWithMetadata:
    '''
    Bundles a candidate URL with its reporting metadata.
    '''
    #: Spec of candidate URL.
    url: str

    #: Any associated reporting metadata.
    reporting_metadata: typing.List[SharedStorageReportingMetadata]

    def to_json(self):
        json = dict()
        json['url'] = self.url
        json['reportingMetadata'] = [i.to_json() for i in self.reporting_metadata]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            url=str(json['url']),
            reporting_metadata=[SharedStorageReportingMetadata.from_json(i) for i in json['reportingMetadata']],
        )


@dataclass
class SharedStorageAccessParams:
    '''
    Bundles the parameters for shared storage access events whose
    presence/absence can vary according to SharedStorageAccessType.
    '''
    #: Spec of the module script URL.
    #: Present only for SharedStorageAccessType.documentAddModule.
    script_source_url: typing.Optional[str] = None

    #: Name of the registered operation to be run.
    #: Present only for SharedStorageAccessType.documentRun and
    #: SharedStorageAccessType.documentSelectURL.
    operation_name: typing.Optional[str] = None

    #: The operation's serialized data in bytes (converted to a string).
    #: Present only for SharedStorageAccessType.documentRun and
    #: SharedStorageAccessType.documentSelectURL.
    serialized_data: typing.Optional[str] = None

    #: Array of candidate URLs' specs, along with any associated metadata.
    #: Present only for SharedStorageAccessType.documentSelectURL.
    urls_with_metadata: typing.Optional[typing.List[SharedStorageUrlWithMetadata]] = None

    #: Key for a specific entry in an origin's shared storage.
    #: Present only for SharedStorageAccessType.documentSet,
    #: SharedStorageAccessType.documentAppend,
    #: SharedStorageAccessType.documentDelete,
    #: SharedStorageAccessType.workletSet,
    #: SharedStorageAccessType.workletAppend,
    #: SharedStorageAccessType.workletDelete,
    #: SharedStorageAccessType.workletGet,
    #: SharedStorageAccessType.headerSet,
    #: SharedStorageAccessType.headerAppend, and
    #: SharedStorageAccessType.headerDelete.
    key: typing.Optional[str] = None

    #: Value for a specific entry in an origin's shared storage.
    #: Present only for SharedStorageAccessType.documentSet,
    #: SharedStorageAccessType.documentAppend,
    #: SharedStorageAccessType.workletSet,
    #: SharedStorageAccessType.workletAppend,
    #: SharedStorageAccessType.headerSet, and
    #: SharedStorageAccessType.headerAppend.
    value: typing.Optional[str] = None

    #: Whether or not to set an entry for a key if that key is already present.
    #: Present only for SharedStorageAccessType.documentSet,
    #: SharedStorageAccessType.workletSet, and
    #: SharedStorageAccessType.headerSet.
    ignore_if_present: typing.Optional[bool] = None

    def to_json(self):
        json = dict()
        if self.script_source_url is not None:
            json['scriptSourceUrl'] = self.script_source_url
        if self.operation_name is not None:
            json['operationName'] = self.operation_name
        if self.serialized_data is not None:
            json['serializedData'] = self.serialized_data
        if self.urls_with_metadata is not None:
            json['urlsWithMetadata'] = [i.to_json() for i in self.urls_with_metadata]
        if self.key is not None:
            json['key'] = self.key
        if self.value is not None:
            json['value'] = self.value
        if self.ignore_if_present is not None:
            json['ignoreIfPresent'] = self.ignore_if_present
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            script_source_url=str(json['scriptSourceUrl']) if 'scriptSourceUrl' in json else None,
            operation_name=str(json['operationName']) if 'operationName' in json else None,
            serialized_data=str(json['serializedData']) if 'serializedData' in json else None,
            urls_with_metadata=[SharedStorageUrlWithMetadata.from_json(i) for i in json['urlsWithMetadata']] if 'urlsWithMetadata' in json else None,
            key=str(json['key']) if 'key' in json else None,
            value=str(json['value']) if 'value' in json else None,
            ignore_if_present=bool(json['ignoreIfPresent']) if 'ignoreIfPresent' in json else None,
        )


class StorageBucketsDurability(enum.Enum):
    RELAXED = "relaxed"
    STRICT = "strict"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class StorageBucket:
    storage_key: SerializedStorageKey

    #: If not specified, it is the default bucket of the storageKey.
    name: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['storageKey'] = self.storage_key.to_json()
        if self.name is not None:
            json['name'] = self.name
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            storage_key=SerializedStorageKey.from_json(json['storageKey']),
            name=str(json['name']) if 'name' in json else None,
        )


@dataclass
class StorageBucketInfo:
    bucket: StorageBucket

    id_: str

    expiration: network.TimeSinceEpoch

    #: Storage quota (bytes).
    quota: float

    persistent: bool

    durability: StorageBucketsDurability

    def to_json(self):
        json = dict()
        json['bucket'] = self.bucket.to_json()
        json['id'] = self.id_
        json['expiration'] = self.expiration.to_json()
        json['quota'] = self.quota
        json['persistent'] = self.persistent
        json['durability'] = self.durability.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            bucket=StorageBucket.from_json(json['bucket']),
            id_=str(json['id']),
            expiration=network.TimeSinceEpoch.from_json(json['expiration']),
            quota=float(json['quota']),
            persistent=bool(json['persistent']),
            durability=StorageBucketsDurability.from_json(json['durability']),
        )


class AttributionReportingSourceType(enum.Enum):
    NAVIGATION = "navigation"
    EVENT = "event"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class UnsignedInt64AsBase10(str):
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> UnsignedInt64AsBase10:
        return cls(json)

    def __repr__(self):
        return 'UnsignedInt64AsBase10({})'.format(super().__repr__())


class UnsignedInt128AsBase16(str):
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> UnsignedInt128AsBase16:
        return cls(json)

    def __repr__(self):
        return 'UnsignedInt128AsBase16({})'.format(super().__repr__())


class SignedInt64AsBase10(str):
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> SignedInt64AsBase10:
        return cls(json)

    def __repr__(self):
        return 'SignedInt64AsBase10({})'.format(super().__repr__())


@dataclass
class AttributionReportingFilterDataEntry:
    key: str

    values: typing.List[str]

    def to_json(self):
        json = dict()
        json['key'] = self.key
        json['values'] = [i for i in self.values]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            key=str(json['key']),
            values=[str(i) for i in json['values']],
        )


@dataclass
class AttributionReportingFilterConfig:
    filter_values: typing.List[AttributionReportingFilterDataEntry]

    #: duration in seconds
    lookback_window: typing.Optional[int] = None

    def to_json(self):
        json = dict()
        json['filterValues'] = [i.to_json() for i in self.filter_values]
        if self.lookback_window is not None:
            json['lookbackWindow'] = self.lookback_window
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            filter_values=[AttributionReportingFilterDataEntry.from_json(i) for i in json['filterValues']],
            lookback_window=int(json['lookbackWindow']) if 'lookbackWindow' in json else None,
        )


@dataclass
class AttributionReportingFilterPair:
    filters: typing.List[AttributionReportingFilterConfig]

    not_filters: typing.List[AttributionReportingFilterConfig]

    def to_json(self):
        json = dict()
        json['filters'] = [i.to_json() for i in self.filters]
        json['notFilters'] = [i.to_json() for i in self.not_filters]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            filters=[AttributionReportingFilterConfig.from_json(i) for i in json['filters']],
            not_filters=[AttributionReportingFilterConfig.from_json(i) for i in json['notFilters']],
        )


@dataclass
class AttributionReportingAggregationKeysEntry:
    key: str

    value: UnsignedInt128AsBase16

    def to_json(self):
        json = dict()
        json['key'] = self.key
        json['value'] = self.value.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            key=str(json['key']),
            value=UnsignedInt128AsBase16.from_json(json['value']),
        )


@dataclass
class AttributionReportingEventReportWindows:
    #: duration in seconds
    start: int

    #: duration in seconds
    ends: typing.List[int]

    def to_json(self):
        json = dict()
        json['start'] = self.start
        json['ends'] = [i for i in self.ends]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            start=int(json['start']),
            ends=[int(i) for i in json['ends']],
        )


@dataclass
class AttributionReportingTriggerSpec:
    #: number instead of integer because not all uint32 can be represented by
    #: int
    trigger_data: typing.List[float]

    event_report_windows: AttributionReportingEventReportWindows

    def to_json(self):
        json = dict()
        json['triggerData'] = [i for i in self.trigger_data]
        json['eventReportWindows'] = self.event_report_windows.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            trigger_data=[float(i) for i in json['triggerData']],
            event_report_windows=AttributionReportingEventReportWindows.from_json(json['eventReportWindows']),
        )


class AttributionReportingTriggerDataMatching(enum.Enum):
    EXACT = "exact"
    MODULUS = "modulus"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class AttributionReportingAggregatableDebugReportingData:
    key_piece: UnsignedInt128AsBase16

    #: number instead of integer because not all uint32 can be represented by
    #: int
    value: float

    types: typing.List[str]

    def to_json(self):
        json = dict()
        json['keyPiece'] = self.key_piece.to_json()
        json['value'] = self.value
        json['types'] = [i for i in self.types]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            key_piece=UnsignedInt128AsBase16.from_json(json['keyPiece']),
            value=float(json['value']),
            types=[str(i) for i in json['types']],
        )


@dataclass
class AttributionReportingAggregatableDebugReportingConfig:
    key_piece: UnsignedInt128AsBase16

    debug_data: typing.List[AttributionReportingAggregatableDebugReportingData]

    #: number instead of integer because not all uint32 can be represented by
    #: int, only present for source registrations
    budget: typing.Optional[float] = None

    aggregation_coordinator_origin: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['keyPiece'] = self.key_piece.to_json()
        json['debugData'] = [i.to_json() for i in self.debug_data]
        if self.budget is not None:
            json['budget'] = self.budget
        if self.aggregation_coordinator_origin is not None:
            json['aggregationCoordinatorOrigin'] = self.aggregation_coordinator_origin
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            key_piece=UnsignedInt128AsBase16.from_json(json['keyPiece']),
            debug_data=[AttributionReportingAggregatableDebugReportingData.from_json(i) for i in json['debugData']],
            budget=float(json['budget']) if 'budget' in json else None,
            aggregation_coordinator_origin=str(json['aggregationCoordinatorOrigin']) if 'aggregationCoordinatorOrigin' in json else None,
        )


@dataclass
class AttributionScopesData:
    values: typing.List[str]

    #: number instead of integer because not all uint32 can be represented by
    #: int
    limit: float

    max_event_states: float

    def to_json(self):
        json = dict()
        json['values'] = [i for i in self.values]
        json['limit'] = self.limit
        json['maxEventStates'] = self.max_event_states
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            values=[str(i) for i in json['values']],
            limit=float(json['limit']),
            max_event_states=float(json['maxEventStates']),
        )


@dataclass
class AttributionReportingSourceRegistration:
    time: network.TimeSinceEpoch

    #: duration in seconds
    expiry: int

    trigger_specs: typing.List[AttributionReportingTriggerSpec]

    #: duration in seconds
    aggregatable_report_window: int

    type_: AttributionReportingSourceType

    source_origin: str

    reporting_origin: str

    destination_sites: typing.List[str]

    event_id: UnsignedInt64AsBase10

    priority: SignedInt64AsBase10

    filter_data: typing.List[AttributionReportingFilterDataEntry]

    aggregation_keys: typing.List[AttributionReportingAggregationKeysEntry]

    trigger_data_matching: AttributionReportingTriggerDataMatching

    destination_limit_priority: SignedInt64AsBase10

    aggregatable_debug_reporting_config: AttributionReportingAggregatableDebugReportingConfig

    max_event_level_reports: int

    debug_key: typing.Optional[UnsignedInt64AsBase10] = None

    scopes_data: typing.Optional[AttributionScopesData] = None

    def to_json(self):
        json = dict()
        json['time'] = self.time.to_json()
        json['expiry'] = self.expiry
        json['triggerSpecs'] = [i.to_json() for i in self.trigger_specs]
        json['aggregatableReportWindow'] = self.aggregatable_report_window
        json['type'] = self.type_.to_json()
        json['sourceOrigin'] = self.source_origin
        json['reportingOrigin'] = self.reporting_origin
        json['destinationSites'] = [i for i in self.destination_sites]
        json['eventId'] = self.event_id.to_json()
        json['priority'] = self.priority.to_json()
        json['filterData'] = [i.to_json() for i in self.filter_data]
        json['aggregationKeys'] = [i.to_json() for i in self.aggregation_keys]
        json['triggerDataMatching'] = self.trigger_data_matching.to_json()
        json['destinationLimitPriority'] = self.destination_limit_priority.to_json()
        json['aggregatableDebugReportingConfig'] = self.aggregatable_debug_reporting_config.to_json()
        json['maxEventLevelReports'] = self.max_event_level_reports
        if self.debug_key is not None:
            json['debugKey'] = self.debug_key.to_json()
        if self.scopes_data is not None:
            json['scopesData'] = self.scopes_data.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            time=network.TimeSinceEpoch.from_json(json['time']),
            expiry=int(json['expiry']),
            trigger_specs=[AttributionReportingTriggerSpec.from_json(i) for i in json['triggerSpecs']],
            aggregatable_report_window=int(json['aggregatableReportWindow']),
            type_=AttributionReportingSourceType.from_json(json['type']),
            source_origin=str(json['sourceOrigin']),
            reporting_origin=str(json['reportingOrigin']),
            destination_sites=[str(i) for i in json['destinationSites']],
            event_id=UnsignedInt64AsBase10.from_json(json['eventId']),
            priority=SignedInt64AsBase10.from_json(json['priority']),
            filter_data=[AttributionReportingFilterDataEntry.from_json(i) for i in json['filterData']],
            aggregation_keys=[AttributionReportingAggregationKeysEntry.from_json(i) for i in json['aggregationKeys']],
            trigger_data_matching=AttributionReportingTriggerDataMatching.from_json(json['triggerDataMatching']),
            destination_limit_priority=SignedInt64AsBase10.from_json(json['destinationLimitPriority']),
            aggregatable_debug_reporting_config=AttributionReportingAggregatableDebugReportingConfig.from_json(json['aggregatableDebugReportingConfig']),
            max_event_level_reports=int(json['maxEventLevelReports']),
            debug_key=UnsignedInt64AsBase10.from_json(json['debugKey']) if 'debugKey' in json else None,
            scopes_data=AttributionScopesData.from_json(json['scopesData']) if 'scopesData' in json else None,
        )


class AttributionReportingSourceRegistrationResult(enum.Enum):
    SUCCESS = "success"
    INTERNAL_ERROR = "internalError"
    INSUFFICIENT_SOURCE_CAPACITY = "insufficientSourceCapacity"
    INSUFFICIENT_UNIQUE_DESTINATION_CAPACITY = "insufficientUniqueDestinationCapacity"
    EXCESSIVE_REPORTING_ORIGINS = "excessiveReportingOrigins"
    PROHIBITED_BY_BROWSER_POLICY = "prohibitedByBrowserPolicy"
    SUCCESS_NOISED = "successNoised"
    DESTINATION_REPORTING_LIMIT_REACHED = "destinationReportingLimitReached"
    DESTINATION_GLOBAL_LIMIT_REACHED = "destinationGlobalLimitReached"
    DESTINATION_BOTH_LIMITS_REACHED = "destinationBothLimitsReached"
    REPORTING_ORIGINS_PER_SITE_LIMIT_REACHED = "reportingOriginsPerSiteLimitReached"
    EXCEEDS_MAX_CHANNEL_CAPACITY = "exceedsMaxChannelCapacity"
    EXCEEDS_MAX_SCOPES_CHANNEL_CAPACITY = "exceedsMaxScopesChannelCapacity"
    EXCEEDS_MAX_TRIGGER_STATE_CARDINALITY = "exceedsMaxTriggerStateCardinality"
    EXCEEDS_MAX_EVENT_STATES_LIMIT = "exceedsMaxEventStatesLimit"
    DESTINATION_PER_DAY_REPORTING_LIMIT_REACHED = "destinationPerDayReportingLimitReached"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class AttributionReportingSourceRegistrationTimeConfig(enum.Enum):
    INCLUDE = "include"
    EXCLUDE = "exclude"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class AttributionReportingAggregatableValueDictEntry:
    key: str

    #: number instead of integer because not all uint32 can be represented by
    #: int
    value: float

    filtering_id: UnsignedInt64AsBase10

    def to_json(self):
        json = dict()
        json['key'] = self.key
        json['value'] = self.value
        json['filteringId'] = self.filtering_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            key=str(json['key']),
            value=float(json['value']),
            filtering_id=UnsignedInt64AsBase10.from_json(json['filteringId']),
        )


@dataclass
class AttributionReportingAggregatableValueEntry:
    values: typing.List[AttributionReportingAggregatableValueDictEntry]

    filters: AttributionReportingFilterPair

    def to_json(self):
        json = dict()
        json['values'] = [i.to_json() for i in self.values]
        json['filters'] = self.filters.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            values=[AttributionReportingAggregatableValueDictEntry.from_json(i) for i in json['values']],
            filters=AttributionReportingFilterPair.from_json(json['filters']),
        )


@dataclass
class AttributionReportingEventTriggerData:
    data: UnsignedInt64AsBase10

    priority: SignedInt64AsBase10

    filters: AttributionReportingFilterPair

    dedup_key: typing.Optional[UnsignedInt64AsBase10] = None

    def to_json(self):
        json = dict()
        json['data'] = self.data.to_json()
        json['priority'] = self.priority.to_json()
        json['filters'] = self.filters.to_json()
        if self.dedup_key is not None:
            json['dedupKey'] = self.dedup_key.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            data=UnsignedInt64AsBase10.from_json(json['data']),
            priority=SignedInt64AsBase10.from_json(json['priority']),
            filters=AttributionReportingFilterPair.from_json(json['filters']),
            dedup_key=UnsignedInt64AsBase10.from_json(json['dedupKey']) if 'dedupKey' in json else None,
        )


@dataclass
class AttributionReportingAggregatableTriggerData:
    key_piece: UnsignedInt128AsBase16

    source_keys: typing.List[str]

    filters: AttributionReportingFilterPair

    def to_json(self):
        json = dict()
        json['keyPiece'] = self.key_piece.to_json()
        json['sourceKeys'] = [i for i in self.source_keys]
        json['filters'] = self.filters.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            key_piece=UnsignedInt128AsBase16.from_json(json['keyPiece']),
            source_keys=[str(i) for i in json['sourceKeys']],
            filters=AttributionReportingFilterPair.from_json(json['filters']),
        )


@dataclass
class AttributionReportingAggregatableDedupKey:
    filters: AttributionReportingFilterPair

    dedup_key: typing.Optional[UnsignedInt64AsBase10] = None

    def to_json(self):
        json = dict()
        json['filters'] = self.filters.to_json()
        if self.dedup_key is not None:
            json['dedupKey'] = self.dedup_key.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            filters=AttributionReportingFilterPair.from_json(json['filters']),
            dedup_key=UnsignedInt64AsBase10.from_json(json['dedupKey']) if 'dedupKey' in json else None,
        )


@dataclass
class AttributionReportingTriggerRegistration:
    filters: AttributionReportingFilterPair

    aggregatable_dedup_keys: typing.List[AttributionReportingAggregatableDedupKey]

    event_trigger_data: typing.List[AttributionReportingEventTriggerData]

    aggregatable_trigger_data: typing.List[AttributionReportingAggregatableTriggerData]

    aggregatable_values: typing.List[AttributionReportingAggregatableValueEntry]

    aggregatable_filtering_id_max_bytes: int

    debug_reporting: bool

    source_registration_time_config: AttributionReportingSourceRegistrationTimeConfig

    aggregatable_debug_reporting_config: AttributionReportingAggregatableDebugReportingConfig

    scopes: typing.List[str]

    debug_key: typing.Optional[UnsignedInt64AsBase10] = None

    aggregation_coordinator_origin: typing.Optional[str] = None

    trigger_context_id: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['filters'] = self.filters.to_json()
        json['aggregatableDedupKeys'] = [i.to_json() for i in self.aggregatable_dedup_keys]
        json['eventTriggerData'] = [i.to_json() for i in self.event_trigger_data]
        json['aggregatableTriggerData'] = [i.to_json() for i in self.aggregatable_trigger_data]
        json['aggregatableValues'] = [i.to_json() for i in self.aggregatable_values]
        json['aggregatableFilteringIdMaxBytes'] = self.aggregatable_filtering_id_max_bytes
        json['debugReporting'] = self.debug_reporting
        json['sourceRegistrationTimeConfig'] = self.source_registration_time_config.to_json()
        json['aggregatableDebugReportingConfig'] = self.aggregatable_debug_reporting_config.to_json()
        json['scopes'] = [i for i in self.scopes]
        if self.debug_key is not None:
            json['debugKey'] = self.debug_key.to_json()
        if self.aggregation_coordinator_origin is not None:
            json['aggregationCoordinatorOrigin'] = self.aggregation_coordinator_origin
        if self.trigger_context_id is not None:
            json['triggerContextId'] = self.trigger_context_id
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            filters=AttributionReportingFilterPair.from_json(json['filters']),
            aggregatable_dedup_keys=[AttributionReportingAggregatableDedupKey.from_json(i) for i in json['aggregatableDedupKeys']],
            event_trigger_data=[AttributionReportingEventTriggerData.from_json(i) for i in json['eventTriggerData']],
            aggregatable_trigger_data=[AttributionReportingAggregatableTriggerData.from_json(i) for i in json['aggregatableTriggerData']],
            aggregatable_values=[AttributionReportingAggregatableValueEntry.from_json(i) for i in json['aggregatableValues']],
            aggregatable_filtering_id_max_bytes=int(json['aggregatableFilteringIdMaxBytes']),
            debug_reporting=bool(json['debugReporting']),
            source_registration_time_config=AttributionReportingSourceRegistrationTimeConfig.from_json(json['sourceRegistrationTimeConfig']),
            aggregatable_debug_reporting_config=AttributionReportingAggregatableDebugReportingConfig.from_json(json['aggregatableDebugReportingConfig']),
            scopes=[str(i) for i in json['scopes']],
            debug_key=UnsignedInt64AsBase10.from_json(json['debugKey']) if 'debugKey' in json else None,
            aggregation_coordinator_origin=str(json['aggregationCoordinatorOrigin']) if 'aggregationCoordinatorOrigin' in json else None,
            trigger_context_id=str(json['triggerContextId']) if 'triggerContextId' in json else None,
        )


class AttributionReportingEventLevelResult(enum.Enum):
    SUCCESS = "success"
    SUCCESS_DROPPED_LOWER_PRIORITY = "successDroppedLowerPriority"
    INTERNAL_ERROR = "internalError"
    NO_CAPACITY_FOR_ATTRIBUTION_DESTINATION = "noCapacityForAttributionDestination"
    NO_MATCHING_SOURCES = "noMatchingSources"
    DEDUPLICATED = "deduplicated"
    EXCESSIVE_ATTRIBUTIONS = "excessiveAttributions"
    PRIORITY_TOO_LOW = "priorityTooLow"
    NEVER_ATTRIBUTED_SOURCE = "neverAttributedSource"
    EXCESSIVE_REPORTING_ORIGINS = "excessiveReportingOrigins"
    NO_MATCHING_SOURCE_FILTER_DATA = "noMatchingSourceFilterData"
    PROHIBITED_BY_BROWSER_POLICY = "prohibitedByBrowserPolicy"
    NO_MATCHING_CONFIGURATIONS = "noMatchingConfigurations"
    EXCESSIVE_REPORTS = "excessiveReports"
    FALSELY_ATTRIBUTED_SOURCE = "falselyAttributedSource"
    REPORT_WINDOW_PASSED = "reportWindowPassed"
    NOT_REGISTERED = "notRegistered"
    REPORT_WINDOW_NOT_STARTED = "reportWindowNotStarted"
    NO_MATCHING_TRIGGER_DATA = "noMatchingTriggerData"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class AttributionReportingAggregatableResult(enum.Enum):
    SUCCESS = "success"
    INTERNAL_ERROR = "internalError"
    NO_CAPACITY_FOR_ATTRIBUTION_DESTINATION = "noCapacityForAttributionDestination"
    NO_MATCHING_SOURCES = "noMatchingSources"
    EXCESSIVE_ATTRIBUTIONS = "excessiveAttributions"
    EXCESSIVE_REPORTING_ORIGINS = "excessiveReportingOrigins"
    NO_HISTOGRAMS = "noHistograms"
    INSUFFICIENT_BUDGET = "insufficientBudget"
    INSUFFICIENT_NAMED_BUDGET = "insufficientNamedBudget"
    NO_MATCHING_SOURCE_FILTER_DATA = "noMatchingSourceFilterData"
    NOT_REGISTERED = "notRegistered"
    PROHIBITED_BY_BROWSER_POLICY = "prohibitedByBrowserPolicy"
    DEDUPLICATED = "deduplicated"
    REPORT_WINDOW_PASSED = "reportWindowPassed"
    EXCESSIVE_REPORTS = "excessiveReports"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class RelatedWebsiteSet:
    '''
    A single Related Website Set object.
    '''
    #: The primary site of this set, along with the ccTLDs if there is any.
    primary_sites: typing.List[str]

    #: The associated sites of this set, along with the ccTLDs if there is any.
    associated_sites: typing.List[str]

    #: The service sites of this set, along with the ccTLDs if there is any.
    service_sites: typing.List[str]

    def to_json(self):
        json = dict()
        json['primarySites'] = [i for i in self.primary_sites]
        json['associatedSites'] = [i for i in self.associated_sites]
        json['serviceSites'] = [i for i in self.service_sites]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            primary_sites=[str(i) for i in json['primarySites']],
            associated_sites=[str(i) for i in json['associatedSites']],
            service_sites=[str(i) for i in json['serviceSites']],
        )


def get_storage_key_for_frame(
        frame_id: page.FrameId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,SerializedStorageKey]:
    '''
    Returns a storage key given a frame id.

    :param frame_id:
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['frameId'] = frame_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.getStorageKeyForFrame',
        'params': params,
    }
    json = yield cmd_dict
    return SerializedStorageKey.from_json(json['storageKey'])


def clear_data_for_origin(
        origin: str,
        storage_types: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears storage for origin.

    :param origin: Security origin.
    :param storage_types: Comma separated list of StorageType to clear.
    '''
    params: T_JSON_DICT = dict()
    params['origin'] = origin
    params['storageTypes'] = storage_types
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.clearDataForOrigin',
        'params': params,
    }
    json = yield cmd_dict


def clear_data_for_storage_key(
        storage_key: str,
        storage_types: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears storage for storage key.

    :param storage_key: Storage key.
    :param storage_types: Comma separated list of StorageType to clear.
    '''
    params: T_JSON_DICT = dict()
    params['storageKey'] = storage_key
    params['storageTypes'] = storage_types
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.clearDataForStorageKey',
        'params': params,
    }
    json = yield cmd_dict


def get_cookies(
        browser_context_id: typing.Optional[browser.BrowserContextID] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[network.Cookie]]:
    '''
    Returns all browser cookies.

    :param browser_context_id: *(Optional)* Browser context to use when called on the browser endpoint.
    :returns: Array of cookie objects.
    '''
    params: T_JSON_DICT = dict()
    if browser_context_id is not None:
        params['browserContextId'] = browser_context_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.getCookies',
        'params': params,
    }
    json = yield cmd_dict
    return [network.Cookie.from_json(i) for i in json['cookies']]


def set_cookies(
        cookies: typing.List[network.CookieParam],
        browser_context_id: typing.Optional[browser.BrowserContextID] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets given cookies.

    :param cookies: Cookies to be set.
    :param browser_context_id: *(Optional)* Browser context to use when called on the browser endpoint.
    '''
    params: T_JSON_DICT = dict()
    params['cookies'] = [i.to_json() for i in cookies]
    if browser_context_id is not None:
        params['browserContextId'] = browser_context_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.setCookies',
        'params': params,
    }
    json = yield cmd_dict


def clear_cookies(
        browser_context_id: typing.Optional[browser.BrowserContextID] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears cookies.

    :param browser_context_id: *(Optional)* Browser context to use when called on the browser endpoint.
    '''
    params: T_JSON_DICT = dict()
    if browser_context_id is not None:
        params['browserContextId'] = browser_context_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.clearCookies',
        'params': params,
    }
    json = yield cmd_dict


def get_usage_and_quota(
        origin: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[float, float, bool, typing.List[UsageForType]]]:
    '''
    Returns usage and quota in bytes.

    :param origin: Security origin.
    :returns: A tuple with the following items:

        0. **usage** - Storage usage (bytes).
        1. **quota** - Storage quota (bytes).
        2. **overrideActive** - Whether or not the origin has an active storage quota override
        3. **usageBreakdown** - Storage usage per type (bytes).
    '''
    params: T_JSON_DICT = dict()
    params['origin'] = origin
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.getUsageAndQuota',
        'params': params,
    }
    json = yield cmd_dict
    return (
        float(json['usage']),
        float(json['quota']),
        bool(json['overrideActive']),
        [UsageForType.from_json(i) for i in json['usageBreakdown']]
    )


def override_quota_for_origin(
        origin: str,
        quota_size: typing.Optional[float] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Override quota for the specified origin

    **EXPERIMENTAL**

    :param origin: Security origin.
    :param quota_size: *(Optional)* The quota size (in bytes) to override the original quota with. If this is called multiple times, the overridden quota will be equal to the quotaSize provided in the final call. If this is called without specifying a quotaSize, the quota will be reset to the default value for the specified origin. If this is called multiple times with different origins, the override will be maintained for each origin until it is disabled (called without a quotaSize).
    '''
    params: T_JSON_DICT = dict()
    params['origin'] = origin
    if quota_size is not None:
        params['quotaSize'] = quota_size
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.overrideQuotaForOrigin',
        'params': params,
    }
    json = yield cmd_dict


def track_cache_storage_for_origin(
        origin: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Registers origin to be notified when an update occurs to its cache storage list.

    :param origin: Security origin.
    '''
    params: T_JSON_DICT = dict()
    params['origin'] = origin
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.trackCacheStorageForOrigin',
        'params': params,
    }
    json = yield cmd_dict


def track_cache_storage_for_storage_key(
        storage_key: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Registers storage key to be notified when an update occurs to its cache storage list.

    :param storage_key: Storage key.
    '''
    params: T_JSON_DICT = dict()
    params['storageKey'] = storage_key
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.trackCacheStorageForStorageKey',
        'params': params,
    }
    json = yield cmd_dict


def track_indexed_db_for_origin(
        origin: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Registers origin to be notified when an update occurs to its IndexedDB.

    :param origin: Security origin.
    '''
    params: T_JSON_DICT = dict()
    params['origin'] = origin
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.trackIndexedDBForOrigin',
        'params': params,
    }
    json = yield cmd_dict


def track_indexed_db_for_storage_key(
        storage_key: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Registers storage key to be notified when an update occurs to its IndexedDB.

    :param storage_key: Storage key.
    '''
    params: T_JSON_DICT = dict()
    params['storageKey'] = storage_key
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.trackIndexedDBForStorageKey',
        'params': params,
    }
    json = yield cmd_dict


def untrack_cache_storage_for_origin(
        origin: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Unregisters origin from receiving notifications for cache storage.

    :param origin: Security origin.
    '''
    params: T_JSON_DICT = dict()
    params['origin'] = origin
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.untrackCacheStorageForOrigin',
        'params': params,
    }
    json = yield cmd_dict


def untrack_cache_storage_for_storage_key(
        storage_key: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Unregisters storage key from receiving notifications for cache storage.

    :param storage_key: Storage key.
    '''
    params: T_JSON_DICT = dict()
    params['storageKey'] = storage_key
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.untrackCacheStorageForStorageKey',
        'params': params,
    }
    json = yield cmd_dict


def untrack_indexed_db_for_origin(
        origin: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Unregisters origin from receiving notifications for IndexedDB.

    :param origin: Security origin.
    '''
    params: T_JSON_DICT = dict()
    params['origin'] = origin
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.untrackIndexedDBForOrigin',
        'params': params,
    }
    json = yield cmd_dict


def untrack_indexed_db_for_storage_key(
        storage_key: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Unregisters storage key from receiving notifications for IndexedDB.

    :param storage_key: Storage key.
    '''
    params: T_JSON_DICT = dict()
    params['storageKey'] = storage_key
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.untrackIndexedDBForStorageKey',
        'params': params,
    }
    json = yield cmd_dict


def get_trust_tokens() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[TrustTokens]]:
    '''
    Returns the number of stored Trust Tokens per issuer for the
    current browsing context.

    **EXPERIMENTAL**

    :returns: 
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.getTrustTokens',
    }
    json = yield cmd_dict
    return [TrustTokens.from_json(i) for i in json['tokens']]


def clear_trust_tokens(
        issuer_origin: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,bool]:
    '''
    Removes all Trust Tokens issued by the provided issuerOrigin.
    Leaves other stored data, including the issuer's Redemption Records, intact.

    **EXPERIMENTAL**

    :param issuer_origin:
    :returns: True if any tokens were deleted, false otherwise.
    '''
    params: T_JSON_DICT = dict()
    params['issuerOrigin'] = issuer_origin
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.clearTrustTokens',
        'params': params,
    }
    json = yield cmd_dict
    return bool(json['didDeleteTokens'])


def get_interest_group_details(
        owner_origin: str,
        name: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,dict]:
    '''
    Gets details for a named interest group.

    **EXPERIMENTAL**

    :param owner_origin:
    :param name:
    :returns: This largely corresponds to: https://wicg.github.io/turtledove/#dictdef-generatebidinterestgroup but has absolute expirationTime instead of relative lifetimeMs and also adds joiningOrigin.
    '''
    params: T_JSON_DICT = dict()
    params['ownerOrigin'] = owner_origin
    params['name'] = name
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.getInterestGroupDetails',
        'params': params,
    }
    json = yield cmd_dict
    return dict(json['details'])


def set_interest_group_tracking(
        enable: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables/Disables issuing of interestGroupAccessed events.

    **EXPERIMENTAL**

    :param enable:
    '''
    params: T_JSON_DICT = dict()
    params['enable'] = enable
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.setInterestGroupTracking',
        'params': params,
    }
    json = yield cmd_dict


def set_interest_group_auction_tracking(
        enable: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables/Disables issuing of interestGroupAuctionEventOccurred and
    interestGroupAuctionNetworkRequestCreated.

    **EXPERIMENTAL**

    :param enable:
    '''
    params: T_JSON_DICT = dict()
    params['enable'] = enable
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.setInterestGroupAuctionTracking',
        'params': params,
    }
    json = yield cmd_dict


def get_shared_storage_metadata(
        owner_origin: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,SharedStorageMetadata]:
    '''
    Gets metadata for an origin's shared storage.

    **EXPERIMENTAL**

    :param owner_origin:
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['ownerOrigin'] = owner_origin
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.getSharedStorageMetadata',
        'params': params,
    }
    json = yield cmd_dict
    return SharedStorageMetadata.from_json(json['metadata'])


def get_shared_storage_entries(
        owner_origin: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[SharedStorageEntry]]:
    '''
    Gets the entries in an given origin's shared storage.

    **EXPERIMENTAL**

    :param owner_origin:
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['ownerOrigin'] = owner_origin
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.getSharedStorageEntries',
        'params': params,
    }
    json = yield cmd_dict
    return [SharedStorageEntry.from_json(i) for i in json['entries']]


def set_shared_storage_entry(
        owner_origin: str,
        key: str,
        value: str,
        ignore_if_present: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets entry with ``key`` and ``value`` for a given origin's shared storage.

    **EXPERIMENTAL**

    :param owner_origin:
    :param key:
    :param value:
    :param ignore_if_present: *(Optional)* If ```ignoreIfPresent```` is included and true, then only sets the entry if ````key``` doesn't already exist.
    '''
    params: T_JSON_DICT = dict()
    params['ownerOrigin'] = owner_origin
    params['key'] = key
    params['value'] = value
    if ignore_if_present is not None:
        params['ignoreIfPresent'] = ignore_if_present
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.setSharedStorageEntry',
        'params': params,
    }
    json = yield cmd_dict


def delete_shared_storage_entry(
        owner_origin: str,
        key: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Deletes entry for ``key`` (if it exists) for a given origin's shared storage.

    **EXPERIMENTAL**

    :param owner_origin:
    :param key:
    '''
    params: T_JSON_DICT = dict()
    params['ownerOrigin'] = owner_origin
    params['key'] = key
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.deleteSharedStorageEntry',
        'params': params,
    }
    json = yield cmd_dict


def clear_shared_storage_entries(
        owner_origin: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears all entries for a given origin's shared storage.

    **EXPERIMENTAL**

    :param owner_origin:
    '''
    params: T_JSON_DICT = dict()
    params['ownerOrigin'] = owner_origin
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.clearSharedStorageEntries',
        'params': params,
    }
    json = yield cmd_dict


def reset_shared_storage_budget(
        owner_origin: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Resets the budget for ``ownerOrigin`` by clearing all budget withdrawals.

    **EXPERIMENTAL**

    :param owner_origin:
    '''
    params: T_JSON_DICT = dict()
    params['ownerOrigin'] = owner_origin
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.resetSharedStorageBudget',
        'params': params,
    }
    json = yield cmd_dict


def set_shared_storage_tracking(
        enable: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables/disables issuing of sharedStorageAccessed events.

    **EXPERIMENTAL**

    :param enable:
    '''
    params: T_JSON_DICT = dict()
    params['enable'] = enable
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.setSharedStorageTracking',
        'params': params,
    }
    json = yield cmd_dict


def set_storage_bucket_tracking(
        storage_key: str,
        enable: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Set tracking for a storage key's buckets.

    **EXPERIMENTAL**

    :param storage_key:
    :param enable:
    '''
    params: T_JSON_DICT = dict()
    params['storageKey'] = storage_key
    params['enable'] = enable
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.setStorageBucketTracking',
        'params': params,
    }
    json = yield cmd_dict


def delete_storage_bucket(
        bucket: StorageBucket
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Deletes the Storage Bucket with the given storage key and bucket name.

    **EXPERIMENTAL**

    :param bucket:
    '''
    params: T_JSON_DICT = dict()
    params['bucket'] = bucket.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.deleteStorageBucket',
        'params': params,
    }
    json = yield cmd_dict


def run_bounce_tracking_mitigations() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[str]]:
    '''
    Deletes state for sites identified as potential bounce trackers, immediately.

    **EXPERIMENTAL**

    :returns: 
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.runBounceTrackingMitigations',
    }
    json = yield cmd_dict
    return [str(i) for i in json['deletedSites']]


def set_attribution_reporting_local_testing_mode(
        enabled: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    https://wicg.github.io/attribution-reporting-api/

    **EXPERIMENTAL**

    :param enabled: If enabled, noise is suppressed and reports are sent immediately.
    '''
    params: T_JSON_DICT = dict()
    params['enabled'] = enabled
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.setAttributionReportingLocalTestingMode',
        'params': params,
    }
    json = yield cmd_dict


def set_attribution_reporting_tracking(
        enable: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables/disables issuing of Attribution Reporting events.

    **EXPERIMENTAL**

    :param enable:
    '''
    params: T_JSON_DICT = dict()
    params['enable'] = enable
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.setAttributionReportingTracking',
        'params': params,
    }
    json = yield cmd_dict


def send_pending_attribution_reports() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,int]:
    '''
    Sends all pending Attribution Reports immediately, regardless of their
    scheduled report time.

    **EXPERIMENTAL**

    :returns: The number of reports that were sent.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.sendPendingAttributionReports',
    }
    json = yield cmd_dict
    return int(json['numSent'])


def get_related_website_sets() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[RelatedWebsiteSet]]:
    '''
    Returns the effective Related Website Sets in use by this profile for the browser
    session. The effective Related Website Sets will not change during a browser session.

    **EXPERIMENTAL**

    :returns: 
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.getRelatedWebsiteSets',
    }
    json = yield cmd_dict
    return [RelatedWebsiteSet.from_json(i) for i in json['sets']]


def get_affected_urls_for_third_party_cookie_metadata(
        first_party_url: str,
        third_party_urls: typing.List[str]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[str]]:
    '''
    Returns the list of URLs from a page and its embedded resources that match
    existing grace period URL pattern rules.
    https://developers.google.com/privacy-sandbox/cookies/temporary-exceptions/grace-period

    **EXPERIMENTAL**

    :param first_party_url: The URL of the page currently being visited.
    :param third_party_urls: The list of embedded resource URLs from the page.
    :returns: Array of matching URLs. If there is a primary pattern match for the first- party URL, only the first-party URL is returned in the array.
    '''
    params: T_JSON_DICT = dict()
    params['firstPartyUrl'] = first_party_url
    params['thirdPartyUrls'] = [i for i in third_party_urls]
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.getAffectedUrlsForThirdPartyCookieMetadata',
        'params': params,
    }
    json = yield cmd_dict
    return [str(i) for i in json['matchedUrls']]


@event_class('Storage.cacheStorageContentUpdated')
@dataclass
class CacheStorageContentUpdated:
    '''
    A cache's contents have been modified.
    '''
    #: Origin to update.
    origin: str
    #: Storage key to update.
    storage_key: str
    #: Storage bucket to update.
    bucket_id: str
    #: Name of cache in origin.
    cache_name: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> CacheStorageContentUpdated:
        return cls(
            origin=str(json['origin']),
            storage_key=str(json['storageKey']),
            bucket_id=str(json['bucketId']),
            cache_name=str(json['cacheName'])
        )


@event_class('Storage.cacheStorageListUpdated')
@dataclass
class CacheStorageListUpdated:
    '''
    A cache has been added/deleted.
    '''
    #: Origin to update.
    origin: str
    #: Storage key to update.
    storage_key: str
    #: Storage bucket to update.
    bucket_id: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> CacheStorageListUpdated:
        return cls(
            origin=str(json['origin']),
            storage_key=str(json['storageKey']),
            bucket_id=str(json['bucketId'])
        )


@event_class('Storage.indexedDBContentUpdated')
@dataclass
class IndexedDBContentUpdated:
    '''
    The origin's IndexedDB object store has been modified.
    '''
    #: Origin to update.
    origin: str
    #: Storage key to update.
    storage_key: str
    #: Storage bucket to update.
    bucket_id: str
    #: Database to update.
    database_name: str
    #: ObjectStore to update.
    object_store_name: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> IndexedDBContentUpdated:
        return cls(
            origin=str(json['origin']),
            storage_key=str(json['storageKey']),
            bucket_id=str(json['bucketId']),
            database_name=str(json['databaseName']),
            object_store_name=str(json['objectStoreName'])
        )


@event_class('Storage.indexedDBListUpdated')
@dataclass
class IndexedDBListUpdated:
    '''
    The origin's IndexedDB database list has been modified.
    '''
    #: Origin to update.
    origin: str
    #: Storage key to update.
    storage_key: str
    #: Storage bucket to update.
    bucket_id: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> IndexedDBListUpdated:
        return cls(
            origin=str(json['origin']),
            storage_key=str(json['storageKey']),
            bucket_id=str(json['bucketId'])
        )


@event_class('Storage.interestGroupAccessed')
@dataclass
class InterestGroupAccessed:
    '''
    One of the interest groups was accessed. Note that these events are global
    to all targets sharing an interest group store.
    '''
    access_time: network.TimeSinceEpoch
    type_: InterestGroupAccessType
    owner_origin: str
    name: str
    #: For topLevelBid/topLevelAdditionalBid, and when appropriate,
    #: win and additionalBidWin
    component_seller_origin: typing.Optional[str]
    #: For bid or somethingBid event, if done locally and not on a server.
    bid: typing.Optional[float]
    bid_currency: typing.Optional[str]
    #: For non-global events --- links to interestGroupAuctionEvent
    unique_auction_id: typing.Optional[InterestGroupAuctionId]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> InterestGroupAccessed:
        return cls(
            access_time=network.TimeSinceEpoch.from_json(json['accessTime']),
            type_=InterestGroupAccessType.from_json(json['type']),
            owner_origin=str(json['ownerOrigin']),
            name=str(json['name']),
            component_seller_origin=str(json['componentSellerOrigin']) if 'componentSellerOrigin' in json else None,
            bid=float(json['bid']) if 'bid' in json else None,
            bid_currency=str(json['bidCurrency']) if 'bidCurrency' in json else None,
            unique_auction_id=InterestGroupAuctionId.from_json(json['uniqueAuctionId']) if 'uniqueAuctionId' in json else None
        )


@event_class('Storage.interestGroupAuctionEventOccurred')
@dataclass
class InterestGroupAuctionEventOccurred:
    '''
    An auction involving interest groups is taking place. These events are
    target-specific.
    '''
    event_time: network.TimeSinceEpoch
    type_: InterestGroupAuctionEventType
    unique_auction_id: InterestGroupAuctionId
    #: Set for child auctions.
    parent_auction_id: typing.Optional[InterestGroupAuctionId]
    #: Set for started and configResolved
    auction_config: typing.Optional[dict]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> InterestGroupAuctionEventOccurred:
        return cls(
            event_time=network.TimeSinceEpoch.from_json(json['eventTime']),
            type_=InterestGroupAuctionEventType.from_json(json['type']),
            unique_auction_id=InterestGroupAuctionId.from_json(json['uniqueAuctionId']),
            parent_auction_id=InterestGroupAuctionId.from_json(json['parentAuctionId']) if 'parentAuctionId' in json else None,
            auction_config=dict(json['auctionConfig']) if 'auctionConfig' in json else None
        )


@event_class('Storage.interestGroupAuctionNetworkRequestCreated')
@dataclass
class InterestGroupAuctionNetworkRequestCreated:
    '''
    Specifies which auctions a particular network fetch may be related to, and
    in what role. Note that it is not ordered with respect to
    Network.requestWillBeSent (but will happen before loadingFinished
    loadingFailed).
    '''
    type_: InterestGroupAuctionFetchType
    request_id: network.RequestId
    #: This is the set of the auctions using the worklet that issued this
    #: request.  In the case of trusted signals, it's possible that only some of
    #: them actually care about the keys being queried.
    auctions: typing.List[InterestGroupAuctionId]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> InterestGroupAuctionNetworkRequestCreated:
        return cls(
            type_=InterestGroupAuctionFetchType.from_json(json['type']),
            request_id=network.RequestId.from_json(json['requestId']),
            auctions=[InterestGroupAuctionId.from_json(i) for i in json['auctions']]
        )


@event_class('Storage.sharedStorageAccessed')
@dataclass
class SharedStorageAccessed:
    '''
    Shared storage was accessed by the associated page.
    The following parameters are included in all events.
    '''
    #: Time of the access.
    access_time: network.TimeSinceEpoch
    #: Enum value indicating the access scope.
    scope: SharedStorageAccessScope
    #: Enum value indicating the Shared Storage API method invoked.
    method: SharedStorageAccessMethod
    #: DevTools Frame Token for the primary frame tree's root.
    main_frame_id: page.FrameId
    #: Serialization of the origin owning the Shared Storage data.
    owner_origin: str
    #: Serialization of the site owning the Shared Storage data.
    owner_site: str
    #: The sub-parameters wrapped by ``params`` are all optional and their
    #: presence/absence depends on ``type``.
    params: SharedStorageAccessParams

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> SharedStorageAccessed:
        return cls(
            access_time=network.TimeSinceEpoch.from_json(json['accessTime']),
            scope=SharedStorageAccessScope.from_json(json['scope']),
            method=SharedStorageAccessMethod.from_json(json['method']),
            main_frame_id=page.FrameId.from_json(json['mainFrameId']),
            owner_origin=str(json['ownerOrigin']),
            owner_site=str(json['ownerSite']),
            params=SharedStorageAccessParams.from_json(json['params'])
        )


@event_class('Storage.storageBucketCreatedOrUpdated')
@dataclass
class StorageBucketCreatedOrUpdated:
    bucket_info: StorageBucketInfo

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> StorageBucketCreatedOrUpdated:
        return cls(
            bucket_info=StorageBucketInfo.from_json(json['bucketInfo'])
        )


@event_class('Storage.storageBucketDeleted')
@dataclass
class StorageBucketDeleted:
    bucket_id: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> StorageBucketDeleted:
        return cls(
            bucket_id=str(json['bucketId'])
        )


@event_class('Storage.attributionReportingSourceRegistered')
@dataclass
class AttributionReportingSourceRegistered:
    '''
    **EXPERIMENTAL**


    '''
    registration: AttributionReportingSourceRegistration
    result: AttributionReportingSourceRegistrationResult

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> AttributionReportingSourceRegistered:
        return cls(
            registration=AttributionReportingSourceRegistration.from_json(json['registration']),
            result=AttributionReportingSourceRegistrationResult.from_json(json['result'])
        )


@event_class('Storage.attributionReportingTriggerRegistered')
@dataclass
class AttributionReportingTriggerRegistered:
    '''
    **EXPERIMENTAL**


    '''
    registration: AttributionReportingTriggerRegistration
    event_level: AttributionReportingEventLevelResult
    aggregatable: AttributionReportingAggregatableResult

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> AttributionReportingTriggerRegistered:
        return cls(
            registration=AttributionReportingTriggerRegistration.from_json(json['registration']),
            event_level=AttributionReportingEventLevelResult.from_json(json['eventLevel']),
            aggregatable=AttributionReportingAggregatableResult.from_json(json['aggregatable'])
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v135\storage.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Storage (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import browser
from . import network
from . import page


class SerializedStorageKey(str):
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> SerializedStorageKey:
        return cls(json)

    def __repr__(self):
        return 'SerializedStorageKey({})'.format(super().__repr__())


class StorageType(enum.Enum):
    '''
    Enum of possible storage types.
    '''
    COOKIES = "cookies"
    FILE_SYSTEMS = "file_systems"
    INDEXEDDB = "indexeddb"
    LOCAL_STORAGE = "local_storage"
    SHADER_CACHE = "shader_cache"
    WEBSQL = "websql"
    SERVICE_WORKERS = "service_workers"
    CACHE_STORAGE = "cache_storage"
    INTEREST_GROUPS = "interest_groups"
    SHARED_STORAGE = "shared_storage"
    STORAGE_BUCKETS = "storage_buckets"
    ALL_ = "all"
    OTHER = "other"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class UsageForType:
    '''
    Usage for a storage type.
    '''
    #: Name of storage type.
    storage_type: StorageType

    #: Storage usage (bytes).
    usage: float

    def to_json(self):
        json = dict()
        json['storageType'] = self.storage_type.to_json()
        json['usage'] = self.usage
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            storage_type=StorageType.from_json(json['storageType']),
            usage=float(json['usage']),
        )


@dataclass
class TrustTokens:
    '''
    Pair of issuer origin and number of available (signed, but not used) Trust
    Tokens from that issuer.
    '''
    issuer_origin: str

    count: float

    def to_json(self):
        json = dict()
        json['issuerOrigin'] = self.issuer_origin
        json['count'] = self.count
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            issuer_origin=str(json['issuerOrigin']),
            count=float(json['count']),
        )


class InterestGroupAuctionId(str):
    '''
    Protected audience interest group auction identifier.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> InterestGroupAuctionId:
        return cls(json)

    def __repr__(self):
        return 'InterestGroupAuctionId({})'.format(super().__repr__())


class InterestGroupAccessType(enum.Enum):
    '''
    Enum of interest group access types.
    '''
    JOIN = "join"
    LEAVE = "leave"
    UPDATE = "update"
    LOADED = "loaded"
    BID = "bid"
    WIN = "win"
    ADDITIONAL_BID = "additionalBid"
    ADDITIONAL_BID_WIN = "additionalBidWin"
    TOP_LEVEL_BID = "topLevelBid"
    TOP_LEVEL_ADDITIONAL_BID = "topLevelAdditionalBid"
    CLEAR = "clear"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class InterestGroupAuctionEventType(enum.Enum):
    '''
    Enum of auction events.
    '''
    STARTED = "started"
    CONFIG_RESOLVED = "configResolved"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class InterestGroupAuctionFetchType(enum.Enum):
    '''
    Enum of network fetches auctions can do.
    '''
    BIDDER_JS = "bidderJs"
    BIDDER_WASM = "bidderWasm"
    SELLER_JS = "sellerJs"
    BIDDER_TRUSTED_SIGNALS = "bidderTrustedSignals"
    SELLER_TRUSTED_SIGNALS = "sellerTrustedSignals"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class SharedStorageAccessType(enum.Enum):
    '''
    Enum of shared storage access types.
    '''
    DOCUMENT_ADD_MODULE = "documentAddModule"
    DOCUMENT_SELECT_URL = "documentSelectURL"
    DOCUMENT_RUN = "documentRun"
    DOCUMENT_SET = "documentSet"
    DOCUMENT_APPEND = "documentAppend"
    DOCUMENT_DELETE = "documentDelete"
    DOCUMENT_CLEAR = "documentClear"
    DOCUMENT_GET = "documentGet"
    WORKLET_SET = "workletSet"
    WORKLET_APPEND = "workletAppend"
    WORKLET_DELETE = "workletDelete"
    WORKLET_CLEAR = "workletClear"
    WORKLET_GET = "workletGet"
    WORKLET_KEYS = "workletKeys"
    WORKLET_ENTRIES = "workletEntries"
    WORKLET_LENGTH = "workletLength"
    WORKLET_REMAINING_BUDGET = "workletRemainingBudget"
    HEADER_SET = "headerSet"
    HEADER_APPEND = "headerAppend"
    HEADER_DELETE = "headerDelete"
    HEADER_CLEAR = "headerClear"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class SharedStorageEntry:
    '''
    Struct for a single key-value pair in an origin's shared storage.
    '''
    key: str

    value: str

    def to_json(self):
        json = dict()
        json['key'] = self.key
        json['value'] = self.value
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            key=str(json['key']),
            value=str(json['value']),
        )


@dataclass
class SharedStorageMetadata:
    '''
    Details for an origin's shared storage.
    '''
    #: Time when the origin's shared storage was last created.
    creation_time: network.TimeSinceEpoch

    #: Number of key-value pairs stored in origin's shared storage.
    length: int

    #: Current amount of bits of entropy remaining in the navigation budget.
    remaining_budget: float

    #: Total number of bytes stored as key-value pairs in origin's shared
    #: storage.
    bytes_used: int

    def to_json(self):
        json = dict()
        json['creationTime'] = self.creation_time.to_json()
        json['length'] = self.length
        json['remainingBudget'] = self.remaining_budget
        json['bytesUsed'] = self.bytes_used
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            creation_time=network.TimeSinceEpoch.from_json(json['creationTime']),
            length=int(json['length']),
            remaining_budget=float(json['remainingBudget']),
            bytes_used=int(json['bytesUsed']),
        )


@dataclass
class SharedStorageReportingMetadata:
    '''
    Pair of reporting metadata details for a candidate URL for ``selectURL()``.
    '''
    event_type: str

    reporting_url: str

    def to_json(self):
        json = dict()
        json['eventType'] = self.event_type
        json['reportingUrl'] = self.reporting_url
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            event_type=str(json['eventType']),
            reporting_url=str(json['reportingUrl']),
        )


@dataclass
class SharedStorageUrlWithMetadata:
    '''
    Bundles a candidate URL with its reporting metadata.
    '''
    #: Spec of candidate URL.
    url: str

    #: Any associated reporting metadata.
    reporting_metadata: typing.List[SharedStorageReportingMetadata]

    def to_json(self):
        json = dict()
        json['url'] = self.url
        json['reportingMetadata'] = [i.to_json() for i in self.reporting_metadata]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            url=str(json['url']),
            reporting_metadata=[SharedStorageReportingMetadata.from_json(i) for i in json['reportingMetadata']],
        )


@dataclass
class SharedStorageAccessParams:
    '''
    Bundles the parameters for shared storage access events whose
    presence/absence can vary according to SharedStorageAccessType.
    '''
    #: Spec of the module script URL.
    #: Present only for SharedStorageAccessType.documentAddModule.
    script_source_url: typing.Optional[str] = None

    #: Name of the registered operation to be run.
    #: Present only for SharedStorageAccessType.documentRun and
    #: SharedStorageAccessType.documentSelectURL.
    operation_name: typing.Optional[str] = None

    #: The operation's serialized data in bytes (converted to a string).
    #: Present only for SharedStorageAccessType.documentRun and
    #: SharedStorageAccessType.documentSelectURL.
    serialized_data: typing.Optional[str] = None

    #: Array of candidate URLs' specs, along with any associated metadata.
    #: Present only for SharedStorageAccessType.documentSelectURL.
    urls_with_metadata: typing.Optional[typing.List[SharedStorageUrlWithMetadata]] = None

    #: Key for a specific entry in an origin's shared storage.
    #: Present only for SharedStorageAccessType.documentSet,
    #: SharedStorageAccessType.documentAppend,
    #: SharedStorageAccessType.documentDelete,
    #: SharedStorageAccessType.workletSet,
    #: SharedStorageAccessType.workletAppend,
    #: SharedStorageAccessType.workletDelete,
    #: SharedStorageAccessType.workletGet,
    #: SharedStorageAccessType.headerSet,
    #: SharedStorageAccessType.headerAppend, and
    #: SharedStorageAccessType.headerDelete.
    key: typing.Optional[str] = None

    #: Value for a specific entry in an origin's shared storage.
    #: Present only for SharedStorageAccessType.documentSet,
    #: SharedStorageAccessType.documentAppend,
    #: SharedStorageAccessType.workletSet,
    #: SharedStorageAccessType.workletAppend,
    #: SharedStorageAccessType.headerSet, and
    #: SharedStorageAccessType.headerAppend.
    value: typing.Optional[str] = None

    #: Whether or not to set an entry for a key if that key is already present.
    #: Present only for SharedStorageAccessType.documentSet,
    #: SharedStorageAccessType.workletSet, and
    #: SharedStorageAccessType.headerSet.
    ignore_if_present: typing.Optional[bool] = None

    def to_json(self):
        json = dict()
        if self.script_source_url is not None:
            json['scriptSourceUrl'] = self.script_source_url
        if self.operation_name is not None:
            json['operationName'] = self.operation_name
        if self.serialized_data is not None:
            json['serializedData'] = self.serialized_data
        if self.urls_with_metadata is not None:
            json['urlsWithMetadata'] = [i.to_json() for i in self.urls_with_metadata]
        if self.key is not None:
            json['key'] = self.key
        if self.value is not None:
            json['value'] = self.value
        if self.ignore_if_present is not None:
            json['ignoreIfPresent'] = self.ignore_if_present
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            script_source_url=str(json['scriptSourceUrl']) if 'scriptSourceUrl' in json else None,
            operation_name=str(json['operationName']) if 'operationName' in json else None,
            serialized_data=str(json['serializedData']) if 'serializedData' in json else None,
            urls_with_metadata=[SharedStorageUrlWithMetadata.from_json(i) for i in json['urlsWithMetadata']] if 'urlsWithMetadata' in json else None,
            key=str(json['key']) if 'key' in json else None,
            value=str(json['value']) if 'value' in json else None,
            ignore_if_present=bool(json['ignoreIfPresent']) if 'ignoreIfPresent' in json else None,
        )


class StorageBucketsDurability(enum.Enum):
    RELAXED = "relaxed"
    STRICT = "strict"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class StorageBucket:
    storage_key: SerializedStorageKey

    #: If not specified, it is the default bucket of the storageKey.
    name: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['storageKey'] = self.storage_key.to_json()
        if self.name is not None:
            json['name'] = self.name
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            storage_key=SerializedStorageKey.from_json(json['storageKey']),
            name=str(json['name']) if 'name' in json else None,
        )


@dataclass
class StorageBucketInfo:
    bucket: StorageBucket

    id_: str

    expiration: network.TimeSinceEpoch

    #: Storage quota (bytes).
    quota: float

    persistent: bool

    durability: StorageBucketsDurability

    def to_json(self):
        json = dict()
        json['bucket'] = self.bucket.to_json()
        json['id'] = self.id_
        json['expiration'] = self.expiration.to_json()
        json['quota'] = self.quota
        json['persistent'] = self.persistent
        json['durability'] = self.durability.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            bucket=StorageBucket.from_json(json['bucket']),
            id_=str(json['id']),
            expiration=network.TimeSinceEpoch.from_json(json['expiration']),
            quota=float(json['quota']),
            persistent=bool(json['persistent']),
            durability=StorageBucketsDurability.from_json(json['durability']),
        )


class AttributionReportingSourceType(enum.Enum):
    NAVIGATION = "navigation"
    EVENT = "event"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class UnsignedInt64AsBase10(str):
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> UnsignedInt64AsBase10:
        return cls(json)

    def __repr__(self):
        return 'UnsignedInt64AsBase10({})'.format(super().__repr__())


class UnsignedInt128AsBase16(str):
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> UnsignedInt128AsBase16:
        return cls(json)

    def __repr__(self):
        return 'UnsignedInt128AsBase16({})'.format(super().__repr__())


class SignedInt64AsBase10(str):
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> SignedInt64AsBase10:
        return cls(json)

    def __repr__(self):
        return 'SignedInt64AsBase10({})'.format(super().__repr__())


@dataclass
class AttributionReportingFilterDataEntry:
    key: str

    values: typing.List[str]

    def to_json(self):
        json = dict()
        json['key'] = self.key
        json['values'] = [i for i in self.values]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            key=str(json['key']),
            values=[str(i) for i in json['values']],
        )


@dataclass
class AttributionReportingFilterConfig:
    filter_values: typing.List[AttributionReportingFilterDataEntry]

    #: duration in seconds
    lookback_window: typing.Optional[int] = None

    def to_json(self):
        json = dict()
        json['filterValues'] = [i.to_json() for i in self.filter_values]
        if self.lookback_window is not None:
            json['lookbackWindow'] = self.lookback_window
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            filter_values=[AttributionReportingFilterDataEntry.from_json(i) for i in json['filterValues']],
            lookback_window=int(json['lookbackWindow']) if 'lookbackWindow' in json else None,
        )


@dataclass
class AttributionReportingFilterPair:
    filters: typing.List[AttributionReportingFilterConfig]

    not_filters: typing.List[AttributionReportingFilterConfig]

    def to_json(self):
        json = dict()
        json['filters'] = [i.to_json() for i in self.filters]
        json['notFilters'] = [i.to_json() for i in self.not_filters]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            filters=[AttributionReportingFilterConfig.from_json(i) for i in json['filters']],
            not_filters=[AttributionReportingFilterConfig.from_json(i) for i in json['notFilters']],
        )


@dataclass
class AttributionReportingAggregationKeysEntry:
    key: str

    value: UnsignedInt128AsBase16

    def to_json(self):
        json = dict()
        json['key'] = self.key
        json['value'] = self.value.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            key=str(json['key']),
            value=UnsignedInt128AsBase16.from_json(json['value']),
        )


@dataclass
class AttributionReportingEventReportWindows:
    #: duration in seconds
    start: int

    #: duration in seconds
    ends: typing.List[int]

    def to_json(self):
        json = dict()
        json['start'] = self.start
        json['ends'] = [i for i in self.ends]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            start=int(json['start']),
            ends=[int(i) for i in json['ends']],
        )


@dataclass
class AttributionReportingTriggerSpec:
    #: number instead of integer because not all uint32 can be represented by
    #: int
    trigger_data: typing.List[float]

    event_report_windows: AttributionReportingEventReportWindows

    def to_json(self):
        json = dict()
        json['triggerData'] = [i for i in self.trigger_data]
        json['eventReportWindows'] = self.event_report_windows.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            trigger_data=[float(i) for i in json['triggerData']],
            event_report_windows=AttributionReportingEventReportWindows.from_json(json['eventReportWindows']),
        )


class AttributionReportingTriggerDataMatching(enum.Enum):
    EXACT = "exact"
    MODULUS = "modulus"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class AttributionReportingAggregatableDebugReportingData:
    key_piece: UnsignedInt128AsBase16

    #: number instead of integer because not all uint32 can be represented by
    #: int
    value: float

    types: typing.List[str]

    def to_json(self):
        json = dict()
        json['keyPiece'] = self.key_piece.to_json()
        json['value'] = self.value
        json['types'] = [i for i in self.types]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            key_piece=UnsignedInt128AsBase16.from_json(json['keyPiece']),
            value=float(json['value']),
            types=[str(i) for i in json['types']],
        )


@dataclass
class AttributionReportingAggregatableDebugReportingConfig:
    key_piece: UnsignedInt128AsBase16

    debug_data: typing.List[AttributionReportingAggregatableDebugReportingData]

    #: number instead of integer because not all uint32 can be represented by
    #: int, only present for source registrations
    budget: typing.Optional[float] = None

    aggregation_coordinator_origin: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['keyPiece'] = self.key_piece.to_json()
        json['debugData'] = [i.to_json() for i in self.debug_data]
        if self.budget is not None:
            json['budget'] = self.budget
        if self.aggregation_coordinator_origin is not None:
            json['aggregationCoordinatorOrigin'] = self.aggregation_coordinator_origin
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            key_piece=UnsignedInt128AsBase16.from_json(json['keyPiece']),
            debug_data=[AttributionReportingAggregatableDebugReportingData.from_json(i) for i in json['debugData']],
            budget=float(json['budget']) if 'budget' in json else None,
            aggregation_coordinator_origin=str(json['aggregationCoordinatorOrigin']) if 'aggregationCoordinatorOrigin' in json else None,
        )


@dataclass
class AttributionScopesData:
    values: typing.List[str]

    #: number instead of integer because not all uint32 can be represented by
    #: int
    limit: float

    max_event_states: float

    def to_json(self):
        json = dict()
        json['values'] = [i for i in self.values]
        json['limit'] = self.limit
        json['maxEventStates'] = self.max_event_states
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            values=[str(i) for i in json['values']],
            limit=float(json['limit']),
            max_event_states=float(json['maxEventStates']),
        )


@dataclass
class AttributionReportingSourceRegistration:
    time: network.TimeSinceEpoch

    #: duration in seconds
    expiry: int

    trigger_specs: typing.List[AttributionReportingTriggerSpec]

    #: duration in seconds
    aggregatable_report_window: int

    type_: AttributionReportingSourceType

    source_origin: str

    reporting_origin: str

    destination_sites: typing.List[str]

    event_id: UnsignedInt64AsBase10

    priority: SignedInt64AsBase10

    filter_data: typing.List[AttributionReportingFilterDataEntry]

    aggregation_keys: typing.List[AttributionReportingAggregationKeysEntry]

    trigger_data_matching: AttributionReportingTriggerDataMatching

    destination_limit_priority: SignedInt64AsBase10

    aggregatable_debug_reporting_config: AttributionReportingAggregatableDebugReportingConfig

    max_event_level_reports: int

    debug_key: typing.Optional[UnsignedInt64AsBase10] = None

    scopes_data: typing.Optional[AttributionScopesData] = None

    def to_json(self):
        json = dict()
        json['time'] = self.time.to_json()
        json['expiry'] = self.expiry
        json['triggerSpecs'] = [i.to_json() for i in self.trigger_specs]
        json['aggregatableReportWindow'] = self.aggregatable_report_window
        json['type'] = self.type_.to_json()
        json['sourceOrigin'] = self.source_origin
        json['reportingOrigin'] = self.reporting_origin
        json['destinationSites'] = [i for i in self.destination_sites]
        json['eventId'] = self.event_id.to_json()
        json['priority'] = self.priority.to_json()
        json['filterData'] = [i.to_json() for i in self.filter_data]
        json['aggregationKeys'] = [i.to_json() for i in self.aggregation_keys]
        json['triggerDataMatching'] = self.trigger_data_matching.to_json()
        json['destinationLimitPriority'] = self.destination_limit_priority.to_json()
        json['aggregatableDebugReportingConfig'] = self.aggregatable_debug_reporting_config.to_json()
        json['maxEventLevelReports'] = self.max_event_level_reports
        if self.debug_key is not None:
            json['debugKey'] = self.debug_key.to_json()
        if self.scopes_data is not None:
            json['scopesData'] = self.scopes_data.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            time=network.TimeSinceEpoch.from_json(json['time']),
            expiry=int(json['expiry']),
            trigger_specs=[AttributionReportingTriggerSpec.from_json(i) for i in json['triggerSpecs']],
            aggregatable_report_window=int(json['aggregatableReportWindow']),
            type_=AttributionReportingSourceType.from_json(json['type']),
            source_origin=str(json['sourceOrigin']),
            reporting_origin=str(json['reportingOrigin']),
            destination_sites=[str(i) for i in json['destinationSites']],
            event_id=UnsignedInt64AsBase10.from_json(json['eventId']),
            priority=SignedInt64AsBase10.from_json(json['priority']),
            filter_data=[AttributionReportingFilterDataEntry.from_json(i) for i in json['filterData']],
            aggregation_keys=[AttributionReportingAggregationKeysEntry.from_json(i) for i in json['aggregationKeys']],
            trigger_data_matching=AttributionReportingTriggerDataMatching.from_json(json['triggerDataMatching']),
            destination_limit_priority=SignedInt64AsBase10.from_json(json['destinationLimitPriority']),
            aggregatable_debug_reporting_config=AttributionReportingAggregatableDebugReportingConfig.from_json(json['aggregatableDebugReportingConfig']),
            max_event_level_reports=int(json['maxEventLevelReports']),
            debug_key=UnsignedInt64AsBase10.from_json(json['debugKey']) if 'debugKey' in json else None,
            scopes_data=AttributionScopesData.from_json(json['scopesData']) if 'scopesData' in json else None,
        )


class AttributionReportingSourceRegistrationResult(enum.Enum):
    SUCCESS = "success"
    INTERNAL_ERROR = "internalError"
    INSUFFICIENT_SOURCE_CAPACITY = "insufficientSourceCapacity"
    INSUFFICIENT_UNIQUE_DESTINATION_CAPACITY = "insufficientUniqueDestinationCapacity"
    EXCESSIVE_REPORTING_ORIGINS = "excessiveReportingOrigins"
    PROHIBITED_BY_BROWSER_POLICY = "prohibitedByBrowserPolicy"
    SUCCESS_NOISED = "successNoised"
    DESTINATION_REPORTING_LIMIT_REACHED = "destinationReportingLimitReached"
    DESTINATION_GLOBAL_LIMIT_REACHED = "destinationGlobalLimitReached"
    DESTINATION_BOTH_LIMITS_REACHED = "destinationBothLimitsReached"
    REPORTING_ORIGINS_PER_SITE_LIMIT_REACHED = "reportingOriginsPerSiteLimitReached"
    EXCEEDS_MAX_CHANNEL_CAPACITY = "exceedsMaxChannelCapacity"
    EXCEEDS_MAX_SCOPES_CHANNEL_CAPACITY = "exceedsMaxScopesChannelCapacity"
    EXCEEDS_MAX_TRIGGER_STATE_CARDINALITY = "exceedsMaxTriggerStateCardinality"
    EXCEEDS_MAX_EVENT_STATES_LIMIT = "exceedsMaxEventStatesLimit"
    DESTINATION_PER_DAY_REPORTING_LIMIT_REACHED = "destinationPerDayReportingLimitReached"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class AttributionReportingSourceRegistrationTimeConfig(enum.Enum):
    INCLUDE = "include"
    EXCLUDE = "exclude"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class AttributionReportingAggregatableValueDictEntry:
    key: str

    #: number instead of integer because not all uint32 can be represented by
    #: int
    value: float

    filtering_id: UnsignedInt64AsBase10

    def to_json(self):
        json = dict()
        json['key'] = self.key
        json['value'] = self.value
        json['filteringId'] = self.filtering_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            key=str(json['key']),
            value=float(json['value']),
            filtering_id=UnsignedInt64AsBase10.from_json(json['filteringId']),
        )


@dataclass
class AttributionReportingAggregatableValueEntry:
    values: typing.List[AttributionReportingAggregatableValueDictEntry]

    filters: AttributionReportingFilterPair

    def to_json(self):
        json = dict()
        json['values'] = [i.to_json() for i in self.values]
        json['filters'] = self.filters.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            values=[AttributionReportingAggregatableValueDictEntry.from_json(i) for i in json['values']],
            filters=AttributionReportingFilterPair.from_json(json['filters']),
        )


@dataclass
class AttributionReportingEventTriggerData:
    data: UnsignedInt64AsBase10

    priority: SignedInt64AsBase10

    filters: AttributionReportingFilterPair

    dedup_key: typing.Optional[UnsignedInt64AsBase10] = None

    def to_json(self):
        json = dict()
        json['data'] = self.data.to_json()
        json['priority'] = self.priority.to_json()
        json['filters'] = self.filters.to_json()
        if self.dedup_key is not None:
            json['dedupKey'] = self.dedup_key.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            data=UnsignedInt64AsBase10.from_json(json['data']),
            priority=SignedInt64AsBase10.from_json(json['priority']),
            filters=AttributionReportingFilterPair.from_json(json['filters']),
            dedup_key=UnsignedInt64AsBase10.from_json(json['dedupKey']) if 'dedupKey' in json else None,
        )


@dataclass
class AttributionReportingAggregatableTriggerData:
    key_piece: UnsignedInt128AsBase16

    source_keys: typing.List[str]

    filters: AttributionReportingFilterPair

    def to_json(self):
        json = dict()
        json['keyPiece'] = self.key_piece.to_json()
        json['sourceKeys'] = [i for i in self.source_keys]
        json['filters'] = self.filters.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            key_piece=UnsignedInt128AsBase16.from_json(json['keyPiece']),
            source_keys=[str(i) for i in json['sourceKeys']],
            filters=AttributionReportingFilterPair.from_json(json['filters']),
        )


@dataclass
class AttributionReportingAggregatableDedupKey:
    filters: AttributionReportingFilterPair

    dedup_key: typing.Optional[UnsignedInt64AsBase10] = None

    def to_json(self):
        json = dict()
        json['filters'] = self.filters.to_json()
        if self.dedup_key is not None:
            json['dedupKey'] = self.dedup_key.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            filters=AttributionReportingFilterPair.from_json(json['filters']),
            dedup_key=UnsignedInt64AsBase10.from_json(json['dedupKey']) if 'dedupKey' in json else None,
        )


@dataclass
class AttributionReportingTriggerRegistration:
    filters: AttributionReportingFilterPair

    aggregatable_dedup_keys: typing.List[AttributionReportingAggregatableDedupKey]

    event_trigger_data: typing.List[AttributionReportingEventTriggerData]

    aggregatable_trigger_data: typing.List[AttributionReportingAggregatableTriggerData]

    aggregatable_values: typing.List[AttributionReportingAggregatableValueEntry]

    aggregatable_filtering_id_max_bytes: int

    debug_reporting: bool

    source_registration_time_config: AttributionReportingSourceRegistrationTimeConfig

    aggregatable_debug_reporting_config: AttributionReportingAggregatableDebugReportingConfig

    scopes: typing.List[str]

    debug_key: typing.Optional[UnsignedInt64AsBase10] = None

    aggregation_coordinator_origin: typing.Optional[str] = None

    trigger_context_id: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['filters'] = self.filters.to_json()
        json['aggregatableDedupKeys'] = [i.to_json() for i in self.aggregatable_dedup_keys]
        json['eventTriggerData'] = [i.to_json() for i in self.event_trigger_data]
        json['aggregatableTriggerData'] = [i.to_json() for i in self.aggregatable_trigger_data]
        json['aggregatableValues'] = [i.to_json() for i in self.aggregatable_values]
        json['aggregatableFilteringIdMaxBytes'] = self.aggregatable_filtering_id_max_bytes
        json['debugReporting'] = self.debug_reporting
        json['sourceRegistrationTimeConfig'] = self.source_registration_time_config.to_json()
        json['aggregatableDebugReportingConfig'] = self.aggregatable_debug_reporting_config.to_json()
        json['scopes'] = [i for i in self.scopes]
        if self.debug_key is not None:
            json['debugKey'] = self.debug_key.to_json()
        if self.aggregation_coordinator_origin is not None:
            json['aggregationCoordinatorOrigin'] = self.aggregation_coordinator_origin
        if self.trigger_context_id is not None:
            json['triggerContextId'] = self.trigger_context_id
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            filters=AttributionReportingFilterPair.from_json(json['filters']),
            aggregatable_dedup_keys=[AttributionReportingAggregatableDedupKey.from_json(i) for i in json['aggregatableDedupKeys']],
            event_trigger_data=[AttributionReportingEventTriggerData.from_json(i) for i in json['eventTriggerData']],
            aggregatable_trigger_data=[AttributionReportingAggregatableTriggerData.from_json(i) for i in json['aggregatableTriggerData']],
            aggregatable_values=[AttributionReportingAggregatableValueEntry.from_json(i) for i in json['aggregatableValues']],
            aggregatable_filtering_id_max_bytes=int(json['aggregatableFilteringIdMaxBytes']),
            debug_reporting=bool(json['debugReporting']),
            source_registration_time_config=AttributionReportingSourceRegistrationTimeConfig.from_json(json['sourceRegistrationTimeConfig']),
            aggregatable_debug_reporting_config=AttributionReportingAggregatableDebugReportingConfig.from_json(json['aggregatableDebugReportingConfig']),
            scopes=[str(i) for i in json['scopes']],
            debug_key=UnsignedInt64AsBase10.from_json(json['debugKey']) if 'debugKey' in json else None,
            aggregation_coordinator_origin=str(json['aggregationCoordinatorOrigin']) if 'aggregationCoordinatorOrigin' in json else None,
            trigger_context_id=str(json['triggerContextId']) if 'triggerContextId' in json else None,
        )


class AttributionReportingEventLevelResult(enum.Enum):
    SUCCESS = "success"
    SUCCESS_DROPPED_LOWER_PRIORITY = "successDroppedLowerPriority"
    INTERNAL_ERROR = "internalError"
    NO_CAPACITY_FOR_ATTRIBUTION_DESTINATION = "noCapacityForAttributionDestination"
    NO_MATCHING_SOURCES = "noMatchingSources"
    DEDUPLICATED = "deduplicated"
    EXCESSIVE_ATTRIBUTIONS = "excessiveAttributions"
    PRIORITY_TOO_LOW = "priorityTooLow"
    NEVER_ATTRIBUTED_SOURCE = "neverAttributedSource"
    EXCESSIVE_REPORTING_ORIGINS = "excessiveReportingOrigins"
    NO_MATCHING_SOURCE_FILTER_DATA = "noMatchingSourceFilterData"
    PROHIBITED_BY_BROWSER_POLICY = "prohibitedByBrowserPolicy"
    NO_MATCHING_CONFIGURATIONS = "noMatchingConfigurations"
    EXCESSIVE_REPORTS = "excessiveReports"
    FALSELY_ATTRIBUTED_SOURCE = "falselyAttributedSource"
    REPORT_WINDOW_PASSED = "reportWindowPassed"
    NOT_REGISTERED = "notRegistered"
    REPORT_WINDOW_NOT_STARTED = "reportWindowNotStarted"
    NO_MATCHING_TRIGGER_DATA = "noMatchingTriggerData"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class AttributionReportingAggregatableResult(enum.Enum):
    SUCCESS = "success"
    INTERNAL_ERROR = "internalError"
    NO_CAPACITY_FOR_ATTRIBUTION_DESTINATION = "noCapacityForAttributionDestination"
    NO_MATCHING_SOURCES = "noMatchingSources"
    EXCESSIVE_ATTRIBUTIONS = "excessiveAttributions"
    EXCESSIVE_REPORTING_ORIGINS = "excessiveReportingOrigins"
    NO_HISTOGRAMS = "noHistograms"
    INSUFFICIENT_BUDGET = "insufficientBudget"
    INSUFFICIENT_NAMED_BUDGET = "insufficientNamedBudget"
    NO_MATCHING_SOURCE_FILTER_DATA = "noMatchingSourceFilterData"
    NOT_REGISTERED = "notRegistered"
    PROHIBITED_BY_BROWSER_POLICY = "prohibitedByBrowserPolicy"
    DEDUPLICATED = "deduplicated"
    REPORT_WINDOW_PASSED = "reportWindowPassed"
    EXCESSIVE_REPORTS = "excessiveReports"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class RelatedWebsiteSet:
    '''
    A single Related Website Set object.
    '''
    #: The primary site of this set, along with the ccTLDs if there is any.
    primary_sites: typing.List[str]

    #: The associated sites of this set, along with the ccTLDs if there is any.
    associated_sites: typing.List[str]

    #: The service sites of this set, along with the ccTLDs if there is any.
    service_sites: typing.List[str]

    def to_json(self):
        json = dict()
        json['primarySites'] = [i for i in self.primary_sites]
        json['associatedSites'] = [i for i in self.associated_sites]
        json['serviceSites'] = [i for i in self.service_sites]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            primary_sites=[str(i) for i in json['primarySites']],
            associated_sites=[str(i) for i in json['associatedSites']],
            service_sites=[str(i) for i in json['serviceSites']],
        )


def get_storage_key_for_frame(
        frame_id: page.FrameId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,SerializedStorageKey]:
    '''
    Returns a storage key given a frame id.

    :param frame_id:
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['frameId'] = frame_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.getStorageKeyForFrame',
        'params': params,
    }
    json = yield cmd_dict
    return SerializedStorageKey.from_json(json['storageKey'])


def clear_data_for_origin(
        origin: str,
        storage_types: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears storage for origin.

    :param origin: Security origin.
    :param storage_types: Comma separated list of StorageType to clear.
    '''
    params: T_JSON_DICT = dict()
    params['origin'] = origin
    params['storageTypes'] = storage_types
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.clearDataForOrigin',
        'params': params,
    }
    json = yield cmd_dict


def clear_data_for_storage_key(
        storage_key: str,
        storage_types: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears storage for storage key.

    :param storage_key: Storage key.
    :param storage_types: Comma separated list of StorageType to clear.
    '''
    params: T_JSON_DICT = dict()
    params['storageKey'] = storage_key
    params['storageTypes'] = storage_types
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.clearDataForStorageKey',
        'params': params,
    }
    json = yield cmd_dict


def get_cookies(
        browser_context_id: typing.Optional[browser.BrowserContextID] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[network.Cookie]]:
    '''
    Returns all browser cookies.

    :param browser_context_id: *(Optional)* Browser context to use when called on the browser endpoint.
    :returns: Array of cookie objects.
    '''
    params: T_JSON_DICT = dict()
    if browser_context_id is not None:
        params['browserContextId'] = browser_context_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.getCookies',
        'params': params,
    }
    json = yield cmd_dict
    return [network.Cookie.from_json(i) for i in json['cookies']]


def set_cookies(
        cookies: typing.List[network.CookieParam],
        browser_context_id: typing.Optional[browser.BrowserContextID] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets given cookies.

    :param cookies: Cookies to be set.
    :param browser_context_id: *(Optional)* Browser context to use when called on the browser endpoint.
    '''
    params: T_JSON_DICT = dict()
    params['cookies'] = [i.to_json() for i in cookies]
    if browser_context_id is not None:
        params['browserContextId'] = browser_context_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.setCookies',
        'params': params,
    }
    json = yield cmd_dict


def clear_cookies(
        browser_context_id: typing.Optional[browser.BrowserContextID] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears cookies.

    :param browser_context_id: *(Optional)* Browser context to use when called on the browser endpoint.
    '''
    params: T_JSON_DICT = dict()
    if browser_context_id is not None:
        params['browserContextId'] = browser_context_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.clearCookies',
        'params': params,
    }
    json = yield cmd_dict


def get_usage_and_quota(
        origin: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[float, float, bool, typing.List[UsageForType]]]:
    '''
    Returns usage and quota in bytes.

    :param origin: Security origin.
    :returns: A tuple with the following items:

        0. **usage** - Storage usage (bytes).
        1. **quota** - Storage quota (bytes).
        2. **overrideActive** - Whether or not the origin has an active storage quota override
        3. **usageBreakdown** - Storage usage per type (bytes).
    '''
    params: T_JSON_DICT = dict()
    params['origin'] = origin
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.getUsageAndQuota',
        'params': params,
    }
    json = yield cmd_dict
    return (
        float(json['usage']),
        float(json['quota']),
        bool(json['overrideActive']),
        [UsageForType.from_json(i) for i in json['usageBreakdown']]
    )


def override_quota_for_origin(
        origin: str,
        quota_size: typing.Optional[float] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Override quota for the specified origin

    **EXPERIMENTAL**

    :param origin: Security origin.
    :param quota_size: *(Optional)* The quota size (in bytes) to override the original quota with. If this is called multiple times, the overridden quota will be equal to the quotaSize provided in the final call. If this is called without specifying a quotaSize, the quota will be reset to the default value for the specified origin. If this is called multiple times with different origins, the override will be maintained for each origin until it is disabled (called without a quotaSize).
    '''
    params: T_JSON_DICT = dict()
    params['origin'] = origin
    if quota_size is not None:
        params['quotaSize'] = quota_size
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.overrideQuotaForOrigin',
        'params': params,
    }
    json = yield cmd_dict


def track_cache_storage_for_origin(
        origin: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Registers origin to be notified when an update occurs to its cache storage list.

    :param origin: Security origin.
    '''
    params: T_JSON_DICT = dict()
    params['origin'] = origin
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.trackCacheStorageForOrigin',
        'params': params,
    }
    json = yield cmd_dict


def track_cache_storage_for_storage_key(
        storage_key: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Registers storage key to be notified when an update occurs to its cache storage list.

    :param storage_key: Storage key.
    '''
    params: T_JSON_DICT = dict()
    params['storageKey'] = storage_key
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.trackCacheStorageForStorageKey',
        'params': params,
    }
    json = yield cmd_dict


def track_indexed_db_for_origin(
        origin: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Registers origin to be notified when an update occurs to its IndexedDB.

    :param origin: Security origin.
    '''
    params: T_JSON_DICT = dict()
    params['origin'] = origin
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.trackIndexedDBForOrigin',
        'params': params,
    }
    json = yield cmd_dict


def track_indexed_db_for_storage_key(
        storage_key: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Registers storage key to be notified when an update occurs to its IndexedDB.

    :param storage_key: Storage key.
    '''
    params: T_JSON_DICT = dict()
    params['storageKey'] = storage_key
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.trackIndexedDBForStorageKey',
        'params': params,
    }
    json = yield cmd_dict


def untrack_cache_storage_for_origin(
        origin: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Unregisters origin from receiving notifications for cache storage.

    :param origin: Security origin.
    '''
    params: T_JSON_DICT = dict()
    params['origin'] = origin
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.untrackCacheStorageForOrigin',
        'params': params,
    }
    json = yield cmd_dict


def untrack_cache_storage_for_storage_key(
        storage_key: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Unregisters storage key from receiving notifications for cache storage.

    :param storage_key: Storage key.
    '''
    params: T_JSON_DICT = dict()
    params['storageKey'] = storage_key
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.untrackCacheStorageForStorageKey',
        'params': params,
    }
    json = yield cmd_dict


def untrack_indexed_db_for_origin(
        origin: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Unregisters origin from receiving notifications for IndexedDB.

    :param origin: Security origin.
    '''
    params: T_JSON_DICT = dict()
    params['origin'] = origin
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.untrackIndexedDBForOrigin',
        'params': params,
    }
    json = yield cmd_dict


def untrack_indexed_db_for_storage_key(
        storage_key: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Unregisters storage key from receiving notifications for IndexedDB.

    :param storage_key: Storage key.
    '''
    params: T_JSON_DICT = dict()
    params['storageKey'] = storage_key
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.untrackIndexedDBForStorageKey',
        'params': params,
    }
    json = yield cmd_dict


def get_trust_tokens() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[TrustTokens]]:
    '''
    Returns the number of stored Trust Tokens per issuer for the
    current browsing context.

    **EXPERIMENTAL**

    :returns: 
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.getTrustTokens',
    }
    json = yield cmd_dict
    return [TrustTokens.from_json(i) for i in json['tokens']]


def clear_trust_tokens(
        issuer_origin: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,bool]:
    '''
    Removes all Trust Tokens issued by the provided issuerOrigin.
    Leaves other stored data, including the issuer's Redemption Records, intact.

    **EXPERIMENTAL**

    :param issuer_origin:
    :returns: True if any tokens were deleted, false otherwise.
    '''
    params: T_JSON_DICT = dict()
    params['issuerOrigin'] = issuer_origin
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.clearTrustTokens',
        'params': params,
    }
    json = yield cmd_dict
    return bool(json['didDeleteTokens'])


def get_interest_group_details(
        owner_origin: str,
        name: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,dict]:
    '''
    Gets details for a named interest group.

    **EXPERIMENTAL**

    :param owner_origin:
    :param name:
    :returns: This largely corresponds to: https://wicg.github.io/turtledove/#dictdef-generatebidinterestgroup but has absolute expirationTime instead of relative lifetimeMs and also adds joiningOrigin.
    '''
    params: T_JSON_DICT = dict()
    params['ownerOrigin'] = owner_origin
    params['name'] = name
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.getInterestGroupDetails',
        'params': params,
    }
    json = yield cmd_dict
    return dict(json['details'])


def set_interest_group_tracking(
        enable: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables/Disables issuing of interestGroupAccessed events.

    **EXPERIMENTAL**

    :param enable:
    '''
    params: T_JSON_DICT = dict()
    params['enable'] = enable
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.setInterestGroupTracking',
        'params': params,
    }
    json = yield cmd_dict


def set_interest_group_auction_tracking(
        enable: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables/Disables issuing of interestGroupAuctionEventOccurred and
    interestGroupAuctionNetworkRequestCreated.

    **EXPERIMENTAL**

    :param enable:
    '''
    params: T_JSON_DICT = dict()
    params['enable'] = enable
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.setInterestGroupAuctionTracking',
        'params': params,
    }
    json = yield cmd_dict


def get_shared_storage_metadata(
        owner_origin: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,SharedStorageMetadata]:
    '''
    Gets metadata for an origin's shared storage.

    **EXPERIMENTAL**

    :param owner_origin:
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['ownerOrigin'] = owner_origin
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.getSharedStorageMetadata',
        'params': params,
    }
    json = yield cmd_dict
    return SharedStorageMetadata.from_json(json['metadata'])


def get_shared_storage_entries(
        owner_origin: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[SharedStorageEntry]]:
    '''
    Gets the entries in an given origin's shared storage.

    **EXPERIMENTAL**

    :param owner_origin:
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['ownerOrigin'] = owner_origin
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.getSharedStorageEntries',
        'params': params,
    }
    json = yield cmd_dict
    return [SharedStorageEntry.from_json(i) for i in json['entries']]


def set_shared_storage_entry(
        owner_origin: str,
        key: str,
        value: str,
        ignore_if_present: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets entry with ``key`` and ``value`` for a given origin's shared storage.

    **EXPERIMENTAL**

    :param owner_origin:
    :param key:
    :param value:
    :param ignore_if_present: *(Optional)* If ```ignoreIfPresent```` is included and true, then only sets the entry if ````key``` doesn't already exist.
    '''
    params: T_JSON_DICT = dict()
    params['ownerOrigin'] = owner_origin
    params['key'] = key
    params['value'] = value
    if ignore_if_present is not None:
        params['ignoreIfPresent'] = ignore_if_present
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.setSharedStorageEntry',
        'params': params,
    }
    json = yield cmd_dict


def delete_shared_storage_entry(
        owner_origin: str,
        key: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Deletes entry for ``key`` (if it exists) for a given origin's shared storage.

    **EXPERIMENTAL**

    :param owner_origin:
    :param key:
    '''
    params: T_JSON_DICT = dict()
    params['ownerOrigin'] = owner_origin
    params['key'] = key
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.deleteSharedStorageEntry',
        'params': params,
    }
    json = yield cmd_dict


def clear_shared_storage_entries(
        owner_origin: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears all entries for a given origin's shared storage.

    **EXPERIMENTAL**

    :param owner_origin:
    '''
    params: T_JSON_DICT = dict()
    params['ownerOrigin'] = owner_origin
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.clearSharedStorageEntries',
        'params': params,
    }
    json = yield cmd_dict


def reset_shared_storage_budget(
        owner_origin: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Resets the budget for ``ownerOrigin`` by clearing all budget withdrawals.

    **EXPERIMENTAL**

    :param owner_origin:
    '''
    params: T_JSON_DICT = dict()
    params['ownerOrigin'] = owner_origin
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.resetSharedStorageBudget',
        'params': params,
    }
    json = yield cmd_dict


def set_shared_storage_tracking(
        enable: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables/disables issuing of sharedStorageAccessed events.

    **EXPERIMENTAL**

    :param enable:
    '''
    params: T_JSON_DICT = dict()
    params['enable'] = enable
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.setSharedStorageTracking',
        'params': params,
    }
    json = yield cmd_dict


def set_storage_bucket_tracking(
        storage_key: str,
        enable: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Set tracking for a storage key's buckets.

    **EXPERIMENTAL**

    :param storage_key:
    :param enable:
    '''
    params: T_JSON_DICT = dict()
    params['storageKey'] = storage_key
    params['enable'] = enable
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.setStorageBucketTracking',
        'params': params,
    }
    json = yield cmd_dict


def delete_storage_bucket(
        bucket: StorageBucket
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Deletes the Storage Bucket with the given storage key and bucket name.

    **EXPERIMENTAL**

    :param bucket:
    '''
    params: T_JSON_DICT = dict()
    params['bucket'] = bucket.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.deleteStorageBucket',
        'params': params,
    }
    json = yield cmd_dict


def run_bounce_tracking_mitigations() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[str]]:
    '''
    Deletes state for sites identified as potential bounce trackers, immediately.

    **EXPERIMENTAL**

    :returns: 
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.runBounceTrackingMitigations',
    }
    json = yield cmd_dict
    return [str(i) for i in json['deletedSites']]


def set_attribution_reporting_local_testing_mode(
        enabled: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    https://wicg.github.io/attribution-reporting-api/

    **EXPERIMENTAL**

    :param enabled: If enabled, noise is suppressed and reports are sent immediately.
    '''
    params: T_JSON_DICT = dict()
    params['enabled'] = enabled
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.setAttributionReportingLocalTestingMode',
        'params': params,
    }
    json = yield cmd_dict


def set_attribution_reporting_tracking(
        enable: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables/disables issuing of Attribution Reporting events.

    **EXPERIMENTAL**

    :param enable:
    '''
    params: T_JSON_DICT = dict()
    params['enable'] = enable
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.setAttributionReportingTracking',
        'params': params,
    }
    json = yield cmd_dict


def send_pending_attribution_reports() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,int]:
    '''
    Sends all pending Attribution Reports immediately, regardless of their
    scheduled report time.

    **EXPERIMENTAL**

    :returns: The number of reports that were sent.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.sendPendingAttributionReports',
    }
    json = yield cmd_dict
    return int(json['numSent'])


def get_related_website_sets() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[RelatedWebsiteSet]]:
    '''
    Returns the effective Related Website Sets in use by this profile for the browser
    session. The effective Related Website Sets will not change during a browser session.

    **EXPERIMENTAL**

    :returns: 
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.getRelatedWebsiteSets',
    }
    json = yield cmd_dict
    return [RelatedWebsiteSet.from_json(i) for i in json['sets']]


def get_affected_urls_for_third_party_cookie_metadata(
        first_party_url: str,
        third_party_urls: typing.List[str]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[str]]:
    '''
    Returns the list of URLs from a page and its embedded resources that match
    existing grace period URL pattern rules.
    https://developers.google.com/privacy-sandbox/cookies/temporary-exceptions/grace-period

    **EXPERIMENTAL**

    :param first_party_url: The URL of the page currently being visited.
    :param third_party_urls: The list of embedded resource URLs from the page.
    :returns: Array of matching URLs. If there is a primary pattern match for the first- party URL, only the first-party URL is returned in the array.
    '''
    params: T_JSON_DICT = dict()
    params['firstPartyUrl'] = first_party_url
    params['thirdPartyUrls'] = [i for i in third_party_urls]
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.getAffectedUrlsForThirdPartyCookieMetadata',
        'params': params,
    }
    json = yield cmd_dict
    return [str(i) for i in json['matchedUrls']]


@event_class('Storage.cacheStorageContentUpdated')
@dataclass
class CacheStorageContentUpdated:
    '''
    A cache's contents have been modified.
    '''
    #: Origin to update.
    origin: str
    #: Storage key to update.
    storage_key: str
    #: Storage bucket to update.
    bucket_id: str
    #: Name of cache in origin.
    cache_name: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> CacheStorageContentUpdated:
        return cls(
            origin=str(json['origin']),
            storage_key=str(json['storageKey']),
            bucket_id=str(json['bucketId']),
            cache_name=str(json['cacheName'])
        )


@event_class('Storage.cacheStorageListUpdated')
@dataclass
class CacheStorageListUpdated:
    '''
    A cache has been added/deleted.
    '''
    #: Origin to update.
    origin: str
    #: Storage key to update.
    storage_key: str
    #: Storage bucket to update.
    bucket_id: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> CacheStorageListUpdated:
        return cls(
            origin=str(json['origin']),
            storage_key=str(json['storageKey']),
            bucket_id=str(json['bucketId'])
        )


@event_class('Storage.indexedDBContentUpdated')
@dataclass
class IndexedDBContentUpdated:
    '''
    The origin's IndexedDB object store has been modified.
    '''
    #: Origin to update.
    origin: str
    #: Storage key to update.
    storage_key: str
    #: Storage bucket to update.
    bucket_id: str
    #: Database to update.
    database_name: str
    #: ObjectStore to update.
    object_store_name: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> IndexedDBContentUpdated:
        return cls(
            origin=str(json['origin']),
            storage_key=str(json['storageKey']),
            bucket_id=str(json['bucketId']),
            database_name=str(json['databaseName']),
            object_store_name=str(json['objectStoreName'])
        )


@event_class('Storage.indexedDBListUpdated')
@dataclass
class IndexedDBListUpdated:
    '''
    The origin's IndexedDB database list has been modified.
    '''
    #: Origin to update.
    origin: str
    #: Storage key to update.
    storage_key: str
    #: Storage bucket to update.
    bucket_id: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> IndexedDBListUpdated:
        return cls(
            origin=str(json['origin']),
            storage_key=str(json['storageKey']),
            bucket_id=str(json['bucketId'])
        )


@event_class('Storage.interestGroupAccessed')
@dataclass
class InterestGroupAccessed:
    '''
    One of the interest groups was accessed. Note that these events are global
    to all targets sharing an interest group store.
    '''
    access_time: network.TimeSinceEpoch
    type_: InterestGroupAccessType
    owner_origin: str
    name: str
    #: For topLevelBid/topLevelAdditionalBid, and when appropriate,
    #: win and additionalBidWin
    component_seller_origin: typing.Optional[str]
    #: For bid or somethingBid event, if done locally and not on a server.
    bid: typing.Optional[float]
    bid_currency: typing.Optional[str]
    #: For non-global events --- links to interestGroupAuctionEvent
    unique_auction_id: typing.Optional[InterestGroupAuctionId]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> InterestGroupAccessed:
        return cls(
            access_time=network.TimeSinceEpoch.from_json(json['accessTime']),
            type_=InterestGroupAccessType.from_json(json['type']),
            owner_origin=str(json['ownerOrigin']),
            name=str(json['name']),
            component_seller_origin=str(json['componentSellerOrigin']) if 'componentSellerOrigin' in json else None,
            bid=float(json['bid']) if 'bid' in json else None,
            bid_currency=str(json['bidCurrency']) if 'bidCurrency' in json else None,
            unique_auction_id=InterestGroupAuctionId.from_json(json['uniqueAuctionId']) if 'uniqueAuctionId' in json else None
        )


@event_class('Storage.interestGroupAuctionEventOccurred')
@dataclass
class InterestGroupAuctionEventOccurred:
    '''
    An auction involving interest groups is taking place. These events are
    target-specific.
    '''
    event_time: network.TimeSinceEpoch
    type_: InterestGroupAuctionEventType
    unique_auction_id: InterestGroupAuctionId
    #: Set for child auctions.
    parent_auction_id: typing.Optional[InterestGroupAuctionId]
    #: Set for started and configResolved
    auction_config: typing.Optional[dict]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> InterestGroupAuctionEventOccurred:
        return cls(
            event_time=network.TimeSinceEpoch.from_json(json['eventTime']),
            type_=InterestGroupAuctionEventType.from_json(json['type']),
            unique_auction_id=InterestGroupAuctionId.from_json(json['uniqueAuctionId']),
            parent_auction_id=InterestGroupAuctionId.from_json(json['parentAuctionId']) if 'parentAuctionId' in json else None,
            auction_config=dict(json['auctionConfig']) if 'auctionConfig' in json else None
        )


@event_class('Storage.interestGroupAuctionNetworkRequestCreated')
@dataclass
class InterestGroupAuctionNetworkRequestCreated:
    '''
    Specifies which auctions a particular network fetch may be related to, and
    in what role. Note that it is not ordered with respect to
    Network.requestWillBeSent (but will happen before loadingFinished
    loadingFailed).
    '''
    type_: InterestGroupAuctionFetchType
    request_id: network.RequestId
    #: This is the set of the auctions using the worklet that issued this
    #: request.  In the case of trusted signals, it's possible that only some of
    #: them actually care about the keys being queried.
    auctions: typing.List[InterestGroupAuctionId]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> InterestGroupAuctionNetworkRequestCreated:
        return cls(
            type_=InterestGroupAuctionFetchType.from_json(json['type']),
            request_id=network.RequestId.from_json(json['requestId']),
            auctions=[InterestGroupAuctionId.from_json(i) for i in json['auctions']]
        )


@event_class('Storage.sharedStorageAccessed')
@dataclass
class SharedStorageAccessed:
    '''
    Shared storage was accessed by the associated page.
    The following parameters are included in all events.
    '''
    #: Time of the access.
    access_time: network.TimeSinceEpoch
    #: Enum value indicating the Shared Storage API method invoked.
    type_: SharedStorageAccessType
    #: DevTools Frame Token for the primary frame tree's root.
    main_frame_id: page.FrameId
    #: Serialized origin for the context that invoked the Shared Storage API.
    owner_origin: str
    #: The sub-parameters wrapped by ``params`` are all optional and their
    #: presence/absence depends on ``type``.
    params: SharedStorageAccessParams

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> SharedStorageAccessed:
        return cls(
            access_time=network.TimeSinceEpoch.from_json(json['accessTime']),
            type_=SharedStorageAccessType.from_json(json['type']),
            main_frame_id=page.FrameId.from_json(json['mainFrameId']),
            owner_origin=str(json['ownerOrigin']),
            params=SharedStorageAccessParams.from_json(json['params'])
        )


@event_class('Storage.storageBucketCreatedOrUpdated')
@dataclass
class StorageBucketCreatedOrUpdated:
    bucket_info: StorageBucketInfo

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> StorageBucketCreatedOrUpdated:
        return cls(
            bucket_info=StorageBucketInfo.from_json(json['bucketInfo'])
        )


@event_class('Storage.storageBucketDeleted')
@dataclass
class StorageBucketDeleted:
    bucket_id: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> StorageBucketDeleted:
        return cls(
            bucket_id=str(json['bucketId'])
        )


@event_class('Storage.attributionReportingSourceRegistered')
@dataclass
class AttributionReportingSourceRegistered:
    '''
    **EXPERIMENTAL**


    '''
    registration: AttributionReportingSourceRegistration
    result: AttributionReportingSourceRegistrationResult

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> AttributionReportingSourceRegistered:
        return cls(
            registration=AttributionReportingSourceRegistration.from_json(json['registration']),
            result=AttributionReportingSourceRegistrationResult.from_json(json['result'])
        )


@event_class('Storage.attributionReportingTriggerRegistered')
@dataclass
class AttributionReportingTriggerRegistered:
    '''
    **EXPERIMENTAL**


    '''
    registration: AttributionReportingTriggerRegistration
    event_level: AttributionReportingEventLevelResult
    aggregatable: AttributionReportingAggregatableResult

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> AttributionReportingTriggerRegistered:
        return cls(
            registration=AttributionReportingTriggerRegistration.from_json(json['registration']),
            event_level=AttributionReportingEventLevelResult.from_json(json['eventLevel']),
            aggregatable=AttributionReportingAggregatableResult.from_json(json['aggregatable'])
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v135\dom.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: DOM
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import page
from . import runtime


class NodeId(int):
    '''
    Unique DOM node identifier.
    '''
    def to_json(self) -> int:
        return self

    @classmethod
    def from_json(cls, json: int) -> NodeId:
        return cls(json)

    def __repr__(self):
        return 'NodeId({})'.format(super().__repr__())


class BackendNodeId(int):
    '''
    Unique DOM node identifier used to reference a node that may not have been pushed to the
    front-end.
    '''
    def to_json(self) -> int:
        return self

    @classmethod
    def from_json(cls, json: int) -> BackendNodeId:
        return cls(json)

    def __repr__(self):
        return 'BackendNodeId({})'.format(super().__repr__())


@dataclass
class BackendNode:
    '''
    Backend node with a friendly name.
    '''
    #: ``Node``'s nodeType.
    node_type: int

    #: ``Node``'s nodeName.
    node_name: str

    backend_node_id: BackendNodeId

    def to_json(self):
        json = dict()
        json['nodeType'] = self.node_type
        json['nodeName'] = self.node_name
        json['backendNodeId'] = self.backend_node_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            node_type=int(json['nodeType']),
            node_name=str(json['nodeName']),
            backend_node_id=BackendNodeId.from_json(json['backendNodeId']),
        )


class PseudoType(enum.Enum):
    '''
    Pseudo element type.
    '''
    FIRST_LINE = "first-line"
    FIRST_LETTER = "first-letter"
    CHECKMARK = "checkmark"
    BEFORE = "before"
    AFTER = "after"
    PICKER_ICON = "picker-icon"
    MARKER = "marker"
    BACKDROP = "backdrop"
    COLUMN = "column"
    SELECTION = "selection"
    SEARCH_TEXT = "search-text"
    TARGET_TEXT = "target-text"
    SPELLING_ERROR = "spelling-error"
    GRAMMAR_ERROR = "grammar-error"
    HIGHLIGHT = "highlight"
    FIRST_LINE_INHERITED = "first-line-inherited"
    SCROLL_MARKER = "scroll-marker"
    SCROLL_MARKER_GROUP = "scroll-marker-group"
    SCROLL_BUTTON = "scroll-button"
    SCROLLBAR = "scrollbar"
    SCROLLBAR_THUMB = "scrollbar-thumb"
    SCROLLBAR_BUTTON = "scrollbar-button"
    SCROLLBAR_TRACK = "scrollbar-track"
    SCROLLBAR_TRACK_PIECE = "scrollbar-track-piece"
    SCROLLBAR_CORNER = "scrollbar-corner"
    RESIZER = "resizer"
    INPUT_LIST_BUTTON = "input-list-button"
    VIEW_TRANSITION = "view-transition"
    VIEW_TRANSITION_GROUP = "view-transition-group"
    VIEW_TRANSITION_IMAGE_PAIR = "view-transition-image-pair"
    VIEW_TRANSITION_OLD = "view-transition-old"
    VIEW_TRANSITION_NEW = "view-transition-new"
    PLACEHOLDER = "placeholder"
    FILE_SELECTOR_BUTTON = "file-selector-button"
    DETAILS_CONTENT = "details-content"
    PICKER = "picker"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class ShadowRootType(enum.Enum):
    '''
    Shadow root type.
    '''
    USER_AGENT = "user-agent"
    OPEN_ = "open"
    CLOSED = "closed"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class CompatibilityMode(enum.Enum):
    '''
    Document compatibility mode.
    '''
    QUIRKS_MODE = "QuirksMode"
    LIMITED_QUIRKS_MODE = "LimitedQuirksMode"
    NO_QUIRKS_MODE = "NoQuirksMode"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class PhysicalAxes(enum.Enum):
    '''
    ContainerSelector physical axes
    '''
    HORIZONTAL = "Horizontal"
    VERTICAL = "Vertical"
    BOTH = "Both"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class LogicalAxes(enum.Enum):
    '''
    ContainerSelector logical axes
    '''
    INLINE = "Inline"
    BLOCK = "Block"
    BOTH = "Both"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class ScrollOrientation(enum.Enum):
    '''
    Physical scroll orientation
    '''
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class Node:
    '''
    DOM interaction is implemented in terms of mirror objects that represent the actual DOM nodes.
    DOMNode is a base node mirror type.
    '''
    #: Node identifier that is passed into the rest of the DOM messages as the ``nodeId``. Backend
    #: will only push node with given ``id`` once. It is aware of all requested nodes and will only
    #: fire DOM events for nodes known to the client.
    node_id: NodeId

    #: The BackendNodeId for this node.
    backend_node_id: BackendNodeId

    #: ``Node``'s nodeType.
    node_type: int

    #: ``Node``'s nodeName.
    node_name: str

    #: ``Node``'s localName.
    local_name: str

    #: ``Node``'s nodeValue.
    node_value: str

    #: The id of the parent node if any.
    parent_id: typing.Optional[NodeId] = None

    #: Child count for ``Container`` nodes.
    child_node_count: typing.Optional[int] = None

    #: Child nodes of this node when requested with children.
    children: typing.Optional[typing.List[Node]] = None

    #: Attributes of the ``Element`` node in the form of flat array ``[name1, value1, name2, value2]``.
    attributes: typing.Optional[typing.List[str]] = None

    #: Document URL that ``Document`` or ``FrameOwner`` node points to.
    document_url: typing.Optional[str] = None

    #: Base URL that ``Document`` or ``FrameOwner`` node uses for URL completion.
    base_url: typing.Optional[str] = None

    #: ``DocumentType``'s publicId.
    public_id: typing.Optional[str] = None

    #: ``DocumentType``'s systemId.
    system_id: typing.Optional[str] = None

    #: ``DocumentType``'s internalSubset.
    internal_subset: typing.Optional[str] = None

    #: ``Document``'s XML version in case of XML documents.
    xml_version: typing.Optional[str] = None

    #: ``Attr``'s name.
    name: typing.Optional[str] = None

    #: ``Attr``'s value.
    value: typing.Optional[str] = None

    #: Pseudo element type for this node.
    pseudo_type: typing.Optional[PseudoType] = None

    #: Pseudo element identifier for this node. Only present if there is a
    #: valid pseudoType.
    pseudo_identifier: typing.Optional[str] = None

    #: Shadow root type.
    shadow_root_type: typing.Optional[ShadowRootType] = None

    #: Frame ID for frame owner elements.
    frame_id: typing.Optional[page.FrameId] = None

    #: Content document for frame owner elements.
    content_document: typing.Optional[Node] = None

    #: Shadow root list for given element host.
    shadow_roots: typing.Optional[typing.List[Node]] = None

    #: Content document fragment for template elements.
    template_content: typing.Optional[Node] = None

    #: Pseudo elements associated with this node.
    pseudo_elements: typing.Optional[typing.List[Node]] = None

    #: Deprecated, as the HTML Imports API has been removed (crbug.com/937746).
    #: This property used to return the imported document for the HTMLImport links.
    #: The property is always undefined now.
    imported_document: typing.Optional[Node] = None

    #: Distributed nodes for given insertion point.
    distributed_nodes: typing.Optional[typing.List[BackendNode]] = None

    #: Whether the node is SVG.
    is_svg: typing.Optional[bool] = None

    compatibility_mode: typing.Optional[CompatibilityMode] = None

    assigned_slot: typing.Optional[BackendNode] = None

    is_scrollable: typing.Optional[bool] = None

    def to_json(self):
        json = dict()
        json['nodeId'] = self.node_id.to_json()
        json['backendNodeId'] = self.backend_node_id.to_json()
        json['nodeType'] = self.node_type
        json['nodeName'] = self.node_name
        json['localName'] = self.local_name
        json['nodeValue'] = self.node_value
        if self.parent_id is not None:
            json['parentId'] = self.parent_id.to_json()
        if self.child_node_count is not None:
            json['childNodeCount'] = self.child_node_count
        if self.children is not None:
            json['children'] = [i.to_json() for i in self.children]
        if self.attributes is not None:
            json['attributes'] = [i for i in self.attributes]
        if self.document_url is not None:
            json['documentURL'] = self.document_url
        if self.base_url is not None:
            json['baseURL'] = self.base_url
        if self.public_id is not None:
            json['publicId'] = self.public_id
        if self.system_id is not None:
            json['systemId'] = self.system_id
        if self.internal_subset is not None:
            json['internalSubset'] = self.internal_subset
        if self.xml_version is not None:
            json['xmlVersion'] = self.xml_version
        if self.name is not None:
            json['name'] = self.name
        if self.value is not None:
            json['value'] = self.value
        if self.pseudo_type is not None:
            json['pseudoType'] = self.pseudo_type.to_json()
        if self.pseudo_identifier is not None:
            json['pseudoIdentifier'] = self.pseudo_identifier
        if self.shadow_root_type is not None:
            json['shadowRootType'] = self.shadow_root_type.to_json()
        if self.frame_id is not None:
            json['frameId'] = self.frame_id.to_json()
        if self.content_document is not None:
            json['contentDocument'] = self.content_document.to_json()
        if self.shadow_roots is not None:
            json['shadowRoots'] = [i.to_json() for i in self.shadow_roots]
        if self.template_content is not None:
            json['templateContent'] = self.template_content.to_json()
        if self.pseudo_elements is not None:
            json['pseudoElements'] = [i.to_json() for i in self.pseudo_elements]
        if self.imported_document is not None:
            json['importedDocument'] = self.imported_document.to_json()
        if self.distributed_nodes is not None:
            json['distributedNodes'] = [i.to_json() for i in self.distributed_nodes]
        if self.is_svg is not None:
            json['isSVG'] = self.is_svg
        if self.compatibility_mode is not None:
            json['compatibilityMode'] = self.compatibility_mode.to_json()
        if self.assigned_slot is not None:
            json['assignedSlot'] = self.assigned_slot.to_json()
        if self.is_scrollable is not None:
            json['isScrollable'] = self.is_scrollable
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            node_id=NodeId.from_json(json['nodeId']),
            backend_node_id=BackendNodeId.from_json(json['backendNodeId']),
            node_type=int(json['nodeType']),
            node_name=str(json['nodeName']),
            local_name=str(json['localName']),
            node_value=str(json['nodeValue']),
            parent_id=NodeId.from_json(json['parentId']) if 'parentId' in json else None,
            child_node_count=int(json['childNodeCount']) if 'childNodeCount' in json else None,
            children=[Node.from_json(i) for i in json['children']] if 'children' in json else None,
            attributes=[str(i) for i in json['attributes']] if 'attributes' in json else None,
            document_url=str(json['documentURL']) if 'documentURL' in json else None,
            base_url=str(json['baseURL']) if 'baseURL' in json else None,
            public_id=str(json['publicId']) if 'publicId' in json else None,
            system_id=str(json['systemId']) if 'systemId' in json else None,
            internal_subset=str(json['internalSubset']) if 'internalSubset' in json else None,
            xml_version=str(json['xmlVersion']) if 'xmlVersion' in json else None,
            name=str(json['name']) if 'name' in json else None,
            value=str(json['value']) if 'value' in json else None,
            pseudo_type=PseudoType.from_json(json['pseudoType']) if 'pseudoType' in json else None,
            pseudo_identifier=str(json['pseudoIdentifier']) if 'pseudoIdentifier' in json else None,
            shadow_root_type=ShadowRootType.from_json(json['shadowRootType']) if 'shadowRootType' in json else None,
            frame_id=page.FrameId.from_json(json['frameId']) if 'frameId' in json else None,
            content_document=Node.from_json(json['contentDocument']) if 'contentDocument' in json else None,
            shadow_roots=[Node.from_json(i) for i in json['shadowRoots']] if 'shadowRoots' in json else None,
            template_content=Node.from_json(json['templateContent']) if 'templateContent' in json else None,
            pseudo_elements=[Node.from_json(i) for i in json['pseudoElements']] if 'pseudoElements' in json else None,
            imported_document=Node.from_json(json['importedDocument']) if 'importedDocument' in json else None,
            distributed_nodes=[BackendNode.from_json(i) for i in json['distributedNodes']] if 'distributedNodes' in json else None,
            is_svg=bool(json['isSVG']) if 'isSVG' in json else None,
            compatibility_mode=CompatibilityMode.from_json(json['compatibilityMode']) if 'compatibilityMode' in json else None,
            assigned_slot=BackendNode.from_json(json['assignedSlot']) if 'assignedSlot' in json else None,
            is_scrollable=bool(json['isScrollable']) if 'isScrollable' in json else None,
        )


@dataclass
class DetachedElementInfo:
    '''
    A structure to hold the top-level node of a detached tree and an array of its retained descendants.
    '''
    tree_node: Node

    retained_node_ids: typing.List[NodeId]

    def to_json(self):
        json = dict()
        json['treeNode'] = self.tree_node.to_json()
        json['retainedNodeIds'] = [i.to_json() for i in self.retained_node_ids]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            tree_node=Node.from_json(json['treeNode']),
            retained_node_ids=[NodeId.from_json(i) for i in json['retainedNodeIds']],
        )


@dataclass
class RGBA:
    '''
    A structure holding an RGBA color.
    '''
    #: The red component, in the [0-255] range.
    r: int

    #: The green component, in the [0-255] range.
    g: int

    #: The blue component, in the [0-255] range.
    b: int

    #: The alpha component, in the [0-1] range (default: 1).
    a: typing.Optional[float] = None

    def to_json(self):
        json = dict()
        json['r'] = self.r
        json['g'] = self.g
        json['b'] = self.b
        if self.a is not None:
            json['a'] = self.a
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            r=int(json['r']),
            g=int(json['g']),
            b=int(json['b']),
            a=float(json['a']) if 'a' in json else None,
        )


class Quad(list):
    '''
    An array of quad vertices, x immediately followed by y for each point, points clock-wise.
    '''
    def to_json(self) -> typing.List[float]:
        return self

    @classmethod
    def from_json(cls, json: typing.List[float]) -> Quad:
        return cls(json)

    def __repr__(self):
        return 'Quad({})'.format(super().__repr__())


@dataclass
class BoxModel:
    '''
    Box model.
    '''
    #: Content box
    content: Quad

    #: Padding box
    padding: Quad

    #: Border box
    border: Quad

    #: Margin box
    margin: Quad

    #: Node width
    width: int

    #: Node height
    height: int

    #: Shape outside coordinates
    shape_outside: typing.Optional[ShapeOutsideInfo] = None

    def to_json(self):
        json = dict()
        json['content'] = self.content.to_json()
        json['padding'] = self.padding.to_json()
        json['border'] = self.border.to_json()
        json['margin'] = self.margin.to_json()
        json['width'] = self.width
        json['height'] = self.height
        if self.shape_outside is not None:
            json['shapeOutside'] = self.shape_outside.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            content=Quad.from_json(json['content']),
            padding=Quad.from_json(json['padding']),
            border=Quad.from_json(json['border']),
            margin=Quad.from_json(json['margin']),
            width=int(json['width']),
            height=int(json['height']),
            shape_outside=ShapeOutsideInfo.from_json(json['shapeOutside']) if 'shapeOutside' in json else None,
        )


@dataclass
class ShapeOutsideInfo:
    '''
    CSS Shape Outside details.
    '''
    #: Shape bounds
    bounds: Quad

    #: Shape coordinate details
    shape: typing.List[typing.Any]

    #: Margin shape bounds
    margin_shape: typing.List[typing.Any]

    def to_json(self):
        json = dict()
        json['bounds'] = self.bounds.to_json()
        json['shape'] = [i for i in self.shape]
        json['marginShape'] = [i for i in self.margin_shape]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            bounds=Quad.from_json(json['bounds']),
            shape=[i for i in json['shape']],
            margin_shape=[i for i in json['marginShape']],
        )


@dataclass
class Rect:
    '''
    Rectangle.
    '''
    #: X coordinate
    x: float

    #: Y coordinate
    y: float

    #: Rectangle width
    width: float

    #: Rectangle height
    height: float

    def to_json(self):
        json = dict()
        json['x'] = self.x
        json['y'] = self.y
        json['width'] = self.width
        json['height'] = self.height
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            x=float(json['x']),
            y=float(json['y']),
            width=float(json['width']),
            height=float(json['height']),
        )


@dataclass
class CSSComputedStyleProperty:
    #: Computed style property name.
    name: str

    #: Computed style property value.
    value: str

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['value'] = self.value
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            value=str(json['value']),
        )


def collect_class_names_from_subtree(
        node_id: NodeId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[str]]:
    '''
    Collects class names for the node with given id and all of it's child nodes.

    **EXPERIMENTAL**

    :param node_id: Id of the node to collect class names.
    :returns: Class name list.
    '''
    params: T_JSON_DICT = dict()
    params['nodeId'] = node_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.collectClassNamesFromSubtree',
        'params': params,
    }
    json = yield cmd_dict
    return [str(i) for i in json['classNames']]


def copy_to(
        node_id: NodeId,
        target_node_id: NodeId,
        insert_before_node_id: typing.Optional[NodeId] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,NodeId]:
    '''
    Creates a deep copy of the specified node and places it into the target container before the
    given anchor.

    **EXPERIMENTAL**

    :param node_id: Id of the node to copy.
    :param target_node_id: Id of the element to drop the copy into.
    :param insert_before_node_id: *(Optional)* Drop the copy before this node (if absent, the copy becomes the last child of ```targetNodeId```).
    :returns: Id of the node clone.
    '''
    params: T_JSON_DICT = dict()
    params['nodeId'] = node_id.to_json()
    params['targetNodeId'] = target_node_id.to_json()
    if insert_before_node_id is not None:
        params['insertBeforeNodeId'] = insert_before_node_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.copyTo',
        'params': params,
    }
    json = yield cmd_dict
    return NodeId.from_json(json['nodeId'])


def describe_node(
        node_id: typing.Optional[NodeId] = None,
        backend_node_id: typing.Optional[BackendNodeId] = None,
        object_id: typing.Optional[runtime.RemoteObjectId] = None,
        depth: typing.Optional[int] = None,
        pierce: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,Node]:
    '''
    Describes node given its id, does not require domain to be enabled. Does not start tracking any
    objects, can be used for automation.

    :param node_id: *(Optional)* Identifier of the node.
    :param backend_node_id: *(Optional)* Identifier of the backend node.
    :param object_id: *(Optional)* JavaScript object id of the node wrapper.
    :param depth: *(Optional)* The maximum depth at which children should be retrieved, defaults to 1. Use -1 for the entire subtree or provide an integer larger than 0.
    :param pierce: *(Optional)* Whether or not iframes and shadow roots should be traversed when returning the subtree (default is false).
    :returns: Node description.
    '''
    params: T_JSON_DICT = dict()
    if node_id is not None:
        params['nodeId'] = node_id.to_json()
    if backend_node_id is not None:
        params['backendNodeId'] = backend_node_id.to_json()
    if object_id is not None:
        params['objectId'] = object_id.to_json()
    if depth is not None:
        params['depth'] = depth
    if pierce is not None:
        params['pierce'] = pierce
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.describeNode',
        'params': params,
    }
    json = yield cmd_dict
    return Node.from_json(json['node'])


def scroll_into_view_if_needed(
        node_id: typing.Optional[NodeId] = None,
        backend_node_id: typing.Optional[BackendNodeId] = None,
        object_id: typing.Optional[runtime.RemoteObjectId] = None,
        rect: typing.Optional[Rect] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Scrolls the specified rect of the given node into view if not already visible.
    Note: exactly one between nodeId, backendNodeId and objectId should be passed
    to identify the node.

    :param node_id: *(Optional)* Identifier of the node.
    :param backend_node_id: *(Optional)* Identifier of the backend node.
    :param object_id: *(Optional)* JavaScript object id of the node wrapper.
    :param rect: *(Optional)* The rect to be scrolled into view, relative to the node's border box, in CSS pixels. When omitted, center of the node will be used, similar to Element.scrollIntoView.
    '''
    params: T_JSON_DICT = dict()
    if node_id is not None:
        params['nodeId'] = node_id.to_json()
    if backend_node_id is not None:
        params['backendNodeId'] = backend_node_id.to_json()
    if object_id is not None:
        params['objectId'] = object_id.to_json()
    if rect is not None:
        params['rect'] = rect.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.scrollIntoViewIfNeeded',
        'params': params,
    }
    json = yield cmd_dict


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables DOM agent for the given page.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.disable',
    }
    json = yield cmd_dict


def discard_search_results(
        search_id: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Discards search results from the session with the given id. ``getSearchResults`` should no longer
    be called for that search.

    **EXPERIMENTAL**

    :param search_id: Unique search session identifier.
    '''
    params: T_JSON_DICT = dict()
    params['searchId'] = search_id
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.discardSearchResults',
        'params': params,
    }
    json = yield cmd_dict


def enable(
        include_whitespace: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables DOM agent for the given page.

    :param include_whitespace: **(EXPERIMENTAL)** *(Optional)* Whether to include whitespaces in the children array of returned Nodes.
    '''
    params: T_JSON_DICT = dict()
    if include_whitespace is not None:
        params['includeWhitespace'] = include_whitespace
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.enable',
        'params': params,
    }
    json = yield cmd_dict


def focus(
        node_id: typing.Optional[NodeId] = None,
        backend_node_id: typing.Optional[BackendNodeId] = None,
        object_id: typing.Optional[runtime.RemoteObjectId] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Focuses the given element.

    :param node_id: *(Optional)* Identifier of the node.
    :param backend_node_id: *(Optional)* Identifier of the backend node.
    :param object_id: *(Optional)* JavaScript object id of the node wrapper.
    '''
    params: T_JSON_DICT = dict()
    if node_id is not None:
        params['nodeId'] = node_id.to_json()
    if backend_node_id is not None:
        params['backendNodeId'] = backend_node_id.to_json()
    if object_id is not None:
        params['objectId'] = object_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.focus',
        'params': params,
    }
    json = yield cmd_dict


def get_attributes(
        node_id: NodeId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[str]]:
    '''
    Returns attributes for the specified node.

    :param node_id: Id of the node to retrieve attributes for.
    :returns: An interleaved array of node attribute names and values.
    '''
    params: T_JSON_DICT = dict()
    params['nodeId'] = node_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.getAttributes',
        'params': params,
    }
    json = yield cmd_dict
    return [str(i) for i in json['attributes']]


def get_box_model(
        node_id: typing.Optional[NodeId] = None,
        backend_node_id: typing.Optional[BackendNodeId] = None,
        object_id: typing.Optional[runtime.RemoteObjectId] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,BoxModel]:
    '''
    Returns boxes for the given node.

    :param node_id: *(Optional)* Identifier of the node.
    :param backend_node_id: *(Optional)* Identifier of the backend node.
    :param object_id: *(Optional)* JavaScript object id of the node wrapper.
    :returns: Box model for the node.
    '''
    params: T_JSON_DICT = dict()
    if node_id is not None:
        params['nodeId'] = node_id.to_json()
    if backend_node_id is not None:
        params['backendNodeId'] = backend_node_id.to_json()
    if object_id is not None:
        params['objectId'] = object_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.getBoxModel',
        'params': params,
    }
    json = yield cmd_dict
    return BoxModel.from_json(json['model'])


def get_content_quads(
        node_id: typing.Optional[NodeId] = None,
        backend_node_id: typing.Optional[BackendNodeId] = None,
        object_id: typing.Optional[runtime.RemoteObjectId] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[Quad]]:
    '''
    Returns quads that describe node position on the page. This method
    might return multiple quads for inline nodes.

    **EXPERIMENTAL**

    :param node_id: *(Optional)* Identifier of the node.
    :param backend_node_id: *(Optional)* Identifier of the backend node.
    :param object_id: *(Optional)* JavaScript object id of the node wrapper.
    :returns: Quads that describe node layout relative to viewport.
    '''
    params: T_JSON_DICT = dict()
    if node_id is not None:
        params['nodeId'] = node_id.to_json()
    if backend_node_id is not None:
        params['backendNodeId'] = backend_node_id.to_json()
    if object_id is not None:
        params['objectId'] = object_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.getContentQuads',
        'params': params,
    }
    json = yield cmd_dict
    return [Quad.from_json(i) for i in json['quads']]


def get_document(
        depth: typing.Optional[int] = None,
        pierce: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,Node]:
    '''
    Returns the root DOM node (and optionally the subtree) to the caller.
    Implicitly enables the DOM domain events for the current target.

    :param depth: *(Optional)* The maximum depth at which children should be retrieved, defaults to 1. Use -1 for the entire subtree or provide an integer larger than 0.
    :param pierce: *(Optional)* Whether or not iframes and shadow roots should be traversed when returning the subtree (default is false).
    :returns: Resulting node.
    '''
    params: T_JSON_DICT = dict()
    if depth is not None:
        params['depth'] = depth
    if pierce is not None:
        params['pierce'] = pierce
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.getDocument',
        'params': params,
    }
    json = yield cmd_dict
    return Node.from_json(json['root'])


def get_flattened_document(
        depth: typing.Optional[int] = None,
        pierce: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[Node]]:
    '''
    Returns the root DOM node (and optionally the subtree) to the caller.
    Deprecated, as it is not designed to work well with the rest of the DOM agent.
    Use DOMSnapshot.captureSnapshot instead.

    :param depth: *(Optional)* The maximum depth at which children should be retrieved, defaults to 1. Use -1 for the entire subtree or provide an integer larger than 0.
    :param pierce: *(Optional)* Whether or not iframes and shadow roots should be traversed when returning the subtree (default is false).
    :returns: Resulting node.
    '''
    params: T_JSON_DICT = dict()
    if depth is not None:
        params['depth'] = depth
    if pierce is not None:
        params['pierce'] = pierce
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.getFlattenedDocument',
        'params': params,
    }
    json = yield cmd_dict
    return [Node.from_json(i) for i in json['nodes']]


def get_nodes_for_subtree_by_style(
        node_id: NodeId,
        computed_styles: typing.List[CSSComputedStyleProperty],
        pierce: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[NodeId]]:
    '''
    Finds nodes with a given computed style in a subtree.

    **EXPERIMENTAL**

    :param node_id: Node ID pointing to the root of a subtree.
    :param computed_styles: The style to filter nodes by (includes nodes if any of properties matches).
    :param pierce: *(Optional)* Whether or not iframes and shadow roots in the same target should be traversed when returning the results (default is false).
    :returns: Resulting nodes.
    '''
    params: T_JSON_DICT = dict()
    params['nodeId'] = node_id.to_json()
    params['computedStyles'] = [i.to_json() for i in computed_styles]
    if pierce is not None:
        params['pierce'] = pierce
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.getNodesForSubtreeByStyle',
        'params': params,
    }
    json = yield cmd_dict
    return [NodeId.from_json(i) for i in json['nodeIds']]


def get_node_for_location(
        x: int,
        y: int,
        include_user_agent_shadow_dom: typing.Optional[bool] = None,
        ignore_pointer_events_none: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[BackendNodeId, page.FrameId, typing.Optional[NodeId]]]:
    '''
    Returns node id at given location. Depending on whether DOM domain is enabled, nodeId is
    either returned or not.

    :param x: X coordinate.
    :param y: Y coordinate.
    :param include_user_agent_shadow_dom: *(Optional)* False to skip to the nearest non-UA shadow root ancestor (default: false).
    :param ignore_pointer_events_none: *(Optional)* Whether to ignore pointer-events: none on elements and hit test them.
    :returns: A tuple with the following items:

        0. **backendNodeId** - Resulting node.
        1. **frameId** - Frame this node belongs to.
        2. **nodeId** - *(Optional)* Id of the node at given coordinates, only when enabled and requested document.
    '''
    params: T_JSON_DICT = dict()
    params['x'] = x
    params['y'] = y
    if include_user_agent_shadow_dom is not None:
        params['includeUserAgentShadowDOM'] = include_user_agent_shadow_dom
    if ignore_pointer_events_none is not None:
        params['ignorePointerEventsNone'] = ignore_pointer_events_none
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.getNodeForLocation',
        'params': params,
    }
    json = yield cmd_dict
    return (
        BackendNodeId.from_json(json['backendNodeId']),
        page.FrameId.from_json(json['frameId']),
        NodeId.from_json(json['nodeId']) if 'nodeId' in json else None
    )


def get_outer_html(
        node_id: typing.Optional[NodeId] = None,
        backend_node_id: typing.Optional[BackendNodeId] = None,
        object_id: typing.Optional[runtime.RemoteObjectId] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,str]:
    '''
    Returns node's HTML markup.

    :param node_id: *(Optional)* Identifier of the node.
    :param backend_node_id: *(Optional)* Identifier of the backend node.
    :param object_id: *(Optional)* JavaScript object id of the node wrapper.
    :returns: Outer HTML markup.
    '''
    params: T_JSON_DICT = dict()
    if node_id is not None:
        params['nodeId'] = node_id.to_json()
    if backend_node_id is not None:
        params['backendNodeId'] = backend_node_id.to_json()
    if object_id is not None:
        params['objectId'] = object_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.getOuterHTML',
        'params': params,
    }
    json = yield cmd_dict
    return str(json['outerHTML'])


def get_relayout_boundary(
        node_id: NodeId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,NodeId]:
    '''
    Returns the id of the nearest ancestor that is a relayout boundary.

    **EXPERIMENTAL**

    :param node_id: Id of the node.
    :returns: Relayout boundary node id for the given node.
    '''
    params: T_JSON_DICT = dict()
    params['nodeId'] = node_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.getRelayoutBoundary',
        'params': params,
    }
    json = yield cmd_dict
    return NodeId.from_json(json['nodeId'])


def get_search_results(
        search_id: str,
        from_index: int,
        to_index: int
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[NodeId]]:
    '''
    Returns search results from given ``fromIndex`` to given ``toIndex`` from the search with the given
    identifier.

    **EXPERIMENTAL**

    :param search_id: Unique search session identifier.
    :param from_index: Start index of the search result to be returned.
    :param to_index: End index of the search result to be returned.
    :returns: Ids of the search result nodes.
    '''
    params: T_JSON_DICT = dict()
    params['searchId'] = search_id
    params['fromIndex'] = from_index
    params['toIndex'] = to_index
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.getSearchResults',
        'params': params,
    }
    json = yield cmd_dict
    return [NodeId.from_json(i) for i in json['nodeIds']]


def hide_highlight() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Hides any highlight.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.hideHighlight',
    }
    json = yield cmd_dict


def highlight_node() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Highlights DOM node.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.highlightNode',
    }
    json = yield cmd_dict


def highlight_rect() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Highlights given rectangle.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.highlightRect',
    }
    json = yield cmd_dict


def mark_undoable_state() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Marks last undoable state.

    **EXPERIMENTAL**
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.markUndoableState',
    }
    json = yield cmd_dict


def move_to(
        node_id: NodeId,
        target_node_id: NodeId,
        insert_before_node_id: typing.Optional[NodeId] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,NodeId]:
    '''
    Moves node into the new container, places it before the given anchor.

    :param node_id: Id of the node to move.
    :param target_node_id: Id of the element to drop the moved node into.
    :param insert_before_node_id: *(Optional)* Drop node before this one (if absent, the moved node becomes the last child of ```targetNodeId```).
    :returns: New id of the moved node.
    '''
    params: T_JSON_DICT = dict()
    params['nodeId'] = node_id.to_json()
    params['targetNodeId'] = target_node_id.to_json()
    if insert_before_node_id is not None:
        params['insertBeforeNodeId'] = insert_before_node_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.moveTo',
        'params': params,
    }
    json = yield cmd_dict
    return NodeId.from_json(json['nodeId'])


def perform_search(
        query: str,
        include_user_agent_shadow_dom: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[str, int]]:
    '''
    Searches for a given string in the DOM tree. Use ``getSearchResults`` to access search results or
    ``cancelSearch`` to end this search session.

    **EXPERIMENTAL**

    :param query: Plain text or query selector or XPath search query.
    :param include_user_agent_shadow_dom: *(Optional)* True to search in user agent shadow DOM.
    :returns: A tuple with the following items:

        0. **searchId** - Unique search session identifier.
        1. **resultCount** - Number of search results.
    '''
    params: T_JSON_DICT = dict()
    params['query'] = query
    if include_user_agent_shadow_dom is not None:
        params['includeUserAgentShadowDOM'] = include_user_agent_shadow_dom
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.performSearch',
        'params': params,
    }
    json = yield cmd_dict
    return (
        str(json['searchId']),
        int(json['resultCount'])
    )


def push_node_by_path_to_frontend(
        path: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,NodeId]:
    '''
    Requests that the node is sent to the caller given its path. // FIXME, use XPath

    **EXPERIMENTAL**

    :param path: Path to node in the proprietary format.
    :returns: Id of the node for given path.
    '''
    params: T_JSON_DICT = dict()
    params['path'] = path
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.pushNodeByPathToFrontend',
        'params': params,
    }
    json = yield cmd_dict
    return NodeId.from_json(json['nodeId'])


def push_nodes_by_backend_ids_to_frontend(
        backend_node_ids: typing.List[BackendNodeId]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[NodeId]]:
    '''
    Requests that a batch of nodes is sent to the caller given their backend node ids.

    **EXPERIMENTAL**

    :param backend_node_ids: The array of backend node ids.
    :returns: The array of ids of pushed nodes that correspond to the backend ids specified in backendNodeIds.
    '''
    params: T_JSON_DICT = dict()
    params['backendNodeIds'] = [i.to_json() for i in backend_node_ids]
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.pushNodesByBackendIdsToFrontend',
        'params': params,
    }
    json = yield cmd_dict
    return [NodeId.from_json(i) for i in json['nodeIds']]


def query_selector(
        node_id: NodeId,
        selector: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,NodeId]:
    '''
    Executes ``querySelector`` on a given node.

    :param node_id: Id of the node to query upon.
    :param selector: Selector string.
    :returns: Query selector result.
    '''
    params: T_JSON_DICT = dict()
    params['nodeId'] = node_id.to_json()
    params['selector'] = selector
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.querySelector',
        'params': params,
    }
    json = yield cmd_dict
    return NodeId.from_json(json['nodeId'])


def query_selector_all(
        node_id: NodeId,
        selector: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[NodeId]]:
    '''
    Executes ``querySelectorAll`` on a given node.

    :param node_id: Id of the node to query upon.
    :param selector: Selector string.
    :returns: Query selector result.
    '''
    params: T_JSON_DICT = dict()
    params['nodeId'] = node_id.to_json()
    params['selector'] = selector
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.querySelectorAll',
        'params': params,
    }
    json = yield cmd_dict
    return [NodeId.from_json(i) for i in json['nodeIds']]


def get_top_layer_elements() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[NodeId]]:
    '''
    Returns NodeIds of current top layer elements.
    Top layer is rendered closest to the user within a viewport, therefore its elements always
    appear on top of all other content.

    **EXPERIMENTAL**

    :returns: NodeIds of top layer elements
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.getTopLayerElements',
    }
    json = yield cmd_dict
    return [NodeId.from_json(i) for i in json['nodeIds']]


def get_element_by_relation(
        node_id: NodeId,
        relation: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,NodeId]:
    '''
    Returns the NodeId of the matched element according to certain relations.

    **EXPERIMENTAL**

    :param node_id: Id of the node from which to query the relation.
    :param relation: Type of relation to get.
    :returns: NodeId of the element matching the queried relation.
    '''
    params: T_JSON_DICT = dict()
    params['nodeId'] = node_id.to_json()
    params['relation'] = relation
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.getElementByRelation',
        'params': params,
    }
    json = yield cmd_dict
    return NodeId.from_json(json['nodeId'])


def redo() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Re-does the last undone action.

    **EXPERIMENTAL**
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.redo',
    }
    json = yield cmd_dict


def remove_attribute(
        node_id: NodeId,
        name: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Removes attribute with given name from an element with given id.

    :param node_id: Id of the element to remove attribute from.
    :param name: Name of the attribute to remove.
    '''
    params: T_JSON_DICT = dict()
    params['nodeId'] = node_id.to_json()
    params['name'] = name
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.removeAttribute',
        'params': params,
    }
    json = yield cmd_dict


def remove_node(
        node_id: NodeId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Removes node with given id.

    :param node_id: Id of the node to remove.
    '''
    params: T_JSON_DICT = dict()
    params['nodeId'] = node_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.removeNode',
        'params': params,
    }
    json = yield cmd_dict


def request_child_nodes(
        node_id: NodeId,
        depth: typing.Optional[int] = None,
        pierce: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Requests that children of the node with given id are returned to the caller in form of
    ``setChildNodes`` events where not only immediate children are retrieved, but all children down to
    the specified depth.

    :param node_id: Id of the node to get children for.
    :param depth: *(Optional)* The maximum depth at which children should be retrieved, defaults to 1. Use -1 for the entire subtree or provide an integer larger than 0.
    :param pierce: *(Optional)* Whether or not iframes and shadow roots should be traversed when returning the sub-tree (default is false).
    '''
    params: T_JSON_DICT = dict()
    params['nodeId'] = node_id.to_json()
    if depth is not None:
        params['depth'] = depth
    if pierce is not None:
        params['pierce'] = pierce
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.requestChildNodes',
        'params': params,
    }
    json = yield cmd_dict


def request_node(
        object_id: runtime.RemoteObjectId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,NodeId]:
    '''
    Requests that the node is sent to the caller given the JavaScript node object reference. All
    nodes that form the path from the node to the root are also sent to the client as a series of
    ``setChildNodes`` notifications.

    :param object_id: JavaScript object id to convert into node.
    :returns: Node id for given object.
    '''
    params: T_JSON_DICT = dict()
    params['objectId'] = object_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.requestNode',
        'params': params,
    }
    json = yield cmd_dict
    return NodeId.from_json(json['nodeId'])


def resolve_node(
        node_id: typing.Optional[NodeId] = None,
        backend_node_id: typing.Optional[BackendNodeId] = None,
        object_group: typing.Optional[str] = None,
        execution_context_id: typing.Optional[runtime.ExecutionContextId] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,runtime.RemoteObject]:
    '''
    Resolves the JavaScript node object for a given NodeId or BackendNodeId.

    :param node_id: *(Optional)* Id of the node to resolve.
    :param backend_node_id: *(Optional)* Backend identifier of the node to resolve.
    :param object_group: *(Optional)* Symbolic group name that can be used to release multiple objects.
    :param execution_context_id: *(Optional)* Execution context in which to resolve the node.
    :returns: JavaScript object wrapper for given node.
    '''
    params: T_JSON_DICT = dict()
    if node_id is not None:
        params['nodeId'] = node_id.to_json()
    if backend_node_id is not None:
        params['backendNodeId'] = backend_node_id.to_json()
    if object_group is not None:
        params['objectGroup'] = object_group
    if execution_context_id is not None:
        params['executionContextId'] = execution_context_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.resolveNode',
        'params': params,
    }
    json = yield cmd_dict
    return runtime.RemoteObject.from_json(json['object'])


def set_attribute_value(
        node_id: NodeId,
        name: str,
        value: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets attribute for an element with given id.

    :param node_id: Id of the element to set attribute for.
    :param name: Attribute name.
    :param value: Attribute value.
    '''
    params: T_JSON_DICT = dict()
    params['nodeId'] = node_id.to_json()
    params['name'] = name
    params['value'] = value
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.setAttributeValue',
        'params': params,
    }
    json = yield cmd_dict


def set_attributes_as_text(
        node_id: NodeId,
        text: str,
        name: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets attributes on element with given id. This method is useful when user edits some existing
    attribute value and types in several attribute name/value pairs.

    :param node_id: Id of the element to set attributes for.
    :param text: Text with a number of attributes. Will parse this text using HTML parser.
    :param name: *(Optional)* Attribute name to replace with new attributes derived from text in case text parsed successfully.
    '''
    params: T_JSON_DICT = dict()
    params['nodeId'] = node_id.to_json()
    params['text'] = text
    if name is not None:
        params['name'] = name
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.setAttributesAsText',
        'params': params,
    }
    json = yield cmd_dict


def set_file_input_files(
        files: typing.List[str],
        node_id: typing.Optional[NodeId] = None,
        backend_node_id: typing.Optional[BackendNodeId] = None,
        object_id: typing.Optional[runtime.RemoteObjectId] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets files for the given file input element.

    :param files: Array of file paths to set.
    :param node_id: *(Optional)* Identifier of the node.
    :param backend_node_id: *(Optional)* Identifier of the backend node.
    :param object_id: *(Optional)* JavaScript object id of the node wrapper.
    '''
    params: T_JSON_DICT = dict()
    params['files'] = [i for i in files]
    if node_id is not None:
        params['nodeId'] = node_id.to_json()
    if backend_node_id is not None:
        params['backendNodeId'] = backend_node_id.to_json()
    if object_id is not None:
        params['objectId'] = object_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.setFileInputFiles',
        'params': params,
    }
    json = yield cmd_dict


def set_node_stack_traces_enabled(
        enable: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets if stack traces should be captured for Nodes. See ``Node.getNodeStackTraces``. Default is disabled.

    **EXPERIMENTAL**

    :param enable: Enable or disable.
    '''
    params: T_JSON_DICT = dict()
    params['enable'] = enable
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.setNodeStackTracesEnabled',
        'params': params,
    }
    json = yield cmd_dict


def get_node_stack_traces(
        node_id: NodeId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Optional[runtime.StackTrace]]:
    '''
    Gets stack traces associated with a Node. As of now, only provides stack trace for Node creation.

    **EXPERIMENTAL**

    :param node_id: Id of the node to get stack traces for.
    :returns: *(Optional)* Creation stack trace, if available.
    '''
    params: T_JSON_DICT = dict()
    params['nodeId'] = node_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.getNodeStackTraces',
        'params': params,
    }
    json = yield cmd_dict
    return runtime.StackTrace.from_json(json['creation']) if 'creation' in json else None


def get_file_info(
        object_id: runtime.RemoteObjectId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,str]:
    '''
    Returns file information for the given
    File wrapper.

    **EXPERIMENTAL**

    :param object_id: JavaScript object id of the node wrapper.
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['objectId'] = object_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.getFileInfo',
        'params': params,
    }
    json = yield cmd_dict
    return str(json['path'])


def get_detached_dom_nodes() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[DetachedElementInfo]]:
    '''
    Returns list of detached nodes

    **EXPERIMENTAL**

    :returns: The list of detached nodes
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.getDetachedDomNodes',
    }
    json = yield cmd_dict
    return [DetachedElementInfo.from_json(i) for i in json['detachedNodes']]


def set_inspected_node(
        node_id: NodeId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables console to refer to the node with given id via $x (see Command Line API for more details
    $x functions).

    **EXPERIMENTAL**

    :param node_id: DOM node id to be accessible by means of $x command line API.
    '''
    params: T_JSON_DICT = dict()
    params['nodeId'] = node_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.setInspectedNode',
        'params': params,
    }
    json = yield cmd_dict


def set_node_name(
        node_id: NodeId,
        name: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,NodeId]:
    '''
    Sets node name for a node with given id.

    :param node_id: Id of the node to set name for.
    :param name: New node's name.
    :returns: New node's id.
    '''
    params: T_JSON_DICT = dict()
    params['nodeId'] = node_id.to_json()
    params['name'] = name
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.setNodeName',
        'params': params,
    }
    json = yield cmd_dict
    return NodeId.from_json(json['nodeId'])


def set_node_value(
        node_id: NodeId,
        value: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets node value for a node with given id.

    :param node_id: Id of the node to set value for.
    :param value: New node's value.
    '''
    params: T_JSON_DICT = dict()
    params['nodeId'] = node_id.to_json()
    params['value'] = value
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.setNodeValue',
        'params': params,
    }
    json = yield cmd_dict


def set_outer_html(
        node_id: NodeId,
        outer_html: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets node HTML markup, returns new node id.

    :param node_id: Id of the node to set markup for.
    :param outer_html: Outer HTML markup to set.
    '''
    params: T_JSON_DICT = dict()
    params['nodeId'] = node_id.to_json()
    params['outerHTML'] = outer_html
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.setOuterHTML',
        'params': params,
    }
    json = yield cmd_dict


def undo() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Undoes the last performed action.

    **EXPERIMENTAL**
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.undo',
    }
    json = yield cmd_dict


def get_frame_owner(
        frame_id: page.FrameId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[BackendNodeId, typing.Optional[NodeId]]]:
    '''
    Returns iframe node that owns iframe with the given domain.

    **EXPERIMENTAL**

    :param frame_id:
    :returns: A tuple with the following items:

        0. **backendNodeId** - Resulting node.
        1. **nodeId** - *(Optional)* Id of the node at given coordinates, only when enabled and requested document.
    '''
    params: T_JSON_DICT = dict()
    params['frameId'] = frame_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.getFrameOwner',
        'params': params,
    }
    json = yield cmd_dict
    return (
        BackendNodeId.from_json(json['backendNodeId']),
        NodeId.from_json(json['nodeId']) if 'nodeId' in json else None
    )


def get_container_for_node(
        node_id: NodeId,
        container_name: typing.Optional[str] = None,
        physical_axes: typing.Optional[PhysicalAxes] = None,
        logical_axes: typing.Optional[LogicalAxes] = None,
        queries_scroll_state: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Optional[NodeId]]:
    '''
    Returns the query container of the given node based on container query
    conditions: containerName, physical and logical axes, and whether it queries
    scroll-state. If no axes are provided and queriesScrollState is false, the
    style container is returned, which is the direct parent or the closest
    element with a matching container-name.

    **EXPERIMENTAL**

    :param node_id:
    :param container_name: *(Optional)*
    :param physical_axes: *(Optional)*
    :param logical_axes: *(Optional)*
    :param queries_scroll_state: *(Optional)*
    :returns: *(Optional)* The container node for the given node, or null if not found.
    '''
    params: T_JSON_DICT = dict()
    params['nodeId'] = node_id.to_json()
    if container_name is not None:
        params['containerName'] = container_name
    if physical_axes is not None:
        params['physicalAxes'] = physical_axes.to_json()
    if logical_axes is not None:
        params['logicalAxes'] = logical_axes.to_json()
    if queries_scroll_state is not None:
        params['queriesScrollState'] = queries_scroll_state
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.getContainerForNode',
        'params': params,
    }
    json = yield cmd_dict
    return NodeId.from_json(json['nodeId']) if 'nodeId' in json else None


def get_querying_descendants_for_container(
        node_id: NodeId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[NodeId]]:
    '''
    Returns the descendants of a container query container that have
    container queries against this container.

    **EXPERIMENTAL**

    :param node_id: Id of the container node to find querying descendants from.
    :returns: Descendant nodes with container queries against the given container.
    '''
    params: T_JSON_DICT = dict()
    params['nodeId'] = node_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.getQueryingDescendantsForContainer',
        'params': params,
    }
    json = yield cmd_dict
    return [NodeId.from_json(i) for i in json['nodeIds']]


def get_anchor_element(
        node_id: NodeId,
        anchor_specifier: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,NodeId]:
    '''
    Returns the target anchor element of the given anchor query according to
    https://www.w3.org/TR/css-anchor-position-1/#target.

    **EXPERIMENTAL**

    :param node_id: Id of the positioned element from which to find the anchor.
    :param anchor_specifier: *(Optional)* An optional anchor specifier, as defined in https://www.w3.org/TR/css-anchor-position-1/#anchor-specifier. If not provided, it will return the implicit anchor element for the given positioned element.
    :returns: The anchor element of the given anchor query.
    '''
    params: T_JSON_DICT = dict()
    params['nodeId'] = node_id.to_json()
    if anchor_specifier is not None:
        params['anchorSpecifier'] = anchor_specifier
    cmd_dict: T_JSON_DICT = {
        'method': 'DOM.getAnchorElement',
        'params': params,
    }
    json = yield cmd_dict
    return NodeId.from_json(json['nodeId'])


@event_class('DOM.attributeModified')
@dataclass
class AttributeModified:
    '''
    Fired when ``Element``'s attribute is modified.
    '''
    #: Id of the node that has changed.
    node_id: NodeId
    #: Attribute name.
    name: str
    #: Attribute value.
    value: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> AttributeModified:
        return cls(
            node_id=NodeId.from_json(json['nodeId']),
            name=str(json['name']),
            value=str(json['value'])
        )


@event_class('DOM.attributeRemoved')
@dataclass
class AttributeRemoved:
    '''
    Fired when ``Element``'s attribute is removed.
    '''
    #: Id of the node that has changed.
    node_id: NodeId
    #: A ttribute name.
    name: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> AttributeRemoved:
        return cls(
            node_id=NodeId.from_json(json['nodeId']),
            name=str(json['name'])
        )


@event_class('DOM.characterDataModified')
@dataclass
class CharacterDataModified:
    '''
    Mirrors ``DOMCharacterDataModified`` event.
    '''
    #: Id of the node that has changed.
    node_id: NodeId
    #: New text value.
    character_data: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> CharacterDataModified:
        return cls(
            node_id=NodeId.from_json(json['nodeId']),
            character_data=str(json['characterData'])
        )


@event_class('DOM.childNodeCountUpdated')
@dataclass
class ChildNodeCountUpdated:
    '''
    Fired when ``Container``'s child node count has changed.
    '''
    #: Id of the node that has changed.
    node_id: NodeId
    #: New node count.
    child_node_count: int

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ChildNodeCountUpdated:
        return cls(
            node_id=NodeId.from_json(json['nodeId']),
            child_node_count=int(json['childNodeCount'])
        )


@event_class('DOM.childNodeInserted')
@dataclass
class ChildNodeInserted:
    '''
    Mirrors ``DOMNodeInserted`` event.
    '''
    #: Id of the node that has changed.
    parent_node_id: NodeId
    #: Id of the previous sibling.
    previous_node_id: NodeId
    #: Inserted node data.
    node: Node

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ChildNodeInserted:
        return cls(
            parent_node_id=NodeId.from_json(json['parentNodeId']),
            previous_node_id=NodeId.from_json(json['previousNodeId']),
            node=Node.from_json(json['node'])
        )


@event_class('DOM.childNodeRemoved')
@dataclass
class ChildNodeRemoved:
    '''
    Mirrors ``DOMNodeRemoved`` event.
    '''
    #: Parent id.
    parent_node_id: NodeId
    #: Id of the node that has been removed.
    node_id: NodeId

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ChildNodeRemoved:
        return cls(
            parent_node_id=NodeId.from_json(json['parentNodeId']),
            node_id=NodeId.from_json(json['nodeId'])
        )


@event_class('DOM.distributedNodesUpdated')
@dataclass
class DistributedNodesUpdated:
    '''
    **EXPERIMENTAL**

    Called when distribution is changed.
    '''
    #: Insertion point where distributed nodes were updated.
    insertion_point_id: NodeId
    #: Distributed nodes for given insertion point.
    distributed_nodes: typing.List[BackendNode]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DistributedNodesUpdated:
        return cls(
            insertion_point_id=NodeId.from_json(json['insertionPointId']),
            distributed_nodes=[BackendNode.from_json(i) for i in json['distributedNodes']]
        )


@event_class('DOM.documentUpdated')
@dataclass
class DocumentUpdated:
    '''
    Fired when ``Document`` has been totally updated. Node ids are no longer valid.
    '''


    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DocumentUpdated:
        return cls(

        )


@event_class('DOM.inlineStyleInvalidated')
@dataclass
class InlineStyleInvalidated:
    '''
    **EXPERIMENTAL**

    Fired when ``Element``'s inline style is modified via a CSS property modification.
    '''
    #: Ids of the nodes for which the inline styles have been invalidated.
    node_ids: typing.List[NodeId]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> InlineStyleInvalidated:
        return cls(
            node_ids=[NodeId.from_json(i) for i in json['nodeIds']]
        )


@event_class('DOM.pseudoElementAdded')
@dataclass
class PseudoElementAdded:
    '''
    **EXPERIMENTAL**

    Called when a pseudo element is added to an element.
    '''
    #: Pseudo element's parent element id.
    parent_id: NodeId
    #: The added pseudo element.
    pseudo_element: Node

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> PseudoElementAdded:
        return cls(
            parent_id=NodeId.from_json(json['parentId']),
            pseudo_element=Node.from_json(json['pseudoElement'])
        )


@event_class('DOM.topLayerElementsUpdated')
@dataclass
class TopLayerElementsUpdated:
    '''
    **EXPERIMENTAL**

    Called when top layer elements are changed.
    '''


    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> TopLayerElementsUpdated:
        return cls(

        )


@event_class('DOM.scrollableFlagUpdated')
@dataclass
class ScrollableFlagUpdated:
    '''
    **EXPERIMENTAL**

    Fired when a node's scrollability state changes.
    '''
    #: The id of the node.
    node_id: dom.NodeId
    #: If the node is scrollable.
    is_scrollable: bool

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ScrollableFlagUpdated:
        return cls(
            node_id=dom.NodeId.from_json(json['nodeId']),
            is_scrollable=bool(json['isScrollable'])
        )


@event_class('DOM.pseudoElementRemoved')
@dataclass
class PseudoElementRemoved:
    '''
    **EXPERIMENTAL**

    Called when a pseudo element is removed from an element.
    '''
    #: Pseudo element's parent element id.
    parent_id: NodeId
    #: The removed pseudo element id.
    pseudo_element_id: NodeId

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> PseudoElementRemoved:
        return cls(
            parent_id=NodeId.from_json(json['parentId']),
            pseudo_element_id=NodeId.from_json(json['pseudoElementId'])
        )


@event_class('DOM.setChildNodes')
@dataclass
class SetChildNodes:
    '''
    Fired when backend wants to provide client with the missing DOM structure. This happens upon
    most of the calls requesting node ids.
    '''
    #: Parent node id to populate with children.
    parent_id: NodeId
    #: Child nodes array.
    nodes: typing.List[Node]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> SetChildNodes:
        return cls(
            parent_id=NodeId.from_json(json['parentId']),
            nodes=[Node.from_json(i) for i in json['nodes']]
        )


@event_class('DOM.shadowRootPopped')
@dataclass
class ShadowRootPopped:
    '''
    **EXPERIMENTAL**

    Called when shadow root is popped from the element.
    '''
    #: Host element id.
    host_id: NodeId
    #: Shadow root id.
    root_id: NodeId

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ShadowRootPopped:
        return cls(
            host_id=NodeId.from_json(json['hostId']),
            root_id=NodeId.from_json(json['rootId'])
        )


@event_class('DOM.shadowRootPushed')
@dataclass
class ShadowRootPushed:
    '''
    **EXPERIMENTAL**

    Called when shadow root is pushed into the element.
    '''
    #: Host element id.
    host_id: NodeId
    #: Shadow root.
    root: Node

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ShadowRootPushed:
        return cls(
            host_id=NodeId.from_json(json['hostId']),
            root=Node.from_json(json['root'])
        )