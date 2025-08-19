
# === NexusCore/openenv\Lib\site-packages\matplotlib\_color_data.py ===
BASE_COLORS = {
    'b': (0, 0, 1),        # blue
    'g': (0, 0.5, 0),      # green
    'r': (1, 0, 0),        # red
    'c': (0, 0.75, 0.75),  # cyan
    'm': (0.75, 0, 0.75),  # magenta
    'y': (0.75, 0.75, 0),  # yellow
    'k': (0, 0, 0),        # black
    'w': (1, 1, 1),        # white
}


# These colors are from Tableau
TABLEAU_COLORS = {
    'tab:blue': '#1f77b4',
    'tab:orange': '#ff7f0e',
    'tab:green': '#2ca02c',
    'tab:red': '#d62728',
    'tab:purple': '#9467bd',
    'tab:brown': '#8c564b',
    'tab:pink': '#e377c2',
    'tab:gray': '#7f7f7f',
    'tab:olive': '#bcbd22',
    'tab:cyan': '#17becf',
}


# This mapping of color names -> hex values is taken from
# a survey run by Randall Munroe see:
# https://blog.xkcd.com/2010/05/03/color-survey-results/
# for more details.  The results are hosted at
# https://xkcd.com/color/rgb/
# and also available as a text file at
# https://xkcd.com/color/rgb.txt
#
# License: https://creativecommons.org/publicdomain/zero/1.0/
XKCD_COLORS = {
    'cloudy blue': '#acc2d9',
    'dark pastel green': '#56ae57',
    'dust': '#b2996e',
    'electric lime': '#a8ff04',
    'fresh green': '#69d84f',
    'light eggplant': '#894585',
    'nasty green': '#70b23f',
    'really light blue': '#d4ffff',
    'tea': '#65ab7c',
    'warm purple': '#952e8f',
    'yellowish tan': '#fcfc81',
    'cement': '#a5a391',
    'dark grass green': '#388004',
    'dusty teal': '#4c9085',
    'grey teal': '#5e9b8a',
    'macaroni and cheese': '#efb435',
    'pinkish tan': '#d99b82',
    'spruce': '#0a5f38',
    'strong blue': '#0c06f7',
    'toxic green': '#61de2a',
    'windows blue': '#3778bf',
    'blue blue': '#2242c7',
    'blue with a hint of purple': '#533cc6',
    'booger': '#9bb53c',
    'bright sea green': '#05ffa6',
    'dark green blue': '#1f6357',
    'deep turquoise': '#017374',
    'green teal': '#0cb577',
    'strong pink': '#ff0789',
    'bland': '#afa88b',
    'deep aqua': '#08787f',
    'lavender pink': '#dd85d7',
    'light moss green': '#a6c875',
    'light seafoam green': '#a7ffb5',
    'olive yellow': '#c2b709',
    'pig pink': '#e78ea5',
    'deep lilac': '#966ebd',
    'desert': '#ccad60',
    'dusty lavender': '#ac86a8',
    'purpley grey': '#947e94',
    'purply': '#983fb2',
    'candy pink': '#ff63e9',
    'light pastel green': '#b2fba5',
    'boring green': '#63b365',
    'kiwi green': '#8ee53f',
    'light grey green': '#b7e1a1',
    'orange pink': '#ff6f52',
    'tea green': '#bdf8a3',
    'very light brown': '#d3b683',
    'egg shell': '#fffcc4',
    'eggplant purple': '#430541',
    'powder pink': '#ffb2d0',
    'reddish grey': '#997570',
    'baby shit brown': '#ad900d',
    'liliac': '#c48efd',
    'stormy blue': '#507b9c',
    'ugly brown': '#7d7103',
    'custard': '#fffd78',
    'darkish pink': '#da467d',
    'deep brown': '#410200',
    'greenish beige': '#c9d179',
    'manilla': '#fffa86',
    'off blue': '#5684ae',
    'battleship grey': '#6b7c85',
    'browny green': '#6f6c0a',
    'bruise': '#7e4071',
    'kelley green': '#009337',
    'sickly yellow': '#d0e429',
    'sunny yellow': '#fff917',
    'azul': '#1d5dec',
    'darkgreen': '#054907',
    'green/yellow': '#b5ce08',
    'lichen': '#8fb67b',
    'light light green': '#c8ffb0',
    'pale gold': '#fdde6c',
    'sun yellow': '#ffdf22',
    'tan green': '#a9be70',
    'burple': '#6832e3',
    'butterscotch': '#fdb147',
    'toupe': '#c7ac7d',
    'dark cream': '#fff39a',
    'indian red': '#850e04',
    'light lavendar': '#efc0fe',
    'poison green': '#40fd14',
    'baby puke green': '#b6c406',
    'bright yellow green': '#9dff00',
    'charcoal grey': '#3c4142',
    'squash': '#f2ab15',
    'cinnamon': '#ac4f06',
    'light pea green': '#c4fe82',
    'radioactive green': '#2cfa1f',
    'raw sienna': '#9a6200',
    'baby purple': '#ca9bf7',
    'cocoa': '#875f42',
    'light royal blue': '#3a2efe',
    'orangeish': '#fd8d49',
    'rust brown': '#8b3103',
    'sand brown': '#cba560',
    'swamp': '#698339',
    'tealish green': '#0cdc73',
    'burnt siena': '#b75203',
    'camo': '#7f8f4e',
    'dusk blue': '#26538d',
    'fern': '#63a950',
    'old rose': '#c87f89',
    'pale light green': '#b1fc99',
    'peachy pink': '#ff9a8a',
    'rosy pink': '#f6688e',
    'light bluish green': '#76fda8',
    'light bright green': '#53fe5c',
    'light neon green': '#4efd54',
    'light seafoam': '#a0febf',
    'tiffany blue': '#7bf2da',
    'washed out green': '#bcf5a6',
    'browny orange': '#ca6b02',
    'nice blue': '#107ab0',
    'sapphire': '#2138ab',
    'greyish teal': '#719f91',
    'orangey yellow': '#fdb915',
    'parchment': '#fefcaf',
    'straw': '#fcf679',
    'very dark brown': '#1d0200',
    'terracota': '#cb6843',
    'ugly blue': '#31668a',
    'clear blue': '#247afd',
    'creme': '#ffffb6',
    'foam green': '#90fda9',
    'grey/green': '#86a17d',
    'light gold': '#fddc5c',
    'seafoam blue': '#78d1b6',
    'topaz': '#13bbaf',
    'violet pink': '#fb5ffc',
    'wintergreen': '#20f986',
    'yellow tan': '#ffe36e',
    'dark fuchsia': '#9d0759',
    'indigo blue': '#3a18b1',
    'light yellowish green': '#c2ff89',
    'pale magenta': '#d767ad',
    'rich purple': '#720058',
    'sunflower yellow': '#ffda03',
    'green/blue': '#01c08d',
    'leather': '#ac7434',
    'racing green': '#014600',
    'vivid purple': '#9900fa',
    'dark royal blue': '#02066f',
    'hazel': '#8e7618',
    'muted pink': '#d1768f',
    'booger green': '#96b403',
    'canary': '#fdff63',
    'cool grey': '#95a3a6',
    'dark taupe': '#7f684e',
    'darkish purple': '#751973',
    'true green': '#089404',
    'coral pink': '#ff6163',
    'dark sage': '#598556',
    'dark slate blue': '#214761',
    'flat blue': '#3c73a8',
    'mushroom': '#ba9e88',
    'rich blue': '#021bf9',
    'dirty purple': '#734a65',
    'greenblue': '#23c48b',
    'icky green': '#8fae22',
    'light khaki': '#e6f2a2',
    'warm blue': '#4b57db',
    'dark hot pink': '#d90166',
    'deep sea blue': '#015482',
    'carmine': '#9d0216',
    'dark yellow green': '#728f02',
    'pale peach': '#ffe5ad',
    'plum purple': '#4e0550',
    'golden rod': '#f9bc08',
    'neon red': '#ff073a',
    'old pink': '#c77986',
    'very pale blue': '#d6fffe',
    'blood orange': '#fe4b03',
    'grapefruit': '#fd5956',
    'sand yellow': '#fce166',
    'clay brown': '#b2713d',
    'dark blue grey': '#1f3b4d',
    'flat green': '#699d4c',
    'light green blue': '#56fca2',
    'warm pink': '#fb5581',
    'dodger blue': '#3e82fc',
    'gross green': '#a0bf16',
    'ice': '#d6fffa',
    'metallic blue': '#4f738e',
    'pale salmon': '#ffb19a',
    'sap green': '#5c8b15',
    'algae': '#54ac68',
    'bluey grey': '#89a0b0',
    'greeny grey': '#7ea07a',
    'highlighter green': '#1bfc06',
    'light light blue': '#cafffb',
    'light mint': '#b6ffbb',
    'raw umber': '#a75e09',
    'vivid blue': '#152eff',
    'deep lavender': '#8d5eb7',
    'dull teal': '#5f9e8f',
    'light greenish blue': '#63f7b4',
    'mud green': '#606602',
    'pinky': '#fc86aa',
    'red wine': '#8c0034',
    'shit green': '#758000',
    'tan brown': '#ab7e4c',
    'darkblue': '#030764',
    'rosa': '#fe86a4',
    'lipstick': '#d5174e',
    'pale mauve': '#fed0fc',
    'claret': '#680018',
    'dandelion': '#fedf08',
    'orangered': '#fe420f',
    'poop green': '#6f7c00',
    'ruby': '#ca0147',
    'dark': '#1b2431',
    'greenish turquoise': '#00fbb0',
    'pastel red': '#db5856',
    'piss yellow': '#ddd618',
    'bright cyan': '#41fdfe',
    'dark coral': '#cf524e',
    'algae green': '#21c36f',
    'darkish red': '#a90308',
    'reddy brown': '#6e1005',
    'blush pink': '#fe828c',
    'camouflage green': '#4b6113',
    'lawn green': '#4da409',
    'putty': '#beae8a',
    'vibrant blue': '#0339f8',
    'dark sand': '#a88f59',
    'purple/blue': '#5d21d0',
    'saffron': '#feb209',
    'twilight': '#4e518b',
    'warm brown': '#964e02',
    'bluegrey': '#85a3b2',
    'bubble gum pink': '#ff69af',
    'duck egg blue': '#c3fbf4',
    'greenish cyan': '#2afeb7',
    'petrol': '#005f6a',
    'royal': '#0c1793',
    'butter': '#ffff81',
    'dusty orange': '#f0833a',
    'off yellow': '#f1f33f',
    'pale olive green': '#b1d27b',
    'orangish': '#fc824a',
    'leaf': '#71aa34',
    'light blue grey': '#b7c9e2',
    'dried blood': '#4b0101',
    'lightish purple': '#a552e6',
    'rusty red': '#af2f0d',
    'lavender blue': '#8b88f8',
    'light grass green': '#9af764',
    'light mint green': '#a6fbb2',
    'sunflower': '#ffc512',
    'velvet': '#750851',
    'brick orange': '#c14a09',
    'lightish red': '#fe2f4a',
    'pure blue': '#0203e2',
    'twilight blue': '#0a437a',
    'violet red': '#a50055',
    'yellowy brown': '#ae8b0c',
    'carnation': '#fd798f',
    'muddy yellow': '#bfac05',
    'dark seafoam green': '#3eaf76',
    'deep rose': '#c74767',
    'dusty red': '#b9484e',
    'grey/blue': '#647d8e',
    'lemon lime': '#bffe28',
    'purple/pink': '#d725de',
    'brown yellow': '#b29705',
    'purple brown': '#673a3f',
    'wisteria': '#a87dc2',
    'banana yellow': '#fafe4b',
    'lipstick red': '#c0022f',
    'water blue': '#0e87cc',
    'brown grey': '#8d8468',
    'vibrant purple': '#ad03de',
    'baby green': '#8cff9e',
    'barf green': '#94ac02',
    'eggshell blue': '#c4fff7',
    'sandy yellow': '#fdee73',
    'cool green': '#33b864',
    'pale': '#fff9d0',
    'blue/grey': '#758da3',
    'hot magenta': '#f504c9',
    'greyblue': '#77a1b5',
    'purpley': '#8756e4',
    'baby shit green': '#889717',
    'brownish pink': '#c27e79',
    'dark aquamarine': '#017371',
    'diarrhea': '#9f8303',
    'light mustard': '#f7d560',
    'pale sky blue': '#bdf6fe',
    'turtle green': '#75b84f',
    'bright olive': '#9cbb04',
    'dark grey blue': '#29465b',
    'greeny brown': '#696006',
    'lemon green': '#adf802',
    'light periwinkle': '#c1c6fc',
    'seaweed green': '#35ad6b',
    'sunshine yellow': '#fffd37',
    'ugly purple': '#a442a0',
    'medium pink': '#f36196',
    'puke brown': '#947706',
    'very light pink': '#fff4f2',
    'viridian': '#1e9167',
    'bile': '#b5c306',
    'faded yellow': '#feff7f',
    'very pale green': '#cffdbc',
    'vibrant green': '#0add08',
    'bright lime': '#87fd05',
    'spearmint': '#1ef876',
    'light aquamarine': '#7bfdc7',
    'light sage': '#bcecac',
    'yellowgreen': '#bbf90f',
    'baby poo': '#ab9004',
    'dark seafoam': '#1fb57a',
    'deep teal': '#00555a',
    'heather': '#a484ac',
    'rust orange': '#c45508',
    'dirty blue': '#3f829d',
    'fern green': '#548d44',
    'bright lilac': '#c95efb',
    'weird green': '#3ae57f',
    'peacock blue': '#016795',
    'avocado green': '#87a922',
    'faded orange': '#f0944d',
    'grape purple': '#5d1451',
    'hot green': '#25ff29',
    'lime yellow': '#d0fe1d',
    'mango': '#ffa62b',
    'shamrock': '#01b44c',
    'bubblegum': '#ff6cb5',
    'purplish brown': '#6b4247',
    'vomit yellow': '#c7c10c',
    'pale cyan': '#b7fffa',
    'key lime': '#aeff6e',
    'tomato red': '#ec2d01',
    'lightgreen': '#76ff7b',
    'merlot': '#730039',
    'night blue': '#040348',
    'purpleish pink': '#df4ec8',
    'apple': '#6ecb3c',
    'baby poop green': '#8f9805',
    'green apple': '#5edc1f',
    'heliotrope': '#d94ff5',
    'yellow/green': '#c8fd3d',
    'almost black': '#070d0d',
    'cool blue': '#4984b8',
    'leafy green': '#51b73b',
    'mustard brown': '#ac7e04',
    'dusk': '#4e5481',
    'dull brown': '#876e4b',
    'frog green': '#58bc08',
    'vivid green': '#2fef10',
    'bright light green': '#2dfe54',
    'fluro green': '#0aff02',
    'kiwi': '#9cef43',
    'seaweed': '#18d17b',
    'navy green': '#35530a',
    'ultramarine blue': '#1805db',
    'iris': '#6258c4',
    'pastel orange': '#ff964f',
    'yellowish orange': '#ffab0f',
    'perrywinkle': '#8f8ce7',
    'tealish': '#24bca8',
    'dark plum': '#3f012c',
    'pear': '#cbf85f',
    'pinkish orange': '#ff724c',
    'midnight purple': '#280137',
    'light urple': '#b36ff6',
    'dark mint': '#48c072',
    'greenish tan': '#bccb7a',
    'light burgundy': '#a8415b',
    'turquoise blue': '#06b1c4',
    'ugly pink': '#cd7584',
    'sandy': '#f1da7a',
    'electric pink': '#ff0490',
    'muted purple': '#805b87',
    'mid green': '#50a747',
    'greyish': '#a8a495',
    'neon yellow': '#cfff04',
    'banana': '#ffff7e',
    'carnation pink': '#ff7fa7',
    'tomato': '#ef4026',
    'sea': '#3c9992',
    'muddy brown': '#886806',
    'turquoise green': '#04f489',
    'buff': '#fef69e',
    'fawn': '#cfaf7b',
    'muted blue': '#3b719f',
    'pale rose': '#fdc1c5',
    'dark mint green': '#20c073',
    'amethyst': '#9b5fc0',
    'blue/green': '#0f9b8e',
    'chestnut': '#742802',
    'sick green': '#9db92c',
    'pea': '#a4bf20',
    'rusty orange': '#cd5909',
    'stone': '#ada587',
    'rose red': '#be013c',
    'pale aqua': '#b8ffeb',
    'deep orange': '#dc4d01',
    'earth': '#a2653e',
    'mossy green': '#638b27',
    'grassy green': '#419c03',
    'pale lime green': '#b1ff65',
    'light grey blue': '#9dbcd4',
    'pale grey': '#fdfdfe',
    'asparagus': '#77ab56',
    'blueberry': '#464196',
    'purple red': '#990147',
    'pale lime': '#befd73',
    'greenish teal': '#32bf84',
    'caramel': '#af6f09',
    'deep magenta': '#a0025c',
    'light peach': '#ffd8b1',
    'milk chocolate': '#7f4e1e',
    'ocher': '#bf9b0c',
    'off green': '#6ba353',
    'purply pink': '#f075e6',
    'lightblue': '#7bc8f6',
    'dusky blue': '#475f94',
    'golden': '#f5bf03',
    'light beige': '#fffeb6',
    'butter yellow': '#fffd74',
    'dusky purple': '#895b7b',
    'french blue': '#436bad',
    'ugly yellow': '#d0c101',
    'greeny yellow': '#c6f808',
    'orangish red': '#f43605',
    'shamrock green': '#02c14d',
    'orangish brown': '#b25f03',
    'tree green': '#2a7e19',
    'deep violet': '#490648',
    'gunmetal': '#536267',
    'blue/purple': '#5a06ef',
    'cherry': '#cf0234',
    'sandy brown': '#c4a661',
    'warm grey': '#978a84',
    'dark indigo': '#1f0954',
    'midnight': '#03012d',
    'bluey green': '#2bb179',
    'grey pink': '#c3909b',
    'soft purple': '#a66fb5',
    'blood': '#770001',
    'brown red': '#922b05',
    'medium grey': '#7d7f7c',
    'berry': '#990f4b',
    'poo': '#8f7303',
    'purpley pink': '#c83cb9',
    'light salmon': '#fea993',
    'snot': '#acbb0d',
    'easter purple': '#c071fe',
    'light yellow green': '#ccfd7f',
    'dark navy blue': '#00022e',
    'drab': '#828344',
    'light rose': '#ffc5cb',
    'rouge': '#ab1239',
    'purplish red': '#b0054b',
    'slime green': '#99cc04',
    'baby poop': '#937c00',
    'irish green': '#019529',
    'pink/purple': '#ef1de7',
    'dark navy': '#000435',
    'greeny blue': '#42b395',
    'light plum': '#9d5783',
    'pinkish grey': '#c8aca9',
    'dirty orange': '#c87606',
    'rust red': '#aa2704',
    'pale lilac': '#e4cbff',
    'orangey red': '#fa4224',
    'primary blue': '#0804f9',
    'kermit green': '#5cb200',
    'brownish purple': '#76424e',
    'murky green': '#6c7a0e',
    'wheat': '#fbdd7e',
    'very dark purple': '#2a0134',
    'bottle green': '#044a05',
    'watermelon': '#fd4659',
    'deep sky blue': '#0d75f8',
    'fire engine red': '#fe0002',
    'yellow ochre': '#cb9d06',
    'pumpkin orange': '#fb7d07',
    'pale olive': '#b9cc81',
    'light lilac': '#edc8ff',
    'lightish green': '#61e160',
    'carolina blue': '#8ab8fe',
    'mulberry': '#920a4e',
    'shocking pink': '#fe02a2',
    'auburn': '#9a3001',
    'bright lime green': '#65fe08',
    'celadon': '#befdb7',
    'pinkish brown': '#b17261',
    'poo brown': '#885f01',
    'bright sky blue': '#02ccfe',
    'celery': '#c1fd95',
    'dirt brown': '#836539',
    'strawberry': '#fb2943',
    'dark lime': '#84b701',
    'copper': '#b66325',
    'medium brown': '#7f5112',
    'muted green': '#5fa052',
    "robin's egg": '#6dedfd',
    'bright aqua': '#0bf9ea',
    'bright lavender': '#c760ff',
    'ivory': '#ffffcb',
    'very light purple': '#f6cefc',
    'light navy': '#155084',
    'pink red': '#f5054f',
    'olive brown': '#645403',
    'poop brown': '#7a5901',
    'mustard green': '#a8b504',
    'ocean green': '#3d9973',
    'very dark blue': '#000133',
    'dusty green': '#76a973',
    'light navy blue': '#2e5a88',
    'minty green': '#0bf77d',
    'adobe': '#bd6c48',
    'barney': '#ac1db8',
    'jade green': '#2baf6a',
    'bright light blue': '#26f7fd',
    'light lime': '#aefd6c',
    'dark khaki': '#9b8f55',
    'orange yellow': '#ffad01',
    'ocre': '#c69c04',
    'maize': '#f4d054',
    'faded pink': '#de9dac',
    'british racing green': '#05480d',
    'sandstone': '#c9ae74',
    'mud brown': '#60460f',
    'light sea green': '#98f6b0',
    'robin egg blue': '#8af1fe',
    'aqua marine': '#2ee8bb',
    'dark sea green': '#11875d',
    'soft pink': '#fdb0c0',
    'orangey brown': '#b16002',
    'cherry red': '#f7022a',
    'burnt yellow': '#d5ab09',
    'brownish grey': '#86775f',
    'camel': '#c69f59',
    'purplish grey': '#7a687f',
    'marine': '#042e60',
    'greyish pink': '#c88d94',
    'pale turquoise': '#a5fbd5',
    'pastel yellow': '#fffe71',
    'bluey purple': '#6241c7',
    'canary yellow': '#fffe40',
    'faded red': '#d3494e',
    'sepia': '#985e2b',
    'coffee': '#a6814c',
    'bright magenta': '#ff08e8',
    'mocha': '#9d7651',
    'ecru': '#feffca',
    'purpleish': '#98568d',
    'cranberry': '#9e003a',
    'darkish green': '#287c37',
    'brown orange': '#b96902',
    'dusky rose': '#ba6873',
    'melon': '#ff7855',
    'sickly green': '#94b21c',
    'silver': '#c5c9c7',
    'purply blue': '#661aee',
    'purpleish blue': '#6140ef',
    'hospital green': '#9be5aa',
    'shit brown': '#7b5804',
    'mid blue': '#276ab3',
    'amber': '#feb308',
    'easter green': '#8cfd7e',
    'soft blue': '#6488ea',
    'cerulean blue': '#056eee',
    'golden brown': '#b27a01',
    'bright turquoise': '#0ffef9',
    'red pink': '#fa2a55',
    'red purple': '#820747',
    'greyish brown': '#7a6a4f',
    'vermillion': '#f4320c',
    'russet': '#a13905',
    'steel grey': '#6f828a',
    'lighter purple': '#a55af4',
    'bright violet': '#ad0afd',
    'prussian blue': '#004577',
    'slate green': '#658d6d',
    'dirty pink': '#ca7b80',
    'dark blue green': '#005249',
    'pine': '#2b5d34',
    'yellowy green': '#bff128',
    'dark gold': '#b59410',
    'bluish': '#2976bb',
    'darkish blue': '#014182',
    'dull red': '#bb3f3f',
    'pinky red': '#fc2647',
    'bronze': '#a87900',
    'pale teal': '#82cbb2',
    'military green': '#667c3e',
    'barbie pink': '#fe46a5',
    'bubblegum pink': '#fe83cc',
    'pea soup green': '#94a617',
    'dark mustard': '#a88905',
    'shit': '#7f5f00',
    'medium purple': '#9e43a2',
    'very dark green': '#062e03',
    'dirt': '#8a6e45',
    'dusky pink': '#cc7a8b',
    'red violet': '#9e0168',
    'lemon yellow': '#fdff38',
    'pistachio': '#c0fa8b',
    'dull yellow': '#eedc5b',
    'dark lime green': '#7ebd01',
    'denim blue': '#3b5b92',
    'teal blue': '#01889f',
    'lightish blue': '#3d7afd',
    'purpley blue': '#5f34e7',
    'light indigo': '#6d5acf',
    'swamp green': '#748500',
    'brown green': '#706c11',
    'dark maroon': '#3c0008',
    'hot purple': '#cb00f5',
    'dark forest green': '#002d04',
    'faded blue': '#658cbb',
    'drab green': '#749551',
    'light lime green': '#b9ff66',
    'snot green': '#9dc100',
    'yellowish': '#faee66',
    'light blue green': '#7efbb3',
    'bordeaux': '#7b002c',
    'light mauve': '#c292a1',
    'ocean': '#017b92',
    'marigold': '#fcc006',
    'muddy green': '#657432',
    'dull orange': '#d8863b',
    'steel': '#738595',
    'electric purple': '#aa23ff',
    'fluorescent green': '#08ff08',
    'yellowish brown': '#9b7a01',
    'blush': '#f29e8e',
    'soft green': '#6fc276',
    'bright orange': '#ff5b00',
    'lemon': '#fdff52',
    'purple grey': '#866f85',
    'acid green': '#8ffe09',
    'pale lavender': '#eecffe',
    'violet blue': '#510ac9',
    'light forest green': '#4f9153',
    'burnt red': '#9f2305',
    'khaki green': '#728639',
    'cerise': '#de0c62',
    'faded purple': '#916e99',
    'apricot': '#ffb16d',
    'dark olive green': '#3c4d03',
    'grey brown': '#7f7053',
    'green grey': '#77926f',
    'true blue': '#010fcc',
    'pale violet': '#ceaefa',
    'periwinkle blue': '#8f99fb',
    'light sky blue': '#c6fcff',
    'blurple': '#5539cc',
    'green brown': '#544e03',
    'bluegreen': '#017a79',
    'bright teal': '#01f9c6',
    'brownish yellow': '#c9b003',
    'pea soup': '#929901',
    'forest': '#0b5509',
    'barney purple': '#a00498',
    'ultramarine': '#2000b1',
    'purplish': '#94568c',
    'puke yellow': '#c2be0e',
    'bluish grey': '#748b97',
    'dark periwinkle': '#665fd1',
    'dark lilac': '#9c6da5',
    'reddish': '#c44240',
    'light maroon': '#a24857',
    'dusty purple': '#825f87',
    'terra cotta': '#c9643b',
    'avocado': '#90b134',
    'marine blue': '#01386a',
    'teal green': '#25a36f',
    'slate grey': '#59656d',
    'lighter green': '#75fd63',
    'electric green': '#21fc0d',
    'dusty blue': '#5a86ad',
    'golden yellow': '#fec615',
    'bright yellow': '#fffd01',
    'light lavender': '#dfc5fe',
    'umber': '#b26400',
    'poop': '#7f5e00',
    'dark peach': '#de7e5d',
    'jungle green': '#048243',
    'eggshell': '#ffffd4',
    'denim': '#3b638c',
    'yellow brown': '#b79400',
    'dull purple': '#84597e',
    'chocolate brown': '#411900',
    'wine red': '#7b0323',
    'neon blue': '#04d9ff',
    'dirty green': '#667e2c',
    'light tan': '#fbeeac',
    'ice blue': '#d7fffe',
    'cadet blue': '#4e7496',
    'dark mauve': '#874c62',
    'very light blue': '#d5ffff',
    'grey purple': '#826d8c',
    'pastel pink': '#ffbacd',
    'very light green': '#d1ffbd',
    'dark sky blue': '#448ee4',
    'evergreen': '#05472a',
    'dull pink': '#d5869d',
    'aubergine': '#3d0734',
    'mahogany': '#4a0100',
    'reddish orange': '#f8481c',
    'deep green': '#02590f',
    'vomit green': '#89a203',
    'purple pink': '#e03fd8',
    'dusty pink': '#d58a94',
    'faded green': '#7bb274',
    'camo green': '#526525',
    'pinky purple': '#c94cbe',
    'pink purple': '#db4bda',
    'brownish red': '#9e3623',
    'dark rose': '#b5485d',
    'mud': '#735c12',
    'brownish': '#9c6d57',
    'emerald green': '#028f1e',
    'pale brown': '#b1916e',
    'dull blue': '#49759c',
    'burnt umber': '#a0450e',
    'medium green': '#39ad48',
    'clay': '#b66a50',
    'light aqua': '#8cffdb',
    'light olive green': '#a4be5c',
    'brownish orange': '#cb7723',
    'dark aqua': '#05696b',
    'purplish pink': '#ce5dae',
    'dark salmon': '#c85a53',
    'greenish grey': '#96ae8d',
    'jade': '#1fa774',
    'ugly green': '#7a9703',
    'dark beige': '#ac9362',
    'emerald': '#01a049',
    'pale red': '#d9544d',
    'light magenta': '#fa5ff7',
    'sky': '#82cafc',
    'light cyan': '#acfffc',
    'yellow orange': '#fcb001',
    'reddish purple': '#910951',
    'reddish pink': '#fe2c54',
    'orchid': '#c875c4',
    'dirty yellow': '#cdc50a',
    'orange red': '#fd411e',
    'deep red': '#9a0200',
    'orange brown': '#be6400',
    'cobalt blue': '#030aa7',
    'neon pink': '#fe019a',
    'rose pink': '#f7879a',
    'greyish purple': '#887191',
    'raspberry': '#b00149',
    'aqua green': '#12e193',
    'salmon pink': '#fe7b7c',
    'tangerine': '#ff9408',
    'brownish green': '#6a6e09',
    'red brown': '#8b2e16',
    'greenish brown': '#696112',
    'pumpkin': '#e17701',
    'pine green': '#0a481e',
    'charcoal': '#343837',
    'baby pink': '#ffb7ce',
    'cornflower': '#6a79f7',
    'blue violet': '#5d06e9',
    'chocolate': '#3d1c02',
    'greyish green': '#82a67d',
    'scarlet': '#be0119',
    'green yellow': '#c9ff27',
    'dark olive': '#373e02',
    'sienna': '#a9561e',
    'pastel purple': '#caa0ff',
    'terracotta': '#ca6641',
    'aqua blue': '#02d8e9',
    'sage green': '#88b378',
    'blood red': '#980002',
    'deep pink': '#cb0162',
    'grass': '#5cac2d',
    'moss': '#769958',
    'pastel blue': '#a2bffe',
    'bluish green': '#10a674',
    'green blue': '#06b48b',
    'dark tan': '#af884a',
    'greenish blue': '#0b8b87',
    'pale orange': '#ffa756',
    'vomit': '#a2a415',
    'forrest green': '#154406',
    'dark lavender': '#856798',
    'dark violet': '#34013f',
    'purple blue': '#632de9',
    'dark cyan': '#0a888a',
    'olive drab': '#6f7632',
    'pinkish': '#d46a7e',
    'cobalt': '#1e488f',
    'neon purple': '#bc13fe',
    'light turquoise': '#7ef4cc',
    'apple green': '#76cd26',
    'dull green': '#74a662',
    'wine': '#80013f',
    'powder blue': '#b1d1fc',
    'off white': '#ffffe4',
    'electric blue': '#0652ff',
    'dark turquoise': '#045c5a',
    'blue purple': '#5729ce',
    'azure': '#069af3',
    'bright red': '#ff000d',
    'pinkish red': '#f10c45',
    'cornflower blue': '#5170d7',
    'light olive': '#acbf69',
    'grape': '#6c3461',
    'greyish blue': '#5e819d',
    'purplish blue': '#601ef9',
    'yellowish green': '#b0dd16',
    'greenish yellow': '#cdfd02',
    'medium blue': '#2c6fbb',
    'dusty rose': '#c0737a',
    'light violet': '#d6b4fc',
    'midnight blue': '#020035',
    'bluish purple': '#703be7',
    'red orange': '#fd3c06',
    'dark magenta': '#960056',
    'greenish': '#40a368',
    'ocean blue': '#03719c',
    'coral': '#fc5a50',
    'cream': '#ffffc2',
    'reddish brown': '#7f2b0a',
    'burnt sienna': '#b04e0f',
    'brick': '#a03623',
    'sage': '#87ae73',
    'grey green': '#789b73',
    'white': '#ffffff',
    "robin's egg blue": '#98eff9',
    'moss green': '#658b38',
    'steel blue': '#5a7d9a',
    'eggplant': '#380835',
    'light yellow': '#fffe7a',
    'leaf green': '#5ca904',
    'light grey': '#d8dcd6',
    'puke': '#a5a502',
    'pinkish purple': '#d648d7',
    'sea blue': '#047495',
    'pale purple': '#b790d4',
    'slate blue': '#5b7c99',
    'blue grey': '#607c8e',
    'hunter green': '#0b4008',
    'fuchsia': '#ed0dd9',
    'crimson': '#8c000f',
    'pale yellow': '#ffff84',
    'ochre': '#bf9005',
    'mustard yellow': '#d2bd0a',
    'light red': '#ff474c',
    'cerulean': '#0485d1',
    'pale pink': '#ffcfdc',
    'deep blue': '#040273',
    'rust': '#a83c09',
    'light teal': '#90e4c1',
    'slate': '#516572',
    'goldenrod': '#fac205',
    'dark yellow': '#d5b60a',
    'dark grey': '#363737',
    'army green': '#4b5d16',
    'grey blue': '#6b8ba4',
    'seafoam': '#80f9ad',
    'puce': '#a57e52',
    'spring green': '#a9f971',
    'dark orange': '#c65102',
    'sand': '#e2ca76',
    'pastel green': '#b0ff9d',
    'mint': '#9ffeb0',
    'light orange': '#fdaa48',
    'bright pink': '#fe01b1',
    'chartreuse': '#c1f80a',
    'deep purple': '#36013f',
    'dark brown': '#341c02',
    'taupe': '#b9a281',
    'pea green': '#8eab12',
    'puke green': '#9aae07',
    'kelly green': '#02ab2e',
    'seafoam green': '#7af9ab',
    'blue green': '#137e6d',
    'khaki': '#aaa662',
    'burgundy': '#610023',
    'dark teal': '#014d4e',
    'brick red': '#8f1402',
    'royal purple': '#4b006e',
    'plum': '#580f41',
    'mint green': '#8fff9f',
    'gold': '#dbb40c',
    'baby blue': '#a2cffe',
    'yellow green': '#c0fb2d',
    'bright purple': '#be03fd',
    'dark red': '#840000',
    'pale blue': '#d0fefe',
    'grass green': '#3f9b0b',
    'navy': '#01153e',
    'aquamarine': '#04d8b2',
    'burnt orange': '#c04e01',
    'neon green': '#0cff0c',
    'bright blue': '#0165fc',
    'rose': '#cf6275',
    'light pink': '#ffd1df',
    'mustard': '#ceb301',
    'indigo': '#380282',
    'lime': '#aaff32',
    'sea green': '#53fca1',
    'periwinkle': '#8e82fe',
    'dark pink': '#cb416b',
    'olive green': '#677a04',
    'peach': '#ffb07c',
    'pale green': '#c7fdb5',
    'light brown': '#ad8150',
    'hot pink': '#ff028d',
    'black': '#000000',
    'lilac': '#cea2fd',
    'navy blue': '#001146',
    'royal blue': '#0504aa',
    'beige': '#e6daa6',
    'salmon': '#ff796c',
    'olive': '#6e750e',
    'maroon': '#650021',
    'bright green': '#01ff07',
    'dark purple': '#35063e',
    'mauve': '#ae7181',
    'forest green': '#06470c',
    'aqua': '#13eac9',
    'cyan': '#00ffff',
    'tan': '#d1b26f',
    'dark blue': '#00035b',
    'lavender': '#c79fef',
    'turquoise': '#06c2ac',
    'dark green': '#033500',
    'violet': '#9a0eea',
    'light purple': '#bf77f6',
    'lime green': '#89fe05',
    'grey': '#929591',
    'sky blue': '#75bbfd',
    'yellow': '#ffff14',
    'magenta': '#c20078',
    'light green': '#96f97b',
    'orange': '#f97306',
    'teal': '#029386',
    'light blue': '#95d0fc',
    'red': '#e50000',
    'brown': '#653700',
    'pink': '#ff81c0',
    'blue': '#0343df',
    'green': '#15b01a',
    'purple': '#7e1e9c'}

# Normalize name to "xkcd:<name>" to avoid name collisions.
XKCD_COLORS = {'xkcd:' + name: value for name, value in XKCD_COLORS.items()}


# https://drafts.csswg.org/css-color-4/#named-colors
CSS4_COLORS = {
    'aliceblue':            '#F0F8FF',
    'antiquewhite':         '#FAEBD7',
    'aqua':                 '#00FFFF',
    'aquamarine':           '#7FFFD4',
    'azure':                '#F0FFFF',
    'beige':                '#F5F5DC',
    'bisque':               '#FFE4C4',
    'black':                '#000000',
    'blanchedalmond':       '#FFEBCD',
    'blue':                 '#0000FF',
    'blueviolet':           '#8A2BE2',
    'brown':                '#A52A2A',
    'burlywood':            '#DEB887',
    'cadetblue':            '#5F9EA0',
    'chartreuse':           '#7FFF00',
    'chocolate':            '#D2691E',
    'coral':                '#FF7F50',
    'cornflowerblue':       '#6495ED',
    'cornsilk':             '#FFF8DC',
    'crimson':              '#DC143C',
    'cyan':                 '#00FFFF',
    'darkblue':             '#00008B',
    'darkcyan':             '#008B8B',
    'darkgoldenrod':        '#B8860B',
    'darkgray':             '#A9A9A9',
    'darkgreen':            '#006400',
    'darkgrey':             '#A9A9A9',
    'darkkhaki':            '#BDB76B',
    'darkmagenta':          '#8B008B',
    'darkolivegreen':       '#556B2F',
    'darkorange':           '#FF8C00',
    'darkorchid':           '#9932CC',
    'darkred':              '#8B0000',
    'darksalmon':           '#E9967A',
    'darkseagreen':         '#8FBC8F',
    'darkslateblue':        '#483D8B',
    'darkslategray':        '#2F4F4F',
    'darkslategrey':        '#2F4F4F',
    'darkturquoise':        '#00CED1',
    'darkviolet':           '#9400D3',
    'deeppink':             '#FF1493',
    'deepskyblue':          '#00BFFF',
    'dimgray':              '#696969',
    'dimgrey':              '#696969',
    'dodgerblue':           '#1E90FF',
    'firebrick':            '#B22222',
    'floralwhite':          '#FFFAF0',
    'forestgreen':          '#228B22',
    'fuchsia':              '#FF00FF',
    'gainsboro':            '#DCDCDC',
    'ghostwhite':           '#F8F8FF',
    'gold':                 '#FFD700',
    'goldenrod':            '#DAA520',
    'gray':                 '#808080',
    'green':                '#008000',
    'greenyellow':          '#ADFF2F',
    'grey':                 '#808080',
    'honeydew':             '#F0FFF0',
    'hotpink':              '#FF69B4',
    'indianred':            '#CD5C5C',
    'indigo':               '#4B0082',
    'ivory':                '#FFFFF0',
    'khaki':                '#F0E68C',
    'lavender':             '#E6E6FA',
    'lavenderblush':        '#FFF0F5',
    'lawngreen':            '#7CFC00',
    'lemonchiffon':         '#FFFACD',
    'lightblue':            '#ADD8E6',
    'lightcoral':           '#F08080',
    'lightcyan':            '#E0FFFF',
    'lightgoldenrodyellow': '#FAFAD2',
    'lightgray':            '#D3D3D3',
    'lightgreen':           '#90EE90',
    'lightgrey':            '#D3D3D3',
    'lightpink':            '#FFB6C1',
    'lightsalmon':          '#FFA07A',
    'lightseagreen':        '#20B2AA',
    'lightskyblue':         '#87CEFA',
    'lightslategray':       '#778899',
    'lightslategrey':       '#778899',
    'lightsteelblue':       '#B0C4DE',
    'lightyellow':          '#FFFFE0',
    'lime':                 '#00FF00',
    'limegreen':            '#32CD32',
    'linen':                '#FAF0E6',
    'magenta':              '#FF00FF',
    'maroon':               '#800000',
    'mediumaquamarine':     '#66CDAA',
    'mediumblue':           '#0000CD',
    'mediumorchid':         '#BA55D3',
    'mediumpurple':         '#9370DB',
    'mediumseagreen':       '#3CB371',
    'mediumslateblue':      '#7B68EE',
    'mediumspringgreen':    '#00FA9A',
    'mediumturquoise':      '#48D1CC',
    'mediumvioletred':      '#C71585',
    'midnightblue':         '#191970',
    'mintcream':            '#F5FFFA',
    'mistyrose':            '#FFE4E1',
    'moccasin':             '#FFE4B5',
    'navajowhite':          '#FFDEAD',
    'navy':                 '#000080',
    'oldlace':              '#FDF5E6',
    'olive':                '#808000',
    'olivedrab':            '#6B8E23',
    'orange':               '#FFA500',
    'orangered':            '#FF4500',
    'orchid':               '#DA70D6',
    'palegoldenrod':        '#EEE8AA',
    'palegreen':            '#98FB98',
    'paleturquoise':        '#AFEEEE',
    'palevioletred':        '#DB7093',
    'papayawhip':           '#FFEFD5',
    'peachpuff':            '#FFDAB9',
    'peru':                 '#CD853F',
    'pink':                 '#FFC0CB',
    'plum':                 '#DDA0DD',
    'powderblue':           '#B0E0E6',
    'purple':               '#800080',
    'rebeccapurple':        '#663399',
    'red':                  '#FF0000',
    'rosybrown':            '#BC8F8F',
    'royalblue':            '#4169E1',
    'saddlebrown':          '#8B4513',
    'salmon':               '#FA8072',
    'sandybrown':           '#F4A460',
    'seagreen':             '#2E8B57',
    'seashell':             '#FFF5EE',
    'sienna':               '#A0522D',
    'silver':               '#C0C0C0',
    'skyblue':              '#87CEEB',
    'slateblue':            '#6A5ACD',
    'slategray':            '#708090',
    'slategrey':            '#708090',
    'snow':                 '#FFFAFA',
    'springgreen':          '#00FF7F',
    'steelblue':            '#4682B4',
    'tan':                  '#D2B48C',
    'teal':                 '#008080',
    'thistle':              '#D8BFD8',
    'tomato':               '#FF6347',
    'turquoise':            '#40E0D0',
    'violet':               '#EE82EE',
    'wheat':                '#F5DEB3',
    'white':                '#FFFFFF',
    'whitesmoke':           '#F5F5F5',
    'yellow':               '#FFFF00',
    'yellowgreen':          '#9ACD32'}

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\urllib3\connectionpool.py ===
from __future__ import absolute_import

import errno
import logging
import re
import socket
import sys
import warnings
from socket import error as SocketError
from socket import timeout as SocketTimeout

from ._collections import HTTPHeaderDict
from .connection import (
    BaseSSLError,
    BrokenPipeError,
    DummyConnection,
    HTTPConnection,
    HTTPException,
    HTTPSConnection,
    VerifiedHTTPSConnection,
    port_by_scheme,
)
from .exceptions import (
    ClosedPoolError,
    EmptyPoolError,
    HeaderParsingError,
    HostChangedError,
    InsecureRequestWarning,
    LocationValueError,
    MaxRetryError,
    NewConnectionError,
    ProtocolError,
    ProxyError,
    ReadTimeoutError,
    SSLError,
    TimeoutError,
)
from .packages import six
from .packages.six.moves import queue
from .request import RequestMethods
from .response import HTTPResponse
from .util.connection import is_connection_dropped
from .util.proxy import connection_requires_http_tunnel
from .util.queue import LifoQueue
from .util.request import set_file_position
from .util.response import assert_header_parsing
from .util.retry import Retry
from .util.ssl_match_hostname import CertificateError
from .util.timeout import Timeout
from .util.url import Url, _encode_target
from .util.url import _normalize_host as normalize_host
from .util.url import get_host, parse_url

try:  # Platform-specific: Python 3
    import weakref

    weakref_finalize = weakref.finalize
except AttributeError:  # Platform-specific: Python 2
    from .packages.backports.weakref_finalize import weakref_finalize

xrange = six.moves.xrange

log = logging.getLogger(__name__)

_Default = object()


# Pool objects
class ConnectionPool(object):
    """
    Base class for all connection pools, such as
    :class:`.HTTPConnectionPool` and :class:`.HTTPSConnectionPool`.

    .. note::
       ConnectionPool.urlopen() does not normalize or percent-encode target URIs
       which is useful if your target server doesn't support percent-encoded
       target URIs.
    """

    scheme = None
    QueueCls = LifoQueue

    def __init__(self, host, port=None):
        if not host:
            raise LocationValueError("No host specified.")

        self.host = _normalize_host(host, scheme=self.scheme)
        self._proxy_host = host.lower()
        self.port = port

    def __str__(self):
        return "%s(host=%r, port=%r)" % (type(self).__name__, self.host, self.port)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        # Return False to re-raise any potential exceptions
        return False

    def close(self):
        """
        Close all pooled connections and disable the pool.
        """
        pass


# This is taken from http://hg.python.org/cpython/file/7aaba721ebc0/Lib/socket.py#l252
_blocking_errnos = {errno.EAGAIN, errno.EWOULDBLOCK}


class HTTPConnectionPool(ConnectionPool, RequestMethods):
    """
    Thread-safe connection pool for one host.

    :param host:
        Host used for this HTTP Connection (e.g. "localhost"), passed into
        :class:`http.client.HTTPConnection`.

    :param port:
        Port used for this HTTP Connection (None is equivalent to 80), passed
        into :class:`http.client.HTTPConnection`.

    :param strict:
        Causes BadStatusLine to be raised if the status line can't be parsed
        as a valid HTTP/1.0 or 1.1 status line, passed into
        :class:`http.client.HTTPConnection`.

        .. note::
           Only works in Python 2. This parameter is ignored in Python 3.

    :param timeout:
        Socket timeout in seconds for each individual connection. This can
        be a float or integer, which sets the timeout for the HTTP request,
        or an instance of :class:`urllib3.util.Timeout` which gives you more
        fine-grained control over request timeouts. After the constructor has
        been parsed, this is always a `urllib3.util.Timeout` object.

    :param maxsize:
        Number of connections to save that can be reused. More than 1 is useful
        in multithreaded situations. If ``block`` is set to False, more
        connections will be created but they will not be saved once they've
        been used.

    :param block:
        If set to True, no more than ``maxsize`` connections will be used at
        a time. When no free connections are available, the call will block
        until a connection has been released. This is a useful side effect for
        particular multithreaded situations where one does not want to use more
        than maxsize connections per host to prevent flooding.

    :param headers:
        Headers to include with all requests, unless other headers are given
        explicitly.

    :param retries:
        Retry configuration to use by default with requests in this pool.

    :param _proxy:
        Parsed proxy URL, should not be used directly, instead, see
        :class:`urllib3.ProxyManager`

    :param _proxy_headers:
        A dictionary with proxy headers, should not be used directly,
        instead, see :class:`urllib3.ProxyManager`

    :param \\**conn_kw:
        Additional parameters are used to create fresh :class:`urllib3.connection.HTTPConnection`,
        :class:`urllib3.connection.HTTPSConnection` instances.
    """

    scheme = "http"
    ConnectionCls = HTTPConnection
    ResponseCls = HTTPResponse

    def __init__(
        self,
        host,
        port=None,
        strict=False,
        timeout=Timeout.DEFAULT_TIMEOUT,
        maxsize=1,
        block=False,
        headers=None,
        retries=None,
        _proxy=None,
        _proxy_headers=None,
        _proxy_config=None,
        **conn_kw
    ):
        ConnectionPool.__init__(self, host, port)
        RequestMethods.__init__(self, headers)

        self.strict = strict

        if not isinstance(timeout, Timeout):
            timeout = Timeout.from_float(timeout)

        if retries is None:
            retries = Retry.DEFAULT

        self.timeout = timeout
        self.retries = retries

        self.pool = self.QueueCls(maxsize)
        self.block = block

        self.proxy = _proxy
        self.proxy_headers = _proxy_headers or {}
        self.proxy_config = _proxy_config

        # Fill the queue up so that doing get() on it will block properly
        for _ in xrange(maxsize):
            self.pool.put(None)

        # These are mostly for testing and debugging purposes.
        self.num_connections = 0
        self.num_requests = 0
        self.conn_kw = conn_kw

        if self.proxy:
            # Enable Nagle's algorithm for proxies, to avoid packet fragmentation.
            # We cannot know if the user has added default socket options, so we cannot replace the
            # list.
            self.conn_kw.setdefault("socket_options", [])

            self.conn_kw["proxy"] = self.proxy
            self.conn_kw["proxy_config"] = self.proxy_config

        # Do not pass 'self' as callback to 'finalize'.
        # Then the 'finalize' would keep an endless living (leak) to self.
        # By just passing a reference to the pool allows the garbage collector
        # to free self if nobody else has a reference to it.
        pool = self.pool

        # Close all the HTTPConnections in the pool before the
        # HTTPConnectionPool object is garbage collected.
        weakref_finalize(self, _close_pool_connections, pool)

    def _new_conn(self):
        """
        Return a fresh :class:`HTTPConnection`.
        """
        self.num_connections += 1
        log.debug(
            "Starting new HTTP connection (%d): %s:%s",
            self.num_connections,
            self.host,
            self.port or "80",
        )

        conn = self.ConnectionCls(
            host=self.host,
            port=self.port,
            timeout=self.timeout.connect_timeout,
            strict=self.strict,
            **self.conn_kw
        )
        return conn

    def _get_conn(self, timeout=None):
        """
        Get a connection. Will return a pooled connection if one is available.

        If no connections are available and :prop:`.block` is ``False``, then a
        fresh connection is returned.

        :param timeout:
            Seconds to wait before giving up and raising
            :class:`urllib3.exceptions.EmptyPoolError` if the pool is empty and
            :prop:`.block` is ``True``.
        """
        conn = None
        try:
            conn = self.pool.get(block=self.block, timeout=timeout)

        except AttributeError:  # self.pool is None
            raise ClosedPoolError(self, "Pool is closed.")

        except queue.Empty:
            if self.block:
                raise EmptyPoolError(
                    self,
                    "Pool reached maximum size and no more connections are allowed.",
                )
            pass  # Oh well, we'll create a new connection then

        # If this is a persistent connection, check if it got disconnected
        if conn and is_connection_dropped(conn):
            log.debug("Resetting dropped connection: %s", self.host)
            conn.close()
            if getattr(conn, "auto_open", 1) == 0:
                # This is a proxied connection that has been mutated by
                # http.client._tunnel() and cannot be reused (since it would
                # attempt to bypass the proxy)
                conn = None

        return conn or self._new_conn()

    def _put_conn(self, conn):
        """
        Put a connection back into the pool.

        :param conn:
            Connection object for the current host and port as returned by
            :meth:`._new_conn` or :meth:`._get_conn`.

        If the pool is already full, the connection is closed and discarded
        because we exceeded maxsize. If connections are discarded frequently,
        then maxsize should be increased.

        If the pool is closed, then the connection will be closed and discarded.
        """
        try:
            self.pool.put(conn, block=False)
            return  # Everything is dandy, done.
        except AttributeError:
            # self.pool is None.
            pass
        except queue.Full:
            # This should never happen if self.block == True
            log.warning(
                "Connection pool is full, discarding connection: %s. Connection pool size: %s",
                self.host,
                self.pool.qsize(),
            )
        # Connection never got put back into the pool, close it.
        if conn:
            conn.close()

    def _validate_conn(self, conn):
        """
        Called right before a request is made, after the socket is created.
        """
        pass

    def _prepare_proxy(self, conn):
        # Nothing to do for HTTP connections.
        pass

    def _get_timeout(self, timeout):
        """Helper that always returns a :class:`urllib3.util.Timeout`"""
        if timeout is _Default:
            return self.timeout.clone()

        if isinstance(timeout, Timeout):
            return timeout.clone()
        else:
            # User passed us an int/float. This is for backwards compatibility,
            # can be removed later
            return Timeout.from_float(timeout)

    def _raise_timeout(self, err, url, timeout_value):
        """Is the error actually a timeout? Will raise a ReadTimeout or pass"""

        if isinstance(err, SocketTimeout):
            raise ReadTimeoutError(
                self, url, "Read timed out. (read timeout=%s)" % timeout_value
            )

        # See the above comment about EAGAIN in Python 3. In Python 2 we have
        # to specifically catch it and throw the timeout error
        if hasattr(err, "errno") and err.errno in _blocking_errnos:
            raise ReadTimeoutError(
                self, url, "Read timed out. (read timeout=%s)" % timeout_value
            )

        # Catch possible read timeouts thrown as SSL errors. If not the
        # case, rethrow the original. We need to do this because of:
        # http://bugs.python.org/issue10272
        if "timed out" in str(err) or "did not complete (read)" in str(
            err
        ):  # Python < 2.7.4
            raise ReadTimeoutError(
                self, url, "Read timed out. (read timeout=%s)" % timeout_value
            )

    def _make_request(
        self, conn, method, url, timeout=_Default, chunked=False, **httplib_request_kw
    ):
        """
        Perform a request on a given urllib connection object taken from our
        pool.

        :param conn:
            a connection from one of our connection pools

        :param timeout:
            Socket timeout in seconds for the request. This can be a
            float or integer, which will set the same timeout value for
            the socket connect and the socket read, or an instance of
            :class:`urllib3.util.Timeout`, which gives you more fine-grained
            control over your timeouts.
        """
        self.num_requests += 1

        timeout_obj = self._get_timeout(timeout)
        timeout_obj.start_connect()
        conn.timeout = Timeout.resolve_default_timeout(timeout_obj.connect_timeout)

        # Trigger any extra validation we need to do.
        try:
            self._validate_conn(conn)
        except (SocketTimeout, BaseSSLError) as e:
            # Py2 raises this as a BaseSSLError, Py3 raises it as socket timeout.
            self._raise_timeout(err=e, url=url, timeout_value=conn.timeout)
            raise

        # conn.request() calls http.client.*.request, not the method in
        # urllib3.request. It also calls makefile (recv) on the socket.
        try:
            if chunked:
                conn.request_chunked(method, url, **httplib_request_kw)
            else:
                conn.request(method, url, **httplib_request_kw)

        # We are swallowing BrokenPipeError (errno.EPIPE) since the server is
        # legitimately able to close the connection after sending a valid response.
        # With this behaviour, the received response is still readable.
        except BrokenPipeError:
            # Python 3
            pass
        except IOError as e:
            # Python 2 and macOS/Linux
            # EPIPE and ESHUTDOWN are BrokenPipeError on Python 2, and EPROTOTYPE/ECONNRESET are needed on macOS
            # https://erickt.github.io/blog/2014/11/19/adventures-in-debugging-a-potential-osx-kernel-bug/
            if e.errno not in {
                errno.EPIPE,
                errno.ESHUTDOWN,
                errno.EPROTOTYPE,
                errno.ECONNRESET,
            }:
                raise

        # Reset the timeout for the recv() on the socket
        read_timeout = timeout_obj.read_timeout

        # App Engine doesn't have a sock attr
        if getattr(conn, "sock", None):
            # In Python 3 socket.py will catch EAGAIN and return None when you
            # try and read into the file pointer created by http.client, which
            # instead raises a BadStatusLine exception. Instead of catching
            # the exception and assuming all BadStatusLine exceptions are read
            # timeouts, check for a zero timeout before making the request.
            if read_timeout == 0:
                raise ReadTimeoutError(
                    self, url, "Read timed out. (read timeout=%s)" % read_timeout
                )
            if read_timeout is Timeout.DEFAULT_TIMEOUT:
                conn.sock.settimeout(socket.getdefaulttimeout())
            else:  # None or a value
                conn.sock.settimeout(read_timeout)

        # Receive the response from the server
        try:
            try:
                # Python 2.7, use buffering of HTTP responses
                httplib_response = conn.getresponse(buffering=True)
            except TypeError:
                # Python 3
                try:
                    httplib_response = conn.getresponse()
                except BaseException as e:
                    # Remove the TypeError from the exception chain in
                    # Python 3 (including for exceptions like SystemExit).
                    # Otherwise it looks like a bug in the code.
                    six.raise_from(e, None)
        except (SocketTimeout, BaseSSLError, SocketError) as e:
            self._raise_timeout(err=e, url=url, timeout_value=read_timeout)
            raise

        # AppEngine doesn't have a version attr.
        http_version = getattr(conn, "_http_vsn_str", "HTTP/?")
        log.debug(
            '%s://%s:%s "%s %s %s" %s %s',
            self.scheme,
            self.host,
            self.port,
            method,
            url,
            http_version,
            httplib_response.status,
            httplib_response.length,
        )

        try:
            assert_header_parsing(httplib_response.msg)
        except (HeaderParsingError, TypeError) as hpe:  # Platform-specific: Python 3
            log.warning(
                "Failed to parse headers (url=%s): %s",
                self._absolute_url(url),
                hpe,
                exc_info=True,
            )

        return httplib_response

    def _absolute_url(self, path):
        return Url(scheme=self.scheme, host=self.host, port=self.port, path=path).url

    def close(self):
        """
        Close all pooled connections and disable the pool.
        """
        if self.pool is None:
            return
        # Disable access to the pool
        old_pool, self.pool = self.pool, None

        # Close all the HTTPConnections in the pool.
        _close_pool_connections(old_pool)

    def is_same_host(self, url):
        """
        Check if the given ``url`` is a member of the same host as this
        connection pool.
        """
        if url.startswith("/"):
            return True

        # TODO: Add optional support for socket.gethostbyname checking.
        scheme, host, port = get_host(url)
        if host is not None:
            host = _normalize_host(host, scheme=scheme)

        # Use explicit default port for comparison when none is given
        if self.port and not port:
            port = port_by_scheme.get(scheme)
        elif not self.port and port == port_by_scheme.get(scheme):
            port = None

        return (scheme, host, port) == (self.scheme, self.host, self.port)

    def urlopen(
        self,
        method,
        url,
        body=None,
        headers=None,
        retries=None,
        redirect=True,
        assert_same_host=True,
        timeout=_Default,
        pool_timeout=None,
        release_conn=None,
        chunked=False,
        body_pos=None,
        **response_kw
    ):
        """
        Get a connection from the pool and perform an HTTP request. This is the
        lowest level call for making a request, so you'll need to specify all
        the raw details.

        .. note::

           More commonly, it's appropriate to use a convenience method provided
           by :class:`.RequestMethods`, such as :meth:`request`.

        .. note::

           `release_conn` will only behave as expected if
           `preload_content=False` because we want to make
           `preload_content=False` the default behaviour someday soon without
           breaking backwards compatibility.

        :param method:
            HTTP request method (such as GET, POST, PUT, etc.)

        :param url:
            The URL to perform the request on.

        :param body:
            Data to send in the request body, either :class:`str`, :class:`bytes`,
            an iterable of :class:`str`/:class:`bytes`, or a file-like object.

        :param headers:
            Dictionary of custom headers to send, such as User-Agent,
            If-None-Match, etc. If None, pool headers are used. If provided,
            these headers completely replace any pool-specific headers.

        :param retries:
            Configure the number of retries to allow before raising a
            :class:`~urllib3.exceptions.MaxRetryError` exception.

            Pass ``None`` to retry until you receive a response. Pass a
            :class:`~urllib3.util.retry.Retry` object for fine-grained control
            over different types of retries.
            Pass an integer number to retry connection errors that many times,
            but no other types of errors. Pass zero to never retry.

            If ``False``, then retries are disabled and any exception is raised
            immediately. Also, instead of raising a MaxRetryError on redirects,
            the redirect response will be returned.

        :type retries: :class:`~urllib3.util.retry.Retry`, False, or an int.

        :param redirect:
            If True, automatically handle redirects (status codes 301, 302,
            303, 307, 308). Each redirect counts as a retry. Disabling retries
            will disable redirect, too.

        :param assert_same_host:
            If ``True``, will make sure that the host of the pool requests is
            consistent else will raise HostChangedError. When ``False``, you can
            use the pool on an HTTP proxy and request foreign hosts.

        :param timeout:
            If specified, overrides the default timeout for this one
            request. It may be a float (in seconds) or an instance of
            :class:`urllib3.util.Timeout`.

        :param pool_timeout:
            If set and the pool is set to block=True, then this method will
            block for ``pool_timeout`` seconds and raise EmptyPoolError if no
            connection is available within the time period.

        :param release_conn:
            If False, then the urlopen call will not release the connection
            back into the pool once a response is received (but will release if
            you read the entire contents of the response such as when
            `preload_content=True`). This is useful if you're not preloading
            the response's content immediately. You will need to call
            ``r.release_conn()`` on the response ``r`` to return the connection
            back into the pool. If None, it takes the value of
            ``response_kw.get('preload_content', True)``.

        :param chunked:
            If True, urllib3 will send the body using chunked transfer
            encoding. Otherwise, urllib3 will send the body using the standard
            content-length form. Defaults to False.

        :param int body_pos:
            Position to seek to in file-like body in the event of a retry or
            redirect. Typically this won't need to be set because urllib3 will
            auto-populate the value when needed.

        :param \\**response_kw:
            Additional parameters are passed to
            :meth:`urllib3.response.HTTPResponse.from_httplib`
        """

        parsed_url = parse_url(url)
        destination_scheme = parsed_url.scheme

        if headers is None:
            headers = self.headers

        if not isinstance(retries, Retry):
            retries = Retry.from_int(retries, redirect=redirect, default=self.retries)

        if release_conn is None:
            release_conn = response_kw.get("preload_content", True)

        # Check host
        if assert_same_host and not self.is_same_host(url):
            raise HostChangedError(self, url, retries)

        # Ensure that the URL we're connecting to is properly encoded
        if url.startswith("/"):
            url = six.ensure_str(_encode_target(url))
        else:
            url = six.ensure_str(parsed_url.url)

        conn = None

        # Track whether `conn` needs to be released before
        # returning/raising/recursing. Update this variable if necessary, and
        # leave `release_conn` constant throughout the function. That way, if
        # the function recurses, the original value of `release_conn` will be
        # passed down into the recursive call, and its value will be respected.
        #
        # See issue #651 [1] for details.
        #
        # [1] <https://github.com/urllib3/urllib3/issues/651>
        release_this_conn = release_conn

        http_tunnel_required = connection_requires_http_tunnel(
            self.proxy, self.proxy_config, destination_scheme
        )

        # Merge the proxy headers. Only done when not using HTTP CONNECT. We
        # have to copy the headers dict so we can safely change it without those
        # changes being reflected in anyone else's copy.
        if not http_tunnel_required:
            headers = headers.copy()
            headers.update(self.proxy_headers)

        # Must keep the exception bound to a separate variable or else Python 3
        # complains about UnboundLocalError.
        err = None

        # Keep track of whether we cleanly exited the except block. This
        # ensures we do proper cleanup in finally.
        clean_exit = False

        # Rewind body position, if needed. Record current position
        # for future rewinds in the event of a redirect/retry.
        body_pos = set_file_position(body, body_pos)

        try:
            # Request a connection from the queue.
            timeout_obj = self._get_timeout(timeout)
            conn = self._get_conn(timeout=pool_timeout)

            conn.timeout = timeout_obj.connect_timeout

            is_new_proxy_conn = self.proxy is not None and not getattr(
                conn, "sock", None
            )
            if is_new_proxy_conn and http_tunnel_required:
                self._prepare_proxy(conn)

            # Make the request on the httplib connection object.
            httplib_response = self._make_request(
                conn,
                method,
                url,
                timeout=timeout_obj,
                body=body,
                headers=headers,
                chunked=chunked,
            )

            # If we're going to release the connection in ``finally:``, then
            # the response doesn't need to know about the connection. Otherwise
            # it will also try to release it and we'll have a double-release
            # mess.
            response_conn = conn if not release_conn else None

            # Pass method to Response for length checking
            response_kw["request_method"] = method

            # Import httplib's response into our own wrapper object
            response = self.ResponseCls.from_httplib(
                httplib_response,
                pool=self,
                connection=response_conn,
                retries=retries,
                **response_kw
            )

            # Everything went great!
            clean_exit = True

        except EmptyPoolError:
            # Didn't get a connection from the pool, no need to clean up
            clean_exit = True
            release_this_conn = False
            raise

        except (
            TimeoutError,
            HTTPException,
            SocketError,
            ProtocolError,
            BaseSSLError,
            SSLError,
            CertificateError,
        ) as e:
            # Discard the connection for these exceptions. It will be
            # replaced during the next _get_conn() call.
            clean_exit = False

            def _is_ssl_error_message_from_http_proxy(ssl_error):
                # We're trying to detect the message 'WRONG_VERSION_NUMBER' but
                # SSLErrors are kinda all over the place when it comes to the message,
                # so we try to cover our bases here!
                message = " ".join(re.split("[^a-z]", str(ssl_error).lower()))
                return (
                    "wrong version number" in message
                    or "unknown protocol" in message
                    or "record layer failure" in message
                )

            # Try to detect a common user error with proxies which is to
            # set an HTTP proxy to be HTTPS when it should be 'http://'
            # (ie {'http': 'http://proxy', 'https': 'https://proxy'})
            # Instead we add a nice error message and point to a URL.
            if (
                isinstance(e, BaseSSLError)
                and self.proxy
                and _is_ssl_error_message_from_http_proxy(e)
                and conn.proxy
                and conn.proxy.scheme == "https"
            ):
                e = ProxyError(
                    "Your proxy appears to only use HTTP and not HTTPS, "
                    "try changing your proxy URL to be HTTP. See: "
                    "https://urllib3.readthedocs.io/en/1.26.x/advanced-usage.html"
                    "#https-proxy-error-http-proxy",
                    SSLError(e),
                )
            elif isinstance(e, (BaseSSLError, CertificateError)):
                e = SSLError(e)
            elif isinstance(e, (SocketError, NewConnectionError)) and self.proxy:
                e = ProxyError("Cannot connect to proxy.", e)
            elif isinstance(e, (SocketError, HTTPException)):
                e = ProtocolError("Connection aborted.", e)

            retries = retries.increment(
                method, url, error=e, _pool=self, _stacktrace=sys.exc_info()[2]
            )
            retries.sleep()

            # Keep track of the error for the retry warning.
            err = e

        finally:
            if not clean_exit:
                # We hit some kind of exception, handled or otherwise. We need
                # to throw the connection away unless explicitly told not to.
                # Close the connection, set the variable to None, and make sure
                # we put the None back in the pool to avoid leaking it.
                conn = conn and conn.close()
                release_this_conn = True

            if release_this_conn:
                # Put the connection back to be reused. If the connection is
                # expired then it will be None, which will get replaced with a
                # fresh connection during _get_conn.
                self._put_conn(conn)

        if not conn:
            # Try again
            log.warning(
                "Retrying (%r) after connection broken by '%r': %s", retries, err, url
            )
            return self.urlopen(
                method,
                url,
                body,
                headers,
                retries,
                redirect,
                assert_same_host,
                timeout=timeout,
                pool_timeout=pool_timeout,
                release_conn=release_conn,
                chunked=chunked,
                body_pos=body_pos,
                **response_kw
            )

        # Handle redirect?
        redirect_location = redirect and response.get_redirect_location()
        if redirect_location:
            if response.status == 303:
                # Change the method according to RFC 9110, Section 15.4.4.
                method = "GET"
                # And lose the body not to transfer anything sensitive.
                body = None
                headers = HTTPHeaderDict(headers)._prepare_for_method_change()

            try:
                retries = retries.increment(method, url, response=response, _pool=self)
            except MaxRetryError:
                if retries.raise_on_redirect:
                    response.drain_conn()
                    raise
                return response

            response.drain_conn()
            retries.sleep_for_retry(response)
            log.debug("Redirecting %s -> %s", url, redirect_location)
            return self.urlopen(
                method,
                redirect_location,
                body,
                headers,
                retries=retries,
                redirect=redirect,
                assert_same_host=assert_same_host,
                timeout=timeout,
                pool_timeout=pool_timeout,
                release_conn=release_conn,
                chunked=chunked,
                body_pos=body_pos,
                **response_kw
            )

        # Check if we should retry the HTTP response.
        has_retry_after = bool(response.headers.get("Retry-After"))
        if retries.is_retry(method, response.status, has_retry_after):
            try:
                retries = retries.increment(method, url, response=response, _pool=self)
            except MaxRetryError:
                if retries.raise_on_status:
                    response.drain_conn()
                    raise
                return response

            response.drain_conn()
            retries.sleep(response)
            log.debug("Retry: %s", url)
            return self.urlopen(
                method,
                url,
                body,
                headers,
                retries=retries,
                redirect=redirect,
                assert_same_host=assert_same_host,
                timeout=timeout,
                pool_timeout=pool_timeout,
                release_conn=release_conn,
                chunked=chunked,
                body_pos=body_pos,
                **response_kw
            )

        return response


class HTTPSConnectionPool(HTTPConnectionPool):
    """
    Same as :class:`.HTTPConnectionPool`, but HTTPS.

    :class:`.HTTPSConnection` uses one of ``assert_fingerprint``,
    ``assert_hostname`` and ``host`` in this order to verify connections.
    If ``assert_hostname`` is False, no verification is done.

    The ``key_file``, ``cert_file``, ``cert_reqs``, ``ca_certs``,
    ``ca_cert_dir``, ``ssl_version``, ``key_password`` are only used if :mod:`ssl`
    is available and are fed into :meth:`urllib3.util.ssl_wrap_socket` to upgrade
    the connection socket into an SSL socket.
    """

    scheme = "https"
    ConnectionCls = HTTPSConnection

    def __init__(
        self,
        host,
        port=None,
        strict=False,
        timeout=Timeout.DEFAULT_TIMEOUT,
        maxsize=1,
        block=False,
        headers=None,
        retries=None,
        _proxy=None,
        _proxy_headers=None,
        key_file=None,
        cert_file=None,
        cert_reqs=None,
        key_password=None,
        ca_certs=None,
        ssl_version=None,
        assert_hostname=None,
        assert_fingerprint=None,
        ca_cert_dir=None,
        **conn_kw
    ):

        HTTPConnectionPool.__init__(
            self,
            host,
            port,
            strict,
            timeout,
            maxsize,
            block,
            headers,
            retries,
            _proxy,
            _proxy_headers,
            **conn_kw
        )

        self.key_file = key_file
        self.cert_file = cert_file
        self.cert_reqs = cert_reqs
        self.key_password = key_password
        self.ca_certs = ca_certs
        self.ca_cert_dir = ca_cert_dir
        self.ssl_version = ssl_version
        self.assert_hostname = assert_hostname
        self.assert_fingerprint = assert_fingerprint

    def _prepare_conn(self, conn):
        """
        Prepare the ``connection`` for :meth:`urllib3.util.ssl_wrap_socket`
        and establish the tunnel if proxy is used.
        """

        if isinstance(conn, VerifiedHTTPSConnection):
            conn.set_cert(
                key_file=self.key_file,
                key_password=self.key_password,
                cert_file=self.cert_file,
                cert_reqs=self.cert_reqs,
                ca_certs=self.ca_certs,
                ca_cert_dir=self.ca_cert_dir,
                assert_hostname=self.assert_hostname,
                assert_fingerprint=self.assert_fingerprint,
            )
            conn.ssl_version = self.ssl_version
        return conn

    def _prepare_proxy(self, conn):
        """
        Establishes a tunnel connection through HTTP CONNECT.

        Tunnel connection is established early because otherwise httplib would
        improperly set Host: header to proxy's IP:port.
        """

        conn.set_tunnel(self._proxy_host, self.port, self.proxy_headers)

        if self.proxy.scheme == "https":
            conn.tls_in_tls_required = True

        conn.connect()

    def _new_conn(self):
        """
        Return a fresh :class:`http.client.HTTPSConnection`.
        """
        self.num_connections += 1
        log.debug(
            "Starting new HTTPS connection (%d): %s:%s",
            self.num_connections,
            self.host,
            self.port or "443",
        )

        if not self.ConnectionCls or self.ConnectionCls is DummyConnection:
            raise SSLError(
                "Can't connect to HTTPS URL because the SSL module is not available."
            )

        actual_host = self.host
        actual_port = self.port
        if self.proxy is not None:
            actual_host = self.proxy.host
            actual_port = self.proxy.port

        conn = self.ConnectionCls(
            host=actual_host,
            port=actual_port,
            timeout=self.timeout.connect_timeout,
            strict=self.strict,
            cert_file=self.cert_file,
            key_file=self.key_file,
            key_password=self.key_password,
            **self.conn_kw
        )

        return self._prepare_conn(conn)

    def _validate_conn(self, conn):
        """
        Called right before a request is made, after the socket is created.
        """
        super(HTTPSConnectionPool, self)._validate_conn(conn)

        # Force connect early to allow us to validate the connection.
        if not getattr(conn, "sock", None):  # AppEngine might not have  `.sock`
            conn.connect()

        if not conn.is_verified:
            warnings.warn(
                (
                    "Unverified HTTPS request is being made to host '%s'. "
                    "Adding certificate verification is strongly advised. See: "
                    "https://urllib3.readthedocs.io/en/1.26.x/advanced-usage.html"
                    "#ssl-warnings" % conn.host
                ),
                InsecureRequestWarning,
            )

        if getattr(conn, "proxy_is_verified", None) is False:
            warnings.warn(
                (
                    "Unverified HTTPS connection done to an HTTPS proxy. "
                    "Adding certificate verification is strongly advised. See: "
                    "https://urllib3.readthedocs.io/en/1.26.x/advanced-usage.html"
                    "#ssl-warnings"
                ),
                InsecureRequestWarning,
            )


def connection_from_url(url, **kw):
    """
    Given a url, return an :class:`.ConnectionPool` instance of its host.

    This is a shortcut for not having to parse out the scheme, host, and port
    of the url before creating an :class:`.ConnectionPool` instance.

    :param url:
        Absolute URL string that must include the scheme. Port is optional.

    :param \\**kw:
        Passes additional parameters to the constructor of the appropriate
        :class:`.ConnectionPool`. Useful for specifying things like
        timeout, maxsize, headers, etc.

    Example::

        >>> conn = connection_from_url('http://google.com/')
        >>> r = conn.request('GET', '/')
    """
    scheme, host, port = get_host(url)
    port = port or port_by_scheme.get(scheme, 80)
    if scheme == "https":
        return HTTPSConnectionPool(host, port=port, **kw)
    else:
        return HTTPConnectionPool(host, port=port, **kw)


def _normalize_host(host, scheme):
    """
    Normalize hosts for comparisons and use with sockets.
    """

    host = normalize_host(host, scheme)

    # httplib doesn't like it when we include brackets in IPv6 addresses
    # Specifically, if we include brackets but also pass the port then
    # httplib crazily doubles up the square brackets on the Host header.
    # Instead, we need to make sure we never pass ``None`` as the port.
    # However, for backward compatibility reasons we can't actually
    # *assert* that.  See http://bugs.python.org/issue28539
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    return host


def _close_pool_connections(pool):
    """Drains a queue of connections and closes each one."""
    try:
        while True:
            conn = pool.get(block=False)
            if conn:
                conn.close()
    except queue.Empty:
        pass  # Done.

# === NexusCore/openenv\Lib\site-packages\aiohttp\multipart.py ===
import base64
import binascii
import json
import re
import sys
import uuid
import warnings
from collections import deque
from collections.abc import Mapping, Sequence
from types import TracebackType
from typing import (
    TYPE_CHECKING,
    Any,
    Deque,
    Dict,
    Iterator,
    List,
    Optional,
    Tuple,
    Type,
    Union,
    cast,
)
from urllib.parse import parse_qsl, unquote, urlencode

from multidict import CIMultiDict, CIMultiDictProxy

from .compression_utils import ZLibCompressor, ZLibDecompressor
from .hdrs import (
    CONTENT_DISPOSITION,
    CONTENT_ENCODING,
    CONTENT_LENGTH,
    CONTENT_TRANSFER_ENCODING,
    CONTENT_TYPE,
)
from .helpers import CHAR, TOKEN, parse_mimetype, reify
from .http import HeadersParser
from .log import internal_logger
from .payload import (
    JsonPayload,
    LookupError,
    Order,
    Payload,
    StringPayload,
    get_payload,
    payload_type,
)
from .streams import StreamReader

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing import TypeVar

    Self = TypeVar("Self", bound="BodyPartReader")

__all__ = (
    "MultipartReader",
    "MultipartWriter",
    "BodyPartReader",
    "BadContentDispositionHeader",
    "BadContentDispositionParam",
    "parse_content_disposition",
    "content_disposition_filename",
)


if TYPE_CHECKING:
    from .client_reqrep import ClientResponse


class BadContentDispositionHeader(RuntimeWarning):
    pass


class BadContentDispositionParam(RuntimeWarning):
    pass


def parse_content_disposition(
    header: Optional[str],
) -> Tuple[Optional[str], Dict[str, str]]:
    def is_token(string: str) -> bool:
        return bool(string) and TOKEN >= set(string)

    def is_quoted(string: str) -> bool:
        return string[0] == string[-1] == '"'

    def is_rfc5987(string: str) -> bool:
        return is_token(string) and string.count("'") == 2

    def is_extended_param(string: str) -> bool:
        return string.endswith("*")

    def is_continuous_param(string: str) -> bool:
        pos = string.find("*") + 1
        if not pos:
            return False
        substring = string[pos:-1] if string.endswith("*") else string[pos:]
        return substring.isdigit()

    def unescape(text: str, *, chars: str = "".join(map(re.escape, CHAR))) -> str:
        return re.sub(f"\\\\([{chars}])", "\\1", text)

    if not header:
        return None, {}

    disptype, *parts = header.split(";")
    if not is_token(disptype):
        warnings.warn(BadContentDispositionHeader(header))
        return None, {}

    params: Dict[str, str] = {}
    while parts:
        item = parts.pop(0)

        if "=" not in item:
            warnings.warn(BadContentDispositionHeader(header))
            return None, {}

        key, value = item.split("=", 1)
        key = key.lower().strip()
        value = value.lstrip()

        if key in params:
            warnings.warn(BadContentDispositionHeader(header))
            return None, {}

        if not is_token(key):
            warnings.warn(BadContentDispositionParam(item))
            continue

        elif is_continuous_param(key):
            if is_quoted(value):
                value = unescape(value[1:-1])
            elif not is_token(value):
                warnings.warn(BadContentDispositionParam(item))
                continue

        elif is_extended_param(key):
            if is_rfc5987(value):
                encoding, _, value = value.split("'", 2)
                encoding = encoding or "utf-8"
            else:
                warnings.warn(BadContentDispositionParam(item))
                continue

            try:
                value = unquote(value, encoding, "strict")
            except UnicodeDecodeError:  # pragma: nocover
                warnings.warn(BadContentDispositionParam(item))
                continue

        else:
            failed = True
            if is_quoted(value):
                failed = False
                value = unescape(value[1:-1].lstrip("\\/"))
            elif is_token(value):
                failed = False
            elif parts:
                # maybe just ; in filename, in any case this is just
                # one case fix, for proper fix we need to redesign parser
                _value = f"{value};{parts[0]}"
                if is_quoted(_value):
                    parts.pop(0)
                    value = unescape(_value[1:-1].lstrip("\\/"))
                    failed = False

            if failed:
                warnings.warn(BadContentDispositionHeader(header))
                return None, {}

        params[key] = value

    return disptype.lower(), params


def content_disposition_filename(
    params: Mapping[str, str], name: str = "filename"
) -> Optional[str]:
    name_suf = "%s*" % name
    if not params:
        return None
    elif name_suf in params:
        return params[name_suf]
    elif name in params:
        return params[name]
    else:
        parts = []
        fnparams = sorted(
            (key, value) for key, value in params.items() if key.startswith(name_suf)
        )
        for num, (key, value) in enumerate(fnparams):
            _, tail = key.split("*", 1)
            if tail.endswith("*"):
                tail = tail[:-1]
            if tail == str(num):
                parts.append(value)
            else:
                break
        if not parts:
            return None
        value = "".join(parts)
        if "'" in value:
            encoding, _, value = value.split("'", 2)
            encoding = encoding or "utf-8"
            return unquote(value, encoding, "strict")
        return value


class MultipartResponseWrapper:
    """Wrapper around the MultipartReader.

    It takes care about
    underlying connection and close it when it needs in.
    """

    def __init__(
        self,
        resp: "ClientResponse",
        stream: "MultipartReader",
    ) -> None:
        self.resp = resp
        self.stream = stream

    def __aiter__(self) -> "MultipartResponseWrapper":
        return self

    async def __anext__(
        self,
    ) -> Union["MultipartReader", "BodyPartReader"]:
        part = await self.next()
        if part is None:
            raise StopAsyncIteration
        return part

    def at_eof(self) -> bool:
        """Returns True when all response data had been read."""
        return self.resp.content.at_eof()

    async def next(
        self,
    ) -> Optional[Union["MultipartReader", "BodyPartReader"]]:
        """Emits next multipart reader object."""
        item = await self.stream.next()
        if self.stream.at_eof():
            await self.release()
        return item

    async def release(self) -> None:
        """Release the connection gracefully.

        All remaining content is read to the void.
        """
        await self.resp.release()


class BodyPartReader:
    """Multipart reader for single body part."""

    chunk_size = 8192

    def __init__(
        self,
        boundary: bytes,
        headers: "CIMultiDictProxy[str]",
        content: StreamReader,
        *,
        subtype: str = "mixed",
        default_charset: Optional[str] = None,
    ) -> None:
        self.headers = headers
        self._boundary = boundary
        self._boundary_len = len(boundary) + 2  # Boundary + \r\n
        self._content = content
        self._default_charset = default_charset
        self._at_eof = False
        self._is_form_data = subtype == "form-data"
        # https://datatracker.ietf.org/doc/html/rfc7578#section-4.8
        length = None if self._is_form_data else self.headers.get(CONTENT_LENGTH, None)
        self._length = int(length) if length is not None else None
        self._read_bytes = 0
        self._unread: Deque[bytes] = deque()
        self._prev_chunk: Optional[bytes] = None
        self._content_eof = 0
        self._cache: Dict[str, Any] = {}

    def __aiter__(self: Self) -> Self:
        return self

    async def __anext__(self) -> bytes:
        part = await self.next()
        if part is None:
            raise StopAsyncIteration
        return part

    async def next(self) -> Optional[bytes]:
        item = await self.read()
        if not item:
            return None
        return item

    async def read(self, *, decode: bool = False) -> bytes:
        """Reads body part data.

        decode: Decodes data following by encoding
                method from Content-Encoding header. If it missed
                data remains untouched
        """
        if self._at_eof:
            return b""
        data = bytearray()
        while not self._at_eof:
            data.extend(await self.read_chunk(self.chunk_size))
        if decode:
            return self.decode(data)
        return data

    async def read_chunk(self, size: int = chunk_size) -> bytes:
        """Reads body part content chunk of the specified size.

        size: chunk size
        """
        if self._at_eof:
            return b""
        if self._length:
            chunk = await self._read_chunk_from_length(size)
        else:
            chunk = await self._read_chunk_from_stream(size)

        # For the case of base64 data, we must read a fragment of size with a
        # remainder of 0 by dividing by 4 for string without symbols \n or \r
        encoding = self.headers.get(CONTENT_TRANSFER_ENCODING)
        if encoding and encoding.lower() == "base64":
            stripped_chunk = b"".join(chunk.split())
            remainder = len(stripped_chunk) % 4

            while remainder != 0 and not self.at_eof():
                over_chunk_size = 4 - remainder
                over_chunk = b""

                if self._prev_chunk:
                    over_chunk = self._prev_chunk[:over_chunk_size]
                    self._prev_chunk = self._prev_chunk[len(over_chunk) :]

                if len(over_chunk) != over_chunk_size:
                    over_chunk += await self._content.read(4 - len(over_chunk))

                if not over_chunk:
                    self._at_eof = True

                stripped_chunk += b"".join(over_chunk.split())
                chunk += over_chunk
                remainder = len(stripped_chunk) % 4

        self._read_bytes += len(chunk)
        if self._read_bytes == self._length:
            self._at_eof = True
        if self._at_eof:
            clrf = await self._content.readline()
            assert (
                b"\r\n" == clrf
            ), "reader did not read all the data or it is malformed"
        return chunk

    async def _read_chunk_from_length(self, size: int) -> bytes:
        # Reads body part content chunk of the specified size.
        # The body part must has Content-Length header with proper value.
        assert self._length is not None, "Content-Length required for chunked read"
        chunk_size = min(size, self._length - self._read_bytes)
        chunk = await self._content.read(chunk_size)
        if self._content.at_eof():
            self._at_eof = True
        return chunk

    async def _read_chunk_from_stream(self, size: int) -> bytes:
        # Reads content chunk of body part with unknown length.
        # The Content-Length header for body part is not necessary.
        assert (
            size >= self._boundary_len
        ), "Chunk size must be greater or equal than boundary length + 2"
        first_chunk = self._prev_chunk is None
        if first_chunk:
            self._prev_chunk = await self._content.read(size)

        chunk = b""
        # content.read() may return less than size, so we need to loop to ensure
        # we have enough data to detect the boundary.
        while len(chunk) < self._boundary_len:
            chunk += await self._content.read(size)
            self._content_eof += int(self._content.at_eof())
            assert self._content_eof < 3, "Reading after EOF"
            if self._content_eof:
                break
        if len(chunk) > size:
            self._content.unread_data(chunk[size:])
            chunk = chunk[:size]

        assert self._prev_chunk is not None
        window = self._prev_chunk + chunk
        sub = b"\r\n" + self._boundary
        if first_chunk:
            idx = window.find(sub)
        else:
            idx = window.find(sub, max(0, len(self._prev_chunk) - len(sub)))
        if idx >= 0:
            # pushing boundary back to content
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=DeprecationWarning)
                self._content.unread_data(window[idx:])
            if size > idx:
                self._prev_chunk = self._prev_chunk[:idx]
            chunk = window[len(self._prev_chunk) : idx]
            if not chunk:
                self._at_eof = True
        result = self._prev_chunk
        self._prev_chunk = chunk
        return result

    async def readline(self) -> bytes:
        """Reads body part by line by line."""
        if self._at_eof:
            return b""

        if self._unread:
            line = self._unread.popleft()
        else:
            line = await self._content.readline()

        if line.startswith(self._boundary):
            # the very last boundary may not come with \r\n,
            # so set single rules for everyone
            sline = line.rstrip(b"\r\n")
            boundary = self._boundary
            last_boundary = self._boundary + b"--"
            # ensure that we read exactly the boundary, not something alike
            if sline == boundary or sline == last_boundary:
                self._at_eof = True
                self._unread.append(line)
                return b""
        else:
            next_line = await self._content.readline()
            if next_line.startswith(self._boundary):
                line = line[:-2]  # strip CRLF but only once
            self._unread.append(next_line)

        return line

    async def release(self) -> None:
        """Like read(), but reads all the data to the void."""
        if self._at_eof:
            return
        while not self._at_eof:
            await self.read_chunk(self.chunk_size)

    async def text(self, *, encoding: Optional[str] = None) -> str:
        """Like read(), but assumes that body part contains text data."""
        data = await self.read(decode=True)
        # see https://www.w3.org/TR/html5/forms.html#multipart/form-data-encoding-algorithm
        # and https://dvcs.w3.org/hg/xhr/raw-file/tip/Overview.html#dom-xmlhttprequest-send
        encoding = encoding or self.get_charset(default="utf-8")
        return data.decode(encoding)

    async def json(self, *, encoding: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Like read(), but assumes that body parts contains JSON data."""
        data = await self.read(decode=True)
        if not data:
            return None
        encoding = encoding or self.get_charset(default="utf-8")
        return cast(Dict[str, Any], json.loads(data.decode(encoding)))

    async def form(self, *, encoding: Optional[str] = None) -> List[Tuple[str, str]]:
        """Like read(), but assumes that body parts contain form urlencoded data."""
        data = await self.read(decode=True)
        if not data:
            return []
        if encoding is not None:
            real_encoding = encoding
        else:
            real_encoding = self.get_charset(default="utf-8")
        try:
            decoded_data = data.rstrip().decode(real_encoding)
        except UnicodeDecodeError:
            raise ValueError("data cannot be decoded with %s encoding" % real_encoding)

        return parse_qsl(
            decoded_data,
            keep_blank_values=True,
            encoding=real_encoding,
        )

    def at_eof(self) -> bool:
        """Returns True if the boundary was reached or False otherwise."""
        return self._at_eof

    def decode(self, data: bytes) -> bytes:
        """Decodes data.

        Decoding is done according the specified Content-Encoding
        or Content-Transfer-Encoding headers value.
        """
        if CONTENT_TRANSFER_ENCODING in self.headers:
            data = self._decode_content_transfer(data)
        # https://datatracker.ietf.org/doc/html/rfc7578#section-4.8
        if not self._is_form_data and CONTENT_ENCODING in self.headers:
            return self._decode_content(data)
        return data

    def _decode_content(self, data: bytes) -> bytes:
        encoding = self.headers.get(CONTENT_ENCODING, "").lower()
        if encoding == "identity":
            return data
        if encoding in {"deflate", "gzip"}:
            return ZLibDecompressor(
                encoding=encoding,
                suppress_deflate_header=True,
            ).decompress_sync(data)

        raise RuntimeError(f"unknown content encoding: {encoding}")

    def _decode_content_transfer(self, data: bytes) -> bytes:
        encoding = self.headers.get(CONTENT_TRANSFER_ENCODING, "").lower()

        if encoding == "base64":
            return base64.b64decode(data)
        elif encoding == "quoted-printable":
            return binascii.a2b_qp(data)
        elif encoding in ("binary", "8bit", "7bit"):
            return data
        else:
            raise RuntimeError(f"unknown content transfer encoding: {encoding}")

    def get_charset(self, default: str) -> str:
        """Returns charset parameter from Content-Type header or default."""
        ctype = self.headers.get(CONTENT_TYPE, "")
        mimetype = parse_mimetype(ctype)
        return mimetype.parameters.get("charset", self._default_charset or default)

    @reify
    def name(self) -> Optional[str]:
        """Returns name specified in Content-Disposition header.

        If the header is missing or malformed, returns None.
        """
        _, params = parse_content_disposition(self.headers.get(CONTENT_DISPOSITION))
        return content_disposition_filename(params, "name")

    @reify
    def filename(self) -> Optional[str]:
        """Returns filename specified in Content-Disposition header.

        Returns None if the header is missing or malformed.
        """
        _, params = parse_content_disposition(self.headers.get(CONTENT_DISPOSITION))
        return content_disposition_filename(params, "filename")


@payload_type(BodyPartReader, order=Order.try_first)
class BodyPartReaderPayload(Payload):
    _value: BodyPartReader
    # _autoclose = False (inherited) - Streaming reader that may have resources

    def __init__(self, value: BodyPartReader, *args: Any, **kwargs: Any) -> None:
        super().__init__(value, *args, **kwargs)

        params: Dict[str, str] = {}
        if value.name is not None:
            params["name"] = value.name
        if value.filename is not None:
            params["filename"] = value.filename

        if params:
            self.set_content_disposition("attachment", True, **params)

    def decode(self, encoding: str = "utf-8", errors: str = "strict") -> str:
        raise TypeError("Unable to decode.")

    async def as_bytes(self, encoding: str = "utf-8", errors: str = "strict") -> bytes:
        """Raises TypeError as body parts should be consumed via write().

        This is intentional: BodyPartReader payloads are designed for streaming
        large data (potentially gigabytes) and must be consumed only once via
        the write() method to avoid memory exhaustion. They cannot be buffered
        in memory for reuse.
        """
        raise TypeError("Unable to read body part as bytes. Use write() to consume.")

    async def write(self, writer: Any) -> None:
        field = self._value
        chunk = await field.read_chunk(size=2**16)
        while chunk:
            await writer.write(field.decode(chunk))
            chunk = await field.read_chunk(size=2**16)


class MultipartReader:
    """Multipart body reader."""

    #: Response wrapper, used when multipart readers constructs from response.
    response_wrapper_cls = MultipartResponseWrapper
    #: Multipart reader class, used to handle multipart/* body parts.
    #: None points to type(self)
    multipart_reader_cls: Optional[Type["MultipartReader"]] = None
    #: Body part reader class for non multipart/* content types.
    part_reader_cls = BodyPartReader

    def __init__(self, headers: Mapping[str, str], content: StreamReader) -> None:
        self._mimetype = parse_mimetype(headers[CONTENT_TYPE])
        assert self._mimetype.type == "multipart", "multipart/* content type expected"
        if "boundary" not in self._mimetype.parameters:
            raise ValueError(
                "boundary missed for Content-Type: %s" % headers[CONTENT_TYPE]
            )

        self.headers = headers
        self._boundary = ("--" + self._get_boundary()).encode()
        self._content = content
        self._default_charset: Optional[str] = None
        self._last_part: Optional[Union["MultipartReader", BodyPartReader]] = None
        self._at_eof = False
        self._at_bof = True
        self._unread: List[bytes] = []

    def __aiter__(self: Self) -> Self:
        return self

    async def __anext__(
        self,
    ) -> Optional[Union["MultipartReader", BodyPartReader]]:
        part = await self.next()
        if part is None:
            raise StopAsyncIteration
        return part

    @classmethod
    def from_response(
        cls,
        response: "ClientResponse",
    ) -> MultipartResponseWrapper:
        """Constructs reader instance from HTTP response.

        :param response: :class:`~aiohttp.client.ClientResponse` instance
        """
        obj = cls.response_wrapper_cls(
            response, cls(response.headers, response.content)
        )
        return obj

    def at_eof(self) -> bool:
        """Returns True if the final boundary was reached, false otherwise."""
        return self._at_eof

    async def next(
        self,
    ) -> Optional[Union["MultipartReader", BodyPartReader]]:
        """Emits the next multipart body part."""
        # So, if we're at BOF, we need to skip till the boundary.
        if self._at_eof:
            return None
        await self._maybe_release_last_part()
        if self._at_bof:
            await self._read_until_first_boundary()
            self._at_bof = False
        else:
            await self._read_boundary()
        if self._at_eof:  # we just read the last boundary, nothing to do there
            return None

        part = await self.fetch_next_part()
        # https://datatracker.ietf.org/doc/html/rfc7578#section-4.6
        if (
            self._last_part is None
            and self._mimetype.subtype == "form-data"
            and isinstance(part, BodyPartReader)
        ):
            _, params = parse_content_disposition(part.headers.get(CONTENT_DISPOSITION))
            if params.get("name") == "_charset_":
                # Longest encoding in https://encoding.spec.whatwg.org/encodings.json
                # is 19 characters, so 32 should be more than enough for any valid encoding.
                charset = await part.read_chunk(32)
                if len(charset) > 31:
                    raise RuntimeError("Invalid default charset")
                self._default_charset = charset.strip().decode()
                part = await self.fetch_next_part()
        self._last_part = part
        return self._last_part

    async def release(self) -> None:
        """Reads all the body parts to the void till the final boundary."""
        while not self._at_eof:
            item = await self.next()
            if item is None:
                break
            await item.release()

    async def fetch_next_part(
        self,
    ) -> Union["MultipartReader", BodyPartReader]:
        """Returns the next body part reader."""
        headers = await self._read_headers()
        return self._get_part_reader(headers)

    def _get_part_reader(
        self,
        headers: "CIMultiDictProxy[str]",
    ) -> Union["MultipartReader", BodyPartReader]:
        """Dispatches the response by the `Content-Type` header.

        Returns a suitable reader instance.

        :param dict headers: Response headers
        """
        ctype = headers.get(CONTENT_TYPE, "")
        mimetype = parse_mimetype(ctype)

        if mimetype.type == "multipart":
            if self.multipart_reader_cls is None:
                return type(self)(headers, self._content)
            return self.multipart_reader_cls(headers, self._content)
        else:
            return self.part_reader_cls(
                self._boundary,
                headers,
                self._content,
                subtype=self._mimetype.subtype,
                default_charset=self._default_charset,
            )

    def _get_boundary(self) -> str:
        boundary = self._mimetype.parameters["boundary"]
        if len(boundary) > 70:
            raise ValueError("boundary %r is too long (70 chars max)" % boundary)

        return boundary

    async def _readline(self) -> bytes:
        if self._unread:
            return self._unread.pop()
        return await self._content.readline()

    async def _read_until_first_boundary(self) -> None:
        while True:
            chunk = await self._readline()
            if chunk == b"":
                raise ValueError(
                    "Could not find starting boundary %r" % (self._boundary)
                )
            chunk = chunk.rstrip()
            if chunk == self._boundary:
                return
            elif chunk == self._boundary + b"--":
                self._at_eof = True
                return

    async def _read_boundary(self) -> None:
        chunk = (await self._readline()).rstrip()
        if chunk == self._boundary:
            pass
        elif chunk == self._boundary + b"--":
            self._at_eof = True
            epilogue = await self._readline()
            next_line = await self._readline()

            # the epilogue is expected and then either the end of input or the
            # parent multipart boundary, if the parent boundary is found then
            # it should be marked as unread and handed to the parent for
            # processing
            if next_line[:2] == b"--":
                self._unread.append(next_line)
            # otherwise the request is likely missing an epilogue and both
            # lines should be passed to the parent for processing
            # (this handles the old behavior gracefully)
            else:
                self._unread.extend([next_line, epilogue])
        else:
            raise ValueError(f"Invalid boundary {chunk!r}, expected {self._boundary!r}")

    async def _read_headers(self) -> "CIMultiDictProxy[str]":
        lines = [b""]
        while True:
            chunk = await self._content.readline()
            chunk = chunk.strip()
            lines.append(chunk)
            if not chunk:
                break
        parser = HeadersParser()
        headers, raw_headers = parser.parse_headers(lines)
        return headers

    async def _maybe_release_last_part(self) -> None:
        """Ensures that the last read body part is read completely."""
        if self._last_part is not None:
            if not self._last_part.at_eof():
                await self._last_part.release()
            self._unread.extend(self._last_part._unread)
            self._last_part = None


_Part = Tuple[Payload, str, str]


class MultipartWriter(Payload):
    """Multipart body writer."""

    _value: None
    # _consumed = False (inherited) - Can be encoded multiple times
    _autoclose = True  # No file handles, just collects parts in memory

    def __init__(self, subtype: str = "mixed", boundary: Optional[str] = None) -> None:
        boundary = boundary if boundary is not None else uuid.uuid4().hex
        # The underlying Payload API demands a str (utf-8), not bytes,
        # so we need to ensure we don't lose anything during conversion.
        # As a result, require the boundary to be ASCII only.
        # In both situations.

        try:
            self._boundary = boundary.encode("ascii")
        except UnicodeEncodeError:
            raise ValueError("boundary should contain ASCII only chars") from None
        ctype = f"multipart/{subtype}; boundary={self._boundary_value}"

        super().__init__(None, content_type=ctype)

        self._parts: List[_Part] = []
        self._is_form_data = subtype == "form-data"

    def __enter__(self) -> "MultipartWriter":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        pass

    def __iter__(self) -> Iterator[_Part]:
        return iter(self._parts)

    def __len__(self) -> int:
        return len(self._parts)

    def __bool__(self) -> bool:
        return True

    _valid_tchar_regex = re.compile(rb"\A[!#$%&'*+\-.^_`|~\w]+\Z")
    _invalid_qdtext_char_regex = re.compile(rb"[\x00-\x08\x0A-\x1F\x7F]")

    @property
    def _boundary_value(self) -> str:
        """Wrap boundary parameter value in quotes, if necessary.

        Reads self.boundary and returns a unicode string.
        """
        # Refer to RFCs 7231, 7230, 5234.
        #
        # parameter      = token "=" ( token / quoted-string )
        # token          = 1*tchar
        # quoted-string  = DQUOTE *( qdtext / quoted-pair ) DQUOTE
        # qdtext         = HTAB / SP / %x21 / %x23-5B / %x5D-7E / obs-text
        # obs-text       = %x80-FF
        # quoted-pair    = "\" ( HTAB / SP / VCHAR / obs-text )
        # tchar          = "!" / "#" / "$" / "%" / "&" / "'" / "*"
        #                  / "+" / "-" / "." / "^" / "_" / "`" / "|" / "~"
        #                  / DIGIT / ALPHA
        #                  ; any VCHAR, except delimiters
        # VCHAR           = %x21-7E
        value = self._boundary
        if re.match(self._valid_tchar_regex, value):
            return value.decode("ascii")  # cannot fail

        if re.search(self._invalid_qdtext_char_regex, value):
            raise ValueError("boundary value contains invalid characters")

        # escape %x5C and %x22
        quoted_value_content = value.replace(b"\\", b"\\\\")
        quoted_value_content = quoted_value_content.replace(b'"', b'\\"')

        return '"' + quoted_value_content.decode("ascii") + '"'

    @property
    def boundary(self) -> str:
        return self._boundary.decode("ascii")

    def append(self, obj: Any, headers: Optional[Mapping[str, str]] = None) -> Payload:
        if headers is None:
            headers = CIMultiDict()

        if isinstance(obj, Payload):
            obj.headers.update(headers)
            return self.append_payload(obj)
        else:
            try:
                payload = get_payload(obj, headers=headers)
            except LookupError:
                raise TypeError("Cannot create payload from %r" % obj)
            else:
                return self.append_payload(payload)

    def append_payload(self, payload: Payload) -> Payload:
        """Adds a new body part to multipart writer."""
        encoding: Optional[str] = None
        te_encoding: Optional[str] = None
        if self._is_form_data:
            # https://datatracker.ietf.org/doc/html/rfc7578#section-4.7
            # https://datatracker.ietf.org/doc/html/rfc7578#section-4.8
            assert (
                not {CONTENT_ENCODING, CONTENT_LENGTH, CONTENT_TRANSFER_ENCODING}
                & payload.headers.keys()
            )
            # Set default Content-Disposition in case user doesn't create one
            if CONTENT_DISPOSITION not in payload.headers:
                name = f"section-{len(self._parts)}"
                payload.set_content_disposition("form-data", name=name)
        else:
            # compression
            encoding = payload.headers.get(CONTENT_ENCODING, "").lower()
            if encoding and encoding not in ("deflate", "gzip", "identity"):
                raise RuntimeError(f"unknown content encoding: {encoding}")
            if encoding == "identity":
                encoding = None

            # te encoding
            te_encoding = payload.headers.get(CONTENT_TRANSFER_ENCODING, "").lower()
            if te_encoding not in ("", "base64", "quoted-printable", "binary"):
                raise RuntimeError(f"unknown content transfer encoding: {te_encoding}")
            if te_encoding == "binary":
                te_encoding = None

            # size
            size = payload.size
            if size is not None and not (encoding or te_encoding):
                payload.headers[CONTENT_LENGTH] = str(size)

        self._parts.append((payload, encoding, te_encoding))  # type: ignore[arg-type]
        return payload

    def append_json(
        self, obj: Any, headers: Optional[Mapping[str, str]] = None
    ) -> Payload:
        """Helper to append JSON part."""
        if headers is None:
            headers = CIMultiDict()

        return self.append_payload(JsonPayload(obj, headers=headers))

    def append_form(
        self,
        obj: Union[Sequence[Tuple[str, str]], Mapping[str, str]],
        headers: Optional[Mapping[str, str]] = None,
    ) -> Payload:
        """Helper to append form urlencoded part."""
        assert isinstance(obj, (Sequence, Mapping))

        if headers is None:
            headers = CIMultiDict()

        if isinstance(obj, Mapping):
            obj = list(obj.items())
        data = urlencode(obj, doseq=True)

        return self.append_payload(
            StringPayload(
                data, headers=headers, content_type="application/x-www-form-urlencoded"
            )
        )

    @property
    def size(self) -> Optional[int]:
        """Size of the payload."""
        total = 0
        for part, encoding, te_encoding in self._parts:
            if encoding or te_encoding or part.size is None:
                return None

            total += int(
                2
                + len(self._boundary)
                + 2
                + part.size  # b'--'+self._boundary+b'\r\n'
                + len(part._binary_headers)
                + 2  # b'\r\n'
            )

        total += 2 + len(self._boundary) + 4  # b'--'+self._boundary+b'--\r\n'
        return total

    def decode(self, encoding: str = "utf-8", errors: str = "strict") -> str:
        """Return string representation of the multipart data.

        WARNING: This method may do blocking I/O if parts contain file payloads.
        It should not be called in the event loop. Use as_bytes().decode() instead.
        """
        return "".join(
            "--"
            + self.boundary
            + "\r\n"
            + part._binary_headers.decode(encoding, errors)
            + part.decode()
            for part, _e, _te in self._parts
        )

    async def as_bytes(self, encoding: str = "utf-8", errors: str = "strict") -> bytes:
        """Return bytes representation of the multipart data.

        This method is async-safe and calls as_bytes on underlying payloads.
        """
        parts: List[bytes] = []

        # Process each part
        for part, _e, _te in self._parts:
            # Add boundary
            parts.append(b"--" + self._boundary + b"\r\n")

            # Add headers
            parts.append(part._binary_headers)

            # Add payload content using as_bytes for async safety
            part_bytes = await part.as_bytes(encoding, errors)
            parts.append(part_bytes)

            # Add trailing CRLF
            parts.append(b"\r\n")

        # Add closing boundary
        parts.append(b"--" + self._boundary + b"--\r\n")

        return b"".join(parts)

    async def write(self, writer: Any, close_boundary: bool = True) -> None:
        """Write body."""
        for part, encoding, te_encoding in self._parts:
            if self._is_form_data:
                # https://datatracker.ietf.org/doc/html/rfc7578#section-4.2
                assert CONTENT_DISPOSITION in part.headers
                assert "name=" in part.headers[CONTENT_DISPOSITION]

            await writer.write(b"--" + self._boundary + b"\r\n")
            await writer.write(part._binary_headers)

            if encoding or te_encoding:
                w = MultipartPayloadWriter(writer)
                if encoding:
                    w.enable_compression(encoding)
                if te_encoding:
                    w.enable_encoding(te_encoding)
                await part.write(w)  # type: ignore[arg-type]
                await w.write_eof()
            else:
                await part.write(writer)

            await writer.write(b"\r\n")

        if close_boundary:
            await writer.write(b"--" + self._boundary + b"--\r\n")

    async def close(self) -> None:
        """
        Close all part payloads that need explicit closing.

        IMPORTANT: This method must not await anything that might not finish
        immediately, as it may be called during cleanup/cancellation. Schedule
        any long-running operations without awaiting them.
        """
        if self._consumed:
            return
        self._consumed = True

        # Close all parts that need explicit closing
        # We catch and log exceptions to ensure all parts get a chance to close
        # we do not use asyncio.gather() here because we are not allowed
        # to suspend given we may be called during cleanup
        for idx, (part, _, _) in enumerate(self._parts):
            if not part.autoclose and not part.consumed:
                try:
                    await part.close()
                except Exception as exc:
                    internal_logger.error(
                        "Failed to close multipart part %d: %s", idx, exc, exc_info=True
                    )


class MultipartPayloadWriter:
    def __init__(self, writer: Any) -> None:
        self._writer = writer
        self._encoding: Optional[str] = None
        self._compress: Optional[ZLibCompressor] = None
        self._encoding_buffer: Optional[bytearray] = None

    def enable_encoding(self, encoding: str) -> None:
        if encoding == "base64":
            self._encoding = encoding
            self._encoding_buffer = bytearray()
        elif encoding == "quoted-printable":
            self._encoding = "quoted-printable"

    def enable_compression(
        self, encoding: str = "deflate", strategy: Optional[int] = None
    ) -> None:
        self._compress = ZLibCompressor(
            encoding=encoding,
            suppress_deflate_header=True,
            strategy=strategy,
        )

    async def write_eof(self) -> None:
        if self._compress is not None:
            chunk = self._compress.flush()
            if chunk:
                self._compress = None
                await self.write(chunk)

        if self._encoding == "base64":
            if self._encoding_buffer:
                await self._writer.write(base64.b64encode(self._encoding_buffer))

    async def write(self, chunk: bytes) -> None:
        if self._compress is not None:
            if chunk:
                chunk = await self._compress.compress(chunk)
                if not chunk:
                    return

        if self._encoding == "base64":
            buf = self._encoding_buffer
            assert buf is not None
            buf.extend(chunk)

            if buf:
                div, mod = divmod(len(buf), 3)
                enc_chunk, self._encoding_buffer = (buf[: div * 3], buf[div * 3 :])
                if enc_chunk:
                    b64chunk = base64.b64encode(enc_chunk)
                    await self._writer.write(b64chunk)
        elif self._encoding == "quoted-printable":
            await self._writer.write(binascii.b2a_qp(chunk))
        else:
            await self._writer.write(chunk)

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\urllib3\connectionpool.py ===
from __future__ import absolute_import

import errno
import logging
import re
import socket
import sys
import warnings
from socket import error as SocketError
from socket import timeout as SocketTimeout

from ._collections import HTTPHeaderDict
from .connection import (
    BaseSSLError,
    BrokenPipeError,
    DummyConnection,
    HTTPConnection,
    HTTPException,
    HTTPSConnection,
    VerifiedHTTPSConnection,
    port_by_scheme,
)
from .exceptions import (
    ClosedPoolError,
    EmptyPoolError,
    HeaderParsingError,
    HostChangedError,
    InsecureRequestWarning,
    LocationValueError,
    MaxRetryError,
    NewConnectionError,
    ProtocolError,
    ProxyError,
    ReadTimeoutError,
    SSLError,
    TimeoutError,
)
from .packages import six
from .packages.six.moves import queue
from .request import RequestMethods
from .response import HTTPResponse
from .util.connection import is_connection_dropped
from .util.proxy import connection_requires_http_tunnel
from .util.queue import LifoQueue
from .util.request import set_file_position
from .util.response import assert_header_parsing
from .util.retry import Retry
from .util.ssl_match_hostname import CertificateError
from .util.timeout import Timeout
from .util.url import Url, _encode_target
from .util.url import _normalize_host as normalize_host
from .util.url import get_host, parse_url

try:  # Platform-specific: Python 3
    import weakref

    weakref_finalize = weakref.finalize
except AttributeError:  # Platform-specific: Python 2
    from .packages.backports.weakref_finalize import weakref_finalize

xrange = six.moves.xrange

log = logging.getLogger(__name__)

_Default = object()


# Pool objects
class ConnectionPool(object):
    """
    Base class for all connection pools, such as
    :class:`.HTTPConnectionPool` and :class:`.HTTPSConnectionPool`.

    .. note::
       ConnectionPool.urlopen() does not normalize or percent-encode target URIs
       which is useful if your target server doesn't support percent-encoded
       target URIs.
    """

    scheme = None
    QueueCls = LifoQueue

    def __init__(self, host, port=None):
        if not host:
            raise LocationValueError("No host specified.")

        self.host = _normalize_host(host, scheme=self.scheme)
        self._proxy_host = host.lower()
        self.port = port

    def __str__(self):
        return "%s(host=%r, port=%r)" % (type(self).__name__, self.host, self.port)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        # Return False to re-raise any potential exceptions
        return False

    def close(self):
        """
        Close all pooled connections and disable the pool.
        """
        pass


# This is taken from http://hg.python.org/cpython/file/7aaba721ebc0/Lib/socket.py#l252
_blocking_errnos = {errno.EAGAIN, errno.EWOULDBLOCK}


class HTTPConnectionPool(ConnectionPool, RequestMethods):
    """
    Thread-safe connection pool for one host.

    :param host:
        Host used for this HTTP Connection (e.g. "localhost"), passed into
        :class:`http.client.HTTPConnection`.

    :param port:
        Port used for this HTTP Connection (None is equivalent to 80), passed
        into :class:`http.client.HTTPConnection`.

    :param strict:
        Causes BadStatusLine to be raised if the status line can't be parsed
        as a valid HTTP/1.0 or 1.1 status line, passed into
        :class:`http.client.HTTPConnection`.

        .. note::
           Only works in Python 2. This parameter is ignored in Python 3.

    :param timeout:
        Socket timeout in seconds for each individual connection. This can
        be a float or integer, which sets the timeout for the HTTP request,
        or an instance of :class:`urllib3.util.Timeout` which gives you more
        fine-grained control over request timeouts. After the constructor has
        been parsed, this is always a `urllib3.util.Timeout` object.

    :param maxsize:
        Number of connections to save that can be reused. More than 1 is useful
        in multithreaded situations. If ``block`` is set to False, more
        connections will be created but they will not be saved once they've
        been used.

    :param block:
        If set to True, no more than ``maxsize`` connections will be used at
        a time. When no free connections are available, the call will block
        until a connection has been released. This is a useful side effect for
        particular multithreaded situations where one does not want to use more
        than maxsize connections per host to prevent flooding.

    :param headers:
        Headers to include with all requests, unless other headers are given
        explicitly.

    :param retries:
        Retry configuration to use by default with requests in this pool.

    :param _proxy:
        Parsed proxy URL, should not be used directly, instead, see
        :class:`urllib3.ProxyManager`

    :param _proxy_headers:
        A dictionary with proxy headers, should not be used directly,
        instead, see :class:`urllib3.ProxyManager`

    :param \\**conn_kw:
        Additional parameters are used to create fresh :class:`urllib3.connection.HTTPConnection`,
        :class:`urllib3.connection.HTTPSConnection` instances.
    """

    scheme = "http"
    ConnectionCls = HTTPConnection
    ResponseCls = HTTPResponse

    def __init__(
        self,
        host,
        port=None,
        strict=False,
        timeout=Timeout.DEFAULT_TIMEOUT,
        maxsize=1,
        block=False,
        headers=None,
        retries=None,
        _proxy=None,
        _proxy_headers=None,
        _proxy_config=None,
        **conn_kw
    ):
        ConnectionPool.__init__(self, host, port)
        RequestMethods.__init__(self, headers)

        self.strict = strict

        if not isinstance(timeout, Timeout):
            timeout = Timeout.from_float(timeout)

        if retries is None:
            retries = Retry.DEFAULT

        self.timeout = timeout
        self.retries = retries

        self.pool = self.QueueCls(maxsize)
        self.block = block

        self.proxy = _proxy
        self.proxy_headers = _proxy_headers or {}
        self.proxy_config = _proxy_config

        # Fill the queue up so that doing get() on it will block properly
        for _ in xrange(maxsize):
            self.pool.put(None)

        # These are mostly for testing and debugging purposes.
        self.num_connections = 0
        self.num_requests = 0
        self.conn_kw = conn_kw

        if self.proxy:
            # Enable Nagle's algorithm for proxies, to avoid packet fragmentation.
            # We cannot know if the user has added default socket options, so we cannot replace the
            # list.
            self.conn_kw.setdefault("socket_options", [])

            self.conn_kw["proxy"] = self.proxy
            self.conn_kw["proxy_config"] = self.proxy_config

        # Do not pass 'self' as callback to 'finalize'.
        # Then the 'finalize' would keep an endless living (leak) to self.
        # By just passing a reference to the pool allows the garbage collector
        # to free self if nobody else has a reference to it.
        pool = self.pool

        # Close all the HTTPConnections in the pool before the
        # HTTPConnectionPool object is garbage collected.
        weakref_finalize(self, _close_pool_connections, pool)

    def _new_conn(self):
        """
        Return a fresh :class:`HTTPConnection`.
        """
        self.num_connections += 1
        log.debug(
            "Starting new HTTP connection (%d): %s:%s",
            self.num_connections,
            self.host,
            self.port or "80",
        )

        conn = self.ConnectionCls(
            host=self.host,
            port=self.port,
            timeout=self.timeout.connect_timeout,
            strict=self.strict,
            **self.conn_kw
        )
        return conn

    def _get_conn(self, timeout=None):
        """
        Get a connection. Will return a pooled connection if one is available.

        If no connections are available and :prop:`.block` is ``False``, then a
        fresh connection is returned.

        :param timeout:
            Seconds to wait before giving up and raising
            :class:`urllib3.exceptions.EmptyPoolError` if the pool is empty and
            :prop:`.block` is ``True``.
        """
        conn = None
        try:
            conn = self.pool.get(block=self.block, timeout=timeout)

        except AttributeError:  # self.pool is None
            raise ClosedPoolError(self, "Pool is closed.")

        except queue.Empty:
            if self.block:
                raise EmptyPoolError(
                    self,
                    "Pool reached maximum size and no more connections are allowed.",
                )
            pass  # Oh well, we'll create a new connection then

        # If this is a persistent connection, check if it got disconnected
        if conn and is_connection_dropped(conn):
            log.debug("Resetting dropped connection: %s", self.host)
            conn.close()
            if getattr(conn, "auto_open", 1) == 0:
                # This is a proxied connection that has been mutated by
                # http.client._tunnel() and cannot be reused (since it would
                # attempt to bypass the proxy)
                conn = None

        return conn or self._new_conn()

    def _put_conn(self, conn):
        """
        Put a connection back into the pool.

        :param conn:
            Connection object for the current host and port as returned by
            :meth:`._new_conn` or :meth:`._get_conn`.

        If the pool is already full, the connection is closed and discarded
        because we exceeded maxsize. If connections are discarded frequently,
        then maxsize should be increased.

        If the pool is closed, then the connection will be closed and discarded.
        """
        try:
            self.pool.put(conn, block=False)
            return  # Everything is dandy, done.
        except AttributeError:
            # self.pool is None.
            pass
        except queue.Full:
            # This should never happen if self.block == True
            log.warning(
                "Connection pool is full, discarding connection: %s. Connection pool size: %s",
                self.host,
                self.pool.qsize(),
            )
        # Connection never got put back into the pool, close it.
        if conn:
            conn.close()

    def _validate_conn(self, conn):
        """
        Called right before a request is made, after the socket is created.
        """
        pass

    def _prepare_proxy(self, conn):
        # Nothing to do for HTTP connections.
        pass

    def _get_timeout(self, timeout):
        """Helper that always returns a :class:`urllib3.util.Timeout`"""
        if timeout is _Default:
            return self.timeout.clone()

        if isinstance(timeout, Timeout):
            return timeout.clone()
        else:
            # User passed us an int/float. This is for backwards compatibility,
            # can be removed later
            return Timeout.from_float(timeout)

    def _raise_timeout(self, err, url, timeout_value):
        """Is the error actually a timeout? Will raise a ReadTimeout or pass"""

        if isinstance(err, SocketTimeout):
            raise ReadTimeoutError(
                self, url, "Read timed out. (read timeout=%s)" % timeout_value
            )

        # See the above comment about EAGAIN in Python 3. In Python 2 we have
        # to specifically catch it and throw the timeout error
        if hasattr(err, "errno") and err.errno in _blocking_errnos:
            raise ReadTimeoutError(
                self, url, "Read timed out. (read timeout=%s)" % timeout_value
            )

        # Catch possible read timeouts thrown as SSL errors. If not the
        # case, rethrow the original. We need to do this because of:
        # http://bugs.python.org/issue10272
        if "timed out" in str(err) or "did not complete (read)" in str(
            err
        ):  # Python < 2.7.4
            raise ReadTimeoutError(
                self, url, "Read timed out. (read timeout=%s)" % timeout_value
            )

    def _make_request(
        self, conn, method, url, timeout=_Default, chunked=False, **httplib_request_kw
    ):
        """
        Perform a request on a given urllib connection object taken from our
        pool.

        :param conn:
            a connection from one of our connection pools

        :param timeout:
            Socket timeout in seconds for the request. This can be a
            float or integer, which will set the same timeout value for
            the socket connect and the socket read, or an instance of
            :class:`urllib3.util.Timeout`, which gives you more fine-grained
            control over your timeouts.
        """
        self.num_requests += 1

        timeout_obj = self._get_timeout(timeout)
        timeout_obj.start_connect()
        conn.timeout = Timeout.resolve_default_timeout(timeout_obj.connect_timeout)

        # Trigger any extra validation we need to do.
        try:
            self._validate_conn(conn)
        except (SocketTimeout, BaseSSLError) as e:
            # Py2 raises this as a BaseSSLError, Py3 raises it as socket timeout.
            self._raise_timeout(err=e, url=url, timeout_value=conn.timeout)
            raise

        # conn.request() calls http.client.*.request, not the method in
        # urllib3.request. It also calls makefile (recv) on the socket.
        try:
            if chunked:
                conn.request_chunked(method, url, **httplib_request_kw)
            else:
                conn.request(method, url, **httplib_request_kw)

        # We are swallowing BrokenPipeError (errno.EPIPE) since the server is
        # legitimately able to close the connection after sending a valid response.
        # With this behaviour, the received response is still readable.
        except BrokenPipeError:
            # Python 3
            pass
        except IOError as e:
            # Python 2 and macOS/Linux
            # EPIPE and ESHUTDOWN are BrokenPipeError on Python 2, and EPROTOTYPE/ECONNRESET are needed on macOS
            # https://erickt.github.io/blog/2014/11/19/adventures-in-debugging-a-potential-osx-kernel-bug/
            if e.errno not in {
                errno.EPIPE,
                errno.ESHUTDOWN,
                errno.EPROTOTYPE,
                errno.ECONNRESET,
            }:
                raise

        # Reset the timeout for the recv() on the socket
        read_timeout = timeout_obj.read_timeout

        # App Engine doesn't have a sock attr
        if getattr(conn, "sock", None):
            # In Python 3 socket.py will catch EAGAIN and return None when you
            # try and read into the file pointer created by http.client, which
            # instead raises a BadStatusLine exception. Instead of catching
            # the exception and assuming all BadStatusLine exceptions are read
            # timeouts, check for a zero timeout before making the request.
            if read_timeout == 0:
                raise ReadTimeoutError(
                    self, url, "Read timed out. (read timeout=%s)" % read_timeout
                )
            if read_timeout is Timeout.DEFAULT_TIMEOUT:
                conn.sock.settimeout(socket.getdefaulttimeout())
            else:  # None or a value
                conn.sock.settimeout(read_timeout)

        # Receive the response from the server
        try:
            try:
                # Python 2.7, use buffering of HTTP responses
                httplib_response = conn.getresponse(buffering=True)
            except TypeError:
                # Python 3
                try:
                    httplib_response = conn.getresponse()
                except BaseException as e:
                    # Remove the TypeError from the exception chain in
                    # Python 3 (including for exceptions like SystemExit).
                    # Otherwise it looks like a bug in the code.
                    six.raise_from(e, None)
        except (SocketTimeout, BaseSSLError, SocketError) as e:
            self._raise_timeout(err=e, url=url, timeout_value=read_timeout)
            raise

        # AppEngine doesn't have a version attr.
        http_version = getattr(conn, "_http_vsn_str", "HTTP/?")
        log.debug(
            '%s://%s:%s "%s %s %s" %s %s',
            self.scheme,
            self.host,
            self.port,
            method,
            url,
            http_version,
            httplib_response.status,
            httplib_response.length,
        )

        try:
            assert_header_parsing(httplib_response.msg)
        except (HeaderParsingError, TypeError) as hpe:  # Platform-specific: Python 3
            log.warning(
                "Failed to parse headers (url=%s): %s",
                self._absolute_url(url),
                hpe,
                exc_info=True,
            )

        return httplib_response

    def _absolute_url(self, path):
        return Url(scheme=self.scheme, host=self.host, port=self.port, path=path).url

    def close(self):
        """
        Close all pooled connections and disable the pool.
        """
        if self.pool is None:
            return
        # Disable access to the pool
        old_pool, self.pool = self.pool, None

        # Close all the HTTPConnections in the pool.
        _close_pool_connections(old_pool)

    def is_same_host(self, url):
        """
        Check if the given ``url`` is a member of the same host as this
        connection pool.
        """
        if url.startswith("/"):
            return True

        # TODO: Add optional support for socket.gethostbyname checking.
        scheme, host, port = get_host(url)
        if host is not None:
            host = _normalize_host(host, scheme=scheme)

        # Use explicit default port for comparison when none is given
        if self.port and not port:
            port = port_by_scheme.get(scheme)
        elif not self.port and port == port_by_scheme.get(scheme):
            port = None

        return (scheme, host, port) == (self.scheme, self.host, self.port)

    def urlopen(
        self,
        method,
        url,
        body=None,
        headers=None,
        retries=None,
        redirect=True,
        assert_same_host=True,
        timeout=_Default,
        pool_timeout=None,
        release_conn=None,
        chunked=False,
        body_pos=None,
        **response_kw
    ):
        """
        Get a connection from the pool and perform an HTTP request. This is the
        lowest level call for making a request, so you'll need to specify all
        the raw details.

        .. note::

           More commonly, it's appropriate to use a convenience method provided
           by :class:`.RequestMethods`, such as :meth:`request`.

        .. note::

           `release_conn` will only behave as expected if
           `preload_content=False` because we want to make
           `preload_content=False` the default behaviour someday soon without
           breaking backwards compatibility.

        :param method:
            HTTP request method (such as GET, POST, PUT, etc.)

        :param url:
            The URL to perform the request on.

        :param body:
            Data to send in the request body, either :class:`str`, :class:`bytes`,
            an iterable of :class:`str`/:class:`bytes`, or a file-like object.

        :param headers:
            Dictionary of custom headers to send, such as User-Agent,
            If-None-Match, etc. If None, pool headers are used. If provided,
            these headers completely replace any pool-specific headers.

        :param retries:
            Configure the number of retries to allow before raising a
            :class:`~urllib3.exceptions.MaxRetryError` exception.

            Pass ``None`` to retry until you receive a response. Pass a
            :class:`~urllib3.util.retry.Retry` object for fine-grained control
            over different types of retries.
            Pass an integer number to retry connection errors that many times,
            but no other types of errors. Pass zero to never retry.

            If ``False``, then retries are disabled and any exception is raised
            immediately. Also, instead of raising a MaxRetryError on redirects,
            the redirect response will be returned.

        :type retries: :class:`~urllib3.util.retry.Retry`, False, or an int.

        :param redirect:
            If True, automatically handle redirects (status codes 301, 302,
            303, 307, 308). Each redirect counts as a retry. Disabling retries
            will disable redirect, too.

        :param assert_same_host:
            If ``True``, will make sure that the host of the pool requests is
            consistent else will raise HostChangedError. When ``False``, you can
            use the pool on an HTTP proxy and request foreign hosts.

        :param timeout:
            If specified, overrides the default timeout for this one
            request. It may be a float (in seconds) or an instance of
            :class:`urllib3.util.Timeout`.

        :param pool_timeout:
            If set and the pool is set to block=True, then this method will
            block for ``pool_timeout`` seconds and raise EmptyPoolError if no
            connection is available within the time period.

        :param release_conn:
            If False, then the urlopen call will not release the connection
            back into the pool once a response is received (but will release if
            you read the entire contents of the response such as when
            `preload_content=True`). This is useful if you're not preloading
            the response's content immediately. You will need to call
            ``r.release_conn()`` on the response ``r`` to return the connection
            back into the pool. If None, it takes the value of
            ``response_kw.get('preload_content', True)``.

        :param chunked:
            If True, urllib3 will send the body using chunked transfer
            encoding. Otherwise, urllib3 will send the body using the standard
            content-length form. Defaults to False.

        :param int body_pos:
            Position to seek to in file-like body in the event of a retry or
            redirect. Typically this won't need to be set because urllib3 will
            auto-populate the value when needed.

        :param \\**response_kw:
            Additional parameters are passed to
            :meth:`urllib3.response.HTTPResponse.from_httplib`
        """

        parsed_url = parse_url(url)
        destination_scheme = parsed_url.scheme

        if headers is None:
            headers = self.headers

        if not isinstance(retries, Retry):
            retries = Retry.from_int(retries, redirect=redirect, default=self.retries)

        if release_conn is None:
            release_conn = response_kw.get("preload_content", True)

        # Check host
        if assert_same_host and not self.is_same_host(url):
            raise HostChangedError(self, url, retries)

        # Ensure that the URL we're connecting to is properly encoded
        if url.startswith("/"):
            url = six.ensure_str(_encode_target(url))
        else:
            url = six.ensure_str(parsed_url.url)

        conn = None

        # Track whether `conn` needs to be released before
        # returning/raising/recursing. Update this variable if necessary, and
        # leave `release_conn` constant throughout the function. That way, if
        # the function recurses, the original value of `release_conn` will be
        # passed down into the recursive call, and its value will be respected.
        #
        # See issue #651 [1] for details.
        #
        # [1] <https://github.com/urllib3/urllib3/issues/651>
        release_this_conn = release_conn

        http_tunnel_required = connection_requires_http_tunnel(
            self.proxy, self.proxy_config, destination_scheme
        )

        # Merge the proxy headers. Only done when not using HTTP CONNECT. We
        # have to copy the headers dict so we can safely change it without those
        # changes being reflected in anyone else's copy.
        if not http_tunnel_required:
            headers = headers.copy()
            headers.update(self.proxy_headers)

        # Must keep the exception bound to a separate variable or else Python 3
        # complains about UnboundLocalError.
        err = None

        # Keep track of whether we cleanly exited the except block. This
        # ensures we do proper cleanup in finally.
        clean_exit = False

        # Rewind body position, if needed. Record current position
        # for future rewinds in the event of a redirect/retry.
        body_pos = set_file_position(body, body_pos)

        try:
            # Request a connection from the queue.
            timeout_obj = self._get_timeout(timeout)
            conn = self._get_conn(timeout=pool_timeout)

            conn.timeout = timeout_obj.connect_timeout

            is_new_proxy_conn = self.proxy is not None and not getattr(
                conn, "sock", None
            )
            if is_new_proxy_conn and http_tunnel_required:
                self._prepare_proxy(conn)

            # Make the request on the httplib connection object.
            httplib_response = self._make_request(
                conn,
                method,
                url,
                timeout=timeout_obj,
                body=body,
                headers=headers,
                chunked=chunked,
            )

            # If we're going to release the connection in ``finally:``, then
            # the response doesn't need to know about the connection. Otherwise
            # it will also try to release it and we'll have a double-release
            # mess.
            response_conn = conn if not release_conn else None

            # Pass method to Response for length checking
            response_kw["request_method"] = method

            # Import httplib's response into our own wrapper object
            response = self.ResponseCls.from_httplib(
                httplib_response,
                pool=self,
                connection=response_conn,
                retries=retries,
                **response_kw
            )

            # Everything went great!
            clean_exit = True

        except EmptyPoolError:
            # Didn't get a connection from the pool, no need to clean up
            clean_exit = True
            release_this_conn = False
            raise

        except (
            TimeoutError,
            HTTPException,
            SocketError,
            ProtocolError,
            BaseSSLError,
            SSLError,
            CertificateError,
        ) as e:
            # Discard the connection for these exceptions. It will be
            # replaced during the next _get_conn() call.
            clean_exit = False

            def _is_ssl_error_message_from_http_proxy(ssl_error):
                # We're trying to detect the message 'WRONG_VERSION_NUMBER' but
                # SSLErrors are kinda all over the place when it comes to the message,
                # so we try to cover our bases here!
                message = " ".join(re.split("[^a-z]", str(ssl_error).lower()))
                return (
                    "wrong version number" in message
                    or "unknown protocol" in message
                    or "record layer failure" in message
                )

            # Try to detect a common user error with proxies which is to
            # set an HTTP proxy to be HTTPS when it should be 'http://'
            # (ie {'http': 'http://proxy', 'https': 'https://proxy'})
            # Instead we add a nice error message and point to a URL.
            if (
                isinstance(e, BaseSSLError)
                and self.proxy
                and _is_ssl_error_message_from_http_proxy(e)
                and conn.proxy
                and conn.proxy.scheme == "https"
            ):
                e = ProxyError(
                    "Your proxy appears to only use HTTP and not HTTPS, "
                    "try changing your proxy URL to be HTTP. See: "
                    "https://urllib3.readthedocs.io/en/1.26.x/advanced-usage.html"
                    "#https-proxy-error-http-proxy",
                    SSLError(e),
                )
            elif isinstance(e, (BaseSSLError, CertificateError)):
                e = SSLError(e)
            elif isinstance(e, (SocketError, NewConnectionError)) and self.proxy:
                e = ProxyError("Cannot connect to proxy.", e)
            elif isinstance(e, (SocketError, HTTPException)):
                e = ProtocolError("Connection aborted.", e)

            retries = retries.increment(
                method, url, error=e, _pool=self, _stacktrace=sys.exc_info()[2]
            )
            retries.sleep()

            # Keep track of the error for the retry warning.
            err = e

        finally:
            if not clean_exit:
                # We hit some kind of exception, handled or otherwise. We need
                # to throw the connection away unless explicitly told not to.
                # Close the connection, set the variable to None, and make sure
                # we put the None back in the pool to avoid leaking it.
                conn = conn and conn.close()
                release_this_conn = True

            if release_this_conn:
                # Put the connection back to be reused. If the connection is
                # expired then it will be None, which will get replaced with a
                # fresh connection during _get_conn.
                self._put_conn(conn)

        if not conn:
            # Try again
            log.warning(
                "Retrying (%r) after connection broken by '%r': %s", retries, err, url
            )
            return self.urlopen(
                method,
                url,
                body,
                headers,
                retries,
                redirect,
                assert_same_host,
                timeout=timeout,
                pool_timeout=pool_timeout,
                release_conn=release_conn,
                chunked=chunked,
                body_pos=body_pos,
                **response_kw
            )

        # Handle redirect?
        redirect_location = redirect and response.get_redirect_location()
        if redirect_location:
            if response.status == 303:
                # Change the method according to RFC 9110, Section 15.4.4.
                method = "GET"
                # And lose the body not to transfer anything sensitive.
                body = None
                headers = HTTPHeaderDict(headers)._prepare_for_method_change()

            try:
                retries = retries.increment(method, url, response=response, _pool=self)
            except MaxRetryError:
                if retries.raise_on_redirect:
                    response.drain_conn()
                    raise
                return response

            response.drain_conn()
            retries.sleep_for_retry(response)
            log.debug("Redirecting %s -> %s", url, redirect_location)
            return self.urlopen(
                method,
                redirect_location,
                body,
                headers,
                retries=retries,
                redirect=redirect,
                assert_same_host=assert_same_host,
                timeout=timeout,
                pool_timeout=pool_timeout,
                release_conn=release_conn,
                chunked=chunked,
                body_pos=body_pos,
                **response_kw
            )

        # Check if we should retry the HTTP response.
        has_retry_after = bool(response.headers.get("Retry-After"))
        if retries.is_retry(method, response.status, has_retry_after):
            try:
                retries = retries.increment(method, url, response=response, _pool=self)
            except MaxRetryError:
                if retries.raise_on_status:
                    response.drain_conn()
                    raise
                return response

            response.drain_conn()
            retries.sleep(response)
            log.debug("Retry: %s", url)
            return self.urlopen(
                method,
                url,
                body,
                headers,
                retries=retries,
                redirect=redirect,
                assert_same_host=assert_same_host,
                timeout=timeout,
                pool_timeout=pool_timeout,
                release_conn=release_conn,
                chunked=chunked,
                body_pos=body_pos,
                **response_kw
            )

        return response


class HTTPSConnectionPool(HTTPConnectionPool):
    """
    Same as :class:`.HTTPConnectionPool`, but HTTPS.

    :class:`.HTTPSConnection` uses one of ``assert_fingerprint``,
    ``assert_hostname`` and ``host`` in this order to verify connections.
    If ``assert_hostname`` is False, no verification is done.

    The ``key_file``, ``cert_file``, ``cert_reqs``, ``ca_certs``,
    ``ca_cert_dir``, ``ssl_version``, ``key_password`` are only used if :mod:`ssl`
    is available and are fed into :meth:`urllib3.util.ssl_wrap_socket` to upgrade
    the connection socket into an SSL socket.
    """

    scheme = "https"
    ConnectionCls = HTTPSConnection

    def __init__(
        self,
        host,
        port=None,
        strict=False,
        timeout=Timeout.DEFAULT_TIMEOUT,
        maxsize=1,
        block=False,
        headers=None,
        retries=None,
        _proxy=None,
        _proxy_headers=None,
        key_file=None,
        cert_file=None,
        cert_reqs=None,
        key_password=None,
        ca_certs=None,
        ssl_version=None,
        assert_hostname=None,
        assert_fingerprint=None,
        ca_cert_dir=None,
        **conn_kw
    ):

        HTTPConnectionPool.__init__(
            self,
            host,
            port,
            strict,
            timeout,
            maxsize,
            block,
            headers,
            retries,
            _proxy,
            _proxy_headers,
            **conn_kw
        )

        self.key_file = key_file
        self.cert_file = cert_file
        self.cert_reqs = cert_reqs
        self.key_password = key_password
        self.ca_certs = ca_certs
        self.ca_cert_dir = ca_cert_dir
        self.ssl_version = ssl_version
        self.assert_hostname = assert_hostname
        self.assert_fingerprint = assert_fingerprint

    def _prepare_conn(self, conn):
        """
        Prepare the ``connection`` for :meth:`urllib3.util.ssl_wrap_socket`
        and establish the tunnel if proxy is used.
        """

        if isinstance(conn, VerifiedHTTPSConnection):
            conn.set_cert(
                key_file=self.key_file,
                key_password=self.key_password,
                cert_file=self.cert_file,
                cert_reqs=self.cert_reqs,
                ca_certs=self.ca_certs,
                ca_cert_dir=self.ca_cert_dir,
                assert_hostname=self.assert_hostname,
                assert_fingerprint=self.assert_fingerprint,
            )
            conn.ssl_version = self.ssl_version
        return conn

    def _prepare_proxy(self, conn):
        """
        Establishes a tunnel connection through HTTP CONNECT.

        Tunnel connection is established early because otherwise httplib would
        improperly set Host: header to proxy's IP:port.
        """

        conn.set_tunnel(self._proxy_host, self.port, self.proxy_headers)

        if self.proxy.scheme == "https":
            conn.tls_in_tls_required = True

        conn.connect()

    def _new_conn(self):
        """
        Return a fresh :class:`http.client.HTTPSConnection`.
        """
        self.num_connections += 1
        log.debug(
            "Starting new HTTPS connection (%d): %s:%s",
            self.num_connections,
            self.host,
            self.port or "443",
        )

        if not self.ConnectionCls or self.ConnectionCls is DummyConnection:
            raise SSLError(
                "Can't connect to HTTPS URL because the SSL module is not available."
            )

        actual_host = self.host
        actual_port = self.port
        if self.proxy is not None:
            actual_host = self.proxy.host
            actual_port = self.proxy.port

        conn = self.ConnectionCls(
            host=actual_host,
            port=actual_port,
            timeout=self.timeout.connect_timeout,
            strict=self.strict,
            cert_file=self.cert_file,
            key_file=self.key_file,
            key_password=self.key_password,
            **self.conn_kw
        )

        return self._prepare_conn(conn)

    def _validate_conn(self, conn):
        """
        Called right before a request is made, after the socket is created.
        """
        super(HTTPSConnectionPool, self)._validate_conn(conn)

        # Force connect early to allow us to validate the connection.
        if not getattr(conn, "sock", None):  # AppEngine might not have  `.sock`
            conn.connect()

        if not conn.is_verified:
            warnings.warn(
                (
                    "Unverified HTTPS request is being made to host '%s'. "
                    "Adding certificate verification is strongly advised. See: "
                    "https://urllib3.readthedocs.io/en/1.26.x/advanced-usage.html"
                    "#ssl-warnings" % conn.host
                ),
                InsecureRequestWarning,
            )

        if getattr(conn, "proxy_is_verified", None) is False:
            warnings.warn(
                (
                    "Unverified HTTPS connection done to an HTTPS proxy. "
                    "Adding certificate verification is strongly advised. See: "
                    "https://urllib3.readthedocs.io/en/1.26.x/advanced-usage.html"
                    "#ssl-warnings"
                ),
                InsecureRequestWarning,
            )


def connection_from_url(url, **kw):
    """
    Given a url, return an :class:`.ConnectionPool` instance of its host.

    This is a shortcut for not having to parse out the scheme, host, and port
    of the url before creating an :class:`.ConnectionPool` instance.

    :param url:
        Absolute URL string that must include the scheme. Port is optional.

    :param \\**kw:
        Passes additional parameters to the constructor of the appropriate
        :class:`.ConnectionPool`. Useful for specifying things like
        timeout, maxsize, headers, etc.

    Example::

        >>> conn = connection_from_url('http://google.com/')
        >>> r = conn.request('GET', '/')
    """
    scheme, host, port = get_host(url)
    port = port or port_by_scheme.get(scheme, 80)
    if scheme == "https":
        return HTTPSConnectionPool(host, port=port, **kw)
    else:
        return HTTPConnectionPool(host, port=port, **kw)


def _normalize_host(host, scheme):
    """
    Normalize hosts for comparisons and use with sockets.
    """

    host = normalize_host(host, scheme)

    # httplib doesn't like it when we include brackets in IPv6 addresses
    # Specifically, if we include brackets but also pass the port then
    # httplib crazily doubles up the square brackets on the Host header.
    # Instead, we need to make sure we never pass ``None`` as the port.
    # However, for backward compatibility reasons we can't actually
    # *assert* that.  See http://bugs.python.org/issue28539
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    return host


def _close_pool_connections(pool):
    """Drains a queue of connections and closes each one."""
    try:
        while True:
            conn = pool.get(block=False)
            if conn:
                conn.close()
    except queue.Empty:
        pass  # Done.

# === NexusCore/openenv\Lib\site-packages\matplotlib\dviread.py ===
"""
A module for reading dvi files output by TeX. Several limitations make
this not (currently) useful as a general-purpose dvi preprocessor, but
it is currently used by the pdf backend for processing usetex text.

Interface::

  with Dvi(filename, 72) as dvi:
      # iterate over pages:
      for page in dvi:
          w, h, d = page.width, page.height, page.descent
          for x, y, font, glyph, width in page.text:
              fontname = font.texname
              pointsize = font.size
              ...
          for x, y, height, width in page.boxes:
              ...
"""

from collections import namedtuple
import enum
from functools import lru_cache, partial, wraps
import logging
import os
from pathlib import Path
import re
import struct
import subprocess
import sys

import numpy as np

from matplotlib import _api, cbook

_log = logging.getLogger(__name__)

# Many dvi related files are looked for by external processes, require
# additional parsing, and are used many times per rendering, which is why they
# are cached using lru_cache().

# Dvi is a bytecode format documented in
# https://ctan.org/pkg/dvitype
# https://texdoc.org/serve/dvitype.pdf/0
#
# The file consists of a preamble, some number of pages, a postamble,
# and a finale. Different opcodes are allowed in different contexts,
# so the Dvi object has a parser state:
#
#   pre:       expecting the preamble
#   outer:     between pages (followed by a page or the postamble,
#              also e.g. font definitions are allowed)
#   page:      processing a page
#   post_post: state after the postamble (our current implementation
#              just stops reading)
#   finale:    the finale (unimplemented in our current implementation)

_dvistate = enum.Enum('DviState', 'pre outer inpage post_post finale')

# The marks on a page consist of text and boxes. A page also has dimensions.
Page = namedtuple('Page', 'text boxes height width descent')
Box = namedtuple('Box', 'x y height width')


# Also a namedtuple, for backcompat.
class Text(namedtuple('Text', 'x y font glyph width')):
    """
    A glyph in the dvi file.

    The *x* and *y* attributes directly position the glyph.  The *font*,
    *glyph*, and *width* attributes are kept public for back-compatibility,
    but users wanting to draw the glyph themselves are encouraged to instead
    load the font specified by `font_path` at `font_size`, warp it with the
    effects specified by `font_effects`, and load the glyph specified by
    `glyph_name_or_index`.
    """

    def _get_pdftexmap_entry(self):
        return PsfontsMap(find_tex_file("pdftex.map"))[self.font.texname]

    @property
    def font_path(self):
        """The `~pathlib.Path` to the font for this glyph."""
        psfont = self._get_pdftexmap_entry()
        if psfont.filename is None:
            raise ValueError("No usable font file found for {} ({}); "
                             "the font may lack a Type-1 version"
                             .format(psfont.psname.decode("ascii"),
                                     psfont.texname.decode("ascii")))
        return Path(psfont.filename)

    @property
    def font_size(self):
        """The font size."""
        return self.font.size

    @property
    def font_effects(self):
        """
        The "font effects" dict for this glyph.

        This dict contains the values for this glyph of SlantFont and
        ExtendFont (if any), read off :file:`pdftex.map`.
        """
        return self._get_pdftexmap_entry().effects

    @property
    def glyph_name_or_index(self):
        """
        Either the glyph name or the native charmap glyph index.

        If :file:`pdftex.map` specifies an encoding for this glyph's font, that
        is a mapping of glyph indices to Adobe glyph names; use it to convert
        dvi indices to glyph names.  Callers can then convert glyph names to
        glyph indices (with FT_Get_Name_Index/get_name_index), and load the
        glyph using FT_Load_Glyph/load_glyph.

        If :file:`pdftex.map` specifies no encoding, the indices directly map
        to the font's "native" charmap; glyphs should directly load using
        FT_Load_Char/load_char after selecting the native charmap.
        """
        entry = self._get_pdftexmap_entry()
        return (_parse_enc(entry.encoding)[self.glyph]
                if entry.encoding is not None else self.glyph)


# Opcode argument parsing
#
# Each of the following functions takes a Dvi object and delta, which is the
# difference between the opcode and the minimum opcode with the same meaning.
# Dvi opcodes often encode the number of argument bytes in this delta.
_arg_mapping = dict(
    # raw: Return delta as is.
    raw=lambda dvi, delta: delta,
    # u1: Read 1 byte as an unsigned number.
    u1=lambda dvi, delta: dvi._read_arg(1, signed=False),
    # u4: Read 4 bytes as an unsigned number.
    u4=lambda dvi, delta: dvi._read_arg(4, signed=False),
    # s4: Read 4 bytes as a signed number.
    s4=lambda dvi, delta: dvi._read_arg(4, signed=True),
    # slen: Read delta bytes as a signed number, or None if delta is None.
    slen=lambda dvi, delta: dvi._read_arg(delta, signed=True) if delta else None,
    # slen1: Read (delta + 1) bytes as a signed number.
    slen1=lambda dvi, delta: dvi._read_arg(delta + 1, signed=True),
    # ulen1: Read (delta + 1) bytes as an unsigned number.
    ulen1=lambda dvi, delta: dvi._read_arg(delta + 1, signed=False),
    # olen1: Read (delta + 1) bytes as an unsigned number if less than 4 bytes,
    # as a signed number if 4 bytes.
    olen1=lambda dvi, delta: dvi._read_arg(delta + 1, signed=(delta == 3)),
)


def _dispatch(table, min, max=None, state=None, args=('raw',)):
    """
    Decorator for dispatch by opcode. Sets the values in *table*
    from *min* to *max* to this method, adds a check that the Dvi state
    matches *state* if not None, reads arguments from the file according
    to *args*.

    Parameters
    ----------
    table : dict[int, callable]
        The dispatch table to be filled in.

    min, max : int
        Range of opcodes that calls the registered function; *max* defaults to
        *min*.

    state : _dvistate, optional
        State of the Dvi object in which these opcodes are allowed.

    args : list[str], default: ['raw']
        Sequence of argument specifications:

        - 'raw': opcode minus minimum
        - 'u1': read one unsigned byte
        - 'u4': read four bytes, treat as an unsigned number
        - 's4': read four bytes, treat as a signed number
        - 'slen': read (opcode - minimum) bytes, treat as signed
        - 'slen1': read (opcode - minimum + 1) bytes, treat as signed
        - 'ulen1': read (opcode - minimum + 1) bytes, treat as unsigned
        - 'olen1': read (opcode - minimum + 1) bytes, treat as unsigned
          if under four bytes, signed if four bytes
    """
    def decorate(method):
        get_args = [_arg_mapping[x] for x in args]

        @wraps(method)
        def wrapper(self, byte):
            if state is not None and self.state != state:
                raise ValueError("state precondition failed")
            return method(self, *[f(self, byte-min) for f in get_args])
        if max is None:
            table[min] = wrapper
        else:
            for i in range(min, max+1):
                assert table[i] is None
                table[i] = wrapper
        return wrapper
    return decorate


class Dvi:
    """
    A reader for a dvi ("device-independent") file, as produced by TeX.

    The current implementation can only iterate through pages in order,
    and does not even attempt to verify the postamble.

    This class can be used as a context manager to close the underlying
    file upon exit. Pages can be read via iteration. Here is an overly
    simple way to extract text without trying to detect whitespace::

        >>> with matplotlib.dviread.Dvi('input.dvi', 72) as dvi:
        ...     for page in dvi:
        ...         print(''.join(chr(t.glyph) for t in page.text))
    """
    # dispatch table
    _dtable = [None] * 256
    _dispatch = partial(_dispatch, _dtable)

    def __init__(self, filename, dpi):
        """
        Read the data from the file named *filename* and convert
        TeX's internal units to units of *dpi* per inch.
        *dpi* only sets the units and does not limit the resolution.
        Use None to return TeX's internal units.
        """
        _log.debug('Dvi: %s', filename)
        self.file = open(filename, 'rb')
        self.dpi = dpi
        self.fonts = {}
        self.state = _dvistate.pre
        self._missing_font = None

    def __enter__(self):
        """Context manager enter method, does nothing."""
        return self

    def __exit__(self, etype, evalue, etrace):
        """
        Context manager exit method, closes the underlying file if it is open.
        """
        self.close()

    def __iter__(self):
        """
        Iterate through the pages of the file.

        Yields
        ------
        Page
            Details of all the text and box objects on the page.
            The Page tuple contains lists of Text and Box tuples and
            the page dimensions, and the Text and Box tuples contain
            coordinates transformed into a standard Cartesian
            coordinate system at the dpi value given when initializing.
            The coordinates are floating point numbers, but otherwise
            precision is not lost and coordinate values are not clipped to
            integers.
        """
        while self._read():
            yield self._output()

    def close(self):
        """Close the underlying file if it is open."""
        if not self.file.closed:
            self.file.close()

    def _output(self):
        """
        Output the text and boxes belonging to the most recent page.
        page = dvi._output()
        """
        minx = miny = np.inf
        maxx = maxy = -np.inf
        maxy_pure = -np.inf
        for elt in self.text + self.boxes:
            if isinstance(elt, Box):
                x, y, h, w = elt
                e = 0  # zero depth
            else:  # glyph
                x, y, font, g, w = elt
                h, e = font._height_depth_of(g)
            minx = min(minx, x)
            miny = min(miny, y - h)
            maxx = max(maxx, x + w)
            maxy = max(maxy, y + e)
            maxy_pure = max(maxy_pure, y)
        if self._baseline_v is not None:
            maxy_pure = self._baseline_v  # This should normally be the case.
            self._baseline_v = None

        if not self.text and not self.boxes:  # Avoid infs/nans from inf+/-inf.
            return Page(text=[], boxes=[], width=0, height=0, descent=0)

        if self.dpi is None:
            # special case for ease of debugging: output raw dvi coordinates
            return Page(text=self.text, boxes=self.boxes,
                        width=maxx-minx, height=maxy_pure-miny,
                        descent=maxy-maxy_pure)

        # convert from TeX's "scaled points" to dpi units
        d = self.dpi / (72.27 * 2**16)
        descent = (maxy - maxy_pure) * d

        text = [Text((x-minx)*d, (maxy-y)*d - descent, f, g, w*d)
                for (x, y, f, g, w) in self.text]
        boxes = [Box((x-minx)*d, (maxy-y)*d - descent, h*d, w*d)
                 for (x, y, h, w) in self.boxes]

        return Page(text=text, boxes=boxes, width=(maxx-minx)*d,
                    height=(maxy_pure-miny)*d, descent=descent)

    def _read(self):
        """
        Read one page from the file. Return True if successful,
        False if there were no more pages.
        """
        # Pages appear to start with the sequence
        #   bop (begin of page)
        #   xxx comment
        #   <push, ..., pop>  # if using chemformula
        #   down
        #   push
        #     down
        #     <push, push, xxx, right, xxx, pop, pop>  # if using xcolor
        #     down
        #     push
        #       down (possibly multiple)
        #       push  <=  here, v is the baseline position.
        #         etc.
        # (dviasm is useful to explore this structure.)
        # Thus, we use the vertical position at the first time the stack depth
        # reaches 3, while at least three "downs" have been executed (excluding
        # those popped out (corresponding to the chemformula preamble)), as the
        # baseline (the "down" count is necessary to handle xcolor).
        down_stack = [0]
        self._baseline_v = None
        while True:
            byte = self.file.read(1)[0]
            self._dtable[byte](self, byte)
            if self._missing_font:
                raise self._missing_font.to_exception()
            name = self._dtable[byte].__name__
            if name == "_push":
                down_stack.append(down_stack[-1])
            elif name == "_pop":
                down_stack.pop()
            elif name == "_down":
                down_stack[-1] += 1
            if (self._baseline_v is None
                    and len(getattr(self, "stack", [])) == 3
                    and down_stack[-1] >= 4):
                self._baseline_v = self.v
            if byte == 140:                         # end of page
                return True
            if self.state is _dvistate.post_post:   # end of file
                self.close()
                return False

    def _read_arg(self, nbytes, signed=False):
        """
        Read and return a big-endian integer *nbytes* long.
        Signedness is determined by the *signed* keyword.
        """
        return int.from_bytes(self.file.read(nbytes), "big", signed=signed)

    @_dispatch(min=0, max=127, state=_dvistate.inpage)
    def _set_char_immediate(self, char):
        self._put_char_real(char)
        if isinstance(self.fonts[self.f], cbook._ExceptionInfo):
            return
        self.h += self.fonts[self.f]._width_of(char)

    @_dispatch(min=128, max=131, state=_dvistate.inpage, args=('olen1',))
    def _set_char(self, char):
        self._put_char_real(char)
        if isinstance(self.fonts[self.f], cbook._ExceptionInfo):
            return
        self.h += self.fonts[self.f]._width_of(char)

    @_dispatch(132, state=_dvistate.inpage, args=('s4', 's4'))
    def _set_rule(self, a, b):
        self._put_rule_real(a, b)
        self.h += b

    @_dispatch(min=133, max=136, state=_dvistate.inpage, args=('olen1',))
    def _put_char(self, char):
        self._put_char_real(char)

    def _put_char_real(self, char):
        font = self.fonts[self.f]
        if isinstance(font, cbook._ExceptionInfo):
            self._missing_font = font
        elif font._vf is None:
            self.text.append(Text(self.h, self.v, font, char,
                                  font._width_of(char)))
        else:
            scale = font._scale
            for x, y, f, g, w in font._vf[char].text:
                newf = DviFont(scale=_mul2012(scale, f._scale),
                               tfm=f._tfm, texname=f.texname, vf=f._vf)
                self.text.append(Text(self.h + _mul2012(x, scale),
                                      self.v + _mul2012(y, scale),
                                      newf, g, newf._width_of(g)))
            self.boxes.extend([Box(self.h + _mul2012(x, scale),
                                   self.v + _mul2012(y, scale),
                                   _mul2012(a, scale), _mul2012(b, scale))
                               for x, y, a, b in font._vf[char].boxes])

    @_dispatch(137, state=_dvistate.inpage, args=('s4', 's4'))
    def _put_rule(self, a, b):
        self._put_rule_real(a, b)

    def _put_rule_real(self, a, b):
        if a > 0 and b > 0:
            self.boxes.append(Box(self.h, self.v, a, b))

    @_dispatch(138)
    def _nop(self, _):
        pass

    @_dispatch(139, state=_dvistate.outer, args=('s4',)*11)
    def _bop(self, c0, c1, c2, c3, c4, c5, c6, c7, c8, c9, p):
        self.state = _dvistate.inpage
        self.h = self.v = self.w = self.x = self.y = self.z = 0
        self.stack = []
        self.text = []          # list of Text objects
        self.boxes = []         # list of Box objects

    @_dispatch(140, state=_dvistate.inpage)
    def _eop(self, _):
        self.state = _dvistate.outer
        del self.h, self.v, self.w, self.x, self.y, self.z, self.stack

    @_dispatch(141, state=_dvistate.inpage)
    def _push(self, _):
        self.stack.append((self.h, self.v, self.w, self.x, self.y, self.z))

    @_dispatch(142, state=_dvistate.inpage)
    def _pop(self, _):
        self.h, self.v, self.w, self.x, self.y, self.z = self.stack.pop()

    @_dispatch(min=143, max=146, state=_dvistate.inpage, args=('slen1',))
    def _right(self, b):
        self.h += b

    @_dispatch(min=147, max=151, state=_dvistate.inpage, args=('slen',))
    def _right_w(self, new_w):
        if new_w is not None:
            self.w = new_w
        self.h += self.w

    @_dispatch(min=152, max=156, state=_dvistate.inpage, args=('slen',))
    def _right_x(self, new_x):
        if new_x is not None:
            self.x = new_x
        self.h += self.x

    @_dispatch(min=157, max=160, state=_dvistate.inpage, args=('slen1',))
    def _down(self, a):
        self.v += a

    @_dispatch(min=161, max=165, state=_dvistate.inpage, args=('slen',))
    def _down_y(self, new_y):
        if new_y is not None:
            self.y = new_y
        self.v += self.y

    @_dispatch(min=166, max=170, state=_dvistate.inpage, args=('slen',))
    def _down_z(self, new_z):
        if new_z is not None:
            self.z = new_z
        self.v += self.z

    @_dispatch(min=171, max=234, state=_dvistate.inpage)
    def _fnt_num_immediate(self, k):
        self.f = k

    @_dispatch(min=235, max=238, state=_dvistate.inpage, args=('olen1',))
    def _fnt_num(self, new_f):
        self.f = new_f

    @_dispatch(min=239, max=242, args=('ulen1',))
    def _xxx(self, datalen):
        special = self.file.read(datalen)
        _log.debug(
            'Dvi._xxx: encountered special: %s',
            ''.join([chr(ch) if 32 <= ch < 127 else '<%02x>' % ch
                     for ch in special]))

    @_dispatch(min=243, max=246, args=('olen1', 'u4', 'u4', 'u4', 'u1', 'u1'))
    def _fnt_def(self, k, c, s, d, a, l):
        self._fnt_def_real(k, c, s, d, a, l)

    def _fnt_def_real(self, k, c, s, d, a, l):
        n = self.file.read(a + l)
        fontname = n[-l:].decode('ascii')
        try:
            tfm = _tfmfile(fontname)
        except FileNotFoundError as exc:
            # Explicitly allow defining missing fonts for Vf support; we only
            # register an error when trying to load a glyph from a missing font
            # and throw that error in Dvi._read.  For Vf, _finalize_packet
            # checks whether a missing glyph has been used, and in that case
            # skips the glyph definition.
            self.fonts[k] = cbook._ExceptionInfo.from_exception(exc)
            return
        if c != 0 and tfm.checksum != 0 and c != tfm.checksum:
            raise ValueError(f'tfm checksum mismatch: {n}')
        try:
            vf = _vffile(fontname)
        except FileNotFoundError:
            vf = None
        self.fonts[k] = DviFont(scale=s, tfm=tfm, texname=n, vf=vf)

    @_dispatch(247, state=_dvistate.pre, args=('u1', 'u4', 'u4', 'u4', 'u1'))
    def _pre(self, i, num, den, mag, k):
        self.file.read(k)  # comment in the dvi file
        if i != 2:
            raise ValueError(f"Unknown dvi format {i}")
        if num != 25400000 or den != 7227 * 2**16:
            raise ValueError("Nonstandard units in dvi file")
            # meaning: TeX always uses those exact values, so it
            # should be enough for us to support those
            # (There are 72.27 pt to an inch so 7227 pt =
            # 7227 * 2**16 sp to 100 in. The numerator is multiplied
            # by 10^5 to get units of 10**-7 meters.)
        if mag != 1000:
            raise ValueError("Nonstandard magnification in dvi file")
            # meaning: LaTeX seems to frown on setting \mag, so
            # I think we can assume this is constant
        self.state = _dvistate.outer

    @_dispatch(248, state=_dvistate.outer)
    def _post(self, _):
        self.state = _dvistate.post_post
        # TODO: actually read the postamble and finale?
        # currently post_post just triggers closing the file

    @_dispatch(249)
    def _post_post(self, _):
        raise NotImplementedError

    @_dispatch(min=250, max=255)
    def _malformed(self, offset):
        raise ValueError(f"unknown command: byte {250 + offset}")


class DviFont:
    """
    Encapsulation of a font that a DVI file can refer to.

    This class holds a font's texname and size, supports comparison,
    and knows the widths of glyphs in the same units as the AFM file.
    There are also internal attributes (for use by dviread.py) that
    are *not* used for comparison.

    The size is in Adobe points (converted from TeX points).

    Parameters
    ----------
    scale : float
        Factor by which the font is scaled from its natural size.
    tfm : Tfm
        TeX font metrics for this font
    texname : bytes
       Name of the font as used internally by TeX and friends, as an ASCII
       bytestring.  This is usually very different from any external font
       names; `PsfontsMap` can be used to find the external name of the font.
    vf : Vf
       A TeX "virtual font" file, or None if this font is not virtual.

    Attributes
    ----------
    texname : bytes
    size : float
       Size of the font in Adobe points, converted from the slightly
       smaller TeX points.
    widths : list
       Widths of glyphs in glyph-space units, typically 1/1000ths of
       the point size.

    """
    __slots__ = ('texname', 'size', 'widths', '_scale', '_vf', '_tfm')

    def __init__(self, scale, tfm, texname, vf):
        _api.check_isinstance(bytes, texname=texname)
        self._scale = scale
        self._tfm = tfm
        self.texname = texname
        self._vf = vf
        self.size = scale * (72.0 / (72.27 * 2**16))
        try:
            nchars = max(tfm.width) + 1
        except ValueError:
            nchars = 0
        self.widths = [(1000*tfm.width.get(char, 0)) >> 20
                       for char in range(nchars)]

    def __eq__(self, other):
        return (type(self) is type(other)
                and self.texname == other.texname and self.size == other.size)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return f"<{type(self).__name__}: {self.texname}>"

    def _width_of(self, char):
        """Width of char in dvi units."""
        width = self._tfm.width.get(char, None)
        if width is not None:
            return _mul2012(width, self._scale)
        _log.debug('No width for char %d in font %s.', char, self.texname)
        return 0

    def _height_depth_of(self, char):
        """Height and depth of char in dvi units."""
        result = []
        for metric, name in ((self._tfm.height, "height"),
                             (self._tfm.depth, "depth")):
            value = metric.get(char, None)
            if value is None:
                _log.debug('No %s for char %d in font %s',
                           name, char, self.texname)
                result.append(0)
            else:
                result.append(_mul2012(value, self._scale))
        # cmsyXX (symbols font) glyph 0 ("minus") has a nonzero descent
        # so that TeX aligns equations properly
        # (https://tex.stackexchange.com/q/526103/)
        # but we actually care about the rasterization depth to align
        # the dvipng-generated images.
        if re.match(br'^cmsy\d+$', self.texname) and char == 0:
            result[-1] = 0
        return result


class Vf(Dvi):
    r"""
    A virtual font (\*.vf file) containing subroutines for dvi files.

    Parameters
    ----------
    filename : str or path-like

    Notes
    -----
    The virtual font format is a derivative of dvi:
    http://mirrors.ctan.org/info/knuth/virtual-fonts
    This class reuses some of the machinery of `Dvi`
    but replaces the `_read` loop and dispatch mechanism.

    Examples
    --------
    ::

        vf = Vf(filename)
        glyph = vf[code]
        glyph.text, glyph.boxes, glyph.width
    """

    def __init__(self, filename):
        super().__init__(filename, 0)
        try:
            self._first_font = None
            self._chars = {}
            self._read()
        finally:
            self.close()

    def __getitem__(self, code):
        return self._chars[code]

    def _read(self):
        """
        Read one page from the file. Return True if successful,
        False if there were no more pages.
        """
        packet_char = packet_ends = None
        packet_len = packet_width = None
        while True:
            byte = self.file.read(1)[0]
            # If we are in a packet, execute the dvi instructions
            if self.state is _dvistate.inpage:
                byte_at = self.file.tell()-1
                if byte_at == packet_ends:
                    self._finalize_packet(packet_char, packet_width)
                    packet_len = packet_char = packet_width = None
                    # fall through to out-of-packet code
                elif byte_at > packet_ends:
                    raise ValueError("Packet length mismatch in vf file")
                else:
                    if byte in (139, 140) or byte >= 243:
                        raise ValueError(f"Inappropriate opcode {byte} in vf file")
                    Dvi._dtable[byte](self, byte)
                    continue

            # We are outside a packet
            if byte < 242:          # a short packet (length given by byte)
                packet_len = byte
                packet_char = self._read_arg(1)
                packet_width = self._read_arg(3)
                packet_ends = self._init_packet(byte)
                self.state = _dvistate.inpage
            elif byte == 242:       # a long packet
                packet_len = self._read_arg(4)
                packet_char = self._read_arg(4)
                packet_width = self._read_arg(4)
                self._init_packet(packet_len)
            elif 243 <= byte <= 246:
                k = self._read_arg(byte - 242, byte == 246)
                c = self._read_arg(4)
                s = self._read_arg(4)
                d = self._read_arg(4)
                a = self._read_arg(1)
                l = self._read_arg(1)
                self._fnt_def_real(k, c, s, d, a, l)
                if self._first_font is None:
                    self._first_font = k
            elif byte == 247:       # preamble
                i = self._read_arg(1)
                k = self._read_arg(1)
                x = self.file.read(k)
                cs = self._read_arg(4)
                ds = self._read_arg(4)
                self._pre(i, x, cs, ds)
            elif byte == 248:       # postamble (just some number of 248s)
                break
            else:
                raise ValueError(f"Unknown vf opcode {byte}")

    def _init_packet(self, pl):
        if self.state != _dvistate.outer:
            raise ValueError("Misplaced packet in vf file")
        self.h = self.v = self.w = self.x = self.y = self.z = 0
        self.stack = []
        self.text = []
        self.boxes = []
        self.f = self._first_font
        self._missing_font = None
        return self.file.tell() + pl

    def _finalize_packet(self, packet_char, packet_width):
        if not self._missing_font:  # Otherwise we don't have full glyph definition.
            self._chars[packet_char] = Page(
                text=self.text, boxes=self.boxes, width=packet_width,
                height=None, descent=None)
        self.state = _dvistate.outer

    def _pre(self, i, x, cs, ds):
        if self.state is not _dvistate.pre:
            raise ValueError("pre command in middle of vf file")
        if i != 202:
            raise ValueError(f"Unknown vf format {i}")
        if len(x):
            _log.debug('vf file comment: %s', x)
        self.state = _dvistate.outer
        # cs = checksum, ds = design size


def _mul2012(num1, num2):
    """Multiply two numbers in 20.12 fixed point format."""
    # Separated into a function because >> has surprising precedence
    return (num1*num2) >> 20


class Tfm:
    """
    A TeX Font Metric file.

    This implementation covers only the bare minimum needed by the Dvi class.

    Parameters
    ----------
    filename : str or path-like

    Attributes
    ----------
    checksum : int
       Used for verifying against the dvi file.
    design_size : int
       Design size of the font (unknown units)
    width, height, depth : dict
       Dimensions of each character, need to be scaled by the factor
       specified in the dvi file. These are dicts because indexing may
       not start from 0.
    """
    __slots__ = ('checksum', 'design_size', 'width', 'height', 'depth')

    def __init__(self, filename):
        _log.debug('opening tfm file %s', filename)
        with open(filename, 'rb') as file:
            header1 = file.read(24)
            lh, bc, ec, nw, nh, nd = struct.unpack('!6H', header1[2:14])
            _log.debug('lh=%d, bc=%d, ec=%d, nw=%d, nh=%d, nd=%d',
                       lh, bc, ec, nw, nh, nd)
            header2 = file.read(4*lh)
            self.checksum, self.design_size = struct.unpack('!2I', header2[:8])
            # there is also encoding information etc.
            char_info = file.read(4*(ec-bc+1))
            widths = struct.unpack(f'!{nw}i', file.read(4*nw))
            heights = struct.unpack(f'!{nh}i', file.read(4*nh))
            depths = struct.unpack(f'!{nd}i', file.read(4*nd))
        self.width = {}
        self.height = {}
        self.depth = {}
        for idx, char in enumerate(range(bc, ec+1)):
            byte0 = char_info[4*idx]
            byte1 = char_info[4*idx+1]
            self.width[char] = widths[byte0]
            self.height[char] = heights[byte1 >> 4]
            self.depth[char] = depths[byte1 & 0xf]


PsFont = namedtuple('PsFont', 'texname psname effects encoding filename')


class PsfontsMap:
    """
    A psfonts.map formatted file, mapping TeX fonts to PS fonts.

    Parameters
    ----------
    filename : str or path-like

    Notes
    -----
    For historical reasons, TeX knows many Type-1 fonts by different
    names than the outside world. (For one thing, the names have to
    fit in eight characters.) Also, TeX's native fonts are not Type-1
    but Metafont, which is nontrivial to convert to PostScript except
    as a bitmap. While high-quality conversions to Type-1 format exist
    and are shipped with modern TeX distributions, we need to know
    which Type-1 fonts are the counterparts of which native fonts. For
    these reasons a mapping is needed from internal font names to font
    file names.

    A texmf tree typically includes mapping files called e.g.
    :file:`psfonts.map`, :file:`pdftex.map`, or :file:`dvipdfm.map`.
    The file :file:`psfonts.map` is used by :program:`dvips`,
    :file:`pdftex.map` by :program:`pdfTeX`, and :file:`dvipdfm.map`
    by :program:`dvipdfm`. :file:`psfonts.map` might avoid embedding
    the 35 PostScript fonts (i.e., have no filename for them, as in
    the Times-Bold example above), while the pdf-related files perhaps
    only avoid the "Base 14" pdf fonts. But the user may have
    configured these files differently.

    Examples
    --------
    >>> map = PsfontsMap(find_tex_file('pdftex.map'))
    >>> entry = map[b'ptmbo8r']
    >>> entry.texname
    b'ptmbo8r'
    >>> entry.psname
    b'Times-Bold'
    >>> entry.encoding
    '/usr/local/texlive/2008/texmf-dist/fonts/enc/dvips/base/8r.enc'
    >>> entry.effects
    {'slant': 0.16700000000000001}
    >>> entry.filename
    """
    __slots__ = ('_filename', '_unparsed', '_parsed')

    # Create a filename -> PsfontsMap cache, so that calling
    # `PsfontsMap(filename)` with the same filename a second time immediately
    # returns the same object.
    @lru_cache
    def __new__(cls, filename):
        self = object.__new__(cls)
        self._filename = os.fsdecode(filename)
        # Some TeX distributions have enormous pdftex.map files which would
        # take hundreds of milliseconds to parse, but it is easy enough to just
        # store the unparsed lines (keyed by the first word, which is the
        # texname) and parse them on-demand.
        with open(filename, 'rb') as file:
            self._unparsed = {}
            for line in file:
                tfmname = line.split(b' ', 1)[0]
                self._unparsed.setdefault(tfmname, []).append(line)
        self._parsed = {}
        return self

    def __getitem__(self, texname):
        assert isinstance(texname, bytes)
        if texname in self._unparsed:
            for line in self._unparsed.pop(texname):
                if self._parse_and_cache_line(line):
                    break
        try:
            return self._parsed[texname]
        except KeyError:
            raise LookupError(
                f"An associated PostScript font (required by Matplotlib) "
                f"could not be found for TeX font {texname.decode('ascii')!r} "
                f"in {self._filename!r}; this problem can often be solved by "
                f"installing a suitable PostScript font package in your TeX "
                f"package manager") from None

    def _parse_and_cache_line(self, line):
        """
        Parse a line in the font mapping file.

        The format is (partially) documented at
        http://mirrors.ctan.org/systems/doc/pdftex/manual/pdftex-a.pdf
        https://tug.org/texinfohtml/dvips.html#psfonts_002emap
        Each line can have the following fields:

        - tfmname (first, only required field),
        - psname (defaults to tfmname, must come immediately after tfmname if
          present),
        - fontflags (integer, must come immediately after psname if present,
          ignored by us),
        - special (SlantFont and ExtendFont, only field that is double-quoted),
        - fontfile, encodingfile (optional, prefixed by <, <<, or <[; << always
          precedes a font, <[ always precedes an encoding, < can precede either
          but then an encoding file must have extension .enc; < and << also
          request different font subsetting behaviors but we ignore that; < can
          be separated from the filename by whitespace).

        special, fontfile, and encodingfile can appear in any order.
        """
        # If the map file specifies multiple encodings for a font, we
        # follow pdfTeX in choosing the last one specified. Such
        # entries are probably mistakes but they have occurred.
        # https://tex.stackexchange.com/q/10826/

        if not line or line.startswith((b" ", b"%", b"*", b";", b"#")):
            return
        tfmname = basename = special = encodingfile = fontfile = None
        is_subsetted = is_t1 = is_truetype = False
        matches = re.finditer(br'"([^"]*)(?:"|$)|(\S+)', line)
        for match in matches:
            quoted, unquoted = match.groups()
            if unquoted:
                if unquoted.startswith(b"<<"):  # font
                    fontfile = unquoted[2:]
                elif unquoted.startswith(b"<["):  # encoding
                    encodingfile = unquoted[2:]
                elif unquoted.startswith(b"<"):  # font or encoding
                    word = (
                        # <foo => foo
                        unquoted[1:]
                        # < by itself => read the next word
                        or next(filter(None, next(matches).groups())))
                    if word.endswith(b".enc"):
                        encodingfile = word
                    else:
                        fontfile = word
                        is_subsetted = True
                elif tfmname is None:
                    tfmname = unquoted
                elif basename is None:
                    basename = unquoted
            elif quoted:
                special = quoted
        effects = {}
        if special:
            words = reversed(special.split())
            for word in words:
                if word == b"SlantFont":
                    effects["slant"] = float(next(words))
                elif word == b"ExtendFont":
                    effects["extend"] = float(next(words))

        # Verify some properties of the line that would cause it to be ignored
        # otherwise.
        if fontfile is not None:
            if fontfile.endswith((b".ttf", b".ttc")):
                is_truetype = True
            elif not fontfile.endswith(b".otf"):
                is_t1 = True
        elif basename is not None:
            is_t1 = True
        if is_truetype and is_subsetted and encodingfile is None:
            return
        if not is_t1 and ("slant" in effects or "extend" in effects):
            return
        if abs(effects.get("slant", 0)) > 1:
            return
        if abs(effects.get("extend", 0)) > 2:
            return

        if basename is None:
            basename = tfmname
        if encodingfile is not None:
            encodingfile = find_tex_file(encodingfile)
        if fontfile is not None:
            fontfile = find_tex_file(fontfile)
        self._parsed[tfmname] = PsFont(
            texname=tfmname, psname=basename, effects=effects,
            encoding=encodingfile, filename=fontfile)
        return True


def _parse_enc(path):
    r"""
    Parse a \*.enc file referenced from a psfonts.map style file.

    The format supported by this function is a tiny subset of PostScript.

    Parameters
    ----------
    path : `os.PathLike`

    Returns
    -------
    list
        The nth entry of the list is the PostScript glyph name of the nth
        glyph.
    """
    no_comments = re.sub("%.*", "", Path(path).read_text(encoding="ascii"))
    array = re.search(r"(?s)\[(.*)\]", no_comments).group(1)
    lines = [line for line in array.split() if line]
    if all(line.startswith("/") for line in lines):
        return [line[1:] for line in lines]
    else:
        raise ValueError(f"Failed to parse {path} as Postscript encoding")


class _LuatexKpsewhich:
    @lru_cache  # A singleton.
    def __new__(cls):
        self = object.__new__(cls)
        self._proc = self._new_proc()
        return self

    def _new_proc(self):
        return subprocess.Popen(
            ["luatex", "--luaonly",
             str(cbook._get_data_path("kpsewhich.lua"))],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    def search(self, filename):
        if self._proc.poll() is not None:  # Dead, restart it.
            self._proc = self._new_proc()
        self._proc.stdin.write(os.fsencode(filename) + b"\n")
        self._proc.stdin.flush()
        out = self._proc.stdout.readline().rstrip()
        return None if out == b"nil" else os.fsdecode(out)


@lru_cache
def find_tex_file(filename):
    """
    Find a file in the texmf tree using kpathsea_.

    The kpathsea library, provided by most existing TeX distributions, both
    on Unix-like systems and on Windows (MikTeX), is invoked via a long-lived
    luatex process if luatex is installed, or via kpsewhich otherwise.

    .. _kpathsea: https://www.tug.org/kpathsea/

    Parameters
    ----------
    filename : str or path-like

    Raises
    ------
    FileNotFoundError
        If the file is not found.
    """

    # we expect these to always be ascii encoded, but use utf-8
    # out of caution
    if isinstance(filename, bytes):
        filename = filename.decode('utf-8', errors='replace')

    try:
        lk = _LuatexKpsewhich()
    except FileNotFoundError:
        lk = None  # Fallback to directly calling kpsewhich, as below.

    if lk:
        path = lk.search(filename)
    else:
        if sys.platform == 'win32':
            # On Windows only, kpathsea can use utf-8 for cmd args and output.
            # The `command_line_encoding` environment variable is set to force
            # it to always use utf-8 encoding.  See Matplotlib issue #11848.
            kwargs = {'env': {**os.environ, 'command_line_encoding': 'utf-8'},
                      'encoding': 'utf-8'}
        else:  # On POSIX, run through the equivalent of os.fsdecode().
            kwargs = {'encoding': sys.getfilesystemencoding(),
                      'errors': 'surrogateescape'}

        try:
            path = (cbook._check_and_log_subprocess(['kpsewhich', filename],
                                                    _log, **kwargs)
                    .rstrip('\n'))
        except (FileNotFoundError, RuntimeError):
            path = None

    if path:
        return path
    else:
        raise FileNotFoundError(
            f"Matplotlib's TeX implementation searched for a file named "
            f"{filename!r} in your texmf tree, but could not find it")


@lru_cache
def _fontfile(cls, suffix, texname):
    return cls(find_tex_file(texname + suffix))


_tfmfile = partial(_fontfile, Tfm, ".tfm")
_vffile = partial(_fontfile, Vf, ".vf")


if __name__ == '__main__':
    from argparse import ArgumentParser
    import itertools

    parser = ArgumentParser()
    parser.add_argument("filename")
    parser.add_argument("dpi", nargs="?", type=float, default=None)
    args = parser.parse_args()
    with Dvi(args.filename, args.dpi) as dvi:
        fontmap = PsfontsMap(find_tex_file('pdftex.map'))
        for page in dvi:
            print(f"=== new page === "
                  f"(w: {page.width}, h: {page.height}, d: {page.descent})")
            for font, group in itertools.groupby(
                    page.text, lambda text: text.font):
                print(f"font: {font.texname.decode('latin-1')!r}\t"
                      f"scale: {font._scale / 2 ** 20}")
                print("x", "y", "glyph", "chr", "w", "(glyphs)", sep="\t")
                for text in group:
                    print(text.x, text.y, text.glyph,
                          chr(text.glyph) if chr(text.glyph).isprintable()
                          else ".",
                          text.width, sep="\t")
            if page.boxes:
                print("x", "y", "h", "w", "", "(boxes)", sep="\t")
                for box in page.boxes:
                    print(box.x, box.y, box.height, box.width, sep="\t")

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\management_endpoints\scim\scim_v2.py ===
"""
✨ SCIM v2 Endpoints for LiteLLM Proxy using Internal User/Team Management

This is an enterprise feature and requires a premium license.
"""

import uuid
from typing import Any, Dict, List, Optional, Set, Tuple, TypedDict

from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    Path,
    Query,
    Request,
    Response,
)

from litellm._logging import verbose_proxy_logger
from litellm.litellm_core_utils.safe_json_dumps import safe_dumps
from litellm.proxy._types import (
    LiteLLM_UserTable,
    LitellmUserRoles,
    Member,
    NewTeamRequest,
    NewUserRequest,
    TeamMemberAddRequest,
    TeamMemberDeleteRequest,
    UserAPIKeyAuth,
)
from litellm.proxy.auth.user_api_key_auth import user_api_key_auth
from litellm.proxy.management_endpoints.internal_user_endpoints import new_user
from litellm.proxy.management_endpoints.scim.scim_transformations import (
    ScimTransformations,
)
from litellm.proxy.management_endpoints.team_endpoints import (
    new_team,
    team_member_add,
    team_member_delete,
)
from litellm.proxy.utils import _premium_user_check, handle_exception_on_proxy
from litellm.types.proxy.management_endpoints.scim_v2 import *


class UserProvisionerHelpers:
    """Helper methods for user provisioning operations."""
    
    @staticmethod
    async def handle_existing_user_by_email(
        prisma_client,
        new_user_request: NewUserRequest
    ) -> Optional[SCIMUser]:
        """
        Check if a user with the given email already exists and update them if found.
        
        Args:
            prisma_client: Database client
            new_user_request: New user request data
            
        Returns:
            SCIMUser if user was updated, None if no existing user found
        """
        if not new_user_request.user_email:
            return None
            
        existing_user = await prisma_client.db.litellm_usertable.find_first(
            where={"user_email": new_user_request.user_email}
        )
        
        if not existing_user:
            return None
            
        # Update the user
        updated_user = await prisma_client.db.litellm_usertable.update(
            where={"user_id": existing_user.user_id},
            data={
                "user_id": new_user_request.user_id,
                "user_email": new_user_request.user_email,
                "user_alias": new_user_request.user_alias,
                "teams": new_user_request.teams,
                "metadata": safe_dumps(new_user_request.metadata),
            },
        )
        
        return await ScimTransformations.transform_litellm_user_to_scim_user(updated_user)


class ScimUserData(TypedDict):
    """Typed structure for extracted SCIM user data."""
    user_email: Optional[str]
    user_alias: Optional[str]
    sso_user_id: Optional[str]
    teams: List[str]
    given_name: Optional[str]
    family_name: Optional[str]
    active: Optional[bool]


scim_router = APIRouter(
    prefix="/scim/v2",
    tags=["✨ SCIM v2 (Enterprise Only)"],
    dependencies=[Depends(_premium_user_check)],
)


# Helper functions for common operations
async def _get_prisma_client_or_raise_exception():
    """Check if database is connected and raise HTTPException if not."""
    from litellm.proxy.proxy_server import prisma_client
    
    if prisma_client is None:
        raise HTTPException(status_code=500, detail={"error": "No database connected"})
    return prisma_client


async def _check_user_exists(user_id: str):
    """Check if user exists and return user, raise 404 if not found."""
    prisma_client = await _get_prisma_client_or_raise_exception()
    
    user = await prisma_client.db.litellm_usertable.find_unique(
        where={"user_id": user_id}
    )
    
    if not user:
        raise HTTPException(
            status_code=404, detail={"error": f"User not found with ID: {user_id}"}
        )
    
    return user


async def _check_team_exists(team_id: str):
    """Check if team exists and return team, raise 404 if not found."""
    prisma_client = await _get_prisma_client_or_raise_exception()
    
    team = await prisma_client.db.litellm_teamtable.find_unique(
        where={"team_id": team_id}
    )
    
    if not team:
        raise HTTPException(
            status_code=404, detail={"error": f"Group not found with ID: {team_id}"}
        )
    
    return team


def _extract_scim_user_data(user: SCIMUser) -> ScimUserData:
    """Extract common data from SCIMUser object."""
    user_email = None
    if user.emails and len(user.emails) > 0:
        user_email = user.emails[0].value

    user_alias = None
    if user.name and user.name.givenName:
        user_alias = user.name.givenName

    teams = []
    if user.groups:
        teams = [group.value for group in user.groups]

    return {
        "user_email": user_email,
        "user_alias": user_alias,
        "sso_user_id": user.externalId,
        "teams": teams,
        "given_name": user.name.givenName if user.name else None,
        "family_name": user.name.familyName if user.name else None,
        "active": user.active,
    }


def _build_scim_metadata(given_name: Optional[str], family_name: Optional[str], active: Optional[bool] = None) -> Dict[str, Any]:
    """Build metadata dictionary with SCIM data."""
    metadata: Dict[str, Any] = {
        "scim_metadata": LiteLLM_UserScimMetadata(
            givenName=given_name,
            familyName=family_name,
        ).model_dump()
    }
    
    if active is not None:
        metadata["scim_active"] = active
    
    return metadata


async def _extract_group_member_ids(group: SCIMGroup) -> List[str]:
    """Extract valid member IDs from SCIMGroup, verifying users exist."""
    prisma_client = await _get_prisma_client_or_raise_exception()
    member_ids = []
    
    if group.members:
        for member in group.members:
            # Check if user exists
            user = await prisma_client.db.litellm_usertable.find_unique(
                where={"user_id": member.value}
            )
            if user:
                member_ids.append(member.value)
    
    return member_ids


async def _get_team_members_display(member_ids: List[str]) -> List[SCIMMember]:
    """Get SCIMMember objects with display names for a list of member IDs."""
    prisma_client = await _get_prisma_client_or_raise_exception()
    members: List[SCIMMember] = []
    
    for member_id in member_ids:
        user = await prisma_client.db.litellm_usertable.find_unique(
            where={"user_id": member_id}
        )
        if user:
            display_name = user.user_email or user.user_id
            members.append(SCIMMember(value=user.user_id, display=display_name))
    
    return members


async def _handle_team_membership_changes(user_id: str, existing_teams: List[str], new_teams: List[str]) -> None:
    """Handle adding/removing user from teams based on changes."""
    existing_teams_set = set(existing_teams)
    new_teams_set = set(new_teams)
    
    teams_to_add = new_teams_set - existing_teams_set
    teams_to_remove = existing_teams_set - new_teams_set
    
    if teams_to_add or teams_to_remove:
        await patch_team_membership(
            user_id=user_id,
            teams_ids_to_add_user_to=list(teams_to_add),
            teams_ids_to_remove_user_from=list(teams_to_remove),
        )


# Dependency to set the correct SCIM Content-Type
async def set_scim_content_type(response: Response):
    """Sets the Content-Type header to application/scim+json"""
    # Check if content type is already application/json, only override in that case
    # Avoids overriding for non-JSON responses or already correct types if they were set manually
    response.headers["Content-Type"] = "application/scim+json"


# User Endpoints
@scim_router.get(
    "/Users",
    response_model=SCIMListResponse,
    status_code=200,
    dependencies=[Depends(user_api_key_auth), Depends(set_scim_content_type)],
)
async def get_users(
    startIndex: int = Query(1, ge=1),
    count: int = Query(10, ge=1, le=100),
    filter: Optional[str] = Query(None),
):
    """
    Get a list of users according to SCIM v2 protocol
    """
    try:
        prisma_client = await _get_prisma_client_or_raise_exception()
        # Parse filter if provided (basic support)
        where_conditions = {}
        if filter:
            # Very basic filter support - only handling userName eq and emails.value eq
            if "userName eq" in filter:
                user_id = filter.split("userName eq ")[1].strip("\"'")
                where_conditions["user_id"] = user_id
            elif "emails.value eq" in filter:
                email = filter.split("emails.value eq ")[1].strip("\"'")
                where_conditions["user_email"] = email

        # Get users from database
        users: List[LiteLLM_UserTable] = (
            await prisma_client.db.litellm_usertable.find_many(
                where=where_conditions,
                skip=(startIndex - 1),
                take=count,
                order={"created_at": "desc"},
            )
        )

        # Get total count for pagination
        total_count = await prisma_client.db.litellm_usertable.count(
            where=where_conditions
        )

        # Convert to SCIM format
        scim_users: List[SCIMUser] = []
        for user in users:
            scim_user = await ScimTransformations.transform_litellm_user_to_scim_user(
                user=user
            )
            scim_users.append(scim_user)

        return SCIMListResponse(
            totalResults=total_count,
            startIndex=startIndex,
            itemsPerPage=min(count, len(scim_users)),
            Resources=scim_users,
        )

    except Exception as e:
        raise handle_exception_on_proxy(e)


@scim_router.get(
    "/Users/{user_id}",
    response_model=SCIMUser,
    status_code=200,
    dependencies=[Depends(user_api_key_auth), Depends(set_scim_content_type)],
)
async def get_user(
    user_id: str = Path(..., title="User ID"),
):
    """
    Get a single user by ID according to SCIM v2 protocol
    """
    try:
        user = await _check_user_exists(user_id)
        
        # Convert to SCIM format
        scim_user = await ScimTransformations.transform_litellm_user_to_scim_user(user)
        return scim_user

    except Exception as e:
        raise handle_exception_on_proxy(e)

@scim_router.post(
    "/Users",
    response_model=SCIMUser,
    status_code=201,
    dependencies=[Depends(user_api_key_auth), Depends(set_scim_content_type)],
)
async def create_user(
    user: SCIMUser = Body(...),
):
    """
    Create a user according to SCIM v2 protocol
    """
    try:
        verbose_proxy_logger.debug("SCIM CREATE USER request: %s", user)
        prisma_client = await _get_prisma_client_or_raise_exception()
        
        # Extract data from SCIM user
        user_data = _extract_scim_user_data(user)

        # Check if user already exists
        if user.userName:
            existing_user = await prisma_client.db.litellm_usertable.find_unique(
                where={"user_id": user.userName}
            )
            if existing_user:
                raise HTTPException(
                    status_code=409,
                    detail={"error": f"User already exists with username: {user.userName}"},
                )

        # Create user in database
        user_id = user.userName or str(uuid.uuid4())
        metadata = _build_scim_metadata(user_data["given_name"], user_data["family_name"])
        new_user_request = NewUserRequest(
            user_id=user_id,
            user_email=user_data["user_email"],
            user_alias=user_data["user_alias"],
            teams=user_data["teams"],
            metadata=metadata,
            auto_create_key=False,
        )

        # Check if user with email already exists and update if found
        existing_user_scim = await UserProvisionerHelpers.handle_existing_user_by_email(
            prisma_client=prisma_client,
            new_user_request=new_user_request
        )
        
        if existing_user_scim:
            return existing_user_scim

        created_user = await new_user(
            data=new_user_request,
        )
        
        scim_user = await ScimTransformations.transform_litellm_user_to_scim_user(
            user=created_user
        )
        return scim_user
    except HTTPException as e: # allow exceptions like SCIMUserAlreadyExists to be raised
        raise e
    except Exception as e:
        raise handle_exception_on_proxy(e)


@scim_router.put(
    "/Users/{user_id}",
    response_model=SCIMUser,
    status_code=200,
    dependencies=[Depends(user_api_key_auth), Depends(set_scim_content_type)],
)
async def update_user(
    user_id: str = Path(..., title="User ID"),
    user: SCIMUser = Body(...),
):
    """
    Update a user according to SCIM v2 protocol (full replacement)
    """
    verbose_proxy_logger.debug("SCIM PUT USER request: %s", user)

    try:
        prisma_client = await _get_prisma_client_or_raise_exception()
        existing_user = await _check_user_exists(user_id)

        # Extract data from SCIM user
        user_data = _extract_scim_user_data(user)

        # Build metadata with SCIM data  
        metadata = _build_scim_metadata(
            user_data["given_name"], 
            user_data["family_name"], 
            user_data["active"]
        )

        # Handle team membership changes
        await _handle_team_membership_changes(
            user_id=user_id,
            existing_teams=existing_user.teams or [],
            new_teams=user_data["teams"]
        )

        # Update user with all new data (full replacement)
        update_data = {
            "user_email": user_data["user_email"],
            "user_alias": user_data["user_alias"],
            "sso_user_id": user_data["sso_user_id"],
            "teams": user_data["teams"],
            "metadata": metadata,
        }

        # Serialize metadata to JSON string for Prisma to avoid GraphQL parsing issues
        if "metadata" in update_data and isinstance(update_data["metadata"], dict):
            from litellm.litellm_core_utils.safe_json_dumps import safe_dumps
            update_data["metadata"] = safe_dumps(update_data["metadata"])

        updated_user = await prisma_client.db.litellm_usertable.update(
            where={"user_id": user_id},
            data=update_data,
        )

        # Convert back to SCIM format
        scim_user = await ScimTransformations.transform_litellm_user_to_scim_user(updated_user)
        
        return scim_user

    except Exception as e:
        raise handle_exception_on_proxy(e)


@scim_router.delete(
    "/Users/{user_id}",
    status_code=204,
    dependencies=[Depends(user_api_key_auth)],
)
async def delete_user(
    user_id: str = Path(..., title="User ID"),
):
    """
    Delete a user according to SCIM v2 protocol
    """
    try:
        prisma_client = await _get_prisma_client_or_raise_exception()
        existing_user = await _check_user_exists(user_id)

        # Get teams user belongs to
        teams = []
        if existing_user.teams:
            for team_id in existing_user.teams:
                team = await prisma_client.db.litellm_teamtable.find_unique(
                    where={"team_id": team_id}
                )
                if team:
                    teams.append(team)

        # Remove user from all teams
        for team in teams:
            current_members = team.members or []
            if user_id in current_members:
                new_members = [m for m in current_members if m != user_id]
                await prisma_client.db.litellm_teamtable.update(
                    where={"team_id": team.team_id}, data={"members": new_members}
                )

        # Delete user
        await prisma_client.db.litellm_usertable.delete(where={"user_id": user_id})

        return Response(status_code=204)
    except Exception as e:
        raise handle_exception_on_proxy(e)


def _extract_group_values(value: Any) -> List[str]:
    """Return group ids from a SCIM patch value."""
    group_values: List[str] = []
    if isinstance(value, list):
        for v in value:
            if isinstance(v, dict) and v.get("value"):
                group_values.append(str(v.get("value")))
            elif isinstance(v, str):
                group_values.append(v)
    elif isinstance(value, dict):
        if value.get("value"):
            group_values.append(str(value.get("value")))
    elif isinstance(value, str):
        group_values.append(value)
    return group_values


def _handle_displayname_update(op_type: str, value: Any, update_data: Dict[str, Any]) -> None:
    """Handle displayname updates."""
    if op_type == "remove":
        update_data["user_alias"] = None
    else:
        update_data["user_alias"] = str(value)


def _handle_externalid_update(op_type: str, value: Any, update_data: Dict[str, Any]) -> None:
    """Handle externalid updates."""
    if op_type == "remove":
        update_data["sso_user_id"] = None
    else:
        update_data["sso_user_id"] = str(value)


def _handle_active_update(op_type: str, value: Any, metadata: Dict[str, Any]) -> None:
    """Handle active status updates."""
    if op_type == "remove":
        metadata.pop("scim_active", None)
    else:
        bool_val = value
        if isinstance(value, str):
            bool_val = value.lower() == "true"
        else:
            bool_val = bool(value)
        metadata["scim_active"] = bool_val


def _handle_name_update(path: str, op_type: str, value: Any, scim_metadata: Dict[str, Any]) -> None:
    """Handle name field updates (givenName, familyName)."""
    if path == "name.givenname":
        if op_type == "remove":
            scim_metadata.pop("givenName", None)
        else:
            scim_metadata["givenName"] = str(value)
    elif path == "name.familyname":
        if op_type == "remove":
            scim_metadata.pop("familyName", None)
        else:
            scim_metadata["familyName"] = str(value)


def _handle_group_operations(op_type: str, value: Any, teams_set: Set[str]) -> Optional[Set[str]]:
    """Handle group/team membership operations."""
    group_values = _extract_group_values(value)
    if op_type == "replace":
        return set(group_values)
    elif op_type == "add":
        teams_set.update(group_values)
    elif op_type == "remove":
        for gid in group_values:
            teams_set.discard(gid)
    return None


def _handle_generic_metadata(path: str, op_type: str, value: Any, metadata: Dict[str, Any]) -> None:
    """Handle generic metadata operations for unknown paths."""
    if op_type == "remove":
        metadata.pop(path, None)
    else:
        metadata[path] = value


def _apply_patch_ops(
    existing_user: LiteLLM_UserTable,
    patch_ops: SCIMPatchOp,
) -> Tuple[Dict[str, Any], Set[str]]:
    """Apply patch operations and return update data and final team set."""
    update_data: Dict[str, Any] = {}
    metadata = existing_user.metadata or {}
    scim_metadata = metadata.get("scim_metadata", {})

    teams_set: Set[str] = set(existing_user.teams or [])
    replace_team_set: Optional[Set[str]] = None

    for op in patch_ops.Operations:
        path = (op.path or "").lower()
        value = op.value
        op_type = op.op

        if path == "displayname":
            _handle_displayname_update(op_type, value, update_data)
        elif path == "externalid":
            _handle_externalid_update(op_type, value, update_data)
        elif path == "active":
            _handle_active_update(op_type, value, metadata)
        elif path in ("name.givenname", "name.familyname"):
            _handle_name_update(path, op_type, value, scim_metadata)
        elif path.startswith("groups"):
            new_replace_set = _handle_group_operations(op_type, value, teams_set)
            if new_replace_set is not None:
                replace_team_set = new_replace_set
        else:
            _handle_generic_metadata(path, op_type, value, metadata)

    final_team_set = replace_team_set if replace_team_set is not None else teams_set
    metadata["scim_metadata"] = scim_metadata
    update_data["metadata"] = metadata
    return update_data, final_team_set

async def patch_team_membership(
    user_id: str,
    teams_ids_to_add_user_to: List[str],
    teams_ids_to_remove_user_from: List[str],
) -> bool:
    """
    Add or remove user from teams
    """
    for _team_id in teams_ids_to_add_user_to:
            try:
                await team_member_add(
                    data=TeamMemberAddRequest(
                        team_id=_team_id,
                        member=Member(user_id=user_id, role="user"),
                    ),
                    user_api_key_dict=UserAPIKeyAuth(user_role=LitellmUserRoles.PROXY_ADMIN),
                )
            except Exception as e:
                verbose_proxy_logger.exception(f"Error adding user to team {_team_id}: {e}")

    for _team_id in teams_ids_to_remove_user_from:
        try:
            await team_member_delete(
                data=TeamMemberDeleteRequest(team_id=_team_id, user_id=user_id),
                user_api_key_dict=UserAPIKeyAuth(user_role=LitellmUserRoles.PROXY_ADMIN),
            )
        except Exception as e:
            verbose_proxy_logger.exception(f"Error removing user from team {_team_id}: {e}")
    

    return True

@scim_router.patch(
    "/Users/{user_id}",
    response_model=SCIMUser,
    status_code=200,
    dependencies=[Depends(user_api_key_auth), Depends(set_scim_content_type)],
)
async def patch_user(
    user_id: str = Path(..., title="User ID"),
    patch_ops: SCIMPatchOp = Body(...),
):
    """
    Patch a user according to SCIM v2 protocol
    """
    verbose_proxy_logger.debug("SCIM PATCH USER request: %s", patch_ops)

    try:
        prisma_client = await _get_prisma_client_or_raise_exception()
        existing_user = await _check_user_exists(user_id)

        update_data, final_team_set = _apply_patch_ops(
            existing_user=existing_user,
            patch_ops=patch_ops,
        )

        # Handle team membership changes
        await _handle_team_membership_changes(
            user_id=user_id,
            existing_teams=existing_user.teams or [],
            new_teams=list(final_team_set)
        )

        update_data["teams"] = list(final_team_set)

        # Serialize metadata to JSON string for Prisma to avoid GraphQL parsing issues
        if "metadata" in update_data and isinstance(update_data["metadata"], dict):
            from litellm.litellm_core_utils.safe_json_dumps import safe_dumps
            update_data["metadata"] = safe_dumps(update_data["metadata"])

        updated_user = await prisma_client.db.litellm_usertable.update(
            where={"user_id": user_id},
            data=update_data,
        )

        scim_user = await ScimTransformations.transform_litellm_user_to_scim_user(updated_user)

        return scim_user

    except Exception as e:
        raise handle_exception_on_proxy(e)


# Group Endpoints
@scim_router.get(
    "/Groups",
    response_model=SCIMListResponse,
    status_code=200,
    dependencies=[Depends(user_api_key_auth), Depends(set_scim_content_type)],
)
async def get_groups(
    startIndex: int = Query(1, ge=1),
    count: int = Query(10, ge=1, le=100),
    filter: Optional[str] = Query(None),
):
    """
    Get a list of groups according to SCIM v2 protocol
    """
    try:
        prisma_client = await _get_prisma_client_or_raise_exception()
        # Parse filter if provided (basic support)
        where_conditions = {}
        if filter:
            # Very basic filter support - only handling displayName eq
            if "displayName eq" in filter:
                team_alias = filter.split("displayName eq ")[1].strip("\"'")
                where_conditions["team_alias"] = team_alias

        # Get teams from database
        teams = await prisma_client.db.litellm_teamtable.find_many(
            where=where_conditions,
            skip=(startIndex - 1),
            take=count,
            order={"created_at": "desc"},
        )

        # Get total count for pagination
        total_count = await prisma_client.db.litellm_teamtable.count(
            where=where_conditions
        )

        # Convert to SCIM format
        scim_groups = []
        for team in teams:
            # Get team members with display names
            members = await _get_team_members_display(team.members or [])
            verbose_proxy_logger.debug(f"SCIM GET GROUPS members: {members}")
            team_alias = getattr(team, "team_alias", team.team_id)
            team_created_at = team.created_at.isoformat() if team.created_at else None
            team_updated_at = team.updated_at.isoformat() if team.updated_at else None

            scim_group = SCIMGroup(
                schemas=["urn:ietf:params:scim:schemas:core:2.0:Group"],
                id=team.team_id,
                displayName=team_alias,
                members=members,
                meta={
                    "resourceType": "Group",
                    "created": team_created_at,
                    "lastModified": team_updated_at,
                },
            )
            scim_groups.append(scim_group)

        verbose_proxy_logger.debug(f"SCIM GET GROUPS response: {scim_groups}")
        return SCIMListResponse(
            totalResults=total_count,
            startIndex=startIndex,
            itemsPerPage=min(count, len(scim_groups)),
            Resources=scim_groups,
        )

    except Exception as e:
        raise handle_exception_on_proxy(e)


@scim_router.get(
    "/Groups/{group_id}",
    response_model=SCIMGroup,
    status_code=200,
    dependencies=[Depends(user_api_key_auth), Depends(set_scim_content_type)],
)
async def get_group(
    group_id: str = Path(..., title="Group ID"),
):
    """
    Get a single group by ID according to SCIM v2 protocol
    """
    try:
        team = await _check_team_exists(group_id)

        scim_group = await ScimTransformations.transform_litellm_team_to_scim_group(
            team
        )
        verbose_proxy_logger.debug(f"SCIM GET GROUP response: {scim_group}")
        return scim_group

    except Exception as e:
        raise handle_exception_on_proxy(e)


@scim_router.post(
    "/Groups",
    response_model=SCIMGroup,
    status_code=201,
    dependencies=[Depends(user_api_key_auth), Depends(set_scim_content_type)],
)
async def create_group(
    group: SCIMGroup = Body(...),
):
    """
    Create a group according to SCIM v2 protocol
    """
    try:
        prisma_client = await _get_prisma_client_or_raise_exception()
        
        # Generate ID if not provided
        team_id = group.id or str(uuid.uuid4())

        # Check if team already exists
        existing_team = await prisma_client.db.litellm_teamtable.find_unique(
            where={"team_id": team_id}
        )

        if existing_team:
            raise HTTPException(
                status_code=409,
                detail={"error": f"Group already exists with ID: {team_id}"},
            )

        # Extract valid member IDs  
        member_ids = await _extract_group_member_ids(group)
        members_with_roles = [Member(user_id=member_id, role="user") for member_id in member_ids]

        # Create team in database
        created_team = await new_team(
            data=NewTeamRequest(
                team_id=team_id,
                team_alias=group.displayName,
                members_with_roles=members_with_roles,
            ),
            http_request=Request(scope={"type": "http", "path": "/scim/v2/Groups"}),
            user_api_key_dict=UserAPIKeyAuth(user_role=LitellmUserRoles.PROXY_ADMIN),
        )

        scim_group = await ScimTransformations.transform_litellm_team_to_scim_group(
            created_team
        )
        return scim_group
    except Exception as e:
        raise handle_exception_on_proxy(e)


@scim_router.put(
    "/Groups/{group_id}",
    response_model=SCIMGroup,
    status_code=200,
    dependencies=[Depends(user_api_key_auth), Depends(set_scim_content_type)],
)
async def update_group(
    group_id: str = Path(..., title="Group ID"),
    group: SCIMGroup = Body(...),
):
    """
    Update a group according to SCIM v2 protocol
    """
    try:
        prisma_client = await _get_prisma_client_or_raise_exception()
        existing_team = await _check_team_exists(group_id)

        # Extract valid member IDs
        member_ids = await _extract_group_member_ids(group)

        # Update team in database
        existing_metadata = existing_team.metadata if existing_team.metadata else {}
        updated_team = await prisma_client.db.litellm_teamtable.update(
            where={"team_id": group_id},
            data={
                "team_alias": group.displayName,
                "members": member_ids,
                "metadata": {**existing_metadata, "scim_data": group.model_dump()},
            },
        )

        # Handle user-team relationships
        current_members = existing_team.members or []

        # Add new members to team
        for member_id in member_ids:
            if member_id not in current_members:
                user = await prisma_client.db.litellm_usertable.find_unique(
                    where={"user_id": member_id}
                )
                if user:
                    current_user_teams = user.teams or []
                    if group_id not in current_user_teams:
                        await prisma_client.db.litellm_usertable.update(
                            where={"user_id": member_id},
                            data={"teams": {"push": group_id}},
                        )

        # Remove former members from team
        for member_id in current_members:
            if member_id not in member_ids:
                user = await prisma_client.db.litellm_usertable.find_unique(
                    where={"user_id": member_id}
                )
                if user:
                    current_user_teams = user.teams or []
                    if group_id in current_user_teams:
                        new_teams = [t for t in current_user_teams if t != group_id]
                        await prisma_client.db.litellm_usertable.update(
                            where={"user_id": member_id}, data={"teams": new_teams}
                        )

        # Get updated members for response
        members = await _get_team_members_display(member_ids)

        team_created_at = (
            updated_team.created_at.isoformat() if updated_team.created_at else None
        )
        team_updated_at = (
            updated_team.updated_at.isoformat() if updated_team.updated_at else None
        )

        return SCIMGroup(
            schemas=["urn:ietf:params:scim:schemas:core:2.0:Group"],
            id=group_id,
            displayName=updated_team.team_alias or group_id,
            members=members,
            meta={
                "resourceType": "Group",
                "created": team_created_at,
                "lastModified": team_updated_at,
            },
        )

    except Exception as e:
        raise handle_exception_on_proxy(e)


@scim_router.delete(
    "/Groups/{group_id}",
    status_code=204,
    dependencies=[Depends(user_api_key_auth)],
)
async def delete_group(
    group_id: str = Path(..., title="Group ID"),
):
    """
    Delete a group according to SCIM v2 protocol
    """
    try:
        prisma_client = await _get_prisma_client_or_raise_exception()
        existing_team = await _check_team_exists(group_id)

        # For each member, remove this team from their teams list
        for member_id in existing_team.members or []:
            user = await prisma_client.db.litellm_usertable.find_unique(
                where={"user_id": member_id}
            )
            if user:
                current_teams = user.teams or []
                if group_id in current_teams:
                    new_teams = [t for t in current_teams if t != group_id]
                    await prisma_client.db.litellm_usertable.update(
                        where={"user_id": member_id}, data={"teams": new_teams}
                    )

        # Delete team
        await prisma_client.db.litellm_teamtable.delete(where={"team_id": group_id})

        return Response(status_code=204)

    except Exception as e:
        raise handle_exception_on_proxy(e)


async def _process_group_patch_operations(
    patch_ops: SCIMPatchOp,
    existing_team,
    prisma_client
) -> Tuple[Dict[str, Any], Set[str]]:
    """Process patch operations for a group and return update data and final members."""
    update_data: Dict[str, Any] = {}
    
    # Create a fresh copy of existing metadata to avoid Prisma issues
    existing_metadata = existing_team.metadata or {}
    metadata = dict(existing_metadata) if existing_metadata else {}
    
    # Track member changes
    current_members = set(existing_team.members or [])
    final_members = current_members.copy()
    
    # Process each patch operation
    for op in patch_ops.Operations:
        path = (op.path or "").lower()
        value = op.value
        op_type = op.op

        if path == "displayname":
            if op_type == "remove":
                update_data["team_alias"] = None
            else:
                update_data["team_alias"] = str(value)
        elif path == "externalid":
            if op_type == "remove":
                metadata.pop("externalId", None)
            else:
                metadata["externalId"] = str(value)
        elif path.startswith("members"):
            # Handle member operations
            member_values = _extract_group_values(value)
            # Validate that users exist
            valid_members = []
            for member_id in member_values:
                user = await prisma_client.db.litellm_usertable.find_unique(
                    where={"user_id": member_id}
                )
                if user:
                    valid_members.append(member_id)
            
            if op_type == "replace":
                final_members = set(valid_members)
            elif op_type == "add":
                final_members.update(valid_members)
            elif op_type == "remove":
                for member_id in valid_members:
                    final_members.discard(member_id)
        else:
            # Handle other generic metadata
            if op_type == "remove":
                metadata.pop(path, None)
            else:
                metadata[path] = value

    # Include metadata in update data if it exists
    if metadata:
        update_data["metadata"] = metadata
    
    return update_data, final_members


async def _apply_group_patch_updates(
    group_id: str,
    update_data: Dict[str, Any],
    final_members: Set[str],
    prisma_client
):
    """Apply patch updates to the group in the database."""
    # Serialize metadata if present
    if "metadata" in update_data and isinstance(update_data["metadata"], dict):
        update_data["metadata"] = safe_dumps(update_data["metadata"])
    
    # Update members list
    update_data["members"] = list(final_members)

    # Update team in database
    updated_team = await prisma_client.db.litellm_teamtable.update(
        where={"team_id": group_id},
        data=update_data,
    )
    
    return updated_team


async def _handle_group_membership_changes(
    group_id: str,
    current_members: Set[str],
    final_members: Set[str]
):
    """Handle adding/removing members from the group."""
    members_to_add = final_members - current_members
    members_to_remove = current_members - final_members
    
    verbose_proxy_logger.debug(f"members_to_add: {members_to_add}")
    verbose_proxy_logger.debug(f"members_to_remove: {members_to_remove}")
    
    # Use existing helper functions for team membership changes
    for member_id in members_to_add:
        await patch_team_membership(
            user_id=member_id,
            teams_ids_to_add_user_to=[group_id],
            teams_ids_to_remove_user_from=[],
        )

    for member_id in members_to_remove:
        await patch_team_membership(
            user_id=member_id,
            teams_ids_to_add_user_to=[],
            teams_ids_to_remove_user_from=[group_id],
        )


@scim_router.patch(
    "/Groups/{group_id}",
    response_model=SCIMGroup,
    status_code=200,
    dependencies=[Depends(user_api_key_auth), Depends(set_scim_content_type)],
)
async def patch_group(
    group_id: str = Path(..., title="Group ID"),
    patch_ops: SCIMPatchOp = Body(...),
):
    """
    Patch a group according to SCIM v2 protocol
    """
    verbose_proxy_logger.debug("SCIM PATCH GROUP request: %s", patch_ops)

    try:
        prisma_client = await _get_prisma_client_or_raise_exception()
        existing_team = await _check_team_exists(group_id)

        # Process patch operations
        update_data, final_members = await _process_group_patch_operations(
            patch_ops, existing_team, prisma_client
        )
        
        # Track current members for comparison
        current_members = set(existing_team.members or [])

        # Apply updates to the database
        updated_team = await _apply_group_patch_updates(
            group_id, update_data, final_members, prisma_client
        )

        # Handle user-team relationship changes
        await _handle_group_membership_changes(
            group_id, current_members, final_members
        )

        # Convert to SCIM format and return
        scim_group = await ScimTransformations.transform_litellm_team_to_scim_group(
            updated_team
        )
        return scim_group

    except Exception as e:
        raise handle_exception_on_proxy(e)

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\distlib\compat.py ===
# -*- coding: utf-8 -*-
#
# Copyright (C) 2013-2017 Vinay Sajip.
# Licensed to the Python Software Foundation under a contributor agreement.
# See LICENSE.txt and CONTRIBUTORS.txt.
#
from __future__ import absolute_import

import os
import re
import shutil
import sys

try:
    import ssl
except ImportError:  # pragma: no cover
    ssl = None

if sys.version_info[0] < 3:  # pragma: no cover
    from StringIO import StringIO
    string_types = basestring,
    text_type = unicode
    from types import FileType as file_type
    import __builtin__ as builtins
    import ConfigParser as configparser
    from urlparse import urlparse, urlunparse, urljoin, urlsplit, urlunsplit
    from urllib import (urlretrieve, quote as _quote, unquote, url2pathname,
                        pathname2url, ContentTooShortError, splittype)

    def quote(s):
        if isinstance(s, unicode):
            s = s.encode('utf-8')
        return _quote(s)

    import urllib2
    from urllib2 import (Request, urlopen, URLError, HTTPError,
                         HTTPBasicAuthHandler, HTTPPasswordMgr, HTTPHandler,
                         HTTPRedirectHandler, build_opener)
    if ssl:
        from urllib2 import HTTPSHandler
    import httplib
    import xmlrpclib
    import Queue as queue
    from HTMLParser import HTMLParser
    import htmlentitydefs
    raw_input = raw_input
    from itertools import ifilter as filter
    from itertools import ifilterfalse as filterfalse

    # Leaving this around for now, in case it needs resurrecting in some way
    # _userprog = None
    # def splituser(host):
    # """splituser('user[:passwd]@host[:port]') --> 'user[:passwd]', 'host[:port]'."""
    # global _userprog
    # if _userprog is None:
    # import re
    # _userprog = re.compile('^(.*)@(.*)$')

    # match = _userprog.match(host)
    # if match: return match.group(1, 2)
    # return None, host

else:  # pragma: no cover
    from io import StringIO
    string_types = str,
    text_type = str
    from io import TextIOWrapper as file_type
    import builtins
    import configparser
    from urllib.parse import (urlparse, urlunparse, urljoin, quote, unquote,
                              urlsplit, urlunsplit, splittype)
    from urllib.request import (urlopen, urlretrieve, Request, url2pathname,
                                pathname2url, HTTPBasicAuthHandler,
                                HTTPPasswordMgr, HTTPHandler,
                                HTTPRedirectHandler, build_opener)
    if ssl:
        from urllib.request import HTTPSHandler
    from urllib.error import HTTPError, URLError, ContentTooShortError
    import http.client as httplib
    import urllib.request as urllib2
    import xmlrpc.client as xmlrpclib
    import queue
    from html.parser import HTMLParser
    import html.entities as htmlentitydefs
    raw_input = input
    from itertools import filterfalse
    filter = filter

try:
    from ssl import match_hostname, CertificateError
except ImportError:  # pragma: no cover

    class CertificateError(ValueError):
        pass

    def _dnsname_match(dn, hostname, max_wildcards=1):
        """Matching according to RFC 6125, section 6.4.3

        http://tools.ietf.org/html/rfc6125#section-6.4.3
        """
        pats = []
        if not dn:
            return False

        parts = dn.split('.')
        leftmost, remainder = parts[0], parts[1:]

        wildcards = leftmost.count('*')
        if wildcards > max_wildcards:
            # Issue #17980: avoid denials of service by refusing more
            # than one wildcard per fragment.  A survey of established
            # policy among SSL implementations showed it to be a
            # reasonable choice.
            raise CertificateError(
                "too many wildcards in certificate DNS name: " + repr(dn))

        # speed up common case w/o wildcards
        if not wildcards:
            return dn.lower() == hostname.lower()

        # RFC 6125, section 6.4.3, subitem 1.
        # The client SHOULD NOT attempt to match a presented identifier in which
        # the wildcard character comprises a label other than the left-most label.
        if leftmost == '*':
            # When '*' is a fragment by itself, it matches a non-empty dotless
            # fragment.
            pats.append('[^.]+')
        elif leftmost.startswith('xn--') or hostname.startswith('xn--'):
            # RFC 6125, section 6.4.3, subitem 3.
            # The client SHOULD NOT attempt to match a presented identifier
            # where the wildcard character is embedded within an A-label or
            # U-label of an internationalized domain name.
            pats.append(re.escape(leftmost))
        else:
            # Otherwise, '*' matches any dotless string, e.g. www*
            pats.append(re.escape(leftmost).replace(r'\*', '[^.]*'))

        # add the remaining fragments, ignore any wildcards
        for frag in remainder:
            pats.append(re.escape(frag))

        pat = re.compile(r'\A' + r'\.'.join(pats) + r'\Z', re.IGNORECASE)
        return pat.match(hostname)

    def match_hostname(cert, hostname):
        """Verify that *cert* (in decoded format as returned by
        SSLSocket.getpeercert()) matches the *hostname*.  RFC 2818 and RFC 6125
        rules are followed, but IP addresses are not accepted for *hostname*.

        CertificateError is raised on failure. On success, the function
        returns nothing.
        """
        if not cert:
            raise ValueError("empty or no certificate, match_hostname needs a "
                             "SSL socket or SSL context with either "
                             "CERT_OPTIONAL or CERT_REQUIRED")
        dnsnames = []
        san = cert.get('subjectAltName', ())
        for key, value in san:
            if key == 'DNS':
                if _dnsname_match(value, hostname):
                    return
                dnsnames.append(value)
        if not dnsnames:
            # The subject is only checked when there is no dNSName entry
            # in subjectAltName
            for sub in cert.get('subject', ()):
                for key, value in sub:
                    # XXX according to RFC 2818, the most specific Common Name
                    # must be used.
                    if key == 'commonName':
                        if _dnsname_match(value, hostname):
                            return
                        dnsnames.append(value)
        if len(dnsnames) > 1:
            raise CertificateError("hostname %r "
                                   "doesn't match either of %s" %
                                   (hostname, ', '.join(map(repr, dnsnames))))
        elif len(dnsnames) == 1:
            raise CertificateError("hostname %r "
                                   "doesn't match %r" %
                                   (hostname, dnsnames[0]))
        else:
            raise CertificateError("no appropriate commonName or "
                                   "subjectAltName fields were found")


try:
    from types import SimpleNamespace as Container
except ImportError:  # pragma: no cover

    class Container(object):
        """
        A generic container for when multiple values need to be returned
        """

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)


try:
    from shutil import which
except ImportError:  # pragma: no cover
    # Implementation from Python 3.3
    def which(cmd, mode=os.F_OK | os.X_OK, path=None):
        """Given a command, mode, and a PATH string, return the path which
        conforms to the given mode on the PATH, or None if there is no such
        file.

        `mode` defaults to os.F_OK | os.X_OK. `path` defaults to the result
        of os.environ.get("PATH"), or can be overridden with a custom search
        path.

        """

        # Check that a given file can be accessed with the correct mode.
        # Additionally check that `file` is not a directory, as on Windows
        # directories pass the os.access check.
        def _access_check(fn, mode):
            return (os.path.exists(fn) and os.access(fn, mode) and not os.path.isdir(fn))

        # If we're given a path with a directory part, look it up directly rather
        # than referring to PATH directories. This includes checking relative to the
        # current directory, e.g. ./script
        if os.path.dirname(cmd):
            if _access_check(cmd, mode):
                return cmd
            return None

        if path is None:
            path = os.environ.get("PATH", os.defpath)
        if not path:
            return None
        path = path.split(os.pathsep)

        if sys.platform == "win32":
            # The current directory takes precedence on Windows.
            if os.curdir not in path:
                path.insert(0, os.curdir)

            # PATHEXT is necessary to check on Windows.
            pathext = os.environ.get("PATHEXT", "").split(os.pathsep)
            # See if the given file matches any of the expected path extensions.
            # This will allow us to short circuit when given "python.exe".
            # If it does match, only test that one, otherwise we have to try
            # others.
            if any(cmd.lower().endswith(ext.lower()) for ext in pathext):
                files = [cmd]
            else:
                files = [cmd + ext for ext in pathext]
        else:
            # On other platforms you don't have things like PATHEXT to tell you
            # what file suffixes are executable, so just pass on cmd as-is.
            files = [cmd]

        seen = set()
        for dir in path:
            normdir = os.path.normcase(dir)
            if normdir not in seen:
                seen.add(normdir)
                for thefile in files:
                    name = os.path.join(dir, thefile)
                    if _access_check(name, mode):
                        return name
        return None


# ZipFile is a context manager in 2.7, but not in 2.6

from zipfile import ZipFile as BaseZipFile

if hasattr(BaseZipFile, '__enter__'):  # pragma: no cover
    ZipFile = BaseZipFile
else:  # pragma: no cover
    from zipfile import ZipExtFile as BaseZipExtFile

    class ZipExtFile(BaseZipExtFile):

        def __init__(self, base):
            self.__dict__.update(base.__dict__)

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            self.close()
            # return None, so if an exception occurred, it will propagate

    class ZipFile(BaseZipFile):

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            self.close()
            # return None, so if an exception occurred, it will propagate

        def open(self, *args, **kwargs):
            base = BaseZipFile.open(self, *args, **kwargs)
            return ZipExtFile(base)


try:
    from platform import python_implementation
except ImportError:  # pragma: no cover

    def python_implementation():
        """Return a string identifying the Python implementation."""
        if 'PyPy' in sys.version:
            return 'PyPy'
        if os.name == 'java':
            return 'Jython'
        if sys.version.startswith('IronPython'):
            return 'IronPython'
        return 'CPython'


import sysconfig

try:
    callable = callable
except NameError:  # pragma: no cover
    from collections.abc import Callable

    def callable(obj):
        return isinstance(obj, Callable)


try:
    fsencode = os.fsencode
    fsdecode = os.fsdecode
except AttributeError:  # pragma: no cover
    # Issue #99: on some systems (e.g. containerised),
    # sys.getfilesystemencoding() returns None, and we need a real value,
    # so fall back to utf-8. From the CPython 2.7 docs relating to Unix and
    # sys.getfilesystemencoding(): the return value is "the user’s preference
    # according to the result of nl_langinfo(CODESET), or None if the
    # nl_langinfo(CODESET) failed."
    _fsencoding = sys.getfilesystemencoding() or 'utf-8'
    if _fsencoding == 'mbcs':
        _fserrors = 'strict'
    else:
        _fserrors = 'surrogateescape'

    def fsencode(filename):
        if isinstance(filename, bytes):
            return filename
        elif isinstance(filename, text_type):
            return filename.encode(_fsencoding, _fserrors)
        else:
            raise TypeError("expect bytes or str, not %s" %
                            type(filename).__name__)

    def fsdecode(filename):
        if isinstance(filename, text_type):
            return filename
        elif isinstance(filename, bytes):
            return filename.decode(_fsencoding, _fserrors)
        else:
            raise TypeError("expect bytes or str, not %s" %
                            type(filename).__name__)


try:
    from tokenize import detect_encoding
except ImportError:  # pragma: no cover
    from codecs import BOM_UTF8, lookup

    cookie_re = re.compile(r"coding[:=]\s*([-\w.]+)")

    def _get_normal_name(orig_enc):
        """Imitates get_normal_name in tokenizer.c."""
        # Only care about the first 12 characters.
        enc = orig_enc[:12].lower().replace("_", "-")
        if enc == "utf-8" or enc.startswith("utf-8-"):
            return "utf-8"
        if enc in ("latin-1", "iso-8859-1", "iso-latin-1") or \
           enc.startswith(("latin-1-", "iso-8859-1-", "iso-latin-1-")):
            return "iso-8859-1"
        return orig_enc

    def detect_encoding(readline):
        """
        The detect_encoding() function is used to detect the encoding that should
        be used to decode a Python source file.  It requires one argument, readline,
        in the same way as the tokenize() generator.

        It will call readline a maximum of twice, and return the encoding used
        (as a string) and a list of any lines (left as bytes) it has read in.

        It detects the encoding from the presence of a utf-8 bom or an encoding
        cookie as specified in pep-0263.  If both a bom and a cookie are present,
        but disagree, a SyntaxError will be raised.  If the encoding cookie is an
        invalid charset, raise a SyntaxError.  Note that if a utf-8 bom is found,
        'utf-8-sig' is returned.

        If no encoding is specified, then the default of 'utf-8' will be returned.
        """
        try:
            filename = readline.__self__.name
        except AttributeError:
            filename = None
        bom_found = False
        encoding = None
        default = 'utf-8'

        def read_or_stop():
            try:
                return readline()
            except StopIteration:
                return b''

        def find_cookie(line):
            try:
                # Decode as UTF-8. Either the line is an encoding declaration,
                # in which case it should be pure ASCII, or it must be UTF-8
                # per default encoding.
                line_string = line.decode('utf-8')
            except UnicodeDecodeError:
                msg = "invalid or missing encoding declaration"
                if filename is not None:
                    msg = '{} for {!r}'.format(msg, filename)
                raise SyntaxError(msg)

            matches = cookie_re.findall(line_string)
            if not matches:
                return None
            encoding = _get_normal_name(matches[0])
            try:
                codec = lookup(encoding)
            except LookupError:
                # This behaviour mimics the Python interpreter
                if filename is None:
                    msg = "unknown encoding: " + encoding
                else:
                    msg = "unknown encoding for {!r}: {}".format(
                        filename, encoding)
                raise SyntaxError(msg)

            if bom_found:
                if codec.name != 'utf-8':
                    # This behaviour mimics the Python interpreter
                    if filename is None:
                        msg = 'encoding problem: utf-8'
                    else:
                        msg = 'encoding problem for {!r}: utf-8'.format(
                            filename)
                    raise SyntaxError(msg)
                encoding += '-sig'
            return encoding

        first = read_or_stop()
        if first.startswith(BOM_UTF8):
            bom_found = True
            first = first[3:]
            default = 'utf-8-sig'
        if not first:
            return default, []

        encoding = find_cookie(first)
        if encoding:
            return encoding, [first]

        second = read_or_stop()
        if not second:
            return default, [first]

        encoding = find_cookie(second)
        if encoding:
            return encoding, [first, second]

        return default, [first, second]


# For converting & <-> &amp; etc.
try:
    from html import escape
except ImportError:
    from cgi import escape
if sys.version_info[:2] < (3, 4):
    unescape = HTMLParser().unescape
else:
    from html import unescape

try:
    from collections import ChainMap
except ImportError:  # pragma: no cover
    from collections import MutableMapping

    try:
        from reprlib import recursive_repr as _recursive_repr
    except ImportError:

        def _recursive_repr(fillvalue='...'):
            '''
            Decorator to make a repr function return fillvalue for a recursive
            call
            '''

            def decorating_function(user_function):
                repr_running = set()

                def wrapper(self):
                    key = id(self), get_ident()
                    if key in repr_running:
                        return fillvalue
                    repr_running.add(key)
                    try:
                        result = user_function(self)
                    finally:
                        repr_running.discard(key)
                    return result

                # Can't use functools.wraps() here because of bootstrap issues
                wrapper.__module__ = getattr(user_function, '__module__')
                wrapper.__doc__ = getattr(user_function, '__doc__')
                wrapper.__name__ = getattr(user_function, '__name__')
                wrapper.__annotations__ = getattr(user_function,
                                                  '__annotations__', {})
                return wrapper

            return decorating_function

    class ChainMap(MutableMapping):
        '''
        A ChainMap groups multiple dicts (or other mappings) together
        to create a single, updateable view.

        The underlying mappings are stored in a list.  That list is public and can
        accessed or updated using the *maps* attribute.  There is no other state.

        Lookups search the underlying mappings successively until a key is found.
        In contrast, writes, updates, and deletions only operate on the first
        mapping.
        '''

        def __init__(self, *maps):
            '''Initialize a ChainMap by setting *maps* to the given mappings.
            If no mappings are provided, a single empty dictionary is used.

            '''
            self.maps = list(maps) or [{}]  # always at least one map

        def __missing__(self, key):
            raise KeyError(key)

        def __getitem__(self, key):
            for mapping in self.maps:
                try:
                    return mapping[
                        key]  # can't use 'key in mapping' with defaultdict
                except KeyError:
                    pass
            return self.__missing__(
                key)  # support subclasses that define __missing__

        def get(self, key, default=None):
            return self[key] if key in self else default

        def __len__(self):
            return len(set().union(
                *self.maps))  # reuses stored hash values if possible

        def __iter__(self):
            return iter(set().union(*self.maps))

        def __contains__(self, key):
            return any(key in m for m in self.maps)

        def __bool__(self):
            return any(self.maps)

        @_recursive_repr()
        def __repr__(self):
            return '{0.__class__.__name__}({1})'.format(
                self, ', '.join(map(repr, self.maps)))

        @classmethod
        def fromkeys(cls, iterable, *args):
            'Create a ChainMap with a single dict created from the iterable.'
            return cls(dict.fromkeys(iterable, *args))

        def copy(self):
            'New ChainMap or subclass with a new copy of maps[0] and refs to maps[1:]'
            return self.__class__(self.maps[0].copy(), *self.maps[1:])

        __copy__ = copy

        def new_child(self):  # like Django's Context.push()
            'New ChainMap with a new dict followed by all previous maps.'
            return self.__class__({}, *self.maps)

        @property
        def parents(self):  # like Django's Context.pop()
            'New ChainMap from maps[1:].'
            return self.__class__(*self.maps[1:])

        def __setitem__(self, key, value):
            self.maps[0][key] = value

        def __delitem__(self, key):
            try:
                del self.maps[0][key]
            except KeyError:
                raise KeyError(
                    'Key not found in the first mapping: {!r}'.format(key))

        def popitem(self):
            'Remove and return an item pair from maps[0]. Raise KeyError is maps[0] is empty.'
            try:
                return self.maps[0].popitem()
            except KeyError:
                raise KeyError('No keys found in the first mapping.')

        def pop(self, key, *args):
            'Remove *key* from maps[0] and return its value. Raise KeyError if *key* not in maps[0].'
            try:
                return self.maps[0].pop(key, *args)
            except KeyError:
                raise KeyError(
                    'Key not found in the first mapping: {!r}'.format(key))

        def clear(self):
            'Clear maps[0], leaving maps[1:] intact.'
            self.maps[0].clear()


try:
    from importlib.util import cache_from_source  # Python >= 3.4
except ImportError:  # pragma: no cover

    def cache_from_source(path, debug_override=None):
        assert path.endswith('.py')
        if debug_override is None:
            debug_override = __debug__
        if debug_override:
            suffix = 'c'
        else:
            suffix = 'o'
        return path + suffix


try:
    from collections import OrderedDict
except ImportError:  # pragma: no cover
    # {{{ http://code.activestate.com/recipes/576693/ (r9)
    # Backport of OrderedDict() class that runs on Python 2.4, 2.5, 2.6, 2.7 and pypy.
    # Passes Python2.7's test suite and incorporates all the latest updates.
    try:
        from thread import get_ident as _get_ident
    except ImportError:
        from dummy_thread import get_ident as _get_ident

    try:
        from _abcoll import KeysView, ValuesView, ItemsView
    except ImportError:
        pass

    class OrderedDict(dict):
        'Dictionary that remembers insertion order'

        # An inherited dict maps keys to values.
        # The inherited dict provides __getitem__, __len__, __contains__, and get.
        # The remaining methods are order-aware.
        # Big-O running times for all methods are the same as for regular dictionaries.

        # The internal self.__map dictionary maps keys to links in a doubly linked list.
        # The circular doubly linked list starts and ends with a sentinel element.
        # The sentinel element never gets deleted (this simplifies the algorithm).
        # Each link is stored as a list of length three:  [PREV, NEXT, KEY].

        def __init__(self, *args, **kwds):
            '''Initialize an ordered dictionary.  Signature is the same as for
            regular dictionaries, but keyword arguments are not recommended
            because their insertion order is arbitrary.

            '''
            if len(args) > 1:
                raise TypeError('expected at most 1 arguments, got %d' %
                                len(args))
            try:
                self.__root
            except AttributeError:
                self.__root = root = []  # sentinel node
                root[:] = [root, root, None]
                self.__map = {}
            self.__update(*args, **kwds)

        def __setitem__(self, key, value, dict_setitem=dict.__setitem__):
            'od.__setitem__(i, y) <==> od[i]=y'
            # Setting a new item creates a new link which goes at the end of the linked
            # list, and the inherited dictionary is updated with the new key/value pair.
            if key not in self:
                root = self.__root
                last = root[0]
                last[1] = root[0] = self.__map[key] = [last, root, key]
            dict_setitem(self, key, value)

        def __delitem__(self, key, dict_delitem=dict.__delitem__):
            'od.__delitem__(y) <==> del od[y]'
            # Deleting an existing item uses self.__map to find the link which is
            # then removed by updating the links in the predecessor and successor nodes.
            dict_delitem(self, key)
            link_prev, link_next, key = self.__map.pop(key)
            link_prev[1] = link_next
            link_next[0] = link_prev

        def __iter__(self):
            'od.__iter__() <==> iter(od)'
            root = self.__root
            curr = root[1]
            while curr is not root:
                yield curr[2]
                curr = curr[1]

        def __reversed__(self):
            'od.__reversed__() <==> reversed(od)'
            root = self.__root
            curr = root[0]
            while curr is not root:
                yield curr[2]
                curr = curr[0]

        def clear(self):
            'od.clear() -> None.  Remove all items from od.'
            try:
                for node in self.__map.itervalues():
                    del node[:]
                root = self.__root
                root[:] = [root, root, None]
                self.__map.clear()
            except AttributeError:
                pass
            dict.clear(self)

        def popitem(self, last=True):
            '''od.popitem() -> (k, v), return and remove a (key, value) pair.
            Pairs are returned in LIFO order if last is true or FIFO order if false.

            '''
            if not self:
                raise KeyError('dictionary is empty')
            root = self.__root
            if last:
                link = root[0]
                link_prev = link[0]
                link_prev[1] = root
                root[0] = link_prev
            else:
                link = root[1]
                link_next = link[1]
                root[1] = link_next
                link_next[0] = root
            key = link[2]
            del self.__map[key]
            value = dict.pop(self, key)
            return key, value

        # -- the following methods do not depend on the internal structure --

        def keys(self):
            'od.keys() -> list of keys in od'
            return list(self)

        def values(self):
            'od.values() -> list of values in od'
            return [self[key] for key in self]

        def items(self):
            'od.items() -> list of (key, value) pairs in od'
            return [(key, self[key]) for key in self]

        def iterkeys(self):
            'od.iterkeys() -> an iterator over the keys in od'
            return iter(self)

        def itervalues(self):
            'od.itervalues -> an iterator over the values in od'
            for k in self:
                yield self[k]

        def iteritems(self):
            'od.iteritems -> an iterator over the (key, value) items in od'
            for k in self:
                yield (k, self[k])

        def update(*args, **kwds):
            '''od.update(E, **F) -> None.  Update od from dict/iterable E and F.

            If E is a dict instance, does:           for k in E: od[k] = E[k]
            If E has a .keys() method, does:         for k in E.keys(): od[k] = E[k]
            Or if E is an iterable of items, does:   for k, v in E: od[k] = v
            In either case, this is followed by:     for k, v in F.items(): od[k] = v

            '''
            if len(args) > 2:
                raise TypeError('update() takes at most 2 positional '
                                'arguments (%d given)' % (len(args), ))
            elif not args:
                raise TypeError('update() takes at least 1 argument (0 given)')
            self = args[0]
            # Make progressively weaker assumptions about "other"
            other = ()
            if len(args) == 2:
                other = args[1]
            if isinstance(other, dict):
                for key in other:
                    self[key] = other[key]
            elif hasattr(other, 'keys'):
                for key in other.keys():
                    self[key] = other[key]
            else:
                for key, value in other:
                    self[key] = value
            for key, value in kwds.items():
                self[key] = value

        __update = update  # let subclasses override update without breaking __init__

        __marker = object()

        def pop(self, key, default=__marker):
            '''od.pop(k[,d]) -> v, remove specified key and return the corresponding value.
            If key is not found, d is returned if given, otherwise KeyError is raised.

            '''
            if key in self:
                result = self[key]
                del self[key]
                return result
            if default is self.__marker:
                raise KeyError(key)
            return default

        def setdefault(self, key, default=None):
            'od.setdefault(k[,d]) -> od.get(k,d), also set od[k]=d if k not in od'
            if key in self:
                return self[key]
            self[key] = default
            return default

        def __repr__(self, _repr_running=None):
            'od.__repr__() <==> repr(od)'
            if not _repr_running:
                _repr_running = {}
            call_key = id(self), _get_ident()
            if call_key in _repr_running:
                return '...'
            _repr_running[call_key] = 1
            try:
                if not self:
                    return '%s()' % (self.__class__.__name__, )
                return '%s(%r)' % (self.__class__.__name__, self.items())
            finally:
                del _repr_running[call_key]

        def __reduce__(self):
            'Return state information for pickling'
            items = [[k, self[k]] for k in self]
            inst_dict = vars(self).copy()
            for k in vars(OrderedDict()):
                inst_dict.pop(k, None)
            if inst_dict:
                return (self.__class__, (items, ), inst_dict)
            return self.__class__, (items, )

        def copy(self):
            'od.copy() -> a shallow copy of od'
            return self.__class__(self)

        @classmethod
        def fromkeys(cls, iterable, value=None):
            '''OD.fromkeys(S[, v]) -> New ordered dictionary with keys from S
            and values equal to v (which defaults to None).

            '''
            d = cls()
            for key in iterable:
                d[key] = value
            return d

        def __eq__(self, other):
            '''od.__eq__(y) <==> od==y.  Comparison to another OD is order-sensitive
            while comparison to a regular mapping is order-insensitive.

            '''
            if isinstance(other, OrderedDict):
                return len(self) == len(
                    other) and self.items() == other.items()
            return dict.__eq__(self, other)

        def __ne__(self, other):
            return not self == other

        # -- the following methods are only used in Python 2.7 --

        def viewkeys(self):
            "od.viewkeys() -> a set-like object providing a view on od's keys"
            return KeysView(self)

        def viewvalues(self):
            "od.viewvalues() -> an object providing a view on od's values"
            return ValuesView(self)

        def viewitems(self):
            "od.viewitems() -> a set-like object providing a view on od's items"
            return ItemsView(self)


try:
    from logging.config import BaseConfigurator, valid_ident
except ImportError:  # pragma: no cover
    IDENTIFIER = re.compile('^[a-z_][a-z0-9_]*$', re.I)

    def valid_ident(s):
        m = IDENTIFIER.match(s)
        if not m:
            raise ValueError('Not a valid Python identifier: %r' % s)
        return True

    # The ConvertingXXX classes are wrappers around standard Python containers,
    # and they serve to convert any suitable values in the container. The
    # conversion converts base dicts, lists and tuples to their wrapped
    # equivalents, whereas strings which match a conversion format are converted
    # appropriately.
    #
    # Each wrapper should have a configurator attribute holding the actual
    # configurator to use for conversion.

    class ConvertingDict(dict):
        """A converting dictionary wrapper."""

        def __getitem__(self, key):
            value = dict.__getitem__(self, key)
            result = self.configurator.convert(value)
            # If the converted value is different, save for next time
            if value is not result:
                self[key] = result
                if type(result) in (ConvertingDict, ConvertingList,
                                    ConvertingTuple):
                    result.parent = self
                    result.key = key
            return result

        def get(self, key, default=None):
            value = dict.get(self, key, default)
            result = self.configurator.convert(value)
            # If the converted value is different, save for next time
            if value is not result:
                self[key] = result
                if type(result) in (ConvertingDict, ConvertingList,
                                    ConvertingTuple):
                    result.parent = self
                    result.key = key
            return result

    def pop(self, key, default=None):
        value = dict.pop(self, key, default)
        result = self.configurator.convert(value)
        if value is not result:
            if type(result) in (ConvertingDict, ConvertingList,
                                ConvertingTuple):
                result.parent = self
                result.key = key
        return result

    class ConvertingList(list):
        """A converting list wrapper."""

        def __getitem__(self, key):
            value = list.__getitem__(self, key)
            result = self.configurator.convert(value)
            # If the converted value is different, save for next time
            if value is not result:
                self[key] = result
                if type(result) in (ConvertingDict, ConvertingList,
                                    ConvertingTuple):
                    result.parent = self
                    result.key = key
            return result

        def pop(self, idx=-1):
            value = list.pop(self, idx)
            result = self.configurator.convert(value)
            if value is not result:
                if type(result) in (ConvertingDict, ConvertingList,
                                    ConvertingTuple):
                    result.parent = self
            return result

    class ConvertingTuple(tuple):
        """A converting tuple wrapper."""

        def __getitem__(self, key):
            value = tuple.__getitem__(self, key)
            result = self.configurator.convert(value)
            if value is not result:
                if type(result) in (ConvertingDict, ConvertingList,
                                    ConvertingTuple):
                    result.parent = self
                    result.key = key
            return result

    class BaseConfigurator(object):
        """
        The configurator base class which defines some useful defaults.
        """

        CONVERT_PATTERN = re.compile(r'^(?P<prefix>[a-z]+)://(?P<suffix>.*)$')

        WORD_PATTERN = re.compile(r'^\s*(\w+)\s*')
        DOT_PATTERN = re.compile(r'^\.\s*(\w+)\s*')
        INDEX_PATTERN = re.compile(r'^\[\s*(\w+)\s*\]\s*')
        DIGIT_PATTERN = re.compile(r'^\d+$')

        value_converters = {
            'ext': 'ext_convert',
            'cfg': 'cfg_convert',
        }

        # We might want to use a different one, e.g. importlib
        importer = staticmethod(__import__)

        def __init__(self, config):
            self.config = ConvertingDict(config)
            self.config.configurator = self

        def resolve(self, s):
            """
            Resolve strings to objects using standard import and attribute
            syntax.
            """
            name = s.split('.')
            used = name.pop(0)
            try:
                found = self.importer(used)
                for frag in name:
                    used += '.' + frag
                    try:
                        found = getattr(found, frag)
                    except AttributeError:
                        self.importer(used)
                        found = getattr(found, frag)
                return found
            except ImportError:
                e, tb = sys.exc_info()[1:]
                v = ValueError('Cannot resolve %r: %s' % (s, e))
                v.__cause__, v.__traceback__ = e, tb
                raise v

        def ext_convert(self, value):
            """Default converter for the ext:// protocol."""
            return self.resolve(value)

        def cfg_convert(self, value):
            """Default converter for the cfg:// protocol."""
            rest = value
            m = self.WORD_PATTERN.match(rest)
            if m is None:
                raise ValueError("Unable to convert %r" % value)
            else:
                rest = rest[m.end():]
                d = self.config[m.groups()[0]]
                while rest:
                    m = self.DOT_PATTERN.match(rest)
                    if m:
                        d = d[m.groups()[0]]
                    else:
                        m = self.INDEX_PATTERN.match(rest)
                        if m:
                            idx = m.groups()[0]
                            if not self.DIGIT_PATTERN.match(idx):
                                d = d[idx]
                            else:
                                try:
                                    n = int(
                                        idx
                                    )  # try as number first (most likely)
                                    d = d[n]
                                except TypeError:
                                    d = d[idx]
                    if m:
                        rest = rest[m.end():]
                    else:
                        raise ValueError('Unable to convert '
                                         '%r at %r' % (value, rest))
            # rest should be empty
            return d

        def convert(self, value):
            """
            Convert values to an appropriate type. dicts, lists and tuples are
            replaced by their converting alternatives. Strings are checked to
            see if they have a conversion format and are converted if they do.
            """
            if not isinstance(value, ConvertingDict) and isinstance(
                    value, dict):
                value = ConvertingDict(value)
                value.configurator = self
            elif not isinstance(value, ConvertingList) and isinstance(
                    value, list):
                value = ConvertingList(value)
                value.configurator = self
            elif not isinstance(value, ConvertingTuple) and isinstance(value, tuple):
                value = ConvertingTuple(value)
                value.configurator = self
            elif isinstance(value, string_types):
                m = self.CONVERT_PATTERN.match(value)
                if m:
                    d = m.groupdict()
                    prefix = d['prefix']
                    converter = self.value_converters.get(prefix, None)
                    if converter:
                        suffix = d['suffix']
                        converter = getattr(self, converter)
                        value = converter(suffix)
            return value

        def configure_custom(self, config):
            """Configure an object with a user-supplied factory."""
            c = config.pop('()')
            if not callable(c):
                c = self.resolve(c)
            props = config.pop('.', None)
            # Check for valid identifiers
            kwargs = dict([(k, config[k]) for k in config if valid_ident(k)])
            result = c(**kwargs)
            if props:
                for name, value in props.items():
                    setattr(result, name, value)
            return result

        def as_tuple(self, value):
            """Utility function which converts lists to tuples."""
            if isinstance(value, list):
                value = tuple(value)
            return value

# === NexusCore/openenv\Lib\site-packages\yaml\emitter.py ===

# Emitter expects events obeying the following grammar:
# stream ::= STREAM-START document* STREAM-END
# document ::= DOCUMENT-START node DOCUMENT-END
# node ::= SCALAR | sequence | mapping
# sequence ::= SEQUENCE-START node* SEQUENCE-END
# mapping ::= MAPPING-START (node node)* MAPPING-END

__all__ = ['Emitter', 'EmitterError']

from .error import YAMLError
from .events import *

class EmitterError(YAMLError):
    pass

class ScalarAnalysis:
    def __init__(self, scalar, empty, multiline,
            allow_flow_plain, allow_block_plain,
            allow_single_quoted, allow_double_quoted,
            allow_block):
        self.scalar = scalar
        self.empty = empty
        self.multiline = multiline
        self.allow_flow_plain = allow_flow_plain
        self.allow_block_plain = allow_block_plain
        self.allow_single_quoted = allow_single_quoted
        self.allow_double_quoted = allow_double_quoted
        self.allow_block = allow_block

class Emitter:

    DEFAULT_TAG_PREFIXES = {
        '!' : '!',
        'tag:yaml.org,2002:' : '!!',
    }

    def __init__(self, stream, canonical=None, indent=None, width=None,
            allow_unicode=None, line_break=None):

        # The stream should have the methods `write` and possibly `flush`.
        self.stream = stream

        # Encoding can be overridden by STREAM-START.
        self.encoding = None

        # Emitter is a state machine with a stack of states to handle nested
        # structures.
        self.states = []
        self.state = self.expect_stream_start

        # Current event and the event queue.
        self.events = []
        self.event = None

        # The current indentation level and the stack of previous indents.
        self.indents = []
        self.indent = None

        # Flow level.
        self.flow_level = 0

        # Contexts.
        self.root_context = False
        self.sequence_context = False
        self.mapping_context = False
        self.simple_key_context = False

        # Characteristics of the last emitted character:
        #  - current position.
        #  - is it a whitespace?
        #  - is it an indention character
        #    (indentation space, '-', '?', or ':')?
        self.line = 0
        self.column = 0
        self.whitespace = True
        self.indention = True

        # Whether the document requires an explicit document indicator
        self.open_ended = False

        # Formatting details.
        self.canonical = canonical
        self.allow_unicode = allow_unicode
        self.best_indent = 2
        if indent and 1 < indent < 10:
            self.best_indent = indent
        self.best_width = 80
        if width and width > self.best_indent*2:
            self.best_width = width
        self.best_line_break = '\n'
        if line_break in ['\r', '\n', '\r\n']:
            self.best_line_break = line_break

        # Tag prefixes.
        self.tag_prefixes = None

        # Prepared anchor and tag.
        self.prepared_anchor = None
        self.prepared_tag = None

        # Scalar analysis and style.
        self.analysis = None
        self.style = None

    def dispose(self):
        # Reset the state attributes (to clear self-references)
        self.states = []
        self.state = None

    def emit(self, event):
        self.events.append(event)
        while not self.need_more_events():
            self.event = self.events.pop(0)
            self.state()
            self.event = None

    # In some cases, we wait for a few next events before emitting.

    def need_more_events(self):
        if not self.events:
            return True
        event = self.events[0]
        if isinstance(event, DocumentStartEvent):
            return self.need_events(1)
        elif isinstance(event, SequenceStartEvent):
            return self.need_events(2)
        elif isinstance(event, MappingStartEvent):
            return self.need_events(3)
        else:
            return False

    def need_events(self, count):
        level = 0
        for event in self.events[1:]:
            if isinstance(event, (DocumentStartEvent, CollectionStartEvent)):
                level += 1
            elif isinstance(event, (DocumentEndEvent, CollectionEndEvent)):
                level -= 1
            elif isinstance(event, StreamEndEvent):
                level = -1
            if level < 0:
                return False
        return (len(self.events) < count+1)

    def increase_indent(self, flow=False, indentless=False):
        self.indents.append(self.indent)
        if self.indent is None:
            if flow:
                self.indent = self.best_indent
            else:
                self.indent = 0
        elif not indentless:
            self.indent += self.best_indent

    # States.

    # Stream handlers.

    def expect_stream_start(self):
        if isinstance(self.event, StreamStartEvent):
            if self.event.encoding and not hasattr(self.stream, 'encoding'):
                self.encoding = self.event.encoding
            self.write_stream_start()
            self.state = self.expect_first_document_start
        else:
            raise EmitterError("expected StreamStartEvent, but got %s"
                    % self.event)

    def expect_nothing(self):
        raise EmitterError("expected nothing, but got %s" % self.event)

    # Document handlers.

    def expect_first_document_start(self):
        return self.expect_document_start(first=True)

    def expect_document_start(self, first=False):
        if isinstance(self.event, DocumentStartEvent):
            if (self.event.version or self.event.tags) and self.open_ended:
                self.write_indicator('...', True)
                self.write_indent()
            if self.event.version:
                version_text = self.prepare_version(self.event.version)
                self.write_version_directive(version_text)
            self.tag_prefixes = self.DEFAULT_TAG_PREFIXES.copy()
            if self.event.tags:
                handles = sorted(self.event.tags.keys())
                for handle in handles:
                    prefix = self.event.tags[handle]
                    self.tag_prefixes[prefix] = handle
                    handle_text = self.prepare_tag_handle(handle)
                    prefix_text = self.prepare_tag_prefix(prefix)
                    self.write_tag_directive(handle_text, prefix_text)
            implicit = (first and not self.event.explicit and not self.canonical
                    and not self.event.version and not self.event.tags
                    and not self.check_empty_document())
            if not implicit:
                self.write_indent()
                self.write_indicator('---', True)
                if self.canonical:
                    self.write_indent()
            self.state = self.expect_document_root
        elif isinstance(self.event, StreamEndEvent):
            if self.open_ended:
                self.write_indicator('...', True)
                self.write_indent()
            self.write_stream_end()
            self.state = self.expect_nothing
        else:
            raise EmitterError("expected DocumentStartEvent, but got %s"
                    % self.event)

    def expect_document_end(self):
        if isinstance(self.event, DocumentEndEvent):
            self.write_indent()
            if self.event.explicit:
                self.write_indicator('...', True)
                self.write_indent()
            self.flush_stream()
            self.state = self.expect_document_start
        else:
            raise EmitterError("expected DocumentEndEvent, but got %s"
                    % self.event)

    def expect_document_root(self):
        self.states.append(self.expect_document_end)
        self.expect_node(root=True)

    # Node handlers.

    def expect_node(self, root=False, sequence=False, mapping=False,
            simple_key=False):
        self.root_context = root
        self.sequence_context = sequence
        self.mapping_context = mapping
        self.simple_key_context = simple_key
        if isinstance(self.event, AliasEvent):
            self.expect_alias()
        elif isinstance(self.event, (ScalarEvent, CollectionStartEvent)):
            self.process_anchor('&')
            self.process_tag()
            if isinstance(self.event, ScalarEvent):
                self.expect_scalar()
            elif isinstance(self.event, SequenceStartEvent):
                if self.flow_level or self.canonical or self.event.flow_style   \
                        or self.check_empty_sequence():
                    self.expect_flow_sequence()
                else:
                    self.expect_block_sequence()
            elif isinstance(self.event, MappingStartEvent):
                if self.flow_level or self.canonical or self.event.flow_style   \
                        or self.check_empty_mapping():
                    self.expect_flow_mapping()
                else:
                    self.expect_block_mapping()
        else:
            raise EmitterError("expected NodeEvent, but got %s" % self.event)

    def expect_alias(self):
        if self.event.anchor is None:
            raise EmitterError("anchor is not specified for alias")
        self.process_anchor('*')
        self.state = self.states.pop()

    def expect_scalar(self):
        self.increase_indent(flow=True)
        self.process_scalar()
        self.indent = self.indents.pop()
        self.state = self.states.pop()

    # Flow sequence handlers.

    def expect_flow_sequence(self):
        self.write_indicator('[', True, whitespace=True)
        self.flow_level += 1
        self.increase_indent(flow=True)
        self.state = self.expect_first_flow_sequence_item

    def expect_first_flow_sequence_item(self):
        if isinstance(self.event, SequenceEndEvent):
            self.indent = self.indents.pop()
            self.flow_level -= 1
            self.write_indicator(']', False)
            self.state = self.states.pop()
        else:
            if self.canonical or self.column > self.best_width:
                self.write_indent()
            self.states.append(self.expect_flow_sequence_item)
            self.expect_node(sequence=True)

    def expect_flow_sequence_item(self):
        if isinstance(self.event, SequenceEndEvent):
            self.indent = self.indents.pop()
            self.flow_level -= 1
            if self.canonical:
                self.write_indicator(',', False)
                self.write_indent()
            self.write_indicator(']', False)
            self.state = self.states.pop()
        else:
            self.write_indicator(',', False)
            if self.canonical or self.column > self.best_width:
                self.write_indent()
            self.states.append(self.expect_flow_sequence_item)
            self.expect_node(sequence=True)

    # Flow mapping handlers.

    def expect_flow_mapping(self):
        self.write_indicator('{', True, whitespace=True)
        self.flow_level += 1
        self.increase_indent(flow=True)
        self.state = self.expect_first_flow_mapping_key

    def expect_first_flow_mapping_key(self):
        if isinstance(self.event, MappingEndEvent):
            self.indent = self.indents.pop()
            self.flow_level -= 1
            self.write_indicator('}', False)
            self.state = self.states.pop()
        else:
            if self.canonical or self.column > self.best_width:
                self.write_indent()
            if not self.canonical and self.check_simple_key():
                self.states.append(self.expect_flow_mapping_simple_value)
                self.expect_node(mapping=True, simple_key=True)
            else:
                self.write_indicator('?', True)
                self.states.append(self.expect_flow_mapping_value)
                self.expect_node(mapping=True)

    def expect_flow_mapping_key(self):
        if isinstance(self.event, MappingEndEvent):
            self.indent = self.indents.pop()
            self.flow_level -= 1
            if self.canonical:
                self.write_indicator(',', False)
                self.write_indent()
            self.write_indicator('}', False)
            self.state = self.states.pop()
        else:
            self.write_indicator(',', False)
            if self.canonical or self.column > self.best_width:
                self.write_indent()
            if not self.canonical and self.check_simple_key():
                self.states.append(self.expect_flow_mapping_simple_value)
                self.expect_node(mapping=True, simple_key=True)
            else:
                self.write_indicator('?', True)
                self.states.append(self.expect_flow_mapping_value)
                self.expect_node(mapping=True)

    def expect_flow_mapping_simple_value(self):
        self.write_indicator(':', False)
        self.states.append(self.expect_flow_mapping_key)
        self.expect_node(mapping=True)

    def expect_flow_mapping_value(self):
        if self.canonical or self.column > self.best_width:
            self.write_indent()
        self.write_indicator(':', True)
        self.states.append(self.expect_flow_mapping_key)
        self.expect_node(mapping=True)

    # Block sequence handlers.

    def expect_block_sequence(self):
        indentless = (self.mapping_context and not self.indention)
        self.increase_indent(flow=False, indentless=indentless)
        self.state = self.expect_first_block_sequence_item

    def expect_first_block_sequence_item(self):
        return self.expect_block_sequence_item(first=True)

    def expect_block_sequence_item(self, first=False):
        if not first and isinstance(self.event, SequenceEndEvent):
            self.indent = self.indents.pop()
            self.state = self.states.pop()
        else:
            self.write_indent()
            self.write_indicator('-', True, indention=True)
            self.states.append(self.expect_block_sequence_item)
            self.expect_node(sequence=True)

    # Block mapping handlers.

    def expect_block_mapping(self):
        self.increase_indent(flow=False)
        self.state = self.expect_first_block_mapping_key

    def expect_first_block_mapping_key(self):
        return self.expect_block_mapping_key(first=True)

    def expect_block_mapping_key(self, first=False):
        if not first and isinstance(self.event, MappingEndEvent):
            self.indent = self.indents.pop()
            self.state = self.states.pop()
        else:
            self.write_indent()
            if self.check_simple_key():
                self.states.append(self.expect_block_mapping_simple_value)
                self.expect_node(mapping=True, simple_key=True)
            else:
                self.write_indicator('?', True, indention=True)
                self.states.append(self.expect_block_mapping_value)
                self.expect_node(mapping=True)

    def expect_block_mapping_simple_value(self):
        self.write_indicator(':', False)
        self.states.append(self.expect_block_mapping_key)
        self.expect_node(mapping=True)

    def expect_block_mapping_value(self):
        self.write_indent()
        self.write_indicator(':', True, indention=True)
        self.states.append(self.expect_block_mapping_key)
        self.expect_node(mapping=True)

    # Checkers.

    def check_empty_sequence(self):
        return (isinstance(self.event, SequenceStartEvent) and self.events
                and isinstance(self.events[0], SequenceEndEvent))

    def check_empty_mapping(self):
        return (isinstance(self.event, MappingStartEvent) and self.events
                and isinstance(self.events[0], MappingEndEvent))

    def check_empty_document(self):
        if not isinstance(self.event, DocumentStartEvent) or not self.events:
            return False
        event = self.events[0]
        return (isinstance(event, ScalarEvent) and event.anchor is None
                and event.tag is None and event.implicit and event.value == '')

    def check_simple_key(self):
        length = 0
        if isinstance(self.event, NodeEvent) and self.event.anchor is not None:
            if self.prepared_anchor is None:
                self.prepared_anchor = self.prepare_anchor(self.event.anchor)
            length += len(self.prepared_anchor)
        if isinstance(self.event, (ScalarEvent, CollectionStartEvent))  \
                and self.event.tag is not None:
            if self.prepared_tag is None:
                self.prepared_tag = self.prepare_tag(self.event.tag)
            length += len(self.prepared_tag)
        if isinstance(self.event, ScalarEvent):
            if self.analysis is None:
                self.analysis = self.analyze_scalar(self.event.value)
            length += len(self.analysis.scalar)
        return (length < 128 and (isinstance(self.event, AliasEvent)
            or (isinstance(self.event, ScalarEvent)
                    and not self.analysis.empty and not self.analysis.multiline)
            or self.check_empty_sequence() or self.check_empty_mapping()))

    # Anchor, Tag, and Scalar processors.

    def process_anchor(self, indicator):
        if self.event.anchor is None:
            self.prepared_anchor = None
            return
        if self.prepared_anchor is None:
            self.prepared_anchor = self.prepare_anchor(self.event.anchor)
        if self.prepared_anchor:
            self.write_indicator(indicator+self.prepared_anchor, True)
        self.prepared_anchor = None

    def process_tag(self):
        tag = self.event.tag
        if isinstance(self.event, ScalarEvent):
            if self.style is None:
                self.style = self.choose_scalar_style()
            if ((not self.canonical or tag is None) and
                ((self.style == '' and self.event.implicit[0])
                        or (self.style != '' and self.event.implicit[1]))):
                self.prepared_tag = None
                return
            if self.event.implicit[0] and tag is None:
                tag = '!'
                self.prepared_tag = None
        else:
            if (not self.canonical or tag is None) and self.event.implicit:
                self.prepared_tag = None
                return
        if tag is None:
            raise EmitterError("tag is not specified")
        if self.prepared_tag is None:
            self.prepared_tag = self.prepare_tag(tag)
        if self.prepared_tag:
            self.write_indicator(self.prepared_tag, True)
        self.prepared_tag = None

    def choose_scalar_style(self):
        if self.analysis is None:
            self.analysis = self.analyze_scalar(self.event.value)
        if self.event.style == '"' or self.canonical:
            return '"'
        if not self.event.style and self.event.implicit[0]:
            if (not (self.simple_key_context and
                    (self.analysis.empty or self.analysis.multiline))
                and (self.flow_level and self.analysis.allow_flow_plain
                    or (not self.flow_level and self.analysis.allow_block_plain))):
                return ''
        if self.event.style and self.event.style in '|>':
            if (not self.flow_level and not self.simple_key_context
                    and self.analysis.allow_block):
                return self.event.style
        if not self.event.style or self.event.style == '\'':
            if (self.analysis.allow_single_quoted and
                    not (self.simple_key_context and self.analysis.multiline)):
                return '\''
        return '"'

    def process_scalar(self):
        if self.analysis is None:
            self.analysis = self.analyze_scalar(self.event.value)
        if self.style is None:
            self.style = self.choose_scalar_style()
        split = (not self.simple_key_context)
        #if self.analysis.multiline and split    \
        #        and (not self.style or self.style in '\'\"'):
        #    self.write_indent()
        if self.style == '"':
            self.write_double_quoted(self.analysis.scalar, split)
        elif self.style == '\'':
            self.write_single_quoted(self.analysis.scalar, split)
        elif self.style == '>':
            self.write_folded(self.analysis.scalar)
        elif self.style == '|':
            self.write_literal(self.analysis.scalar)
        else:
            self.write_plain(self.analysis.scalar, split)
        self.analysis = None
        self.style = None

    # Analyzers.

    def prepare_version(self, version):
        major, minor = version
        if major != 1:
            raise EmitterError("unsupported YAML version: %d.%d" % (major, minor))
        return '%d.%d' % (major, minor)

    def prepare_tag_handle(self, handle):
        if not handle:
            raise EmitterError("tag handle must not be empty")
        if handle[0] != '!' or handle[-1] != '!':
            raise EmitterError("tag handle must start and end with '!': %r" % handle)
        for ch in handle[1:-1]:
            if not ('0' <= ch <= '9' or 'A' <= ch <= 'Z' or 'a' <= ch <= 'z'    \
                    or ch in '-_'):
                raise EmitterError("invalid character %r in the tag handle: %r"
                        % (ch, handle))
        return handle

    def prepare_tag_prefix(self, prefix):
        if not prefix:
            raise EmitterError("tag prefix must not be empty")
        chunks = []
        start = end = 0
        if prefix[0] == '!':
            end = 1
        while end < len(prefix):
            ch = prefix[end]
            if '0' <= ch <= '9' or 'A' <= ch <= 'Z' or 'a' <= ch <= 'z' \
                    or ch in '-;/?!:@&=+$,_.~*\'()[]':
                end += 1
            else:
                if start < end:
                    chunks.append(prefix[start:end])
                start = end = end+1
                data = ch.encode('utf-8')
                for ch in data:
                    chunks.append('%%%02X' % ord(ch))
        if start < end:
            chunks.append(prefix[start:end])
        return ''.join(chunks)

    def prepare_tag(self, tag):
        if not tag:
            raise EmitterError("tag must not be empty")
        if tag == '!':
            return tag
        handle = None
        suffix = tag
        prefixes = sorted(self.tag_prefixes.keys())
        for prefix in prefixes:
            if tag.startswith(prefix)   \
                    and (prefix == '!' or len(prefix) < len(tag)):
                handle = self.tag_prefixes[prefix]
                suffix = tag[len(prefix):]
        chunks = []
        start = end = 0
        while end < len(suffix):
            ch = suffix[end]
            if '0' <= ch <= '9' or 'A' <= ch <= 'Z' or 'a' <= ch <= 'z' \
                    or ch in '-;/?:@&=+$,_.~*\'()[]'   \
                    or (ch == '!' and handle != '!'):
                end += 1
            else:
                if start < end:
                    chunks.append(suffix[start:end])
                start = end = end+1
                data = ch.encode('utf-8')
                for ch in data:
                    chunks.append('%%%02X' % ch)
        if start < end:
            chunks.append(suffix[start:end])
        suffix_text = ''.join(chunks)
        if handle:
            return '%s%s' % (handle, suffix_text)
        else:
            return '!<%s>' % suffix_text

    def prepare_anchor(self, anchor):
        if not anchor:
            raise EmitterError("anchor must not be empty")
        for ch in anchor:
            if not ('0' <= ch <= '9' or 'A' <= ch <= 'Z' or 'a' <= ch <= 'z'    \
                    or ch in '-_'):
                raise EmitterError("invalid character %r in the anchor: %r"
                        % (ch, anchor))
        return anchor

    def analyze_scalar(self, scalar):

        # Empty scalar is a special case.
        if not scalar:
            return ScalarAnalysis(scalar=scalar, empty=True, multiline=False,
                    allow_flow_plain=False, allow_block_plain=True,
                    allow_single_quoted=True, allow_double_quoted=True,
                    allow_block=False)

        # Indicators and special characters.
        block_indicators = False
        flow_indicators = False
        line_breaks = False
        special_characters = False

        # Important whitespace combinations.
        leading_space = False
        leading_break = False
        trailing_space = False
        trailing_break = False
        break_space = False
        space_break = False

        # Check document indicators.
        if scalar.startswith('---') or scalar.startswith('...'):
            block_indicators = True
            flow_indicators = True

        # First character or preceded by a whitespace.
        preceded_by_whitespace = True

        # Last character or followed by a whitespace.
        followed_by_whitespace = (len(scalar) == 1 or
                scalar[1] in '\0 \t\r\n\x85\u2028\u2029')

        # The previous character is a space.
        previous_space = False

        # The previous character is a break.
        previous_break = False

        index = 0
        while index < len(scalar):
            ch = scalar[index]

            # Check for indicators.
            if index == 0:
                # Leading indicators are special characters.
                if ch in '#,[]{}&*!|>\'\"%@`':
                    flow_indicators = True
                    block_indicators = True
                if ch in '?:':
                    flow_indicators = True
                    if followed_by_whitespace:
                        block_indicators = True
                if ch == '-' and followed_by_whitespace:
                    flow_indicators = True
                    block_indicators = True
            else:
                # Some indicators cannot appear within a scalar as well.
                if ch in ',?[]{}':
                    flow_indicators = True
                if ch == ':':
                    flow_indicators = True
                    if followed_by_whitespace:
                        block_indicators = True
                if ch == '#' and preceded_by_whitespace:
                    flow_indicators = True
                    block_indicators = True

            # Check for line breaks, special, and unicode characters.
            if ch in '\n\x85\u2028\u2029':
                line_breaks = True
            if not (ch == '\n' or '\x20' <= ch <= '\x7E'):
                if (ch == '\x85' or '\xA0' <= ch <= '\uD7FF'
                        or '\uE000' <= ch <= '\uFFFD'
                        or '\U00010000' <= ch < '\U0010ffff') and ch != '\uFEFF':
                    unicode_characters = True
                    if not self.allow_unicode:
                        special_characters = True
                else:
                    special_characters = True

            # Detect important whitespace combinations.
            if ch == ' ':
                if index == 0:
                    leading_space = True
                if index == len(scalar)-1:
                    trailing_space = True
                if previous_break:
                    break_space = True
                previous_space = True
                previous_break = False
            elif ch in '\n\x85\u2028\u2029':
                if index == 0:
                    leading_break = True
                if index == len(scalar)-1:
                    trailing_break = True
                if previous_space:
                    space_break = True
                previous_space = False
                previous_break = True
            else:
                previous_space = False
                previous_break = False

            # Prepare for the next character.
            index += 1
            preceded_by_whitespace = (ch in '\0 \t\r\n\x85\u2028\u2029')
            followed_by_whitespace = (index+1 >= len(scalar) or
                    scalar[index+1] in '\0 \t\r\n\x85\u2028\u2029')

        # Let's decide what styles are allowed.
        allow_flow_plain = True
        allow_block_plain = True
        allow_single_quoted = True
        allow_double_quoted = True
        allow_block = True

        # Leading and trailing whitespaces are bad for plain scalars.
        if (leading_space or leading_break
                or trailing_space or trailing_break):
            allow_flow_plain = allow_block_plain = False

        # We do not permit trailing spaces for block scalars.
        if trailing_space:
            allow_block = False

        # Spaces at the beginning of a new line are only acceptable for block
        # scalars.
        if break_space:
            allow_flow_plain = allow_block_plain = allow_single_quoted = False

        # Spaces followed by breaks, as well as special character are only
        # allowed for double quoted scalars.
        if space_break or special_characters:
            allow_flow_plain = allow_block_plain =  \
            allow_single_quoted = allow_block = False

        # Although the plain scalar writer supports breaks, we never emit
        # multiline plain scalars.
        if line_breaks:
            allow_flow_plain = allow_block_plain = False

        # Flow indicators are forbidden for flow plain scalars.
        if flow_indicators:
            allow_flow_plain = False

        # Block indicators are forbidden for block plain scalars.
        if block_indicators:
            allow_block_plain = False

        return ScalarAnalysis(scalar=scalar,
                empty=False, multiline=line_breaks,
                allow_flow_plain=allow_flow_plain,
                allow_block_plain=allow_block_plain,
                allow_single_quoted=allow_single_quoted,
                allow_double_quoted=allow_double_quoted,
                allow_block=allow_block)

    # Writers.

    def flush_stream(self):
        if hasattr(self.stream, 'flush'):
            self.stream.flush()

    def write_stream_start(self):
        # Write BOM if needed.
        if self.encoding and self.encoding.startswith('utf-16'):
            self.stream.write('\uFEFF'.encode(self.encoding))

    def write_stream_end(self):
        self.flush_stream()

    def write_indicator(self, indicator, need_whitespace,
            whitespace=False, indention=False):
        if self.whitespace or not need_whitespace:
            data = indicator
        else:
            data = ' '+indicator
        self.whitespace = whitespace
        self.indention = self.indention and indention
        self.column += len(data)
        self.open_ended = False
        if self.encoding:
            data = data.encode(self.encoding)
        self.stream.write(data)

    def write_indent(self):
        indent = self.indent or 0
        if not self.indention or self.column > indent   \
                or (self.column == indent and not self.whitespace):
            self.write_line_break()
        if self.column < indent:
            self.whitespace = True
            data = ' '*(indent-self.column)
            self.column = indent
            if self.encoding:
                data = data.encode(self.encoding)
            self.stream.write(data)

    def write_line_break(self, data=None):
        if data is None:
            data = self.best_line_break
        self.whitespace = True
        self.indention = True
        self.line += 1
        self.column = 0
        if self.encoding:
            data = data.encode(self.encoding)
        self.stream.write(data)

    def write_version_directive(self, version_text):
        data = '%%YAML %s' % version_text
        if self.encoding:
            data = data.encode(self.encoding)
        self.stream.write(data)
        self.write_line_break()

    def write_tag_directive(self, handle_text, prefix_text):
        data = '%%TAG %s %s' % (handle_text, prefix_text)
        if self.encoding:
            data = data.encode(self.encoding)
        self.stream.write(data)
        self.write_line_break()

    # Scalar streams.

    def write_single_quoted(self, text, split=True):
        self.write_indicator('\'', True)
        spaces = False
        breaks = False
        start = end = 0
        while end <= len(text):
            ch = None
            if end < len(text):
                ch = text[end]
            if spaces:
                if ch is None or ch != ' ':
                    if start+1 == end and self.column > self.best_width and split   \
                            and start != 0 and end != len(text):
                        self.write_indent()
                    else:
                        data = text[start:end]
                        self.column += len(data)
                        if self.encoding:
                            data = data.encode(self.encoding)
                        self.stream.write(data)
                    start = end
            elif breaks:
                if ch is None or ch not in '\n\x85\u2028\u2029':
                    if text[start] == '\n':
                        self.write_line_break()
                    for br in text[start:end]:
                        if br == '\n':
                            self.write_line_break()
                        else:
                            self.write_line_break(br)
                    self.write_indent()
                    start = end
            else:
                if ch is None or ch in ' \n\x85\u2028\u2029' or ch == '\'':
                    if start < end:
                        data = text[start:end]
                        self.column += len(data)
                        if self.encoding:
                            data = data.encode(self.encoding)
                        self.stream.write(data)
                        start = end
            if ch == '\'':
                data = '\'\''
                self.column += 2
                if self.encoding:
                    data = data.encode(self.encoding)
                self.stream.write(data)
                start = end + 1
            if ch is not None:
                spaces = (ch == ' ')
                breaks = (ch in '\n\x85\u2028\u2029')
            end += 1
        self.write_indicator('\'', False)

    ESCAPE_REPLACEMENTS = {
        '\0':       '0',
        '\x07':     'a',
        '\x08':     'b',
        '\x09':     't',
        '\x0A':     'n',
        '\x0B':     'v',
        '\x0C':     'f',
        '\x0D':     'r',
        '\x1B':     'e',
        '\"':       '\"',
        '\\':       '\\',
        '\x85':     'N',
        '\xA0':     '_',
        '\u2028':   'L',
        '\u2029':   'P',
    }

    def write_double_quoted(self, text, split=True):
        self.write_indicator('"', True)
        start = end = 0
        while end <= len(text):
            ch = None
            if end < len(text):
                ch = text[end]
            if ch is None or ch in '"\\\x85\u2028\u2029\uFEFF' \
                    or not ('\x20' <= ch <= '\x7E'
                        or (self.allow_unicode
                            and ('\xA0' <= ch <= '\uD7FF'
                                or '\uE000' <= ch <= '\uFFFD'))):
                if start < end:
                    data = text[start:end]
                    self.column += len(data)
                    if self.encoding:
                        data = data.encode(self.encoding)
                    self.stream.write(data)
                    start = end
                if ch is not None:
                    if ch in self.ESCAPE_REPLACEMENTS:
                        data = '\\'+self.ESCAPE_REPLACEMENTS[ch]
                    elif ch <= '\xFF':
                        data = '\\x%02X' % ord(ch)
                    elif ch <= '\uFFFF':
                        data = '\\u%04X' % ord(ch)
                    else:
                        data = '\\U%08X' % ord(ch)
                    self.column += len(data)
                    if self.encoding:
                        data = data.encode(self.encoding)
                    self.stream.write(data)
                    start = end+1
            if 0 < end < len(text)-1 and (ch == ' ' or start >= end)    \
                    and self.column+(end-start) > self.best_width and split:
                data = text[start:end]+'\\'
                if start < end:
                    start = end
                self.column += len(data)
                if self.encoding:
                    data = data.encode(self.encoding)
                self.stream.write(data)
                self.write_indent()
                self.whitespace = False
                self.indention = False
                if text[start] == ' ':
                    data = '\\'
                    self.column += len(data)
                    if self.encoding:
                        data = data.encode(self.encoding)
                    self.stream.write(data)
            end += 1
        self.write_indicator('"', False)

    def determine_block_hints(self, text):
        hints = ''
        if text:
            if text[0] in ' \n\x85\u2028\u2029':
                hints += str(self.best_indent)
            if text[-1] not in '\n\x85\u2028\u2029':
                hints += '-'
            elif len(text) == 1 or text[-2] in '\n\x85\u2028\u2029':
                hints += '+'
        return hints

    def write_folded(self, text):
        hints = self.determine_block_hints(text)
        self.write_indicator('>'+hints, True)
        if hints[-1:] == '+':
            self.open_ended = True
        self.write_line_break()
        leading_space = True
        spaces = False
        breaks = True
        start = end = 0
        while end <= len(text):
            ch = None
            if end < len(text):
                ch = text[end]
            if breaks:
                if ch is None or ch not in '\n\x85\u2028\u2029':
                    if not leading_space and ch is not None and ch != ' '   \
                            and text[start] == '\n':
                        self.write_line_break()
                    leading_space = (ch == ' ')
                    for br in text[start:end]:
                        if br == '\n':
                            self.write_line_break()
                        else:
                            self.write_line_break(br)
                    if ch is not None:
                        self.write_indent()
                    start = end
            elif spaces:
                if ch != ' ':
                    if start+1 == end and self.column > self.best_width:
                        self.write_indent()
                    else:
                        data = text[start:end]
                        self.column += len(data)
                        if self.encoding:
                            data = data.encode(self.encoding)
                        self.stream.write(data)
                    start = end
            else:
                if ch is None or ch in ' \n\x85\u2028\u2029':
                    data = text[start:end]
                    self.column += len(data)
                    if self.encoding:
                        data = data.encode(self.encoding)
                    self.stream.write(data)
                    if ch is None:
                        self.write_line_break()
                    start = end
            if ch is not None:
                breaks = (ch in '\n\x85\u2028\u2029')
                spaces = (ch == ' ')
            end += 1

    def write_literal(self, text):
        hints = self.determine_block_hints(text)
        self.write_indicator('|'+hints, True)
        if hints[-1:] == '+':
            self.open_ended = True
        self.write_line_break()
        breaks = True
        start = end = 0
        while end <= len(text):
            ch = None
            if end < len(text):
                ch = text[end]
            if breaks:
                if ch is None or ch not in '\n\x85\u2028\u2029':
                    for br in text[start:end]:
                        if br == '\n':
                            self.write_line_break()
                        else:
                            self.write_line_break(br)
                    if ch is not None:
                        self.write_indent()
                    start = end
            else:
                if ch is None or ch in '\n\x85\u2028\u2029':
                    data = text[start:end]
                    if self.encoding:
                        data = data.encode(self.encoding)
                    self.stream.write(data)
                    if ch is None:
                        self.write_line_break()
                    start = end
            if ch is not None:
                breaks = (ch in '\n\x85\u2028\u2029')
            end += 1

    def write_plain(self, text, split=True):
        if self.root_context:
            self.open_ended = True
        if not text:
            return
        if not self.whitespace:
            data = ' '
            self.column += len(data)
            if self.encoding:
                data = data.encode(self.encoding)
            self.stream.write(data)
        self.whitespace = False
        self.indention = False
        spaces = False
        breaks = False
        start = end = 0
        while end <= len(text):
            ch = None
            if end < len(text):
                ch = text[end]
            if spaces:
                if ch != ' ':
                    if start+1 == end and self.column > self.best_width and split:
                        self.write_indent()
                        self.whitespace = False
                        self.indention = False
                    else:
                        data = text[start:end]
                        self.column += len(data)
                        if self.encoding:
                            data = data.encode(self.encoding)
                        self.stream.write(data)
                    start = end
            elif breaks:
                if ch not in '\n\x85\u2028\u2029':
                    if text[start] == '\n':
                        self.write_line_break()
                    for br in text[start:end]:
                        if br == '\n':
                            self.write_line_break()
                        else:
                            self.write_line_break(br)
                    self.write_indent()
                    self.whitespace = False
                    self.indention = False
                    start = end
            else:
                if ch is None or ch in ' \n\x85\u2028\u2029':
                    data = text[start:end]
                    self.column += len(data)
                    if self.encoding:
                        data = data.encode(self.encoding)
                    self.stream.write(data)
                    start = end
            if ch is not None:
                spaces = (ch == ' ')
                breaks = (ch in '\n\x85\u2028\u2029')
            end += 1

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\distlib\compat.py ===
# -*- coding: utf-8 -*-
#
# Copyright (C) 2013-2017 Vinay Sajip.
# Licensed to the Python Software Foundation under a contributor agreement.
# See LICENSE.txt and CONTRIBUTORS.txt.
#
from __future__ import absolute_import

import os
import re
import shutil
import sys

try:
    import ssl
except ImportError:  # pragma: no cover
    ssl = None

if sys.version_info[0] < 3:  # pragma: no cover
    from StringIO import StringIO
    string_types = basestring,
    text_type = unicode
    from types import FileType as file_type
    import __builtin__ as builtins
    import ConfigParser as configparser
    from urlparse import urlparse, urlunparse, urljoin, urlsplit, urlunsplit
    from urllib import (urlretrieve, quote as _quote, unquote, url2pathname,
                        pathname2url, ContentTooShortError, splittype)

    def quote(s):
        if isinstance(s, unicode):
            s = s.encode('utf-8')
        return _quote(s)

    import urllib2
    from urllib2 import (Request, urlopen, URLError, HTTPError,
                         HTTPBasicAuthHandler, HTTPPasswordMgr, HTTPHandler,
                         HTTPRedirectHandler, build_opener)
    if ssl:
        from urllib2 import HTTPSHandler
    import httplib
    import xmlrpclib
    import Queue as queue
    from HTMLParser import HTMLParser
    import htmlentitydefs
    raw_input = raw_input
    from itertools import ifilter as filter
    from itertools import ifilterfalse as filterfalse

    # Leaving this around for now, in case it needs resurrecting in some way
    # _userprog = None
    # def splituser(host):
    # """splituser('user[:passwd]@host[:port]') --> 'user[:passwd]', 'host[:port]'."""
    # global _userprog
    # if _userprog is None:
    # import re
    # _userprog = re.compile('^(.*)@(.*)$')

    # match = _userprog.match(host)
    # if match: return match.group(1, 2)
    # return None, host

else:  # pragma: no cover
    from io import StringIO
    string_types = str,
    text_type = str
    from io import TextIOWrapper as file_type
    import builtins
    import configparser
    from urllib.parse import (urlparse, urlunparse, urljoin, quote, unquote,
                              urlsplit, urlunsplit, splittype)
    from urllib.request import (urlopen, urlretrieve, Request, url2pathname,
                                pathname2url, HTTPBasicAuthHandler,
                                HTTPPasswordMgr, HTTPHandler,
                                HTTPRedirectHandler, build_opener)
    if ssl:
        from urllib.request import HTTPSHandler
    from urllib.error import HTTPError, URLError, ContentTooShortError
    import http.client as httplib
    import urllib.request as urllib2
    import xmlrpc.client as xmlrpclib
    import queue
    from html.parser import HTMLParser
    import html.entities as htmlentitydefs
    raw_input = input
    from itertools import filterfalse
    filter = filter

try:
    from ssl import match_hostname, CertificateError
except ImportError:  # pragma: no cover

    class CertificateError(ValueError):
        pass

    def _dnsname_match(dn, hostname, max_wildcards=1):
        """Matching according to RFC 6125, section 6.4.3

        http://tools.ietf.org/html/rfc6125#section-6.4.3
        """
        pats = []
        if not dn:
            return False

        parts = dn.split('.')
        leftmost, remainder = parts[0], parts[1:]

        wildcards = leftmost.count('*')
        if wildcards > max_wildcards:
            # Issue #17980: avoid denials of service by refusing more
            # than one wildcard per fragment.  A survey of established
            # policy among SSL implementations showed it to be a
            # reasonable choice.
            raise CertificateError(
                "too many wildcards in certificate DNS name: " + repr(dn))

        # speed up common case w/o wildcards
        if not wildcards:
            return dn.lower() == hostname.lower()

        # RFC 6125, section 6.4.3, subitem 1.
        # The client SHOULD NOT attempt to match a presented identifier in which
        # the wildcard character comprises a label other than the left-most label.
        if leftmost == '*':
            # When '*' is a fragment by itself, it matches a non-empty dotless
            # fragment.
            pats.append('[^.]+')
        elif leftmost.startswith('xn--') or hostname.startswith('xn--'):
            # RFC 6125, section 6.4.3, subitem 3.
            # The client SHOULD NOT attempt to match a presented identifier
            # where the wildcard character is embedded within an A-label or
            # U-label of an internationalized domain name.
            pats.append(re.escape(leftmost))
        else:
            # Otherwise, '*' matches any dotless string, e.g. www*
            pats.append(re.escape(leftmost).replace(r'\*', '[^.]*'))

        # add the remaining fragments, ignore any wildcards
        for frag in remainder:
            pats.append(re.escape(frag))

        pat = re.compile(r'\A' + r'\.'.join(pats) + r'\Z', re.IGNORECASE)
        return pat.match(hostname)

    def match_hostname(cert, hostname):
        """Verify that *cert* (in decoded format as returned by
        SSLSocket.getpeercert()) matches the *hostname*.  RFC 2818 and RFC 6125
        rules are followed, but IP addresses are not accepted for *hostname*.

        CertificateError is raised on failure. On success, the function
        returns nothing.
        """
        if not cert:
            raise ValueError("empty or no certificate, match_hostname needs a "
                             "SSL socket or SSL context with either "
                             "CERT_OPTIONAL or CERT_REQUIRED")
        dnsnames = []
        san = cert.get('subjectAltName', ())
        for key, value in san:
            if key == 'DNS':
                if _dnsname_match(value, hostname):
                    return
                dnsnames.append(value)
        if not dnsnames:
            # The subject is only checked when there is no dNSName entry
            # in subjectAltName
            for sub in cert.get('subject', ()):
                for key, value in sub:
                    # XXX according to RFC 2818, the most specific Common Name
                    # must be used.
                    if key == 'commonName':
                        if _dnsname_match(value, hostname):
                            return
                        dnsnames.append(value)
        if len(dnsnames) > 1:
            raise CertificateError("hostname %r "
                                   "doesn't match either of %s" %
                                   (hostname, ', '.join(map(repr, dnsnames))))
        elif len(dnsnames) == 1:
            raise CertificateError("hostname %r "
                                   "doesn't match %r" %
                                   (hostname, dnsnames[0]))
        else:
            raise CertificateError("no appropriate commonName or "
                                   "subjectAltName fields were found")


try:
    from types import SimpleNamespace as Container
except ImportError:  # pragma: no cover

    class Container(object):
        """
        A generic container for when multiple values need to be returned
        """

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)


try:
    from shutil import which
except ImportError:  # pragma: no cover
    # Implementation from Python 3.3
    def which(cmd, mode=os.F_OK | os.X_OK, path=None):
        """Given a command, mode, and a PATH string, return the path which
        conforms to the given mode on the PATH, or None if there is no such
        file.

        `mode` defaults to os.F_OK | os.X_OK. `path` defaults to the result
        of os.environ.get("PATH"), or can be overridden with a custom search
        path.

        """

        # Check that a given file can be accessed with the correct mode.
        # Additionally check that `file` is not a directory, as on Windows
        # directories pass the os.access check.
        def _access_check(fn, mode):
            return (os.path.exists(fn) and os.access(fn, mode) and not os.path.isdir(fn))

        # If we're given a path with a directory part, look it up directly rather
        # than referring to PATH directories. This includes checking relative to the
        # current directory, e.g. ./script
        if os.path.dirname(cmd):
            if _access_check(cmd, mode):
                return cmd
            return None

        if path is None:
            path = os.environ.get("PATH", os.defpath)
        if not path:
            return None
        path = path.split(os.pathsep)

        if sys.platform == "win32":
            # The current directory takes precedence on Windows.
            if os.curdir not in path:
                path.insert(0, os.curdir)

            # PATHEXT is necessary to check on Windows.
            pathext = os.environ.get("PATHEXT", "").split(os.pathsep)
            # See if the given file matches any of the expected path extensions.
            # This will allow us to short circuit when given "python.exe".
            # If it does match, only test that one, otherwise we have to try
            # others.
            if any(cmd.lower().endswith(ext.lower()) for ext in pathext):
                files = [cmd]
            else:
                files = [cmd + ext for ext in pathext]
        else:
            # On other platforms you don't have things like PATHEXT to tell you
            # what file suffixes are executable, so just pass on cmd as-is.
            files = [cmd]

        seen = set()
        for dir in path:
            normdir = os.path.normcase(dir)
            if normdir not in seen:
                seen.add(normdir)
                for thefile in files:
                    name = os.path.join(dir, thefile)
                    if _access_check(name, mode):
                        return name
        return None


# ZipFile is a context manager in 2.7, but not in 2.6

from zipfile import ZipFile as BaseZipFile

if hasattr(BaseZipFile, '__enter__'):  # pragma: no cover
    ZipFile = BaseZipFile
else:  # pragma: no cover
    from zipfile import ZipExtFile as BaseZipExtFile

    class ZipExtFile(BaseZipExtFile):

        def __init__(self, base):
            self.__dict__.update(base.__dict__)

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            self.close()
            # return None, so if an exception occurred, it will propagate

    class ZipFile(BaseZipFile):

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            self.close()
            # return None, so if an exception occurred, it will propagate

        def open(self, *args, **kwargs):
            base = BaseZipFile.open(self, *args, **kwargs)
            return ZipExtFile(base)


try:
    from platform import python_implementation
except ImportError:  # pragma: no cover

    def python_implementation():
        """Return a string identifying the Python implementation."""
        if 'PyPy' in sys.version:
            return 'PyPy'
        if os.name == 'java':
            return 'Jython'
        if sys.version.startswith('IronPython'):
            return 'IronPython'
        return 'CPython'


import sysconfig

try:
    callable = callable
except NameError:  # pragma: no cover
    from collections.abc import Callable

    def callable(obj):
        return isinstance(obj, Callable)


try:
    fsencode = os.fsencode
    fsdecode = os.fsdecode
except AttributeError:  # pragma: no cover
    # Issue #99: on some systems (e.g. containerised),
    # sys.getfilesystemencoding() returns None, and we need a real value,
    # so fall back to utf-8. From the CPython 2.7 docs relating to Unix and
    # sys.getfilesystemencoding(): the return value is "the user’s preference
    # according to the result of nl_langinfo(CODESET), or None if the
    # nl_langinfo(CODESET) failed."
    _fsencoding = sys.getfilesystemencoding() or 'utf-8'
    if _fsencoding == 'mbcs':
        _fserrors = 'strict'
    else:
        _fserrors = 'surrogateescape'

    def fsencode(filename):
        if isinstance(filename, bytes):
            return filename
        elif isinstance(filename, text_type):
            return filename.encode(_fsencoding, _fserrors)
        else:
            raise TypeError("expect bytes or str, not %s" %
                            type(filename).__name__)

    def fsdecode(filename):
        if isinstance(filename, text_type):
            return filename
        elif isinstance(filename, bytes):
            return filename.decode(_fsencoding, _fserrors)
        else:
            raise TypeError("expect bytes or str, not %s" %
                            type(filename).__name__)


try:
    from tokenize import detect_encoding
except ImportError:  # pragma: no cover
    from codecs import BOM_UTF8, lookup

    cookie_re = re.compile(r"coding[:=]\s*([-\w.]+)")

    def _get_normal_name(orig_enc):
        """Imitates get_normal_name in tokenizer.c."""
        # Only care about the first 12 characters.
        enc = orig_enc[:12].lower().replace("_", "-")
        if enc == "utf-8" or enc.startswith("utf-8-"):
            return "utf-8"
        if enc in ("latin-1", "iso-8859-1", "iso-latin-1") or \
           enc.startswith(("latin-1-", "iso-8859-1-", "iso-latin-1-")):
            return "iso-8859-1"
        return orig_enc

    def detect_encoding(readline):
        """
        The detect_encoding() function is used to detect the encoding that should
        be used to decode a Python source file.  It requires one argument, readline,
        in the same way as the tokenize() generator.

        It will call readline a maximum of twice, and return the encoding used
        (as a string) and a list of any lines (left as bytes) it has read in.

        It detects the encoding from the presence of a utf-8 bom or an encoding
        cookie as specified in pep-0263.  If both a bom and a cookie are present,
        but disagree, a SyntaxError will be raised.  If the encoding cookie is an
        invalid charset, raise a SyntaxError.  Note that if a utf-8 bom is found,
        'utf-8-sig' is returned.

        If no encoding is specified, then the default of 'utf-8' will be returned.
        """
        try:
            filename = readline.__self__.name
        except AttributeError:
            filename = None
        bom_found = False
        encoding = None
        default = 'utf-8'

        def read_or_stop():
            try:
                return readline()
            except StopIteration:
                return b''

        def find_cookie(line):
            try:
                # Decode as UTF-8. Either the line is an encoding declaration,
                # in which case it should be pure ASCII, or it must be UTF-8
                # per default encoding.
                line_string = line.decode('utf-8')
            except UnicodeDecodeError:
                msg = "invalid or missing encoding declaration"
                if filename is not None:
                    msg = '{} for {!r}'.format(msg, filename)
                raise SyntaxError(msg)

            matches = cookie_re.findall(line_string)
            if not matches:
                return None
            encoding = _get_normal_name(matches[0])
            try:
                codec = lookup(encoding)
            except LookupError:
                # This behaviour mimics the Python interpreter
                if filename is None:
                    msg = "unknown encoding: " + encoding
                else:
                    msg = "unknown encoding for {!r}: {}".format(
                        filename, encoding)
                raise SyntaxError(msg)

            if bom_found:
                if codec.name != 'utf-8':
                    # This behaviour mimics the Python interpreter
                    if filename is None:
                        msg = 'encoding problem: utf-8'
                    else:
                        msg = 'encoding problem for {!r}: utf-8'.format(
                            filename)
                    raise SyntaxError(msg)
                encoding += '-sig'
            return encoding

        first = read_or_stop()
        if first.startswith(BOM_UTF8):
            bom_found = True
            first = first[3:]
            default = 'utf-8-sig'
        if not first:
            return default, []

        encoding = find_cookie(first)
        if encoding:
            return encoding, [first]

        second = read_or_stop()
        if not second:
            return default, [first]

        encoding = find_cookie(second)
        if encoding:
            return encoding, [first, second]

        return default, [first, second]


# For converting & <-> &amp; etc.
try:
    from html import escape
except ImportError:
    from cgi import escape
if sys.version_info[:2] < (3, 4):
    unescape = HTMLParser().unescape
else:
    from html import unescape

try:
    from collections import ChainMap
except ImportError:  # pragma: no cover
    from collections import MutableMapping

    try:
        from reprlib import recursive_repr as _recursive_repr
    except ImportError:

        def _recursive_repr(fillvalue='...'):
            '''
            Decorator to make a repr function return fillvalue for a recursive
            call
            '''

            def decorating_function(user_function):
                repr_running = set()

                def wrapper(self):
                    key = id(self), get_ident()
                    if key in repr_running:
                        return fillvalue
                    repr_running.add(key)
                    try:
                        result = user_function(self)
                    finally:
                        repr_running.discard(key)
                    return result

                # Can't use functools.wraps() here because of bootstrap issues
                wrapper.__module__ = getattr(user_function, '__module__')
                wrapper.__doc__ = getattr(user_function, '__doc__')
                wrapper.__name__ = getattr(user_function, '__name__')
                wrapper.__annotations__ = getattr(user_function,
                                                  '__annotations__', {})
                return wrapper

            return decorating_function

    class ChainMap(MutableMapping):
        '''
        A ChainMap groups multiple dicts (or other mappings) together
        to create a single, updateable view.

        The underlying mappings are stored in a list.  That list is public and can
        accessed or updated using the *maps* attribute.  There is no other state.

        Lookups search the underlying mappings successively until a key is found.
        In contrast, writes, updates, and deletions only operate on the first
        mapping.
        '''

        def __init__(self, *maps):
            '''Initialize a ChainMap by setting *maps* to the given mappings.
            If no mappings are provided, a single empty dictionary is used.

            '''
            self.maps = list(maps) or [{}]  # always at least one map

        def __missing__(self, key):
            raise KeyError(key)

        def __getitem__(self, key):
            for mapping in self.maps:
                try:
                    return mapping[
                        key]  # can't use 'key in mapping' with defaultdict
                except KeyError:
                    pass
            return self.__missing__(
                key)  # support subclasses that define __missing__

        def get(self, key, default=None):
            return self[key] if key in self else default

        def __len__(self):
            return len(set().union(
                *self.maps))  # reuses stored hash values if possible

        def __iter__(self):
            return iter(set().union(*self.maps))

        def __contains__(self, key):
            return any(key in m for m in self.maps)

        def __bool__(self):
            return any(self.maps)

        @_recursive_repr()
        def __repr__(self):
            return '{0.__class__.__name__}({1})'.format(
                self, ', '.join(map(repr, self.maps)))

        @classmethod
        def fromkeys(cls, iterable, *args):
            'Create a ChainMap with a single dict created from the iterable.'
            return cls(dict.fromkeys(iterable, *args))

        def copy(self):
            'New ChainMap or subclass with a new copy of maps[0] and refs to maps[1:]'
            return self.__class__(self.maps[0].copy(), *self.maps[1:])

        __copy__ = copy

        def new_child(self):  # like Django's Context.push()
            'New ChainMap with a new dict followed by all previous maps.'
            return self.__class__({}, *self.maps)

        @property
        def parents(self):  # like Django's Context.pop()
            'New ChainMap from maps[1:].'
            return self.__class__(*self.maps[1:])

        def __setitem__(self, key, value):
            self.maps[0][key] = value

        def __delitem__(self, key):
            try:
                del self.maps[0][key]
            except KeyError:
                raise KeyError(
                    'Key not found in the first mapping: {!r}'.format(key))

        def popitem(self):
            'Remove and return an item pair from maps[0]. Raise KeyError is maps[0] is empty.'
            try:
                return self.maps[0].popitem()
            except KeyError:
                raise KeyError('No keys found in the first mapping.')

        def pop(self, key, *args):
            'Remove *key* from maps[0] and return its value. Raise KeyError if *key* not in maps[0].'
            try:
                return self.maps[0].pop(key, *args)
            except KeyError:
                raise KeyError(
                    'Key not found in the first mapping: {!r}'.format(key))

        def clear(self):
            'Clear maps[0], leaving maps[1:] intact.'
            self.maps[0].clear()


try:
    from importlib.util import cache_from_source  # Python >= 3.4
except ImportError:  # pragma: no cover

    def cache_from_source(path, debug_override=None):
        assert path.endswith('.py')
        if debug_override is None:
            debug_override = __debug__
        if debug_override:
            suffix = 'c'
        else:
            suffix = 'o'
        return path + suffix


try:
    from collections import OrderedDict
except ImportError:  # pragma: no cover
    # {{{ http://code.activestate.com/recipes/576693/ (r9)
    # Backport of OrderedDict() class that runs on Python 2.4, 2.5, 2.6, 2.7 and pypy.
    # Passes Python2.7's test suite and incorporates all the latest updates.
    try:
        from thread import get_ident as _get_ident
    except ImportError:
        from dummy_thread import get_ident as _get_ident

    try:
        from _abcoll import KeysView, ValuesView, ItemsView
    except ImportError:
        pass

    class OrderedDict(dict):
        'Dictionary that remembers insertion order'

        # An inherited dict maps keys to values.
        # The inherited dict provides __getitem__, __len__, __contains__, and get.
        # The remaining methods are order-aware.
        # Big-O running times for all methods are the same as for regular dictionaries.

        # The internal self.__map dictionary maps keys to links in a doubly linked list.
        # The circular doubly linked list starts and ends with a sentinel element.
        # The sentinel element never gets deleted (this simplifies the algorithm).
        # Each link is stored as a list of length three:  [PREV, NEXT, KEY].

        def __init__(self, *args, **kwds):
            '''Initialize an ordered dictionary.  Signature is the same as for
            regular dictionaries, but keyword arguments are not recommended
            because their insertion order is arbitrary.

            '''
            if len(args) > 1:
                raise TypeError('expected at most 1 arguments, got %d' %
                                len(args))
            try:
                self.__root
            except AttributeError:
                self.__root = root = []  # sentinel node
                root[:] = [root, root, None]
                self.__map = {}
            self.__update(*args, **kwds)

        def __setitem__(self, key, value, dict_setitem=dict.__setitem__):
            'od.__setitem__(i, y) <==> od[i]=y'
            # Setting a new item creates a new link which goes at the end of the linked
            # list, and the inherited dictionary is updated with the new key/value pair.
            if key not in self:
                root = self.__root
                last = root[0]
                last[1] = root[0] = self.__map[key] = [last, root, key]
            dict_setitem(self, key, value)

        def __delitem__(self, key, dict_delitem=dict.__delitem__):
            'od.__delitem__(y) <==> del od[y]'
            # Deleting an existing item uses self.__map to find the link which is
            # then removed by updating the links in the predecessor and successor nodes.
            dict_delitem(self, key)
            link_prev, link_next, key = self.__map.pop(key)
            link_prev[1] = link_next
            link_next[0] = link_prev

        def __iter__(self):
            'od.__iter__() <==> iter(od)'
            root = self.__root
            curr = root[1]
            while curr is not root:
                yield curr[2]
                curr = curr[1]

        def __reversed__(self):
            'od.__reversed__() <==> reversed(od)'
            root = self.__root
            curr = root[0]
            while curr is not root:
                yield curr[2]
                curr = curr[0]

        def clear(self):
            'od.clear() -> None.  Remove all items from od.'
            try:
                for node in self.__map.itervalues():
                    del node[:]
                root = self.__root
                root[:] = [root, root, None]
                self.__map.clear()
            except AttributeError:
                pass
            dict.clear(self)

        def popitem(self, last=True):
            '''od.popitem() -> (k, v), return and remove a (key, value) pair.
            Pairs are returned in LIFO order if last is true or FIFO order if false.

            '''
            if not self:
                raise KeyError('dictionary is empty')
            root = self.__root
            if last:
                link = root[0]
                link_prev = link[0]
                link_prev[1] = root
                root[0] = link_prev
            else:
                link = root[1]
                link_next = link[1]
                root[1] = link_next
                link_next[0] = root
            key = link[2]
            del self.__map[key]
            value = dict.pop(self, key)
            return key, value

        # -- the following methods do not depend on the internal structure --

        def keys(self):
            'od.keys() -> list of keys in od'
            return list(self)

        def values(self):
            'od.values() -> list of values in od'
            return [self[key] for key in self]

        def items(self):
            'od.items() -> list of (key, value) pairs in od'
            return [(key, self[key]) for key in self]

        def iterkeys(self):
            'od.iterkeys() -> an iterator over the keys in od'
            return iter(self)

        def itervalues(self):
            'od.itervalues -> an iterator over the values in od'
            for k in self:
                yield self[k]

        def iteritems(self):
            'od.iteritems -> an iterator over the (key, value) items in od'
            for k in self:
                yield (k, self[k])

        def update(*args, **kwds):
            '''od.update(E, **F) -> None.  Update od from dict/iterable E and F.

            If E is a dict instance, does:           for k in E: od[k] = E[k]
            If E has a .keys() method, does:         for k in E.keys(): od[k] = E[k]
            Or if E is an iterable of items, does:   for k, v in E: od[k] = v
            In either case, this is followed by:     for k, v in F.items(): od[k] = v

            '''
            if len(args) > 2:
                raise TypeError('update() takes at most 2 positional '
                                'arguments (%d given)' % (len(args), ))
            elif not args:
                raise TypeError('update() takes at least 1 argument (0 given)')
            self = args[0]
            # Make progressively weaker assumptions about "other"
            other = ()
            if len(args) == 2:
                other = args[1]
            if isinstance(other, dict):
                for key in other:
                    self[key] = other[key]
            elif hasattr(other, 'keys'):
                for key in other.keys():
                    self[key] = other[key]
            else:
                for key, value in other:
                    self[key] = value
            for key, value in kwds.items():
                self[key] = value

        __update = update  # let subclasses override update without breaking __init__

        __marker = object()

        def pop(self, key, default=__marker):
            '''od.pop(k[,d]) -> v, remove specified key and return the corresponding value.
            If key is not found, d is returned if given, otherwise KeyError is raised.

            '''
            if key in self:
                result = self[key]
                del self[key]
                return result
            if default is self.__marker:
                raise KeyError(key)
            return default

        def setdefault(self, key, default=None):
            'od.setdefault(k[,d]) -> od.get(k,d), also set od[k]=d if k not in od'
            if key in self:
                return self[key]
            self[key] = default
            return default

        def __repr__(self, _repr_running=None):
            'od.__repr__() <==> repr(od)'
            if not _repr_running:
                _repr_running = {}
            call_key = id(self), _get_ident()
            if call_key in _repr_running:
                return '...'
            _repr_running[call_key] = 1
            try:
                if not self:
                    return '%s()' % (self.__class__.__name__, )
                return '%s(%r)' % (self.__class__.__name__, self.items())
            finally:
                del _repr_running[call_key]

        def __reduce__(self):
            'Return state information for pickling'
            items = [[k, self[k]] for k in self]
            inst_dict = vars(self).copy()
            for k in vars(OrderedDict()):
                inst_dict.pop(k, None)
            if inst_dict:
                return (self.__class__, (items, ), inst_dict)
            return self.__class__, (items, )

        def copy(self):
            'od.copy() -> a shallow copy of od'
            return self.__class__(self)

        @classmethod
        def fromkeys(cls, iterable, value=None):
            '''OD.fromkeys(S[, v]) -> New ordered dictionary with keys from S
            and values equal to v (which defaults to None).

            '''
            d = cls()
            for key in iterable:
                d[key] = value
            return d

        def __eq__(self, other):
            '''od.__eq__(y) <==> od==y.  Comparison to another OD is order-sensitive
            while comparison to a regular mapping is order-insensitive.

            '''
            if isinstance(other, OrderedDict):
                return len(self) == len(
                    other) and self.items() == other.items()
            return dict.__eq__(self, other)

        def __ne__(self, other):
            return not self == other

        # -- the following methods are only used in Python 2.7 --

        def viewkeys(self):
            "od.viewkeys() -> a set-like object providing a view on od's keys"
            return KeysView(self)

        def viewvalues(self):
            "od.viewvalues() -> an object providing a view on od's values"
            return ValuesView(self)

        def viewitems(self):
            "od.viewitems() -> a set-like object providing a view on od's items"
            return ItemsView(self)


try:
    from logging.config import BaseConfigurator, valid_ident
except ImportError:  # pragma: no cover
    IDENTIFIER = re.compile('^[a-z_][a-z0-9_]*$', re.I)

    def valid_ident(s):
        m = IDENTIFIER.match(s)
        if not m:
            raise ValueError('Not a valid Python identifier: %r' % s)
        return True

    # The ConvertingXXX classes are wrappers around standard Python containers,
    # and they serve to convert any suitable values in the container. The
    # conversion converts base dicts, lists and tuples to their wrapped
    # equivalents, whereas strings which match a conversion format are converted
    # appropriately.
    #
    # Each wrapper should have a configurator attribute holding the actual
    # configurator to use for conversion.

    class ConvertingDict(dict):
        """A converting dictionary wrapper."""

        def __getitem__(self, key):
            value = dict.__getitem__(self, key)
            result = self.configurator.convert(value)
            # If the converted value is different, save for next time
            if value is not result:
                self[key] = result
                if type(result) in (ConvertingDict, ConvertingList,
                                    ConvertingTuple):
                    result.parent = self
                    result.key = key
            return result

        def get(self, key, default=None):
            value = dict.get(self, key, default)
            result = self.configurator.convert(value)
            # If the converted value is different, save for next time
            if value is not result:
                self[key] = result
                if type(result) in (ConvertingDict, ConvertingList,
                                    ConvertingTuple):
                    result.parent = self
                    result.key = key
            return result

    def pop(self, key, default=None):
        value = dict.pop(self, key, default)
        result = self.configurator.convert(value)
        if value is not result:
            if type(result) in (ConvertingDict, ConvertingList,
                                ConvertingTuple):
                result.parent = self
                result.key = key
        return result

    class ConvertingList(list):
        """A converting list wrapper."""

        def __getitem__(self, key):
            value = list.__getitem__(self, key)
            result = self.configurator.convert(value)
            # If the converted value is different, save for next time
            if value is not result:
                self[key] = result
                if type(result) in (ConvertingDict, ConvertingList,
                                    ConvertingTuple):
                    result.parent = self
                    result.key = key
            return result

        def pop(self, idx=-1):
            value = list.pop(self, idx)
            result = self.configurator.convert(value)
            if value is not result:
                if type(result) in (ConvertingDict, ConvertingList,
                                    ConvertingTuple):
                    result.parent = self
            return result

    class ConvertingTuple(tuple):
        """A converting tuple wrapper."""

        def __getitem__(self, key):
            value = tuple.__getitem__(self, key)
            result = self.configurator.convert(value)
            if value is not result:
                if type(result) in (ConvertingDict, ConvertingList,
                                    ConvertingTuple):
                    result.parent = self
                    result.key = key
            return result

    class BaseConfigurator(object):
        """
        The configurator base class which defines some useful defaults.
        """

        CONVERT_PATTERN = re.compile(r'^(?P<prefix>[a-z]+)://(?P<suffix>.*)$')

        WORD_PATTERN = re.compile(r'^\s*(\w+)\s*')
        DOT_PATTERN = re.compile(r'^\.\s*(\w+)\s*')
        INDEX_PATTERN = re.compile(r'^\[\s*(\w+)\s*\]\s*')
        DIGIT_PATTERN = re.compile(r'^\d+$')

        value_converters = {
            'ext': 'ext_convert',
            'cfg': 'cfg_convert',
        }

        # We might want to use a different one, e.g. importlib
        importer = staticmethod(__import__)

        def __init__(self, config):
            self.config = ConvertingDict(config)
            self.config.configurator = self

        def resolve(self, s):
            """
            Resolve strings to objects using standard import and attribute
            syntax.
            """
            name = s.split('.')
            used = name.pop(0)
            try:
                found = self.importer(used)
                for frag in name:
                    used += '.' + frag
                    try:
                        found = getattr(found, frag)
                    except AttributeError:
                        self.importer(used)
                        found = getattr(found, frag)
                return found
            except ImportError:
                e, tb = sys.exc_info()[1:]
                v = ValueError('Cannot resolve %r: %s' % (s, e))
                v.__cause__, v.__traceback__ = e, tb
                raise v

        def ext_convert(self, value):
            """Default converter for the ext:// protocol."""
            return self.resolve(value)

        def cfg_convert(self, value):
            """Default converter for the cfg:// protocol."""
            rest = value
            m = self.WORD_PATTERN.match(rest)
            if m is None:
                raise ValueError("Unable to convert %r" % value)
            else:
                rest = rest[m.end():]
                d = self.config[m.groups()[0]]
                while rest:
                    m = self.DOT_PATTERN.match(rest)
                    if m:
                        d = d[m.groups()[0]]
                    else:
                        m = self.INDEX_PATTERN.match(rest)
                        if m:
                            idx = m.groups()[0]
                            if not self.DIGIT_PATTERN.match(idx):
                                d = d[idx]
                            else:
                                try:
                                    n = int(
                                        idx
                                    )  # try as number first (most likely)
                                    d = d[n]
                                except TypeError:
                                    d = d[idx]
                    if m:
                        rest = rest[m.end():]
                    else:
                        raise ValueError('Unable to convert '
                                         '%r at %r' % (value, rest))
            # rest should be empty
            return d

        def convert(self, value):
            """
            Convert values to an appropriate type. dicts, lists and tuples are
            replaced by their converting alternatives. Strings are checked to
            see if they have a conversion format and are converted if they do.
            """
            if not isinstance(value, ConvertingDict) and isinstance(
                    value, dict):
                value = ConvertingDict(value)
                value.configurator = self
            elif not isinstance(value, ConvertingList) and isinstance(
                    value, list):
                value = ConvertingList(value)
                value.configurator = self
            elif not isinstance(value, ConvertingTuple) and isinstance(value, tuple):
                value = ConvertingTuple(value)
                value.configurator = self
            elif isinstance(value, string_types):
                m = self.CONVERT_PATTERN.match(value)
                if m:
                    d = m.groupdict()
                    prefix = d['prefix']
                    converter = self.value_converters.get(prefix, None)
                    if converter:
                        suffix = d['suffix']
                        converter = getattr(self, converter)
                        value = converter(suffix)
            return value

        def configure_custom(self, config):
            """Configure an object with a user-supplied factory."""
            c = config.pop('()')
            if not callable(c):
                c = self.resolve(c)
            props = config.pop('.', None)
            # Check for valid identifiers
            kwargs = dict([(k, config[k]) for k in config if valid_ident(k)])
            result = c(**kwargs)
            if props:
                for name, value in props.items():
                    setattr(result, name, value)
            return result

        def as_tuple(self, value):
            """Utility function which converts lists to tuples."""
            if isinstance(value, list):
                value = tuple(value)
            return value