"""Données initiales (idempotentes) — v2.0 « Plafond ouvert ».

GRAPHE DE COMPÉTENCES : 103 nœuds répartis en 14 domaines, trilingues
(français / English / español), reliés par des prérequis (skill_edges).
v2.3 : nouveau domaine « 🚀 Créer & Inventer » — boucle du
petit inventeur : imaginer → concevoir → construire → tester → expliquer.
v2.4 : 7 plans « Fabrique & Assemble » (résultat garanti), fiches de
fabrication illustrées, et le domaine 🇨🇩 LINGALA (langue bantoue).
v2.5 : conversations ANIMÉES (guides gestuels 🦜🐬), 🇵🇹 PORTUGAIS, 6
COLORIAGES de précision (doigt/stylet), activités aux « moyens de bord ».

PHILOSOPHIE (demande explicite des parents) :
- L'ÂGE ne fixe QUE les règles de protection (temps d'écran, accompagnement).
  Il ne plafonne JAMAIS le contenu : une compétence se débloque dès que ses
  prérequis sont maîtrisés. Une enfant de 3 ans qui va vite est nourrie vite.
- L'évaluation de départ (dashboard parent) permet de déclarer ce que Jade
  sait DÉJÀ (compter jusqu'à 22, alphabet…) → le départ se cale sur elle.
- Les profils d'attention / de langage adaptent la durée et la voix,
  sans jamais toucher aux protections (règle absolue, non négociable).

⚠ Les questions d'identification par défaut restent des PLACEHOLDERS :
les parents les remplacent depuis le Dashboard (jamais stockées en clair).
"""
from __future__ import annotations

import sqlite3

from .audit import audit
from .db import dumps, iso, q_one
from .security import hash_answer

CHILD_ID = "jade"
CHILD_DOB = "2022-09-03"

L = lambda fr, en, es: {"fr": fr, "en": en, "es": es}  # noqa: E731


# ------------------------------------------------------------------ helpers jeux

def _item(i: str, emoji: str, fr: str, en: str, es: str) -> dict:
    return {"id": i, "emoji": emoji, "labels": {"fr": fr, "en": en, "es": es}}


def _tap(items: list[dict], rounds: int = 3, instruction: dict | None = None) -> dict:
    return {
        "type": "tap",
        "instruction_tpl": instruction or L("Touche : {label} {emoji}", "Touch: {label} {emoji}", "Toca: {label} {emoji}"),
        "items": items,
        "rounds": rounds,
    }


COLORS_1 = [
    _item("red", "🔴", "rouge", "red", "rojo"), _item("blue", "🔵", "bleu", "blue", "azul"),
    _item("green", "🟢", "vert", "green", "verde"), _item("yellow", "🟡", "jaune", "yellow", "amarillo"),
]
COLORS_2 = [
    _item("orange", "🟠", "orange", "orange", "naranja"), _item("purple", "🟣", "violet", "purple", "morado"),
    _item("pink", "🌸", "rose", "pink", "rosa"), _item("brown", "🟤", "marron", "brown", "marrón"),
]
ANIMALS_1 = [
    _item("cat", "🐱", "chat", "cat", "gato"), _item("dog", "🐶", "chien", "dog", "perro"),
    _item("rabbit", "🐰", "lapin", "rabbit", "conejo"), _item("duck", "🦆", "canard", "duck", "pato"),
]
ANIMALS_2 = [
    _item("lion", "🦁", "lion", "lion", "león"), _item("monkey", "🐵", "singe", "monkey", "mono"),
    _item("fish", "🐟", "poisson", "fish", "pez"), _item("bird", "🐦", "oiseau", "bird", "pájaro"),
]
ANIMALS_3 = [
    _item("dolphin", "🐬", "dauphin", "dolphin", "delfín"), _item("whale", "🐋", "baleine", "whale", "ballena"),
    _item("octopus", "🐙", "pieuvre", "octopus", "pulpo"), _item("turtle", "🐢", "tortue", "turtle", "tortuga"),
]
SHAPES_1 = [
    _item("circle", "⭕", "cercle", "circle", "círculo"), _item("square", "🟦", "carré", "square", "cuadrado"),
    _item("triangle", "🔺", "triangle", "triangle", "triángulo"), _item("star", "⭐", "étoile", "star", "estrella"),
]
SHAPES_2 = [
    _item("diamond", "🔶", "losange", "diamond", "rombo"), _item("heart", "❤️", "cœur", "heart", "corazón"),
    _item("moon", "🌙", "lune", "moon", "luna"), _item("drop", "💧", "goutte", "drop", "gota"),
]


def _skill(ord_i: int, sid: str, domain: str, level: int, emoji: str, name: dict, game: dict) -> dict:
    return {"id": sid, "ord_i": ord_i, "domain": domain, "level": level,
            "emoji": emoji, "name": name, "game": game}


def _build(emoji: str, label: dict, parts: list[dict], intro: dict, cheer: dict) -> dict:
    """Jeu « Fabrique & Assemble » (v2.4) : plan de pièces numérotées que
    l'enfant joint une à une à l'écran. AUCUN échec possible : la mauvaise
    pièce gigote, la bonne s'emboîte — le RÉSULTAT est garanti (création animée)."""
    return {"type": "build", "parts": parts,
            "result": {"emoji": emoji, "label": label},
            "intro": intro, "cheer": cheer, "rounds": 1}




# --------- images de COLORIAGE (v2.5) : grandes formes à contours épais,
# dessinées pour être coloriées au doigt ou au stylet — le trait reste net
def _art(inner: str) -> str:
    return ('<svg viewBox="0 0 400 300" xmlns="http://www.w3.org/2000/svg"><g fill="none" '
            'stroke="#1f2937" stroke-width="7" stroke-linecap="round" stroke-linejoin="round">'
            + inner + "</g></svg>")


ART_MAISON = _art('<circle cx="332" cy="52" r="26"/><path d="M332 14v12M332 78v12M292 52h12M362 52h12"/>'
                  '<path d="M70 145 L200 45 L330 145"/><rect x="92" y="145" width="216" height="120"/>'
                  '<rect x="180" y="202" width="44" height="63"/><rect x="112" y="170" width="46" height="42"/>'
                  '<rect x="246" y="170" width="46" height="42"/>')
ART_VOITURE = _art('<path d="M52 205 L52 165 Q52 145 75 145 L112 145 L145 100 Q151 90 164 90 L252 90 '
                   'Q265 90 272 101 L297 145 L338 145 Q358 145 358 166 L358 205 Z"/>'
                   '<circle cx="112" cy="210" r="26"/><circle cx="296" cy="210" r="26"/>'
                   '<circle cx="112" cy="210" r="9"/><circle cx="296" cy="210" r="9"/>'
                   '<path d="M158 103 L253 103 L272 142 L138 142 Z"/><path d="M204 93 L204 141"/>')
ART_FLEUR = _art('<circle cx="200" cy="118" r="30"/><ellipse cx="200" cy="58" rx="22" ry="30"/>'
                 '<ellipse cx="252" cy="98" rx="22" ry="30" transform="rotate(72 252 98)"/>'
                 '<ellipse cx="232" cy="166" rx="22" ry="30" transform="rotate(144 232 166)"/>'
                 '<ellipse cx="168" cy="166" rx="22" ry="30" transform="rotate(216 168 166)"/>'
                 '<ellipse cx="148" cy="98" rx="22" ry="30" transform="rotate(288 148 98)"/>'
                 '<path d="M200 148 L200 262"/><path d="M200 226 Q160 206 138 232 Q168 252 200 236"/>')
ART_POISSON = _art('<ellipse cx="185" cy="150" rx="105" ry="68"/><path d="M288 150 L352 108 L352 192 Z"/>'
                   '<circle cx="132" cy="134" r="9"/><path d="M70 150 Q100 168 130 150"/>'
                   '<path d="M196 96 Q216 62 244 86"/><path d="M300 60 q8 -14 16 0 q8 14 16 0"/>')
ART_PAPILLON = _art('<ellipse cx="200" cy="150" rx="10" ry="58"/><circle cx="200" cy="82" r="9"/>'
                    '<path d="M196 92 Q182 66 168 58"/><path d="M204 92 Q218 66 232 58"/>'
                    '<ellipse cx="136" cy="104" rx="48" ry="58" transform="rotate(-16 136 104)"/>'
                    '<ellipse cx="264" cy="104" rx="48" ry="58" transform="rotate(16 264 104)"/>'
                    '<ellipse cx="150" cy="202" rx="38" ry="44" transform="rotate(14 150 202)"/>'
                    '<ellipse cx="250" cy="202" rx="38" ry="44" transform="rotate(-14 250 202)"/>')
ART_FUSEE = _art('<path d="M200 34 Q262 92 262 178 L262 226 L138 226 L138 178 Q138 92 200 34 Z"/>'
                 '<circle cx="200" cy="132" r="24"/><circle cx="200" cy="132" r="9"/>'
                 '<path d="M138 196 L96 252 L138 240"/><path d="M262 196 L304 252 L262 240"/>'
                 '<path d="M184 232 Q200 292 216 232"/>'
                 '<path d="M70 60 l6 14 l14 6 l-14 6 l-6 14 l-6 -14 l-14 -6 l14 -6 Z"/>'
                 '<path d="M320 70 l5 12 l12 5 l-12 5 l-5 12 l-5 -12 l-12 -5 l12 -5 Z"/>')


# ------------------------------------------------------------------ les 62 compétences
SKILLS: list[dict] = [
    # ============ 🔢 MATHÉMATIQUES (14) ============
    _skill(1, "num-1", "maths", 1, "🍎", L("Compter jusqu'à 3", "Count up to 3", "Contar hasta 3"),
           {"type": "count", "object_emoji": "🍎", "min": 1, "max": 3, "rounds": 3}),
    _skill(2, "num-2", "maths", 2, "🖐", L("Compter jusqu'à 5", "Count up to 5", "Contar hasta 5"),
           {"type": "count", "object_emoji": "🍓", "min": 2, "max": 5, "rounds": 3}),
    _skill(3, "num-3", "maths", 3, "🔟", L("Compter jusqu'à 10", "Count up to 10", "Contar hasta 10"),
           {"type": "count", "object_emoji": "🦆", "min": 3, "max": 10, "rounds": 3}),
    _skill(4, "num-4", "maths", 4, "🎯", L("Compter jusqu'à 20", "Count up to 20", "Contar hasta 20"),
           {"type": "voice", "kind": "count_to", "to": 20, "rounds": 1}),
    _skill(5, "num-5", "maths", 5, "🚀", L("Les nombres jusqu'à 50", "Numbers up to 50", "Los números hasta 50"),
           {"type": "math", "kind": "after", "min": 10, "max": 49, "rounds": 4}),
    _skill(6, "num-6", "maths", 6, "💯", L("Les nombres jusqu'à 100", "Numbers up to 100", "Los números hasta 100"),
           {"type": "math", "kind": "after", "min": 50, "max": 99, "rounds": 4}),
    _skill(7, "num-pair", "maths", 4, "✌️", L("Pair ou impair", "Even or odd", "Par o impar"),
           {"type": "math", "kind": "evenodd", "min": 1, "max": 20, "rounds": 4}),
    _skill(8, "num-suite", "maths", 4, "🔁", L("Compter de 2 en 2", "Count by twos", "Contar de dos en dos"),
           {"type": "math", "kind": "sequence", "min": 2, "max": 20, "step": 2, "rounds": 4}),
    _skill(9, "num-add-1", "maths", 3, "➕", L("Petites additions (jusqu'à 5)", "Small additions (up to 5)", "Sumas pequeñas (hasta 5)"),
           {"type": "math", "kind": "add", "min": 1, "max": 4, "max_sum": 5, "rounds": 4}),
    _skill(10, "num-add-2", "maths", 4, "➕", L("Additions jusqu'à 10", "Additions up to 10", "Sumas hasta 10"),
           {"type": "math", "kind": "add", "min": 2, "max": 9, "max_sum": 10, "rounds": 4}),
    _skill(11, "num-sub-1", "maths", 4, "➖", L("Petites soustractions (jusqu'à 5)", "Small subtractions (up to 5)", "Restas pequeñas (hasta 5)"),
           {"type": "math", "kind": "sub", "min": 1, "max": 5, "rounds": 4}),
    _skill(12, "num-sub-2", "maths", 5, "➖", L("Soustractions jusqu'à 10", "Subtractions up to 10", "Restas hasta 10"),
           {"type": "math", "kind": "sub", "min": 1, "max": 10, "rounds": 4}),
    _skill(13, "num-mult-1", "maths", 5, "✖️", L("Tables de 2, 5 et 10", "Times tables 2, 5 and 10", "Tablas del 2, 5 y 10"),
           {"type": "math", "kind": "mult", "ops": [2, 5, 10], "maxf": 5, "rounds": 4}),
    _skill(14, "num-mult-2", "maths", 6, "✖️", L("Toutes les tables", "All times tables", "Todas las tablas"),
           {"type": "math", "kind": "mult", "ops": [2, 3, 4, 6, 7, 8, 9], "maxf": 9, "rounds": 4}),
    # ============ 🔷 FORMES (4) ============
    _skill(15, "form-1", "formes", 1, "🔷", L("Les formes", "Shapes", "Las formas"), _tap(SHAPES_1)),
    _skill(16, "form-2", "formes", 2, "💠", L("Les formes, niveau 2", "Shapes 2", "Las formas 2"), _tap(SHAPES_2)),
    _skill(17, "form-3", "formes", 3, "🌀", L("Formes rigolotes", "Fun shapes", "Formas divertidas"),
           _tap([_item("hexagon", "⬡", "hexagone", "hexagon", "hexágono"),
                 _item("oval", "🥚", "ovale", "oval", "óvalo"),
                 _item("cross", "✚", "croix", "cross", "cruz"),
                 _item("spiral", "🌀", "spirale", "spiral", "espiral")])),
    _skill(18, "form-3d", "formes", 4, "🧊", L("Les solides", "3D shapes", "Los sólidos"),
           _tap([_item("cube", "🧊", "cube", "cube", "cubo"),
                 _item("sphere", "🔮", "sphère", "sphere", "esfera"),
                 _item("cone", "🍦", "cône", "cone", "cono"),
                 _item("cylinder", "🥫", "cylindre", "cylinder", "cilindro")])),
    # ============ 🎨 ARTS (5) ============
    _skill(19, "coul-1", "arts", 1, "🎨", L("Les couleurs", "Colors", "Los colores"), _tap(COLORS_1)),
    _skill(20, "coul-2", "arts", 2, "🌈", L("L'arc-en-ciel", "The rainbow", "El arcoíris"), _tap(COLORS_2)),
    _skill(21, "art-mix", "arts", 3, "🧪", L("Mélange de couleurs", "Mixing colors", "Mezclar colores"),
           {"type": "mix", "rounds": 3, "combos": [
               {"a": "🔴", "b": "🔵", "r": "🟣", "distractors": ["🟢", "🟠", "🌸"]},
               {"a": "🔴", "b": "🟡", "r": "🟠", "distractors": ["🟣", "🟢", "🟤"]},
               {"a": "🔵", "b": "🟡", "r": "🟢", "distractors": ["🟣", "🟠", "🌸"]},
               {"a": "⚪", "b": "🔴", "r": "🌸", "distractors": ["🟠", "🟢", "🟤"]}]}),
    _skill(22, "art-rythme", "arts", 1, "🥁", L("Le rythme", "Rhythm", "El ritmo"),
           {"type": "sequence", "rounds": 3,
            "options": [_item("drum", "🥁", "tambour", "drum", "tambor"),
                        _item("clap", "👏", "mains", "clap", "palmas"),
                        _item("bell", "🔔", "cloche", "bell", "campana")],
            "puzzles": [{"seq": ["drum", "clap", "drum"], "answer": "clap"},
                        {"seq": ["bell", "bell", "drum", "bell", "bell"], "answer": "drum"},
                        {"seq": ["clap", "clap", "bell", "clap", "clap"], "answer": "bell"}]}),
    _skill(23, "art-music", "arts", 1, "🎹", L("Les instruments", "Instruments", "Los instrumentos"),
           _tap([_item("piano", "🎹", "piano", "piano", "piano"),
                 _item("guitar", "🎸", "guitare", "guitar", "guitarra"),
                 _item("drum", "🥁", "tambour", "drum", "tambor"),
                 _item("trumpet", "🎺", "trompette", "trumpet", "trompeta")])),
    # ============ 🐾 ANIMAUX (4) ============
    _skill(24, "anim-1", "animaux", 1, "🐱", L("Les animaux familiers", "Pets & farm", "Animales de la granja"), _tap(ANIMALS_1)),
    _skill(25, "anim-2", "animaux", 2, "🦁", L("Les animaux sauvages", "Wild animals", "Animales salvajes"), _tap(ANIMALS_2)),
    _skill(26, "anim-3", "animaux", 3, "🐬", L("Les animaux de la mer", "Sea animals", "Animales del mar"), _tap(ANIMALS_3)),
    _skill(27, "anim-4", "animaux", 4, "🏡", L("Où vivent-ils ?", "Where do they live?", "¿Dónde viven?"),
           _tap([_item("sea", "🌊", "la mer", "the sea", "el mar"),
                 _item("forest", "🌲", "la forêt", "the forest", "el bosque"),
                 _item("farm", "🌾", "la ferme", "the farm", "la granja"),
                 _item("savanna", "🌴", "la savane", "the savanna", "la sabana")],
                instruction=L("Touche : {label} {emoji}", "Touch: {label} {emoji}", "Toca: {label} {emoji}"))),
    # ============ 📖 FRANÇAIS (8) ============
    _skill(28, "lett-1", "francais", 1, "🔤", L("Les lettres A B C D", "Letters A B C D", "Las letras A B C D"),
           _tap([_item("a", "🅰️", "A", "A", "A"), _item("b", "🅱️", "B", "B", "B"),
                 _item("c", "©️", "C", "C", "C"), _item("d", "🌛", "D", "D", "D")], rounds=4,
                instruction=L("Touche la lettre : {label}", "Touch the letter: {label}", "Toca la letra: {label}"))),
    _skill(29, "lett-2", "francais", 2, "🔡", L("Tout l'alphabet", "The whole alphabet", "Todo el alfabeto"),
           {"type": "letters", "alphabet": "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "rounds": 4}),
    _skill(30, "lett-3", "francais", 3, "🗣️", L("Les sons des lettres", "Letter sounds", "Los sonidos de las letras"),
           {"type": "voice", "kind": "speak", "target_lang": "fr",
            "intro": L("Dis le son de la lettre", "Say the sound of the letter", "Di el sonido de la letra"),
            "targets": ["A", "B", "M", "S", "O"], "rounds": 3}),
    _skill(31, "lect-1", "francais", 4, "📖", L("Mes premières syllabes", "My first syllables", "Mis primeras sílabas"),
           _tap([_item("ba", "🅱️", "BA", "BA", "BA"), _item("ma", "Ⓜ️", "MA", "MA", "MA"),
                 _item("la", "🌿", "LA", "LA", "LA"), _item("sa", "⭐", "SA", "SA", "SA")], rounds=4,
                instruction=L("Touche la syllabe : « {label} »", "Touch the syllable: “{label}”", "Toca la sílaba: «{label}»"))),
    _skill(32, "lect-2", "francais", 5, "📖", L("Mes premiers mots", "My first words", "Mis primeras palabras"),
           {"type": "voice", "kind": "speak", "target_lang": "fr",
            "intro": L("Lis ce mot", "Read this word", "Lee esta palabra"),
            "targets": ["chat", "maman", "papa", "lune", "main"], "rounds": 3}),
    _skill(33, "lect-3", "francais", 6, "📚", L("Mes premières phrases", "My first sentences", "Mis primeras frases"),
           {"type": "voice", "kind": "speak", "target_lang": "fr",
            "intro": L("Lis cette phrase", "Read this sentence", "Lee esta frase"),
            "targets": ["Le chat dort.", "J'aime maman.", "Le soleil brille."], "rounds": 2}),
    _skill(34, "ecri-1", "francais", 3, "✏️", L("J'écris mon prénom", "I write my name", "Escribo mi nombre"),
           {"type": "task", "tasks": [
               L("Sur une feuille, écris ton prénom en capitales — l'adulte valide ! ✍️",
                 "On a sheet of paper, write your first name in capitals — a grown-up validates! ✍️",
                 "En una hoja, escribe tu nombre en mayúsculas — ¡un adulto lo valida! ✍️")], "rounds": 1}),
    _skill(35, "ecri-2", "francais", 5, "✏️", L("J'écris des mots", "I write words", "Escribo palabras"),
           {"type": "task", "tasks": [
               L("Écris le mot « chat » sur une feuille ! 🐱", "Write the word “cat” on paper! 🐱", "¡Escribe la palabra «gato» en una hoja! 🐱"),
               L("Écris le mot « maman » sur une feuille ! 💛", "Write the word “mummy” on paper! 💛", "¡Escribe la palabra «mamá» en una hoja! 💛")], "rounds": 2}),
    # ============ 🇬🇧 ANGLAIS (5) ============
    _skill(36, "en-word-1", "anglais", 1, "🇬🇧", L("English : les couleurs", "English: colors", "Inglés: los colores"),
           _tap([_item("en-red", "🔴", "red", "red", "red"), _item("en-blue", "🔵", "blue", "blue", "blue"),
                 _item("en-green", "🟢", "green", "green", "green"), _item("en-yellow", "🟡", "yellow", "yellow", "yellow")],
                instruction=L("Touche « {label} » {emoji}", "Touch “{label}” {emoji}", "Toca «{label}» {emoji}"))),
    _skill(37, "en-word-2", "anglais", 2, "🇬🇧", L("English : les animaux", "English: animals", "Inglés: los animales"),
           _tap([_item("en-cat", "🐱", "cat", "cat", "cat"), _item("en-dog", "🐶", "dog", "dog", "dog"),
                 _item("en-bird", "🐦", "bird", "bird", "bird"), _item("en-fish", "🐟", "fish", "fish", "fish")],
                instruction=L("Touche « {label} » {emoji}", "Touch “{label}” {emoji}", "Toca «{label}» {emoji}"))),
    _skill(38, "en-word-3", "anglais", 3, "🇬🇧", L("English : les nombres", "English: numbers", "Inglés: los números"),
           {"type": "voice", "kind": "speak", "target_lang": "en",
            "intro": L("Répète en anglais", "Say it in English", "Repite en inglés"),
            "targets": ["one", "two", "three", "four", "five"], "rounds": 3}),
    _skill(39, "en-phr-1", "anglais", 1, "🇬🇧", L("English : saluer", "English: greetings", "Inglés: saludos"),
           {"type": "voice", "kind": "speak", "target_lang": "en",
            "intro": L("Répète en anglais", "Say it in English", "Repite en inglés"),
            "targets": ["Hello!", "Goodbye!", "Thank you!"], "rounds": 3}),
    _skill(40, "en-phr-2", "anglais", 2, "🇬🇧", L("English : se présenter", "English: introduce yourself", "Inglés: presentarse"),
           {"type": "voice", "kind": "speak", "target_lang": "en",
            "intro": L("Répète en anglais", "Say it in English", "Repite en inglés"),
            "targets": ["My name is…", "I am three", "How are you?"], "rounds": 3}),
    # ============ 🇪🇸 ESPAGNOL (5) ============
    _skill(41, "es-word-1", "espagnol", 1, "🇪🇸", L("Espagnol : les couleurs", "Spanish: colors", "Español: los colores"),
           _tap([_item("es-red", "🔴", "rojo", "rojo", "rojo"), _item("es-blue", "🔵", "azul", "azul", "azul"),
                 _item("es-green", "🟢", "verde", "verde", "verde"), _item("es-yellow", "🟡", "amarillo", "amarillo", "amarillo")],
                instruction=L("Touche « {label} » {emoji}", "Touch “{label}” {emoji}", "Toca «{label}» {emoji}"))),
    _skill(42, "es-word-2", "espagnol", 2, "🇪🇸", L("Espagnol : les animaux", "Spanish: animals", "Español: los animales"),
           _tap([_item("es-cat", "🐱", "gato", "gato", "gato"), _item("es-dog", "🐶", "perro", "perro", "perro"),
                 _item("es-bird", "🐦", "pájaro", "pájaro", "pájaro"), _item("es-fish", "🐟", "pez", "pez", "pez")],
                instruction=L("Touche « {label} » {emoji}", "Touch “{label}” {emoji}", "Toca «{label}» {emoji}"))),
    _skill(43, "es-word-3", "espagnol", 3, "🇪🇸", L("Espagnol : les nombres", "Spanish: numbers", "Español: los números"),
           {"type": "voice", "kind": "speak", "target_lang": "es",
            "intro": L("Répète en espagnol", "Say it in Spanish", "Repite en español"),
            "targets": ["uno", "dos", "tres", "cuatro", "cinco"], "rounds": 3}),
    _skill(44, "es-phr-1", "espagnol", 1, "🇪🇸", L("Espagnol : saluer", "Spanish: greetings", "Español: saludos"),
           {"type": "voice", "kind": "speak", "target_lang": "es",
            "intro": L("Répète en espagnol", "Say it in Spanish", "Repite en español"),
            "targets": ["¡Hola!", "¡Adiós!", "¡Gracias!"], "rounds": 3}),
    _skill(45, "es-phr-2", "espagnol", 2, "🇪🇸", L("Espagnol : se présenter", "Spanish: introduce yourself", "Español: presentarse"),
           {"type": "voice", "kind": "speak", "target_lang": "es",
            "intro": L("Répète en espagnol", "Say it in Spanish", "Repite en español"),
            "targets": ["Me llamo…", "Tengo tres años", "¿Cómo estás?"], "rounds": 3}),
    # ============ 🧩 LOGIQUE (5) ============
    _skill(46, "log-tri", "logique", 1, "🧺", L("L'intrus", "The odd one out", "El intruso"),
           {"type": "oddone", "rounds": 3, "sets": [
               {"options": [{"id": "cat", "emoji": "🐱"}, {"id": "dog", "emoji": "🐶"}, {"id": "apple", "emoji": "🍎"}],
                "odd": "apple",
                "hint": L("n'est pas un animal", "is not an animal", "no es un animal")},
               {"options": [{"id": "red", "emoji": "🔴"}, {"id": "blue", "emoji": "🔵"}, {"id": "star", "emoji": "⭐"}],
                "odd": "star",
                "hint": L("n'est pas un rond", "is not a dot", "no es un círculo")},
               {"options": [{"id": "banana", "emoji": "🍌"}, {"id": "apple2", "emoji": "🍏"}, {"id": "sock", "emoji": "🧦"}],
                "odd": "sock",
                "hint": L("ne se mange pas", "is not food", "no se come")}]}),
    _skill(47, "log-suite", "logique", 2, "🔴", L("Complète la série", "Complete the pattern", "Completa la serie"),
           {"type": "sequence", "rounds": 3,
            "options": [_item("red", "🔴", "rouge", "red", "rojo"), _item("blue", "🔵", "bleu", "blue", "azul"),
                        _item("star", "⭐", "étoile", "star", "estrella"), _item("moon", "🌙", "lune", "moon", "luna")],
            "puzzles": [{"seq": ["red", "blue", "red"], "answer": "blue"},
                        {"seq": ["star", "star", "moon", "star", "star"], "answer": "moon"},
                        {"seq": ["red", "red", "blue", "red", "red"], "answer": "blue"}]}),
    _skill(48, "log-ombre", "logique", 1, "👯", L("Les jumeaux", "The twins", "Los gemelos"),
           {"type": "same", "rounds": 3, "targets": [
               {"id": "star", "emoji": "⭐", "distractors": ["✨", "🌟", "💫"]},
               {"id": "apple", "emoji": "🍎", "distractors": ["🍏", "🍊", "🍋"]},
               {"id": "car", "emoji": "🚗", "distractors": ["🚙", "🚕", "🚌"]}]}),
    _skill(49, "log-cause", "logique", 1, "⚡", L("Cause et effet", "Cause and effect", "Causa y efecto"),
           {"type": "quiz", "rounds": 3, "scenes": [
               {"q": L("Il pleut ! ☔ Que prends-tu ?", "It's raining! ☔ What do you take?", "¡Llueve! ☔ ¿Qué coges?"),
                "options": [_item("umbrella", "🌂", "parapluie", "umbrella", "paraguas"),
                            _item("sunglasses", "🕶️", "lunettes de soleil", "sunglasses", "gafas de sol"),
                            _item("icecream", "🍦", "glace", "ice cream", "helado")],
                "answer": "umbrella"},
               {"q": L("Tu as froid ! ❄️ Que mets-tu ?", "You're cold! ❄️ What do you wear?", "¡Tienes frío! ❄️ ¿Qué te pones?"),
                "options": [_item("coat", "🧥", "manteau", "coat", "abrigo"),
                            _item("swimsuit", "🩱", "maillot", "swimsuit", "bañador"),
                            _item("crown", "👑", "couronne", "crown", "corona")],
                "answer": "coat"},
               {"q": L("C'est la nuit 🌙 Où vas-tu ?", "It's night time 🌙 Where do you go?", "Es de noche 🌙 ¿Adónde vas?"),
                "options": [_item("bed", "🛏️", "au lit", "to bed", "a la cama"),
                            _item("park", "🛝", "au parc", "to the park", "al parque"),
                            _item("pool", "🏊", "à la piscine", "to the pool", "a la piscina")],
                "answer": "bed"}]}),
    _skill(50, "log-taille", "logique", 2, "🐘", L("Le plus grand, le plus petit", "Big and small", "Grande y pequeño"),
           {"type": "size", "rounds": 4, "sets": [
               {"options": [{"id": "elephant", "emoji": "🐘", "size": 3}, {"id": "mouse", "emoji": "🐁", "size": 1},
                            {"id": "bird", "emoji": "🦜", "size": 2}]},
               {"options": [{"id": "tree", "emoji": "🌳", "size": 3}, {"id": "flower", "emoji": "🌼", "size": 1},
                            {"id": "bush", "emoji": "🌿", "size": 2}]}]}),
    # ============ ❤️ BIEN-ÊTRE (6) ============
    _skill(51, "bien-emo-1", "bien-etre", 1, "😊", L("Les émotions", "Emotions", "Las emociones"),
           _tap([_item("happy", "😊", "contente", "happy", "contenta"),
                 _item("sad", "😢", "triste", "sad", "triste"),
                 _item("angry", "😠", "en colère", "angry", "enfadada"),
                 _item("scared", "😨", "effrayée", "scared", "asustada")], rounds=4,
                instruction=L("Touche le visage : {label} {emoji}", "Touch the face: {label} {emoji}", "Toca la cara: {label} {emoji}"))),
    _skill(52, "bien-resp", "bien-etre", 2, "🌬️", L("Je respire et je me calme", "I breathe and calm down", "Respiro y me calmo"),
           {"type": "breath", "cycles": 3}),
    _skill(53, "bien-pol", "bien-etre", 1, "🙏", L("Les mots magiques", "Magic words", "Las palabras mágicas"),
           {"type": "quiz", "rounds": 3, "scenes": [
               {"q": L("On t'offre un cadeau 🎁 Que dis-tu ?", "You receive a gift 🎁 What do you say?", "Te regalan algo 🎁 ¿Qué dices?"),
                "options": [_item("thanks", "💛", "MERCI", "THANK YOU", "GRACIAS"),
                            _item("want", "😤", "JE VEUX !", "I WANT!", "¡LO QUIERO!"),
                            _item("nothing", "😐", "rien", "nothing", "nada")],
                "answer": "thanks"},
               {"q": L("Tu veux un bonbon 🍬 Que dis-tu ?", "You want a sweet 🍬 What do you say?", "Quieres un caramelo 🍬 ¿Qué dices?"),
                "options": [_item("please", "🙏", "S'IL TE PLAÎT", "PLEASE", "POR FAVOR"),
                            _item("now", "😠", "TOUT DE SUITE !", "RIGHT NOW!", "¡AHORA!"),
                            _item("cry", "😭", "pleurer", "cry", "llorar")],
                "answer": "please"},
               {"q": L("Tu as bousculé quelqu'un 😯 Que dis-tu ?", "You bumped into someone 😯 What do you say?", "Chocas con alguien 😯 ¿Qué dices?"),
                "options": [_item("sorry", "🤗", "PARDON", "SORRY", "PERDÓN"),
                            _item("laugh", "😂", "rire", "laugh", "reírse"),
                            _item("run", "🏃", "courir", "run away", "salir corriendo")],
                "answer": "sorry"}]}),
    _skill(54, "bien-part", "bien-etre", 2, "🤝", L("Je partage", "I share", "Comparto"),
           {"type": "quiz", "rounds": 2, "scenes": [
               {"q": L("Ton ami veut ton jouet 🧸 Que fais-tu ?", "Your friend wants your toy 🧸 What do you do?", "Tu amigo quiere tu juguete 🧸 ¿Qué haces?"),
                "options": [_item("share", "🤝", "je prête", "I share", "lo presto"),
                            _item("hide", "🙈", "je cache", "I hide it", "lo escondo"),
                            _item("shout", "📢", "je crie", "I shout", "grito")],
                "answer": "share"},
               {"q": L("C'est le tour de ta sœur 🎠 Que fais-tu ?", "It's your sister's turn 🎠 What do you do?", "Es el turno de tu hermana 🎠 ¿Qué haces?"),
                "options": [_item("wait", "😌", "j'attends", "I wait", "espero"),
                            _item("push", "👋", "je pousse", "I push", "empujo"),
                            _item("cry2", "😭", "je pleure", "I cry", "lloro")],
                "answer": "wait"}]}),
    _skill(55, "bien-hyg", "bien-etre", 1, "🧼", L("Propre comme un sou", "Clean and healthy", "Limpio y sano"),
           {"type": "quiz", "rounds": 2, "scenes": [
               {"q": L("Avant de manger 🍽️ Que fais-tu ?", "Before eating 🍽️ What do you do?", "Antes de comer 🍽️ ¿Qué haces?"),
                "options": [_item("wash", "🧼", "me laver les mains", "wash my hands", "lavarme las manos"),
                            _item("run", "🏃", "courir", "run", "correr"),
                            _item("tv", "📺", "regarder la télé", "watch TV", "ver la tele")],
                "answer": "wash"},
               {"q": L("Avant de dormir 🌙 Que fais-tu ?", "Before bed 🌙 What do you do?", "Antes de dormir 🌙 ¿Qué haces?"),
                "options": [_item("teeth", "🪥", "me brosser les dents", "brush my teeth", "cepillarme los dientes"),
                            _item("candy", "🍬", "manger un bonbon", "eat a sweet", "comer un caramelo"),
                            _item("jump", "🤸", "sauter", "jump", "saltar")],
                "answer": "teeth"}]}),
    _skill(56, "bien-corps", "bien-etre", 1, "🖐️", L("Mon corps", "My body", "Mi cuerpo"),
           _tap([_item("hand", "🖐️", "la main", "hand", "la mano"),
                 _item("nose", "👃", "le nez", "nose", "la nariz"),
                 _item("mouth", "👄", "la bouche", "mouth", "la boca"),
                 _item("eye", "👁️", "l'œil", "eye", "el ojo"),
                 _item("foot", "🦶", "le pied", "foot", "el pie")], rounds=4,
                instruction=L("Montre : {label} {emoji}", "Show me: {label} {emoji}", "Muéstrame: {label} {emoji}"))),
    # ============ 🌍 DÉCOUVERTE (4) ============
    _skill(57, "dec-meteo", "decouverte", 1, "☀️", L("La météo", "The weather", "El tiempo"),
           _tap([_item("sun", "☀️", "le soleil", "sun", "el sol"), _item("rain", "🌧️", "la pluie", "rain", "la lluvia"),
                 _item("snow", "❄️", "la neige", "snow", "la nieve"), _item("wind", "💨", "le vent", "wind", "el viento")])),
    _skill(58, "dec-saisons", "decouverte", 2, "🍂", L("Les quatre saisons", "The four seasons", "Las cuatro estaciones"),
           _tap([_item("spring", "🌸", "le printemps", "spring", "la primavera"),
                 _item("summer", "☀️", "l'été", "summer", "el verano"),
                 _item("autumn", "🍂", "l'automne", "autumn", "el otoño"),
                 _item("winter", "❄️", "l'hiver", "winter", "el invierno")], rounds=4)),
    _skill(59, "dec-espace", "decouverte", 1, "🌙", L("Terre, Lune et Soleil", "Earth, Moon and Sun", "Tierra, Luna y Sol"),
           _tap([_item("earth", "🌍", "la Terre", "the Earth", "la Tierra"),
                 _item("moon", "🌙", "la Lune", "the Moon", "la Luna"),
                 _item("sun", "☀️", "le Soleil", "the Sun", "el Sol"),
                 _item("stars", "⭐", "les étoiles", "the stars", "las estrellas")],
                instruction=L("Touche : {label} {emoji}", "Touch: {label} {emoji}", "Toca: {label} {emoji}"))),
    _skill(60, "dec-temps", "decouverte", 1, "⏰", L("Matin, midi et soir", "Morning, noon and night", "Mañana, mediodía y noche"),
           _tap([_item("morning", "🌅", "le matin", "morning", "la mañana"),
                 _item("noon", "☀️", "le midi", "noon", "el mediodía"),
                 _item("evening", "🌙", "le soir", "evening", "la noche")])),
    # ============ 🎵 COMPTINES (2) ============
    _skill(61, "song-1", "comptines", 1, "🎵", L("Comptine : Une souris verte", "Song: A Little Green Mouse", "Canción: Una ratita verde"),
           {"type": "song",
            "title": L("Une souris verte", "A Little Green Mouse", "Una ratita verde"),
            "lines": {"fr": ["Une souris verte 🐭", "Qui courait dans l'herbe 🌿",
                             "Je l'attrape par la queue 🐾", "Je la montre à ces messieurs 🎩"],
                      "en": ["A little green mouse 🐭", "Running through the grass 🌿",
                             "I catch her by the tail 🐾", "And show her to the gentlemen 🎩"],
                      "es": ["Una ratita verde 🐭", "Que corría por la hierba 🌿",
                             "La atrapé por la cola 🐾", "Y se la mostré a los señores 🎩"]}}),
    _skill(62, "song-2", "comptines", 1, "🎵", L("Comptine : Frère Jacques", "Song: Brother John", "Canción: Fray Santiago"),
           {"type": "song",
            "title": L("Frère Jacques", "Brother John", "Fray Santiago"),
            "lines": {"fr": ["Frère Jacques, Frère Jacques 🎵", "Dormez-vous ? Dormez-vous ? 😴",
                             "Sonnez les matines, sonnez les matines 🔔", "Din din don, din din don 🔔"],
                      "en": ["Are you sleeping, are you sleeping 🎵", "Brother John, Brother John 😴",
                             "Morning bells are ringing, morning bells are ringing 🔔", "Ding ding dong, ding ding dong 🔔"],
                      "es": ["¿Estás durmiendo, estás durmiendo? 🎵", "Fray Santiago, Fray Santiago 😴",
                             "Suenan las campanas, suenan las campanas 🔔", "Din din don, din din don 🔔"]}}),
    # ============ 🚀 CRÉER & INVENTER (16) — rubrique v2.3 ============
    # Boucle du petit inventeur : Imaginer → Concevoir → Construire → Tester → Expliquer.
    # Règle d'or anti-frustration : tout ce qui est CRÉATION (draw/task) n'a jamais de
    # « mauvaise réponse » — l'adulte valide, l'enfant gagne toujours. Seules les notions
    # FACTUELLES (sciences, ordre, pourquoi) sont des quiz/tap/séquences notés.
    _skill(63, "inv-obs", "invention", 2, "🔍", L("Œil de scientifique : j'observe", "Scientist's eye: I observe", "Ojo de científica: yo observo"),
           _tap([_item("loupe", "🔍", "la loupe", "the magnifying glass", "la lupa"),
                 _item("balance", "⚖️", "la balance", "the scale", "la balanza"),
                 _item("thermo", "🌡️", "le thermomètre", "the thermometer", "el termómetro"),
                 _item("aimant", "🧲", "l'aimant", "the magnet", "el imán")], rounds=4,
                instruction=L("Les outils du savant ! Touche : {label} {emoji}", "The scientist's tools! Touch: {label} {emoji}", "¡Las herramientas del científico! Toca: {label} {emoji}"))),
    _skill(64, "inv-cause", "invention", 2, "🔮", L("Devine ce qui va se passer", "Guess what will happen", "Adivina lo que va a pasar"),
           {"type": "quiz", "rounds": 3, "scenes": [
               {"q": L("On laisse un glaçon au soleil ☀️ Que va-t-il faire ?", "We leave an ice cube in the sun ☀️ What will it do?", "Dejamos un cubito de hielo al sol ☀️ ¿Qué hará?"),
                "options": [_item("melt", "💧", "il fond", "it melts", "se derrite"),
                            _item("grow", "🧊", "il grossit", "it grows", "crece"),
                            _item("fly", "🕊️", "il s'envole", "it flies away", "sale volando")],
                "answer": "melt"},
               {"q": L("On lâche un ballon gonflé 🎈 Que fait-il ?", "We let go of an inflated balloon 🎈 What does it do?", "Soltamos un globo inflado 🎈 ¿Qué hace?"),
                "options": [_item("up", "🎈", "il s'envole", "it flies up", "sale volando"),
                            _item("stone", "🪨", "il tombe comme un caillou", "it drops like a stone", "cae como una piedra"),
                            _item("sleep", "😴", "il dort", "it sleeps", "duerme")],
                "answer": "up"},
               {"q": L("On arrose une petite graine 🌱 Que va-t-elle devenir ?", "We water a little seed 🌱 What will it become?", "Regamos una semillita 🌱 ¿En qué se convertirá?"),
                "options": [_item("plant", "🌻", "une plante", "a plant", "una planta"),
                            _item("car", "🚗", "une voiture", "a car", "un coche"),
                            _item("fish", "🐟", "un poisson", "a fish", "un pez")],
                "answer": "plant"}]}),
    _skill(65, "draw-animal", "invention", 2, "🦄", L("Dessine ton animal rêvé", "Draw your dream animal", "Dibuja tu animal soñado"),
           {"type": "draw", "rounds": 1,
            "intro": L("Invente un animal qui n'existe pas ! Dessine-le avec ton doigt sur l'ardoise magique ✨",
                       "Invent an animal that doesn't exist! Draw it with your finger on the magic board ✨",
                       "¡Inventa un animal que no existe! Dibújalo con tu dedo en la pizarra mágica ✨"),
            "palette": ["#e11d48", "#2563eb", "#16a34a", "#eab308", "#9333ea", "#0ea5e9", "#f97316", "#1e293b"]}),
    _skill(66, "inv-eau", "invention", 3, "💧", L("Expérience : ça coule ou ça flotte ?", "Experiment: sink or float?", "Experimento: ¿se hunde o flota?"),
           {"type": "task", "tasks": [
               L("Avec l'adulte, remplis une bassine d'eau 💧 Mets-y 3 objets (bouchon, cuillère, éponge…) et dis pour chacun : ÇA COULE ou ÇA FLOTTE ! L'adulte valide.",
                 "With a grown-up, fill a bowl with water 💧 Put in 3 objects (cork, spoon, sponge…) and say for each one: it SINKS or it FLOATS! A grown-up validates.",
                 "Con un adulto, llena un recipiente con agua 💧 Mete 3 objetos (corcho, cuchara, esponja…) y di de cada uno: ¡SE HUNDE o FLOTA! Un adulto lo valida.")],
            "rounds": 1,
            "materiel": L("Matériel maison 🎒 : une bassine (ou un grand saladier), de l’eau, 3 petits objets : bouchon, cuillère en plastique, éponge…", "At-home supplies 🎒: a basin (or big bowl), water, 3 small things: cork, plastic spoon, sponge…", "Material de casa 🎒: un barreño (o un tazón grande), agua, 3 objetos pequeños: corcho, cuchara de plástico, esponja…"),
            "guide": [
               {"emoji": "🪣", "label": L("1. Remplis la bassine d'eau", "1. Fill the bowl with water", "1. Llena el recipiente de agua")},
               {"emoji": "🤏", "label": L("2. Prends un objet", "2. Pick up an object", "2. Toma un objeto")},
               {"emoji": "💧", "label": L("3. Plonge ! Ça coule ou ça flotte ?", "3. Dip it in! Sinks or floats?", "3. ¡Mójalo! ¿Se hunde o flota?")}]}),
    _skill(67, "inv-aimant", "invention", 3, "🧲", L("Expérience : le pouvoir de l'aimant", "Experiment: magnet power", "Experimento: el poder del imán"),
           {"type": "task", "tasks": [
               L("Avec l'adulte, promène un aimant 🧲 sur 5 objets de la maison (clé, pièce, jouet, papier, cuillère). Dis lesquels COLLENT ! L'adulte valide.",
                 "With a grown-up, try a magnet 🧲 on 5 things at home (key, coin, toy, paper, spoon). Say which ones STICK! A grown-up validates.",
                 "Con un adulto, prueba un imán 🧲 con 5 objetos de casa (llave, moneda, juguete, papel, cuchara). Di cuáles SE PEGAN. Un adulto lo valida.")],
            "rounds": 1,
            "materiel": L("Matériel maison 🎒 : un aimant de frigo, 5 objets : clé, pièce, feuille de papier, jouet, cuillère", "At-home supplies 🎒: a fridge magnet, 5 things: key, coin, sheet of paper, toy, spoon", "Material de casa 🎒: un imán de nevera, 5 objetos: llave, moneda, hoja de papel, juguete, cuchara"),
            "guide": [
               {"emoji": "🧲", "label": L("1. Prends l'aimant", "1. Take the magnet", "1. Toma el imán")},
               {"emoji": "🔎", "label": L("2. Approche-le de chaque objet", "2. Bring it near each thing", "2. Acércalo a cada objeto")},
               {"emoji": "✨", "label": L("3. Ça colle ? Tu as trouvé !", "3. It sticks? You found one!", "3. ¿Se pega? ¡Lo hallaste!")}]}),
    _skill(68, "inv-graine", "invention", 3, "🌱", L("La graine devient plante", "The seed becomes a plant", "La semilla se convierte en planta"),
           {"type": "sequence", "rounds": 3,
            "options": [_item("seed", "🫘", "graine", "seed", "semilla"),
                        _item("water", "💧", "eau", "water", "agua"),
                        _item("sun", "☀️", "soleil", "sun", "sol"),
                        _item("plant", "🌻", "plante", "plant", "planta")],
            "puzzles": [{"seq": ["seed", "water", "sun"], "answer": "plant"}]}),
    _skill(69, "inv-histoire", "invention", 3, "📖", L("J'invente une histoire", "I invent a story", "Invento una historia"),
           {"type": "task", "tasks": [
               L("Raconte une histoire à voix haute ! Commence par « Il était une fois… » : un héros, un problème, une fin heureuse. L'adulte écoute et valide 📖✨",
                 "Tell a story out loud! Start with “Once upon a time…”: a hero, a problem, a happy ending. A grown-up listens and validates 📖✨",
                 "¡Cuenta una historia en voz alta! Empieza con «Érase una vez…»: un héroe, un problema y un final feliz. Un adulto escucha y valida 📖✨")],
            "rounds": 1,
            "materiel": L("Matériel maison 🎒 : rien du tout ! Ta voix suffit — ou des crayons et une feuille pour dessiner ton héros", "At-home supplies 🎒: nothing at all! Your voice is enough — or crayons and paper to draw your hero", "Material de casa 🎒: ¡nada! Tu voz basta — o crayones y una hoja para dibujar tu héroe"),
            "guide": [
               {"emoji": "🦸", "label": L("1. Choisis un héros", "1. Choose a hero", "1. Elige un héroe")},
               {"emoji": "😱", "label": L("2. Invente-lui un problème", "2. Give them a problem", "2. Invéntale un problema")},
               {"emoji": "🎉", "label": L("3. Trouve une fin heureuse !", "3. Find a happy ending!", "3. ¡Busca un final feliz!")}]}),
    _skill(70, "inv-robot", "invention", 3, "🤖", L("Je construis un robot", "I build a robot", "Construyo un robot"),
           {"type": "task", "tasks": [
               L("Avec l'adulte, construis un ROBOT avec des objets recyclés : rouleaux de carton, boîtes, bouchons, papier d'alu… Ajoute des boutons imaginaires ! L'adulte valide 🤖",
                 "With a grown-up, build a ROBOT from recycled things: cardboard tubes, boxes, bottle tops, foil… Add imaginary buttons! A grown-up validates 🤖",
                 "Con un adulto, construye un ROBOT con cosas recicladas: tubos de cartón, cajas, tapones, papel de aluminio… ¡Añade botones imaginarios! Un adulto lo valida 🤖")],
            "rounds": 1,
            "materiel": L("Matériel maison 🎒 : rouleaux de papier toilette ou d’essuie-tout, petites boîtes, bouchons, papier d’alu, ruban adhésif — l’adulte manie ciseaux et colle", "At-home supplies 🎒: toilet/kitchen roll tubes, small boxes, bottle caps, foil, sticky tape — the grown-up handles scissors and glue", "Material de casa 🎒: tubos de papel higiénico o de cocina, cajitas, tapones, papel de aluminio, cinta adhesiva — el adulto usa tijeras y pegamento"),
            "guide": [
               {"emoji": "🧴", "label": L("1. Rassemble : cartons, bouchons, alu", "1. Gather: cardboard, caps, foil", "1. Junta: cartón, tapas, aluminio")},
               {"emoji": "🔗", "label": L("2. Assemble tête, corps, bras", "2. Join head, body, arms", "2. Une cabeza, cuerpo, brazos")},
               {"emoji": "🎛️", "label": L("3. Dessine les boutons magiques", "3. Draw the magic buttons", "3. Dibuja los botones mágicos")}]}),
    _skill(71, "inv-tour", "invention", 3, "🏗️", L("L'architecte : la plus haute tour", "The architect: the tallest tower", "La arquitecta: la torre más alta"),
           {"type": "task", "tasks": [
               L("Construis la tour LA PLUS HAUTE possible avec des blocs, des boîtes ou des livres… jusqu'à 10 étages ! Compte-les à voix haute. L'adulte valide 🏗️",
                 "Build the TALLEST tower you can with blocks, boxes or books… up to 10 floors! Count them out loud. A grown-up validates 🏗️",
                 "¡Construye la torre MÁS ALTA posible con bloques, cajas o libros… hasta 10 pisos! Cuéntalos en voz alta. Un adulto lo valida 🏗️")],
            "rounds": 1,
            "materiel": L("Matériel maison 🎒 : blocs, ou boîtes en carton, ou livres — et une surface plane (table ou sol)", "At-home supplies 🎒: blocks, or cardboard boxes, or books — and a flat surface (table or floor)", "Material de casa 🎒: bloques, cajas de cartón o libros — y una superficie plana (mesa o suelo)"),
            "guide": [
               {"emoji": "🟥", "label": L("1. Pose la première brique bien à plat", "1. Lay the first brick really flat", "1. Pon el primer ladrillo bien plano")},
               {"emoji": "🧱", "label": L("2. Empile en alternant les pièces", "2. Stack, alternating the pieces", "2. Apila alternando las piezas")},
               {"emoji": "🔟", "label": L("3. Compte les étages à voix haute !", "3. Count the floors out loud!", "3. ¡Cuenta los pisos en voz alta!")}]}),
    _skill(72, "inv-boite", "invention", 3, "📦", L("Nouvelle vie pour une boîte", "A new life for a box", "Una vida nueva para una caja"),
           {"type": "task", "tasks": [
               L("Prends une boîte en carton vide 📦 et transforme-la : maison, fusée, voiture, bateau… Dis ce qu'elle est devenue ! L'adulte valide.",
                 "Take an empty cardboard box 📦 and turn it into something: house, rocket, car, boat… Say what it became! A grown-up validates.",
                 "Toma una caja de cartón vacía 📦 y transfórmala: casa, cohete, coche, barco… ¡Di en qué se convirtió! Un adulto lo valida.")],
            "rounds": 1,
            "materiel": L("Matériel maison 🎒 : une boîte en carton (chaussures, céréales…), ciseaux (pour l’adulte !), colle ou ruban adhésif, crayons", "At-home supplies 🎒: a cardboard box (shoes, cereal…), scissors (for the grown-up!), glue or sticky tape, crayons", "Material de casa 🎒: una caja de cartón (zapatos, cereales…), tijeras (¡para el adulto!), pegamento o cinta, crayones"),
            "guide": [
               {"emoji": "📦", "label": L("1. Prends la boîte vide", "1. Take the empty box", "1. Toma la caja vacía")},
               {"emoji": "✂️", "label": L("2. Avec l'adulte : coupe, colle, décore", "2. With a grown-up: cut, glue, decorate", "2. Con un adulto: corta, pega, decora")},
               {"emoji": "🚀", "label": L("3. Dis ce qu'elle est devenue !", "3. Say what it became!", "3. ¡Di en qué se convirtió!")}]}),
    _skill(73, "inv-pont", "invention", 4, "🌉", L("L'ingénieure : le pont", "The engineer: the bridge", "La ingeniera: el puente"),
           {"type": "task", "tasks": [
               L("Avec des livres, du carton ou des légos, construis un PONT entre deux chaises 🌉 Test : pose un petit jouet dessus. Il tient ? L'adulte valide !",
                 "With books, cardboard or building bricks, build a BRIDGE between two chairs 🌉 Test: put a small toy on it. Does it hold? A grown-up validates!",
                 "Con libros, cartón o bloques, construye un PUENTE entre dos sillas 🌉 Prueba: pon un juguete encima. ¿Aguanta? ¡Un adulto lo valida!")],
            "rounds": 1,
            "materiel": L("Matériel maison 🎒 : 2 chaises, des livres rigides ou du carton ou des légos, un petit jouet pour le test", "At-home supplies 🎒: 2 chairs, hardback books or cardboard or building bricks, a small toy for the test", "Material de casa 🎒: 2 sillas, libros gruesos o cartón o bloques de construcción, un juguete pequeño para la prueba"),
            "guide": [
               {"emoji": "🪑", "label": L("1. Écarte deux chaises", "1. Spread two chairs apart", "1. Separa dos sillas")},
               {"emoji": "🌉", "label": L("2. Pose ton pont entre les deux", "2. Lay your bridge across them", "2. Coloca tu puente entre las dos")},
               {"emoji": "🧸", "label": L("3. Test : le jouet traverse ?", "3. Test: does the toy cross?", "3. Prueba: ¿cruza el juguete?")}]}),
    _skill(74, "inv-plan", "invention", 4, "📐", L("Dans le bon ordre !", "In the right order!", "¡En el orden correcto!"),
           {"type": "sequence", "rounds": 3,
            "options": [_item("bread", "🍞", "pain", "bread", "pan"),
                        _item("cheese", "🧀", "fromage", "cheese", "queso"),
                        _item("lettuce", "🥬", "salade", "lettuce", "lechuga"),
                        _item("sandwich", "🥪", "sandwich", "sandwich", "sándwich")],
            "puzzles": [{"seq": ["bread", "cheese", "lettuce"], "answer": "sandwich"}]}),
    _skill(75, "inv-probleme", "invention", 4, "🧠", L("La débrouille des inventeurs", "The inventors' cleverness", "El ingenio de los inventores"),
           {"type": "quiz", "rounds": 3, "scenes": [
               {"q": L("Ton jouet est passé sous le canapé 🛋️ Comment l'attraper ?", "Your toy slipped under the sofa 🛋️ How do you get it?", "Tu juguete se metió debajo del sofá 🛋️ ¿Cómo lo sacas?"),
                "options": [_item("stick", "🪄", "avec un bâton, je le pousse", "with a stick, I push it out", "con un palo, lo empujo"),
                            _item("cry", "😭", "je pleure", "I cry", "lloro"),
                            _item("sofa", "🤪", "je porte le canapé sur ma tête", "I carry the sofa on my head", "cargo el sofá en mi cabeza")],
                "answer": "stick"},
               {"q": L("Tu as plein de blocs à porter dans l'autre pièce 🧱 Comment faire en UN voyage ?", "You have lots of blocks to carry to the other room 🧱 How can you do it in ONE trip?", "Tienes muchos bloques que llevar a la otra habitación 🧱 ¿Cómo lo haces en UN viaje?"),
                "options": [_item("box", "📦", "dans une boîte, tout d'un coup", "in a box, all at once", "en una caja, todo de golpe"),
                            _item("slow", "🐢", "un par un, dix voyages", "one by one, ten trips", "uno a uno, diez viajes"),
                            _item("hide", "🙈", "je les cache", "I hide them", "los escondo")],
                "answer": "box"},
               {"q": L("Le ballon est coincé dans l'arbre 🎈🌳 Que faire ?", "The balloon is stuck in the tree 🎈🌳 What should you do?", "El globo se quedó en el árbol 🎈🌳 ¿Qué haces?"),
                "options": [_item("help", "🙋", "je demande de l'aide à un adulte", "I ask a grown-up for help", "pido ayuda a un adulto"),
                            _item("climb", "🧗", "je grimpe tout seul jusqu'en haut", "I climb to the top all alone", "trepo solo hasta arriba"),
                            _item("rocks", "🪨", "je lance des cailloux", "I throw rocks", "tiro piedras")],
                "answer": "help"}]}),
    _skill(76, "draw-machine", "invention", 5, "⚙️", L("J'invente une machine", "I invent a machine", "Invento una máquina"),
           {"type": "draw", "rounds": 1,
            "intro": L("Invente une MACHINE ! Une machine à bonbons 🍬 à voyager 🚀 ou à ranger ta chambre… Dessine-la avec ton doigt !",
                       "Invent a MACHINE! A candy machine 🍬 a travel machine 🚀 or a room-tidying machine… Draw it with your finger!",
                       "¡Inventa una MÁQUINA! ¡Una máquina de dulces 🍬 de viajar 🚀 o de ordenar tu cuarto… Dibújala con tu dedo!"),
            "palette": ["#e11d48", "#2563eb", "#16a34a", "#eab308", "#9333ea", "#0ea5e9", "#f97316", "#1e293b"]}),
    _skill(77, "inv-nom", "invention", 5, "🏷️", L("Je baptise mon invention", "I name my invention", "Le pongo nombre a mi invento"),
           {"type": "task", "tasks": [
               L("Ta machine a besoin d'un NOM d'inventeur ! Dis-le fort : un nom que personne n'a jamais entendu (exemple : « le Bonbonotron 3000 »). L'adulte valide 🏷️",
                 "Your machine needs an inventor's NAME! Say it out loud — a name nobody has ever heard (example: “the Candytron 3000”). A grown-up validates 🏷️",
                 "¡Tu máquina necesita un NOMBRE de inventora! Dilo fuerte: un nombre que nadie ha oído jamás (ejemplo: «el Dulcetrón 3000»). Un adulto lo valida 🏷️")],
            "rounds": 1,
            "guide": [
               {"emoji": "👀", "label": L("1. Regarde bien ta machine", "1. Look closely at your machine", "1. Mira bien tu máquina")},
               {"emoji": "🔤", "label": L("2. Assemble des sons rigolos", "2. Put funny sounds together", "2. Junta sonidos graciosos")},
               {"emoji": "🏷️", "label": L("3. Dis le nom fort et fier !", "3. Say the name loud and proud!", "3. ¡Di el nombre fuerte y orgullosa!")}]}),
    _skill(78, "inv-pourquoi", "invention", 5, "🤔", L("Le pourquoi des choses", "The why of things", "El porqué de las cosas"),
           {"type": "quiz", "rounds": 3, "scenes": [
               {"q": L("Pourquoi les roues sont-elles rondes ? 🛞", "Why are wheels round? 🛞", "¿Por qué las ruedas son redondas? 🛞"),
                "options": [_item("roll", "😊", "pour rouler tout doux", "to roll smoothly", "para rodar suave"),
                            _item("pretty", "🌸", "parce que c'est joli", "because they are pretty", "porque son bonitas"),
                            _item("square", "🟦", "pour faire carré", "to be square", "para ser cuadradas")],
                "answer": "roll"},
               {"q": L("Pourquoi les maisons ont-elles un toit ? 🏠", "Why do houses have a roof? 🏠", "¿Por qué las casas tienen tejado? 🏠"),
                "options": [_item("dry", "☔", "pour rester au sec quand il pleut", "to stay dry when it rains", "para no mojarnos cuando llueve"),
                            _item("sky", "☁️", "pour coller au ciel", "to stick to the sky", "para pegarse al cielo"),
                            _item("ant", "🐜", "pour cacher le soleil aux fourmis", "to hide the sun from the ants", "para esconder el sol a las hormigas")],
                "answer": "dry"},
               {"q": L("Pourquoi met-on la ceinture en voiture ? 🚗", "Why do we wear a seatbelt in the car? 🚗", "¿Por qué nos ponemos el cinturón en el coche? 🚗"),
                "options": [_item("safe", "🛡️", "elle nous protège", "it keeps us safe", "nos protege"),
                            _item("stuck", "😤", "pour être coincé", "to be stuck", "para estar atrapados"),
                            _item("bow", "🎀", "pour faire joli", "to look pretty", "para estar guapos")],
                "answer": "safe"}]}),
    # ---- 🧩 Fabrique & Assemble (7 plans garantis) — résultat TOUJOURS obtenu ----
    _skill(79, "build-maison", "invention", 2, "🏠", L("Je fabrique une maison", "I build a house", "Fabrico una casa"),
           _build("🏠", L("une maison", "a house", "una casa"),
                  [_item("b-mur", "🧱", "les murs", "the walls", "las paredes"),
                   _item("b-porte", "🚪", "la porte", "the door", "la puerta"),
                   _item("b-fenetre", "🪟", "la fenêtre", "the window", "la ventana"),
                   _item("b-toit", "🔺", "le toit", "the roof", "el tejado")],
                  L("Assemble ta MAISON ! Suis le plan : 1, 2, 3, 4… les pièces s'emboîtent comme par magie ✨",
                    "Build your HOUSE! Follow the plan: 1, 2, 3, 4… the pieces click together like magic ✨",
                    "¡Monta tu CASA! Sigue el plan: 1, 2, 3, 4… las piezas encajan como por magia ✨"),
                  L("Tu as construit une MAISON ! Bravo, architecte ! 🏠",
                    "You built a HOUSE! Well done, architect! 🏠",
                    "¡Has construido una CASA! ¡Bravo, arquitecta! 🏠"))),
    _skill(80, "build-voiture", "invention", 3, "🚗", L("Je fabrique une voiture", "I build a car", "Fabrico un coche"),
           _build("🚗", L("une voiture", "a car", "un coche"),
                  [_item("b-roues", "🛞", "les roues", "the wheels", "las ruedas"),
                   _item("b-caisse", "🟦", "la carrosserie", "the body", "la carrocería"),
                   _item("b-vitre", "🪟", "le pare-brise", "the windshield", "el parabrisas"),
                   _item("b-gyro", "🚨", "le gyrophare", "the siren light", "la sirena")],
                  L("Vroum ! Assemble ta VOITURE : d'abord les roues, puis le reste du plan 🧩",
                    "Vroom! Build your CAR: first the wheels, then the rest of the plan 🧩",
                    "¡Vrum! Monta tu COCHE: primero las ruedas, luego el resto del plan 🧩"),
                  L("Vroum vroum ! Ta VOITURE est prête à rouler ! 🚗",
                    "Vroom vroom! Your CAR is ready to go! 🚗",
                    "¡Vrum vrum! ¡Tu COCHE está listo para rodar! 🚗"))),
    _skill(81, "build-robot", "invention", 3, "🤖", L("Je fabrique un robot", "I build a robot", "Fabrico un robot"),
           _build("🤖", L("un robot", "a robot", "un robot"),
                  [_item("b-pieds", "🦶", "les pieds", "the feet", "los pies"),
                   _item("b-corps", "📦", "le corps", "the body", "el cuerpo"),
                   _item("b-tete", "📺", "la tête", "the head", "la cabeza"),
                   _item("b-antenne", "📡", "l'antenne", "the antenna", "la antena")],
                  L("Bip bip ! Fabrique ton ROBOT pièce par pièce, du bas vers le haut 🤖",
                    "Beep boop! Build your ROBOT piece by piece, from the bottom up 🤖",
                    "¡Bip bip! Fabrica tu ROBOT pieza a pieza, de abajo hacia arriba 🤖"),
                  L("Bip-bip ! Ton ROBOT est vivant ! Tu es un vrai inventeur ! 🤖",
                    "Beep-boop! Your ROBOT is alive! You are a real inventor! 🤖",
                    "¡Bip-bip! ¡Tu ROBOT está vivo! ¡Eres un verdadero inventor! 🤖"))),
    _skill(82, "build-fusee", "invention", 3, "🚀", L("Je fabrique une fusée", "I build a rocket", "Fabrico un cohete"),
           _build("🚀", L("une fusée", "a rocket", "un cohete"),
                  [_item("b-moteur", "🔥", "le moteur", "the engine", "el motor"),
                   _item("b-reservoir", "🍾", "le réservoir", "the tank", "el depósito"),
                   _item("b-hublot", "⭕", "le hublot", "the porthole", "el ojo de buey"),
                   _item("b-pointe", "🔺", "la pointe", "the nose cone", "la punta")],
                  L("Direction les étoiles ! Assemble ta FUSÉE : moteur, réservoir, hublot, pointe 🚀",
                    "To the stars! Build your ROCKET: engine, tank, porthole, nose cone 🚀",
                    "¡Rumbo a las estrellas! Monta tu COHETE: motor, depósito, ojo de buey y punta 🚀"),
                  L("3… 2… 1… DÉCOLLAGE ! Ta FUSÉE file vers les étoiles ! 🚀✨",
                    "3… 2… 1… LIFTOFF! Your ROCKET zooms to the stars! 🚀✨",
                    "¡3… 2… 1… DESPEGUE! ¡Tu COHETE vuela hacia las estrellas! 🚀✨"))),
    _skill(83, "build-fleur", "invention", 3, "🌻", L("Je fais pousser une fleur", "I grow a flower", "Hago crecer una flor"),
           _build("🌻", L("une fleur", "a flower", "una flor"),
                  [_item("b-graine", "🫘", "la graine", "the seed", "la semilla"),
                   _item("b-eau", "💧", "l'eau", "the water", "el agua"),
                   _item("b-tige", "🌱", "la tige", "the stem", "el tallo"),
                   _item("b-feuilles", "🍃", "les feuilles", "the leaves", "las hojas"),
                   _item("b-petale", "🌻", "les pétales", "the petals", "los pétalos")],
                  L("Comme une vraie jardinière ! Fais POUSSER ta fleur : graine, eau, tige, feuilles, pétales 🌻",
                    "Like a real gardener! GROW your flower: seed, water, stem, leaves, petals 🌻",
                    "¡Como una verdadera jardinera! Haz CRECER tu flor: semilla, agua, tallo, hojas, pétalos 🌻"),
                  L("Ta FLEUR a poussé ! Quelle jardinière de génie ! 🌻",
                    "Your FLOWER has grown! What a clever gardener! 🌻",
                    "¡Tu FLOR ha crecido! ¡Qué jardinera tan genial! 🌻"))),
    _skill(84, "build-pont", "invention", 4, "🌉", L("Je fabrique un pont", "I build a bridge", "Fabrico un puente"),
           _build("🌉", L("un pont", "a bridge", "un puente"),
                  [_item("b-pile1", "🧱", "le premier pilier", "the first pillar", "el primer pilar"),
                   _item("b-pile2", "🧱", "le deuxième pilier", "the second pillar", "el segundo pilar"),
                   _item("b-tablier", "📏", "le tablier", "the deck", "el tablero"),
                   _item("b-test", "🚗", "la voiture de test", "the test car", "el coche de prueba")],
                  L("Ingénieure en chef ! Construis ton PONT : deux piliers, le tablier… puis TESTE avec la voiture 🌉",
                    "Chief engineer! Build your BRIDGE: two pillars, the deck… then TEST it with the car 🌉",
                    "¡Ingeniera jefa! Construye tu PUENTE: dos pilares, el tablero… y PRUEBA con el coche 🌉"),
                  L("Ton PONT tient bon ! Les voitures peuvent passer ! 🌉🚗",
                    "Your BRIDGE holds! The cars can cross! 🌉🚗",
                    "¡Tu PUENTE aguanta! ¡Los coches pueden pasar! 🌉🚗"))),
    _skill(85, "build-machine", "invention", 5, "⚙️", L("Je fabrique une machine à bonbons", "I build a candy machine", "Fabrico una máquina de dulces"),
           _build("⚙️", L("une machine à bonbons", "a candy machine", "una máquina de dulces"),
                  [_item("b-boite", "📦", "la boîte", "the box", "la caja"),
                   _item("b-bonbons", "🍬", "les bonbons", "the candy", "los dulces"),
                   _item("b-manivelle", "🌀", "la manivelle", "the crank", "la manivela"),
                   _item("b-trou", "🕳️", "l'ouverture", "the slot", "la salida")],
                  L("Le rêve ! Fabrique ta MACHINE À BONBONS : la boîte, les bonbons, la manivelle, l'ouverture ⚙️",
                    "The dream! Build your CANDY MACHINE: the box, the candy, the crank, the slot ⚙️",
                    "¡El sueño! Fabrica tu MÁQUINA DE DULCES: la caja, los dulces, la manivela, la salida ⚙️"),
                  L("Clic-clac ! Ta MACHINE À BONBONS fonctionne ! Inventrice de génie ! ⚙️🍬",
                    "Click-clack! Your CANDY MACHINE works! Genius inventor! ⚙️🍬",
                    "¡Clic-clac! ¡Tu MÁQUINA DE DULCES funciona! ¡Inventora genial! ⚙️🍬"))),
    # ============ 🇨🇩 LINGALA (6) — première langue bantoue (v2.4) ============
    # Même pédagogie que les pistes EN/ES : le mot lingala EST la cible (le label
    # est identique dans les 3 langues), la consigne suit la langue du profil.
    # La voix du téléphone lit à la française (lingala = langue phonétique :
    # lecture très proche de la prononciation réelle).
    _skill(86, "ln-word-1", "lingala", 1, "🔢", L("Lingala : les nombres", "Lingala: numbers", "Lingala: los números"),
           _tap([_item("ln-moko", "1️⃣", "mokɔ́", "mokɔ́", "mokɔ́"), _item("ln-mibale", "2️⃣", "míbalé", "míbalé", "míbalé"),
                 _item("ln-misato", "3️⃣", "mísáto", "mísáto", "mísáto"), _item("ln-minei", "4️⃣", "mínei", "mínei", "mínei"),
                 _item("ln-mitano", "5️⃣", "mítáno", "mítáno", "mítáno")], rounds=4,
                instruction=L("En lingala (langue bantoue 🇨🇩) ! Touche « {label} » {emoji}",
                              "In Lingala (a Bantu language 🇨🇩)! Touch “{label}” {emoji}",
                              "¡En lingala (lengua bantú 🇨🇩)! Toca «{label}» {emoji}"))),
    _skill(87, "ln-word-2", "lingala", 1, "👨‍👩‍👧", L("Lingala : ma famille", "Lingala: my family", "Lingala: mi familia"),
           _tap([_item("ln-tata", "👨", "tata", "tata", "tata"), _item("ln-mama", "👩", "mama", "mama", "mama"),
                 _item("ln-koko", "👵", "koko", "koko", "koko"), _item("ln-ndeko", "🧒", "ndeko", "ndeko", "ndeko")], rounds=4,
                instruction=L("La famille en lingala ! Touche « {label} » {emoji}",
                              "Family in Lingala! Touch “{label}” {emoji}",
                              "¡La familia en lingala! Toca «{label}» {emoji}"))),
    _skill(88, "ln-word-3", "lingala", 1, "🐶", L("Lingala : les animaux", "Lingala: animals", "Lingala: los animales"),
           _tap([_item("ln-mbwa", "🐶", "mbwa", "mbwa", "mbwa"), _item("ln-mbisi", "🐟", "mbísi", "mbísi", "mbísi"),
                 _item("ln-soso", "🐔", "sóso", "sóso", "sóso"), _item("ln-nyama", "🦌", "nyama", "nyama", "nyama")], rounds=4,
                instruction=L("Les animaux en lingala ! Touche « {label} » {emoji}",
                              "Animals in Lingala! Touch “{label}” {emoji}",
                              "¡Los animales en lingala! Toca «{label}» {emoji}"))),
    _skill(89, "ln-word-4", "lingala", 2, "🖐️", L("Lingala : mon corps", "Lingala: my body", "Lingala: mi cuerpo"),
           _tap([_item("ln-loboko", "🖐️", "lobɔ́kɔ́", "lobɔ́kɔ́", "lobɔ́kɔ́"), _item("ln-miso", "👁️", "míso", "míso", "míso"),
                 _item("ln-matoi", "👂", "matói", "matói", "matói"), _item("ln-lolo", "👄", "lólo", "lólo", "lólo")], rounds=4,
                instruction=L("Mon corps en lingala ! Touche « {label} » {emoji}",
                              "My body in Lingala! Touch “{label}” {emoji}",
                              "¡Mi cuerpo en lingala! Toca «{label}» {emoji}"))),
    _skill(90, "ln-phr-1", "lingala", 2, "👋", L("Lingala : dire bonjour", "Lingala: say hello", "Lingala: saludar"),
           {"type": "chat", "partner": {"emoji": "🦜", "name": "Koko"},
            "lines": [
                {"say_l": "Mbote !", "gesture": "wave",
                 "say_i18n": L("Koko le perroquet te fait un grand signe de la main : il te dit bonjour en lingala ! Répète-lui :",
                               "Koko the parrot waves at you: he says hello in Lingala! Say it back to him:",
                               "Koko el loro te saluda con la mano: ¡te dice hola en lingala! Respóndele:")},
                {"say_l": "Mbote mama !", "gesture": "clap",
                 "say_i18n": L("Et maintenant, dis bonjour à maman ! Répète en t'applaudissant :",
                               "And now, say hello to mummy! Repeat while clapping:",
                               "Y ahora, ¡saluda a mamá! Repite aplaudiendo:")}],
            "cheer": L("Koko danse de joie : tu sais dire bonjour en lingala ! 👋",
                       "Koko dances with joy: you can say hello in Lingala! 👋",
                       "¡Koko baila de alegría: ya sabes saludar en lingala! 👋")}),
    _skill(91, "ln-phr-2", "lingala", 3, "🌙", L("Lingala : merci et bonne nuit", "Lingala: thank you & good night", "Lingala: gracias y buenas noches"),
           {"type": "chat", "partner": {"emoji": "🦜", "name": "Koko"},
            "lines": [
                {"say_l": "Matondo !", "gesture": "bow",
                 "say_i18n": L("Tu offres un fruit à Koko : il s'incline et dit merci. Réponds-lui :",
                               "You offer Koko a fruit: he bows and says thank you. Answer him:",
                               "Le ofreces una fruta a Koko: se inclina y da las gracias. Respóndele:")},
                {"say_l": "Lala salama !", "gesture": "sleep",
                 "say_i18n": L("Koko bâille et ferme les yeux : il te souhaite bonne nuit. Souhaite-lui bonne nuit aussi :",
                               "Koko yawns and closes his eyes: he wishes you good night. Wish him good night too:",
                               "Koko bosteza y cierra los ojos: te desea buenas noches. Deséale buenas noches también:")}],
            "cheer": L("Koko s'endort heureux : quelle belle conversation en lingala ! 🌙",
                       "Koko falls asleep happy: what a lovely conversation in Lingala! 🌙",
                       "Koko se duerme feliz: ¡qué bonita conversación en lingala! 🌙")}),
    # ============ 🇵🇹 PORTUGAIS (6) — même méthode que le lingala (v2.5) ============
    # Tout s'apprend sur BASE DU FRANÇAIS (langue du profil) : la consigne guide
    # en français, le mot portugais est la cible. Conversations animées avec
    # Dina le dauphin (gestes démonstratifs : signe, révérence, dodo).
    _skill(92, "pt-word-1", "portugais", 1, "🔢", L("Portugais : les nombres", "Portuguese: numbers", "Portugués: los números"),
           _tap([_item("pt-um", "1️⃣", "um", "um", "um"), _item("pt-dois", "2️⃣", "dois", "dois", "dois"),
                 _item("pt-tres", "3️⃣", "três", "três", "três"), _item("pt-quatro", "4️⃣", "quatro", "quatro", "quatro"),
                 _item("pt-cinco", "5️⃣", "cinco", "cinco", "cinco")], rounds=4,
                instruction=L("En portugais ! Touche « {label} » {emoji}", "In Portuguese! Touch “{label}” {emoji}", "¡En portugués! Toca «{label}» {emoji}"))),
    _skill(93, "pt-word-2", "portugais", 1, "👨‍👩‍👧", L("Portugais : ma famille", "Portuguese: my family", "Portugués: mi familia"),
           _tap([_item("pt-pai", "👨", "pai", "pai", "pai"), _item("pt-mae", "👩", "mãe", "mãe", "mãe"),
                 _item("pt-avo", "👵", "avó", "avó", "avó"), _item("pt-irmao", "🧒", "irmão", "irmão", "irmão")], rounds=4,
                instruction=L("La famille en portugais ! Touche « {label} » {emoji}", "Family in Portuguese! Touch “{label}” {emoji}", "¡La familia en portugués! Toca «{label}» {emoji}"))),
    _skill(94, "pt-word-3", "portugais", 1, "🐶", L("Portugais : les animaux", "Portuguese: animals", "Portugués: los animales"),
           _tap([_item("pt-cao", "🐶", "cão", "cão", "cão"), _item("pt-peixe", "🐟", "peixe", "peixe", "peixe"),
                 _item("pt-galinha", "🐔", "galinha", "galinha", "galinha"), _item("pt-gato", "🐱", "gato", "gato", "gato")], rounds=4,
                instruction=L("Les animaux en portugais ! Touche « {label} » {emoji}", "Animals in Portuguese! Touch “{label}” {emoji}", "¡Los animales en portugués! Toca «{label}» {emoji}"))),
    _skill(95, "pt-word-4", "portugais", 2, "🖐️", L("Portugais : mon corps", "Portuguese: my body", "Portugués: mi cuerpo"),
           _tap([_item("pt-mao", "🖐️", "mão", "mão", "mão"), _item("pt-olhos", "👁️", "olhos", "olhos", "olhos"),
                 _item("pt-orelhas", "👂", "orelhas", "orelhas", "orelhas"), _item("pt-boca", "👄", "boca", "boca", "boca")], rounds=4,
                instruction=L("Mon corps en portugais ! Touche « {label} » {emoji}", "My body in Portuguese! Touch “{label}” {emoji}", "¡Mi cuerpo en portugués! Toca «{label}» {emoji}"))),
    _skill(96, "pt-chat-1", "portugais", 2, "👋", L("Portugais : dire bonjour", "Portuguese: say hello", "Portugués: saludar"),
           {"type": "chat", "partner": {"emoji": "🐬", "name": "Dina"},
            "lines": [
                {"say_l": "Olá !", "gesture": "wave",
                 "say_i18n": L("Dina le dauphin saute hors de l'eau et te dit bonjour en portugais ! Répète-lui :",
                               "Dina the dolphin jumps out of the water and says hello in Portuguese! Say it back:",
                               "¡Dina el delfín salta fuera del agua y te dice hola en portugués! Respóndele:")},
                {"say_l": "Bom dia !", "gesture": "clap",
                 "say_i18n": L("Le soleil se lève ! Dina te souhaite bonne journée — répète-lui :",
                               "The sun is rising! Dina wishes you a good day — say it back:",
                               "¡Sale el sol! Dina te desea un buen día. Respóndele:")}],
            "cheer": L("Dina fait des pirouettes : tu sais dire bonjour en portugais ! 👋",
                       "Dina spins with joy: you can say hello in Portuguese! 👋",
                       "¡Dina da piruetas: ya sabes saludar en portugués! 👋")}),
    _skill(97, "pt-chat-2", "portugais", 3, "🌙", L("Portugais : merci et bonne nuit", "Portuguese: thank you & good night", "Portugués: gracias y buenas noches"),
           {"type": "chat", "partner": {"emoji": "🐬", "name": "Dina"},
            "lines": [
                {"say_l": "Obrigado !", "gesture": "bow",
                 "say_i18n": L("Tu donnes un poisson à Dina : elle fait une révérence et dit merci. Réponds-lui :",
                               "You give Dina a fish: she bows and says thank you. Answer her:",
                               "Le das un pez a Dina: hace una reverencia y da las gracias. Respóndele:")},
                {"say_l": "Boa noite !", "gesture": "sleep",
                 "say_i18n": L("Dina s'endort sur une vague : souhaite-lui bonne nuit !",
                               "Dina falls asleep on a wave: wish her good night!",
                               "Dina se duerme sobre una ola: ¡deséale buenas noches!")}],
            "cheer": L("Dina dort paisiblement : quelle belle conversation en portugais ! 🌙",
                       "Dina sleeps peacefully: what a lovely conversation in Portuguese! 🌙",
                       "Dina duerme tranquila: ¡qué bonita conversación en portugués! 🌙")}),
    # ============ 🖍️ COLORIAGES (6) — finesse & précision (v2.5) ============
    # Grandes formes à contours épais : l'enfant colorie SOUS le trait (le contour
    # reste toujours net), avec 3 tailles de mine — au doigt ou au stylet.
    _skill(98, "color-maison", "arts", 1, "🏠", L("Coloriage : la maison", "Colouring: the house", "Colorear: la casa"),
           {"type": "coloring", "art": ART_MAISON, "rounds": 1,
            "title": L("Colorie la grande maison ! Reste bien dans les lignes 🖍️",
                       "Colour the big house! Stay nicely inside the lines 🖍️",
                       "¡Colorea la casa grande! Quédate bien dentro de las líneas 🖍️")}),
    _skill(99, "color-fleur", "arts", 1, "🌻", L("Coloriage : la fleur", "Colouring: the flower", "Colorear: la flor"),
           {"type": "coloring", "art": ART_FLEUR, "rounds": 1,
            "title": L("Colorie la belle fleur ! Chaque pétale a sa couleur 🌈",
                       "Colour the pretty flower! Each petal gets its colour 🌈",
                       "¡Colorea la flor bonita! ¡Cada pétalo tiene su color 🌈")}),
    _skill(100, "color-papillon", "arts", 2, "🦋", L("Coloriage : le papillon", "Colouring: the butterfly", "Colorear: la mariposa"),
           {"type": "coloring", "art": ART_PAPILLON, "rounds": 1,
            "title": L("Colorie le papillon ! Les deux ailes pareilles, comme des jumelles 🦋",
                       "Colour the butterfly! Both wings match, like twins 🦋",
                       "¡Colorea la mariposa! Las dos alas iguales, como gemelas 🦋")}),
    _skill(101, "color-voiture", "arts", 2, "🚗", L("Coloriage : la voiture", "Colouring: the car", "Colorear: el coche"),
           {"type": "coloring", "art": ART_VOITURE, "rounds": 1,
            "title": L("Colorie la voiture de course ! Prends ton temps 🏎️",
                       "Colour the racing car! Take your time 🏎️",
                       "¡Colorea el coche de carreras! Tómate tu tiempo 🏎️")}),
    _skill(102, "color-fusee", "arts", 2, "🚀", L("Coloriage : la fusée", "Colouring: the rocket", "Colorear: el cohete"),
           {"type": "coloring", "art": ART_FUSEE, "rounds": 1,
            "title": L("Colorie la fusée avant le décollage ! 🔥",
                       "Colour the rocket before lift-off! 🔥",
                       "¡Colorea el cohete antes del despegue! 🔥")}),
    _skill(103, "color-poisson", "arts", 2, "🐟", L("Coloriage : le poisson", "Colouring: the fish", "Colorear: el pez"),
           {"type": "coloring", "art": ART_POISSON, "rounds": 1,
            "title": L("Colorie le poisson arc-en-ciel ! Glisse doucement ton doigt 🐟",
                       "Colour the rainbow fish! Glide your finger gently 🐟",
                       "¡Colorea el pez arcoíris! Desliza el dedo suavemente 🐟")}),
]

# ------------------------------------------------------------------ prérequis (arêtes)
SKILL_EDGES = [
    # maths — la grande échelle
    ("num-1", "num-2"), ("num-2", "num-3"), ("num-3", "num-4"), ("num-4", "num-5"), ("num-5", "num-6"),
    ("num-3", "num-pair"), ("num-3", "num-suite"),
    ("num-2", "num-add-1"), ("num-add-1", "num-add-2"), ("num-add-1", "num-sub-1"),
    ("num-sub-1", "num-sub-2"), ("num-add-2", "num-mult-1"), ("num-mult-1", "num-mult-2"),
    # formes, arts, animaux
    ("form-1", "form-2"), ("form-2", "form-3"), ("form-3", "form-3d"),
    ("coul-1", "coul-2"), ("coul-2", "art-mix"),
    ("anim-1", "anim-2"), ("anim-2", "anim-3"), ("anim-3", "anim-4"),
    # français — l'escalier de la lecture
    ("lett-1", "lett-2"), ("lett-2", "lett-3"), ("lett-3", "lect-1"),
    ("lect-1", "lect-2"), ("lect-2", "lect-3"),
    ("lett-2", "ecri-1"), ("ecri-1", "ecri-2"),
    # anglais / espagnol : adossés aux fondations correspondantes
    ("coul-1", "en-word-1"), ("anim-1", "en-word-2"), ("num-3", "en-word-3"),
    ("en-phr-1", "en-phr-2"),
    ("coul-1", "es-word-1"), ("anim-1", "es-word-2"), ("num-3", "es-word-3"),
    ("es-phr-1", "es-phr-2"),
    # logique
    ("log-tri", "log-suite"), ("log-tri", "log-taille"),
    # bien-être
    ("bien-emo-1", "bien-resp"), ("bien-pol", "bien-part"),
    # découverte
    ("dec-meteo", "dec-saisons"),
    # 🚀 créer & inventer — la créativité a 2 portes d'entrée SANS prérequis
    # (inv-obs, draw-animal) : elle ne se fait pas attendre. Le reste se chaîne.
    ("inv-obs", "inv-cause"), ("inv-cause", "inv-eau"), ("inv-eau", "inv-aimant"),
    ("log-suite", "inv-graine"), ("log-suite", "inv-plan"),
    ("draw-animal", "inv-histoire"), ("draw-animal", "inv-robot"), ("draw-animal", "inv-boite"),
    ("log-taille", "inv-tour"), ("inv-tour", "inv-pont"),
    ("inv-cause", "inv-probleme"), ("inv-obs", "inv-pourquoi"),
    ("draw-animal", "draw-machine"), ("draw-machine", "inv-nom"),
    # 🧩 fabrique & assemble — enchaînés sur les notions correspondantes
    ("inv-obs", "build-maison"), ("build-maison", "build-voiture"),
    ("draw-animal", "build-robot"), ("inv-cause", "build-fusee"),
    ("inv-graine", "build-fleur"), ("inv-tour", "build-pont"),
    ("draw-machine", "build-machine"),
    # 🇨🇩 lingala — mêmes fondations que les pistes EN/ES
    ("num-3", "ln-word-1"), ("ln-word-1", "ln-word-2"), ("ln-word-2", "ln-word-3"),
    ("bien-corps", "ln-word-4"), ("ln-word-1", "ln-phr-1"), ("ln-phr-1", "ln-phr-2"),
    # 🇵🇹 portugais — mêmes fondations
    ("num-3", "pt-word-1"), ("pt-word-1", "pt-word-2"), ("pt-word-2", "pt-word-3"),
    ("bien-corps", "pt-word-4"), ("pt-word-1", "pt-chat-1"), ("pt-chat-1", "pt-chat-2"),
    # 🖍️ coloriages — adossés aux couleurs
    ("coul-1", "color-maison"), ("color-maison", "color-fleur"), ("color-fleur", "color-papillon"),
    ("color-maison", "color-voiture"), ("color-voiture", "color-fusee"), ("coul-2", "color-poisson"),
]

QUESTIONS: list[dict] = [
    {"id": "q1", "modality": "voice", "prompt": {"text": "Comment tu t'appelles ?", "emoji": "👋"},
     "options": None, "answers": ["jade", "jade queen", "jade mbo", "jade queen mbo"]},
    {"id": "q2", "modality": "image_tap", "prompt": {"text": "Touche la couleur rouge", "emoji": "❤️"},
     "options": [{"id": "red", "label": "rouge", "emoji": "🔴"}, {"id": "blue", "label": "bleu", "emoji": "🔵"},
                 {"id": "green", "label": "vert", "emoji": "🟢"}, {"id": "yellow", "label": "jaune", "emoji": "🟡"}],
     "answers": ["red"]},
    {"id": "q3", "modality": "image_tap", "prompt": {"text": "Touche le chat", "emoji": "🐾"},
     "options": [{"id": "dog", "label": "chien", "emoji": "🐶"}, {"id": "cat", "label": "chat", "emoji": "🐱"},
                 {"id": "rabbit", "label": "lapin", "emoji": "🐰"}, {"id": "duck", "label": "canard", "emoji": "🦆"}],
     "answers": ["cat"]},
    {"id": "q4", "modality": "voice", "prompt": {"text": "Quel âge as-tu ?", "emoji": "🎂"},
     "options": None, "answers": ["3", "trois", "trois ans", "j ai trois ans"]},
    {"id": "q5", "modality": "image_tap", "prompt": {"text": "Touche l'étoile", "emoji": "⭐"},
     "options": [{"id": "star", "label": "étoile", "emoji": "⭐"}, {"id": "heart", "label": "cœur", "emoji": "❤️"},
                 {"id": "dot", "label": "rond", "emoji": "🔵"}, {"id": "tri", "label": "triangle", "emoji": "🔺"}],
     "answers": ["star"]},
]

CONSENTS = ["education", "stockage_donnees", "voix_audio", "rapports_parents"]

# Banques de questions placeholder par LANGUE DU PROFIL (v2.1) : un profil
# anglophone reçoit ses questions en anglais dès sa création. À personnaliser.
QUESTIONS_EN: list[dict] = [
    {"id": "q1", "modality": "voice", "prompt": {"text": "What is your name?", "emoji": "👋"},
     "options": None, "answers": []},  # complété avec le prénom du profil
    {"id": "q2", "modality": "image_tap", "prompt": {"text": "Touch the colour red", "emoji": "❤️"},
     "options": [{"id": "red", "label": "red", "emoji": "🔴"}, {"id": "blue", "label": "blue", "emoji": "🔵"},
                 {"id": "green", "label": "green", "emoji": "🟢"}, {"id": "yellow", "label": "yellow", "emoji": "🟡"}],
     "answers": ["red"]},
    {"id": "q3", "modality": "image_tap", "prompt": {"text": "Touch the cat", "emoji": "🐾"},
     "options": [{"id": "dog", "label": "dog", "emoji": "🐶"}, {"id": "cat", "label": "cat", "emoji": "🐱"},
                 {"id": "rabbit", "label": "rabbit", "emoji": "🐰"}, {"id": "duck", "label": "duck", "emoji": "🦆"}],
     "answers": ["cat"]},
    {"id": "q4", "modality": "voice", "prompt": {"text": "How old are you?", "emoji": "🎂"},
     "options": None, "answers": []},  # complété avec l'âge réel du profil
    {"id": "q5", "modality": "image_tap", "prompt": {"text": "Touch the star", "emoji": "⭐"},
     "options": [{"id": "star", "label": "star", "emoji": "⭐"}, {"id": "heart", "label": "heart", "emoji": "❤️"},
                 {"id": "dot", "label": "dot", "emoji": "🔵"}, {"id": "tri", "label": "triangle", "emoji": "🔺"}],
     "answers": ["star"]},
]

QUESTIONS_ES: list[dict] = [
    {"id": "q1", "modality": "voice", "prompt": {"text": "¿Cómo te llamas?", "emoji": "👋"},
     "options": None, "answers": []},
    {"id": "q2", "modality": "image_tap", "prompt": {"text": "Toca el color rojo", "emoji": "❤️"},
     "options": [{"id": "red", "label": "rojo", "emoji": "🔴"}, {"id": "blue", "label": "azul", "emoji": "🔵"},
                 {"id": "green", "label": "verde", "emoji": "🟢"}, {"id": "yellow", "label": "amarillo", "emoji": "🟡"}],
     "answers": ["red"]},
    {"id": "q3", "modality": "image_tap", "prompt": {"text": "Toca el gato", "emoji": "🐾"},
     "options": [{"id": "dog", "label": "perro", "emoji": "🐶"}, {"id": "cat", "label": "gato", "emoji": "🐱"},
                 {"id": "rabbit", "label": "conejo", "emoji": "🐰"}, {"id": "duck", "label": "pato", "emoji": "🦆"}],
     "answers": ["cat"]},
    {"id": "q4", "modality": "voice", "prompt": {"text": "¿Cuántos años tienes?", "emoji": "🎂"},
     "options": None, "answers": []},
    {"id": "q5", "modality": "image_tap", "prompt": {"text": "Toca la estrella", "emoji": "⭐"},
     "options": [{"id": "star", "label": "estrella", "emoji": "⭐"}, {"id": "heart", "label": "corazón", "emoji": "❤️"},
                 {"id": "dot", "label": "punto", "emoji": "🔵"}, {"id": "tri", "label": "triángulo", "emoji": "🔺"}],
     "answers": ["star"]},
]

QUESTION_BANKS = {"fr": QUESTIONS, "en": QUESTIONS_EN, "es": QUESTIONS_ES}


def seed_skills(con: sqlite3.Connection) -> None:
    """Upsert : installe les nouvelles compétences ET rafraîchit le contenu
    des anciennes (traductions, jeux) — jamais de perte de maîtrise acquise."""
    for s in SKILLS:
        con.execute(
            """INSERT INTO skills (id, ord_i, domain, label, emoji, min_phase, game_json, names_json, level)
               VALUES (?,?,?,?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET
                 ord_i = excluded.ord_i, domain = excluded.domain, label = excluded.label,
                 emoji = excluded.emoji, game_json = excluded.game_json,
                 names_json = excluded.names_json, level = excluded.level""",
            (s["id"], s["ord_i"], s["domain"], s["name"]["fr"], s["emoji"], "PHASE_1",
             dumps(s["game"]), dumps(s["name"]), s["level"]),
        )
    existing_edges = {(r["from_skill"], r["to_skill"]) for r in con.execute("SELECT * FROM skill_edges").fetchall()}
    for a, b in SKILL_EDGES:
        if (a, b) not in existing_edges:
            con.execute("INSERT INTO skill_edges (from_skill, to_skill) VALUES (?,?)", (a, b))


def seed_default_questions(con: sqlite3.Connection, child_id: str,
                           firstname: str | None = None, dob: str | None = None,
                           lang: str = "fr") -> None:
    """Clone les questions placeholder DANS LA LANGUE DU PROFIL (le parent
    les remplace ensuite).
    Bonus : le prénom (q1) et l'âge calculé depuis la date de naissance (q4)
    sont déjà des réponses acceptées — le dispositif marche dès la création."""
    from datetime import date as _date
    from .strings import norm_lang

    bank = QUESTION_BANKS.get(norm_lang(lang), QUESTIONS)
    existing = {r["id"] for r in con.execute(
        "SELECT id FROM identity_questions WHERE child_id = ?", (child_id,)).fetchall()}
    for q in bank:
        qid = f"{child_id}-default-{q['id']}" if child_id != CHILD_ID else q["id"]
        if qid in existing:
            continue
        answers = list(q["answers"])
        if q["id"] == "q1" and firstname:
            answers = [firstname.strip().lower()]                 # le prénom du profil
        elif q["id"] == "q4" and dob:
            try:
                d0 = _date.fromisoformat(dob)
                today = _date.today()
                months = (today.year - d0.year) * 12 + (today.month - d0.month) - (1 if today.day < d0.day else 0)
                answers = [str(months // 12)]                     # l'âge réel en années
            except ValueError:
                answers = list(q["answers"])
        if not answers:                                             # sécurité : jamais vide
            answers = ["parent"]
        con.execute(
            """INSERT INTO identity_questions
               (id, child_id, modality, prompt_json, options_json, answer_hashes_json,
                min_age_months, active, version, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (qid, child_id, q["modality"], dumps(q["prompt"]),
             dumps(q["options"]) if q["options"] else None,
             dumps([hash_answer(a) for a in answers]),
             0, 1, 1, iso()),
        )


def seed_consents(con: sqlite3.Connection) -> None:
    for scope in CONSENTS:
        if q_one(con, "SELECT scope FROM consents WHERE scope = ?", (scope,)) is None:
            con.execute("INSERT INTO consents (scope, version, granted_at, revoked_at) VALUES (?,?,?,NULL)",
                        (scope, 1, iso()))


def seed(con: sqlite3.Connection) -> None:
    """Idempotent : n'insère/rafraîchit que ce qui manque."""
    if q_one(con, "SELECT id FROM children WHERE id = ?", (CHILD_ID,)) is None:
        con.execute(
            "INSERT INTO children (id, display_name, dob, phase, created_at) VALUES (?,?,?,?,?)",
            (CHILD_ID, "Jade", CHILD_DOB, "PHASE_1", iso()),
        )
        audit(con, "system.child_created", child_id=CHILD_ID, payload={"display_name": "Jade"})

    seed_skills(con)
    seed_default_questions(con, CHILD_ID)
    seed_consents(con)
    con.commit()
