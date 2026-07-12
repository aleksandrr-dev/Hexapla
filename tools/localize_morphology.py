# -*- coding: utf-8 -*-
"""Inject localized interlinear morphology terms into every strings.xml.

Companion to the 1.4.2 Interlinear.kt change: the Robinson/OSHM decoders
now assemble their output from string resources instead of hardcoded
English. This script holds the curated terminology table (12 locales)
and writes the <string> entries into each res/values*/strings.xml,
before </resources>. Idempotent: a file already containing morph_noun
is skipped.

Terminology notes:
- Russian follows established seminary usage (аорист, действительный
  залог, изъявительное наклонение; Hebrew stems transliterated in
  Cyrillic: каль, нифаль, хифиль…).
- French Hebrew conjugations use accompli/inaccompli (standard in
  French Hebrew grammars); Greek keeps parfait etc.
- Chinese follows the CBOL/信望爱 parsing vocabulary (关身语态 middle,
  不定过去时 aorist, 关身形主动意 middle deponent, 所有格/间接受格/直接受格
  cases); Traditional uses the Taiwan forms (假設語氣 subjunctive).
- Japanese follows NT-Greek textbook usage (直説法, 希求法, アオリスト);
  Hebrew stems in katakana.
- Hebrew binyan names stay in the scholarly Latin transliteration for
  Latin-script locales (German capitalizes them as nouns), Cyrillic for
  Russian, katakana for Japanese; Chinese keeps Latin (common in
  Chinese-language grammars).
- The values of morph_second and morph_aramaic_prefix carry trailing
  spaces (quoted in XML); the CJK values deliberately do not.
"""
import io
import os
import re
import sys

RES = os.path.join(os.path.dirname(__file__), "..", "app", "src", "main", "res")

# Locale order: en(default), ru, de, es, fr, pt, it, sv, da, ja, zh, zh-Hant
DIRS = ["values", "values-ru", "values-de", "values-es", "values-fr",
        "values-pt", "values-it", "values-sv", "values-da", "values-ja",
        "values-zh", "values-b+zh+Hant"]

T = {
    # ---- shared parts of speech ----
    "morph_noun": ["noun", "существительное", "Substantiv", "sustantivo", "nom", "substantivo", "sostantivo", "substantiv", "substantiv", "名詞", "名词", "名詞"],
    "morph_adjective": ["adjective", "прилагательное", "Adjektiv", "adjetivo", "adjectif", "adjetivo", "aggettivo", "adjektiv", "adjektiv", "形容詞", "形容词", "形容詞"],
    "morph_article": ["article", "артикль", "Artikel", "artículo", "article", "artigo", "articolo", "artikel", "artikel", "冠詞", "冠词", "冠詞"],
    "morph_verb": ["verb", "глагол", "Verb", "verbo", "verbe", "verbo", "verbo", "verb", "verbum", "動詞", "动词", "動詞"],
    "morph_particle": ["particle", "частица", "Partikel", "partícula", "particule", "partícula", "particella", "partikel", "partikel", "小辞", "质词", "質詞"],
    "morph_preposition": ["preposition", "предлог", "Präposition", "preposición", "préposition", "preposição", "preposizione", "preposition", "præposition", "前置詞", "介词", "介詞"],
    "morph_conjunction": ["conjunction", "союз", "Konjunktion", "conjunción", "conjonction", "conjunção", "congiunzione", "konjunktion", "konjunktion", "接続詞", "连词", "連詞"],
    "morph_adverb": ["adverb", "наречие", "Adverb", "adverbio", "adverbe", "advérbio", "avverbio", "adverb", "adverbium", "副詞", "副词", "副詞"],
    "morph_interjection": ["interjection", "междометие", "Interjektion", "interjección", "interjection", "interjeição", "interiezione", "interjektion", "interjektion", "間投詞", "感叹词", "感嘆詞"],
    "morph_pronoun": ["pronoun", "местоимение", "Pronomen", "pronombre", "pronom", "pronome", "pronome", "pronomen", "pronomen", "代名詞", "代词", "代詞"],
    "morph_pron_personal": ["personal pronoun", "личное местоимение", "Personalpronomen", "pronombre personal", "pronom personnel", "pronome pessoal", "pronome personale", "personligt pronomen", "personligt pronomen", "人称代名詞", "人称代词", "人稱代詞"],
    "morph_pron_relative": ["relative pronoun", "относительное местоимение", "Relativpronomen", "pronombre relativo", "pronom relatif", "pronome relativo", "pronome relativo", "relativt pronomen", "relativt pronomen", "関係代名詞", "关系代词", "關係代詞"],
    "morph_pron_reciprocal": ["reciprocal pronoun", "взаимное местоимение", "Reziprokpronomen", "pronombre recíproco", "pronom réciproque", "pronome recíproco", "pronome reciproco", "reciprokt pronomen", "reciprokt pronomen", "相互代名詞", "相互代词", "相互代詞"],
    "morph_pron_demonstrative": ["demonstrative pronoun", "указательное местоимение", "Demonstrativpronomen", "pronombre demostrativo", "pronom démonstratif", "pronome demonstrativo", "pronome dimostrativo", "demonstrativt pronomen", "demonstrativt pronomen", "指示代名詞", "指示代词", "指示代詞"],
    "morph_pron_reflexive": ["reflexive pronoun", "возвратное местоимение", "Reflexivpronomen", "pronombre reflexivo", "pronom réfléchi", "pronome reflexivo", "pronome riflessivo", "reflexivt pronomen", "refleksivt pronomen", "再帰代名詞", "反身代词", "反身代詞"],
    "morph_pron_interrogative": ["interrogative pronoun", "вопросительное местоимение", "Interrogativpronomen", "pronombre interrogativo", "pronom interrogatif", "pronome interrogativo", "pronome interrogativo", "interrogativt pronomen", "interrogativt pronomen", "疑問代名詞", "疑问代词", "疑問代詞"],
    "morph_pron_indefinite": ["indefinite pronoun", "неопределённое местоимение", "Indefinitpronomen", "pronombre indefinido", "pronom indéfini", "pronome indefinido", "pronome indefinito", "indefinit pronomen", "ubestemt pronomen", "不定代名詞", "不定代词", "不定代詞"],
    "morph_pron_correlative": ["correlative pronoun", "соотносительное местоимение", "Korrelativpronomen", "pronombre correlativo", "pronom corrélatif", "pronome correlativo", "pronome correlativo", "korrelativt pronomen", "korrelativt pronomen", "相関代名詞", "关联代词", "關聯代詞"],
    "morph_pron_possessive": ["possessive pronoun", "притяжательное местоимение", "Possessivpronomen", "pronombre posesivo", "pronom possessif", "pronome possessivo", "pronome possessivo", "possessivt pronomen", "possessivt pronomen", "所有代名詞", "物主代词", "物主代詞"],
    "morph_cond_particle": ["conditional particle", "условная частица", "Konditionalpartikel", "partícula condicional", "particule conditionnelle", "partícula condicional", "particella condizionale", "konditionalpartikel", "konditionalpartikel", "条件小辞", "条件质词", "條件質詞"],
    "morph_aramaic_word": ["Aramaic word", "арамейское слово", "aramäisches Wort", "palabra aramea", "mot araméen", "palavra aramaica", "parola aramaica", "arameiskt ord", "aramaisk ord", "アラム語", "亚兰文词", "亞蘭文詞"],
    "morph_hebrew_word": ["Hebrew word", "еврейское слово", "hebräisches Wort", "palabra hebrea", "mot hébreu", "palavra hebraica", "parola ebraica", "hebreiskt ord", "hebraisk ord", "ヘブライ語", "希伯来文词", "希伯來文詞"],
    # ---- gender / number / person (shared Greek+Hebrew) ----
    "morph_masculine": ["masculine", "мужской род", "maskulin", "masculino", "masculin", "masculino", "maschile", "maskulinum", "maskulinum", "男性", "阳性", "陽性"],
    "morph_feminine": ["feminine", "женский род", "feminin", "femenino", "féminin", "feminino", "femminile", "femininum", "femininum", "女性", "阴性", "陰性"],
    "morph_neuter": ["neuter", "средний род", "neutrum", "neutro", "neutre", "neutro", "neutro", "neutrum", "neutrum", "中性", "中性", "中性"],
    "morph_common": ["common", "общий род", "communis", "común", "commun", "comum", "comune", "gemensamt genus", "fælleskøn", "通性", "通性", "通性"],
    "morph_singular": ["singular", "единственное число", "Singular", "singular", "singulier", "singular", "singolare", "singularis", "singularis", "単数", "单数", "單數"],
    "morph_plural": ["plural", "множественное число", "Plural", "plural", "pluriel", "plural", "plurale", "pluralis", "pluralis", "複数", "复数", "複數"],
    "morph_dual": ["dual", "двойственное число", "Dual", "dual", "duel", "dual", "duale", "dualis", "dualis", "双数", "双数", "雙數"],
    "morph_person_1": ["1st person", "1-е лицо", "1. Person", "1.ª persona", "1re personne", "1.ª pessoa", "1ª persona", "1:a person", "1. person", "一人称", "第一人称", "第一人稱"],
    "morph_person_2": ["2nd person", "2-е лицо", "2. Person", "2.ª persona", "2e personne", "2.ª pessoa", "2ª persona", "2:a person", "2. person", "二人称", "第二人称", "第二人稱"],
    "morph_person_3": ["3rd person", "3-е лицо", "3. Person", "3.ª persona", "3e personne", "3.ª pessoa", "3ª persona", "3:e person", "3. person", "三人称", "第三人称", "第三人稱"],
    # ---- Greek tense ----
    "morph_tense_present": ["present", "настоящее время", "Präsens", "presente", "présent", "presente", "presente", "presens", "præsens", "現在", "现在时", "現在式"],
    "morph_tense_imperfect": ["imperfect", "имперфект", "Imperfekt", "imperfecto", "imparfait", "imperfeito", "imperfetto", "imperfekt", "imperfektum", "未完了過去", "未完成时", "未完成式"],
    "morph_tense_future": ["future", "будущее время", "Futur", "futuro", "futur", "futuro", "futuro", "futurum", "futurum", "未来", "将来时", "未來式"],
    "morph_tense_aorist": ["aorist", "аорист", "Aorist", "aoristo", "aoriste", "aoristo", "aoristo", "aorist", "aorist", "アオリスト", "不定过去时", "不定過去式"],
    "morph_tense_perfect": ["perfect", "перфект", "Perfekt", "perfecto", "parfait", "perfeito", "perfetto", "perfekt", "perfektum", "完了", "完成时", "完成式"],
    "morph_tense_pluperfect": ["pluperfect", "плюсквамперфект", "Plusquamperfekt", "pluscuamperfecto", "plus-que-parfait", "mais-que-perfeito", "piuccheperfetto", "pluskvamperfekt", "pluskvamperfektum", "過去完了", "过去完成时", "過去完成式"],
    "morph_second": ["2nd ", "второй ", "2. ", "2.º ", "2e ", "2.º ", "2º ", "2:a ", "2. ", "第二", "第二", "第二"],
    # ---- Greek voice ----
    "morph_voice_active": ["active", "действительный залог", "Aktiv", "voz activa", "actif", "voz ativa", "attivo", "aktivum", "aktiv", "能動態", "主动语态", "主動語態"],
    "morph_voice_middle": ["middle", "средний залог", "Medium", "voz media", "moyen", "voz média", "medio", "medium", "medium", "中動態", "关身语态", "關身語態"],
    "morph_voice_passive": ["passive", "страдательный залог", "Passiv", "voz pasiva", "passif", "voz passiva", "passivo", "passivum", "passiv", "受動態", "被动语态", "被動語態"],
    "morph_voice_midpass": ["middle/passive", "средний/страдательный залог", "Medium/Passiv", "voz media/pasiva", "moyen/passif", "voz média/passiva", "medio/passivo", "medium/passivum", "medium/passiv", "中受動態", "关身/被动语态", "關身/被動語態"],
    "morph_voice_mid_deponent": ["middle deponent", "отложительный (средний залог)", "Deponens Medium", "deponente (voz media)", "déponent moyen", "depoente (voz média)", "deponente medio", "deponens medium", "deponens medium", "中動デポネント", "关身形主动意", "關身形主動意"],
    "morph_voice_pass_deponent": ["passive deponent", "отложительный (страдательный залог)", "Deponens Passiv", "deponente (voz pasiva)", "déponent passif", "depoente (voz passiva)", "deponente passivo", "deponens passivum", "deponens passiv", "受動デポネント", "被动形主动意", "被動形主動意"],
    "morph_voice_midpass_deponent": ["middle/passive deponent", "отложительный (средний/страдательный)", "Deponens Medium/Passiv", "deponente (voz media/pasiva)", "déponent moyen/passif", "depoente (voz média/passiva)", "deponente medio/passivo", "deponens medium/passivum", "deponens medium/passiv", "中受動デポネント", "关身/被动形主动意", "關身/被動形主動意"],
    "morph_voice_impersonal": ["impersonal active", "безличный действительный", "unpersönliches Aktiv", "voz activa impersonal", "actif impersonnel", "voz ativa impessoal", "attivo impersonale", "opersonligt aktivum", "upersonlig aktiv", "非人称能動態", "无人称主动", "無人稱主動"],
    # ---- Greek mood ----
    "morph_mood_indicative": ["indicative", "изъявительное наклонение", "Indikativ", "indicativo", "indicatif", "indicativo", "indicativo", "indikativ", "indikativ", "直説法", "直说语气", "直說語氣"],
    "morph_mood_subjunctive": ["subjunctive", "сослагательное наклонение", "Konjunktiv", "subjuntivo", "subjonctif", "subjuntivo", "congiuntivo", "konjunktiv", "konjunktiv", "接続法", "虚拟语气", "假設語氣"],
    "morph_mood_optative": ["optative", "желательное наклонение", "Optativ", "optativo", "optatif", "optativo", "ottativo", "optativ", "optativ", "希求法", "祈愿语气", "祈願語氣"],
    "morph_mood_imperative": ["imperative", "повелительное наклонение", "Imperativ", "imperativo", "impératif", "imperativo", "imperativo", "imperativ", "imperativ", "命令法", "命令语气", "命令語氣"],
    "morph_mood_infinitive": ["infinitive", "инфинитив", "Infinitiv", "infinitivo", "infinitif", "infinitivo", "infinito", "infinitiv", "infinitiv", "不定詞", "不定词", "不定詞"],
    "morph_mood_participle": ["participle", "причастие", "Partizip", "participio", "participe", "particípio", "participio", "particip", "participium", "分詞", "分词", "分詞"],
    # ---- Greek case ----
    "morph_case_nominative": ["nominative", "именительный падеж", "Nominativ", "nominativo", "nominatif", "nominativo", "nominativo", "nominativ", "nominativ", "主格", "主格", "主格"],
    "morph_case_genitive": ["genitive", "родительный падеж", "Genitiv", "genitivo", "génitif", "genitivo", "genitivo", "genitiv", "genitiv", "属格", "所有格", "所有格"],
    "morph_case_dative": ["dative", "дательный падеж", "Dativ", "dativo", "datif", "dativo", "dativo", "dativ", "dativ", "与格", "间接受格", "間接受格"],
    "morph_case_accusative": ["accusative", "винительный падеж", "Akkusativ", "acusativo", "accusatif", "acusativo", "accusativo", "ackusativ", "akkusativ", "対格", "直接受格", "直接受格"],
    "morph_case_vocative": ["vocative", "звательный падеж", "Vokativ", "vocativo", "vocatif", "vocativo", "vocativo", "vokativ", "vokativ", "呼格", "呼格", "呼格"],
    # ---- Greek qualifiers ----
    "morph_q_pri": ["proper indeclinable", "несклоняемое имя собственное", "indeklinabler Eigenname", "nombre propio indeclinable", "nom propre indéclinable", "nome próprio indeclinável", "nome proprio indeclinabile", "oböjligt egennamn", "ubøjeligt egennavn", "無変化の固有名詞", "无变格专有名词", "無變格專有名詞"],
    "morph_q_nui": ["numeral indeclinable", "несклоняемое числительное", "indeklinables Zahlwort", "numeral indeclinable", "numéral indéclinable", "numeral indeclinável", "numerale indeclinabile", "oböjligt räkneord", "ubøjeligt talord", "無変化の数詞", "无变格数词", "無變格數詞"],
    "morph_q_li": ["letter indeclinable", "несклоняемая буква", "indeklinabler Buchstabe", "letra indeclinable", "lettre indéclinable", "letra indeclinável", "lettera indeclinabile", "oböjlig bokstav", "ubøjeligt bogstav", "無変化の文字", "无变格字母", "無變格字母"],
    "morph_q_oi": ["other indeclinable", "прочее несклоняемое", "sonstiges Indeklinabile", "otro indeclinable", "autre indéclinable", "outro indeclinável", "altro indeclinabile", "övrigt oböjligt", "andet ubøjeligt", "その他の無変化語", "其他无变格词", "其他無變格詞"],
    "morph_q_negative": ["negative", "отрицательная", "negativ", "negativa", "négatif", "negativa", "negativo", "negerande", "nægtende", "否定", "否定", "否定"],
    "morph_q_interrogative": ["interrogative", "вопросительная", "interrogativ", "interrogativa", "interrogatif", "interrogativa", "interrogativo", "frågande", "spørgende", "疑問", "疑问", "疑問"],
    "morph_q_crasis": ["crasis", "красис", "Krasis", "crasis", "crase", "crase", "crasi", "krasis", "krasis", "クラシス", "合音词", "合音詞"],
    "morph_q_superlative": ["superlative", "превосходная степень", "Superlativ", "superlativo", "superlatif", "superlativo", "superlativo", "superlativ", "superlativ", "最上級", "最高级", "最高級"],
    "morph_q_comparative": ["comparative", "сравнительная степень", "Komparativ", "comparativo", "comparatif", "comparativo", "comparativo", "komparativ", "komparativ", "比較級", "比较级", "比較級"],
    "morph_q_att": ["Attic form", "аттическая форма", "attische Form", "forma ática", "forme attique", "forma ática", "forma attica", "attisk form", "attisk form", "アッティカ形", "阿提卡形式", "阿提卡形式"],
    "morph_q_abb": ["abbreviated", "сокращённая форма", "abgekürzt", "forma abreviada", "forme abrégée", "forma abreviada", "forma abbreviata", "förkortad form", "forkortet form", "短縮形", "缩略形式", "縮略形式"],
    "morph_q_attached": ["particle attached", "с приросшей частицей", "mit angehängter Partikel", "con partícula adjunta", "avec particule attachée", "com partícula anexa", "con particella annessa", "med vidhängd partikel", "med tilføjet partikel", "付加小辞つき", "附有质词", "附有質詞"],
    # ---- Hebrew/Aramaic stems (binyanim) ----
    "morph_stem_qal": ["qal", "каль", "Qal", "qal", "qal", "qal", "qal", "qal", "qal", "カル", "qal", "qal"],
    "morph_stem_niphal": ["niphal", "нифаль", "Niphal", "niphal", "niphal", "niphal", "niphal", "niphal", "niphal", "ニファル", "niphal", "niphal"],
    "morph_stem_piel": ["piel", "пиэль", "Piel", "piel", "piel", "piel", "piel", "piel", "piel", "ピエル", "piel", "piel"],
    "morph_stem_pual": ["pual", "пуаль", "Pual", "pual", "pual", "pual", "pual", "pual", "pual", "プアル", "pual", "pual"],
    "morph_stem_hiphil": ["hiphil", "хифиль", "Hiphil", "hiphil", "hiphil", "hiphil", "hiphil", "hiphil", "hiphil", "ヒフィル", "hiphil", "hiphil"],
    "morph_stem_hophal": ["hophal", "хофаль", "Hophal", "hophal", "hophal", "hophal", "hophal", "hophal", "hophal", "ホファル", "hophal", "hophal"],
    "morph_stem_hithpael": ["hithpael", "хитпаэль", "Hithpael", "hithpael", "hithpael", "hithpael", "hithpael", "hithpael", "hithpael", "ヒトパエル", "hithpael", "hithpael"],
    "morph_stem_polel": ["polel", "полель", "Polel", "polel", "polel", "polel", "polel", "polel", "polel", "ポレル", "polel", "polel"],
    "morph_stem_polal": ["polal", "полаль", "Polal", "polal", "polal", "polal", "polal", "polal", "polal", "ポラル", "polal", "polal"],
    "morph_stem_hithpolel": ["hithpolel", "хитполель", "Hithpolel", "hithpolel", "hithpolel", "hithpolel", "hithpolel", "hithpolel", "hithpolel", "ヒトポレル", "hithpolel", "hithpolel"],
    "morph_stem_poel": ["poel", "поэль", "Poel", "poel", "poel", "poel", "poel", "poel", "poel", "ポエル", "poel", "poel"],
    "morph_stem_poal": ["poal", "поаль", "Poal", "poal", "poal", "poal", "poal", "poal", "poal", "ポアル", "poal", "poal"],
    "morph_stem_palel": ["palel", "палель", "Palel", "palel", "palel", "palel", "palel", "palel", "palel", "パレル", "palel", "palel"],
    "morph_stem_pulal": ["pulal", "пулаль", "Pulal", "pulal", "pulal", "pulal", "pulal", "pulal", "pulal", "プラル", "pulal", "pulal"],
    "morph_stem_qal_passive": ["qal passive", "каль пассивный", "Qal Passiv", "qal pasivo", "qal passif", "qal passivo", "qal passivo", "qal passivum", "qal passiv", "カル受動", "qal 被动", "qal 被動"],
    "morph_stem_pilpel": ["pilpel", "пильпель", "Pilpel", "pilpel", "pilpel", "pilpel", "pilpel", "pilpel", "pilpel", "ピルペル", "pilpel", "pilpel"],
    "morph_stem_polpal": ["polpal", "польпаль", "Polpal", "polpal", "polpal", "polpal", "polpal", "polpal", "polpal", "ポルパル", "polpal", "polpal"],
    "morph_stem_hithpalpel": ["hithpalpel", "хитпальпель", "Hithpalpel", "hithpalpel", "hithpalpel", "hithpalpel", "hithpalpel", "hithpalpel", "hithpalpel", "ヒトパルペル", "hithpalpel", "hithpalpel"],
    "morph_stem_nithpael": ["nithpael", "нитпаэль", "Nithpael", "nithpael", "nithpael", "nithpael", "nithpael", "nithpael", "nithpael", "ニトパエル", "nithpael", "nithpael"],
    "morph_stem_pealal": ["pealal", "пеалаль", "Pealal", "pealal", "pealal", "pealal", "pealal", "pealal", "pealal", "ペアラル", "pealal", "pealal"],
    "morph_stem_pilel": ["pilel", "пилель", "Pilel", "pilel", "pilel", "pilel", "pilel", "pilel", "pilel", "ピレル", "pilel", "pilel"],
    "morph_stem_hothpaal": ["hothpaal", "хотпааль", "Hothpaal", "hothpaal", "hothpaal", "hothpaal", "hothpaal", "hothpaal", "hothpaal", "ホトパアル", "hothpaal", "hothpaal"],
    "morph_stem_tiphil": ["tiphil", "тифиль", "Tiphil", "tiphil", "tiphil", "tiphil", "tiphil", "tiphil", "tiphil", "ティフィル", "tiphil", "tiphil"],
    "morph_stem_hishtaphel": ["hishtaphel", "хиштафель", "Hishtaphel", "hishtaphel", "hishtaphel", "hishtaphel", "hishtaphel", "hishtaphel", "hishtaphel", "ヒシュタフェル", "hishtaphel", "hishtaphel"],
    "morph_stem_nithpalel": ["nithpalel", "нитпалель", "Nithpalel", "nithpalel", "nithpalel", "nithpalel", "nithpalel", "nithpalel", "nithpalel", "ニトパレル", "nithpalel", "nithpalel"],
    "morph_stem_nithpoel": ["nithpoel", "нитпоэль", "Nithpoel", "nithpoel", "nithpoel", "nithpoel", "nithpoel", "nithpoel", "nithpoel", "ニトポエル", "nithpoel", "nithpoel"],
    "morph_stem_hithpoel": ["hithpoel", "хитпоэль", "Hithpoel", "hithpoel", "hithpoel", "hithpoel", "hithpoel", "hithpoel", "hithpoel", "ヒトポエル", "hithpoel", "hithpoel"],
    "morph_stem_peal": ["peal", "пеаль", "Peal", "peal", "peal", "peal", "peal", "peal", "peal", "ペアル", "peal", "peal"],
    "morph_stem_peil": ["peil", "пеиль", "Peil", "peil", "peil", "peil", "peil", "peil", "peil", "ペイル", "peil", "peil"],
    "morph_stem_hithpeel": ["hithpeel", "хитпеэль", "Hithpeel", "hithpeel", "hithpeel", "hithpeel", "hithpeel", "hithpeel", "hithpeel", "ヒトペエル", "hithpeel", "hithpeel"],
    "morph_stem_saphel": ["saphel", "сафель", "Saphel", "saphel", "saphel", "saphel", "saphel", "saphel", "saphel", "サフェル", "saphel", "saphel"],
    "morph_stem_pael": ["pael", "паэль", "Pael", "pael", "pael", "pael", "pael", "pael", "pael", "パエル", "pael", "pael"],
    "morph_stem_ithpaal": ["ithpaal", "итпааль", "Ithpaal", "ithpaal", "ithpaal", "ithpaal", "ithpaal", "ithpaal", "ithpaal", "イトパアル", "ithpaal", "ithpaal"],
    "morph_stem_ithpeel": ["ithpeel", "итпеэль", "Ithpeel", "ithpeel", "ithpeel", "ithpeel", "ithpeel", "ithpeel", "ithpeel", "イトペエル", "ithpeel", "ithpeel"],
    # ---- Hebrew conjugations ----
    "morph_hconj_perfect": ["perfect", "перфект", "Perfekt", "perfecto", "accompli", "perfeito", "perfetto", "perfekt", "perfektum", "完了形", "完成式", "完成式"],
    "morph_hconj_seq_perfect": ["sequential perfect", "перфект с вав последовательным", "Perfectum consecutivum", "perfecto consecutivo", "accompli inverti", "perfeito consecutivo", "perfetto consecutivo", "perfekt konsekutiv", "perfektum konsekutiv", "ワウ継続完了形", "连续完成式", "連續完成式"],
    "morph_hconj_imperfect": ["imperfect", "имперфект", "Imperfekt", "imperfecto", "inaccompli", "imperfeito", "imperfetto", "imperfekt", "imperfektum", "未完了形", "未完成式", "未完成式"],
    "morph_hconj_seq_imperfect": ["sequential imperfect", "имперфект с вав последовательным", "Imperfectum consecutivum", "imperfecto consecutivo", "inaccompli inverti", "imperfeito consecutivo", "imperfetto consecutivo", "imperfekt konsekutiv", "imperfektum konsekutiv", "ワウ継続未完了形", "连续未完成式", "連續未完成式"],
    "morph_hconj_cohortative": ["cohortative", "когортатив", "Kohortativ", "cohortativo", "cohortatif", "coortativo", "coortativo", "kohortativ", "kohortativ", "コホルタティブ", "鼓励式", "鼓勵式"],
    "morph_hconj_jussive": ["jussive", "юссив", "Jussiv", "yusivo", "jussif", "jussivo", "iussivo", "jussiv", "jussiv", "ユッシブ", "祈愿式", "祈願式"],
    "morph_hconj_imperative": ["imperative", "императив", "Imperativ", "imperativo", "impératif", "imperativo", "imperativo", "imperativ", "imperativ", "命令形", "命令式", "命令式"],
    "morph_hconj_participle": ["participle", "причастие", "Partizip", "participio", "participe", "particípio", "participio", "particip", "participium", "分詞", "分词", "分詞"],
    "morph_hconj_passive_participle": ["passive participle", "страдательное причастие", "Partizip Passiv", "participio pasivo", "participe passif", "particípio passivo", "participio passivo", "passivt particip", "passivt participium", "受動分詞", "被动分词", "被動分詞"],
    "morph_hconj_inf_absolute": ["infinitive absolute", "абсолютный инфинитив", "Infinitivus absolutus", "infinitivo absoluto", "infinitif absolu", "infinitivo absoluto", "infinito assoluto", "infinitivus absolutus", "infinitivus absolutus", "独立不定詞", "独立不定词", "獨立不定詞"],
    "morph_hconj_inf_construct": ["infinitive construct", "сопряжённый инфинитив", "Infinitivus constructus", "infinitivo constructo", "infinitif construit", "infinitivo construto", "infinito costrutto", "infinitivus constructus", "infinitivus constructus", "合成不定詞", "附属不定词", "附屬不定詞"],
    # ---- Hebrew states ----
    "morph_state_absolute": ["absolute", "абсолютное состояние", "Status absolutus", "estado absoluto", "état absolu", "estado absoluto", "stato assoluto", "status absolutus", "status absolutus", "独立形", "独立形", "獨立形"],
    "morph_state_construct": ["construct", "сопряжённое состояние", "Status constructus", "estado constructo", "état construit", "estado construto", "stato costrutto", "status constructus", "status constructus", "合成形", "附属形", "附屬形"],
    "morph_state_determined": ["determined", "определённое состояние", "determiniert", "determinado", "déterminé", "determinado", "determinato", "determinerad", "determineret", "限定形", "限定形", "限定形"],
    # ---- Hebrew particles and word classes ----
    "morph_prep_article": ["preposition + article", "предлог + артикль", "Präposition + Artikel", "preposición + artículo", "préposition + article", "preposição + artigo", "preposizione + articolo", "preposition + artikel", "præposition + artikel", "前置詞＋冠詞", "介词＋冠词", "介詞＋冠詞"],
    "morph_affirmation": ["affirmation", "утвердительная частица", "Affirmationspartikel", "partícula afirmativa", "particule affirmative", "partícula afirmativa", "particella affermativa", "bekräftelsepartikel", "bekræftelsespartikel", "断定辞", "肯定词", "肯定詞"],
    "morph_exhortation": ["exhortation", "побудительная частица", "Aufforderungspartikel", "partícula exhortativa", "particule exhortative", "partícula exortativa", "particella esortativa", "uppmaningspartikel", "opfordringspartikel", "勧告辞", "劝勉词", "勸勉詞"],
    "morph_int_particle": ["interrogative particle", "вопросительная частица", "Fragepartikel", "partícula interrogativa", "particule interrogative", "partícula interrogativa", "particella interrogativa", "frågepartikel", "spørgepartikel", "疑問辞", "疑问词", "疑問詞"],
    "morph_neg_particle": ["negative particle", "отрицательная частица", "Negationspartikel", "partícula negativa", "particule négative", "partícula negativa", "particella negativa", "negationspartikel", "nægtelsespartikel", "否定辞", "否定词", "否定詞"],
    "morph_obj_marker": ["direct object marker", "показатель прямого дополнения", "Akkusativpartikel", "marcador de objeto directo", "marqueur d'objet direct", "marcador de objeto direto", "marcatore dell'oggetto diretto", "objektsmarkör", "objektsmarkør", "直接目的語の標識", "直接宾语标记", "直接賓語標記"],
    "morph_rel_particle": ["relative particle", "относительная частица", "Relativpartikel", "partícula relativa", "particule relative", "partícula relativa", "particella relativa", "relativpartikel", "relativpartikel", "関係辞", "关系词", "關係詞"],
    "morph_proper_noun": ["proper noun", "имя собственное", "Eigenname", "nombre propio", "nom propre", "nome próprio", "nome proprio", "egennamn", "egennavn", "固有名詞", "专有名词", "專有名詞"],
    "morph_gentilic_noun": ["gentilic noun", "название народа", "Völkername", "nombre gentilicio", "nom gentilé", "nome gentílico", "nome etnico", "folkslagsnamn", "folkeslagsnavn", "民族名詞", "族名", "族名"],
    "morph_cardinal": ["cardinal number", "количественное числительное", "Kardinalzahl", "número cardinal", "nombre cardinal", "número cardinal", "numero cardinale", "grundtal", "mængdetal", "基数詞", "基数词", "基數詞"],
    "morph_ordinal": ["ordinal number", "порядковое числительное", "Ordinalzahl", "número ordinal", "nombre ordinal", "número ordinal", "numero ordinale", "ordningstal", "ordenstal", "序数詞", "序数词", "序數詞"],
    "morph_gentilic_adj": ["gentilic adjective", "прилагательное от названия народа", "Völkername-Adjektiv", "adjetivo gentilicio", "adjectif gentilé", "adjetivo gentílico", "aggettivo etnico", "folkslagsadjektiv", "folkeslagsadjektiv", "民族形容詞", "族名形容词", "族名形容詞"],
    "morph_suffix": ["suffix", "суффикс", "Suffix", "sufijo", "suffixe", "sufixo", "suffisso", "suffix", "suffiks", "接尾辞", "后缀", "後綴"],
    "morph_suffix_pron": ["pronominal suffix", "местоименный суффикс", "Pronominalsuffix", "sufijo pronominal", "suffixe pronominal", "sufixo pronominal", "suffisso pronominale", "pronominalsuffix", "pronominalsuffiks", "代名詞接尾辞", "代词后缀", "代詞後綴"],
    "morph_suffix_dir": ["directional suffix", "суффикс направления", "Richtungssuffix", "sufijo direccional", "suffixe directionnel", "sufixo direcional", "suffisso direzionale", "riktningssuffix", "retningssuffiks", "方向接尾辞", "方向后缀", "方向後綴"],
    "morph_paragogic_he": ["paragogic he", "парагогическое хе", "paragogisches He", "he paragógica", "hé paragogique", "he paragógico", "he paragogico", "paragogiskt he", "paragogisk he", "語尾添加のヘー", "附加字母 He", "附加字母 He"],
    "morph_paragogic_nun": ["paragogic nun", "парагогический нун", "paragogisches Nun", "nun paragógica", "noun paragogique", "nun paragógico", "nun paragogico", "paragogiskt nun", "paragogisk nun", "語尾添加のヌン", "附加字母 Nun", "附加字母 Nun"],
    # ---- prefix for Aramaic verses (trailing space/colon included) ----
    "morph_aramaic_prefix": ["Aramaic: ", "арамейский: ", "Aramäisch: ", "arameo: ", "araméen : ", "aramaico: ", "aramaico: ", "arameiska: ", "aramaisk: ", "アラム語：", "亚兰文：", "亞蘭文："],
}


def esc(v):
    v = v.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    v = v.replace("'", "\\'")
    # Trailing/leading spaces survive only inside quotes in Android XML.
    if v != v.strip():
        v = '"%s"' % v
    return v


def main():
    n = len(DIRS)
    for vals in T.values():
        assert len(vals) == n, vals
    for i, d in enumerate(DIRS):
        path = os.path.join(RES, d, "strings.xml")
        with io.open(path, encoding="utf-8") as f:
            xml = f.read()
        if "morph_noun" in xml:
            print("skip (already localized):", d)
            continue
        block = ["    <!-- Interlinear morphology (Interlinear.kt decoders) -->"]
        for key, vals in T.items():
            block.append('    <string name="%s">%s</string>' % (key, esc(vals[i])))
        xml = xml.replace("</resources>", "\n".join(block) + "\n</resources>")
        with io.open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(xml)
        print("wrote %d strings: %s" % (len(T), d))


if __name__ == "__main__":
    sys.exit(main())
