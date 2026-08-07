"""Données initiales (idempotentes) — v2.0 « Plafond ouvert ».

GRAPHE DE COMPÉTENCES : 62 nœuds répartis en 11 domaines, trilingues
(français / English / español), reliés par des prérequis (skill_edges).

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
