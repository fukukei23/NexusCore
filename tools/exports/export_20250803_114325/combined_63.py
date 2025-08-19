
# === NexusCore/openenv\Lib\site-packages\charset_normalizer\constant.py ===
from __future__ import annotations

from codecs import BOM_UTF8, BOM_UTF16_BE, BOM_UTF16_LE, BOM_UTF32_BE, BOM_UTF32_LE
from encodings.aliases import aliases
from re import IGNORECASE
from re import compile as re_compile

# Contain for each eligible encoding a list of/item bytes SIG/BOM
ENCODING_MARKS: dict[str, bytes | list[bytes]] = {
    "utf_8": BOM_UTF8,
    "utf_7": [
        b"\x2b\x2f\x76\x38",
        b"\x2b\x2f\x76\x39",
        b"\x2b\x2f\x76\x2b",
        b"\x2b\x2f\x76\x2f",
        b"\x2b\x2f\x76\x38\x2d",
    ],
    "gb18030": b"\x84\x31\x95\x33",
    "utf_32": [BOM_UTF32_BE, BOM_UTF32_LE],
    "utf_16": [BOM_UTF16_BE, BOM_UTF16_LE],
}

TOO_SMALL_SEQUENCE: int = 32
TOO_BIG_SEQUENCE: int = int(10e6)

UTF8_MAXIMAL_ALLOCATION: int = 1_112_064

# Up-to-date Unicode ucd/15.0.0
UNICODE_RANGES_COMBINED: dict[str, range] = {
    "Control character": range(32),
    "Basic Latin": range(32, 128),
    "Latin-1 Supplement": range(128, 256),
    "Latin Extended-A": range(256, 384),
    "Latin Extended-B": range(384, 592),
    "IPA Extensions": range(592, 688),
    "Spacing Modifier Letters": range(688, 768),
    "Combining Diacritical Marks": range(768, 880),
    "Greek and Coptic": range(880, 1024),
    "Cyrillic": range(1024, 1280),
    "Cyrillic Supplement": range(1280, 1328),
    "Armenian": range(1328, 1424),
    "Hebrew": range(1424, 1536),
    "Arabic": range(1536, 1792),
    "Syriac": range(1792, 1872),
    "Arabic Supplement": range(1872, 1920),
    "Thaana": range(1920, 1984),
    "NKo": range(1984, 2048),
    "Samaritan": range(2048, 2112),
    "Mandaic": range(2112, 2144),
    "Syriac Supplement": range(2144, 2160),
    "Arabic Extended-B": range(2160, 2208),
    "Arabic Extended-A": range(2208, 2304),
    "Devanagari": range(2304, 2432),
    "Bengali": range(2432, 2560),
    "Gurmukhi": range(2560, 2688),
    "Gujarati": range(2688, 2816),
    "Oriya": range(2816, 2944),
    "Tamil": range(2944, 3072),
    "Telugu": range(3072, 3200),
    "Kannada": range(3200, 3328),
    "Malayalam": range(3328, 3456),
    "Sinhala": range(3456, 3584),
    "Thai": range(3584, 3712),
    "Lao": range(3712, 3840),
    "Tibetan": range(3840, 4096),
    "Myanmar": range(4096, 4256),
    "Georgian": range(4256, 4352),
    "Hangul Jamo": range(4352, 4608),
    "Ethiopic": range(4608, 4992),
    "Ethiopic Supplement": range(4992, 5024),
    "Cherokee": range(5024, 5120),
    "Unified Canadian Aboriginal Syllabics": range(5120, 5760),
    "Ogham": range(5760, 5792),
    "Runic": range(5792, 5888),
    "Tagalog": range(5888, 5920),
    "Hanunoo": range(5920, 5952),
    "Buhid": range(5952, 5984),
    "Tagbanwa": range(5984, 6016),
    "Khmer": range(6016, 6144),
    "Mongolian": range(6144, 6320),
    "Unified Canadian Aboriginal Syllabics Extended": range(6320, 6400),
    "Limbu": range(6400, 6480),
    "Tai Le": range(6480, 6528),
    "New Tai Lue": range(6528, 6624),
    "Khmer Symbols": range(6624, 6656),
    "Buginese": range(6656, 6688),
    "Tai Tham": range(6688, 6832),
    "Combining Diacritical Marks Extended": range(6832, 6912),
    "Balinese": range(6912, 7040),
    "Sundanese": range(7040, 7104),
    "Batak": range(7104, 7168),
    "Lepcha": range(7168, 7248),
    "Ol Chiki": range(7248, 7296),
    "Cyrillic Extended-C": range(7296, 7312),
    "Georgian Extended": range(7312, 7360),
    "Sundanese Supplement": range(7360, 7376),
    "Vedic Extensions": range(7376, 7424),
    "Phonetic Extensions": range(7424, 7552),
    "Phonetic Extensions Supplement": range(7552, 7616),
    "Combining Diacritical Marks Supplement": range(7616, 7680),
    "Latin Extended Additional": range(7680, 7936),
    "Greek Extended": range(7936, 8192),
    "General Punctuation": range(8192, 8304),
    "Superscripts and Subscripts": range(8304, 8352),
    "Currency Symbols": range(8352, 8400),
    "Combining Diacritical Marks for Symbols": range(8400, 8448),
    "Letterlike Symbols": range(8448, 8528),
    "Number Forms": range(8528, 8592),
    "Arrows": range(8592, 8704),
    "Mathematical Operators": range(8704, 8960),
    "Miscellaneous Technical": range(8960, 9216),
    "Control Pictures": range(9216, 9280),
    "Optical Character Recognition": range(9280, 9312),
    "Enclosed Alphanumerics": range(9312, 9472),
    "Box Drawing": range(9472, 9600),
    "Block Elements": range(9600, 9632),
    "Geometric Shapes": range(9632, 9728),
    "Miscellaneous Symbols": range(9728, 9984),
    "Dingbats": range(9984, 10176),
    "Miscellaneous Mathematical Symbols-A": range(10176, 10224),
    "Supplemental Arrows-A": range(10224, 10240),
    "Braille Patterns": range(10240, 10496),
    "Supplemental Arrows-B": range(10496, 10624),
    "Miscellaneous Mathematical Symbols-B": range(10624, 10752),
    "Supplemental Mathematical Operators": range(10752, 11008),
    "Miscellaneous Symbols and Arrows": range(11008, 11264),
    "Glagolitic": range(11264, 11360),
    "Latin Extended-C": range(11360, 11392),
    "Coptic": range(11392, 11520),
    "Georgian Supplement": range(11520, 11568),
    "Tifinagh": range(11568, 11648),
    "Ethiopic Extended": range(11648, 11744),
    "Cyrillic Extended-A": range(11744, 11776),
    "Supplemental Punctuation": range(11776, 11904),
    "CJK Radicals Supplement": range(11904, 12032),
    "Kangxi Radicals": range(12032, 12256),
    "Ideographic Description Characters": range(12272, 12288),
    "CJK Symbols and Punctuation": range(12288, 12352),
    "Hiragana": range(12352, 12448),
    "Katakana": range(12448, 12544),
    "Bopomofo": range(12544, 12592),
    "Hangul Compatibility Jamo": range(12592, 12688),
    "Kanbun": range(12688, 12704),
    "Bopomofo Extended": range(12704, 12736),
    "CJK Strokes": range(12736, 12784),
    "Katakana Phonetic Extensions": range(12784, 12800),
    "Enclosed CJK Letters and Months": range(12800, 13056),
    "CJK Compatibility": range(13056, 13312),
    "CJK Unified Ideographs Extension A": range(13312, 19904),
    "Yijing Hexagram Symbols": range(19904, 19968),
    "CJK Unified Ideographs": range(19968, 40960),
    "Yi Syllables": range(40960, 42128),
    "Yi Radicals": range(42128, 42192),
    "Lisu": range(42192, 42240),
    "Vai": range(42240, 42560),
    "Cyrillic Extended-B": range(42560, 42656),
    "Bamum": range(42656, 42752),
    "Modifier Tone Letters": range(42752, 42784),
    "Latin Extended-D": range(42784, 43008),
    "Syloti Nagri": range(43008, 43056),
    "Common Indic Number Forms": range(43056, 43072),
    "Phags-pa": range(43072, 43136),
    "Saurashtra": range(43136, 43232),
    "Devanagari Extended": range(43232, 43264),
    "Kayah Li": range(43264, 43312),
    "Rejang": range(43312, 43360),
    "Hangul Jamo Extended-A": range(43360, 43392),
    "Javanese": range(43392, 43488),
    "Myanmar Extended-B": range(43488, 43520),
    "Cham": range(43520, 43616),
    "Myanmar Extended-A": range(43616, 43648),
    "Tai Viet": range(43648, 43744),
    "Meetei Mayek Extensions": range(43744, 43776),
    "Ethiopic Extended-A": range(43776, 43824),
    "Latin Extended-E": range(43824, 43888),
    "Cherokee Supplement": range(43888, 43968),
    "Meetei Mayek": range(43968, 44032),
    "Hangul Syllables": range(44032, 55216),
    "Hangul Jamo Extended-B": range(55216, 55296),
    "High Surrogates": range(55296, 56192),
    "High Private Use Surrogates": range(56192, 56320),
    "Low Surrogates": range(56320, 57344),
    "Private Use Area": range(57344, 63744),
    "CJK Compatibility Ideographs": range(63744, 64256),
    "Alphabetic Presentation Forms": range(64256, 64336),
    "Arabic Presentation Forms-A": range(64336, 65024),
    "Variation Selectors": range(65024, 65040),
    "Vertical Forms": range(65040, 65056),
    "Combining Half Marks": range(65056, 65072),
    "CJK Compatibility Forms": range(65072, 65104),
    "Small Form Variants": range(65104, 65136),
    "Arabic Presentation Forms-B": range(65136, 65280),
    "Halfwidth and Fullwidth Forms": range(65280, 65520),
    "Specials": range(65520, 65536),
    "Linear B Syllabary": range(65536, 65664),
    "Linear B Ideograms": range(65664, 65792),
    "Aegean Numbers": range(65792, 65856),
    "Ancient Greek Numbers": range(65856, 65936),
    "Ancient Symbols": range(65936, 66000),
    "Phaistos Disc": range(66000, 66048),
    "Lycian": range(66176, 66208),
    "Carian": range(66208, 66272),
    "Coptic Epact Numbers": range(66272, 66304),
    "Old Italic": range(66304, 66352),
    "Gothic": range(66352, 66384),
    "Old Permic": range(66384, 66432),
    "Ugaritic": range(66432, 66464),
    "Old Persian": range(66464, 66528),
    "Deseret": range(66560, 66640),
    "Shavian": range(66640, 66688),
    "Osmanya": range(66688, 66736),
    "Osage": range(66736, 66816),
    "Elbasan": range(66816, 66864),
    "Caucasian Albanian": range(66864, 66928),
    "Vithkuqi": range(66928, 67008),
    "Linear A": range(67072, 67456),
    "Latin Extended-F": range(67456, 67520),
    "Cypriot Syllabary": range(67584, 67648),
    "Imperial Aramaic": range(67648, 67680),
    "Palmyrene": range(67680, 67712),
    "Nabataean": range(67712, 67760),
    "Hatran": range(67808, 67840),
    "Phoenician": range(67840, 67872),
    "Lydian": range(67872, 67904),
    "Meroitic Hieroglyphs": range(67968, 68000),
    "Meroitic Cursive": range(68000, 68096),
    "Kharoshthi": range(68096, 68192),
    "Old South Arabian": range(68192, 68224),
    "Old North Arabian": range(68224, 68256),
    "Manichaean": range(68288, 68352),
    "Avestan": range(68352, 68416),
    "Inscriptional Parthian": range(68416, 68448),
    "Inscriptional Pahlavi": range(68448, 68480),
    "Psalter Pahlavi": range(68480, 68528),
    "Old Turkic": range(68608, 68688),
    "Old Hungarian": range(68736, 68864),
    "Hanifi Rohingya": range(68864, 68928),
    "Rumi Numeral Symbols": range(69216, 69248),
    "Yezidi": range(69248, 69312),
    "Arabic Extended-C": range(69312, 69376),
    "Old Sogdian": range(69376, 69424),
    "Sogdian": range(69424, 69488),
    "Old Uyghur": range(69488, 69552),
    "Chorasmian": range(69552, 69600),
    "Elymaic": range(69600, 69632),
    "Brahmi": range(69632, 69760),
    "Kaithi": range(69760, 69840),
    "Sora Sompeng": range(69840, 69888),
    "Chakma": range(69888, 69968),
    "Mahajani": range(69968, 70016),
    "Sharada": range(70016, 70112),
    "Sinhala Archaic Numbers": range(70112, 70144),
    "Khojki": range(70144, 70224),
    "Multani": range(70272, 70320),
    "Khudawadi": range(70320, 70400),
    "Grantha": range(70400, 70528),
    "Newa": range(70656, 70784),
    "Tirhuta": range(70784, 70880),
    "Siddham": range(71040, 71168),
    "Modi": range(71168, 71264),
    "Mongolian Supplement": range(71264, 71296),
    "Takri": range(71296, 71376),
    "Ahom": range(71424, 71504),
    "Dogra": range(71680, 71760),
    "Warang Citi": range(71840, 71936),
    "Dives Akuru": range(71936, 72032),
    "Nandinagari": range(72096, 72192),
    "Zanabazar Square": range(72192, 72272),
    "Soyombo": range(72272, 72368),
    "Unified Canadian Aboriginal Syllabics Extended-A": range(72368, 72384),
    "Pau Cin Hau": range(72384, 72448),
    "Devanagari Extended-A": range(72448, 72544),
    "Bhaiksuki": range(72704, 72816),
    "Marchen": range(72816, 72896),
    "Masaram Gondi": range(72960, 73056),
    "Gunjala Gondi": range(73056, 73136),
    "Makasar": range(73440, 73472),
    "Kawi": range(73472, 73568),
    "Lisu Supplement": range(73648, 73664),
    "Tamil Supplement": range(73664, 73728),
    "Cuneiform": range(73728, 74752),
    "Cuneiform Numbers and Punctuation": range(74752, 74880),
    "Early Dynastic Cuneiform": range(74880, 75088),
    "Cypro-Minoan": range(77712, 77824),
    "Egyptian Hieroglyphs": range(77824, 78896),
    "Egyptian Hieroglyph Format Controls": range(78896, 78944),
    "Anatolian Hieroglyphs": range(82944, 83584),
    "Bamum Supplement": range(92160, 92736),
    "Mro": range(92736, 92784),
    "Tangsa": range(92784, 92880),
    "Bassa Vah": range(92880, 92928),
    "Pahawh Hmong": range(92928, 93072),
    "Medefaidrin": range(93760, 93856),
    "Miao": range(93952, 94112),
    "Ideographic Symbols and Punctuation": range(94176, 94208),
    "Tangut": range(94208, 100352),
    "Tangut Components": range(100352, 101120),
    "Khitan Small Script": range(101120, 101632),
    "Tangut Supplement": range(101632, 101760),
    "Kana Extended-B": range(110576, 110592),
    "Kana Supplement": range(110592, 110848),
    "Kana Extended-A": range(110848, 110896),
    "Small Kana Extension": range(110896, 110960),
    "Nushu": range(110960, 111360),
    "Duployan": range(113664, 113824),
    "Shorthand Format Controls": range(113824, 113840),
    "Znamenny Musical Notation": range(118528, 118736),
    "Byzantine Musical Symbols": range(118784, 119040),
    "Musical Symbols": range(119040, 119296),
    "Ancient Greek Musical Notation": range(119296, 119376),
    "Kaktovik Numerals": range(119488, 119520),
    "Mayan Numerals": range(119520, 119552),
    "Tai Xuan Jing Symbols": range(119552, 119648),
    "Counting Rod Numerals": range(119648, 119680),
    "Mathematical Alphanumeric Symbols": range(119808, 120832),
    "Sutton SignWriting": range(120832, 121520),
    "Latin Extended-G": range(122624, 122880),
    "Glagolitic Supplement": range(122880, 122928),
    "Cyrillic Extended-D": range(122928, 123024),
    "Nyiakeng Puachue Hmong": range(123136, 123216),
    "Toto": range(123536, 123584),
    "Wancho": range(123584, 123648),
    "Nag Mundari": range(124112, 124160),
    "Ethiopic Extended-B": range(124896, 124928),
    "Mende Kikakui": range(124928, 125152),
    "Adlam": range(125184, 125280),
    "Indic Siyaq Numbers": range(126064, 126144),
    "Ottoman Siyaq Numbers": range(126208, 126288),
    "Arabic Mathematical Alphabetic Symbols": range(126464, 126720),
    "Mahjong Tiles": range(126976, 127024),
    "Domino Tiles": range(127024, 127136),
    "Playing Cards": range(127136, 127232),
    "Enclosed Alphanumeric Supplement": range(127232, 127488),
    "Enclosed Ideographic Supplement": range(127488, 127744),
    "Miscellaneous Symbols and Pictographs": range(127744, 128512),
    "Emoticons range(Emoji)": range(128512, 128592),
    "Ornamental Dingbats": range(128592, 128640),
    "Transport and Map Symbols": range(128640, 128768),
    "Alchemical Symbols": range(128768, 128896),
    "Geometric Shapes Extended": range(128896, 129024),
    "Supplemental Arrows-C": range(129024, 129280),
    "Supplemental Symbols and Pictographs": range(129280, 129536),
    "Chess Symbols": range(129536, 129648),
    "Symbols and Pictographs Extended-A": range(129648, 129792),
    "Symbols for Legacy Computing": range(129792, 130048),
    "CJK Unified Ideographs Extension B": range(131072, 173792),
    "CJK Unified Ideographs Extension C": range(173824, 177984),
    "CJK Unified Ideographs Extension D": range(177984, 178208),
    "CJK Unified Ideographs Extension E": range(178208, 183984),
    "CJK Unified Ideographs Extension F": range(183984, 191472),
    "CJK Compatibility Ideographs Supplement": range(194560, 195104),
    "CJK Unified Ideographs Extension G": range(196608, 201552),
    "CJK Unified Ideographs Extension H": range(201552, 205744),
    "Tags": range(917504, 917632),
    "Variation Selectors Supplement": range(917760, 918000),
    "Supplementary Private Use Area-A": range(983040, 1048576),
    "Supplementary Private Use Area-B": range(1048576, 1114112),
}


UNICODE_SECONDARY_RANGE_KEYWORD: list[str] = [
    "Supplement",
    "Extended",
    "Extensions",
    "Modifier",
    "Marks",
    "Punctuation",
    "Symbols",
    "Forms",
    "Operators",
    "Miscellaneous",
    "Drawing",
    "Block",
    "Shapes",
    "Supplemental",
    "Tags",
]

RE_POSSIBLE_ENCODING_INDICATION = re_compile(
    r"(?:(?:encoding)|(?:charset)|(?:coding))(?:[\:= ]{1,10})(?:[\"\']?)([a-zA-Z0-9\-_]+)(?:[\"\']?)",
    IGNORECASE,
)

IANA_NO_ALIASES = [
    "cp720",
    "cp737",
    "cp856",
    "cp874",
    "cp875",
    "cp1006",
    "koi8_r",
    "koi8_t",
    "koi8_u",
]

IANA_SUPPORTED: list[str] = sorted(
    filter(
        lambda x: x.endswith("_codec") is False
        and x not in {"rot_13", "tactis", "mbcs"},
        list(set(aliases.values())) + IANA_NO_ALIASES,
    )
)

IANA_SUPPORTED_COUNT: int = len(IANA_SUPPORTED)

# pre-computed code page that are similar using the function cp_similarity.
IANA_SUPPORTED_SIMILAR: dict[str, list[str]] = {
    "cp037": ["cp1026", "cp1140", "cp273", "cp500"],
    "cp1026": ["cp037", "cp1140", "cp273", "cp500"],
    "cp1125": ["cp866"],
    "cp1140": ["cp037", "cp1026", "cp273", "cp500"],
    "cp1250": ["iso8859_2"],
    "cp1251": ["kz1048", "ptcp154"],
    "cp1252": ["iso8859_15", "iso8859_9", "latin_1"],
    "cp1253": ["iso8859_7"],
    "cp1254": ["iso8859_15", "iso8859_9", "latin_1"],
    "cp1257": ["iso8859_13"],
    "cp273": ["cp037", "cp1026", "cp1140", "cp500"],
    "cp437": ["cp850", "cp858", "cp860", "cp861", "cp862", "cp863", "cp865"],
    "cp500": ["cp037", "cp1026", "cp1140", "cp273"],
    "cp850": ["cp437", "cp857", "cp858", "cp865"],
    "cp857": ["cp850", "cp858", "cp865"],
    "cp858": ["cp437", "cp850", "cp857", "cp865"],
    "cp860": ["cp437", "cp861", "cp862", "cp863", "cp865"],
    "cp861": ["cp437", "cp860", "cp862", "cp863", "cp865"],
    "cp862": ["cp437", "cp860", "cp861", "cp863", "cp865"],
    "cp863": ["cp437", "cp860", "cp861", "cp862", "cp865"],
    "cp865": ["cp437", "cp850", "cp857", "cp858", "cp860", "cp861", "cp862", "cp863"],
    "cp866": ["cp1125"],
    "iso8859_10": ["iso8859_14", "iso8859_15", "iso8859_4", "iso8859_9", "latin_1"],
    "iso8859_11": ["tis_620"],
    "iso8859_13": ["cp1257"],
    "iso8859_14": [
        "iso8859_10",
        "iso8859_15",
        "iso8859_16",
        "iso8859_3",
        "iso8859_9",
        "latin_1",
    ],
    "iso8859_15": [
        "cp1252",
        "cp1254",
        "iso8859_10",
        "iso8859_14",
        "iso8859_16",
        "iso8859_3",
        "iso8859_9",
        "latin_1",
    ],
    "iso8859_16": [
        "iso8859_14",
        "iso8859_15",
        "iso8859_2",
        "iso8859_3",
        "iso8859_9",
        "latin_1",
    ],
    "iso8859_2": ["cp1250", "iso8859_16", "iso8859_4"],
    "iso8859_3": ["iso8859_14", "iso8859_15", "iso8859_16", "iso8859_9", "latin_1"],
    "iso8859_4": ["iso8859_10", "iso8859_2", "iso8859_9", "latin_1"],
    "iso8859_7": ["cp1253"],
    "iso8859_9": [
        "cp1252",
        "cp1254",
        "cp1258",
        "iso8859_10",
        "iso8859_14",
        "iso8859_15",
        "iso8859_16",
        "iso8859_3",
        "iso8859_4",
        "latin_1",
    ],
    "kz1048": ["cp1251", "ptcp154"],
    "latin_1": [
        "cp1252",
        "cp1254",
        "cp1258",
        "iso8859_10",
        "iso8859_14",
        "iso8859_15",
        "iso8859_16",
        "iso8859_3",
        "iso8859_4",
        "iso8859_9",
    ],
    "mac_iceland": ["mac_roman", "mac_turkish"],
    "mac_roman": ["mac_iceland", "mac_turkish"],
    "mac_turkish": ["mac_iceland", "mac_roman"],
    "ptcp154": ["cp1251", "kz1048"],
    "tis_620": ["iso8859_11"],
}


CHARDET_CORRESPONDENCE: dict[str, str] = {
    "iso2022_kr": "ISO-2022-KR",
    "iso2022_jp": "ISO-2022-JP",
    "euc_kr": "EUC-KR",
    "tis_620": "TIS-620",
    "utf_32": "UTF-32",
    "euc_jp": "EUC-JP",
    "koi8_r": "KOI8-R",
    "iso8859_1": "ISO-8859-1",
    "iso8859_2": "ISO-8859-2",
    "iso8859_5": "ISO-8859-5",
    "iso8859_6": "ISO-8859-6",
    "iso8859_7": "ISO-8859-7",
    "iso8859_8": "ISO-8859-8",
    "utf_16": "UTF-16",
    "cp855": "IBM855",
    "mac_cyrillic": "MacCyrillic",
    "gb2312": "GB2312",
    "gb18030": "GB18030",
    "cp932": "CP932",
    "cp866": "IBM866",
    "utf_8": "utf-8",
    "utf_8_sig": "UTF-8-SIG",
    "shift_jis": "SHIFT_JIS",
    "big5": "Big5",
    "cp1250": "windows-1250",
    "cp1251": "windows-1251",
    "cp1252": "Windows-1252",
    "cp1253": "windows-1253",
    "cp1255": "windows-1255",
    "cp1256": "windows-1256",
    "cp1254": "Windows-1254",
    "cp949": "CP949",
}


COMMON_SAFE_ASCII_CHARACTERS: set[str] = {
    "<",
    ">",
    "=",
    ":",
    "/",
    "&",
    ";",
    "{",
    "}",
    "[",
    "]",
    ",",
    "|",
    '"',
    "-",
    "(",
    ")",
}

# Sample character sets — replace with full lists if needed
COMMON_CHINESE_CHARACTERS = "的一是在不了有和人这中大为上个国我以要他时来用们生到作地于出就分对成会可主发年动同工也能下过子说产种面而方后多定行学法所民得经十三之进着等部度家电力里如水化高自二理起小物现实加量都两体制机当使点从业本去把性好应开它合还因由其些然前外天政四日那社义事平形相全表间样与关各重新线内数正心反你明看原又么利比或但质气第向道命此变条只没结解问意建月公无系军很情者最立代想已通并提直题党程展五果料象员革位入常文总次品式活设及管特件长求老头基资边流路级少图山统接知较将组见计别她手角期根论运农指几九区强放决西被干做必战先回则任取据处队南给色光门即保治北造百规热领七海口东导器压志世金增争济阶油思术极交受联什认六共权收证改清己美再采转更单风切打白教速花带安场身车例真务具万每目至达走积示议声报斗完类八离华名确才科张信马节话米整空元况今集温传土许步群广石记需段研界拉林律叫且究观越织装影算低持音众书布复容儿须际商非验连断深难近矿千周委素技备半办青省列习响约支般史感劳便团往酸历市克何除消构府太准精值号率族维划选标写存候毛亲快效斯院查江型眼王按格养易置派层片始却专状育厂京识适属圆包火住调满县局照参红细引听该铁价严龙飞"

COMMON_JAPANESE_CHARACTERS = "日一国年大十二本中長出三時行見月分後前生五間上東四今金九入学高円子外八六下来気小七山話女北午百書先名川千水半男西電校語土木聞食車何南万毎白天母火右読友左休父雨"

COMMON_KOREAN_CHARACTERS = "一二三四五六七八九十百千萬上下左右中人女子大小山川日月火水木金土父母天地國名年時文校學生"

# Combine all into a set
COMMON_CJK_CHARACTERS = set(
    "".join(
        [
            COMMON_CHINESE_CHARACTERS,
            COMMON_JAPANESE_CHARACTERS,
            COMMON_KOREAN_CHARACTERS,
        ]
    )
)

KO_NAMES: set[str] = {"johab", "cp949", "euc_kr"}
ZH_NAMES: set[str] = {"big5", "cp950", "big5hkscs", "hz"}

# Logging LEVEL below DEBUG
TRACE: int = 5


# Language label that contain the em dash "—"
# character are to be considered alternative seq to origin
FREQUENCIES: dict[str, list[str]] = {
    "English": [
        "e",
        "a",
        "t",
        "i",
        "o",
        "n",
        "s",
        "r",
        "h",
        "l",
        "d",
        "c",
        "u",
        "m",
        "f",
        "p",
        "g",
        "w",
        "y",
        "b",
        "v",
        "k",
        "x",
        "j",
        "z",
        "q",
    ],
    "English—": [
        "e",
        "a",
        "t",
        "i",
        "o",
        "n",
        "s",
        "r",
        "h",
        "l",
        "d",
        "c",
        "m",
        "u",
        "f",
        "p",
        "g",
        "w",
        "b",
        "y",
        "v",
        "k",
        "j",
        "x",
        "z",
        "q",
    ],
    "German": [
        "e",
        "n",
        "i",
        "r",
        "s",
        "t",
        "a",
        "d",
        "h",
        "u",
        "l",
        "g",
        "o",
        "c",
        "m",
        "b",
        "f",
        "k",
        "w",
        "z",
        "p",
        "v",
        "ü",
        "ä",
        "ö",
        "j",
    ],
    "French": [
        "e",
        "a",
        "s",
        "n",
        "i",
        "t",
        "r",
        "l",
        "u",
        "o",
        "d",
        "c",
        "p",
        "m",
        "é",
        "v",
        "g",
        "f",
        "b",
        "h",
        "q",
        "à",
        "x",
        "è",
        "y",
        "j",
    ],
    "Dutch": [
        "e",
        "n",
        "a",
        "i",
        "r",
        "t",
        "o",
        "d",
        "s",
        "l",
        "g",
        "h",
        "v",
        "m",
        "u",
        "k",
        "c",
        "p",
        "b",
        "w",
        "j",
        "z",
        "f",
        "y",
        "x",
        "ë",
    ],
    "Italian": [
        "e",
        "i",
        "a",
        "o",
        "n",
        "l",
        "t",
        "r",
        "s",
        "c",
        "d",
        "u",
        "p",
        "m",
        "g",
        "v",
        "f",
        "b",
        "z",
        "h",
        "q",
        "è",
        "à",
        "k",
        "y",
        "ò",
    ],
    "Polish": [
        "a",
        "i",
        "o",
        "e",
        "n",
        "r",
        "z",
        "w",
        "s",
        "c",
        "t",
        "k",
        "y",
        "d",
        "p",
        "m",
        "u",
        "l",
        "j",
        "ł",
        "g",
        "b",
        "h",
        "ą",
        "ę",
        "ó",
    ],
    "Spanish": [
        "e",
        "a",
        "o",
        "n",
        "s",
        "r",
        "i",
        "l",
        "d",
        "t",
        "c",
        "u",
        "m",
        "p",
        "b",
        "g",
        "v",
        "f",
        "y",
        "ó",
        "h",
        "q",
        "í",
        "j",
        "z",
        "á",
    ],
    "Russian": [
        "о",
        "а",
        "е",
        "и",
        "н",
        "с",
        "т",
        "р",
        "в",
        "л",
        "к",
        "м",
        "д",
        "п",
        "у",
        "г",
        "я",
        "ы",
        "з",
        "б",
        "й",
        "ь",
        "ч",
        "х",
        "ж",
        "ц",
    ],
    # Jap-Kanji
    "Japanese": [
        "人",
        "一",
        "大",
        "亅",
        "丁",
        "丨",
        "竹",
        "笑",
        "口",
        "日",
        "今",
        "二",
        "彳",
        "行",
        "十",
        "土",
        "丶",
        "寸",
        "寺",
        "時",
        "乙",
        "丿",
        "乂",
        "气",
        "気",
        "冂",
        "巾",
        "亠",
        "市",
        "目",
        "儿",
        "見",
        "八",
        "小",
        "凵",
        "県",
        "月",
        "彐",
        "門",
        "間",
        "木",
        "東",
        "山",
        "出",
        "本",
        "中",
        "刀",
        "分",
        "耳",
        "又",
        "取",
        "最",
        "言",
        "田",
        "心",
        "思",
        "刂",
        "前",
        "京",
        "尹",
        "事",
        "生",
        "厶",
        "云",
        "会",
        "未",
        "来",
        "白",
        "冫",
        "楽",
        "灬",
        "馬",
        "尸",
        "尺",
        "駅",
        "明",
        "耂",
        "者",
        "了",
        "阝",
        "都",
        "高",
        "卜",
        "占",
        "厂",
        "广",
        "店",
        "子",
        "申",
        "奄",
        "亻",
        "俺",
        "上",
        "方",
        "冖",
        "学",
        "衣",
        "艮",
        "食",
        "自",
    ],
    # Jap-Katakana
    "Japanese—": [
        "ー",
        "ン",
        "ス",
        "・",
        "ル",
        "ト",
        "リ",
        "イ",
        "ア",
        "ラ",
        "ッ",
        "ク",
        "ド",
        "シ",
        "レ",
        "ジ",
        "タ",
        "フ",
        "ロ",
        "カ",
        "テ",
        "マ",
        "ィ",
        "グ",
        "バ",
        "ム",
        "プ",
        "オ",
        "コ",
        "デ",
        "ニ",
        "ウ",
        "メ",
        "サ",
        "ビ",
        "ナ",
        "ブ",
        "ャ",
        "エ",
        "ュ",
        "チ",
        "キ",
        "ズ",
        "ダ",
        "パ",
        "ミ",
        "ェ",
        "ョ",
        "ハ",
        "セ",
        "ベ",
        "ガ",
        "モ",
        "ツ",
        "ネ",
        "ボ",
        "ソ",
        "ノ",
        "ァ",
        "ヴ",
        "ワ",
        "ポ",
        "ペ",
        "ピ",
        "ケ",
        "ゴ",
        "ギ",
        "ザ",
        "ホ",
        "ゲ",
        "ォ",
        "ヤ",
        "ヒ",
        "ユ",
        "ヨ",
        "ヘ",
        "ゼ",
        "ヌ",
        "ゥ",
        "ゾ",
        "ヶ",
        "ヂ",
        "ヲ",
        "ヅ",
        "ヵ",
        "ヱ",
        "ヰ",
        "ヮ",
        "ヽ",
        "゠",
        "ヾ",
        "ヷ",
        "ヿ",
        "ヸ",
        "ヹ",
        "ヺ",
    ],
    # Jap-Hiragana
    "Japanese——": [
        "の",
        "に",
        "る",
        "た",
        "と",
        "は",
        "し",
        "い",
        "を",
        "で",
        "て",
        "が",
        "な",
        "れ",
        "か",
        "ら",
        "さ",
        "っ",
        "り",
        "す",
        "あ",
        "も",
        "こ",
        "ま",
        "う",
        "く",
        "よ",
        "き",
        "ん",
        "め",
        "お",
        "け",
        "そ",
        "つ",
        "だ",
        "や",
        "え",
        "ど",
        "わ",
        "ち",
        "み",
        "せ",
        "じ",
        "ば",
        "へ",
        "び",
        "ず",
        "ろ",
        "ほ",
        "げ",
        "む",
        "べ",
        "ひ",
        "ょ",
        "ゆ",
        "ぶ",
        "ご",
        "ゃ",
        "ね",
        "ふ",
        "ぐ",
        "ぎ",
        "ぼ",
        "ゅ",
        "づ",
        "ざ",
        "ぞ",
        "ぬ",
        "ぜ",
        "ぱ",
        "ぽ",
        "ぷ",
        "ぴ",
        "ぃ",
        "ぁ",
        "ぇ",
        "ぺ",
        "ゞ",
        "ぢ",
        "ぉ",
        "ぅ",
        "ゐ",
        "ゝ",
        "ゑ",
        "゛",
        "゜",
        "ゎ",
        "ゔ",
        "゚",
        "ゟ",
        "゙",
        "ゕ",
        "ゖ",
    ],
    "Portuguese": [
        "a",
        "e",
        "o",
        "s",
        "i",
        "r",
        "d",
        "n",
        "t",
        "m",
        "u",
        "c",
        "l",
        "p",
        "g",
        "v",
        "b",
        "f",
        "h",
        "ã",
        "q",
        "é",
        "ç",
        "á",
        "z",
        "í",
    ],
    "Swedish": [
        "e",
        "a",
        "n",
        "r",
        "t",
        "s",
        "i",
        "l",
        "d",
        "o",
        "m",
        "k",
        "g",
        "v",
        "h",
        "f",
        "u",
        "p",
        "ä",
        "c",
        "b",
        "ö",
        "å",
        "y",
        "j",
        "x",
    ],
    "Chinese": [
        "的",
        "一",
        "是",
        "不",
        "了",
        "在",
        "人",
        "有",
        "我",
        "他",
        "这",
        "个",
        "们",
        "中",
        "来",
        "上",
        "大",
        "为",
        "和",
        "国",
        "地",
        "到",
        "以",
        "说",
        "时",
        "要",
        "就",
        "出",
        "会",
        "可",
        "也",
        "你",
        "对",
        "生",
        "能",
        "而",
        "子",
        "那",
        "得",
        "于",
        "着",
        "下",
        "自",
        "之",
        "年",
        "过",
        "发",
        "后",
        "作",
        "里",
        "用",
        "道",
        "行",
        "所",
        "然",
        "家",
        "种",
        "事",
        "成",
        "方",
        "多",
        "经",
        "么",
        "去",
        "法",
        "学",
        "如",
        "都",
        "同",
        "现",
        "当",
        "没",
        "动",
        "面",
        "起",
        "看",
        "定",
        "天",
        "分",
        "还",
        "进",
        "好",
        "小",
        "部",
        "其",
        "些",
        "主",
        "样",
        "理",
        "心",
        "她",
        "本",
        "前",
        "开",
        "但",
        "因",
        "只",
        "从",
        "想",
        "实",
    ],
    "Ukrainian": [
        "о",
        "а",
        "н",
        "і",
        "и",
        "р",
        "в",
        "т",
        "е",
        "с",
        "к",
        "л",
        "у",
        "д",
        "м",
        "п",
        "з",
        "я",
        "ь",
        "б",
        "г",
        "й",
        "ч",
        "х",
        "ц",
        "ї",
    ],
    "Norwegian": [
        "e",
        "r",
        "n",
        "t",
        "a",
        "s",
        "i",
        "o",
        "l",
        "d",
        "g",
        "k",
        "m",
        "v",
        "f",
        "p",
        "u",
        "b",
        "h",
        "å",
        "y",
        "j",
        "ø",
        "c",
        "æ",
        "w",
    ],
    "Finnish": [
        "a",
        "i",
        "n",
        "t",
        "e",
        "s",
        "l",
        "o",
        "u",
        "k",
        "ä",
        "m",
        "r",
        "v",
        "j",
        "h",
        "p",
        "y",
        "d",
        "ö",
        "g",
        "c",
        "b",
        "f",
        "w",
        "z",
    ],
    "Vietnamese": [
        "n",
        "h",
        "t",
        "i",
        "c",
        "g",
        "a",
        "o",
        "u",
        "m",
        "l",
        "r",
        "à",
        "đ",
        "s",
        "e",
        "v",
        "p",
        "b",
        "y",
        "ư",
        "d",
        "á",
        "k",
        "ộ",
        "ế",
    ],
    "Czech": [
        "o",
        "e",
        "a",
        "n",
        "t",
        "s",
        "i",
        "l",
        "v",
        "r",
        "k",
        "d",
        "u",
        "m",
        "p",
        "í",
        "c",
        "h",
        "z",
        "á",
        "y",
        "j",
        "b",
        "ě",
        "é",
        "ř",
    ],
    "Hungarian": [
        "e",
        "a",
        "t",
        "l",
        "s",
        "n",
        "k",
        "r",
        "i",
        "o",
        "z",
        "á",
        "é",
        "g",
        "m",
        "b",
        "y",
        "v",
        "d",
        "h",
        "u",
        "p",
        "j",
        "ö",
        "f",
        "c",
    ],
    "Korean": [
        "이",
        "다",
        "에",
        "의",
        "는",
        "로",
        "하",
        "을",
        "가",
        "고",
        "지",
        "서",
        "한",
        "은",
        "기",
        "으",
        "년",
        "대",
        "사",
        "시",
        "를",
        "리",
        "도",
        "인",
        "스",
        "일",
    ],
    "Indonesian": [
        "a",
        "n",
        "e",
        "i",
        "r",
        "t",
        "u",
        "s",
        "d",
        "k",
        "m",
        "l",
        "g",
        "p",
        "b",
        "o",
        "h",
        "y",
        "j",
        "c",
        "w",
        "f",
        "v",
        "z",
        "x",
        "q",
    ],
    "Turkish": [
        "a",
        "e",
        "i",
        "n",
        "r",
        "l",
        "ı",
        "k",
        "d",
        "t",
        "s",
        "m",
        "y",
        "u",
        "o",
        "b",
        "ü",
        "ş",
        "v",
        "g",
        "z",
        "h",
        "c",
        "p",
        "ç",
        "ğ",
    ],
    "Romanian": [
        "e",
        "i",
        "a",
        "r",
        "n",
        "t",
        "u",
        "l",
        "o",
        "c",
        "s",
        "d",
        "p",
        "m",
        "ă",
        "f",
        "v",
        "î",
        "g",
        "b",
        "ș",
        "ț",
        "z",
        "h",
        "â",
        "j",
    ],
    "Farsi": [
        "ا",
        "ی",
        "ر",
        "د",
        "ن",
        "ه",
        "و",
        "م",
        "ت",
        "ب",
        "س",
        "ل",
        "ک",
        "ش",
        "ز",
        "ف",
        "گ",
        "ع",
        "خ",
        "ق",
        "ج",
        "آ",
        "پ",
        "ح",
        "ط",
        "ص",
    ],
    "Arabic": [
        "ا",
        "ل",
        "ي",
        "م",
        "و",
        "ن",
        "ر",
        "ت",
        "ب",
        "ة",
        "ع",
        "د",
        "س",
        "ف",
        "ه",
        "ك",
        "ق",
        "أ",
        "ح",
        "ج",
        "ش",
        "ط",
        "ص",
        "ى",
        "خ",
        "إ",
    ],
    "Danish": [
        "e",
        "r",
        "n",
        "t",
        "a",
        "i",
        "s",
        "d",
        "l",
        "o",
        "g",
        "m",
        "k",
        "f",
        "v",
        "u",
        "b",
        "h",
        "p",
        "å",
        "y",
        "ø",
        "æ",
        "c",
        "j",
        "w",
    ],
    "Serbian": [
        "а",
        "и",
        "о",
        "е",
        "н",
        "р",
        "с",
        "у",
        "т",
        "к",
        "ј",
        "в",
        "д",
        "м",
        "п",
        "л",
        "г",
        "з",
        "б",
        "a",
        "i",
        "e",
        "o",
        "n",
        "ц",
        "ш",
    ],
    "Lithuanian": [
        "i",
        "a",
        "s",
        "o",
        "r",
        "e",
        "t",
        "n",
        "u",
        "k",
        "m",
        "l",
        "p",
        "v",
        "d",
        "j",
        "g",
        "ė",
        "b",
        "y",
        "ų",
        "š",
        "ž",
        "c",
        "ą",
        "į",
    ],
    "Slovene": [
        "e",
        "a",
        "i",
        "o",
        "n",
        "r",
        "s",
        "l",
        "t",
        "j",
        "v",
        "k",
        "d",
        "p",
        "m",
        "u",
        "z",
        "b",
        "g",
        "h",
        "č",
        "c",
        "š",
        "ž",
        "f",
        "y",
    ],
    "Slovak": [
        "o",
        "a",
        "e",
        "n",
        "i",
        "r",
        "v",
        "t",
        "s",
        "l",
        "k",
        "d",
        "m",
        "p",
        "u",
        "c",
        "h",
        "j",
        "b",
        "z",
        "á",
        "y",
        "ý",
        "í",
        "č",
        "é",
    ],
    "Hebrew": [
        "י",
        "ו",
        "ה",
        "ל",
        "ר",
        "ב",
        "ת",
        "מ",
        "א",
        "ש",
        "נ",
        "ע",
        "ם",
        "ד",
        "ק",
        "ח",
        "פ",
        "ס",
        "כ",
        "ג",
        "ט",
        "צ",
        "ן",
        "ז",
        "ך",
    ],
    "Bulgarian": [
        "а",
        "и",
        "о",
        "е",
        "н",
        "т",
        "р",
        "с",
        "в",
        "л",
        "к",
        "д",
        "п",
        "м",
        "з",
        "г",
        "я",
        "ъ",
        "у",
        "б",
        "ч",
        "ц",
        "й",
        "ж",
        "щ",
        "х",
    ],
    "Croatian": [
        "a",
        "i",
        "o",
        "e",
        "n",
        "r",
        "j",
        "s",
        "t",
        "u",
        "k",
        "l",
        "v",
        "d",
        "m",
        "p",
        "g",
        "z",
        "b",
        "c",
        "č",
        "h",
        "š",
        "ž",
        "ć",
        "f",
    ],
    "Hindi": [
        "क",
        "र",
        "स",
        "न",
        "त",
        "म",
        "ह",
        "प",
        "य",
        "ल",
        "व",
        "ज",
        "द",
        "ग",
        "ब",
        "श",
        "ट",
        "अ",
        "ए",
        "थ",
        "भ",
        "ड",
        "च",
        "ध",
        "ष",
        "इ",
    ],
    "Estonian": [
        "a",
        "i",
        "e",
        "s",
        "t",
        "l",
        "u",
        "n",
        "o",
        "k",
        "r",
        "d",
        "m",
        "v",
        "g",
        "p",
        "j",
        "h",
        "ä",
        "b",
        "õ",
        "ü",
        "f",
        "c",
        "ö",
        "y",
    ],
    "Thai": [
        "า",
        "น",
        "ร",
        "อ",
        "ก",
        "เ",
        "ง",
        "ม",
        "ย",
        "ล",
        "ว",
        "ด",
        "ท",
        "ส",
        "ต",
        "ะ",
        "ป",
        "บ",
        "ค",
        "ห",
        "แ",
        "จ",
        "พ",
        "ช",
        "ข",
        "ใ",
    ],
    "Greek": [
        "α",
        "τ",
        "ο",
        "ι",
        "ε",
        "ν",
        "ρ",
        "σ",
        "κ",
        "η",
        "π",
        "ς",
        "υ",
        "μ",
        "λ",
        "ί",
        "ό",
        "ά",
        "γ",
        "έ",
        "δ",
        "ή",
        "ω",
        "χ",
        "θ",
        "ύ",
    ],
    "Tamil": [
        "க",
        "த",
        "ப",
        "ட",
        "ர",
        "ம",
        "ல",
        "ன",
        "வ",
        "ற",
        "ய",
        "ள",
        "ச",
        "ந",
        "இ",
        "ண",
        "அ",
        "ஆ",
        "ழ",
        "ங",
        "எ",
        "உ",
        "ஒ",
        "ஸ",
    ],
    "Kazakh": [
        "а",
        "ы",
        "е",
        "н",
        "т",
        "р",
        "л",
        "і",
        "д",
        "с",
        "м",
        "қ",
        "к",
        "о",
        "б",
        "и",
        "у",
        "ғ",
        "ж",
        "ң",
        "з",
        "ш",
        "й",
        "п",
        "г",
        "ө",
    ],
}

LANGUAGE_SUPPORTED_COUNT: int = len(FREQUENCIES)

# === NexusCore/openenv\Lib\site-packages\numpy\lib\_array_utils_impl.py ===
"""
Miscellaneous utils.
"""
from numpy._core import asarray
from numpy._core.numeric import normalize_axis_index, normalize_axis_tuple
from numpy._utils import set_module

__all__ = ["byte_bounds", "normalize_axis_tuple", "normalize_axis_index"]


@set_module("numpy.lib.array_utils")
def byte_bounds(a):
    """
    Returns pointers to the end-points of an array.

    Parameters
    ----------
    a : ndarray
        Input array. It must conform to the Python-side of the array
        interface.

    Returns
    -------
    (low, high) : tuple of 2 integers
        The first integer is the first byte of the array, the second
        integer is just past the last byte of the array.  If `a` is not
        contiguous it will not use every byte between the (`low`, `high`)
        values.

    Examples
    --------
    >>> import numpy as np
    >>> I = np.eye(2, dtype='f'); I.dtype
    dtype('float32')
    >>> low, high = np.lib.array_utils.byte_bounds(I)
    >>> high - low == I.size*I.itemsize
    True
    >>> I = np.eye(2); I.dtype
    dtype('float64')
    >>> low, high = np.lib.array_utils.byte_bounds(I)
    >>> high - low == I.size*I.itemsize
    True

    """
    ai = a.__array_interface__
    a_data = ai['data'][0]
    astrides = ai['strides']
    ashape = ai['shape']
    bytes_a = asarray(a).dtype.itemsize

    a_low = a_high = a_data
    if astrides is None:
        # contiguous case
        a_high += a.size * bytes_a
    else:
        for shape, stride in zip(ashape, astrides):
            if stride < 0:
                a_low += (shape - 1) * stride
            else:
                a_high += (shape - 1) * stride
        a_high += bytes_a
    return a_low, a_high

# === NexusCore/openenv\Lib\site-packages\numpy\polynomial\chebyshev.py ===
"""
====================================================
Chebyshev Series (:mod:`numpy.polynomial.chebyshev`)
====================================================

This module provides a number of objects (mostly functions) useful for
dealing with Chebyshev series, including a `Chebyshev` class that
encapsulates the usual arithmetic operations.  (General information
on how this module represents and works with such polynomials is in the
docstring for its "parent" sub-package, `numpy.polynomial`).

Classes
-------

.. autosummary::
   :toctree: generated/

   Chebyshev


Constants
---------

.. autosummary::
   :toctree: generated/

   chebdomain
   chebzero
   chebone
   chebx

Arithmetic
----------

.. autosummary::
   :toctree: generated/

   chebadd
   chebsub
   chebmulx
   chebmul
   chebdiv
   chebpow
   chebval
   chebval2d
   chebval3d
   chebgrid2d
   chebgrid3d

Calculus
--------

.. autosummary::
   :toctree: generated/

   chebder
   chebint

Misc Functions
--------------

.. autosummary::
   :toctree: generated/

   chebfromroots
   chebroots
   chebvander
   chebvander2d
   chebvander3d
   chebgauss
   chebweight
   chebcompanion
   chebfit
   chebpts1
   chebpts2
   chebtrim
   chebline
   cheb2poly
   poly2cheb
   chebinterpolate

See also
--------
`numpy.polynomial`

Notes
-----
The implementations of multiplication, division, integration, and
differentiation use the algebraic identities [1]_:

.. math::
    T_n(x) = \\frac{z^n + z^{-n}}{2} \\\\
    z\\frac{dx}{dz} = \\frac{z - z^{-1}}{2}.

where

.. math:: x = \\frac{z + z^{-1}}{2}.

These identities allow a Chebyshev series to be expressed as a finite,
symmetric Laurent series.  In this module, this sort of Laurent series
is referred to as a "z-series."

References
----------
.. [1] A. T. Benjamin, et al., "Combinatorial Trigonometry with Chebyshev
  Polynomials," *Journal of Statistical Planning and Inference 14*, 2008
  (https://web.archive.org/web/20080221202153/https://www.math.hmc.edu/~benjamin/papers/CombTrig.pdf, pg. 4)

"""  # noqa: E501
import numpy as np
import numpy.linalg as la
from numpy.lib.array_utils import normalize_axis_index

from . import polyutils as pu
from ._polybase import ABCPolyBase

__all__ = [
    'chebzero', 'chebone', 'chebx', 'chebdomain', 'chebline', 'chebadd',
    'chebsub', 'chebmulx', 'chebmul', 'chebdiv', 'chebpow', 'chebval',
    'chebder', 'chebint', 'cheb2poly', 'poly2cheb', 'chebfromroots',
    'chebvander', 'chebfit', 'chebtrim', 'chebroots', 'chebpts1',
    'chebpts2', 'Chebyshev', 'chebval2d', 'chebval3d', 'chebgrid2d',
    'chebgrid3d', 'chebvander2d', 'chebvander3d', 'chebcompanion',
    'chebgauss', 'chebweight', 'chebinterpolate']

chebtrim = pu.trimcoef

#
# A collection of functions for manipulating z-series. These are private
# functions and do minimal error checking.
#

def _cseries_to_zseries(c):
    """Convert Chebyshev series to z-series.

    Convert a Chebyshev series to the equivalent z-series. The result is
    never an empty array. The dtype of the return is the same as that of
    the input. No checks are run on the arguments as this routine is for
    internal use.

    Parameters
    ----------
    c : 1-D ndarray
        Chebyshev coefficients, ordered from low to high

    Returns
    -------
    zs : 1-D ndarray
        Odd length symmetric z-series, ordered from  low to high.

    """
    n = c.size
    zs = np.zeros(2 * n - 1, dtype=c.dtype)
    zs[n - 1:] = c / 2
    return zs + zs[::-1]


def _zseries_to_cseries(zs):
    """Convert z-series to a Chebyshev series.

    Convert a z series to the equivalent Chebyshev series. The result is
    never an empty array. The dtype of the return is the same as that of
    the input. No checks are run on the arguments as this routine is for
    internal use.

    Parameters
    ----------
    zs : 1-D ndarray
        Odd length symmetric z-series, ordered from  low to high.

    Returns
    -------
    c : 1-D ndarray
        Chebyshev coefficients, ordered from  low to high.

    """
    n = (zs.size + 1) // 2
    c = zs[n - 1:].copy()
    c[1:n] *= 2
    return c


def _zseries_mul(z1, z2):
    """Multiply two z-series.

    Multiply two z-series to produce a z-series.

    Parameters
    ----------
    z1, z2 : 1-D ndarray
        The arrays must be 1-D but this is not checked.

    Returns
    -------
    product : 1-D ndarray
        The product z-series.

    Notes
    -----
    This is simply convolution. If symmetric/anti-symmetric z-series are
    denoted by S/A then the following rules apply:

    S*S, A*A -> S
    S*A, A*S -> A

    """
    return np.convolve(z1, z2)


def _zseries_div(z1, z2):
    """Divide the first z-series by the second.

    Divide `z1` by `z2` and return the quotient and remainder as z-series.
    Warning: this implementation only applies when both z1 and z2 have the
    same symmetry, which is sufficient for present purposes.

    Parameters
    ----------
    z1, z2 : 1-D ndarray
        The arrays must be 1-D and have the same symmetry, but this is not
        checked.

    Returns
    -------

    (quotient, remainder) : 1-D ndarrays
        Quotient and remainder as z-series.

    Notes
    -----
    This is not the same as polynomial division on account of the desired form
    of the remainder. If symmetric/anti-symmetric z-series are denoted by S/A
    then the following rules apply:

    S/S -> S,S
    A/A -> S,A

    The restriction to types of the same symmetry could be fixed but seems like
    unneeded generality. There is no natural form for the remainder in the case
    where there is no symmetry.

    """
    z1 = z1.copy()
    z2 = z2.copy()
    lc1 = len(z1)
    lc2 = len(z2)
    if lc2 == 1:
        z1 /= z2
        return z1, z1[:1] * 0
    elif lc1 < lc2:
        return z1[:1] * 0, z1
    else:
        dlen = lc1 - lc2
        scl = z2[0]
        z2 /= scl
        quo = np.empty(dlen + 1, dtype=z1.dtype)
        i = 0
        j = dlen
        while i < j:
            r = z1[i]
            quo[i] = z1[i]
            quo[dlen - i] = r
            tmp = r * z2
            z1[i:i + lc2] -= tmp
            z1[j:j + lc2] -= tmp
            i += 1
            j -= 1
        r = z1[i]
        quo[i] = r
        tmp = r * z2
        z1[i:i + lc2] -= tmp
        quo /= scl
        rem = z1[i + 1:i - 1 + lc2].copy()
        return quo, rem


def _zseries_der(zs):
    """Differentiate a z-series.

    The derivative is with respect to x, not z. This is achieved using the
    chain rule and the value of dx/dz given in the module notes.

    Parameters
    ----------
    zs : z-series
        The z-series to differentiate.

    Returns
    -------
    derivative : z-series
        The derivative

    Notes
    -----
    The zseries for x (ns) has been multiplied by two in order to avoid
    using floats that are incompatible with Decimal and likely other
    specialized scalar types. This scaling has been compensated by
    multiplying the value of zs by two also so that the two cancels in the
    division.

    """
    n = len(zs) // 2
    ns = np.array([-1, 0, 1], dtype=zs.dtype)
    zs *= np.arange(-n, n + 1) * 2
    d, r = _zseries_div(zs, ns)
    return d


def _zseries_int(zs):
    """Integrate a z-series.

    The integral is with respect to x, not z. This is achieved by a change
    of variable using dx/dz given in the module notes.

    Parameters
    ----------
    zs : z-series
        The z-series to integrate

    Returns
    -------
    integral : z-series
        The indefinite integral

    Notes
    -----
    The zseries for x (ns) has been multiplied by two in order to avoid
    using floats that are incompatible with Decimal and likely other
    specialized scalar types. This scaling has been compensated by
    dividing the resulting zs by two.

    """
    n = 1 + len(zs) // 2
    ns = np.array([-1, 0, 1], dtype=zs.dtype)
    zs = _zseries_mul(zs, ns)
    div = np.arange(-n, n + 1) * 2
    zs[:n] /= div[:n]
    zs[n + 1:] /= div[n + 1:]
    zs[n] = 0
    return zs

#
# Chebyshev series functions
#


def poly2cheb(pol):
    """
    Convert a polynomial to a Chebyshev series.

    Convert an array representing the coefficients of a polynomial (relative
    to the "standard" basis) ordered from lowest degree to highest, to an
    array of the coefficients of the equivalent Chebyshev series, ordered
    from lowest to highest degree.

    Parameters
    ----------
    pol : array_like
        1-D array containing the polynomial coefficients

    Returns
    -------
    c : ndarray
        1-D array containing the coefficients of the equivalent Chebyshev
        series.

    See Also
    --------
    cheb2poly

    Notes
    -----
    The easy way to do conversions between polynomial basis sets
    is to use the convert method of a class instance.

    Examples
    --------
    >>> from numpy import polynomial as P
    >>> p = P.Polynomial(range(4))
    >>> p
    Polynomial([0., 1., 2., 3.], domain=[-1.,  1.], window=[-1.,  1.], symbol='x')
    >>> c = p.convert(kind=P.Chebyshev)
    >>> c
    Chebyshev([1.  , 3.25, 1.  , 0.75], domain=[-1.,  1.], window=[-1., ...
    >>> P.chebyshev.poly2cheb(range(4))
    array([1.  , 3.25, 1.  , 0.75])

    """
    [pol] = pu.as_series([pol])
    deg = len(pol) - 1
    res = 0
    for i in range(deg, -1, -1):
        res = chebadd(chebmulx(res), pol[i])
    return res


def cheb2poly(c):
    """
    Convert a Chebyshev series to a polynomial.

    Convert an array representing the coefficients of a Chebyshev series,
    ordered from lowest degree to highest, to an array of the coefficients
    of the equivalent polynomial (relative to the "standard" basis) ordered
    from lowest to highest degree.

    Parameters
    ----------
    c : array_like
        1-D array containing the Chebyshev series coefficients, ordered
        from lowest order term to highest.

    Returns
    -------
    pol : ndarray
        1-D array containing the coefficients of the equivalent polynomial
        (relative to the "standard" basis) ordered from lowest order term
        to highest.

    See Also
    --------
    poly2cheb

    Notes
    -----
    The easy way to do conversions between polynomial basis sets
    is to use the convert method of a class instance.

    Examples
    --------
    >>> from numpy import polynomial as P
    >>> c = P.Chebyshev(range(4))
    >>> c
    Chebyshev([0., 1., 2., 3.], domain=[-1.,  1.], window=[-1.,  1.], symbol='x')
    >>> p = c.convert(kind=P.Polynomial)
    >>> p
    Polynomial([-2., -8.,  4., 12.], domain=[-1.,  1.], window=[-1.,  1.], ...
    >>> P.chebyshev.cheb2poly(range(4))
    array([-2.,  -8.,   4.,  12.])

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
            c0 = polysub(c[i - 2], c1)
            c1 = polyadd(tmp, polymulx(c1) * 2)
        return polyadd(c0, polymulx(c1))


#
# These are constant arrays are of integer type so as to be compatible
# with the widest range of other types, such as Decimal.
#

# Chebyshev default domain.
chebdomain = np.array([-1., 1.])

# Chebyshev coefficients representing zero.
chebzero = np.array([0])

# Chebyshev coefficients representing one.
chebone = np.array([1])

# Chebyshev coefficients representing the identity x.
chebx = np.array([0, 1])


def chebline(off, scl):
    """
    Chebyshev series whose graph is a straight line.

    Parameters
    ----------
    off, scl : scalars
        The specified line is given by ``off + scl*x``.

    Returns
    -------
    y : ndarray
        This module's representation of the Chebyshev series for
        ``off + scl*x``.

    See Also
    --------
    numpy.polynomial.polynomial.polyline
    numpy.polynomial.legendre.legline
    numpy.polynomial.laguerre.lagline
    numpy.polynomial.hermite.hermline
    numpy.polynomial.hermite_e.hermeline

    Examples
    --------
    >>> import numpy.polynomial.chebyshev as C
    >>> C.chebline(3,2)
    array([3, 2])
    >>> C.chebval(-3, C.chebline(3,2)) # should be -3
    -3.0

    """
    if scl != 0:
        return np.array([off, scl])
    else:
        return np.array([off])


def chebfromroots(roots):
    """
    Generate a Chebyshev series with given roots.

    The function returns the coefficients of the polynomial

    .. math:: p(x) = (x - r_0) * (x - r_1) * ... * (x - r_n),

    in Chebyshev form, where the :math:`r_n` are the roots specified in
    `roots`.  If a zero has multiplicity n, then it must appear in `roots`
    n times.  For instance, if 2 is a root of multiplicity three and 3 is a
    root of multiplicity 2, then `roots` looks something like [2, 2, 2, 3, 3].
    The roots can appear in any order.

    If the returned coefficients are `c`, then

    .. math:: p(x) = c_0 + c_1 * T_1(x) + ... +  c_n * T_n(x)

    The coefficient of the last term is not generally 1 for monic
    polynomials in Chebyshev form.

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
    numpy.polynomial.legendre.legfromroots
    numpy.polynomial.laguerre.lagfromroots
    numpy.polynomial.hermite.hermfromroots
    numpy.polynomial.hermite_e.hermefromroots

    Examples
    --------
    >>> import numpy.polynomial.chebyshev as C
    >>> C.chebfromroots((-1,0,1)) # x^3 - x relative to the standard basis
    array([ 0.  , -0.25,  0.  ,  0.25])
    >>> j = complex(0,1)
    >>> C.chebfromroots((-j,j)) # x^2 + 1 relative to the standard basis
    array([1.5+0.j, 0. +0.j, 0.5+0.j])

    """
    return pu._fromroots(chebline, chebmul, roots)


def chebadd(c1, c2):
    """
    Add one Chebyshev series to another.

    Returns the sum of two Chebyshev series `c1` + `c2`.  The arguments
    are sequences of coefficients ordered from lowest order term to
    highest, i.e., [1,2,3] represents the series ``T_0 + 2*T_1 + 3*T_2``.

    Parameters
    ----------
    c1, c2 : array_like
        1-D arrays of Chebyshev series coefficients ordered from low to
        high.

    Returns
    -------
    out : ndarray
        Array representing the Chebyshev series of their sum.

    See Also
    --------
    chebsub, chebmulx, chebmul, chebdiv, chebpow

    Notes
    -----
    Unlike multiplication, division, etc., the sum of two Chebyshev series
    is a Chebyshev series (without having to "reproject" the result onto
    the basis set) so addition, just like that of "standard" polynomials,
    is simply "component-wise."

    Examples
    --------
    >>> from numpy.polynomial import chebyshev as C
    >>> c1 = (1,2,3)
    >>> c2 = (3,2,1)
    >>> C.chebadd(c1,c2)
    array([4., 4., 4.])

    """
    return pu._add(c1, c2)


def chebsub(c1, c2):
    """
    Subtract one Chebyshev series from another.

    Returns the difference of two Chebyshev series `c1` - `c2`.  The
    sequences of coefficients are from lowest order term to highest, i.e.,
    [1,2,3] represents the series ``T_0 + 2*T_1 + 3*T_2``.

    Parameters
    ----------
    c1, c2 : array_like
        1-D arrays of Chebyshev series coefficients ordered from low to
        high.

    Returns
    -------
    out : ndarray
        Of Chebyshev series coefficients representing their difference.

    See Also
    --------
    chebadd, chebmulx, chebmul, chebdiv, chebpow

    Notes
    -----
    Unlike multiplication, division, etc., the difference of two Chebyshev
    series is a Chebyshev series (without having to "reproject" the result
    onto the basis set) so subtraction, just like that of "standard"
    polynomials, is simply "component-wise."

    Examples
    --------
    >>> from numpy.polynomial import chebyshev as C
    >>> c1 = (1,2,3)
    >>> c2 = (3,2,1)
    >>> C.chebsub(c1,c2)
    array([-2.,  0.,  2.])
    >>> C.chebsub(c2,c1) # -C.chebsub(c1,c2)
    array([ 2.,  0., -2.])

    """
    return pu._sub(c1, c2)


def chebmulx(c):
    """Multiply a Chebyshev series by x.

    Multiply the polynomial `c` by x, where x is the independent
    variable.


    Parameters
    ----------
    c : array_like
        1-D array of Chebyshev series coefficients ordered from low to
        high.

    Returns
    -------
    out : ndarray
        Array representing the result of the multiplication.

    See Also
    --------
    chebadd, chebsub, chebmul, chebdiv, chebpow

    Examples
    --------
    >>> from numpy.polynomial import chebyshev as C
    >>> C.chebmulx([1,2,3])
    array([1. , 2.5, 1. , 1.5])

    """
    # c is a trimmed copy
    [c] = pu.as_series([c])
    # The zero series needs special treatment
    if len(c) == 1 and c[0] == 0:
        return c

    prd = np.empty(len(c) + 1, dtype=c.dtype)
    prd[0] = c[0] * 0
    prd[1] = c[0]
    if len(c) > 1:
        tmp = c[1:] / 2
        prd[2:] = tmp
        prd[0:-2] += tmp
    return prd


def chebmul(c1, c2):
    """
    Multiply one Chebyshev series by another.

    Returns the product of two Chebyshev series `c1` * `c2`.  The arguments
    are sequences of coefficients, from lowest order "term" to highest,
    e.g., [1,2,3] represents the series ``T_0 + 2*T_1 + 3*T_2``.

    Parameters
    ----------
    c1, c2 : array_like
        1-D arrays of Chebyshev series coefficients ordered from low to
        high.

    Returns
    -------
    out : ndarray
        Of Chebyshev series coefficients representing their product.

    See Also
    --------
    chebadd, chebsub, chebmulx, chebdiv, chebpow

    Notes
    -----
    In general, the (polynomial) product of two C-series results in terms
    that are not in the Chebyshev polynomial basis set.  Thus, to express
    the product as a C-series, it is typically necessary to "reproject"
    the product onto said basis set, which typically produces
    "unintuitive live" (but correct) results; see Examples section below.

    Examples
    --------
    >>> from numpy.polynomial import chebyshev as C
    >>> c1 = (1,2,3)
    >>> c2 = (3,2,1)
    >>> C.chebmul(c1,c2) # multiplication requires "reprojection"
    array([  6.5,  12. ,  12. ,   4. ,   1.5])

    """
    # c1, c2 are trimmed copies
    [c1, c2] = pu.as_series([c1, c2])
    z1 = _cseries_to_zseries(c1)
    z2 = _cseries_to_zseries(c2)
    prd = _zseries_mul(z1, z2)
    ret = _zseries_to_cseries(prd)
    return pu.trimseq(ret)


def chebdiv(c1, c2):
    """
    Divide one Chebyshev series by another.

    Returns the quotient-with-remainder of two Chebyshev series
    `c1` / `c2`.  The arguments are sequences of coefficients from lowest
    order "term" to highest, e.g., [1,2,3] represents the series
    ``T_0 + 2*T_1 + 3*T_2``.

    Parameters
    ----------
    c1, c2 : array_like
        1-D arrays of Chebyshev series coefficients ordered from low to
        high.

    Returns
    -------
    [quo, rem] : ndarrays
        Of Chebyshev series coefficients representing the quotient and
        remainder.

    See Also
    --------
    chebadd, chebsub, chebmulx, chebmul, chebpow

    Notes
    -----
    In general, the (polynomial) division of one C-series by another
    results in quotient and remainder terms that are not in the Chebyshev
    polynomial basis set.  Thus, to express these results as C-series, it
    is typically necessary to "reproject" the results onto said basis
    set, which typically produces "unintuitive" (but correct) results;
    see Examples section below.

    Examples
    --------
    >>> from numpy.polynomial import chebyshev as C
    >>> c1 = (1,2,3)
    >>> c2 = (3,2,1)
    >>> C.chebdiv(c1,c2) # quotient "intuitive," remainder not
    (array([3.]), array([-8., -4.]))
    >>> c2 = (0,1,2,3)
    >>> C.chebdiv(c2,c1) # neither "intuitive"
    (array([0., 2.]), array([-2., -4.]))

    """
    # c1, c2 are trimmed copies
    [c1, c2] = pu.as_series([c1, c2])
    if c2[-1] == 0:
        raise ZeroDivisionError  # FIXME: add message with details to exception

    # note: this is more efficient than `pu._div(chebmul, c1, c2)`
    lc1 = len(c1)
    lc2 = len(c2)
    if lc1 < lc2:
        return c1[:1] * 0, c1
    elif lc2 == 1:
        return c1 / c2[-1], c1[:1] * 0
    else:
        z1 = _cseries_to_zseries(c1)
        z2 = _cseries_to_zseries(c2)
        quo, rem = _zseries_div(z1, z2)
        quo = pu.trimseq(_zseries_to_cseries(quo))
        rem = pu.trimseq(_zseries_to_cseries(rem))
        return quo, rem


def chebpow(c, pow, maxpower=16):
    """Raise a Chebyshev series to a power.

    Returns the Chebyshev series `c` raised to the power `pow`. The
    argument `c` is a sequence of coefficients ordered from low to high.
    i.e., [1,2,3] is the series  ``T_0 + 2*T_1 + 3*T_2.``

    Parameters
    ----------
    c : array_like
        1-D array of Chebyshev series coefficients ordered from low to
        high.
    pow : integer
        Power to which the series will be raised
    maxpower : integer, optional
        Maximum power allowed. This is mainly to limit growth of the series
        to unmanageable size. Default is 16

    Returns
    -------
    coef : ndarray
        Chebyshev series of power.

    See Also
    --------
    chebadd, chebsub, chebmulx, chebmul, chebdiv

    Examples
    --------
    >>> from numpy.polynomial import chebyshev as C
    >>> C.chebpow([1, 2, 3, 4], 2)
    array([15.5, 22. , 16. , ..., 12.5, 12. ,  8. ])

    """
    # note: this is more efficient than `pu._pow(chebmul, c1, c2)`, as it
    # avoids converting between z and c series repeatedly

    # c is a trimmed copy
    [c] = pu.as_series([c])
    power = int(pow)
    if power != pow or power < 0:
        raise ValueError("Power must be a non-negative integer.")
    elif maxpower is not None and power > maxpower:
        raise ValueError("Power is too large")
    elif power == 0:
        return np.array([1], dtype=c.dtype)
    elif power == 1:
        return c
    else:
        # This can be made more efficient by using powers of two
        # in the usual way.
        zs = _cseries_to_zseries(c)
        prd = zs
        for i in range(2, power + 1):
            prd = np.convolve(prd, zs)
        return _zseries_to_cseries(prd)


def chebder(c, m=1, scl=1, axis=0):
    """
    Differentiate a Chebyshev series.

    Returns the Chebyshev series coefficients `c` differentiated `m` times
    along `axis`.  At each iteration the result is multiplied by `scl` (the
    scaling factor is for use in a linear change of variable). The argument
    `c` is an array of coefficients from low to high degree along each
    axis, e.g., [1,2,3] represents the series ``1*T_0 + 2*T_1 + 3*T_2``
    while [[1,2],[1,2]] represents ``1*T_0(x)*T_0(y) + 1*T_1(x)*T_0(y) +
    2*T_0(x)*T_1(y) + 2*T_1(x)*T_1(y)`` if axis=0 is ``x`` and axis=1 is
    ``y``.

    Parameters
    ----------
    c : array_like
        Array of Chebyshev series coefficients. If c is multidimensional
        the different axis correspond to different variables with the
        degree in each axis given by the corresponding index.
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
        Chebyshev series of the derivative.

    See Also
    --------
    chebint

    Notes
    -----
    In general, the result of differentiating a C-series needs to be
    "reprojected" onto the C-series basis set. Thus, typically, the
    result of this function is "unintuitive," albeit correct; see Examples
    section below.

    Examples
    --------
    >>> from numpy.polynomial import chebyshev as C
    >>> c = (1,2,3,4)
    >>> C.chebder(c)
    array([14., 12., 24.])
    >>> C.chebder(c,3)
    array([96.])
    >>> C.chebder(c,scl=-1)
    array([-14., -12., -24.])
    >>> C.chebder(c,2,-1)
    array([12.,  96.])

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
                der[j - 1] = (2 * j) * c[j]
                c[j - 2] += (j * c[j]) / (j - 2)
            if n > 1:
                der[1] = 4 * c[2]
            der[0] = c[1]
            c = der
    c = np.moveaxis(c, 0, iaxis)
    return c


def chebint(c, m=1, k=[], lbnd=0, scl=1, axis=0):
    """
    Integrate a Chebyshev series.

    Returns the Chebyshev series coefficients `c` integrated `m` times from
    `lbnd` along `axis`. At each iteration the resulting series is
    **multiplied** by `scl` and an integration constant, `k`, is added.
    The scaling factor is for use in a linear change of variable.  ("Buyer
    beware": note that, depending on what one is doing, one may want `scl`
    to be the reciprocal of what one might expect; for more information,
    see the Notes section below.)  The argument `c` is an array of
    coefficients from low to high degree along each axis, e.g., [1,2,3]
    represents the series ``T_0 + 2*T_1 + 3*T_2`` while [[1,2],[1,2]]
    represents ``1*T_0(x)*T_0(y) + 1*T_1(x)*T_0(y) + 2*T_0(x)*T_1(y) +
    2*T_1(x)*T_1(y)`` if axis=0 is ``x`` and axis=1 is ``y``.

    Parameters
    ----------
    c : array_like
        Array of Chebyshev series coefficients. If c is multidimensional
        the different axis correspond to different variables with the
        degree in each axis given by the corresponding index.
    m : int, optional
        Order of integration, must be positive. (Default: 1)
    k : {[], list, scalar}, optional
        Integration constant(s).  The value of the first integral at zero
        is the first value in the list, the value of the second integral
        at zero is the second value, etc.  If ``k == []`` (the default),
        all constants are set to zero.  If ``m == 1``, a single scalar can
        be given instead of a list.
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
        C-series coefficients of the integral.

    Raises
    ------
    ValueError
        If ``m < 1``, ``len(k) > m``, ``np.ndim(lbnd) != 0``, or
        ``np.ndim(scl) != 0``.

    See Also
    --------
    chebder

    Notes
    -----
    Note that the result of each integration is *multiplied* by `scl`.
    Why is this important to note?  Say one is making a linear change of
    variable :math:`u = ax + b` in an integral relative to `x`.  Then
    :math:`dx = du/a`, so one will need to set `scl` equal to
    :math:`1/a`- perhaps not what one would have first thought.

    Also note that, in general, the result of integrating a C-series needs
    to be "reprojected" onto the C-series basis set.  Thus, typically,
    the result of this function is "unintuitive," albeit correct; see
    Examples section below.

    Examples
    --------
    >>> from numpy.polynomial import chebyshev as C
    >>> c = (1,2,3)
    >>> C.chebint(c)
    array([ 0.5, -0.5,  0.5,  0.5])
    >>> C.chebint(c,3)
    array([ 0.03125   , -0.1875    ,  0.04166667, -0.05208333,  0.01041667, # may vary
        0.00625   ])
    >>> C.chebint(c, k=3)
    array([ 3.5, -0.5,  0.5,  0.5])
    >>> C.chebint(c,lbnd=-2)
    array([ 8.5, -0.5,  0.5,  0.5])
    >>> C.chebint(c,scl=-2)
    array([-1.,  1., -1., -1.])

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
                tmp[2] = c[1] / 4
            for j in range(2, n):
                tmp[j + 1] = c[j] / (2 * (j + 1))
                tmp[j - 1] -= c[j] / (2 * (j - 1))
            tmp[0] += k[i] - chebval(lbnd, tmp)
            c = tmp
    c = np.moveaxis(c, 0, iaxis)
    return c


def chebval(x, c, tensor=True):
    """
    Evaluate a Chebyshev series at points x.

    If `c` is of length `n + 1`, this function returns the value:

    .. math:: p(x) = c_0 * T_0(x) + c_1 * T_1(x) + ... + c_n * T_n(x)

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
    chebval2d, chebgrid2d, chebval3d, chebgrid3d

    Notes
    -----
    The evaluation uses Clenshaw recursion, aka synthetic division.

    """
    c = np.array(c, ndmin=1, copy=True)
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
        x2 = 2 * x
        c0 = c[-2]
        c1 = c[-1]
        for i in range(3, len(c) + 1):
            tmp = c0
            c0 = c[-i] - c1
            c1 = tmp + c1 * x2
    return c0 + c1 * x


def chebval2d(x, y, c):
    """
    Evaluate a 2-D Chebyshev series at points (x, y).

    This function returns the values:

    .. math:: p(x,y) = \\sum_{i,j} c_{i,j} * T_i(x) * T_j(y)

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
        dimension greater than 2 the remaining indices enumerate multiple
        sets of coefficients.

    Returns
    -------
    values : ndarray, compatible object
        The values of the two dimensional Chebyshev series at points formed
        from pairs of corresponding values from `x` and `y`.

    See Also
    --------
    chebval, chebgrid2d, chebval3d, chebgrid3d
    """
    return pu._valnd(chebval, c, x, y)


def chebgrid2d(x, y, c):
    """
    Evaluate a 2-D Chebyshev series on the Cartesian product of x and y.

    This function returns the values:

    .. math:: p(a,b) = \\sum_{i,j} c_{i,j} * T_i(a) * T_j(b),

    where the points `(a, b)` consist of all pairs formed by taking
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
    chebval, chebval2d, chebval3d, chebgrid3d
    """
    return pu._gridnd(chebval, c, x, y)


def chebval3d(x, y, z, c):
    """
    Evaluate a 3-D Chebyshev series at points (x, y, z).

    This function returns the values:

    .. math:: p(x,y,z) = \\sum_{i,j,k} c_{i,j,k} * T_i(x) * T_j(y) * T_k(z)

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
    chebval, chebval2d, chebgrid2d, chebgrid3d
    """
    return pu._valnd(chebval, c, x, y, z)


def chebgrid3d(x, y, z, c):
    """
    Evaluate a 3-D Chebyshev series on the Cartesian product of x, y, and z.

    This function returns the values:

    .. math:: p(a,b,c) = \\sum_{i,j,k} c_{i,j,k} * T_i(a) * T_j(b) * T_k(c)

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
    chebval, chebval2d, chebgrid2d, chebval3d
    """
    return pu._gridnd(chebval, c, x, y, z)


def chebvander(x, deg):
    """Pseudo-Vandermonde matrix of given degree.

    Returns the pseudo-Vandermonde matrix of degree `deg` and sample points
    `x`. The pseudo-Vandermonde matrix is defined by

    .. math:: V[..., i] = T_i(x),

    where ``0 <= i <= deg``. The leading indices of `V` index the elements of
    `x` and the last index is the degree of the Chebyshev polynomial.

    If `c` is a 1-D array of coefficients of length ``n + 1`` and `V` is the
    matrix ``V = chebvander(x, n)``, then ``np.dot(V, c)`` and
    ``chebval(x, c)`` are the same up to roundoff.  This equivalence is
    useful both for least squares fitting and for the evaluation of a large
    number of Chebyshev series of the same degree and sample points.

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
        The pseudo Vandermonde matrix. The shape of the returned matrix is
        ``x.shape + (deg + 1,)``, where The last index is the degree of the
        corresponding Chebyshev polynomial.  The dtype will be the same as
        the converted `x`.

    """
    ideg = pu._as_int(deg, "deg")
    if ideg < 0:
        raise ValueError("deg must be non-negative")

    x = np.array(x, copy=None, ndmin=1) + 0.0
    dims = (ideg + 1,) + x.shape
    dtyp = x.dtype
    v = np.empty(dims, dtype=dtyp)
    # Use forward recursion to generate the entries.
    v[0] = x * 0 + 1
    if ideg > 0:
        x2 = 2 * x
        v[1] = x
        for i in range(2, ideg + 1):
            v[i] = v[i - 1] * x2 - v[i - 2]
    return np.moveaxis(v, 0, -1)


def chebvander2d(x, y, deg):
    """Pseudo-Vandermonde matrix of given degrees.

    Returns the pseudo-Vandermonde matrix of degrees `deg` and sample
    points ``(x, y)``. The pseudo-Vandermonde matrix is defined by

    .. math:: V[..., (deg[1] + 1)*i + j] = T_i(x) * T_j(y),

    where ``0 <= i <= deg[0]`` and ``0 <= j <= deg[1]``. The leading indices of
    `V` index the points ``(x, y)`` and the last index encodes the degrees of
    the Chebyshev polynomials.

    If ``V = chebvander2d(x, y, [xdeg, ydeg])``, then the columns of `V`
    correspond to the elements of a 2-D coefficient array `c` of shape
    (xdeg + 1, ydeg + 1) in the order

    .. math:: c_{00}, c_{01}, c_{02} ... , c_{10}, c_{11}, c_{12} ...

    and ``np.dot(V, c.flat)`` and ``chebval2d(x, y, c)`` will be the same
    up to roundoff. This equivalence is useful both for least squares
    fitting and for the evaluation of a large number of 2-D Chebyshev
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
    chebvander, chebvander3d, chebval2d, chebval3d
    """
    return pu._vander_nd_flat((chebvander, chebvander), (x, y), deg)


def chebvander3d(x, y, z, deg):
    """Pseudo-Vandermonde matrix of given degrees.

    Returns the pseudo-Vandermonde matrix of degrees `deg` and sample
    points ``(x, y, z)``. If `l`, `m`, `n` are the given degrees in `x`, `y`, `z`,
    then The pseudo-Vandermonde matrix is defined by

    .. math:: V[..., (m+1)(n+1)i + (n+1)j + k] = T_i(x)*T_j(y)*T_k(z),

    where ``0 <= i <= l``, ``0 <= j <= m``, and ``0 <= j <= n``.  The leading
    indices of `V` index the points ``(x, y, z)`` and the last index encodes
    the degrees of the Chebyshev polynomials.

    If ``V = chebvander3d(x, y, z, [xdeg, ydeg, zdeg])``, then the columns
    of `V` correspond to the elements of a 3-D coefficient array `c` of
    shape (xdeg + 1, ydeg + 1, zdeg + 1) in the order

    .. math:: c_{000}, c_{001}, c_{002},... , c_{010}, c_{011}, c_{012},...

    and ``np.dot(V, c.flat)`` and ``chebval3d(x, y, z, c)`` will be the
    same up to roundoff. This equivalence is useful both for least squares
    fitting and for the evaluation of a large number of 3-D Chebyshev
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
    chebvander, chebvander3d, chebval2d, chebval3d
    """
    return pu._vander_nd_flat((chebvander, chebvander, chebvander), (x, y, z), deg)


def chebfit(x, y, deg, rcond=None, full=False, w=None):
    """
    Least squares fit of Chebyshev series to data.

    Return the coefficients of a Chebyshev series of degree `deg` that is the
    least squares fit to the data values `y` given at points `x`. If `y` is
    1-D the returned coefficients will also be 1-D. If `y` is 2-D multiple
    fits are done, one for each column of `y`, and the resulting
    coefficients are stored in the corresponding columns of a 2-D return.
    The fitted polynomial(s) are in the form

    .. math::  p(x) = c_0 + c_1 * T_1(x) + ... + c_n * T_n(x),

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
        Degree(s) of the fitting polynomials. If `deg` is a single integer,
        all terms up to and including the `deg`'th term are included in the
        fit. For NumPy versions >= 1.11.0 a list of integers specifying the
        degrees of the terms to include may be used instead.
    rcond : float, optional
        Relative condition number of the fit. Singular values smaller than
        this relative to the largest singular value will be ignored. The
        default value is ``len(x)*eps``, where eps is the relative precision of
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
        Chebyshev coefficients ordered from low to high. If `y` was 2-D,
        the coefficients for the data in column k  of `y` are in column
        `k`.

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
    numpy.polynomial.legendre.legfit
    numpy.polynomial.laguerre.lagfit
    numpy.polynomial.hermite.hermfit
    numpy.polynomial.hermite_e.hermefit
    chebval : Evaluates a Chebyshev series.
    chebvander : Vandermonde matrix of Chebyshev series.
    chebweight : Chebyshev weight function.
    numpy.linalg.lstsq : Computes a least-squares fit from the matrix.
    scipy.interpolate.UnivariateSpline : Computes spline fits.

    Notes
    -----
    The solution is the coefficients of the Chebyshev series `p` that
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

    Fits using Chebyshev series are usually better conditioned than fits
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
    return pu._fit(chebvander, x, y, deg, rcond, full, w)


def chebcompanion(c):
    """Return the scaled companion matrix of c.

    The basis polynomials are scaled so that the companion matrix is
    symmetric when `c` is a Chebyshev basis polynomial. This provides
    better eigenvalue estimates than the unscaled case and for basis
    polynomials the eigenvalues are guaranteed to be real if
    `numpy.linalg.eigvalsh` is used to obtain them.

    Parameters
    ----------
    c : array_like
        1-D array of Chebyshev series coefficients ordered from low to high
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
    scl = np.array([1.] + [np.sqrt(.5)] * (n - 1))
    top = mat.reshape(-1)[1::n + 1]
    bot = mat.reshape(-1)[n::n + 1]
    top[0] = np.sqrt(.5)
    top[1:] = 1 / 2
    bot[...] = top
    mat[:, -1] -= (c[:-1] / c[-1]) * (scl / scl[-1]) * .5
    return mat


def chebroots(c):
    """
    Compute the roots of a Chebyshev series.

    Return the roots (a.k.a. "zeros") of the polynomial

    .. math:: p(x) = \\sum_i c[i] * T_i(x).

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
    numpy.polynomial.legendre.legroots
    numpy.polynomial.laguerre.lagroots
    numpy.polynomial.hermite.hermroots
    numpy.polynomial.hermite_e.hermeroots

    Notes
    -----
    The root estimates are obtained as the eigenvalues of the companion
    matrix, Roots far from the origin of the complex plane may have large
    errors due to the numerical instability of the series for such
    values. Roots with multiplicity greater than 1 will also show larger
    errors as the value of the series near such points is relatively
    insensitive to errors in the roots. Isolated roots near the origin can
    be improved by a few iterations of Newton's method.

    The Chebyshev series basis polynomials aren't powers of `x` so the
    results of this function may seem unintuitive.

    Examples
    --------
    >>> import numpy.polynomial.chebyshev as cheb
    >>> cheb.chebroots((-1, 1,-1, 1)) # T3 - T2 + T1 - T0 has real roots
    array([ -5.00000000e-01,   2.60860684e-17,   1.00000000e+00]) # may vary

    """
    # c is a trimmed copy
    [c] = pu.as_series([c])
    if len(c) < 2:
        return np.array([], dtype=c.dtype)
    if len(c) == 2:
        return np.array([-c[0] / c[1]])

    # rotated companion matrix reduces error
    m = chebcompanion(c)[::-1, ::-1]
    r = la.eigvals(m)
    r.sort()
    return r


def chebinterpolate(func, deg, args=()):
    """Interpolate a function at the Chebyshev points of the first kind.

    Returns the Chebyshev series that interpolates `func` at the Chebyshev
    points of the first kind in the interval [-1, 1]. The interpolating
    series tends to a minmax approximation to `func` with increasing `deg`
    if the function is continuous in the interval.

    Parameters
    ----------
    func : function
        The function to be approximated. It must be a function of a single
        variable of the form ``f(x, a, b, c...)``, where ``a, b, c...`` are
        extra arguments passed in the `args` parameter.
    deg : int
        Degree of the interpolating polynomial
    args : tuple, optional
        Extra arguments to be used in the function call. Default is no extra
        arguments.

    Returns
    -------
    coef : ndarray, shape (deg + 1,)
        Chebyshev coefficients of the interpolating series ordered from low to
        high.

    Examples
    --------
    >>> import numpy.polynomial.chebyshev as C
    >>> C.chebinterpolate(lambda x: np.tanh(x) + 0.5, 8)
    array([  5.00000000e-01,   8.11675684e-01,  -9.86864911e-17,
            -5.42457905e-02,  -2.71387850e-16,   4.51658839e-03,
             2.46716228e-17,  -3.79694221e-04,  -3.26899002e-16])

    Notes
    -----
    The Chebyshev polynomials used in the interpolation are orthogonal when
    sampled at the Chebyshev points of the first kind. If it is desired to
    constrain some of the coefficients they can simply be set to the desired
    value after the interpolation, no new interpolation or fit is needed. This
    is especially useful if it is known apriori that some of coefficients are
    zero. For instance, if the function is even then the coefficients of the
    terms of odd degree in the result can be set to zero.

    """
    deg = np.asarray(deg)

    # check arguments.
    if deg.ndim > 0 or deg.dtype.kind not in 'iu' or deg.size == 0:
        raise TypeError("deg must be an int")
    if deg < 0:
        raise ValueError("expected deg >= 0")

    order = deg + 1
    xcheb = chebpts1(order)
    yfunc = func(xcheb, *args)
    m = chebvander(xcheb, deg)
    c = np.dot(m.T, yfunc)
    c[0] /= order
    c[1:] /= 0.5 * order

    return c


def chebgauss(deg):
    """
    Gauss-Chebyshev quadrature.

    Computes the sample points and weights for Gauss-Chebyshev quadrature.
    These sample points and weights will correctly integrate polynomials of
    degree :math:`2*deg - 1` or less over the interval :math:`[-1, 1]` with
    the weight function :math:`f(x) = 1/\\sqrt{1 - x^2}`.

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
    be problematic. For Gauss-Chebyshev there are closed form solutions for
    the sample points and weights. If n = `deg`, then

    .. math:: x_i = \\cos(\\pi (2 i - 1) / (2 n))

    .. math:: w_i = \\pi / n

    """
    ideg = pu._as_int(deg, "deg")
    if ideg <= 0:
        raise ValueError("deg must be a positive integer")

    x = np.cos(np.pi * np.arange(1, 2 * ideg, 2) / (2.0 * ideg))
    w = np.ones(ideg) * (np.pi / ideg)

    return x, w


def chebweight(x):
    """
    The weight function of the Chebyshev polynomials.

    The weight function is :math:`1/\\sqrt{1 - x^2}` and the interval of
    integration is :math:`[-1, 1]`. The Chebyshev polynomials are
    orthogonal, but not normalized, with respect to this weight function.

    Parameters
    ----------
    x : array_like
       Values at which the weight function will be computed.

    Returns
    -------
    w : ndarray
       The weight function at `x`.
    """
    w = 1. / (np.sqrt(1. + x) * np.sqrt(1. - x))
    return w


def chebpts1(npts):
    """
    Chebyshev points of the first kind.

    The Chebyshev points of the first kind are the points ``cos(x)``,
    where ``x = [pi*(k + .5)/npts for k in range(npts)]``.

    Parameters
    ----------
    npts : int
        Number of sample points desired.

    Returns
    -------
    pts : ndarray
        The Chebyshev points of the first kind.

    See Also
    --------
    chebpts2
    """
    _npts = int(npts)
    if _npts != npts:
        raise ValueError("npts must be integer")
    if _npts < 1:
        raise ValueError("npts must be >= 1")

    x = 0.5 * np.pi / _npts * np.arange(-_npts + 1, _npts + 1, 2)
    return np.sin(x)


def chebpts2(npts):
    """
    Chebyshev points of the second kind.

    The Chebyshev points of the second kind are the points ``cos(x)``,
    where ``x = [pi*k/(npts - 1) for k in range(npts)]`` sorted in ascending
    order.

    Parameters
    ----------
    npts : int
        Number of sample points desired.

    Returns
    -------
    pts : ndarray
        The Chebyshev points of the second kind.
    """
    _npts = int(npts)
    if _npts != npts:
        raise ValueError("npts must be integer")
    if _npts < 2:
        raise ValueError("npts must be >= 2")

    x = np.linspace(-np.pi, 0, _npts)
    return np.cos(x)


#
# Chebyshev series class
#

class Chebyshev(ABCPolyBase):
    """A Chebyshev series class.

    The Chebyshev class provides the standard Python numerical methods
    '+', '-', '*', '//', '%', 'divmod', '**', and '()' as well as the
    attributes and methods listed below.

    Parameters
    ----------
    coef : array_like
        Chebyshev coefficients in order of increasing degree, i.e.,
        ``(1, 2, 3)`` gives ``1*T_0(x) + 2*T_1(x) + 3*T_2(x)``.
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
    _add = staticmethod(chebadd)
    _sub = staticmethod(chebsub)
    _mul = staticmethod(chebmul)
    _div = staticmethod(chebdiv)
    _pow = staticmethod(chebpow)
    _val = staticmethod(chebval)
    _int = staticmethod(chebint)
    _der = staticmethod(chebder)
    _fit = staticmethod(chebfit)
    _line = staticmethod(chebline)
    _roots = staticmethod(chebroots)
    _fromroots = staticmethod(chebfromroots)

    @classmethod
    def interpolate(cls, func, deg, domain=None, args=()):
        """Interpolate a function at the Chebyshev points of the first kind.

        Returns the series that interpolates `func` at the Chebyshev points of
        the first kind scaled and shifted to the `domain`. The resulting series
        tends to a minmax approximation of `func` when the function is
        continuous in the domain.

        Parameters
        ----------
        func : function
            The function to be interpolated. It must be a function of a single
            variable of the form ``f(x, a, b, c...)``, where ``a, b, c...`` are
            extra arguments passed in the `args` parameter.
        deg : int
            Degree of the interpolating polynomial.
        domain : {None, [beg, end]}, optional
            Domain over which `func` is interpolated. The default is None, in
            which case the domain is [-1, 1].
        args : tuple, optional
            Extra arguments to be used in the function call. Default is no
            extra arguments.

        Returns
        -------
        polynomial : Chebyshev instance
            Interpolating Chebyshev instance.

        Notes
        -----
        See `numpy.polynomial.chebinterpolate` for more details.

        """
        if domain is None:
            domain = cls.domain
        xfunc = lambda x: func(pu.mapdomain(x, cls.window, domain), *args)
        coef = chebinterpolate(xfunc, deg)
        return cls(coef, domain=domain)

    # Virtual properties
    domain = np.array(chebdomain)
    window = np.array(chebdomain)
    basis_name = 'T'

# === NexusCore/openenv\Lib\site-packages\jinja2\compiler.py ===
"""Compiles nodes from the parser into Python code."""

import typing as t
from contextlib import contextmanager
from functools import update_wrapper
from io import StringIO
from itertools import chain
from keyword import iskeyword as is_python_keyword

from markupsafe import escape
from markupsafe import Markup

from . import nodes
from .exceptions import TemplateAssertionError
from .idtracking import Symbols
from .idtracking import VAR_LOAD_ALIAS
from .idtracking import VAR_LOAD_PARAMETER
from .idtracking import VAR_LOAD_RESOLVE
from .idtracking import VAR_LOAD_UNDEFINED
from .nodes import EvalContext
from .optimizer import Optimizer
from .utils import _PassArg
from .utils import concat
from .visitor import NodeVisitor

if t.TYPE_CHECKING:
    import typing_extensions as te

    from .environment import Environment

F = t.TypeVar("F", bound=t.Callable[..., t.Any])

operators = {
    "eq": "==",
    "ne": "!=",
    "gt": ">",
    "gteq": ">=",
    "lt": "<",
    "lteq": "<=",
    "in": "in",
    "notin": "not in",
}


def optimizeconst(f: F) -> F:
    def new_func(
        self: "CodeGenerator", node: nodes.Expr, frame: "Frame", **kwargs: t.Any
    ) -> t.Any:
        # Only optimize if the frame is not volatile
        if self.optimizer is not None and not frame.eval_ctx.volatile:
            new_node = self.optimizer.visit(node, frame.eval_ctx)

            if new_node != node:
                return self.visit(new_node, frame)

        return f(self, node, frame, **kwargs)

    return update_wrapper(new_func, f)  # type: ignore[return-value]


def _make_binop(op: str) -> t.Callable[["CodeGenerator", nodes.BinExpr, "Frame"], None]:
    @optimizeconst
    def visitor(self: "CodeGenerator", node: nodes.BinExpr, frame: Frame) -> None:
        if (
            self.environment.sandboxed and op in self.environment.intercepted_binops  # type: ignore
        ):
            self.write(f"environment.call_binop(context, {op!r}, ")
            self.visit(node.left, frame)
            self.write(", ")
            self.visit(node.right, frame)
        else:
            self.write("(")
            self.visit(node.left, frame)
            self.write(f" {op} ")
            self.visit(node.right, frame)

        self.write(")")

    return visitor


def _make_unop(
    op: str,
) -> t.Callable[["CodeGenerator", nodes.UnaryExpr, "Frame"], None]:
    @optimizeconst
    def visitor(self: "CodeGenerator", node: nodes.UnaryExpr, frame: Frame) -> None:
        if (
            self.environment.sandboxed and op in self.environment.intercepted_unops  # type: ignore
        ):
            self.write(f"environment.call_unop(context, {op!r}, ")
            self.visit(node.node, frame)
        else:
            self.write("(" + op)
            self.visit(node.node, frame)

        self.write(")")

    return visitor


def generate(
    node: nodes.Template,
    environment: "Environment",
    name: t.Optional[str],
    filename: t.Optional[str],
    stream: t.Optional[t.TextIO] = None,
    defer_init: bool = False,
    optimized: bool = True,
) -> t.Optional[str]:
    """Generate the python source for a node tree."""
    if not isinstance(node, nodes.Template):
        raise TypeError("Can't compile non template nodes")

    generator = environment.code_generator_class(
        environment, name, filename, stream, defer_init, optimized
    )
    generator.visit(node)

    if stream is None:
        return generator.stream.getvalue()  # type: ignore

    return None


def has_safe_repr(value: t.Any) -> bool:
    """Does the node have a safe representation?"""
    if value is None or value is NotImplemented or value is Ellipsis:
        return True

    if type(value) in {bool, int, float, complex, range, str, Markup}:
        return True

    if type(value) in {tuple, list, set, frozenset}:
        return all(has_safe_repr(v) for v in value)

    if type(value) is dict:  # noqa E721
        return all(has_safe_repr(k) and has_safe_repr(v) for k, v in value.items())

    return False


def find_undeclared(
    nodes: t.Iterable[nodes.Node], names: t.Iterable[str]
) -> t.Set[str]:
    """Check if the names passed are accessed undeclared.  The return value
    is a set of all the undeclared names from the sequence of names found.
    """
    visitor = UndeclaredNameVisitor(names)
    try:
        for node in nodes:
            visitor.visit(node)
    except VisitorExit:
        pass
    return visitor.undeclared


class MacroRef:
    def __init__(self, node: t.Union[nodes.Macro, nodes.CallBlock]) -> None:
        self.node = node
        self.accesses_caller = False
        self.accesses_kwargs = False
        self.accesses_varargs = False


class Frame:
    """Holds compile time information for us."""

    def __init__(
        self,
        eval_ctx: EvalContext,
        parent: t.Optional["Frame"] = None,
        level: t.Optional[int] = None,
    ) -> None:
        self.eval_ctx = eval_ctx

        # the parent of this frame
        self.parent = parent

        if parent is None:
            self.symbols = Symbols(level=level)

            # in some dynamic inheritance situations the compiler needs to add
            # write tests around output statements.
            self.require_output_check = False

            # inside some tags we are using a buffer rather than yield statements.
            # this for example affects {% filter %} or {% macro %}.  If a frame
            # is buffered this variable points to the name of the list used as
            # buffer.
            self.buffer: t.Optional[str] = None

            # the name of the block we're in, otherwise None.
            self.block: t.Optional[str] = None

        else:
            self.symbols = Symbols(parent.symbols, level=level)
            self.require_output_check = parent.require_output_check
            self.buffer = parent.buffer
            self.block = parent.block

        # a toplevel frame is the root + soft frames such as if conditions.
        self.toplevel = False

        # the root frame is basically just the outermost frame, so no if
        # conditions.  This information is used to optimize inheritance
        # situations.
        self.rootlevel = False

        # variables set inside of loops and blocks should not affect outer frames,
        # but they still needs to be kept track of as part of the active context.
        self.loop_frame = False
        self.block_frame = False

        # track whether the frame is being used in an if-statement or conditional
        # expression as it determines which errors should be raised during runtime
        # or compile time.
        self.soft_frame = False

    def copy(self) -> "te.Self":
        """Create a copy of the current one."""
        rv = object.__new__(self.__class__)
        rv.__dict__.update(self.__dict__)
        rv.symbols = self.symbols.copy()
        return rv

    def inner(self, isolated: bool = False) -> "Frame":
        """Return an inner frame."""
        if isolated:
            return Frame(self.eval_ctx, level=self.symbols.level + 1)
        return Frame(self.eval_ctx, self)

    def soft(self) -> "te.Self":
        """Return a soft frame.  A soft frame may not be modified as
        standalone thing as it shares the resources with the frame it
        was created of, but it's not a rootlevel frame any longer.

        This is only used to implement if-statements and conditional
        expressions.
        """
        rv = self.copy()
        rv.rootlevel = False
        rv.soft_frame = True
        return rv

    __copy__ = copy


class VisitorExit(RuntimeError):
    """Exception used by the `UndeclaredNameVisitor` to signal a stop."""


class DependencyFinderVisitor(NodeVisitor):
    """A visitor that collects filter and test calls."""

    def __init__(self) -> None:
        self.filters: t.Set[str] = set()
        self.tests: t.Set[str] = set()

    def visit_Filter(self, node: nodes.Filter) -> None:
        self.generic_visit(node)
        self.filters.add(node.name)

    def visit_Test(self, node: nodes.Test) -> None:
        self.generic_visit(node)
        self.tests.add(node.name)

    def visit_Block(self, node: nodes.Block) -> None:
        """Stop visiting at blocks."""


class UndeclaredNameVisitor(NodeVisitor):
    """A visitor that checks if a name is accessed without being
    declared.  This is different from the frame visitor as it will
    not stop at closure frames.
    """

    def __init__(self, names: t.Iterable[str]) -> None:
        self.names = set(names)
        self.undeclared: t.Set[str] = set()

    def visit_Name(self, node: nodes.Name) -> None:
        if node.ctx == "load" and node.name in self.names:
            self.undeclared.add(node.name)
            if self.undeclared == self.names:
                raise VisitorExit()
        else:
            self.names.discard(node.name)

    def visit_Block(self, node: nodes.Block) -> None:
        """Stop visiting a blocks."""


class CompilerExit(Exception):
    """Raised if the compiler encountered a situation where it just
    doesn't make sense to further process the code.  Any block that
    raises such an exception is not further processed.
    """


class CodeGenerator(NodeVisitor):
    def __init__(
        self,
        environment: "Environment",
        name: t.Optional[str],
        filename: t.Optional[str],
        stream: t.Optional[t.TextIO] = None,
        defer_init: bool = False,
        optimized: bool = True,
    ) -> None:
        if stream is None:
            stream = StringIO()
        self.environment = environment
        self.name = name
        self.filename = filename
        self.stream = stream
        self.created_block_context = False
        self.defer_init = defer_init
        self.optimizer: t.Optional[Optimizer] = None

        if optimized:
            self.optimizer = Optimizer(environment)

        # aliases for imports
        self.import_aliases: t.Dict[str, str] = {}

        # a registry for all blocks.  Because blocks are moved out
        # into the global python scope they are registered here
        self.blocks: t.Dict[str, nodes.Block] = {}

        # the number of extends statements so far
        self.extends_so_far = 0

        # some templates have a rootlevel extends.  In this case we
        # can safely assume that we're a child template and do some
        # more optimizations.
        self.has_known_extends = False

        # the current line number
        self.code_lineno = 1

        # registry of all filters and tests (global, not block local)
        self.tests: t.Dict[str, str] = {}
        self.filters: t.Dict[str, str] = {}

        # the debug information
        self.debug_info: t.List[t.Tuple[int, int]] = []
        self._write_debug_info: t.Optional[int] = None

        # the number of new lines before the next write()
        self._new_lines = 0

        # the line number of the last written statement
        self._last_line = 0

        # true if nothing was written so far.
        self._first_write = True

        # used by the `temporary_identifier` method to get new
        # unique, temporary identifier
        self._last_identifier = 0

        # the current indentation
        self._indentation = 0

        # Tracks toplevel assignments
        self._assign_stack: t.List[t.Set[str]] = []

        # Tracks parameter definition blocks
        self._param_def_block: t.List[t.Set[str]] = []

        # Tracks the current context.
        self._context_reference_stack = ["context"]

    @property
    def optimized(self) -> bool:
        return self.optimizer is not None

    # -- Various compilation helpers

    def fail(self, msg: str, lineno: int) -> "te.NoReturn":
        """Fail with a :exc:`TemplateAssertionError`."""
        raise TemplateAssertionError(msg, lineno, self.name, self.filename)

    def temporary_identifier(self) -> str:
        """Get a new unique identifier."""
        self._last_identifier += 1
        return f"t_{self._last_identifier}"

    def buffer(self, frame: Frame) -> None:
        """Enable buffering for the frame from that point onwards."""
        frame.buffer = self.temporary_identifier()
        self.writeline(f"{frame.buffer} = []")

    def return_buffer_contents(
        self, frame: Frame, force_unescaped: bool = False
    ) -> None:
        """Return the buffer contents of the frame."""
        if not force_unescaped:
            if frame.eval_ctx.volatile:
                self.writeline("if context.eval_ctx.autoescape:")
                self.indent()
                self.writeline(f"return Markup(concat({frame.buffer}))")
                self.outdent()
                self.writeline("else:")
                self.indent()
                self.writeline(f"return concat({frame.buffer})")
                self.outdent()
                return
            elif frame.eval_ctx.autoescape:
                self.writeline(f"return Markup(concat({frame.buffer}))")
                return
        self.writeline(f"return concat({frame.buffer})")

    def indent(self) -> None:
        """Indent by one."""
        self._indentation += 1

    def outdent(self, step: int = 1) -> None:
        """Outdent by step."""
        self._indentation -= step

    def start_write(self, frame: Frame, node: t.Optional[nodes.Node] = None) -> None:
        """Yield or write into the frame buffer."""
        if frame.buffer is None:
            self.writeline("yield ", node)
        else:
            self.writeline(f"{frame.buffer}.append(", node)

    def end_write(self, frame: Frame) -> None:
        """End the writing process started by `start_write`."""
        if frame.buffer is not None:
            self.write(")")

    def simple_write(
        self, s: str, frame: Frame, node: t.Optional[nodes.Node] = None
    ) -> None:
        """Simple shortcut for start_write + write + end_write."""
        self.start_write(frame, node)
        self.write(s)
        self.end_write(frame)

    def blockvisit(self, nodes: t.Iterable[nodes.Node], frame: Frame) -> None:
        """Visit a list of nodes as block in a frame.  If the current frame
        is no buffer a dummy ``if 0: yield None`` is written automatically.
        """
        try:
            self.writeline("pass")
            for node in nodes:
                self.visit(node, frame)
        except CompilerExit:
            pass

    def write(self, x: str) -> None:
        """Write a string into the output stream."""
        if self._new_lines:
            if not self._first_write:
                self.stream.write("\n" * self._new_lines)
                self.code_lineno += self._new_lines
                if self._write_debug_info is not None:
                    self.debug_info.append((self._write_debug_info, self.code_lineno))
                    self._write_debug_info = None
            self._first_write = False
            self.stream.write("    " * self._indentation)
            self._new_lines = 0
        self.stream.write(x)

    def writeline(
        self, x: str, node: t.Optional[nodes.Node] = None, extra: int = 0
    ) -> None:
        """Combination of newline and write."""
        self.newline(node, extra)
        self.write(x)

    def newline(self, node: t.Optional[nodes.Node] = None, extra: int = 0) -> None:
        """Add one or more newlines before the next write."""
        self._new_lines = max(self._new_lines, 1 + extra)
        if node is not None and node.lineno != self._last_line:
            self._write_debug_info = node.lineno
            self._last_line = node.lineno

    def signature(
        self,
        node: t.Union[nodes.Call, nodes.Filter, nodes.Test],
        frame: Frame,
        extra_kwargs: t.Optional[t.Mapping[str, t.Any]] = None,
    ) -> None:
        """Writes a function call to the stream for the current node.
        A leading comma is added automatically.  The extra keyword
        arguments may not include python keywords otherwise a syntax
        error could occur.  The extra keyword arguments should be given
        as python dict.
        """
        # if any of the given keyword arguments is a python keyword
        # we have to make sure that no invalid call is created.
        kwarg_workaround = any(
            is_python_keyword(t.cast(str, k))
            for k in chain((x.key for x in node.kwargs), extra_kwargs or ())
        )

        for arg in node.args:
            self.write(", ")
            self.visit(arg, frame)

        if not kwarg_workaround:
            for kwarg in node.kwargs:
                self.write(", ")
                self.visit(kwarg, frame)
            if extra_kwargs is not None:
                for key, value in extra_kwargs.items():
                    self.write(f", {key}={value}")
        if node.dyn_args:
            self.write(", *")
            self.visit(node.dyn_args, frame)

        if kwarg_workaround:
            if node.dyn_kwargs is not None:
                self.write(", **dict({")
            else:
                self.write(", **{")
            for kwarg in node.kwargs:
                self.write(f"{kwarg.key!r}: ")
                self.visit(kwarg.value, frame)
                self.write(", ")
            if extra_kwargs is not None:
                for key, value in extra_kwargs.items():
                    self.write(f"{key!r}: {value}, ")
            if node.dyn_kwargs is not None:
                self.write("}, **")
                self.visit(node.dyn_kwargs, frame)
                self.write(")")
            else:
                self.write("}")

        elif node.dyn_kwargs is not None:
            self.write(", **")
            self.visit(node.dyn_kwargs, frame)

    def pull_dependencies(self, nodes: t.Iterable[nodes.Node]) -> None:
        """Find all filter and test names used in the template and
        assign them to variables in the compiled namespace. Checking
        that the names are registered with the environment is done when
        compiling the Filter and Test nodes. If the node is in an If or
        CondExpr node, the check is done at runtime instead.

        .. versionchanged:: 3.0
            Filters and tests in If and CondExpr nodes are checked at
            runtime instead of compile time.
        """
        visitor = DependencyFinderVisitor()

        for node in nodes:
            visitor.visit(node)

        for id_map, names, dependency in (
            (self.filters, visitor.filters, "filters"),
            (
                self.tests,
                visitor.tests,
                "tests",
            ),
        ):
            for name in sorted(names):
                if name not in id_map:
                    id_map[name] = self.temporary_identifier()

                # add check during runtime that dependencies used inside of executed
                # blocks are defined, as this step may be skipped during compile time
                self.writeline("try:")
                self.indent()
                self.writeline(f"{id_map[name]} = environment.{dependency}[{name!r}]")
                self.outdent()
                self.writeline("except KeyError:")
                self.indent()
                self.writeline("@internalcode")
                self.writeline(f"def {id_map[name]}(*unused):")
                self.indent()
                self.writeline(
                    f'raise TemplateRuntimeError("No {dependency[:-1]}'
                    f' named {name!r} found.")'
                )
                self.outdent()
                self.outdent()

    def enter_frame(self, frame: Frame) -> None:
        undefs = []
        for target, (action, param) in frame.symbols.loads.items():
            if action == VAR_LOAD_PARAMETER:
                pass
            elif action == VAR_LOAD_RESOLVE:
                self.writeline(f"{target} = {self.get_resolve_func()}({param!r})")
            elif action == VAR_LOAD_ALIAS:
                self.writeline(f"{target} = {param}")
            elif action == VAR_LOAD_UNDEFINED:
                undefs.append(target)
            else:
                raise NotImplementedError("unknown load instruction")
        if undefs:
            self.writeline(f"{' = '.join(undefs)} = missing")

    def leave_frame(self, frame: Frame, with_python_scope: bool = False) -> None:
        if not with_python_scope:
            undefs = []
            for target in frame.symbols.loads:
                undefs.append(target)
            if undefs:
                self.writeline(f"{' = '.join(undefs)} = missing")

    def choose_async(self, async_value: str = "async ", sync_value: str = "") -> str:
        return async_value if self.environment.is_async else sync_value

    def func(self, name: str) -> str:
        return f"{self.choose_async()}def {name}"

    def macro_body(
        self, node: t.Union[nodes.Macro, nodes.CallBlock], frame: Frame
    ) -> t.Tuple[Frame, MacroRef]:
        """Dump the function def of a macro or call block."""
        frame = frame.inner()
        frame.symbols.analyze_node(node)
        macro_ref = MacroRef(node)

        explicit_caller = None
        skip_special_params = set()
        args = []

        for idx, arg in enumerate(node.args):
            if arg.name == "caller":
                explicit_caller = idx
            if arg.name in ("kwargs", "varargs"):
                skip_special_params.add(arg.name)
            args.append(frame.symbols.ref(arg.name))

        undeclared = find_undeclared(node.body, ("caller", "kwargs", "varargs"))

        if "caller" in undeclared:
            # In older Jinja versions there was a bug that allowed caller
            # to retain the special behavior even if it was mentioned in
            # the argument list.  However thankfully this was only really
            # working if it was the last argument.  So we are explicitly
            # checking this now and error out if it is anywhere else in
            # the argument list.
            if explicit_caller is not None:
                try:
                    node.defaults[explicit_caller - len(node.args)]
                except IndexError:
                    self.fail(
                        "When defining macros or call blocks the "
                        'special "caller" argument must be omitted '
                        "or be given a default.",
                        node.lineno,
                    )
            else:
                args.append(frame.symbols.declare_parameter("caller"))
            macro_ref.accesses_caller = True
        if "kwargs" in undeclared and "kwargs" not in skip_special_params:
            args.append(frame.symbols.declare_parameter("kwargs"))
            macro_ref.accesses_kwargs = True
        if "varargs" in undeclared and "varargs" not in skip_special_params:
            args.append(frame.symbols.declare_parameter("varargs"))
            macro_ref.accesses_varargs = True

        # macros are delayed, they never require output checks
        frame.require_output_check = False
        frame.symbols.analyze_node(node)
        self.writeline(f"{self.func('macro')}({', '.join(args)}):", node)
        self.indent()

        self.buffer(frame)
        self.enter_frame(frame)

        self.push_parameter_definitions(frame)
        for idx, arg in enumerate(node.args):
            ref = frame.symbols.ref(arg.name)
            self.writeline(f"if {ref} is missing:")
            self.indent()
            try:
                default = node.defaults[idx - len(node.args)]
            except IndexError:
                self.writeline(
                    f'{ref} = undefined("parameter {arg.name!r} was not provided",'
                    f" name={arg.name!r})"
                )
            else:
                self.writeline(f"{ref} = ")
                self.visit(default, frame)
            self.mark_parameter_stored(ref)
            self.outdent()
        self.pop_parameter_definitions()

        self.blockvisit(node.body, frame)
        self.return_buffer_contents(frame, force_unescaped=True)
        self.leave_frame(frame, with_python_scope=True)
        self.outdent()

        return frame, macro_ref

    def macro_def(self, macro_ref: MacroRef, frame: Frame) -> None:
        """Dump the macro definition for the def created by macro_body."""
        arg_tuple = ", ".join(repr(x.name) for x in macro_ref.node.args)
        name = getattr(macro_ref.node, "name", None)
        if len(macro_ref.node.args) == 1:
            arg_tuple += ","
        self.write(
            f"Macro(environment, macro, {name!r}, ({arg_tuple}),"
            f" {macro_ref.accesses_kwargs!r}, {macro_ref.accesses_varargs!r},"
            f" {macro_ref.accesses_caller!r}, context.eval_ctx.autoescape)"
        )

    def position(self, node: nodes.Node) -> str:
        """Return a human readable position for the node."""
        rv = f"line {node.lineno}"
        if self.name is not None:
            rv = f"{rv} in {self.name!r}"
        return rv

    def dump_local_context(self, frame: Frame) -> str:
        items_kv = ", ".join(
            f"{name!r}: {target}"
            for name, target in frame.symbols.dump_stores().items()
        )
        return f"{{{items_kv}}}"

    def write_commons(self) -> None:
        """Writes a common preamble that is used by root and block functions.
        Primarily this sets up common local helpers and enforces a generator
        through a dead branch.
        """
        self.writeline("resolve = context.resolve_or_missing")
        self.writeline("undefined = environment.undefined")
        self.writeline("concat = environment.concat")
        # always use the standard Undefined class for the implicit else of
        # conditional expressions
        self.writeline("cond_expr_undefined = Undefined")
        self.writeline("if 0: yield None")

    def push_parameter_definitions(self, frame: Frame) -> None:
        """Pushes all parameter targets from the given frame into a local
        stack that permits tracking of yet to be assigned parameters.  In
        particular this enables the optimization from `visit_Name` to skip
        undefined expressions for parameters in macros as macros can reference
        otherwise unbound parameters.
        """
        self._param_def_block.append(frame.symbols.dump_param_targets())

    def pop_parameter_definitions(self) -> None:
        """Pops the current parameter definitions set."""
        self._param_def_block.pop()

    def mark_parameter_stored(self, target: str) -> None:
        """Marks a parameter in the current parameter definitions as stored.
        This will skip the enforced undefined checks.
        """
        if self._param_def_block:
            self._param_def_block[-1].discard(target)

    def push_context_reference(self, target: str) -> None:
        self._context_reference_stack.append(target)

    def pop_context_reference(self) -> None:
        self._context_reference_stack.pop()

    def get_context_ref(self) -> str:
        return self._context_reference_stack[-1]

    def get_resolve_func(self) -> str:
        target = self._context_reference_stack[-1]
        if target == "context":
            return "resolve"
        return f"{target}.resolve"

    def derive_context(self, frame: Frame) -> str:
        return f"{self.get_context_ref()}.derived({self.dump_local_context(frame)})"

    def parameter_is_undeclared(self, target: str) -> bool:
        """Checks if a given target is an undeclared parameter."""
        if not self._param_def_block:
            return False
        return target in self._param_def_block[-1]

    def push_assign_tracking(self) -> None:
        """Pushes a new layer for assignment tracking."""
        self._assign_stack.append(set())

    def pop_assign_tracking(self, frame: Frame) -> None:
        """Pops the topmost level for assignment tracking and updates the
        context variables if necessary.
        """
        vars = self._assign_stack.pop()
        if (
            not frame.block_frame
            and not frame.loop_frame
            and not frame.toplevel
            or not vars
        ):
            return
        public_names = [x for x in vars if x[:1] != "_"]
        if len(vars) == 1:
            name = next(iter(vars))
            ref = frame.symbols.ref(name)
            if frame.loop_frame:
                self.writeline(f"_loop_vars[{name!r}] = {ref}")
                return
            if frame.block_frame:
                self.writeline(f"_block_vars[{name!r}] = {ref}")
                return
            self.writeline(f"context.vars[{name!r}] = {ref}")
        else:
            if frame.loop_frame:
                self.writeline("_loop_vars.update({")
            elif frame.block_frame:
                self.writeline("_block_vars.update({")
            else:
                self.writeline("context.vars.update({")
            for idx, name in enumerate(sorted(vars)):
                if idx:
                    self.write(", ")
                ref = frame.symbols.ref(name)
                self.write(f"{name!r}: {ref}")
            self.write("})")
        if not frame.block_frame and not frame.loop_frame and public_names:
            if len(public_names) == 1:
                self.writeline(f"context.exported_vars.add({public_names[0]!r})")
            else:
                names_str = ", ".join(map(repr, sorted(public_names)))
                self.writeline(f"context.exported_vars.update(({names_str}))")

    # -- Statement Visitors

    def visit_Template(
        self, node: nodes.Template, frame: t.Optional[Frame] = None
    ) -> None:
        assert frame is None, "no root frame allowed"
        eval_ctx = EvalContext(self.environment, self.name)

        from .runtime import async_exported
        from .runtime import exported

        if self.environment.is_async:
            exported_names = sorted(exported + async_exported)
        else:
            exported_names = sorted(exported)

        self.writeline("from jinja2.runtime import " + ", ".join(exported_names))

        # if we want a deferred initialization we cannot move the
        # environment into a local name
        envenv = "" if self.defer_init else ", environment=environment"

        # do we have an extends tag at all?  If not, we can save some
        # overhead by just not processing any inheritance code.
        have_extends = node.find(nodes.Extends) is not None

        # find all blocks
        for block in node.find_all(nodes.Block):
            if block.name in self.blocks:
                self.fail(f"block {block.name!r} defined twice", block.lineno)
            self.blocks[block.name] = block

        # find all imports and import them
        for import_ in node.find_all(nodes.ImportedName):
            if import_.importname not in self.import_aliases:
                imp = import_.importname
                self.import_aliases[imp] = alias = self.temporary_identifier()
                if "." in imp:
                    module, obj = imp.rsplit(".", 1)
                    self.writeline(f"from {module} import {obj} as {alias}")
                else:
                    self.writeline(f"import {imp} as {alias}")

        # add the load name
        self.writeline(f"name = {self.name!r}")

        # generate the root render function.
        self.writeline(
            f"{self.func('root')}(context, missing=missing{envenv}):", extra=1
        )
        self.indent()
        self.write_commons()

        # process the root
        frame = Frame(eval_ctx)
        if "self" in find_undeclared(node.body, ("self",)):
            ref = frame.symbols.declare_parameter("self")
            self.writeline(f"{ref} = TemplateReference(context)")
        frame.symbols.analyze_node(node)
        frame.toplevel = frame.rootlevel = True
        frame.require_output_check = have_extends and not self.has_known_extends
        if have_extends:
            self.writeline("parent_template = None")
        self.enter_frame(frame)
        self.pull_dependencies(node.body)
        self.blockvisit(node.body, frame)
        self.leave_frame(frame, with_python_scope=True)
        self.outdent()

        # make sure that the parent root is called.
        if have_extends:
            if not self.has_known_extends:
                self.indent()
                self.writeline("if parent_template is not None:")
            self.indent()
            if not self.environment.is_async:
                self.writeline("yield from parent_template.root_render_func(context)")
            else:
                self.writeline("agen = parent_template.root_render_func(context)")
                self.writeline("try:")
                self.indent()
                self.writeline("async for event in agen:")
                self.indent()
                self.writeline("yield event")
                self.outdent()
                self.outdent()
                self.writeline("finally: await agen.aclose()")
            self.outdent(1 + (not self.has_known_extends))

        # at this point we now have the blocks collected and can visit them too.
        for name, block in self.blocks.items():
            self.writeline(
                f"{self.func('block_' + name)}(context, missing=missing{envenv}):",
                block,
                1,
            )
            self.indent()
            self.write_commons()
            # It's important that we do not make this frame a child of the
            # toplevel template.  This would cause a variety of
            # interesting issues with identifier tracking.
            block_frame = Frame(eval_ctx)
            block_frame.block_frame = True
            undeclared = find_undeclared(block.body, ("self", "super"))
            if "self" in undeclared:
                ref = block_frame.symbols.declare_parameter("self")
                self.writeline(f"{ref} = TemplateReference(context)")
            if "super" in undeclared:
                ref = block_frame.symbols.declare_parameter("super")
                self.writeline(f"{ref} = context.super({name!r}, block_{name})")
            block_frame.symbols.analyze_node(block)
            block_frame.block = name
            self.writeline("_block_vars = {}")
            self.enter_frame(block_frame)
            self.pull_dependencies(block.body)
            self.blockvisit(block.body, block_frame)
            self.leave_frame(block_frame, with_python_scope=True)
            self.outdent()

        blocks_kv_str = ", ".join(f"{x!r}: block_{x}" for x in self.blocks)
        self.writeline(f"blocks = {{{blocks_kv_str}}}", extra=1)
        debug_kv_str = "&".join(f"{k}={v}" for k, v in self.debug_info)
        self.writeline(f"debug_info = {debug_kv_str!r}")

    def visit_Block(self, node: nodes.Block, frame: Frame) -> None:
        """Call a block and register it for the template."""
        level = 0
        if frame.toplevel:
            # if we know that we are a child template, there is no need to
            # check if we are one
            if self.has_known_extends:
                return
            if self.extends_so_far > 0:
                self.writeline("if parent_template is None:")
                self.indent()
                level += 1

        if node.scoped:
            context = self.derive_context(frame)
        else:
            context = self.get_context_ref()

        if node.required:
            self.writeline(f"if len(context.blocks[{node.name!r}]) <= 1:", node)
            self.indent()
            self.writeline(
                f'raise TemplateRuntimeError("Required block {node.name!r} not found")',
                node,
            )
            self.outdent()

        if not self.environment.is_async and frame.buffer is None:
            self.writeline(
                f"yield from context.blocks[{node.name!r}][0]({context})", node
            )
        else:
            self.writeline(f"gen = context.blocks[{node.name!r}][0]({context})")
            self.writeline("try:")
            self.indent()
            self.writeline(
                f"{self.choose_async()}for event in gen:",
                node,
            )
            self.indent()
            self.simple_write("event", frame)
            self.outdent()
            self.outdent()
            self.writeline(
                f"finally: {self.choose_async('await gen.aclose()', 'gen.close()')}"
            )

        self.outdent(level)

    def visit_Extends(self, node: nodes.Extends, frame: Frame) -> None:
        """Calls the extender."""
        if not frame.toplevel:
            self.fail("cannot use extend from a non top-level scope", node.lineno)

        # if the number of extends statements in general is zero so
        # far, we don't have to add a check if something extended
        # the template before this one.
        if self.extends_so_far > 0:
            # if we have a known extends we just add a template runtime
            # error into the generated code.  We could catch that at compile
            # time too, but i welcome it not to confuse users by throwing the
            # same error at different times just "because we can".
            if not self.has_known_extends:
                self.writeline("if parent_template is not None:")
                self.indent()
            self.writeline('raise TemplateRuntimeError("extended multiple times")')

            # if we have a known extends already we don't need that code here
            # as we know that the template execution will end here.
            if self.has_known_extends:
                raise CompilerExit()
            else:
                self.outdent()

        self.writeline("parent_template = environment.get_template(", node)
        self.visit(node.template, frame)
        self.write(f", {self.name!r})")
        self.writeline("for name, parent_block in parent_template.blocks.items():")
        self.indent()
        self.writeline("context.blocks.setdefault(name, []).append(parent_block)")
        self.outdent()

        # if this extends statement was in the root level we can take
        # advantage of that information and simplify the generated code
        # in the top level from this point onwards
        if frame.rootlevel:
            self.has_known_extends = True

        # and now we have one more
        self.extends_so_far += 1

    def visit_Include(self, node: nodes.Include, frame: Frame) -> None:
        """Handles includes."""
        if node.ignore_missing:
            self.writeline("try:")
            self.indent()

        func_name = "get_or_select_template"
        if isinstance(node.template, nodes.Const):
            if isinstance(node.template.value, str):
                func_name = "get_template"
            elif isinstance(node.template.value, (tuple, list)):
                func_name = "select_template"
        elif isinstance(node.template, (nodes.Tuple, nodes.List)):
            func_name = "select_template"

        self.writeline(f"template = environment.{func_name}(", node)
        self.visit(node.template, frame)
        self.write(f", {self.name!r})")
        if node.ignore_missing:
            self.outdent()
            self.writeline("except TemplateNotFound:")
            self.indent()
            self.writeline("pass")
            self.outdent()
            self.writeline("else:")
            self.indent()

        def loop_body() -> None:
            self.indent()
            self.simple_write("event", frame)
            self.outdent()

        if node.with_context:
            self.writeline(
                f"gen = template.root_render_func("
                "template.new_context(context.get_all(), True,"
                f" {self.dump_local_context(frame)}))"
            )
            self.writeline("try:")
            self.indent()
            self.writeline(f"{self.choose_async()}for event in gen:")
            loop_body()
            self.outdent()
            self.writeline(
                f"finally: {self.choose_async('await gen.aclose()', 'gen.close()')}"
            )
        elif self.environment.is_async:
            self.writeline(
                "for event in (await template._get_default_module_async())"
                "._body_stream:"
            )
            loop_body()
        else:
            self.writeline("yield from template._get_default_module()._body_stream")

        if node.ignore_missing:
            self.outdent()

    def _import_common(
        self, node: t.Union[nodes.Import, nodes.FromImport], frame: Frame
    ) -> None:
        self.write(f"{self.choose_async('await ')}environment.get_template(")
        self.visit(node.template, frame)
        self.write(f", {self.name!r}).")

        if node.with_context:
            f_name = f"make_module{self.choose_async('_async')}"
            self.write(
                f"{f_name}(context.get_all(), True, {self.dump_local_context(frame)})"
            )
        else:
            self.write(f"_get_default_module{self.choose_async('_async')}(context)")

    def visit_Import(self, node: nodes.Import, frame: Frame) -> None:
        """Visit regular imports."""
        self.writeline(f"{frame.symbols.ref(node.target)} = ", node)
        if frame.toplevel:
            self.write(f"context.vars[{node.target!r}] = ")

        self._import_common(node, frame)

        if frame.toplevel and not node.target.startswith("_"):
            self.writeline(f"context.exported_vars.discard({node.target!r})")

    def visit_FromImport(self, node: nodes.FromImport, frame: Frame) -> None:
        """Visit named imports."""
        self.newline(node)
        self.write("included_template = ")
        self._import_common(node, frame)
        var_names = []
        discarded_names = []
        for name in node.names:
            if isinstance(name, tuple):
                name, alias = name
            else:
                alias = name
            self.writeline(
                f"{frame.symbols.ref(alias)} ="
                f" getattr(included_template, {name!r}, missing)"
            )
            self.writeline(f"if {frame.symbols.ref(alias)} is missing:")
            self.indent()
            # The position will contain the template name, and will be formatted
            # into a string that will be compiled into an f-string. Curly braces
            # in the name must be replaced with escapes so that they will not be
            # executed as part of the f-string.
            position = self.position(node).replace("{", "{{").replace("}", "}}")
            message = (
                "the template {included_template.__name__!r}"
                f" (imported on {position})"
                f" does not export the requested name {name!r}"
            )
            self.writeline(
                f"{frame.symbols.ref(alias)} = undefined(f{message!r}, name={name!r})"
            )
            self.outdent()
            if frame.toplevel:
                var_names.append(alias)
                if not alias.startswith("_"):
                    discarded_names.append(alias)

        if var_names:
            if len(var_names) == 1:
                name = var_names[0]
                self.writeline(f"context.vars[{name!r}] = {frame.symbols.ref(name)}")
            else:
                names_kv = ", ".join(
                    f"{name!r}: {frame.symbols.ref(name)}" for name in var_names
                )
                self.writeline(f"context.vars.update({{{names_kv}}})")
        if discarded_names:
            if len(discarded_names) == 1:
                self.writeline(f"context.exported_vars.discard({discarded_names[0]!r})")
            else:
                names_str = ", ".join(map(repr, discarded_names))
                self.writeline(
                    f"context.exported_vars.difference_update(({names_str}))"
                )

    def visit_For(self, node: nodes.For, frame: Frame) -> None:
        loop_frame = frame.inner()
        loop_frame.loop_frame = True
        test_frame = frame.inner()
        else_frame = frame.inner()

        # try to figure out if we have an extended loop.  An extended loop
        # is necessary if the loop is in recursive mode if the special loop
        # variable is accessed in the body if the body is a scoped block.
        extended_loop = (
            node.recursive
            or "loop"
            in find_undeclared(node.iter_child_nodes(only=("body",)), ("loop",))
            or any(block.scoped for block in node.find_all(nodes.Block))
        )

        loop_ref = None
        if extended_loop:
            loop_ref = loop_frame.symbols.declare_parameter("loop")

        loop_frame.symbols.analyze_node(node, for_branch="body")
        if node.else_:
            else_frame.symbols.analyze_node(node, for_branch="else")

        if node.test:
            loop_filter_func = self.temporary_identifier()
            test_frame.symbols.analyze_node(node, for_branch="test")
            self.writeline(f"{self.func(loop_filter_func)}(fiter):", node.test)
            self.indent()
            self.enter_frame(test_frame)
            self.writeline(self.choose_async("async for ", "for "))
            self.visit(node.target, loop_frame)
            self.write(" in ")
            self.write(self.choose_async("auto_aiter(fiter)", "fiter"))
            self.write(":")
            self.indent()
            self.writeline("if ", node.test)
            self.visit(node.test, test_frame)
            self.write(":")
            self.indent()
            self.writeline("yield ")
            self.visit(node.target, loop_frame)
            self.outdent(3)
            self.leave_frame(test_frame, with_python_scope=True)

        # if we don't have an recursive loop we have to find the shadowed
        # variables at that point.  Because loops can be nested but the loop
        # variable is a special one we have to enforce aliasing for it.
        if node.recursive:
            self.writeline(
                f"{self.func('loop')}(reciter, loop_render_func, depth=0):", node
            )
            self.indent()
            self.buffer(loop_frame)

            # Use the same buffer for the else frame
            else_frame.buffer = loop_frame.buffer

        # make sure the loop variable is a special one and raise a template
        # assertion error if a loop tries to write to loop
        if extended_loop:
            self.writeline(f"{loop_ref} = missing")

        for name in node.find_all(nodes.Name):
            if name.ctx == "store" and name.name == "loop":
                self.fail(
                    "Can't assign to special loop variable in for-loop target",
                    name.lineno,
                )

        if node.else_:
            iteration_indicator = self.temporary_identifier()
            self.writeline(f"{iteration_indicator} = 1")

        self.writeline(self.choose_async("async for ", "for "), node)
        self.visit(node.target, loop_frame)
        if extended_loop:
            self.write(f", {loop_ref} in {self.choose_async('Async')}LoopContext(")
        else:
            self.write(" in ")

        if node.test:
            self.write(f"{loop_filter_func}(")
        if node.recursive:
            self.write("reciter")
        else:
            if self.environment.is_async and not extended_loop:
                self.write("auto_aiter(")
            self.visit(node.iter, frame)
            if self.environment.is_async and not extended_loop:
                self.write(")")
        if node.test:
            self.write(")")

        if node.recursive:
            self.write(", undefined, loop_render_func, depth):")
        else:
            self.write(", undefined):" if extended_loop else ":")

        self.indent()
        self.enter_frame(loop_frame)

        self.writeline("_loop_vars = {}")
        self.blockvisit(node.body, loop_frame)
        if node.else_:
            self.writeline(f"{iteration_indicator} = 0")
        self.outdent()
        self.leave_frame(
            loop_frame, with_python_scope=node.recursive and not node.else_
        )

        if node.else_:
            self.writeline(f"if {iteration_indicator}:")
            self.indent()
            self.enter_frame(else_frame)
            self.blockvisit(node.else_, else_frame)
            self.leave_frame(else_frame)
            self.outdent()

        # if the node was recursive we have to return the buffer contents
        # and start the iteration code
        if node.recursive:
            self.return_buffer_contents(loop_frame)
            self.outdent()
            self.start_write(frame, node)
            self.write(f"{self.choose_async('await ')}loop(")
            if self.environment.is_async:
                self.write("auto_aiter(")
            self.visit(node.iter, frame)
            if self.environment.is_async:
                self.write(")")
            self.write(", loop)")
            self.end_write(frame)

        # at the end of the iteration, clear any assignments made in the
        # loop from the top level
        if self._assign_stack:
            self._assign_stack[-1].difference_update(loop_frame.symbols.stores)

    def visit_If(self, node: nodes.If, frame: Frame) -> None:
        if_frame = frame.soft()
        self.writeline("if ", node)
        self.visit(node.test, if_frame)
        self.write(":")
        self.indent()
        self.blockvisit(node.body, if_frame)
        self.outdent()
        for elif_ in node.elif_:
            self.writeline("elif ", elif_)
            self.visit(elif_.test, if_frame)
            self.write(":")
            self.indent()
            self.blockvisit(elif_.body, if_frame)
            self.outdent()
        if node.else_:
            self.writeline("else:")
            self.indent()
            self.blockvisit(node.else_, if_frame)
            self.outdent()

    def visit_Macro(self, node: nodes.Macro, frame: Frame) -> None:
        macro_frame, macro_ref = self.macro_body(node, frame)
        self.newline()
        if frame.toplevel:
            if not node.name.startswith("_"):
                self.write(f"context.exported_vars.add({node.name!r})")
            self.writeline(f"context.vars[{node.name!r}] = ")
        self.write(f"{frame.symbols.ref(node.name)} = ")
        self.macro_def(macro_ref, macro_frame)

    def visit_CallBlock(self, node: nodes.CallBlock, frame: Frame) -> None:
        call_frame, macro_ref = self.macro_body(node, frame)
        self.writeline("caller = ")
        self.macro_def(macro_ref, call_frame)
        self.start_write(frame, node)
        self.visit_Call(node.call, frame, forward_caller=True)
        self.end_write(frame)

    def visit_FilterBlock(self, node: nodes.FilterBlock, frame: Frame) -> None:
        filter_frame = frame.inner()
        filter_frame.symbols.analyze_node(node)
        self.enter_frame(filter_frame)
        self.buffer(filter_frame)
        self.blockvisit(node.body, filter_frame)
        self.start_write(frame, node)
        self.visit_Filter(node.filter, filter_frame)
        self.end_write(frame)
        self.leave_frame(filter_frame)

    def visit_With(self, node: nodes.With, frame: Frame) -> None:
        with_frame = frame.inner()
        with_frame.symbols.analyze_node(node)
        self.enter_frame(with_frame)
        for target, expr in zip(node.targets, node.values):
            self.newline()
            self.visit(target, with_frame)
            self.write(" = ")
            self.visit(expr, frame)
        self.blockvisit(node.body, with_frame)
        self.leave_frame(with_frame)

    def visit_ExprStmt(self, node: nodes.ExprStmt, frame: Frame) -> None:
        self.newline(node)
        self.visit(node.node, frame)

    class _FinalizeInfo(t.NamedTuple):
        const: t.Optional[t.Callable[..., str]]
        src: t.Optional[str]

    @staticmethod
    def _default_finalize(value: t.Any) -> t.Any:
        """The default finalize function if the environment isn't
        configured with one. Or, if the environment has one, this is
        called on that function's output for constants.
        """
        return str(value)

    _finalize: t.Optional[_FinalizeInfo] = None

    def _make_finalize(self) -> _FinalizeInfo:
        """Build the finalize function to be used on constants and at
        runtime. Cached so it's only created once for all output nodes.

        Returns a ``namedtuple`` with the following attributes:

        ``const``
            A function to finalize constant data at compile time.

        ``src``
            Source code to output around nodes to be evaluated at
            runtime.
        """
        if self._finalize is not None:
            return self._finalize

        finalize: t.Optional[t.Callable[..., t.Any]]
        finalize = default = self._default_finalize
        src = None

        if self.environment.finalize:
            src = "environment.finalize("
            env_finalize = self.environment.finalize
            pass_arg = {
                _PassArg.context: "context",
                _PassArg.eval_context: "context.eval_ctx",
                _PassArg.environment: "environment",
            }.get(
                _PassArg.from_obj(env_finalize)  # type: ignore
            )
            finalize = None

            if pass_arg is None:

                def finalize(value: t.Any) -> t.Any:  # noqa: F811
                    return default(env_finalize(value))

            else:
                src = f"{src}{pass_arg}, "

                if pass_arg == "environment":

                    def finalize(value: t.Any) -> t.Any:  # noqa: F811
                        return default(env_finalize(self.environment, value))

        self._finalize = self._FinalizeInfo(finalize, src)
        return self._finalize

    def _output_const_repr(self, group: t.Iterable[t.Any]) -> str:
        """Given a group of constant values converted from ``Output``
        child nodes, produce a string to write to the template module
        source.
        """
        return repr(concat(group))

    def _output_child_to_const(
        self, node: nodes.Expr, frame: Frame, finalize: _FinalizeInfo
    ) -> str:
        """Try to optimize a child of an ``Output`` node by trying to
        convert it to constant, finalized data at compile time.

        If :exc:`Impossible` is raised, the node is not constant and
        will be evaluated at runtime. Any other exception will also be
        evaluated at runtime for easier debugging.
        """
        const = node.as_const(frame.eval_ctx)

        if frame.eval_ctx.autoescape:
            const = escape(const)

        # Template data doesn't go through finalize.
        if isinstance(node, nodes.TemplateData):
            return str(const)

        return finalize.const(const)  # type: ignore

    def _output_child_pre(
        self, node: nodes.Expr, frame: Frame, finalize: _FinalizeInfo
    ) -> None:
        """Output extra source code before visiting a child of an
        ``Output`` node.
        """
        if frame.eval_ctx.volatile:
            self.write("(escape if context.eval_ctx.autoescape else str)(")
        elif frame.eval_ctx.autoescape:
            self.write("escape(")
        else:
            self.write("str(")

        if finalize.src is not None:
            self.write(finalize.src)

    def _output_child_post(
        self, node: nodes.Expr, frame: Frame, finalize: _FinalizeInfo
    ) -> None:
        """Output extra source code after visiting a child of an
        ``Output`` node.
        """
        self.write(")")

        if finalize.src is not None:
            self.write(")")

    def visit_Output(self, node: nodes.Output, frame: Frame) -> None:
        # If an extends is active, don't render outside a block.
        if frame.require_output_check:
            # A top-level extends is known to exist at compile time.
            if self.has_known_extends:
                return

            self.writeline("if parent_template is None:")
            self.indent()

        finalize = self._make_finalize()
        body: t.List[t.Union[t.List[t.Any], nodes.Expr]] = []

        # Evaluate constants at compile time if possible. Each item in
        # body will be either a list of static data or a node to be
        # evaluated at runtime.
        for child in node.nodes:
            try:
                if not (
                    # If the finalize function requires runtime context,
                    # constants can't be evaluated at compile time.
                    finalize.const
                    # Unless it's basic template data that won't be
                    # finalized anyway.
                    or isinstance(child, nodes.TemplateData)
                ):
                    raise nodes.Impossible()

                const = self._output_child_to_const(child, frame, finalize)
            except (nodes.Impossible, Exception):
                # The node was not constant and needs to be evaluated at
                # runtime. Or another error was raised, which is easier
                # to debug at runtime.
                body.append(child)
                continue

            if body and isinstance(body[-1], list):
                body[-1].append(const)
            else:
                body.append([const])

        if frame.buffer is not None:
            if len(body) == 1:
                self.writeline(f"{frame.buffer}.append(")
            else:
                self.writeline(f"{frame.buffer}.extend((")

            self.indent()

        for item in body:
            if isinstance(item, list):
                # A group of constant data to join and output.
                val = self._output_const_repr(item)

                if frame.buffer is None:
                    self.writeline("yield " + val)
                else:
                    self.writeline(val + ",")
            else:
                if frame.buffer is None:
                    self.writeline("yield ", item)
                else:
                    self.newline(item)

                # A node to be evaluated at runtime.
                self._output_child_pre(item, frame, finalize)
                self.visit(item, frame)
                self._output_child_post(item, frame, finalize)

                if frame.buffer is not None:
                    self.write(",")

        if frame.buffer is not None:
            self.outdent()
            self.writeline(")" if len(body) == 1 else "))")

        if frame.require_output_check:
            self.outdent()

    def visit_Assign(self, node: nodes.Assign, frame: Frame) -> None:
        self.push_assign_tracking()

        # ``a.b`` is allowed for assignment, and is parsed as an NSRef. However,
        # it is only valid if it references a Namespace object. Emit a check for
        # that for each ref here, before assignment code is emitted. This can't
        # be done in visit_NSRef as the ref could be in the middle of a tuple.
        seen_refs: t.Set[str] = set()

        for nsref in node.find_all(nodes.NSRef):
            if nsref.name in seen_refs:
                # Only emit the check for each reference once, in case the same
                # ref is used multiple times in a tuple, `ns.a, ns.b = c, d`.
                continue

            seen_refs.add(nsref.name)
            ref = frame.symbols.ref(nsref.name)
            self.writeline(f"if not isinstance({ref}, Namespace):")
            self.indent()
            self.writeline(
                "raise TemplateRuntimeError"
                '("cannot assign attribute on non-namespace object")'
            )
            self.outdent()

        self.newline(node)
        self.visit(node.target, frame)
        self.write(" = ")
        self.visit(node.node, frame)
        self.pop_assign_tracking(frame)

    def visit_AssignBlock(self, node: nodes.AssignBlock, frame: Frame) -> None:
        self.push_assign_tracking()
        block_frame = frame.inner()
        # This is a special case.  Since a set block always captures we
        # will disable output checks.  This way one can use set blocks
        # toplevel even in extended templates.
        block_frame.require_output_check = False
        block_frame.symbols.analyze_node(node)
        self.enter_frame(block_frame)
        self.buffer(block_frame)
        self.blockvisit(node.body, block_frame)
        self.newline(node)
        self.visit(node.target, frame)
        self.write(" = (Markup if context.eval_ctx.autoescape else identity)(")
        if node.filter is not None:
            self.visit_Filter(node.filter, block_frame)
        else:
            self.write(f"concat({block_frame.buffer})")
        self.write(")")
        self.pop_assign_tracking(frame)
        self.leave_frame(block_frame)

    # -- Expression Visitors

    def visit_Name(self, node: nodes.Name, frame: Frame) -> None:
        if node.ctx == "store" and (
            frame.toplevel or frame.loop_frame or frame.block_frame
        ):
            if self._assign_stack:
                self._assign_stack[-1].add(node.name)
        ref = frame.symbols.ref(node.name)

        # If we are looking up a variable we might have to deal with the
        # case where it's undefined.  We can skip that case if the load
        # instruction indicates a parameter which are always defined.
        if node.ctx == "load":
            load = frame.symbols.find_load(ref)
            if not (
                load is not None
                and load[0] == VAR_LOAD_PARAMETER
                and not self.parameter_is_undeclared(ref)
            ):
                self.write(
                    f"(undefined(name={node.name!r}) if {ref} is missing else {ref})"
                )
                return

        self.write(ref)

    def visit_NSRef(self, node: nodes.NSRef, frame: Frame) -> None:
        # NSRef is a dotted assignment target a.b=c, but uses a[b]=c internally.
        # visit_Assign emits code to validate that each ref is to a Namespace
        # object only. That can't be emitted here as the ref could be in the
        # middle of a tuple assignment.
        ref = frame.symbols.ref(node.name)
        self.writeline(f"{ref}[{node.attr!r}]")

    def visit_Const(self, node: nodes.Const, frame: Frame) -> None:
        val = node.as_const(frame.eval_ctx)
        if isinstance(val, float):
            self.write(str(val))
        else:
            self.write(repr(val))

    def visit_TemplateData(self, node: nodes.TemplateData, frame: Frame) -> None:
        try:
            self.write(repr(node.as_const(frame.eval_ctx)))
        except nodes.Impossible:
            self.write(
                f"(Markup if context.eval_ctx.autoescape else identity)({node.data!r})"
            )

    def visit_Tuple(self, node: nodes.Tuple, frame: Frame) -> None:
        self.write("(")
        idx = -1
        for idx, item in enumerate(node.items):
            if idx:
                self.write(", ")
            self.visit(item, frame)
        self.write(",)" if idx == 0 else ")")

    def visit_List(self, node: nodes.List, frame: Frame) -> None:
        self.write("[")
        for idx, item in enumerate(node.items):
            if idx:
                self.write(", ")
            self.visit(item, frame)
        self.write("]")

    def visit_Dict(self, node: nodes.Dict, frame: Frame) -> None:
        self.write("{")
        for idx, item in enumerate(node.items):
            if idx:
                self.write(", ")
            self.visit(item.key, frame)
            self.write(": ")
            self.visit(item.value, frame)
        self.write("}")

    visit_Add = _make_binop("+")
    visit_Sub = _make_binop("-")
    visit_Mul = _make_binop("*")
    visit_Div = _make_binop("/")
    visit_FloorDiv = _make_binop("//")
    visit_Pow = _make_binop("**")
    visit_Mod = _make_binop("%")
    visit_And = _make_binop("and")
    visit_Or = _make_binop("or")
    visit_Pos = _make_unop("+")
    visit_Neg = _make_unop("-")
    visit_Not = _make_unop("not ")

    @optimizeconst
    def visit_Concat(self, node: nodes.Concat, frame: Frame) -> None:
        if frame.eval_ctx.volatile:
            func_name = "(markup_join if context.eval_ctx.volatile else str_join)"
        elif frame.eval_ctx.autoescape:
            func_name = "markup_join"
        else:
            func_name = "str_join"
        self.write(f"{func_name}((")
        for arg in node.nodes:
            self.visit(arg, frame)
            self.write(", ")
        self.write("))")

    @optimizeconst
    def visit_Compare(self, node: nodes.Compare, frame: Frame) -> None:
        self.write("(")
        self.visit(node.expr, frame)
        for op in node.ops:
            self.visit(op, frame)
        self.write(")")

    def visit_Operand(self, node: nodes.Operand, frame: Frame) -> None:
        self.write(f" {operators[node.op]} ")
        self.visit(node.expr, frame)

    @optimizeconst
    def visit_Getattr(self, node: nodes.Getattr, frame: Frame) -> None:
        if self.environment.is_async:
            self.write("(await auto_await(")

        self.write("environment.getattr(")
        self.visit(node.node, frame)
        self.write(f", {node.attr!r})")

        if self.environment.is_async:
            self.write("))")

    @optimizeconst
    def visit_Getitem(self, node: nodes.Getitem, frame: Frame) -> None:
        # slices bypass the environment getitem method.
        if isinstance(node.arg, nodes.Slice):
            self.visit(node.node, frame)
            self.write("[")
            self.visit(node.arg, frame)
            self.write("]")
        else:
            if self.environment.is_async:
                self.write("(await auto_await(")

            self.write("environment.getitem(")
            self.visit(node.node, frame)
            self.write(", ")
            self.visit(node.arg, frame)
            self.write(")")

            if self.environment.is_async:
                self.write("))")

    def visit_Slice(self, node: nodes.Slice, frame: Frame) -> None:
        if node.start is not None:
            self.visit(node.start, frame)
        self.write(":")
        if node.stop is not None:
            self.visit(node.stop, frame)
        if node.step is not None:
            self.write(":")
            self.visit(node.step, frame)

    @contextmanager
    def _filter_test_common(
        self, node: t.Union[nodes.Filter, nodes.Test], frame: Frame, is_filter: bool
    ) -> t.Iterator[None]:
        if self.environment.is_async:
            self.write("(await auto_await(")

        if is_filter:
            self.write(f"{self.filters[node.name]}(")
            func = self.environment.filters.get(node.name)
        else:
            self.write(f"{self.tests[node.name]}(")
            func = self.environment.tests.get(node.name)

        # When inside an If or CondExpr frame, allow the filter to be
        # undefined at compile time and only raise an error if it's
        # actually called at runtime. See pull_dependencies.
        if func is None and not frame.soft_frame:
            type_name = "filter" if is_filter else "test"
            self.fail(f"No {type_name} named {node.name!r}.", node.lineno)

        pass_arg = {
            _PassArg.context: "context",
            _PassArg.eval_context: "context.eval_ctx",
            _PassArg.environment: "environment",
        }.get(
            _PassArg.from_obj(func)  # type: ignore
        )

        if pass_arg is not None:
            self.write(f"{pass_arg}, ")

        # Back to the visitor function to handle visiting the target of
        # the filter or test.
        yield

        self.signature(node, frame)
        self.write(")")

        if self.environment.is_async:
            self.write("))")

    @optimizeconst
    def visit_Filter(self, node: nodes.Filter, frame: Frame) -> None:
        with self._filter_test_common(node, frame, True):
            # if the filter node is None we are inside a filter block
            # and want to write to the current buffer
            if node.node is not None:
                self.visit(node.node, frame)
            elif frame.eval_ctx.volatile:
                self.write(
                    f"(Markup(concat({frame.buffer}))"
                    f" if context.eval_ctx.autoescape else concat({frame.buffer}))"
                )
            elif frame.eval_ctx.autoescape:
                self.write(f"Markup(concat({frame.buffer}))")
            else:
                self.write(f"concat({frame.buffer})")

    @optimizeconst
    def visit_Test(self, node: nodes.Test, frame: Frame) -> None:
        with self._filter_test_common(node, frame, False):
            self.visit(node.node, frame)

    @optimizeconst
    def visit_CondExpr(self, node: nodes.CondExpr, frame: Frame) -> None:
        frame = frame.soft()

        def write_expr2() -> None:
            if node.expr2 is not None:
                self.visit(node.expr2, frame)
                return

            self.write(
                f'cond_expr_undefined("the inline if-expression on'
                f" {self.position(node)} evaluated to false and no else"
                f' section was defined.")'
            )

        self.write("(")
        self.visit(node.expr1, frame)
        self.write(" if ")
        self.visit(node.test, frame)
        self.write(" else ")
        write_expr2()
        self.write(")")

    @optimizeconst
    def visit_Call(
        self, node: nodes.Call, frame: Frame, forward_caller: bool = False
    ) -> None:
        if self.environment.is_async:
            self.write("(await auto_await(")
        if self.environment.sandboxed:
            self.write("environment.call(context, ")
        else:
            self.write("context.call(")
        self.visit(node.node, frame)
        extra_kwargs = {"caller": "caller"} if forward_caller else None
        loop_kwargs = {"_loop_vars": "_loop_vars"} if frame.loop_frame else {}
        block_kwargs = {"_block_vars": "_block_vars"} if frame.block_frame else {}
        if extra_kwargs:
            extra_kwargs.update(loop_kwargs, **block_kwargs)
        elif loop_kwargs or block_kwargs:
            extra_kwargs = dict(loop_kwargs, **block_kwargs)
        self.signature(node, frame, extra_kwargs)
        self.write(")")
        if self.environment.is_async:
            self.write("))")

    def visit_Keyword(self, node: nodes.Keyword, frame: Frame) -> None:
        self.write(node.key + "=")
        self.visit(node.value, frame)

    # -- Unused nodes for extensions

    def visit_MarkSafe(self, node: nodes.MarkSafe, frame: Frame) -> None:
        self.write("Markup(")
        self.visit(node.expr, frame)
        self.write(")")

    def visit_MarkSafeIfAutoescape(
        self, node: nodes.MarkSafeIfAutoescape, frame: Frame
    ) -> None:
        self.write("(Markup if context.eval_ctx.autoescape else identity)(")
        self.visit(node.expr, frame)
        self.write(")")

    def visit_EnvironmentAttribute(
        self, node: nodes.EnvironmentAttribute, frame: Frame
    ) -> None:
        self.write("environment." + node.name)

    def visit_ExtensionAttribute(
        self, node: nodes.ExtensionAttribute, frame: Frame
    ) -> None:
        self.write(f"environment.extensions[{node.identifier!r}].{node.name}")

    def visit_ImportedName(self, node: nodes.ImportedName, frame: Frame) -> None:
        self.write(self.import_aliases[node.importname])

    def visit_InternalName(self, node: nodes.InternalName, frame: Frame) -> None:
        self.write(node.name)

    def visit_ContextReference(
        self, node: nodes.ContextReference, frame: Frame
    ) -> None:
        self.write("context")

    def visit_DerivedContextReference(
        self, node: nodes.DerivedContextReference, frame: Frame
    ) -> None:
        self.write(self.derive_context(frame))

    def visit_Continue(self, node: nodes.Continue, frame: Frame) -> None:
        self.writeline("continue", node)

    def visit_Break(self, node: nodes.Break, frame: Frame) -> None:
        self.writeline("break", node)

    def visit_Scope(self, node: nodes.Scope, frame: Frame) -> None:
        scope_frame = frame.inner()
        scope_frame.symbols.analyze_node(node)
        self.enter_frame(scope_frame)
        self.blockvisit(node.body, scope_frame)
        self.leave_frame(scope_frame)

    def visit_OverlayScope(self, node: nodes.OverlayScope, frame: Frame) -> None:
        ctx = self.temporary_identifier()
        self.writeline(f"{ctx} = {self.derive_context(frame)}")
        self.writeline(f"{ctx}.vars = ")
        self.visit(node.context, frame)
        self.push_context_reference(ctx)

        scope_frame = frame.inner(isolated=True)
        scope_frame.symbols.analyze_node(node)
        self.enter_frame(scope_frame)
        self.blockvisit(node.body, scope_frame)
        self.leave_frame(scope_frame)
        self.pop_context_reference()

    def visit_EvalContextModifier(
        self, node: nodes.EvalContextModifier, frame: Frame
    ) -> None:
        for keyword in node.options:
            self.writeline(f"context.eval_ctx.{keyword.key} = ")
            self.visit(keyword.value, frame)
            try:
                val = keyword.value.as_const(frame.eval_ctx)
            except nodes.Impossible:
                frame.eval_ctx.volatile = True
            else:
                setattr(frame.eval_ctx, keyword.key, val)

    def visit_ScopedEvalContextModifier(
        self, node: nodes.ScopedEvalContextModifier, frame: Frame
    ) -> None:
        old_ctx_name = self.temporary_identifier()
        saved_ctx = frame.eval_ctx.save()
        self.writeline(f"{old_ctx_name} = context.eval_ctx.save()")
        self.visit_EvalContextModifier(node, frame)
        for child in node.body:
            self.visit(child, frame)
        frame.eval_ctx.revert(saved_ctx)
        self.writeline(f"context.eval_ctx.revert({old_ctx_name})")

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\distlib\util.py ===
#
# Copyright (C) 2012-2023 The Python Software Foundation.
# See LICENSE.txt and CONTRIBUTORS.txt.
#
import codecs
from collections import deque
import contextlib
import csv
from glob import iglob as std_iglob
import io
import json
import logging
import os
import py_compile
import re
import socket
try:
    import ssl
except ImportError:  # pragma: no cover
    ssl = None
import subprocess
import sys
import tarfile
import tempfile
import textwrap

try:
    import threading
except ImportError:  # pragma: no cover
    import dummy_threading as threading
import time

from . import DistlibException
from .compat import (string_types, text_type, shutil, raw_input, StringIO, cache_from_source, urlopen, urljoin, httplib,
                     xmlrpclib, HTTPHandler, BaseConfigurator, valid_ident, Container, configparser, URLError, ZipFile,
                     fsdecode, unquote, urlparse)

logger = logging.getLogger(__name__)

#
# Requirement parsing code as per PEP 508
#

IDENTIFIER = re.compile(r'^([\w\.-]+)\s*')
VERSION_IDENTIFIER = re.compile(r'^([\w\.*+-]+)\s*')
COMPARE_OP = re.compile(r'^(<=?|>=?|={2,3}|[~!]=)\s*')
MARKER_OP = re.compile(r'^((<=?)|(>=?)|={2,3}|[~!]=|in|not\s+in)\s*')
OR = re.compile(r'^or\b\s*')
AND = re.compile(r'^and\b\s*')
NON_SPACE = re.compile(r'(\S+)\s*')
STRING_CHUNK = re.compile(r'([\s\w\.{}()*+#:;,/?!~`@$%^&=|<>\[\]-]+)')


def parse_marker(marker_string):
    """
    Parse a marker string and return a dictionary containing a marker expression.

    The dictionary will contain keys "op", "lhs" and "rhs" for non-terminals in
    the expression grammar, or strings. A string contained in quotes is to be
    interpreted as a literal string, and a string not contained in quotes is a
    variable (such as os_name).
    """

    def marker_var(remaining):
        # either identifier, or literal string
        m = IDENTIFIER.match(remaining)
        if m:
            result = m.groups()[0]
            remaining = remaining[m.end():]
        elif not remaining:
            raise SyntaxError('unexpected end of input')
        else:
            q = remaining[0]
            if q not in '\'"':
                raise SyntaxError('invalid expression: %s' % remaining)
            oq = '\'"'.replace(q, '')
            remaining = remaining[1:]
            parts = [q]
            while remaining:
                # either a string chunk, or oq, or q to terminate
                if remaining[0] == q:
                    break
                elif remaining[0] == oq:
                    parts.append(oq)
                    remaining = remaining[1:]
                else:
                    m = STRING_CHUNK.match(remaining)
                    if not m:
                        raise SyntaxError('error in string literal: %s' % remaining)
                    parts.append(m.groups()[0])
                    remaining = remaining[m.end():]
            else:
                s = ''.join(parts)
                raise SyntaxError('unterminated string: %s' % s)
            parts.append(q)
            result = ''.join(parts)
            remaining = remaining[1:].lstrip()  # skip past closing quote
        return result, remaining

    def marker_expr(remaining):
        if remaining and remaining[0] == '(':
            result, remaining = marker(remaining[1:].lstrip())
            if remaining[0] != ')':
                raise SyntaxError('unterminated parenthesis: %s' % remaining)
            remaining = remaining[1:].lstrip()
        else:
            lhs, remaining = marker_var(remaining)
            while remaining:
                m = MARKER_OP.match(remaining)
                if not m:
                    break
                op = m.groups()[0]
                remaining = remaining[m.end():]
                rhs, remaining = marker_var(remaining)
                lhs = {'op': op, 'lhs': lhs, 'rhs': rhs}
            result = lhs
        return result, remaining

    def marker_and(remaining):
        lhs, remaining = marker_expr(remaining)
        while remaining:
            m = AND.match(remaining)
            if not m:
                break
            remaining = remaining[m.end():]
            rhs, remaining = marker_expr(remaining)
            lhs = {'op': 'and', 'lhs': lhs, 'rhs': rhs}
        return lhs, remaining

    def marker(remaining):
        lhs, remaining = marker_and(remaining)
        while remaining:
            m = OR.match(remaining)
            if not m:
                break
            remaining = remaining[m.end():]
            rhs, remaining = marker_and(remaining)
            lhs = {'op': 'or', 'lhs': lhs, 'rhs': rhs}
        return lhs, remaining

    return marker(marker_string)


def parse_requirement(req):
    """
    Parse a requirement passed in as a string. Return a Container
    whose attributes contain the various parts of the requirement.
    """
    remaining = req.strip()
    if not remaining or remaining.startswith('#'):
        return None
    m = IDENTIFIER.match(remaining)
    if not m:
        raise SyntaxError('name expected: %s' % remaining)
    distname = m.groups()[0]
    remaining = remaining[m.end():]
    extras = mark_expr = versions = uri = None
    if remaining and remaining[0] == '[':
        i = remaining.find(']', 1)
        if i < 0:
            raise SyntaxError('unterminated extra: %s' % remaining)
        s = remaining[1:i]
        remaining = remaining[i + 1:].lstrip()
        extras = []
        while s:
            m = IDENTIFIER.match(s)
            if not m:
                raise SyntaxError('malformed extra: %s' % s)
            extras.append(m.groups()[0])
            s = s[m.end():]
            if not s:
                break
            if s[0] != ',':
                raise SyntaxError('comma expected in extras: %s' % s)
            s = s[1:].lstrip()
        if not extras:
            extras = None
    if remaining:
        if remaining[0] == '@':
            # it's a URI
            remaining = remaining[1:].lstrip()
            m = NON_SPACE.match(remaining)
            if not m:
                raise SyntaxError('invalid URI: %s' % remaining)
            uri = m.groups()[0]
            t = urlparse(uri)
            # there are issues with Python and URL parsing, so this test
            # is a bit crude. See bpo-20271, bpo-23505. Python doesn't
            # always parse invalid URLs correctly - it should raise
            # exceptions for malformed URLs
            if not (t.scheme and t.netloc):
                raise SyntaxError('Invalid URL: %s' % uri)
            remaining = remaining[m.end():].lstrip()
        else:

            def get_versions(ver_remaining):
                """
                Return a list of operator, version tuples if any are
                specified, else None.
                """
                m = COMPARE_OP.match(ver_remaining)
                versions = None
                if m:
                    versions = []
                    while True:
                        op = m.groups()[0]
                        ver_remaining = ver_remaining[m.end():]
                        m = VERSION_IDENTIFIER.match(ver_remaining)
                        if not m:
                            raise SyntaxError('invalid version: %s' % ver_remaining)
                        v = m.groups()[0]
                        versions.append((op, v))
                        ver_remaining = ver_remaining[m.end():]
                        if not ver_remaining or ver_remaining[0] != ',':
                            break
                        ver_remaining = ver_remaining[1:].lstrip()
                        # Some packages have a trailing comma which would break things
                        # See issue #148
                        if not ver_remaining:
                            break
                        m = COMPARE_OP.match(ver_remaining)
                        if not m:
                            raise SyntaxError('invalid constraint: %s' % ver_remaining)
                    if not versions:
                        versions = None
                return versions, ver_remaining

            if remaining[0] != '(':
                versions, remaining = get_versions(remaining)
            else:
                i = remaining.find(')', 1)
                if i < 0:
                    raise SyntaxError('unterminated parenthesis: %s' % remaining)
                s = remaining[1:i]
                remaining = remaining[i + 1:].lstrip()
                # As a special diversion from PEP 508, allow a version number
                # a.b.c in parentheses as a synonym for ~= a.b.c (because this
                # is allowed in earlier PEPs)
                if COMPARE_OP.match(s):
                    versions, _ = get_versions(s)
                else:
                    m = VERSION_IDENTIFIER.match(s)
                    if not m:
                        raise SyntaxError('invalid constraint: %s' % s)
                    v = m.groups()[0]
                    s = s[m.end():].lstrip()
                    if s:
                        raise SyntaxError('invalid constraint: %s' % s)
                    versions = [('~=', v)]

    if remaining:
        if remaining[0] != ';':
            raise SyntaxError('invalid requirement: %s' % remaining)
        remaining = remaining[1:].lstrip()

        mark_expr, remaining = parse_marker(remaining)

    if remaining and remaining[0] != '#':
        raise SyntaxError('unexpected trailing data: %s' % remaining)

    if not versions:
        rs = distname
    else:
        rs = '%s %s' % (distname, ', '.join(['%s %s' % con for con in versions]))
    return Container(name=distname, extras=extras, constraints=versions, marker=mark_expr, url=uri, requirement=rs)


def get_resources_dests(resources_root, rules):
    """Find destinations for resources files"""

    def get_rel_path(root, path):
        # normalizes and returns a lstripped-/-separated path
        root = root.replace(os.path.sep, '/')
        path = path.replace(os.path.sep, '/')
        assert path.startswith(root)
        return path[len(root):].lstrip('/')

    destinations = {}
    for base, suffix, dest in rules:
        prefix = os.path.join(resources_root, base)
        for abs_base in iglob(prefix):
            abs_glob = os.path.join(abs_base, suffix)
            for abs_path in iglob(abs_glob):
                resource_file = get_rel_path(resources_root, abs_path)
                if dest is None:  # remove the entry if it was here
                    destinations.pop(resource_file, None)
                else:
                    rel_path = get_rel_path(abs_base, abs_path)
                    rel_dest = dest.replace(os.path.sep, '/').rstrip('/')
                    destinations[resource_file] = rel_dest + '/' + rel_path
    return destinations


def in_venv():
    if hasattr(sys, 'real_prefix'):
        # virtualenv venvs
        result = True
    else:
        # PEP 405 venvs
        result = sys.prefix != getattr(sys, 'base_prefix', sys.prefix)
    return result


def get_executable():
    # The __PYVENV_LAUNCHER__ dance is apparently no longer needed, as
    # changes to the stub launcher mean that sys.executable always points
    # to the stub on OS X
    #    if sys.platform == 'darwin' and ('__PYVENV_LAUNCHER__'
    #                                     in os.environ):
    #        result =  os.environ['__PYVENV_LAUNCHER__']
    #    else:
    #        result = sys.executable
    #    return result
    # Avoid normcasing: see issue #143
    # result = os.path.normcase(sys.executable)
    result = sys.executable
    if not isinstance(result, text_type):
        result = fsdecode(result)
    return result


def proceed(prompt, allowed_chars, error_prompt=None, default=None):
    p = prompt
    while True:
        s = raw_input(p)
        p = prompt
        if not s and default:
            s = default
        if s:
            c = s[0].lower()
            if c in allowed_chars:
                break
            if error_prompt:
                p = '%c: %s\n%s' % (c, error_prompt, prompt)
    return c


def extract_by_key(d, keys):
    if isinstance(keys, string_types):
        keys = keys.split()
    result = {}
    for key in keys:
        if key in d:
            result[key] = d[key]
    return result


def read_exports(stream):
    if sys.version_info[0] >= 3:
        # needs to be a text stream
        stream = codecs.getreader('utf-8')(stream)
    # Try to load as JSON, falling back on legacy format
    data = stream.read()
    stream = StringIO(data)
    try:
        jdata = json.load(stream)
        result = jdata['extensions']['python.exports']['exports']
        for group, entries in result.items():
            for k, v in entries.items():
                s = '%s = %s' % (k, v)
                entry = get_export_entry(s)
                assert entry is not None
                entries[k] = entry
        return result
    except Exception:
        stream.seek(0, 0)

    def read_stream(cp, stream):
        if hasattr(cp, 'read_file'):
            cp.read_file(stream)
        else:
            cp.readfp(stream)

    cp = configparser.ConfigParser()
    try:
        read_stream(cp, stream)
    except configparser.MissingSectionHeaderError:
        stream.close()
        data = textwrap.dedent(data)
        stream = StringIO(data)
        read_stream(cp, stream)

    result = {}
    for key in cp.sections():
        result[key] = entries = {}
        for name, value in cp.items(key):
            s = '%s = %s' % (name, value)
            entry = get_export_entry(s)
            assert entry is not None
            # entry.dist = self
            entries[name] = entry
    return result


def write_exports(exports, stream):
    if sys.version_info[0] >= 3:
        # needs to be a text stream
        stream = codecs.getwriter('utf-8')(stream)
    cp = configparser.ConfigParser()
    for k, v in exports.items():
        # TODO check k, v for valid values
        cp.add_section(k)
        for entry in v.values():
            if entry.suffix is None:
                s = entry.prefix
            else:
                s = '%s:%s' % (entry.prefix, entry.suffix)
            if entry.flags:
                s = '%s [%s]' % (s, ', '.join(entry.flags))
            cp.set(k, entry.name, s)
    cp.write(stream)


@contextlib.contextmanager
def tempdir():
    td = tempfile.mkdtemp()
    try:
        yield td
    finally:
        shutil.rmtree(td)


@contextlib.contextmanager
def chdir(d):
    cwd = os.getcwd()
    try:
        os.chdir(d)
        yield
    finally:
        os.chdir(cwd)


@contextlib.contextmanager
def socket_timeout(seconds=15):
    cto = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(seconds)
        yield
    finally:
        socket.setdefaulttimeout(cto)


class cached_property(object):

    def __init__(self, func):
        self.func = func
        # for attr in ('__name__', '__module__', '__doc__'):
        #     setattr(self, attr, getattr(func, attr, None))

    def __get__(self, obj, cls=None):
        if obj is None:
            return self
        value = self.func(obj)
        object.__setattr__(obj, self.func.__name__, value)
        # obj.__dict__[self.func.__name__] = value = self.func(obj)
        return value


def convert_path(pathname):
    """Return 'pathname' as a name that will work on the native filesystem.

    The path is split on '/' and put back together again using the current
    directory separator.  Needed because filenames in the setup script are
    always supplied in Unix style, and have to be converted to the local
    convention before we can actually use them in the filesystem.  Raises
    ValueError on non-Unix-ish systems if 'pathname' either starts or
    ends with a slash.
    """
    if os.sep == '/':
        return pathname
    if not pathname:
        return pathname
    if pathname[0] == '/':
        raise ValueError("path '%s' cannot be absolute" % pathname)
    if pathname[-1] == '/':
        raise ValueError("path '%s' cannot end with '/'" % pathname)

    paths = pathname.split('/')
    while os.curdir in paths:
        paths.remove(os.curdir)
    if not paths:
        return os.curdir
    return os.path.join(*paths)


class FileOperator(object):

    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.ensured = set()
        self._init_record()

    def _init_record(self):
        self.record = False
        self.files_written = set()
        self.dirs_created = set()

    def record_as_written(self, path):
        if self.record:
            self.files_written.add(path)

    def newer(self, source, target):
        """Tell if the target is newer than the source.

        Returns true if 'source' exists and is more recently modified than
        'target', or if 'source' exists and 'target' doesn't.

        Returns false if both exist and 'target' is the same age or younger
        than 'source'. Raise PackagingFileError if 'source' does not exist.

        Note that this test is not very accurate: files created in the same
        second will have the same "age".
        """
        if not os.path.exists(source):
            raise DistlibException("file '%r' does not exist" % os.path.abspath(source))
        if not os.path.exists(target):
            return True

        return os.stat(source).st_mtime > os.stat(target).st_mtime

    def copy_file(self, infile, outfile, check=True):
        """Copy a file respecting dry-run and force flags.
        """
        self.ensure_dir(os.path.dirname(outfile))
        logger.info('Copying %s to %s', infile, outfile)
        if not self.dry_run:
            msg = None
            if check:
                if os.path.islink(outfile):
                    msg = '%s is a symlink' % outfile
                elif os.path.exists(outfile) and not os.path.isfile(outfile):
                    msg = '%s is a non-regular file' % outfile
            if msg:
                raise ValueError(msg + ' which would be overwritten')
            shutil.copyfile(infile, outfile)
        self.record_as_written(outfile)

    def copy_stream(self, instream, outfile, encoding=None):
        assert not os.path.isdir(outfile)
        self.ensure_dir(os.path.dirname(outfile))
        logger.info('Copying stream %s to %s', instream, outfile)
        if not self.dry_run:
            if encoding is None:
                outstream = open(outfile, 'wb')
            else:
                outstream = codecs.open(outfile, 'w', encoding=encoding)
            try:
                shutil.copyfileobj(instream, outstream)
            finally:
                outstream.close()
        self.record_as_written(outfile)

    def write_binary_file(self, path, data):
        self.ensure_dir(os.path.dirname(path))
        if not self.dry_run:
            if os.path.exists(path):
                os.remove(path)
            with open(path, 'wb') as f:
                f.write(data)
        self.record_as_written(path)

    def write_text_file(self, path, data, encoding):
        self.write_binary_file(path, data.encode(encoding))

    def set_mode(self, bits, mask, files):
        if os.name == 'posix' or (os.name == 'java' and os._name == 'posix'):
            # Set the executable bits (owner, group, and world) on
            # all the files specified.
            for f in files:
                if self.dry_run:
                    logger.info("changing mode of %s", f)
                else:
                    mode = (os.stat(f).st_mode | bits) & mask
                    logger.info("changing mode of %s to %o", f, mode)
                    os.chmod(f, mode)

    set_executable_mode = lambda s, f: s.set_mode(0o555, 0o7777, f)

    def ensure_dir(self, path):
        path = os.path.abspath(path)
        if path not in self.ensured and not os.path.exists(path):
            self.ensured.add(path)
            d, f = os.path.split(path)
            self.ensure_dir(d)
            logger.info('Creating %s' % path)
            if not self.dry_run:
                os.mkdir(path)
            if self.record:
                self.dirs_created.add(path)

    def byte_compile(self, path, optimize=False, force=False, prefix=None, hashed_invalidation=False):
        dpath = cache_from_source(path, not optimize)
        logger.info('Byte-compiling %s to %s', path, dpath)
        if not self.dry_run:
            if force or self.newer(path, dpath):
                if not prefix:
                    diagpath = None
                else:
                    assert path.startswith(prefix)
                    diagpath = path[len(prefix):]
            compile_kwargs = {}
            if hashed_invalidation and hasattr(py_compile, 'PycInvalidationMode'):
                if not isinstance(hashed_invalidation, py_compile.PycInvalidationMode):
                    hashed_invalidation = py_compile.PycInvalidationMode.CHECKED_HASH
                compile_kwargs['invalidation_mode'] = hashed_invalidation
            py_compile.compile(path, dpath, diagpath, True, **compile_kwargs)  # raise error
        self.record_as_written(dpath)
        return dpath

    def ensure_removed(self, path):
        if os.path.exists(path):
            if os.path.isdir(path) and not os.path.islink(path):
                logger.debug('Removing directory tree at %s', path)
                if not self.dry_run:
                    shutil.rmtree(path)
                if self.record:
                    if path in self.dirs_created:
                        self.dirs_created.remove(path)
            else:
                if os.path.islink(path):
                    s = 'link'
                else:
                    s = 'file'
                logger.debug('Removing %s %s', s, path)
                if not self.dry_run:
                    os.remove(path)
                if self.record:
                    if path in self.files_written:
                        self.files_written.remove(path)

    def is_writable(self, path):
        result = False
        while not result:
            if os.path.exists(path):
                result = os.access(path, os.W_OK)
                break
            parent = os.path.dirname(path)
            if parent == path:
                break
            path = parent
        return result

    def commit(self):
        """
        Commit recorded changes, turn off recording, return
        changes.
        """
        assert self.record
        result = self.files_written, self.dirs_created
        self._init_record()
        return result

    def rollback(self):
        if not self.dry_run:
            for f in list(self.files_written):
                if os.path.exists(f):
                    os.remove(f)
            # dirs should all be empty now, except perhaps for
            # __pycache__ subdirs
            # reverse so that subdirs appear before their parents
            dirs = sorted(self.dirs_created, reverse=True)
            for d in dirs:
                flist = os.listdir(d)
                if flist:
                    assert flist == ['__pycache__']
                    sd = os.path.join(d, flist[0])
                    os.rmdir(sd)
                os.rmdir(d)  # should fail if non-empty
        self._init_record()


def resolve(module_name, dotted_path):
    if module_name in sys.modules:
        mod = sys.modules[module_name]
    else:
        mod = __import__(module_name)
    if dotted_path is None:
        result = mod
    else:
        parts = dotted_path.split('.')
        result = getattr(mod, parts.pop(0))
        for p in parts:
            result = getattr(result, p)
    return result


class ExportEntry(object):

    def __init__(self, name, prefix, suffix, flags):
        self.name = name
        self.prefix = prefix
        self.suffix = suffix
        self.flags = flags

    @cached_property
    def value(self):
        return resolve(self.prefix, self.suffix)

    def __repr__(self):  # pragma: no cover
        return '<ExportEntry %s = %s:%s %s>' % (self.name, self.prefix, self.suffix, self.flags)

    def __eq__(self, other):
        if not isinstance(other, ExportEntry):
            result = False
        else:
            result = (self.name == other.name and self.prefix == other.prefix and self.suffix == other.suffix and
                      self.flags == other.flags)
        return result

    __hash__ = object.__hash__


ENTRY_RE = re.compile(
    r'''(?P<name>([^\[]\S*))
                      \s*=\s*(?P<callable>(\w+)([:\.]\w+)*)
                      \s*(\[\s*(?P<flags>[\w-]+(=\w+)?(,\s*\w+(=\w+)?)*)\s*\])?
                      ''', re.VERBOSE)


def get_export_entry(specification):
    m = ENTRY_RE.search(specification)
    if not m:
        result = None
        if '[' in specification or ']' in specification:
            raise DistlibException("Invalid specification "
                                   "'%s'" % specification)
    else:
        d = m.groupdict()
        name = d['name']
        path = d['callable']
        colons = path.count(':')
        if colons == 0:
            prefix, suffix = path, None
        else:
            if colons != 1:
                raise DistlibException("Invalid specification "
                                       "'%s'" % specification)
            prefix, suffix = path.split(':')
        flags = d['flags']
        if flags is None:
            if '[' in specification or ']' in specification:
                raise DistlibException("Invalid specification "
                                       "'%s'" % specification)
            flags = []
        else:
            flags = [f.strip() for f in flags.split(',')]
        result = ExportEntry(name, prefix, suffix, flags)
    return result


def get_cache_base(suffix=None):
    """
    Return the default base location for distlib caches. If the directory does
    not exist, it is created. Use the suffix provided for the base directory,
    and default to '.distlib' if it isn't provided.

    On Windows, if LOCALAPPDATA is defined in the environment, then it is
    assumed to be a directory, and will be the parent directory of the result.
    On POSIX, and on Windows if LOCALAPPDATA is not defined, the user's home
    directory - using os.expanduser('~') - will be the parent directory of
    the result.

    The result is just the directory '.distlib' in the parent directory as
    determined above, or with the name specified with ``suffix``.
    """
    if suffix is None:
        suffix = '.distlib'
    if os.name == 'nt' and 'LOCALAPPDATA' in os.environ:
        result = os.path.expandvars('$localappdata')
    else:
        # Assume posix, or old Windows
        result = os.path.expanduser('~')
    # we use 'isdir' instead of 'exists', because we want to
    # fail if there's a file with that name
    if os.path.isdir(result):
        usable = os.access(result, os.W_OK)
        if not usable:
            logger.warning('Directory exists but is not writable: %s', result)
    else:
        try:
            os.makedirs(result)
            usable = True
        except OSError:
            logger.warning('Unable to create %s', result, exc_info=True)
            usable = False
    if not usable:
        result = tempfile.mkdtemp()
        logger.warning('Default location unusable, using %s', result)
    return os.path.join(result, suffix)


def path_to_cache_dir(path, use_abspath=True):
    """
    Convert an absolute path to a directory name for use in a cache.

    The algorithm used is:

    #. On Windows, any ``':'`` in the drive is replaced with ``'---'``.
    #. Any occurrence of ``os.sep`` is replaced with ``'--'``.
    #. ``'.cache'`` is appended.
    """
    d, p = os.path.splitdrive(os.path.abspath(path) if use_abspath else path)
    if d:
        d = d.replace(':', '---')
    p = p.replace(os.sep, '--')
    return d + p + '.cache'


def ensure_slash(s):
    if not s.endswith('/'):
        return s + '/'
    return s


def parse_credentials(netloc):
    username = password = None
    if '@' in netloc:
        prefix, netloc = netloc.rsplit('@', 1)
        if ':' not in prefix:
            username = prefix
        else:
            username, password = prefix.split(':', 1)
    if username:
        username = unquote(username)
    if password:
        password = unquote(password)
    return username, password, netloc


def get_process_umask():
    result = os.umask(0o22)
    os.umask(result)
    return result


def is_string_sequence(seq):
    result = True
    i = None
    for i, s in enumerate(seq):
        if not isinstance(s, string_types):
            result = False
            break
    assert i is not None
    return result


PROJECT_NAME_AND_VERSION = re.compile('([a-z0-9_]+([.-][a-z_][a-z0-9_]*)*)-'
                                      '([a-z0-9_.+-]+)', re.I)
PYTHON_VERSION = re.compile(r'-py(\d\.?\d?)')


def split_filename(filename, project_name=None):
    """
    Extract name, version, python version from a filename (no extension)

    Return name, version, pyver or None
    """
    result = None
    pyver = None
    filename = unquote(filename).replace(' ', '-')
    m = PYTHON_VERSION.search(filename)
    if m:
        pyver = m.group(1)
        filename = filename[:m.start()]
    if project_name and len(filename) > len(project_name) + 1:
        m = re.match(re.escape(project_name) + r'\b', filename)
        if m:
            n = m.end()
            result = filename[:n], filename[n + 1:], pyver
    if result is None:
        m = PROJECT_NAME_AND_VERSION.match(filename)
        if m:
            result = m.group(1), m.group(3), pyver
    return result


# Allow spaces in name because of legacy dists like "Twisted Core"
NAME_VERSION_RE = re.compile(r'(?P<name>[\w .-]+)\s*'
                             r'\(\s*(?P<ver>[^\s)]+)\)$')


def parse_name_and_version(p):
    """
    A utility method used to get name and version from a string.

    From e.g. a Provides-Dist value.

    :param p: A value in a form 'foo (1.0)'
    :return: The name and version as a tuple.
    """
    m = NAME_VERSION_RE.match(p)
    if not m:
        raise DistlibException('Ill-formed name/version string: \'%s\'' % p)
    d = m.groupdict()
    return d['name'].strip().lower(), d['ver']


def get_extras(requested, available):
    result = set()
    requested = set(requested or [])
    available = set(available or [])
    if '*' in requested:
        requested.remove('*')
        result |= available
    for r in requested:
        if r == '-':
            result.add(r)
        elif r.startswith('-'):
            unwanted = r[1:]
            if unwanted not in available:
                logger.warning('undeclared extra: %s' % unwanted)
            if unwanted in result:
                result.remove(unwanted)
        else:
            if r not in available:
                logger.warning('undeclared extra: %s' % r)
            result.add(r)
    return result


#
# Extended metadata functionality
#


def _get_external_data(url):
    result = {}
    try:
        # urlopen might fail if it runs into redirections,
        # because of Python issue #13696. Fixed in locators
        # using a custom redirect handler.
        resp = urlopen(url)
        headers = resp.info()
        ct = headers.get('Content-Type')
        if not ct.startswith('application/json'):
            logger.debug('Unexpected response for JSON request: %s', ct)
        else:
            reader = codecs.getreader('utf-8')(resp)
            # data = reader.read().decode('utf-8')
            # result = json.loads(data)
            result = json.load(reader)
    except Exception as e:
        logger.exception('Failed to get external data for %s: %s', url, e)
    return result


_external_data_base_url = 'https://www.red-dove.com/pypi/projects/'


def get_project_data(name):
    url = '%s/%s/project.json' % (name[0].upper(), name)
    url = urljoin(_external_data_base_url, url)
    result = _get_external_data(url)
    return result


def get_package_data(name, version):
    url = '%s/%s/package-%s.json' % (name[0].upper(), name, version)
    url = urljoin(_external_data_base_url, url)
    return _get_external_data(url)


class Cache(object):
    """
    A class implementing a cache for resources that need to live in the file system
    e.g. shared libraries. This class was moved from resources to here because it
    could be used by other modules, e.g. the wheel module.
    """

    def __init__(self, base):
        """
        Initialise an instance.

        :param base: The base directory where the cache should be located.
        """
        # we use 'isdir' instead of 'exists', because we want to
        # fail if there's a file with that name
        if not os.path.isdir(base):  # pragma: no cover
            os.makedirs(base)
        if (os.stat(base).st_mode & 0o77) != 0:
            logger.warning('Directory \'%s\' is not private', base)
        self.base = os.path.abspath(os.path.normpath(base))

    def prefix_to_dir(self, prefix, use_abspath=True):
        """
        Converts a resource prefix to a directory name in the cache.
        """
        return path_to_cache_dir(prefix, use_abspath=use_abspath)

    def clear(self):
        """
        Clear the cache.
        """
        not_removed = []
        for fn in os.listdir(self.base):
            fn = os.path.join(self.base, fn)
            try:
                if os.path.islink(fn) or os.path.isfile(fn):
                    os.remove(fn)
                elif os.path.isdir(fn):
                    shutil.rmtree(fn)
            except Exception:
                not_removed.append(fn)
        return not_removed


class EventMixin(object):
    """
    A very simple publish/subscribe system.
    """

    def __init__(self):
        self._subscribers = {}

    def add(self, event, subscriber, append=True):
        """
        Add a subscriber for an event.

        :param event: The name of an event.
        :param subscriber: The subscriber to be added (and called when the
                           event is published).
        :param append: Whether to append or prepend the subscriber to an
                       existing subscriber list for the event.
        """
        subs = self._subscribers
        if event not in subs:
            subs[event] = deque([subscriber])
        else:
            sq = subs[event]
            if append:
                sq.append(subscriber)
            else:
                sq.appendleft(subscriber)

    def remove(self, event, subscriber):
        """
        Remove a subscriber for an event.

        :param event: The name of an event.
        :param subscriber: The subscriber to be removed.
        """
        subs = self._subscribers
        if event not in subs:
            raise ValueError('No subscribers: %r' % event)
        subs[event].remove(subscriber)

    def get_subscribers(self, event):
        """
        Return an iterator for the subscribers for an event.
        :param event: The event to return subscribers for.
        """
        return iter(self._subscribers.get(event, ()))

    def publish(self, event, *args, **kwargs):
        """
        Publish a event and return a list of values returned by its
        subscribers.

        :param event: The event to publish.
        :param args: The positional arguments to pass to the event's
                     subscribers.
        :param kwargs: The keyword arguments to pass to the event's
                       subscribers.
        """
        result = []
        for subscriber in self.get_subscribers(event):
            try:
                value = subscriber(event, *args, **kwargs)
            except Exception:
                logger.exception('Exception during event publication')
                value = None
            result.append(value)
        logger.debug('publish %s: args = %s, kwargs = %s, result = %s', event, args, kwargs, result)
        return result


#
# Simple sequencing
#
class Sequencer(object):

    def __init__(self):
        self._preds = {}
        self._succs = {}
        self._nodes = set()  # nodes with no preds/succs

    def add_node(self, node):
        self._nodes.add(node)

    def remove_node(self, node, edges=False):
        if node in self._nodes:
            self._nodes.remove(node)
        if edges:
            for p in set(self._preds.get(node, ())):
                self.remove(p, node)
            for s in set(self._succs.get(node, ())):
                self.remove(node, s)
            # Remove empties
            for k, v in list(self._preds.items()):
                if not v:
                    del self._preds[k]
            for k, v in list(self._succs.items()):
                if not v:
                    del self._succs[k]

    def add(self, pred, succ):
        assert pred != succ
        self._preds.setdefault(succ, set()).add(pred)
        self._succs.setdefault(pred, set()).add(succ)

    def remove(self, pred, succ):
        assert pred != succ
        try:
            preds = self._preds[succ]
            succs = self._succs[pred]
        except KeyError:  # pragma: no cover
            raise ValueError('%r not a successor of anything' % succ)
        try:
            preds.remove(pred)
            succs.remove(succ)
        except KeyError:  # pragma: no cover
            raise ValueError('%r not a successor of %r' % (succ, pred))

    def is_step(self, step):
        return (step in self._preds or step in self._succs or step in self._nodes)

    def get_steps(self, final):
        if not self.is_step(final):
            raise ValueError('Unknown: %r' % final)
        result = []
        todo = []
        seen = set()
        todo.append(final)
        while todo:
            step = todo.pop(0)
            if step in seen:
                # if a step was already seen,
                # move it to the end (so it will appear earlier
                # when reversed on return) ... but not for the
                # final step, as that would be confusing for
                # users
                if step != final:
                    result.remove(step)
                    result.append(step)
            else:
                seen.add(step)
                result.append(step)
                preds = self._preds.get(step, ())
                todo.extend(preds)
        return reversed(result)

    @property
    def strong_connections(self):
        # http://en.wikipedia.org/wiki/Tarjan%27s_strongly_connected_components_algorithm
        index_counter = [0]
        stack = []
        lowlinks = {}
        index = {}
        result = []

        graph = self._succs

        def strongconnect(node):
            # set the depth index for this node to the smallest unused index
            index[node] = index_counter[0]
            lowlinks[node] = index_counter[0]
            index_counter[0] += 1
            stack.append(node)

            # Consider successors
            try:
                successors = graph[node]
            except Exception:
                successors = []
            for successor in successors:
                if successor not in lowlinks:
                    # Successor has not yet been visited
                    strongconnect(successor)
                    lowlinks[node] = min(lowlinks[node], lowlinks[successor])
                elif successor in stack:
                    # the successor is in the stack and hence in the current
                    # strongly connected component (SCC)
                    lowlinks[node] = min(lowlinks[node], index[successor])

            # If `node` is a root node, pop the stack and generate an SCC
            if lowlinks[node] == index[node]:
                connected_component = []

                while True:
                    successor = stack.pop()
                    connected_component.append(successor)
                    if successor == node:
                        break
                component = tuple(connected_component)
                # storing the result
                result.append(component)

        for node in graph:
            if node not in lowlinks:
                strongconnect(node)

        return result

    @property
    def dot(self):
        result = ['digraph G {']
        for succ in self._preds:
            preds = self._preds[succ]
            for pred in preds:
                result.append('  %s -> %s;' % (pred, succ))
        for node in self._nodes:
            result.append('  %s;' % node)
        result.append('}')
        return '\n'.join(result)


#
# Unarchiving functionality for zip, tar, tgz, tbz, whl
#

ARCHIVE_EXTENSIONS = ('.tar.gz', '.tar.bz2', '.tar', '.zip', '.tgz', '.tbz', '.whl')


def unarchive(archive_filename, dest_dir, format=None, check=True):

    def check_path(path):
        if not isinstance(path, text_type):
            path = path.decode('utf-8')
        p = os.path.abspath(os.path.join(dest_dir, path))
        if not p.startswith(dest_dir) or p[plen] != os.sep:
            raise ValueError('path outside destination: %r' % p)

    dest_dir = os.path.abspath(dest_dir)
    plen = len(dest_dir)
    archive = None
    if format is None:
        if archive_filename.endswith(('.zip', '.whl')):
            format = 'zip'
        elif archive_filename.endswith(('.tar.gz', '.tgz')):
            format = 'tgz'
            mode = 'r:gz'
        elif archive_filename.endswith(('.tar.bz2', '.tbz')):
            format = 'tbz'
            mode = 'r:bz2'
        elif archive_filename.endswith('.tar'):
            format = 'tar'
            mode = 'r'
        else:  # pragma: no cover
            raise ValueError('Unknown format for %r' % archive_filename)
    try:
        if format == 'zip':
            archive = ZipFile(archive_filename, 'r')
            if check:
                names = archive.namelist()
                for name in names:
                    check_path(name)
        else:
            archive = tarfile.open(archive_filename, mode)
            if check:
                names = archive.getnames()
                for name in names:
                    check_path(name)
        if format != 'zip' and sys.version_info[0] < 3:
            # See Python issue 17153. If the dest path contains Unicode,
            # tarfile extraction fails on Python 2.x if a member path name
            # contains non-ASCII characters - it leads to an implicit
            # bytes -> unicode conversion using ASCII to decode.
            for tarinfo in archive.getmembers():
                if not isinstance(tarinfo.name, text_type):
                    tarinfo.name = tarinfo.name.decode('utf-8')

        # Limit extraction of dangerous items, if this Python
        # allows it easily. If not, just trust the input.
        # See: https://docs.python.org/3/library/tarfile.html#extraction-filters
        def extraction_filter(member, path):
            """Run tarfile.tar_filter, but raise the expected ValueError"""
            # This is only called if the current Python has tarfile filters
            try:
                return tarfile.tar_filter(member, path)
            except tarfile.FilterError as exc:
                raise ValueError(str(exc))

        archive.extraction_filter = extraction_filter

        archive.extractall(dest_dir)

    finally:
        if archive:
            archive.close()


def zip_dir(directory):
    """zip a directory tree into a BytesIO object"""
    result = io.BytesIO()
    dlen = len(directory)
    with ZipFile(result, "w") as zf:
        for root, dirs, files in os.walk(directory):
            for name in files:
                full = os.path.join(root, name)
                rel = root[dlen:]
                dest = os.path.join(rel, name)
                zf.write(full, dest)
    return result


#
# Simple progress bar
#

UNITS = ('', 'K', 'M', 'G', 'T', 'P')


class Progress(object):
    unknown = 'UNKNOWN'

    def __init__(self, minval=0, maxval=100):
        assert maxval is None or maxval >= minval
        self.min = self.cur = minval
        self.max = maxval
        self.started = None
        self.elapsed = 0
        self.done = False

    def update(self, curval):
        assert self.min <= curval
        assert self.max is None or curval <= self.max
        self.cur = curval
        now = time.time()
        if self.started is None:
            self.started = now
        else:
            self.elapsed = now - self.started

    def increment(self, incr):
        assert incr >= 0
        self.update(self.cur + incr)

    def start(self):
        self.update(self.min)
        return self

    def stop(self):
        if self.max is not None:
            self.update(self.max)
        self.done = True

    @property
    def maximum(self):
        return self.unknown if self.max is None else self.max

    @property
    def percentage(self):
        if self.done:
            result = '100 %'
        elif self.max is None:
            result = ' ?? %'
        else:
            v = 100.0 * (self.cur - self.min) / (self.max - self.min)
            result = '%3d %%' % v
        return result

    def format_duration(self, duration):
        if (duration <= 0) and self.max is None or self.cur == self.min:
            result = '??:??:??'
        # elif duration < 1:
        #     result = '--:--:--'
        else:
            result = time.strftime('%H:%M:%S', time.gmtime(duration))
        return result

    @property
    def ETA(self):
        if self.done:
            prefix = 'Done'
            t = self.elapsed
            # import pdb; pdb.set_trace()
        else:
            prefix = 'ETA '
            if self.max is None:
                t = -1
            elif self.elapsed == 0 or (self.cur == self.min):
                t = 0
            else:
                # import pdb; pdb.set_trace()
                t = float(self.max - self.min)
                t /= self.cur - self.min
                t = (t - 1) * self.elapsed
        return '%s: %s' % (prefix, self.format_duration(t))

    @property
    def speed(self):
        if self.elapsed == 0:
            result = 0.0
        else:
            result = (self.cur - self.min) / self.elapsed
        for unit in UNITS:
            if result < 1000:
                break
            result /= 1000.0
        return '%d %sB/s' % (result, unit)


#
# Glob functionality
#

RICH_GLOB = re.compile(r'\{([^}]*)\}')
_CHECK_RECURSIVE_GLOB = re.compile(r'[^/\\,{]\*\*|\*\*[^/\\,}]')
_CHECK_MISMATCH_SET = re.compile(r'^[^{]*\}|\{[^}]*$')


def iglob(path_glob):
    """Extended globbing function that supports ** and {opt1,opt2,opt3}."""
    if _CHECK_RECURSIVE_GLOB.search(path_glob):
        msg = """invalid glob %r: recursive glob "**" must be used alone"""
        raise ValueError(msg % path_glob)
    if _CHECK_MISMATCH_SET.search(path_glob):
        msg = """invalid glob %r: mismatching set marker '{' or '}'"""
        raise ValueError(msg % path_glob)
    return _iglob(path_glob)


def _iglob(path_glob):
    rich_path_glob = RICH_GLOB.split(path_glob, 1)
    if len(rich_path_glob) > 1:
        assert len(rich_path_glob) == 3, rich_path_glob
        prefix, set, suffix = rich_path_glob
        for item in set.split(','):
            for path in _iglob(''.join((prefix, item, suffix))):
                yield path
    else:
        if '**' not in path_glob:
            for item in std_iglob(path_glob):
                yield item
        else:
            prefix, radical = path_glob.split('**', 1)
            if prefix == '':
                prefix = '.'
            if radical == '':
                radical = '*'
            else:
                # we support both
                radical = radical.lstrip('/')
                radical = radical.lstrip('\\')
            for path, dir, files in os.walk(prefix):
                path = os.path.normpath(path)
                for fn in _iglob(os.path.join(path, radical)):
                    yield fn


if ssl:
    from .compat import (HTTPSHandler as BaseHTTPSHandler, match_hostname, CertificateError)

    #
    # HTTPSConnection which verifies certificates/matches domains
    #

    class HTTPSConnection(httplib.HTTPSConnection):
        ca_certs = None  # set this to the path to the certs file (.pem)
        check_domain = True  # only used if ca_certs is not None

        # noinspection PyPropertyAccess
        def connect(self):
            sock = socket.create_connection((self.host, self.port), self.timeout)
            if getattr(self, '_tunnel_host', False):
                self.sock = sock
                self._tunnel()

            context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            if hasattr(ssl, 'OP_NO_SSLv2'):
                context.options |= ssl.OP_NO_SSLv2
            if getattr(self, 'cert_file', None):
                context.load_cert_chain(self.cert_file, self.key_file)
            kwargs = {}
            if self.ca_certs:
                context.verify_mode = ssl.CERT_REQUIRED
                context.load_verify_locations(cafile=self.ca_certs)
                if getattr(ssl, 'HAS_SNI', False):
                    kwargs['server_hostname'] = self.host

            self.sock = context.wrap_socket(sock, **kwargs)
            if self.ca_certs and self.check_domain:
                try:
                    match_hostname(self.sock.getpeercert(), self.host)
                    logger.debug('Host verified: %s', self.host)
                except CertificateError:  # pragma: no cover
                    self.sock.shutdown(socket.SHUT_RDWR)
                    self.sock.close()
                    raise

    class HTTPSHandler(BaseHTTPSHandler):

        def __init__(self, ca_certs, check_domain=True):
            BaseHTTPSHandler.__init__(self)
            self.ca_certs = ca_certs
            self.check_domain = check_domain

        def _conn_maker(self, *args, **kwargs):
            """
            This is called to create a connection instance. Normally you'd
            pass a connection class to do_open, but it doesn't actually check for
            a class, and just expects a callable. As long as we behave just as a
            constructor would have, we should be OK. If it ever changes so that
            we *must* pass a class, we'll create an UnsafeHTTPSConnection class
            which just sets check_domain to False in the class definition, and
            choose which one to pass to do_open.
            """
            result = HTTPSConnection(*args, **kwargs)
            if self.ca_certs:
                result.ca_certs = self.ca_certs
                result.check_domain = self.check_domain
            return result

        def https_open(self, req):
            try:
                return self.do_open(self._conn_maker, req)
            except URLError as e:
                if 'certificate verify failed' in str(e.reason):
                    raise CertificateError('Unable to verify server certificate '
                                           'for %s' % req.host)
                else:
                    raise

    #
    # To prevent against mixing HTTP traffic with HTTPS (examples: A Man-In-The-
    # Middle proxy using HTTP listens on port 443, or an index mistakenly serves
    # HTML containing a http://xyz link when it should be https://xyz),
    # you can use the following handler class, which does not allow HTTP traffic.
    #
    # It works by inheriting from HTTPHandler - so build_opener won't add a
    # handler for HTTP itself.
    #
    class HTTPSOnlyHandler(HTTPSHandler, HTTPHandler):

        def http_open(self, req):
            raise URLError('Unexpected HTTP request on what should be a secure '
                           'connection: %s' % req)


#
# XML-RPC with timeouts
#
class Transport(xmlrpclib.Transport):

    def __init__(self, timeout, use_datetime=0):
        self.timeout = timeout
        xmlrpclib.Transport.__init__(self, use_datetime)

    def make_connection(self, host):
        h, eh, x509 = self.get_host_info(host)
        if not self._connection or host != self._connection[0]:
            self._extra_headers = eh
            self._connection = host, httplib.HTTPConnection(h)
        return self._connection[1]


if ssl:

    class SafeTransport(xmlrpclib.SafeTransport):

        def __init__(self, timeout, use_datetime=0):
            self.timeout = timeout
            xmlrpclib.SafeTransport.__init__(self, use_datetime)

        def make_connection(self, host):
            h, eh, kwargs = self.get_host_info(host)
            if not kwargs:
                kwargs = {}
            kwargs['timeout'] = self.timeout
            if not self._connection or host != self._connection[0]:
                self._extra_headers = eh
                self._connection = host, httplib.HTTPSConnection(h, None, **kwargs)
            return self._connection[1]


class ServerProxy(xmlrpclib.ServerProxy):

    def __init__(self, uri, **kwargs):
        self.timeout = timeout = kwargs.pop('timeout', None)
        # The above classes only come into play if a timeout
        # is specified
        if timeout is not None:
            # scheme = splittype(uri)  # deprecated as of Python 3.8
            scheme = urlparse(uri)[0]
            use_datetime = kwargs.get('use_datetime', 0)
            if scheme == 'https':
                tcls = SafeTransport
            else:
                tcls = Transport
            kwargs['transport'] = t = tcls(timeout, use_datetime=use_datetime)
            self.transport = t
        xmlrpclib.ServerProxy.__init__(self, uri, **kwargs)


#
# CSV functionality. This is provided because on 2.x, the csv module can't
# handle Unicode. However, we need to deal with Unicode in e.g. RECORD files.
#


def _csv_open(fn, mode, **kwargs):
    if sys.version_info[0] < 3:
        mode += 'b'
    else:
        kwargs['newline'] = ''
        # Python 3 determines encoding from locale. Force 'utf-8'
        # file encoding to match other forced utf-8 encoding
        kwargs['encoding'] = 'utf-8'
    return open(fn, mode, **kwargs)


class CSVBase(object):
    defaults = {
        'delimiter': str(','),  # The strs are used because we need native
        'quotechar': str('"'),  # str in the csv API (2.x won't take
        'lineterminator': str('\n')  # Unicode)
    }

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.stream.close()


class CSVReader(CSVBase):

    def __init__(self, **kwargs):
        if 'stream' in kwargs:
            stream = kwargs['stream']
            if sys.version_info[0] >= 3:
                # needs to be a text stream
                stream = codecs.getreader('utf-8')(stream)
            self.stream = stream
        else:
            self.stream = _csv_open(kwargs['path'], 'r')
        self.reader = csv.reader(self.stream, **self.defaults)

    def __iter__(self):
        return self

    def next(self):
        result = next(self.reader)
        if sys.version_info[0] < 3:
            for i, item in enumerate(result):
                if not isinstance(item, text_type):
                    result[i] = item.decode('utf-8')
        return result

    __next__ = next


class CSVWriter(CSVBase):

    def __init__(self, fn, **kwargs):
        self.stream = _csv_open(fn, 'w')
        self.writer = csv.writer(self.stream, **self.defaults)

    def writerow(self, row):
        if sys.version_info[0] < 3:
            r = []
            for item in row:
                if isinstance(item, text_type):
                    item = item.encode('utf-8')
                r.append(item)
            row = r
        self.writer.writerow(row)


#
#   Configurator functionality
#


class Configurator(BaseConfigurator):

    value_converters = dict(BaseConfigurator.value_converters)
    value_converters['inc'] = 'inc_convert'

    def __init__(self, config, base=None):
        super(Configurator, self).__init__(config)
        self.base = base or os.getcwd()

    def configure_custom(self, config):

        def convert(o):
            if isinstance(o, (list, tuple)):
                result = type(o)([convert(i) for i in o])
            elif isinstance(o, dict):
                if '()' in o:
                    result = self.configure_custom(o)
                else:
                    result = {}
                    for k in o:
                        result[k] = convert(o[k])
            else:
                result = self.convert(o)
            return result

        c = config.pop('()')
        if not callable(c):
            c = self.resolve(c)
        props = config.pop('.', None)
        # Check for valid identifiers
        args = config.pop('[]', ())
        if args:
            args = tuple([convert(o) for o in args])
        items = [(k, convert(config[k])) for k in config if valid_ident(k)]
        kwargs = dict(items)
        result = c(*args, **kwargs)
        if props:
            for n, v in props.items():
                setattr(result, n, convert(v))
        return result

    def __getitem__(self, key):
        result = self.config[key]
        if isinstance(result, dict) and '()' in result:
            self.config[key] = result = self.configure_custom(result)
        return result

    def inc_convert(self, value):
        """Default converter for the inc:// protocol."""
        if not os.path.isabs(value):
            value = os.path.join(self.base, value)
        with codecs.open(value, 'r', encoding='utf-8') as f:
            result = json.load(f)
        return result


class SubprocessMixin(object):
    """
    Mixin for running subprocesses and capturing their output
    """

    def __init__(self, verbose=False, progress=None):
        self.verbose = verbose
        self.progress = progress

    def reader(self, stream, context):
        """
        Read lines from a subprocess' output stream and either pass to a progress
        callable (if specified) or write progress information to sys.stderr.
        """
        progress = self.progress
        verbose = self.verbose
        while True:
            s = stream.readline()
            if not s:
                break
            if progress is not None:
                progress(s, context)
            else:
                if not verbose:
                    sys.stderr.write('.')
                else:
                    sys.stderr.write(s.decode('utf-8'))
                sys.stderr.flush()
        stream.close()

    def run_command(self, cmd, **kwargs):
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
        t1 = threading.Thread(target=self.reader, args=(p.stdout, 'stdout'))
        t1.start()
        t2 = threading.Thread(target=self.reader, args=(p.stderr, 'stderr'))
        t2.start()
        p.wait()
        t1.join()
        t2.join()
        if self.progress is not None:
            self.progress('done.', 'main')
        elif self.verbose:
            sys.stderr.write('done.\n')
        return p


def normalize_name(name):
    """Normalize a python package name a la PEP 503"""
    # https://www.python.org/dev/peps/pep-0503/#normalized-names
    return re.sub('[-_.]+', '-', name).lower()


# def _get_pypirc_command():
# """
# Get the distutils command for interacting with PyPI configurations.
# :return: the command.
# """
# from distutils.core import Distribution
# from distutils.config import PyPIRCCommand
# d = Distribution()
# return PyPIRCCommand(d)


class PyPIRCFile(object):

    DEFAULT_REPOSITORY = 'https://upload.pypi.org/legacy/'
    DEFAULT_REALM = 'pypi'

    def __init__(self, fn=None, url=None):
        if fn is None:
            fn = os.path.join(os.path.expanduser('~'), '.pypirc')
        self.filename = fn
        self.url = url

    def read(self):
        result = {}

        if os.path.exists(self.filename):
            repository = self.url or self.DEFAULT_REPOSITORY

            config = configparser.RawConfigParser()
            config.read(self.filename)
            sections = config.sections()
            if 'distutils' in sections:
                # let's get the list of servers
                index_servers = config.get('distutils', 'index-servers')
                _servers = [server.strip() for server in index_servers.split('\n') if server.strip() != '']
                if _servers == []:
                    # nothing set, let's try to get the default pypi
                    if 'pypi' in sections:
                        _servers = ['pypi']
                else:
                    for server in _servers:
                        result = {'server': server}
                        result['username'] = config.get(server, 'username')

                        # optional params
                        for key, default in (('repository', self.DEFAULT_REPOSITORY), ('realm', self.DEFAULT_REALM),
                                             ('password', None)):
                            if config.has_option(server, key):
                                result[key] = config.get(server, key)
                            else:
                                result[key] = default

                        # work around people having "repository" for the "pypi"
                        # section of their config set to the HTTP (rather than
                        # HTTPS) URL
                        if (server == 'pypi' and repository in (self.DEFAULT_REPOSITORY, 'pypi')):
                            result['repository'] = self.DEFAULT_REPOSITORY
                        elif (result['server'] != repository and result['repository'] != repository):
                            result = {}
            elif 'server-login' in sections:
                # old format
                server = 'server-login'
                if config.has_option(server, 'repository'):
                    repository = config.get(server, 'repository')
                else:
                    repository = self.DEFAULT_REPOSITORY
                result = {
                    'username': config.get(server, 'username'),
                    'password': config.get(server, 'password'),
                    'repository': repository,
                    'server': server,
                    'realm': self.DEFAULT_REALM
                }
        return result

    def update(self, username, password):
        # import pdb; pdb.set_trace()
        config = configparser.RawConfigParser()
        fn = self.filename
        config.read(fn)
        if not config.has_section('pypi'):
            config.add_section('pypi')
        config.set('pypi', 'username', username)
        config.set('pypi', 'password', password)
        with open(fn, 'w') as f:
            config.write(f)


def _load_pypirc(index):
    """
    Read the PyPI access configuration as supported by distutils.
    """
    return PyPIRCFile(url=index.url).read()


def _store_pypirc(index):
    PyPIRCFile().update(index.username, index.password)


#
# get_platform()/get_host_platform() copied from Python 3.10.a0 source, with some minor
# tweaks
#


def get_host_platform():
    """Return a string that identifies the current platform.  This is used mainly to
    distinguish platform-specific build directories and platform-specific built
    distributions.  Typically includes the OS name and version and the
    architecture (as supplied by 'os.uname()'), although the exact information
    included depends on the OS; eg. on Linux, the kernel version isn't
    particularly important.

    Examples of returned values:
       linux-i586
       linux-alpha (?)
       solaris-2.6-sun4u

    Windows will return one of:
       win-amd64 (64bit Windows on AMD64 (aka x86_64, Intel64, EM64T, etc)
       win32 (all others - specifically, sys.platform is returned)

    For other non-POSIX platforms, currently just returns 'sys.platform'.

    """
    if os.name == 'nt':
        if 'amd64' in sys.version.lower():
            return 'win-amd64'
        if '(arm)' in sys.version.lower():
            return 'win-arm32'
        if '(arm64)' in sys.version.lower():
            return 'win-arm64'
        return sys.platform

    # Set for cross builds explicitly
    if "_PYTHON_HOST_PLATFORM" in os.environ:
        return os.environ["_PYTHON_HOST_PLATFORM"]

    if os.name != 'posix' or not hasattr(os, 'uname'):
        # XXX what about the architecture? NT is Intel or Alpha,
        # Mac OS is M68k or PPC, etc.
        return sys.platform

    # Try to distinguish various flavours of Unix

    (osname, host, release, version, machine) = os.uname()

    # Convert the OS name to lowercase, remove '/' characters, and translate
    # spaces (for "Power Macintosh")
    osname = osname.lower().replace('/', '')
    machine = machine.replace(' ', '_').replace('/', '-')

    if osname[:5] == 'linux':
        # At least on Linux/Intel, 'machine' is the processor --
        # i386, etc.
        # XXX what about Alpha, SPARC, etc?
        return "%s-%s" % (osname, machine)

    elif osname[:5] == 'sunos':
        if release[0] >= '5':  # SunOS 5 == Solaris 2
            osname = 'solaris'
            release = '%d.%s' % (int(release[0]) - 3, release[2:])
            # We can't use 'platform.architecture()[0]' because a
            # bootstrap problem. We use a dict to get an error
            # if some suspicious happens.
            bitness = {2147483647: '32bit', 9223372036854775807: '64bit'}
            machine += '.%s' % bitness[sys.maxsize]
        # fall through to standard osname-release-machine representation
    elif osname[:3] == 'aix':
        from _aix_support import aix_platform
        return aix_platform()
    elif osname[:6] == 'cygwin':
        osname = 'cygwin'
        rel_re = re.compile(r'[\d.]+', re.ASCII)
        m = rel_re.match(release)
        if m:
            release = m.group()
    elif osname[:6] == 'darwin':
        import _osx_support
        try:
            from distutils import sysconfig
        except ImportError:
            import sysconfig
        osname, release, machine = _osx_support.get_platform_osx(sysconfig.get_config_vars(), osname, release, machine)

    return '%s-%s-%s' % (osname, release, machine)


_TARGET_TO_PLAT = {
    'x86': 'win32',
    'x64': 'win-amd64',
    'arm': 'win-arm32',
}


def get_platform():
    if os.name != 'nt':
        return get_host_platform()
    cross_compilation_target = os.environ.get('VSCMD_ARG_TGT_ARCH')
    if cross_compilation_target not in _TARGET_TO_PLAT:
        return get_host_platform()
    return _TARGET_TO_PLAT[cross_compilation_target]

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\distlib\util.py ===
#
# Copyright (C) 2012-2023 The Python Software Foundation.
# See LICENSE.txt and CONTRIBUTORS.txt.
#
import codecs
from collections import deque
import contextlib
import csv
from glob import iglob as std_iglob
import io
import json
import logging
import os
import py_compile
import re
import socket
try:
    import ssl
except ImportError:  # pragma: no cover
    ssl = None
import subprocess
import sys
import tarfile
import tempfile
import textwrap

try:
    import threading
except ImportError:  # pragma: no cover
    import dummy_threading as threading
import time

from . import DistlibException
from .compat import (string_types, text_type, shutil, raw_input, StringIO, cache_from_source, urlopen, urljoin, httplib,
                     xmlrpclib, HTTPHandler, BaseConfigurator, valid_ident, Container, configparser, URLError, ZipFile,
                     fsdecode, unquote, urlparse)

logger = logging.getLogger(__name__)

#
# Requirement parsing code as per PEP 508
#

IDENTIFIER = re.compile(r'^([\w\.-]+)\s*')
VERSION_IDENTIFIER = re.compile(r'^([\w\.*+-]+)\s*')
COMPARE_OP = re.compile(r'^(<=?|>=?|={2,3}|[~!]=)\s*')
MARKER_OP = re.compile(r'^((<=?)|(>=?)|={2,3}|[~!]=|in|not\s+in)\s*')
OR = re.compile(r'^or\b\s*')
AND = re.compile(r'^and\b\s*')
NON_SPACE = re.compile(r'(\S+)\s*')
STRING_CHUNK = re.compile(r'([\s\w\.{}()*+#:;,/?!~`@$%^&=|<>\[\]-]+)')


def parse_marker(marker_string):
    """
    Parse a marker string and return a dictionary containing a marker expression.

    The dictionary will contain keys "op", "lhs" and "rhs" for non-terminals in
    the expression grammar, or strings. A string contained in quotes is to be
    interpreted as a literal string, and a string not contained in quotes is a
    variable (such as os_name).
    """

    def marker_var(remaining):
        # either identifier, or literal string
        m = IDENTIFIER.match(remaining)
        if m:
            result = m.groups()[0]
            remaining = remaining[m.end():]
        elif not remaining:
            raise SyntaxError('unexpected end of input')
        else:
            q = remaining[0]
            if q not in '\'"':
                raise SyntaxError('invalid expression: %s' % remaining)
            oq = '\'"'.replace(q, '')
            remaining = remaining[1:]
            parts = [q]
            while remaining:
                # either a string chunk, or oq, or q to terminate
                if remaining[0] == q:
                    break
                elif remaining[0] == oq:
                    parts.append(oq)
                    remaining = remaining[1:]
                else:
                    m = STRING_CHUNK.match(remaining)
                    if not m:
                        raise SyntaxError('error in string literal: %s' % remaining)
                    parts.append(m.groups()[0])
                    remaining = remaining[m.end():]
            else:
                s = ''.join(parts)
                raise SyntaxError('unterminated string: %s' % s)
            parts.append(q)
            result = ''.join(parts)
            remaining = remaining[1:].lstrip()  # skip past closing quote
        return result, remaining

    def marker_expr(remaining):
        if remaining and remaining[0] == '(':
            result, remaining = marker(remaining[1:].lstrip())
            if remaining[0] != ')':
                raise SyntaxError('unterminated parenthesis: %s' % remaining)
            remaining = remaining[1:].lstrip()
        else:
            lhs, remaining = marker_var(remaining)
            while remaining:
                m = MARKER_OP.match(remaining)
                if not m:
                    break
                op = m.groups()[0]
                remaining = remaining[m.end():]
                rhs, remaining = marker_var(remaining)
                lhs = {'op': op, 'lhs': lhs, 'rhs': rhs}
            result = lhs
        return result, remaining

    def marker_and(remaining):
        lhs, remaining = marker_expr(remaining)
        while remaining:
            m = AND.match(remaining)
            if not m:
                break
            remaining = remaining[m.end():]
            rhs, remaining = marker_expr(remaining)
            lhs = {'op': 'and', 'lhs': lhs, 'rhs': rhs}
        return lhs, remaining

    def marker(remaining):
        lhs, remaining = marker_and(remaining)
        while remaining:
            m = OR.match(remaining)
            if not m:
                break
            remaining = remaining[m.end():]
            rhs, remaining = marker_and(remaining)
            lhs = {'op': 'or', 'lhs': lhs, 'rhs': rhs}
        return lhs, remaining

    return marker(marker_string)


def parse_requirement(req):
    """
    Parse a requirement passed in as a string. Return a Container
    whose attributes contain the various parts of the requirement.
    """
    remaining = req.strip()
    if not remaining or remaining.startswith('#'):
        return None
    m = IDENTIFIER.match(remaining)
    if not m:
        raise SyntaxError('name expected: %s' % remaining)
    distname = m.groups()[0]
    remaining = remaining[m.end():]
    extras = mark_expr = versions = uri = None
    if remaining and remaining[0] == '[':
        i = remaining.find(']', 1)
        if i < 0:
            raise SyntaxError('unterminated extra: %s' % remaining)
        s = remaining[1:i]
        remaining = remaining[i + 1:].lstrip()
        extras = []
        while s:
            m = IDENTIFIER.match(s)
            if not m:
                raise SyntaxError('malformed extra: %s' % s)
            extras.append(m.groups()[0])
            s = s[m.end():]
            if not s:
                break
            if s[0] != ',':
                raise SyntaxError('comma expected in extras: %s' % s)
            s = s[1:].lstrip()
        if not extras:
            extras = None
    if remaining:
        if remaining[0] == '@':
            # it's a URI
            remaining = remaining[1:].lstrip()
            m = NON_SPACE.match(remaining)
            if not m:
                raise SyntaxError('invalid URI: %s' % remaining)
            uri = m.groups()[0]
            t = urlparse(uri)
            # there are issues with Python and URL parsing, so this test
            # is a bit crude. See bpo-20271, bpo-23505. Python doesn't
            # always parse invalid URLs correctly - it should raise
            # exceptions for malformed URLs
            if not (t.scheme and t.netloc):
                raise SyntaxError('Invalid URL: %s' % uri)
            remaining = remaining[m.end():].lstrip()
        else:

            def get_versions(ver_remaining):
                """
                Return a list of operator, version tuples if any are
                specified, else None.
                """
                m = COMPARE_OP.match(ver_remaining)
                versions = None
                if m:
                    versions = []
                    while True:
                        op = m.groups()[0]
                        ver_remaining = ver_remaining[m.end():]
                        m = VERSION_IDENTIFIER.match(ver_remaining)
                        if not m:
                            raise SyntaxError('invalid version: %s' % ver_remaining)
                        v = m.groups()[0]
                        versions.append((op, v))
                        ver_remaining = ver_remaining[m.end():]
                        if not ver_remaining or ver_remaining[0] != ',':
                            break
                        ver_remaining = ver_remaining[1:].lstrip()
                        # Some packages have a trailing comma which would break things
                        # See issue #148
                        if not ver_remaining:
                            break
                        m = COMPARE_OP.match(ver_remaining)
                        if not m:
                            raise SyntaxError('invalid constraint: %s' % ver_remaining)
                    if not versions:
                        versions = None
                return versions, ver_remaining

            if remaining[0] != '(':
                versions, remaining = get_versions(remaining)
            else:
                i = remaining.find(')', 1)
                if i < 0:
                    raise SyntaxError('unterminated parenthesis: %s' % remaining)
                s = remaining[1:i]
                remaining = remaining[i + 1:].lstrip()
                # As a special diversion from PEP 508, allow a version number
                # a.b.c in parentheses as a synonym for ~= a.b.c (because this
                # is allowed in earlier PEPs)
                if COMPARE_OP.match(s):
                    versions, _ = get_versions(s)
                else:
                    m = VERSION_IDENTIFIER.match(s)
                    if not m:
                        raise SyntaxError('invalid constraint: %s' % s)
                    v = m.groups()[0]
                    s = s[m.end():].lstrip()
                    if s:
                        raise SyntaxError('invalid constraint: %s' % s)
                    versions = [('~=', v)]

    if remaining:
        if remaining[0] != ';':
            raise SyntaxError('invalid requirement: %s' % remaining)
        remaining = remaining[1:].lstrip()

        mark_expr, remaining = parse_marker(remaining)

    if remaining and remaining[0] != '#':
        raise SyntaxError('unexpected trailing data: %s' % remaining)

    if not versions:
        rs = distname
    else:
        rs = '%s %s' % (distname, ', '.join(['%s %s' % con for con in versions]))
    return Container(name=distname, extras=extras, constraints=versions, marker=mark_expr, url=uri, requirement=rs)


def get_resources_dests(resources_root, rules):
    """Find destinations for resources files"""

    def get_rel_path(root, path):
        # normalizes and returns a lstripped-/-separated path
        root = root.replace(os.path.sep, '/')
        path = path.replace(os.path.sep, '/')
        assert path.startswith(root)
        return path[len(root):].lstrip('/')

    destinations = {}
    for base, suffix, dest in rules:
        prefix = os.path.join(resources_root, base)
        for abs_base in iglob(prefix):
            abs_glob = os.path.join(abs_base, suffix)
            for abs_path in iglob(abs_glob):
                resource_file = get_rel_path(resources_root, abs_path)
                if dest is None:  # remove the entry if it was here
                    destinations.pop(resource_file, None)
                else:
                    rel_path = get_rel_path(abs_base, abs_path)
                    rel_dest = dest.replace(os.path.sep, '/').rstrip('/')
                    destinations[resource_file] = rel_dest + '/' + rel_path
    return destinations


def in_venv():
    if hasattr(sys, 'real_prefix'):
        # virtualenv venvs
        result = True
    else:
        # PEP 405 venvs
        result = sys.prefix != getattr(sys, 'base_prefix', sys.prefix)
    return result


def get_executable():
    # The __PYVENV_LAUNCHER__ dance is apparently no longer needed, as
    # changes to the stub launcher mean that sys.executable always points
    # to the stub on OS X
    #    if sys.platform == 'darwin' and ('__PYVENV_LAUNCHER__'
    #                                     in os.environ):
    #        result =  os.environ['__PYVENV_LAUNCHER__']
    #    else:
    #        result = sys.executable
    #    return result
    # Avoid normcasing: see issue #143
    # result = os.path.normcase(sys.executable)
    result = sys.executable
    if not isinstance(result, text_type):
        result = fsdecode(result)
    return result


def proceed(prompt, allowed_chars, error_prompt=None, default=None):
    p = prompt
    while True:
        s = raw_input(p)
        p = prompt
        if not s and default:
            s = default
        if s:
            c = s[0].lower()
            if c in allowed_chars:
                break
            if error_prompt:
                p = '%c: %s\n%s' % (c, error_prompt, prompt)
    return c


def extract_by_key(d, keys):
    if isinstance(keys, string_types):
        keys = keys.split()
    result = {}
    for key in keys:
        if key in d:
            result[key] = d[key]
    return result


def read_exports(stream):
    if sys.version_info[0] >= 3:
        # needs to be a text stream
        stream = codecs.getreader('utf-8')(stream)
    # Try to load as JSON, falling back on legacy format
    data = stream.read()
    stream = StringIO(data)
    try:
        jdata = json.load(stream)
        result = jdata['extensions']['python.exports']['exports']
        for group, entries in result.items():
            for k, v in entries.items():
                s = '%s = %s' % (k, v)
                entry = get_export_entry(s)
                assert entry is not None
                entries[k] = entry
        return result
    except Exception:
        stream.seek(0, 0)

    def read_stream(cp, stream):
        if hasattr(cp, 'read_file'):
            cp.read_file(stream)
        else:
            cp.readfp(stream)

    cp = configparser.ConfigParser()
    try:
        read_stream(cp, stream)
    except configparser.MissingSectionHeaderError:
        stream.close()
        data = textwrap.dedent(data)
        stream = StringIO(data)
        read_stream(cp, stream)

    result = {}
    for key in cp.sections():
        result[key] = entries = {}
        for name, value in cp.items(key):
            s = '%s = %s' % (name, value)
            entry = get_export_entry(s)
            assert entry is not None
            # entry.dist = self
            entries[name] = entry
    return result


def write_exports(exports, stream):
    if sys.version_info[0] >= 3:
        # needs to be a text stream
        stream = codecs.getwriter('utf-8')(stream)
    cp = configparser.ConfigParser()
    for k, v in exports.items():
        # TODO check k, v for valid values
        cp.add_section(k)
        for entry in v.values():
            if entry.suffix is None:
                s = entry.prefix
            else:
                s = '%s:%s' % (entry.prefix, entry.suffix)
            if entry.flags:
                s = '%s [%s]' % (s, ', '.join(entry.flags))
            cp.set(k, entry.name, s)
    cp.write(stream)


@contextlib.contextmanager
def tempdir():
    td = tempfile.mkdtemp()
    try:
        yield td
    finally:
        shutil.rmtree(td)


@contextlib.contextmanager
def chdir(d):
    cwd = os.getcwd()
    try:
        os.chdir(d)
        yield
    finally:
        os.chdir(cwd)


@contextlib.contextmanager
def socket_timeout(seconds=15):
    cto = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(seconds)
        yield
    finally:
        socket.setdefaulttimeout(cto)


class cached_property(object):

    def __init__(self, func):
        self.func = func
        # for attr in ('__name__', '__module__', '__doc__'):
        #     setattr(self, attr, getattr(func, attr, None))

    def __get__(self, obj, cls=None):
        if obj is None:
            return self
        value = self.func(obj)
        object.__setattr__(obj, self.func.__name__, value)
        # obj.__dict__[self.func.__name__] = value = self.func(obj)
        return value


def convert_path(pathname):
    """Return 'pathname' as a name that will work on the native filesystem.

    The path is split on '/' and put back together again using the current
    directory separator.  Needed because filenames in the setup script are
    always supplied in Unix style, and have to be converted to the local
    convention before we can actually use them in the filesystem.  Raises
    ValueError on non-Unix-ish systems if 'pathname' either starts or
    ends with a slash.
    """
    if os.sep == '/':
        return pathname
    if not pathname:
        return pathname
    if pathname[0] == '/':
        raise ValueError("path '%s' cannot be absolute" % pathname)
    if pathname[-1] == '/':
        raise ValueError("path '%s' cannot end with '/'" % pathname)

    paths = pathname.split('/')
    while os.curdir in paths:
        paths.remove(os.curdir)
    if not paths:
        return os.curdir
    return os.path.join(*paths)


class FileOperator(object):

    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.ensured = set()
        self._init_record()

    def _init_record(self):
        self.record = False
        self.files_written = set()
        self.dirs_created = set()

    def record_as_written(self, path):
        if self.record:
            self.files_written.add(path)

    def newer(self, source, target):
        """Tell if the target is newer than the source.

        Returns true if 'source' exists and is more recently modified than
        'target', or if 'source' exists and 'target' doesn't.

        Returns false if both exist and 'target' is the same age or younger
        than 'source'. Raise PackagingFileError if 'source' does not exist.

        Note that this test is not very accurate: files created in the same
        second will have the same "age".
        """
        if not os.path.exists(source):
            raise DistlibException("file '%r' does not exist" % os.path.abspath(source))
        if not os.path.exists(target):
            return True

        return os.stat(source).st_mtime > os.stat(target).st_mtime

    def copy_file(self, infile, outfile, check=True):
        """Copy a file respecting dry-run and force flags.
        """
        self.ensure_dir(os.path.dirname(outfile))
        logger.info('Copying %s to %s', infile, outfile)
        if not self.dry_run:
            msg = None
            if check:
                if os.path.islink(outfile):
                    msg = '%s is a symlink' % outfile
                elif os.path.exists(outfile) and not os.path.isfile(outfile):
                    msg = '%s is a non-regular file' % outfile
            if msg:
                raise ValueError(msg + ' which would be overwritten')
            shutil.copyfile(infile, outfile)
        self.record_as_written(outfile)

    def copy_stream(self, instream, outfile, encoding=None):
        assert not os.path.isdir(outfile)
        self.ensure_dir(os.path.dirname(outfile))
        logger.info('Copying stream %s to %s', instream, outfile)
        if not self.dry_run:
            if encoding is None:
                outstream = open(outfile, 'wb')
            else:
                outstream = codecs.open(outfile, 'w', encoding=encoding)
            try:
                shutil.copyfileobj(instream, outstream)
            finally:
                outstream.close()
        self.record_as_written(outfile)

    def write_binary_file(self, path, data):
        self.ensure_dir(os.path.dirname(path))
        if not self.dry_run:
            if os.path.exists(path):
                os.remove(path)
            with open(path, 'wb') as f:
                f.write(data)
        self.record_as_written(path)

    def write_text_file(self, path, data, encoding):
        self.write_binary_file(path, data.encode(encoding))

    def set_mode(self, bits, mask, files):
        if os.name == 'posix' or (os.name == 'java' and os._name == 'posix'):
            # Set the executable bits (owner, group, and world) on
            # all the files specified.
            for f in files:
                if self.dry_run:
                    logger.info("changing mode of %s", f)
                else:
                    mode = (os.stat(f).st_mode | bits) & mask
                    logger.info("changing mode of %s to %o", f, mode)
                    os.chmod(f, mode)

    set_executable_mode = lambda s, f: s.set_mode(0o555, 0o7777, f)

    def ensure_dir(self, path):
        path = os.path.abspath(path)
        if path not in self.ensured and not os.path.exists(path):
            self.ensured.add(path)
            d, f = os.path.split(path)
            self.ensure_dir(d)
            logger.info('Creating %s' % path)
            if not self.dry_run:
                os.mkdir(path)
            if self.record:
                self.dirs_created.add(path)

    def byte_compile(self, path, optimize=False, force=False, prefix=None, hashed_invalidation=False):
        dpath = cache_from_source(path, not optimize)
        logger.info('Byte-compiling %s to %s', path, dpath)
        if not self.dry_run:
            if force or self.newer(path, dpath):
                if not prefix:
                    diagpath = None
                else:
                    assert path.startswith(prefix)
                    diagpath = path[len(prefix):]
            compile_kwargs = {}
            if hashed_invalidation and hasattr(py_compile, 'PycInvalidationMode'):
                if not isinstance(hashed_invalidation, py_compile.PycInvalidationMode):
                    hashed_invalidation = py_compile.PycInvalidationMode.CHECKED_HASH
                compile_kwargs['invalidation_mode'] = hashed_invalidation
            py_compile.compile(path, dpath, diagpath, True, **compile_kwargs)  # raise error
        self.record_as_written(dpath)
        return dpath

    def ensure_removed(self, path):
        if os.path.exists(path):
            if os.path.isdir(path) and not os.path.islink(path):
                logger.debug('Removing directory tree at %s', path)
                if not self.dry_run:
                    shutil.rmtree(path)
                if self.record:
                    if path in self.dirs_created:
                        self.dirs_created.remove(path)
            else:
                if os.path.islink(path):
                    s = 'link'
                else:
                    s = 'file'
                logger.debug('Removing %s %s', s, path)
                if not self.dry_run:
                    os.remove(path)
                if self.record:
                    if path in self.files_written:
                        self.files_written.remove(path)

    def is_writable(self, path):
        result = False
        while not result:
            if os.path.exists(path):
                result = os.access(path, os.W_OK)
                break
            parent = os.path.dirname(path)
            if parent == path:
                break
            path = parent
        return result

    def commit(self):
        """
        Commit recorded changes, turn off recording, return
        changes.
        """
        assert self.record
        result = self.files_written, self.dirs_created
        self._init_record()
        return result

    def rollback(self):
        if not self.dry_run:
            for f in list(self.files_written):
                if os.path.exists(f):
                    os.remove(f)
            # dirs should all be empty now, except perhaps for
            # __pycache__ subdirs
            # reverse so that subdirs appear before their parents
            dirs = sorted(self.dirs_created, reverse=True)
            for d in dirs:
                flist = os.listdir(d)
                if flist:
                    assert flist == ['__pycache__']
                    sd = os.path.join(d, flist[0])
                    os.rmdir(sd)
                os.rmdir(d)  # should fail if non-empty
        self._init_record()


def resolve(module_name, dotted_path):
    if module_name in sys.modules:
        mod = sys.modules[module_name]
    else:
        mod = __import__(module_name)
    if dotted_path is None:
        result = mod
    else:
        parts = dotted_path.split('.')
        result = getattr(mod, parts.pop(0))
        for p in parts:
            result = getattr(result, p)
    return result


class ExportEntry(object):

    def __init__(self, name, prefix, suffix, flags):
        self.name = name
        self.prefix = prefix
        self.suffix = suffix
        self.flags = flags

    @cached_property
    def value(self):
        return resolve(self.prefix, self.suffix)

    def __repr__(self):  # pragma: no cover
        return '<ExportEntry %s = %s:%s %s>' % (self.name, self.prefix, self.suffix, self.flags)

    def __eq__(self, other):
        if not isinstance(other, ExportEntry):
            result = False
        else:
            result = (self.name == other.name and self.prefix == other.prefix and self.suffix == other.suffix and
                      self.flags == other.flags)
        return result

    __hash__ = object.__hash__


ENTRY_RE = re.compile(
    r'''(?P<name>([^\[]\S*))
                      \s*=\s*(?P<callable>(\w+)([:\.]\w+)*)
                      \s*(\[\s*(?P<flags>[\w-]+(=\w+)?(,\s*\w+(=\w+)?)*)\s*\])?
                      ''', re.VERBOSE)


def get_export_entry(specification):
    m = ENTRY_RE.search(specification)
    if not m:
        result = None
        if '[' in specification or ']' in specification:
            raise DistlibException("Invalid specification "
                                   "'%s'" % specification)
    else:
        d = m.groupdict()
        name = d['name']
        path = d['callable']
        colons = path.count(':')
        if colons == 0:
            prefix, suffix = path, None
        else:
            if colons != 1:
                raise DistlibException("Invalid specification "
                                       "'%s'" % specification)
            prefix, suffix = path.split(':')
        flags = d['flags']
        if flags is None:
            if '[' in specification or ']' in specification:
                raise DistlibException("Invalid specification "
                                       "'%s'" % specification)
            flags = []
        else:
            flags = [f.strip() for f in flags.split(',')]
        result = ExportEntry(name, prefix, suffix, flags)
    return result


def get_cache_base(suffix=None):
    """
    Return the default base location for distlib caches. If the directory does
    not exist, it is created. Use the suffix provided for the base directory,
    and default to '.distlib' if it isn't provided.

    On Windows, if LOCALAPPDATA is defined in the environment, then it is
    assumed to be a directory, and will be the parent directory of the result.
    On POSIX, and on Windows if LOCALAPPDATA is not defined, the user's home
    directory - using os.expanduser('~') - will be the parent directory of
    the result.

    The result is just the directory '.distlib' in the parent directory as
    determined above, or with the name specified with ``suffix``.
    """
    if suffix is None:
        suffix = '.distlib'
    if os.name == 'nt' and 'LOCALAPPDATA' in os.environ:
        result = os.path.expandvars('$localappdata')
    else:
        # Assume posix, or old Windows
        result = os.path.expanduser('~')
    # we use 'isdir' instead of 'exists', because we want to
    # fail if there's a file with that name
    if os.path.isdir(result):
        usable = os.access(result, os.W_OK)
        if not usable:
            logger.warning('Directory exists but is not writable: %s', result)
    else:
        try:
            os.makedirs(result)
            usable = True
        except OSError:
            logger.warning('Unable to create %s', result, exc_info=True)
            usable = False
    if not usable:
        result = tempfile.mkdtemp()
        logger.warning('Default location unusable, using %s', result)
    return os.path.join(result, suffix)


def path_to_cache_dir(path, use_abspath=True):
    """
    Convert an absolute path to a directory name for use in a cache.

    The algorithm used is:

    #. On Windows, any ``':'`` in the drive is replaced with ``'---'``.
    #. Any occurrence of ``os.sep`` is replaced with ``'--'``.
    #. ``'.cache'`` is appended.
    """
    d, p = os.path.splitdrive(os.path.abspath(path) if use_abspath else path)
    if d:
        d = d.replace(':', '---')
    p = p.replace(os.sep, '--')
    return d + p + '.cache'


def ensure_slash(s):
    if not s.endswith('/'):
        return s + '/'
    return s


def parse_credentials(netloc):
    username = password = None
    if '@' in netloc:
        prefix, netloc = netloc.rsplit('@', 1)
        if ':' not in prefix:
            username = prefix
        else:
            username, password = prefix.split(':', 1)
    if username:
        username = unquote(username)
    if password:
        password = unquote(password)
    return username, password, netloc


def get_process_umask():
    result = os.umask(0o22)
    os.umask(result)
    return result


def is_string_sequence(seq):
    result = True
    i = None
    for i, s in enumerate(seq):
        if not isinstance(s, string_types):
            result = False
            break
    assert i is not None
    return result


PROJECT_NAME_AND_VERSION = re.compile('([a-z0-9_]+([.-][a-z_][a-z0-9_]*)*)-'
                                      '([a-z0-9_.+-]+)', re.I)
PYTHON_VERSION = re.compile(r'-py(\d\.?\d?)')


def split_filename(filename, project_name=None):
    """
    Extract name, version, python version from a filename (no extension)

    Return name, version, pyver or None
    """
    result = None
    pyver = None
    filename = unquote(filename).replace(' ', '-')
    m = PYTHON_VERSION.search(filename)
    if m:
        pyver = m.group(1)
        filename = filename[:m.start()]
    if project_name and len(filename) > len(project_name) + 1:
        m = re.match(re.escape(project_name) + r'\b', filename)
        if m:
            n = m.end()
            result = filename[:n], filename[n + 1:], pyver
    if result is None:
        m = PROJECT_NAME_AND_VERSION.match(filename)
        if m:
            result = m.group(1), m.group(3), pyver
    return result


# Allow spaces in name because of legacy dists like "Twisted Core"
NAME_VERSION_RE = re.compile(r'(?P<name>[\w .-]+)\s*'
                             r'\(\s*(?P<ver>[^\s)]+)\)$')


def parse_name_and_version(p):
    """
    A utility method used to get name and version from a string.

    From e.g. a Provides-Dist value.

    :param p: A value in a form 'foo (1.0)'
    :return: The name and version as a tuple.
    """
    m = NAME_VERSION_RE.match(p)
    if not m:
        raise DistlibException('Ill-formed name/version string: \'%s\'' % p)
    d = m.groupdict()
    return d['name'].strip().lower(), d['ver']


def get_extras(requested, available):
    result = set()
    requested = set(requested or [])
    available = set(available or [])
    if '*' in requested:
        requested.remove('*')
        result |= available
    for r in requested:
        if r == '-':
            result.add(r)
        elif r.startswith('-'):
            unwanted = r[1:]
            if unwanted not in available:
                logger.warning('undeclared extra: %s' % unwanted)
            if unwanted in result:
                result.remove(unwanted)
        else:
            if r not in available:
                logger.warning('undeclared extra: %s' % r)
            result.add(r)
    return result


#
# Extended metadata functionality
#


def _get_external_data(url):
    result = {}
    try:
        # urlopen might fail if it runs into redirections,
        # because of Python issue #13696. Fixed in locators
        # using a custom redirect handler.
        resp = urlopen(url)
        headers = resp.info()
        ct = headers.get('Content-Type')
        if not ct.startswith('application/json'):
            logger.debug('Unexpected response for JSON request: %s', ct)
        else:
            reader = codecs.getreader('utf-8')(resp)
            # data = reader.read().decode('utf-8')
            # result = json.loads(data)
            result = json.load(reader)
    except Exception as e:
        logger.exception('Failed to get external data for %s: %s', url, e)
    return result


_external_data_base_url = 'https://www.red-dove.com/pypi/projects/'


def get_project_data(name):
    url = '%s/%s/project.json' % (name[0].upper(), name)
    url = urljoin(_external_data_base_url, url)
    result = _get_external_data(url)
    return result


def get_package_data(name, version):
    url = '%s/%s/package-%s.json' % (name[0].upper(), name, version)
    url = urljoin(_external_data_base_url, url)
    return _get_external_data(url)


class Cache(object):
    """
    A class implementing a cache for resources that need to live in the file system
    e.g. shared libraries. This class was moved from resources to here because it
    could be used by other modules, e.g. the wheel module.
    """

    def __init__(self, base):
        """
        Initialise an instance.

        :param base: The base directory where the cache should be located.
        """
        # we use 'isdir' instead of 'exists', because we want to
        # fail if there's a file with that name
        if not os.path.isdir(base):  # pragma: no cover
            os.makedirs(base)
        if (os.stat(base).st_mode & 0o77) != 0:
            logger.warning('Directory \'%s\' is not private', base)
        self.base = os.path.abspath(os.path.normpath(base))

    def prefix_to_dir(self, prefix, use_abspath=True):
        """
        Converts a resource prefix to a directory name in the cache.
        """
        return path_to_cache_dir(prefix, use_abspath=use_abspath)

    def clear(self):
        """
        Clear the cache.
        """
        not_removed = []
        for fn in os.listdir(self.base):
            fn = os.path.join(self.base, fn)
            try:
                if os.path.islink(fn) or os.path.isfile(fn):
                    os.remove(fn)
                elif os.path.isdir(fn):
                    shutil.rmtree(fn)
            except Exception:
                not_removed.append(fn)
        return not_removed


class EventMixin(object):
    """
    A very simple publish/subscribe system.
    """

    def __init__(self):
        self._subscribers = {}

    def add(self, event, subscriber, append=True):
        """
        Add a subscriber for an event.

        :param event: The name of an event.
        :param subscriber: The subscriber to be added (and called when the
                           event is published).
        :param append: Whether to append or prepend the subscriber to an
                       existing subscriber list for the event.
        """
        subs = self._subscribers
        if event not in subs:
            subs[event] = deque([subscriber])
        else:
            sq = subs[event]
            if append:
                sq.append(subscriber)
            else:
                sq.appendleft(subscriber)

    def remove(self, event, subscriber):
        """
        Remove a subscriber for an event.

        :param event: The name of an event.
        :param subscriber: The subscriber to be removed.
        """
        subs = self._subscribers
        if event not in subs:
            raise ValueError('No subscribers: %r' % event)
        subs[event].remove(subscriber)

    def get_subscribers(self, event):
        """
        Return an iterator for the subscribers for an event.
        :param event: The event to return subscribers for.
        """
        return iter(self._subscribers.get(event, ()))

    def publish(self, event, *args, **kwargs):
        """
        Publish a event and return a list of values returned by its
        subscribers.

        :param event: The event to publish.
        :param args: The positional arguments to pass to the event's
                     subscribers.
        :param kwargs: The keyword arguments to pass to the event's
                       subscribers.
        """
        result = []
        for subscriber in self.get_subscribers(event):
            try:
                value = subscriber(event, *args, **kwargs)
            except Exception:
                logger.exception('Exception during event publication')
                value = None
            result.append(value)
        logger.debug('publish %s: args = %s, kwargs = %s, result = %s', event, args, kwargs, result)
        return result


#
# Simple sequencing
#
class Sequencer(object):

    def __init__(self):
        self._preds = {}
        self._succs = {}
        self._nodes = set()  # nodes with no preds/succs

    def add_node(self, node):
        self._nodes.add(node)

    def remove_node(self, node, edges=False):
        if node in self._nodes:
            self._nodes.remove(node)
        if edges:
            for p in set(self._preds.get(node, ())):
                self.remove(p, node)
            for s in set(self._succs.get(node, ())):
                self.remove(node, s)
            # Remove empties
            for k, v in list(self._preds.items()):
                if not v:
                    del self._preds[k]
            for k, v in list(self._succs.items()):
                if not v:
                    del self._succs[k]

    def add(self, pred, succ):
        assert pred != succ
        self._preds.setdefault(succ, set()).add(pred)
        self._succs.setdefault(pred, set()).add(succ)

    def remove(self, pred, succ):
        assert pred != succ
        try:
            preds = self._preds[succ]
            succs = self._succs[pred]
        except KeyError:  # pragma: no cover
            raise ValueError('%r not a successor of anything' % succ)
        try:
            preds.remove(pred)
            succs.remove(succ)
        except KeyError:  # pragma: no cover
            raise ValueError('%r not a successor of %r' % (succ, pred))

    def is_step(self, step):
        return (step in self._preds or step in self._succs or step in self._nodes)

    def get_steps(self, final):
        if not self.is_step(final):
            raise ValueError('Unknown: %r' % final)
        result = []
        todo = []
        seen = set()
        todo.append(final)
        while todo:
            step = todo.pop(0)
            if step in seen:
                # if a step was already seen,
                # move it to the end (so it will appear earlier
                # when reversed on return) ... but not for the
                # final step, as that would be confusing for
                # users
                if step != final:
                    result.remove(step)
                    result.append(step)
            else:
                seen.add(step)
                result.append(step)
                preds = self._preds.get(step, ())
                todo.extend(preds)
        return reversed(result)

    @property
    def strong_connections(self):
        # http://en.wikipedia.org/wiki/Tarjan%27s_strongly_connected_components_algorithm
        index_counter = [0]
        stack = []
        lowlinks = {}
        index = {}
        result = []

        graph = self._succs

        def strongconnect(node):
            # set the depth index for this node to the smallest unused index
            index[node] = index_counter[0]
            lowlinks[node] = index_counter[0]
            index_counter[0] += 1
            stack.append(node)

            # Consider successors
            try:
                successors = graph[node]
            except Exception:
                successors = []
            for successor in successors:
                if successor not in lowlinks:
                    # Successor has not yet been visited
                    strongconnect(successor)
                    lowlinks[node] = min(lowlinks[node], lowlinks[successor])
                elif successor in stack:
                    # the successor is in the stack and hence in the current
                    # strongly connected component (SCC)
                    lowlinks[node] = min(lowlinks[node], index[successor])

            # If `node` is a root node, pop the stack and generate an SCC
            if lowlinks[node] == index[node]:
                connected_component = []

                while True:
                    successor = stack.pop()
                    connected_component.append(successor)
                    if successor == node:
                        break
                component = tuple(connected_component)
                # storing the result
                result.append(component)

        for node in graph:
            if node not in lowlinks:
                strongconnect(node)

        return result

    @property
    def dot(self):
        result = ['digraph G {']
        for succ in self._preds:
            preds = self._preds[succ]
            for pred in preds:
                result.append('  %s -> %s;' % (pred, succ))
        for node in self._nodes:
            result.append('  %s;' % node)
        result.append('}')
        return '\n'.join(result)


#
# Unarchiving functionality for zip, tar, tgz, tbz, whl
#

ARCHIVE_EXTENSIONS = ('.tar.gz', '.tar.bz2', '.tar', '.zip', '.tgz', '.tbz', '.whl')


def unarchive(archive_filename, dest_dir, format=None, check=True):

    def check_path(path):
        if not isinstance(path, text_type):
            path = path.decode('utf-8')
        p = os.path.abspath(os.path.join(dest_dir, path))
        if not p.startswith(dest_dir) or p[plen] != os.sep:
            raise ValueError('path outside destination: %r' % p)

    dest_dir = os.path.abspath(dest_dir)
    plen = len(dest_dir)
    archive = None
    if format is None:
        if archive_filename.endswith(('.zip', '.whl')):
            format = 'zip'
        elif archive_filename.endswith(('.tar.gz', '.tgz')):
            format = 'tgz'
            mode = 'r:gz'
        elif archive_filename.endswith(('.tar.bz2', '.tbz')):
            format = 'tbz'
            mode = 'r:bz2'
        elif archive_filename.endswith('.tar'):
            format = 'tar'
            mode = 'r'
        else:  # pragma: no cover
            raise ValueError('Unknown format for %r' % archive_filename)
    try:
        if format == 'zip':
            archive = ZipFile(archive_filename, 'r')
            if check:
                names = archive.namelist()
                for name in names:
                    check_path(name)
        else:
            archive = tarfile.open(archive_filename, mode)
            if check:
                names = archive.getnames()
                for name in names:
                    check_path(name)
        if format != 'zip' and sys.version_info[0] < 3:
            # See Python issue 17153. If the dest path contains Unicode,
            # tarfile extraction fails on Python 2.x if a member path name
            # contains non-ASCII characters - it leads to an implicit
            # bytes -> unicode conversion using ASCII to decode.
            for tarinfo in archive.getmembers():
                if not isinstance(tarinfo.name, text_type):
                    tarinfo.name = tarinfo.name.decode('utf-8')

        # Limit extraction of dangerous items, if this Python
        # allows it easily. If not, just trust the input.
        # See: https://docs.python.org/3/library/tarfile.html#extraction-filters
        def extraction_filter(member, path):
            """Run tarfile.tar_filter, but raise the expected ValueError"""
            # This is only called if the current Python has tarfile filters
            try:
                return tarfile.tar_filter(member, path)
            except tarfile.FilterError as exc:
                raise ValueError(str(exc))

        archive.extraction_filter = extraction_filter

        archive.extractall(dest_dir)

    finally:
        if archive:
            archive.close()


def zip_dir(directory):
    """zip a directory tree into a BytesIO object"""
    result = io.BytesIO()
    dlen = len(directory)
    with ZipFile(result, "w") as zf:
        for root, dirs, files in os.walk(directory):
            for name in files:
                full = os.path.join(root, name)
                rel = root[dlen:]
                dest = os.path.join(rel, name)
                zf.write(full, dest)
    return result


#
# Simple progress bar
#

UNITS = ('', 'K', 'M', 'G', 'T', 'P')


class Progress(object):
    unknown = 'UNKNOWN'

    def __init__(self, minval=0, maxval=100):
        assert maxval is None or maxval >= minval
        self.min = self.cur = minval
        self.max = maxval
        self.started = None
        self.elapsed = 0
        self.done = False

    def update(self, curval):
        assert self.min <= curval
        assert self.max is None or curval <= self.max
        self.cur = curval
        now = time.time()
        if self.started is None:
            self.started = now
        else:
            self.elapsed = now - self.started

    def increment(self, incr):
        assert incr >= 0
        self.update(self.cur + incr)

    def start(self):
        self.update(self.min)
        return self

    def stop(self):
        if self.max is not None:
            self.update(self.max)
        self.done = True

    @property
    def maximum(self):
        return self.unknown if self.max is None else self.max

    @property
    def percentage(self):
        if self.done:
            result = '100 %'
        elif self.max is None:
            result = ' ?? %'
        else:
            v = 100.0 * (self.cur - self.min) / (self.max - self.min)
            result = '%3d %%' % v
        return result

    def format_duration(self, duration):
        if (duration <= 0) and self.max is None or self.cur == self.min:
            result = '??:??:??'
        # elif duration < 1:
        #     result = '--:--:--'
        else:
            result = time.strftime('%H:%M:%S', time.gmtime(duration))
        return result

    @property
    def ETA(self):
        if self.done:
            prefix = 'Done'
            t = self.elapsed
            # import pdb; pdb.set_trace()
        else:
            prefix = 'ETA '
            if self.max is None:
                t = -1
            elif self.elapsed == 0 or (self.cur == self.min):
                t = 0
            else:
                # import pdb; pdb.set_trace()
                t = float(self.max - self.min)
                t /= self.cur - self.min
                t = (t - 1) * self.elapsed
        return '%s: %s' % (prefix, self.format_duration(t))

    @property
    def speed(self):
        if self.elapsed == 0:
            result = 0.0
        else:
            result = (self.cur - self.min) / self.elapsed
        for unit in UNITS:
            if result < 1000:
                break
            result /= 1000.0
        return '%d %sB/s' % (result, unit)


#
# Glob functionality
#

RICH_GLOB = re.compile(r'\{([^}]*)\}')
_CHECK_RECURSIVE_GLOB = re.compile(r'[^/\\,{]\*\*|\*\*[^/\\,}]')
_CHECK_MISMATCH_SET = re.compile(r'^[^{]*\}|\{[^}]*$')


def iglob(path_glob):
    """Extended globbing function that supports ** and {opt1,opt2,opt3}."""
    if _CHECK_RECURSIVE_GLOB.search(path_glob):
        msg = """invalid glob %r: recursive glob "**" must be used alone"""
        raise ValueError(msg % path_glob)
    if _CHECK_MISMATCH_SET.search(path_glob):
        msg = """invalid glob %r: mismatching set marker '{' or '}'"""
        raise ValueError(msg % path_glob)
    return _iglob(path_glob)


def _iglob(path_glob):
    rich_path_glob = RICH_GLOB.split(path_glob, 1)
    if len(rich_path_glob) > 1:
        assert len(rich_path_glob) == 3, rich_path_glob
        prefix, set, suffix = rich_path_glob
        for item in set.split(','):
            for path in _iglob(''.join((prefix, item, suffix))):
                yield path
    else:
        if '**' not in path_glob:
            for item in std_iglob(path_glob):
                yield item
        else:
            prefix, radical = path_glob.split('**', 1)
            if prefix == '':
                prefix = '.'
            if radical == '':
                radical = '*'
            else:
                # we support both
                radical = radical.lstrip('/')
                radical = radical.lstrip('\\')
            for path, dir, files in os.walk(prefix):
                path = os.path.normpath(path)
                for fn in _iglob(os.path.join(path, radical)):
                    yield fn


if ssl:
    from .compat import (HTTPSHandler as BaseHTTPSHandler, match_hostname, CertificateError)

    #
    # HTTPSConnection which verifies certificates/matches domains
    #

    class HTTPSConnection(httplib.HTTPSConnection):
        ca_certs = None  # set this to the path to the certs file (.pem)
        check_domain = True  # only used if ca_certs is not None

        # noinspection PyPropertyAccess
        def connect(self):
            sock = socket.create_connection((self.host, self.port), self.timeout)
            if getattr(self, '_tunnel_host', False):
                self.sock = sock
                self._tunnel()

            context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            if hasattr(ssl, 'OP_NO_SSLv2'):
                context.options |= ssl.OP_NO_SSLv2
            if getattr(self, 'cert_file', None):
                context.load_cert_chain(self.cert_file, self.key_file)
            kwargs = {}
            if self.ca_certs:
                context.verify_mode = ssl.CERT_REQUIRED
                context.load_verify_locations(cafile=self.ca_certs)
                if getattr(ssl, 'HAS_SNI', False):
                    kwargs['server_hostname'] = self.host

            self.sock = context.wrap_socket(sock, **kwargs)
            if self.ca_certs and self.check_domain:
                try:
                    match_hostname(self.sock.getpeercert(), self.host)
                    logger.debug('Host verified: %s', self.host)
                except CertificateError:  # pragma: no cover
                    self.sock.shutdown(socket.SHUT_RDWR)
                    self.sock.close()
                    raise

    class HTTPSHandler(BaseHTTPSHandler):

        def __init__(self, ca_certs, check_domain=True):
            BaseHTTPSHandler.__init__(self)
            self.ca_certs = ca_certs
            self.check_domain = check_domain

        def _conn_maker(self, *args, **kwargs):
            """
            This is called to create a connection instance. Normally you'd
            pass a connection class to do_open, but it doesn't actually check for
            a class, and just expects a callable. As long as we behave just as a
            constructor would have, we should be OK. If it ever changes so that
            we *must* pass a class, we'll create an UnsafeHTTPSConnection class
            which just sets check_domain to False in the class definition, and
            choose which one to pass to do_open.
            """
            result = HTTPSConnection(*args, **kwargs)
            if self.ca_certs:
                result.ca_certs = self.ca_certs
                result.check_domain = self.check_domain
            return result

        def https_open(self, req):
            try:
                return self.do_open(self._conn_maker, req)
            except URLError as e:
                if 'certificate verify failed' in str(e.reason):
                    raise CertificateError('Unable to verify server certificate '
                                           'for %s' % req.host)
                else:
                    raise

    #
    # To prevent against mixing HTTP traffic with HTTPS (examples: A Man-In-The-
    # Middle proxy using HTTP listens on port 443, or an index mistakenly serves
    # HTML containing a http://xyz link when it should be https://xyz),
    # you can use the following handler class, which does not allow HTTP traffic.
    #
    # It works by inheriting from HTTPHandler - so build_opener won't add a
    # handler for HTTP itself.
    #
    class HTTPSOnlyHandler(HTTPSHandler, HTTPHandler):

        def http_open(self, req):
            raise URLError('Unexpected HTTP request on what should be a secure '
                           'connection: %s' % req)


#
# XML-RPC with timeouts
#
class Transport(xmlrpclib.Transport):

    def __init__(self, timeout, use_datetime=0):
        self.timeout = timeout
        xmlrpclib.Transport.__init__(self, use_datetime)

    def make_connection(self, host):
        h, eh, x509 = self.get_host_info(host)
        if not self._connection or host != self._connection[0]:
            self._extra_headers = eh
            self._connection = host, httplib.HTTPConnection(h)
        return self._connection[1]


if ssl:

    class SafeTransport(xmlrpclib.SafeTransport):

        def __init__(self, timeout, use_datetime=0):
            self.timeout = timeout
            xmlrpclib.SafeTransport.__init__(self, use_datetime)

        def make_connection(self, host):
            h, eh, kwargs = self.get_host_info(host)
            if not kwargs:
                kwargs = {}
            kwargs['timeout'] = self.timeout
            if not self._connection or host != self._connection[0]:
                self._extra_headers = eh
                self._connection = host, httplib.HTTPSConnection(h, None, **kwargs)
            return self._connection[1]


class ServerProxy(xmlrpclib.ServerProxy):

    def __init__(self, uri, **kwargs):
        self.timeout = timeout = kwargs.pop('timeout', None)
        # The above classes only come into play if a timeout
        # is specified
        if timeout is not None:
            # scheme = splittype(uri)  # deprecated as of Python 3.8
            scheme = urlparse(uri)[0]
            use_datetime = kwargs.get('use_datetime', 0)
            if scheme == 'https':
                tcls = SafeTransport
            else:
                tcls = Transport
            kwargs['transport'] = t = tcls(timeout, use_datetime=use_datetime)
            self.transport = t
        xmlrpclib.ServerProxy.__init__(self, uri, **kwargs)


#
# CSV functionality. This is provided because on 2.x, the csv module can't
# handle Unicode. However, we need to deal with Unicode in e.g. RECORD files.
#


def _csv_open(fn, mode, **kwargs):
    if sys.version_info[0] < 3:
        mode += 'b'
    else:
        kwargs['newline'] = ''
        # Python 3 determines encoding from locale. Force 'utf-8'
        # file encoding to match other forced utf-8 encoding
        kwargs['encoding'] = 'utf-8'
    return open(fn, mode, **kwargs)


class CSVBase(object):
    defaults = {
        'delimiter': str(','),  # The strs are used because we need native
        'quotechar': str('"'),  # str in the csv API (2.x won't take
        'lineterminator': str('\n')  # Unicode)
    }

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.stream.close()


class CSVReader(CSVBase):

    def __init__(self, **kwargs):
        if 'stream' in kwargs:
            stream = kwargs['stream']
            if sys.version_info[0] >= 3:
                # needs to be a text stream
                stream = codecs.getreader('utf-8')(stream)
            self.stream = stream
        else:
            self.stream = _csv_open(kwargs['path'], 'r')
        self.reader = csv.reader(self.stream, **self.defaults)

    def __iter__(self):
        return self

    def next(self):
        result = next(self.reader)
        if sys.version_info[0] < 3:
            for i, item in enumerate(result):
                if not isinstance(item, text_type):
                    result[i] = item.decode('utf-8')
        return result

    __next__ = next


class CSVWriter(CSVBase):

    def __init__(self, fn, **kwargs):
        self.stream = _csv_open(fn, 'w')
        self.writer = csv.writer(self.stream, **self.defaults)

    def writerow(self, row):
        if sys.version_info[0] < 3:
            r = []
            for item in row:
                if isinstance(item, text_type):
                    item = item.encode('utf-8')
                r.append(item)
            row = r
        self.writer.writerow(row)


#
#   Configurator functionality
#


class Configurator(BaseConfigurator):

    value_converters = dict(BaseConfigurator.value_converters)
    value_converters['inc'] = 'inc_convert'

    def __init__(self, config, base=None):
        super(Configurator, self).__init__(config)
        self.base = base or os.getcwd()

    def configure_custom(self, config):

        def convert(o):
            if isinstance(o, (list, tuple)):
                result = type(o)([convert(i) for i in o])
            elif isinstance(o, dict):
                if '()' in o:
                    result = self.configure_custom(o)
                else:
                    result = {}
                    for k in o:
                        result[k] = convert(o[k])
            else:
                result = self.convert(o)
            return result

        c = config.pop('()')
        if not callable(c):
            c = self.resolve(c)
        props = config.pop('.', None)
        # Check for valid identifiers
        args = config.pop('[]', ())
        if args:
            args = tuple([convert(o) for o in args])
        items = [(k, convert(config[k])) for k in config if valid_ident(k)]
        kwargs = dict(items)
        result = c(*args, **kwargs)
        if props:
            for n, v in props.items():
                setattr(result, n, convert(v))
        return result

    def __getitem__(self, key):
        result = self.config[key]
        if isinstance(result, dict) and '()' in result:
            self.config[key] = result = self.configure_custom(result)
        return result

    def inc_convert(self, value):
        """Default converter for the inc:// protocol."""
        if not os.path.isabs(value):
            value = os.path.join(self.base, value)
        with codecs.open(value, 'r', encoding='utf-8') as f:
            result = json.load(f)
        return result


class SubprocessMixin(object):
    """
    Mixin for running subprocesses and capturing their output
    """

    def __init__(self, verbose=False, progress=None):
        self.verbose = verbose
        self.progress = progress

    def reader(self, stream, context):
        """
        Read lines from a subprocess' output stream and either pass to a progress
        callable (if specified) or write progress information to sys.stderr.
        """
        progress = self.progress
        verbose = self.verbose
        while True:
            s = stream.readline()
            if not s:
                break
            if progress is not None:
                progress(s, context)
            else:
                if not verbose:
                    sys.stderr.write('.')
                else:
                    sys.stderr.write(s.decode('utf-8'))
                sys.stderr.flush()
        stream.close()

    def run_command(self, cmd, **kwargs):
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
        t1 = threading.Thread(target=self.reader, args=(p.stdout, 'stdout'))
        t1.start()
        t2 = threading.Thread(target=self.reader, args=(p.stderr, 'stderr'))
        t2.start()
        p.wait()
        t1.join()
        t2.join()
        if self.progress is not None:
            self.progress('done.', 'main')
        elif self.verbose:
            sys.stderr.write('done.\n')
        return p


def normalize_name(name):
    """Normalize a python package name a la PEP 503"""
    # https://www.python.org/dev/peps/pep-0503/#normalized-names
    return re.sub('[-_.]+', '-', name).lower()


# def _get_pypirc_command():
# """
# Get the distutils command for interacting with PyPI configurations.
# :return: the command.
# """
# from distutils.core import Distribution
# from distutils.config import PyPIRCCommand
# d = Distribution()
# return PyPIRCCommand(d)


class PyPIRCFile(object):

    DEFAULT_REPOSITORY = 'https://upload.pypi.org/legacy/'
    DEFAULT_REALM = 'pypi'

    def __init__(self, fn=None, url=None):
        if fn is None:
            fn = os.path.join(os.path.expanduser('~'), '.pypirc')
        self.filename = fn
        self.url = url

    def read(self):
        result = {}

        if os.path.exists(self.filename):
            repository = self.url or self.DEFAULT_REPOSITORY

            config = configparser.RawConfigParser()
            config.read(self.filename)
            sections = config.sections()
            if 'distutils' in sections:
                # let's get the list of servers
                index_servers = config.get('distutils', 'index-servers')
                _servers = [server.strip() for server in index_servers.split('\n') if server.strip() != '']
                if _servers == []:
                    # nothing set, let's try to get the default pypi
                    if 'pypi' in sections:
                        _servers = ['pypi']
                else:
                    for server in _servers:
                        result = {'server': server}
                        result['username'] = config.get(server, 'username')

                        # optional params
                        for key, default in (('repository', self.DEFAULT_REPOSITORY), ('realm', self.DEFAULT_REALM),
                                             ('password', None)):
                            if config.has_option(server, key):
                                result[key] = config.get(server, key)
                            else:
                                result[key] = default

                        # work around people having "repository" for the "pypi"
                        # section of their config set to the HTTP (rather than
                        # HTTPS) URL
                        if (server == 'pypi' and repository in (self.DEFAULT_REPOSITORY, 'pypi')):
                            result['repository'] = self.DEFAULT_REPOSITORY
                        elif (result['server'] != repository and result['repository'] != repository):
                            result = {}
            elif 'server-login' in sections:
                # old format
                server = 'server-login'
                if config.has_option(server, 'repository'):
                    repository = config.get(server, 'repository')
                else:
                    repository = self.DEFAULT_REPOSITORY
                result = {
                    'username': config.get(server, 'username'),
                    'password': config.get(server, 'password'),
                    'repository': repository,
                    'server': server,
                    'realm': self.DEFAULT_REALM
                }
        return result

    def update(self, username, password):
        # import pdb; pdb.set_trace()
        config = configparser.RawConfigParser()
        fn = self.filename
        config.read(fn)
        if not config.has_section('pypi'):
            config.add_section('pypi')
        config.set('pypi', 'username', username)
        config.set('pypi', 'password', password)
        with open(fn, 'w') as f:
            config.write(f)


def _load_pypirc(index):
    """
    Read the PyPI access configuration as supported by distutils.
    """
    return PyPIRCFile(url=index.url).read()


def _store_pypirc(index):
    PyPIRCFile().update(index.username, index.password)


#
# get_platform()/get_host_platform() copied from Python 3.10.a0 source, with some minor
# tweaks
#


def get_host_platform():
    """Return a string that identifies the current platform.  This is used mainly to
    distinguish platform-specific build directories and platform-specific built
    distributions.  Typically includes the OS name and version and the
    architecture (as supplied by 'os.uname()'), although the exact information
    included depends on the OS; eg. on Linux, the kernel version isn't
    particularly important.

    Examples of returned values:
       linux-i586
       linux-alpha (?)
       solaris-2.6-sun4u

    Windows will return one of:
       win-amd64 (64bit Windows on AMD64 (aka x86_64, Intel64, EM64T, etc)
       win32 (all others - specifically, sys.platform is returned)

    For other non-POSIX platforms, currently just returns 'sys.platform'.

    """
    if os.name == 'nt':
        if 'amd64' in sys.version.lower():
            return 'win-amd64'
        if '(arm)' in sys.version.lower():
            return 'win-arm32'
        if '(arm64)' in sys.version.lower():
            return 'win-arm64'
        return sys.platform

    # Set for cross builds explicitly
    if "_PYTHON_HOST_PLATFORM" in os.environ:
        return os.environ["_PYTHON_HOST_PLATFORM"]

    if os.name != 'posix' or not hasattr(os, 'uname'):
        # XXX what about the architecture? NT is Intel or Alpha,
        # Mac OS is M68k or PPC, etc.
        return sys.platform

    # Try to distinguish various flavours of Unix

    (osname, host, release, version, machine) = os.uname()

    # Convert the OS name to lowercase, remove '/' characters, and translate
    # spaces (for "Power Macintosh")
    osname = osname.lower().replace('/', '')
    machine = machine.replace(' ', '_').replace('/', '-')

    if osname[:5] == 'linux':
        # At least on Linux/Intel, 'machine' is the processor --
        # i386, etc.
        # XXX what about Alpha, SPARC, etc?
        return "%s-%s" % (osname, machine)

    elif osname[:5] == 'sunos':
        if release[0] >= '5':  # SunOS 5 == Solaris 2
            osname = 'solaris'
            release = '%d.%s' % (int(release[0]) - 3, release[2:])
            # We can't use 'platform.architecture()[0]' because a
            # bootstrap problem. We use a dict to get an error
            # if some suspicious happens.
            bitness = {2147483647: '32bit', 9223372036854775807: '64bit'}
            machine += '.%s' % bitness[sys.maxsize]
        # fall through to standard osname-release-machine representation
    elif osname[:3] == 'aix':
        from _aix_support import aix_platform
        return aix_platform()
    elif osname[:6] == 'cygwin':
        osname = 'cygwin'
        rel_re = re.compile(r'[\d.]+', re.ASCII)
        m = rel_re.match(release)
        if m:
            release = m.group()
    elif osname[:6] == 'darwin':
        import _osx_support
        try:
            from distutils import sysconfig
        except ImportError:
            import sysconfig
        osname, release, machine = _osx_support.get_platform_osx(sysconfig.get_config_vars(), osname, release, machine)

    return '%s-%s-%s' % (osname, release, machine)


_TARGET_TO_PLAT = {
    'x86': 'win32',
    'x64': 'win-amd64',
    'arm': 'win-arm32',
}


def get_platform():
    if os.name != 'nt':
        return get_host_platform()
    cross_compilation_target = os.environ.get('VSCMD_ARG_TGT_ARCH')
    if cross_compilation_target not in _TARGET_TO_PLAT:
        return get_host_platform()
    return _TARGET_TO_PLAT[cross_compilation_target]