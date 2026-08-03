"""Scene-mood map: which musical bed plays under which passage.

Emits app/src/main/assets/mood_map.json for the scene-matched background
music feature (tools/MUSIC_MOOD_PLAN.md).

⚠⚠ CANONICAL KJV COORDINATES ONLY ⚠⚠
Every key in this file and in the emitted JSON is a CANONICAL KJV
(book, chapter[, verse]) coordinate — 0-based book index, and 0-BASED
chapter/verse in the OUTPUT (authored 1-based here, converted on the way
out, exactly like build_chrono_plan.py emits its 1-based chapter tokens).
The app must pivot the displayed translation's own numbering through
VerseMap before looking a mood up. Synodal/Elizabeth psalms are LXX
numbered, Luther/WLC use Masoretic bounds, Karoli keeps Calvin numbering
— a map keyed to the displayed numbering would hand Psalm 23 the wrong
mood in Russian. This is the same defect class already fixed three times
here (plan days 2464f04, bookmarks 845f588, notes/highlights in 1.4.2).

RESOLUTION ORDER (later tiers win; this is the contract the app implements):
  1. book default        — 66 canon books + an apocrypha default
  2. chapter-range override
  3. iconic anchor       — may carry verse-level turns inside one chapter

Apocrypha (book index >= 66) resolve through the apocrypha default (plus a
few per-book overrides). Books absent or empty in a given translation are
simply never asked for; nothing here indexes into a translation's arrays,
so an empty slot cannot throw.

★★ TIER 3 REQUIRES HUMAN REVIEW BEFORE SHIPPING ★★
The plan's review gate applies to the ANCHORS table below and to every
verse-level turn in it. Tiers 1-2 are drafted and spot-checked; tier 3 is
the acceptance criterion and a human reads it. The verse indices of the
turns ARE machine-verified against the KJV text (VERSE_WITNESSES), so a
reviewer is judging mood choices, not off-by-one errors.

OPEN QUESTIONS the drafter could not settle (see also the note strings):
  · Judges 19-21 (the Levite's concubine) is `lament` here; `silence` is
    arguably stronger and the plan explicitly blesses silence.
  · Lamentations: `silence` is applied to ch 5 only. Ch 2 is at least as
    graphic and a reviewer may want it silent too.
  · Psalm 88 ("the darkest psalm") — `lament`, but a candidate for silence.
  · Resurrection chapters (Mt 28, Mk 16, Lk 24, Jn 20) are all `praise`
    for consistency; Lk 24 (Emmaus) reads quieter and could be `hope`.
  · Jonah 2 — thanksgiving sung out of distress; `lament` chosen for the
    sound, `hope` is defensible.
  · 1 Kings 19 — `awe` for the still small voice, though the chapter opens
    in Elijah's despair.
  · Philippians 2 — the kenosis hymn: `praise` chosen over `awe`.
  · Mt 27 / Mk 15: silence runs from the darkness to the end of the
    chapter, i.e. over the burial too. A reviewer may want `lament` there.
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "app", "src", "main", "assets")
KJV = os.path.join(ASSETS, "bibles", "en_kjv.json")
OUT = os.path.join(ASSETS, "mood_map.json")

# Canonical book order of the app's grid (= en_kjv.json order).
BOOKS = ("Gen Exo Lev Num Deu Jos Jdg Rut 1Sa 2Sa 1Ki 2Ki 1Ch 2Ch Ezr Neh "
         "Est Job Psa Pro Ecc Sng Isa Jer Lam Eze Dan Hos Joe Amo Oba Jon "
         "Mic Nah Hab Zep Hag Zec Mal Mat Mar Luk Jhn Act Rom 1Co 2Co Gal "
         "Eph Phl Col 1Th 2Th 1Ti 2Ti Tit Phm Heb Jas 1Pe 2Pe 1Jo 2Jo 3Jo "
         "Jde Rev "
         # apocrypha slots, indexes 66..82 (order fixed by the app's grid)
         "1Es 2Es Tob Jdt Wis Sir Bar LJe Man 1Ma 2Ma 3Ma AEs PrA Sus Bel "
         "Lao").split()
IDX = {a: i for i, a in enumerate(BOOKS)}

# The taxonomy, verbatim from MUSIC_MOOD_PLAN.md, plus `silence`.
# Do not invent moods: every id used below must appear here.
MOODS = ("awe", "narrative", "lament", "judgment", "praise", "wisdom",
         "hope", "passion", "tender", "silence")

# ---------------------------------------------------------------- tier 1
# Per-book default. Obvious rows carry no comment; anything that is a
# judgment call is justified inline.
BOOK_DEFAULT = {
    "Gen": "narrative",
    "Exo": "narrative",
    "Lev": "narrative",   # ritual law: neutral prose bed, not `wisdom`
    "Num": "narrative",
    "Deu": "narrative",
    "Jos": "narrative",
    "Jdg": "narrative",
    "Rut": "tender",      # a short pastoral idyll end to end
    "1Sa": "narrative",
    "2Sa": "narrative",
    "1Ki": "narrative",
    "2Ki": "narrative",
    "1Ch": "narrative",
    "2Ch": "narrative",
    "Ezr": "narrative",
    "Neh": "narrative",
    "Est": "narrative",
    "Job": "lament",      # the dialogue of suffering is the bulk of it
    "Psa": "praise",      # densely overridden below; praise is the residue
    "Pro": "wisdom",
    "Ecc": "wisdom",
    "Sng": "tender",
    "Isa": "judgment",    # true of 1-39; 40-66 overridden wholesale
    "Jer": "judgment",
    "Lam": "lament",
    "Eze": "judgment",
    "Dan": "narrative",   # court narrative dominates; visions overridden
    "Hos": "judgment",
    "Joe": "judgment",
    "Amo": "judgment",    # the restoration is only 9:11-15 — not a book mood
    "Oba": "judgment",
    "Jon": "narrative",
    "Mic": "judgment",
    "Nah": "judgment",
    "Hab": "lament",      # chs 1-2 are the prophet's complaint
    "Zep": "judgment",
    "Hag": "hope",        # "I am with you": rebuilding, not threat
    "Zec": "hope",
    "Mal": "judgment",
    "Mat": "narrative",
    "Mar": "narrative",
    "Luk": "narrative",
    "Jhn": "narrative",
    "Act": "narrative",
    # The didactic epistles: the taxonomy has no "teaching" mood, and
    # `wisdom` (reflective, aphoristic) is its nearest neighbour. Chosen
    # deliberately so exposition does not default to `narrative`.
    "Rom": "wisdom",
    "1Co": "wisdom",
    "2Co": "wisdom",
    "Gal": "wisdom",
    "Eph": "wisdom",
    "Phl": "hope",        # the joy epistle
    "Col": "wisdom",
    "1Th": "hope",        # comfort concerning them which are asleep
    "2Th": "wisdom",
    "1Ti": "wisdom",
    "2Ti": "wisdom",
    "Tit": "wisdom",
    "Phm": "tender",      # a personal appeal, one chapter long
    "Heb": "wisdom",
    "Jas": "wisdom",
    "1Pe": "hope",        # written to strangers under trial
    "2Pe": "wisdom",
    "1Jo": "tender",      # "my little children" — the intimate epistle
    "2Jo": "tender",
    "3Jo": "tender",
    "Jde": "judgment",
    "Rev": "judgment",
}

# Apocrypha slots (book index >= 66). One default, plus per-book overrides
# where a whole book is plainly a different genre. Present so that a
# translation carrying these slots (vul, lut, kxii, glk...) never falls
# through to nothing.
# ⚠⚠ APOCRYPHA ARE DELIBERATELY BOOK-LEVEL ONLY — no ranges, no anchors.
# Not an oversight, and please do not "finish" it by adding chapter overrides.
# The canon sits on the KJV grid and pivots through VerseMap, so a canonical
# chapter number means the same passage in every translation. The apocrypha do
# NOT: the arrangements genuinely differ between the KJV slots, the Vulgate,
# the Slavonic and Luther, and versemap.json does not map them (Esther 10:4-16:24
# and Daniel 13-14 are recorded there as unmapped additions). Measured across
# the shipped assets, five apocrypha books have MORE chapters in some
# translation than in the KJV slot — Church Slavonic carries 3 Maccabees at 7
# chapters where the KJV slot is empty, and Glück has 2 chapters where the KJV
# has 1. A chapter-level override keyed to "canonical apocrypha" would
# therefore land on a different passage depending on what the reader has open.
# A book-level mood is translation-agnostic and cannot be wrong that way.
# The four single-chapter books (Manasses, Azariah, Susanna, Bel) get chapter
# precision for free, because the book IS the chapter.
APOCRYPHA_DEFAULT = "narrative"
APOCRYPHA_BOOK = {
    "Wis": "wisdom",
    "Sir": "wisdom",
    "Bar": "lament",      # exilic confession and lament over Jerusalem
    "LJe": "judgment",    # a polemic against idols
    "Man": "lament",      # a penitential prayer
    "PrA": "praise",      # the Song of the Three Children
    # 2 Esdras is overwhelmingly apocalyptic — the eagle vision, the woes, the
    # signs of the end — and reads far closer to Revelation than to the
    # chronicle of 1 Esdras beside it.
    "2Es": "judgment",
}

# --------------------------------------------------------- track pins
# A specific TRACK for a specific chapter, overriding the mood's normal pool.
# Reserved for the rare case where one recording belongs to one passage and
# nowhere else — not a way to hand-pick music generally, which would defeat
# the mood system.
#
# ★ Dalitz's ricercar is built on the GENEVAN PSALM TUNE FOR PSALM 143, so
# under a reading of Psalm 143 the bed is literally that psalm's own melody.
# It is also the only genuine solo-lute recording in the whole catalogue with
# a clean grant (CC BY-SA 4.0; composer = performer = uploader). At 0:57
# against roughly 1:33 of narration it loops once, which is acceptable for a
# short contemplative piece and is why the pin carries `loop`.
# ⚠ His other five ricercars (Psalms 5, 65, 96, 132, 138) exist only as SCORES.
# If a recording of any of them ever appears, pin it here the same way.
TRACK_PINS = [
    ("Psa", 143, "dalitz_ricercar_ps143",
     "lute ricercar on the Genevan tune for this very psalm"),
]

# ---------------------------------------------------------------- tier 2
# (book, first chapter, last chapter, mood, why) — 1-BASED, inclusive.
# Departures from the book default only. No two entries may overlap.
RANGES = [
    ("Gen", 1, 1, "awe", "creation"),
    ("Gen", 2, 2, "tender", "the garden; the making of the woman"),
    ("Gen", 3, 3, "lament", "the fall and the expulsion"),
    ("Gen", 6, 9, "judgment", "the flood"),
    ("Gen", 15, 15, "hope", "the covenant: 'so shall thy seed be'"),
    ("Gen", 19, 19, "judgment", "Sodom"),
    ("Gen", 22, 22, "passion", "the binding of Isaac — the type of the cross"),
    ("Gen", 23, 23, "lament", "Sarah's death and burial"),
    ("Gen", 28, 28, "awe", "Jacob's ladder: 'this is the gate of heaven'"),
    ("Gen", 32, 32, "awe", "Peniel: 'I have seen God face to face'"),
    ("Gen", 37, 37, "lament", "Joseph sold; Jacob's mourning"),
    ("Gen", 45, 45, "tender", "Joseph makes himself known, weeping"),
    ("Gen", 50, 50, "lament", "the death and burial of Jacob"),

    ("Exo", 3, 3, "awe", "the burning bush; I AM"),
    ("Exo", 7, 11, "judgment", "the plagues"),
    ("Exo", 12, 12, "passion", "the Passover lamb and the blood on the door"),
    ("Exo", 14, 14, "awe", "the sea divided"),
    ("Exo", 15, 15, "praise", "the song of Moses and Miriam"),
    ("Exo", 19, 20, "awe", "Sinai; the ten commandments"),
    ("Exo", 24, 24, "awe", "'they saw the God of Israel'"),
    ("Exo", 32, 32, "judgment", "the golden calf"),
    ("Exo", 33, 34, "awe", "'shew me thy glory'; the glory passes by"),
    ("Exo", 40, 40, "awe", "the glory fills the tabernacle"),

    ("Lev", 10, 10, "judgment", "Nadab and Abihu; strange fire"),
    ("Lev", 16, 16, "passion", "the day of atonement — blood and scapegoat"),
    ("Lev", 26, 26, "judgment", "the covenant curses"),

    ("Num", 6, 6, "hope", "the Aaronic blessing"),
    ("Num", 14, 14, "judgment", "the sentence of forty years"),
    ("Num", 16, 16, "judgment", "Korah; the earth opens"),
    ("Num", 25, 25, "judgment", "Baal-peor and the plague"),

    ("Deu", 6, 6, "wisdom", "the Shema — the didactic centre of the book"),
    ("Deu", 28, 28, "judgment", "the curses"),
    ("Deu", 30, 30, "hope", "restoration; 'choose life'"),
    ("Deu", 32, 32, "judgment", "the song as a witness against them"),
    ("Deu", 33, 33, "hope", "the blessing of the tribes"),
    ("Deu", 34, 34, "lament", "the death of Moses"),

    ("Jos", 24, 24, "hope", "covenant renewal; 'as for me and my house'"),

    ("Jdg", 5, 5, "praise", "the song of Deborah"),
    ("Jdg", 11, 11, "lament", "Jephthah's vow and his daughter"),
    ("Jdg", 16, 16, "lament", "Samson blinded, and his death"),
    # RESOLVED by the owner 2026-08-03: silence, and across all three chapters.
    # This is the one passage where ANY bed risks sounding like it is scoring
    # an atrocity. Silence costs nothing to license and cannot be tonally
    # wrong, which is exactly the case the plan reserves it for.
    ("Jdg", 19, 21, "silence", "Gibeah: the outrage, the war, and its aftermath"),

    ("Rut", 1, 1, "lament", "the three deaths; 'call me Mara'"),

    ("1Sa", 2, 2, "praise", "Hannah's song"),
    ("1Sa", 3, 3, "awe", "the call of Samuel"),
    ("1Sa", 15, 15, "judgment", "Saul rejected"),
    ("1Sa", 28, 28, "judgment", "Endor; Saul's doom pronounced"),
    ("1Sa", 31, 31, "lament", "the death of Saul and Jonathan"),

    ("2Sa", 1, 1, "lament", "'how are the mighty fallen'"),
    ("2Sa", 7, 7, "hope", "the Davidic covenant"),
    ("2Sa", 12, 12, "lament", "Nathan's rebuke; the child dies"),
    ("2Sa", 18, 18, "lament", "'O my son Absalom'"),
    ("2Sa", 22, 22, "praise", "David's song of deliverance (= Psalm 18)"),
    ("2Sa", 24, 24, "judgment", "the census and the plague"),

    ("1Ki", 3, 3, "wisdom", "Solomon asks for an understanding heart"),
    ("1Ki", 8, 8, "awe", "the dedication; the glory fills the house"),
    # ⚠ OPEN: ch 19 opens in Elijah's despair; `awe` chosen for the theophany.
    ("1Ki", 18, 19, "awe", "fire on Carmel; the still small voice"),
    ("1Ki", 21, 21, "judgment", "Naboth's vineyard; sentence on Ahab"),

    ("2Ki", 2, 2, "awe", "Elijah taken up by a whirlwind"),
    ("2Ki", 17, 17, "judgment", "the fall of Samaria and its indictment"),
    ("2Ki", 19, 19, "awe", "the angel of the LORD delivers Jerusalem"),
    ("2Ki", 24, 25, "lament", "Jerusalem falls; the temple burned"),

    ("1Ch", 16, 16, "praise", "the psalm sung at the ark"),
    ("1Ch", 21, 21, "judgment", "the census and the plague"),
    ("1Ch", 29, 29, "praise", "'thine, O LORD, is the greatness'"),

    ("2Ch", 5, 7, "awe", "the glory fills the temple; fire from heaven"),
    ("2Ch", 20, 20, "praise", "the singers go out before the army"),
    ("2Ch", 36, 36, "lament", "the burning of the house and the exile"),

    ("Ezr", 3, 3, "praise", "the foundation laid — shouting mixed with weeping"),
    ("Ezr", 9, 9, "lament", "Ezra's confession"),

    ("Neh", 1, 1, "lament", "Nehemiah weeps over the ruined walls"),
    ("Neh", 8, 8, "praise", "the law read; 'the joy of the LORD is your strength'"),
    ("Neh", 9, 9, "lament", "the great confession"),

    ("Est", 4, 4, "lament", "fasting and mourning; 'if I perish, I perish'"),

    ("Job", 1, 2, "narrative", "the prose prologue"),
    ("Job", 28, 28, "wisdom", "'but where shall wisdom be found?'"),
    ("Job", 38, 41, "awe", "the voice out of the whirlwind"),
    ("Job", 42, 42, "hope", "'mine eye seeth thee'; the restoration"),

    # ---- Psalms: default `praise`; everything below departs from it. ----
    ("Psa", 1, 1, "wisdom", "the two ways"),
    ("Psa", 2, 2, "judgment", "the raging nations broken with a rod of iron"),
    ("Psa", 3, 3, "lament", ""),
    ("Psa", 4, 4, "hope", "the evening psalm of trust"),
    ("Psa", 5, 7, "lament", ""),
    ("Psa", 8, 8, "awe", "'the work of thy fingers'"),
    ("Psa", 10, 10, "lament", ""),
    ("Psa", 11, 11, "hope", "trust under threat"),
    ("Psa", 12, 13, "lament", "'how long wilt thou forget me'"),
    ("Psa", 14, 14, "judgment", "'they are all gone aside'"),
    ("Psa", 15, 15, "wisdom", "'who shall abide in thy tabernacle'"),
    ("Psa", 16, 16, "hope", "'thou wilt not leave my soul in hell'"),
    ("Psa", 17, 17, "lament", ""),
    ("Psa", 19, 19, "awe", "'the heavens declare the glory of God'"),
    ("Psa", 20, 20, "hope", ""),
    ("Psa", 22, 22, "passion", "the dereliction psalm; anchored with a turn below"),
    ("Psa", 23, 23, "tender", "the shepherd psalm"),
    ("Psa", 24, 24, "awe", "'who is this King of glory?'"),
    ("Psa", 25, 26, "lament", ""),
    ("Psa", 27, 27, "hope", "'the LORD is my light and my salvation'"),
    ("Psa", 28, 28, "lament", ""),
    ("Psa", 29, 29, "awe", "the voice of the LORD upon the waters"),
    ("Psa", 31, 31, "lament", ""),
    ("Psa", 32, 32, "hope", "penitential, but resolved: 'blessed is he whose transgression is forgiven'"),
    ("Psa", 35, 35, "lament", "imprecatory complaint"),
    ("Psa", 36, 36, "hope", "'thy mercy, O LORD, is in the heavens'"),
    ("Psa", 37, 37, "wisdom", "'fret not thyself' — the two ways again"),
    ("Psa", 38, 39, "lament", "penitential"),
    ("Psa", 41, 44, "lament", "'as the hart panteth' and the national complaint"),
    ("Psa", 46, 46, "hope", "'God is our refuge and strength'"),
    ("Psa", 49, 49, "wisdom", ""),
    ("Psa", 50, 50, "judgment", "God comes to judge his own people"),
    ("Psa", 51, 51, "lament", "the great penitential psalm"),
    ("Psa", 52, 53, "judgment", ""),
    ("Psa", 54, 57, "lament", ""),
    ("Psa", 58, 58, "judgment", "imprecatory"),
    ("Psa", 59, 60, "lament", ""),
    ("Psa", 61, 62, "hope", "'my soul waiteth upon God'"),
    ("Psa", 63, 63, "tender", "'my soul thirsteth for thee'"),
    ("Psa", 64, 64, "lament", ""),
    ("Psa", 68, 68, "awe", "'let God arise' — the procession into the sanctuary"),
    ("Psa", 69, 71, "lament", "the reproach psalm and the plea of old age"),
    ("Psa", 72, 72, "hope", "the reign of the king's son"),
    ("Psa", 73, 73, "wisdom", "the prosperity of the wicked, resolved in the sanctuary"),
    ("Psa", 74, 74, "lament", "the sanctuary burned"),
    ("Psa", 75, 76, "judgment", ""),
    ("Psa", 77, 77, "lament", ""),
    ("Psa", 78, 78, "narrative", "a historical recital, not a song of praise"),
    ("Psa", 79, 80, "lament", ""),
    ("Psa", 82, 83, "judgment", "imprecatory; the confederacy against Israel"),
    ("Psa", 84, 84, "tender", "'how amiable are thy tabernacles'"),
    ("Psa", 85, 85, "hope", "restoration"),
    ("Psa", 86, 86, "lament", ""),
    # ⚠ OPEN: 88 is the darkest psalm in the psalter — a candidate for silence.
    ("Psa", 88, 89, "lament", "'free among the dead'; the covenant questioned"),
    ("Psa", 90, 90, "wisdom", "'teach us to number our days'"),
    ("Psa", 91, 91, "hope", "'he that dwelleth in the secret place'"),
    ("Psa", 93, 93, "awe", "'the LORD reigneth, he is clothed with majesty'"),
    ("Psa", 94, 94, "judgment", ""),
    ("Psa", 97, 97, "awe", "'clouds and darkness are round about him'"),
    ("Psa", 99, 99, "awe", "'he sitteth between the cherubims'"),
    ("Psa", 101, 101, "wisdom", "the king's resolve"),
    ("Psa", 102, 102, "lament", "penitential"),
    ("Psa", 104, 104, "awe", "the creation psalm"),
    ("Psa", 105, 105, "narrative", "a historical recital"),
    ("Psa", 106, 106, "lament", "the confession of the national history"),
    ("Psa", 109, 109, "judgment", "the sharpest imprecatory psalm"),
    ("Psa", 110, 110, "awe", "'the LORD said unto my Lord'"),
    ("Psa", 112, 112, "wisdom", ""),
    ("Psa", 114, 114, "awe", "'the sea saw it, and fled'"),
    ("Psa", 119, 119, "wisdom", "the Torah psalm"),
    ("Psa", 120, 120, "lament", ""),
    ("Psa", 121, 121, "hope", "'I will lift up mine eyes unto the hills'"),
    ("Psa", 123, 123, "lament", ""),
    ("Psa", 125, 126, "hope", "'they that sow in tears shall reap in joy'"),
    ("Psa", 127, 128, "wisdom", ""),
    ("Psa", 129, 130, "lament", "'out of the depths'"),
    ("Psa", 131, 131, "tender", "'as a child that is weaned of his mother'"),
    ("Psa", 132, 132, "hope", "the oath sworn unto David"),
    ("Psa", 133, 133, "tender", "'brethren to dwell together in unity'"),
    ("Psa", 137, 137, "lament", "by the rivers of Babylon"),
    ("Psa", 139, 139, "awe", "'whither shall I flee from thy presence?'"),
    ("Psa", 140, 143, "lament", "the closing Davidic complaints; 143 penitential"),

    ("Isa", 6, 6, "awe", "the throne vision"),
    ("Isa", 9, 9, "hope", "'unto us a child is born' opens the chapter"),
    ("Isa", 11, 11, "hope", "the rod out of Jesse; the peaceable kingdom"),
    ("Isa", 12, 12, "praise", "'behold, God is my salvation'"),
    ("Isa", 25, 26, "hope", "'he will swallow up death in victory'"),
    ("Isa", 35, 35, "hope", "the desert shall rejoice and blossom"),
    ("Isa", 36, 39, "narrative", "the Hezekiah historical interlude"),
    ("Isa", 40, 52, "hope", "the book of comfort"),
    ("Isa", 53, 53, "passion", "the suffering servant"),
    ("Isa", 54, 55, "hope", ""),
    ("Isa", 60, 62, "hope", "'arise, shine, for thy light is come'"),
    ("Isa", 64, 64, "lament", "'oh that thou wouldest rend the heavens'"),
    ("Isa", 65, 66, "hope", "new heavens and a new earth (the closing woe notwithstanding)"),

    ("Jer", 1, 1, "narrative", "the call of the prophet"),
    ("Jer", 9, 9, "lament", "'oh that my head were waters'"),
    ("Jer", 20, 20, "lament", "the prophet's confession"),
    ("Jer", 30, 33, "hope", "the book of consolation; the new covenant at 31:31"),
    ("Jer", 36, 38, "narrative", "the scroll; the dungeon"),
    ("Jer", 39, 39, "lament", "the city taken"),
    ("Jer", 40, 43, "narrative", "Gedaliah and the flight to Egypt"),
    ("Jer", 45, 45, "narrative", "the word to Baruch"),
    ("Jer", 52, 52, "lament", "the historical appendix: the fall and the exile"),

    # ⚠ The plan names Lamentations as a place where silence is stronger.
    # RESOLVED by the owner 2026-08-03: ch 2 as well. It is at least as graphic
    # as ch 5 — the children fainting in the streets — and was only spared
    # because the first draft applied silence to the closing chapter alone.
    # Ch 3 keeps its mid-chapter turn to `hope` at v22 ("his mercies are new
    # every morning"), which is the book's one lifting point and must not be
    # flattened into silence.
    ("Lam", 2, 2, "silence", "the day of the LORD's anger — no bed at all"),
    ("Lam", 5, 5, "silence", "the closing plea ends unresolved — no bed at all"),

    ("Eze", 1, 1, "awe", "the chariot vision"),
    ("Eze", 2, 3, "narrative", "the commissioning of the prophet"),
    ("Eze", 10, 10, "awe", "the glory departs from the house"),
    ("Eze", 24, 24, "lament", "'the desire of thine eyes' — the prophet's wife dies"),
    ("Eze", 34, 34, "hope", "'I will seek that which was lost'"),
    ("Eze", 36, 37, "hope", "a new heart; the valley of dry bones"),
    ("Eze", 40, 48, "awe", "the visionary temple, the river, 'THE LORD IS THERE'"),

    ("Dan", 5, 5, "judgment", "the writing on the wall"),
    ("Dan", 7, 7, "awe", "the Ancient of days and the Son of man"),
    ("Dan", 9, 9, "lament", "Daniel's confession"),
    ("Dan", 10, 10, "awe", "the man clothed in linen"),
    ("Dan", 12, 12, "hope", "'they that be wise shall shine as the stars'"),

    ("Hos", 11, 11, "tender", "'when Israel was a child, then I loved him'"),
    ("Hos", 14, 14, "hope", "'I will heal their backsliding'"),

    # ⚠ OPEN: a thanksgiving sung out of distress; `hope` is defensible.
    ("Jon", 2, 2, "lament", "'out of the belly of hell cried I'"),

    ("Mic", 4, 5, "hope", "swords into plowshares; Bethlehem Ephratah"),
    ("Mic", 7, 7, "hope", "'who is a God like unto thee, that pardoneth'"),

    ("Hab", 3, 3, "awe", "'God came from Teman' — the mountains trembled"),

    ("Zep", 3, 3, "hope", "'he will rejoice over thee with singing'"),

    ("Zec", 1, 6, "awe", "the night visions"),
    ("Zec", 11, 11, "judgment", "the worthless shepherd; the thirty pieces of silver"),

    ("Mat", 5, 7, "wisdom", "the sermon on the mount"),
    ("Mat", 11, 11, "hope", "'come unto me, all ye that labour'"),
    ("Mat", 13, 13, "wisdom", "the parables of the kingdom"),
    ("Mat", 18, 18, "wisdom", "the discourse on offences and forgiveness"),
    ("Mat", 23, 25, "judgment", "the woes and the Olivet discourse"),
    ("Mat", 26, 27, "passion", ""),
    ("Mat", 28, 28, "praise", "the resurrection"),

    ("Mar", 13, 13, "judgment", "the Olivet discourse"),
    ("Mar", 14, 15, "passion", ""),
    ("Mar", 16, 16, "praise", "the resurrection"),

    ("Luk", 1, 1, "praise", "the Magnificat and the Benedictus"),
    ("Luk", 2, 2, "tender", "the nativity"),
    ("Luk", 6, 6, "wisdom", "the sermon on the plain"),
    ("Luk", 15, 15, "tender", "the lost sheep, the lost coin, the prodigal"),
    ("Luk", 21, 21, "judgment", "the Olivet discourse"),
    ("Luk", 22, 23, "passion", "ch 23 carries verse-level turns below"),
    ("Luk", 24, 24, "praise", "the resurrection"),

    ("Jhn", 1, 1, "awe", "the prologue: 'the Word was God'"),
    ("Jhn", 3, 3, "hope", "'God so loved the world'"),
    ("Jhn", 6, 6, "wisdom", "the bread of life discourse"),
    ("Jhn", 10, 10, "tender", "the good shepherd"),
    ("Jhn", 11, 11, "lament", "'Jesus wept' — turns at the grave, anchored below"),
    ("Jhn", 13, 13, "tender", "the washing of feet; the new commandment"),
    ("Jhn", 14, 16, "hope", "'let not your heart be troubled'"),
    ("Jhn", 17, 17, "awe", "the high priestly prayer"),
    ("Jhn", 18, 19, "passion", ""),
    ("Jhn", 20, 20, "praise", "the resurrection"),
    ("Jhn", 21, 21, "tender", "the breakfast by the sea; 'lovest thou me'"),

    ("Act", 2, 2, "awe", "Pentecost: the rushing mighty wind"),
    ("Act", 7, 7, "lament", "the stoning of Stephen"),
    ("Act", 9, 9, "awe", "the light on the Damascus road"),

    ("Rom", 5, 5, "hope", "peace with God; the reign of grace"),
    ("Rom", 8, 8, "hope", "'no condemnation'; 'more than conquerors'"),

    ("1Co", 13, 13, "tender", "the chapter on charity"),
    ("1Co", 15, 15, "hope", "the resurrection chapter"),

    ("2Co", 4, 5, "hope", "'though our outward man perish'; the house not made with hands"),

    ("Eph", 1, 1, "praise", "the opening benediction/doxology"),

    # ⚠ OPEN: `awe` is defensible for the kenosis hymn.
    ("Phl", 2, 2, "praise", "'every knee shall bow, every tongue confess'"),

    ("Col", 1, 1, "awe", "'by him all things consist'"),

    ("2Th", 1, 2, "judgment", "the day of the Lord and the man of sin"),

    ("2Ti", 4, 4, "hope", "'I have fought a good fight... a crown of righteousness'"),

    ("Heb", 1, 1, "awe", "the Son upholding all things by the word of his power"),
    ("Heb", 11, 11, "hope", "the roll of faith"),

    ("2Pe", 2, 3, "judgment", "the false teachers; the elements melting"),

    ("Rev", 1, 1, "awe", "the vision of the Son of man"),
    ("Rev", 4, 5, "awe", "the throne and the Lamb"),
    ("Rev", 7, 7, "hope", "'God shall wipe away all tears from their eyes'"),
    ("Rev", 19, 19, "praise", "the fourfold Alleluia"),
    ("Rev", 21, 22, "hope", "the new Jerusalem"),
]

# ---------------------------------------------------------------- tier 3
# ★★ HUMAN REVIEW REQUIRED BEFORE SHIPPING ★★ (MUSIC_MOOD_PLAN.md review gate)
#
# The passages that MUST be right — the acceptance criterion. Most simply
# restate the tier-2 result; they are listed anyway so a reviewer reads one
# short table instead of 250 ranges.
#
# (book, chapter, [(from_verse, mood), ...], why) — 1-BASED. The first
# segment must start at verse 1. Verse-level turns are permitted ONLY here
# and only where a chapter genuinely turns; every turn's verse index is
# machine-verified against the KJV text by VERSE_WITNESSES below.
ANCHORS = [
    ("Gen", 1, [(1, "awe")], "creation"),
    ("Gen", 22, [(1, "passion")], "the binding of Isaac"),
    ("Exo", 3, [(1, "awe")], "the burning bush"),
    ("Exo", 14, [(1, "awe")], "the sea divided"),
    ("Exo", 20, [(1, "awe")], "the ten commandments"),
    ("Job", 3, [(1, "lament")], "'let the day perish wherein I was born'"),
    ("Job", 38, [(1, "awe")], "the whirlwind"),
    ("Job", 42, [(1, "hope")], "restoration"),
    # The one classic mid-chapter turn in the psalter: dereliction -> praise.
    ("Psa", 22, [(1, "passion"), (22, "praise")],
     "'my God, why hast thou forsaken me' turns at 'I will declare thy name'"),
    ("Psa", 23, [(1, "tender")], "the shepherd psalm"),
    ("Psa", 51, [(1, "lament")], "the great penitential psalm"),
    ("Psa", 88, [(1, "lament")], "the darkest psalm — see OPEN QUESTIONS"),
    ("Psa", 91, [(1, "hope")], "the secret place of the most High"),
    ("Psa", 121, [(1, "hope")], "'I will lift up mine eyes'"),
    ("Psa", 139, [(1, "awe")], "'whither shall I flee from thy presence'"),
    ("Psa", 150, [(1, "praise")], "the doxology of the psalter"),
    ("Isa", 6, [(1, "awe")], "'holy, holy, holy'"),
    ("Isa", 40, [(1, "hope")], "'comfort ye my people'"),
    ("Isa", 53, [(1, "passion")], "the suffering servant"),
    # Lamentations 3 is the other true mid-chapter turn: the depth of the
    # book's affliction, then 'it is of the LORD's mercies'.
    ("Lam", 3, [(1, "lament"), (22, "hope")],
     "'I am the man that hath seen affliction' turns at the mercies"),
    ("Lam", 5, [(1, "silence")], "the unresolved close — deliberately no bed"),
    ("Eze", 1, [(1, "awe")], "the chariot vision"),
    ("Eze", 37, [(1, "hope")], "the valley of dry bones"),
    ("Dan", 3, [(1, "narrative")], "the fiery furnace — deliberately NOT judgment"),
    ("Mic", 5, [(1, "hope")], "'thou, Bethlehem Ephratah'"),
    ("Mat", 5, [(1, "wisdom")], "the beatitudes"),
    ("Mat", 26, [(1, "passion")], "Gethsemane"),
    ("Mat", 27, [(1, "passion"), (45, "silence")],
     "the darkness from the sixth hour — the plan's own example of silence"),
    ("Mar", 15, [(1, "passion"), (33, "silence")], "the darkness over the whole land"),
    ("Luk", 2, [(1, "tender")], "the nativity"),
    ("Luk", 15, [(1, "tender")], "the prodigal"),
    # The plan's stated example of a chapter that genuinely turns mid-way.
    ("Luk", 23, [(1, "judgment"), (26, "passion"), (44, "silence")],
     "trial before Pilate -> the road to the cross -> the darkness"),
    ("Luk", 24, [(1, "praise")], "the resurrection and the Emmaus road"),
    ("Jhn", 1, [(1, "awe")], "the Word was God"),
    ("Jhn", 3, [(1, "hope")], "'God so loved the world'"),
    ("Jhn", 11, [(1, "lament"), (38, "hope")],
     "'Jesus wept' turns when he cometh to the grave"),
    ("Jhn", 14, [(1, "hope")], "'in my Father's house are many mansions'"),
    ("Jhn", 19, [(1, "passion"), (30, "silence")],
     "'it is finished' — silence through the giving up of the ghost and the burial"),
    ("Act", 2, [(1, "awe")], "Pentecost"),
    ("Rom", 8, [(1, "hope")], "'more than conquerors'"),
    ("1Co", 13, [(1, "tender")], "charity"),
    ("1Co", 15, [(1, "hope")], "'O death, where is thy sting'"),
    ("Heb", 11, [(1, "hope")], "the roll of faith"),
    ("Rev", 4, [(1, "awe")], "the throne"),
    ("Rev", 5, [(1, "awe")], "the Lamb that was slain"),
    ("Rev", 19, [(1, "praise")], "the Alleluia"),
    ("Rev", 21, [(1, "hope")], "the new Jerusalem"),
    ("Rev", 22, [(1, "hope")], "'the Spirit and the bride say, Come'"),
]

# Every verse-level turn is only as good as its verse number. These
# witnesses prove the turn lands where the placement assumes — the same
# discipline as build_chrono_plan.py's ANCHORS.
VERSE_WITNESSES = [
    ("Psa", 22, 1, r"why hast thou forsaken me"),
    ("Psa", 22, 22, r"I will declare thy name unto my brethren"),
    ("Lam", 3, 1, r"I am the man that hath seen affliction"),
    ("Lam", 3, 22, r"It is of the LORD'?S mercies that we are not consumed"),
    ("Mat", 27, 45, r"there was darkness over all the land"),
    ("Mar", 15, 33, r"there was darkness over the whole land"),
    ("Luk", 23, 26, r"laid hold upon one Simon, a Cyrenian"),
    ("Luk", 23, 44, r"there was a darkness over all the earth"),
    ("Jhn", 11, 38, r"groaning in himself cometh to the grave"),
    ("Jhn", 19, 30, r"It is finished"),
]


def load_counts():
    kjv = json.load(open(KJV, encoding="utf-8"))
    # Chapter counts come from the canonical grid, never from memory.
    return kjv, [len(b["chapters"]) for b in kjv]


def main():
    kjv, counts = load_counts()
    canon = counts[:66]
    assert sum(canon) == 1189, f"canon grid is {sum(canon)} chapters, expected 1189"

    # --- taxonomy check -------------------------------------------------
    used = set(BOOK_DEFAULT.values()) | {APOCRYPHA_DEFAULT}
    used |= set(APOCRYPHA_BOOK.values())
    used |= {m for _, _, _, m, _ in RANGES}
    used |= {m for _, _, segs, _ in ANCHORS for _, m in segs}
    bad = sorted(used - set(MOODS))
    assert not bad, f"mood ids not in the taxonomy: {bad}"

    # --- tier 1 ---------------------------------------------------------
    assert len(BOOK_DEFAULT) == 66, f"tier 1 has {len(BOOK_DEFAULT)} books, expected 66"
    for i in range(66):
        assert BOOKS[i] in BOOK_DEFAULT, f"no book default for {BOOKS[i]}"
    for a in APOCRYPHA_BOOK:
        assert IDX[a] >= 66, f"{a} is not an apocrypha slot"

    # --- apocrypha coverage ---------------------------------------------
    # The 1189 assertion below covers the CANON ONLY, so without this the
    # apocrypha were unguarded: a future edit could drop a slot and nothing
    # would notice. They resolve by book default alone (see the note on
    # APOCRYPHA_BOOK), so what has to hold is simply that every slot the app
    # can open has a mood, and that no range or anchor strays into one.
    n_apoc = len(BOOKS) - 66
    assert n_apoc == 17, f"expected 17 apocrypha slots, found {n_apoc}"
    for b in range(66, len(BOOKS)):
        mood = APOCRYPHA_BOOK.get(BOOKS[b], APOCRYPHA_DEFAULT)
        assert mood in MOODS, f"apocrypha slot {b} has mood {mood!r}"
    for abbr, _lo, _hi, _m, _w in RANGES:
        assert IDX[abbr] < 66, (
            f"range on apocrypha book {abbr}: apocrypha are book-level only, "
            f"because chapter numbering differs by translation and versemap "
            f"does not map them")
    for abbr, _ch, _segs, _w in ANCHORS:
        assert IDX[abbr] < 66, (
            f"anchor on apocrypha book {abbr}: apocrypha are book-level only "
            f"(same reason as ranges)")
    # A translation may carry MORE apocrypha chapters than the KJV slot — the
    # Slavonic has 3 Maccabees at 7 where the KJV slot is empty. Book-level
    # resolution handles any chapter index, but assert the app can never ask
    # for a book slot we have not defined.
    assert len(BOOKS) == 83, (
        f"{len(BOOKS)} book slots; the shipped assets top out at index 82, so "
        f"bookDefault must cover 0..82")

    # --- tier 2: bounds + no overlap within a tier -----------------------
    resolved = {}          # (book, chapter1) -> mood
    hit_by_range = {}      # (book, chapter1) -> range index, for collision reports
    for b in range(66):
        for c in range(1, canon[b] + 1):
            resolved[(b, c)] = BOOK_DEFAULT[BOOKS[b]]
    for n, (abbr, lo, hi, mood, _why) in enumerate(RANGES):
        b = IDX[abbr]
        assert b < 66, f"range {abbr} {lo}-{hi} is not a canon book"
        assert 1 <= lo <= hi <= canon[b], \
            f"range out of bounds: {abbr} {lo}-{hi} (book has {canon[b]} chapters)"
        for c in range(lo, hi + 1):
            prev = hit_by_range.get((b, c))
            assert prev is None, (
                f"tier-2 collision at {abbr} {c}: ranges #{prev} and #{n}")
            hit_by_range[(b, c)] = n
            resolved[(b, c)] = mood

    # --- tier 3: unique chapters, ordered segments, in bounds ------------
    seen_anchor = set()
    for abbr, ch, segs, _why in ANCHORS:
        b = IDX[abbr]
        assert b < 66, f"anchor {abbr} {ch} is not a canon book"
        assert 1 <= ch <= canon[b], f"anchor out of bounds: {abbr} {ch}"
        assert (b, ch) not in seen_anchor, f"tier-3 collision: {abbr} {ch} anchored twice"
        seen_anchor.add((b, ch))
        assert segs and segs[0][0] == 1, f"anchor {abbr} {ch} must start at verse 1"
        starts = [v for v, _ in segs]
        assert starts == sorted(set(starts)), \
            f"anchor {abbr} {ch} segments must be strictly increasing"
        nverses = len(kjv[b]["chapters"][ch - 1])
        assert starts[-1] <= nverses, \
            f"anchor {abbr} {ch} turn at v{starts[-1]} but chapter has {nverses} verses"
        # The chapter's mood is its FIRST segment; later segments are turns.
        resolved[(b, ch)] = segs[0][1]

    # --- verse witnesses: the turns land where we think they do ----------
    for abbr, ch, v, pat in VERSE_WITNESSES:
        raw = kjv[IDX[abbr]]["chapters"][ch - 1][v - 1]
        # The KJV asset marks supplied words as {am}; the reader strips them
        # (BibleRepo.parseAsset). Strip the braces, not their contents, so a
        # witness can quote the verse as it is read.
        text = raw.replace("{", "").replace("}", "")
        assert re.search(pat, text), f"witness failed: {abbr} {ch}:{v} ~ /{pat}/\n  {raw!r}"

    # --- coverage: every canonical chapter, exactly one mood -------------
    missing = [(BOOKS[b], c) for b in range(66)
               for c in range(1, canon[b] + 1) if (b, c) not in resolved]
    assert not missing, f"unresolved chapters: {missing[:20]}"
    assert len(resolved) == 1189, f"resolved {len(resolved)} chapters, expected 1189"

    # --- apocrypha: resolves for every slot, empty or not ----------------
    for b in range(66, len(BOOKS)):
        m = APOCRYPHA_BOOK.get(BOOKS[b], APOCRYPHA_DEFAULT)
        assert m in MOODS
        # counts[b] may be 0 (Epistle of Jeremiah / 3 Maccabees / Laodiceans
        # are empty in the KJV asset but present in vul/lut/kxii). Nothing
        # here indexes a translation's arrays, so an empty slot is a no-op.

    # --- report ---------------------------------------------------------
    tally = {}
    for m in resolved.values():
        tally[m] = tally.get(m, 0) + 1
    print("per-mood canonical chapter counts (tiers 1-3 resolved):")
    for m in MOODS:
        print(f"  {m:<10} {tally.get(m, 0):>5}")
    print(f"  {'TOTAL':<10} {sum(tally.values()):>5}")
    print(f"{len(RANGES)} range overrides, {len(ANCHORS)} anchors "
          f"({sum(len(s) - 1 for _, _, s, _ in ANCHORS)} verse-level turns), "
          f"{len(VERSE_WITNESSES)} verse witnesses verified against the KJV text.")
    print("*** TIER 3 (ANCHORS) STILL REQUIRES HUMAN REVIEW BEFORE SHIPPING. ***")

    # --- emit (0-based book, 0-based chapter, 0-based verse) -------------
    out = {
        "version": 1,
        "note": ("Canonical KJV coordinates. book/chapter/verse are 0-BASED. "
                 "Resolve: bookDefault -> ranges -> anchors (later wins). "
                 "Apocrypha = book index >= 66. Generated by "
                 "tools/build_mood_map.py — do not hand-edit."),
        "review": "TIER 3 (anchors) PENDING HUMAN REVIEW",
        "moods": list(MOODS),
        "default": APOCRYPHA_DEFAULT,
        "bookDefault": (
            [BOOK_DEFAULT[BOOKS[b]] for b in range(66)]
            + [APOCRYPHA_BOOK.get(BOOKS[b], APOCRYPHA_DEFAULT)
               for b in range(66, len(BOOKS))]
        ),
        "ranges": [
            {"book": IDX[a], "from": lo - 1, "to": hi - 1, "mood": m}
            for a, lo, hi, m, _ in RANGES
        ],
        "anchors": [
            {"book": IDX[a], "chapter": ch - 1, "mood": segs[0][1],
             **({"turns": [{"verse": v - 1, "mood": m} for v, m in segs[1:]]}
                if len(segs) > 1 else {})}
            for a, ch, segs, _ in ANCHORS
        ],
        "trackPin": [
            {"book": IDX[a], "chapter": ch - 1, "track": t, "why": w}
            for a, ch, t, w in TRACK_PINS
        ],
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("wrote", os.path.normpath(OUT), f"({os.path.getsize(OUT)} bytes)")


if __name__ == "__main__":
    main()
