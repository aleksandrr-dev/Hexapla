# -*- coding: utf-8 -*-
"""Bakar psalter overrides — GENERATED (tools/bakar_psalm_runs.py).

The Bakar prints psalm titles INLINE at the head of verse 1, so the LXX
psalter engine's title-offset assumption never applies here: any surplus or
deficit is a genuine seam. Each psalm below was read against the KJV, and
validated to cover every KJV verse once and name no empty slot.
"""

BAK_PSALTER = {
    # Ps 6 (Bakar 6): Bakar 3 merges KJV 3+4 ("and my soul was troubled greatly, and thou O Lord, how long — return O Lord, deliver my soul, save me for thy mercy's sake").
    6: [(6, 1, 2, 6, 1, 2), (6, 3, 4, 6, 3, 3), (6, 5, 8, 6, 4, 7), (6, 9, 10, 6, 8, 8)],
    # Ps 7 (Bakar 7): Bakar 1 = title + KJV 1. Two genuine LXX splits: KJV 4 spans Bakar 4 ("if I repaid those who repaid me evil") + Bakar 5 (LXX's "let me fall by my enem
    7: [(7, 1, 3, 7, 1, 3), (7, 4, 4, 7, 4, 5), (7, 5, 5, 7, 6, 6), (7, 6, 6, 7, 7, 7), (7, 7, 7, 7, 8, 8), (7, 8, 8, 7, 9, 9), (7, 9, 9, 7, 10, 11), (7, 10, 17, 7, 12, 19)],
    # Ps 14 (Bakar 13): Bakar 1 = title + KJV 1. KJV 7 is split at the Septuagint seam: Bakar 7 = 'Who shall give out of Zion the salvation of Israel', Bakar 8 = 'when the Lo
    14: [(14, 1, 6, 13, 1, 6), (14, 7, 7, 13, 7, 8)],
    # Ps 18 (Bakar 17): Bakar 1 = title + KJV 1 ("I will love thee, O LORD, my strength"). KJV 2 is split LXX-style: Bakar 2 = "O Lord my firmament and my refuge and my deliv
    18: [(18, 1, 1, 17, 1, 1), (18, 2, 2, 17, 2, 3), (18, 3, 50, 17, 4, 51)],
    # Ps 21 (Bakar 20): Bakar 1 = title + KJV 1. One-to-one through KJV 11 (= Bakar 11's opening, 'they intended evil against thee... which they could not perform'). KJV 12 s
    21: [(21, 1, 11, 20, 1, 11), (21, 12, 12, 20, 11, 12), (21, 13, 13, 20, 12, 12)],
    # Ps 22 (Bakar 21): Straight identity through Bakar 27 (title inline in verse 1). Bakar 28 runs "for the kingdom is the Lord's and he ruleth over the nations" (KJV 28) st
    22: [(22, 1, 27, 21, 1, 27), (22, 28, 29, 21, 28, 28), (22, 30, 31, 21, 29, 29)],
    # Ps 27 (Bakar 26): Straight 1:1 for verses 1-12 (Bakar 1 = title "before the anointing" + KJV 1). The only seam is at the end: Bakar 13 merges KJV 13 ("I had fainted, un
    27: [(27, 1, 12, 26, 1, 12), (27, 13, 14, 26, 13, 13)],
    # Ps 29 (Bakar 28): Bakar 1 = title ('of the going out of the tabernacle') + KJV 1. Straight 1:1 through Bakar 9 (voice-of-the-Lord series). Bakar 10 holds both KJV 10 (L
    29: [(29, 1, 9, 28, 1, 9), (29, 10, 11, 28, 10, 10)],
    # Ps 34 (Bakar 33): Bakar 1 = title ("when he changed his behaviour before Abimelech") + KJV 1. Single seam at KJV 8: Bakar 8 = "Taste and see that the LORD is good", Bak
    34: [(34, 1, 7, 33, 1, 7), (34, 8, 8, 33, 8, 9), (34, 9, 22, 33, 10, 23)],
    # Ps 35 (Bakar 34): Bakar 1 = title + KJV 1. Bakar 8 holds KJV 8 and 9 (net catches him ... 'but my soul shall rejoice in the Lord'). Bakar 9 holds all of KJV 10, and Bak
    35: [(35, 1, 7, 34, 1, 7), (35, 8, 9, 34, 8, 8), (35, 10, 10, 34, 9, 9), (35, 11, 15, 34, 11, 15), (35, 16, 16, 34, 15, 16), (35, 17, 22, 34, 17, 22), (35, 23, 23, 34, 23, 24), (35, 24, 28, 34, 25, 29)],
    # Ps 40 (Bakar 39): Identity through 13. KJV 14 is split by the Bakar: verse 14 = "let them be ashamed and confounded together that seek my soul to take it away", verse 1
    40: [(40, 1, 13, 39, 1, 13), (40, 14, 14, 39, 14, 15), (40, 15, 17, 39, 16, 18)],
    # Ps 45 (Bakar 44): Bakar 1 = title (Shoshannim / sons of Korah / song of loves) + KJV 1. The 3/4 boundary sits mid-verse (Bakar 3 = "Gird thy sword upon thy thigh, O mig
    45: [(45, 1, 13, 44, 1, 13), (45, 14, 15, 44, 14, 14), (45, 16, 16, 44, 15, 15), (45, 17, 17, 44, 16, 16)],
    # Ps 51 (Bakar 50): Bakar 1 = Nathan/Bathsheba title + KJV 1. Two merges: Bakar 10 = 'create a clean heart... renew a right spirit' + 'cast me not away... take not thy Ho
    51: [(51, 1, 9, 50, 1, 9), (51, 10, 11, 50, 10, 10), (51, 12, 12, 50, 11, 11), (51, 13, 13, 50, 12, 12), (51, 14, 14, 50, 13, 13), (51, 15, 16, 50, 14, 14), (51, 17, 17, 50, 15, 15), (51, 18, 18, 50, 16, 16), (51, 19, 19, 50, 17, 17)],
    # Ps 53 (Bakar 52): Bakar 1 = title ("upon Mahalath, Maschil") + KJV 1. KJV 5 is split: Bakar 5 = "There they feared with fear, where there was no fear", Bakar 6 = "for G
    53: [(53, 1, 4, 52, 1, 4), (53, 5, 5, 52, 5, 6), (53, 6, 6, 52, 7, 7)],
    # Ps 56 (Bakar 55): Bakar 1 = title + KJV 1. Straight through KJV 9. Bakar 10 merges KJV 10 and 11 into one verse ('In God I will praise my words, and toward the Lord I w
    56: [(56, 1, 9, 55, 1, 9), (56, 10, 11, 55, 10, 10), (56, 12, 12, 55, 11, 11), (56, 13, 13, 55, 12, 12)],
    # Ps 57 (Bakar 56): Identity through 9, title inline in verse 1. The final seam straddles: Bakar 9 ends "for thy mercy is magnified unto the heavens" (= KJV 10a) and Baka
    57: [(57, 1, 9, 56, 1, 9), (57, 10, 11, 56, 10, 10)],
    # Ps 66 (Bakar 65): Bakar 1 carries the title, KJV 1 ("make a joyful noise, all ye lands") AND KJV 2 ("sing forth the honour of his name; make his praise glorious") — tha
    66: [(66, 1, 2, 65, 1, 1), (66, 3, 11, 65, 2, 10), (66, 12, 20, 65, 11, 19)],
    # Ps 67 (Bakar 66): Bakar 1 = title + KJV 1. Bakar 2 carries KJV 2 ('that thy way be known upon earth, thy salvation among all nations') plus the first praise-refrain lin
    67: [(67, 1, 1, 66, 1, 1), (67, 2, 3, 66, 2, 2), (67, 4, 4, 66, 3, 3), (67, 5, 5, 66, 4, 4), (67, 6, 6, 66, 5, 5), (67, 7, 7, 66, 6, 6)],
    # Ps 68 (Bakar 67): Bakar 1 = title + KJV 1. KJV 3 split: Bakar 3 = "let the righteous be glad, let them rejoice before God", Bakar 4 = "and let them exult with gladness"
    68: [(68, 1, 2, 67, 1, 2), (68, 3, 3, 67, 3, 4), (68, 4, 35, 67, 5, 36)],
    # Ps 71 (Bakar 70): Bakar 1 = the long Georgian title ('sons of Jonadab and the first captives, untitled among the Hebrews') + KJV 1. One-to-one all the way to KJV 23. Th
    71: [(71, 1, 23, 70, 1, 23), (71, 24, 24, 70, 24, 25)],
    # Ps 72 (Bakar 71): Clean one-to-one, title inline in verse 1. Bakar 19 ends with "...and let the whole earth be filled with his glory, Amen, Amen" followed only by the d
    72: [(72, 1, 19, 71, 1, 19)],
    # Ps 73 (Bakar 72): Bakar 1 = title ("the hymns of David son of Jesse are ended; a psalm of Asaph") + KJV 1. Identity through KJV 21 ("my heart was grieved... pricked in 
    73: [(73, 1, 21, 72, 1, 21), (73, 22, 23, 72, 22, 22), (73, 24, 28, 72, 23, 27)],
    # Ps 74 (Bakar 73): Bakar 1 = Maschil-of-Asaph title + KJV 1. Single split at KJV 9: Bakar 9 = 'we have not seen our signs, there is no more any prophet', Bakar 10 = 'and
    74: [(74, 1, 8, 73, 1, 8), (74, 9, 9, 73, 9, 10), (74, 10, 23, 73, 11, 24)],
    # Ps 87 (Bakar 86): Two merges at the head. Bakar 1 = title ("a psalm of the sons of Korah") + KJV 1 ("His foundation is in the holy mountains") + KJV 2 ("the LORD loveth
    87: [(87, 1, 2, 86, 1, 1), (87, 3, 4, 86, 2, 2), (87, 5, 5, 86, 3, 3), (87, 6, 6, 86, 4, 4), (87, 7, 7, 86, 5, 5)],
    # Ps 89 (Bakar 88): Bakar 1 = title (Ethan the Israelite) + KJV 1; then one-to-one for a very long stretch, confirmed at anchors: Bakar 20 'I have found David my servant'
    89: [(89, 1, 46, 88, 1, 46), (89, 47, 47, 88, 47, 48), (89, 48, 48, 88, 48, 48), (89, 49, 50, 88, 49, 50), (89, 51, 52, 88, 51, 51)],
    # Ps 90 (Bakar 89): Title inline in verse 1. Bakar 5 holds both KJV 5 and 6 ("their years shall be as nothing; in the morning as green grass it passeth away; in the morni
    90: [(90, 1, 4, 89, 1, 4), (90, 5, 6, 89, 5, 5), (90, 7, 17, 89, 6, 16)],
    # Ps 91 (Bakar 90): Bakar 1 = the Georgian/LXX superscription ("a song of praise of David, without title among the Hebrews") + KJV 1. Clean 1:1 through KJV 14 ("because h
    91: [(91, 1, 14, 90, 1, 14), (91, 15, 16, 90, 15, 15)],
    # Ps 93 (Bakar 92): Bakar 1 = title (sabbath day / when the earth was established) + KJV 1. The split is inside KJV 3-4: Bakar 3 = 'the floods have lifted up, the floods 
    93: [(93, 1, 1, 92, 1, 1), (93, 2, 2, 92, 2, 2), (93, 3, 3, 92, 3, 4), (93, 4, 4, 92, 5, 5), (93, 5, 5, 92, 6, 6)],
    # Ps 99 (Bakar 98): Bakar 1 = title + KJV 1. One merge: Bakar 6 holds both KJV 6 ("Moses and Aaron among his priests, and Samuel... they called upon the LORD and he heard
    99: [(99, 1, 5, 98, 1, 5), (99, 6, 7, 98, 6, 6), (99, 8, 8, 98, 7, 7), (99, 9, 9, 98, 8, 8)],
    # Ps 109 (Bakar 108): Bakar 1 carries the title, KJV 1 AND KJV 2 (it continues '...for the mouth of the sinner and the mouth of the deceitful is opened against me, they spo
    109: [(109, 1, 2, 108, 1, 1), (109, 3, 20, 108, 2, 19), (109, 21, 21, 108, 20, 21), (109, 22, 24, 108, 21, 23), (109, 25, 26, 108, 24, 24), (109, 27, 31, 108, 25, 29)],
    # Ps 119 (Bakar 118): Exactly one merge in the whole psalm, at Bakar 74, which runs "they that fear thee shall see me and be glad, for I have hoped in thy words" (KJV 74) d
    119: [(119, 1, 73, 118, 1, 73), (119, 74, 75, 118, 74, 74), (119, 76, 176, 118, 75, 175)],
    # Ps 126 (Bakar 125): Bakar 1 = title ("a song of degrees") + KJV 1. Verses 1-5 are 1:1 (KJV 4 "turn again our captivity, as the streams in the south" = Bakar 4; KJV 5 "the
    126: [(126, 1, 5, 125, 1, 5), (126, 6, 6, 125, 6, 7)],
    # Ps 128 (Bakar 127): Bakar 1 = 'Song of degrees' title + KJV 1. Single clean split of KJV 3: Bakar 3 = 'thy wife as a fruitful vine by the sides of thy house', Bakar 4 = '
    128: [(128, 1, 1, 127, 1, 1), (128, 2, 2, 127, 2, 2), (128, 3, 3, 127, 3, 4), (128, 4, 4, 127, 5, 5), (128, 5, 5, 127, 6, 6), (128, 6, 6, 127, 7, 7)],
    # Ps 130 (Bakar 129): Bakar 1 = title ("A song of degrees") + KJV 1 + the opening clause of KJV 2 ("Lord, hear my prayer"); Bakar 2 = the remainder of KJV 2 ("let thine ear
    130: [(130, 1, 2, 129, 1, 2), (130, 3, 4, 129, 3, 3), (130, 5, 5, 129, 4, 4), (130, 6, 6, 129, 5, 5), (130, 7, 8, 129, 6, 6)],
    # Ps 140 (Bakar 139): Bakar 1 = title + KJV 1. The single seam is KJV 5, split in two: Bakar 5 = 'the proud have hid a snare for me, and with cords they spread a net for my
    140: [(140, 1, 4, 139, 1, 4), (140, 5, 5, 139, 5, 6), (140, 6, 13, 139, 7, 14)],
    # Ps 150 (Bakar 150): Bakar 4 carries all four instrument clauses — timbrel and dance, strings and organ, well-sounding cymbals, cymbals of shouting — i.e. KJV 4 and 5 toge
    150: [(150, 1, 3, 150, 1, 3), (150, 4, 5, 150, 4, 4), (150, 6, 6, 150, 5, 5)],
}
