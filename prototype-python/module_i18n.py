"""
The international protection & displacement module - every item after the
forced-to-flee question - in the six UN official languages, so the Apply card
and the full questionnaire on questions.html follow the same Language buttons
as the forced-to-flee form does.

SAME STATUS AS question_i18n.py: THESE ARE DRAFTS. Translating an instrument
is a specialist job (TRAPD, forward-and-back with reconciliation); cognitive
testing on an unreviewed translation tests the translation, not the question.
They exist so a task team starts from a recorded draft instead of an ad hoc
one in the field.

What is NOT translated: item codes (FrcFl, Apply, Legal ...) - they are
variable names and appear identically in every version; and the localised
office and document names - those come from protection_context.json in the
country's own language where the source printed one.

Terminology decisions carried over from question_i18n.py: "flee" is rendered
as leaving under duress (contraint de quitter / obligado a abandonar /
اضطررت إلى مغادرة / вынужденно покидать / 被迫离开), not fleeing in panic.
"International protection" uses the established UNHCR term in each language
(protection internationale / protección internacional / الحماية الدولية /
международная защита / 国际保护). "Refugee status" likewise.
"""

M = {
# --------------------------------------------------------------------- EN
"en": {
 "ui": {
  "skip_fleeloc1": "Ask if FleeLoc = Survey country",
  "oos_idp": "&rarr; out of scope &mdash; the home fled was in another country",
  "notidp_apply": "&rarr; not counted as an IDP (repatriated refugee or asylum seeker)",
  "notidp_m12": "&rarr; established residence abroad &mdash; not counted as an IDP",
  "note_apply_idp": "In the IDP-only version this is a screening question: anyone who sought international protection abroad is classified as a repatriated refugee or asylum seeker, not an IDP, and the module ends there.",
  "note_fleecross_idp": "Asked to exclude people who established residence abroad: under IRIS a person remains an IDP only if they never moved to another country, or stayed abroad for less than 12 months and did not seek protection there.",
  "note_fleecross_ref": "A respondent who fled a home in {country} and never moved to another country is internally displaced &mdash; out of scope for refugee identification; the module can end there.",
  "eg": "e.g.", "cust_to": "e.g. to {list}", "cust_other": "e.g. {list}", "cust_adm": "e.g. {list}",
  "cust_dtm": "Among displaced people IOM DTM interviewed in {c}, reasons given outside the codes above: {list}",
  "cust_docs": "In {c}: {list}",
  "formal": "formal name: {n}",
  "ask_all": "Ask all",
  "yes": "Yes", "no": "No",
  "goto": "&rarr; go to {x}",
  "specify": "[SPECIFY]",
  "open": "Open response &mdash; village or town, county, province.",
  "loc_two": "Localisation example &mdash; two versions",
  "verA": "Version <b>A</b> &middot; the office &middot; as in the paper",
  "verB": "Version <b>B</b> &middot; the document &middot; proposed after the paper",
  "in_local": "<i>{n}</i> in local language",
  "called": "commonly called &ldquo;{n}&rdquo;",
  "also_seen": "Also seen: {n}",
  "on_recog": "On recognition, this becomes: {n}",
  "noA": "Cannot be worded here &mdash; no office a respondent would have gone to is named.",
  "noB": "Cannot be worded here &mdash; no document, card or certificate is named for this country.",
  "looks": "What it looks like",
  "instr": "<b>Interviewer instructions.</b> Read the question as written, then <b>one</b> example. "
           "Version A names where the claim is lodged &mdash; never the body that decides it. "
           "Version B names the document the claim produces, which respondents often recall "
           "better than the office, and which the Legal item later asks about; where a specimen "
           "is shown, it can be used as a show card. The stem and the response options never "
           "change between countries.",
  "instr_misfire": "In this country the office framing is known to misfire (see the note below), so prefer Version B.",
  "no_example": "No drafted localisation example for this country yet &mdash; the question is asked as written, without an example.",
  "none_proc": "No registration or international-protection procedure exists in this country &mdash; the Apply / IntApply / Outcome sequence does not apply here.",
  "no_example_short": "&mdash; no localisation example can be drafted for this country.",
 },
 "apply": {
  "skip": "Ask if any valid reason to flee was coded and FleeCross = Yes",
  "stem": "Did you ever apply for international protection, such as refugee status?",
  "probe_office": "For example, did you go to an office like {name} to register?",
  "probe_doc": "For example, did you apply for a document like {name}?",
 },
 "intapply": {
  "skip": "Ask if Apply = No",
  "stem": "Did you ever plan to apply for international protection, such as refugee status?",
 },
 "outcome": {
  "skip": "Ask if Apply = Yes",
  "stem": "What was the outcome of your application for international protection?",
  "opts": ["Refugee status granted", "Refugee status denied",
           "Outcome still being decided", "I withdrew my application"],
 },
 "frcoth": {
  "skip": "Ask if FrcFl = &ldquo;a different threat&rdquo;",
  "stem": "What was the other threat to your safety that meant you had to leave a home?",
  "note": "Open response, coded by the enumerator or in office &mdash; not read aloud. "
          "Localisation of examples and of which answers count as valid is permitted; "
          "the paper's own back-coding list:",
  "list": [
   ["Risk of conscription or forced recruitment by armed groups",
    "recode into armed conflict/widespread violence at FrcFl"],
   ["Eviction", "mass evictions for infrastructure go to FrcFl; one-off evictions by landlords stay here"],
   ["Fear of violent crime", None],
   ["Political insecurity, public disorder or civil unrest", None],
   ["Food insecurity or famine", None],
   ["Lack of medical facilities", None],
   ["Family violence, forced marriage or domestic abuse", None],
   ["Lack of employment opportunities", None],
   ["Lack of local infrastructure e.g. schools, housing, sewage, electricity", None],
   ["Marital, relationship or family breakdown", None],
   ["Other reason (specify)", None],
  ],
 },
 "fleeloc": {
  "skip": "Ask if any valid reason to flee was coded at FrcFl or FrcOth",
  "stem": "In which country was the home you had to flee from?",
  "opts": ["Survey country", "Other country [SPECIFY]"],
 },
 "idploc": {
  "skip": "Ask if FleeLoc = Survey country",
  "stem": "Tell me where you were living right before you were forced to flee home for the first time.",
 },
 "locliv": {
  "skip": "Ask if any valid reason to flee was coded",
  "stem": "Before you fled this home, had you always lived in {country}?",
 },
 "citloc": {
  "skip": "Ask if LocLiv = No",
  "stem": "Were you a citizen of {country} when you fled your home there?",
 },
 "fleecross": {
  "skip": "Ask if any valid reason to flee was coded",
  "stem": "After you fled your home did you ever move to another country, even if this was only temporary?",
 },
 "idppost": {
  "skip": "Ask if FleeLoc = Survey country and FleeCross = No",
  "stem": "When you first fled your home, where did you move to first?",
  "note": "Open response &mdash; village or town, county, province. Do not include short stays or stopovers.",
 },
 "mnths12": {
  "skip": "Ask if FleeCross = Yes",
  "stem": "How long did you stay abroad after fleeing your home?",
  "opts": ["Less than 12 months", "12 months or more"],
 },
 "legal": {
  "skip": "Ask all",
  "stem": "Thinking about your current situation, what is the main document that allows you to stay in {country}?",
  "note": "Higher-order categories are fixed; the response options under each are localisable "
          "to the country's own visa/status categories; the protected-status lines carry this country's document names where they are known.",
  "cats": [
   ["No documents", ["No documents"]],
   ["Visas", ["Tourist visa", "Student visa", "Work visa", "Humanitarian visa", "Family visa", "Other visa (specify)"]],
   ["International agreements", ["Regional free movement agreement (e.g. Mercosur, EU, SADC, EAC, ECOWAS)"]],
   ["Permanent residency and citizenship", ["Permanent resident document", "{country} passport",
                                            "Other document certifying {country} citizenship"]],
   ["Protected status", ["Asylum applicant document", "Refugee", "Recognized stateless person document",
                         "Complementary and subsidiary protection", "Temporary protection"]],
   ["Enrolment document", ["Enrolment document"]],
   ["Other", ["Other (specify)"]],
  ],
 },
},
# --------------------------------------------------------------------- FR
"fr": {
 "ui": {
  "skip_fleeloc1": "Poser si FleeLoc = Pays de l'enquête",
  "oos_idp": "&rarr; hors champ &mdash; le domicile quitté se trouvait dans un autre pays",
  "notidp_apply": "&rarr; non compté comme PDI (réfugié rapatrié ou demandeur d'asile)",
  "notidp_m12": "&rarr; résidence établie à l'étranger &mdash; non compté comme PDI",
  "note_apply_idp": "Dans la version PDI uniquement, c'est une question de filtrage&nbsp;: toute personne ayant demandé une protection internationale à l'étranger est classée réfugié rapatrié ou demandeur d'asile, non PDI, et le module s'arrête là.",
  "note_fleecross_idp": "Posée pour exclure les personnes ayant établi leur résidence à l'étranger&nbsp;: selon l'IRIS, une personne reste PDI seulement si elle n'est jamais partie dans un autre pays, ou y est restée moins de 12 mois sans y demander de protection.",
  "note_fleecross_ref": "Une personne qui a quitté un domicile situé {country} sans jamais partir dans un autre pays est déplacée interne &mdash; hors champ pour l'identification des réfugiés&nbsp;; le module peut s'arrêter là.",
  "eg": "p. ex.", "cust_to": "p. ex. vers {list}", "cust_other": "p. ex. {list}", "cust_adm": "p. ex. {list}",
  "cust_dtm": "Parmi les personnes déplacées interrogées par l'OIM (DTM) en {c}, motifs cités hors des codes ci-dessus&nbsp;: {list}",
  "cust_docs": "En {c}&nbsp;: {list}",
  "formal": "nom officiel&nbsp;: {n}",
  "ask_all": "Poser à tous",
  "yes": "Oui", "no": "Non",
  "goto": "&rarr; aller à {x}",
  "specify": "[PRÉCISER]",
  "open": "Réponse libre &mdash; village ou ville, département, province.",
  "loc_two": "Exemple de localisation &mdash; deux versions",
  "verA": "Version <b>A</b> &middot; le bureau &middot; telle que dans le document",
  "verB": "Version <b>B</b> &middot; le document &middot; proposée après le document",
  "in_local": "<i>{n}</i> dans la langue locale",
  "called": "communément appelé &laquo;&nbsp;{n}&nbsp;&raquo;",
  "also_seen": "Également relevé&nbsp;: {n}",
  "on_recog": "Après reconnaissance, devient&nbsp;: {n}",
  "noA": "Ne peut pas être formulée ici &mdash; aucun bureau où un répondant se serait rendu n'est nommé.",
  "noB": "Ne peut pas être formulée ici &mdash; aucun document, carte ou certificat n'est nommé pour ce pays.",
  "looks": "À quoi cela ressemble",
  "instr": "<b>Consignes à l'enquêteur.</b> Lire la question telle quelle, puis <b>un seul</b> exemple. "
           "La version A nomme le lieu où la demande est déposée &mdash; jamais l'organe qui la tranche. "
           "La version B nomme le document que produit la demande, dont les répondants se souviennent "
           "souvent mieux que du bureau, et sur lequel porte ensuite l'item Legal&nbsp;; lorsqu'un spécimen "
           "est affiché, il peut servir de carte-réponse. La question et les modalités de réponse ne "
           "changent jamais d'un pays à l'autre.",
  "instr_misfire": "Dans ce pays, la formulation par le bureau est connue pour induire en erreur (voir la note ci-dessous)&nbsp;: préférer la version B.",
  "no_example": "Aucun exemple de localisation n'a encore été rédigé pour ce pays &mdash; la question est posée telle quelle, sans exemple.",
  "none_proc": "Il n'existe dans ce pays aucune procédure d'enregistrement ni de protection internationale &mdash; la séquence Apply / IntApply / Outcome ne s'applique pas ici.",
  "no_example_short": "&mdash; aucun exemple de localisation ne peut être rédigé pour ce pays.",
 },
 "apply": {
  "skip": "Poser si un motif valable de départ a été codé et FleeCross = Oui",
  "stem": "Avez-vous déjà demandé une protection internationale, par exemple le statut de réfugié&nbsp;?",
  "probe_office": "Par exemple, êtes-vous allé(e) dans un bureau comme {name} pour vous faire enregistrer&nbsp;?",
  "probe_doc": "Par exemple, avez-vous demandé un document comme {name}&nbsp;?",
 },
 "intapply": {
  "skip": "Poser si Apply = Non",
  "stem": "Avez-vous déjà eu l'intention de demander une protection internationale, par exemple le statut de réfugié&nbsp;?",
 },
 "outcome": {
  "skip": "Poser si Apply = Oui",
  "stem": "Quelle a été l'issue de votre demande de protection internationale&nbsp;?",
  "opts": ["Statut de réfugié accordé", "Statut de réfugié refusé",
           "Décision encore en attente", "J'ai retiré ma demande"],
 },
 "frcoth": {
  "skip": "Poser si FrcFl = &laquo;&nbsp;une autre menace&nbsp;&raquo;",
  "stem": "Quelle était l'autre menace pour votre sécurité qui vous a obligé(e) à quitter un domicile&nbsp;?",
  "note": "Réponse libre, codée par l'enquêteur ou au bureau &mdash; ne pas lire à voix haute. "
          "La localisation des exemples et des réponses considérées comme valables est permise&nbsp;; "
          "liste de recodage du document&nbsp;:",
  "list": [
   ["Risque de conscription ou de recrutement forcé par des groupes armés",
    "recoder en conflit armé / violence généralisée à FrcFl"],
   ["Expulsion", "les expulsions massives liées à des infrastructures vont à FrcFl&nbsp;; les expulsions individuelles par un propriétaire restent ici"],
   ["Peur de la criminalité violente", None],
   ["Insécurité politique, troubles à l'ordre public ou agitation civile", None],
   ["Insécurité alimentaire ou famine", None],
   ["Absence de structures médicales", None],
   ["Violence familiale, mariage forcé ou violence domestique", None],
   ["Absence de possibilités d'emploi", None],
   ["Absence d'infrastructures locales, p. ex. écoles, logement, assainissement, électricité", None],
   ["Rupture conjugale, sentimentale ou familiale", None],
   ["Autre raison (préciser)", None],
  ],
 },
 "fleeloc": {
  "skip": "Poser si un motif valable de départ a été codé à FrcFl ou FrcOth",
  "stem": "Dans quel pays se trouvait le domicile que vous avez dû quitter&nbsp;?",
  "opts": ["Pays de l'enquête", "Autre pays [PRÉCISER]"],
 },
 "idploc": {
  "skip": "Poser si FleeLoc = Pays de l'enquête",
  "stem": "Dites-moi où vous viviez juste avant d'être contraint(e) de quitter votre domicile pour la première fois.",
 },
 "locliv": {
  "skip": "Poser si un motif valable de départ a été codé",
  "stem": "Avant de quitter ce domicile, aviez-vous toujours vécu {country}&nbsp;?",
 },
 "citloc": {
  "skip": "Poser si LocLiv = Non",
  "stem": "Étiez-vous citoyen(ne) de {country} lorsque vous avez quitté votre domicile là-bas&nbsp;?",
 },
 "fleecross": {
  "skip": "Poser si un motif valable de départ a été codé",
  "stem": "Après avoir quitté votre domicile, êtes-vous allé(e) vivre dans un autre pays, même temporairement&nbsp;?",
 },
 "idppost": {
  "skip": "Poser si FleeLoc = Pays de l'enquête et FleeCross = Non",
  "stem": "Lorsque vous avez quitté votre domicile pour la première fois, où êtes-vous allé(e) en premier&nbsp;?",
  "note": "Réponse libre &mdash; village ou ville, département, province. Ne pas compter les courts séjours ni les étapes.",
 },
 "mnths12": {
  "skip": "Poser si FleeCross = Oui",
  "stem": "Combien de temps êtes-vous resté(e) à l'étranger après avoir quitté votre domicile&nbsp;?",
  "opts": ["Moins de 12 mois", "12 mois ou plus"],
 },
 "legal": {
  "skip": "Poser à tous",
  "stem": "En pensant à votre situation actuelle, quel est le principal document qui vous permet de rester {country}&nbsp;?",
  "note": "Les catégories de niveau supérieur sont fixes&nbsp;; les modalités sous chacune peuvent être "
          "adaptées aux catégories de visa et de statut du pays&nbsp;; les lignes du statut protégé portent les noms des documents de ce pays lorsqu'ils sont connus.",
  "cats": [
   ["Aucun document", ["Aucun document"]],
   ["Visas", ["Visa de tourisme", "Visa d'études", "Visa de travail", "Visa humanitaire", "Visa familial", "Autre visa (préciser)"]],
   ["Accords internationaux", ["Accord régional de libre circulation (p. ex. Mercosur, UE, SADC, CAE, CEDEAO)"]],
   ["Résidence permanente et citoyenneté", ["Titre de résident permanent", "Passeport de {country}",
                                            "Autre document attestant la citoyenneté de {country}"]],
   ["Statut protégé", ["Document de demandeur d'asile", "Réfugié", "Document de personne apatride reconnue",
                       "Protection complémentaire et subsidiaire", "Protection temporaire"]],
   ["Document d'enregistrement", ["Document d'enregistrement"]],
   ["Autre", ["Autre (préciser)"]],
  ],
 },
},
# --------------------------------------------------------------------- ES
"es": {
 "ui": {
  "skip_fleeloc1": "Preguntar si FleeLoc = País de la encuesta",
  "oos_idp": "&rarr; fuera de alcance &mdash; el hogar abandonado estaba en otro país",
  "notidp_apply": "&rarr; no se cuenta como desplazado interno (refugiado repatriado o solicitante de asilo)",
  "notidp_m12": "&rarr; estableció residencia en el extranjero &mdash; no se cuenta como desplazado interno",
  "note_apply_idp": "En la versión solo de desplazados internos esta es una pregunta de filtro: quien solicitó protección internacional en el extranjero se clasifica como refugiado repatriado o solicitante de asilo, no como desplazado interno, y el módulo termina ahí.",
  "note_fleecross_idp": "Se pregunta para excluir a quienes establecieron residencia en el extranjero: según las IRIS, una persona sigue siendo desplazada interna solo si nunca se trasladó a otro país, o permaneció fuera menos de 12 meses sin solicitar protección allí.",
  "note_fleecross_ref": "Quien abandonó un hogar en {country} y nunca se trasladó a otro país es desplazado interno &mdash; fuera de alcance para la identificación de refugiados; el módulo puede terminar ahí.",
  "eg": "p. ej.", "cust_to": "p. ej. a {list}", "cust_other": "p. ej. {list}", "cust_adm": "p. ej. {list}",
  "cust_dtm": "Entre las personas desplazadas entrevistadas por la OIM (DTM) en {c}, motivos citados fuera de los códigos anteriores: {list}",
  "cust_docs": "En {c}: {list}",
  "formal": "nombre oficial: {n}",
  "ask_all": "Preguntar a todos",
  "yes": "Sí", "no": "No",
  "goto": "&rarr; pasar a {x}",
  "specify": "[ESPECIFICAR]",
  "open": "Respuesta abierta &mdash; aldea o ciudad, municipio, provincia.",
  "loc_two": "Ejemplo de localización &mdash; dos versiones",
  "verA": "Versión <b>A</b> &middot; la oficina &middot; como en el documento",
  "verB": "Versión <b>B</b> &middot; el documento &middot; propuesta posterior al documento",
  "in_local": "<i>{n}</i> en el idioma local",
  "called": "conocido comúnmente como &laquo;{n}&raquo;",
  "also_seen": "También registrado: {n}",
  "on_recog": "Tras el reconocimiento pasa a ser: {n}",
  "noA": "No puede formularse aquí &mdash; no se nombra ninguna oficina a la que un encuestado hubiera acudido.",
  "noB": "No puede formularse aquí &mdash; no se nombra ningún documento, carné o certificado para este país.",
  "looks": "Cómo es el documento",
  "instr": "<b>Instrucciones para el entrevistador.</b> Lea la pregunta tal como está escrita y después "
           "<b>un solo</b> ejemplo. La versión A nombra el lugar donde se presenta la solicitud &mdash; nunca "
           "el órgano que la decide. La versión B nombra el documento que produce la solicitud, que los "
           "encuestados suelen recordar mejor que la oficina y sobre el que pregunta después el ítem Legal; "
           "cuando se muestra un espécimen, puede usarse como tarjeta. La pregunta y las opciones de "
           "respuesta nunca cambian de un país a otro.",
  "instr_misfire": "En este país se sabe que la formulación por oficina induce a error (véase la nota más abajo), así que es preferible la versión B.",
  "no_example": "Todavía no hay un ejemplo de localización redactado para este país &mdash; la pregunta se hace tal como está escrita, sin ejemplo.",
  "none_proc": "En este país no existe ningún procedimiento de registro ni de protección internacional &mdash; la secuencia Apply / IntApply / Outcome no se aplica aquí.",
  "no_example_short": "&mdash; no puede redactarse ningún ejemplo de localización para este país.",
 },
 "apply": {
  "skip": "Preguntar si se codificó un motivo válido de huida y FleeCross = Sí",
  "stem": "¿Alguna vez solicitó protección internacional, por ejemplo la condición de refugiado?",
  "probe_office": "Por ejemplo, ¿acudió a una oficina como {name} para registrarse?",
  "probe_doc": "Por ejemplo, ¿solicitó un documento como {name}?",
 },
 "intapply": {
  "skip": "Preguntar si Apply = No",
  "stem": "¿Alguna vez tuvo la intención de solicitar protección internacional, por ejemplo la condición de refugiado?",
 },
 "outcome": {
  "skip": "Preguntar si Apply = Sí",
  "stem": "¿Cuál fue el resultado de su solicitud de protección internacional?",
  "opts": ["Se concedió la condición de refugiado", "Se denegó la condición de refugiado",
           "Todavía está pendiente de decisión", "Retiré mi solicitud"],
 },
 "frcoth": {
  "skip": "Preguntar si FrcFl = &laquo;una amenaza distinta&raquo;",
  "stem": "¿Cuál fue la otra amenaza para su seguridad que le obligó a abandonar un hogar?",
  "note": "Respuesta abierta, codificada por el encuestador o en oficina &mdash; no se lee en voz alta. "
          "Se permite localizar los ejemplos y decidir qué respuestas se consideran válidas; "
          "lista de recodificación del propio documento:",
  "list": [
   ["Riesgo de reclutamiento forzoso o conscripción por grupos armados",
    "recodificar en conflicto armado / violencia generalizada en FrcFl"],
   ["Desalojo", "los desalojos masivos por obras de infraestructura van a FrcFl; los desalojos individuales por un arrendador se quedan aquí"],
   ["Miedo a la delincuencia violenta", None],
   ["Inseguridad política, desorden público o disturbios civiles", None],
   ["Inseguridad alimentaria o hambruna", None],
   ["Falta de servicios médicos", None],
   ["Violencia familiar, matrimonio forzado o violencia doméstica", None],
   ["Falta de oportunidades de empleo", None],
   ["Falta de infraestructura local, p. ej. escuelas, vivienda, saneamiento, electricidad", None],
   ["Ruptura conyugal, de pareja o familiar", None],
   ["Otro motivo (especificar)", None],
  ],
 },
 "fleeloc": {
  "skip": "Preguntar si se codificó un motivo válido de huida en FrcFl o FrcOth",
  "stem": "¿En qué país estaba el hogar que tuvo que abandonar?",
  "opts": ["País de la encuesta", "Otro país [ESPECIFICAR]"],
 },
 "idploc": {
  "skip": "Preguntar si FleeLoc = País de la encuesta",
  "stem": "Dígame dónde vivía justo antes de verse obligado a abandonar su hogar por primera vez.",
 },
 "locliv": {
  "skip": "Preguntar si se codificó un motivo válido de huida",
  "stem": "Antes de abandonar ese hogar, ¿había vivido siempre en {country}?",
 },
 "citloc": {
  "skip": "Preguntar si LocLiv = No",
  "stem": "¿Era ciudadano de {country} cuando abandonó su hogar allí?",
 },
 "fleecross": {
  "skip": "Preguntar si se codificó un motivo válido de huida",
  "stem": "Después de abandonar su hogar, ¿se trasladó alguna vez a otro país, aunque fuera de forma temporal?",
 },
 "idppost": {
  "skip": "Preguntar si FleeLoc = País de la encuesta y FleeCross = No",
  "stem": "Cuando abandonó su hogar por primera vez, ¿adónde se trasladó primero?",
  "note": "Respuesta abierta &mdash; aldea o ciudad, municipio, provincia. No cuente estancias breves ni escalas.",
 },
 "mnths12": {
  "skip": "Preguntar si FleeCross = Sí",
  "stem": "¿Cuánto tiempo permaneció en el extranjero después de abandonar su hogar?",
  "opts": ["Menos de 12 meses", "12 meses o más"],
 },
 "legal": {
  "skip": "Preguntar a todos",
  "stem": "Pensando en su situación actual, ¿cuál es el documento principal que le permite permanecer en {country}?",
  "note": "Las categorías de nivel superior son fijas; las opciones bajo cada una pueden adaptarse a las "
          "categorías de visado y estatus del país; las líneas de estatus de protección llevan los nombres de los documentos de este país cuando se conocen.",
  "cats": [
   ["Sin documentos", ["Sin documentos"]],
   ["Visados", ["Visado de turista", "Visado de estudiante", "Visado de trabajo", "Visado humanitario", "Visado familiar", "Otro visado (especificar)"]],
   ["Acuerdos internacionales", ["Acuerdo regional de libre circulación (p. ej. Mercosur, UE, SADC, CAO, CEDEAO)"]],
   ["Residencia permanente y ciudadanía", ["Documento de residente permanente", "Pasaporte de {country}",
                                            "Otro documento que acredite la ciudadanía de {country}"]],
   ["Estatus de protección", ["Documento de solicitante de asilo", "Refugiado", "Documento de persona apátrida reconocida",
                              "Protección complementaria y subsidiaria", "Protección temporal"]],
   ["Documento de inscripción", ["Documento de inscripción"]],
   ["Otro", ["Otro (especificar)"]],
  ],
 },
},
# --------------------------------------------------------------------- AR
"ar": {
 "ui": {
  "skip_fleeloc1": "تُطرح إذا كان FleeLoc = بلد المسح",
  "oos_idp": "&larr; خارج النطاق &mdash; المسكن الذي غادره كان في بلد آخر",
  "notidp_apply": "&larr; لا يُحتسب نازحاً داخلياً (لاجئ عائد أو طالب لجوء)",
  "notidp_m12": "&larr; أقام إقامة في الخارج &mdash; لا يُحتسب نازحاً داخلياً",
  "note_apply_idp": "في نسخة النازحين داخلياً فقط، هذا سؤال فرز: من طلب الحماية الدولية في الخارج يُصنَّف لاجئاً عائداً أو طالب لجوء، لا نازحاً داخلياً، وينتهي النموذج عنده.",
  "note_fleecross_idp": "يُطرح لاستبعاد من أقاموا في الخارج: وفق التوصيات الدولية بشأن إحصاءات النازحين داخلياً، يبقى الشخص نازحاً داخلياً فقط إذا لم ينتقل قط إلى بلد آخر، أو بقي في الخارج أقل من 12 شهراً ولم يطلب الحماية هناك.",
  "note_fleecross_ref": "من غادر مسكناً في {country} ولم ينتقل قط إلى بلد آخر فهو نازح داخلياً &mdash; خارج نطاق تحديد اللاجئين؛ ويمكن أن ينتهي النموذج عنده.",
  "eg": "مثلاً", "cust_to": "مثلاً إلى {list}", "cust_other": "مثلاً {list}", "cust_adm": "مثلاً {list}",
  "cust_dtm": "من بين النازحين الذين قابلتهم المنظمة الدولية للهجرة (DTM) في {c}، أسباب ذُكرت خارج الرموز أعلاه: {list}",
  "cust_docs": "في {c}: {list}",
  "formal": "الاسم الرسمي: {n}",
  "ask_all": "تُطرح على الجميع",
  "yes": "نعم", "no": "لا",
  "goto": "&larr; الانتقال إلى {x}",
  "specify": "[حدِّد]",
  "open": "إجابة مفتوحة &mdash; القرية أو المدينة، المحافظة، الإقليم.",
  "loc_two": "مثال التكييف المحلي &mdash; صيغتان",
  "verA": "الصيغة <b>أ</b> &middot; المكتب &middot; كما وردت في الورقة",
  "verB": "الصيغة <b>ب</b> &middot; الوثيقة &middot; مقترحة بعد الورقة",
  "in_local": "<i>{n}</i> باللغة المحلية",
  "called": "يُعرف عادةً باسم &laquo;{n}&raquo;",
  "also_seen": "ورد أيضاً: {n}",
  "on_recog": "بعد الاعتراف يصبح: {n}",
  "noA": "لا يمكن صياغتها هنا &mdash; لم يُذكر أي مكتب كان المستجيب سيتوجه إليه.",
  "noB": "لا يمكن صياغتها هنا &mdash; لم تُذكر أي وثيقة أو بطاقة أو شهادة لهذا البلد.",
  "looks": "شكل الوثيقة",
  "instr": "<b>تعليمات للباحث الميداني.</b> اقرأ السؤال كما هو مكتوب، ثم مثالاً <b>واحداً</b> فقط. "
           "الصيغة أ تسمّي الجهة التي يُقدَّم إليها الطلب &mdash; وليس أبداً الجهة التي تبتّ فيه. "
           "الصيغة ب تسمّي الوثيقة الناتجة عن الطلب، وهي ما يتذكره المستجيبون غالباً أفضل من المكتب، "
           "وهي موضوع بند Legal لاحقاً؛ وحيثما يُعرض نموذج للوثيقة يمكن استخدامه كبطاقة عرض. "
           "نصّ السؤال وخيارات الإجابة لا تتغير أبداً من بلد إلى آخر.",
  "instr_misfire": "في هذا البلد يُعرف أن صياغة المكتب تُضلّل المستجيبين (انظر الملاحظة أدناه)، فيُفضَّل استخدام الصيغة ب.",
  "no_example": "لم يُصَغ بعد مثال تكييف محلي لهذا البلد &mdash; يُطرح السؤال كما هو مكتوب، دون مثال.",
  "none_proc": "لا يوجد في هذا البلد أي إجراء للتسجيل أو للحماية الدولية &mdash; تسلسل Apply / IntApply / Outcome لا ينطبق هنا.",
  "no_example_short": "&mdash; لا يمكن صياغة أي مثال تكييف محلي لهذا البلد.",
 },
 "apply": {
  "skip": "تُطرح إذا سُجِّل سبب صحيح للمغادرة وكان FleeCross = نعم",
  "stem": "هل سبق أن تقدّمت بطلب للحصول على الحماية الدولية، مثل صفة اللاجئ؟",
  "probe_office": "على سبيل المثال، هل توجّهت إلى مكتب مثل {name} للتسجيل؟",
  "probe_doc": "على سبيل المثال، هل تقدّمت بطلب للحصول على وثيقة مثل {name}؟",
 },
 "intapply": {
  "skip": "تُطرح إذا كان Apply = لا",
  "stem": "هل سبق أن كنت تعتزم التقدّم بطلب للحصول على الحماية الدولية، مثل صفة اللاجئ؟",
 },
 "outcome": {
  "skip": "تُطرح إذا كان Apply = نعم",
  "stem": "ما نتيجة طلبك للحصول على الحماية الدولية؟",
  "opts": ["مُنحت صفة اللاجئ", "رُفضت صفة اللاجئ", "لم يُبتّ في الطلب بعد", "سحبتُ طلبي"],
 },
 "frcoth": {
  "skip": "تُطرح إذا كان FrcFl = &laquo;تهديد آخر&raquo;",
  "stem": "ما التهديد الآخر لسلامتك الذي اضطرك إلى مغادرة مسكنك؟",
  "note": "إجابة مفتوحة يرمّزها الباحث الميداني أو المكتب &mdash; لا تُقرأ بصوت عالٍ. "
          "يُسمح بتكييف الأمثلة محلياً وتحديد الإجابات التي تُعدّ صحيحة؛ قائمة إعادة الترميز الواردة في الورقة:",
  "list": [
   ["خطر التجنيد الإجباري أو التجنيد القسري من قِبل جماعات مسلحة",
    "يُعاد ترميزه ضمن النزاع المسلح / العنف الواسع النطاق في FrcFl"],
   ["الإخلاء", "عمليات الإخلاء الجماعي لمشاريع البنية التحتية تُرمَّز في FrcFl؛ وحالات الإخلاء الفردي من قِبل المالك تبقى هنا"],
   ["الخوف من الجريمة العنيفة", None],
   ["انعدام الاستقرار السياسي أو الإخلال بالنظام العام أو الاضطرابات المدنية", None],
   ["انعدام الأمن الغذائي أو المجاعة", None],
   ["نقص المرافق الطبية", None],
   ["العنف الأسري أو الزواج القسري أو العنف المنزلي", None],
   ["نقص فرص العمل", None],
   ["نقص البنية التحتية المحلية، مثل المدارس والسكن والصرف الصحي والكهرباء", None],
   ["انهيار العلاقة الزوجية أو العاطفية أو الأسرية", None],
   ["سبب آخر (حدِّد)", None],
  ],
 },
 "fleeloc": {
  "skip": "تُطرح إذا سُجِّل سبب صحيح للمغادرة في FrcFl أو FrcOth",
  "stem": "في أي بلد كان المسكن الذي اضطررت إلى مغادرته؟",
  "opts": ["بلد المسح", "بلد آخر [حدِّد]"],
 },
 "idploc": {
  "skip": "تُطرح إذا كان FleeLoc = بلد المسح",
  "stem": "أخبرني أين كنت تعيش مباشرةً قبل أن تُضطر إلى مغادرة مسكنك للمرة الأولى.",
 },
 "locliv": {
  "skip": "تُطرح إذا سُجِّل سبب صحيح للمغادرة",
  "stem": "قبل مغادرة هذا المسكن، هل كنت تعيش دائماً في {country}؟",
 },
 "citloc": {
  "skip": "تُطرح إذا كان LocLiv = لا",
  "stem": "هل كنت من مواطني {country} عندما غادرت مسكنك هناك؟",
 },
 "fleecross": {
  "skip": "تُطرح إذا سُجِّل سبب صحيح للمغادرة",
  "stem": "بعد مغادرة مسكنك، هل انتقلت في أي وقت إلى بلد آخر، ولو بصفة مؤقتة؟",
 },
 "idppost": {
  "skip": "تُطرح إذا كان FleeLoc = بلد المسح وكان FleeCross = لا",
  "stem": "عندما غادرت مسكنك للمرة الأولى، إلى أين انتقلت أولاً؟",
  "note": "إجابة مفتوحة &mdash; القرية أو المدينة، المحافظة، الإقليم. لا تُحتسب الإقامات القصيرة أو محطات التوقف.",
 },
 "mnths12": {
  "skip": "تُطرح إذا كان FleeCross = نعم",
  "stem": "كم من الوقت بقيت في الخارج بعد مغادرة مسكنك؟",
  "opts": ["أقل من 12 شهراً", "12 شهراً أو أكثر"],
 },
 "legal": {
  "skip": "تُطرح على الجميع",
  "stem": "بالنظر إلى وضعك الحالي، ما الوثيقة الرئيسية التي تسمح لك بالبقاء في {country}؟",
  "note": "الفئات العليا ثابتة؛ ويمكن تكييف الخيارات تحت كل فئة وفق فئات التأشيرات والأوضاع القانونية في البلد "
          "؛ وتحمل بنود وضع الحماية أسماء وثائق هذا البلد حيثما كانت معروفة.",
  "cats": [
   ["لا وثائق", ["لا وثائق"]],
   ["التأشيرات", ["تأشيرة سياحية", "تأشيرة دراسة", "تأشيرة عمل", "تأشيرة إنسانية", "تأشيرة لمّ شمل الأسرة", "تأشيرة أخرى (حدِّد)"]],
   ["الاتفاقيات الدولية", ["اتفاقية إقليمية لحرية التنقل (مثل ميركوسور، الاتحاد الأوروبي، سادك، جماعة شرق أفريقيا، إيكواس)"]],
   ["الإقامة الدائمة والجنسية", ["وثيقة إقامة دائمة", "جواز سفر {country}", "وثيقة أخرى تثبت جنسية {country}"]],
   ["وضع الحماية", ["وثيقة طالب لجوء", "لاجئ", "وثيقة شخص عديم الجنسية معترف به", "الحماية التكميلية والفرعية", "الحماية المؤقتة"]],
   ["وثيقة تسجيل", ["وثيقة تسجيل"]],
   ["أخرى", ["أخرى (حدِّد)"]],
  ],
 },
},
# --------------------------------------------------------------------- RU
"ru": {
 "ui": {
  "skip_fleeloc1": "Задавать, если FleeLoc = Страна обследования",
  "oos_idp": "&rarr; вне охвата &mdash; покинутое жильё находилось в другой стране",
  "notidp_apply": "&rarr; не учитывается как ВПЛ (репатриированный беженец или проситель убежища)",
  "notidp_m12": "&rarr; обосновался за границей &mdash; не учитывается как ВПЛ",
  "note_apply_idp": "В версии только для ВПЛ это отсеивающий вопрос: тот, кто обращался за международной защитой за границей, классифицируется как репатриированный беженец или проситель убежища, а не как ВПЛ, и модуль на этом завершается.",
  "note_fleecross_idp": "Задаётся, чтобы исключить обосновавшихся за границей: согласно IRIS человек остаётся ВПЛ, только если никогда не переезжал в другую страну или находился за границей менее 12 месяцев и не обращался там за защитой.",
  "note_fleecross_ref": "Тот, кто покинул жильё в стране {country} и никогда не переезжал в другую страну, является внутренне перемещённым лицом &mdash; вне охвата идентификации беженцев; модуль может на этом завершиться.",
  "eg": "напр.", "cust_to": "напр. в {list}", "cust_other": "напр. {list}", "cust_adm": "напр. {list}",
  "cust_dtm": "Среди перемещённых лиц, опрошенных МОМ (DTM) в стране {c}, причины, названные вне приведённых выше кодов: {list}",
  "cust_docs": "В стране {c}: {list}",
  "formal": "официальное название: {n}",
  "ask_all": "Задавать всем",
  "yes": "Да", "no": "Нет",
  "goto": "&rarr; перейти к {x}",
  "specify": "[УТОЧНИТЬ]",
  "open": "Открытый ответ &mdash; село или город, район, область.",
  "loc_two": "Пример локализации &mdash; две версии",
  "verA": "Версия <b>A</b> &middot; учреждение &middot; как в документе",
  "verB": "Версия <b>B</b> &middot; документ &middot; предложена после документа",
  "in_local": "<i>{n}</i> на местном языке",
  "called": "в обиходе &laquo;{n}&raquo;",
  "also_seen": "Также встречается: {n}",
  "on_recog": "После признания статуса становится: {n}",
  "noA": "Здесь сформулировать нельзя &mdash; не названо учреждение, куда обращался бы респондент.",
  "noB": "Здесь сформулировать нельзя &mdash; для этой страны не названы ни документ, ни карта, ни справка.",
  "looks": "Как выглядит документ",
  "instr": "<b>Инструкция для интервьюера.</b> Прочитайте вопрос как написано, затем <b>один</b> пример. "
           "Версия A называет место подачи ходатайства &mdash; никогда не орган, принимающий решение. "
           "Версия B называет документ, который выдаётся по ходатайству: респонденты часто помнят его лучше, "
           "чем учреждение, и о нём же далее спрашивает пункт Legal; если показан образец, его можно использовать "
           "как карточку. Формулировка вопроса и варианты ответа не меняются от страны к стране.",
  "instr_misfire": "В этой стране формулировка через учреждение, как известно, вводит в заблуждение (см. примечание ниже), поэтому предпочтительна версия B.",
  "no_example": "Для этой страны пример локализации ещё не подготовлен &mdash; вопрос задаётся как написано, без примера.",
  "none_proc": "В этой стране нет ни процедуры регистрации, ни процедуры международной защиты &mdash; последовательность Apply / IntApply / Outcome здесь не применяется.",
  "no_example_short": "&mdash; для этой страны пример локализации составить нельзя.",
 },
 "apply": {
  "skip": "Задавать, если закодирована допустимая причина вынужденного выезда и FleeCross = Да",
  "stem": "Обращались ли Вы когда-либо за международной защитой, например за статусом беженца?",
  "probe_office": "Например, обращались ли Вы для регистрации в учреждение, такое как {name}?",
  "probe_doc": "Например, обращались ли Вы за документом, таким как {name}?",
 },
 "intapply": {
  "skip": "Задавать, если Apply = Нет",
  "stem": "Планировали ли Вы когда-либо обратиться за международной защитой, например за статусом беженца?",
 },
 "outcome": {
  "skip": "Задавать, если Apply = Да",
  "stem": "Каков был результат Вашего ходатайства о международной защите?",
  "opts": ["Статус беженца предоставлен", "В статусе беженца отказано",
           "Решение ещё не принято", "Я отозвал(а) своё ходатайство"],
 },
 "frcoth": {
  "skip": "Задавать, если FrcFl = &laquo;иная угроза&raquo;",
  "stem": "Какая иная угроза Вашей безопасности вынудила Вас покинуть жильё?",
  "note": "Открытый ответ, кодируется интервьюером или в офисе &mdash; вслух не зачитывается. "
          "Допускается локализация примеров и перечня ответов, считающихся допустимыми; "
          "перечень перекодировки из документа:",
  "list": [
   ["Риск призыва или принудительной вербовки вооружёнными группами",
    "перекодировать в вооружённый конфликт / массовое насилие в FrcFl"],
   ["Выселение", "массовые выселения под инфраструктурные проекты относятся к FrcFl; единичные выселения арендодателем остаются здесь"],
   ["Страх перед насильственной преступностью", None],
   ["Политическая нестабильность, нарушения общественного порядка или гражданские беспорядки", None],
   ["Отсутствие продовольственной безопасности или голод", None],
   ["Отсутствие медицинских учреждений", None],
   ["Насилие в семье, принудительный брак или бытовое насилие", None],
   ["Отсутствие возможностей трудоустройства", None],
   ["Отсутствие местной инфраструктуры, например школ, жилья, канализации, электричества", None],
   ["Распад брака, отношений или семьи", None],
   ["Иная причина (уточнить)", None],
  ],
 },
 "fleeloc": {
  "skip": "Задавать, если закодирована допустимая причина вынужденного выезда в FrcFl или FrcOth",
  "stem": "В какой стране находилось жильё, которое Вам пришлось покинуть?",
  "opts": ["Страна обследования", "Другая страна [УТОЧНИТЬ]"],
 },
 "idploc": {
  "skip": "Задавать, если FleeLoc = Страна обследования",
  "stem": "Скажите, где Вы жили непосредственно перед тем, как впервые были вынуждены покинуть жильё.",
 },
 "locliv": {
  "skip": "Задавать, если закодирована допустимая причина вынужденного выезда",
  "stem": "До того как покинуть это жильё, жили ли Вы всегда в стране {country}?",
 },
 "citloc": {
  "skip": "Задавать, если LocLiv = Нет",
  "stem": "Были ли Вы гражданином страны {country}, когда покинули там своё жильё?",
 },
 "fleecross": {
  "skip": "Задавать, если закодирована допустимая причина вынужденного выезда",
  "stem": "После того как Вы покинули жильё, переезжали ли Вы когда-либо в другую страну, пусть даже временно?",
 },
 "idppost": {
  "skip": "Задавать, если FleeLoc = Страна обследования и FleeCross = Нет",
  "stem": "Когда Вы впервые покинули жильё, куда Вы переехали в первую очередь?",
  "note": "Открытый ответ &mdash; село или город, район, область. Кратковременные остановки и пересадки не учитываются.",
 },
 "mnths12": {
  "skip": "Задавать, если FleeCross = Да",
  "stem": "Как долго Вы находились за границей после того, как покинули жильё?",
  "opts": ["Менее 12 месяцев", "12 месяцев и более"],
 },
 "legal": {
  "skip": "Задавать всем",
  "stem": "Если говорить о Вашем нынешнем положении, какой основной документ позволяет Вам находиться в стране {country}?",
  "note": "Категории верхнего уровня фиксированы; варианты внутри каждой могут быть адаптированы к категориям виз "
          "и статусов данной страны; строки защищённого статуса содержат названия документов этой страны, если они известны.",
  "cats": [
   ["Нет документов", ["Нет документов"]],
   ["Визы", ["Туристическая виза", "Учебная виза", "Рабочая виза", "Гуманитарная виза", "Семейная виза", "Иная виза (уточнить)"]],
   ["Международные соглашения", ["Региональное соглашение о свободе передвижения (например, МЕРКОСУР, ЕС, САДК, ВАС, ЭКОВАС)"]],
   ["Постоянное проживание и гражданство", ["Документ постоянного жителя", "Паспорт страны {country}",
                                            "Иной документ, подтверждающий гражданство страны {country}"]],
   ["Защищённый статус", ["Документ ходатайствующего об убежище", "Беженец", "Документ признанного лица без гражданства",
                          "Дополнительная и вспомогательная защита", "Временная защита"]],
   ["Регистрационный документ", ["Регистрационный документ"]],
   ["Иное", ["Иное (уточнить)"]],
  ],
 },
},
# --------------------------------------------------------------------- ZH
"zh": {
 "ui": {
  "skip_fleeloc1": "如 FleeLoc = 调查所在国，则询问",
  "oos_idp": "&rarr; 不在范围内 &mdash; 离开的住所在另一个国家",
  "notidp_apply": "&rarr; 不计为境内流离失所者（回返难民或寻求庇护者）",
  "notidp_m12": "&rarr; 已在国外定居 &mdash; 不计为境内流离失所者",
  "note_apply_idp": "在仅识别境内流离失所者的版本中，这是一道筛选题：凡在国外申请过国际保护者归类为回返难民或寻求庇护者，而非境内流离失所者，问卷到此结束。",
  "note_fleecross_idp": "此题用于排除已在国外定居者：按照IRIS，只有从未迁往他国、或在国外停留不足12个月且未在当地寻求保护的人，才仍算境内流离失所者。",
  "note_fleecross_ref": "在{country}离开住所且从未迁往他国者属于境内流离失所 &mdash; 不在难民识别范围内；问卷可到此结束。",
  "eg": "例如", "cust_to": "例如前往{list}", "cust_other": "例如{list}", "cust_adm": "例如{list}",
  "cust_dtm": "在国际移民组织（DTM）于{c}访谈的流离失所者中，所述的上述编码之外的原因：{list}",
  "cust_docs": "在{c}：{list}",
  "formal": "正式名称：{n}",
  "ask_all": "询问所有人",
  "yes": "是", "no": "否",
  "goto": "&rarr; 转至 {x}",
  "specify": "[请说明]",
  "open": "开放式回答 &mdash; 村或镇、县、省。",
  "loc_two": "本地化示例 &mdash; 两个版本",
  "verA": "版本 <b>A</b> &middot; 办事机构 &middot; 与文件中一致",
  "verB": "版本 <b>B</b> &middot; 证件 &middot; 文件之后提出",
  "in_local": "当地语言：<i>{n}</i>",
  "called": "通常称为“{n}”",
  "also_seen": "另见：{n}",
  "on_recog": "获得承认后变为：{n}",
  "noA": "此处无法表述 &mdash; 未列出受访者可能前往的任何办事机构。",
  "noB": "此处无法表述 &mdash; 未列出该国的任何证件、卡片或证明。",
  "looks": "证件样式",
  "instr": "<b>访员说明。</b>按原文读出问题，然后只读<b>一个</b>示例。版本 A 列出提交申请的地点 &mdash; "
           "绝不是作出决定的机构。版本 B 列出申请所产生的证件，受访者对证件的记忆往往比对机构更清楚，"
           "而且后面的 Legal 题目也会问及该证件；如有样本展示，可用作示卡。题干和答案选项在各国之间从不改变。",
  "instr_misfire": "在该国，已知以办事机构表述容易造成误答（见下方说明），因此宜采用版本 B。",
  "no_example": "该国尚未拟定本地化示例 &mdash; 按原文提问，不加示例。",
  "none_proc": "该国不存在任何登记或国际保护程序 &mdash; Apply / IntApply / Outcome 序列在此不适用。",
  "no_example_short": "&mdash; 无法为该国拟定本地化示例。",
 },
 "apply": {
  "skip": "如已记录有效的被迫离开原因且 FleeCross = 是，则询问",
  "stem": "您是否曾申请过国际保护，例如难民身份？",
  "probe_office": "例如，您是否曾前往像{name}这样的办事机构进行登记？",
  "probe_doc": "例如，您是否曾申请过像{name}这样的证件？",
 },
 "intapply": {
  "skip": "如 Apply = 否，则询问",
  "stem": "您是否曾计划申请国际保护，例如难民身份？",
 },
 "outcome": {
  "skip": "如 Apply = 是，则询问",
  "stem": "您的国际保护申请结果如何？",
  "opts": ["已获得难民身份", "难民身份被拒", "结果尚未决定", "我撤回了申请"],
 },
 "frcoth": {
  "skip": "如 FrcFl = “其他威胁”，则询问",
  "stem": "是什么其他安全威胁使您不得不离开住所？",
  "note": "开放式回答，由访员或办公室编码 &mdash; 不读出。允许对示例及有效答案范围进行本地化；"
          "以下为文件中的回编码清单：",
  "list": [
   ["被武装团体征召或强迫招募的风险", "在 FrcFl 中重新编码为武装冲突/大规模暴力"],
   ["驱逐", "因基础设施项目的大规模驱逐归入 FrcFl；房东的个别驱逐留在此处"],
   ["对暴力犯罪的恐惧", None],
   ["政治不安全、公共秩序混乱或内乱", None],
   ["粮食不安全或饥荒", None],
   ["缺乏医疗设施", None],
   ["家庭暴力、强迫婚姻或家庭虐待", None],
   ["缺乏就业机会", None],
   ["缺乏当地基础设施，如学校、住房、排污、电力", None],
   ["婚姻、恋爱关系或家庭破裂", None],
   ["其他原因（请说明）", None],
  ],
 },
 "fleeloc": {
  "skip": "如在 FrcFl 或 FrcOth 中已记录有效的被迫离开原因，则询问",
  "stem": "您不得不离开的那个住所在哪个国家？",
  "opts": ["调查所在国", "其他国家 [请说明]"],
 },
 "idploc": {
  "skip": "如 FleeLoc = 调查所在国，则询问",
  "stem": "请告诉我，在您第一次被迫离开住所之前，您住在哪里。",
 },
 "locliv": {
  "skip": "如已记录有效的被迫离开原因，则询问",
  "stem": "在离开那个住所之前，您是否一直居住在{country}？",
 },
 "citloc": {
  "skip": "如 LocLiv = 否，则询问",
  "stem": "当您在那里离开住所时，您是否是{country}公民？",
 },
 "fleecross": {
  "skip": "如已记录有效的被迫离开原因，则询问",
  "stem": "离开住所后，您是否曾迁往另一个国家，哪怕只是暂时的？",
 },
 "idppost": {
  "skip": "如 FleeLoc = 调查所在国 且 FleeCross = 否，则询问",
  "stem": "您第一次离开住所时，最先迁往了哪里？",
  "note": "开放式回答 &mdash; 村或镇、县、省。不包括短暂停留或中转。",
 },
 "mnths12": {
  "skip": "如 FleeCross = 是，则询问",
  "stem": "离开住所后，您在国外停留了多长时间？",
  "opts": ["不足 12 个月", "12 个月或以上"],
 },
 "legal": {
  "skip": "询问所有人",
  "stem": "就您目前的情况而言，允许您留在{country}的主要证件是什么？",
  "note": "上级类别固定不变；各类别下的选项可按该国自身的签证/身份类别进行本地化；受保护身份各行在已知时标注该国证件名称。",
  "cats": [
   ["无证件", ["无证件"]],
   ["签证", ["旅游签证", "学生签证", "工作签证", "人道主义签证", "家庭签证", "其他签证（请说明）"]],
   ["国际协定", ["区域自由流动协定（如南方共同市场、欧盟、南部非洲发展共同体、东非共同体、西非国家经济共同体）"]],
   ["永久居留与公民身份", ["永久居民证件", "{country}护照", "证明{country}公民身份的其他证件"]],
   ["受保护身份", ["寻求庇护者证件", "难民", "获承认的无国籍人士证件", "补充保护和辅助保护", "临时保护"]],
   ["登记证件", ["登记证件"]],
   ["其他", ["其他（请说明）"]],
  ],
 },
},
}


def _check():
    keys = {k: set(v) for k, v in M["en"].items() if isinstance(v, dict)}
    for lang, d in M.items():
        assert set(d) == set(M["en"]), f"{lang}: top-level keys differ"
        for sect, sub in keys.items():
            assert set(d[sect]) == sub, f"{lang}.{sect}: keys differ {set(d[sect]) ^ sub}"
        assert len(d["frcoth"]["list"]) == 11, lang
        assert len(d["legal"]["cats"]) == 7, lang
        assert [len(c[1]) for c in d["legal"]["cats"]] == [1, 6, 1, 3, 5, 1, 1], lang
        for sect in ("outcome", "fleeloc", "mnths12"):
            assert len(d[sect]["opts"]) == len(M["en"][sect]["opts"]), f"{lang}.{sect}"
        for k in ("probe_office", "probe_doc"):
            assert "{name}" in d["apply"][k], f"{lang}.apply.{k}"
    return True


if __name__ == "__main__":
    _check()
    print("module_i18n: 6 languages, structure consistent")
