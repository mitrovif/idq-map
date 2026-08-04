"""
The forced-to-flee item in the six UN official languages.

READ THIS BEFORE USING ANY OF IT
These translations are DRAFTS. Translating a survey instrument is a specialist
job with an established methodology - TRAPD, or forward-and-back translation with
reconciliation - because a question does not merely have to mean the same thing,
it has to be understood the same way by people who have never seen it before.
Cognitive testing on an unreviewed translation tests the translation, not the
question, and a mistranslated option will look like a comprehension failure in
the results.

They are here because having a starting draft in the language of the country is
more useful to a task team than having nothing, and because the failure mode of
NOT providing one is that somebody translates it ad hoc in the field with no
record of what was decided.

DECISION TAKEN ON "FLEE" - LEAVING UNDER DURESS, NOT FLEEING IN PANIC
The English item says "flee a home" and then defines it as leaving "due to events
that posed a threat", so the sense is COMPELLED DEPARTURE. Several of these
languages have a default verb that instead means running away in fear, and the
first draft used it in five of them: fuir (fr), huir (es), الفرار (ar),
спасаясь бегством (ru), 逃离 (zh). Each of those invites a respondent to picture
a panicked escape and to answer "no" if their own departure was deliberate -
packing over days, or leaving after a threat rather than during an attack. That
is precisely the population the questions exist to count.

All five now use a duress construction: contraint de quitter, obligado a
abandonar, اضطررت إلى مغادرة, вынужденно покидать, 被迫离开. A reviewer should
still confirm the register country by country, but the sense is now the right
one to be checking.

STILL OPEN, AND NOT SETTLEABLE AUTOMATICALLY
  "persecution" The legal term of art in the refugee definition. In everyday
                registers it can read as ordinary harassment, which is a
                materially different threshold.

Actor names are NOT translated. "Boko Haram" and "Comando Vermelho" are proper
nouns and respondents know them in that form.
"""
import re

LANGS = {
    "en": ("English", "ltr"),
    "fr": ("Français", "ltr"),
    "es": ("Español", "ltr"),
    "ar": ("العربية", "rtl"),
    "ru": ("Русский", "ltr"),
    "zh": ("中文", "ltr"),
}

# Country -> the UN official language most likely to be used in a national
# household survey there. Deliberately one per country: where several are used,
# the field team picks, and this is a starting draft rather than a prescription.
COUNTRY_LANG = {}
_FR = """DZA BEN BFA BDI CMR CAF TCD COM COD COG CIV DJI GAB GIN GNQ HTI MDG MLI
         MAR MRT NER RWA SEN SYC TGO TUN VUT BEL CHE FRA LUX MCO"""
_AR = """DZA BHR TCD COM DJI EGY IRQ JOR KWT LBN LBY MRT MAR OMN PSE QAT SAU SOM
         SDN SYR TUN ARE YEM"""
_ES = """ARG BOL CHL COL CRI CUB DOM ECU SLV GNQ GTM HND MEX NIC PAN PRY PER ESP
         URY VEN"""
_RU = """RUS BLR KAZ KGZ TJK UZB TKM"""
_ZH = """CHN"""
for codes, lang in ((_FR, "fr"), (_ES, "es"), (_RU, "ru"), (_ZH, "zh"), (_AR, "ar")):
    for c in codes.split():
        COUNTRY_LANG[c] = lang     # Arabic last: it wins where both apply


def lang_for(iso3):
    return COUNTRY_LANG.get(iso3, "en")


# --- the fixed instrument text -------------------------------------------
T = {
    "en": {
        "item": "FrcFl",
        "ask": "{Ask all}",
        "stem1": "The next questions are about whether you have ever had to "
                 "<b>flee a home</b>.",
        "stem2": "By this we mean leaving a home, or land, due to <b>events that "
                 "posed a threat to you or your family's safety</b>.",
        "lead": "In your lifetime, have you ever left a home due to…",
        "instr": "SHOW SCREEN OR READ-OUT. CHOOSE ALL THAT APPLY",
        "eg": "e.g.",
        "specify": "[SPECIFY]",
        "none": "None of the above",
        "excl": "[EXCLUSIVE CODE]",
        "more": "+{n} more recorded",
        "opts": {
            1: "Threat of <b>armed conflict</b> or <b>war</b>",
            2: "<b>Widespread violence</b> or <b>breakdown of public order</b>",
            3: "<b>Discrimination or persecution</b>",
            4: "Threat of <b>human rights violations by authorities</b>",
            5: "Other threats of <b>violence against you</b>",
            6: "<b>Natural disasters</b>",
            7: "<b>Man-made events</b>",
            8: "A <b>different threat</b> to you or your family's safety",
        },
        "generic": {
            3: "due to your ethnic group, nationality, religion, political "
               "beliefs, sexual orientation or other group membership",
            4: "detention, torture, confiscation of property",
            6: "floods, droughts, landslides, earthquakes, hurricanes",
            7: "eviction for infrastructure projects, pollution events",
        },
    },
    "fr": {
        "item": "FrcFl",
        "ask": "{Poser à tous}",
        "stem1": "Les questions suivantes portent sur le fait d'avoir déjà été "
                 "<b>contraint de quitter un domicile</b>.",
        "stem2": "Nous entendons par là quitter un domicile, ou une terre, en "
                 "raison d'<b>événements ayant représenté une menace pour votre "
                 "sécurité ou celle de votre famille</b>.",
        "lead": "Au cours de votre vie, avez-vous déjà quitté un domicile en "
                "raison de…",
        "instr": "MONTRER L'ÉCRAN OU LIRE À VOIX HAUTE. CHOISIR TOUT CE QUI S'APPLIQUE",
        "eg": "p. ex.",
        "specify": "[PRÉCISER]",
        "none": "Aucune de ces réponses",
        "excl": "[CODE EXCLUSIF]",
        "more": "+{n} autres recensés",
        "opts": {
            1: "Menace de <b>conflit armé</b> ou de <b>guerre</b>",
            2: "<b>Violence généralisée</b> ou <b>effondrement de l'ordre public</b>",
            3: "<b>Discrimination ou persécution</b>",
            4: "Menace de <b>violations des droits humains par les autorités</b>",
            5: "Autres menaces de <b>violence à votre encontre</b>",
            6: "<b>Catastrophes naturelles</b>",
            7: "<b>Événements d'origine humaine</b>",
            8: "Une <b>autre menace</b> pour votre sécurité ou celle de votre famille",
        },
        "generic": {
            3: "en raison de votre groupe ethnique, nationalité, religion, "
               "opinions politiques, orientation sexuelle ou appartenance à un "
               "autre groupe",
            4: "détention, torture, confiscation de biens",
            6: "inondations, sécheresses, glissements de terrain, séismes, cyclones",
            7: "expulsion pour des projets d'infrastructure, épisodes de pollution",
        },
    },
    "es": {
        "item": "FrcFl",
        "ask": "{Preguntar a todos}",
        "stem1": "Las siguientes preguntas tratan sobre si alguna vez se ha "
                 "visto <b>obligado a abandonar un hogar</b>.",
        "stem2": "Con esto nos referimos a abandonar un hogar, o una tierra, "
                 "debido a <b>hechos que representaron una amenaza para su "
                 "seguridad o la de su familia</b>.",
        "lead": "A lo largo de su vida, ¿alguna vez ha abandonado un hogar "
                "debido a…?",
        "instr": "MOSTRAR PANTALLA O LEER EN VOZ ALTA. ELEGIR TODAS LAS QUE CORRESPONDAN",
        "eg": "p. ej.",
        "specify": "[ESPECIFICAR]",
        "none": "Ninguna de las anteriores",
        "excl": "[CÓDIGO EXCLUYENTE]",
        "more": "+{n} más registrados",
        "opts": {
            1: "Amenaza de <b>conflicto armado</b> o <b>guerra</b>",
            2: "<b>Violencia generalizada</b> o <b>quiebre del orden público</b>",
            3: "<b>Discriminación o persecución</b>",
            4: "Amenaza de <b>violaciones de derechos humanos por parte de las "
               "autoridades</b>",
            5: "Otras amenazas de <b>violencia contra usted</b>",
            6: "<b>Desastres naturales</b>",
            7: "<b>Eventos provocados por el ser humano</b>",
            8: "Otra <b>amenaza distinta</b> para su seguridad o la de su familia",
        },
        "generic": {
            3: "por su grupo étnico, nacionalidad, religión, creencias "
               "políticas, orientación sexual u otra pertenencia a un grupo",
            4: "detención, tortura, confiscación de bienes",
            6: "inundaciones, sequías, deslizamientos de tierra, terremotos, huracanes",
            7: "desalojo por proyectos de infraestructura, episodios de contaminación",
        },
    },
    "ar": {
        "item": "FrcFl",
        "ask": "{تُطرح على الجميع}",
        "stem1": "تتعلق الأسئلة التالية بما إذا كنت قد <b>اضطررت إلى مغادرة "
                 "مكان إقامتك</b> في أي وقت.",
        "stem2": "ونعني بذلك مغادرة المسكن أو الأرض بسبب <b>أحداث شكّلت تهديداً "
                 "لسلامتك أو سلامة أسرتك</b>.",
        "lead": "هل سبق لك في حياتك أن غادرت مكان إقامتك بسبب…",
        "instr": "اعرض الشاشة أو اقرأ بصوت مسموع. اختر كل ما ينطبق",
        "eg": "مثل",
        "specify": "[يُرجى التحديد]",
        "none": "لا شيء مما سبق",
        "excl": "[رمز حصري]",
        "more": "+{n} حالات أخرى مسجلة",
        "opts": {
            1: "خطر <b>النزاع المسلح</b> أو <b>الحرب</b>",
            2: "<b>العنف واسع النطاق</b> أو <b>انهيار النظام العام</b>",
            3: "<b>التمييز أو الاضطهاد</b>",
            4: "خطر <b>انتهاكات حقوق الإنسان من جانب السلطات</b>",
            5: "تهديدات أخرى <b>بالعنف ضدك</b>",
            6: "<b>الكوارث الطبيعية</b>",
            7: "<b>الأحداث الناجمة عن النشاط البشري</b>",
            8: "<b>تهديد آخر</b> لسلامتك أو سلامة أسرتك",
        },
        "generic": {
            3: "بسبب انتمائك العرقي أو جنسيتك أو دينك أو آرائك السياسية أو "
               "ميلك الجنسي أو انتمائك إلى فئة أخرى",
            4: "الاحتجاز، التعذيب، مصادرة الممتلكات",
            6: "الفيضانات، الجفاف، الانهيارات الأرضية، الزلازل، الأعاصير",
            7: "الإخلاء بسبب مشاريع البنية التحتية، حوادث التلوث",
        },
    },
    "ru": {
        "item": "FrcFl",
        "ask": "{Задать всем}",
        "stem1": "Следующие вопросы касаются того, приходилось ли вам "
                 "когда-либо <b>вынужденно покидать дом</b>.",
        "stem2": "Под этим мы понимаем уход из дома или с земли из-за "
                 "<b>событий, представлявших угрозу для вашей безопасности или "
                 "безопасности вашей семьи</b>.",
        "lead": "Приходилось ли вам когда-либо в жизни покидать дом из-за…",
        "instr": "ПОКАЗАТЬ КАРТОЧКУ ИЛИ ЗАЧИТАТЬ. ВЫБРАТЬ ВСЕ ПОДХОДЯЩЕЕ",
        "eg": "напр.",
        "specify": "[УКАЖИТЕ]",
        "none": "Ничего из перечисленного",
        "excl": "[ИСКЛЮЧАЮЩИЙ КОД]",
        "more": "+{n} других зафиксировано",
        "opts": {
            1: "Угроза <b>вооружённого конфликта</b> или <b>войны</b>",
            2: "<b>Массовое насилие</b> или <b>нарушение общественного порядка</b>",
            3: "<b>Дискриминация или преследование</b>",
            4: "Угроза <b>нарушений прав человека со стороны властей</b>",
            5: "Иные угрозы <b>насилия в отношении вас</b>",
            6: "<b>Стихийные бедствия</b>",
            7: "<b>События, вызванные деятельностью человека</b>",
            8: "<b>Иная угроза</b> вашей безопасности или безопасности вашей семьи",
        },
        "generic": {
            3: "из-за вашей этнической принадлежности, гражданства, религии, "
               "политических убеждений, сексуальной ориентации или "
               "принадлежности к иной группе",
            4: "задержание, пытки, конфискация имущества",
            6: "наводнения, засухи, оползни, землетрясения, ураганы",
            7: "выселение из-за инфраструктурных проектов, случаи загрязнения",
        },
    },
    "zh": {
        "item": "FrcFl",
        "ask": "{全部询问}",
        "stem1": "接下来的问题是关于您是否曾<b>被迫离开家园</b>。",
        "stem2": "我们指的是因<b>对您或您家人安全构成威胁的事件</b>而离开住所或土地。",
        "lead": "在您的一生中，您是否曾因以下原因离开过家园……",
        "instr": "出示卡片或朗读。选择所有适用项",
        "eg": "例如",
        "specify": "[请说明]",
        "none": "以上均不适用",
        "excl": "[排他性编码]",
        "more": "另有 {n} 项记录",
        "opts": {
            1: "<b>武装冲突</b>或<b>战争</b>的威胁",
            2: "<b>普遍暴力</b>或<b>公共秩序崩溃</b>",
            3: "<b>歧视或迫害</b>",
            4: "<b>当局侵犯人权</b>的威胁",
            5: "其他<b>针对您的暴力</b>威胁",
            6: "<b>自然灾害</b>",
            7: "<b>人为事件</b>",
            8: "对您或您家人安全的<b>其他威胁</b>",
        },
        "generic": {
            3: "因您的族群、国籍、宗教、政治信仰、性取向或其他群体身份",
            4: "拘留、酷刑、财产没收",
            6: "洪水、干旱、山体滑坡、地震、飓风",
            7: "因基础设施项目而被迫迁离、污染事件",
        },
    },
}

# --- the generated example fragments -------------------------------------
# Templates keep {} for the actor names, which are never translated.
FRAG = {
    "the fighting involving {}": {
        "fr": "les combats impliquant {}", "es": "los enfrentamientos con {}",
        "ar": "الاشتباكات التي شارك فيها {}", "ru": "боевые действия с участием {}",
        "zh": "涉及{}的战斗"},
    "clashes between armed groups, including {}": {
        "fr": "des affrontements entre groupes armés, dont {}",
        "es": "enfrentamientos entre grupos armados, incluidos {}",
        "ar": "اشتباكات بين جماعات مسلحة، من بينها {}",
        "ru": "столкновения между вооружёнными группами, включая {}",
        "zh": "武装团体之间的冲突，包括{}"},
    "attacks on civilians by {}": {
        "fr": "des attaques contre des civils par {}",
        "es": "ataques contra civiles por parte de {}",
        "ar": "هجمات على المدنيين من جانب {}",
        "ru": "нападения на гражданских лиц со стороны {}",
        "zh": "{}对平民的袭击"},
    # must come AFTER the "including" variant, which is more specific
    "clashes between {}": {
        "fr": "des affrontements entre {}", "es": "enfrentamientos entre {}",
        "ar": "اشتباكات بين {}", "ru": "столкновения между {}",
        "zh": "{}之间的冲突"},
    "communal or intercommunal violence": {
        "fr": "des violences communautaires ou intercommunautaires",
        "es": "violencia comunitaria o intercomunitaria",
        "ar": "عنف طائفي أو بين المجتمعات المحلية",
        "ru": "межобщинное насилие", "zh": "族群间或社区间暴力"},
    "attacks on civilians by armed groups": {
        "fr": "des attaques contre des civils par des groupes armés",
        "es": "ataques contra civiles por parte de grupos armados",
        "ar": "هجمات على المدنيين من جانب جماعات مسلحة",
        "ru": "нападения вооружённых групп на гражданских лиц",
        "zh": "武装团体对平民的袭击"},
    "action by government forces against civilians": {
        "fr": "des actions des forces gouvernementales contre des civils",
        "es": "acciones de las fuerzas gubernamentales contra civiles",
        "ar": "أعمال قوات حكومية ضد المدنيين",
        "ru": "действия правительственных сил против гражданских лиц",
        "zh": "政府军对平民的行动"},
}

HAZ = {
    "floods": {"fr": "inondations", "es": "inundaciones", "ar": "فيضانات",
               "ru": "наводнения", "zh": "洪水"},
    "storms": {"fr": "tempêtes", "es": "tormentas", "ar": "عواصف",
               "ru": "штормы", "zh": "风暴"},
    "wildfires": {"fr": "feux de forêt", "es": "incendios forestales",
                  "ar": "حرائق الغابات", "ru": "лесные пожары", "zh": "野火"},
    "landslides": {"fr": "glissements de terrain", "es": "deslizamientos de tierra",
                   "ar": "انهيارات أرضية", "ru": "оползни", "zh": "山体滑坡"},
    "cyclones": {"fr": "cyclones", "es": "ciclones", "ar": "أعاصير",
                 "ru": "циклоны", "zh": "气旋"},
    "earthquakes": {"fr": "séismes", "es": "terremotos", "ar": "زلازل",
                    "ru": "землетрясения", "zh": "地震"},
    "tornadoes": {"fr": "tornades", "es": "tornados", "ar": "أعاصير قمعية",
                  "ru": "торнадо", "zh": "龙卷风"},
    "drought": {"fr": "sécheresse", "es": "sequía", "ar": "جفاف",
                "ru": "засуха", "zh": "干旱"},
    "hailstorms": {"fr": "tempêtes de grêle", "es": "granizadas",
                   "ar": "عواصف البَرَد", "ru": "град", "zh": "冰雹"},
    "erosion": {"fr": "érosion", "es": "erosión", "ar": "تآكل التربة",
                "ru": "эрозия", "zh": "侵蚀"},
    "tsunami": {"fr": "tsunami", "es": "tsunami", "ar": "تسونامي",
                "ru": "цунами", "zh": "海啸"},
    "storm surges": {"fr": "ondes de tempête", "es": "marejadas ciclónicas",
                     "ar": "عواصف مدّية", "ru": "штормовые нагоны", "zh": "风暴潮"},
    "volcanic eruptions": {"fr": "éruptions volcaniques", "es": "erupciones volcánicas",
                           "ar": "ثورات بركانية", "ru": "извержения вулканов",
                           "zh": "火山喷发"},
    "rising sea levels": {"fr": "élévation du niveau de la mer",
                          "es": "aumento del nivel del mar",
                          "ar": "ارتفاع مستوى سطح البحر",
                          "ru": "повышение уровня моря", "zh": "海平面上升"},
    "sinkholes": {"fr": "effondrements de terrain", "es": "socavones",
                  "ar": "انهيارات أرضية مفاجئة", "ru": "провалы грунта",
                  "zh": "地面塌陷"},
    "dam releases": {"fr": "lâchers de barrage", "es": "descargas de presas",
                     "ar": "تصريف السدود", "ru": "сбросы воды из плотин",
                     "zh": "水坝泄洪"},
    "blizzards": {"fr": "blizzards", "es": "ventiscas", "ar": "عواصف ثلجية",
                  "ru": "метели", "zh": "暴风雪"},
    "sandstorms": {"fr": "tempêtes de sable", "es": "tormentas de arena",
                   "ar": "عواصف رملية", "ru": "песчаные бури", "zh": "沙尘暴"},
    "avalanches": {"fr": "avalanches", "es": "avalanchas", "ar": "انهيارات ثلجية",
                   "ru": "лавины", "zh": "雪崩"},
    "extreme cold": {"fr": "froid extrême", "es": "frío extremo",
                     "ar": "موجات برد شديدة", "ru": "аномальные холода",
                     "zh": "极寒"},
}


# "JNIM and Islamic State" left an English conjunction sitting inside an
# otherwise-translated sentence, which reads worse than not translating at all.
CONJ = {"fr": " et ", "es": " y ", "ar": " و ", "ru": " и ", "zh": "、"}


def _actors(a, lang):
    if lang == "en":
        return a
    parts = [p.strip() for p in a.replace(" and ", "|").split("|")]
    parts = [re.sub(r"^the\s+", "", p, flags=re.I) for p in parts]
    return CONJ.get(lang, " and ").join(parts)


def translate_example(text, lang):
    """Translate a generated example, leaving proper nouns alone."""
    if lang == "en":
        return text, True
    if text in HAZ:
        return HAZ[text].get(lang, text), lang in HAZ[text]
    for src, tr in FRAG.items():
        if "{}" not in src:
            if text == src:
                return tr.get(lang, text), lang in tr
            continue
        stem = src.split("{}")[0]
        if text.startswith(stem):
            actors = text[len(stem):]
            t = tr.get(lang)
            return ((t.format(_actors(actors, lang)), True) if t
                    else (text, False))
    return text, False       # untranslated: flagged in the output
