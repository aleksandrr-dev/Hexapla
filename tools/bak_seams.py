# -*- coding: utf-8 -*-
"""Bakar 1743 Georgian — per-chapter seam runs for the versemap.

GENERATED from the seam-reading pass of 2026-08-04 (tools/bakar_seam_runs.py),
then filtered. Each chapter here was read verse by verse against the KJV by an
agent that quoted the Georgian at the seam; the quotes live in the workflow
journal and a sample is in research/BAKAR_BUILD_LOG.md.

⚠ TWO LIMITS ON THIS DATA, both real:
 1. SINGLE READER. The workflow verified only findings below high confidence,
    and every reader marked its own work high — so these 114 chapters carry one
    reading each, not an independent second opinion. 31 verifier agents also
    died when the session limit hit.
 2. ARITHMETIC IS THE ONLY INDEPENDENT WITNESS they got, and it is a real one:
    a "merge" claim requires the Bakar chapter to hold exactly one FEWER verse
    than the KJV's, a "split" exactly one MORE. That check REJECTED 18 of 132
    claims outright — chapters off by two, where no single seam can explain the
    count. Those are not here.

So: the seam TYPE is verified, the seam LOCATION is not. A location that is
slightly wrong misaligns a few verses of one chapter; leaving the chapter to
identity misaligns every verse after the true seam. Mapping is the better bet,
but these deserve a verification pass before anyone calls them settled.

46 further chapters were reported as REFLOW — rearranged rather than seamed —
and are deliberately absent, left to identity rather than mapped on a guess.
1 Kings 2-8 and 22, the Exodus tabernacle chapters and the Job tail are all in
that set, which is exactly where the Septuagint is known to restructure.
"""

BAK_SEAM_RUNS = {

    0: [
        # ch 7: split at KJV 3 — Bakar 4 = «და მარხვად თესლი ყოველსა ქუეყანასა ზედა» = KJV 3b 'to keep seed alive upon the face of all the earth'; Bakar 5 = KJV 4 'For yet seven days.
        (7, 3, 3, 7, 3, 4),
        (7, 4, 24, 7, 5, 25),
        # ch 10: merge at KJV 9 — Bakar [9] contains BOTH KJV 9 and KJV 10: 'ესე იყო გმირი მონადირე წინაშე უფლისაჲ' (= 'He was a mighty hunter before the LORD') runs straight on into '
        (10, 9, 10, 10, 9, 9),
        (10, 11, 32, 10, 10, 31),
        # ch 21: split at KJV 32 — Bakar 1-31 = KJV 1-31 one-to-one (Bakar 31 = KJV 31, naming Beersheba, «ჯურღმული ფიცისა ... რამეთუ მუნ ფუცეს ორთავე»). Bakar 32 is a two-word fragment
        (21, 32, 32, 21, 32, 33),
        (21, 33, 34, 21, 34, 35),
        # ch 24: merge at KJV 33 — Bakar 24:1-32 are 1:1 with KJV (Abraham's oath, the ten camels, Rebekah at the well, the earring and bracelets). Bakar 33 ends «...და ჰრქუა : თქუჱნ და
        (24, 33, 34, 24, 33, 33),
        (24, 35, 67, 24, 34, 66),
        # ch 32: split at KJV 32 — bakar [31] 'ხოლო აღმოუჴდა მას მზე ... და იგი იკლებდა ბარკალსა თჳსსა' = KJV 31 (the sun rose upon him, he halted upon his thigh). bakar [32] is an EMPT
        (32, 32, 32, 32, 32, 33),
        # ch 33: merge at KJV 8 — Bakar 8 tail 'და თქუა ესავ : არიან ჩემდა ფრიად ძმაო : იყუნენ შენდად შენნი' = KJV 9 'And Esau said, I have enough, my brother; keep that thou hast unto
        (33, 8, 9, 33, 8, 8),
        (33, 10, 20, 33, 9, 19),
        # ch 50: merge at KJV 23 — Bakar 50:1-22 are one-to-one with KJV 1-22 (Bakar 22 = KJV 22, 'დაემკჳდრა იოსებ ეგვიპტეს ... ცხოვნდა იოსებ ასდა ათწელ' = dwelt in Egypt / lived 110 ye
        (50, 23, 24, 50, 23, 23),
        (50, 25, 26, 50, 24, 25),
    ],
    1: [
        # ch 8: split at KJV 16 — Bakar 16 «...განირთხ ჴელითა შენითა კუჱრთხი ეგე , დაეც მიწასა ქუეყანისას» / Bakar 17 «და იყოს მუმლი , კაცთა ზედა , და ოთხფერჴთა და ყოველსა ქუეყანასა , 
        (8, 16, 16, 8, 16, 17),
        (8, 17, 32, 8, 18, 33),
        # ch 11: split at KJV 5 — The extra Bakar slot is an EMPTY verse [6] sitting immediately after KJV 5. Bakar [5] is all of KJV 5 ('და მოსწყდეს ყოველი პირმშო ქუეყანასა ეგჳპტისასა
        (11, 5, 5, 11, 5, 6),
        (11, 6, 10, 11, 7, 11),
        # ch 16: merge at KJV 35 — Bakar 1-34 track KJV 1-34 one-to-one (quails at even + dew in the morning = bakar 13 = kjv 13; Aaron laying the omer before the Testimony = bakar 34 =
        (16, 35, 36, 16, 35, 35),
        # ch 21: merge at KJV 23 — Bakar 22 = KJV 22 (women strive, woman with child, no mischief, husband lays a fine). Bakar 23 carries BOTH KJV 23 and KJV 24: it opens «უკეთუ გამოხატ
        (21, 23, 24, 21, 23, 23),
        (21, 25, 36, 21, 24, 35),
    ],
    2: [
        # ch 3: split at KJV 17 — Bakar 17 «ყოველივე ცმელი უფლისაჲ სჯჳლად საუკუნოდ ნათესავსა შორის თქუენსა» ; Bakar 18 «ყოველი ცმელი და ყოველი სისხლი არა ჰჭამოთ ყოველთა შინა სავნებელთა
        (3, 17, 17, 3, 17, 18),
        # ch 7: split at KJV 15 — KJV 15 is divided in two. Bakar [15] = the first clause: 'და ჴორცი მსხუჱრპლისა ქებისა ცხოვრებასა მასავე იყოს' (= 'And the flesh of the sacrifice of hi
        (7, 15, 15, 7, 15, 16),
        (7, 16, 38, 7, 17, 39),
        # ch 11: split at KJV 34 — bakar 34 = KJV 34a ('და ყოველი საჭმელი, რომელი იჭამების... არაწმიდაჲ იყოს თქუენდა' = all meat which is eaten, whereon [water] cometh, shall be unclean
        (11, 34, 34, 11, 34, 35),
        (11, 35, 47, 11, 36, 48),
        # ch 13: merge at KJV 35 — Bakar 35 = KJV 35+36: "But if the scall spread in the skin after his cleansing, and the priest shall look, and behold the scall is spread in the skin,
        (13, 35, 36, 13, 35, 35),
        (13, 37, 59, 13, 36, 58),
    ],
    3: [
        # ch 6: merge at KJV 26 — Bakar 6:1-25 are word-for-word 1:1 with KJV (the Nazarite vow, no razor, the eighth-day turtledoves, the ram of the peace offering, the priestly bless
        (6, 26, 27, 6, 26, 26),
        # ch 11: merge at KJV 11 — bakar [10] = KJV 10 (Moses heard the people weep throughout their families). bakar [11] contains BOTH KJV 11 and 12 in one verse: 'რაჲსათჳს ბოროტი უყა
        (11, 11, 12, 11, 11, 11),
        (11, 13, 35, 11, 12, 34),
        # ch 20: split at KJV 28 — Bakar 1-27 track KJV 1-27 one-to-one (Bakar 13 = 'ესე არს წყალი ცილობისა' = KJV 13 water of Meribah; Bakar 22 = journeyed from Kadesh to mount Hor = K
        (20, 28, 28, 20, 28, 29),
        (20, 29, 29, 20, 30, 30),
    ],
    4: [
        # ch 2: split at KJV 14 — bakar 14 = KJV 14a ('და დღესა რომელსა შინა გამოხვედით კადით ბაჲრნეთ ვიდრე მოსულამდე ჴევსა მას ზარედისასა' = the space in which we came from Kadeshbarn
        (2, 14, 14, 2, 14, 15),
        (2, 15, 37, 2, 16, 38),
        # ch 19: split at KJV 15 — KJV 15 is one verse ("One witness shall not rise up against a man for any iniquity... at the mouth of two witnesses, or at the mouth of three witnesse
        (19, 15, 15, 19, 15, 16),
        (19, 16, 21, 19, 17, 22),
        # ch 31: merge at KJV 24 — Bakar 24 = «იყო რაჟამს დაასრულნა მოსე შთაწერად ყოველნი სიტყვანი ესე შჯულისანი წიგნთა მათ რომელთა აქუნ და კიდობანი იგი სჯულისა მის უფლისაჲ და ჰრქუა» — 
        (31, 24, 25, 31, 24, 24),
        (31, 26, 30, 31, 25, 29),
    ],
    5: [
        # ch 6: split at KJV 19 — bakar [18] 'ხოლო თქუენ ეკრძალენით შეჩვენებულისა მისგან ... და მოგუსრნეს ჩუენ' = KJV 18 in full (keep yourselves from the accursed thing). bakar [19] i
        (6, 19, 19, 6, 19, 20),
        (6, 20, 27, 6, 21, 28),
    ],
    6: [
        # ch 19: merge at KJV 26 — Bakar 19:1-25 are 1:1 with KJV (the Levite, the concubine, the four months, Jebus/Jerusalem, Gibeah, the old man of mount Ephraim, the sons of Belial)
        (19, 26, 27, 19, 26, 26),
        (19, 28, 30, 19, 27, 29),
    ],
    8: [
        # ch 20: split at KJV 42 — Bakar 42 ends '...შორის თესლისა ჩემისა და შორის თესლისა შენისა უკუნისამდე' = KJV 42a '...between my seed and thy seed for ever'; Bakar 43 'და აღდგა და
        (20, 42, 42, 20, 42, 43),
    ],
    9: [
        # ch 1: merge at KJV 26 — Bakar 1-25 = KJV 1-25 one-to-one (Bakar 24 = 'ტიროდით საულისათჳს ასულნო ისრაჱლისანო' = KJV 24 'Ye daughters of Israel, weep over Saul'; Bakar 25 = 'ვი
        (1, 26, 27, 1, 26, 26),
        # ch 4: split at KJV 9 — Bakar 9 «და მიუგო დავით რიხავს და ვანს , ძმასა მისსა ძეთა რემმონისა...» / Bakar 10 «და ჰრქუაჲ მათ ცხოველ არს უფალი რომელმან იჴსნა სული ჩემი ყოვლისაგან
        (4, 9, 9, 4, 9, 10),
        (4, 10, 12, 4, 11, 13),
        # ch 7: merge at KJV 15 — Bakar [15] carries KJV 15 and KJV 16 in one verse: 'ხოლო წყალობაჲ ჩემი არა განვაშორო მისგან' (= 'But my mercy shall not depart away from him') continu
        (7, 15, 16, 7, 15, 15),
        (7, 17, 29, 7, 16, 28),
        # ch 13: split at KJV 4 — KJV 4 is one verse containing both Jonadab's question and Amnon's answer. The Bakar splits it: bakar 4 = "and Jonadab said unto him, What is it that t
        (13, 4, 4, 13, 4, 5),
        (13, 5, 39, 13, 6, 40),
        # ch 14: merge at KJV 30 — Bakar 30 = «და ჰრქუაჲ აბესალომ ყრმათა მიმართ თჳსთა: შევედით ნაწილსა აგარაკსა ზედა იოაბისასა ... მოწჳთ იგი ცეცხლითა ... და აღდგა იოაბ და მოვიდა აბესალო
        (14, 30, 31, 14, 30, 30),
        (14, 32, 33, 14, 31, 32),
        # ch 20: merge at KJV 25 — Bakar 20:1-24 are 1:1 with KJV (Sheba son of Bichri, the ten concubines, Amasa smitten in the fifth rib, the wise woman of Abel, Joab over the host, B
        (20, 25, 26, 20, 25, 25),
        # ch 23: merge at KJV 36 — bakar [35] 'ასარაი კარმელელი : ურემ ძე ასვისა' = KJV 35 (Hezrai the Carmelite, Paarai the Arbite) — two names, matching KJV's pairing. bakar [36] carr
        (23, 36, 37, 23, 36, 36),
        (23, 38, 39, 23, 37, 38),
        # ch 24: split at KJV 15 — Bakar 15 'და გამოირჩია დავით თავისა თჳსისათჳს სიკუდილი . და დღენი იფქლის მკისანი' = LXX-only 'And David chose for himself death; and the days were of 
        (24, 15, 15, 24, 15, 16),
        (24, 16, 25, 24, 17, 26),
    ],
    10: [
        # ch 9: merge at KJV 27 — Despite 1 Kings being reflowed elsewhere, this chapter runs 1:1 for verses 1-26 (the LORD appears the second time, the twenty cities of Galilee and 't
        (9, 27, 28, 9, 27, 27),
        # ch 17: merge at KJV 22 — bakar [21] ends 'უფალო , ღმერთო ჩემო , მოაქციენ უკუე სული ყრმისა ამისავე . და იქმნა ეგრეთ' = KJV 21 plus the opening clause of LXX 17:22 ('and it was 
        (17, 22, 23, 17, 22, 22),
        (17, 24, 24, 17, 23, 23),
    ],
    11: [
        # ch 1: merge at KJV 17 — Bakar 1-16 are one-to-one with KJV 1-16 (Bakar 8 'კაცი წყლტუ და ერტყას ტყავი წელსა მისსა ... ელია თეზებიტელი არს ესე' = the hairy man with a leather g
        (1, 17, 18, 1, 17, 17),
        # ch 5: merge at KJV 15 — Bakar 1-14 = KJV 1-14 one-to-one (Bakar 14 = Naaman dipped himself seven times in Jordan, his flesh came again as a little child's). Bakar 15 contains
        (5, 15, 16, 5, 15, 15),
        (5, 17, 27, 5, 16, 26),
        # ch 6: merge at KJV 16 — Bakar 16 «...რამეთუ მრავალნი არს რომელ ჩუენ თანა . ვიდრეღა მათ თანა და ილოცაჲ ელისე ... აჰა მთა სავსე ცხენებითა , და ეტლებითა ცეცხლისათა გარემოს ელისე
        (6, 16, 17, 6, 16, 16),
        (6, 18, 33, 6, 17, 32),
        # ch 8: merge at KJV 16 — Bakar [16] runs the accession formula and the regnal-years formula together: 'და წელსა მეხუთესა იორამისასა ძისა აქაბისასა მეფისა ისრაჱლისა... გამეფდა 
        (8, 16, 17, 8, 16, 16),
        (8, 18, 29, 8, 17, 28),
        # ch 12: split at KJV 5 — bakar slot 6 is EMPTY — the numbering, not the text, gains a verse. bakar 5 = KJV 5 ('let the priests take it to them... let them repair the breaches 
        (12, 5, 5, 12, 5, 6),
        (12, 6, 21, 12, 7, 22),
        # ch 14: merge at KJV 28 — Bakar 1-27 match KJV 1-27 one-to-one (Amaziah 25 years old / 29 years reign; the thistle and cedar of Lebanon parable; Bethshemesh; Jonah son of Amitt
        (14, 28, 29, 14, 28, 28),
    ],
    12: [
        # ch 19: split at KJV 2 — Bakar 1 = KJV 1 (Nahash king of Ammon dies, Hanun reigns). KJV 2 is then two Georgian verses: Bakar 2 = 'And David said, I will shew kindness to Hanun
        (19, 2, 2, 19, 2, 3),
        (19, 3, 19, 19, 4, 20),
        # ch 21: merge at KJV 27 — bakar [26] 'და აღუშენა მუნ დავით საკურთხეველი უფალსა ... და ისმინა მისი ცეცხლითა ზეცითგარდამო' = KJV 26. bakar [27] contains BOTH KJV 27 and 28: 'და ჰ
        (21, 27, 28, 21, 27, 27),
        (21, 29, 30, 21, 28, 29),
    ],
    13: [
        # ch 3: merge at KJV 11 — Bakar 11 'და ფრთანი ქერუბინთანი , სიგრძე ოცი წყრთა და ერთი ფრთე ხუთი წყრთა , შემხებელი კედლისა სახლისა და მეორე ფრთე , წყრთა ხუთი , შემხებელი ფრთისა ქ
        (3, 11, 12, 3, 11, 11),
        (3, 13, 17, 3, 12, 16),
        # ch 6: merge at KJV 27 — Bakar 1-26 are one-to-one with KJV 1-26 (Bakar 13 = KJV 13, the brasen scaffold 'ხუთი წყრთა სიგრძე ... სამი წყრთა სიმაღლე' five cubits long, three cub
        (6, 27, 28, 6, 27, 27),
        (6, 29, 42, 6, 28, 41),
        # ch 7: merge at KJV 9 — Bakar 1-8 = KJV 1-8 one-to-one (Bakar 8 = the feast seven days, from the entering in of Hamath unto the river of Egypt = KJV 8). Bakar 9 holds KJV 9 a
        (7, 9, 10, 7, 9, 9),
        (7, 11, 22, 7, 10, 21),
        # ch 10: merge at KJV 18 — Bakar 18 «...და ივლტოდა იჱრუსალიმს შინა და განდგეს ისრაჱლნი სახლისაგან დავითისა ვიდრე დღეინდელად დღედმდე ამისა» = KJV 18 + 19.
        (10, 18, 19, 10, 18, 18),
        # ch 17: split at KJV 14 — KJV 14 divides at its colon. Bakar [14] is the heading clause alone: 'და ესე არს რიცხჳ მათი სახლთაებრ მამულთა მათთა' (= 'And these are the numbers of 
        (17, 14, 14, 17, 14, 15),
        (17, 15, 19, 17, 16, 20),
        # ch 20: merge at KJV 35 — bakar 35 carries both KJV 35 ('და შემდგომად ამისა შეიერთა იოსაფათ, მეფე იუდასა, ოქოზიას, მეფისა ისრაჱლისა თანა' = after this did Jehoshaphat king of J
        (20, 35, 36, 20, 35, 35),
        (20, 37, 37, 20, 36, 36),
        # ch 31: merge at KJV 20 — Bakar 1-19 = KJV 1-19 one-to-one (Bakar 19 = KJV 19, the sons of Aaron in the fields of the suburbs, portions to all the males). Bakar 20 then carries
        (31, 20, 21, 31, 20, 20),
        # ch 33: merge at KJV 23 — bakar [22] 'და ქმნა ბოროტი წინაშე უფლისა , ვითარცა ჰყოფდა მანასე , მამა მისი ...' = KJV 22 (Amon did evil as did Manasseh his father). bakar [23] carr
        (33, 23, 24, 33, 23, 23),
        (33, 25, 25, 33, 24, 24),
        # ch 35: merge at KJV 26 — Bakar 26 'ხოლო სხუანი სიტყუანი იოსიასა და სასოება მისნი იყვნეს წერილნი სჯულსა უფლისსა , ხოლო საქმენი მისნი პირველნი და უკანასკნელნი , აჰა , წერილარიან
        (35, 26, 27, 35, 26, 26),
    ],
    14: [
        # ch 2: merge at KJV 44 — The census lists align name-for-name and number-for-number through Bakar 43 = KJV 43 (the Nethinims: Ziha, Hasupha, Tabbaoth — three names). Bakar 44 
        (2, 44, 45, 2, 44, 44),
        (2, 46, 70, 2, 45, 69),
        # ch 7: merge at KJV 7 — Bakar 7 «...იერუსალემსა მეშჳდესა არტაკსერეკსის მეფისასა : და მოვიდეს იერუსალიმს შინა თუესა მეხუთესა ესე წერილ არს წელი მეშჳდე მეფისა» = KJV 7 + 8.
        (7, 7, 8, 7, 7, 7),
        (7, 9, 28, 7, 8, 27),
    ],
    15: [
        # ch 1: merge at KJV 4 — A three-into-one merge plus an empty slot. Bakar [4] contains KJV 4, 5 AND 6 continuously: 'და ვტიროდი და ვგოდებდი დღე მრავალ და ვიქმენ მარხულ და ვევე
        (1, 4, 5, 1, 4, 4),
        (1, 6, 11, 1, 5, 10),
        # ch 5: merge at KJV 16 — Bakar 1-15 track KJV 1-15 (the cry of the people; "I shook my lap" at bakar 13 = kjv 13; the twelve years from the twentieth to the two-and-thirtieth 
        (5, 16, 17, 5, 16, 16),
        (5, 18, 19, 5, 17, 18),
        # ch 6: split at KJV 10 — Bakar 10 = «ხოლო მე შევედ სახლსა სემეავსასა ძისა დალაივასა, ძისა მეთავეილევასა, და იგი დაჴშული და ჰრქუა» — 'I came unto the house of Shemaiah the son 
        (6, 10, 10, 6, 10, 11),
        (6, 11, 19, 6, 12, 20),
        # ch 8: merge at KJV 17 — Bakar 8:1-16 are 1:1 with KJV (the water gate, Ezra's pulpit of wood with the named men on his right and left, the Levites causing the people to under
        (8, 17, 18, 8, 17, 17),
    ],
    17: [
        # ch 3: merge at KJV 25 — Bakar 1-24 = KJV 1-24 one-to-one (Bakar 24 = 'რამეთუ პირველ საჭმელთა ჩემთა სულთქმით შემოვალს' = KJV 24 'For my sighing cometh before I eat'). Bakar 25
        (3, 25, 26, 3, 25, 25),
        # ch 6: merge at KJV 27 — Bakar 27 «გარნა ვითარცა ობოლსა ზედა დაესხნეთ ხოლო მირბით მეგობარსა ზედა თქვენსა . ხოლო აწ მივხედო პირსა ზედა თქვენსა , არა ვსტყუო» = KJV 27 + 28; Baka
        (6, 27, 28, 6, 27, 27),
        (6, 29, 30, 6, 28, 29),
        # ch 16: split at KJV 4 — KJV 4 divides mid-verse. Bakar [4] = 'მიცა ვითარცა თქუენ ვიტყოდე, უკუეთუმცა ქვაჲ მდებარე იყოს სული თქვენი ნაცვლად ჩემისა' (= 'I also could speak as ye
        (16, 4, 4, 16, 4, 5),
        (16, 5, 22, 16, 6, 23),
    ],
    19: [
        # ch 13: split at KJV 13 — Bakar 1-13 are one-to-one with KJV 1-13 (Bakar 12 = KJV 12 'ხე ცხორებისა სურვილი კეთილი' = the desire cometh, it is a tree of life; Bakar 13 = KJV 13,
        (13, 13, 13, 13, 13, 14),
        (13, 14, 25, 13, 15, 26),
        # ch 18: split at KJV 22 — Bakar 23 «რომელი განსდევნის დედაკაცსა კეთილსა , განსდევნის კეთილთა ...» = cu 18:23 «Иже изгоняет жену добрую, изгоняет благая...»; Bakar 24 tail «ვედრ
        (18, 22, 22, 18, 22, 23),
        (18, 23, 24, 18, 24, 25),
        # ch 25: split at KJV 20 — The extra verse is the Septuagint-only colon at Prov 25:20a. bakar 20 = KJV 20 in its LXX form ('ვითარცა ძმარი არა სარგებელ არს წყლულისა, და კვამლი თვ
        (25, 20, 20, 25, 20, 21),
        (25, 21, 28, 25, 22, 29),
        # ch 29: split at KJV 25 — Bakar 1-25 track KJV 1-25, and bakar 25 = KJV 25 ("they that fear and are ashamed of men are tripped up, but he that trusteth in the LORD shall rejoic
        (29, 25, 25, 29, 25, 26),
        (29, 26, 27, 29, 27, 28),
    ],
    20: [
        # ch 11: split at KJV 3 — KJV 3 is two Bakar verses, cut exactly at the KJV's own colon. Bakar 3 = KJV 3a: 'ოკუეთუ აღივსოს ღრუბელი წჳმითაჲ , ქუეყანასა ზედა გარდა ადინებენ' (if 
        (11, 3, 3, 11, 3, 4),
        (11, 4, 10, 11, 5, 11),
    ],
    21: [
        # ch 1: merge at KJV 1 — The Georgian chapter has no superscription verse. Bakar 1 = 'ამბორს მიყვეს მე ამბორის ყოფისაგან პირისა თჳსისათა, რამეთუ უმჯობეს არიან ძუძუნი შენნი უფრ
        (1, 1, 2, 1, 1, 1),
        (1, 3, 17, 1, 2, 16),
    ],
    22: [
        # ch 27: merge at KJV 12 — KJV 27:12 ('the LORD shall beat off from the channel of the river unto the stream of Egypt, and ye shall be gathered one by one') has no Georgian coun
        (27, 12, 13, 27, 12, 12),
        # ch 45: split at KJV 23 — Bakar 23 = «თავისა მიმართ ჩემისა ვფუცავ. გამოვიდეს თქუენდა პირისა ჩემისაგან სიმართლე და სიტყუაჲნი ჩემნი არა გარე მიიქცენ» — 'I have sworn by myself, r
        (45, 23, 23, 45, 23, 24),
        (45, 24, 25, 45, 25, 26),
        # ch 48: merge at KJV 21 — Bakar 48:1-20 are 1:1 with KJV (the house of Jacob called by the name of Israel, 'thy neck is an iron sinew and thy brow brass', 'I have refined thee 
        (48, 21, 22, 48, 21, 21),
        # ch 52: split at KJV 10 — bakar [9] = KJV 9 (break forth into joy, ye waste places of Jerusalem). bakar [10] 'და გამოაცხადოს უფალმან მკლავი თჳსი წმიდაჲ წინაშე ყოველთა წარმართთა
        (52, 10, 10, 52, 10, 11),
        (52, 11, 15, 52, 12, 16),
    ],
    23: [
        # ch 7: merge at KJV 16 — Bakar 16 'და შენ ნუ ილოცავ მწედ ერისა ამის ... რამეთუ არა ვისმინო' = KJV 16, ending there; Bakar 17 'ძენი მათნი შეიკრებენ შეშათა , და მამანი მათნი აღა
        (7, 16, 17, 7, 16, 16),
        (7, 18, 34, 7, 17, 33),
        # ch 13: merge at KJV 24 — Bakar 1-23 are one-to-one with KJV 1-23 (Bakar 23 = KJV 23, 'უკუეთუ ცვალოს ეთიოპელმან ტყავი თჳსი და ვეფხვმან სიჭრელენი მისნი' = can the Ethiopian chan
        (13, 24, 25, 13, 24, 24),
        (13, 26, 27, 13, 25, 26),
        # ch 37: merge at KJV 4 — Bakar 1-3 = KJV 1-3 (Zedekiah made king in place of Coniah; he and his servants hearkened not; he sent Jehucal son of Shelemiah and Zephaniah son of M
        (37, 4, 5, 37, 4, 4),
        (37, 6, 21, 37, 5, 20),
        # ch 39: merge at KJV 16 — Bakar 16 «...და გაცხოვნო შენ მას დღესა შინა , თქუა უფალმან და არ მიგცე შენ ჴელთა კაცთასა , რომელთაგან შენ გეშინის» = KJV 17 fused onto 16.
        (39, 16, 17, 39, 16, 16),
        (39, 18, 18, 39, 17, 17),
    ],
    25: [
        # ch 2: merge at KJV 9 — Bakar [9] holds KJV 9 and 10 together: 'და ვიხილე, და აჰა ჴელი განმარტებული ჩემდამო, და მას შინა თავი წიგნისაჲ' (= KJV 9, 'And when I looked, behold, 
        (2, 9, 10, 2, 9, 9),
        # ch 4: split at KJV 6 — bakar 6 = KJV 6a only ('და შეასრულნე იგინი შენი, და დასწვე გუჱრდსა შენსა ზედა მარჯუჱნესა მეორედ' = and when thou hast accomplished them, lie again on 
        (4, 6, 6, 4, 6, 7),
        (4, 7, 17, 4, 8, 18),
        # ch 7: split at KJV 24 — The extra Bakar verse is an EMPTY SLOT, not extra text. Bakar 1-24 match KJV 1-24 verse for verse (including the KJV/MT order at vv. 3-9, i.e. this wi
        (7, 24, 24, 7, 24, 25),
        (7, 25, 27, 7, 26, 28),
        # ch 10: merge at KJV 15 — Bakar 15 = «და აღიმაღლეს ქეროვიმთა, ესე ცხოველი რომელი ვიხილე მდინარესა ზედა ქობარისასა» (KJV 15, 'the cherubims were lifted up; this is the living cr
        (10, 15, 16, 10, 15, 15),
        (10, 17, 22, 10, 16, 21),
        # ch 18: split at KJV 30 — Bakar 18:1-29 are 1:1 with KJV (the sour-grapes proverb, 'all souls are mine', the just man, the robber son, the son who sees his father's sins, 'the 
        (18, 30, 30, 18, 30, 31),
        (18, 31, 32, 18, 32, 33),
        # ch 19: merge at KJV 13 — bakar [12] 'და შეიმუსრა გულისწყრომითა ქუეყანასა ზედა დავარდა და ქარი შემწუველი განაჴმობდა რჩეულთა მისთა ... ცეცხლმან განლია იგი' = KJV 12 (plucked up 
        (19, 13, 14, 19, 13, 13),
        # ch 20: merge at KJV 48 — Bakar 48 'და ცნას ყოველმან ჴორცმან ვითარმედ მე უფალმან აღვაგზენ იგი და არა დავშრიტო , და ვთქუ ნუსადა უფალო უფალო , იგინი მეტყჳან მე ანუ არა იგავი თქუმ
        (20, 48, 49, 20, 48, 48),
        # ch 29: split at KJV 12 — KJV 12 is two Bakar verses, cut at the KJV's own final comma. Bakar 12 = KJV 12a, ending 'და განვსთესო ეგჳპტე წარმართთა შორის' (and I will scatter the
        (29, 12, 12, 29, 12, 13),
        (29, 13, 21, 29, 14, 22),
        # ch 30: merge at KJV 24 — Bakar 1-23 = KJV 1-23 one-to-one (Bakar 23 = 'და განვსთესნე მეგჳპტელნი წარმართთა შორის და განვფიწლნე იგინი სოფლებთა მიმართ' = KJV 23 'I will scatter t
        (30, 24, 25, 30, 24, 24),
        (30, 26, 26, 30, 25, 25),
        # ch 31: merge at KJV 13 — Bakar 13 «და დაცემასა მისსა ზედა განისუენეს ყოველთა მფრინველთა ცისათა ... რაჲთა არა აღმაღლდენ სიდიდესა თანა მათსა ყოველნი ხენი წყლის ზედანი ...» = KJV
        (31, 13, 14, 31, 13, 13),
        (31, 15, 18, 31, 14, 17),
        # ch 35: split at KJV 15 — The final verse divides. Bakar [15] = 'ვითარ იგი იხარე მკჳდრობასა სახლისა ისრაჱლისასა, ვითარ უჩინო იქმნა, ეგრეთ გიყო შენ' (= 'As thou didst rejoice at
        (35, 15, 15, 35, 15, 16),
    ],
    27: [
        # ch 5: split at KJV 1 — KJV 1 ends "...because ye have been a snare on Mizpah, and a net spread upon Tabor." The Bakar cuts that in two: bakar 1 ends at "a snare to the watch
        (5, 1, 1, 5, 1, 2),
        (5, 2, 15, 5, 3, 16),
        # ch 11: merge at KJV 11 — Bakar 11 = «განჰკრთენ ვითარცა მფრინველი ეგჳპტით გამო, და ვითარცა ტრედი ქუეყანით გამო ასსურასტანელთაჲთ. და კუალად ვაგნე იგინი, სახლთავე მათთა იტყჳს უფა
        (11, 11, 12, 11, 11, 11),
    ],
    29: [
        # ch 6: split at KJV 10 — Bakar 10 ends '...და ჰრქუას ზედა მდგომელთა სახლისათა უკუეთუ არსღა შენ თანა' = KJV 10a '...and shall say unto him that is by the sides of the house, Is
        (6, 10, 10, 6, 10, 11),
        (6, 11, 14, 6, 12, 15),
    ],
    32: [
        # ch 5: merge at KJV 11 — Bakar 11 «და მოვსრნე ქალაქნი ქუჱყანისა შენისანი , და აღვიხუნე ყოველნი სიმაგრენი შენნი , და აღვიხუნე ყოველნი გრძნებანი შენნი ჴელთაგან შენთა და აღმომჴმო
        (5, 11, 12, 5, 11, 11),
        (5, 13, 15, 5, 12, 14),
    ],
    34: [
        # ch 1: merge at KJV 15 — Bakar [15] contains KJV 15 and 16 in one verse: 'მოსასრულებელად სამჭედურთა აღმოიტაცა და მოიზიდა იგი სათხევლითა, და შეკრიბა იგი სათრომელთა მიერ მისთა' 
        (1, 15, 16, 1, 15, 15),
        (1, 17, 17, 1, 16, 16),
    ],
    35: [
        # ch 1: split at KJV 18 — bakar 18 = KJV 18a ('და ვეცხლი მათი და ოქროჲ მათი ვერ შემძლებელ არს განრინებად მათდა დღესა შინა რისხვისა უფლისასა' = neither their silver nor their go
        (1, 18, 18, 1, 18, 19),
    ],
    36: [
        # ch 2: split at KJV 3 — Bakar 3 = KJV 3 complete; Bakar 4 = '' (empty); Bakar 5 = KJV 4 complete; and the +1 offset then holds all the way down — Bakar 11 = KJV 10 (four and 
        (2, 3, 3, 2, 3, 4),
        (2, 4, 23, 2, 5, 24),
    ],
    37: [
        # ch 7: split at KJV 5 — Bakar 7:1-4 are 1:1 with KJV (the fourth year of Darius, the fourth day of the ninth month Chisleu; Sherezer and Regemmelech sent to Bethel; the quest
        (7, 5, 5, 7, 5, 6),
        (7, 6, 14, 7, 7, 15),
    ],
    40: [
        # ch 15: merge at KJV 27 — FIRST seam — bakar [27] holds KJV 27 AND 28, with the print's verse-28 numeral left INSIDE the text: 'და მის თანა ჯუარს აცუნეს ორნი ავაზაკნი : ერთი მა
        (15, 27, 28, 15, 27, 27),
        (15, 29, 47, 15, 28, 46),
    ],
    41: [
        # ch 9: merge at KJV 61 — Bakar 61 'ჰრქუაჲ მას სხვამან : მეცა მიგდევდე შენ უფალო : ხოლო პირველად მიბრძანე ჯმნა , სახლეულთა ჩემთაგან' (KJV 61) followed in the same slot by 'ჰრქუ
        (9, 61, 62, 9, 61, 61),
    ],
    42: [
        # ch 1: split at KJV 38 — KJV 38 is two Bakar verses. Bakar 38 = KJV 38a: 'მოექცა იესუ , და იხილნა იგინი მირაჲსდევდეს მას , და ჰრქუა მათ' (then Jesus turned, and saw them follo
        (1, 38, 38, 1, 38, 39),
        (1, 39, 51, 1, 40, 52),
        # ch 14: split at KJV 11 — Bakar 1-10 = KJV 1-10 one-to-one (Bakar 10 = 'არა გრწამსა, რამეთუ მე მამისა თანა ვარ... არამედ მამა ჩემი, რომელი ჩემ თანა არს, იგი იქმს საქმესა' = KJV
        (14, 11, 11, 14, 11, 12),
        (14, 12, 31, 14, 13, 32),
        # ch 18: split at KJV 36 — Bakar 36 = KJV 36 «მეუფება ჩემი არა ამის სოფლისაგანი არს»; Bakar 37 = "" (empty); Bakar 38 «ჰრქუა მას პილატე : უკუჱთუ მეუფ ხარ შენ ;» = KJV 37 'Art th
        (18, 36, 36, 18, 36, 37),
        (18, 37, 40, 18, 38, 41),
    ],
    43: [
        # ch 17: merge at KJV 32 — Bakar [32] holds KJV 32 and 33: 'ხოლო მათ ვითარცა ესმა აღდგომაჲ მკუდართა, რომელნიმე ეკიცხევდეს და რომელთამე თქუეს: ვისმინოთ შენი ამისთჳს კუალადცა' (= 
        (17, 32, 33, 17, 32, 32),
        (17, 34, 34, 17, 33, 33),
        # ch 19: merge at KJV 40 — bakar 40 carries both KJV 40 ('რამეთუ ვიურვით ბრალობად შფოთისა ამისათვისცა დღეინდელისა, რამეთუ არარაჲ მიზეზი იყო' = we are in danger to be called in q
        (19, 40, 41, 19, 40, 40),
        # ch 28: merge at KJV 30 — Bakar 1-29 match KJV 1-29 one-to-one (Melita; the viper; Publius; Castor and Pollux at bakar 11 = kjv 11; Appii forum and the Three Taverns at bakar 1
        (28, 30, 31, 28, 30, 30),
    ],
    44: [
        # ch 2: split at KJV 16 — Bakar 16 = KJV 16 ('in the day when God shall judge the secrets of men by Jesus Christ according to my gospel'); Bakar 17 = «დასასრული კვირიაკისა» alo
        (2, 16, 16, 2, 16, 17),
        (2, 17, 29, 2, 18, 30),
        # ch 7: merge at KJV 9 — Bakar 7:1-8 are 1:1 with KJV (the law hath dominion as long as a man liveth, the woman bound to her husband, 'ye also are become dead to the law by th
        (7, 9, 10, 7, 9, 9),
        (7, 11, 25, 7, 10, 24),
        # ch 8: split at KJV 9 — bakar [9] 'ხოლო თქუენ არა ხართ ჴორცთა შინა , არამედ სულთა : უკუეთუ სული ღმრთისაჲ დამკჳდრებულ არს თქუენ შორის' = KJV 9a ONLY (ye are not in the flesh b
        (8, 9, 9, 8, 9, 10),
        (8, 10, 39, 8, 11, 40),
        # ch 11: split at KJV 2 — Bakar 2 'არა განიშორა ღმერთმან ერი თჳსი , რომელი იგი წინაწარ იცნა' = KJV 2a; Bakar 3 'ანუ არა უწყითა ელიაჲსი რაჲსა იგი იტყჳს წიგნი : ვითარ იგი შეემთხუ
        (11, 2, 2, 11, 2, 3),
        (11, 3, 36, 11, 4, 37),
    ],
    46: [
        # ch 7: split at KJV 10 — KJV 10 is two Bakar verses, cut at the KJV's own colon. Bakar 10 = KJV 10a: 'რამეთუ ღმრთისა მიერი იგი , მწუხარებაჲ სინანულისა ცხორებისასა შეუნანებელსა
        (7, 10, 10, 7, 10, 11),
        (7, 11, 16, 7, 12, 17),
        # ch 13: merge at KJV 12 — Bakar 12 «მოიკითხევდით ურთიერთას ამბორის ყოფითა წმიდითა . გიკითხვენ თქუენ წმიდაჲნი ყოველნი» = KJV 12 + 13; Bakar 13 «მადლი უფლისაჲ ჩუენისა იესუ ქრისტე
        (13, 12, 13, 13, 12, 12),
        (13, 14, 14, 13, 13, 13),
    ],
    47: [
        # ch 1: merge at KJV 2 — The seam is very early. Bakar [1] = KJV 1 (Paul an apostle, not of men, neither by man, but by Jesus Christ and God the Father who raised him from the
        (1, 2, 3, 1, 2, 2),
        (1, 4, 24, 1, 3, 23),
    ],
    54: [
        # ch 4: split at KJV 11 — bakar 11 = KJV 11a alone ('ლუკა არს მარტო ჩემ თანა' = Only Luke is with me); bakar 12 = KJV 11b ('მარკოზ აღადგინე და მოიყვანე შენ თანა, რამეთუ საჴმარ 
        (4, 11, 11, 4, 11, 12),
        (4, 12, 22, 4, 13, 23),
    ],
    57: [
        # ch 10: split at KJV 38 — KJV 38 is one verse: "Now the just shall live by faith: but if any man draw back, my soul shall have no pleasure in him." The Bakar cuts it exactly at
        (10, 38, 38, 10, 38, 39),
        (10, 39, 39, 10, 40, 40),
    ],
    58: [
        # ch 4: split at KJV 16 — Bakar 1-16 = KJV 1-16 verified one-to-one at anchors (Bakar 6 = KJV 6, 'God resisteth the proud but giveth grace to the humble'; Bakar 12 = KJV 12, 't
        (4, 16, 16, 4, 16, 17),
        (4, 17, 17, 4, 18, 18),
    ],
    63: [
        # ch 1: split at KJV 14 — The classic Greek 3 John tail. Bakar 1-13 are 1:1 with KJV (the elder to wellbeloved Gaius, Diotrephes who loveth the preeminence, Demetrius, 'I will 
        (1, 14, 14, 1, 14, 15),
    ],
    65: [
        # ch 12: split at KJV 17 — bakar [17] 'და განრისხნა ვეშაპი იგი დედაკაცისა მისთჳს და წარვიდა ბრძოლისა ყოფად სხუათა მათ თანა თესლისა მისისთა' = KJV 17 in full (the dragon was wrot
        (12, 17, 17, 12, 17, 18),
        # ch 22: merge at KJV 12 — Bakar 12 'და აჰა მოვალ ადრე , და სასყიდელი მივაგო საქმეთა მათთაებრ . მე ვარ ანი და ჵოე , პირველი და უკანასკნელი , დასაბამი და დასასრული' — KJV 12 and 
        (22, 12, 13, 22, 12, 12),
        (22, 14, 21, 22, 13, 20),
    ],
}
