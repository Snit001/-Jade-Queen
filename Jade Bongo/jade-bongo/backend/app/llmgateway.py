"""llm-gateway-service — Multi Intelligence avec garde-fous enfant.

Architecture : TOUT appel IA passe ici (routage, cache, filtrage entrée/sortie,
fallback fournisseur). En environnement sans clés API, le gateway fonctionne en
**mode local** : banque de contenus validés (règle absolue : rien d'improvisé
n'atteint un enfant sans validation). Les connecteurs OpenAI / Claude / Gemini /
modèles locaux se branchent derrière la même interface (`chat_safe`).
"""
from __future__ import annotations

import random
import re
from typing import Any

# Banque de répliques validées — ton Phase 1 (3 ans), bienveillant, encourageant.
_ENCOURAGE_SUCCESS = [
    "Bravo {name} ! 🎉", "Génial {name} ! ⭐", "Tu es formidable {name} ! 💪",
    "Super {name} ! Quelle championne ! 🏆", "Yes ! Tu l'as trouvé {name} ! 🌟",
    "Magnifique {name} ! Continue comme ça ! 🚀",
]
_ENCOURAGE_RETRY = [
    "Essaie encore {name} ! 😊", "Presque {name} ! On réessaie ensemble ? 🌟",
    "Ce n'est pas grave {name}, on apprend ! 💛", "Tu vas y arriver {name} ! 🌈",
]
_SESSION_END = [
    "C'est l'heure de la pause {name} ! 🌙 À très vite !",
    "Bravo pour aujourd'hui {name} ! Maintenant, on va jouer dehors ! 🌳",
]

# Garde-fou sortie : tout texte destiné à Jade est nettoyé et borné.
_FORBIDDEN = re.compile(r"(http|www\.|acheter|abonne)", re.IGNORECASE)
_MAX_LEN = 160


def safety_filter(text: str) -> str:
    """Filtre de sortie enfant : coupe tout contenu non conforme."""
    cleaned = text.strip()
    if _FORBIDDEN.search(cleaned) or len(cleaned) > _MAX_LEN:
        return "Bravo ! 🎉"  # repli sûr et validé
    return cleaned


def encourage(kind: str, name: str = "Jade") -> dict[str, Any]:
    """Réplique du Mentor — mode local (contenus validés), filtrée à la sortie."""
    pools = {"success": _ENCOURAGE_SUCCESS, "retry": _ENCOURAGE_RETRY, "session_end": _SESSION_END}
    pool = pools.get(kind, _ENCOURAGE_SUCCESS)
    text = safety_filter(random.choice(pool).format(name=name))
    return {"text": text, "provider": "local-curated", "filtered": True}


def chat_safe(prompt: str, *, age_years: int) -> dict[str, Any]:
    """Point d'entrée unique des appels LLM (production).

    Route selon : coût, qualité, adéquation pédagogique, latence — avec filtrage
    entrée/sortie et fallback fournisseur. Ici : mode local documenté.
    """
    return {
        "text": safety_filter(encourage("success")["text"]),
        "provider": "local-curated",
        "note": "Connecteurs OpenAI/Claude/Gemini : brancher ici (clés via Vault).",
        "age_years": age_years,
    }
