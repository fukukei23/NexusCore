
# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\wheel\macosx_libfile.py ===
"""
This module contains function to analyse dynamic library
headers to extract system information

Currently only for MacOSX

Library file on macosx system starts with Mach-O or Fat field.
This can be distinguish by first 32 bites and it is called magic number.
Proper value of magic number is with suffix _MAGIC. Suffix _CIGAM means
reversed bytes order.
Both fields can occur in two types: 32 and 64 bytes.

FAT field inform that this library contains few version of library
(typically for different types version). It contains
information where Mach-O headers starts.

Each section started with Mach-O header contains one library
(So if file starts with this field it contains only one version).

After filed Mach-O there are section fields.
Each of them starts with two fields:
cmd - magic number for this command
cmdsize - total size occupied by this section information.

In this case only sections LC_VERSION_MIN_MACOSX (for macosx 10.13 and earlier)
and LC_BUILD_VERSION (for macosx 10.14 and newer) are interesting,
because them contains information about minimal system version.

Important remarks:
- For fat files this implementation looks for maximum number version.
  It not check if it is 32 or 64 and do not compare it with currently built package.
  So it is possible to false report higher version that needed.
- All structures signatures are taken form macosx header files.
- I think that binary format will be more stable than `otool` output.
  and if apple introduce some changes both implementation will need to be updated.
- The system compile will set the deployment target no lower than
  11.0 for arm64 builds. For "Universal 2" builds use the x86_64 deployment
  target when the arm64 target is 11.0.
"""

from __future__ import annotations

import ctypes
import os
import sys
from io import BufferedIOBase
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Union

    StrPath = Union[str, os.PathLike[str]]

"""here the needed const and struct from mach-o header files"""

FAT_MAGIC = 0xCAFEBABE
FAT_CIGAM = 0xBEBAFECA
FAT_MAGIC_64 = 0xCAFEBABF
FAT_CIGAM_64 = 0xBFBAFECA
MH_MAGIC = 0xFEEDFACE
MH_CIGAM = 0xCEFAEDFE
MH_MAGIC_64 = 0xFEEDFACF
MH_CIGAM_64 = 0xCFFAEDFE

LC_VERSION_MIN_MACOSX = 0x24
LC_BUILD_VERSION = 0x32

CPU_TYPE_ARM64 = 0x0100000C

mach_header_fields = [
    ("magic", ctypes.c_uint32),
    ("cputype", ctypes.c_int),
    ("cpusubtype", ctypes.c_int),
    ("filetype", ctypes.c_uint32),
    ("ncmds", ctypes.c_uint32),
    ("sizeofcmds", ctypes.c_uint32),
    ("flags", ctypes.c_uint32),
]
"""
struct mach_header {
    uint32_t	magic;		/* mach magic number identifier */
    cpu_type_t	cputype;	/* cpu specifier */
    cpu_subtype_t	cpusubtype;	/* machine specifier */
    uint32_t	filetype;	/* type of file */
    uint32_t	ncmds;		/* number of load commands */
    uint32_t	sizeofcmds;	/* the size of all the load commands */
    uint32_t	flags;		/* flags */
};
typedef integer_t cpu_type_t;
typedef integer_t cpu_subtype_t;
"""

mach_header_fields_64 = mach_header_fields + [("reserved", ctypes.c_uint32)]
"""
struct mach_header_64 {
    uint32_t	magic;		/* mach magic number identifier */
    cpu_type_t	cputype;	/* cpu specifier */
    cpu_subtype_t	cpusubtype;	/* machine specifier */
    uint32_t	filetype;	/* type of file */
    uint32_t	ncmds;		/* number of load commands */
    uint32_t	sizeofcmds;	/* the size of all the load commands */
    uint32_t	flags;		/* flags */
    uint32_t	reserved;	/* reserved */
};
"""

fat_header_fields = [("magic", ctypes.c_uint32), ("nfat_arch", ctypes.c_uint32)]
"""
struct fat_header {
    uint32_t	magic;		/* FAT_MAGIC or FAT_MAGIC_64 */
    uint32_t	nfat_arch;	/* number of structs that follow */
};
"""

fat_arch_fields = [
    ("cputype", ctypes.c_int),
    ("cpusubtype", ctypes.c_int),
    ("offset", ctypes.c_uint32),
    ("size", ctypes.c_uint32),
    ("align", ctypes.c_uint32),
]
"""
struct fat_arch {
    cpu_type_t	cputype;	/* cpu specifier (int) */
    cpu_subtype_t	cpusubtype;	/* machine specifier (int) */
    uint32_t	offset;		/* file offset to this object file */
    uint32_t	size;		/* size of this object file */
    uint32_t	align;		/* alignment as a power of 2 */
};
"""

fat_arch_64_fields = [
    ("cputype", ctypes.c_int),
    ("cpusubtype", ctypes.c_int),
    ("offset", ctypes.c_uint64),
    ("size", ctypes.c_uint64),
    ("align", ctypes.c_uint32),
    ("reserved", ctypes.c_uint32),
]
"""
struct fat_arch_64 {
    cpu_type_t	cputype;	/* cpu specifier (int) */
    cpu_subtype_t	cpusubtype;	/* machine specifier (int) */
    uint64_t	offset;		/* file offset to this object file */
    uint64_t	size;		/* size of this object file */
    uint32_t	align;		/* alignment as a power of 2 */
    uint32_t	reserved;	/* reserved */
};
"""

segment_base_fields = [("cmd", ctypes.c_uint32), ("cmdsize", ctypes.c_uint32)]
"""base for reading segment info"""

segment_command_fields = [
    ("cmd", ctypes.c_uint32),
    ("cmdsize", ctypes.c_uint32),
    ("segname", ctypes.c_char * 16),
    ("vmaddr", ctypes.c_uint32),
    ("vmsize", ctypes.c_uint32),
    ("fileoff", ctypes.c_uint32),
    ("filesize", ctypes.c_uint32),
    ("maxprot", ctypes.c_int),
    ("initprot", ctypes.c_int),
    ("nsects", ctypes.c_uint32),
    ("flags", ctypes.c_uint32),
]
"""
struct segment_command { /* for 32-bit architectures */
    uint32_t	cmd;		/* LC_SEGMENT */
    uint32_t	cmdsize;	/* includes sizeof section structs */
    char		segname[16];	/* segment name */
    uint32_t	vmaddr;		/* memory address of this segment */
    uint32_t	vmsize;		/* memory size of this segment */
    uint32_t	fileoff;	/* file offset of this segment */
    uint32_t	filesize;	/* amount to map from the file */
    vm_prot_t	maxprot;	/* maximum VM protection */
    vm_prot_t	initprot;	/* initial VM protection */
    uint32_t	nsects;		/* number of sections in segment */
    uint32_t	flags;		/* flags */
};
typedef int vm_prot_t;
"""

segment_command_fields_64 = [
    ("cmd", ctypes.c_uint32),
    ("cmdsize", ctypes.c_uint32),
    ("segname", ctypes.c_char * 16),
    ("vmaddr", ctypes.c_uint64),
    ("vmsize", ctypes.c_uint64),
    ("fileoff", ctypes.c_uint64),
    ("filesize", ctypes.c_uint64),
    ("maxprot", ctypes.c_int),
    ("initprot", ctypes.c_int),
    ("nsects", ctypes.c_uint32),
    ("flags", ctypes.c_uint32),
]
"""
struct segment_command_64 { /* for 64-bit architectures */
    uint32_t	cmd;		/* LC_SEGMENT_64 */
    uint32_t	cmdsize;	/* includes sizeof section_64 structs */
    char		segname[16];	/* segment name */
    uint64_t	vmaddr;		/* memory address of this segment */
    uint64_t	vmsize;		/* memory size of this segment */
    uint64_t	fileoff;	/* file offset of this segment */
    uint64_t	filesize;	/* amount to map from the file */
    vm_prot_t	maxprot;	/* maximum VM protection */
    vm_prot_t	initprot;	/* initial VM protection */
    uint32_t	nsects;		/* number of sections in segment */
    uint32_t	flags;		/* flags */
};
"""

version_min_command_fields = segment_base_fields + [
    ("version", ctypes.c_uint32),
    ("sdk", ctypes.c_uint32),
]
"""
struct version_min_command {
    uint32_t	cmd;		/* LC_VERSION_MIN_MACOSX or
                               LC_VERSION_MIN_IPHONEOS or
                               LC_VERSION_MIN_WATCHOS or
                               LC_VERSION_MIN_TVOS */
    uint32_t	cmdsize;	/* sizeof(struct min_version_command) */
    uint32_t	version;	/* X.Y.Z is encoded in nibbles xxxx.yy.zz */
    uint32_t	sdk;		/* X.Y.Z is encoded in nibbles xxxx.yy.zz */
};
"""

build_version_command_fields = segment_base_fields + [
    ("platform", ctypes.c_uint32),
    ("minos", ctypes.c_uint32),
    ("sdk", ctypes.c_uint32),
    ("ntools", ctypes.c_uint32),
]
"""
struct build_version_command {
    uint32_t	cmd;		/* LC_BUILD_VERSION */
    uint32_t	cmdsize;	/* sizeof(struct build_version_command) plus */
                                /* ntools * sizeof(struct build_tool_version) */
    uint32_t	platform;	/* platform */
    uint32_t	minos;		/* X.Y.Z is encoded in nibbles xxxx.yy.zz */
    uint32_t	sdk;		/* X.Y.Z is encoded in nibbles xxxx.yy.zz */
    uint32_t	ntools;		/* number of tool entries following this */
};
"""


def swap32(x: int) -> int:
    return (
        ((x << 24) & 0xFF000000)
        | ((x << 8) & 0x00FF0000)
        | ((x >> 8) & 0x0000FF00)
        | ((x >> 24) & 0x000000FF)
    )


def get_base_class_and_magic_number(
    lib_file: BufferedIOBase,
    seek: int | None = None,
) -> tuple[type[ctypes.Structure], int]:
    if seek is None:
        seek = lib_file.tell()
    else:
        lib_file.seek(seek)
    magic_number = ctypes.c_uint32.from_buffer_copy(
        lib_file.read(ctypes.sizeof(ctypes.c_uint32))
    ).value

    # Handle wrong byte order
    if magic_number in [FAT_CIGAM, FAT_CIGAM_64, MH_CIGAM, MH_CIGAM_64]:
        if sys.byteorder == "little":
            BaseClass = ctypes.BigEndianStructure
        else:
            BaseClass = ctypes.LittleEndianStructure

        magic_number = swap32(magic_number)
    else:
        BaseClass = ctypes.Structure

    lib_file.seek(seek)
    return BaseClass, magic_number


def read_data(struct_class: type[ctypes.Structure], lib_file: BufferedIOBase):
    return struct_class.from_buffer_copy(lib_file.read(ctypes.sizeof(struct_class)))


def extract_macosx_min_system_version(path_to_lib: str):
    with open(path_to_lib, "rb") as lib_file:
        BaseClass, magic_number = get_base_class_and_magic_number(lib_file, 0)
        if magic_number not in [FAT_MAGIC, FAT_MAGIC_64, MH_MAGIC, MH_MAGIC_64]:
            return

        if magic_number in [FAT_MAGIC, FAT_CIGAM_64]:

            class FatHeader(BaseClass):
                _fields_ = fat_header_fields

            fat_header = read_data(FatHeader, lib_file)
            if magic_number == FAT_MAGIC:

                class FatArch(BaseClass):
                    _fields_ = fat_arch_fields

            else:

                class FatArch(BaseClass):
                    _fields_ = fat_arch_64_fields

            fat_arch_list = [
                read_data(FatArch, lib_file) for _ in range(fat_header.nfat_arch)
            ]

            versions_list: list[tuple[int, int, int]] = []
            for el in fat_arch_list:
                try:
                    version = read_mach_header(lib_file, el.offset)
                    if version is not None:
                        if el.cputype == CPU_TYPE_ARM64 and len(fat_arch_list) != 1:
                            # Xcode will not set the deployment target below 11.0.0
                            # for the arm64 architecture. Ignore the arm64 deployment
                            # in fat binaries when the target is 11.0.0, that way
                            # the other architectures can select a lower deployment
                            # target.
                            # This is safe because there is no arm64 variant for
                            # macOS 10.15 or earlier.
                            if version == (11, 0, 0):
                                continue
                        versions_list.append(version)
                except ValueError:
                    pass

            if len(versions_list) > 0:
                return max(versions_list)
            else:
                return None

        else:
            try:
                return read_mach_header(lib_file, 0)
            except ValueError:
                """when some error during read library files"""
                return None


def read_mach_header(
    lib_file: BufferedIOBase,
    seek: int | None = None,
) -> tuple[int, int, int] | None:
    """
    This function parses a Mach-O header and extracts
    information about the minimal macOS version.

    :param lib_file: reference to opened library file with pointer
    """
    base_class, magic_number = get_base_class_and_magic_number(lib_file, seek)
    arch = "32" if magic_number == MH_MAGIC else "64"

    class SegmentBase(base_class):
        _fields_ = segment_base_fields

    if arch == "32":

        class MachHeader(base_class):
            _fields_ = mach_header_fields

    else:

        class MachHeader(base_class):
            _fields_ = mach_header_fields_64

    mach_header = read_data(MachHeader, lib_file)
    for _i in range(mach_header.ncmds):
        pos = lib_file.tell()
        segment_base = read_data(SegmentBase, lib_file)
        lib_file.seek(pos)
        if segment_base.cmd == LC_VERSION_MIN_MACOSX:

            class VersionMinCommand(base_class):
                _fields_ = version_min_command_fields

            version_info = read_data(VersionMinCommand, lib_file)
            return parse_version(version_info.version)
        elif segment_base.cmd == LC_BUILD_VERSION:

            class VersionBuild(base_class):
                _fields_ = build_version_command_fields

            version_info = read_data(VersionBuild, lib_file)
            return parse_version(version_info.minos)
        else:
            lib_file.seek(pos + segment_base.cmdsize)
            continue


def parse_version(version: int) -> tuple[int, int, int]:
    x = (version & 0xFFFF0000) >> 16
    y = (version & 0x0000FF00) >> 8
    z = version & 0x000000FF
    return x, y, z


def calculate_macosx_platform_tag(archive_root: StrPath, platform_tag: str) -> str:
    """
    Calculate proper macosx platform tag basing on files which are included to wheel

    Example platform tag `macosx-10.14-x86_64`
    """
    prefix, base_version, suffix = platform_tag.split("-")
    base_version = tuple(int(x) for x in base_version.split("."))
    base_version = base_version[:2]
    if base_version[0] > 10:
        base_version = (base_version[0], 0)
    assert len(base_version) == 2
    if "MACOSX_DEPLOYMENT_TARGET" in os.environ:
        deploy_target = tuple(
            int(x) for x in os.environ["MACOSX_DEPLOYMENT_TARGET"].split(".")
        )
        deploy_target = deploy_target[:2]
        if deploy_target[0] > 10:
            deploy_target = (deploy_target[0], 0)
        if deploy_target < base_version:
            sys.stderr.write(
                "[WARNING] MACOSX_DEPLOYMENT_TARGET is set to a lower value ({}) than "
                "the version on which the Python interpreter was compiled ({}), and "
                "will be ignored.\n".format(
                    ".".join(str(x) for x in deploy_target),
                    ".".join(str(x) for x in base_version),
                )
            )
        else:
            base_version = deploy_target

    assert len(base_version) == 2
    start_version = base_version
    versions_dict: dict[str, tuple[int, int]] = {}
    for dirpath, _dirnames, filenames in os.walk(archive_root):
        for filename in filenames:
            if filename.endswith(".dylib") or filename.endswith(".so"):
                lib_path = os.path.join(dirpath, filename)
                min_ver = extract_macosx_min_system_version(lib_path)
                if min_ver is not None:
                    min_ver = min_ver[0:2]
                    if min_ver[0] > 10:
                        min_ver = (min_ver[0], 0)
                    versions_dict[lib_path] = min_ver

    if len(versions_dict) > 0:
        base_version = max(base_version, max(versions_dict.values()))

    # macosx platform tag do not support minor bugfix release
    fin_base_version = "_".join([str(x) for x in base_version])
    if start_version < base_version:
        problematic_files = [k for k, v in versions_dict.items() if v > start_version]
        problematic_files = "\n".join(problematic_files)
        if len(problematic_files) == 1:
            files_form = "this file"
        else:
            files_form = "these files"
        error_message = (
            "[WARNING] This wheel needs a higher macOS version than {}  "
            "To silence this warning, set MACOSX_DEPLOYMENT_TARGET to at least "
            + fin_base_version
            + " or recreate "
            + files_form
            + " with lower "
            "MACOSX_DEPLOYMENT_TARGET:  \n" + problematic_files
        )

        if "MACOSX_DEPLOYMENT_TARGET" in os.environ:
            error_message = error_message.format(
                "is set in MACOSX_DEPLOYMENT_TARGET variable."
            )
        else:
            error_message = error_message.format(
                "the version your Python interpreter is compiled against."
            )

        sys.stderr.write(error_message)

    platform_tag = prefix + "_" + fin_base_version + "_" + suffix
    return platform_tag

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\dataclasses.py ===
import inspect
from dataclasses import _MISSING_TYPE, MISSING, Field, field, fields
from functools import wraps
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    get_args,
    get_origin,
    overload,
)

from .errors import (
    StrictDataclassClassValidationError,
    StrictDataclassDefinitionError,
    StrictDataclassFieldValidationError,
)


Validator_T = Callable[[Any], None]
T = TypeVar("T")


# The overload decorator helps type checkers understand the different return types
@overload
def strict(cls: Type[T]) -> Type[T]: ...


@overload
def strict(*, accept_kwargs: bool = False) -> Callable[[Type[T]], Type[T]]: ...


def strict(
    cls: Optional[Type[T]] = None, *, accept_kwargs: bool = False
) -> Union[Type[T], Callable[[Type[T]], Type[T]]]:
    """
    Decorator to add strict validation to a dataclass.

    This decorator must be used on top of `@dataclass` to ensure IDEs and static typing tools
    recognize the class as a dataclass.

    Can be used with or without arguments:
    - `@strict`
    - `@strict(accept_kwargs=True)`

    Args:
        cls:
            The class to convert to a strict dataclass.
        accept_kwargs (`bool`, *optional*):
            If True, allows arbitrary keyword arguments in `__init__`. Defaults to False.

    Returns:
        The enhanced dataclass with strict validation on field assignment.

    Example:
    ```py
    >>> from dataclasses import dataclass
    >>> from huggingface_hub.dataclasses import as_validated_field, strict, validated_field

    >>> @as_validated_field
    >>> def positive_int(value: int):
    ...     if not value >= 0:
    ...         raise ValueError(f"Value must be positive, got {value}")

    >>> @strict(accept_kwargs=True)
    ... @dataclass
    ... class User:
    ...     name: str
    ...     age: int = positive_int(default=10)

    # Initialize
    >>> User(name="John")
    User(name='John', age=10)

    # Extra kwargs are accepted
    >>> User(name="John", age=30, lastname="Doe")
    User(name='John', age=30, *lastname='Doe')

    # Invalid type => raises
    >>> User(name="John", age="30")
    huggingface_hub.errors.StrictDataclassFieldValidationError: Validation error for field 'age':
        TypeError: Field 'age' expected int, got str (value: '30')

    # Invalid value => raises
    >>> User(name="John", age=-1)
    huggingface_hub.errors.StrictDataclassFieldValidationError: Validation error for field 'age':
        ValueError: Value must be positive, got -1
    ```
    """

    def wrap(cls: Type[T]) -> Type[T]:
        if not hasattr(cls, "__dataclass_fields__"):
            raise StrictDataclassDefinitionError(
                f"Class '{cls.__name__}' must be a dataclass before applying @strict."
            )

        # List and store validators
        field_validators: Dict[str, List[Validator_T]] = {}
        for f in fields(cls):  # type: ignore [arg-type]
            validators = []
            validators.append(_create_type_validator(f))
            custom_validator = f.metadata.get("validator")
            if custom_validator is not None:
                if not isinstance(custom_validator, list):
                    custom_validator = [custom_validator]
                for validator in custom_validator:
                    if not _is_validator(validator):
                        raise StrictDataclassDefinitionError(
                            f"Invalid validator for field '{f.name}': {validator}. Must be a callable taking a single argument."
                        )
                validators.extend(custom_validator)
            field_validators[f.name] = validators
        cls.__validators__ = field_validators  # type: ignore

        # Override __setattr__ to validate fields on assignment
        original_setattr = cls.__setattr__

        def __strict_setattr__(self: Any, name: str, value: Any) -> None:
            """Custom __setattr__ method for strict dataclasses."""
            # Run all validators
            for validator in self.__validators__.get(name, []):
                try:
                    validator(value)
                except (ValueError, TypeError) as e:
                    raise StrictDataclassFieldValidationError(field=name, cause=e) from e

            # If validation passed, set the attribute
            original_setattr(self, name, value)

        cls.__setattr__ = __strict_setattr__  # type: ignore[method-assign]

        if accept_kwargs:
            # (optional) Override __init__ to accept arbitrary keyword arguments
            original_init = cls.__init__

            @wraps(original_init)
            def __init__(self, **kwargs: Any) -> None:
                # Extract only the fields that are part of the dataclass
                dataclass_fields = {f.name for f in fields(cls)}  # type: ignore [arg-type]
                standard_kwargs = {k: v for k, v in kwargs.items() if k in dataclass_fields}

                # Call the original __init__ with standard fields
                original_init(self, **standard_kwargs)

                # Add any additional kwargs as attributes
                for name, value in kwargs.items():
                    if name not in dataclass_fields:
                        self.__setattr__(name, value)

            cls.__init__ = __init__  # type: ignore[method-assign]

            # (optional) Override __repr__ to include additional kwargs
            original_repr = cls.__repr__

            @wraps(original_repr)
            def __repr__(self) -> str:
                # Call the original __repr__ to get the standard fields
                standard_repr = original_repr(self)

                # Get additional kwargs
                additional_kwargs = [
                    # add a '*' in front of additional kwargs to let the user know they are not part of the dataclass
                    f"*{k}={v!r}"
                    for k, v in self.__dict__.items()
                    if k not in cls.__dataclass_fields__  # type: ignore [attr-defined]
                ]
                additional_repr = ", ".join(additional_kwargs)

                # Combine both representations
                return f"{standard_repr[:-1]}, {additional_repr})" if additional_kwargs else standard_repr

            cls.__repr__ = __repr__  # type: ignore [method-assign]

        # List all public methods starting with `validate_` => class validators.
        class_validators = []

        for name in dir(cls):
            if not name.startswith("validate_"):
                continue
            method = getattr(cls, name)
            if not callable(method):
                continue
            if len(inspect.signature(method).parameters) != 1:
                raise StrictDataclassDefinitionError(
                    f"Class '{cls.__name__}' has a class validator '{name}' that takes more than one argument."
                    " Class validators must take only 'self' as an argument. Methods starting with 'validate_'"
                    " are considered to be class validators."
                )
            class_validators.append(method)

        cls.__class_validators__ = class_validators  # type: ignore [attr-defined]

        # Add `validate` method to the class, but first check if it already exists
        def validate(self: T) -> None:
            """Run class validators on the instance."""
            for validator in cls.__class_validators__:  # type: ignore [attr-defined]
                try:
                    validator(self)
                except (ValueError, TypeError) as e:
                    raise StrictDataclassClassValidationError(validator=validator.__name__, cause=e) from e

        # Hack to be able to raise if `.validate()` already exists except if it was created by this decorator on a parent class
        # (in which case we just override it)
        validate.__is_defined_by_strict_decorator__ = True  # type: ignore [attr-defined]

        if hasattr(cls, "validate"):
            if not getattr(cls.validate, "__is_defined_by_strict_decorator__", False):  # type: ignore [attr-defined]
                raise StrictDataclassDefinitionError(
                    f"Class '{cls.__name__}' already implements a method called 'validate'."
                    " This method name is reserved when using the @strict decorator on a dataclass."
                    " If you want to keep your own method, please rename it."
                )

        cls.validate = validate  # type: ignore

        # Run class validators after initialization
        initial_init = cls.__init__

        @wraps(initial_init)
        def init_with_validate(self, *args, **kwargs) -> None:
            """Run class validators after initialization."""
            initial_init(self, *args, **kwargs)  # type: ignore [call-arg]
            cls.validate(self)  # type: ignore [attr-defined]

        setattr(cls, "__init__", init_with_validate)

        return cls

    # Return wrapped class or the decorator itself
    return wrap(cls) if cls is not None else wrap


def validated_field(
    validator: Union[List[Validator_T], Validator_T],
    default: Union[Any, _MISSING_TYPE] = MISSING,
    default_factory: Union[Callable[[], Any], _MISSING_TYPE] = MISSING,
    init: bool = True,
    repr: bool = True,
    hash: Optional[bool] = None,
    compare: bool = True,
    metadata: Optional[Dict] = None,
    **kwargs: Any,
) -> Any:
    """
    Create a dataclass field with a custom validator.

    Useful to apply several checks to a field. If only applying one rule, check out the [`as_validated_field`] decorator.

    Args:
        validator (`Callable` or `List[Callable]`):
            A method that takes a value as input and raises ValueError/TypeError if the value is invalid.
            Can be a list of validators to apply multiple checks.
        **kwargs:
            Additional arguments to pass to `dataclasses.field()`.

    Returns:
        A field with the validator attached in metadata
    """
    if not isinstance(validator, list):
        validator = [validator]
    if metadata is None:
        metadata = {}
    metadata["validator"] = validator
    return field(  # type: ignore
        default=default,  # type: ignore [arg-type]
        default_factory=default_factory,  # type: ignore [arg-type]
        init=init,
        repr=repr,
        hash=hash,
        compare=compare,
        metadata=metadata,
        **kwargs,
    )


def as_validated_field(validator: Validator_T):
    """
    Decorates a validator function as a [`validated_field`] (i.e. a dataclass field with a custom validator).

    Args:
        validator (`Callable`):
            A method that takes a value as input and raises ValueError/TypeError if the value is invalid.
    """

    def _inner(
        default: Union[Any, _MISSING_TYPE] = MISSING,
        default_factory: Union[Callable[[], Any], _MISSING_TYPE] = MISSING,
        init: bool = True,
        repr: bool = True,
        hash: Optional[bool] = None,
        compare: bool = True,
        metadata: Optional[Dict] = None,
        **kwargs: Any,
    ):
        return validated_field(
            validator,
            default=default,
            default_factory=default_factory,
            init=init,
            repr=repr,
            hash=hash,
            compare=compare,
            metadata=metadata,
            **kwargs,
        )

    return _inner


def type_validator(name: str, value: Any, expected_type: Any) -> None:
    """Validate that 'value' matches 'expected_type'."""
    origin = get_origin(expected_type)
    args = get_args(expected_type)

    if expected_type is Any:
        return
    elif validator := _BASIC_TYPE_VALIDATORS.get(origin):
        validator(name, value, args)
    elif isinstance(expected_type, type):  # simple types
        _validate_simple_type(name, value, expected_type)
    else:
        raise TypeError(f"Unsupported type for field '{name}': {expected_type}")


def _validate_union(name: str, value: Any, args: Tuple[Any, ...]) -> None:
    """Validate that value matches one of the types in a Union."""
    errors = []
    for t in args:
        try:
            type_validator(name, value, t)
            return  # Valid if any type matches
        except TypeError as e:
            errors.append(str(e))

    raise TypeError(
        f"Field '{name}' with value {repr(value)} doesn't match any type in {args}. Errors: {'; '.join(errors)}"
    )


def _validate_literal(name: str, value: Any, args: Tuple[Any, ...]) -> None:
    """Validate Literal type."""
    if value not in args:
        raise TypeError(f"Field '{name}' expected one of {args}, got {value}")


def _validate_list(name: str, value: Any, args: Tuple[Any, ...]) -> None:
    """Validate List[T] type."""
    if not isinstance(value, list):
        raise TypeError(f"Field '{name}' expected a list, got {type(value).__name__}")

    # Validate each item in the list
    item_type = args[0]
    for i, item in enumerate(value):
        try:
            type_validator(f"{name}[{i}]", item, item_type)
        except TypeError as e:
            raise TypeError(f"Invalid item at index {i} in list '{name}'") from e


def _validate_dict(name: str, value: Any, args: Tuple[Any, ...]) -> None:
    """Validate Dict[K, V] type."""
    if not isinstance(value, dict):
        raise TypeError(f"Field '{name}' expected a dict, got {type(value).__name__}")

    # Validate keys and values
    key_type, value_type = args
    for k, v in value.items():
        try:
            type_validator(f"{name}.key", k, key_type)
            type_validator(f"{name}[{k!r}]", v, value_type)
        except TypeError as e:
            raise TypeError(f"Invalid key or value in dict '{name}'") from e


def _validate_tuple(name: str, value: Any, args: Tuple[Any, ...]) -> None:
    """Validate Tuple type."""
    if not isinstance(value, tuple):
        raise TypeError(f"Field '{name}' expected a tuple, got {type(value).__name__}")

    # Handle variable-length tuples: Tuple[T, ...]
    if len(args) == 2 and args[1] is Ellipsis:
        for i, item in enumerate(value):
            try:
                type_validator(f"{name}[{i}]", item, args[0])
            except TypeError as e:
                raise TypeError(f"Invalid item at index {i} in tuple '{name}'") from e
    # Handle fixed-length tuples: Tuple[T1, T2, ...]
    elif len(args) != len(value):
        raise TypeError(f"Field '{name}' expected a tuple of length {len(args)}, got {len(value)}")
    else:
        for i, (item, expected) in enumerate(zip(value, args)):
            try:
                type_validator(f"{name}[{i}]", item, expected)
            except TypeError as e:
                raise TypeError(f"Invalid item at index {i} in tuple '{name}'") from e


def _validate_set(name: str, value: Any, args: Tuple[Any, ...]) -> None:
    """Validate Set[T] type."""
    if not isinstance(value, set):
        raise TypeError(f"Field '{name}' expected a set, got {type(value).__name__}")

    # Validate each item in the set
    item_type = args[0]
    for i, item in enumerate(value):
        try:
            type_validator(f"{name} item", item, item_type)
        except TypeError as e:
            raise TypeError(f"Invalid item in set '{name}'") from e


def _validate_simple_type(name: str, value: Any, expected_type: type) -> None:
    """Validate simple type (int, str, etc.)."""
    if not isinstance(value, expected_type):
        raise TypeError(
            f"Field '{name}' expected {expected_type.__name__}, got {type(value).__name__} (value: {repr(value)})"
        )


def _create_type_validator(field: Field) -> Validator_T:
    """Create a type validator function for a field."""
    # Hacky: we cannot use a lambda here because of reference issues

    def validator(value: Any) -> None:
        type_validator(field.name, value, field.type)

    return validator


def _is_validator(validator: Any) -> bool:
    """Check if a function is a validator.

    A validator is a Callable that can be called with a single positional argument.
    The validator can have more arguments with default values.

    Basically, returns True if `validator(value)` is possible.
    """
    if not callable(validator):
        return False

    signature = inspect.signature(validator)
    parameters = list(signature.parameters.values())
    if len(parameters) == 0:
        return False
    if parameters[0].kind not in (
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
        inspect.Parameter.POSITIONAL_ONLY,
        inspect.Parameter.VAR_POSITIONAL,
    ):
        return False
    for parameter in parameters[1:]:
        if parameter.default == inspect.Parameter.empty:
            return False
    return True


_BASIC_TYPE_VALIDATORS = {
    Union: _validate_union,
    Literal: _validate_literal,
    list: _validate_list,
    dict: _validate_dict,
    tuple: _validate_tuple,
    set: _validate_set,
}


__all__ = [
    "strict",
    "validated_field",
    "Validator_T",
    "StrictDataclassClassValidationError",
    "StrictDataclassDefinitionError",
    "StrictDataclassFieldValidationError",
]

# === NexusCore/openenv\Lib\site-packages\litellm\llms\vertex_ai\files\transformation.py ===
import json
import os
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union

from httpx import Headers, Response

from litellm.litellm_core_utils.prompt_templates.common_utils import extract_file_data
from litellm.llms.base_llm.chat.transformation import BaseLLMException
from litellm.llms.base_llm.files.transformation import (
    BaseFilesConfig,
    LiteLLMLoggingObj,
)
from litellm.llms.vertex_ai.common_utils import (
    _convert_vertex_datetime_to_openai_datetime,
)
from litellm.llms.vertex_ai.gemini.transformation import _transform_request_body
from litellm.llms.vertex_ai.gemini.vertex_and_google_ai_studio_gemini import (
    VertexGeminiConfig,
)
from litellm.types.llms.openai import (
    AllMessageValues,
    CreateFileRequest,
    FileTypes,
    OpenAICreateFileRequestOptionalParams,
    OpenAIFileObject,
    PathLike,
)
from litellm.types.llms.vertex_ai import GcsBucketResponse
from litellm.types.utils import ExtractedFileData, LlmProviders

from ..common_utils import VertexAIError
from ..vertex_llm_base import VertexBase


class VertexAIFilesConfig(VertexBase, BaseFilesConfig):
    """
    Config for VertexAI Files
    """

    def __init__(self):
        self.jsonl_transformation = VertexAIJsonlFilesTransformation()
        super().__init__()

    @property
    def custom_llm_provider(self) -> LlmProviders:
        return LlmProviders.VERTEX_AI

    def validate_environment(
        self,
        headers: dict,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ) -> dict:
        if not api_key:
            api_key, _ = self.get_access_token(
                credentials=litellm_params.get("vertex_credentials"),
                project_id=litellm_params.get("vertex_project"),
            )
            if not api_key:
                raise ValueError("api_key is required")
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    def _get_content_from_openai_file(self, openai_file_content: FileTypes) -> str:
        """
        Helper to extract content from various OpenAI file types and return as string.

        Handles:
        - Direct content (str, bytes, IO[bytes])
        - Tuple formats: (filename, content, [content_type], [headers])
        - PathLike objects
        """
        content: Union[str, bytes] = b""
        # Extract file content from tuple if necessary
        if isinstance(openai_file_content, tuple):
            # Take the second element which is always the file content
            file_content = openai_file_content[1]
        else:
            file_content = openai_file_content

        # Handle different file content types
        if isinstance(file_content, str):
            # String content can be used directly
            content = file_content
        elif isinstance(file_content, bytes):
            # Bytes content can be decoded
            content = file_content
        elif isinstance(file_content, PathLike):  # PathLike
            with open(str(file_content), "rb") as f:
                content = f.read()
        elif hasattr(file_content, "read"):  # IO[bytes]
            # File-like objects need to be read
            content = file_content.read()

        # Ensure content is string
        if isinstance(content, bytes):
            content = content.decode("utf-8")

        return content

    def _get_gcs_object_name_from_batch_jsonl(
        self,
        openai_jsonl_content: List[Dict[str, Any]],
    ) -> str:
        """
        Gets a unique GCS object name for the VertexAI batch prediction job

        named as: litellm-vertex-{model}-{uuid}
        """
        _model = openai_jsonl_content[0].get("body", {}).get("model", "")
        if "publishers/google/models" not in _model:
            _model = f"publishers/google/models/{_model}"
        object_name = f"litellm-vertex-files/{_model}/{uuid.uuid4()}"
        return object_name

    def get_object_name(
        self, extracted_file_data: ExtractedFileData, purpose: str
    ) -> str:
        """
        Get the object name for the request
        """
        extracted_file_data_content = extracted_file_data.get("content")

        if extracted_file_data_content is None:
            raise ValueError("file content is required")

        if purpose == "batch":
            ## 1. If jsonl, check if there's a model name
            file_content = self._get_content_from_openai_file(
                extracted_file_data_content
            )

            # Split into lines and parse each line as JSON
            openai_jsonl_content = [
                json.loads(line) for line in file_content.splitlines() if line.strip()
            ]
            if len(openai_jsonl_content) > 0:
                return self._get_gcs_object_name_from_batch_jsonl(openai_jsonl_content)

        ## 2. If not jsonl, return the filename
        filename = extracted_file_data.get("filename")
        if filename:
            return filename
        ## 3. If no file name, return timestamp
        return str(int(time.time()))

    def get_complete_file_url(
        self,
        api_base: Optional[str],
        api_key: Optional[str],
        model: str,
        optional_params: Dict,
        litellm_params: Dict,
        data: CreateFileRequest,
    ) -> str:
        """
        Get the complete url for the request
        """
        bucket_name = litellm_params.get("bucket_name") or os.getenv("GCS_BUCKET_NAME")
        if not bucket_name:
            raise ValueError("GCS bucket_name is required")
        file_data = data.get("file")
        purpose = data.get("purpose")
        if file_data is None:
            raise ValueError("file is required")
        if purpose is None:
            raise ValueError("purpose is required")
        extracted_file_data = extract_file_data(file_data)
        object_name = self.get_object_name(extracted_file_data, purpose)
        endpoint = (
            f"upload/storage/v1/b/{bucket_name}/o?uploadType=media&name={object_name}"
        )
        api_base = api_base or "https://storage.googleapis.com"
        if not api_base:
            raise ValueError("api_base is required")

        return f"{api_base}/{endpoint}"

    def get_supported_openai_params(
        self, model: str
    ) -> List[OpenAICreateFileRequestOptionalParams]:
        return []

    def map_openai_params(
        self,
        non_default_params: dict,
        optional_params: dict,
        model: str,
        drop_params: bool,
    ) -> dict:
        return optional_params

    def _map_openai_to_vertex_params(
        self,
        openai_request_body: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        wrapper to call VertexGeminiConfig.map_openai_params
        """
        from litellm.llms.vertex_ai.gemini.vertex_and_google_ai_studio_gemini import (
            VertexGeminiConfig,
        )

        config = VertexGeminiConfig()
        _model = openai_request_body.get("model", "")
        vertex_params = config.map_openai_params(
            model=_model,
            non_default_params=openai_request_body,
            optional_params={},
            drop_params=False,
        )
        return vertex_params

    def _transform_openai_jsonl_content_to_vertex_ai_jsonl_content(
        self, openai_jsonl_content: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Transforms OpenAI JSONL content to VertexAI JSONL content

        jsonl body for vertex is {"request": <request_body>}
        Example Vertex jsonl
        {"request":{"contents": [{"role": "user", "parts": [{"text": "What is the relation between the following video and image samples?"}, {"fileData": {"fileUri": "gs://cloud-samples-data/generative-ai/video/animals.mp4", "mimeType": "video/mp4"}}, {"fileData": {"fileUri": "gs://cloud-samples-data/generative-ai/image/cricket.jpeg", "mimeType": "image/jpeg"}}]}]}}
        {"request":{"contents": [{"role": "user", "parts": [{"text": "Describe what is happening in this video."}, {"fileData": {"fileUri": "gs://cloud-samples-data/generative-ai/video/another_video.mov", "mimeType": "video/mov"}}]}]}}
        """

        vertex_jsonl_content = []
        for _openai_jsonl_content in openai_jsonl_content:
            openai_request_body = _openai_jsonl_content.get("body") or {}
            vertex_request_body = _transform_request_body(
                messages=openai_request_body.get("messages", []),
                model=openai_request_body.get("model", ""),
                optional_params=self._map_openai_to_vertex_params(openai_request_body),
                custom_llm_provider="vertex_ai",
                litellm_params={},
                cached_content=None,
            )
            vertex_jsonl_content.append({"request": vertex_request_body})
        return vertex_jsonl_content

    def transform_create_file_request(
        self,
        model: str,
        create_file_data: CreateFileRequest,
        optional_params: dict,
        litellm_params: dict,
    ) -> Union[bytes, str, dict]:
        """
        2 Cases:
        1. Handle basic file upload
        2. Handle batch file upload (.jsonl)
        """
        file_data = create_file_data.get("file")
        if file_data is None:
            raise ValueError("file is required")
        extracted_file_data = extract_file_data(file_data)
        extracted_file_data_content = extracted_file_data.get("content")
        if (
            create_file_data.get("purpose") == "batch"
            and extracted_file_data.get("content_type") == "application/jsonl"
            and extracted_file_data_content is not None
        ):
            ## 1. If jsonl, check if there's a model name
            file_content = self._get_content_from_openai_file(
                extracted_file_data_content
            )

            # Split into lines and parse each line as JSON
            openai_jsonl_content = [
                json.loads(line) for line in file_content.splitlines() if line.strip()
            ]
            vertex_jsonl_content = (
                self._transform_openai_jsonl_content_to_vertex_ai_jsonl_content(
                    openai_jsonl_content
                )
            )
            return json.dumps(vertex_jsonl_content)
        elif isinstance(extracted_file_data_content, bytes):
            return extracted_file_data_content
        else:
            raise ValueError("Unsupported file content type")

    def transform_create_file_response(
        self,
        model: Optional[str],
        raw_response: Response,
        logging_obj: LiteLLMLoggingObj,
        litellm_params: dict,
    ) -> OpenAIFileObject:
        """
        Transform VertexAI File upload response into OpenAI-style FileObject
        """
        response_json = raw_response.json()

        try:
            response_object = GcsBucketResponse(**response_json)  # type: ignore
        except Exception as e:
            raise VertexAIError(
                status_code=raw_response.status_code,
                message=f"Error reading GCS bucket response: {e}",
                headers=raw_response.headers,
            )

        gcs_id = response_object.get("id", "")
        # Remove the last numeric ID from the path
        gcs_id = "/".join(gcs_id.split("/")[:-1]) if gcs_id else ""

        return OpenAIFileObject(
            purpose=response_object.get("purpose", "batch"),
            id=f"gs://{gcs_id}",
            filename=response_object.get("name", ""),
            created_at=_convert_vertex_datetime_to_openai_datetime(
                vertex_datetime=response_object.get("timeCreated", "")
            ),
            status="uploaded",
            bytes=int(response_object.get("size", 0)),
            object="file",
        )

    def get_error_class(
        self, error_message: str, status_code: int, headers: Union[Dict, Headers]
    ) -> BaseLLMException:
        return VertexAIError(
            status_code=status_code, message=error_message, headers=headers
        )


class VertexAIJsonlFilesTransformation(VertexGeminiConfig):
    """
    Transforms OpenAI /v1/files/* requests to VertexAI /v1/files/* requests
    """

    def transform_openai_file_content_to_vertex_ai_file_content(
        self, openai_file_content: Optional[FileTypes] = None
    ) -> Tuple[str, str]:
        """
        Transforms OpenAI FileContentRequest to VertexAI FileContentRequest
        """

        if openai_file_content is None:
            raise ValueError("contents of file are None")
        # Read the content of the file
        file_content = self._get_content_from_openai_file(openai_file_content)

        # Split into lines and parse each line as JSON
        openai_jsonl_content = [
            json.loads(line) for line in file_content.splitlines() if line.strip()
        ]
        vertex_jsonl_content = (
            self._transform_openai_jsonl_content_to_vertex_ai_jsonl_content(
                openai_jsonl_content
            )
        )
        vertex_jsonl_string = "\n".join(
            json.dumps(item) for item in vertex_jsonl_content
        )
        object_name = self._get_gcs_object_name(
            openai_jsonl_content=openai_jsonl_content
        )
        return vertex_jsonl_string, object_name

    def _transform_openai_jsonl_content_to_vertex_ai_jsonl_content(
        self, openai_jsonl_content: List[Dict[str, Any]]
    ):
        """
        Transforms OpenAI JSONL content to VertexAI JSONL content

        jsonl body for vertex is {"request": <request_body>}
        Example Vertex jsonl
        {"request":{"contents": [{"role": "user", "parts": [{"text": "What is the relation between the following video and image samples?"}, {"fileData": {"fileUri": "gs://cloud-samples-data/generative-ai/video/animals.mp4", "mimeType": "video/mp4"}}, {"fileData": {"fileUri": "gs://cloud-samples-data/generative-ai/image/cricket.jpeg", "mimeType": "image/jpeg"}}]}]}}
        {"request":{"contents": [{"role": "user", "parts": [{"text": "Describe what is happening in this video."}, {"fileData": {"fileUri": "gs://cloud-samples-data/generative-ai/video/another_video.mov", "mimeType": "video/mov"}}]}]}}
        """

        vertex_jsonl_content = []
        for _openai_jsonl_content in openai_jsonl_content:
            openai_request_body = _openai_jsonl_content.get("body") or {}
            vertex_request_body = _transform_request_body(
                messages=openai_request_body.get("messages", []),
                model=openai_request_body.get("model", ""),
                optional_params=self._map_openai_to_vertex_params(openai_request_body),
                custom_llm_provider="vertex_ai",
                litellm_params={},
                cached_content=None,
            )
            vertex_jsonl_content.append({"request": vertex_request_body})
        return vertex_jsonl_content

    def _get_gcs_object_name(
        self,
        openai_jsonl_content: List[Dict[str, Any]],
    ) -> str:
        """
        Gets a unique GCS object name for the VertexAI batch prediction job

        named as: litellm-vertex-{model}-{uuid}
        """
        _model = openai_jsonl_content[0].get("body", {}).get("model", "")
        if "publishers/google/models" not in _model:
            _model = f"publishers/google/models/{_model}"
        object_name = f"litellm-vertex-files/{_model}/{uuid.uuid4()}"
        return object_name

    def _map_openai_to_vertex_params(
        self,
        openai_request_body: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        wrapper to call VertexGeminiConfig.map_openai_params
        """
        _model = openai_request_body.get("model", "")
        vertex_params = self.map_openai_params(
            model=_model,
            non_default_params=openai_request_body,
            optional_params={},
            drop_params=False,
        )
        return vertex_params

    def _get_content_from_openai_file(self, openai_file_content: FileTypes) -> str:
        """
        Helper to extract content from various OpenAI file types and return as string.

        Handles:
        - Direct content (str, bytes, IO[bytes])
        - Tuple formats: (filename, content, [content_type], [headers])
        - PathLike objects
        """
        content: Union[str, bytes] = b""
        # Extract file content from tuple if necessary
        if isinstance(openai_file_content, tuple):
            # Take the second element which is always the file content
            file_content = openai_file_content[1]
        else:
            file_content = openai_file_content

        # Handle different file content types
        if isinstance(file_content, str):
            # String content can be used directly
            content = file_content
        elif isinstance(file_content, bytes):
            # Bytes content can be decoded
            content = file_content
        elif isinstance(file_content, PathLike):  # PathLike
            with open(str(file_content), "rb") as f:
                content = f.read()
        elif hasattr(file_content, "read"):  # IO[bytes]
            # File-like objects need to be read
            content = file_content.read()

        # Ensure content is string
        if isinstance(content, bytes):
            content = content.decode("utf-8")

        return content

    def transform_gcs_bucket_response_to_openai_file_object(
        self, create_file_data: CreateFileRequest, gcs_upload_response: Dict[str, Any]
    ) -> OpenAIFileObject:
        """
        Transforms GCS Bucket upload file response to OpenAI FileObject
        """
        gcs_id = gcs_upload_response.get("id", "")
        # Remove the last numeric ID from the path
        gcs_id = "/".join(gcs_id.split("/")[:-1]) if gcs_id else ""

        return OpenAIFileObject(
            purpose=create_file_data.get("purpose", "batch"),
            id=f"gs://{gcs_id}",
            filename=gcs_upload_response.get("name", ""),
            created_at=_convert_vertex_datetime_to_openai_datetime(
                vertex_datetime=gcs_upload_response.get("timeCreated", "")
            ),
            status="uploaded",
            bytes=gcs_upload_response.get("size", 0),
            object="file",
        )

# === NexusCore/openenv\Lib\site-packages\nltk\sem\linearlogic.py ===
# Natural Language Toolkit: Linear Logic
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# Copyright (C) 2001-2024 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

from nltk.internals import Counter
from nltk.sem.logic import APP, LogicParser

_counter = Counter()


class Tokens:
    # Punctuation
    OPEN = "("
    CLOSE = ")"

    # Operations
    IMP = "-o"

    PUNCT = [OPEN, CLOSE]
    TOKENS = PUNCT + [IMP]


class LinearLogicParser(LogicParser):
    """A linear logic expression parser."""

    def __init__(self):
        LogicParser.__init__(self)

        self.operator_precedence = {APP: 1, Tokens.IMP: 2, None: 3}
        self.right_associated_operations += [Tokens.IMP]

    def get_all_symbols(self):
        return Tokens.TOKENS

    def handle(self, tok, context):
        if tok not in Tokens.TOKENS:
            return self.handle_variable(tok, context)
        elif tok == Tokens.OPEN:
            return self.handle_open(tok, context)

    def get_BooleanExpression_factory(self, tok):
        if tok == Tokens.IMP:
            return ImpExpression
        else:
            return None

    def make_BooleanExpression(self, factory, first, second):
        return factory(first, second)

    def attempt_ApplicationExpression(self, expression, context):
        """Attempt to make an application expression.  If the next tokens
        are an argument in parens, then the argument expression is a
        function being applied to the arguments.  Otherwise, return the
        argument expression."""
        if self.has_priority(APP, context):
            if self.inRange(0) and self.token(0) == Tokens.OPEN:
                self.token()  # swallow then open paren
                argument = self.process_next_expression(APP)
                self.assertNextToken(Tokens.CLOSE)
                expression = ApplicationExpression(expression, argument, None)
        return expression

    def make_VariableExpression(self, name):
        if name[0].isupper():
            return VariableExpression(name)
        else:
            return ConstantExpression(name)


class Expression:
    _linear_logic_parser = LinearLogicParser()

    @classmethod
    def fromstring(cls, s):
        return cls._linear_logic_parser.parse(s)

    def applyto(self, other, other_indices=None):
        return ApplicationExpression(self, other, other_indices)

    def __call__(self, other):
        return self.applyto(other)

    def __repr__(self):
        return f"<{self.__class__.__name__} {self}>"


class AtomicExpression(Expression):
    def __init__(self, name, dependencies=None):
        """
        :param name: str for the constant name
        :param dependencies: list of int for the indices on which this atom is dependent
        """
        assert isinstance(name, str)
        self.name = name

        if not dependencies:
            dependencies = []
        self.dependencies = dependencies

    def simplify(self, bindings=None):
        """
        If 'self' is bound by 'bindings', return the atomic to which it is bound.
        Otherwise, return self.

        :param bindings: ``BindingDict`` A dictionary of bindings used to simplify
        :return: ``AtomicExpression``
        """
        if bindings and self in bindings:
            return bindings[self]
        else:
            return self

    def compile_pos(self, index_counter, glueFormulaFactory):
        """
        From Iddo Lev's PhD Dissertation p108-109

        :param index_counter: ``Counter`` for unique indices
        :param glueFormulaFactory: ``GlueFormula`` for creating new glue formulas
        :return: (``Expression``,set) for the compiled linear logic and any newly created glue formulas
        """
        self.dependencies = []
        return (self, [])

    def compile_neg(self, index_counter, glueFormulaFactory):
        """
        From Iddo Lev's PhD Dissertation p108-109

        :param index_counter: ``Counter`` for unique indices
        :param glueFormulaFactory: ``GlueFormula`` for creating new glue formulas
        :return: (``Expression``,set) for the compiled linear logic and any newly created glue formulas
        """
        self.dependencies = []
        return (self, [])

    def initialize_labels(self, fstruct):
        self.name = fstruct.initialize_label(self.name.lower())

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.name == other.name

    def __ne__(self, other):
        return not self == other

    def __str__(self):
        accum = self.name
        if self.dependencies:
            accum += "%s" % self.dependencies
        return accum

    def __hash__(self):
        return hash(self.name)


class ConstantExpression(AtomicExpression):
    def unify(self, other, bindings):
        """
        If 'other' is a constant, then it must be equal to 'self'.  If 'other' is a variable,
        then it must not be bound to anything other than 'self'.

        :param other: ``Expression``
        :param bindings: ``BindingDict`` A dictionary of all current bindings
        :return: ``BindingDict`` A new combined dictionary of of 'bindings' and any new binding
        :raise UnificationException: If 'self' and 'other' cannot be unified in the context of 'bindings'
        """
        assert isinstance(other, Expression)
        if isinstance(other, VariableExpression):
            try:
                return bindings + BindingDict([(other, self)])
            except VariableBindingException:
                pass
        elif self == other:
            return bindings
        raise UnificationException(self, other, bindings)


class VariableExpression(AtomicExpression):
    def unify(self, other, bindings):
        """
        'self' must not be bound to anything other than 'other'.

        :param other: ``Expression``
        :param bindings: ``BindingDict`` A dictionary of all current bindings
        :return: ``BindingDict`` A new combined dictionary of of 'bindings' and the new binding
        :raise UnificationException: If 'self' and 'other' cannot be unified in the context of 'bindings'
        """
        assert isinstance(other, Expression)
        try:
            if self == other:
                return bindings
            else:
                return bindings + BindingDict([(self, other)])
        except VariableBindingException as e:
            raise UnificationException(self, other, bindings) from e


class ImpExpression(Expression):
    def __init__(self, antecedent, consequent):
        """
        :param antecedent: ``Expression`` for the antecedent
        :param consequent: ``Expression`` for the consequent
        """
        assert isinstance(antecedent, Expression)
        assert isinstance(consequent, Expression)
        self.antecedent = antecedent
        self.consequent = consequent

    def simplify(self, bindings=None):
        return self.__class__(
            self.antecedent.simplify(bindings), self.consequent.simplify(bindings)
        )

    def unify(self, other, bindings):
        """
        Both the antecedent and consequent of 'self' and 'other' must unify.

        :param other: ``ImpExpression``
        :param bindings: ``BindingDict`` A dictionary of all current bindings
        :return: ``BindingDict`` A new combined dictionary of of 'bindings' and any new bindings
        :raise UnificationException: If 'self' and 'other' cannot be unified in the context of 'bindings'
        """
        assert isinstance(other, ImpExpression)
        try:
            return (
                bindings
                + self.antecedent.unify(other.antecedent, bindings)
                + self.consequent.unify(other.consequent, bindings)
            )
        except VariableBindingException as e:
            raise UnificationException(self, other, bindings) from e

    def compile_pos(self, index_counter, glueFormulaFactory):
        """
        From Iddo Lev's PhD Dissertation p108-109

        :param index_counter: ``Counter`` for unique indices
        :param glueFormulaFactory: ``GlueFormula`` for creating new glue formulas
        :return: (``Expression``,set) for the compiled linear logic and any newly created glue formulas
        """
        (a, a_new) = self.antecedent.compile_neg(index_counter, glueFormulaFactory)
        (c, c_new) = self.consequent.compile_pos(index_counter, glueFormulaFactory)
        return (ImpExpression(a, c), a_new + c_new)

    def compile_neg(self, index_counter, glueFormulaFactory):
        """
        From Iddo Lev's PhD Dissertation p108-109

        :param index_counter: ``Counter`` for unique indices
        :param glueFormulaFactory: ``GlueFormula`` for creating new glue formulas
        :return: (``Expression``,list of ``GlueFormula``) for the compiled linear logic and any newly created glue formulas
        """
        (a, a_new) = self.antecedent.compile_pos(index_counter, glueFormulaFactory)
        (c, c_new) = self.consequent.compile_neg(index_counter, glueFormulaFactory)
        fresh_index = index_counter.get()
        c.dependencies.append(fresh_index)
        new_v = glueFormulaFactory("v%s" % fresh_index, a, {fresh_index})
        return (c, a_new + c_new + [new_v])

    def initialize_labels(self, fstruct):
        self.antecedent.initialize_labels(fstruct)
        self.consequent.initialize_labels(fstruct)

    def __eq__(self, other):
        return (
            self.__class__ == other.__class__
            and self.antecedent == other.antecedent
            and self.consequent == other.consequent
        )

    def __ne__(self, other):
        return not self == other

    def __str__(self):
        return "{}{} {} {}{}".format(
            Tokens.OPEN,
            self.antecedent,
            Tokens.IMP,
            self.consequent,
            Tokens.CLOSE,
        )

    def __hash__(self):
        return hash(f"{hash(self.antecedent)}{Tokens.IMP}{hash(self.consequent)}")


class ApplicationExpression(Expression):
    def __init__(self, function, argument, argument_indices=None):
        """
        :param function: ``Expression`` for the function
        :param argument: ``Expression`` for the argument
        :param argument_indices: set for the indices of the glue formula from which the argument came
        :raise LinearLogicApplicationException: If 'function' cannot be applied to 'argument' given 'argument_indices'.
        """
        function_simp = function.simplify()
        argument_simp = argument.simplify()

        assert isinstance(function_simp, ImpExpression)
        assert isinstance(argument_simp, Expression)

        bindings = BindingDict()

        try:
            if isinstance(function, ApplicationExpression):
                bindings += function.bindings
            if isinstance(argument, ApplicationExpression):
                bindings += argument.bindings
            bindings += function_simp.antecedent.unify(argument_simp, bindings)
        except UnificationException as e:
            raise LinearLogicApplicationException(
                f"Cannot apply {function_simp} to {argument_simp}. {e}"
            ) from e

        # If you are running it on complied premises, more conditions apply
        if argument_indices:
            # A.dependencies of (A -o (B -o C)) must be a proper subset of argument_indices
            if not set(function_simp.antecedent.dependencies) < argument_indices:
                raise LinearLogicApplicationException(
                    "Dependencies unfulfilled when attempting to apply Linear Logic formula %s to %s"
                    % (function_simp, argument_simp)
                )
            if set(function_simp.antecedent.dependencies) == argument_indices:
                raise LinearLogicApplicationException(
                    "Dependencies not a proper subset of indices when attempting to apply Linear Logic formula %s to %s"
                    % (function_simp, argument_simp)
                )

        self.function = function
        self.argument = argument
        self.bindings = bindings

    def simplify(self, bindings=None):
        """
        Since function is an implication, return its consequent.  There should be
        no need to check that the application is valid since the checking is done
        by the constructor.

        :param bindings: ``BindingDict`` A dictionary of bindings used to simplify
        :return: ``Expression``
        """
        if not bindings:
            bindings = self.bindings

        return self.function.simplify(bindings).consequent

    def __eq__(self, other):
        return (
            self.__class__ == other.__class__
            and self.function == other.function
            and self.argument == other.argument
        )

    def __ne__(self, other):
        return not self == other

    def __str__(self):
        return "%s" % self.function + Tokens.OPEN + "%s" % self.argument + Tokens.CLOSE

    def __hash__(self):
        return hash(f"{hash(self.antecedent)}{Tokens.OPEN}{hash(self.consequent)}")


class BindingDict:
    def __init__(self, bindings=None):
        """
        :param bindings:
            list [(``VariableExpression``, ``AtomicExpression``)] to initialize the dictionary
            dict {``VariableExpression``: ``AtomicExpression``} to initialize the dictionary
        """
        self.d = {}

        if isinstance(bindings, dict):
            bindings = bindings.items()

        if bindings:
            for v, b in bindings:
                self[v] = b

    def __setitem__(self, variable, binding):
        """
        A binding is consistent with the dict if its variable is not already bound, OR if its
        variable is already bound to its argument.

        :param variable: ``VariableExpression`` The variable bind
        :param binding: ``Expression`` The expression to which 'variable' should be bound
        :raise VariableBindingException: If the variable cannot be bound in this dictionary
        """
        assert isinstance(variable, VariableExpression)
        assert isinstance(binding, Expression)

        assert variable != binding

        existing = self.d.get(variable, None)

        if not existing or binding == existing:
            self.d[variable] = binding
        else:
            raise VariableBindingException(
                "Variable %s already bound to another value" % (variable)
            )

    def __getitem__(self, variable):
        """
        Return the expression to which 'variable' is bound
        """
        assert isinstance(variable, VariableExpression)

        intermediate = self.d[variable]
        while intermediate:
            try:
                intermediate = self.d[intermediate]
            except KeyError:
                return intermediate

    def __contains__(self, item):
        return item in self.d

    def __add__(self, other):
        """
        :param other: ``BindingDict`` The dict with which to combine self
        :return: ``BindingDict`` A new dict containing all the elements of both parameters
        :raise VariableBindingException: If the parameter dictionaries are not consistent with each other
        """
        try:
            combined = BindingDict()
            for v in self.d:
                combined[v] = self.d[v]
            for v in other.d:
                combined[v] = other.d[v]
            return combined
        except VariableBindingException as e:
            raise VariableBindingException(
                "Attempting to add two contradicting"
                " VariableBindingsLists: %s, %s" % (self, other)
            ) from e

    def __ne__(self, other):
        return not self == other

    def __eq__(self, other):
        if not isinstance(other, BindingDict):
            raise TypeError
        return self.d == other.d

    def __str__(self):
        return "{" + ", ".join(f"{v}: {self.d[v]}" for v in sorted(self.d.keys())) + "}"

    def __repr__(self):
        return "BindingDict: %s" % self


class VariableBindingException(Exception):
    pass


class UnificationException(Exception):
    def __init__(self, a, b, bindings):
        Exception.__init__(self, f"Cannot unify {a} with {b} given {bindings}")


class LinearLogicApplicationException(Exception):
    pass


def demo():
    lexpr = Expression.fromstring

    print(lexpr(r"f"))
    print(lexpr(r"(g -o f)"))
    print(lexpr(r"((g -o G) -o G)"))
    print(lexpr(r"g -o h -o f"))
    print(lexpr(r"(g -o f)(g)").simplify())
    print(lexpr(r"(H -o f)(g)").simplify())
    print(lexpr(r"((g -o G) -o G)((g -o f))").simplify())
    print(lexpr(r"(H -o H)((g -o f))").simplify())


if __name__ == "__main__":
    demo()

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\rich\box.py ===
import sys
from typing import TYPE_CHECKING, Iterable, List

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from pip._vendor.typing_extensions import Literal  # pragma: no cover


from ._loop import loop_last

if TYPE_CHECKING:
    from pip._vendor.rich.console import ConsoleOptions


class Box:
    """Defines characters to render boxes.

    ┌─┬┐ top
    │ ││ head
    ├─┼┤ head_row
    │ ││ mid
    ├─┼┤ row
    ├─┼┤ foot_row
    │ ││ foot
    └─┴┘ bottom

    Args:
        box (str): Characters making up box.
        ascii (bool, optional): True if this box uses ascii characters only. Default is False.
    """

    def __init__(self, box: str, *, ascii: bool = False) -> None:
        self._box = box
        self.ascii = ascii
        line1, line2, line3, line4, line5, line6, line7, line8 = box.splitlines()
        # top
        self.top_left, self.top, self.top_divider, self.top_right = iter(line1)
        # head
        self.head_left, _, self.head_vertical, self.head_right = iter(line2)
        # head_row
        (
            self.head_row_left,
            self.head_row_horizontal,
            self.head_row_cross,
            self.head_row_right,
        ) = iter(line3)

        # mid
        self.mid_left, _, self.mid_vertical, self.mid_right = iter(line4)
        # row
        self.row_left, self.row_horizontal, self.row_cross, self.row_right = iter(line5)
        # foot_row
        (
            self.foot_row_left,
            self.foot_row_horizontal,
            self.foot_row_cross,
            self.foot_row_right,
        ) = iter(line6)
        # foot
        self.foot_left, _, self.foot_vertical, self.foot_right = iter(line7)
        # bottom
        self.bottom_left, self.bottom, self.bottom_divider, self.bottom_right = iter(
            line8
        )

    def __repr__(self) -> str:
        return "Box(...)"

    def __str__(self) -> str:
        return self._box

    def substitute(self, options: "ConsoleOptions", safe: bool = True) -> "Box":
        """Substitute this box for another if it won't render due to platform issues.

        Args:
            options (ConsoleOptions): Console options used in rendering.
            safe (bool, optional): Substitute this for another Box if there are known problems
                displaying on the platform (currently only relevant on Windows). Default is True.

        Returns:
            Box: A different Box or the same Box.
        """
        box = self
        if options.legacy_windows and safe:
            box = LEGACY_WINDOWS_SUBSTITUTIONS.get(box, box)
        if options.ascii_only and not box.ascii:
            box = ASCII
        return box

    def get_plain_headed_box(self) -> "Box":
        """If this box uses special characters for the borders of the header, then
        return the equivalent box that does not.

        Returns:
            Box: The most similar Box that doesn't use header-specific box characters.
                If the current Box already satisfies this criterion, then it's returned.
        """
        return PLAIN_HEADED_SUBSTITUTIONS.get(self, self)

    def get_top(self, widths: Iterable[int]) -> str:
        """Get the top of a simple box.

        Args:
            widths (List[int]): Widths of columns.

        Returns:
            str: A string of box characters.
        """

        parts: List[str] = []
        append = parts.append
        append(self.top_left)
        for last, width in loop_last(widths):
            append(self.top * width)
            if not last:
                append(self.top_divider)
        append(self.top_right)
        return "".join(parts)

    def get_row(
        self,
        widths: Iterable[int],
        level: Literal["head", "row", "foot", "mid"] = "row",
        edge: bool = True,
    ) -> str:
        """Get the top of a simple box.

        Args:
            width (List[int]): Widths of columns.

        Returns:
            str: A string of box characters.
        """
        if level == "head":
            left = self.head_row_left
            horizontal = self.head_row_horizontal
            cross = self.head_row_cross
            right = self.head_row_right
        elif level == "row":
            left = self.row_left
            horizontal = self.row_horizontal
            cross = self.row_cross
            right = self.row_right
        elif level == "mid":
            left = self.mid_left
            horizontal = " "
            cross = self.mid_vertical
            right = self.mid_right
        elif level == "foot":
            left = self.foot_row_left
            horizontal = self.foot_row_horizontal
            cross = self.foot_row_cross
            right = self.foot_row_right
        else:
            raise ValueError("level must be 'head', 'row' or 'foot'")

        parts: List[str] = []
        append = parts.append
        if edge:
            append(left)
        for last, width in loop_last(widths):
            append(horizontal * width)
            if not last:
                append(cross)
        if edge:
            append(right)
        return "".join(parts)

    def get_bottom(self, widths: Iterable[int]) -> str:
        """Get the bottom of a simple box.

        Args:
            widths (List[int]): Widths of columns.

        Returns:
            str: A string of box characters.
        """

        parts: List[str] = []
        append = parts.append
        append(self.bottom_left)
        for last, width in loop_last(widths):
            append(self.bottom * width)
            if not last:
                append(self.bottom_divider)
        append(self.bottom_right)
        return "".join(parts)


# fmt: off
ASCII: Box = Box(
    "+--+\n"
    "| ||\n"
    "|-+|\n"
    "| ||\n"
    "|-+|\n"
    "|-+|\n"
    "| ||\n"
    "+--+\n",
    ascii=True,
)

ASCII2: Box = Box(
    "+-++\n"
    "| ||\n"
    "+-++\n"
    "| ||\n"
    "+-++\n"
    "+-++\n"
    "| ||\n"
    "+-++\n",
    ascii=True,
)

ASCII_DOUBLE_HEAD: Box = Box(
    "+-++\n"
    "| ||\n"
    "+=++\n"
    "| ||\n"
    "+-++\n"
    "+-++\n"
    "| ||\n"
    "+-++\n",
    ascii=True,
)

SQUARE: Box = Box(
    "┌─┬┐\n"
    "│ ││\n"
    "├─┼┤\n"
    "│ ││\n"
    "├─┼┤\n"
    "├─┼┤\n"
    "│ ││\n"
    "└─┴┘\n"
)

SQUARE_DOUBLE_HEAD: Box = Box(
    "┌─┬┐\n"
    "│ ││\n"
    "╞═╪╡\n"
    "│ ││\n"
    "├─┼┤\n"
    "├─┼┤\n"
    "│ ││\n"
    "└─┴┘\n"
)

MINIMAL: Box = Box(
    "  ╷ \n"
    "  │ \n"
    "╶─┼╴\n"
    "  │ \n"
    "╶─┼╴\n"
    "╶─┼╴\n"
    "  │ \n"
    "  ╵ \n"
)


MINIMAL_HEAVY_HEAD: Box = Box(
    "  ╷ \n"
    "  │ \n"
    "╺━┿╸\n"
    "  │ \n"
    "╶─┼╴\n"
    "╶─┼╴\n"
    "  │ \n"
    "  ╵ \n"
)

MINIMAL_DOUBLE_HEAD: Box = Box(
    "  ╷ \n"
    "  │ \n"
    " ═╪ \n"
    "  │ \n"
    " ─┼ \n"
    " ─┼ \n"
    "  │ \n"
    "  ╵ \n"
)


SIMPLE: Box = Box(
    "    \n"
    "    \n"
    " ── \n"
    "    \n"
    "    \n"
    " ── \n"
    "    \n"
    "    \n"
)

SIMPLE_HEAD: Box = Box(
    "    \n"
    "    \n"
    " ── \n"
    "    \n"
    "    \n"
    "    \n"
    "    \n"
    "    \n"
)


SIMPLE_HEAVY: Box = Box(
    "    \n"
    "    \n"
    " ━━ \n"
    "    \n"
    "    \n"
    " ━━ \n"
    "    \n"
    "    \n"
)


HORIZONTALS: Box = Box(
    " ── \n"
    "    \n"
    " ── \n"
    "    \n"
    " ── \n"
    " ── \n"
    "    \n"
    " ── \n"
)

ROUNDED: Box = Box(
    "╭─┬╮\n"
    "│ ││\n"
    "├─┼┤\n"
    "│ ││\n"
    "├─┼┤\n"
    "├─┼┤\n"
    "│ ││\n"
    "╰─┴╯\n"
)

HEAVY: Box = Box(
    "┏━┳┓\n"
    "┃ ┃┃\n"
    "┣━╋┫\n"
    "┃ ┃┃\n"
    "┣━╋┫\n"
    "┣━╋┫\n"
    "┃ ┃┃\n"
    "┗━┻┛\n"
)

HEAVY_EDGE: Box = Box(
    "┏━┯┓\n"
    "┃ │┃\n"
    "┠─┼┨\n"
    "┃ │┃\n"
    "┠─┼┨\n"
    "┠─┼┨\n"
    "┃ │┃\n"
    "┗━┷┛\n"
)

HEAVY_HEAD: Box = Box(
    "┏━┳┓\n"
    "┃ ┃┃\n"
    "┡━╇┩\n"
    "│ ││\n"
    "├─┼┤\n"
    "├─┼┤\n"
    "│ ││\n"
    "└─┴┘\n"
)

DOUBLE: Box = Box(
    "╔═╦╗\n"
    "║ ║║\n"
    "╠═╬╣\n"
    "║ ║║\n"
    "╠═╬╣\n"
    "╠═╬╣\n"
    "║ ║║\n"
    "╚═╩╝\n"
)

DOUBLE_EDGE: Box = Box(
    "╔═╤╗\n"
    "║ │║\n"
    "╟─┼╢\n"
    "║ │║\n"
    "╟─┼╢\n"
    "╟─┼╢\n"
    "║ │║\n"
    "╚═╧╝\n"
)

MARKDOWN: Box = Box(
    "    \n"
    "| ||\n"
    "|-||\n"
    "| ||\n"
    "|-||\n"
    "|-||\n"
    "| ||\n"
    "    \n",
    ascii=True,
)
# fmt: on

# Map Boxes that don't render with raster fonts on to equivalent that do
LEGACY_WINDOWS_SUBSTITUTIONS = {
    ROUNDED: SQUARE,
    MINIMAL_HEAVY_HEAD: MINIMAL,
    SIMPLE_HEAVY: SIMPLE,
    HEAVY: SQUARE,
    HEAVY_EDGE: SQUARE,
    HEAVY_HEAD: SQUARE,
}

# Map headed boxes to their headerless equivalents
PLAIN_HEADED_SUBSTITUTIONS = {
    HEAVY_HEAD: SQUARE,
    SQUARE_DOUBLE_HEAD: SQUARE,
    MINIMAL_DOUBLE_HEAD: MINIMAL,
    MINIMAL_HEAVY_HEAD: MINIMAL,
    ASCII_DOUBLE_HEAD: ASCII2,
}


if __name__ == "__main__":  # pragma: no cover
    from pip._vendor.rich.columns import Columns
    from pip._vendor.rich.panel import Panel

    from . import box as box
    from .console import Console
    from .table import Table
    from .text import Text

    console = Console(record=True)

    BOXES = [
        "ASCII",
        "ASCII2",
        "ASCII_DOUBLE_HEAD",
        "SQUARE",
        "SQUARE_DOUBLE_HEAD",
        "MINIMAL",
        "MINIMAL_HEAVY_HEAD",
        "MINIMAL_DOUBLE_HEAD",
        "SIMPLE",
        "SIMPLE_HEAD",
        "SIMPLE_HEAVY",
        "HORIZONTALS",
        "ROUNDED",
        "HEAVY",
        "HEAVY_EDGE",
        "HEAVY_HEAD",
        "DOUBLE",
        "DOUBLE_EDGE",
        "MARKDOWN",
    ]

    console.print(Panel("[bold green]Box Constants", style="green"), justify="center")
    console.print()

    columns = Columns(expand=True, padding=2)
    for box_name in sorted(BOXES):
        table = Table(
            show_footer=True, style="dim", border_style="not dim", expand=True
        )
        table.add_column("Header 1", "Footer 1")
        table.add_column("Header 2", "Footer 2")
        table.add_row("Cell", "Cell")
        table.add_row("Cell", "Cell")
        table.box = getattr(box, box_name)
        table.title = Text(f"box.{box_name}", style="magenta")
        columns.add_renderable(table)
    console.print(columns)

    # console.save_svg("box.svg")

# === NexusCore/openenv\Lib\site-packages\rich\box.py ===
import sys
from typing import TYPE_CHECKING, Iterable, List

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal  # pragma: no cover


from ._loop import loop_last

if TYPE_CHECKING:
    from rich.console import ConsoleOptions


class Box:
    """Defines characters to render boxes.

    ┌─┬┐ top
    │ ││ head
    ├─┼┤ head_row
    │ ││ mid
    ├─┼┤ row
    ├─┼┤ foot_row
    │ ││ foot
    └─┴┘ bottom

    Args:
        box (str): Characters making up box.
        ascii (bool, optional): True if this box uses ascii characters only. Default is False.
    """

    def __init__(self, box: str, *, ascii: bool = False) -> None:
        self._box = box
        self.ascii = ascii
        line1, line2, line3, line4, line5, line6, line7, line8 = box.splitlines()
        # top
        self.top_left, self.top, self.top_divider, self.top_right = iter(line1)
        # head
        self.head_left, _, self.head_vertical, self.head_right = iter(line2)
        # head_row
        (
            self.head_row_left,
            self.head_row_horizontal,
            self.head_row_cross,
            self.head_row_right,
        ) = iter(line3)

        # mid
        self.mid_left, _, self.mid_vertical, self.mid_right = iter(line4)
        # row
        self.row_left, self.row_horizontal, self.row_cross, self.row_right = iter(line5)
        # foot_row
        (
            self.foot_row_left,
            self.foot_row_horizontal,
            self.foot_row_cross,
            self.foot_row_right,
        ) = iter(line6)
        # foot
        self.foot_left, _, self.foot_vertical, self.foot_right = iter(line7)
        # bottom
        self.bottom_left, self.bottom, self.bottom_divider, self.bottom_right = iter(
            line8
        )

    def __repr__(self) -> str:
        return "Box(...)"

    def __str__(self) -> str:
        return self._box

    def substitute(self, options: "ConsoleOptions", safe: bool = True) -> "Box":
        """Substitute this box for another if it won't render due to platform issues.

        Args:
            options (ConsoleOptions): Console options used in rendering.
            safe (bool, optional): Substitute this for another Box if there are known problems
                displaying on the platform (currently only relevant on Windows). Default is True.

        Returns:
            Box: A different Box or the same Box.
        """
        box = self
        if options.legacy_windows and safe:
            box = LEGACY_WINDOWS_SUBSTITUTIONS.get(box, box)
        if options.ascii_only and not box.ascii:
            box = ASCII
        return box

    def get_plain_headed_box(self) -> "Box":
        """If this box uses special characters for the borders of the header, then
        return the equivalent box that does not.

        Returns:
            Box: The most similar Box that doesn't use header-specific box characters.
                If the current Box already satisfies this criterion, then it's returned.
        """
        return PLAIN_HEADED_SUBSTITUTIONS.get(self, self)

    def get_top(self, widths: Iterable[int]) -> str:
        """Get the top of a simple box.

        Args:
            widths (List[int]): Widths of columns.

        Returns:
            str: A string of box characters.
        """

        parts: List[str] = []
        append = parts.append
        append(self.top_left)
        for last, width in loop_last(widths):
            append(self.top * width)
            if not last:
                append(self.top_divider)
        append(self.top_right)
        return "".join(parts)

    def get_row(
        self,
        widths: Iterable[int],
        level: Literal["head", "row", "foot", "mid"] = "row",
        edge: bool = True,
    ) -> str:
        """Get the top of a simple box.

        Args:
            width (List[int]): Widths of columns.

        Returns:
            str: A string of box characters.
        """
        if level == "head":
            left = self.head_row_left
            horizontal = self.head_row_horizontal
            cross = self.head_row_cross
            right = self.head_row_right
        elif level == "row":
            left = self.row_left
            horizontal = self.row_horizontal
            cross = self.row_cross
            right = self.row_right
        elif level == "mid":
            left = self.mid_left
            horizontal = " "
            cross = self.mid_vertical
            right = self.mid_right
        elif level == "foot":
            left = self.foot_row_left
            horizontal = self.foot_row_horizontal
            cross = self.foot_row_cross
            right = self.foot_row_right
        else:
            raise ValueError("level must be 'head', 'row' or 'foot'")

        parts: List[str] = []
        append = parts.append
        if edge:
            append(left)
        for last, width in loop_last(widths):
            append(horizontal * width)
            if not last:
                append(cross)
        if edge:
            append(right)
        return "".join(parts)

    def get_bottom(self, widths: Iterable[int]) -> str:
        """Get the bottom of a simple box.

        Args:
            widths (List[int]): Widths of columns.

        Returns:
            str: A string of box characters.
        """

        parts: List[str] = []
        append = parts.append
        append(self.bottom_left)
        for last, width in loop_last(widths):
            append(self.bottom * width)
            if not last:
                append(self.bottom_divider)
        append(self.bottom_right)
        return "".join(parts)


# fmt: off
ASCII: Box = Box(
    "+--+\n"
    "| ||\n"
    "|-+|\n"
    "| ||\n"
    "|-+|\n"
    "|-+|\n"
    "| ||\n"
    "+--+\n",
    ascii=True,
)

ASCII2: Box = Box(
    "+-++\n"
    "| ||\n"
    "+-++\n"
    "| ||\n"
    "+-++\n"
    "+-++\n"
    "| ||\n"
    "+-++\n",
    ascii=True,
)

ASCII_DOUBLE_HEAD: Box = Box(
    "+-++\n"
    "| ||\n"
    "+=++\n"
    "| ||\n"
    "+-++\n"
    "+-++\n"
    "| ||\n"
    "+-++\n",
    ascii=True,
)

SQUARE: Box = Box(
    "┌─┬┐\n"
    "│ ││\n"
    "├─┼┤\n"
    "│ ││\n"
    "├─┼┤\n"
    "├─┼┤\n"
    "│ ││\n"
    "└─┴┘\n"
)

SQUARE_DOUBLE_HEAD: Box = Box(
    "┌─┬┐\n"
    "│ ││\n"
    "╞═╪╡\n"
    "│ ││\n"
    "├─┼┤\n"
    "├─┼┤\n"
    "│ ││\n"
    "└─┴┘\n"
)

MINIMAL: Box = Box(
    "  ╷ \n"
    "  │ \n"
    "╶─┼╴\n"
    "  │ \n"
    "╶─┼╴\n"
    "╶─┼╴\n"
    "  │ \n"
    "  ╵ \n"
)


MINIMAL_HEAVY_HEAD: Box = Box(
    "  ╷ \n"
    "  │ \n"
    "╺━┿╸\n"
    "  │ \n"
    "╶─┼╴\n"
    "╶─┼╴\n"
    "  │ \n"
    "  ╵ \n"
)

MINIMAL_DOUBLE_HEAD: Box = Box(
    "  ╷ \n"
    "  │ \n"
    " ═╪ \n"
    "  │ \n"
    " ─┼ \n"
    " ─┼ \n"
    "  │ \n"
    "  ╵ \n"
)


SIMPLE: Box = Box(
    "    \n"
    "    \n"
    " ── \n"
    "    \n"
    "    \n"
    " ── \n"
    "    \n"
    "    \n"
)

SIMPLE_HEAD: Box = Box(
    "    \n"
    "    \n"
    " ── \n"
    "    \n"
    "    \n"
    "    \n"
    "    \n"
    "    \n"
)


SIMPLE_HEAVY: Box = Box(
    "    \n"
    "    \n"
    " ━━ \n"
    "    \n"
    "    \n"
    " ━━ \n"
    "    \n"
    "    \n"
)


HORIZONTALS: Box = Box(
    " ── \n"
    "    \n"
    " ── \n"
    "    \n"
    " ── \n"
    " ── \n"
    "    \n"
    " ── \n"
)

ROUNDED: Box = Box(
    "╭─┬╮\n"
    "│ ││\n"
    "├─┼┤\n"
    "│ ││\n"
    "├─┼┤\n"
    "├─┼┤\n"
    "│ ││\n"
    "╰─┴╯\n"
)

HEAVY: Box = Box(
    "┏━┳┓\n"
    "┃ ┃┃\n"
    "┣━╋┫\n"
    "┃ ┃┃\n"
    "┣━╋┫\n"
    "┣━╋┫\n"
    "┃ ┃┃\n"
    "┗━┻┛\n"
)

HEAVY_EDGE: Box = Box(
    "┏━┯┓\n"
    "┃ │┃\n"
    "┠─┼┨\n"
    "┃ │┃\n"
    "┠─┼┨\n"
    "┠─┼┨\n"
    "┃ │┃\n"
    "┗━┷┛\n"
)

HEAVY_HEAD: Box = Box(
    "┏━┳┓\n"
    "┃ ┃┃\n"
    "┡━╇┩\n"
    "│ ││\n"
    "├─┼┤\n"
    "├─┼┤\n"
    "│ ││\n"
    "└─┴┘\n"
)

DOUBLE: Box = Box(
    "╔═╦╗\n"
    "║ ║║\n"
    "╠═╬╣\n"
    "║ ║║\n"
    "╠═╬╣\n"
    "╠═╬╣\n"
    "║ ║║\n"
    "╚═╩╝\n"
)

DOUBLE_EDGE: Box = Box(
    "╔═╤╗\n"
    "║ │║\n"
    "╟─┼╢\n"
    "║ │║\n"
    "╟─┼╢\n"
    "╟─┼╢\n"
    "║ │║\n"
    "╚═╧╝\n"
)

MARKDOWN: Box = Box(
    "    \n"
    "| ||\n"
    "|-||\n"
    "| ||\n"
    "|-||\n"
    "|-||\n"
    "| ||\n"
    "    \n",
    ascii=True,
)
# fmt: on

# Map Boxes that don't render with raster fonts on to equivalent that do
LEGACY_WINDOWS_SUBSTITUTIONS = {
    ROUNDED: SQUARE,
    MINIMAL_HEAVY_HEAD: MINIMAL,
    SIMPLE_HEAVY: SIMPLE,
    HEAVY: SQUARE,
    HEAVY_EDGE: SQUARE,
    HEAVY_HEAD: SQUARE,
}

# Map headed boxes to their headerless equivalents
PLAIN_HEADED_SUBSTITUTIONS = {
    HEAVY_HEAD: SQUARE,
    SQUARE_DOUBLE_HEAD: SQUARE,
    MINIMAL_DOUBLE_HEAD: MINIMAL,
    MINIMAL_HEAVY_HEAD: MINIMAL,
    ASCII_DOUBLE_HEAD: ASCII2,
}


if __name__ == "__main__":  # pragma: no cover
    from rich.columns import Columns
    from rich.panel import Panel

    from . import box as box
    from .console import Console
    from .table import Table
    from .text import Text

    console = Console(record=True)

    BOXES = [
        "ASCII",
        "ASCII2",
        "ASCII_DOUBLE_HEAD",
        "SQUARE",
        "SQUARE_DOUBLE_HEAD",
        "MINIMAL",
        "MINIMAL_HEAVY_HEAD",
        "MINIMAL_DOUBLE_HEAD",
        "SIMPLE",
        "SIMPLE_HEAD",
        "SIMPLE_HEAVY",
        "HORIZONTALS",
        "ROUNDED",
        "HEAVY",
        "HEAVY_EDGE",
        "HEAVY_HEAD",
        "DOUBLE",
        "DOUBLE_EDGE",
        "MARKDOWN",
    ]

    console.print(Panel("[bold green]Box Constants", style="green"), justify="center")
    console.print()

    columns = Columns(expand=True, padding=2)
    for box_name in sorted(BOXES):
        table = Table(
            show_footer=True, style="dim", border_style="not dim", expand=True
        )
        table.add_column("Header 1", "Footer 1")
        table.add_column("Header 2", "Footer 2")
        table.add_row("Cell", "Cell")
        table.add_row("Cell", "Cell")
        table.box = getattr(box, box_name)
        table.title = Text(f"box.{box_name}", style="magenta")
        columns.add_renderable(table)
    console.print(columns)

    # console.save_svg("box.svg")

# === NexusCore/openenv\Lib\site-packages\jedi\api\environment.py ===
"""
Environments are a way to activate different Python versions or Virtualenvs for
static analysis. The Python binary in that environment is going to be executed.
"""
import os
import sys
import hashlib
import filecmp
from collections import namedtuple
from shutil import which
from typing import TYPE_CHECKING

from jedi.cache import memoize_method, time_cache
from jedi.inference.compiled.subprocess import CompiledSubprocess, \
    InferenceStateSameProcess, InferenceStateSubprocess

import parso

if TYPE_CHECKING:
    from jedi.inference import InferenceState


_VersionInfo = namedtuple('VersionInfo', 'major minor micro')  # type: ignore[name-match]

_SUPPORTED_PYTHONS = ['3.13', '3.12', '3.11', '3.10', '3.9', '3.8', '3.7', '3.6']
_SAFE_PATHS = ['/usr/bin', '/usr/local/bin']
_CONDA_VAR = 'CONDA_PREFIX'
_CURRENT_VERSION = '%s.%s' % (sys.version_info.major, sys.version_info.minor)


class InvalidPythonEnvironment(Exception):
    """
    If you see this exception, the Python executable or Virtualenv you have
    been trying to use is probably not a correct Python version.
    """


class _BaseEnvironment:
    @memoize_method
    def get_grammar(self):
        version_string = '%s.%s' % (self.version_info.major, self.version_info.minor)
        return parso.load_grammar(version=version_string)

    @property
    def _sha256(self):
        try:
            return self._hash
        except AttributeError:
            self._hash = _calculate_sha256_for_file(self.executable)
            return self._hash


def _get_info():
    return (
        sys.executable,
        sys.prefix,
        sys.version_info[:3],
    )


class Environment(_BaseEnvironment):
    """
    This class is supposed to be created by internal Jedi architecture. You
    should not create it directly. Please use create_environment or the other
    functions instead. It is then returned by that function.
    """
    _subprocess = None

    def __init__(self, executable, env_vars=None):
        self._start_executable = executable
        self._env_vars = env_vars
        # Initialize the environment
        self._get_subprocess()

    def _get_subprocess(self):
        if self._subprocess is not None and not self._subprocess.is_crashed:
            return self._subprocess

        try:
            self._subprocess = CompiledSubprocess(self._start_executable,
                                                  env_vars=self._env_vars)
            info = self._subprocess._send(None, _get_info)
        except Exception as exc:
            raise InvalidPythonEnvironment(
                "Could not get version information for %r: %r" % (
                    self._start_executable,
                    exc))

        # Since it could change and might not be the same(?) as the one given,
        # set it here.
        self.executable = info[0]
        """
        The Python executable, matches ``sys.executable``.
        """
        self.path = info[1]
        """
        The path to an environment, matches ``sys.prefix``.
        """
        self.version_info = _VersionInfo(*info[2])
        """
        Like :data:`sys.version_info`: a tuple to show the current
        Environment's Python version.
        """
        return self._subprocess

    def __repr__(self):
        version = '.'.join(str(i) for i in self.version_info)
        return '<%s: %s in %s>' % (self.__class__.__name__, version, self.path)

    def get_inference_state_subprocess(
        self,
        inference_state: 'InferenceState',
    ) -> InferenceStateSubprocess:
        return InferenceStateSubprocess(inference_state, self._get_subprocess())

    @memoize_method
    def get_sys_path(self):
        """
        The sys path for this environment. Does not include potential
        modifications from e.g. appending to :data:`sys.path`.

        :returns: list of str
        """
        # It's pretty much impossible to generate the sys path without actually
        # executing Python. The sys path (when starting with -S) itself depends
        # on how the Python version was compiled (ENV variables).
        # If you omit -S when starting Python (normal case), additionally
        # site.py gets executed.
        return self._get_subprocess().get_sys_path()


class _SameEnvironmentMixin:
    def __init__(self):
        self._start_executable = self.executable = sys.executable
        self.path = sys.prefix
        self.version_info = _VersionInfo(*sys.version_info[:3])
        self._env_vars = None


class SameEnvironment(_SameEnvironmentMixin, Environment):
    pass


class InterpreterEnvironment(_SameEnvironmentMixin, _BaseEnvironment):
    def get_inference_state_subprocess(
        self,
        inference_state: 'InferenceState',
    ) -> InferenceStateSameProcess:
        return InferenceStateSameProcess(inference_state)

    def get_sys_path(self):
        return sys.path


def _get_virtual_env_from_var(env_var='VIRTUAL_ENV'):
    """Get virtualenv environment from VIRTUAL_ENV environment variable.

    It uses `safe=False` with ``create_environment``, because the environment
    variable is considered to be safe / controlled by the user solely.
    """
    var = os.environ.get(env_var)
    if var:
        # Under macOS in some cases - notably when using Pipenv - the
        # sys.prefix of the virtualenv is /path/to/env/bin/.. instead of
        # /path/to/env so we need to fully resolve the paths in order to
        # compare them.
        if os.path.realpath(var) == os.path.realpath(sys.prefix):
            return _try_get_same_env()

        try:
            return create_environment(var, safe=False)
        except InvalidPythonEnvironment:
            pass


def _calculate_sha256_for_file(path):
    sha256 = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(filecmp.BUFSIZE), b''):
            sha256.update(block)
    return sha256.hexdigest()


def get_default_environment():
    """
    Tries to return an active Virtualenv or conda environment.
    If there is no VIRTUAL_ENV variable or no CONDA_PREFIX variable set
    set it will return the latest Python version installed on the system. This
    makes it possible to use as many new Python features as possible when using
    autocompletion and other functionality.

    :returns: :class:`.Environment`
    """
    virtual_env = _get_virtual_env_from_var()
    if virtual_env is not None:
        return virtual_env

    conda_env = _get_virtual_env_from_var(_CONDA_VAR)
    if conda_env is not None:
        return conda_env

    return _try_get_same_env()


def _try_get_same_env():
    env = SameEnvironment()
    if not os.path.basename(env.executable).lower().startswith('python'):
        # This tries to counter issues with embedding. In some cases (e.g.
        # VIM's Python Mac/Windows, sys.executable is /foo/bar/vim. This
        # happens, because for Mac a function called `_NSGetExecutablePath` is
        # used and for Windows `GetModuleFileNameW`. These are both platform
        # specific functions. For all other systems sys.executable should be
        # alright. However here we try to generalize:
        #
        # 1. Check if the executable looks like python (heuristic)
        # 2. In case it's not try to find the executable
        # 3. In case we don't find it use an interpreter environment.
        #
        # The last option will always work, but leads to potential crashes of
        # Jedi - which is ok, because it happens very rarely and even less,
        # because the code below should work for most cases.
        if os.name == 'nt':
            # The first case would be a virtualenv and the second a normal
            # Python installation.
            checks = (r'Scripts\python.exe', 'python.exe')
        else:
            # For unix it looks like Python is always in a bin folder.
            checks = (
                'bin/python%s.%s' % (sys.version_info[0], sys.version[1]),
                'bin/python%s' % (sys.version_info[0]),
                'bin/python',
            )
        for check in checks:
            guess = os.path.join(sys.exec_prefix, check)
            if os.path.isfile(guess):
                # Bingo - We think we have our Python.
                return Environment(guess)
        # It looks like there is no reasonable Python to be found.
        return InterpreterEnvironment()
    # If no virtualenv is found, use the environment we're already
    # using.
    return env


def get_cached_default_environment():
    var = os.environ.get('VIRTUAL_ENV') or os.environ.get(_CONDA_VAR)
    environment = _get_cached_default_environment()

    # Under macOS in some cases - notably when using Pipenv - the
    # sys.prefix of the virtualenv is /path/to/env/bin/.. instead of
    # /path/to/env so we need to fully resolve the paths in order to
    # compare them.
    if var and os.path.realpath(var) != os.path.realpath(environment.path):
        _get_cached_default_environment.clear_cache()
        return _get_cached_default_environment()
    return environment


@time_cache(seconds=10 * 60)  # 10 Minutes
def _get_cached_default_environment():
    try:
        return get_default_environment()
    except InvalidPythonEnvironment:
        # It's possible that `sys.executable` is wrong. Typically happens
        # when Jedi is used in an executable that embeds Python. For further
        # information, have a look at:
        # https://github.com/davidhalter/jedi/issues/1531
        return InterpreterEnvironment()


def find_virtualenvs(paths=None, *, safe=True, use_environment_vars=True):
    """
    :param paths: A list of paths in your file system to be scanned for
        Virtualenvs. It will search in these paths and potentially execute the
        Python binaries.
    :param safe: Default True. In case this is False, it will allow this
        function to execute potential `python` environments. An attacker might
        be able to drop an executable in a path this function is searching by
        default. If the executable has not been installed by root, it will not
        be executed.
    :param use_environment_vars: Default True. If True, the VIRTUAL_ENV
        variable will be checked if it contains a valid VirtualEnv.
        CONDA_PREFIX will be checked to see if it contains a valid conda
        environment.

    :yields: :class:`.Environment`
    """
    if paths is None:
        paths = []

    _used_paths = set()

    if use_environment_vars:
        # Using this variable should be safe, because attackers might be
        # able to drop files (via git) but not environment variables.
        virtual_env = _get_virtual_env_from_var()
        if virtual_env is not None:
            yield virtual_env
            _used_paths.add(virtual_env.path)

        conda_env = _get_virtual_env_from_var(_CONDA_VAR)
        if conda_env is not None:
            yield conda_env
            _used_paths.add(conda_env.path)

    for directory in paths:
        if not os.path.isdir(directory):
            continue

        directory = os.path.abspath(directory)
        for path in os.listdir(directory):
            path = os.path.join(directory, path)
            if path in _used_paths:
                # A path shouldn't be inferred twice.
                continue
            _used_paths.add(path)

            try:
                executable = _get_executable_path(path, safe=safe)
                yield Environment(executable)
            except InvalidPythonEnvironment:
                pass


def find_system_environments(*, env_vars=None):
    """
    Ignores virtualenvs and returns the Python versions that were installed on
    your system. This might return nothing, if you're running Python e.g. from
    a portable version.

    The environments are sorted from latest to oldest Python version.

    :yields: :class:`.Environment`
    """
    for version_string in _SUPPORTED_PYTHONS:
        try:
            yield get_system_environment(version_string, env_vars=env_vars)
        except InvalidPythonEnvironment:
            pass


# TODO: this function should probably return a list of environments since
# multiple Python installations can be found on a system for the same version.
def get_system_environment(version, *, env_vars=None):
    """
    Return the first Python environment found for a string of the form 'X.Y'
    where X and Y are the major and minor versions of Python.

    :raises: :exc:`.InvalidPythonEnvironment`
    :returns: :class:`.Environment`
    """
    exe = which('python' + version)
    if exe:
        if exe == sys.executable:
            return SameEnvironment()
        return Environment(exe)

    if os.name == 'nt':
        for exe in _get_executables_from_windows_registry(version):
            try:
                return Environment(exe, env_vars=env_vars)
            except InvalidPythonEnvironment:
                pass
    raise InvalidPythonEnvironment("Cannot find executable python%s." % version)


def create_environment(path, *, safe=True, env_vars=None):
    """
    Make it possible to manually create an Environment object by specifying a
    Virtualenv path or an executable path and optional environment variables.

    :raises: :exc:`.InvalidPythonEnvironment`
    :returns: :class:`.Environment`
    """
    if os.path.isfile(path):
        _assert_safe(path, safe)
        return Environment(path, env_vars=env_vars)
    return Environment(_get_executable_path(path, safe=safe), env_vars=env_vars)


def _get_executable_path(path, safe=True):
    """
    Returns None if it's not actually a virtual env.
    """

    if os.name == 'nt':
        pythons = [os.path.join(path, 'Scripts', 'python.exe'), os.path.join(path, 'python.exe')]
    else:
        pythons = [os.path.join(path, 'bin', 'python')]
    for python in pythons:
        if os.path.exists(python):
            break
    else:
        raise InvalidPythonEnvironment("%s seems to be missing." % python)

    _assert_safe(python, safe)
    return python


def _get_executables_from_windows_registry(version):
    import winreg

    # TODO: support Python Anaconda.
    sub_keys = [
        r'SOFTWARE\Python\PythonCore\{version}\InstallPath',
        r'SOFTWARE\Wow6432Node\Python\PythonCore\{version}\InstallPath',
        r'SOFTWARE\Python\PythonCore\{version}-32\InstallPath',
        r'SOFTWARE\Wow6432Node\Python\PythonCore\{version}-32\InstallPath'
    ]
    for root_key in [winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE]:
        for sub_key in sub_keys:
            sub_key = sub_key.format(version=version)
            try:
                with winreg.OpenKey(root_key, sub_key) as key:
                    prefix = winreg.QueryValueEx(key, '')[0]
                    exe = os.path.join(prefix, 'python.exe')
                    if os.path.isfile(exe):
                        yield exe
            except WindowsError:
                pass


def _assert_safe(executable_path, safe):
    if safe and not _is_safe(executable_path):
        raise InvalidPythonEnvironment(
            "The python binary is potentially unsafe.")


def _is_safe(executable_path):
    # Resolve sym links. A venv typically is a symlink to a known Python
    # binary. Only virtualenvs copy symlinks around.
    real_path = os.path.realpath(executable_path)

    if _is_unix_safe_simple(real_path):
        return True

    # Just check the list of known Python versions. If it's not in there,
    # it's likely an attacker or some Python that was not properly
    # installed in the system.
    for environment in find_system_environments():
        if environment.executable == real_path:
            return True

        # If the versions don't match, just compare the binary files. If we
        # don't do that, only venvs will be working and not virtualenvs.
        # venvs are symlinks while virtualenvs are actual copies of the
        # Python files.
        # This still means that if the system Python is updated and the
        # virtualenv's Python is not (which is probably never going to get
        # upgraded), it will not work with Jedi. IMO that's fine, because
        # people should just be using venv. ~ dave
        if environment._sha256 == _calculate_sha256_for_file(real_path):
            return True
    return False


def _is_unix_safe_simple(real_path):
    if _is_unix_admin():
        # In case we are root, just be conservative and
        # only execute known paths.
        return any(real_path.startswith(p) for p in _SAFE_PATHS)

    uid = os.stat(real_path).st_uid
    # The interpreter needs to be owned by root. This means that it wasn't
    # written by a user and therefore attacking Jedi is not as simple.
    # The attack could look like the following:
    # 1. A user clones a repository.
    # 2. The repository has an innocent looking folder called foobar. jedi
    #    searches for the folder and executes foobar/bin/python --version if
    #    there's also a foobar/bin/activate.
    # 3. The attacker has gained code execution, since he controls
    #    foobar/bin/python.
    return uid == 0


def _is_unix_admin():
    try:
        return os.getuid() == 0
    except AttributeError:
        return False  # Windows

# === NexusCore/openenv\Lib\site-packages\litellm\llms\bedrock\embed\embedding.py ===
"""
Handles embedding calls to Bedrock's `/invoke` endpoint
"""

import copy
import json
from typing import Any, Callable, List, Optional, Tuple, Union

import httpx

import litellm
from litellm.llms.cohere.embed.handler import embedding as cohere_embedding
from litellm.llms.custom_httpx.http_handler import (
    AsyncHTTPHandler,
    HTTPHandler,
    _get_httpx_client,
    get_async_httpx_client,
)
from litellm.secret_managers.main import get_secret
from litellm.types.llms.bedrock import AmazonEmbeddingRequest, CohereEmbeddingRequest
from litellm.types.utils import EmbeddingResponse

from ..base_aws_llm import BaseAWSLLM
from ..common_utils import BedrockError
from .amazon_titan_g1_transformation import AmazonTitanG1Config
from .amazon_titan_multimodal_transformation import (
    AmazonTitanMultimodalEmbeddingG1Config,
)
from .amazon_titan_v2_transformation import AmazonTitanV2Config
from .cohere_transformation import BedrockCohereEmbeddingConfig


class BedrockEmbedding(BaseAWSLLM):
    def _load_credentials(
        self,
        optional_params: dict,
    ) -> Tuple[Any, str]:
        try:
            from botocore.credentials import Credentials
        except ImportError:
            raise ImportError("Missing boto3 to call bedrock. Run 'pip install boto3'.")
        ## CREDENTIALS ##
        # pop aws_secret_access_key, aws_access_key_id, aws_session_token, aws_region_name from kwargs, since completion calls fail with them
        aws_secret_access_key = optional_params.pop("aws_secret_access_key", None)
        aws_access_key_id = optional_params.pop("aws_access_key_id", None)
        aws_session_token = optional_params.pop("aws_session_token", None)
        aws_region_name = optional_params.pop("aws_region_name", None)
        aws_role_name = optional_params.pop("aws_role_name", None)
        aws_session_name = optional_params.pop("aws_session_name", None)
        aws_profile_name = optional_params.pop("aws_profile_name", None)
        aws_web_identity_token = optional_params.pop("aws_web_identity_token", None)
        aws_sts_endpoint = optional_params.pop("aws_sts_endpoint", None)

        ### SET REGION NAME ###
        if aws_region_name is None:
            # check env #
            litellm_aws_region_name = get_secret("AWS_REGION_NAME", None)

            if litellm_aws_region_name is not None and isinstance(
                litellm_aws_region_name, str
            ):
                aws_region_name = litellm_aws_region_name

            standard_aws_region_name = get_secret("AWS_REGION", None)
            if standard_aws_region_name is not None and isinstance(
                standard_aws_region_name, str
            ):
                aws_region_name = standard_aws_region_name

            if aws_region_name is None:
                aws_region_name = "us-west-2"

        credentials: Credentials = self.get_credentials(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
            aws_region_name=aws_region_name,
            aws_session_name=aws_session_name,
            aws_profile_name=aws_profile_name,
            aws_role_name=aws_role_name,
            aws_web_identity_token=aws_web_identity_token,
            aws_sts_endpoint=aws_sts_endpoint,
        )
        return credentials, aws_region_name

    async def async_embeddings(self):
        pass

    def _make_sync_call(
        self,
        client: Optional[HTTPHandler],
        timeout: Optional[Union[float, httpx.Timeout]],
        api_base: str,
        headers: dict,
        data: dict,
    ) -> dict:
        if client is None or not isinstance(client, HTTPHandler):
            _params = {}
            if timeout is not None:
                if isinstance(timeout, float) or isinstance(timeout, int):
                    timeout = httpx.Timeout(timeout)
                _params["timeout"] = timeout
            client = _get_httpx_client(_params)  # type: ignore
        else:
            client = client
        try:
            response = client.post(url=api_base, headers=headers, data=json.dumps(data))  # type: ignore
            response.raise_for_status()
        except httpx.HTTPStatusError as err:
            error_code = err.response.status_code
            raise BedrockError(status_code=error_code, message=err.response.text)
        except httpx.TimeoutException:
            raise BedrockError(status_code=408, message="Timeout error occurred.")

        return response.json()

    async def _make_async_call(
        self,
        client: Optional[AsyncHTTPHandler],
        timeout: Optional[Union[float, httpx.Timeout]],
        api_base: str,
        headers: dict,
        data: dict,
    ) -> dict:
        if client is None or not isinstance(client, AsyncHTTPHandler):
            _params = {}
            if timeout is not None:
                if isinstance(timeout, float) or isinstance(timeout, int):
                    timeout = httpx.Timeout(timeout)
                _params["timeout"] = timeout
            client = get_async_httpx_client(
                params=_params, llm_provider=litellm.LlmProviders.BEDROCK
            )
        else:
            client = client

        try:
            response = await client.post(url=api_base, headers=headers, data=json.dumps(data))  # type: ignore
            response.raise_for_status()
        except httpx.HTTPStatusError as err:
            error_code = err.response.status_code
            raise BedrockError(status_code=error_code, message=err.response.text)
        except httpx.TimeoutException:
            raise BedrockError(status_code=408, message="Timeout error occurred.")

        return response.json()

    def _single_func_embeddings(
        self,
        client: Optional[HTTPHandler],
        timeout: Optional[Union[float, httpx.Timeout]],
        batch_data: List[dict],
        credentials: Any,
        extra_headers: Optional[dict],
        endpoint_url: str,
        aws_region_name: str,
        model: str,
        logging_obj: Any,
    ):
        try:
            from botocore.auth import SigV4Auth
            from botocore.awsrequest import AWSRequest
        except ImportError:
            raise ImportError("Missing boto3 to call bedrock. Run 'pip install boto3'.")

        responses: List[dict] = []
        for data in batch_data:
            sigv4 = SigV4Auth(credentials, "bedrock", aws_region_name)
            headers = {"Content-Type": "application/json"}
            if extra_headers is not None:
                headers = {"Content-Type": "application/json", **extra_headers}
            request = AWSRequest(
                method="POST", url=endpoint_url, data=json.dumps(data), headers=headers
            )
            sigv4.add_auth(request)
            if (
                extra_headers is not None and "Authorization" in extra_headers
            ):  # prevent sigv4 from overwriting the auth header
                request.headers["Authorization"] = extra_headers["Authorization"]
            prepped = request.prepare()

            ## LOGGING
            logging_obj.pre_call(
                input=data,
                api_key="",
                additional_args={
                    "complete_input_dict": data,
                    "api_base": prepped.url,
                    "headers": prepped.headers,
                },
            )
            response = self._make_sync_call(
                client=client,
                timeout=timeout,
                api_base=prepped.url,
                headers=prepped.headers,  # type: ignore
                data=data,
            )

            ## LOGGING
            logging_obj.post_call(
                input=data,
                api_key="",
                original_response=response,
                additional_args={"complete_input_dict": data},
            )

            responses.append(response)

        returned_response: Optional[EmbeddingResponse] = None

        ## TRANSFORM RESPONSE ##
        if model == "amazon.titan-embed-image-v1":
            returned_response = (
                AmazonTitanMultimodalEmbeddingG1Config()._transform_response(
                    response_list=responses, model=model
                )
            )
        elif model == "amazon.titan-embed-text-v1":
            returned_response = AmazonTitanG1Config()._transform_response(
                response_list=responses, model=model
            )
        elif model == "amazon.titan-embed-text-v2:0":
            returned_response = AmazonTitanV2Config()._transform_response(
                response_list=responses, model=model
            )

        if returned_response is None:
            raise Exception(
                "Unable to map model response to known provider format. model={}".format(
                    model
                )
            )

        return returned_response

    async def _async_single_func_embeddings(
        self,
        client: Optional[AsyncHTTPHandler],
        timeout: Optional[Union[float, httpx.Timeout]],
        batch_data: List[dict],
        credentials: Any,
        extra_headers: Optional[dict],
        endpoint_url: str,
        aws_region_name: str,
        model: str,
        logging_obj: Any,
    ):
        try:
            from botocore.auth import SigV4Auth
            from botocore.awsrequest import AWSRequest
        except ImportError:
            raise ImportError("Missing boto3 to call bedrock. Run 'pip install boto3'.")

        responses: List[dict] = []
        for data in batch_data:
            sigv4 = SigV4Auth(credentials, "bedrock", aws_region_name)
            headers = {"Content-Type": "application/json"}
            if extra_headers is not None:
                headers = {"Content-Type": "application/json", **extra_headers}
            request = AWSRequest(
                method="POST", url=endpoint_url, data=json.dumps(data), headers=headers
            )
            sigv4.add_auth(request)
            if (
                extra_headers is not None and "Authorization" in extra_headers
            ):  # prevent sigv4 from overwriting the auth header
                request.headers["Authorization"] = extra_headers["Authorization"]
            prepped = request.prepare()

            ## LOGGING
            logging_obj.pre_call(
                input=data,
                api_key="",
                additional_args={
                    "complete_input_dict": data,
                    "api_base": prepped.url,
                    "headers": prepped.headers,
                },
            )
            response = await self._make_async_call(
                client=client,
                timeout=timeout,
                api_base=prepped.url,
                headers=prepped.headers,  # type: ignore
                data=data,
            )

            ## LOGGING
            logging_obj.post_call(
                input=data,
                api_key="",
                original_response=response,
                additional_args={"complete_input_dict": data},
            )

            responses.append(response)

        returned_response: Optional[EmbeddingResponse] = None

        ## TRANSFORM RESPONSE ##
        if model == "amazon.titan-embed-image-v1":
            returned_response = (
                AmazonTitanMultimodalEmbeddingG1Config()._transform_response(
                    response_list=responses, model=model
                )
            )
        elif model == "amazon.titan-embed-text-v1":
            returned_response = AmazonTitanG1Config()._transform_response(
                response_list=responses, model=model
            )
        elif model == "amazon.titan-embed-text-v2:0":
            returned_response = AmazonTitanV2Config()._transform_response(
                response_list=responses, model=model
            )

        if returned_response is None:
            raise Exception(
                "Unable to map model response to known provider format. model={}".format(
                    model
                )
            )

        return returned_response

    def embeddings(
        self,
        model: str,
        input: List[str],
        api_base: Optional[str],
        model_response: EmbeddingResponse,
        print_verbose: Callable,
        encoding,
        logging_obj,
        client: Optional[Union[HTTPHandler, AsyncHTTPHandler]],
        timeout: Optional[Union[float, httpx.Timeout]],
        aembedding: Optional[bool],
        extra_headers: Optional[dict],
        optional_params: dict,
        litellm_params: dict,
    ) -> EmbeddingResponse:
        try:
            from botocore.auth import SigV4Auth
            from botocore.awsrequest import AWSRequest
        except ImportError:
            raise ImportError("Missing boto3 to call bedrock. Run 'pip install boto3'.")

        credentials, aws_region_name = self._load_credentials(optional_params)

        ### TRANSFORMATION ###
        provider = model.split(".")[0]
        inference_params = copy.deepcopy(optional_params)
        inference_params = {
            k: v
            for k, v in inference_params.items()
            if k.lower() not in self.aws_authentication_params
        }
        inference_params.pop(
            "user", None
        )  # make sure user is not passed in for bedrock call
        modelId = (
            optional_params.pop("model_id", None) or model
        )  # default to model if not passed

        data: Optional[CohereEmbeddingRequest] = None
        batch_data: Optional[List] = None
        if provider == "cohere":
            data = BedrockCohereEmbeddingConfig()._transform_request(
                model=model, input=input, inference_params=inference_params
            )
        elif provider == "amazon" and model in [
            "amazon.titan-embed-image-v1",
            "amazon.titan-embed-text-v1",
            "amazon.titan-embed-text-v2:0",
        ]:
            batch_data = []
            for i in input:
                if model == "amazon.titan-embed-image-v1":
                    transformed_request: (
                        AmazonEmbeddingRequest
                    ) = AmazonTitanMultimodalEmbeddingG1Config()._transform_request(
                        input=i, inference_params=inference_params
                    )
                elif model == "amazon.titan-embed-text-v1":
                    transformed_request = AmazonTitanG1Config()._transform_request(
                        input=i, inference_params=inference_params
                    )
                elif model == "amazon.titan-embed-text-v2:0":
                    transformed_request = AmazonTitanV2Config()._transform_request(
                        input=i, inference_params=inference_params
                    )
                else:
                    raise Exception(
                        "Unmapped model. Received={}. Expected={}".format(
                            model,
                            [
                                "amazon.titan-embed-image-v1",
                                "amazon.titan-embed-text-v1",
                                "amazon.titan-embed-text-v2:0",
                            ],
                        )
                    )
                batch_data.append(transformed_request)

        ### SET RUNTIME ENDPOINT ###
        endpoint_url, proxy_endpoint_url = self.get_runtime_endpoint(
            api_base=api_base,
            aws_bedrock_runtime_endpoint=optional_params.pop(
                "aws_bedrock_runtime_endpoint", None
            ),
            aws_region_name=aws_region_name,
        )
        endpoint_url = f"{endpoint_url}/model/{modelId}/invoke"

        if batch_data is not None:
            if aembedding:
                return self._async_single_func_embeddings(  # type: ignore
                    client=(
                        client
                        if client is not None and isinstance(client, AsyncHTTPHandler)
                        else None
                    ),
                    timeout=timeout,
                    batch_data=batch_data,
                    credentials=credentials,
                    extra_headers=extra_headers,
                    endpoint_url=endpoint_url,
                    aws_region_name=aws_region_name,
                    model=model,
                    logging_obj=logging_obj,
                )
            return self._single_func_embeddings(
                client=(
                    client
                    if client is not None and isinstance(client, HTTPHandler)
                    else None
                ),
                timeout=timeout,
                batch_data=batch_data,
                credentials=credentials,
                extra_headers=extra_headers,
                endpoint_url=endpoint_url,
                aws_region_name=aws_region_name,
                model=model,
                logging_obj=logging_obj,
            )
        elif data is None:
            raise Exception("Unable to map Bedrock request to provider")

        sigv4 = SigV4Auth(credentials, "bedrock", aws_region_name)
        headers = {"Content-Type": "application/json"}
        if extra_headers is not None:
            headers = {"Content-Type": "application/json", **extra_headers}

        request = AWSRequest(
            method="POST", url=endpoint_url, data=json.dumps(data), headers=headers
        )
        sigv4.add_auth(request)
        if (
            extra_headers is not None and "Authorization" in extra_headers
        ):  # prevent sigv4 from overwriting the auth header
            request.headers["Authorization"] = extra_headers["Authorization"]
        prepped = request.prepare()

        ## ROUTING ##
        return cohere_embedding(
            model=model,
            input=input,
            model_response=model_response,
            logging_obj=logging_obj,
            optional_params=optional_params,
            encoding=encoding,
            data=data,  # type: ignore
            complete_api_base=prepped.url,
            api_key=None,
            aembedding=aembedding,
            timeout=timeout,
            client=client,
            headers=prepped.headers,  # type: ignore
        )

# === NexusCore/openenv\Lib\site-packages\nltk\ccg\chart.py ===
# Natural Language Toolkit: Combinatory Categorial Grammar
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Graeme Gange <ggange@csse.unimelb.edu.au>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
The lexicon is constructed by calling
``lexicon.fromstring(<lexicon string>)``.

In order to construct a parser, you also need a rule set.
The standard English rules are provided in chart as
``chart.DefaultRuleSet``.

The parser can then be constructed by calling, for example:
``parser = chart.CCGChartParser(<lexicon>, <ruleset>)``

Parsing is then performed by running
``parser.parse(<sentence>.split())``.

While this returns a list of trees, the default representation
of the produced trees is not very enlightening, particularly
given that it uses the same tree class as the CFG parsers.
It is probably better to call:
``chart.printCCGDerivation(<parse tree extracted from list>)``
which should print a nice representation of the derivation.

This entire process is shown far more clearly in the demonstration:
python chart.py
"""

import itertools

from nltk.ccg.combinator import *
from nltk.ccg.combinator import (
    BackwardApplication,
    BackwardBx,
    BackwardComposition,
    BackwardSx,
    BackwardT,
    ForwardApplication,
    ForwardComposition,
    ForwardSubstitution,
    ForwardT,
)
from nltk.ccg.lexicon import Token, fromstring
from nltk.ccg.logic import *
from nltk.parse import ParserI
from nltk.parse.chart import AbstractChartRule, Chart, EdgeI
from nltk.sem.logic import *
from nltk.tree import Tree


# Based on the EdgeI class from NLTK.
# A number of the properties of the EdgeI interface don't
# transfer well to CCGs, however.
class CCGEdge(EdgeI):
    def __init__(self, span, categ, rule):
        self._span = span
        self._categ = categ
        self._rule = rule
        self._comparison_key = (span, categ, rule)

    # Accessors
    def lhs(self):
        return self._categ

    def span(self):
        return self._span

    def start(self):
        return self._span[0]

    def end(self):
        return self._span[1]

    def length(self):
        return self._span[1] - self.span[0]

    def rhs(self):
        return ()

    def dot(self):
        return 0

    def is_complete(self):
        return True

    def is_incomplete(self):
        return False

    def nextsym(self):
        return None

    def categ(self):
        return self._categ

    def rule(self):
        return self._rule


class CCGLeafEdge(EdgeI):
    """
    Class representing leaf edges in a CCG derivation.
    """

    def __init__(self, pos, token, leaf):
        self._pos = pos
        self._token = token
        self._leaf = leaf
        self._comparison_key = (pos, token.categ(), leaf)

    # Accessors
    def lhs(self):
        return self._token.categ()

    def span(self):
        return (self._pos, self._pos + 1)

    def start(self):
        return self._pos

    def end(self):
        return self._pos + 1

    def length(self):
        return 1

    def rhs(self):
        return self._leaf

    def dot(self):
        return 0

    def is_complete(self):
        return True

    def is_incomplete(self):
        return False

    def nextsym(self):
        return None

    def token(self):
        return self._token

    def categ(self):
        return self._token.categ()

    def leaf(self):
        return self._leaf


class BinaryCombinatorRule(AbstractChartRule):
    """
    Class implementing application of a binary combinator to a chart.
    Takes the directed combinator to apply.
    """

    NUMEDGES = 2

    def __init__(self, combinator):
        self._combinator = combinator

    # Apply a combinator
    def apply(self, chart, grammar, left_edge, right_edge):
        # The left & right edges must be touching.
        if not (left_edge.end() == right_edge.start()):
            return

        # Check if the two edges are permitted to combine.
        # If so, generate the corresponding edge.
        if self._combinator.can_combine(left_edge.categ(), right_edge.categ()):
            for res in self._combinator.combine(left_edge.categ(), right_edge.categ()):
                new_edge = CCGEdge(
                    span=(left_edge.start(), right_edge.end()),
                    categ=res,
                    rule=self._combinator,
                )
                if chart.insert(new_edge, (left_edge, right_edge)):
                    yield new_edge

    # The representation of the combinator (for printing derivations)
    def __str__(self):
        return "%s" % self._combinator


# Type-raising must be handled slightly differently to the other rules, as the
# resulting rules only span a single edge, rather than both edges.


class ForwardTypeRaiseRule(AbstractChartRule):
    """
    Class for applying forward type raising
    """

    NUMEDGES = 2

    def __init__(self):
        self._combinator = ForwardT

    def apply(self, chart, grammar, left_edge, right_edge):
        if not (left_edge.end() == right_edge.start()):
            return

        for res in self._combinator.combine(left_edge.categ(), right_edge.categ()):
            new_edge = CCGEdge(span=left_edge.span(), categ=res, rule=self._combinator)
            if chart.insert(new_edge, (left_edge,)):
                yield new_edge

    def __str__(self):
        return "%s" % self._combinator


class BackwardTypeRaiseRule(AbstractChartRule):
    """
    Class for applying backward type raising.
    """

    NUMEDGES = 2

    def __init__(self):
        self._combinator = BackwardT

    def apply(self, chart, grammar, left_edge, right_edge):
        if not (left_edge.end() == right_edge.start()):
            return

        for res in self._combinator.combine(left_edge.categ(), right_edge.categ()):
            new_edge = CCGEdge(span=right_edge.span(), categ=res, rule=self._combinator)
            if chart.insert(new_edge, (right_edge,)):
                yield new_edge

    def __str__(self):
        return "%s" % self._combinator


# Common sets of combinators used for English derivations.
ApplicationRuleSet = [
    BinaryCombinatorRule(ForwardApplication),
    BinaryCombinatorRule(BackwardApplication),
]
CompositionRuleSet = [
    BinaryCombinatorRule(ForwardComposition),
    BinaryCombinatorRule(BackwardComposition),
    BinaryCombinatorRule(BackwardBx),
]
SubstitutionRuleSet = [
    BinaryCombinatorRule(ForwardSubstitution),
    BinaryCombinatorRule(BackwardSx),
]
TypeRaiseRuleSet = [ForwardTypeRaiseRule(), BackwardTypeRaiseRule()]

# The standard English rule set.
DefaultRuleSet = (
    ApplicationRuleSet + CompositionRuleSet + SubstitutionRuleSet + TypeRaiseRuleSet
)


class CCGChartParser(ParserI):
    """
    Chart parser for CCGs.
    Based largely on the ChartParser class from NLTK.
    """

    def __init__(self, lexicon, rules, trace=0):
        self._lexicon = lexicon
        self._rules = rules
        self._trace = trace

    def lexicon(self):
        return self._lexicon

    # Implements the CYK algorithm
    def parse(self, tokens):
        tokens = list(tokens)
        chart = CCGChart(list(tokens))
        lex = self._lexicon

        # Initialize leaf edges.
        for index in range(chart.num_leaves()):
            for token in lex.categories(chart.leaf(index)):
                new_edge = CCGLeafEdge(index, token, chart.leaf(index))
                chart.insert(new_edge, ())

        # Select a span for the new edges
        for span in range(2, chart.num_leaves() + 1):
            for start in range(0, chart.num_leaves() - span + 1):
                # Try all possible pairs of edges that could generate
                # an edge for that span
                for part in range(1, span):
                    lstart = start
                    mid = start + part
                    rend = start + span

                    for left in chart.select(span=(lstart, mid)):
                        for right in chart.select(span=(mid, rend)):
                            # Generate all possible combinations of the two edges
                            for rule in self._rules:
                                edges_added_by_rule = 0
                                for newedge in rule.apply(chart, lex, left, right):
                                    edges_added_by_rule += 1

        # Output the resulting parses
        return chart.parses(lex.start())


class CCGChart(Chart):
    def __init__(self, tokens):
        Chart.__init__(self, tokens)

    # Constructs the trees for a given parse. Unfortnunately, the parse trees need to be
    # constructed slightly differently to those in the default Chart class, so it has to
    # be reimplemented
    def _trees(self, edge, complete, memo, tree_class):
        assert complete, "CCGChart cannot build incomplete trees"

        if edge in memo:
            return memo[edge]

        if isinstance(edge, CCGLeafEdge):
            word = tree_class(edge.token(), [self._tokens[edge.start()]])
            leaf = tree_class((edge.token(), "Leaf"), [word])
            memo[edge] = [leaf]
            return [leaf]

        memo[edge] = []
        trees = []

        for cpl in self.child_pointer_lists(edge):
            child_choices = [self._trees(cp, complete, memo, tree_class) for cp in cpl]
            for children in itertools.product(*child_choices):
                lhs = (
                    Token(
                        self._tokens[edge.start() : edge.end()],
                        edge.lhs(),
                        compute_semantics(children, edge),
                    ),
                    str(edge.rule()),
                )
                trees.append(tree_class(lhs, children))

        memo[edge] = trees
        return trees


def compute_semantics(children, edge):
    if children[0].label()[0].semantics() is None:
        return None

    if len(children) == 2:
        if isinstance(edge.rule(), BackwardCombinator):
            children = [children[1], children[0]]

        combinator = edge.rule()._combinator
        function = children[0].label()[0].semantics()
        argument = children[1].label()[0].semantics()

        if isinstance(combinator, UndirectedFunctionApplication):
            return compute_function_semantics(function, argument)
        elif isinstance(combinator, UndirectedComposition):
            return compute_composition_semantics(function, argument)
        elif isinstance(combinator, UndirectedSubstitution):
            return compute_substitution_semantics(function, argument)
        else:
            raise AssertionError("Unsupported combinator '" + combinator + "'")
    else:
        return compute_type_raised_semantics(children[0].label()[0].semantics())


# --------
# Displaying derivations
# --------
def printCCGDerivation(tree):
    # Get the leaves and initial categories
    leafcats = tree.pos()
    leafstr = ""
    catstr = ""

    # Construct a string with both the leaf word and corresponding
    # category aligned.
    for leaf, cat in leafcats:
        str_cat = "%s" % cat
        nextlen = 2 + max(len(leaf), len(str_cat))
        lcatlen = (nextlen - len(str_cat)) // 2
        rcatlen = lcatlen + (nextlen - len(str_cat)) % 2
        catstr += " " * lcatlen + str_cat + " " * rcatlen
        lleaflen = (nextlen - len(leaf)) // 2
        rleaflen = lleaflen + (nextlen - len(leaf)) % 2
        leafstr += " " * lleaflen + leaf + " " * rleaflen
    print(leafstr.rstrip())
    print(catstr.rstrip())

    # Display the derivation steps
    printCCGTree(0, tree)


# Prints the sequence of derivation steps.
def printCCGTree(lwidth, tree):
    rwidth = lwidth

    # Is a leaf (word).
    # Increment the span by the space occupied by the leaf.
    if not isinstance(tree, Tree):
        return 2 + lwidth + len(tree)

    # Find the width of the current derivation step
    for child in tree:
        rwidth = max(rwidth, printCCGTree(rwidth, child))

    # Is a leaf node.
    # Don't print anything, but account for the space occupied.
    if not isinstance(tree.label(), tuple):
        return max(
            rwidth, 2 + lwidth + len("%s" % tree.label()), 2 + lwidth + len(tree[0])
        )

    (token, op) = tree.label()

    if op == "Leaf":
        return rwidth

    # Pad to the left with spaces, followed by a sequence of '-'
    # and the derivation rule.
    print(lwidth * " " + (rwidth - lwidth) * "-" + "%s" % op)
    # Print the resulting category on a new line.
    str_res = "%s" % (token.categ())
    if token.semantics() is not None:
        str_res += " {" + str(token.semantics()) + "}"
    respadlen = (rwidth - lwidth - len(str_res)) // 2 + lwidth
    print(respadlen * " " + str_res)
    return rwidth


### Demonstration code

# Construct the lexicon
lex = fromstring(
    """
    :- S, NP, N, VP    # Primitive categories, S is the target primitive

    Det :: NP/N         # Family of words
    Pro :: NP
    TV :: VP/NP
    Modal :: (S\\NP)/VP # Backslashes need to be escaped

    I => Pro             # Word -> Category mapping
    you => Pro

    the => Det

    # Variables have the special keyword 'var'
    # '.' prevents permutation
    # ',' prevents composition
    and => var\\.,var/.,var

    which => (N\\N)/(S/NP)

    will => Modal # Categories can be either explicit, or families.
    might => Modal

    cook => TV
    eat => TV

    mushrooms => N
    parsnips => N
    bacon => N
    """
)


def demo():
    parser = CCGChartParser(lex, DefaultRuleSet)
    for parse in parser.parse("I might cook and eat the bacon".split()):
        printCCGDerivation(parse)


if __name__ == "__main__":
    demo()

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\rich\box.py ===
import sys
from typing import TYPE_CHECKING, Iterable, List

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from pip._vendor.typing_extensions import Literal  # pragma: no cover


from ._loop import loop_last

if TYPE_CHECKING:
    from pip._vendor.rich.console import ConsoleOptions


class Box:
    """Defines characters to render boxes.

    ┌─┬┐ top
    │ ││ head
    ├─┼┤ head_row
    │ ││ mid
    ├─┼┤ row
    ├─┼┤ foot_row
    │ ││ foot
    └─┴┘ bottom

    Args:
        box (str): Characters making up box.
        ascii (bool, optional): True if this box uses ascii characters only. Default is False.
    """

    def __init__(self, box: str, *, ascii: bool = False) -> None:
        self._box = box
        self.ascii = ascii
        line1, line2, line3, line4, line5, line6, line7, line8 = box.splitlines()
        # top
        self.top_left, self.top, self.top_divider, self.top_right = iter(line1)
        # head
        self.head_left, _, self.head_vertical, self.head_right = iter(line2)
        # head_row
        (
            self.head_row_left,
            self.head_row_horizontal,
            self.head_row_cross,
            self.head_row_right,
        ) = iter(line3)

        # mid
        self.mid_left, _, self.mid_vertical, self.mid_right = iter(line4)
        # row
        self.row_left, self.row_horizontal, self.row_cross, self.row_right = iter(line5)
        # foot_row
        (
            self.foot_row_left,
            self.foot_row_horizontal,
            self.foot_row_cross,
            self.foot_row_right,
        ) = iter(line6)
        # foot
        self.foot_left, _, self.foot_vertical, self.foot_right = iter(line7)
        # bottom
        self.bottom_left, self.bottom, self.bottom_divider, self.bottom_right = iter(
            line8
        )

    def __repr__(self) -> str:
        return "Box(...)"

    def __str__(self) -> str:
        return self._box

    def substitute(self, options: "ConsoleOptions", safe: bool = True) -> "Box":
        """Substitute this box for another if it won't render due to platform issues.

        Args:
            options (ConsoleOptions): Console options used in rendering.
            safe (bool, optional): Substitute this for another Box if there are known problems
                displaying on the platform (currently only relevant on Windows). Default is True.

        Returns:
            Box: A different Box or the same Box.
        """
        box = self
        if options.legacy_windows and safe:
            box = LEGACY_WINDOWS_SUBSTITUTIONS.get(box, box)
        if options.ascii_only and not box.ascii:
            box = ASCII
        return box

    def get_plain_headed_box(self) -> "Box":
        """If this box uses special characters for the borders of the header, then
        return the equivalent box that does not.

        Returns:
            Box: The most similar Box that doesn't use header-specific box characters.
                If the current Box already satisfies this criterion, then it's returned.
        """
        return PLAIN_HEADED_SUBSTITUTIONS.get(self, self)

    def get_top(self, widths: Iterable[int]) -> str:
        """Get the top of a simple box.

        Args:
            widths (List[int]): Widths of columns.

        Returns:
            str: A string of box characters.
        """

        parts: List[str] = []
        append = parts.append
        append(self.top_left)
        for last, width in loop_last(widths):
            append(self.top * width)
            if not last:
                append(self.top_divider)
        append(self.top_right)
        return "".join(parts)

    def get_row(
        self,
        widths: Iterable[int],
        level: Literal["head", "row", "foot", "mid"] = "row",
        edge: bool = True,
    ) -> str:
        """Get the top of a simple box.

        Args:
            width (List[int]): Widths of columns.

        Returns:
            str: A string of box characters.
        """
        if level == "head":
            left = self.head_row_left
            horizontal = self.head_row_horizontal
            cross = self.head_row_cross
            right = self.head_row_right
        elif level == "row":
            left = self.row_left
            horizontal = self.row_horizontal
            cross = self.row_cross
            right = self.row_right
        elif level == "mid":
            left = self.mid_left
            horizontal = " "
            cross = self.mid_vertical
            right = self.mid_right
        elif level == "foot":
            left = self.foot_row_left
            horizontal = self.foot_row_horizontal
            cross = self.foot_row_cross
            right = self.foot_row_right
        else:
            raise ValueError("level must be 'head', 'row' or 'foot'")

        parts: List[str] = []
        append = parts.append
        if edge:
            append(left)
        for last, width in loop_last(widths):
            append(horizontal * width)
            if not last:
                append(cross)
        if edge:
            append(right)
        return "".join(parts)

    def get_bottom(self, widths: Iterable[int]) -> str:
        """Get the bottom of a simple box.

        Args:
            widths (List[int]): Widths of columns.

        Returns:
            str: A string of box characters.
        """

        parts: List[str] = []
        append = parts.append
        append(self.bottom_left)
        for last, width in loop_last(widths):
            append(self.bottom * width)
            if not last:
                append(self.bottom_divider)
        append(self.bottom_right)
        return "".join(parts)


# fmt: off
ASCII: Box = Box(
    "+--+\n"
    "| ||\n"
    "|-+|\n"
    "| ||\n"
    "|-+|\n"
    "|-+|\n"
    "| ||\n"
    "+--+\n",
    ascii=True,
)

ASCII2: Box = Box(
    "+-++\n"
    "| ||\n"
    "+-++\n"
    "| ||\n"
    "+-++\n"
    "+-++\n"
    "| ||\n"
    "+-++\n",
    ascii=True,
)

ASCII_DOUBLE_HEAD: Box = Box(
    "+-++\n"
    "| ||\n"
    "+=++\n"
    "| ||\n"
    "+-++\n"
    "+-++\n"
    "| ||\n"
    "+-++\n",
    ascii=True,
)

SQUARE: Box = Box(
    "┌─┬┐\n"
    "│ ││\n"
    "├─┼┤\n"
    "│ ││\n"
    "├─┼┤\n"
    "├─┼┤\n"
    "│ ││\n"
    "└─┴┘\n"
)

SQUARE_DOUBLE_HEAD: Box = Box(
    "┌─┬┐\n"
    "│ ││\n"
    "╞═╪╡\n"
    "│ ││\n"
    "├─┼┤\n"
    "├─┼┤\n"
    "│ ││\n"
    "└─┴┘\n"
)

MINIMAL: Box = Box(
    "  ╷ \n"
    "  │ \n"
    "╶─┼╴\n"
    "  │ \n"
    "╶─┼╴\n"
    "╶─┼╴\n"
    "  │ \n"
    "  ╵ \n"
)


MINIMAL_HEAVY_HEAD: Box = Box(
    "  ╷ \n"
    "  │ \n"
    "╺━┿╸\n"
    "  │ \n"
    "╶─┼╴\n"
    "╶─┼╴\n"
    "  │ \n"
    "  ╵ \n"
)

MINIMAL_DOUBLE_HEAD: Box = Box(
    "  ╷ \n"
    "  │ \n"
    " ═╪ \n"
    "  │ \n"
    " ─┼ \n"
    " ─┼ \n"
    "  │ \n"
    "  ╵ \n"
)


SIMPLE: Box = Box(
    "    \n"
    "    \n"
    " ── \n"
    "    \n"
    "    \n"
    " ── \n"
    "    \n"
    "    \n"
)

SIMPLE_HEAD: Box = Box(
    "    \n"
    "    \n"
    " ── \n"
    "    \n"
    "    \n"
    "    \n"
    "    \n"
    "    \n"
)


SIMPLE_HEAVY: Box = Box(
    "    \n"
    "    \n"
    " ━━ \n"
    "    \n"
    "    \n"
    " ━━ \n"
    "    \n"
    "    \n"
)


HORIZONTALS: Box = Box(
    " ── \n"
    "    \n"
    " ── \n"
    "    \n"
    " ── \n"
    " ── \n"
    "    \n"
    " ── \n"
)

ROUNDED: Box = Box(
    "╭─┬╮\n"
    "│ ││\n"
    "├─┼┤\n"
    "│ ││\n"
    "├─┼┤\n"
    "├─┼┤\n"
    "│ ││\n"
    "╰─┴╯\n"
)

HEAVY: Box = Box(
    "┏━┳┓\n"
    "┃ ┃┃\n"
    "┣━╋┫\n"
    "┃ ┃┃\n"
    "┣━╋┫\n"
    "┣━╋┫\n"
    "┃ ┃┃\n"
    "┗━┻┛\n"
)

HEAVY_EDGE: Box = Box(
    "┏━┯┓\n"
    "┃ │┃\n"
    "┠─┼┨\n"
    "┃ │┃\n"
    "┠─┼┨\n"
    "┠─┼┨\n"
    "┃ │┃\n"
    "┗━┷┛\n"
)

HEAVY_HEAD: Box = Box(
    "┏━┳┓\n"
    "┃ ┃┃\n"
    "┡━╇┩\n"
    "│ ││\n"
    "├─┼┤\n"
    "├─┼┤\n"
    "│ ││\n"
    "└─┴┘\n"
)

DOUBLE: Box = Box(
    "╔═╦╗\n"
    "║ ║║\n"
    "╠═╬╣\n"
    "║ ║║\n"
    "╠═╬╣\n"
    "╠═╬╣\n"
    "║ ║║\n"
    "╚═╩╝\n"
)

DOUBLE_EDGE: Box = Box(
    "╔═╤╗\n"
    "║ │║\n"
    "╟─┼╢\n"
    "║ │║\n"
    "╟─┼╢\n"
    "╟─┼╢\n"
    "║ │║\n"
    "╚═╧╝\n"
)

MARKDOWN: Box = Box(
    "    \n"
    "| ||\n"
    "|-||\n"
    "| ||\n"
    "|-||\n"
    "|-||\n"
    "| ||\n"
    "    \n",
    ascii=True,
)
# fmt: on

# Map Boxes that don't render with raster fonts on to equivalent that do
LEGACY_WINDOWS_SUBSTITUTIONS = {
    ROUNDED: SQUARE,
    MINIMAL_HEAVY_HEAD: MINIMAL,
    SIMPLE_HEAVY: SIMPLE,
    HEAVY: SQUARE,
    HEAVY_EDGE: SQUARE,
    HEAVY_HEAD: SQUARE,
}

# Map headed boxes to their headerless equivalents
PLAIN_HEADED_SUBSTITUTIONS = {
    HEAVY_HEAD: SQUARE,
    SQUARE_DOUBLE_HEAD: SQUARE,
    MINIMAL_DOUBLE_HEAD: MINIMAL,
    MINIMAL_HEAVY_HEAD: MINIMAL,
    ASCII_DOUBLE_HEAD: ASCII2,
}


if __name__ == "__main__":  # pragma: no cover
    from pip._vendor.rich.columns import Columns
    from pip._vendor.rich.panel import Panel

    from . import box as box
    from .console import Console
    from .table import Table
    from .text import Text

    console = Console(record=True)

    BOXES = [
        "ASCII",
        "ASCII2",
        "ASCII_DOUBLE_HEAD",
        "SQUARE",
        "SQUARE_DOUBLE_HEAD",
        "MINIMAL",
        "MINIMAL_HEAVY_HEAD",
        "MINIMAL_DOUBLE_HEAD",
        "SIMPLE",
        "SIMPLE_HEAD",
        "SIMPLE_HEAVY",
        "HORIZONTALS",
        "ROUNDED",
        "HEAVY",
        "HEAVY_EDGE",
        "HEAVY_HEAD",
        "DOUBLE",
        "DOUBLE_EDGE",
        "MARKDOWN",
    ]

    console.print(Panel("[bold green]Box Constants", style="green"), justify="center")
    console.print()

    columns = Columns(expand=True, padding=2)
    for box_name in sorted(BOXES):
        table = Table(
            show_footer=True, style="dim", border_style="not dim", expand=True
        )
        table.add_column("Header 1", "Footer 1")
        table.add_column("Header 2", "Footer 2")
        table.add_row("Cell", "Cell")
        table.add_row("Cell", "Cell")
        table.box = getattr(box, box_name)
        table.title = Text(f"box.{box_name}", style="magenta")
        columns.add_renderable(table)
    console.print(columns)

    # console.save_svg("box.svg")

# === NexusCore/openenv\Lib\site-packages\fontTools\ttx.py ===
"""\
usage: ttx [options] inputfile1 [... inputfileN]

TTX -- From OpenType To XML And Back

If an input file is a TrueType or OpenType font file, it will be
decompiled to a TTX file (an XML-based text format).
If an input file is a TTX file, it will be compiled to whatever
format the data is in, a TrueType or OpenType/CFF font file.
A special input value of - means read from the standard input.

Output files are created so they are unique: an existing file is
never overwritten.

General options
===============

-h Help            print this message.
--version          show version and exit.
-d <outputfolder>  Specify a directory where the output files are
                   to be created.
-o <outputfile>    Specify a file to write the output to. A special
                   value of - would use the standard output.
-f                 Overwrite existing output file(s), ie. don't append
                   numbers.
-v                 Verbose: more messages will be written to stdout
                   about what is being done.
-q                 Quiet: No messages will be written to stdout about
                   what is being done.
-a                 allow virtual glyphs ID's on compile or decompile.

Dump options
============

-l           List table info: instead of dumping to a TTX file, list
             some minimal info about each table.
-t <table>   Specify a table to dump. Multiple -t options
             are allowed. When no -t option is specified, all tables
             will be dumped.
-x <table>   Specify a table to exclude from the dump. Multiple
             -x options are allowed. -t and -x are mutually exclusive.
-s           Split tables: save the TTX data into separate TTX files per
             table and write one small TTX file that contains references
             to the individual table dumps. This file can be used as
             input to ttx, as long as the table files are in the
             same directory.
-g           Split glyf table: Save the glyf data into separate TTX files
             per glyph and write a small TTX for the glyf table which
             contains references to the individual TTGlyph elements.
             NOTE: specifying -g implies -s (no need for -s together
             with -g)
-i           Do NOT disassemble TT instructions: when this option is
             given, all TrueType programs (glyph programs, the font
             program and the pre-program) will be written to the TTX
             file as hex data instead of assembly. This saves some time
             and makes the TTX file smaller.
-z <format>  Specify a bitmap data export option for EBDT:
             {'raw', 'row', 'bitwise', 'extfile'} or for the CBDT:
             {'raw', 'extfile'} Each option does one of the following:

             -z raw
               export the bitmap data as a hex dump
             -z row
               export each row as hex data
             -z bitwise
               export each row as binary in an ASCII art style
             -z extfile
               export the data as external files with XML references

             If no export format is specified 'raw' format is used.
-e           Don't ignore decompilation errors, but show a full traceback
             and abort.
-y <number>  Select font number for TrueType Collection (.ttc/.otc),
             starting from 0.
--unicodedata <UnicodeData.txt>
             Use custom database file to write character names in the
             comments of the cmap TTX output.
--newline <value>
             Control how line endings are written in the XML file. It
             can be 'LF', 'CR', or 'CRLF'. If not specified, the
             default platform-specific line endings are used.

Compile options
===============

-m           Merge with TrueType-input-file: specify a TrueType or
             OpenType font file to be merged with the TTX file. This
             option is only valid when at most one TTX file is specified.
-b           Don't recalc glyph bounding boxes: use the values in the
             TTX file as-is.
--recalc-timestamp
             Set font 'modified' timestamp to current time.
             By default, the modification time of the TTX file will be
             used.
--no-recalc-timestamp
             Keep the original font 'modified' timestamp.
--flavor <type>
             Specify flavor of output font file. May be 'woff' or 'woff2'.
             Note that WOFF2 requires the Brotli Python extension,
             available at https://github.com/google/brotli
--with-zopfli
             Use Zopfli instead of Zlib to compress WOFF. The Python
             extension is available at https://pypi.python.org/pypi/zopfli
--optimize-font-speed
             Enable optimizations that prioritize speed over file size.
             This mainly affects how glyf t able and gvar / VARC tables are
             compiled. The produced fonts will be larger, but rendering
             performance will be improved with HarfBuzz and other text
             layout engines.
"""

from fontTools.ttLib import OPTIMIZE_FONT_SPEED, TTFont, TTLibError
from fontTools.misc.macCreatorType import getMacCreatorAndType
from fontTools.unicode import setUnicodeData
from fontTools.misc.textTools import Tag, tostr
from fontTools.misc.timeTools import timestampSinceEpoch
from fontTools.misc.loggingTools import Timer
from fontTools.misc.cliTools import makeOutputFileName
import os
import sys
import getopt
import re
import logging


log = logging.getLogger("fontTools.ttx")

opentypeheaderRE = re.compile("""sfntVersion=['"]OTTO["']""")


class Options(object):
    listTables = False
    outputDir = None
    outputFile = None
    overWrite = False
    verbose = False
    quiet = False
    splitTables = False
    splitGlyphs = False
    disassembleInstructions = True
    mergeFile = None
    recalcBBoxes = True
    ignoreDecompileErrors = True
    bitmapGlyphDataFormat = "raw"
    unicodedata = None
    newlinestr = "\n"
    recalcTimestamp = None
    flavor = None
    useZopfli = False
    optimizeFontSpeed = False

    def __init__(self, rawOptions, numFiles):
        self.onlyTables = []
        self.skipTables = []
        self.fontNumber = -1
        for option, value in rawOptions:
            # general options
            if option == "-h":
                print(__doc__)
                sys.exit(0)
            elif option == "--version":
                from fontTools import version

                print(version)
                sys.exit(0)
            elif option == "-d":
                if not os.path.isdir(value):
                    raise getopt.GetoptError(
                        "The -d option value must be an existing directory"
                    )
                self.outputDir = value
            elif option == "-o":
                self.outputFile = value
            elif option == "-f":
                self.overWrite = True
            elif option == "-v":
                self.verbose = True
            elif option == "-q":
                self.quiet = True
            # dump options
            elif option == "-l":
                self.listTables = True
            elif option == "-t":
                # pad with space if table tag length is less than 4
                value = value.ljust(4)
                self.onlyTables.append(value)
            elif option == "-x":
                # pad with space if table tag length is less than 4
                value = value.ljust(4)
                self.skipTables.append(value)
            elif option == "-s":
                self.splitTables = True
            elif option == "-g":
                # -g implies (and forces) splitTables
                self.splitGlyphs = True
                self.splitTables = True
            elif option == "-i":
                self.disassembleInstructions = False
            elif option == "-z":
                validOptions = ("raw", "row", "bitwise", "extfile")
                if value not in validOptions:
                    raise getopt.GetoptError(
                        "-z does not allow %s as a format. Use %s"
                        % (option, validOptions)
                    )
                self.bitmapGlyphDataFormat = value
            elif option == "-y":
                self.fontNumber = int(value)
            # compile options
            elif option == "-m":
                self.mergeFile = value
            elif option == "-b":
                self.recalcBBoxes = False
            elif option == "-e":
                self.ignoreDecompileErrors = False
            elif option == "--unicodedata":
                self.unicodedata = value
            elif option == "--newline":
                validOptions = ("LF", "CR", "CRLF")
                if value == "LF":
                    self.newlinestr = "\n"
                elif value == "CR":
                    self.newlinestr = "\r"
                elif value == "CRLF":
                    self.newlinestr = "\r\n"
                else:
                    raise getopt.GetoptError(
                        "Invalid choice for --newline: %r (choose from %s)"
                        % (value, ", ".join(map(repr, validOptions)))
                    )
            elif option == "--recalc-timestamp":
                self.recalcTimestamp = True
            elif option == "--no-recalc-timestamp":
                self.recalcTimestamp = False
            elif option == "--flavor":
                self.flavor = value
            elif option == "--with-zopfli":
                self.useZopfli = True
            elif option == "--optimize-font-speed":
                self.optimizeFontSpeed = True
        if self.verbose and self.quiet:
            raise getopt.GetoptError("-q and -v options are mutually exclusive")
        if self.verbose:
            self.logLevel = logging.DEBUG
        elif self.quiet:
            self.logLevel = logging.WARNING
        else:
            self.logLevel = logging.INFO
        if self.mergeFile and self.flavor:
            raise getopt.GetoptError("-m and --flavor options are mutually exclusive")
        if self.onlyTables and self.skipTables:
            raise getopt.GetoptError("-t and -x options are mutually exclusive")
        if self.mergeFile and numFiles > 1:
            raise getopt.GetoptError(
                "Must specify exactly one TTX source file when using -m"
            )
        if self.flavor != "woff" and self.useZopfli:
            raise getopt.GetoptError("--with-zopfli option requires --flavor 'woff'")


def ttList(input, output, options):
    ttf = TTFont(input, fontNumber=options.fontNumber, lazy=True)
    reader = ttf.reader
    tags = sorted(reader.keys())
    print('Listing table info for "%s":' % input)
    format = "    %4s  %10s  %8s  %8s"
    print(format % ("tag ", "  checksum", "  length", "  offset"))
    print(format % ("----", "----------", "--------", "--------"))
    for tag in tags:
        entry = reader.tables[tag]
        if ttf.flavor == "woff2":
            # WOFF2 doesn't store table checksums, so they must be calculated
            from fontTools.ttLib.sfnt import calcChecksum

            data = entry.loadData(reader.transformBuffer)
            checkSum = calcChecksum(data)
        else:
            checkSum = int(entry.checkSum)
        if checkSum < 0:
            checkSum = checkSum + 0x100000000
        checksum = "0x%08X" % checkSum
        print(format % (tag, checksum, entry.length, entry.offset))
    print()
    ttf.close()


@Timer(log, "Done dumping TTX in %(time).3f seconds")
def ttDump(input, output, options):
    input_name = input
    if input == "-":
        input, input_name = sys.stdin.buffer, sys.stdin.name
    output_name = output
    if output == "-":
        output, output_name = sys.stdout, sys.stdout.name
    log.info('Dumping "%s" to "%s"...', input_name, output_name)
    if options.unicodedata:
        setUnicodeData(options.unicodedata)
    ttf = TTFont(
        input,
        0,
        ignoreDecompileErrors=options.ignoreDecompileErrors,
        fontNumber=options.fontNumber,
    )
    ttf.saveXML(
        output,
        tables=options.onlyTables,
        skipTables=options.skipTables,
        splitTables=options.splitTables,
        splitGlyphs=options.splitGlyphs,
        disassembleInstructions=options.disassembleInstructions,
        bitmapGlyphDataFormat=options.bitmapGlyphDataFormat,
        newlinestr=options.newlinestr,
    )
    ttf.close()


@Timer(log, "Done compiling TTX in %(time).3f seconds")
def ttCompile(input, output, options):
    input_name = input
    if input == "-":
        input, input_name = sys.stdin, sys.stdin.name
    output_name = output
    if output == "-":
        output, output_name = sys.stdout.buffer, sys.stdout.name
    log.info('Compiling "%s" to "%s"...' % (input_name, output))
    if options.useZopfli:
        from fontTools.ttLib import sfnt

        sfnt.USE_ZOPFLI = True
    ttf = TTFont(
        options.mergeFile,
        flavor=options.flavor,
        recalcBBoxes=options.recalcBBoxes,
        recalcTimestamp=options.recalcTimestamp,
    )
    if options.optimizeFontSpeed:
        ttf.cfg[OPTIMIZE_FONT_SPEED] = options.optimizeFontSpeed
    ttf.importXML(input)

    if options.recalcTimestamp is None and "head" in ttf and input is not sys.stdin:
        # use TTX file modification time for head "modified" timestamp
        mtime = os.path.getmtime(input)
        ttf["head"].modified = timestampSinceEpoch(mtime)

    ttf.save(output)


def guessFileType(fileName):
    if fileName == "-":
        header = sys.stdin.buffer.peek(256)
        ext = ""
    else:
        base, ext = os.path.splitext(fileName)
        try:
            with open(fileName, "rb") as f:
                header = f.read(256)
        except IOError:
            return None

    if header.startswith(b"\xef\xbb\xbf<?xml"):
        header = header.lstrip(b"\xef\xbb\xbf")
    cr, tp = getMacCreatorAndType(fileName)
    if tp in ("sfnt", "FFIL"):
        return "TTF"
    if ext == ".dfont":
        return "TTF"
    head = Tag(header[:4])
    if head == "OTTO":
        return "OTF"
    elif head == "ttcf":
        return "TTC"
    elif head in ("\0\1\0\0", "true"):
        return "TTF"
    elif head == "wOFF":
        return "WOFF"
    elif head == "wOF2":
        return "WOFF2"
    elif head == "<?xm":
        # Use 'latin1' because that can't fail.
        header = tostr(header, "latin1")
        if opentypeheaderRE.search(header):
            return "OTX"
        else:
            return "TTX"
    return None


def parseOptions(args):
    rawOptions, files = getopt.gnu_getopt(
        args,
        "ld:o:fvqht:x:sgim:z:baey:",
        [
            "unicodedata=",
            "recalc-timestamp",
            "no-recalc-timestamp",
            "flavor=",
            "version",
            "with-zopfli",
            "newline=",
            "optimize-font-speed",
        ],
    )

    options = Options(rawOptions, len(files))
    jobs = []

    if not files:
        raise getopt.GetoptError("Must specify at least one input file")

    for input in files:
        if input != "-" and not os.path.isfile(input):
            raise getopt.GetoptError('File not found: "%s"' % input)
        tp = guessFileType(input)
        if tp in ("OTF", "TTF", "TTC", "WOFF", "WOFF2"):
            extension = ".ttx"
            if options.listTables:
                action = ttList
            else:
                action = ttDump
        elif tp == "TTX":
            extension = "." + options.flavor if options.flavor else ".ttf"
            action = ttCompile
        elif tp == "OTX":
            extension = "." + options.flavor if options.flavor else ".otf"
            action = ttCompile
        else:
            raise getopt.GetoptError('Unknown file type: "%s"' % input)

        if options.outputFile:
            output = options.outputFile
        else:
            if input == "-":
                raise getopt.GetoptError("Must provide -o when reading from stdin")
            output = makeOutputFileName(
                input, options.outputDir, extension, options.overWrite
            )
            # 'touch' output file to avoid race condition in choosing file names
            if action != ttList:
                open(output, "a").close()
        jobs.append((action, input, output))
    return jobs, options


def process(jobs, options):
    for action, input, output in jobs:
        action(input, output, options)


def main(args=None):
    """Convert OpenType fonts to XML and back"""
    from fontTools import configLogger

    if args is None:
        args = sys.argv[1:]
    try:
        jobs, options = parseOptions(args)
    except getopt.GetoptError as e:
        print("%s\nERROR: %s" % (__doc__, e), file=sys.stderr)
        sys.exit(2)

    configLogger(level=options.logLevel)

    try:
        process(jobs, options)
    except KeyboardInterrupt:
        log.error("(Cancelled.)")
        sys.exit(1)
    except SystemExit:
        raise
    except TTLibError as e:
        log.error(e)
        sys.exit(1)
    except:
        log.exception("Unhandled exception has occurred")
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())

# === NexusCore/openenv\Lib\site-packages\urllib3\_collections.py ===
from __future__ import annotations

import typing
from collections import OrderedDict
from enum import Enum, auto
from threading import RLock

if typing.TYPE_CHECKING:
    # We can only import Protocol if TYPE_CHECKING because it's a development
    # dependency, and is not available at runtime.
    from typing import Protocol

    from typing_extensions import Self

    class HasGettableStringKeys(Protocol):
        def keys(self) -> typing.Iterator[str]: ...

        def __getitem__(self, key: str) -> str: ...


__all__ = ["RecentlyUsedContainer", "HTTPHeaderDict"]


# Key type
_KT = typing.TypeVar("_KT")
# Value type
_VT = typing.TypeVar("_VT")
# Default type
_DT = typing.TypeVar("_DT")

ValidHTTPHeaderSource = typing.Union[
    "HTTPHeaderDict",
    typing.Mapping[str, str],
    typing.Iterable[tuple[str, str]],
    "HasGettableStringKeys",
]


class _Sentinel(Enum):
    not_passed = auto()


def ensure_can_construct_http_header_dict(
    potential: object,
) -> ValidHTTPHeaderSource | None:
    if isinstance(potential, HTTPHeaderDict):
        return potential
    elif isinstance(potential, typing.Mapping):
        # Full runtime checking of the contents of a Mapping is expensive, so for the
        # purposes of typechecking, we assume that any Mapping is the right shape.
        return typing.cast(typing.Mapping[str, str], potential)
    elif isinstance(potential, typing.Iterable):
        # Similarly to Mapping, full runtime checking of the contents of an Iterable is
        # expensive, so for the purposes of typechecking, we assume that any Iterable
        # is the right shape.
        return typing.cast(typing.Iterable[tuple[str, str]], potential)
    elif hasattr(potential, "keys") and hasattr(potential, "__getitem__"):
        return typing.cast("HasGettableStringKeys", potential)
    else:
        return None


class RecentlyUsedContainer(typing.Generic[_KT, _VT], typing.MutableMapping[_KT, _VT]):
    """
    Provides a thread-safe dict-like container which maintains up to
    ``maxsize`` keys while throwing away the least-recently-used keys beyond
    ``maxsize``.

    :param maxsize:
        Maximum number of recent elements to retain.

    :param dispose_func:
        Every time an item is evicted from the container,
        ``dispose_func(value)`` is called.  Callback which will get called
    """

    _container: typing.OrderedDict[_KT, _VT]
    _maxsize: int
    dispose_func: typing.Callable[[_VT], None] | None
    lock: RLock

    def __init__(
        self,
        maxsize: int = 10,
        dispose_func: typing.Callable[[_VT], None] | None = None,
    ) -> None:
        super().__init__()
        self._maxsize = maxsize
        self.dispose_func = dispose_func
        self._container = OrderedDict()
        self.lock = RLock()

    def __getitem__(self, key: _KT) -> _VT:
        # Re-insert the item, moving it to the end of the eviction line.
        with self.lock:
            item = self._container.pop(key)
            self._container[key] = item
            return item

    def __setitem__(self, key: _KT, value: _VT) -> None:
        evicted_item = None
        with self.lock:
            # Possibly evict the existing value of 'key'
            try:
                # If the key exists, we'll overwrite it, which won't change the
                # size of the pool. Because accessing a key should move it to
                # the end of the eviction line, we pop it out first.
                evicted_item = key, self._container.pop(key)
                self._container[key] = value
            except KeyError:
                # When the key does not exist, we insert the value first so that
                # evicting works in all cases, including when self._maxsize is 0
                self._container[key] = value
                if len(self._container) > self._maxsize:
                    # If we didn't evict an existing value, and we've hit our maximum
                    # size, then we have to evict the least recently used item from
                    # the beginning of the container.
                    evicted_item = self._container.popitem(last=False)

        # After releasing the lock on the pool, dispose of any evicted value.
        if evicted_item is not None and self.dispose_func:
            _, evicted_value = evicted_item
            self.dispose_func(evicted_value)

    def __delitem__(self, key: _KT) -> None:
        with self.lock:
            value = self._container.pop(key)

        if self.dispose_func:
            self.dispose_func(value)

    def __len__(self) -> int:
        with self.lock:
            return len(self._container)

    def __iter__(self) -> typing.NoReturn:
        raise NotImplementedError(
            "Iteration over this class is unlikely to be threadsafe."
        )

    def clear(self) -> None:
        with self.lock:
            # Copy pointers to all values, then wipe the mapping
            values = list(self._container.values())
            self._container.clear()

        if self.dispose_func:
            for value in values:
                self.dispose_func(value)

    def keys(self) -> set[_KT]:  # type: ignore[override]
        with self.lock:
            return set(self._container.keys())


class HTTPHeaderDictItemView(set[tuple[str, str]]):
    """
    HTTPHeaderDict is unusual for a Mapping[str, str] in that it has two modes of
    address.

    If we directly try to get an item with a particular name, we will get a string
    back that is the concatenated version of all the values:

    >>> d['X-Header-Name']
    'Value1, Value2, Value3'

    However, if we iterate over an HTTPHeaderDict's items, we will optionally combine
    these values based on whether combine=True was called when building up the dictionary

    >>> d = HTTPHeaderDict({"A": "1", "B": "foo"})
    >>> d.add("A", "2", combine=True)
    >>> d.add("B", "bar")
    >>> list(d.items())
    [
        ('A', '1, 2'),
        ('B', 'foo'),
        ('B', 'bar'),
    ]

    This class conforms to the interface required by the MutableMapping ABC while
    also giving us the nonstandard iteration behavior we want; items with duplicate
    keys, ordered by time of first insertion.
    """

    _headers: HTTPHeaderDict

    def __init__(self, headers: HTTPHeaderDict) -> None:
        self._headers = headers

    def __len__(self) -> int:
        return len(list(self._headers.iteritems()))

    def __iter__(self) -> typing.Iterator[tuple[str, str]]:
        return self._headers.iteritems()

    def __contains__(self, item: object) -> bool:
        if isinstance(item, tuple) and len(item) == 2:
            passed_key, passed_val = item
            if isinstance(passed_key, str) and isinstance(passed_val, str):
                return self._headers._has_value_for_header(passed_key, passed_val)
        return False


class HTTPHeaderDict(typing.MutableMapping[str, str]):
    """
    :param headers:
        An iterable of field-value pairs. Must not contain multiple field names
        when compared case-insensitively.

    :param kwargs:
        Additional field-value pairs to pass in to ``dict.update``.

    A ``dict`` like container for storing HTTP Headers.

    Field names are stored and compared case-insensitively in compliance with
    RFC 7230. Iteration provides the first case-sensitive key seen for each
    case-insensitive pair.

    Using ``__setitem__`` syntax overwrites fields that compare equal
    case-insensitively in order to maintain ``dict``'s api. For fields that
    compare equal, instead create a new ``HTTPHeaderDict`` and use ``.add``
    in a loop.

    If multiple fields that are equal case-insensitively are passed to the
    constructor or ``.update``, the behavior is undefined and some will be
    lost.

    >>> headers = HTTPHeaderDict()
    >>> headers.add('Set-Cookie', 'foo=bar')
    >>> headers.add('set-cookie', 'baz=quxx')
    >>> headers['content-length'] = '7'
    >>> headers['SET-cookie']
    'foo=bar, baz=quxx'
    >>> headers['Content-Length']
    '7'
    """

    _container: typing.MutableMapping[str, list[str]]

    def __init__(self, headers: ValidHTTPHeaderSource | None = None, **kwargs: str):
        super().__init__()
        self._container = {}  # 'dict' is insert-ordered
        if headers is not None:
            if isinstance(headers, HTTPHeaderDict):
                self._copy_from(headers)
            else:
                self.extend(headers)
        if kwargs:
            self.extend(kwargs)

    def __setitem__(self, key: str, val: str) -> None:
        # avoid a bytes/str comparison by decoding before httplib
        if isinstance(key, bytes):
            key = key.decode("latin-1")
        self._container[key.lower()] = [key, val]

    def __getitem__(self, key: str) -> str:
        val = self._container[key.lower()]
        return ", ".join(val[1:])

    def __delitem__(self, key: str) -> None:
        del self._container[key.lower()]

    def __contains__(self, key: object) -> bool:
        if isinstance(key, str):
            return key.lower() in self._container
        return False

    def setdefault(self, key: str, default: str = "") -> str:
        return super().setdefault(key, default)

    def __eq__(self, other: object) -> bool:
        maybe_constructable = ensure_can_construct_http_header_dict(other)
        if maybe_constructable is None:
            return False
        else:
            other_as_http_header_dict = type(self)(maybe_constructable)

        return {k.lower(): v for k, v in self.itermerged()} == {
            k.lower(): v for k, v in other_as_http_header_dict.itermerged()
        }

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __len__(self) -> int:
        return len(self._container)

    def __iter__(self) -> typing.Iterator[str]:
        # Only provide the originally cased names
        for vals in self._container.values():
            yield vals[0]

    def discard(self, key: str) -> None:
        try:
            del self[key]
        except KeyError:
            pass

    def add(self, key: str, val: str, *, combine: bool = False) -> None:
        """Adds a (name, value) pair, doesn't overwrite the value if it already
        exists.

        If this is called with combine=True, instead of adding a new header value
        as a distinct item during iteration, this will instead append the value to
        any existing header value with a comma. If no existing header value exists
        for the key, then the value will simply be added, ignoring the combine parameter.

        >>> headers = HTTPHeaderDict(foo='bar')
        >>> headers.add('Foo', 'baz')
        >>> headers['foo']
        'bar, baz'
        >>> list(headers.items())
        [('foo', 'bar'), ('foo', 'baz')]
        >>> headers.add('foo', 'quz', combine=True)
        >>> list(headers.items())
        [('foo', 'bar, baz, quz')]
        """
        # avoid a bytes/str comparison by decoding before httplib
        if isinstance(key, bytes):
            key = key.decode("latin-1")
        key_lower = key.lower()
        new_vals = [key, val]
        # Keep the common case aka no item present as fast as possible
        vals = self._container.setdefault(key_lower, new_vals)
        if new_vals is not vals:
            # if there are values here, then there is at least the initial
            # key/value pair
            assert len(vals) >= 2
            if combine:
                vals[-1] = vals[-1] + ", " + val
            else:
                vals.append(val)

    def extend(self, *args: ValidHTTPHeaderSource, **kwargs: str) -> None:
        """Generic import function for any type of header-like object.
        Adapted version of MutableMapping.update in order to insert items
        with self.add instead of self.__setitem__
        """
        if len(args) > 1:
            raise TypeError(
                f"extend() takes at most 1 positional arguments ({len(args)} given)"
            )
        other = args[0] if len(args) >= 1 else ()

        if isinstance(other, HTTPHeaderDict):
            for key, val in other.iteritems():
                self.add(key, val)
        elif isinstance(other, typing.Mapping):
            for key, val in other.items():
                self.add(key, val)
        elif isinstance(other, typing.Iterable):
            other = typing.cast(typing.Iterable[tuple[str, str]], other)
            for key, value in other:
                self.add(key, value)
        elif hasattr(other, "keys") and hasattr(other, "__getitem__"):
            # THIS IS NOT A TYPESAFE BRANCH
            # In this branch, the object has a `keys` attr but is not a Mapping or any of
            # the other types indicated in the method signature. We do some stuff with
            # it as though it partially implements the Mapping interface, but we're not
            # doing that stuff safely AT ALL.
            for key in other.keys():
                self.add(key, other[key])

        for key, value in kwargs.items():
            self.add(key, value)

    @typing.overload
    def getlist(self, key: str) -> list[str]: ...

    @typing.overload
    def getlist(self, key: str, default: _DT) -> list[str] | _DT: ...

    def getlist(
        self, key: str, default: _Sentinel | _DT = _Sentinel.not_passed
    ) -> list[str] | _DT:
        """Returns a list of all the values for the named field. Returns an
        empty list if the key doesn't exist."""
        try:
            vals = self._container[key.lower()]
        except KeyError:
            if default is _Sentinel.not_passed:
                # _DT is unbound; empty list is instance of List[str]
                return []
            # _DT is bound; default is instance of _DT
            return default
        else:
            # _DT may or may not be bound; vals[1:] is instance of List[str], which
            # meets our external interface requirement of `Union[List[str], _DT]`.
            return vals[1:]

    def _prepare_for_method_change(self) -> Self:
        """
        Remove content-specific header fields before changing the request
        method to GET or HEAD according to RFC 9110, Section 15.4.
        """
        content_specific_headers = [
            "Content-Encoding",
            "Content-Language",
            "Content-Location",
            "Content-Type",
            "Content-Length",
            "Digest",
            "Last-Modified",
        ]
        for header in content_specific_headers:
            self.discard(header)
        return self

    # Backwards compatibility for httplib
    getheaders = getlist
    getallmatchingheaders = getlist
    iget = getlist

    # Backwards compatibility for http.cookiejar
    get_all = getlist

    def __repr__(self) -> str:
        return f"{type(self).__name__}({dict(self.itermerged())})"

    def _copy_from(self, other: HTTPHeaderDict) -> None:
        for key in other:
            val = other.getlist(key)
            self._container[key.lower()] = [key, *val]

    def copy(self) -> Self:
        clone = type(self)()
        clone._copy_from(self)
        return clone

    def iteritems(self) -> typing.Iterator[tuple[str, str]]:
        """Iterate over all header lines, including duplicate ones."""
        for key in self:
            vals = self._container[key.lower()]
            for val in vals[1:]:
                yield vals[0], val

    def itermerged(self) -> typing.Iterator[tuple[str, str]]:
        """Iterate over all headers, merging duplicate ones together."""
        for key in self:
            val = self._container[key.lower()]
            yield val[0], ", ".join(val[1:])

    def items(self) -> HTTPHeaderDictItemView:  # type: ignore[override]
        return HTTPHeaderDictItemView(self)

    def _has_value_for_header(self, header_name: str, potential_value: str) -> bool:
        if header_name in self:
            return potential_value in self._container[header_name.lower()][1:]
        return False

    def __ior__(self, other: object) -> HTTPHeaderDict:
        # Supports extending a header dict in-place using operator |=
        # combining items with add instead of __setitem__
        maybe_constructable = ensure_can_construct_http_header_dict(other)
        if maybe_constructable is None:
            return NotImplemented
        self.extend(maybe_constructable)
        return self

    def __or__(self, other: object) -> Self:
        # Supports merging header dicts using operator |
        # combining items with add instead of __setitem__
        maybe_constructable = ensure_can_construct_http_header_dict(other)
        if maybe_constructable is None:
            return NotImplemented
        result = self.copy()
        result.extend(maybe_constructable)
        return result

    def __ror__(self, other: object) -> Self:
        # Supports merging header dicts using operator | when other is on left side
        # combining items with add instead of __setitem__
        maybe_constructable = ensure_can_construct_http_header_dict(other)
        if maybe_constructable is None:
            return NotImplemented
        result = type(self)(maybe_constructable)
        result.extend(self)
        return result

# === NexusCore/openenv\Lib\site-packages\google\generativeai\types\permission_types.py ===
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
from __future__ import annotations

import dataclasses
from typing import Optional, Union, Any, Iterable, AsyncIterable
import re

import google.ai.generativelanguage as glm
from google.generativeai import protos

from google.protobuf import field_mask_pb2

from google.generativeai.client import get_default_permission_client
from google.generativeai.client import get_default_permission_async_client
from google.generativeai.utils import flatten_update_paths
from google.generativeai import string_utils

__all__ = ["Permission", "Permissions"]

GranteeType = protos.Permission.GranteeType
Role = protos.Permission.Role

GranteeTypeOptions = Union[str, int, GranteeType]
RoleOptions = Union[str, int, Role]

_GRANTEE_TYPE: dict[GranteeTypeOptions, GranteeType] = {
    GranteeType.GRANTEE_TYPE_UNSPECIFIED: GranteeType.GRANTEE_TYPE_UNSPECIFIED,
    0: GranteeType.GRANTEE_TYPE_UNSPECIFIED,
    "grantee_type_unspecified": GranteeType.GRANTEE_TYPE_UNSPECIFIED,
    "unspecified": GranteeType.GRANTEE_TYPE_UNSPECIFIED,
    GranteeType.USER: GranteeType.USER,
    1: GranteeType.USER,
    "user": GranteeType.USER,
    GranteeType.GROUP: GranteeType.GROUP,
    2: GranteeType.GROUP,
    "group": GranteeType.GROUP,
    GranteeType.EVERYONE: GranteeType.EVERYONE,
    3: GranteeType.EVERYONE,
    "everyone": GranteeType.EVERYONE,
}

_ROLE: dict[RoleOptions, Role] = {
    Role.ROLE_UNSPECIFIED: Role.ROLE_UNSPECIFIED,
    0: Role.ROLE_UNSPECIFIED,
    "role_unspecified": Role.ROLE_UNSPECIFIED,
    "unspecified": Role.ROLE_UNSPECIFIED,
    Role.OWNER: Role.OWNER,
    1: Role.OWNER,
    "owner": Role.OWNER,
    Role.WRITER: Role.WRITER,
    2: Role.WRITER,
    "writer": Role.WRITER,
    Role.READER: Role.READER,
    3: Role.READER,
    "reader": Role.READER,
}

_VALID_PERMISSION_ID = r"permissions/([a-z0-9]+)$"
INVALID_PERMISSION_ID_MSG = """`permission_id` must follow the pattern: `permissions/<id>` and must \
consist of only alphanumeric characters. Got: `{permission_id}` instead."""


def to_grantee_type(x: GranteeTypeOptions) -> GranteeType:
    if isinstance(x, str):
        x = x.lower()
    return _GRANTEE_TYPE[x]


def to_role(x: RoleOptions) -> Role:
    if isinstance(x, str):
        x = x.lower()
    return _ROLE[x]


def valid_id(name: str) -> bool:
    return re.match(_VALID_PERMISSION_ID, name) is not None


@string_utils.prettyprint
@dataclasses.dataclass(init=False)
class Permission:
    """
    A permission to access a resource.
    """

    name: str
    role: Role
    grantee_type: Optional[GranteeType]
    email_address: Optional[str] = None

    def __init__(
        self,
        name: str,
        role: RoleOptions,
        grantee_type: Optional[GranteeTypeOptions] = None,
        email_address: Optional[str] = None,
    ):
        self.name = name
        if role is None:
            self.role = None
        else:
            self.role = to_role(role)
        if grantee_type is None:
            self.grantee_type = None
        else:
            self.grantee_type = to_grantee_type(grantee_type)
        self.email_address = email_address

    def delete(
        self,
        client: glm.PermissionServiceClient | None = None,
    ) -> None:
        """
        Delete permission (self).
        """
        if client is None:
            client = get_default_permission_client()
        delete_request = protos.DeletePermissionRequest(name=self.name)
        client.delete_permission(request=delete_request)

    async def delete_async(
        self,
        client: glm.PermissionServiceAsyncClient | None = None,
    ) -> None:
        """
        This is the async version of `Permission.delete`.
        """
        if client is None:
            client = get_default_permission_async_client()
        delete_request = protos.DeletePermissionRequest(name=self.name)
        await client.delete_permission(request=delete_request)

    # TODO (magashe): Add a method to validate update value. As of now only `role` is supported as a mask path
    def _apply_update(self, path, value):
        parts = path.split(".")
        for part in parts[:-1]:
            self = getattr(self, part)
        setattr(self, parts[-1], value)

    def update(
        self,
        updates: dict[str, Any],
        client: glm.PermissionServiceClient | None = None,
    ) -> Permission:
        """
        Update a list of fields for a specified permission.

        Args:
            updates: The list of fields to update.
                     Currently only `role` is supported as an update path.

        Returns:
            `Permission` object with specified updates.
        """
        if client is None:
            client = get_default_permission_client()

        updates = flatten_update_paths(updates)
        for update_path in updates:
            if update_path != "role":
                raise ValueError(
                    f"Invalid update path: '{update_path}'. Currently, only the 'role' attribute can be updated for 'Permission'."
                )
        field_mask = field_mask_pb2.FieldMask()

        for path in updates.keys():
            field_mask.paths.append(path)
        for path, value in updates.items():
            self._apply_update(path, value)

        update_request = protos.UpdatePermissionRequest(
            permission=self._to_proto(), update_mask=field_mask
        )
        client.update_permission(request=update_request)
        return self

    async def update_async(
        self,
        updates: dict[str, Any],
        client: glm.PermissionServiceAsyncClient | None = None,
    ) -> Permission:
        """
        This is the async version of `Permission.update`.
        """
        if client is None:
            client = get_default_permission_async_client()

        updates = flatten_update_paths(updates)
        for update_path in updates:
            if update_path != "role":
                raise ValueError(
                    f"Invalid update path: '{update_path}'. Currently, only the 'role' attribute can be updated for 'Permission'."
                )
        field_mask = field_mask_pb2.FieldMask()

        for path in updates.keys():
            field_mask.paths.append(path)
        for path, value in updates.items():
            self._apply_update(path, value)

        update_request = protos.UpdatePermissionRequest(
            permission=self._to_proto(), update_mask=field_mask
        )
        await client.update_permission(request=update_request)
        return self

    def _to_proto(self) -> protos.Permission:
        return protos.Permission(
            name=self.name,
            role=self.role,
            grantee_type=self.grantee_type,
            email_address=self.email_address,
        )

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def get(
        cls,
        name: str,
        client: glm.PermissionServiceClient | None = None,
    ) -> Permission:
        """
        Get information about a specific permission.

        Args:
            name: The name of the permission to get.

        Returns:
            Requested permission as an instance of `Permission`.
        """
        if client is None:
            client = get_default_permission_client()
        get_perm_request = protos.GetPermissionRequest(name=name)
        get_perm_response = client.get_permission(request=get_perm_request)
        get_perm_response = type(get_perm_response).to_dict(get_perm_response)
        return cls(**get_perm_response)

    @classmethod
    async def get_async(
        cls,
        name: str,
        client: glm.PermissionServiceAsyncClient | None = None,
    ) -> Permission:
        """
        This is the async version of `Permission.get`.
        """
        if client is None:
            client = get_default_permission_async_client()
        get_perm_request = protos.GetPermissionRequest(name=name)
        get_perm_response = await client.get_permission(request=get_perm_request)
        get_perm_response = type(get_perm_response).to_dict(get_perm_response)
        return cls(**get_perm_response)


class Permissions:
    def __init__(self, parent):
        if isinstance(parent, str):
            self._parent = parent
        else:
            self._parent = parent.name

    @property
    def parent(self):
        return self._parent

    def _make_create_permission_request(
        self,
        role: RoleOptions,
        grantee_type: Optional[GranteeTypeOptions] = None,
        email_address: Optional[str] = None,
    ) -> protos.CreatePermissionRequest:
        role = to_role(role)

        if grantee_type:
            grantee_type = to_grantee_type(grantee_type)

        if email_address and grantee_type == GranteeType.EVERYONE:
            raise ValueError(
                f"Invalid operation: Access cannot be limited for a specific email address ('{email_address}') when 'grantee_type' is set to 'EVERYONE'."
            )
        if not email_address and grantee_type != GranteeType.EVERYONE:
            raise ValueError(
                f"Invalid operation: An 'email_address' must be provided when 'grantee_type' is not set to 'EVERYONE'. Currently, 'grantee_type' is set to '{grantee_type}' and 'email_address' is '{email_address if email_address else 'not provided'}'."
            )

        if email_address and grantee_type is None:
            if email_address.endswith("googlegroups.com"):
                grantee_type = GranteeType.GROUP
            else:
                grantee_type = GranteeType.USER

        permission = protos.Permission(
            role=role,
            grantee_type=grantee_type,
            email_address=email_address,
        )
        return protos.CreatePermissionRequest(
            parent=self.parent,
            permission=permission,
        )

    def create(
        self,
        role: RoleOptions,
        grantee_type: Optional[GranteeTypeOptions] = None,
        email_address: Optional[str] = None,
        client: glm.PermissionServiceClient | None = None,
    ) -> Permission:
        """
        Create a new permission on a resource (self).

        Args:
            parent: The resource name of the parent resource in which the permission will be listed.
            role: role that will be granted by the permission.
            grantee_type: The type of the grantee for the permission.
            email_address: The email address of the grantee.

        Returns:
            `Permission` object with specified parent, role, grantee type, and email address.

        Raises:
            ValueError: When email_address is specified and grantee_type is set to EVERYONE.
            ValueError: When email_address is not specified and grantee_type is not set to EVERYONE.
        """
        if client is None:
            client = get_default_permission_client()

        request = self._make_create_permission_request(
            role=role, grantee_type=grantee_type, email_address=email_address
        )
        permission_response = client.create_permission(request=request)
        permission_response = type(permission_response).to_dict(permission_response)
        return Permission(**permission_response)

    async def create_async(
        self,
        role: RoleOptions,
        grantee_type: Optional[GranteeTypeOptions] = None,
        email_address: Optional[str] = None,
        client: glm.PermissionServiceAsyncClient | None = None,
    ) -> Permission:
        """
        This is the async version of `PermissionAdapter.create_permission`.
        """
        if client is None:
            client = get_default_permission_async_client()

        request = self._make_create_permission_request(
            role=role, grantee_type=grantee_type, email_address=email_address
        )
        permission_response = await client.create_permission(request=request)
        permission_response = type(permission_response).to_dict(permission_response)
        return Permission(**permission_response)

    def list(
        self,
        page_size: Optional[int] = None,
        client: glm.PermissionServiceClient | None = None,
    ) -> Iterable[Permission]:
        """
        List `Permission`s enforced on a resource (self).

        Args:
            parent: The resource name of the parent resource in which the permission will be listed.
            page_size: The maximum number of permissions to return (per page). The service may return fewer permissions.

        Returns:
            Paginated list of `Permission` objects.
        """
        if client is None:
            client = get_default_permission_client()

        request = protos.ListPermissionsRequest(
            parent=self.parent, page_size=page_size  # pytype: disable=attribute-error
        )
        for permission in client.list_permissions(request):
            permission = type(permission).to_dict(permission)
            yield Permission(**permission)

    def __iter__(self):
        return self.list()

    async def list_async(
        self,
        page_size: Optional[int] = None,
        client: glm.PermissionServiceAsyncClient | None = None,
    ) -> AsyncIterable[Permission]:
        """
        This is the async version of `PermissionAdapter.list_permissions`.
        """
        if client is None:
            client = get_default_permission_async_client()

        request = protos.ListPermissionsRequest(
            parent=self.parent, page_size=page_size  # pytype: disable=attribute-error
        )
        async for permission in await client.list_permissions(request):
            permission = type(permission).to_dict(permission)
            yield Permission(**permission)

    async def __aiter__(self):
        return self.list_async()

    @classmethod
    def get(cls, name: str) -> Permission:
        """
        Get information about a specific permission.

        Args:
            name: The name of the permission to get.

        Returns:
            Requested permission as an instance of `Permission`.
        """
        return Permission.get(name)

    @classmethod
    async def get_async(cls, name: str) -> Permission:
        """
        Get information about a specific permission.

        Args:
            name: The name of the permission to get.

        Returns:
            Requested permission as an instance of `Permission`.
        """
        return await Permission.get_async(name)

    def transfer_ownership(
        self,
        email_address: str,
        client: glm.PermissionServiceClient | None = None,
    ) -> None:
        """
        Transfer ownership of a resource (self) to a new owner.

        Args:
            name: Name of the resource to transfer ownership.
            email_address: Email address of the new owner.
        """
        if self.parent.startswith("corpora"):
            raise NotImplementedError("Can'/t transfer_ownership for a Corpus")
        if client is None:
            client = get_default_permission_client()
        transfer_request = protos.TransferOwnershipRequest(
            name=self.parent, email_address=email_address  # pytype: disable=attribute-error
        )
        return client.transfer_ownership(request=transfer_request)

    async def transfer_ownership_async(
        self,
        email_address: str,
        client: glm.PermissionServiceAsyncClient | None = None,
    ) -> None:
        """This is the async version of `PermissionAdapter.transfer_ownership`."""
        if self.parent.startswith("corpora"):
            raise NotImplementedError("Can'/t transfer_ownership for a Corpus")
        if client is None:
            client = get_default_permission_async_client()
        transfer_request = protos.TransferOwnershipRequest(
            name=self.parent, email_address=email_address  # pytype: disable=attribute-error
        )
        return await client.transfer_ownership(request=transfer_request)

# === NexusCore/openenv\Lib\site-packages\google\generativeai\notebook\lib\__init__.py ===
# -*- coding: utf-8 -*-
# Copyright 2023 Google LLC
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

# === NexusCore/openenv\Lib\site-packages\mpl_toolkits\axisartist\axislines.py ===
"""
Axislines includes modified implementation of the Axes class. The
biggest difference is that the artists responsible for drawing the axis spine,
ticks, ticklabels and axis labels are separated out from Matplotlib's Axis
class. Originally, this change was motivated to support curvilinear
grid. Here are a few reasons that I came up with a new axes class:

* "top" and "bottom" x-axis (or "left" and "right" y-axis) can have
  different ticks (tick locations and labels). This is not possible
  with the current Matplotlib, although some twin axes trick can help.

* Curvilinear grid.

* angled ticks.

In the new axes class, xaxis and yaxis is set to not visible by
default, and new set of artist (AxisArtist) are defined to draw axis
line, ticks, ticklabels and axis label. Axes.axis attribute serves as
a dictionary of these artists, i.e., ax.axis["left"] is a AxisArtist
instance responsible to draw left y-axis. The default Axes.axis contains
"bottom", "left", "top" and "right".

AxisArtist can be considered as a container artist and has the following
children artists which will draw ticks, labels, etc.

* line
* major_ticks, major_ticklabels
* minor_ticks, minor_ticklabels
* offsetText
* label

Note that these are separate artists from `matplotlib.axis.Axis`, thus most
tick-related functions in Matplotlib won't work. For example, color and
markerwidth of the ``ax.axis["bottom"].major_ticks`` will follow those of
Axes.xaxis unless explicitly specified.

In addition to AxisArtist, the Axes will have *gridlines* attribute,
which obviously draws grid lines. The gridlines needs to be separated
from the axis as some gridlines can never pass any axis.
"""

import numpy as np

import matplotlib as mpl
from matplotlib import _api
import matplotlib.axes as maxes
from matplotlib.path import Path
from mpl_toolkits.axes_grid1 import mpl_axes
from .axisline_style import AxislineStyle  # noqa
from .axis_artist import AxisArtist, GridlinesCollection


class _AxisArtistHelperBase:
    """
    Base class for axis helper.

    Subclasses should define the methods listed below.  The *axes*
    argument will be the ``.axes`` attribute of the caller artist. ::

        # Construct the spine.

        def get_line_transform(self, axes):
            return transform

        def get_line(self, axes):
            return path

        # Construct the label.

        def get_axislabel_transform(self, axes):
            return transform

        def get_axislabel_pos_angle(self, axes):
            return (x, y), angle

        # Construct the ticks.

        def get_tick_transform(self, axes):
            return transform

        def get_tick_iterators(self, axes):
            # A pair of iterables (one for major ticks, one for minor ticks)
            # that yield (tick_position, tick_angle, tick_label).
            return iter_major, iter_minor
    """

    def __init__(self, nth_coord):
        self.nth_coord = nth_coord

    def update_lim(self, axes):
        pass

    def get_nth_coord(self):
        return self.nth_coord

    def _to_xy(self, values, const):
        """
        Create a (*values.shape, 2)-shape array representing (x, y) pairs.

        The other coordinate is filled with the constant *const*.

        Example::

            >>> self.nth_coord = 0
            >>> self._to_xy([1, 2, 3], const=0)
            array([[1, 0],
                   [2, 0],
                   [3, 0]])
        """
        if self.nth_coord == 0:
            return np.stack(np.broadcast_arrays(values, const), axis=-1)
        elif self.nth_coord == 1:
            return np.stack(np.broadcast_arrays(const, values), axis=-1)
        else:
            raise ValueError("Unexpected nth_coord")


class _FixedAxisArtistHelperBase(_AxisArtistHelperBase):
    """Helper class for a fixed (in the axes coordinate) axis."""

    @_api.delete_parameter("3.9", "nth_coord")
    def __init__(self, loc, nth_coord=None):
        """``nth_coord = 0``: x-axis; ``nth_coord = 1``: y-axis."""
        super().__init__(_api.check_getitem(
            {"bottom": 0, "top": 0, "left": 1, "right": 1}, loc=loc))
        self._loc = loc
        self._pos = {"bottom": 0, "top": 1, "left": 0, "right": 1}[loc]
        # axis line in transAxes
        self._path = Path(self._to_xy((0, 1), const=self._pos))

    # LINE

    def get_line(self, axes):
        return self._path

    def get_line_transform(self, axes):
        return axes.transAxes

    # LABEL

    def get_axislabel_transform(self, axes):
        return axes.transAxes

    def get_axislabel_pos_angle(self, axes):
        """
        Return the label reference position in transAxes.

        get_label_transform() returns a transform of (transAxes+offset)
        """
        return dict(left=((0., 0.5), 90),  # (position, angle_tangent)
                    right=((1., 0.5), 90),
                    bottom=((0.5, 0.), 0),
                    top=((0.5, 1.), 0))[self._loc]

    # TICK

    def get_tick_transform(self, axes):
        return [axes.get_xaxis_transform(), axes.get_yaxis_transform()][self.nth_coord]


class _FloatingAxisArtistHelperBase(_AxisArtistHelperBase):
    def __init__(self, nth_coord, value):
        self._value = value
        super().__init__(nth_coord)

    def get_line(self, axes):
        raise RuntimeError("get_line method should be defined by the derived class")


class FixedAxisArtistHelperRectilinear(_FixedAxisArtistHelperBase):

    @_api.delete_parameter("3.9", "nth_coord")
    def __init__(self, axes, loc, nth_coord=None):
        """
        nth_coord = along which coordinate value varies
        in 2D, nth_coord = 0 ->  x axis, nth_coord = 1 -> y axis
        """
        super().__init__(loc)
        self.axis = [axes.xaxis, axes.yaxis][self.nth_coord]

    # TICK

    def get_tick_iterators(self, axes):
        """tick_loc, tick_angle, tick_label"""
        angle_normal, angle_tangent = {0: (90, 0), 1: (0, 90)}[self.nth_coord]

        major = self.axis.major
        major_locs = major.locator()
        major_labels = major.formatter.format_ticks(major_locs)

        minor = self.axis.minor
        minor_locs = minor.locator()
        minor_labels = minor.formatter.format_ticks(minor_locs)

        tick_to_axes = self.get_tick_transform(axes) - axes.transAxes

        def _f(locs, labels):
            for loc, label in zip(locs, labels):
                c = self._to_xy(loc, const=self._pos)
                # check if the tick point is inside axes
                c2 = tick_to_axes.transform(c)
                if mpl.transforms._interval_contains_close((0, 1), c2[self.nth_coord]):
                    yield c, angle_normal, angle_tangent, label

        return _f(major_locs, major_labels), _f(minor_locs, minor_labels)


class FloatingAxisArtistHelperRectilinear(_FloatingAxisArtistHelperBase):

    def __init__(self, axes, nth_coord,
                 passingthrough_point, axis_direction="bottom"):
        super().__init__(nth_coord, passingthrough_point)
        self._axis_direction = axis_direction
        self.axis = [axes.xaxis, axes.yaxis][self.nth_coord]

    def get_line(self, axes):
        fixed_coord = 1 - self.nth_coord
        data_to_axes = axes.transData - axes.transAxes
        p = data_to_axes.transform([self._value, self._value])
        return Path(self._to_xy((0, 1), const=p[fixed_coord]))

    def get_line_transform(self, axes):
        return axes.transAxes

    def get_axislabel_transform(self, axes):
        return axes.transAxes

    def get_axislabel_pos_angle(self, axes):
        """
        Return the label reference position in transAxes.

        get_label_transform() returns a transform of (transAxes+offset)
        """
        angle = [0, 90][self.nth_coord]
        fixed_coord = 1 - self.nth_coord
        data_to_axes = axes.transData - axes.transAxes
        p = data_to_axes.transform([self._value, self._value])
        verts = self._to_xy(0.5, const=p[fixed_coord])
        return (verts, angle) if 0 <= verts[fixed_coord] <= 1 else (None, None)

    def get_tick_transform(self, axes):
        return axes.transData

    def get_tick_iterators(self, axes):
        """tick_loc, tick_angle, tick_label"""
        angle_normal, angle_tangent = {0: (90, 0), 1: (0, 90)}[self.nth_coord]

        major = self.axis.major
        major_locs = major.locator()
        major_labels = major.formatter.format_ticks(major_locs)

        minor = self.axis.minor
        minor_locs = minor.locator()
        minor_labels = minor.formatter.format_ticks(minor_locs)

        data_to_axes = axes.transData - axes.transAxes

        def _f(locs, labels):
            for loc, label in zip(locs, labels):
                c = self._to_xy(loc, const=self._value)
                c1, c2 = data_to_axes.transform(c)
                if 0 <= c1 <= 1 and 0 <= c2 <= 1:
                    yield c, angle_normal, angle_tangent, label

        return _f(major_locs, major_labels), _f(minor_locs, minor_labels)


class AxisArtistHelper:  # Backcompat.
    Fixed = _FixedAxisArtistHelperBase
    Floating = _FloatingAxisArtistHelperBase


class AxisArtistHelperRectlinear:  # Backcompat.
    Fixed = FixedAxisArtistHelperRectilinear
    Floating = FloatingAxisArtistHelperRectilinear


class GridHelperBase:

    def __init__(self):
        self._old_limits = None
        super().__init__()

    def update_lim(self, axes):
        x1, x2 = axes.get_xlim()
        y1, y2 = axes.get_ylim()
        if self._old_limits != (x1, x2, y1, y2):
            self._update_grid(x1, y1, x2, y2)
            self._old_limits = (x1, x2, y1, y2)

    def _update_grid(self, x1, y1, x2, y2):
        """Cache relevant computations when the axes limits have changed."""

    def get_gridlines(self, which, axis):
        """
        Return list of grid lines as a list of paths (list of points).

        Parameters
        ----------
        which : {"both", "major", "minor"}
        axis : {"both", "x", "y"}
        """
        return []


class GridHelperRectlinear(GridHelperBase):

    def __init__(self, axes):
        super().__init__()
        self.axes = axes

    @_api.delete_parameter(
        "3.9", "nth_coord", addendum="'nth_coord' is now inferred from 'loc'.")
    def new_fixed_axis(
            self, loc, nth_coord=None, axis_direction=None, offset=None, axes=None):
        if axes is None:
            _api.warn_external(
                "'new_fixed_axis' explicitly requires the axes keyword.")
            axes = self.axes
        if axis_direction is None:
            axis_direction = loc
        return AxisArtist(axes, FixedAxisArtistHelperRectilinear(axes, loc),
                          offset=offset, axis_direction=axis_direction)

    def new_floating_axis(self, nth_coord, value, axis_direction="bottom", axes=None):
        if axes is None:
            _api.warn_external(
                "'new_floating_axis' explicitly requires the axes keyword.")
            axes = self.axes
        helper = FloatingAxisArtistHelperRectilinear(
            axes, nth_coord, value, axis_direction)
        axisline = AxisArtist(axes, helper, axis_direction=axis_direction)
        axisline.line.set_clip_on(True)
        axisline.line.set_clip_box(axisline.axes.bbox)
        return axisline

    def get_gridlines(self, which="major", axis="both"):
        """
        Return list of gridline coordinates in data coordinates.

        Parameters
        ----------
        which : {"both", "major", "minor"}
        axis : {"both", "x", "y"}
        """
        _api.check_in_list(["both", "major", "minor"], which=which)
        _api.check_in_list(["both", "x", "y"], axis=axis)
        gridlines = []

        if axis in ("both", "x"):
            locs = []
            y1, y2 = self.axes.get_ylim()
            if which in ("both", "major"):
                locs.extend(self.axes.xaxis.major.locator())
            if which in ("both", "minor"):
                locs.extend(self.axes.xaxis.minor.locator())
            gridlines.extend([[x, x], [y1, y2]] for x in locs)

        if axis in ("both", "y"):
            x1, x2 = self.axes.get_xlim()
            locs = []
            if self.axes.yaxis._major_tick_kw["gridOn"]:
                locs.extend(self.axes.yaxis.major.locator())
            if self.axes.yaxis._minor_tick_kw["gridOn"]:
                locs.extend(self.axes.yaxis.minor.locator())
            gridlines.extend([[x1, x2], [y, y]] for y in locs)

        return gridlines


class Axes(maxes.Axes):

    def __init__(self, *args, grid_helper=None, **kwargs):
        self._axisline_on = True
        self._grid_helper = grid_helper if grid_helper else GridHelperRectlinear(self)
        super().__init__(*args, **kwargs)
        self.toggle_axisline(True)

    def toggle_axisline(self, b=None):
        if b is None:
            b = not self._axisline_on
        if b:
            self._axisline_on = True
            self.spines[:].set_visible(False)
            self.xaxis.set_visible(False)
            self.yaxis.set_visible(False)
        else:
            self._axisline_on = False
            self.spines[:].set_visible(True)
            self.xaxis.set_visible(True)
            self.yaxis.set_visible(True)

    @property
    def axis(self):
        return self._axislines

    def clear(self):
        # docstring inherited

        # Init gridlines before clear() as clear() calls grid().
        self.gridlines = gridlines = GridlinesCollection(
            [],
            colors=mpl.rcParams['grid.color'],
            linestyles=mpl.rcParams['grid.linestyle'],
            linewidths=mpl.rcParams['grid.linewidth'])
        self._set_artist_props(gridlines)
        gridlines.set_grid_helper(self.get_grid_helper())

        super().clear()

        # clip_path is set after Axes.clear(): that's when a patch is created.
        gridlines.set_clip_path(self.axes.patch)

        # Init axis artists.
        self._axislines = mpl_axes.Axes.AxisDict(self)
        new_fixed_axis = self.get_grid_helper().new_fixed_axis
        self._axislines.update({
            loc: new_fixed_axis(loc=loc, axes=self, axis_direction=loc)
            for loc in ["bottom", "top", "left", "right"]})
        for axisline in [self._axislines["top"], self._axislines["right"]]:
            axisline.label.set_visible(False)
            axisline.major_ticklabels.set_visible(False)
            axisline.minor_ticklabels.set_visible(False)

    def get_grid_helper(self):
        return self._grid_helper

    def grid(self, visible=None, which='major', axis="both", **kwargs):
        """
        Toggle the gridlines, and optionally set the properties of the lines.
        """
        # There are some discrepancies in the behavior of grid() between
        # axes_grid and Matplotlib, because axes_grid explicitly sets the
        # visibility of the gridlines.
        super().grid(visible, which=which, axis=axis, **kwargs)
        if not self._axisline_on:
            return
        if visible is None:
            visible = (self.axes.xaxis._minor_tick_kw["gridOn"]
                       or self.axes.xaxis._major_tick_kw["gridOn"]
                       or self.axes.yaxis._minor_tick_kw["gridOn"]
                       or self.axes.yaxis._major_tick_kw["gridOn"])
        self.gridlines.set(which=which, axis=axis, visible=visible)
        self.gridlines.set(**kwargs)

    def get_children(self):
        if self._axisline_on:
            children = [*self._axislines.values(), self.gridlines]
        else:
            children = []
        children.extend(super().get_children())
        return children

    def new_fixed_axis(self, loc, offset=None):
        return self.get_grid_helper().new_fixed_axis(loc, offset=offset, axes=self)

    def new_floating_axis(self, nth_coord, value, axis_direction="bottom"):
        return self.get_grid_helper().new_floating_axis(
            nth_coord, value, axis_direction=axis_direction, axes=self)


class AxesZero(Axes):

    def clear(self):
        super().clear()
        new_floating_axis = self.get_grid_helper().new_floating_axis
        self._axislines.update(
            xzero=new_floating_axis(
                nth_coord=0, value=0., axis_direction="bottom", axes=self),
            yzero=new_floating_axis(
                nth_coord=1, value=0., axis_direction="left", axes=self),
        )
        for k in ["xzero", "yzero"]:
            self._axislines[k].line.set_clip_path(self.patch)
            self._axislines[k].set_visible(False)


Subplot = Axes
SubplotZero = AxesZero

# === NexusCore/openenv\Lib\site-packages\pydantic\_internal\_discriminated_union.py ===
from __future__ import annotations as _annotations

from collections.abc import Hashable, Sequence
from typing import TYPE_CHECKING, Any, cast

from pydantic_core import CoreSchema, core_schema

from ..errors import PydanticUserError
from . import _core_utils
from ._core_utils import (
    CoreSchemaField,
)

if TYPE_CHECKING:
    from ..types import Discriminator
    from ._core_metadata import CoreMetadata


class MissingDefinitionForUnionRef(Exception):
    """Raised when applying a discriminated union discriminator to a schema
    requires a definition that is not yet defined
    """

    def __init__(self, ref: str) -> None:
        self.ref = ref
        super().__init__(f'Missing definition for ref {self.ref!r}')


def set_discriminator_in_metadata(schema: CoreSchema, discriminator: Any) -> None:
    metadata = cast('CoreMetadata', schema.setdefault('metadata', {}))
    metadata['pydantic_internal_union_discriminator'] = discriminator


def apply_discriminator(
    schema: core_schema.CoreSchema,
    discriminator: str | Discriminator,
    definitions: dict[str, core_schema.CoreSchema] | None = None,
) -> core_schema.CoreSchema:
    """Applies the discriminator and returns a new core schema.

    Args:
        schema: The input schema.
        discriminator: The name of the field which will serve as the discriminator.
        definitions: A mapping of schema ref to schema.

    Returns:
        The new core schema.

    Raises:
        TypeError:
            - If `discriminator` is used with invalid union variant.
            - If `discriminator` is used with `Union` type with one variant.
            - If `discriminator` value mapped to multiple choices.
        MissingDefinitionForUnionRef:
            If the definition for ref is missing.
        PydanticUserError:
            - If a model in union doesn't have a discriminator field.
            - If discriminator field has a non-string alias.
            - If discriminator fields have different aliases.
            - If discriminator field not of type `Literal`.
    """
    from ..types import Discriminator

    if isinstance(discriminator, Discriminator):
        if isinstance(discriminator.discriminator, str):
            discriminator = discriminator.discriminator
        else:
            return discriminator._convert_schema(schema)

    return _ApplyInferredDiscriminator(discriminator, definitions or {}).apply(schema)


class _ApplyInferredDiscriminator:
    """This class is used to convert an input schema containing a union schema into one where that union is
    replaced with a tagged-union, with all the associated debugging and performance benefits.

    This is done by:
    * Validating that the input schema is compatible with the provided discriminator
    * Introspecting the schema to determine which discriminator values should map to which union choices
    * Handling various edge cases such as 'definitions', 'default', 'nullable' schemas, and more

    I have chosen to implement the conversion algorithm in this class, rather than a function,
    to make it easier to maintain state while recursively walking the provided CoreSchema.
    """

    def __init__(self, discriminator: str, definitions: dict[str, core_schema.CoreSchema]):
        # `discriminator` should be the name of the field which will serve as the discriminator.
        # It must be the python name of the field, and *not* the field's alias. Note that as of now,
        # all members of a discriminated union _must_ use a field with the same name as the discriminator.
        # This may change if/when we expose a way to manually specify the TaggedUnionSchema's choices.
        self.discriminator = discriminator

        # `definitions` should contain a mapping of schema ref to schema for all schemas which might
        # be referenced by some choice
        self.definitions = definitions

        # `_discriminator_alias` will hold the value, if present, of the alias for the discriminator
        #
        # Note: following the v1 implementation, we currently disallow the use of different aliases
        # for different choices. This is not a limitation of pydantic_core, but if we try to handle
        # this, the inference logic gets complicated very quickly, and could result in confusing
        # debugging challenges for users making subtle mistakes.
        #
        # Rather than trying to do the most powerful inference possible, I think we should eventually
        # expose a way to more-manually control the way the TaggedUnionSchema is constructed through
        # the use of a new type which would be placed as an Annotation on the Union type. This would
        # provide the full flexibility/power of pydantic_core's TaggedUnionSchema where necessary for
        # more complex cases, without over-complicating the inference logic for the common cases.
        self._discriminator_alias: str | None = None

        # `_should_be_nullable` indicates whether the converted union has `None` as an allowed value.
        # If `None` is an acceptable value of the (possibly-wrapped) union, we ignore it while
        # constructing the TaggedUnionSchema, but set the `_should_be_nullable` attribute to True.
        # Once we have constructed the TaggedUnionSchema, if `_should_be_nullable` is True, we ensure
        # that the final schema gets wrapped as a NullableSchema. This has the same semantics on the
        # python side, but resolves the issue that `None` cannot correspond to any discriminator values.
        self._should_be_nullable = False

        # `_is_nullable` is used to track if the final produced schema will definitely be nullable;
        # we set it to True if the input schema is wrapped in a nullable schema that we know will be preserved
        # as an indication that, even if None is discovered as one of the union choices, we will not need to wrap
        # the final value in another nullable schema.
        #
        # This is more complicated than just checking for the final outermost schema having type 'nullable' thanks
        # to the possible presence of other wrapper schemas such as DefinitionsSchema, WithDefaultSchema, etc.
        self._is_nullable = False

        # `_choices_to_handle` serves as a stack of choices to add to the tagged union. Initially, choices
        # from the union in the wrapped schema will be appended to this list, and the recursive choice-handling
        # algorithm may add more choices to this stack as (nested) unions are encountered.
        self._choices_to_handle: list[core_schema.CoreSchema] = []

        # `_tagged_union_choices` is built during the call to `apply`, and will hold the choices to be included
        # in the output TaggedUnionSchema that will replace the union from the input schema
        self._tagged_union_choices: dict[Hashable, core_schema.CoreSchema] = {}

        # `_used` is changed to True after applying the discriminator to prevent accidental reuse
        self._used = False

    def apply(self, schema: core_schema.CoreSchema) -> core_schema.CoreSchema:
        """Return a new CoreSchema based on `schema` that uses a tagged-union with the discriminator provided
        to this class.

        Args:
            schema: The input schema.

        Returns:
            The new core schema.

        Raises:
            TypeError:
                - If `discriminator` is used with invalid union variant.
                - If `discriminator` is used with `Union` type with one variant.
                - If `discriminator` value mapped to multiple choices.
            ValueError:
                If the definition for ref is missing.
            PydanticUserError:
                - If a model in union doesn't have a discriminator field.
                - If discriminator field has a non-string alias.
                - If discriminator fields have different aliases.
                - If discriminator field not of type `Literal`.
        """
        assert not self._used
        schema = self._apply_to_root(schema)
        if self._should_be_nullable and not self._is_nullable:
            schema = core_schema.nullable_schema(schema)
        self._used = True
        return schema

    def _apply_to_root(self, schema: core_schema.CoreSchema) -> core_schema.CoreSchema:
        """This method handles the outer-most stage of recursion over the input schema:
        unwrapping nullable or definitions schemas, and calling the `_handle_choice`
        method iteratively on the choices extracted (recursively) from the possibly-wrapped union.
        """
        if schema['type'] == 'nullable':
            self._is_nullable = True
            wrapped = self._apply_to_root(schema['schema'])
            nullable_wrapper = schema.copy()
            nullable_wrapper['schema'] = wrapped
            return nullable_wrapper

        if schema['type'] == 'definitions':
            wrapped = self._apply_to_root(schema['schema'])
            definitions_wrapper = schema.copy()
            definitions_wrapper['schema'] = wrapped
            return definitions_wrapper

        if schema['type'] != 'union':
            # If the schema is not a union, it probably means it just had a single member and
            # was flattened by pydantic_core.
            # However, it still may make sense to apply the discriminator to this schema,
            # as a way to get discriminated-union-style error messages, so we allow this here.
            schema = core_schema.union_schema([schema])

        # Reverse the choices list before extending the stack so that they get handled in the order they occur
        choices_schemas = [v[0] if isinstance(v, tuple) else v for v in schema['choices'][::-1]]
        self._choices_to_handle.extend(choices_schemas)
        while self._choices_to_handle:
            choice = self._choices_to_handle.pop()
            self._handle_choice(choice)

        if self._discriminator_alias is not None and self._discriminator_alias != self.discriminator:
            # * We need to annotate `discriminator` as a union here to handle both branches of this conditional
            # * We need to annotate `discriminator` as list[list[str | int]] and not list[list[str]] due to the
            #   invariance of list, and because list[list[str | int]] is the type of the discriminator argument
            #   to tagged_union_schema below
            # * See the docstring of pydantic_core.core_schema.tagged_union_schema for more details about how to
            #   interpret the value of the discriminator argument to tagged_union_schema. (The list[list[str]] here
            #   is the appropriate way to provide a list of fallback attributes to check for a discriminator value.)
            discriminator: str | list[list[str | int]] = [[self.discriminator], [self._discriminator_alias]]
        else:
            discriminator = self.discriminator
        return core_schema.tagged_union_schema(
            choices=self._tagged_union_choices,
            discriminator=discriminator,
            custom_error_type=schema.get('custom_error_type'),
            custom_error_message=schema.get('custom_error_message'),
            custom_error_context=schema.get('custom_error_context'),
            strict=False,
            from_attributes=True,
            ref=schema.get('ref'),
            metadata=schema.get('metadata'),
            serialization=schema.get('serialization'),
        )

    def _handle_choice(self, choice: core_schema.CoreSchema) -> None:
        """This method handles the "middle" stage of recursion over the input schema.
        Specifically, it is responsible for handling each choice of the outermost union
        (and any "coalesced" choices obtained from inner unions).

        Here, "handling" entails:
        * Coalescing nested unions and compatible tagged-unions
        * Tracking the presence of 'none' and 'nullable' schemas occurring as choices
        * Validating that each allowed discriminator value maps to a unique choice
        * Updating the _tagged_union_choices mapping that will ultimately be used to build the TaggedUnionSchema.
        """
        if choice['type'] == 'definition-ref':
            if choice['schema_ref'] not in self.definitions:
                raise MissingDefinitionForUnionRef(choice['schema_ref'])

        if choice['type'] == 'none':
            self._should_be_nullable = True
        elif choice['type'] == 'definitions':
            self._handle_choice(choice['schema'])
        elif choice['type'] == 'nullable':
            self._should_be_nullable = True
            self._handle_choice(choice['schema'])  # unwrap the nullable schema
        elif choice['type'] == 'union':
            # Reverse the choices list before extending the stack so that they get handled in the order they occur
            choices_schemas = [v[0] if isinstance(v, tuple) else v for v in choice['choices'][::-1]]
            self._choices_to_handle.extend(choices_schemas)
        elif choice['type'] not in {
            'model',
            'typed-dict',
            'tagged-union',
            'lax-or-strict',
            'dataclass',
            'dataclass-args',
            'definition-ref',
        } and not _core_utils.is_function_with_inner_schema(choice):
            # We should eventually handle 'definition-ref' as well
            err_str = f'The core schema type {choice["type"]!r} is not a valid discriminated union variant.'
            if choice['type'] == 'list':
                err_str += (
                    ' If you are making use of a list of union types, make sure the discriminator is applied to the '
                    'union type and not the list (e.g. `list[Annotated[<T> | <U>, Field(discriminator=...)]]`).'
                )
            raise TypeError(err_str)
        else:
            if choice['type'] == 'tagged-union' and self._is_discriminator_shared(choice):
                # In this case, this inner tagged-union is compatible with the outer tagged-union,
                # and its choices can be coalesced into the outer TaggedUnionSchema.
                subchoices = [x for x in choice['choices'].values() if not isinstance(x, (str, int))]
                # Reverse the choices list before extending the stack so that they get handled in the order they occur
                self._choices_to_handle.extend(subchoices[::-1])
                return

            inferred_discriminator_values = self._infer_discriminator_values_for_choice(choice, source_name=None)
            self._set_unique_choice_for_values(choice, inferred_discriminator_values)

    def _is_discriminator_shared(self, choice: core_schema.TaggedUnionSchema) -> bool:
        """This method returns a boolean indicating whether the discriminator for the `choice`
        is the same as that being used for the outermost tagged union. This is used to
        determine whether this TaggedUnionSchema choice should be "coalesced" into the top level,
        or whether it should be treated as a separate (nested) choice.
        """
        inner_discriminator = choice['discriminator']
        return inner_discriminator == self.discriminator or (
            isinstance(inner_discriminator, list)
            and (self.discriminator in inner_discriminator or [self.discriminator] in inner_discriminator)
        )

    def _infer_discriminator_values_for_choice(  # noqa C901
        self, choice: core_schema.CoreSchema, source_name: str | None
    ) -> list[str | int]:
        """This function recurses over `choice`, extracting all discriminator values that should map to this choice.

        `model_name` is accepted for the purpose of producing useful error messages.
        """
        if choice['type'] == 'definitions':
            return self._infer_discriminator_values_for_choice(choice['schema'], source_name=source_name)

        elif _core_utils.is_function_with_inner_schema(choice):
            return self._infer_discriminator_values_for_choice(choice['schema'], source_name=source_name)

        elif choice['type'] == 'lax-or-strict':
            return sorted(
                set(
                    self._infer_discriminator_values_for_choice(choice['lax_schema'], source_name=None)
                    + self._infer_discriminator_values_for_choice(choice['strict_schema'], source_name=None)
                )
            )

        elif choice['type'] == 'tagged-union':
            values: list[str | int] = []
            # Ignore str/int "choices" since these are just references to other choices
            subchoices = [x for x in choice['choices'].values() if not isinstance(x, (str, int))]
            for subchoice in subchoices:
                subchoice_values = self._infer_discriminator_values_for_choice(subchoice, source_name=None)
                values.extend(subchoice_values)
            return values

        elif choice['type'] == 'union':
            values = []
            for subchoice in choice['choices']:
                subchoice_schema = subchoice[0] if isinstance(subchoice, tuple) else subchoice
                subchoice_values = self._infer_discriminator_values_for_choice(subchoice_schema, source_name=None)
                values.extend(subchoice_values)
            return values

        elif choice['type'] == 'nullable':
            self._should_be_nullable = True
            return self._infer_discriminator_values_for_choice(choice['schema'], source_name=None)

        elif choice['type'] == 'model':
            return self._infer_discriminator_values_for_choice(choice['schema'], source_name=choice['cls'].__name__)

        elif choice['type'] == 'dataclass':
            return self._infer_discriminator_values_for_choice(choice['schema'], source_name=choice['cls'].__name__)

        elif choice['type'] == 'model-fields':
            return self._infer_discriminator_values_for_model_choice(choice, source_name=source_name)

        elif choice['type'] == 'dataclass-args':
            return self._infer_discriminator_values_for_dataclass_choice(choice, source_name=source_name)

        elif choice['type'] == 'typed-dict':
            return self._infer_discriminator_values_for_typed_dict_choice(choice, source_name=source_name)

        elif choice['type'] == 'definition-ref':
            schema_ref = choice['schema_ref']
            if schema_ref not in self.definitions:
                raise MissingDefinitionForUnionRef(schema_ref)
            return self._infer_discriminator_values_for_choice(self.definitions[schema_ref], source_name=source_name)
        else:
            err_str = f'The core schema type {choice["type"]!r} is not a valid discriminated union variant.'
            if choice['type'] == 'list':
                err_str += (
                    ' If you are making use of a list of union types, make sure the discriminator is applied to the '
                    'union type and not the list (e.g. `list[Annotated[<T> | <U>, Field(discriminator=...)]]`).'
                )
            raise TypeError(err_str)

    def _infer_discriminator_values_for_typed_dict_choice(
        self, choice: core_schema.TypedDictSchema, source_name: str | None = None
    ) -> list[str | int]:
        """This method just extracts the _infer_discriminator_values_for_choice logic specific to TypedDictSchema
        for the sake of readability.
        """
        source = 'TypedDict' if source_name is None else f'TypedDict {source_name!r}'
        field = choice['fields'].get(self.discriminator)
        if field is None:
            raise PydanticUserError(
                f'{source} needs a discriminator field for key {self.discriminator!r}', code='discriminator-no-field'
            )
        return self._infer_discriminator_values_for_field(field, source)

    def _infer_discriminator_values_for_model_choice(
        self, choice: core_schema.ModelFieldsSchema, source_name: str | None = None
    ) -> list[str | int]:
        source = 'ModelFields' if source_name is None else f'Model {source_name!r}'
        field = choice['fields'].get(self.discriminator)
        if field is None:
            raise PydanticUserError(
                f'{source} needs a discriminator field for key {self.discriminator!r}', code='discriminator-no-field'
            )
        return self._infer_discriminator_values_for_field(field, source)

    def _infer_discriminator_values_for_dataclass_choice(
        self, choice: core_schema.DataclassArgsSchema, source_name: str | None = None
    ) -> list[str | int]:
        source = 'DataclassArgs' if source_name is None else f'Dataclass {source_name!r}'
        for field in choice['fields']:
            if field['name'] == self.discriminator:
                break
        else:
            raise PydanticUserError(
                f'{source} needs a discriminator field for key {self.discriminator!r}', code='discriminator-no-field'
            )
        return self._infer_discriminator_values_for_field(field, source)

    def _infer_discriminator_values_for_field(self, field: CoreSchemaField, source: str) -> list[str | int]:
        if field['type'] == 'computed-field':
            # This should never occur as a discriminator, as it is only relevant to serialization
            return []
        alias = field.get('validation_alias', self.discriminator)
        if not isinstance(alias, str):
            raise PydanticUserError(
                f'Alias {alias!r} is not supported in a discriminated union', code='discriminator-alias-type'
            )
        if self._discriminator_alias is None:
            self._discriminator_alias = alias
        elif self._discriminator_alias != alias:
            raise PydanticUserError(
                f'Aliases for discriminator {self.discriminator!r} must be the same '
                f'(got {alias}, {self._discriminator_alias})',
                code='discriminator-alias',
            )
        return self._infer_discriminator_values_for_inner_schema(field['schema'], source)

    def _infer_discriminator_values_for_inner_schema(
        self, schema: core_schema.CoreSchema, source: str
    ) -> list[str | int]:
        """When inferring discriminator values for a field, we typically extract the expected values from a literal
        schema. This function does that, but also handles nested unions and defaults.
        """
        if schema['type'] == 'literal':
            return schema['expected']

        elif schema['type'] == 'union':
            # Generally when multiple values are allowed they should be placed in a single `Literal`, but
            # we add this case to handle the situation where a field is annotated as a `Union` of `Literal`s.
            # For example, this lets us handle `Union[Literal['key'], Union[Literal['Key'], Literal['KEY']]]`
            values: list[Any] = []
            for choice in schema['choices']:
                choice_schema = choice[0] if isinstance(choice, tuple) else choice
                choice_values = self._infer_discriminator_values_for_inner_schema(choice_schema, source)
                values.extend(choice_values)
            return values

        elif schema['type'] == 'default':
            # This will happen if the field has a default value; we ignore it while extracting the discriminator values
            return self._infer_discriminator_values_for_inner_schema(schema['schema'], source)

        elif schema['type'] == 'function-after':
            # After validators don't affect the discriminator values
            return self._infer_discriminator_values_for_inner_schema(schema['schema'], source)

        elif schema['type'] in {'function-before', 'function-wrap', 'function-plain'}:
            validator_type = repr(schema['type'].split('-')[1])
            raise PydanticUserError(
                f'Cannot use a mode={validator_type} validator in the'
                f' discriminator field {self.discriminator!r} of {source}',
                code='discriminator-validator',
            )

        else:
            raise PydanticUserError(
                f'{source} needs field {self.discriminator!r} to be of type `Literal`',
                code='discriminator-needs-literal',
            )

    def _set_unique_choice_for_values(self, choice: core_schema.CoreSchema, values: Sequence[str | int]) -> None:
        """This method updates `self.tagged_union_choices` so that all provided (discriminator) `values` map to the
        provided `choice`, validating that none of these values already map to another (different) choice.
        """
        for discriminator_value in values:
            if discriminator_value in self._tagged_union_choices:
                # It is okay if `value` is already in tagged_union_choices as long as it maps to the same value.
                # Because tagged_union_choices may map values to other values, we need to walk the choices dict
                # until we get to a "real" choice, and confirm that is equal to the one assigned.
                existing_choice = self._tagged_union_choices[discriminator_value]
                if existing_choice != choice:
                    raise TypeError(
                        f'Value {discriminator_value!r} for discriminator '
                        f'{self.discriminator!r} mapped to multiple choices'
                    )
            else:
                self._tagged_union_choices[discriminator_value] = choice

# === NexusCore/openenv\Lib\site-packages\win32\lib\win2kras.py ===
"""\
win2kras used to be an extension module with wrapped the "new" RAS functions \
in Windows 2000, so win32ras could still be used on NT/etc.
I think in 2021 we can be confident pywin32 is not used on earlier OSs, so \
that functionality is now in win32ras.

This exists just to avoid breaking old scripts.\
"""

import warnings

from win32ras import *  # nopycln: import

warnings.warn(str(__doc__), category=DeprecationWarning)

# === NexusCore/openenv\Lib\site-packages\nltk\parse\shiftreduce.py ===
# Natural Language Toolkit: Shift-Reduce Parser
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
#         Steven Bird <stevenbird1@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

from nltk.grammar import Nonterminal
from nltk.parse.api import ParserI
from nltk.tree import Tree


##//////////////////////////////////////////////////////
##  Shift/Reduce Parser
##//////////////////////////////////////////////////////
class ShiftReduceParser(ParserI):
    """
    A simple bottom-up CFG parser that uses two operations, "shift"
    and "reduce", to find a single parse for a text.

    ``ShiftReduceParser`` maintains a stack, which records the
    structure of a portion of the text.  This stack is a list of
    strings and Trees that collectively cover a portion of
    the text.  For example, while parsing the sentence "the dog saw
    the man" with a typical grammar, ``ShiftReduceParser`` will produce
    the following stack, which covers "the dog saw"::

       [(NP: (Det: 'the') (N: 'dog')), (V: 'saw')]

    ``ShiftReduceParser`` attempts to extend the stack to cover the
    entire text, and to combine the stack elements into a single tree,
    producing a complete parse for the sentence.

    Initially, the stack is empty.  It is extended to cover the text,
    from left to right, by repeatedly applying two operations:

      - "shift" moves a token from the beginning of the text to the
        end of the stack.
      - "reduce" uses a CFG production to combine the rightmost stack
        elements into a single Tree.

    Often, more than one operation can be performed on a given stack.
    In this case, ``ShiftReduceParser`` uses the following heuristics
    to decide which operation to perform:

      - Only shift if no reductions are available.
      - If multiple reductions are available, then apply the reduction
        whose CFG production is listed earliest in the grammar.

    Note that these heuristics are not guaranteed to choose an
    operation that leads to a parse of the text.  Also, if multiple
    parses exists, ``ShiftReduceParser`` will return at most one of
    them.

    :see: ``nltk.grammar``
    """

    def __init__(self, grammar, trace=0):
        """
        Create a new ``ShiftReduceParser``, that uses ``grammar`` to
        parse texts.

        :type grammar: Grammar
        :param grammar: The grammar used to parse texts.
        :type trace: int
        :param trace: The level of tracing that should be used when
            parsing a text.  ``0`` will generate no tracing output;
            and higher numbers will produce more verbose tracing
            output.
        """
        self._grammar = grammar
        self._trace = trace
        self._check_grammar()

    def grammar(self):
        return self._grammar

    def parse(self, tokens):
        tokens = list(tokens)
        self._grammar.check_coverage(tokens)

        # initialize the stack.
        stack = []
        remaining_text = tokens

        # Trace output.
        if self._trace:
            print("Parsing %r" % " ".join(tokens))
            self._trace_stack(stack, remaining_text)

        # iterate through the text, pushing the token onto
        # the stack, then reducing the stack.
        while len(remaining_text) > 0:
            self._shift(stack, remaining_text)
            while self._reduce(stack, remaining_text):
                pass

        # Did we reduce everything?
        if len(stack) == 1:
            # Did we end up with the right category?
            if stack[0].label() == self._grammar.start().symbol():
                yield stack[0]

    def _shift(self, stack, remaining_text):
        """
        Move a token from the beginning of ``remaining_text`` to the
        end of ``stack``.

        :type stack: list(str and Tree)
        :param stack: A list of strings and Trees, encoding
            the structure of the text that has been parsed so far.
        :type remaining_text: list(str)
        :param remaining_text: The portion of the text that is not yet
            covered by ``stack``.
        :rtype: None
        """
        stack.append(remaining_text[0])
        remaining_text.remove(remaining_text[0])
        if self._trace:
            self._trace_shift(stack, remaining_text)

    def _match_rhs(self, rhs, rightmost_stack):
        """
        :rtype: bool
        :return: true if the right hand side of a CFG production
            matches the rightmost elements of the stack.  ``rhs``
            matches ``rightmost_stack`` if they are the same length,
            and each element of ``rhs`` matches the corresponding
            element of ``rightmost_stack``.  A nonterminal element of
            ``rhs`` matches any Tree whose node value is equal
            to the nonterminal's symbol.  A terminal element of ``rhs``
            matches any string whose type is equal to the terminal.
        :type rhs: list(terminal and Nonterminal)
        :param rhs: The right hand side of a CFG production.
        :type rightmost_stack: list(string and Tree)
        :param rightmost_stack: The rightmost elements of the parser's
            stack.
        """

        if len(rightmost_stack) != len(rhs):
            return False
        for i in range(len(rightmost_stack)):
            if isinstance(rightmost_stack[i], Tree):
                if not isinstance(rhs[i], Nonterminal):
                    return False
                if rightmost_stack[i].label() != rhs[i].symbol():
                    return False
            else:
                if isinstance(rhs[i], Nonterminal):
                    return False
                if rightmost_stack[i] != rhs[i]:
                    return False
        return True

    def _reduce(self, stack, remaining_text, production=None):
        """
        Find a CFG production whose right hand side matches the
        rightmost stack elements; and combine those stack elements
        into a single Tree, with the node specified by the
        production's left-hand side.  If more than one CFG production
        matches the stack, then use the production that is listed
        earliest in the grammar.  The new Tree replaces the
        elements in the stack.

        :rtype: Production or None
        :return: If a reduction is performed, then return the CFG
            production that the reduction is based on; otherwise,
            return false.
        :type stack: list(string and Tree)
        :param stack: A list of strings and Trees, encoding
            the structure of the text that has been parsed so far.
        :type remaining_text: list(str)
        :param remaining_text: The portion of the text that is not yet
            covered by ``stack``.
        """
        if production is None:
            productions = self._grammar.productions()
        else:
            productions = [production]

        # Try each production, in order.
        for production in productions:
            rhslen = len(production.rhs())

            # check if the RHS of a production matches the top of the stack
            if self._match_rhs(production.rhs(), stack[-rhslen:]):
                # combine the tree to reflect the reduction
                tree = Tree(production.lhs().symbol(), stack[-rhslen:])
                stack[-rhslen:] = [tree]

                # We reduced something
                if self._trace:
                    self._trace_reduce(stack, production, remaining_text)
                return production

        # We didn't reduce anything
        return None

    def trace(self, trace=2):
        """
        Set the level of tracing output that should be generated when
        parsing a text.

        :type trace: int
        :param trace: The trace level.  A trace level of ``0`` will
            generate no tracing output; and higher trace levels will
            produce more verbose tracing output.
        :rtype: None
        """
        # 1: just show shifts.
        # 2: show shifts & reduces
        # 3: display which tokens & productions are shifed/reduced
        self._trace = trace

    def _trace_stack(self, stack, remaining_text, marker=" "):
        """
        Print trace output displaying the given stack and text.

        :rtype: None
        :param marker: A character that is printed to the left of the
            stack.  This is used with trace level 2 to print 'S'
            before shifted stacks and 'R' before reduced stacks.
        """
        s = "  " + marker + " [ "
        for elt in stack:
            if isinstance(elt, Tree):
                s += repr(Nonterminal(elt.label())) + " "
            else:
                s += repr(elt) + " "
        s += "* " + " ".join(remaining_text) + "]"
        print(s)

    def _trace_shift(self, stack, remaining_text):
        """
        Print trace output displaying that a token has been shifted.

        :rtype: None
        """
        if self._trace > 2:
            print("Shift %r:" % stack[-1])
        if self._trace == 2:
            self._trace_stack(stack, remaining_text, "S")
        elif self._trace > 0:
            self._trace_stack(stack, remaining_text)

    def _trace_reduce(self, stack, production, remaining_text):
        """
        Print trace output displaying that ``production`` was used to
        reduce ``stack``.

        :rtype: None
        """
        if self._trace > 2:
            rhs = " ".join(production.rhs())
            print(f"Reduce {production.lhs()!r} <- {rhs}")
        if self._trace == 2:
            self._trace_stack(stack, remaining_text, "R")
        elif self._trace > 1:
            self._trace_stack(stack, remaining_text)

    def _check_grammar(self):
        """
        Check to make sure that all of the CFG productions are
        potentially useful.  If any productions can never be used,
        then print a warning.

        :rtype: None
        """
        productions = self._grammar.productions()

        # Any production whose RHS is an extension of another production's RHS
        # will never be used.
        for i in range(len(productions)):
            for j in range(i + 1, len(productions)):
                rhs1 = productions[i].rhs()
                rhs2 = productions[j].rhs()
                if rhs1[: len(rhs2)] == rhs2:
                    print("Warning: %r will never be used" % productions[i])


##//////////////////////////////////////////////////////
##  Stepping Shift/Reduce Parser
##//////////////////////////////////////////////////////
class SteppingShiftReduceParser(ShiftReduceParser):
    """
    A ``ShiftReduceParser`` that allows you to setp through the parsing
    process, performing a single operation at a time.  It also allows
    you to change the parser's grammar midway through parsing a text.

    The ``initialize`` method is used to start parsing a text.
    ``shift`` performs a single shift operation, and ``reduce`` performs
    a single reduce operation.  ``step`` will perform a single reduce
    operation if possible; otherwise, it will perform a single shift
    operation.  ``parses`` returns the set of parses that have been
    found by the parser.

    :ivar _history: A list of ``(stack, remaining_text)`` pairs,
        containing all of the previous states of the parser.  This
        history is used to implement the ``undo`` operation.
    :see: ``nltk.grammar``
    """

    def __init__(self, grammar, trace=0):
        super().__init__(grammar, trace)
        self._stack = None
        self._remaining_text = None
        self._history = []

    def parse(self, tokens):
        tokens = list(tokens)
        self.initialize(tokens)
        while self.step():
            pass
        return self.parses()

    def stack(self):
        """
        :return: The parser's stack.
        :rtype: list(str and Tree)
        """
        return self._stack

    def remaining_text(self):
        """
        :return: The portion of the text that is not yet covered by the
            stack.
        :rtype: list(str)
        """
        return self._remaining_text

    def initialize(self, tokens):
        """
        Start parsing a given text.  This sets the parser's stack to
        ``[]`` and sets its remaining text to ``tokens``.
        """
        self._stack = []
        self._remaining_text = tokens
        self._history = []

    def step(self):
        """
        Perform a single parsing operation.  If a reduction is
        possible, then perform that reduction, and return the
        production that it is based on.  Otherwise, if a shift is
        possible, then perform it, and return True.  Otherwise,
        return False.

        :return: False if no operation was performed; True if a shift was
            performed; and the CFG production used to reduce if a
            reduction was performed.
        :rtype: Production or bool
        """
        return self.reduce() or self.shift()

    def shift(self):
        """
        Move a token from the beginning of the remaining text to the
        end of the stack.  If there are no more tokens in the
        remaining text, then do nothing.

        :return: True if the shift operation was successful.
        :rtype: bool
        """
        if len(self._remaining_text) == 0:
            return False
        self._history.append((self._stack[:], self._remaining_text[:]))
        self._shift(self._stack, self._remaining_text)
        return True

    def reduce(self, production=None):
        """
        Use ``production`` to combine the rightmost stack elements into
        a single Tree.  If ``production`` does not match the
        rightmost stack elements, then do nothing.

        :return: The production used to reduce the stack, if a
            reduction was performed.  If no reduction was performed,
            return None.

        :rtype: Production or None
        """
        self._history.append((self._stack[:], self._remaining_text[:]))
        return_val = self._reduce(self._stack, self._remaining_text, production)

        if not return_val:
            self._history.pop()
        return return_val

    def undo(self):
        """
        Return the parser to its state before the most recent
        shift or reduce operation.  Calling ``undo`` repeatedly return
        the parser to successively earlier states.  If no shift or
        reduce operations have been performed, ``undo`` will make no
        changes.

        :return: true if an operation was successfully undone.
        :rtype: bool
        """
        if len(self._history) == 0:
            return False
        (self._stack, self._remaining_text) = self._history.pop()
        return True

    def reducible_productions(self):
        """
        :return: A list of the productions for which reductions are
            available for the current parser state.
        :rtype: list(Production)
        """
        productions = []
        for production in self._grammar.productions():
            rhslen = len(production.rhs())
            if self._match_rhs(production.rhs(), self._stack[-rhslen:]):
                productions.append(production)
        return productions

    def parses(self):
        """
        :return: An iterator of the parses that have been found by this
            parser so far.
        :rtype: iter(Tree)
        """
        if (
            len(self._remaining_text) == 0
            and len(self._stack) == 1
            and self._stack[0].label() == self._grammar.start().symbol()
        ):
            yield self._stack[0]

    # copied from nltk.parser

    def set_grammar(self, grammar):
        """
        Change the grammar used to parse texts.

        :param grammar: The new grammar.
        :type grammar: CFG
        """
        self._grammar = grammar


##//////////////////////////////////////////////////////
##  Demonstration Code
##//////////////////////////////////////////////////////


def demo():
    """
    A demonstration of the shift-reduce parser.
    """

    from nltk import CFG, parse

    grammar = CFG.fromstring(
        """
    S -> NP VP
    NP -> Det N | Det N PP
    VP -> V NP | V NP PP
    PP -> P NP
    NP -> 'I'
    N -> 'man' | 'park' | 'telescope' | 'dog'
    Det -> 'the' | 'a'
    P -> 'in' | 'with'
    V -> 'saw'
    """
    )

    sent = "I saw a man in the park".split()

    parser = parse.ShiftReduceParser(grammar, trace=2)
    for p in parser.parse(sent):
        print(p)


if __name__ == "__main__":
    demo()

# === NexusCore/openenv\Lib\site-packages\pyasn1_modules\rfc4357.py ===
#
# This file is part of pyasn1-modules software.
#
# Created by Russ Housley with assistance from asn1ate v.0.6.0.
#
# Copyright (c) 2019, Vigil Security, LLC
# License: http://snmplabs.com/pyasn1/license.html
#
# Additional Cryptographic Algorithms for Use with GOST 28147-89,
# GOST R 34.10-94, GOST R 34.10-2001, and GOST R 34.11-94 Algorithms
#
# ASN.1 source from:
# https://www.rfc-editor.org/rfc/rfc4357.txt
# https://www.rfc-editor.org/errata/eid5927
# https://www.rfc-editor.org/errata/eid5928
#

from pyasn1.type import constraint
from pyasn1.type import namedtype
from pyasn1.type import namedval
from pyasn1.type import tag
from pyasn1.type import univ

from pyasn1_modules import rfc5280


# Import from RFC 5280

AlgorithmIdentifier = rfc5280.AlgorithmIdentifier


# Object Identifiers

id_CryptoPro = univ.ObjectIdentifier((1, 2, 643, 2, 2,))


id_CryptoPro_modules = id_CryptoPro + (1, 1,)

id_CryptoPro_extensions = id_CryptoPro + (34,)

id_CryptoPro_policyIds = id_CryptoPro + (38,)

id_CryptoPro_policyQt = id_CryptoPro + (39,)


cryptographic_Gost_Useful_Definitions = id_CryptoPro_modules + (0, 1,)

gostR3411_94_DigestSyntax = id_CryptoPro_modules + (1, 1,)

gostR3410_94_PKISyntax = id_CryptoPro_modules + (2, 1,)

gostR3410_94_SignatureSyntax = id_CryptoPro_modules + (3, 1,)

gost28147_89_EncryptionSyntax = id_CryptoPro_modules + (4, 1,)

gostR3410_EncryptionSyntax = id_CryptoPro_modules + (5, 2,)

gost28147_89_ParamSetSyntax = id_CryptoPro_modules + (6, 1,)

gostR3411_94_ParamSetSyntax = id_CryptoPro_modules + (7, 1,)

gostR3410_94_ParamSetSyntax = id_CryptoPro_modules + (8, 1, 1)

gostR3410_2001_PKISyntax = id_CryptoPro_modules + (9, 1,)

gostR3410_2001_SignatureSyntax = id_CryptoPro_modules + (10, 1,)

gostR3410_2001_ParamSetSyntax = id_CryptoPro_modules + (12, 1,)

gost_CryptoPro_ExtendedKeyUsage = id_CryptoPro_modules + (13, 1,)

gost_CryptoPro_PrivateKey = id_CryptoPro_modules + (14, 1,)

gost_CryptoPro_PKIXCMP = id_CryptoPro_modules + (15, 1,)

gost_CryptoPro_TLS = id_CryptoPro_modules + (16, 1,)

gost_CryptoPro_Policy = id_CryptoPro_modules + (17, 1,)

gost_CryptoPro_Constants = id_CryptoPro_modules + (18, 1,)


id_CryptoPro_algorithms = id_CryptoPro

id_GostR3411_94_with_GostR3410_2001 = id_CryptoPro_algorithms + (3,)

id_GostR3411_94_with_GostR3410_94 = id_CryptoPro_algorithms + (4,)

id_GostR3411_94 = id_CryptoPro_algorithms + (9,)

id_Gost28147_89_None_KeyMeshing = id_CryptoPro_algorithms + (14, 0,)

id_Gost28147_89_CryptoPro_KeyMeshing = id_CryptoPro_algorithms + (14, 1,)

id_GostR3410_2001 = id_CryptoPro_algorithms + (19,)

id_GostR3410_94 = id_CryptoPro_algorithms + (20,)

id_Gost28147_89 = id_CryptoPro_algorithms + (21,)

id_Gost28147_89_MAC = id_CryptoPro_algorithms + (22,)

id_CryptoPro_hashes = id_CryptoPro_algorithms + (30,)

id_CryptoPro_encrypts = id_CryptoPro_algorithms + (31,)

id_CryptoPro_signs = id_CryptoPro_algorithms + (32,)

id_CryptoPro_exchanges = id_CryptoPro_algorithms + (33,)

id_CryptoPro_ecc_signs = id_CryptoPro_algorithms + (35,)

id_CryptoPro_ecc_exchanges = id_CryptoPro_algorithms + (36,)

id_CryptoPro_private_keys = id_CryptoPro_algorithms + (37,)

id_CryptoPro_pkixcmp_infos = id_CryptoPro_algorithms + (41,)

id_CryptoPro_audit_service_types = id_CryptoPro_algorithms + (42,)

id_CryptoPro_audit_record_types = id_CryptoPro_algorithms + (43,)

id_CryptoPro_attributes = id_CryptoPro_algorithms + (44,)

id_CryptoPro_name_service_types = id_CryptoPro_algorithms + (45,)

id_GostR3410_2001DH = id_CryptoPro_algorithms + (98,)

id_GostR3410_94DH = id_CryptoPro_algorithms + (99,)


id_Gost28147_89_TestParamSet = id_CryptoPro_encrypts + (0,)

id_Gost28147_89_CryptoPro_A_ParamSet = id_CryptoPro_encrypts + (1,)

id_Gost28147_89_CryptoPro_B_ParamSet = id_CryptoPro_encrypts + (2,)

id_Gost28147_89_CryptoPro_C_ParamSet = id_CryptoPro_encrypts + (3,)

id_Gost28147_89_CryptoPro_D_ParamSet = id_CryptoPro_encrypts + (4,)

id_Gost28147_89_CryptoPro_Oscar_1_1_ParamSet = id_CryptoPro_encrypts + (5,)

id_Gost28147_89_CryptoPro_Oscar_1_0_ParamSet = id_CryptoPro_encrypts + (6,)

id_Gost28147_89_CryptoPro_RIC_1_ParamSet = id_CryptoPro_encrypts + (7,)


id_GostR3410_2001_TestParamSet = id_CryptoPro_ecc_signs + (0,)

id_GostR3410_2001_CryptoPro_A_ParamSet = id_CryptoPro_ecc_signs + (1,)

id_GostR3410_2001_CryptoPro_B_ParamSet = id_CryptoPro_ecc_signs + (2,)

id_GostR3410_2001_CryptoPro_C_ParamSet = id_CryptoPro_ecc_signs + (3,)


id_GostR3410_2001_CryptoPro_XchA_ParamSet = id_CryptoPro_ecc_exchanges + (0,)

id_GostR3410_2001_CryptoPro_XchB_ParamSet = id_CryptoPro_ecc_exchanges + (1,)


id_GostR3410_94_TestParamSet = id_CryptoPro_signs + (0,)

id_GostR3410_94_CryptoPro_A_ParamSet = id_CryptoPro_signs + (2,)

id_GostR3410_94_CryptoPro_B_ParamSet = id_CryptoPro_signs + (3,)

id_GostR3410_94_CryptoPro_C_ParamSet = id_CryptoPro_signs + (4,)

id_GostR3410_94_CryptoPro_D_ParamSet = id_CryptoPro_signs + (5,)


id_GostR3410_94_CryptoPro_XchA_ParamSet = id_CryptoPro_exchanges + (1,)

id_GostR3410_94_CryptoPro_XchB_ParamSet = id_CryptoPro_exchanges + (2,)

id_GostR3410_94_CryptoPro_XchC_ParamSet = id_CryptoPro_exchanges + (3,)


id_GostR3410_94_a = id_GostR3410_94 + (1,)

id_GostR3410_94_aBis = id_GostR3410_94 + (2,)

id_GostR3410_94_b = id_GostR3410_94 + (3,)

id_GostR3410_94_bBis = id_GostR3410_94 + (4,)


id_GostR3411_94_TestParamSet = id_CryptoPro_hashes + (0,)

id_GostR3411_94_CryptoProParamSet = id_CryptoPro_hashes + (1,)




class Gost28147_89_ParamSet(univ.ObjectIdentifier):
    pass

Gost28147_89_ParamSet.subtypeSpec = constraint.SingleValueConstraint(
    id_Gost28147_89_TestParamSet,
    id_Gost28147_89_CryptoPro_A_ParamSet,
    id_Gost28147_89_CryptoPro_B_ParamSet,
    id_Gost28147_89_CryptoPro_C_ParamSet,
    id_Gost28147_89_CryptoPro_D_ParamSet,
    id_Gost28147_89_CryptoPro_Oscar_1_1_ParamSet,
    id_Gost28147_89_CryptoPro_Oscar_1_0_ParamSet,
    id_Gost28147_89_CryptoPro_RIC_1_ParamSet
)


class Gost28147_89_BlobParameters(univ.Sequence):
    pass

Gost28147_89_BlobParameters.componentType = namedtype.NamedTypes(
    namedtype.NamedType('encryptionParamSet', Gost28147_89_ParamSet())
)


class Gost28147_89_MAC(univ.OctetString):
    pass

Gost28147_89_MAC.subtypeSpec = constraint.ValueSizeConstraint(1, 4)


class Gost28147_89_Key(univ.OctetString):
    pass

Gost28147_89_Key.subtypeSpec = constraint.ValueSizeConstraint(32, 32)


class Gost28147_89_EncryptedKey(univ.Sequence):
    pass

Gost28147_89_EncryptedKey.componentType = namedtype.NamedTypes(
    namedtype.NamedType('encryptedKey', Gost28147_89_Key()),
    namedtype.OptionalNamedType('maskKey', Gost28147_89_Key().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.NamedType('macKey', Gost28147_89_MAC())
)


class Gost28147_89_IV(univ.OctetString):
    pass

Gost28147_89_IV.subtypeSpec = constraint.ValueSizeConstraint(8, 8)


class Gost28147_89_UZ(univ.OctetString):
    pass

Gost28147_89_UZ.subtypeSpec = constraint.ValueSizeConstraint(64, 64)


class Gost28147_89_ParamSetParameters(univ.Sequence):
    pass

Gost28147_89_ParamSetParameters.componentType = namedtype.NamedTypes(
    namedtype.NamedType('eUZ', Gost28147_89_UZ()),
    namedtype.NamedType('mode',
        univ.Integer(namedValues=namedval.NamedValues(
            ('gost28147-89-CNT', 0),
            ('gost28147-89-CFB', 1),
            ('cryptoPro-CBC', 2)
    ))),
    namedtype.NamedType('shiftBits',
        univ.Integer(namedValues=namedval.NamedValues(
            ('gost28147-89-block', 64)
    ))),
    namedtype.NamedType('keyMeshing', AlgorithmIdentifier())
)


class Gost28147_89_Parameters(univ.Sequence):
    pass

Gost28147_89_Parameters.componentType = namedtype.NamedTypes(
    namedtype.NamedType('iv', Gost28147_89_IV()),
    namedtype.NamedType('encryptionParamSet', Gost28147_89_ParamSet())
)


class GostR3410_2001_CertificateSignature(univ.BitString):
    pass

GostR3410_2001_CertificateSignature.subtypeSpec=constraint.ValueSizeConstraint(256, 512)


class GostR3410_2001_ParamSetParameters(univ.Sequence):
    pass

GostR3410_2001_ParamSetParameters.componentType = namedtype.NamedTypes(
    namedtype.NamedType('a', univ.Integer()),
    namedtype.NamedType('b', univ.Integer()),
    namedtype.NamedType('p', univ.Integer()),
    namedtype.NamedType('q', univ.Integer()),
    namedtype.NamedType('x', univ.Integer()),
    namedtype.NamedType('y', univ.Integer())
)


class GostR3410_2001_PublicKey(univ.OctetString):
    pass

GostR3410_2001_PublicKey.subtypeSpec = constraint.ValueSizeConstraint(64, 64)


class GostR3410_2001_PublicKeyParameters(univ.Sequence):
    pass

GostR3410_2001_PublicKeyParameters.componentType = namedtype.NamedTypes(
    namedtype.NamedType('publicKeyParamSet', univ.ObjectIdentifier().subtype(
        subtypeSpec=constraint.SingleValueConstraint(
            id_GostR3410_2001_TestParamSet,
            id_GostR3410_2001_CryptoPro_A_ParamSet,
            id_GostR3410_2001_CryptoPro_B_ParamSet,
            id_GostR3410_2001_CryptoPro_C_ParamSet,
            id_GostR3410_2001_CryptoPro_XchA_ParamSet,
            id_GostR3410_2001_CryptoPro_XchB_ParamSet
    ))),
    namedtype.NamedType('digestParamSet', univ.ObjectIdentifier().subtype(
        subtypeSpec=constraint.SingleValueConstraint(
            id_GostR3411_94_TestParamSet,
            id_GostR3411_94_CryptoProParamSet
    ))),
    namedtype.DefaultedNamedType('encryptionParamSet',
        Gost28147_89_ParamSet().subtype(value=id_Gost28147_89_CryptoPro_A_ParamSet
    ))
)


class GostR3410_94_CertificateSignature(univ.BitString):
    pass

GostR3410_94_CertificateSignature.subtypeSpec = constraint.ValueSizeConstraint(256, 512)


class GostR3410_94_ParamSetParameters_t(univ.Integer):
    pass

GostR3410_94_ParamSetParameters_t.subtypeSpec = constraint.SingleValueConstraint(512, 1024)


class GostR3410_94_ParamSetParameters(univ.Sequence):
    pass

GostR3410_94_ParamSetParameters.componentType = namedtype.NamedTypes(
    namedtype.NamedType('t', GostR3410_94_ParamSetParameters_t()),
    namedtype.NamedType('p', univ.Integer()),
    namedtype.NamedType('q', univ.Integer()),
    namedtype.NamedType('a', univ.Integer()),
    namedtype.OptionalNamedType('validationAlgorithm', AlgorithmIdentifier())
)


class GostR3410_94_PublicKey(univ.OctetString):
    pass

GostR3410_94_PublicKey.subtypeSpec = constraint.ConstraintsUnion(
    constraint.ValueSizeConstraint(64, 64),
    constraint.ValueSizeConstraint(128, 128)
)


class GostR3410_94_PublicKeyParameters(univ.Sequence):
    pass

GostR3410_94_PublicKeyParameters.componentType = namedtype.NamedTypes(
    namedtype.NamedType('publicKeyParamSet', univ.ObjectIdentifier().subtype(
        subtypeSpec=constraint.SingleValueConstraint(
            id_GostR3410_94_TestParamSet,
            id_GostR3410_94_CryptoPro_A_ParamSet,
            id_GostR3410_94_CryptoPro_B_ParamSet,
            id_GostR3410_94_CryptoPro_C_ParamSet,
            id_GostR3410_94_CryptoPro_D_ParamSet,
            id_GostR3410_94_CryptoPro_XchA_ParamSet,
            id_GostR3410_94_CryptoPro_XchB_ParamSet,
            id_GostR3410_94_CryptoPro_XchC_ParamSet
    ))),
    namedtype.NamedType('digestParamSet', univ.ObjectIdentifier().subtype(
        subtypeSpec=constraint.SingleValueConstraint(
            id_GostR3411_94_TestParamSet,
            id_GostR3411_94_CryptoProParamSet
    ))),
    namedtype.DefaultedNamedType('encryptionParamSet',
        Gost28147_89_ParamSet().subtype(value=id_Gost28147_89_CryptoPro_A_ParamSet
    ))
)


class GostR3410_94_ValidationBisParameters_c(univ.Integer):
    pass

GostR3410_94_ValidationBisParameters_c.subtypeSpec = constraint.ValueRangeConstraint(0, 4294967295)


class GostR3410_94_ValidationBisParameters(univ.Sequence):
    pass

GostR3410_94_ValidationBisParameters.componentType = namedtype.NamedTypes(
    namedtype.NamedType('x0', GostR3410_94_ValidationBisParameters_c()),
    namedtype.NamedType('c', GostR3410_94_ValidationBisParameters_c()),
    namedtype.OptionalNamedType('d', univ.Integer())
)


class GostR3410_94_ValidationParameters_c(univ.Integer):
    pass

GostR3410_94_ValidationParameters_c.subtypeSpec = constraint.ValueRangeConstraint(0, 65535)


class GostR3410_94_ValidationParameters(univ.Sequence):
    pass

GostR3410_94_ValidationParameters.componentType = namedtype.NamedTypes(
    namedtype.NamedType('x0', GostR3410_94_ValidationParameters_c()),
    namedtype.NamedType('c', GostR3410_94_ValidationParameters_c()),
    namedtype.OptionalNamedType('d', univ.Integer())
)


class GostR3411_94_Digest(univ.OctetString):
    pass

GostR3411_94_Digest.subtypeSpec = constraint.ValueSizeConstraint(32, 32)


class GostR3411_94_DigestParameters(univ.ObjectIdentifier):
    pass

GostR3411_94_DigestParameters.subtypeSpec = constraint.ConstraintsUnion(
     constraint.SingleValueConstraint(id_GostR3411_94_TestParamSet),
     constraint.SingleValueConstraint(id_GostR3411_94_CryptoProParamSet),
)


class GostR3411_94_ParamSetParameters(univ.Sequence):
    pass

GostR3411_94_ParamSetParameters.componentType = namedtype.NamedTypes(
    namedtype.NamedType('hUZ', Gost28147_89_UZ()),
    namedtype.NamedType('h0', GostR3411_94_Digest())
)


# Update the Algorithm Identifier map in rfc5280.py

_algorithmIdentifierMapUpdate = {
    id_Gost28147_89: Gost28147_89_Parameters(),
    id_Gost28147_89_TestParamSet: Gost28147_89_ParamSetParameters(),
    id_Gost28147_89_CryptoPro_A_ParamSet: Gost28147_89_ParamSetParameters(),
    id_Gost28147_89_CryptoPro_B_ParamSet: Gost28147_89_ParamSetParameters(),
    id_Gost28147_89_CryptoPro_C_ParamSet: Gost28147_89_ParamSetParameters(),
    id_Gost28147_89_CryptoPro_D_ParamSet: Gost28147_89_ParamSetParameters(),
    id_Gost28147_89_CryptoPro_KeyMeshing: univ.Null(""),
    id_Gost28147_89_None_KeyMeshing: univ.Null(""),
    id_GostR3410_94: GostR3410_94_PublicKeyParameters(),
    id_GostR3410_94_TestParamSet: GostR3410_94_ParamSetParameters(),
    id_GostR3410_94_CryptoPro_A_ParamSet: GostR3410_94_ParamSetParameters(),
    id_GostR3410_94_CryptoPro_B_ParamSet: GostR3410_94_ParamSetParameters(),
    id_GostR3410_94_CryptoPro_C_ParamSet: GostR3410_94_ParamSetParameters(),
    id_GostR3410_94_CryptoPro_D_ParamSet: GostR3410_94_ParamSetParameters(),
    id_GostR3410_94_CryptoPro_XchA_ParamSet: GostR3410_94_ParamSetParameters(),
    id_GostR3410_94_CryptoPro_XchB_ParamSet: GostR3410_94_ParamSetParameters(),
    id_GostR3410_94_CryptoPro_XchC_ParamSet: GostR3410_94_ParamSetParameters(),
    id_GostR3410_94_a: GostR3410_94_ValidationParameters(),
    id_GostR3410_94_aBis: GostR3410_94_ValidationBisParameters(),
    id_GostR3410_94_b: GostR3410_94_ValidationParameters(),
    id_GostR3410_94_bBis: GostR3410_94_ValidationBisParameters(),
    id_GostR3410_2001: univ.Null(""),
    id_GostR3411_94: univ.Null(""),
    id_GostR3411_94_TestParamSet: GostR3411_94_ParamSetParameters(),
    id_GostR3411_94_CryptoProParamSet: GostR3411_94_ParamSetParameters(),
}

rfc5280.algorithmIdentifierMap.update(_algorithmIdentifierMapUpdate)

# === NexusCore/openenv\Lib\site-packages\setuptools\command\bdist_egg.py ===
"""setuptools.command.bdist_egg

Build .egg distributions"""

from __future__ import annotations

import marshal
import os
import re
import sys
import textwrap
from sysconfig import get_path, get_platform, get_python_version
from types import CodeType
from typing import TYPE_CHECKING, Literal

from setuptools import Command
from setuptools.extension import Library

from .._path import StrPathT, ensure_directory

from distutils import log
from distutils.dir_util import mkpath, remove_tree

if TYPE_CHECKING:
    from typing_extensions import TypeAlias

# Same as zipfile._ZipFileMode from typeshed
_ZipFileMode: TypeAlias = Literal["r", "w", "x", "a"]


def _get_purelib():
    return get_path("purelib")


def strip_module(filename):
    if '.' in filename:
        filename = os.path.splitext(filename)[0]
    if filename.endswith('module'):
        filename = filename[:-6]
    return filename


def sorted_walk(dir):
    """Do os.walk in a reproducible way,
    independent of indeterministic filesystem readdir order
    """
    for base, dirs, files in os.walk(dir):
        dirs.sort()
        files.sort()
        yield base, dirs, files


def write_stub(resource, pyfile) -> None:
    _stub_template = textwrap.dedent(
        """
        def __bootstrap__():
            global __bootstrap__, __loader__, __file__
            import sys, importlib.resources as irs, importlib.util
            with irs.as_file(irs.files(__name__).joinpath(%r)) as __file__:
                __loader__ = None; del __bootstrap__, __loader__
                spec = importlib.util.spec_from_file_location(__name__,__file__)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
        __bootstrap__()
        """
    ).lstrip()
    with open(pyfile, 'w', encoding="utf-8") as f:
        f.write(_stub_template % resource)


class bdist_egg(Command):
    description = 'create an "egg" distribution'

    user_options = [
        ('bdist-dir=', 'b', "temporary directory for creating the distribution"),
        (
            'plat-name=',
            'p',
            "platform name to embed in generated filenames "
            "(by default uses `sysconfig.get_platform()`)",
        ),
        ('exclude-source-files', None, "remove all .py files from the generated egg"),
        (
            'keep-temp',
            'k',
            "keep the pseudo-installation tree around after "
            "creating the distribution archive",
        ),
        ('dist-dir=', 'd', "directory to put final built distributions in"),
        ('skip-build', None, "skip rebuilding everything (for testing/debugging)"),
    ]

    boolean_options = ['keep-temp', 'skip-build', 'exclude-source-files']

    def initialize_options(self):
        self.bdist_dir = None
        self.plat_name = None
        self.keep_temp = False
        self.dist_dir = None
        self.skip_build = False
        self.egg_output = None
        self.exclude_source_files = None

    def finalize_options(self) -> None:
        ei_cmd = self.ei_cmd = self.get_finalized_command("egg_info")
        self.egg_info = ei_cmd.egg_info

        if self.bdist_dir is None:
            bdist_base = self.get_finalized_command('bdist').bdist_base
            self.bdist_dir = os.path.join(bdist_base, 'egg')

        if self.plat_name is None:
            self.plat_name = get_platform()

        self.set_undefined_options('bdist', ('dist_dir', 'dist_dir'))

        if self.egg_output is None:
            # Compute filename of the output egg
            basename = ei_cmd._get_egg_basename(
                py_version=get_python_version(),
                platform=self.distribution.has_ext_modules() and self.plat_name,
            )

            self.egg_output = os.path.join(self.dist_dir, basename + '.egg')

    def do_install_data(self) -> None:
        # Hack for packages that install data to install's --install-lib
        self.get_finalized_command('install').install_lib = self.bdist_dir

        site_packages = os.path.normcase(os.path.realpath(_get_purelib()))
        old, self.distribution.data_files = self.distribution.data_files, []

        for item in old:
            if isinstance(item, tuple) and len(item) == 2:
                if os.path.isabs(item[0]):
                    realpath = os.path.realpath(item[0])
                    normalized = os.path.normcase(realpath)
                    if normalized == site_packages or normalized.startswith(
                        site_packages + os.sep
                    ):
                        item = realpath[len(site_packages) + 1 :], item[1]
                        # XXX else: raise ???
            self.distribution.data_files.append(item)

        try:
            log.info("installing package data to %s", self.bdist_dir)
            self.call_command('install_data', force=False, root=None)
        finally:
            self.distribution.data_files = old

    def get_outputs(self):
        return [self.egg_output]

    def call_command(self, cmdname, **kw):
        """Invoke reinitialized command `cmdname` with keyword args"""
        for dirname in INSTALL_DIRECTORY_ATTRS:
            kw.setdefault(dirname, self.bdist_dir)
        kw.setdefault('skip_build', self.skip_build)
        kw.setdefault('dry_run', self.dry_run)
        cmd = self.reinitialize_command(cmdname, **kw)
        self.run_command(cmdname)
        return cmd

    def run(self):  # noqa: C901  # is too complex (14)  # FIXME
        # Generate metadata first
        self.run_command("egg_info")
        # We run install_lib before install_data, because some data hacks
        # pull their data path from the install_lib command.
        log.info("installing library code to %s", self.bdist_dir)
        instcmd = self.get_finalized_command('install')
        old_root = instcmd.root
        instcmd.root = None
        if self.distribution.has_c_libraries() and not self.skip_build:
            self.run_command('build_clib')
        cmd = self.call_command('install_lib', warn_dir=False)
        instcmd.root = old_root

        all_outputs, ext_outputs = self.get_ext_outputs()
        self.stubs = []
        to_compile = []
        for p, ext_name in enumerate(ext_outputs):
            filename, _ext = os.path.splitext(ext_name)
            pyfile = os.path.join(self.bdist_dir, strip_module(filename) + '.py')
            self.stubs.append(pyfile)
            log.info("creating stub loader for %s", ext_name)
            if not self.dry_run:
                write_stub(os.path.basename(ext_name), pyfile)
            to_compile.append(pyfile)
            ext_outputs[p] = ext_name.replace(os.sep, '/')

        if to_compile:
            cmd.byte_compile(to_compile)
        if self.distribution.data_files:
            self.do_install_data()

        # Make the EGG-INFO directory
        archive_root = self.bdist_dir
        egg_info = os.path.join(archive_root, 'EGG-INFO')
        self.mkpath(egg_info)
        if self.distribution.scripts:
            script_dir = os.path.join(egg_info, 'scripts')
            log.info("installing scripts to %s", script_dir)
            self.call_command('install_scripts', install_dir=script_dir, no_ep=True)

        self.copy_metadata_to(egg_info)
        native_libs = os.path.join(egg_info, "native_libs.txt")
        if all_outputs:
            log.info("writing %s", native_libs)
            if not self.dry_run:
                ensure_directory(native_libs)
                with open(native_libs, 'wt', encoding="utf-8") as libs_file:
                    libs_file.write('\n'.join(all_outputs))
                    libs_file.write('\n')
        elif os.path.isfile(native_libs):
            log.info("removing %s", native_libs)
            if not self.dry_run:
                os.unlink(native_libs)

        write_safety_flag(os.path.join(archive_root, 'EGG-INFO'), self.zip_safe())

        if os.path.exists(os.path.join(self.egg_info, 'depends.txt')):
            log.warn(
                "WARNING: 'depends.txt' will not be used by setuptools 0.6!\n"
                "Use the install_requires/extras_require setup() args instead."
            )

        if self.exclude_source_files:
            self.zap_pyfiles()

        # Make the archive
        make_zipfile(
            self.egg_output,
            archive_root,
            verbose=self.verbose,
            dry_run=self.dry_run,
            mode=self.gen_header(),
        )
        if not self.keep_temp:
            remove_tree(self.bdist_dir, dry_run=self.dry_run)

        # Add to 'Distribution.dist_files' so that the "upload" command works
        getattr(self.distribution, 'dist_files', []).append((
            'bdist_egg',
            get_python_version(),
            self.egg_output,
        ))

    def zap_pyfiles(self):
        log.info("Removing .py files from temporary directory")
        for base, dirs, files in walk_egg(self.bdist_dir):
            for name in files:
                path = os.path.join(base, name)

                if name.endswith('.py'):
                    log.debug("Deleting %s", path)
                    os.unlink(path)

                if base.endswith('__pycache__'):
                    path_old = path

                    pattern = r'(?P<name>.+)\.(?P<magic>[^.]+)\.pyc'
                    m = re.match(pattern, name)
                    path_new = os.path.join(base, os.pardir, m.group('name') + '.pyc')
                    log.info(f"Renaming file from [{path_old}] to [{path_new}]")
                    try:
                        os.remove(path_new)
                    except OSError:
                        pass
                    os.rename(path_old, path_new)

    def zip_safe(self):
        safe = getattr(self.distribution, 'zip_safe', None)
        if safe is not None:
            return safe
        log.warn("zip_safe flag not set; analyzing archive contents...")
        return analyze_egg(self.bdist_dir, self.stubs)

    def gen_header(self) -> Literal["w"]:
        return 'w'

    def copy_metadata_to(self, target_dir) -> None:
        "Copy metadata (egg info) to the target_dir"
        # normalize the path (so that a forward-slash in egg_info will
        # match using startswith below)
        norm_egg_info = os.path.normpath(self.egg_info)
        prefix = os.path.join(norm_egg_info, '')
        for path in self.ei_cmd.filelist.files:
            if path.startswith(prefix):
                target = os.path.join(target_dir, path[len(prefix) :])
                ensure_directory(target)
                self.copy_file(path, target)

    def get_ext_outputs(self):
        """Get a list of relative paths to C extensions in the output distro"""

        all_outputs = []
        ext_outputs = []

        paths = {self.bdist_dir: ''}
        for base, dirs, files in sorted_walk(self.bdist_dir):
            all_outputs.extend(
                paths[base] + filename
                for filename in files
                if os.path.splitext(filename)[1].lower() in NATIVE_EXTENSIONS
            )
            for filename in dirs:
                paths[os.path.join(base, filename)] = paths[base] + filename + '/'

        if self.distribution.has_ext_modules():
            build_cmd = self.get_finalized_command('build_ext')
            for ext in build_cmd.extensions:
                if isinstance(ext, Library):
                    continue
                fullname = build_cmd.get_ext_fullname(ext.name)
                filename = build_cmd.get_ext_filename(fullname)
                if not os.path.basename(filename).startswith('dl-'):
                    if os.path.exists(os.path.join(self.bdist_dir, filename)):
                        ext_outputs.append(filename)

        return all_outputs, ext_outputs


NATIVE_EXTENSIONS: dict[str, None] = dict.fromkeys('.dll .so .dylib .pyd'.split())


def walk_egg(egg_dir):
    """Walk an unpacked egg's contents, skipping the metadata directory"""
    walker = sorted_walk(egg_dir)
    base, dirs, files = next(walker)
    if 'EGG-INFO' in dirs:
        dirs.remove('EGG-INFO')
    yield base, dirs, files
    yield from walker


def analyze_egg(egg_dir, stubs):
    # check for existing flag in EGG-INFO
    for flag, fn in safety_flags.items():
        if os.path.exists(os.path.join(egg_dir, 'EGG-INFO', fn)):
            return flag
    if not can_scan():
        return False
    safe = True
    for base, dirs, files in walk_egg(egg_dir):
        for name in files:
            if name.endswith('.py') or name.endswith('.pyw'):
                continue
            elif name.endswith('.pyc') or name.endswith('.pyo'):
                # always scan, even if we already know we're not safe
                safe = scan_module(egg_dir, base, name, stubs) and safe
    return safe


def write_safety_flag(egg_dir, safe) -> None:
    # Write or remove zip safety flag file(s)
    for flag, fn in safety_flags.items():
        fn = os.path.join(egg_dir, fn)
        if os.path.exists(fn):
            if safe is None or bool(safe) != flag:
                os.unlink(fn)
        elif safe is not None and bool(safe) == flag:
            with open(fn, 'wt', encoding="utf-8") as f:
                f.write('\n')


safety_flags = {
    True: 'zip-safe',
    False: 'not-zip-safe',
}


def scan_module(egg_dir, base, name, stubs):
    """Check whether module possibly uses unsafe-for-zipfile stuff"""

    filename = os.path.join(base, name)
    if filename[:-1] in stubs:
        return True  # Extension module
    pkg = base[len(egg_dir) + 1 :].replace(os.sep, '.')
    module = pkg + (pkg and '.' or '') + os.path.splitext(name)[0]
    skip = 16  # skip magic & reserved? & date & file size
    f = open(filename, 'rb')
    f.read(skip)
    code = marshal.load(f)
    f.close()
    safe = True
    symbols = dict.fromkeys(iter_symbols(code))
    for bad in ['__file__', '__path__']:
        if bad in symbols:
            log.warn("%s: module references %s", module, bad)
            safe = False
    if 'inspect' in symbols:
        for bad in [
            'getsource',
            'getabsfile',
            'getfile',
            'getsourcefile',
            'getsourcelines',
            'findsource',
            'getcomments',
            'getframeinfo',
            'getinnerframes',
            'getouterframes',
            'stack',
            'trace',
        ]:
            if bad in symbols:
                log.warn("%s: module MAY be using inspect.%s", module, bad)
                safe = False
    return safe


def iter_symbols(code):
    """Yield names and strings used by `code` and its nested code objects"""
    yield from code.co_names
    for const in code.co_consts:
        if isinstance(const, str):
            yield const
        elif isinstance(const, CodeType):
            yield from iter_symbols(const)


def can_scan() -> bool:
    if not sys.platform.startswith('java') and sys.platform != 'cli':
        # CPython, PyPy, etc.
        return True
    log.warn("Unable to analyze compiled code on this platform.")
    log.warn(
        "Please ask the author to include a 'zip_safe'"
        " setting (either True or False) in the package's setup.py"
    )
    return False


# Attribute names of options for commands that might need to be convinced to
# install to the egg build directory

INSTALL_DIRECTORY_ATTRS = ['install_lib', 'install_dir', 'install_data', 'install_base']


def make_zipfile(
    zip_filename: StrPathT,
    base_dir,
    verbose: bool = False,
    dry_run: bool = False,
    compress=True,
    mode: _ZipFileMode = 'w',
) -> StrPathT:
    """Create a zip file from all the files under 'base_dir'.  The output
    zip file will be named 'base_dir' + ".zip".  Uses either the "zipfile"
    Python module (if available) or the InfoZIP "zip" utility (if installed
    and found on the default search path).  If neither tool is available,
    raises DistutilsExecError.  Returns the name of the output zip file.
    """
    import zipfile

    mkpath(os.path.dirname(zip_filename), dry_run=dry_run)  # type: ignore[arg-type] # python/mypy#18075
    log.info("creating '%s' and adding '%s' to it", zip_filename, base_dir)

    def visit(z, dirname, names):
        for name in names:
            path = os.path.normpath(os.path.join(dirname, name))
            if os.path.isfile(path):
                p = path[len(base_dir) + 1 :]
                if not dry_run:
                    z.write(path, p)
                log.debug("adding '%s'", p)

    compression = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED
    if not dry_run:
        z = zipfile.ZipFile(zip_filename, mode, compression=compression)
        for dirname, dirs, files in sorted_walk(base_dir):
            visit(z, dirname, files)
        z.close()
    else:
        for dirname, dirs, files in sorted_walk(base_dir):
            visit(None, dirname, files)
    return zip_filename

# === NexusCore/openenv\Lib\site-packages\blessed\keyboard.py ===
"""Sub-module providing 'keyboard awareness'."""

# std imports
import os
import re
import time
import platform
from collections import OrderedDict

# local
from blessed._compat import TextType, unicode_chr

# isort: off
# curses
if platform.system() == 'Windows':
    # pylint: disable=import-error
    import jinxed as curses
    from jinxed.has_key import _capability_names as capability_names
else:
    import curses
    from curses.has_key import _capability_names as capability_names


class Keystroke(TextType):
    """
    A unicode-derived class for describing a single keystroke.

    A class instance describes a single keystroke received on input,
    which may contain multiple characters as a multibyte sequence,
    which is indicated by properties :attr:`is_sequence` returning
    ``True``.

    When the string is a known sequence, :attr:`code` matches terminal
    class attributes for comparison, such as ``term.KEY_LEFT``.

    The string-name of the sequence, such as ``u'KEY_LEFT'`` is accessed
    by property :attr:`name`, and is used by the :meth:`__repr__` method
    to display a human-readable form of the Keystroke this class
    instance represents. It may otherwise by joined, split, or evaluated
    just as as any other unicode string.
    """

    def __new__(cls, ucs='', code=None, name=None):
        """Class constructor."""
        new = TextType.__new__(cls, ucs)
        new._name = name
        new._code = code
        return new

    @property
    def is_sequence(self):
        """Whether the value represents a multibyte sequence (bool)."""
        return self._code is not None

    def __repr__(self):
        """Docstring overwritten."""
        return (TextType.__repr__(self) if self._name is None else
                self._name)
    __repr__.__doc__ = TextType.__doc__

    @property
    def name(self):
        """String-name of key sequence, such as ``u'KEY_LEFT'`` (str)."""
        return self._name

    @property
    def code(self):
        """Integer keycode value of multibyte sequence (int)."""
        return self._code


def get_curses_keycodes():
    """
    Return mapping of curses key-names paired by their keycode integer value.

    :rtype: dict
    :returns: Dictionary of (name, code) pairs for curses keyboard constant
        values and their mnemonic name. Such as code ``260``, with the value of
        its key-name identity, ``u'KEY_LEFT'``.
    """
    _keynames = [attr for attr in dir(curses)
                 if attr.startswith('KEY_')]
    return {keyname: getattr(curses, keyname) for keyname in _keynames}


def get_keyboard_codes():
    """
    Return mapping of keycode integer values paired by their curses key-name.

    :rtype: dict
    :returns: Dictionary of (code, name) pairs for curses keyboard constant
        values and their mnemonic name. Such as key ``260``, with the value of
        its identity, ``u'KEY_LEFT'``.

    These keys are derived from the attributes by the same of the curses module,
    with the following exceptions:

    * ``KEY_DELETE`` in place of ``KEY_DC``
    * ``KEY_INSERT`` in place of ``KEY_IC``
    * ``KEY_PGUP`` in place of ``KEY_PPAGE``
    * ``KEY_PGDOWN`` in place of ``KEY_NPAGE``
    * ``KEY_ESCAPE`` in place of ``KEY_EXIT``
    * ``KEY_SUP`` in place of ``KEY_SR``
    * ``KEY_SDOWN`` in place of ``KEY_SF``

    This function is the inverse of :func:`get_curses_keycodes`.  With the
    given override "mixins" listed above, the keycode for the delete key will
    map to our imaginary ``KEY_DELETE`` mnemonic, effectively erasing the
    phrase ``KEY_DC`` from our code vocabulary for anyone that wishes to use
    the return value to determine the key-name by keycode.
    """
    keycodes = OrderedDict(get_curses_keycodes())
    keycodes.update(CURSES_KEYCODE_OVERRIDE_MIXIN)
    # merge _CURSES_KEYCODE_ADDINS added to our module space
    keycodes.update(
        (name, value) for name, value in globals().copy().items() if name.startswith('KEY_')
    )

    # invert dictionary (key, values) => (values, key), preferring the
    # last-most inserted value ('KEY_DELETE' over 'KEY_DC').
    return dict(zip(keycodes.values(), keycodes.keys()))


def _alternative_left_right(term):
    r"""
    Determine and return mapping of left and right arrow keys sequences.

    :arg blessed.Terminal term: :class:`~.Terminal` instance.
    :rtype: dict
    :returns: Dictionary of sequences ``term._cuf1``, and ``term._cub1``,
        valued as ``KEY_RIGHT``, ``KEY_LEFT`` (when appropriate).

    This function supports :func:`get_terminal_sequences` to discover
    the preferred input sequence for the left and right application keys.

    It is necessary to check the value of these sequences to ensure we do not
    use ``u' '`` and ``u'\b'`` for ``KEY_RIGHT`` and ``KEY_LEFT``,
    preferring their true application key sequence, instead.
    """
    # pylint: disable=protected-access
    keymap = {}
    if term._cuf1 and term._cuf1 != u' ':
        keymap[term._cuf1] = curses.KEY_RIGHT
    if term._cub1 and term._cub1 != u'\b':
        keymap[term._cub1] = curses.KEY_LEFT
    return keymap


def get_keyboard_sequences(term):
    r"""
    Return mapping of keyboard sequences paired by keycodes.

    :arg blessed.Terminal term: :class:`~.Terminal` instance.
    :returns: mapping of keyboard unicode sequences paired by keycodes
        as integer.  This is used as the argument ``mapper`` to
        the supporting function :func:`resolve_sequence`.
    :rtype: OrderedDict

    Initialize and return a keyboard map and sequence lookup table,
    (sequence, keycode) from :class:`~.Terminal` instance ``term``,
    where ``sequence`` is a multibyte input sequence of unicode
    characters, such as ``u'\x1b[D'``, and ``keycode`` is an integer
    value, matching curses constant such as term.KEY_LEFT.

    The return value is an OrderedDict instance, with their keys
    sorted longest-first.
    """
    # A small gem from curses.has_key that makes this all possible,
    # _capability_names: a lookup table of terminal capability names for
    # keyboard sequences (fe. kcub1, key_left), keyed by the values of
    # constants found beginning with KEY_ in the main curses module
    # (such as KEY_LEFT).
    #
    # latin1 encoding is used so that bytes in 8-bit range of 127-255
    # have equivalent chr() and unichr() values, so that the sequence
    # of a kermit or avatar terminal, for example, remains unchanged
    # in its byte sequence values even when represented by unicode.
    #
    sequence_map = dict((
        (seq.decode('latin1'), val)
        for (seq, val) in (
            (curses.tigetstr(cap), val)
            for (val, cap) in capability_names.items()
        ) if seq
    ) if term.does_styling else ())

    sequence_map.update(_alternative_left_right(term))
    sequence_map.update(DEFAULT_SEQUENCE_MIXIN)

    # This is for fast lookup matching of sequences, preferring
    # full-length sequence such as ('\x1b[D', KEY_LEFT)
    # over simple sequences such as ('\x1b', KEY_EXIT).
    return OrderedDict((
        (seq, sequence_map[seq]) for seq in sorted(
            sequence_map.keys(), key=len, reverse=True)))


def get_leading_prefixes(sequences):
    """
    Return a set of proper prefixes for given sequence of strings.

    :arg iterable sequences
    :rtype: set
    :return: Set of all string prefixes

    Given an iterable of strings, all textparts leading up to the final
    string is returned as a unique set.  This function supports the
    :meth:`~.Terminal.inkey` method by determining whether the given
    input is a sequence that **may** lead to a final matching pattern.

    >>> prefixes(['abc', 'abdf', 'e', 'jkl'])
    set([u'a', u'ab', u'abd', u'j', u'jk'])
    """
    return {seq[:i] for seq in sequences for i in range(1, len(seq))}


def resolve_sequence(text, mapper, codes):
    r"""
    Return a single :class:`Keystroke` instance for given sequence ``text``.

    :arg str text: string of characters received from terminal input stream.
    :arg OrderedDict mapper: unicode multibyte sequences, such as ``u'\x1b[D'``
        paired by their integer value (260)
    :arg dict codes: a :type:`dict` of integer values (such as 260) paired
        by their mnemonic name, such as ``'KEY_LEFT'``.
    :rtype: Keystroke
    :returns: Keystroke instance for the given sequence

    The given ``text`` may extend beyond a matching sequence, such as
    ``u\x1b[Dxxx`` returns a :class:`Keystroke` instance of attribute
    :attr:`Keystroke.sequence` valued only ``u\x1b[D``.  It is up to
    calls to determine that ``xxx`` remains unresolved.
    """
    for sequence, code in mapper.items():
        if text.startswith(sequence):
            return Keystroke(ucs=sequence, code=code, name=codes[code])
    return Keystroke(ucs=text and text[0] or u'')


def _time_left(stime, timeout):
    """
    Return time remaining since ``stime`` before given ``timeout``.

    This function assists determining the value of ``timeout`` for
    class method :meth:`~.Terminal.kbhit` and similar functions.

    :arg float stime: starting time for measurement
    :arg float timeout: timeout period, may be set to None to
       indicate no timeout (where None is always returned).
    :rtype: float or int
    :returns: time remaining as float. If no time is remaining,
       then the integer ``0`` is returned.
    """
    return max(0, timeout - (time.time() - stime)) if timeout else timeout


def _read_until(term, pattern, timeout):
    """
    Convenience read-until-pattern function, supporting :meth:`~.get_location`.

    :arg blessed.Terminal term: :class:`~.Terminal` instance.
    :arg float timeout: timeout period, may be set to None to indicate no
        timeout (where 0 is always returned).
    :arg str pattern: target regular expression pattern to seek.
    :rtype: tuple
    :returns: tuple in form of ``(match, str)``, *match*
        may be :class:`re.MatchObject` if pattern is discovered
        in input stream before timeout has elapsed, otherwise
        None. ``str`` is any remaining text received exclusive
        of the matching pattern).

    The reason a tuple containing non-matching data is returned, is that the
    consumer should push such data back into the input buffer by
    :meth:`~.Terminal.ungetch` if any was received.

    For example, when a user is performing rapid input keystrokes while its
    terminal emulator surreptitiously responds to this in-band sequence, we
    must ensure any such keyboard data is well-received by the next call to
    term.inkey() without delay.
    """
    stime = time.time()
    match, buf = None, u''

    # first, buffer all pending data. pexpect library provides a
    # 'searchwindowsize' attribute that limits this memory region.  We're not
    # concerned about OOM conditions: only (human) keyboard input and terminal
    # response sequences are expected.

    while True:  # pragma: no branch
        # block as long as necessary to ensure at least one character is
        # received on input or remaining timeout has elapsed.
        ucs = term.inkey(timeout=_time_left(stime, timeout))
        # while the keyboard buffer is "hot" (has input), we continue to
        # aggregate all awaiting data.  We do this to ensure slow I/O
        # calls do not unnecessarily give up within the first 'while' loop
        # for short timeout periods.
        while ucs:
            buf += ucs
            ucs = term.inkey(timeout=0)

        match = re.search(pattern=pattern, string=buf)
        if match is not None:
            # match
            break

        if timeout is not None and not _time_left(stime, timeout):
            # timeout
            break

    return match, buf


#: Though we may determine *keynames* and codes for keyboard input that
#: generate multibyte sequences, it is also especially useful to aliases
#: a few basic ASCII characters such as ``KEY_TAB`` instead of ``u'\t'`` for
#: uniformity.
#:
#: Furthermore, many key-names for application keys enabled only by context
#: manager :meth:`~.Terminal.keypad` are surprisingly absent.  We inject them
#: here directly into the curses module.
_CURSES_KEYCODE_ADDINS = (
    'TAB',
    'KP_MULTIPLY',
    'KP_ADD',
    'KP_SEPARATOR',
    'KP_SUBTRACT',
    'KP_DECIMAL',
    'KP_DIVIDE',
    'KP_EQUAL',
    'KP_0',
    'KP_1',
    'KP_2',
    'KP_3',
    'KP_4',
    'KP_5',
    'KP_6',
    'KP_7',
    'KP_8',
    'KP_9')

_LASTVAL = max(get_curses_keycodes().values())
for keycode_name in _CURSES_KEYCODE_ADDINS:
    _LASTVAL += 1
    globals()['KEY_' + keycode_name] = _LASTVAL

#: In a perfect world, terminal emulators would always send exactly what
#: the terminfo(5) capability database plans for them, accordingly by the
#: value of the ``TERM`` name they declare.
#:
#: But this isn't a perfect world. Many vt220-derived terminals, such as
#: those declaring 'xterm', will continue to send vt220 codes instead of
#: their native-declared codes, for backwards-compatibility.
#:
#: This goes for many: rxvt, putty, iTerm.
#:
#: These "mixins" are used for *all* terminals, regardless of their type.
#:
#: Furthermore, curses does not provide sequences sent by the keypad,
#: at least, it does not provide a way to distinguish between keypad 0
#: and numeric 0.
DEFAULT_SEQUENCE_MIXIN = (
    # these common control characters (and 127, ctrl+'?') mapped to
    # an application key definition.
    (unicode_chr(10), curses.KEY_ENTER),
    (unicode_chr(13), curses.KEY_ENTER),
    (unicode_chr(8), curses.KEY_BACKSPACE),
    (unicode_chr(9), KEY_TAB),  # noqa  # pylint: disable=undefined-variable
    (unicode_chr(27), curses.KEY_EXIT),
    (unicode_chr(127), curses.KEY_BACKSPACE),

    (u"\x1b[A", curses.KEY_UP),
    (u"\x1b[B", curses.KEY_DOWN),
    (u"\x1b[C", curses.KEY_RIGHT),
    (u"\x1b[D", curses.KEY_LEFT),
    (u"\x1b[1;2A", curses.KEY_SR),
    (u"\x1b[1;2B", curses.KEY_SF),
    (u"\x1b[1;2C", curses.KEY_SRIGHT),
    (u"\x1b[1;2D", curses.KEY_SLEFT),
    (u"\x1b[F", curses.KEY_END),
    (u"\x1b[H", curses.KEY_HOME),
    # not sure where these are from .. please report
    (u"\x1b[K", curses.KEY_END),
    (u"\x1b[U", curses.KEY_NPAGE),
    (u"\x1b[V", curses.KEY_PPAGE),

    # keys sent after term.smkx (keypad_xmit) is emitted, source:
    # http://www.xfree86.org/current/ctlseqs.html#PC-Style%20Function%20Keys
    # http://fossies.org/linux/rxvt/doc/rxvtRef.html#KeyCodes
    #
    # keypad, numlock on
    (u"\x1bOM", curses.KEY_ENTER),  # noqa return
    (u"\x1bOj", KEY_KP_MULTIPLY),   # noqa *  # pylint: disable=undefined-variable
    (u"\x1bOk", KEY_KP_ADD),        # noqa +  # pylint: disable=undefined-variable
    (u"\x1bOl", KEY_KP_SEPARATOR),  # noqa ,  # pylint: disable=undefined-variable
    (u"\x1bOm", KEY_KP_SUBTRACT),   # noqa -  # pylint: disable=undefined-variable
    (u"\x1bOn", KEY_KP_DECIMAL),    # noqa .  # pylint: disable=undefined-variable
    (u"\x1bOo", KEY_KP_DIVIDE),     # noqa /  # pylint: disable=undefined-variable
    (u"\x1bOX", KEY_KP_EQUAL),      # noqa =  # pylint: disable=undefined-variable
    (u"\x1bOp", KEY_KP_0),          # noqa 0  # pylint: disable=undefined-variable
    (u"\x1bOq", KEY_KP_1),          # noqa 1  # pylint: disable=undefined-variable
    (u"\x1bOr", KEY_KP_2),          # noqa 2  # pylint: disable=undefined-variable
    (u"\x1bOs", KEY_KP_3),          # noqa 3  # pylint: disable=undefined-variable
    (u"\x1bOt", KEY_KP_4),          # noqa 4  # pylint: disable=undefined-variable
    (u"\x1bOu", KEY_KP_5),          # noqa 5  # pylint: disable=undefined-variable
    (u"\x1bOv", KEY_KP_6),          # noqa 6  # pylint: disable=undefined-variable
    (u"\x1bOw", KEY_KP_7),          # noqa 7  # pylint: disable=undefined-variable
    (u"\x1bOx", KEY_KP_8),          # noqa 8  # pylint: disable=undefined-variable
    (u"\x1bOy", KEY_KP_9),          # noqa 9  # pylint: disable=undefined-variable

    # keypad, numlock off
    (u"\x1b[1~", curses.KEY_FIND),         # find
    (u"\x1b[2~", curses.KEY_IC),           # insert (0)
    (u"\x1b[3~", curses.KEY_DC),           # delete (.), "Execute"
    (u"\x1b[4~", curses.KEY_SELECT),       # select
    (u"\x1b[5~", curses.KEY_PPAGE),        # pgup   (9)
    (u"\x1b[6~", curses.KEY_NPAGE),        # pgdown (3)
    (u"\x1b[7~", curses.KEY_HOME),         # home
    (u"\x1b[8~", curses.KEY_END),          # end
    (u"\x1b[OA", curses.KEY_UP),           # up     (8)
    (u"\x1b[OB", curses.KEY_DOWN),         # down   (2)
    (u"\x1b[OC", curses.KEY_RIGHT),        # right  (6)
    (u"\x1b[OD", curses.KEY_LEFT),         # left   (4)
    (u"\x1b[OF", curses.KEY_END),          # end    (1)
    (u"\x1b[OH", curses.KEY_HOME),         # home   (7)

    # The vt220 placed F1-F4 above the keypad, in place of actual
    # F1-F4 were local functions (hold screen, print screen,
    # set up, data/talk, break).
    (u"\x1bOP", curses.KEY_F1),
    (u"\x1bOQ", curses.KEY_F2),
    (u"\x1bOR", curses.KEY_F3),
    (u"\x1bOS", curses.KEY_F4),
)

#: Override mixins for a few curses constants with easier
#: mnemonics: there may only be a 1:1 mapping when only a
#: keycode (int) is given, where these phrases are preferred.
CURSES_KEYCODE_OVERRIDE_MIXIN = (
    ('KEY_DELETE', curses.KEY_DC),
    ('KEY_INSERT', curses.KEY_IC),
    ('KEY_PGUP', curses.KEY_PPAGE),
    ('KEY_PGDOWN', curses.KEY_NPAGE),
    ('KEY_ESCAPE', curses.KEY_EXIT),
    ('KEY_SUP', curses.KEY_SR),
    ('KEY_SDOWN', curses.KEY_SF),
    ('KEY_UP_LEFT', curses.KEY_A1),
    ('KEY_UP_RIGHT', curses.KEY_A3),
    ('KEY_CENTER', curses.KEY_B2),
    ('KEY_BEGIN', curses.KEY_BEG),
)

#: Default delay, in seconds, of Escape key detection in
#: :meth:`Terminal.inkey`.` curses has a default delay of 1000ms (1 second) for
#: escape sequences.  This is too long for modern applications, so we set it to
#: 350ms, or 0.35 seconds. It is still a bit conservative, for remote telnet or
#: ssh servers, for example.
DEFAULT_ESCDELAY = 0.35


def _reinit_escdelay():
    # pylint: disable=W0603
    # Using the global statement: this is necessary to
    # allow test coverage without complex module reload
    global DEFAULT_ESCDELAY
    if os.environ.get('ESCDELAY'):
        try:
            DEFAULT_ESCDELAY = int(os.environ['ESCDELAY']) / 1000.0
        except ValueError:
            # invalid values of 'ESCDELAY' are ignored
            pass


_reinit_escdelay()


__all__ = ('Keystroke', 'get_keyboard_codes', 'get_keyboard_sequences',)

# === NexusCore/openenv\Lib\site-packages\blessed\sequences.py ===
# -*- coding: utf-8 -*-
"""Module providing 'sequence awareness'."""
# std imports
import re
import math
import textwrap

# 3rd party
from wcwidth import wcwidth

# local
from blessed._compat import TextType
from blessed._capabilities import CAPABILITIES_CAUSE_MOVEMENT

__all__ = ('Sequence', 'SequenceTextWrapper', 'iter_parse', 'measure_length')


# pylint: disable=unused-argument,missing-function-docstring

class Termcap(object):
    """Terminal capability of given variable name and pattern."""

    def __init__(self, name, pattern, attribute):
        """
        Class initializer.

        :arg str name: name describing capability.
        :arg str pattern: regular expression string.
        :arg str attribute: :class:`~.Terminal` attribute used to build
            this terminal capability.
        """
        self.name = name
        self.pattern = pattern
        self.attribute = attribute
        self._re_compiled = None

    def __repr__(self):
        # pylint: disable=redundant-keyword-arg
        return '<Termcap {self.name}:{self.pattern!r}>'.format(self=self)

    @property
    def named_pattern(self):
        """Regular expression pattern for capability with named group."""
        # pylint: disable=redundant-keyword-arg
        return '(?P<{self.name}>{self.pattern})'.format(self=self)

    @property
    def re_compiled(self):
        """Compiled regular expression pattern for capability."""
        if self._re_compiled is None:
            self._re_compiled = re.compile(self.pattern)
        return self._re_compiled

    @property
    def will_move(self):
        """Whether capability causes cursor movement."""
        return self.name in CAPABILITIES_CAUSE_MOVEMENT

    def horizontal_distance(self, text):
        """
        Horizontal carriage adjusted by capability, may be negative.

        :rtype: int
        :arg str text: for capabilities *parm_left_cursor*, *parm_right_cursor*, provide the
            matching sequence text, its interpreted distance is returned.
        :returns: 0 except for matching '
        """
        value = {
            'cursor_left': -1,
            'backspace': -1,
            'cursor_right': 1,
            'tab': 8,
            'ascii_tab': 8,
        }.get(self.name)
        if value is not None:
            return value

        unit = {
            'parm_left_cursor': -1,
            'parm_right_cursor': 1
        }.get(self.name)
        if unit is not None:
            value = int(self.re_compiled.match(text).group(1))
            return unit * value

        return 0

    # pylint: disable=too-many-positional-arguments
    @classmethod
    def build(cls, name, capability, attribute, nparams=0,
              numeric=99, match_grouped=False, match_any=False,
              match_optional=False):
        r"""
        Class factory builder for given capability definition.

        :arg str name: Variable name given for this pattern.
        :arg str capability: A unicode string representing a terminal
            capability to build for. When ``nparams`` is non-zero, it
            must be a callable unicode string (such as the result from
            ``getattr(term, 'bold')``.
        :arg str attribute: The terminfo(5) capability name by which this
            pattern is known.
        :arg int nparams: number of positional arguments for callable.
        :arg int numeric: Value to substitute into capability to when generating pattern
        :arg bool match_grouped: If the numeric pattern should be
            grouped, ``(\d+)`` when ``True``, ``\d+`` default.
        :arg bool match_any: When keyword argument ``nparams`` is given,
            *any* numeric found in output is suitable for building as
            pattern ``(\d+)``.  Otherwise, only the first matching value of
            range *(numeric - 1)* through *(numeric + 1)* will be replaced by
            pattern ``(\d+)`` in builder.
        :arg bool match_optional: When ``True``, building of numeric patterns
            containing ``(\d+)`` will be built as optional, ``(\d+)?``.
        :rtype: blessed.sequences.Termcap
        :returns: Terminal capability instance for given capability definition
        """
        _numeric_regex = r'\d+'
        if match_grouped:
            _numeric_regex = r'(\d+)'
        if match_optional:
            _numeric_regex = r'(\d+)?'
        numeric = 99 if numeric is None else numeric

        # basic capability attribute, not used as a callable
        if nparams == 0:
            return cls(name, re.escape(capability), attribute)

        # a callable capability accepting numeric argument
        _outp = re.escape(capability(*(numeric,) * nparams))
        if not match_any:
            for num in range(numeric - 1, numeric + 2):
                if str(num) in _outp:
                    pattern = _outp.replace(str(num), _numeric_regex)
                    return cls(name, pattern, attribute)

        if match_grouped:
            pattern = re.sub(r'(\d+)', lambda x: _numeric_regex, _outp)
        else:
            pattern = re.sub(r'\d+', lambda x: _numeric_regex, _outp)
        return cls(name, pattern, attribute)


class SequenceTextWrapper(textwrap.TextWrapper):
    """Docstring overridden."""

    def __init__(self, width, term, **kwargs):
        """
        Class initializer.

        This class supports the :meth:`~.Terminal.wrap` method.
        """
        self.term = term
        textwrap.TextWrapper.__init__(self, width, **kwargs)

    def _wrap_chunks(self, chunks):
        """
        Sequence-aware variant of :meth:`textwrap.TextWrapper._wrap_chunks`.

        :raises ValueError: ``self.width`` is not a positive integer
        :rtype: list
        :returns: text chunks adjusted for width

        This simply ensures that word boundaries are not broken mid-sequence, as standard python
        textwrap would incorrectly determine the length of a string containing sequences, and may
        also break consider sequences part of a "word" that may be broken by hyphen (``-``), where
        this implementation corrects both.
        """
        lines = []
        if self.width <= 0 or not isinstance(self.width, int):
            raise ValueError(
                "invalid width {0!r}({1!r}) (must be integer > 0)"
                .format(self.width, type(self.width)))

        term = self.term
        drop_whitespace = not hasattr(self, 'drop_whitespace'
                                      ) or self.drop_whitespace
        chunks.reverse()
        while chunks:
            cur_line = []
            cur_len = 0
            indent = self.subsequent_indent if lines else self.initial_indent
            width = self.width - len(indent)
            if drop_whitespace and (
                    Sequence(chunks[-1], term).strip() == '' and lines):
                del chunks[-1]
            while chunks:
                chunk_len = Sequence(chunks[-1], term).length()
                if cur_len + chunk_len > width:
                    if chunk_len > width:
                        self._handle_long_word(chunks, cur_line, cur_len, width)
                    break
                cur_line.append(chunks.pop())
                cur_len += chunk_len
            if drop_whitespace and (
                    cur_line and Sequence(cur_line[-1], term).strip() == ''):
                del cur_line[-1]
            if cur_line:
                lines.append(indent + u''.join(cur_line))
        return lines

    def _handle_long_word(self, reversed_chunks, cur_line, cur_len, width):
        """
        Sequence-aware :meth:`textwrap.TextWrapper._handle_long_word`.

        This method ensures that word boundaries are not broken mid-sequence, as
        standard python textwrap would incorrectly determine the length of a
        string containing sequences and wide characters it would also break
        these "words" that would be broken by hyphen (``-``), this
        implementation corrects both.

        This is done by mutating the passed arguments, removing items from
        'reversed_chunks' and appending them to 'cur_line'.

        However, some characters (east-asian, emoji, etc.) cannot be split any
        less than 2 cells, so in the case of a width of 1, we have no choice
        but to allow those characters to flow outside of the given cell.
        """
        # Figure out when indent is larger than the specified width, and make
        # sure at least one character is stripped off on every pass
        space_left = 1 if width < 1 else width - cur_len
        # If we're allowed to break long words, then do so: put as much
        # of the next chunk onto the current line as will fit.

        if self.break_long_words:
            term = self.term
            chunk = reversed_chunks[-1]
            idx = nxt = 0
            for text, _ in iter_parse(term, chunk):
                nxt += len(text)
                seq_length = Sequence(chunk[:nxt], term).length()
                if seq_length > space_left:
                    if cur_len == 0 and width == 1 and nxt == 1 and seq_length == 2:
                        # Emoji etc. cannot be split under 2 cells, so in the
                        # case of a width of 1, we have no choice but to allow
                        # those characters to flow outside of the given cell.
                        pass
                    else:
                        break
                idx = nxt
            cur_line.append(chunk[:idx])
            reversed_chunks[-1] = chunk[idx:]

        # Otherwise, we have to preserve the long word intact.  Only add
        # it to the current line if there's nothing already there --
        # that minimizes how much we violate the width constraint.
        elif not cur_line:
            cur_line.append(reversed_chunks.pop())

        # If we're not allowed to break long words, and there's already
        # text on the current line, do nothing.  Next time through the
        # main loop of _wrap_chunks(), we'll wind up here again, but
        # cur_len will be zero, so the next line will be entirely
        # devoted to the long word that we can't handle right now.


SequenceTextWrapper.__doc__ = textwrap.TextWrapper.__doc__


class Sequence(TextType):
    """
    A "sequence-aware" version of the base :class:`str` class.

    This unicode-derived class understands the effect of escape sequences
    of printable length, allowing a properly implemented :meth:`rjust`,
    :meth:`ljust`, :meth:`center`, and :meth:`length`.
    """

    def __new__(cls, sequence_text, term):
        # pylint: disable = missing-return-doc, missing-return-type-doc
        """
        Class constructor.

        :arg str sequence_text: A string that may contain sequences.
        :arg blessed.Terminal term: :class:`~.Terminal` instance.
        """
        new = TextType.__new__(cls, sequence_text)
        new._term = term
        return new

    def ljust(self, width, fillchar=u' '):
        """
        Return string containing sequences, left-adjusted.

        :arg int width: Total width given to left-adjust ``text``.  If
            unspecified, the width of the attached terminal is used (default).
        :arg str fillchar: String for padding right-of ``text``.
        :returns: String of ``text``, left-aligned by ``width``.
        :rtype: str
        """
        rightside = fillchar * int(
            (max(0.0, float(width.__index__() - self.length()))) / float(len(fillchar)))
        return u''.join((self, rightside))

    def rjust(self, width, fillchar=u' '):
        """
        Return string containing sequences, right-adjusted.

        :arg int width: Total width given to right-adjust ``text``.  If
            unspecified, the width of the attached terminal is used (default).
        :arg str fillchar: String for padding left-of ``text``.
        :returns: String of ``text``, right-aligned by ``width``.
        :rtype: str
        """
        leftside = fillchar * int(
            (max(0.0, float(width.__index__() - self.length()))) / float(len(fillchar)))
        return u''.join((leftside, self))

    def center(self, width, fillchar=u' '):
        """
        Return string containing sequences, centered.

        :arg int width: Total width given to center ``text``.  If
            unspecified, the width of the attached terminal is used (default).
        :arg str fillchar: String for padding left and right-of ``text``.
        :returns: String of ``text``, centered by ``width``.
        :rtype: str
        """
        split = max(0.0, float(width.__index__()) - self.length()) / 2
        leftside = fillchar * int(
            (max(0.0, math.floor(split))) / float(len(fillchar)))
        rightside = fillchar * int(
            (max(0.0, math.ceil(split))) / float(len(fillchar)))
        return u''.join((leftside, self, rightside))

    def truncate(self, width):
        """
        Truncate a string in a sequence-aware manner.

        Any printable characters beyond ``width`` are removed, while all
        sequences remain in place. Horizontal Sequences are first expanded
        by :meth:`padd`.

        :arg int width: The printable width to truncate the string to.
        :rtype: str
        :returns: String truncated to at most ``width`` printable characters.
        """
        output = ""
        current_width = 0
        target_width = width.__index__()
        parsed_seq = iter_parse(self._term, self.padd())

        # Retain all text until non-cap width reaches desired width
        for text, cap in parsed_seq:
            if not cap:
                # use wcwidth clipped to 0 because it can sometimes return -1
                current_width += max(wcwidth(text), 0)
                if current_width > target_width:
                    break
            output += text

        # Return with remaining caps appended
        return output + ''.join(text for text, cap in parsed_seq if cap)

    def length(self):
        r"""
        Return the printable length of string containing sequences.

        Strings containing ``term.left`` or ``\b`` will cause "overstrike",
        but a length less than 0 is not ever returned. So ``_\b+`` is a
        length of 1 (displays as ``+``), but ``\b`` alone is simply a
        length of 0.

        Some characters may consume more than one cell, mainly those CJK
        Unified Ideographs (Chinese, Japanese, Korean) defined by Unicode
        as half or full-width characters.

        For example:

            >>> from blessed import Terminal
            >>> from blessed.sequences import Sequence
            >>> term = Terminal()
            >>> msg = term.clear + term.red(u'コンニチハ')
            >>> Sequence(msg, term).length()
            10

        .. note:: Although accounted for, strings containing sequences such
            as ``term.clear`` will not give accurate returns, it is not
            considered lengthy (a length of 0).
        """
        # because control characters may return -1, "clip" their length to 0.
        return sum(max(wcwidth(w_char), 0) for w_char in self.padd(strip=True))

    def strip(self, chars=None):
        """
        Return string of sequences, leading and trailing whitespace removed.

        :arg str chars: Remove characters in chars instead of whitespace.
        :rtype: str
        :returns: string of sequences with leading and trailing whitespace removed.
        """
        return self.strip_seqs().strip(chars)

    def lstrip(self, chars=None):
        """
        Return string of all sequences and leading whitespace removed.

        :arg str chars: Remove characters in chars instead of whitespace.
        :rtype: str
        :returns: string of sequences with leading removed.
        """
        return self.strip_seqs().lstrip(chars)

    def rstrip(self, chars=None):
        """
        Return string of all sequences and trailing whitespace removed.

        :arg str chars: Remove characters in chars instead of whitespace.
        :rtype: str
        :returns: string of sequences with trailing removed.
        """
        return self.strip_seqs().rstrip(chars)

    def strip_seqs(self):
        """
        Return ``text`` stripped of only its terminal sequences.

        :rtype: str
        :returns: Text with terminal sequences removed
        """
        return self.padd(strip=True)

    def padd(self, strip=False):
        """
        Return non-destructive horizontal movement as destructive spacing.

        :arg bool strip: Strip terminal sequences
        :rtype: str
        :returns: Text adjusted for horizontal movement
        """
        outp = ''
        for text, cap in iter_parse(self._term, self):
            if not cap:
                outp += text
                continue

            value = cap.horizontal_distance(text)
            if value > 0:
                outp += ' ' * value
            elif value < 0:
                outp = outp[:value]
            elif not strip:
                outp += text
        return outp


def iter_parse(term, text):
    """
    Generator yields (text, capability) for characters of ``text``.

    value for ``capability`` may be ``None``, where ``text`` is
    :class:`str` of length 1.  Otherwise, ``text`` is a full
    matching sequence of given capability.
    """
    for match in term._caps_compiled_any.finditer(text):  # pylint: disable=protected-access
        name = match.lastgroup
        value = match.group(name)
        if name == 'MISMATCH':
            yield (value, None)
        else:
            yield value, term.caps[name]


def measure_length(text, term):
    """
    .. deprecated:: 1.12.0.

    :rtype: int
    :returns: Length of the first sequence in the string
    """
    try:
        text, capability = next(iter_parse(term, text))
        if capability:
            return len(text)
    except StopIteration:
        return 0
    return 0

# === NexusCore/openenv\Lib\site-packages\PIL\EpsImagePlugin.py ===
#
# The Python Imaging Library.
# $Id$
#
# EPS file handling
#
# History:
# 1995-09-01 fl   Created (0.1)
# 1996-05-18 fl   Don't choke on "atend" fields, Ghostscript interface (0.2)
# 1996-08-22 fl   Don't choke on floating point BoundingBox values
# 1996-08-23 fl   Handle files from Macintosh (0.3)
# 2001-02-17 fl   Use 're' instead of 'regex' (Python 2.1) (0.4)
# 2003-09-07 fl   Check gs.close status (from Federico Di Gregorio) (0.5)
# 2014-05-07 e    Handling of EPS with binary preview and fixed resolution
#                 resizing
#
# Copyright (c) 1997-2003 by Secret Labs AB.
# Copyright (c) 1995-2003 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#
from __future__ import annotations

import io
import os
import re
import subprocess
import sys
import tempfile
from typing import IO

from . import Image, ImageFile
from ._binary import i32le as i32

# --------------------------------------------------------------------


split = re.compile(r"^%%([^:]*):[ \t]*(.*)[ \t]*$")
field = re.compile(r"^%[%!\w]([^:]*)[ \t]*$")

gs_binary: str | bool | None = None
gs_windows_binary = None


def has_ghostscript() -> bool:
    global gs_binary, gs_windows_binary
    if gs_binary is None:
        if sys.platform.startswith("win"):
            if gs_windows_binary is None:
                import shutil

                for binary in ("gswin32c", "gswin64c", "gs"):
                    if shutil.which(binary) is not None:
                        gs_windows_binary = binary
                        break
                else:
                    gs_windows_binary = False
            gs_binary = gs_windows_binary
        else:
            try:
                subprocess.check_call(["gs", "--version"], stdout=subprocess.DEVNULL)
                gs_binary = "gs"
            except OSError:
                gs_binary = False
    return gs_binary is not False


def Ghostscript(
    tile: list[ImageFile._Tile],
    size: tuple[int, int],
    fp: IO[bytes],
    scale: int = 1,
    transparency: bool = False,
) -> Image.core.ImagingCore:
    """Render an image using Ghostscript"""
    global gs_binary
    if not has_ghostscript():
        msg = "Unable to locate Ghostscript on paths"
        raise OSError(msg)
    assert isinstance(gs_binary, str)

    # Unpack decoder tile
    args = tile[0].args
    assert isinstance(args, tuple)
    length, bbox = args

    # Hack to support hi-res rendering
    scale = int(scale) or 1
    width = size[0] * scale
    height = size[1] * scale
    # resolution is dependent on bbox and size
    res_x = 72.0 * width / (bbox[2] - bbox[0])
    res_y = 72.0 * height / (bbox[3] - bbox[1])

    out_fd, outfile = tempfile.mkstemp()
    os.close(out_fd)

    infile_temp = None
    if hasattr(fp, "name") and os.path.exists(fp.name):
        infile = fp.name
    else:
        in_fd, infile_temp = tempfile.mkstemp()
        os.close(in_fd)
        infile = infile_temp

        # Ignore length and offset!
        # Ghostscript can read it
        # Copy whole file to read in Ghostscript
        with open(infile_temp, "wb") as f:
            # fetch length of fp
            fp.seek(0, io.SEEK_END)
            fsize = fp.tell()
            # ensure start position
            # go back
            fp.seek(0)
            lengthfile = fsize
            while lengthfile > 0:
                s = fp.read(min(lengthfile, 100 * 1024))
                if not s:
                    break
                lengthfile -= len(s)
                f.write(s)

    if transparency:
        # "RGBA"
        device = "pngalpha"
    else:
        # "pnmraw" automatically chooses between
        # PBM ("1"), PGM ("L"), and PPM ("RGB").
        device = "pnmraw"

    # Build Ghostscript command
    command = [
        gs_binary,
        "-q",  # quiet mode
        f"-g{width:d}x{height:d}",  # set output geometry (pixels)
        f"-r{res_x:f}x{res_y:f}",  # set input DPI (dots per inch)
        "-dBATCH",  # exit after processing
        "-dNOPAUSE",  # don't pause between pages
        "-dSAFER",  # safe mode
        f"-sDEVICE={device}",
        f"-sOutputFile={outfile}",  # output file
        # adjust for image origin
        "-c",
        f"{-bbox[0]} {-bbox[1]} translate",
        "-f",
        infile,  # input file
        # showpage (see https://bugs.ghostscript.com/show_bug.cgi?id=698272)
        "-c",
        "showpage",
    ]

    # push data through Ghostscript
    try:
        startupinfo = None
        if sys.platform.startswith("win"):
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        subprocess.check_call(command, startupinfo=startupinfo)
        with Image.open(outfile) as out_im:
            out_im.load()
            return out_im.im.copy()
    finally:
        try:
            os.unlink(outfile)
            if infile_temp:
                os.unlink(infile_temp)
        except OSError:
            pass


def _accept(prefix: bytes) -> bool:
    return prefix.startswith(b"%!PS") or (
        len(prefix) >= 4 and i32(prefix) == 0xC6D3D0C5
    )


##
# Image plugin for Encapsulated PostScript. This plugin supports only
# a few variants of this format.


class EpsImageFile(ImageFile.ImageFile):
    """EPS File Parser for the Python Imaging Library"""

    format = "EPS"
    format_description = "Encapsulated Postscript"

    mode_map = {1: "L", 2: "LAB", 3: "RGB", 4: "CMYK"}

    def _open(self) -> None:
        (length, offset) = self._find_offset(self.fp)

        # go to offset - start of "%!PS"
        self.fp.seek(offset)

        self._mode = "RGB"

        # When reading header comments, the first comment is used.
        # When reading trailer comments, the last comment is used.
        bounding_box: list[int] | None = None
        imagedata_size: tuple[int, int] | None = None

        byte_arr = bytearray(255)
        bytes_mv = memoryview(byte_arr)
        bytes_read = 0
        reading_header_comments = True
        reading_trailer_comments = False
        trailer_reached = False

        def check_required_header_comments() -> None:
            """
            The EPS specification requires that some headers exist.
            This should be checked when the header comments formally end,
            when image data starts, or when the file ends, whichever comes first.
            """
            if "PS-Adobe" not in self.info:
                msg = 'EPS header missing "%!PS-Adobe" comment'
                raise SyntaxError(msg)
            if "BoundingBox" not in self.info:
                msg = 'EPS header missing "%%BoundingBox" comment'
                raise SyntaxError(msg)

        def read_comment(s: str) -> bool:
            nonlocal bounding_box, reading_trailer_comments
            try:
                m = split.match(s)
            except re.error as e:
                msg = "not an EPS file"
                raise SyntaxError(msg) from e

            if not m:
                return False

            k, v = m.group(1, 2)
            self.info[k] = v
            if k == "BoundingBox":
                if v == "(atend)":
                    reading_trailer_comments = True
                elif not bounding_box or (trailer_reached and reading_trailer_comments):
                    try:
                        # Note: The DSC spec says that BoundingBox
                        # fields should be integers, but some drivers
                        # put floating point values there anyway.
                        bounding_box = [int(float(i)) for i in v.split()]
                    except Exception:
                        pass
            return True

        while True:
            byte = self.fp.read(1)
            if byte == b"":
                # if we didn't read a byte we must be at the end of the file
                if bytes_read == 0:
                    if reading_header_comments:
                        check_required_header_comments()
                    break
            elif byte in b"\r\n":
                # if we read a line ending character, ignore it and parse what
                # we have already read. if we haven't read any other characters,
                # continue reading
                if bytes_read == 0:
                    continue
            else:
                # ASCII/hexadecimal lines in an EPS file must not exceed
                # 255 characters, not including line ending characters
                if bytes_read >= 255:
                    # only enforce this for lines starting with a "%",
                    # otherwise assume it's binary data
                    if byte_arr[0] == ord("%"):
                        msg = "not an EPS file"
                        raise SyntaxError(msg)
                    else:
                        if reading_header_comments:
                            check_required_header_comments()
                            reading_header_comments = False
                        # reset bytes_read so we can keep reading
                        # data until the end of the line
                        bytes_read = 0
                byte_arr[bytes_read] = byte[0]
                bytes_read += 1
                continue

            if reading_header_comments:
                # Load EPS header

                # if this line doesn't start with a "%",
                # or does start with "%%EndComments",
                # then we've reached the end of the header/comments
                if byte_arr[0] != ord("%") or bytes_mv[:13] == b"%%EndComments":
                    check_required_header_comments()
                    reading_header_comments = False
                    continue

                s = str(bytes_mv[:bytes_read], "latin-1")
                if not read_comment(s):
                    m = field.match(s)
                    if m:
                        k = m.group(1)
                        if k.startswith("PS-Adobe"):
                            self.info["PS-Adobe"] = k[9:]
                        else:
                            self.info[k] = ""
                    elif s[0] == "%":
                        # handle non-DSC PostScript comments that some
                        # tools mistakenly put in the Comments section
                        pass
                    else:
                        msg = "bad EPS header"
                        raise OSError(msg)
            elif bytes_mv[:11] == b"%ImageData:":
                # Check for an "ImageData" descriptor
                # https://www.adobe.com/devnet-apps/photoshop/fileformatashtml/#50577413_pgfId-1035096

                # If we've already read an "ImageData" descriptor,
                # don't read another one.
                if imagedata_size:
                    bytes_read = 0
                    continue

                # Values:
                # columns
                # rows
                # bit depth (1 or 8)
                # mode (1: L, 2: LAB, 3: RGB, 4: CMYK)
                # number of padding channels
                # block size (number of bytes per row per channel)
                # binary/ascii (1: binary, 2: ascii)
                # data start identifier (the image data follows after a single line
                #   consisting only of this quoted value)
                image_data_values = byte_arr[11:bytes_read].split(None, 7)
                columns, rows, bit_depth, mode_id = (
                    int(value) for value in image_data_values[:4]
                )

                if bit_depth == 1:
                    self._mode = "1"
                elif bit_depth == 8:
                    try:
                        self._mode = self.mode_map[mode_id]
                    except ValueError:
                        break
                else:
                    break

                # Parse the columns and rows after checking the bit depth and mode
                # in case the bit depth and/or mode are invalid.
                imagedata_size = columns, rows
            elif bytes_mv[:5] == b"%%EOF":
                break
            elif trailer_reached and reading_trailer_comments:
                # Load EPS trailer
                s = str(bytes_mv[:bytes_read], "latin-1")
                read_comment(s)
            elif bytes_mv[:9] == b"%%Trailer":
                trailer_reached = True
            bytes_read = 0

        # A "BoundingBox" is always required,
        # even if an "ImageData" descriptor size exists.
        if not bounding_box:
            msg = "cannot determine EPS bounding box"
            raise OSError(msg)

        # An "ImageData" size takes precedence over the "BoundingBox".
        self._size = imagedata_size or (
            bounding_box[2] - bounding_box[0],
            bounding_box[3] - bounding_box[1],
        )

        self.tile = [
            ImageFile._Tile("eps", (0, 0) + self.size, offset, (length, bounding_box))
        ]

    def _find_offset(self, fp: IO[bytes]) -> tuple[int, int]:
        s = fp.read(4)

        if s == b"%!PS":
            # for HEAD without binary preview
            fp.seek(0, io.SEEK_END)
            length = fp.tell()
            offset = 0
        elif i32(s) == 0xC6D3D0C5:
            # FIX for: Some EPS file not handled correctly / issue #302
            # EPS can contain binary data
            # or start directly with latin coding
            # more info see:
            # https://web.archive.org/web/20160528181353/http://partners.adobe.com/public/developer/en/ps/5002.EPSF_Spec.pdf
            s = fp.read(8)
            offset = i32(s)
            length = i32(s, 4)
        else:
            msg = "not an EPS file"
            raise SyntaxError(msg)

        return length, offset

    def load(
        self, scale: int = 1, transparency: bool = False
    ) -> Image.core.PixelAccess | None:
        # Load EPS via Ghostscript
        if self.tile:
            self.im = Ghostscript(self.tile, self.size, self.fp, scale, transparency)
            self._mode = self.im.mode
            self._size = self.im.size
            self.tile = []
        return Image.Image.load(self)

    def load_seek(self, pos: int) -> None:
        # we can't incrementally load, so force ImageFile.parser to
        # use our custom load method by defining this method.
        pass


# --------------------------------------------------------------------


def _save(im: Image.Image, fp: IO[bytes], filename: str | bytes, eps: int = 1) -> None:
    """EPS Writer for the Python Imaging Library."""

    # make sure image data is available
    im.load()

    # determine PostScript image mode
    if im.mode == "L":
        operator = (8, 1, b"image")
    elif im.mode == "RGB":
        operator = (8, 3, b"false 3 colorimage")
    elif im.mode == "CMYK":
        operator = (8, 4, b"false 4 colorimage")
    else:
        msg = "image mode is not supported"
        raise ValueError(msg)

    if eps:
        # write EPS header
        fp.write(b"%!PS-Adobe-3.0 EPSF-3.0\n")
        fp.write(b"%%Creator: PIL 0.1 EpsEncode\n")
        # fp.write("%%CreationDate: %s"...)
        fp.write(b"%%%%BoundingBox: 0 0 %d %d\n" % im.size)
        fp.write(b"%%Pages: 1\n")
        fp.write(b"%%EndComments\n")
        fp.write(b"%%Page: 1 1\n")
        fp.write(b"%%ImageData: %d %d " % im.size)
        fp.write(b'%d %d 0 1 1 "%s"\n' % operator)

    # image header
    fp.write(b"gsave\n")
    fp.write(b"10 dict begin\n")
    fp.write(b"/buf %d string def\n" % (im.size[0] * operator[1]))
    fp.write(b"%d %d scale\n" % im.size)
    fp.write(b"%d %d 8\n" % im.size)  # <= bits
    fp.write(b"[%d 0 0 -%d 0 %d]\n" % (im.size[0], im.size[1], im.size[1]))
    fp.write(b"{ currentfile buf readhexstring pop } bind\n")
    fp.write(operator[2] + b"\n")
    if hasattr(fp, "flush"):
        fp.flush()

    ImageFile._save(im, fp, [ImageFile._Tile("eps", (0, 0) + im.size)])

    fp.write(b"\n%%%%EndBinary\n")
    fp.write(b"grestore end\n")
    if hasattr(fp, "flush"):
        fp.flush()


# --------------------------------------------------------------------


Image.register_open(EpsImageFile.format, EpsImageFile, _accept)

Image.register_save(EpsImageFile.format, _save)

Image.register_extensions(EpsImageFile.format, [".ps", ".eps"])

Image.register_mime(EpsImageFile.format, "application/postscript")