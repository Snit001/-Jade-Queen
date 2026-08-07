"use strict";
/* ============================================================
   Jade Bɔngɔ́ — i18n (interfaces en 3 langues : 🇫🇷 🇬🇧 🇪🇸)
   - La langue d'AFFICHAGE de l'appareil (localStorage jb_lang)
   - La langue des COURS de l'enfant est fixée par les parents
     (et l'appareil peut la pousser via ?lang= sur l'API)
   ============================================================ */
(function () {
  const LANGS = ["fr", "en", "es"];
  const FLAGS = { fr: "🇫🇷", en: "🇬🇧", es: "🇪🇸" };

  const DICT = {
    /* ---------------- Application ENFANT ---------------- */
    "kid.hello": { fr: "Bonjour {name} !", en: "Hello {name}!", es: "¡Hola {name}!" },
    "kid.school_mine": { fr: "L'école magique de {name}", en: "{name}'s magic school", es: "La escuela mágica de {name}" },
    "kid.school_kids": { fr: "L'école magique des enfants", en: "The children's magic school", es: "La escuela mágica de los niños" },
    "kid.who_plays": { fr: "Qui va jouer ? Touche ton nom :", en: "Who is playing? Touch your name:", es: "¿Quién juega? Toca tu nombre:" },
    "kid.start": { fr: "▶ Commencer", en: "▶ Start", es: "▶ Empezar" },
    "kid.parent_note": { fr: "💛 Un adulte accompagne l'enfant pendant la session.", en: "💛 A grown-up stays with the child during the session.", es: "💛 Un adulto acompaña al niño durante la sesión." },
    "kid.parents_space": { fr: "👨‍👩‍👧 Espace Parents", en: "👨‍👩‍👧 Parents' Area", es: "👨‍👩‍👧 Zona de Padres" },
    "kid.id_hello": { fr: "Coucou ! C'est bien toi {name} ?", en: "Hi there! Is that really you, {name}?", es: "¡Holaaa! ¿Eres tú, {name}?" },
    "kid.q_progress": { fr: "Question {i} / {n}", en: "Question {i} / {n}", es: "Pregunta {i} / {n}" },
    "kid.mic_hint": { fr: "🎤 Dis ta réponse à voix haute !", en: "🎤 Say your answer out loud!", es: "🎤 ¡Di tu respuesta en voz alta!" },
    "kid.mic_retry": { fr: "Je n'ai pas entendu. Réessaie !", en: "I didn't hear you. Try again!", es: "No te he oído. ¡Inténtalo otra vez!" },
    "kid.adult_validate": { fr: "✅ Un adulte valide ma réponse", en: "✅ A grown-up confirms my answer", es: "✅ Un adulto valida mi respuesta" },
    "kid.bravo": { fr: "Bravo !", en: "Well done!", es: "¡Bravo!" },
    "kid.try_again": { fr: "Essaie encore, tu vas y arriver !", en: "Try again, you can do it!", es: "¡Inténtalo otra vez, tú puedes!" },
    "kid.oops_adult": { fr: "Oh oh, petit souci. Demande à un adulte !", en: "Oh-oh, little problem. Ask a grown-up!", es: "¡Oh oh, pequeño problema! ¡Pregunta a un adulto!" },
    "kid.need_consent": { fr: "Un adulte doit d'abord autoriser les leçons (Espace Parents).", en: "A grown-up must allow the lessons first (Parents' Area).", es: "Un adulto debe autorizar las lecciones primero (Zona de Padres)." },
    "kid.locked_title": { fr: "Petite pause !", en: "Little break!", es: "¡Pequeña pausa!" },
    "kid.locked_body": { fr: "Demande à papa ou maman.", en: "Go and ask mummy or daddy.", es: "Pregunta a papá o mamá." },
    "kid.locked_when": { fr: "On pourra réessayer à {t}.", en: "We can try again at {t}.", es: "Podremos intentarlo a las {t}." },
    "kid.locked_mail": { fr: "💌 Un message a été envoyé aux parents.", en: "💌 A message has been sent to the parents.", es: "💌 Se ha enviado un mensaje a los padres." },
    "kid.daily_title": { fr: "Tu as bien joué !", en: "You played so well!", es: "¡Has jugado muy bien!" },
    "kid.daily_body": { fr: "C'est assez pour aujourd'hui.\nOn retourne jouer dehors ! 🌳", en: "That's enough for today.\nLet's go back to playing outside! 🌳", es: "Es suficiente por hoy.\n¡Volvemos a jugar fuera! 🌳" },
    "kid.daily_hint": { fr: "À demain pour de nouvelles aventures !", en: "See you tomorrow for new adventures!", es: "¡Hasta mañana para nuevas aventuras!" },
    "kid.daily_voice": { fr: "Tu as bien joué ! C'est assez pour aujourd'hui. À demain !", en: "You played so well! That's enough for today. See you tomorrow!", es: "¡Has jugado muy bien! Es suficiente por hoy. ¡Hasta mañana!" },
    "kid.oops": { fr: "Oups !", en: "Oops!", es: "¡Ups!" },
    "kid.restart": { fr: "↩ Recommencer", en: "↩ Start again", es: "↩ Volver a empezar" },
    "kid.veto_title": { fr: "C'est l'heure de la pause !", en: "Break time!", es: "¡Hora de la pausa!" },
    "kid.veto_body": { fr: "Tu as bien travaillé !\nMaintenant on bouge, on joue dehors ! 🌳⚽", en: "Great work!\nNow let's move and play outside! 🌳⚽", es: "¡Has trabajado muy bien!\n¡Ahora a moverse y jugar fuera! 🌳⚽" },
    "kid.veto_voice": { fr: "C'est l'heure de la pause ! Bravo pour aujourd'hui !", en: "Break time! Well done today!", es: "¡Hora de la pausa! ¡Bravo por hoy!" },
    "kid.review": { fr: "🔁 Révision", en: "🔁 Review", es: "🔁 Repaso" },
    "kid.new_lesson": { fr: "✨ Nouvelle leçon", en: "✨ New lesson", es: "✨ Nueva lección" },
    "kid.finish": { fr: "⏹ Fin", en: "⏹ End", es: "⏹ Fin" },
    "kid.count_q": { fr: "Combien tu en vois ? Compte avec moi !", en: "How many can you see? Count with me!", es: "¿Cuántos ves? ¡Cuenta conmigo!" },
    "kid.count_voice": { fr: "Compte avec moi ! Combien tu en vois ?", en: "Count with me! How many can you see?", es: "¡Cuenta conmigo! ¿Cuántos ves?" },
    "kid.count_yes": { fr: "Oui, {n} ! Bravo !", en: "Yes, {n}! Well done!", es: "¡Sí, {n}! ¡Bravo!" },
    "kid.recount": { fr: "Recompte doucement !", en: "Count again slowly!", es: "¡Cuenta de nuevo despacio!" },
    "kid.after_q": { fr: "Quel nombre vient juste après {n} ?", en: "Which number comes right after {n}?", es: "¿Qué número viene justo después de {n}?" },
    "kid.even_q": { fr: "Touche le nombre PAIR !", en: "Touch the EVEN number!", es: "¡Toca el número PAR!" },
    "kid.odd_q": { fr: "Touche le nombre IMPAIR !", en: "Touch the ODD number!", es: "¡Toca el número IMPAR!" },
    "kid.seq_q": { fr: "Qu'est-ce qui vient après ?", en: "What comes next?", es: "¿Qué viene después?" },
    "kid.oddone_q": { fr: "Touche ce qui {hint} !", en: "Touch what {hint}!", es: "¡Toca lo que {hint}!" },
    "kid.same_q": { fr: "Trouve le jumeau exact ! 👯", en: "Find the exact twin! 👯", es: "¡Encuentra el gemelo exacto! 👯" },
    "kid.big_q": { fr: "Touche le plus GRAND !", en: "Touch the BIGGEST one!", es: "¡Toca el MÁS GRANDE!" },
    "kid.small_q": { fr: "Touche le plus PETIT !", en: "Touch the SMALLEST one!", es: "¡Toca el MÁS PEQUEÑO!" },
    "kid.mix_q": { fr: "Quelle couleur font-ils ensemble ?", en: "Which colour do they make together?", es: "¿Qué color forman juntos?" },
    "kid.letter_q": { fr: "Touche la lettre : « {l} »", en: "Touch the letter: “{l}”", es: "Toca la letra: «{l}»" },
    "kid.voice_say": { fr: "{intro} :\n« {t} »", en: "{intro}:\n“{t}”", es: "{intro} :\n«{t}»" },
    "kid.voice_listen": { fr: "🔊 Écoute", en: "🔊 Listen", es: "🔊 Escucha" },
    "kid.voice_mic": { fr: "🎤 À toi !", en: "🎤 Your turn!", es: "🎤 ¡A ti!" },
    "kid.count_to": { fr: "Compte à voix haute jusqu'à {n} ! L'adulte écoute et valide. 🎤", en: "Count out loud up to {n}! A grown-up listens and validates. 🎤", es: "¡Cuenta en voz alta hasta {n}! Un adulto escucha y valida. 🎤" },
    "kid.breath_in": { fr: "Inspire… 🌬️", en: "Breathe in… 🌬️", es: "Inspira… 🌬️" },
    "kid.breath_out": { fr: "Souffle doucement… 🎈", en: "Blow softly… 🎈", es: "Sopla suavemente… 🎈" },
    "kid.breath_done": { fr: "Magnifique respiration !", en: "Beautiful breathing!", es: "¡Qué respiración tan bonita!" },
    "kid.task_listen": { fr: "🔊 Écoute la consigne", en: "🔊 Listen to the instruction", es: "🔊 Escucha la consigna" },
    "kid.task_done": { fr: "C'est fait ! ✅", en: "All done! ✅", es: "¡Hecho! ✅" },
    "kid.task_adult": { fr: "Fais la consigne (sans écran, avec un adulte), puis valide !", en: "Do the activity (off-screen, with a grown-up), then validate!", es: "Haz la actividad (sin pantalla, con un adulto), ¡y valida!" },
    "kid.song_listen": { fr: "Écoute chaque phrase, puis répète !", en: "Listen to each line, then repeat!", es: "¡Escucha cada frase y repite!" },
    "kid.song_done": { fr: "J'ai tout écouté ! 🎵", en: "I listened to everything! 🎵", es: "¡Lo he escuchado todo! 🎵" },
    "kid.song_bravo": { fr: "Quelle belle voix ! Bravo !", en: "What a beautiful voice! Well done!", es: "¡Qué voz tan bonita! ¡Bravo!" },
    "kid.alldone_t1": { fr: "Bravo {name} !", en: "Well done {name}!", es: "¡Bravo {name}!" },
    "kid.alldone_body": { fr: "Tu as tout appris pour le moment !\n{m} / {t} compétences maîtrisées ({p} %)", en: "You've learned everything for now!\n{m} / {t} skills mastered ({p}%)", es: "¡Lo has aprendido todo por ahora!\n{m} / {t} competencias dominadas ({p} %)" },
    "kid.alldone_hint": { fr: "Reviens demain : il y aura des révisions et des surprises ! ⭐", en: "Come back tomorrow: reviews and surprises await! ⭐", es: "¡Vuelve mañana: habrá repasos y sorpresas! ⭐" },
    "kid.alldone_end": { fr: "⏹ Finir la session", en: "⏹ End the session", es: "⏹ Terminar la sesión" },
    "kid.alldone_voice": { fr: "Bravo ! Tu es un vrai champion !", en: "Well done! You're a real champion!", es: "¡Bravo! ¡Eres una verdadera campeona!" },
    "kid.play_together": { fr: "Bonjour {name} ! On va jouer et apprendre ensemble !", en: "Hello {name}! We're going to play and learn together!", es: "¡Hola {name}! ¡Vamos a jugar y aprender juntas!" },
    "kid.break_title": { fr: "🌬️ Pause magique ?", en: "🌬️ Magic break?", es: "🌬️ ¿Pausa mágica?" },
    "kid.break_body": { fr: "On dirait que c'est difficile… On souffle ensemble, puis on continue 💛", en: "This looks a bit hard… Let's blow together, then carry on 💛", es: "Parece difícil… Soplamos juntas y seguimos 💛" },
    "kid.break_continue": { fr: "💪 On continue", en: "💪 Keep going", es: "💪 Seguimos" },
    "kid.break_stop": { fr: "🌙 On fait une pause", en: "🌙 Take a break", es: "🌙 Hacemos una pausa" },
    "kid.accel": { fr: "🚀 Tu vas très vite ! Nouvelle aventure débloquée : {name}", en: "🚀 You're so fast! New adventure unlocked: {name}", es: "🚀 ¡Vas muy rápido! Nueva aventura desbloqueada: {name}" },
    "kid.accel_voice": { fr: "Incroyable ! Tu apprends si vite qu'on passe au niveau suivant !", en: "Incredible! You learn so fast, we're moving to the next level!", es: "¡Increíble! ¡Aprendes tan rápido que pasamos al siguiente nivel!" },

    /* ---------------- Espace PARENTS ---------------- */
    "p.title": { fr: "👨‍👩‍👧 Espace Parents", en: "👨‍👩‍👧 Parents' Area", es: "👨‍👩‍👧 Zona de Padres" },
    "p.sub": { fr: "Jade Bɔngɔ́ — supervision, sécurité, transparence.", en: "Jade Bɔngɔ́ — supervision, safety, transparency.", es: "Jade Bɔngɔ́ — supervisión, seguridad, transparencia." },
    "p.pin": { fr: "Code parent (PIN)", en: "Parent code (PIN)", es: "Código de padres (PIN)" },
    "p.login": { fr: "Se connecter", en: "Sign in", es: "Conectarse" },
    "p.login_err": { fr: "Code incorrect. Réessayez.", en: "Wrong code. Try again.", es: "Código incorrecto. Inténtelo de nuevo." },
    "p.back_app": { fr: "← Retour à l'application de Jade", en: "← Back to Jade's app", es: "← Volver a la aplicación de Jade" },
    "p.command": { fr: "🖥 Command Center", en: "🖥 Command Center", es: "🖥 Centro de Mando" },
    "p.refresh": { fr: "↻ Rafraîchir", en: "↻ Refresh", es: "↻ Actualizar" },
    "p.notif_read": { fr: "✉ Marquer alertes lues", en: "✉ Mark alerts as read", es: "✉ Marcar alertas leídas" },
    "p.unlock": { fr: "🔓 Déverrouiller l'accès", en: "🔓 Unlock access", es: "🔓 Desbloquear acceso" },
    "p.logout": { fr: "Déconnexion", en: "Sign out", es: "Desconexión" },
    "p.c_age": { fr: "📅 Âge & Phase", en: "📅 Age & Phase", es: "📅 Edad y Fase" },
    "p.c_today": { fr: "⏱ Aujourd'hui & Bien-être", en: "⏱ Today & Wellbeing", es: "⏱ Hoy y Bienestar" },
    "p.c_mastery": { fr: "⭐ Compétences", en: "⭐ Skills", es: "⭐ Competencias" },
    "p.c_notif": { fr: "🔔 Alertes", en: "🔔 Alerts", es: "🔔 Alertas" },
    "p.c_consents": { fr: "📜 Consentements RGPD", en: "📜 GDPR Consents", es: "📜 Consentimientos RGPD" },
    "p.c_questions": { fr: "🔐 Questions d'identification", en: "🔐 Identification questions", es: "🔐 Preguntas de identificación" },
    "p.c_audit": { fr: "🧾 Journal d'audit (transparence totale)", en: "🧾 Audit log (full transparency)", es: "🧾 Registro de auditoría (transparencia total)" },
    "p.c_children": { fr: "👶 Enfants", en: "👶 Children", es: "👶 Niños" },
    "p.c_settings": { fr: "🌍 Langue & Profil d'adaptation", en: "🌍 Language & Adaptation profile", es: "🌍 Idioma y Perfil de adaptación" },
    "p.c_eval": { fr: "🚀 Évaluation initiale — « elle sait déjà ! »", en: "🚀 Initial assessment — “she already knows!”", es: "🚀 Evaluación inicial — «¡ya lo sabe!»" },
    "p.age_exact": { fr: "Âge exact", en: "Exact age", es: "Edad exacta" },
    "p.phase": { fr: "Phase", en: "Phase", es: "Fase" },
    "p.session_min": { fr: "Durée max par session (min)", en: "Max session length (min)", es: "Duración máx. por sesión (min)" },
    "p.sessions_day": { fr: "Sessions max par jour", en: "Max sessions per day", es: "Sesiones máx. por día" },
    "p.save_policy": { fr: "💾 Enregistrer la politique", en: "💾 Save policy", es: "💾 Guardar política" },
    "p.screen_time": { fr: "Temps d'écran", en: "Screen time", es: "Tiempo de pantalla" },
    "p.sessions": { fr: "Sessions", en: "Sessions", es: "Sesiones" },
    "p.id_fails": { fr: "Échecs d'identification", en: "Failed identifications", es: "Fallos de identificación" },
    "p.access": { fr: "Statut d'accès", en: "Access status", es: "Estado de acceso" },
    "p.locked_until": { fr: "🔒 Verrouillé jusqu'à {t}", en: "🔒 Locked until {t}", es: "🔒 Bloqueado hasta {t}" },
    "p.free": { fr: "✅ Accès libre", en: "✅ Free access", es: "✅ Acceso libre" },
    "p.global_progress": { fr: "Progression globale", en: "Overall progress", es: "Progreso global" },
    "p.series_review": { fr: "série : {s} · prochaine révision : {d}", en: "streak: {s} · next review: {d}", es: "racha: {s} · próximo repaso: {d}" },
    "p.unread": { fr: "Alertes non lues", en: "Unread alerts", es: "Alertas no leídas" },
    "p.no_alert": { fr: "Aucune alerte récente. Tout va bien 💛", en: "No recent alerts. All is well 💛", es: "Sin alertas recientes. Todo va bien 💛" },
    "p.consent_note": { fr: "Révoquer « Éducation » bloque immédiatement toute nouvelle session (tous les enfants).", en: "Revoking “Education” immediately blocks any new session (all children).", es: "Revocar «Educación» bloquea inmediatamente cualquier sesión nueva (todos los niños)." },
    "p.add_child": { fr: "➕ Ajouter un enfant", en: "➕ Add a child", es: "➕ Añadir un niño" },
    "p.firstname": { fr: "Prénom", en: "First name", es: "Nombre" },
    "p.dob": { fr: "Date de naissance", en: "Date of birth", es: "Fecha de nacimiento" },
    "p.emoji": { fr: "Emoji", en: "Emoji", es: "Emoji" },
    "p.create_profile": { fr: "💾 Créer le profil", en: "💾 Create profile", es: "💾 Crear perfil" },
    "p.profile_created": { fr: "Profil créé : {n} {e} — pensez à personnaliser ses questions ci-dessous.", en: "Profile created: {n} {e} — remember to personalise their questions below.", es: "Perfil creado: {n} {e} — personalice sus preguntas abajo." },
    "p.check_fields": { fr: "Erreur : vérifiez les champs.", en: "Error: check the fields.", es: "Error: revise los campos." },
    "p.q_active": { fr: "Questions actives (de l'enfant)", en: "Active questions (child)", es: "Preguntas activas (del niño)" },
    "p.q_add": { fr: "➕ Ajouter une question", en: "➕ Add a question", es: "➕ Añadir una pregunta" },
    "p.q_text": { fr: "Texte de la question (ex : Comment s'appelle ton doudou ?)", en: "Question text (e.g.: What is your teddy's name?)", es: "Texto de la pregunta (ej.: ¿Cómo se llama tu peluche?)" },
    "p.q_options": { fr: "Options (si image) — une par ligne : id|emoji|label", en: "Options (if image) — one per line: id|emoji|label", es: "Opciones (si imagen) — una por línea: id|emoji|etiqueta" },
    "p.q_answers": { fr: "Réponses acceptées — une par ligne (variantes tolérées)", en: "Accepted answers — one per line (variants tolerated)", es: "Respuestas aceptadas — una por línea (variantes toleradas)" },
    "p.q_add_btn": { fr: "💾 Ajouter (hachées côté serveur)", en: "💾 Add (hashed server-side)", es: "💾 Añadir (cifradas en el servidor)" },
    "p.q_modality_voice": { fr: "🎤 voix", en: "🎤 voice", es: "🎤 voz" },
    "p.q_modality_image": { fr: "👆 image", en: "👆 image", es: "👆 imagen" },
    "p.all_events": { fr: "Tous les événements", en: "All events", es: "Todos los eventos" },
    "p.ev_identity": { fr: "Identifications", en: "Identifications", es: "Identificaciones" },
    "p.ev_learning": { fr: "Apprentissage", en: "Learning", es: "Aprendizaje" },
    "p.ev_wellbeing": { fr: "Bien-être", en: "Wellbeing", es: "Bienestar" },
    "p.ev_session": { fr: "Sessions", en: "Sessions", es: "Sesiones" },
    "p.ev_parent": { fr: "Actions parents", en: "Parent actions", es: "Acciones de padres" },
    "p.ev_gdpr": { fr: "RGPD / consentements", en: "GDPR / consents", es: "RGPD / consentimientos" },
    "p.eval_help": { fr: "Cochez ce que votre enfant sait DÉJÀ faire : le graphe démarre à SON niveau réel (les prérequis sont validés automatiquement). 🔒 = encore à débloquer · ▶ = disponible · ✅ = acquise. Le temps d'écran, lui, ne change jamais.", en: "Tick what your child ALREADY knows: the journey starts at THEIR real level (prerequisites are validated automatically). 🔒 = still locked · ▶ = available · ✅ = mastered. Screen time limits never change.", es: "Marque lo que su hijo YA sabe hacer: el recorrido empieza a SU nivel real (los prerrequisitos se validan automáticamente). 🔒 = bloqueada · ▶ = disponible · ✅ = adquirida. El tiempo de pantalla nunca cambia." },
    "p.eval_knows": { fr: "✔ Acquis", en: "✔ Mastered", es: "✔ Lo sabe" },
    "p.eval_reset": { fr: "↺", en: "↺", es: "↺" },
    "p.eval_done": { fr: "Évaluation enregistrée : {n} compétence(s) validée(s) {auto}.", en: "Assessment saved: {n} skill(s) validated {auto}.", es: "Evaluación guardada: {n} competencia(s) validada(s) {auto}." },
    "p.eval_auto": { fr: "(dont {a} prérequis)", en: "(incl. {a} prerequisites)", es: "(incl. {a} prerrequisitos)" },
    "p.lang_child": { fr: "Langue des cours", en: "Course language", es: "Idioma de los cursos" },
    "p.attention": { fr: "Profil d'attention", en: "Attention profile", es: "Perfil de atención" },
    "p.attnormal": { fr: "🙂 Normale", en: "🙂 Typical", es: "🙂 Normal" },
    "p.attcourte": { fr: "⚡ Courte (sessions −1/3, plus d'encouragements)", en: "⚡ Short (sessions −1/3, more encouragement)", es: "⚡ Corta (sesiones −1/3, más ánimo)" },
    "p.speech": { fr: "Soutien langage (voix lente, consignes répétées)", en: "Speech support (slow voice, repeated instructions)", es: "Apoyo del lenguaje (voz lenta, consignas repetidas)" },
    "p.save_settings": { fr: "💾 Enregistrer les réglages", en: "💾 Save settings", es: "💾 Guardar ajustes" },
    "p.saved": { fr: "Réglages enregistrés ✅", en: "Settings saved ✅", es: "Ajustes guardados ✅" },
    "p.filter_domain": { fr: "Tous les domaines", en: "All domains", es: "Todos los dominios" },
    "p.del_child": { fr: "🗑 Supprimer", en: "🗑 Delete", es: "🗑 Eliminar" },
    "p.del_confirm": { fr: "Supprimer définitivement le profil de {n} ?\nToutes ses données (progression, questions, sessions) seront effacées.", en: "Permanently delete {n}'s profile?\nAll their data (progress, questions, sessions) will be erased.", es: "¿Eliminar definitivamente el perfil de {n}?\nTodos sus datos (progreso, preguntas, sesiones) serán borrados." },
    "p.del_done": { fr: "Profil supprimé : {n}", en: "Profile deleted: {n}", es: "Perfil eliminado: {n}" },
    "p.assist": { fr: "🧭 Assistant de démarrage", en: "🧭 Setup assistant", es: "🧭 Asistente de inicio" },
    "p.a_step1": { fr: "Créer un profil enfant", en: "Create a child profile", es: "Crear un perfil de niño" },
    "p.a_step2": { fr: "Choisir la langue des cours", en: "Choose the course language", es: "Elegir el idioma de los cursos" },
    "p.a_step3": { fr: "Évaluation initiale ({n} compétence(s) validée(s))", en: "Initial assessment ({n} skill(s) validated)", es: "Evaluación inicial ({n} competencia(s) validada(s))" },
    "p.a_step4": { fr: "Personnaliser les questions secrètes ({n} active(s))", en: "Personalise secret questions ({n} active)", es: "Personalizar preguntas secretas ({n} activa(s))" },
    "p.a_step5": { fr: "Première session réalisée", en: "First session completed", es: "Primera sesión realizada" },
    "p.a_open": { fr: "Ouvrir", en: "Open", es: "Abrir" },
    "p.a_ready": { fr: "🎉 Tout est prêt ! Bon apprentissage.", en: "🎉 All set! Happy learning.", es: "🎉 ¡Todo listo! Buen aprendizaje." },
    "p.a_default_q": { fr: "⚠ Remplacez les questions placeholder (exemplaires) par vos vraies questions secrètes.", en: "⚠ Replace the placeholder questions with your real secret questions.", es: "⚠ Sustituya las preguntas de ejemplo por sus verdaderas preguntas secretas." },

    /* ---------------- Command Center ---------------- */
    "c.title": { fr: "🖥 JADE BƆNGƆ́ — COMMAND CENTER", en: "🖥 JADE BƆNGƆ́ — COMMAND CENTER", es: "🖥 JADE BƆNGƆ́ — CENTRO DE MANDO" },
    "c.mission": { fr: "Mission : élever une élite, en douceur et sous contrôle parental.", en: "Mission: raise an elite mind, gently and under parental control.", es: "Misión: formar una élite, con dulzura y bajo control parental." },
    "c.login_hint": { fr: "Connectez-vous depuis l'Espace Parents.", en: "Sign in from the Parents' Area first.", es: "Conéctese primero desde la Zona de Padres." },
  };

  function get() {
    const l = localStorage.getItem("jb_lang") || "fr";
    return LANGS.includes(l) ? l : "fr";
  }
  function set(lang) { localStorage.setItem("jb_lang", lang); }
  function t(key, vars) {
    const lang = get();
    const entry = DICT[key];
    let s = entry ? (entry[lang] || entry.fr || key) : key;
    if (vars) Object.keys(vars).forEach((k) => { s = s.replaceAll("{" + k + "}", vars[k]); });
    return s;
  }
  const TTS_LANG = { fr: "fr-FR", en: "en-US", es: "es-ES" };

  function applyStatic(root) {
    (root || document).querySelectorAll("[data-i18n]").forEach((n) => { n.textContent = t(n.dataset.i18n); });
    document.querySelectorAll("[data-i18n-title]").forEach((n) => { n.title = t(n.dataset.i18nTitle); });
  }

  /* Sélecteur de langue flottant (toutes les pages) */
  function mountSwitcher() {
    if (document.querySelector(".langswitch")) return;
    const box = document.createElement("div");
    box.className = "langswitch";
    LANGS.forEach((l) => {
      const b = document.createElement("button");
      b.textContent = FLAGS[l];
      b.title = l.toUpperCase();
      b.dataset.lang = l;
      if (l === get()) b.classList.add("active");
      b.onclick = () => { set(l); location.reload(); };
      box.appendChild(b);
    });
    document.body.appendChild(box);
  }
  /* Réaligne l'indicateur actif sans recharger (quand le PROFIL impose sa langue) */
  function syncSwitcher() {
    document.querySelectorAll(".langswitch button").forEach((b) => {
      b.classList.toggle("active", b.dataset.lang === get());
    });
  }

  window.I18N = { get, set, t, TTS_LANG, applyStatic, mountSwitcher, syncSwitcher, FLAGS };
  document.addEventListener("DOMContentLoaded", () => { mountSwitcher(); applyStatic(); });
})();
