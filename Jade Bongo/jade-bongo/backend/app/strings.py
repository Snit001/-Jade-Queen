"""Ressources linguistiques du backend — français / English / español.

Toute chaîne affichée à l'enfant ou aux parents passe ici ou dans les
données de compétences (seed). La langue effective = `lang` demandée,
avec repli français (langue maternelle de Jade).
"""
from __future__ import annotations

LANGS = ("fr", "en", "es")
DEFAULT_LANG = "fr"


def norm_lang(lang: str | None) -> str:
    """Valide et normalise une langue demandée (repli fr)."""
    if lang and lang.split("-")[0].lower() in LANGS:
        return lang.split("-")[0].lower()
    return DEFAULT_LANG


DOMAIN_NAMES: dict[str, dict[str, str]] = {
    "maths": {"fr": "Mathématiques", "en": "Mathematics", "es": "Matemáticas"},
    "formes": {"fr": "Formes", "en": "Shapes", "es": "Formas"},
    "arts": {"fr": "Arts & créativité", "en": "Arts & creativity", "es": "Arte y creatividad"},
    "animaux": {"fr": "Animaux & nature", "en": "Animals & nature", "es": "Animales y naturaleza"},
    "francais": {"fr": "Français", "en": "French", "es": "Francés"},
    "anglais": {"fr": "Anglais", "en": "English", "es": "Inglés"},
    "espagnol": {"fr": "Espagnol", "en": "Spanish", "es": "Español"},
    "logique": {"fr": "Logique", "en": "Logic", "es": "Lógica"},
    "bien-etre": {"fr": "Bien-être", "en": "Wellbeing", "es": "Bienestar"},
    "decouverte": {"fr": "Découverte du monde", "en": "World discovery", "es": "Descubrir el mundo"},
    "comptines": {"fr": "Comptines", "en": "Songs", "es": "Canciones"},
    "invention": {"fr": "Créer & Inventer", "en": "Create & Invent", "es": "Crear e Inventar"},
    "lingala": {"fr": "Lingala 🇨🇩", "en": "Lingala 🇨🇩", "es": "Lingala 🇨🇩"},
    "portugais": {"fr": "Portugais 🇵🇹", "en": "Portuguese 🇵🇹", "es": "Portugués 🇵🇹"},
}


def domain_name(domain: str, lang: str) -> str:
    return DOMAIN_NAMES.get(domain, {}).get(lang) or DOMAIN_NAMES.get(domain, {}).get(DEFAULT_LANG, domain)


# Encouragements du Mentor (ton 3-4 ans, bienveillant) — par langue.
ENCOURAGE = {
    "fr": {
        "success": ["Bravo {name} ! 🎉", "Génial {name} ! ⭐", "Tu es formidable {name} ! 💪",
                    "Quelle championne ! 🏆", "Yes {name} ! Tu l'as trouvé ! 🌟", "Magnifique ! Continue comme ça ! 🚀"],
        "retry": ["Essaie encore {name} ! 😊", "Presque ! On réessaie ensemble ? 🌟",
                  "Ce n'est pas grave, on apprend ! 💛", "Tu vas y arriver {name} ! 🌈"],
        "session_end": ["C'est l'heure de la pause {name} ! 🌙 À très vite !",
                        "Bravo pour aujourd'hui {name} ! Maintenant, on va jouer dehors ! 🌳"],
        "acceleration": ["Incroyable {name} ! Tu vas très loin, on monte d'un cran ! 🚀",
                         "Quelle fusée {name} ! Nouvelle aventure débloquée ! ⭐"],
        "suggest_break": ["On dirait que c'est difficile… et si on respirait un coup ensemble ? 🌬️",
                          "Petite pause magique ? On souffle… et on repart ! 💛"],
    },
    "en": {
        "success": ["Well done {name}! 🎉", "Great job {name}! ⭐", "You're amazing {name}! 💪",
                    "What a champion! 🏆", "Yes {name}! You found it! 🌟", "Wonderful! Keep going! 🚀"],
        "retry": ["Try again {name}! 😊", "Almost! Shall we try together? 🌟",
                  "It's okay, we're learning! 💛", "You can do it {name}! 🌈"],
        "session_end": ["Time for a break {name}! 🌙 See you soon!",
                        "Well done today {name}! Now let's go play outside! 🌳"],
        "acceleration": ["Incredible {name}! Level up — you're flying! 🚀",
                         "What a rocket {name}! New adventure unlocked! ⭐"],
        "suggest_break": ["It looks a bit hard… shall we breathe together? 🌬️",
                          "A little magic break? We blow… and off we go again! 💛"],
    },
    "es": {
        "success": ["¡Bravo {name}! 🎉", "¡Genial {name}! ⭐", "¡Eres increíble {name}! 💪",
                    "¡Qué campeona! 🏆", "¡Sí {name}! ¡Lo encontraste! 🌟", "¡Magnífico! ¡Sigue así! 🚀"],
        "retry": ["¡Inténtalo otra vez {name}! 😊", "¡Casi! ¿Lo intentamos juntas? 🌟",
                  "No pasa nada, ¡estamos aprendiendo! 💛", "¡Tú puedes {name}! 🌈"],
        "session_end": ["¡Hora del descanso {name}! 🌙 ¡Hasta pronto!",
                        "¡Bravo por hoy {name}! ¡Ahora a jugar fuera! 🌳"],
        "acceleration": ["¡Increíble {name}! ¡Subimos de nivel! 🚀",
                         "¡Qué cohete {name}! ¡Nueva aventura desbloqueada! ⭐"],
        "suggest_break": ["Parece difícil… ¿respiramos un poco juntas? 🌬️",
                          "¿Una pequeña pausa mágica? Soplamos… ¡y seguimos! 💛"],
    },
}

# Libellés de statut de compétence (arbre parent).
STATUS_LABELS = {
    "mastered": {"fr": "Acquise ✅", "en": "Mastered ✅", "es": "Adquirida ✅"},
    "unlocked": {"fr": "Disponible ▶", "en": "Unlocked ▶", "es": "Disponible ▶"},
    "locked": {"fr": "À débloquer 🔒", "en": "Locked 🔒", "es": "Bloqueada 🔒"},
}
