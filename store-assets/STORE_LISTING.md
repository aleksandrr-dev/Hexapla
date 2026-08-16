# Hexapla — store listing text (RuStore / Google Play)

## RuStore per-version Safety form (asked on every upload)

Requested data: select nothing (0/38 — app collects no data).
POST_NOTIFICATIONS reason:

> Разрешение POST_NOTIFICATIONS используется исключительно для двух функций:
> 1) необязательное ежедневное напоминание о чтении Библии, которое
> пользователь сам включает в настройках (по умолчанию выключено);
> 2) медиа-уведомление с элементами управления воспроизведением при фоновом
> прослушивании аудио (чтение Библии вслух). Рекламные и маркетинговые
> уведомления не отправляются.

Screenshot upload order (strongest first — reused for any store):
1) lock-screen media card with Doré art during audio, 2) red letters
(Matthew 5), 3) split view (KJV ‖ Синодальный, Titus 1), 4) Good News tab,
5) Strong's popup (H3068), 6) widget (`screenshot_widget.png` here).

Localized reader screenshots (John 1 in the language's own translation,
`screenshot_reader_{ja,zh_cn,zh_tw,pt,it,sv,da,ta}.png`, generator
`tools/make_reader_shot.py`): lead with the reader shot on that
language's Play listing, then the order above.

## Release-notes format — STANDARD (owner request 2026-07-23)

Release notes ("What's new") are kept as a **full Play-Console copy-paste
block**: every listing locale in its own `<locale>…</locale>` tag, matching
Play's own "What's new" locale list, so the whole set pastes in at once
instead of entering each language by hand. For each new release, FILL EVERY
locale (reuse the previous release's wording where a phrase is stable; only
the changed facts need new translation). Keep each note under Play's
500-character limit. ⚠ be / hy-AM / iw-IL / ta-IN translations are
best-effort and native review is still pending (same open item as those
languages' listing text) — safe to ship, refine when a native speaker is
available. Locale notes: iw-IL is Play's code for Hebrew; es-419/es-ES/es-US
share one Spanish text; fr-CA/fr-FR share one French text; zh-CN is
Simplified, zh-HK/zh-TW are Traditional. Older release sections below predate
this standard and keep their EN/RU/DE-only form (historical, do not reformat).

★ **VALIDATE BEFORE PASTING — `python tools/check_release_notes.py`.**
Both defects that hit the 1.6.1 paste were mechanical and invisible to reading:
en-IN was missing (30 of Play's 31 locales — the block predated that locale
being added to the account), and ta-IN was 507 against the 500 cap, because an
earlier wording fix swapped a 19-character Tamil phrase for a 31-character one
and only English was re-measured afterwards. ⚠ RE-RUN IT AFTER ANY EDIT THAT
TOUCHES MORE THAN ONE LOCALE — a substitution that fits in English can push
another language over. The check covers: locale set exactly matches Play's
list, locale ORDER matches Play's (so the block pastes in one go), every entry
≤ 500 chars, nothing empty or placeholder, and only ONE release block above
the descriptions section.

★ **ONLY THE CURRENT RELEASE'S NOTES LIVE AT THE TOP** (owner, 2026-07-28).
When a release ships, move its block down under the
`# ── ARCHIVE: older release notes (historical) ──` banner at the END of this
## 1.6.4 release notes (paste per store)

<en-US>
The Persian Bible is complete: William Glen's Old Testament of 1856 joins Henry Martyn's New Testament, transcribed page by page from the original printing for this app. The Church Slavonic Bible is now fully narrated, and the Russian apocrypha too. Strong's dictionary now reads in Russian — every Hebrew and Greek entry — for readers of the Synodal Bible. Book covers now rotate: the most-read books show a different engraving each day. Now 36 translations in 30 languages.
</en-US>

<ar>
اكتمل الكتاب المقدس بالفارسية: عهد وليم غلن القديم (1856) ينضم إلى عهد هنري مارتن الجديد، منسوخًا صفحةً صفحةً عن الطبعة الأصلية من أجل هذا التطبيق. والكتاب المقدس بالسلافونية الكنسية صار له تسجيل صوتي كامل، وكذلك الأسفار القانونية الثانية بالروسية. وقاموس سترونغ صار متاحًا بالروسية بكل مداخله العبرية واليونانية. وأغلفة الأسفار صارت تتبدل: الأسفار الأكثر قراءةً تعرض نقشًا مختلفًا كل يوم. الآن 36 ترجمة بـ30 لغة.
</ar>

<be>
Персідская Біблія поўная: Стары Запавет Уільяма Глена 1856 года далучыўся да Новага Запавету Генры Мартына — перапісаны старонка за старонкай з арыгінальнага друку. Царкоўнаславянская Біблія поўнасцю агучана, як і рускія апокрыфы. Слоўнік Стронга цяпер чытаецца па-руску: усе яўрэйскія і грэчаскія артыкулы. Вокладкі кніг цяпер чаргуюцца: найбольш чытаныя кнігі паказваюць новую гравюру кожны дзень. Цяпер 36 перакладаў на 30 мовах.
</be>

<cs-CZ>
Perská Bible je úplná: Starý zákon Williama Glena z roku 1856 se připojuje k Novému zákonu Henryho Martyna — přepsán stránku po stránce z původního tisku. Církevněslovanská Bible má nyní úplnou zvukovou nahrávku, stejně jako ruské apokryfy. Strongův slovník je nyní i rusky, všechna hebrejská i řecká hesla. Obálky knih se nyní střídají: nejčtenější knihy ukazují každý den jinou rytinu. Nyní 36 překladů ve 30 jazycích.
</cs-CZ>

<da-DK>
Den persiske bibel er komplet: William Glens Gamle Testamente fra 1856 slutter sig til Henry Martyns Nye Testamente — afskrevet side for side fra originaltrykket. Den kirkeslaviske bibel er nu fuldt indlæst, og de russiske apokryfer med. Strongs ordbog findes nu på russisk med alle hebraiske og græske opslag. Bogomslag skifter nu: de mest læste bøger viser et nyt stik hver dag. Nu 36 oversættelser på 30 sprog.
</da-DK>

<de-DE>
Die persische Bibel ist vollständig: das Alte Testament von William Glen (1856) tritt zum Neuen Testament Henry Martyns — Seite für Seite aus dem Originaldruck übertragen. Die kirchenslawische Bibel ist jetzt vollständig vertont, ebenso die russischen Apokryphen. Strongs Wörterbuch gibt es jetzt auf Russisch, alle hebräischen und griechischen Einträge. Buchtitelbilder wechseln nun täglich bei den meistgelesenen Büchern. Jetzt 36 Übersetzungen in 30 Sprachen.
</de-DE>

<el-GR>
Η περσική Βίβλος ολοκληρώθηκε: η Παλαιά Διαθήκη του Ουίλιαμ Γκλεν (1856) προστίθεται στην Καινή Διαθήκη του Χένρι Μάρτιν — αντιγραμμένη σελίδα προς σελίδα από την αρχική έκδοση. Η εκκλησιαστική σλαβονική Βίβλος ηχογραφήθηκε πλήρως, όπως και τα ρωσικά απόκρυφα. Το λεξικό Strong διατίθεται τώρα και στα ρωσικά. Τα εξώφυλλα εναλλάσσονται: τα πιο διαβασμένα βιβλία δείχνουν κάθε μέρα άλλη χαλκογραφία. Τώρα 36 μεταφράσεις σε 30 γλώσσες.
</el-GR>

<en-IN>
The Persian Bible is complete: William Glen's Old Testament of 1856 joins Henry Martyn's New Testament, transcribed page by page from the original printing for this app. The Church Slavonic Bible is now fully narrated, and the Russian apocrypha too. Strong's dictionary now reads in Russian — every Hebrew and Greek entry — for readers of the Synodal Bible. Book covers now rotate: the most-read books show a different engraving each day. Now 36 translations in 30 languages.
</en-IN>

<es-419>
La Biblia en persa está completa: el Antiguo Testamento de William Glen (1856) se une al Nuevo Testamento de Henry Martyn, transcrito página por página de la impresión original. La Biblia en eslavo eclesiástico ya está narrada por completo, y los apócrifos rusos también. El diccionario de Strong ya se lee en ruso, con todas sus entradas hebreas y griegas. Las portadas rotan: los libros más leídos muestran cada día otro grabado. Ahora 36 traducciones en 30 idiomas.
</es-419>

<es-ES>
La Biblia en persa está completa: el Antiguo Testamento de William Glen (1856) se une al Nuevo Testamento de Henry Martyn, transcrito página por página de la impresión original. La Biblia en eslavo eclesiástico ya está narrada por completo, y los apócrifos rusos también. El diccionario de Strong ya se lee en ruso, con todas sus entradas hebreas y griegas. Las portadas rotan: los libros más leídos muestran cada día otro grabado. Ahora 36 traducciones en 30 idiomas.
</es-ES>

<es-US>
La Biblia en persa está completa: el Antiguo Testamento de William Glen (1856) se une al Nuevo Testamento de Henry Martyn, transcrito página por página de la impresión original. La Biblia en eslavo eclesiástico ya está narrada por completo, y los apócrifos rusos también. El diccionario de Strong ya se lee en ruso, con todas sus entradas hebreas y griegas. Las portadas rotan: los libros más leídos muestran cada día otro grabado. Ahora 36 traducciones en 30 idiomas.
</es-US>

<fi-FI>
Persiankielinen Raamattu on täydellinen: William Glenin vuoden 1856 Vanha testamentti liittyy Henry Martynin Uuteen testamenttiin — jäljennettynä sivu sivulta alkuperäisestä painoksesta. Kirkkoslaavilainen Raamattu on nyt kokonaan äänitetty, samoin venäjän apokryfikirjat. Strongin sanakirja on nyt myös venäjäksi, kaikki heprean ja kreikan hakusanat. Kirjojen kannet vaihtuvat: luetuimmat kirjat näyttävät joka päivä eri kuparipiirroksen. Nyt 36 käännöstä 30 kielellä.
</fi-FI>

<fr-CA>
La Bible en persan est complète : l'Ancien Testament de William Glen (1856) rejoint le Nouveau Testament d'Henry Martyn, transcrit page à page depuis l'impression d'origine. La Bible en slavon d'église est désormais entièrement narrée, et les apocryphes russes aussi. Le dictionnaire Strong se lit désormais en russe, toutes ses entrées hébraïques et grecques. Les couvertures changent chaque jour pour les livres les plus lus. Désormais 36 traductions en 30 langues.
</fr-CA>

<fr-FR>
La Bible en persan est complète : l'Ancien Testament de William Glen (1856) rejoint le Nouveau Testament d'Henry Martyn, transcrit page à page depuis l'impression d'origine. La Bible en slavon d'église est désormais entièrement narrée, et les apocryphes russes aussi. Le dictionnaire Strong se lit désormais en russe, toutes ses entrées hébraïques et grecques. Les couvertures changent chaque jour pour les livres les plus lus. Désormais 36 traductions en 30 langues.
</fr-FR>

<hu-HU>
A perzsa Biblia teljes: William Glen 1856-os Ószövetsége Henry Martyn Újszövetségéhez csatlakozik — oldalról oldalra átírva az eredeti nyomtatványból. Az egyházi szláv Biblia most teljes hangfelvételt kapott, és az orosz apokrifok is. A Strong-szótár mostantól oroszul is olvasható, minden héber és görög szócikkel. A könyvborítók váltakoznak: a legolvasottabb könyvek naponta más metszetet mutatnak. Most 36 fordítás 30 nyelven.
</hu-HU>

<hy-AM>
Պարսկերեն Աստվածաշունչն ամբողջական է՝ Ուիլյամ Գլենի 1856 թ. Հին Կտակարանը միանում է Հենրի Մարտինի Նոր Կտակարանին՝ էջ առ էջ ընդօրինակված բնօրինակ տպագրությունից։ Եկեղեցասլավոներեն Աստվածաշունչն այժմ ամբողջությամբ ընթերցվում է, ինչպես նաև ռուսերեն պարականոն գրքերը։ Սթրոնգի բառարանն այժմ կարդացվում է նաև ռուսերեն։ Գրքերի շապիկներն այժմ հերթափոխվում են ամեն օր։ Այժմ 36 թարգմանություն 30 լեզվով։
</hy-AM>

<it-IT>
La Bibbia in persiano è completa: l'Antico Testamento di William Glen (1856) si unisce al Nuovo Testamento di Henry Martyn, trascritto pagina per pagina dalla stampa originale. La Bibbia in slavo ecclesiastico è ora narrata per intero, e anche gli apocrifi russi. Il dizionario di Strong si legge ora anche in russo, con tutte le voci ebraiche e greche. Le copertine ruotano: i libri più letti mostrano ogni giorno un'incisione diversa. Ora 36 traduzioni in 30 lingue.
</it-IT>

<iw-IL>
התנ"ך והברית החדשה בפרסית הושלמו: הברית הישנה של ויליאם גלן (1856) מצטרפת לברית החדשה של הנרי מרטין — מועתקת עמוד אחר עמוד מן הדפוס המקורי. לתנ"ך בסלאבית כנסייתית יש כעת הקראה קולית מלאה, וכן לספרים החיצוניים הרוסיים. מילון סטרונג נקרא כעת גם ברוסית, כל הערכים בעברית וביוונית. עטיפות הספרים מתחלפות: הספרים הנקראים ביותר מציגים תחריט אחר בכל יום. כעת 36 תרגומים ב-30 שפות.
</iw-IL>

<ja-JP>
ペルシア語聖書が完成しました。ウィリアム・グレンの1856年旧約が、ヘンリー・マーティンの新約に加わります。原本から一頁ずつ本アプリのために書き起こしたものです。教会スラヴ語聖書に全章の音声朗読が加わり、ロシア語外典も朗読されます。ストロング辞典がロシア語でも読めるようになり、ヘブライ語・ギリシア語の全項目を収録。書物の表紙が日替わりになり、さらに五つの書物に初めて挿絵が付きました。現在36訳・30言語。
</ja-JP>

<lv>
Persiešu Bībele ir pilnīga: Viljama Glena 1856. gada Vecā Derība pievienojas Henrija Mārtina Jaunajai Derībai — pārrakstīta lapu pa lapai no oriģinālizdevuma. Baznīcslāvu Bībele tagad ir pilnībā ieskaņota, tāpat krievu apokrifi. Stronga vārdnīca tagad lasāma arī krieviski, visi ebreju un grieķu šķirkļi. Grāmatu vāki tagad mainās: visvairāk lasītās grāmatas katru dienu rāda citu gravīru. Tagad 36 tulkojumi 30 valodās.
</lv>

<nl-NL>
De Perzische Bijbel is compleet: het Oude Testament van William Glen (1856) voegt zich bij het Nieuwe Testament van Henry Martyn — pagina voor pagina overgeschreven uit de oorspronkelijke druk. De kerkslavische Bijbel is nu volledig ingesproken, en de Russische apocriefen ook. Strongs woordenboek is nu ook in het Russisch te lezen. De omslagen wisselen nu: de meestgelezen boeken tonen elke dag een andere gravure. Nu 36 vertalingen in 30 talen.
</nl-NL>

<pl-PL>
Biblia perska jest kompletna: Stary Testament Williama Glena z 1856 roku dołącza do Nowego Testamentu Henry'ego Martyna — przepisany strona po stronie z pierwodruku. Biblia cerkiewnosłowiańska ma teraz pełne nagranie audio, podobnie jak apokryfy rosyjskie. Słownik Stronga czyta się teraz po rosyjsku, wszystkie hasła hebrajskie i greckie. Okładki ksiąg się zmieniają: najczęściej czytane księgi pokazują co dzień inny sztych. Teraz 36 przekładów w 30 językach.
</pl-PL>

<pt-BR>
A Bíblia em persa está completa: o Antigo Testamento de William Glen (1856) junta-se ao Novo Testamento de Henry Martyn, transcrito página a página da impressão original. A Bíblia em eslavo eclesiástico agora está narrada por completo, e os apócrifos russos também. O dicionário de Strong agora se lê em russo, com todos os verbetes hebraicos e gregos. As capas alternam: os livros mais lidos mostram uma gravura diferente a cada dia. Agora 36 traduções em 30 idiomas.
</pt-BR>

<pt-PT>
A Bíblia em persa está completa: o Antigo Testamento de William Glen (1856) junta-se ao Novo Testamento de Henry Martyn, transcrito página a página da impressão original. A Bíblia em eslavo eclesiástico está agora narrada por completo, e os apócrifos russos também. O dicionário de Strong lê-se agora em russo, com todos os verbetes hebraicos e gregos. As capas alternam: os livros mais lidos mostram uma gravura diferente cada dia. Agora 36 traduções em 30 idiomas.
</pt-PT>

<ru-RU>
Персидская Библия стала полной: Ветхий Завет Уильяма Глена 1856 года присоединился к Новому Завету Генри Мартина — переписанный страница за страницей с оригинального издания. Церковнославянская Библия полностью озвучена, как и русские апокрифы. Словарь Стронга теперь читается по-русски: все еврейские и греческие статьи. Обложки книг теперь чередуются: самые читаемые книги каждый день показывают другую гравюру. Теперь 36 переводов на 30 языках.
</ru-RU>

<sr>
Персијска Библија је потпуна: Стари завет Вилијама Глена из 1856. придружује се Новом завету Хенрија Мартина — преписан страну по страну са изворног издања. Црквенословенска Библија сада има потпуно аудио читање, као и руски апокрифи. Стронгов речник сада се чита и на руском, све јеврејске и грчке одреднице. Корице књига се сада смењују: најчитаније књиге сваког дана приказују други бакрорез. Сада 36 превода на 30 језика.
</sr>

<sv-SE>
Den persiska bibeln är fullständig: William Glens Gamla testamente från 1856 sluter sig till Henry Martyns Nya testamente — avskrivet sida för sida ur originaltrycket. Den kyrkslaviska bibeln är nu fullständigt inläst, liksom de ryska apokryferna. Strongs lexikon går nu att läsa på ryska, alla hebreiska och grekiska uppslagsord. Bokomslagen växlar nu: de mest lästa böckerna visar ett nytt kopparstick varje dag. Nu 36 översättningar på 30 språk.
</sv-SE>

<ta-IN>
பாரசீக பைபிள் முழுமை அடைந்தது: வில்லியம் கிளென்னின் 1856 பழைய ஏற்பாடு, ஹென்றி மார்ட்டினின் புதிய ஏற்பாட்டுடன் இணைந்தது. திருச்சபை ஸ்லாவோனிக் பைபிளுக்கும் ரஷ்ய அபோக்ரிபா நூல்களுக்கும் இப்போது முழு ஒலி வாசிப்பு. ஸ்ட்ராங் அகராதி இப்போது ரஷ்ய மொழியிலும். புத்தக அட்டைகள் இப்போது மாறும்: அதிகம் வாசிக்கப்படும் புத்தகங்கள் நாள்தோறும் வேறு படத்தைக் காட்டும். இப்போது 36 மொழிபெயர்ப்புகள், 30 மொழிகளில்.
</ta-IN>

<zh-CN>
波斯语圣经已完整：威廉·格伦1856年的旧约与亨利·马丁的新约合璧，逐页照原版刻本为本应用抄录。教会斯拉夫语圣经现已有全部章节的语音朗读，俄文次经也已录制。斯特朗词典现可用俄文阅读，希伯来语与希腊语词条一应俱全。书卷封面开始轮换：最常阅读的书卷每天显示不同的版画，另有五卷书首次拥有插图。现有36部译本、30种语言。
</zh-CN>

<zh-HK>
波斯文聖經已完整：威廉·格倫1856年的舊約與亨利·馬丁的新約合璧，逐頁依原版刻本為本應用抄錄。教會斯拉夫語聖經現已有全部章節的語音朗讀，俄文次經也已錄製。斯特朗詞典現可用俄文閱讀，希伯來文與希臘文詞條一應俱全。書卷封面開始輪換：最常閱讀的書卷每天顯示不同的版畫，另有五卷書首次擁有插圖。現有36部譯本、30種語言。
</zh-HK>

<zh-TW>
波斯文聖經已完整：威廉·格倫1856年的舊約與亨利·馬丁的新約合璧，逐頁依原版刻本為本應用抄錄。教會斯拉夫語聖經現已有全部章節的語音朗讀，俄文次經也已錄製。斯特朗詞典現可用俄文閱讀，希伯來文與希臘文詞條一應俱全。書卷封面開始輪換：最常閱讀的書卷每天顯示不同的版畫，另有五卷書首次擁有插圖。現有36部譯本、30種語言。
</zh-TW>

## Store descriptions (per language — English first, then alphabetical)

*One block per listing language. Short line first, then the full 📖 description. Copy the block for the locale you're editing.*

### English (en-US)

**Title:** Hexapla — Parallel Bible

**Short description:**
Offline Bible: 35 classic translations, audio, Strong's, reading plans.

**Full description:**

Hexapla is the complete Bible — offline, ad-free, account-free, and it collects no data. Everything is free and nothing is locked.

📖 35 classic translations across 30 languages: KJV 1611 with Apocrypha, Webster 1833, Geneva 1599, Wycliffe, Tyndale, Bible Martin 1744 (French), Luther 1545 (German), Karl XII 1703/1873 (Swedish), Danish 1819/1871, Reina-Valera 1909 (Spanish), Diodati 1649 (Italian), Bíblia Livre — Almeida TR (Portuguese), 明治元訳 Meiji Motoyaku — the first Japanese Bible 1880/87, the Chinese Union Version 和合本 1919 (Traditional and Simplified), Russian Synodal, Church Slavonic, the Hebrew Tanakh (Leningrad Codex), the Greek New Testament (Byzantine Text), the Sanskrit New Testament of 1851, the Tamil Bible (IRV 2019, the 1871 Bower lineage), the Clementine Vulgate of 1592 (Latin), the Dutch Statenvertaling (1637), the Arabic Van Dyck (1865), and the Persian New Testament in Henry Martyn's translation (1876), and more.

✝️ The Good News — God's plan of salvation, step by step, Scripture only.
🔴 Words of Christ in red.
🎧 Audio: recorded narration (LibriVox readings and generated voices) and text-to-speech with verse and word highlighting, background playback, sleep timer, speed control.
📚 Strong's numbers with the full Hebrew/Greek lexicon; Webster's 1828 dictionary — tap any word in the English translations.
🔀 Read two translations side by side, verse-locked, or compare a verse across all translations.
📜 Original-language interlinear: tap a word in the Greek or Hebrew text for its Strong's number and full grammatical parsing.
📅 Reading plans — Bible in a year, chronological year plan (the whole Bible in event order), NT in 90 days, Gospels in 30, Proverbs, Psalms — with progress and streaks.
🔍 Diacritic-insensitive search across all translations.
✏️ Bookmarks, notes, colored highlights, cross-references, backup and restore.
🖼 Verse of the day widget and reminder; classic Doré and Schnorr engravings.

All texts are public domain. The app collects nothing.

---

### English — India (en-IN) · add on Play production day; Tamil/Sanskrit emphasis

**Title:** Hexapla — Parallel Bible

**Short description (≤80):**
Offline Bible: 35 classic translations incl. Tamil, Latin and the Sanskrit NT, audio, Strong's.

**Full description:**

Hexapla is the complete Bible — offline, ad-free, account-free, and it collects no data. Everything is free and nothing is locked.

📖 35 classic translations across 30 languages — including the **complete Tamil Bible** (IRV 2019, the TR-faithful 1871 Bower lineage), the **Sanskrit New Testament of 1851** (सत्यवेदः, Calcutta Baptist Mission, Devanagari), the Hebrew Tanakh (Leningrad Codex), the Greek New Testament (Byzantine Text), the KJV 1611 with Apocrypha, Geneva 1599, Wycliffe, Tyndale, Luther 1545, and more.
✝️ The Good News — God's plan of salvation, step by step, Scripture only.
🔴 Words of Christ in red.
🎧 Audio: recorded narration (LibriVox readings and generated voices) and text-to-speech with verse highlighting, background playback, sleep timer.
📚 Strong's numbers with the full Hebrew/Greek lexicon; original-language interlinear — tap any Greek or Hebrew word for its parsing.
🔀 Read two translations side by side, verse-locked, or compare a verse across all translations.
📅 Reading plans with progress. 🔍 Search across all translations. ✏️ Bookmarks, notes, highlights, backup.

All texts are public domain. The app collects nothing.

### العربية — Arabic (ar)

**العنوان:** Hexapla — كتاب مقدس موازي

**الوصف القصير (≤80):**
الكتاب المقدس دون إنترنت: 35 ترجمة، صوت، خطط قراءة، أرقام سترونغ.

**الوصف الكامل:**

هكسابلا هو الكتاب المقدس الكامل — دون إنترنت، دون إعلانات، دون حساب، ودون جمع أي بيانات. كل شيء مجاني ولا شيء مقفل.

📖 35 ترجمة كلاسيكية في 30 لغة: ترجمة فان دايك 1865 (العربية)، الملك جيمس KJV 1611 مع الأسفار القانونية الثانية، وبستر 1833، جنيف 1599، ديوداتي 1649، رينا-فاليرا 1909، لوثر 1545، مارتن 1744، كارل الثاني عشر 1703/1873، السينودسية الروسية، السلافية الكنسية، المييجي اليابانية، والنسخة الصينية الموحدة (和合本)، إضافة إلى النصين الأصليين العبري واليوناني.
✝️ البشارة — خطة الله للخلاص، خطوة بخطوة، من الكتاب المقدس فقط.
🔴 كلام المسيح باللون الأحمر.
🎧 صوت: تلاوة وتحويل نص إلى كلام مع تمييز الآية، تشغيل في الخلفية، مؤقت نوم.
📚 أرقام سترونغ مع المعجم العبري واليوناني الكامل.
📜 ترجمة بين السطور للنص الأصلي: اضغط على أي كلمة في النص اليوناني أو العبري لرؤية رقم سترونغ والتحليل النحوي الكامل.
🔀 اقرأ ترجمتين جنبًا إلى جنب، آية بآية، أو قارن آية واحدة عبر كل الترجمات.
📅 خطط قراءة: الكتاب المقدس في سنة، خطة زمنية، العهد الجديد في 90 يومًا وأكثر — مع تتبع التقدم.
🔍 بحث لا يتأثر بالتشكيل عبر جميع الترجمات.
✏️ إشارات مرجعية، ملاحظات، تظليل، مراجع متقاطعة، نسخ احتياطي.
🖼 آية اليوم على الودجت؛ لوحات كلاسيكية لدوريه وشنور.

جميع النصوص ملك عام. التطبيق لا يجمع أي بيانات.

### Հայերեն — Armenian (hy-AM) · best-effort, native review pending

**Վերնագիր:** Hexapla — Զուգահեռ Սուրբ Գիրք

**Համառոտ նկարագրութիւն (≤80):**
Աստուածաշունչ առանց ինտերնետի. 35 թարգմանութիւն, ձայն, ընթերցման ծրագրեր, Strong

**Ամբողջական նկարագրութիւն:**

Hexapla-ն ամբողջական Աստուածաշունչն է՝ առանց ինտերնետի, առանց գովազդի, առանց հաշուի եւ առանց տուեալների հաւաքման։ Ամէն ինչ անվճար է, ոչինչ փակուած չէ։

📖 35 դասական թարգմանութիւն 30 լեզուներով՝ Զոհրապեան Հին Կտակարանը (1805) եւ Արեւմտահայերէն Նոր Կտակարանը (1853), KJV 1611-ը՝ ապոկրիֆներով, Webster 1833, Ժնեւի Աստուածաշունչը 1599, Diodati 1649, Reina-Valera 1909, Լիւթերի Աստուածաշունչը 1545, Martin 1744, Կարլոս XII-ի Աստուածաշունչը 1703/1873, ռուսական սինոդալ թարգմանութիւնը, եկեղեցասլավոներէնը, ճապոներէն Մեիջին, չինական Union տարբերակը (和合本), ինչպէս նաեւ եբրայերէն եւ հունարէն բնագրերը։
✝️ Բարի լուրը — Աստուծոյ փրկութեան ծրագիրը քայլ առ քայլ, միայն Սուրբ Գրքից։
🔴 Քրիստոսի խօսքերը՝ կարմիրով։
🎧 Ձայն՝ կենդանի ընթերցում եւ տեքստից խօսք փոխակերպում՝ համարի ընդգծմամբ, ֆոնային նուագարկում, քնի ժամաչափ։
📚 Strong-ի համարներ՝ ամբողջական եբրայերէն-հունարէն բառարանով։
📜 Բնագրի միջտողային վերլուծութիւն. հպեք հունարէն կամ եբրայերէն տեքստի ցանկացած բառին՝ տեսնելու Strong-ի համարը եւ ամբողջական քերականական վերլուծութիւնը։
🔀 Կարդացեք երկու թարգմանութիւն կողք կողքի՝ համար առ համար, կամ համեմատեք մէկ համարը բոլոր թարգմանութիւններում։
📅 Ընթերցման ծրագրեր՝ Աստուածաշունչը մէկ տարում, ժամանակագրական ծրագիր, Նոր Կտակարանը 90 օրում եւ ուրիշներ՝ առաջընթացի հետեւմամբ։
🔍 Փնտրում՝ անկախ շեշտադրումից, բոլոր թարգմանութիւններում։
✏️ Էջանիշեր, նշումներ, գունանշումներ, հղումներ, պահուստաւորում։
🖼 Օրուայ համարը վիջեթի վրայ. Doré-ի եւ Schnorr-ի դասական փորագրանկարներ։

Բոլոր տեքստերը հանրային սեփականութիւն են։ Հաւելուածը որեւէ տուեալ չի հաւաքում։

*Note: as of 1.6.3 Armenian covers the WHOLE Bible across two texts — the classical Zohrab Old Testament (1805, `zoh`) and the Western Armenian New Testament (1853, `arm`). Each is named for the testament it holds rather than implied to be a full Bible, matching how the app discloses grc (Greek NT) and the Sanskrit NT. ⚠ The Zohrab is deliberately OT-ONLY: its New Testament authentically lacks the Comma Johanneum (a 5th-century version, not a critical-text edit), and scoping to the OT was the owner's resolution of that doctrinal-boundary call — do not "complete" it without re-opening that decision.*

### Беларуская — Belarusian (be) · тарашкевіца, native review pending

**Назва:** Hexapla — Паралельная Біблія

**Кароткі апіс (≤80):**
Біблія без інтэрнэту: 35 клясычных перакладаў, аўдыё, плян чытаньня, Strong.

**Поўны апіс:**

Hexapla — гэта поўная Біблія — без інтэрнэту, без рэклямы, без рэгістрацыі і без збору даных. Усё бясплатна, нічога не заблакавана.

📖 35 клясычных перакладаў у 30 мовах: Новы Запавет і Псальмы ў перакладзе Дзекуць-Малея і Луцкевіча (1931), KJV 1611 з апокрыфамі, Webster 1833, Жэнеўская Біблія 1599, Diodati 1649, Reina-Valera 1909, Лютэраўская Біблія 1545, Martin 1744, Біблія Карла XII 1703/1873, расійскі сінадальны пераклад, царкоўнаславянская мова, японская Мэйдзі, кітайская версія Union (和合本), а таксама габрэйскі і грэцкі арыгінальныя тэксты.
✝️ Добрая Навіна — Божы плян збаўленьня крок за крокам, толькі паводле Пісаньня.
🔴 Словы Хрыста чырвоным колерам.
🎧 Аўдыё: жывое чытаньне і сынтэз мовы з падсьвятленьнем радка, прайграваньне ў фоне, таймэр сну.
📚 Нумары Стронга з поўным габрэйска-грэцкім слоўнікам.
📜 Міжрадковы пераклад арыгіналу: дакраніцеся да слова ў грэцкім ці габрэйскім тэксьце, каб убачыць нумар Стронга і поўны граматычны разбор.
🔀 Чытайце два пераклады побач, радок за радком, або параўноўвайце адзін радок ва ўсіх перакладах.
📅 Плян чытаньня: Біблія за год, храналягічны плян, НЗ за 90 дзён і іншыя — з адсочваньнем посьпеху.
🔍 Пошук незалежна ад дыякрытыкі, ва ўсіх перакладах.
✏️ Закладкі, нататкі, вылучэньні колерам, спасылкі, рэзэрвовае капіяваньне.
🖼 Радок дня на віджэце; клясычныя гравюры Дарэ і Шнора.

Усе тэксты — грамадзкая ўласнасьць. Дадатак не зьбірае ніякіх даных.

*Note: be_dzekuc is a New Testament + Psalms translation (1931) — named explicitly above ("Новы Запавет і Псальмы", "New Testament and Psalms") rather than implied to be a full Bible, matching how the app already discloses grc (Greek NT), the Sanskrit NT, and hy_west1853 (Armenian NT) elsewhere in this file. The app as a whole still offers the complete Bible via its other translations, read in parallel; confirmed directly against the asset — `be_dzekuc.json` has real chapter data only for the New Testament books (Matthew idx39 through Revelation idx65) and Psalms (idx18), every other OT book empty.*

*⚠ ORTHOGRAPHY CAVEAT (unresolved, needs a native-speaker pass): the shipped verse text reads as classical Belarusian orthography ("тарашкевіца" — the pre-1933-reform standard still used by diaspora/independent Belarusian publications), not the modern official "narkamaŭka" standard most contemporary software localization defaults to. Spot-checked directly in `be_dzekuc.json`: John 1:14 "пасялілася", 1 Timothy 3:16 "багабойнасьці", "зьявіўся", "сьвеце" (soft-sign assimilation — тарашкевіца spells these with ь; narkamaŭka drops it, e.g. "багабойнасці", "з'явіўся", "свеце"). This listing text above was written to match that classical register as a good-faith, non-native-speaker effort — it has NOT been reviewed by a native Belarusian speaker, the same open item already flagged for the Armenian listing text elsewhere in this file. Do not treat it as final; get a native-speaker orthography check before shipping it with confidence.*


---

### 繁體中文（香港） — Chinese, Hong Kong (zh-HK)

**標題:** Hexapla — 對照聖經

**簡短說明 (≤80):**
離線聖經：35部經典譯本，語音朗讀，讀經計劃，史特朗編號，原文對照。

**完整說明:**

Hexapla（六欄經）— 完整聖經，無需連網，無廣告，無需註冊，不收集任何資料。完全免費，沒有任何限制。

📖 30種語言、35部經典譯本：和合本1919（繁體與簡體）、英文欽定本 KJV 1611（含次經）、韋伯斯特1833、日內瓦1599、義大利迪奧達蒂1649、西班牙雷納-瓦萊拉1909、德文路德1545、日文明治元譯，以及希伯來文與希臘文原文。
✝️ 福音：神的救恩計劃，逐步呈現，唯獨聖經經文。
🔴 基督的話語以紅字顯示。
🎧 語音：真人朗讀與語音合成，逐節高亮，背景播放，定時關閉。
📚 史特朗原文編號，附完整希伯來/希臘文詞典。
📜 原文對照：點按希臘文或希伯來文經文中的任何詞語，即可查看史特朗編號與文法分析。
🔀 雙譯本對照閱讀，或在所有譯本中比較同一節經文。
📅 讀經計劃：一年讀經、按年代順序、90天新約等，附進度記錄。
🔍 跨所有譯本的搜尋。
✏️ 書籤、筆記、螢光標記、串珠、備份。
🖼 桌面小工具顯示每日經文；多雷與施諾爾的經典版畫。

所有經文均屬公有領域。本應用程式不收集任何資料。

### 简体中文 — Chinese, Simplified (zh-CN)

**标题:** Hexapla — 对照圣经

**简短说明 (≤80):**
离线圣经：35部经典译本，语音朗读，读经计划，斯特朗编号，原文对照。

**完整说明:**

Hexapla（六栏经）— 完整圣经，无需联网，无广告，无需注册，不收集任何数据。完全免费，没有任何限制。

📖 30种语言、35部经典译本：和合本1919（简体与繁体）、英文钦定本 KJV 1611（含次经）、韦伯斯特1833、日内瓦1599、意大利迪奥达蒂1649、西班牙雷纳-瓦莱拉1909、德文路德1545、日文明治元译，以及希伯来文与希腊文原文。
✝️ 福音：神的救恩计划，逐步呈现，唯独圣经经文。
🔴 基督的话语以红字显示。
🎧 语音：真人朗读与语音合成，逐节高亮，后台播放，定时关闭。
📚 斯特朗原文编号，附完整希伯来/希腊文词典。
📜 原文对照：点按希腊文或希伯来文经文中的任何词语，即可查看斯特朗编号与语法分析。
🔀 双译本对照阅读，或在所有译本中比较同一节经文。
📅 读经计划：一年读经、按年代顺序、90天新约等，带进度记录。
🔍 跨所有译本的搜索。
✏️ 书签、笔记、荧光标记、串珠、备份。
🖼 桌面小组件显示每日经文；多雷与施诺尔的经典版画。

所有经文均属公有领域。本应用不收集任何数据。

### 繁體中文 — Chinese, Traditional (zh-TW)

**標題:** Hexapla — 對照聖經

**簡短說明 (≤80):**
離線聖經：35部經典譯本，語音朗讀，讀經計畫，史特朗編號，原文對照。

**完整說明:**

Hexapla（六欄經）— 完整聖經，無需連網，無廣告，無需註冊，不收集任何資料。完全免費，沒有任何限制。

📖 30種語言、35部經典譯本：和合本1919（繁體與簡體）、英文欽定本 KJV 1611（含次經）、韋伯斯特1833、日內瓦1599、義大利迪奧達蒂1649、西班牙雷納-瓦萊拉1909、德文路德1545、日文明治元譯，以及希伯來文與希臘文原文。
✝️ 福音：神的救恩計畫，逐步呈現，唯獨聖經經文。
🔴 基督的話語以紅字顯示。
🎧 語音：真人朗讀與語音合成，逐節高亮，背景播放，定時關閉。
📚 史特朗原文編號，附完整希伯來/希臘文詞典。
📜 原文對照：點按希臘文或希伯來文經文中的任何詞語，即可查看史特朗編號與文法分析。
🔀 雙譯本對照閱讀，或在所有譯本中比較同一節經文。
📅 讀經計畫：一年讀經、按年代順序、90天新約等，附進度記錄。
🔍 跨所有譯本的搜尋。
✏️ 書籤、筆記、螢光標記、串珠、備份。
🖼 桌面小工具顯示每日經文；多雷與施諾爾的經典版畫。

所有經文均屬公有領域。本應用程式不收集任何資料。

### Čeština — Czech (cs-CZ)

**Název:** Hexapla — Paralelní Bible

**Krátký popis (≤80):**
Bible offline: 35 klasických překladů, zvuk, plány čtení, Strong.

**Úplný popis:**

Hexapla je kompletní Bible — offline, bez reklam, bez účtu a bez sběru dat. Vše zdarma, nic není uzamčeno.

📖 35 klasických překladů ve 30 jazycích: Bible kralická 1613, KJV 1611 s apokryfy, Webster 1833, Ženevská bible 1599, Diodati 1649, Reina-Valera 1909, Lutherova bible 1545, Martin 1744, Karel XII. 1703/1873, ruský synodální překlad, církevní slovanština, japonský Meidži, čínský Union Version (和合本), a hebrejský i řecký původní text.
✝️ Dobrá zpráva — Boží plán spásy krok za krokem, pouze biblický text.
🔴 Slova Kristova červeně.
🎧 Zvuk: namluvené čtení a syntéza řeči se zvýrazněním verše, přehrávání na pozadí, časovač usínání.
📚 Strongova čísla s úplným hebrejsko-řeckým slovníkem.
📜 Interlineární původní text: klepnutím na slovo v řeckém nebo hebrejském textu zobrazíte Strongovo číslo a úplný gramatický rozbor.
🔀 Čtěte dva překlady vedle sebe, verš po verši, nebo porovnejte verš napříč všemi překlady.
📅 Plány čtení: Bible za rok, chronologický plán, NZ za 90 dní a další — se sledováním postupu.
🔍 Vyhledávání necitlivé na diakritiku napříč všemi překlady.
✏️ Záložky, poznámky, zvýraznění, křížové odkazy, záloha.
🖼 Verš dne na widgetu; klasické rytiny Dorého a Schnorra.

Všechny texty jsou volným dílem. Aplikace neshromažďuje žádná data.

### Dansk — Danish (da-DK)

**Titel:** Hexapla — Parallelbibel

**Kort beskrivelse (≤80):**
Bibelen offline: 35 klassiske oversættelser, lyd, læseplaner, Strong.

**Fuld beskrivelse:**

Hexapla — hele Bibelen uden internet, uden reklamer, uden konto og uden dataindsamling. Alt er gratis, intet er låst.

📖 35 klassiske oversættelser på 30 sprog: Dansk Bibel 1819, KJV 1611 med apokryfer, Webster 1833, Genève 1599, Diodati 1649, Reina-Valera 1909, Luther 1545, Martin 1744, Karl XII 1703/1873, russisk synodal, kirkeslavisk, japansk 明治元訳, kinesisk 和合本 samt de hebraiske og græske grundtekster.
✝️ Det gode budskab: Guds frelsesplan trin for trin, kun Skriften.
🔴 Kristi ord med rødt.
🎧 Lyd: oplæsning og talesyntese med versfremhævning, baggrundsafspilning, sleep-timer.
📚 Strongs numre med komplet hebraisk/græsk leksikon.
📜 Interlineær grundtekst: tryk på et ord i den græske eller hebraiske tekst for Strongs nummer og grammatisk analyse.
🔀 Læs to oversættelser side om side, eller sammenlign et vers i alle.
📅 Læseplaner: Bibelen på 1 år, kronologisk plan, NT på 90 dage m.m. — med fremskridt.
🔍 Søgning uden diakritiske tegn i alle oversættelser.
✏️ Bogmærker, noter, fremhævninger, krydshenvisninger, backup.
🖼 Dagens vers som widget; klassiske stik af Doré og Schnorr.

Alle tekster er offentlig ejendom. Appen indsamler ingen data.

### Nederlands — Dutch (nl-NL)

**Titel:** Hexapla — Parallelle Bijbel

**Korte beschrijving (≤80):**
Bijbel offline: 35 klassieke vertalingen, audio, leesplannen, Strong.

**Volledige beschrijving:**

Hexapla is de complete Bijbel — offline, zonder advertenties, zonder account en zonder gegevensverzameling. Alles gratis, niets vergrendeld.

📖 35 klassieke vertalingen in 30 talen: de Statenvertaling 1637/1888, de KJV 1611 met apocriefen, Webster 1833, Genève 1599, Diodati 1649, Reina-Valera 1909, Luther 1545, Martin 1744, Karel XII 1703/1873, Russisch-Synodale vertaling, Kerkslavisch, Japans Meiji, Chinese Union-versie (和合本), en de Hebreeuwse en Griekse grondteksten.
✝️ Het Goede Nieuws — Gods heilsplan stap voor stap, uitsluitend Schrift.
🔴 Woorden van Christus in rood.
🎧 Audio: voorlezen en tekst-naar-spraak met versmarkering, afspelen op de achtergrond, slaaptimer.
📚 Strongnummers met het volledige Hebreeuws/Grieks lexicon.
📜 Interlineair van de grondtekst: tik op een woord in de Griekse of Hebreeuwse tekst voor het Strongnummer en de volledige grammaticale analyse.
🔀 Lees twee vertalingen naast elkaar, vers voor vers, of vergelijk een vers in alle vertalingen.
📅 Leesplannen: de Bijbel in 1 jaar, chronologisch plan, het NT in 90 dagen en meer — met voortgangsbijhouding.
🔍 Zoeken ongevoelig voor diakritische tekens, in alle vertalingen.
✏️ Bladwijzers, notities, markeringen, kruisverwijzingen, back-up.
🖼 Vers van de dag op de widget; klassieke gravures van Doré en Schnorr.

Alle teksten zijn publiek domein. De app verzamelt geen gegevens.

### Suomi — Finnish (fi-FI)

**Nimi:** Hexapla — Rinnakkaisraamattu

**Lyhyt kuvaus (≤80):**
Raamattu offline: 35 klassista käännöstä, ääni, lukusuunnitelmat, Strong.

**Täydellinen kuvaus:**

Hexapla on koko Raamattu — ilman internetiä, ilman mainoksia, ilman tiliä ja ilman tiedonkeruuta. Kaikki on ilmaista, mikään ei ole lukittu.

📖 35 klassista käännöstä 30 kielellä: Vanha kirkkoraamattu 1776, KJV 1611 apokryfikirjoineen, Webster 1833, Geneven raamattu 1599, Diodati 1649, Reina-Valera 1909, Lutherin raamattu 1545, Martin 1744, Kaarle XII:n raamattu 1703/1873, venäläinen synodaalikäännös, kirkkoslaavi, japanilainen Meiji, kiinalainen Union-versio (和合本) sekä heprean- ja kreikankieliset alkutekstit.
✝️ Hyvä sanoma — Jumalan pelastussuunnitelma askel askeleelta, pelkkää Raamattua.
🔴 Kristuksen sanat punaisella.
🎧 Ääni: ihmisääninen luenta ja tekstistä puheeksi -toiminto jakeen korostuksella, taustatoisto, uniajastin.
📚 Strongin numerot täydellisen heprean/kreikan sanakirjan kanssa.
📜 Alkukielen interlineaari: kosketa sanaa kreikan- tai hepreankielisessä tekstissä nähdäksesi Strongin numeron ja täyden kieliopillisen analyysin.
🔀 Lue kaksi käännöstä rinnakkain, jae jakeelta, tai vertaa jaetta kaikissa käännöksissä.
📅 Lukusuunnitelmat: Raamattu vuodessa, kronologinen suunnitelma, UT 90 päivässä ja muita — edistymisen seurannalla.
🔍 Diakriittisistä merkeistä riippumaton haku kaikista käännöksistä.
✏️ Kirjanmerkit, muistiinpanot, korostukset, ristiviittaukset, varmuuskopiointi.
🖼 Päivän jae widgetissä; Dorén ja Schnorrin klassiset kaiverrukset.

Kaikki tekstit ovat vapaasti käytettävissä (public domain). Sovellus ei kerää mitään tietoja.

### Français — French (fr-FR, fr-CA)

**Titre :** Hexapla — Bible parallèle

**Description courte :**
Bible hors ligne : 35 traductions classiques, audio, plans de lecture.

**Description complète :**

Hexapla, c'est la Bible complète — hors ligne, sans publicité, sans compte, sans collecte de données. Tout est gratuit, rien n'est verrouillé.

📖 35 traductions classiques en 30 langues, dont la Bible Martin 1744, la KJV 1611, l'hébreu et le grec originaux. ✝️ La Bonne Nouvelle : le plan du salut, étape par étape, uniquement l'Écriture. 🔴 Paroles du Christ en rouge. 🎧 Lecture audio avec surlignage des versets. 📚 Numéros Strong avec lexique ; interlinéaire grec/hébreu (analyse grammaticale au toucher) ; dictionnaire Webster 1828 pour les traductions anglaises. 📅 Plans de lecture avec progression. ✏️ Signets, notes, surlignages, sauvegarde.

Tous les textes sont dans le domaine public. L'application ne collecte rien.

---

### ქართული — Georgian (ka-GE) · NEW in 1.6.3 · verify the locale code at upload; native review pending · lead with screenshot_reader_ka.png + feature_1024x500_ka.png

**სათაური:** Hexapla — პარალელური ბიბლია

**მოკლე აღწერა (≤80):**
ბიბლია ინტერნეტის გარეშე: 35 თარგმანი, აუდიო, საკითხავი გეგმები, სტრონგი.

**სრული აღწერა:**

Hexapla არის სრული ბიბლია — ინტერნეტის გარეშე, რეკლამის გარეშე, ანგარიშის გარეშე და მონაცემთა შეგროვების გარეშე. ყველაფერი უფასოა, არაფერია დაკეტილი.

📖 35 კლასიკური თარგმანი 30 ენაზე: ბაქარის ბიბლია 1743 (ქართული), KJV 1611 აპოკრიფებით, Webster 1833, ჟენევის ბიბლია 1599, Diodati 1649, Reina-Valera 1909, ლუთერის ბიბლია 1545, Martin 1744, კარლ XII-ის ბიბლია 1703/1873, რუსული სინოდალური თარგმანი, საეკლესიო სლავური, სომხური (ზოჰრაბის ძველი აღთქმა 1805 და ახალი აღთქმა 1853), იაპონური მეიჯი, ჩინური Union (和合本), აგრეთვე ებრაული და ბერძნული დედნები.
✝️ სასიხარულო ცნობა — ღვთის ცხონების გეგმა ნაბიჯ-ნაბიჯ, მხოლოდ წმინდა წერილიდან.
🔴 ქრისტეს სიტყვები წითლად.
🎧 აუდიო: ჩაწერილი კითხვა და ტექსტის ხმად გარდაქმნა მუხლის მონიშვნით, ფონური მუსიკა, ძილის ტაიმერი.
📚 სტრონგის ნომრები სრული ებრაულ-ბერძნული ლექსიკონით.
📜 დედნის სტრიქონთაშორისი გარჩევა: შეეხეთ ბერძნულ ან ებრაულ ტექსტში ნებისმიერ სიტყვას, რომ ნახოთ სტრონგის ნომერი და სრული გრამატიკული გარჩევა.
🔀 წაიკითხეთ ორი თარგმანი გვერდიგვერდ, მუხლი მუხლის გასწვრივ, ან შეადარეთ ერთი მუხლი ყველა თარგმანში.
📅 საკითხავი გეგმები: ბიბლია ერთ წელიწადში, ქრონოლოგიური გეგმა, ახალი აღთქმა 90 დღეში და სხვა — პროგრესის თვალყურის დევნებით.
🔍 ძებნა ყველა თარგმანში.
✏️ სანიშნეები, ჩანაწერები, მონიშვნები, ჯვარედინი მითითებები, სარეზერვო ასლი.
🖼 დღის მუხლი ვიჯეტზე: დორესა და შნორის კლასიკური გრავიურები.

ყველა ტექსტი საზოგადოებრივ საკუთრებაშია. აპლიკაცია არ აგროვებს არანაირ მონაცემს.

*Notes: (1) The Bakar edition (ბაქარის ბიბლია, Moscow 1743) is a COMPLETE Bible — Old and New Testament, plus the deuterocanonical books in the apocrypha slots — so unlike the Armenian and Sanskrit entries it needs no New-Testament-only caveat. (2) Terminology follows the values-ka UI locale, which fixed its glossary against Georgian Orthodox usage first: მუხლი for verse (not ლექსი, a line of poetry), სიმფონია for concordance. (3) Georgian is NOT yet in Play's What's-new locale list — the release-notes block above stays at Play's 31 locales until the language is added to the account; add `ka` to PLAY_ORDER in tools/check_release_notes.py on the same day, and paste the standby Georgian note below.*

**1.6.3 release note — Georgian, standby (paste only once ka is added as a listing language):**
> ქართული ბიბლია პირველად: ბაქარის გამოცემა 1743 — სრული ძველი და ახალი აღთქმა, დეუტეროკანონიკური წიგნებითურთ. აპლიკაციის ინტერფეისიც ქართულადაა. დაემატა სომხური ძველი აღთქმა (ზოჰრაბი) — სომხური ბიბლია ახლა სრულია. ახალია მუსიკა განწყობის მიხედვით და ღილაკი, რომელიც ორ თარგმანს ადგილებს უცვლის გაყოფილ ხედში. სულ 35 თარგმანი 30 ენაზე.

### Deutsch — German (de-DE)

**Titel:** Hexapla — Parallelbibel

**Kurzbeschreibung:**
Bibel offline: 35 klassische Übersetzungen, Audio, Lesepläne, Strong.

**Vollständige Beschreibung:**

Hexapla ist die vollständige Bibel — offline, werbefrei, ohne Konto, ohne Datensammlung. Alles kostenlos, nichts gesperrt.

📖 35 klassische Übersetzungen in 30 Sprachen, darunter die Lutherbibel 1545, die KJV 1611 sowie Hebräisch und Griechisch im Original. ✝️ Die Gute Nachricht: Gottes Heilsplan Schritt für Schritt, nur Schrift. 🔴 Worte Christi in Rot. 🎧 Audiowiedergabe mit Vershervorhebung. 📚 Strong-Nummern mit Lexikon; Interlinear für Griechisch/Hebräisch (grammatische Analyse per Tipp); Websters Wörterbuch 1828 für die englischen Übersetzungen. 📅 Lesepläne mit Fortschritt. ✏️ Lesezeichen, Notizen, Markierungen, Sicherung.

Alle Texte sind gemeinfrei. Die App sammelt keine Daten.

---

### Ελληνικά — Greek (el-GR)

**Τίτλος:** Hexapla — Παράλληλη Βίβλος

**Σύντομη περιγραφή (≤80):**
Βίβλος offline: 35 κλασικές μεταφράσεις, ήχος, προγράμματα ανάγνωσης, Strong.

**Πλήρης περιγραφή:**

Το Hexapla είναι η πλήρης Βίβλος — χωρίς σύνδεση στο διαδίκτυο, χωρίς διαφημίσεις, χωρίς λογαριασμό και χωρίς συλλογή δεδομένων. Όλα δωρεάν, τίποτα κλειδωμένο.

📖 35 κλασικές μεταφράσεις σε 30 γλώσσες: η μετάφραση Βάμβα 1850, η KJV 1611 με τα Απόκρυφα, η Webster 1833, η Γενεύη 1599, η Diodati 1649, η Reina-Valera 1909, η Βίβλος του Λούθηρου 1545, η Martin 1744, ο Κάρολος ΙΒ' 1703/1873, η Ρωσική Συνοδική, η Εκκλησιαστική Σλαβονική, η ιαπωνική Meiji, η κινεζική Union Version (和合本), καθώς και τα πρωτότυπα εβραϊκά και ελληνικά κείμενα.
✝️ Τα Καλά Νέα — το σχέδιο σωτηρίας του Θεού, βήμα προς βήμα, μόνο από τη Γραφή.
🔴 Τα λόγια του Χριστού με κόκκινο.
🎧 Ήχος: αφήγηση και σύνθεση ομιλίας με επισήμανση εδαφίου, αναπαραγωγή στο παρασκήνιο, χρονοδιακόπτης ύπνου.
📚 Αριθμοί Strong με πλήρες εβραϊκό/ελληνικό λεξικό.
📜 Διάστιχη μετάφραση πρωτότυπου κειμένου: πατήστε μια λέξη στο ελληνικό ή εβραϊκό κείμενο για τον αριθμό Strong και την πλήρη γραμματική ανάλυση.
🔀 Διαβάστε δύο μεταφράσεις παράλληλα, εδάφιο προς εδάφιο, ή συγκρίνετε ένα εδάφιο σε όλες τις μεταφράσεις.
📅 Προγράμματα ανάγνωσης: η Βίβλος σε 1 χρόνο, χρονολογικό πρόγραμμα, η Κ.Δ. σε 90 ημέρες και άλλα — με παρακολούθηση προόδου.
🔍 Αναζήτηση χωρίς ευαισθησία σε τονισμό σε όλες τις μεταφράσεις.
✏️ Σελιδοδείκτες, σημειώσεις, επισημάνσεις, παραπομπές, αντίγραφο ασφαλείας.
🖼 Εδάφιο της ημέρας στο γουίτζετ· κλασικές χαλκογραφίες των Doré και Schnorr.

Όλα τα κείμενα είναι κοινό κτήμα. Η εφαρμογή δεν συλλέγει κανένα δεδομένο.

### עברית — Hebrew (iw-IL) · verify iw vs he at upload; native review pending

**שם:** Hexapla — כתבי הקודש במקביל

**תיאור קצר (עד 80 תווים):**
כתבי קודש ללא אינטרנט: 35 תרגומים קלאסיים, שמע, תוכניות קריאה, מספרי סטרונג.

**תיאור מלא:**

Hexapla הוא אוסף כתבי הקודש המלא — ללא אינטרנט, ללא פרסומות, ללא צורך בחשבון וללא איסוף נתונים. הכול חינם וכלום אינו נעול.

📖 35 תרגומים קלאסיים ב-30 שפות: הנוסח העברי של התנ"ך לפי כתב היד של לנינגרד (Westminster Leningrad Codex), ה-KJV משנת 1611 עם הספרים החיצוניים, וובסטר 1833, ג'נבה 1599, דיודאטי 1649, ריינה-ולרה 1909, תרגום לותר 1545, מרטין 1744, קרל ה-12 משנת 1703/1873, הנוסח הסינודלי הרוסי, הסלאבית הכנסייתית, מייג'י היפני, התרגום הסיני 和合本, וכן הטקסט היווני של הברית החדשה.
✝️ הבשורה הטובה — תוכנית הישועה של אלוהים, צעד אחר צעד, מתוך הכתובים בלבד.
🔴 דברי ישוע מודגשים באדום (בתרגומים הנוצריים).
🎧 שמע: קריינות אנושית והמרת טקסט לדיבור עם הדגשת הפסוק, נגינה ברקע, טיימר שינה.
📚 מספרי סטרונג עם מילון עברי-יווני מלא.
📜 בין-שיטין בשפת המקור: הקישו על מילה בטקסט העברי או היווני לצפייה במספר סטרונג ובניתוח דקדוקי מלא.
🔀 קראו שני תרגומים זה לצד זה, פסוק מול פסוק, או השוו פסוק בכל התרגומים.
📅 תוכניות קריאה: התנ"ך בשנה, תוכנית כרונולוגית, הברית החדשה ב-90 יום ועוד — עם מעקב התקדמות.
🔍 חיפוש שאינו רגיש לניקוד בכל התרגומים.
✏️ סימניות, הערות, סימון בצבע, הפניות צולבות, גיבוי.
🖼 פסוק היום בווידג'ט; תחריטים קלאסיים של דורה ושנור.

כל הטקסטים הם נחלת הכלל. האפליקציה אינה אוספת שום נתון.

*Note: he_wlc is the Leningrad Codex — Old Testament / Tanakh only, no New Testament. The description above says so honestly by naming it "התנ"ך" (Tanakh), the same convention the shipped RU/EN listings already use for grc (Greek NT, testament named explicitly) and for the Sanskrit NT — never claims a full Bible for the Hebrew text itself, while the app as a whole (via other translations) still offers the complete Bible in parallel.*

### Magyar — Hungarian (hu-HU)

**Cím:** Hexapla — Párhuzamos Biblia

**Rövid leírás (≤80):**
Biblia internet nélkül: 35 klasszikus fordítás, hang, olvasási tervek, Strong.

**Teljes leírás:**

A Hexapla a teljes Biblia — internet nélkül, hirdetések nélkül, regisztráció nélkül és adatgyűjtés nélkül. Minden ingyenes, semmi sincs lezárva.

📖 35 klasszikus fordítás 30 nyelven: Károli Gáspár fordítása 1590/1908, KJV 1611 az apokrifekkel, Webster 1833, Genfi Biblia 1599, Diodati 1649, Reina-Valera 1909, Luther-Biblia 1545, Martin 1744, XII. Károly Bibliája 1703/1873, orosz szinodális fordítás, egyházi szláv, japán Meidzsi, kínai Union-fordítás (和合本), valamint a héber és görög eredeti szövegek.
✝️ A jó hír — Isten üdvtervének lépései, kizárólag Szentírás alapján.
🔴 Krisztus szavai piros betűkkel.
🎧 Hang: felolvasás és szövegfelolvasás versenkénti kiemeléssel, háttérben lejátszás, elalváskapcsoló.
📚 Strong-számok a teljes héber-görög szótárral.
📜 Eredeti nyelvű sorközi fordítás: érintsen meg egy szót a görög vagy héber szövegben a Strong-szám és a teljes nyelvtani elemzés megjelenítéséhez.
🔀 Olvasson két fordítást egymás mellett, versről versre, vagy hasonlítson össze egy verset az összes fordításban.
📅 Olvasási tervek: Biblia egy év alatt, kronologikus terv, Újszövetség 90 nap alatt és más tervek — haladáskövetéssel.
🔍 Ékezetre nem érzékeny keresés az összes fordításban.
✏️ Könyvjelzők, jegyzetek, kiemelések, kereszthivatkozások, biztonsági mentés.
🖼 A nap verse a widgeten; Doré és Schnorr klasszikus metszetei.

Minden szöveg közkincs. Az alkalmazás semmilyen adatot nem gyűjt.

### Italiano — Italian (it-IT)

**Titolo:** Hexapla — Bibbia parallela

**Descrizione breve (≤80):**
Bibbia offline: 35 traduzioni classiche, audio, piani di lettura, Strong.

**Descrizione completa:**

Hexapla — la Bibbia completa senza internet, senza pubblicità, senza registrazione e senza raccolta dati. Tutto gratuito, niente bloccato.

📖 35 traduzioni classiche in 30 lingue: Diodati 1649/1885, KJV 1611 con apocrifi, Webster 1833, Ginevra 1599, Reina-Valera 1909, Almeida TR, Lutero 1545, Martin 1744, Carlo XII 1703/1873, danese 1819, Sinodale russa, slavo ecclesiastico, 明治元訳 giapponese, 和合本 cinese, e gli originali ebraico e greco.
✝️ La Buona Novella: il piano di salvezza di Dio passo dopo passo, solo Scrittura.
🔴 Parole di Cristo in rosso.
🎧 Audio: narrazione e sintesi vocale con evidenziazione dei versetti, riproduzione in sottofondo, timer.
📚 Numeri di Strong con lessico ebraico/greco completo.
📜 Interlineare dell'originale: tocca una parola del testo greco o ebraico per il numero di Strong e l'analisi grammaticale.
🔀 Leggi due traduzioni affiancate o confronta un versetto in tutte.
📅 Piani di lettura: Bibbia in 1 anno, piano cronologico, NT in 90 giorni e altri — con progresso.
🔍 Ricerca senza accenti in tutte le traduzioni.
✏️ Segnalibri, note, evidenziazioni, riferimenti incrociati, backup.
🖼 Versetto del giorno nel widget; incisioni classiche di Doré e Schnorr.

Tutti i testi sono di pubblico dominio. L'app non raccoglie alcun dato.

### 日本語 — Japanese (ja-JP)

**タイトル:** Hexapla — 対照聖書

**簡単な説明 (≤80):**
オフライン聖書：古典訳35種・音声・通読計画・ストロング番号・原語対訳。

**詳細な説明:**

Hexapla（ヘクサプラ）— インターネット不要、広告なし、登録不要、データ収集なしの聖書アプリ。すべて無料、制限はありません。

📖 30言語・35の古典訳：明治元訳（1880/87年、日本初の聖書）、欽定訳 KJV 1611（外典付き）、ウェブスター訳1833、ジュネーブ聖書1599、ディオダティ訳1649、レイナ・バレラ訳1909、ルター訳1545、中国語和合本1919（繁体・簡体）、ロシア語会堂訳ほか、ヘブライ語・ギリシア語原典も収録。
✝️ 福音：神の救いのご計画を聖書の御言葉だけで、順を追って。
🔴 キリストの言葉を赤字で表示。
🎧 音声：朗読と読み上げ（節のハイライト付き）、バックグラウンド再生、スリープタイマー。
📚 ストロング番号とヘブライ語・ギリシア語辞典。
📜 原語対訳：ギリシア語・ヘブライ語本文の単語をタップすると、ストロング番号と文法解析を表示。
🔀 2つの訳を並べて読む、または全訳で節を比較。
📅 通読計画：1年通読・年代順・新約90日など、進捗記録付き。
🔍 全訳を横断する検索。
✏️ しおり・メモ・ハイライト・引照・バックアップ。
🖼 ウィジェットに今日の聖句；ドレとシュノルの古典版画。

すべての本文はパブリックドメインです。アプリはいかなるデータも収集しません。

### Latviešu — Latvian (lv)

**Nosaukums:** Hexapla — Paralēlā Bībele

**Īsais apraksts (≤80):**
Bībele bez interneta: 35 klasiski tulkojumi, audio, lasīšanas plāni, Strong.

**Pilnais apraksts:**

Hexapla ir pilna Bībele — bez interneta, bez reklāmām, bez konta un bez datu vākšanas. Viss ir bez maksas, nekas nav slēgts.

📖 35 klasiski tulkojumi 30 valodās: Glika Bībele 1685/1689, KJV 1611 ar apokrifiem, Webster 1833, Ženēvas Bībele 1599, Diodati 1649, Reina-Valera 1909, Lutera Bībele 1545, Martina Bībele 1744, Kārļa XII Bībele 1703/1873, krievu Sinodālais tulkojums, baznīcslāvu valoda, japāņu Meidzi, ķīniešu Union versija (和合本), kā arī ebreju un grieķu oriģinālteksti.
✝️ Labā vēsts — Dieva pestīšanas plāns soli pa solim, tikai no Rakstiem.
🔴 Kristus vārdi sarkanā krāsā.
🎧 Audio: lasījums balsī un teksta pārvēršana runā ar panta izcelšanu, atskaņošana fonā, aizmigšanas taimeris.
📚 Stronga numuri ar pilnu ebreju/grieķu vārdnīcu.
📜 Oriģinālvalodas starprindu tulkojums: pieskarieties vārdam grieķu vai ebreju tekstā, lai redzētu Stronga numuru un pilnu gramatisko analīzi.
🔀 Lasiet divus tulkojumus blakus, pantu pēc panta, vai salīdziniet vienu pantu visos tulkojumos.
📅 Lasīšanas plāni: Bībele gada laikā, hronoloģisks plāns, Jaunā Derība 90 dienās un citi — ar progresa izsekošanu.
🔍 Meklēšana, kas nav jutīga pret diakritiskajām zīmēm, visos tulkojumos.
✏️ Grāmatzīmes, piezīmes, iekrāsojumi, savstarpējas atsauces, dublējums.
🖼 Dienas pants logrīkā; Dorē un Šnorra klasiskie gravējumi.

Visi teksti ir sabiedrības īpašums. Lietotne nevāc nekādus datus.

### Polski — Polish (pl-PL)

**Nazwa:** Hexapla — Biblia Równoległa

**Krótki opis (≤80):**
Biblia offline: 35 klasycznych przekładów, audio, plany czytania, Strong.

**Pełny opis:**

Hexapla to kompletna Biblia — bez internetu, bez reklam, bez konta i bez zbierania danych. Wszystko za darmo, nic nie jest zablokowane.

📖 35 klasycznych przekładów w 30 językach: Biblia Gdańska 1632, KJV 1611 z apokryfami, Webster 1833, Biblia Genewska 1599, Diodati 1649, Reina-Valera 1909, Biblia Lutra 1545, Martin 1744, Biblia Karola XII 1703/1873, rosyjski przekład synodalny, cerkiewnosłowiański, japoński Meiji, chińska Union Version (和合本), a także oryginalne teksty hebrajski i grecki.
✝️ Dobra Nowina — Boży plan zbawienia krok po kroku, wyłącznie na podstawie Pisma.
🔴 Słowa Chrystusa zaznaczone na czerwono.
🎧 Audio: lektor i synteza mowy z podświetlaniem wersetu, odtwarzanie w tle, minutnik snu.
📚 Numery Stronga z pełnym słownikiem hebrajsko-greckim.
📜 Interlinia tekstu oryginalnego: dotknij słowa w tekście greckim lub hebrajskim, aby zobaczyć numer Stronga i pełną analizę gramatyczną.
🔀 Czytaj dwa przekłady obok siebie, werset po wersecie, lub porównaj werset we wszystkich przekładach.
📅 Plany czytania: Biblia w rok, plan chronologiczny, NT w 90 dni i inne — ze śledzeniem postępów.
🔍 Wyszukiwanie niewrażliwe na znaki diakrytyczne we wszystkich przekładach.
✏️ Zakładki, notatki, zakreślenia, odsyłacze, kopia zapasowa.
🖼 Werset dnia na widżecie; klasyczne ryciny Dorégo i Schnorra.

Wszystkie teksty są w domenie publicznej. Aplikacja nie zbiera żadnych danych.

### Português — Portuguese, Brazil (pt-BR)

**Título:** Hexapla — Bíblia Paralela

**Descrição curta (≤80):**
Bíblia offline: 35 traduções clássicas, áudio, planos de leitura, Strong.

**Descrição completa:**

Hexapla — a Bíblia completa sem internet, sem anúncios, sem cadastro e sem coleta de dados. Tudo gratuito, nada bloqueado.

📖 35 traduções clássicas em 30 idiomas: Almeida (Bíblia Livre, Textus Receptus), KJV 1611 com apócrifos, Webster 1833, Genebra 1599, Diodati 1649, Reina-Valera 1909, Lutero 1545, Martin 1744, Carlos XII 1703/1873 (sueca), dinamarquesa 1819, Sinodal russa, eslavo eclesiástico, 明治元訳 japonesa, 和合本 chinesa, e os originais em hebraico e grego.
✝️ As Boas Novas: o plano de salvação de Deus passo a passo, somente Escritura.
🔴 Palavras de Cristo em vermelho.
🎧 Áudio: narração e voz sintetizada com realce de versículos, reprodução em segundo plano, temporizador.
📚 Números de Strong com léxico hebraico/grego completo.
📜 Interlinear do original: toque numa palavra do texto grego ou hebraico e veja o número de Strong e a análise gramatical.
🔀 Leia duas traduções lado a lado ou compare um versículo em todas.
📅 Planos de leitura: Bíblia em 1 ano, plano cronológico, NT em 90 dias e mais — com progresso.
🔍 Busca sem acentos em todas as traduções.
✏️ Marcadores, notas, destaques, referências cruzadas, backup.
🖼 Versículo do dia no widget; gravuras clássicas de Doré e Schnorr.

Todos os textos são de domínio público. O app não coleta nenhum dado.

### Português de Portugal — Portuguese, Portugal (pt-PT)

**Título:** Hexapla — Bíblia Paralela

**Descrição curta (≤80):**
Bíblia offline: 35 traduções clássicas, áudio, planos de leitura, Strong.

**Descrição completa:**

Hexapla — a Bíblia completa sem internet, sem anúncios, sem registo e sem recolha de dados. Tudo gratuito, nada bloqueado.

📖 35 traduções clássicas em 30 idiomas: Almeida (Bíblia Livre, Textus Receptus), KJV 1611 com apócrifos, Webster 1833, Genebra 1599, Diodati 1649, Reina-Valera 1909, Lutero 1545, Martin 1744, Carlos XII 1703/1873 (sueca), dinamarquesa 1819, Sinodal russa, eslavo eclesiástico, 明治元訳 japonesa, 和合本 chinesa, e os originais em hebraico e grego.
✝️ As Boas Novas: o plano de salvação de Deus passo a passo, somente Escritura.
🔴 Palavras de Cristo em vermelho.
🎧 Áudio: narração e voz sintetizada com realce de versículos, reprodução em segundo plano, temporizador.
📚 Números de Strong com léxico hebraico/grego completo.
📜 Interlinear do original: toque numa palavra do texto grego ou hebraico e veja o número de Strong e a análise gramatical.
🔀 Leia duas traduções lado a lado ou compare um versículo em todas.
📅 Planos de leitura: Bíblia em 1 ano, plano cronológico, NT em 90 dias e mais — com progresso.
🔍 Pesquisa sem acentos em todas as traduções.
✏️ Marcadores, notas, destaques, referências cruzadas, cópia de segurança.
🖼 Versículo do dia no widget; gravuras clássicas de Doré e Schnorr.

Todos os textos são de domínio público. A aplicação não recolhe nenhum dado.

### Русский — Russian (ru-RU)

**Название:** Гексапла — параллельная Библия

**Краткое описание (до 80 зн.):**
Библия офлайн: 35 переводов, озвучка, планы чтения, симфония Стронга.

**Полное описание:**

Гексапла — полная Библия без интернета, без рекламы, без регистрации и без сбора данных. Всё бесплатно и ничего не заблокировано.

📖 35 классических переводов на 30 языках: Синодальный, Елизаветинская Библия (церковнославянский), KJV 1611 с апокрифами, Библия Уэбстера 1833, Женевская 1599, Уиклиф, Тиндейл, Bible Martin 1744 (франц.), Библия Лютера 1545 (нем.), Карла XII 1703/1873 (швед.), датская 1819, Рейна-Валера 1909 (исп.), Диодати 1649 (итал.), Bíblia Livre — Алмейда TR (порт.), 明治元訳 — первая японская Библия 1880/87, китайская 和合本 1919 (трад. и упрощ. иероглифы), древнееврейский текст (Ленинградский кодекс), греческий Новый Завет (византийский текст), санскритский Новый Завет 1851 года, тамильская Библия (IRV 2019, линия Бауэра 1871), латинская Вульгата (Климентина, 1592), нидерландская Statenvertaling 1637 года, арабская Библия Ван Дейка 1865 года и персидский Новый Завет в переводе Генри Мартина 1876 года — и другие.

✝️ «Благая весть» — план спасения шаг за шагом, только стихи Писания.
🔴 Слова Христа выделены красным.
🎧 Озвучка: записанное чтение (записи LibriVox и сгенерированные голоса) и синтез речи с подсветкой стиха и слова, фоновое воспроизведение, таймер сна, скорость.
📚 Номера Стронга с еврейско-греческим словарём; словарь Уэбстера 1828 — значение любого слова английских переводов по касанию.
🔀 Параллельное чтение двух переводов стих в стих и сравнение стиха во всех переводах.
📜 Подстрочник оригинала: коснитесь слова в греческом или еврейском тексте — номер Стронга и полный грамматический разбор.
📅 Планы чтения: Библия за год, хронологический план (вся Библия в порядке событий), НЗ за 90 дней, Евангелия за 30 дней, Притчи, Псалтирь — с прогрессом и серией дней.
🔍 Поиск без учёта диакритики, по всем переводам.
✏️ Закладки, заметки, цветные выделения, перекрёстные ссылки, резервное копирование.
🖼 Стих дня на виджете и в напоминании; классические гравюры Доре и Шнорра.

Все тексты — общественное достояние. Приложение не собирает никаких данных.

---

### Српски / Srpski — Serbian (sr) · Latin script, matches the translation

**Naziv:** Hexapla — Paralelna Biblija

**Kratak opis (≤80):**
Biblija bez interneta: 35 klasičnih prevoda, audio, planovi čitanja, Strong.

**Pun opis:**

Hexapla je kompletna Biblija — bez interneta, bez reklama, bez naloga i bez prikupljanja podataka. Sve je besplatno, ništa nije zaključano.

📖 35 klasičnih prevoda na 30 jezika: Sveto pismo — Karadžić/Daničić, 1847/1865, KJV 1611 sa apokrifima, Webster 1833, Ženevska Biblija 1599, Diodati 1649, Reina-Valera 1909, Lutherova Biblija 1545, Martin 1744, Biblija Karla XII 1703/1873, ruski Sinodalni prevod, crkvenoslovenski, japanski Meiji, kineska Union verzija (和合本), kao i hebrejski i grčki izvorni tekstovi.
✝️ Dobra vest — Božji plan spasenja korak po korak, isključivo iz Svetog pisma.
🔴 Hristove reči crvenim slovima.
🎧 Audio: čitanje i sinteza govora sa isticanjem stiha, reprodukcija u pozadini, tajmer za spavanje.
📚 Strongovi brojevi sa kompletnim hebrejsko-grčkim rečnikom.
📜 Interlinearni prikaz izvornog teksta: dodirnite reč u grčkom ili hebrejskom tekstu za Strongov broj i potpunu gramatičku analizu.
🔀 Čitajte dva prevoda uporedo, stih po stih, ili uporedite jedan stih u svim prevodima.
📅 Planovi čitanja: Biblija za godinu dana, hronološki plan, Novi zavet za 90 dana i drugi — sa praćenjem napretka.
🔍 Pretraga neosetljiva na dijakritičke znakove kroz sve prevode.
✏️ Obeleživači, beleške, isticanja, unakrsne reference, rezervna kopija.
🖼 Stih dana na vidžetu; klasične gravure Dorea i Šnora.

Svi tekstovi su javno vlasništvo. Aplikacija ne prikuplja nikakve podatke.

### Español — Spanish (es-ES, es-419, es-US)

**Título:** Hexapla — Biblia paralela

**Descripción corta:**
Biblia sin conexión: 35 traducciones clásicas, audio, planes de lectura.

**Descripción completa:**

Hexapla es la Biblia completa — sin conexión, sin anuncios, sin cuentas y sin recopilar datos. Todo es gratis y nada está bloqueado.

📖 35 traducciones clásicas en 30 idiomas, incluida la Reina-Valera 1909, la KJV 1611 y los originales hebreo y griego. ✝️ Las Buenas Nuevas: el plan de salvación de Dios paso a paso, solo Escritura. 🔴 Palabras de Cristo en rojo. 🎧 Audio con resaltado de versículos. 📚 Números Strong con léxico; interlineal griego/hebreo (análisis gramatical al tocar); diccionario Webster 1828 para las traducciones inglesas. 📅 Planes de lectura con progreso. ✏️ Marcadores, notas, resaltados, copia de seguridad.

Todos los textos son de dominio público. La aplicación no recopila nada.


---

### Svenska — Swedish (sv-SE)

**Titel:** Hexapla — Parallellbibel

**Kort beskrivning (≤80):**
Bibeln offline: 35 klassiska översättningar, ljud, läsplaner, Strong.

**Fullständig beskrivning:**

Hexapla — hela Bibeln utan internet, utan reklam, utan konto och utan datainsamling. Allt gratis, inget låst.

📖 35 klassiska översättningar på 30 språk: Karl XII:s Bibel 1703/1873, KJV 1611 med apokryfer, Webster 1833, Genève 1599, Diodati 1649, Reina-Valera 1909, Luther 1545, Martin 1744, danska 1819, ryska synodala, kyrkoslaviska, japanska 明治元訳, kinesiska 和合本 samt hebreiska och grekiska grundtexterna.
✝️ De goda nyheterna: Guds frälsningsplan steg för steg, endast Skriften.
🔴 Kristi ord i rött.
🎧 Ljud: uppläsning och talsyntes med versmarkering, bakgrundsuppspelning, insomningstimer.
📚 Strongs nummer med fullständigt hebreiskt/grekiskt lexikon.
📜 Interlinjär grundtext: tryck på ett ord i den grekiska eller hebreiska texten för Strongs nummer och grammatisk analys.
🔀 Läs två översättningar sida vid sida eller jämför en vers i alla.
📅 Läsplaner: Bibeln på 1 år, kronologisk plan, NT på 90 dagar m.fl. — med framsteg.
🔍 Sökning utan diakritiska tecken i alla översättningar.
✏️ Bokmärken, anteckningar, markeringar, korshänvisningar, säkerhetskopiering.
🖼 Dagens vers som widget; klassiska gravyrer av Doré och Schnorr.

Alla texter är allmän egendom. Appen samlar inte in några data.

### தமிழ் — Tamil (ta-IN) · lead with screenshot_reader_ta.png + feature_1024x500_ta.png

**Title:** Hexapla — இணை வேதாகமம்

**Short description (≤80):**
வேதாகமம் ஆஃப்லைன்: 35 மொழிபெயர்ப்புகள், ஒலி, திட்டங்கள், ஸ்ட்ராங்.

**Full description:**

ஹெக்ஸாப்லா — முழு வேதாகமம்: இணையம் தேவையில்லை, விளம்பரம் இல்லை, பதிவு இல்லை, தரவு சேகரிப்பு இல்லை. எல்லாம் இலவசம், எதுவும் பூட்டப்படவில்லை.

📖 30 மொழிகளில் 35 பாரம்பரிய மொழிபெயர்ப்புகள் — முழு தமிழ் வேதாகமம் (IRV 2019, 1871 பவர்/யூனியன் பாரம்பரியம்), எபிரெய தனக் (லெனின்கிராட் கோடெக்ஸ்), கிரேக்கப் புதிய ஏற்பாடு (பைசந்திய உரை), KJV 1611 (அப்போக்கிரிபாவுடன்), ஜெனீவா 1599, லூத்தர் 1545, சமஸ்கிருதப் புதிய ஏற்பாடு 1851 மற்றும் பல.
✝️ நற்செய்தி — தேவனுடைய இரட்சிப்பின் திட்டம், படிப்படியாக, வேத வசனங்களே.
🔴 கிறிஸ்துவின் வார்த்தைகள் சிவப்பில்.
🎧 ஒலி: பதிவுசெய்யப்பட்ட ஒலிவாசிப்பு (LibriVox வாசிப்புகள் மற்றும் உருவாக்கப்பட்ட குரல்கள்) மற்றும் பேச்சு மாற்றம் வசன ஒளிர்வுடன்; பின்னணி இயக்கம், தூக்க டைமர்.
📚 ஸ்ட்ராங் எண்கள் முழு எபிரெய/கிரேக்க அகராதியுடன்; மூல மொழி இடைவரி — எந்தக் கிரேக்க அல்லது எபிரெய வார்த்தையையும் தொட்டால் முழு இலக்கண விளக்கம், தமிழிலேயே.
🔀 இரண்டு மொழிபெயர்ப்புகளை அருகருகே வசனத்துக்கு வசனம் வாசியுங்கள்; அல்லது ஒரு வசனத்தை எல்லா மொழிபெயர்ப்புகளிலும் ஒப்பிடுங்கள்.
📅 முன்னேற்றத்துடன் வாசிப்புத் திட்டங்கள். 🔍 எல்லா மொழிபெயர்ப்புகளிலும் தேடல். ✏️ அடையாளக்குறிகள், குறிப்புகள், வண்ணக் குறியீடுகள், காப்புப்பிரதி.

எல்லா உரைகளும் பொதுக் களம் (public domain). ஆப் எந்தத் தரவையும் சேகரிப்பதில்லை.

# ── ARCHIVE: older release notes (historical) ──

## 1.6.3 release notes (paste per store)

<en-US>
Georgian for the first time: the Bakar Bible of 1743 — the complete Old and New Testament with the deuterocanonical books — and the app's interface is now in Georgian too. The Armenian Bible is complete: the classical Zohrab Old Testament joins the Western Armenian New Testament. The Russian Synodal Bible is now narrated in full. New: background music suited to each chapter, and a button that swaps the two translations in split view. Now 35 translations in 30 languages.
</en-US>

<ar>
الجورجية لأول مرة: كتاب باكار المقدس (1743) بعهديه القديم والجديد كاملين مع الأسفار القانونية الثانية، وواجهة التطبيق أصبحت بالجورجية أيضًا. واكتمل الكتاب المقدس الأرمني: عهد زوهراب القديم ينضم إلى العهد الجديد بالأرمنية الغربية. كما أصبحت الترجمة السينودسية الروسية مقروءة صوتيًا بالكامل. جديد: موسيقى خلفية تناسب أجواء كل إصحاح، وزر يبدّل الترجمتين في العرض المنقسم. الآن 35 ترجمة في 30 لغة.
</ar>

<be>
Упершыню грузінская: Біблія Бакара 1743 году — поўны Стары і Новы Запавет з дэўтэраканонічнымі кнігамі, а інтэрфейс цяпер таксама па-грузінску. Армянская Біблія стала поўнай: Стары Запавет Зограба далучыўся да заходнеармянскага Новага Запавету. Расійскі сінадальны пераклад цяпер агучаны цалкам. Новае: фонавая музыка пад настрой разьдзелу і кнопка, якая мяняе месцамі два пераклады. Цяпер 35 перакладаў у 30 мовах.
</be>

<cs-CZ>
Poprvé gruzínština: Bakarova Bible z roku 1743 — celý Starý i Nový zákon včetně deuterokanonických knih — a rozhraní je nyní také v gruzínštině. Arménská Bible je úplná: Zohrabův Starý zákon se připojil k západoarménskému Novému zákonu. Ruský synodální překlad je nyní kompletně namluvený. Novinky: hudba na pozadí podle ladění kapitoly a tlačítko, které prohodí oba překlady. Nyní 35 překladů ve 30 jazycích.
</cs-CZ>

<da-DK>
Georgisk for første gang: Bakar-bibelen fra 1743 — hele Det Gamle og Det Nye Testamente med de deuterokanoniske bøger — og appen findes nu også på georgisk. Den armenske bibel er komplet: Zohrabs Gamle Testamente slutter sig til Det Nye Testamente på vestarmensk. Den russiske synodalbibel er nu indlæst i sin helhed. Nyt: baggrundsmusik efter kapitlets stemning, og en knap der bytter om på de to oversættelser. Nu 35 oversættelser på 30 sprog.
</da-DK>

<de-DE>
Erstmals Georgisch: die Bakar-Bibel von 1743 — das vollständige Alte und Neue Testament samt den deuterokanonischen Büchern — und die App gibt es jetzt auch auf Georgisch. Die armenische Bibel ist vollständig: das Alte Testament nach Zohrab tritt zum westarmenischen Neuen Testament. Die russische Synodalbibel wird jetzt ganz vorgelesen. Neu: Hintergrundmusik zur Stimmung des Kapitels und eine Schaltfläche zum Tauschen beider Übersetzungen. Jetzt 35 Übersetzungen in 30 Sprachen.
</de-DE>

<el-GR>
Για πρώτη φορά γεωργιανά: η Βίβλος του Μπακάρ του 1743 — ολόκληρη η Παλαιά και η Καινή Διαθήκη με τα δευτεροκανονικά — και η εφαρμογή είναι πλέον και στα γεωργιανά. Η αρμενική Βίβλος ολοκληρώθηκε: η Παλαιά Διαθήκη του Ζοχράπ προστίθεται στη δυτικοαρμενική Καινή Διαθήκη. Η ρωσική Συνοδική Βίβλος διαβάζεται πλέον ολόκληρη. Νέα: μουσική ανάλογη με το κεφάλαιο και κουμπί που εναλλάσσει τις δύο μεταφράσεις. Τώρα 35 μεταφράσεις σε 30 γλώσσες.
</el-GR>

<en-IN>
Georgian for the first time: the Bakar Bible of 1743 — the complete Old and New Testament with the deuterocanonical books — and the app's interface is now in Georgian too. The Armenian Bible is complete: the classical Zohrab Old Testament joins the Western Armenian New Testament. The Russian Synodal Bible is now narrated in full. New: background music suited to each chapter, and a button that swaps the two translations in split view. Now 35 translations in 30 languages.
</en-IN>

<es-419>
Por primera vez en georgiano: la Biblia de Bakar de 1743, con el Antiguo y el Nuevo Testamento completos y los libros deuterocanónicos; la app también está ya en georgiano. La Biblia armenia queda completa: el Antiguo Testamento de Zohrab se suma al Nuevo Testamento en armenio occidental. La Biblia Sinodal rusa ya está narrada por completo. Novedades: música de fondo acorde al capítulo y un botón que intercambia las traducciones en la vista dividida. Ahora 35 traducciones en 30 idiomas.
</es-419>

<es-ES>
Por primera vez en georgiano: la Biblia de Bakar de 1743, con el Antiguo y el Nuevo Testamento completos y los libros deuterocanónicos; la app también está ya en georgiano. La Biblia armenia queda completa: el Antiguo Testamento de Zohrab se suma al Nuevo Testamento en armenio occidental. La Biblia Sinodal rusa ya está narrada por completo. Novedades: música de fondo acorde al capítulo y un botón que intercambia las traducciones en la vista dividida. Ahora 35 traducciones en 30 idiomas.
</es-ES>

<es-US>
Por primera vez en georgiano: la Biblia de Bakar de 1743, con el Antiguo y el Nuevo Testamento completos y los libros deuterocanónicos; la app también está ya en georgiano. La Biblia armenia queda completa: el Antiguo Testamento de Zohrab se suma al Nuevo Testamento en armenio occidental. La Biblia Sinodal rusa ya está narrada por completo. Novedades: música de fondo acorde al capítulo y un botón que intercambia las traducciones en la vista dividida. Ahora 35 traducciones en 30 idiomas.
</es-US>

<fi-FI>
Ensimmäistä kertaa georgiaa: vuoden 1743 Bakarin Raamattu — koko Vanha ja Uusi testamentti deuterokanonisine kirjoineen — ja sovellus on nyt myös georgiaksi. Armenialainen Raamattu on täydellinen: Zohrabin Vanha testamentti liittyy länsiarmenialaiseen Uuteen testamenttiin. Venäjän synodaaliraamattu on nyt kokonaan ääneen luettu. Uutta: taustamusiikki luvun tunnelman mukaan ja painike, joka vaihtaa käännösten paikkaa. Nyt 35 käännöstä 30 kielellä.
</fi-FI>

<fr-CA>
Le géorgien pour la première fois : la Bible de Bakar de 1743, avec l’Ancien et le Nouveau Testament complets et les livres deutérocanoniques ; l’app est désormais aussi en géorgien. La Bible arménienne est complète : l’Ancien Testament de Zohrab rejoint le Nouveau Testament en arménien occidental. La Bible synodale russe est désormais lue en entier. Nouveautés : une musique adaptée au chapitre et un bouton qui échange les traductions en vue partagée. Désormais 35 traductions en 30 langues.
</fr-CA>

<fr-FR>
Le géorgien pour la première fois : la Bible de Bakar de 1743, avec l’Ancien et le Nouveau Testament complets et les livres deutérocanoniques ; l’app est désormais aussi en géorgien. La Bible arménienne est complète : l’Ancien Testament de Zohrab rejoint le Nouveau Testament en arménien occidental. La Bible synodale russe est désormais lue en entier. Nouveautés : une musique adaptée au chapitre et un bouton qui échange les traductions en vue partagée. Désormais 35 traductions en 30 langues.
</fr-FR>

<hu-HU>
Először grúzul: az 1743-as Bakar-Biblia — a teljes Ó- és Újszövetség a deuterokanonikus könyvekkel —, és az alkalmazás is elérhető grúzul. Az örmény Biblia teljessé vált: Zohrab Ószövetsége csatlakozott a nyugati örmény Újszövetséghez. Az orosz szinodális Biblia mostantól teljesen hallgatható. Újdonság: a fejezet hangulatához illő háttérzene, és egy gomb, amely felcseréli a két fordítást. Most 35 fordítás 30 nyelven.
</hu-HU>

<hy-AM>
Առաջին անգամ վրացերեն՝ 1743 թ. Բաքարի Աստվածաշունչը՝ ամբողջական Հին և Նոր Կտակարան երկրորդականոն գրքերով, իսկ հավելվածն այժմ նույնպես վրացերեն է։ Հայերեն Աստվածաշունչն ամբողջական է՝ Զոհրապյան Հին Կտակարանն ավելացավ արևմտահայերեն Նոր Կտակարանին։ Ռուսերեն Սինոդալ Աստվածաշունչն այժմ ամբողջությամբ ընթերցվում է ձայնով։ Նոր՝ գլխին համապատասխան երաժշտություն և թարգմանությունները փոխող կոճակ։ Այժմ 35 թարգմանություն 30 լեզվով։
</hy-AM>

<it-IT>
Per la prima volta il georgiano: la Bibbia di Bakar del 1743, con l’Antico e il Nuovo Testamento completi e i libri deuterocanonici; anche l’app è ora in georgiano. La Bibbia armena è completa: l’Antico Testamento di Zohrab si affianca al Nuovo Testamento in armeno occidentale. La Bibbia sinodale russa ora si ascolta per intero. Novità: musica di sottofondo adatta al capitolo e un pulsante che scambia le traduzioni. Ora 35 traduzioni in 30 lingue.
</it-IT>

<iw-IL>
גאורגית לראשונה: התנ״ך של בקאר (1743) — הברית הישנה והחדשה במלואן, כולל הספרים החיצוניים — וגם האפליקציה זמינה כעת בגאורגית. המקרא הארמני הושלם: הברית הישנה של זוהרב מצטרפת לברית החדשה בארמנית מערבית. גם המקרא הסינודלי הרוסי נקרא כעת בקול במלואו. חדש: מוזיקת רקע המותאמת לפרק, וכפתור שמחליף בין שני התרגומים. כעת 35 תרגומים ב-30 שפות.
</iw-IL>

<ja-JP>
ジョージア語（グルジア語）が初登場。1743年のバカル聖書は旧約・新約の全巻に第二正典を加えた完全版で、アプリの表示もジョージア語に対応しました。アルメニア語聖書も完成し、ゾフラプ訳旧約が西アルメニア語の新約に加わりました。ロシア語シノド訳の朗読も全巻そろいました。新機能: 章の雰囲気に合わせた背景音楽と、分割表示で二つの訳を入れ替えるボタン。現在35訳・30言語。
</ja-JP>

<lv>
Pirmoreiz gruzīnu valodā: 1743. gada Bakara Bībele — pilnīga Vecā un Jaunā Derība kopā ar deiterokanoniskajām grāmatām — un lietotne tagad pieejama arī gruzīniski. Armēņu Bībele ir pilnīga: Zohraba Vecā Derība pievienojas Jaunajai Derībai rietumarmēņu valodā. Krievu Sinodālā Bībele tagad ir pilnībā ieskaņota. Jaunums: fona mūzika atbilstoši nodaļas noskaņai un poga, kas samaina abus tulkojumus. Tagad 35 tulkojumi 30 valodās.
</lv>

<nl-NL>
Voor het eerst Georgisch: de Bakarbijbel uit 1743 — het volledige Oude en Nieuwe Testament met de deuterocanonieke boeken — en de app is nu ook in het Georgisch. De Armeense Bijbel is compleet: het Oude Testament van Zohrab komt bij het West-Armeense Nieuwe Testament. De Russische Synodale Bijbel wordt nu volledig voorgelezen. Nieuw: achtergrondmuziek die past bij het hoofdstuk, en een knop die de twee vertalingen verwisselt. Nu 35 vertalingen in 30 talen.
</nl-NL>

<pl-PL>
Po raz pierwszy gruziński: Biblia Bakara z 1743 roku — cały Stary i Nowy Testament z księgami deuterokanonicznymi — a aplikacja jest już dostępna także po gruzińsku. Biblia ormiańska jest kompletna: Stary Testament Zohraba dołączył do zachodnioormiańskiego Nowego Testamentu. Rosyjski przekład synodalny jest teraz w całości czytany na głos. Nowość: muzyka w tle dobrana do rozdziału i przycisk zamieniający przekłady. Teraz 35 przekładów w 30 językach.
</pl-PL>

<pt-BR>
Pela primeira vez em georgiano: a Bíblia de Bakar de 1743, com o Antigo e o Novo Testamento completos e os livros deuterocanônicos; o app agora também está em georgiano. A Bíblia armênia ficou completa: o Antigo Testamento de Zohrab junta-se ao Novo Testamento em armênio ocidental. A Bíblia Sinodal russa já é lida por completo em voz alta. Novidades: música de fundo conforme o capítulo e um botão que troca as traduções. Agora 35 traduções em 30 idiomas.
</pt-BR>

<pt-PT>
Pela primeira vez em georgiano: a Bíblia de Bakar de 1743, com o Antigo e o Novo Testamento completos e os livros deuterocanónicos; a aplicação está agora também em georgiano. A Bíblia arménia ficou completa: o Antigo Testamento de Zohrab junta-se ao Novo Testamento em arménio ocidental. A Bíblia Sinodal russa já é lida por completo em voz alta. Novidades: música de fundo conforme o capítulo e um botão que troca as traduções. Agora 35 traduções em 30 idiomas.
</pt-PT>

<ru-RU>
Синодальный перевод теперь озвучен полностью — вся Библия, каждая глава. Впервые грузинский: Библия Бакара 1743 года — полные Ветхий и Новый Завет с неканоническими книгами, — и интерфейс теперь тоже на грузинском. Армянская Библия стала полной: Ветхий Завет Зохраба присоединился к новозаветному тексту на западноармянском. Новое: фоновая музыка под настроение главы и кнопка, меняющая местами два перевода. Теперь 35 переводов на 30 языках.
</ru-RU>

<sr>
Prvi put gruzijski: Bakarova Biblija iz 1743 — ceo Stari i Novi zavet sa devterokanonskim knjigama — a i aplikacija je sada na gruzijskom. Jermenska Biblija je potpuna: Stari zavet Zohraba pridružio se novozavetnom tekstu na zapadnojermenskom. Ruski Sinodalni prevod sada se čita naglas u celini. Novo: pozadinska muzika prilagođena poglavlju i dugme koje zamenjuje prevode. Sada 35 prevoda na 30 jezika.
</sr>

<sv-SE>
Georgiska för första gången: Bakarbibeln från 1743 — hela Gamla och Nya testamentet med de deuterokanoniska böckerna — och appen finns nu också på georgiska. Den armeniska bibeln är komplett: Zohrabs Gamla testamente sluter upp bredvid Nya testamentet på västarmeniska. Den ryska synodalbibeln läses nu upp i sin helhet. Nytt: bakgrundsmusik efter kapitlets stämning och en knapp som byter plats på översättningarna. Nu 35 översättningar på 30 språk.
</sv-SE>

<ta-IN>
முதன்முறையாக ஜார்ஜியன்: 1743 பாக்கர் பைபிள் — பழைய, புதிய ஏற்பாடுகள் முழுமையாக, இரண்டாம் நியமநூல்களுடன்; செயலியும் இப்போது ஜார்ஜிய மொழியில். ஆர்மீனிய பைபிள் முழுமை: ஸோஹ்ராப் பழைய ஏற்பாடு மேற்கு ஆர்மீனிய புதிய ஏற்பாட்டுடன் இணைந்தது. ரஷ்ய சினோடல் பைபிளும் இப்போது முழுமையாக ஒலிவடிவில். புதியவை: அதிகாரத்திற்கேற்ற பின்னணி இசை; மொழிபெயர்ப்புகளை இடம் மாற்றும் பொத்தான். இப்போது 30 மொழிகளில் 35 மொழிபெயர்ப்புகள்.
</ta-IN>

<zh-CN>
首次加入格鲁吉亚语：1743年巴卡尔圣经，完整的旧约与新约，并含次经；应用界面现在也支持格鲁吉亚语。亚美尼亚语圣经已完整：古典亚美尼亚语的佐赫拉布旧约与西亚美尼亚语新约合璧。俄文圣经现代主教公会译本也已完整朗读。新增：随每章气氛而变的背景音乐，以及在分栏视图中一键对调两个译本的按钮。现有35部译本、30种语言。
</zh-CN>

<zh-HK>
首次加入喬治亞語：1743年巴卡爾聖經，完整的舊約與新約，並含次經；應用程式介面現在也支援喬治亞語。亞美尼亞語聖經已完整：古典亞美尼亞語的佐赫拉布舊約與西亞美尼亞語新約合璧。俄文聖經正教會譯本也已完整朗讀。新增：隨每章氣氛而變的背景音樂，以及在分割檢視中一鍵對調兩個譯本的按鈕。現有35部譯本、30種語言。
</zh-HK>

<zh-TW>
首次加入喬治亞語：1743年巴卡爾聖經，完整的舊約與新約，並含次經；應用程式介面現在也支援喬治亞語。亞美尼亞語聖經已完整：古典亞美尼亞語的佐赫拉布舊約與西亞美尼亞語新約合璧。俄文聖經正教會譯本也已完整朗讀。新增：隨每章氣氛而變的背景音樂，以及在分割檢視中一鍵對調兩個譯本的按鈕。現有35部譯本、30種語言。
</zh-TW>

## 1.6.2 release notes (paste per store)

<en-US>
The Geneva Bible (1599) is now read aloud in full — all 66 books, every chapter. Recorded narration follows and highlights each verse, and resuming continues from the exact verse you stopped on. Fixes: the reader no longer reopens at the wrong chapter after using the widget or a reminder, the widget verse is now tappable, a black bar no longer appears beneath the text, and the bottom bar is slimmer. The Swedish Karl XII Bible (1703) is now complete too. Search across all translations is fixed.
</en-US>
<ar>
الكتاب المقدس بترجمة جنيف (1599) أصبح مقروءًا صوتيًا بالكامل: جميع الأسفار الستة والستين، وكل إصحاح. التلاوة المسجَّلة تتابع كل آية وتُبرزها، والاستئناف يبدأ من الآية نفسها التي توقفت عندها. إصلاحات: لم يعد القارئ يفتح على إصحاح خاطئ بعد استخدام الأداة أو التذكير، وأصبحت آية الأداة قابلة للنقر، ولم يعد يظهر شريط أسود أسفل النص، وشريط التنقل السفلي أصبح أنحف. كما اكتمل الكتاب المقدس السويدي (1703). كما أُصلح البحث في كل الترجمات.
</ar>
<be>
Жэнеўская Біблія (1599) цяпер агучана цалкам: усе 66 кніг, кожны разьдзел. Запісаная агучка сочыць за кожным вершам і падсьвятляе яго, а працяг пачынаецца з таго самага верша, на якім вы спыніліся. Выпраўлена: чытач больш не адкрываецца на няправільным разьдзеле пасьля віджэта ці нагадваньня, верш у віджэце цяпер націскальны, чорная паласа пад тэкстам зьнікла, а ніжняя панэль навігацыі стала танчэйшай. Швэдзкая Біблія Карла XII (1703) таксама завершана. Выпраўлены пошук па ўсіх перакладах.
</be>
<cs-CZ>
Ženevská Bible (1599) je nyní kompletně namluvená: všech 66 knih, každá kapitola. Nahraná četba sleduje a zvýrazňuje každý verš a pokračování naváže přesně na verši, kde jste skončili. Opravy: čtečka se už neotevírá ve špatné kapitole po použití widgetu nebo připomenutí, verš ve widgetu lze nyní klepnout, pod textem se už neobjevuje černý pruh a spodní navigační lišta je subtilnější. Švédská Bible Karla XII. (1703) je nyní kompletní. Opraveno je i hledání ve všech překladech.
</cs-CZ>
<da-DK>
Genève-bibelen (1599) læses nu op i sin helhed: alle 66 bøger. Den indlæste oplæsning følger og fremhæver hvert vers, og når du fortsætter, starter den præcis ved det vers, du stoppede på. Rettelser: læseren åbner ikke længere i det forkerte kapitel efter en widget eller en påmindelse, verset i widgetten kan nu trykkes på, der vises ikke længere en sort bjælke under teksten, og den nederste linje er slankere. Karl XII-bibelen (1703) er nu komplet. Søgning i alle oversættelser er rettet.
</da-DK>
<de-DE>
Die Genfer Bibel (1599) wird jetzt vollständig vorgelesen: alle 66 Bücher. Die aufgenommene Lesung folgt jedem Vers und hebt ihn hervor, und beim Fortsetzen geht es genau bei dem Vers weiter, bei dem Sie aufgehört haben. Behoben: Der Leser öffnet nach Widget oder Erinnerung nicht mehr im falschen Kapitel, der Widget-Vers ist jetzt antippbar, unter dem Text erscheint kein schwarzer Balken mehr, und die untere Leiste ist schmaler. Karl XII. (1703) ist nun komplett. Auch die Suche wurde behoben.
</de-DE>
<el-GR>
Η Βίβλος της Γενεύης (1599) διαβάζεται πλέον ολόκληρη: και τα 66 βιβλία. Η ηχογραφημένη ανάγνωση ακολουθεί και επισημαίνει κάθε στίχο, και η συνέχιση ξεκινά ακριβώς από τον στίχο όπου σταματήσατε. Διορθώσεις: ο αναγνώστης δεν ανοίγει πια σε λάθος κεφάλαιο μετά από widget ή υπενθύμιση, ο στίχος στο widget είναι πλέον πατήσιμος, δεν εμφανίζεται μαύρη μπάρα κάτω από το κείμενο και η κάτω μπάρα πλοήγησης είναι λεπτότερη. Ολοκληρώθηκε και η Βίβλος του Καρόλου ΙΒ΄ (1703). Διορθώθηκε και η αναζήτηση.
</el-GR>
<en-IN>
The Geneva Bible (1599) is now read aloud in full — all 66 books, every chapter. Recorded narration follows and highlights each verse, and resuming continues from the exact verse you stopped on. Fixes: the reader no longer reopens at the wrong chapter after using the widget or a reminder, the widget verse is now tappable, a black bar no longer appears beneath the text, and the bottom bar is slimmer. The Swedish Karl XII Bible (1703) is now complete too. Search across all translations is fixed.
</en-IN>
<es-419>
La Biblia de Ginebra (1599) ya se lee en voz alta por completo: los 66 libros. La narración grabada sigue y resalta cada versículo, y al reanudar continúa exactamente en el versículo donde lo dejaste. Correcciones: el lector ya no se abre en el capítulo equivocado tras usar el widget o un recordatorio, el versículo del widget ahora se puede tocar, ya no aparece una barra negra bajo el texto y la barra inferior es más estrecha. Karl XII (1703) ya está completa. También se corrigió la búsqueda.
</es-419>
<es-ES>
La Biblia de Ginebra (1599) ya se lee en voz alta por completo: los 66 libros. La narración grabada sigue y resalta cada versículo, y al reanudar continúa exactamente en el versículo donde lo dejaste. Correcciones: el lector ya no se abre en el capítulo equivocado tras usar el widget o un recordatorio, el versículo del widget ahora se puede tocar, ya no aparece una barra negra bajo el texto y la barra inferior es más estrecha. Karl XII (1703) ya está completa. También se corrigió la búsqueda.
</es-ES>
<es-US>
La Biblia de Ginebra (1599) ya se lee en voz alta por completo: los 66 libros. La narración grabada sigue y resalta cada versículo, y al reanudar continúa exactamente en el versículo donde lo dejaste. Correcciones: el lector ya no se abre en el capítulo equivocado tras usar el widget o un recordatorio, el versículo del widget ahora se puede tocar, ya no aparece una barra negra bajo el texto y la barra inferior es más estrecha. Karl XII (1703) ya está completa. También se corrigió la búsqueda.
</es-US>
<fi-FI>
Geneven Raamattu (1599) luetaan nyt kokonaan ääneen: kaikki 66 kirjaa, jokainen luku. Äänitetty luenta seuraa ja korostaa jokaista jaetta, ja jatkaminen alkaa täsmälleen siitä jakeesta, mihin jäit. Korjauksia: lukunäkymä ei enää avaudu väärään lukuun widgetin tai muistutuksen jälkeen, widgetin jaetta voi nyt napauttaa, tekstin alle ei enää ilmesty mustaa palkkia ja alanavigointipalkki on kapeampi. Kaarle XII:n Raamattu (1703) on nyt valmis. Myös haku on korjattu.
</fi-FI>
<fr-CA>
La Bible de Genève (1599) est désormais lue en entier : les 66 livres. La narration enregistrée suit et met en évidence chaque verset, et la reprise repart exactement au verset où vous vous êtes arrêté. Corrections : le lecteur ne s ouvre plus au mauvais chapitre après un widget ou un rappel, le verset du widget est maintenant cliquable, plus de bande noire sous le texte et la barre inférieure est plus fine. Karl XII (1703) est désormais complète. La recherche a aussi été corrigée.
</fr-CA>
<fr-FR>
La Bible de Genève (1599) est désormais lue en entier : les 66 livres. La narration enregistrée suit et met en évidence chaque verset, et la reprise repart exactement au verset où vous vous êtes arrêté. Corrections : le lecteur ne s ouvre plus au mauvais chapitre après un widget ou un rappel, le verset du widget est maintenant cliquable, plus de bande noire sous le texte et la barre inférieure est plus fine. Karl XII (1703) est désormais complète. La recherche a aussi été corrigée.
</fr-FR>
<hu-HU>
A Genfi Biblia (1599) mostantól teljes egészében hallgatható: mind a 66 könyv, minden fejezet. A felvett felolvasás követi és kiemeli az egyes verseket, a folytatás pedig pontosan annál a versnél indul, ahol abbahagyta. Javítások: az olvasó már nem rossz fejezetnél nyílik meg widget vagy emlékeztető után, a widget verse mostantól megérinthető, nem jelenik meg fekete sáv a szöveg alatt, és az alsó navigációs sáv keskenyebb. A Károly XII. Biblia (1703) is elkészült. A keresés is javítva lett.
</hu-HU>
<hy-AM>
Ժնևի Աստվածաշունչը (1599) այժմ ամբողջությամբ ընթերցվում է ձայնով՝ բոլոր 66 գրքերը, բոլոր գլուխները։ Ձայնագրված ընթերցումը հետևում և ընդգծում է յուրաքանչյուր համար, իսկ շարունակելիս սկսվում է հենց այն համարից, որտեղ կանգ եք առել։ Ուղղումներ՝ ընթերցիչն այլևս սխալ գլխով չի բացվում վիջեթից կամ հիշեցումից հետո, վիջեթի համարն այժմ սեղմելի է, տեքստի տակ սև գոտի այլևս չի երևում, ներքևի նավիգացիոն գոտին ավելի բարակ է։ Կարլ XII-ի Աստվածաշունչը (1703) նույնպես ավարտված է։ Ուղղվել է նաև որոնումը։
</hy-AM>
<it-IT>
La Bibbia di Ginevra (1599) ora si ascolta per intero: tutti i 66 libri. La narrazione registrata segue ed evidenzia ogni versetto e, riprendendo, riparte esattamente dal versetto in cui ti eri fermato. Correzioni: il lettore non si apre più al capitolo sbagliato dopo il widget o un promemoria, il versetto del widget ora è toccabile, non compare più una barra nera sotto il testo e la barra inferiore è più sottile. Anche Karl XII (1703) è ora completa. Anche la ricerca è stata corretta.
</it-IT>
<iw-IL>
התנך של ז׳נבה (1599) נקרא כעת בקול במלואו: כל 66 הספרים, כל פרק. ההקראה המוקלטת עוקבת ומדגישה כל פסוק, וההמשך מתחיל בדיוק בפסוק שבו הפסקת. תיקונים: הקורא כבר לא נפתח בפרק שגוי אחרי הווידג׳ט או תזכורת, אפשר כעת להקיש על הפסוק בווידג׳ט, לא מופיע עוד פס שחור מתחת לטקסט, וסרגל הניווט התחתון צר יותר. גם תנך קרל השנים־עשר (1703) הושלם. גם החיפוש תוקן.
</iw-IL>
<ja-JP>
ジュネーヴ聖書（1599年）の朗読が全巻そろいました。全66巻、すべての章です。録音朗読は各節を追って強調し、再開すると中断した節から正確に続きます。修正: ウィジェットやリマインダーの後に誤った章が開く問題、ウィジェットの聖句をタップできない問題、本文の下に黒い帯が出る問題を修正し、下部のナビゲーションバーを細くしました。 カール12世聖書（1703年）も全巻そろいました。 検索も修正しました。
</ja-JP>
<lv>
Ženēvas Bībele (1599) tagad ir pilnībā ieskaņota: visas 66 grāmatas, katra nodaļa. Ierakstītais lasījums seko katram pantam un to izceļ, bet, turpinot, sākas tieši no tā panta, kurā apstājāties. Labojumi: lasītājs vairs neatveras nepareizā nodaļā pēc logrīka vai atgādinājuma, logrīka pantam tagad var pieskarties, zem teksta vairs neparādās melna josla, un apakšējā navigācijas josla ir šaurāka. Kārļa XII Bībele (1703) tagad ir pabeigta. Labota ir arī meklēšana.
</lv>
<nl-NL>
De Geneefse Bijbel (1599) wordt nu volledig voorgelezen: alle 66 boeken, elk hoofdstuk. De opgenomen voorlezing volgt en markeert elk vers, en bij hervatten gaat het precies verder bij het vers waar u stopte. Opgelost: de lezer opent niet meer in het verkeerde hoofdstuk na de widget of een herinnering, het vers in de widget is nu aantikbaar, er verschijnt geen zwarte balk meer onder de tekst en de onderste navigatiebalk is smaller. Karl XII (1703) is nu ook compleet. Ook het zoeken is hersteld.
</nl-NL>
<pl-PL>
Biblia genewska (1599) jest teraz w całości czytana na głos: wszystkie 66 ksiąg. Nagrane czytanie śledzi i podświetla każdy werset, a wznowienie zaczyna się dokładnie od wersetu, na którym przerwano. Poprawki: czytnik nie otwiera się już w niewłaściwym rozdziale po użyciu widżetu lub przypomnienia, werset w widżecie można teraz kliknąć, pod tekstem nie pojawia się czarny pasek, a dolny pasek nawigacji jest węższy. Biblia Karola XII (1703) jest już kompletna. Poprawiono też wyszukiwanie.
</pl-PL>
<pt-BR>
A Bíblia de Genebra (1599) já é lida por completo em voz alta: todos os 66 livros. A narração gravada acompanha e destaca cada versículo, e ao retomar continua exatamente no versículo onde parou. Correções: o leitor já não abre no capítulo errado depois do widget ou de um lembrete, o versículo do widget agora pode ser tocado, deixou de aparecer uma barra preta sob o texto e a barra de navegação inferior está mais fina. Karl XII (1703) está agora completa. A busca também foi corrigida.
</pt-BR>
<pt-PT>
A Bíblia de Genebra (1599) já é lida por completo em voz alta: todos os 66 livros. A narração gravada acompanha e destaca cada versículo, e ao retomar continua exatamente no versículo onde parou. Correções: o leitor já não abre no capítulo errado depois do widget ou de um lembrete, o versículo do widget agora pode ser tocado, deixou de aparecer uma barra preta sob o texto e a barra de navegação inferior está mais fina. Karl XII (1703) está agora completa. A pesquisa também foi corrigida.
</pt-PT>
<ru-RU>
Женевская Библия (1599) теперь озвучена полностью: все 66 книг, каждая глава. Записанная озвучка следует за каждым стихом и подсвечивает его, а продолжение начинается ровно с того стиха, на котором вы остановились. Исправлено: чтение больше не открывается не на той главе после виджета или напоминания, стих в виджете теперь нажимается, под текстом больше нет чёрной полосы, а нижняя панель навигации стала тоньше. Библия Карла XII (1703) тоже завершена. Также исправлен поиск по всем переводам.
</ru-RU>
<sr>
Ženevska Biblija (1599) sada se čita naglas u celini: svih 66 knjiga, svako poglavlje. Snimljeno čitanje prati i ističe svaki stih, a nastavak počinje tačno od stiha na kome ste stali. Ispravke: čitač se više ne otvara na pogrešnom poglavlju posle vidžeta ili podsetnika, stih u vidžetu sada je moguće dodirnuti, ispod teksta se više ne pojavljuje crna traka, a donja navigaciona traka je tanja. I Biblija Karla XII (1703) sada je kompletna. Ispravljena je i pretraga.
</sr>
<sv-SE>
Genèvebibeln (1599) läses nu upp i sin helhet: alla 66 böcker, varje kapitel. Den inspelade uppläsningen följer och markerar varje vers, och när du fortsätter börjar den exakt vid versen där du slutade. Rättningar: läsaren öppnas inte längre i fel kapitel efter widgeten eller en påminnelse, versen i widgeten går nu att trycka på, ingen svart list visas under texten och den nedre navigeringsraden är smalare. Karl XII:s Bibel (1703) är nu komplett. Även sökningen är rättad.
</sv-SE>
<ta-IN>
ஜெனீவா பைபிள் (1599) இப்போது முழுமையாக ஒலிவடிவில்: 66 புத்தகங்கள், அனைத்து அதிகாரங்களும். பதிவு செய்யப்பட்ட வாசிப்பு ஒவ்வொரு வசனத்தையும் தொடர்ந்து சிறப்பித்துக் காட்டும்; நிறுத்திய வசனத்திலிருந்தே தொடரும். சரிசெய்தவை: விட்ஜெட் அல்லது நினைவூட்டலுக்குப் பிறகு தவறான அதிகாரம் திறக்காது, விட்ஜெட் வசனத்தைத் தொடலாம், உரைக்குக் கீழே கருப்புப் பட்டை இல்லை, கீழ் வழிசெலுத்தல் பட்டை மெலிந்துள்ளது. கார்ல் XII பைபிளும் (1703) இப்போது முழுமையானது. தேடலும் சரிசெய்யப்பட்டது.
</ta-IN>
<zh-CN>
日内瓦圣经（1599）现已完整朗读：全部66卷，每一章。录制朗读会跟随并高亮每一节经文，继续播放时会从你停下的那一节精确接续。修复：使用小组件或提醒后阅读器不再打开错误的章节；小组件中的经文现在可点按；正文下方不再出现黑条；底部导航栏更纤细。 卡尔十二世圣经（1703）也已完整。 搜索问题也已修复。
</zh-CN>
<zh-HK>
日內瓦聖經（1599）現已完整朗讀：全部66卷，每一章。錄製朗讀會跟隨並標示每一節經文，繼續播放時會從你停下的那一節精確接續。修復：使用小工具或提醒後閱讀器不再開啟錯誤的章節；小工具中的經文現在可點按；內文下方不再出現黑條；底部導覽列更纖細。 卡爾十二世聖經（1703）也已完整。 搜尋問題也已修復。
</zh-HK>
<zh-TW>
日內瓦聖經（1599）現已完整朗讀：全部66卷，每一章。錄製朗讀會跟隨並標示每一節經文，繼續播放時會從你停下的那一節精確接續。修復：使用小工具或提醒後閱讀器不再開啟錯誤的章節；小工具中的經文現在可點按；內文下方不再出現黑條；底部導覽列更纖細。 卡爾十二世聖經（1703）也已完整。 搜尋問題也已修復。
</zh-TW>

## 1.6.1 release notes (paste per store)

<en-US>
The Swedish Karl XII Bible (1703) is now read aloud: the complete New Testament plus Genesis, Exodus and the Psalms, with more books added over time. Recorded narration now follows and highlights each verse as it is read, and resuming continues from the exact verse you stopped on. Fixes: narration no longer drops back to the device's text-to-speech partway through a book, and reading plans now open on your current day.
</en-US>
<ar>
أصبح الكتاب المقدس السويدي بترجمة كارل الثاني عشر (1703) مقروءًا صوتيًا: العهد الجديد كاملًا مع سفر التكوين وسفر الخروج والمزامير، وستُضاف أسفار أخرى تباعًا. التلاوة المسجَّلة تتابع كل آية وتُبرزها أثناء القراءة، والاستئناف يبدأ من الآية نفسها التي توقفت عندها. إصلاحات: لم تعد التلاوة تعود إلى القراءة الآلية من الجهاز في منتصف السفر، وخطط القراءة تفتح الآن على يومك الحالي.
</ar>
<be>
Швэдзкая Біблія Карла XII (1703) цяпер агучана: увесь Новы Запавет, а таксама Быцьцё, Выхад і Псальмы; іншыя кнігі дадаюцца паступова. Запісаная агучка сочыць за кожным вершам і падсьвятляе яго, а працяг пачынаецца з таго самага верша, на якім вы спыніліся. Выпраўлена: агучка больш не пераходзіць на сынтэз маўленьня прылады пасярод кнігі, а планы чытаньня адкрываюцца на бягучым дні.
</be>
<cs-CZ>
Švédská Bible Karla XII. (1703) je nyní namluvená: celý Nový zákon a k tomu Genesis, Exodus a Žalmy; další knihy přibývají postupně. Nahraná četba nyní sleduje a zvýrazňuje každý verš a pokračování naváže přesně na verši, kde jste skončili. Opravy: četba už uprostřed knihy nepřepne na hlasový výstup zařízení a plány čtení se otevírají na aktuálním dni.
</cs-CZ>
<da-DK>
Den svenske Karl XII-bibel (1703) læses nu op: hele Det Nye Testamente samt 1. og 2. Mosebog og Salmerne; flere bøger kommer til løbende. Den indlæste oplæsning følger og fremhæver nu hvert vers, og når du fortsætter, starter den præcis ved det vers, du stoppede på. Rettelser: oplæsningen skifter ikke længere til enhedens talesyntese midt i en bog, og læseplaner åbner på din aktuelle dag.
</da-DK>
<de-DE>
Die schwedische Karl-XII.-Bibel (1703) wird jetzt vorgelesen: das vollständige Neue Testament sowie Genesis, Exodus und die Psalmen; weitere Bücher kommen nach und nach hinzu. Die aufgenommene Lesung folgt nun jedem Vers und hebt ihn hervor, und beim Fortsetzen geht es genau bei dem Vers weiter, bei dem Sie aufgehört haben. Behoben: Die Lesung wechselt nicht mehr mitten im Buch zur Sprachausgabe des Geräts, und Lesepläne öffnen sich beim aktuellen Tag.
</de-DE>
<el-GR>
Η σουηδική Βίβλος του Καρόλου ΙΒ΄ (1703) διαβάζεται πλέον φωναχτά: ολόκληρη η Καινή Διαθήκη μαζί με τη Γένεση, την Έξοδο και τους Ψαλμούς· και άλλα βιβλία προστίθενται σταδιακά. Η ηχογραφημένη ανάγνωση ακολουθεί και επισημαίνει τώρα κάθε στίχο, ενώ η συνέχιση ξεκινά ακριβώς από τον στίχο που σταματήσατε. Διορθώσεις: η ανάγνωση δεν γυρίζει πια στη φωνητική σύνθεση της συσκευής στη μέση ενός βιβλίου και τα προγράμματα ανάγνωσης ανοίγουν στην τρέχουσα ημέρα.
</el-GR>
<en-IN>
The Swedish Karl XII Bible (1703) is now read aloud: the complete New Testament plus Genesis, Exodus and the Psalms, with more books added over time. Recorded narration now follows and highlights each verse as it is read, and resuming continues from the exact verse you stopped on. Fixes: narration no longer drops back to the device's text-to-speech partway through a book, and reading plans now open on your current day.
</en-IN>
<es-419>
La Biblia sueca de Carlos XII (1703) ya se lee en voz alta: el Nuevo Testamento completo más Génesis, Éxodo y los Salmos; se irán añadiendo más libros. La narración grabada ahora sigue y resalta cada versículo, y al reanudar continúa exactamente en el versículo donde lo dejaste. Correcciones: la narración ya no vuelve a la síntesis de voz del dispositivo a mitad de un libro y los planes de lectura se abren en tu día actual.
</es-419>
<es-ES>
La Biblia sueca de Carlos XII (1703) ya se lee en voz alta: el Nuevo Testamento completo más Génesis, Éxodo y los Salmos; se irán añadiendo más libros. La narración grabada ahora sigue y resalta cada versículo, y al reanudar continúa exactamente en el versículo donde lo dejaste. Correcciones: la narración ya no vuelve a la síntesis de voz del dispositivo a mitad de un libro y los planes de lectura se abren en tu día actual.
</es-ES>
<es-US>
La Biblia sueca de Carlos XII (1703) ya se lee en voz alta: el Nuevo Testamento completo más Génesis, Éxodo y los Salmos; se irán añadiendo más libros. La narración grabada ahora sigue y resalta cada versículo, y al reanudar continúa exactamente en el versículo donde lo dejaste. Correcciones: la narración ya no vuelve a la síntesis de voz del dispositivo a mitad de un libro y los planes de lectura se abren en tu día actual.
</es-US>
<fi-FI>
Ruotsalainen Kaarle XII:n Raamattu (1703) luetaan nyt ääneen: koko Uusi testamentti sekä 1. ja 2. Mooseksen kirja ja Psalmit; lisää kirjoja tulee vähitellen. Äänitetty luenta seuraa ja korostaa nyt jokaista jaetta, ja jatkaminen alkaa täsmälleen siitä jakeesta, mihin jäit. Korjauksia: luenta ei enää vaihda laitteen puhesynteesiin kesken kirjan, ja lukusuunnitelmat avautuvat nykyiseen päivääsi.
</fi-FI>
<fr-CA>
La Bible suédoise de Charles XII (1703) est désormais lue à voix haute : tout le Nouveau Testament, ainsi que la Genèse, l'Exode et les Psaumes ; d'autres livres s'ajouteront progressivement. La narration enregistrée suit et surligne maintenant chaque verset, et la reprise repart exactement au verset où vous vous étiez arrêté. Corrections : la narration ne bascule plus vers la synthèse vocale de l'appareil au milieu d'un livre, et les plans de lecture s'ouvrent au jour en cours.
</fr-CA>
<fr-FR>
La Bible suédoise de Charles XII (1703) est désormais lue à voix haute : tout le Nouveau Testament, ainsi que la Genèse, l'Exode et les Psaumes ; d'autres livres s'ajouteront progressivement. La narration enregistrée suit et surligne maintenant chaque verset, et la reprise repart exactement au verset où vous vous étiez arrêté. Corrections : la narration ne bascule plus vers la synthèse vocale de l'appareil au milieu d'un livre, et les plans de lecture s'ouvrent au jour en cours.
</fr-FR>
<hu-HU>
A svéd XII. Károly-Biblia (1703) mostantól hangosan is olvasható: a teljes Újszövetség, valamint Mózes első és második könyve és a Zsoltárok; a többi könyv fokozatosan érkezik. A felvett felolvasás mostantól követi és kiemeli az egyes verseket, a folytatás pedig pontosan onnan indul, ahol abbahagytad. Javítások: a felolvasás már nem vált az eszköz beszédszintetizátorára a könyv közepén, az olvasótervek pedig az aktuális napon nyílnak meg.
</hu-HU>
<hy-AM>
Շուէտական Կարլ ԺԲ.-ի Աստուածաշունչը (1703) այժմ ընթերցւում է բարձրաձայն՝ ամբողջ Նոր Կտակարանը, ինչպէս նաեւ Ծննդոց, Ելից եւ Սաղմոսներ գիրքերը. միւս գիրքերը կ՚աւելանան աստիճանաբար։ Ձայնագրուած ընթերցումն այժմ հետեւում է իւրաքանչիւր համարին եւ ընդգծում է այն, իսկ շարունակելիս սկսում է ճիշդ այն համարից, ուր կանգ էիք առել։ Ուղղումներ՝ ընթերցումն այլեւս գրքի կէսին չի անցնում սարքի խօսքի սինթեզի, եւ ընթերցանութեան ծրագրերը բացւում են ընթացիկ օրով։
</hy-AM>
<it-IT>
La Bibbia svedese di Carlo XII (1703) ora viene letta ad alta voce: tutto il Nuovo Testamento più Genesi, Esodo e i Salmi; altri libri saranno aggiunti nel tempo. La narrazione registrata ora segue ed evidenzia ogni versetto, e la ripresa riparte esattamente dal versetto in cui ti eri fermato. Correzioni: la narrazione non torna più alla sintesi vocale del dispositivo a metà libro e i piani di lettura si aprono al giorno corrente.
</it-IT>
<iw-IL>
התרגום השוודי של קרל השנים־עשר (1703) מוקרא כעת בקול: כל הברית החדשה, וכן בראשית, שמות ותהילים; ספרים נוספים יתווספו בהדרגה. ההקראה המוקלטת עוקבת כעת אחר כל פסוק ומדגישה אותו, וההמשך מתחיל בדיוק בפסוק שבו הפסקתם. תיקונים: ההקראה כבר לא עוברת להקראה ממוחשבת של המכשיר באמצע ספר, ותוכניות הקריאה נפתחות ביום הנוכחי.
</iw-IL>
<ja-JP>
スウェーデン語のカール12世訳聖書（1703年）が朗読に対応しました。新約聖書全巻に加え、創世記・出エジプト記・詩篇が聴けます（他の書も順次追加）。録音朗読は各節を追って強調表示するようになり、再開すると止めた節から正確に続きます。修正：朗読が書の途中で端末の音声合成に戻らなくなり、通読プランは現在の日から開くようになりました。
</ja-JP>
<lv>
Zviedru Kārļa XII Bībele (1703) tagad ir ierunāta: visa Jaunā Derība, kā arī 1. un 2. Mozus grāmata un Psalmi; pārējās grāmatas tiks pievienotas pakāpeniski. Ieskaņotā lasīšana tagad seko katram pantam un to izceļ, bet, turpinot atskaņošanu, tā sākas tieši no tā panta, kurā apstājāties. Labojumi: lasīšana vairs nepārslēdzas uz ierīces runas sintēzi grāmatas vidū, un lasīšanas plāni atveras pašreizējā dienā.
</lv>
<nl-NL>
De Zweedse Karel XII-Bijbel (1703) wordt nu voorgelezen: het volledige Nieuwe Testament plus Genesis, Exodus en de Psalmen; meer boeken volgen geleidelijk. De opgenomen voordracht volgt en markeert nu elk vers, en bij hervatten gaat het verder bij precies het vers waar u stopte. Opgelost: de voordracht schakelt niet meer halverwege een boek terug naar de spraakuitvoer van het apparaat, en leesplannen openen op uw huidige dag.
</nl-NL>
<pl-PL>
Szwedzka Biblia Karola XII (1703) jest teraz czytana na głos: cały Nowy Testament oraz Księga Rodzaju, Księga Wyjścia i Psalmy; kolejne księgi będą dodawane stopniowo. Nagrane czytanie śledzi teraz każdy werset i go podświetla, a wznowienie zaczyna się dokładnie od wersetu, na którym przerwano. Poprawki: czytanie nie wraca już do syntezatora mowy urządzenia w środku księgi, a plany czytania otwierają się na bieżącym dniu.
</pl-PL>
<pt-BR>
A Bíblia sueca de Carlos XII (1703) agora é narrada: todo o Novo Testamento, além de Gênesis, Êxodo e os Salmos; outros livros serão acrescentados aos poucos. A narração gravada agora acompanha e destaca cada versículo, e ao retomar continua exatamente no versículo em que você parou. Correções: a narração não volta mais para a síntese de voz do aparelho no meio de um livro, e os planos de leitura abrem no seu dia atual.
</pt-BR>
<pt-PT>
A Bíblia sueca de Carlos XII (1703) passa a ser narrada: todo o Novo Testamento, além de Génesis, Êxodo e os Salmos; outros livros serão acrescentados gradualmente. A narração gravada acompanha agora cada versículo e destaca-o, e ao retomar continua exatamente no versículo em que parou. Correções: a narração já não volta à síntese de voz do aparelho a meio de um livro, e os planos de leitura abrem no seu dia atual.
</pt-PT>
<ru-RU>
Шведская Библия Карла XII (1703) теперь озвучена: весь Новый Завет, а также Бытие, Исход и Псалтирь; остальные книги добавляются постепенно. Записанная озвучка теперь следит за каждым стихом и подсвечивает его, а при продолжении воспроизведение начинается ровно с того стиха, на котором вы остановились. Исправлено: озвучка больше не переключается на синтезатор речи устройства посреди книги, а планы чтения открываются на текущем дне.
</ru-RU>
<sr>
Švedska Biblija Karla XII (1703) sada se čita naglas: ceo Novi zavet, kao i Postanje, Izlazak i Psalmi; ostale knjige dodaju se postepeno. Snimljena naracija sada prati i ističe svaki stih, a nastavak počinje tačno od stiha na kom ste stali. Ispravke: naracija više ne prelazi na sintezu govora uređaja usred knjige, a planovi čitanja otvaraju se na tekućem danu.
</sr>
<sv-SE>
Karl XII:s Bibel (1703) läses nu upp: hela Nya testamentet samt Första och Andra Moseboken och Psaltaren; fler böcker läggs till efter hand. Den inlästa uppläsningen följer och markerar nu varje vers, och när du fortsätter startar den exakt vid versen där du slutade. Rättningar: uppläsningen växlar inte längre till enhetens talsyntes mitt i en bok, och läsplaner öppnas på din aktuella dag.
</sv-SE>
<ta-IN>
கார்ல் பன்னிரண்டாம் மன்னரின் ஸ்வீடிஷ் விவிலியம் (1703) இப்போது ஒலிவடிவில் வாசிக்கப்படுகிறது: புதிய ஏற்பாடு முழுவதும், மேலும் ஆதியாகமம், யாத்திராகமம், சங்கீதம்; மற்ற புத்தகங்கள் படிப்படியாகச் சேர்க்கப்படும். பதிவுசெய்யப்பட்ட ஒலிவாசிப்பு இப்போது ஒவ்வொரு வசனத்தையும் பின்தொடர்ந்து சிறப்பித்துக் காட்டுகிறது; நிறுத்திய வசனத்திலிருந்தே மீண்டும் தொடர்கிறது. சரிசெய்தவை: புத்தகத்தின் நடுவில் ஒலிவாசிப்பு சாதனத்தின் பேச்சுத்தொகுப்புக்கு மாறாது; வாசிப்புத் திட்டங்கள் தற்போதைய நாளில் திறக்கும்.
</ta-IN>
<zh-CN>
瑞典卡尔十二世圣经（1703年）现已支持朗读：新约全书，以及创世记、出埃及记和诗篇；其余各卷将陆续加入。录制朗读现在会逐节跟随并高亮显示，继续播放时会从你停下的那一节精确接续。修复：朗读不再在书卷中途退回设备的语音合成，读经计划现在会打开到你当前的日程。
</zh-CN>
<zh-HK>
瑞典卡爾十二世聖經（1703年）現已支援朗讀：新約全書，以及創世記、出埃及記和詩篇；其餘各卷將陸續加入。錄製朗讀現在會逐節跟隨並高亮顯示，繼續播放時會從你停下的那一節精確接續。修復：朗讀不再在書卷中途退回裝置的語音合成，讀經計劃現在會開啟到你目前的日程。
</zh-HK>
<zh-TW>
瑞典卡爾十二世聖經（1703年）現已支援朗讀：新約全書，以及創世記、出埃及記和詩篇；其餘各卷將陸續加入。錄製朗讀現在會逐節跟隨並高亮顯示，繼續播放時會從你停下的那一節精確接續。修復：朗讀不再在書卷中途退回裝置的語音合成，讀經計劃現在會開啟到你目前的日程。
</zh-TW>

file, newest-first, so the file opens on what you actually need to paste
rather than on years of history. The validator fails if a second release block
is left above the descriptions section.

## 1.6.0 release notes (paste per store)

<en-US>
New translation: the Persian New Testament in Henry Martyn's translation (1876) — now 33 translations in 29 languages. New narration: Webster's Bible (1833) is now read aloud in full, and the remaining King James books are narrated too. Audio saves for offline listening, or turn on streaming to save space.
</en-US>
<ar>
ترجمة جديدة: العهد الجديد الفارسي بترجمة هنري مارتن (1876) — الآن 33 ترجمة في 29 لغة. صوت جديد: أصبحت نسخة وبستر (1833) مقروءة بالكامل، وأُضيفت قراءة صوتية لبقية أسفار الملك جيمس. يُحفظ الصوت للاستماع دون إنترنت، أو فعّل البث لتوفير المساحة.
</ar>
<be>
Новы пераклад: персідскі Новы Запавет у перакладзе Гэнры Мартына (1876) — цяпер 33 пераклады на 29 мовах. Новая агучка: Біблія Ўэбстэра (1833) цалкам агучана, дададзена агучка астатніх кніг Кінга Джэймса. Аўдыё захоўваецца для афлайнавага праслухоўваньня, або ўключыце патокавы рэжым.
</be>
<cs-CZ>
Nový překlad: perský Nový zákon v překladu Henryho Martyna (1876) — nyní 33 překladů ve 29 jazycích. Nové načtení: Websterova Bible (1833) je nyní celá namluvená a přibylo načtení zbývajících knih Bible krále Jakuba. Zvuk se ukládá pro offline poslech, nebo zapněte streamování.
</cs-CZ>
<da-DK>
Ny oversættelse: Det Persiske Nye Testamente i Henry Martyns oversættelse (1876) — nu 33 oversættelser på 29 sprog. Ny oplæsning: Webster-Bibelen (1833) er nu læst helt op, og de øvrige King James-bøger er også indlæst. Lyd gemmes til offline-lytning, eller slå streaming til.
</da-DK>
<de-DE>
Eine neue Übersetzung: das persische Neue Testament in der Übersetzung von Henry Martyn (1876) — jetzt 33 Übersetzungen in 29 Sprachen. Neue Audioausgabe: die Webster-Bibel (1833) wird vollständig vorgelesen, und die übrigen King-James-Bücher erhalten ebenfalls eine Vertonung. Audio wird offline gespeichert oder kann gestreamt werden.
</de-DE>
<el-GR>
Νέα μετάφραση: η Περσική Καινή Διαθήκη στη μετάφραση του Χένρι Μάρτιν (1876) — τώρα 33 μεταφράσεις σε 29 γλώσσες. Νέα αφήγηση: η Βίβλος Webster (1833) διαβάζεται πλέον ολόκληρη, ενώ προστέθηκε αφήγηση και στα υπόλοιπα βιβλία της KJV. Ο ήχος αποθηκεύεται για ακρόαση εκτός σύνδεσης ή ενεργοποιήστε τη ροή.
</el-GR>
<es-419>
Nueva traducción: el Nuevo Testamento persa en la versión de Henry Martyn (1876): ahora 33 traducciones en 29 idiomas. Nueva narración: la Biblia de Webster (1833) ya se lee completa y se añadió narración para los demás libros de la King James. El audio se guarda para escuchar sin conexión, o activa la transmisión para ahorrar espacio.
</es-419>
<es-ES>
Nueva traducción: el Nuevo Testamento persa en la versión de Henry Martyn (1876): ahora 33 traducciones en 29 idiomas. Nueva narración: la Biblia de Webster (1833) ya se lee completa y se añadió narración para los demás libros de la King James. El audio se guarda para escuchar sin conexión, o activa la transmisión para ahorrar espacio.
</es-ES>
<es-US>
Nueva traducción: el Nuevo Testamento persa en la versión de Henry Martyn (1876): ahora 33 traducciones en 29 idiomas. Nueva narración: la Biblia de Webster (1833) ya se lee completa y se añadió narración para los demás libros de la King James. El audio se guarda para escuchar sin conexión, o activa la transmisión para ahorrar espacio.
</es-US>
<fi-FI>
Uusi käännös: persialainen Uusi testamentti Henry Martynin käännöksenä (1876) — nyt 33 käännöstä 29 kielellä. Uusi ääniluku: Websterin Raamattu (1833) luetaan nyt kokonaan, ja myös loput King James -kirjat on äänitetty. Ääni tallentuu offline-kuunteluun, tai ota suoratoisto käyttöön.
</fi-FI>
<fr-CA>
Nouvelle traduction : le Nouveau Testament persan dans la version d'Henry Martyn (1876) — désormais 33 traductions en 29 langues. Nouvelle narration : la Bible de Webster (1833) est maintenant lue en entier, et les autres livres de la King James sont aussi narrés. L'audio est enregistré pour une écoute hors ligne, ou activez la diffusion en continu.
</fr-CA>
<fr-FR>
Nouvelle traduction : le Nouveau Testament persan dans la version d'Henry Martyn (1876) — désormais 33 traductions en 29 langues. Nouvelle narration : la Bible de Webster (1833) est maintenant lue en entier, et les autres livres de la King James sont aussi narrés. L'audio est enregistré pour une écoute hors ligne, ou activez la diffusion en continu.
</fr-FR>
<hu-HU>
Új fordítás: a perzsa Újszövetség Henry Martyn fordításában (1876) — most 33 fordítás 29 nyelven. Új felolvasás: a Webster-Biblia (1833) mostantól teljesen fel van olvasva, és a többi King James-könyv is hangot kapott. A hang letöltődik offline hallgatáshoz, vagy kapcsold be a streamelést.
</hu-HU>
<hy-AM>
Նոր թարգմանութիւն՝ պարսկերէն Նոր Կտակարանը Հենրի Մարտինի թարգմանութեամբ (1876) — այժմ 33 թարգմանութիւն 29 լեզուներով։ Նոր ձայնագրութիւն՝ Ուեբսթերի Աստուածաշունչը (1833) այժմ ամբողջութեամբ ընթերցուած է, եւ ձայն ստացան նաեւ մնացեալ Քինգ Ջեյմս գրքերը։ Ձայնը պահւում է անցանց լսելու համար, կամ միացրէք հոսքը։
</hy-AM>
<it-IT>
Nuova traduzione: il Nuovo Testamento persiano nella versione di Henry Martyn (1876) — ora 33 traduzioni in 29 lingue. Nuova narrazione: la Bibbia di Webster (1833) è ora letta per intero e sono stati narrati anche gli altri libri della King James. L'audio si salva per l'ascolto offline, oppure attiva lo streaming.
</it-IT>
<iw-IL>
תרגום חדש: הברית החדשה הפרסית בתרגומו של הנרי מרטין (1876) — כעת 33 תרגומים ב-29 שפות. הקראה חדשה: תרגום וובסטר (1833) מוקרא כעת במלואו, ונוספה הקראה לשאר ספרי המלך ג'יימס. השמע נשמר להאזנה לא מקוונת, או הפעילו הזרמה.
</iw-IL>
<ja-JP>
新しい翻訳：ヘンリー・マーティン訳のペルシア語新約聖書（1876年）を追加し、33訳・29言語になりました。新しい朗読：ウェブスター訳（1833年）が全編朗読になり、欽定訳の残りの書も朗読されます。音声はオフライン再生用に保存でき、ストリーミングも選べます。
</ja-JP>
<lv>
Jauns tulkojums: persiešu Jaunā Derība Henrija Mārtina tulkojumā (1876) — tagad 33 tulkojumi 29 valodās. Jauns ieskaņojums: Vēbstera Bībele (1833) tagad ir pilnībā ierunāta, un ieskaņotas arī pārējās Karaļa Džeimsa grāmatas. Skaņu var saglabāt bezsaistes klausīšanai vai ieslēgt straumēšanu.
</lv>
<nl-NL>
Nieuwe vertaling: het Perzische Nieuwe Testament in de vertaling van Henry Martyn (1876) — nu 33 vertalingen in 29 talen. Nieuwe voordracht: de Webster-Bijbel (1833) wordt nu volledig voorgelezen en ook de overige King James-boeken zijn ingesproken. Audio wordt opgeslagen voor offline luisteren, of schakel streamen in.
</nl-NL>
<pl-PL>
Nowy przekład: perski Nowy Testament w tłumaczeniu Henry'ego Martyna (1876) — teraz 33 przekłady w 29 językach. Nowe nagranie: Biblia Webstera (1833) jest teraz w całości czytana, a pozostałe księgi King James również otrzymały narrację. Dźwięk zapisuje się do słuchania offline lub włącz strumieniowanie.
</pl-PL>
<pt-BR>
Nova tradução: o Novo Testamento persa na versão de Henry Martyn (1876) — agora 33 traduções em 29 idiomas. Nova narração: a Bíblia de Webster (1833) agora é narrada por completo, e os demais livros da King James também ganharam narração. O áudio é salvo para ouvir offline, ou ative a transmissão.
</pt-BR>
<pt-PT>
Nova tradução: o Novo Testamento persa na versão de Henry Martyn (1876) — agora 33 traduções em 29 idiomas. Nova narração: a Bíblia de Webster (1833) passa a ser narrada por completo, e os restantes livros da King James também têm narração. O áudio é guardado para ouvir offline, ou ative a transmissão.
</pt-PT>
<ru-RU>
Один новый перевод: персидский Новый Завет в переводе Генри Мартина (1876) — теперь 33 перевода на 29 языках. Новая озвучка: Библия Уэбстера (1833) полностью озвучена, добавлена озвучка остальных книг Библии короля Якова. Аудио сохраняется для прослушивания офлайн, либо включите потоковый режим.
</ru-RU>
<sr>
Novi prevod: persijski Novi zavet u prevodu Henrija Martina (1876) — sada 33 prevoda na 29 jezika. Nova naracija: Vebsterova Biblija (1833) sada je u celosti pročitana, a naraciju su dobile i preostale knjige Kralja Džejmsa. Zvuk se čuva za slušanje van mreže ili uključite strimovanje.
</sr>
<sv-SE>
Ny översättning: Persiska Nya testamentet i Henry Martyns översättning (1876) — nu 33 översättningar på 29 språk. Ny inläsning: Webster-bibeln (1833) är nu helt inläst, och de övriga King James-böckerna har också fått inläsning. Ljudet sparas för offline-lyssning, eller slå på streaming.
</sv-SE>
<ta-IN>
புதிய மொழிபெயர்ப்பு: ஹென்றி மார்ட்டின் மொழிபெயர்த்த பாரசீக புதிய ஏற்பாடு (1876) — இப்போது 29 மொழிகளில் 33 மொழிபெயர்ப்புகள். புதிய ஒலிவாசிப்பு: வெப்ஸ்டர் விவிலியம் (1833) இப்போது முழுமையாக வாசிக்கப்படுகிறது; மற்ற கிங் ஜேம்ஸ் புத்தகங்களுக்கும் ஒலிவாசிப்பு சேர்க்கப்பட்டது. ஒலியை ஆஃப்லைனில் கேட்கச் சேமிக்கலாம் அல்லது ஸ்ட்ரீமிங்கை இயக்கவும்.
</ta-IN>
<zh-CN>
新增译本：亨利·马丁翻译的波斯语新约（1876年），现共33部译本、29种语言。新增朗读：韦伯斯特译本（1833年）现已全本朗读，钦定本其余各卷也已录制朗读。音频可保存供离线收听，也可开启流式播放。
</zh-CN>
<zh-HK>
新增譯本：亨利·馬丁翻譯的波斯語新約（1876年），現共33部譯本、29種語言。新增朗讀：韋伯斯特譯本（1833年）現已全本朗讀，欽定本其餘各卷亦已錄製朗讀。音訊可儲存供離線收聽，亦可開啟串流播放。
</zh-HK>
<zh-TW>
新增譯本：亨利·馬丁翻譯的波斯語新約（1876年），現共33部譯本、29種語言。新增朗讀：韋伯斯特譯本（1833年）現已全本朗讀，欽定本其餘各卷亦已錄製朗讀。音訊可儲存供離線收聽，亦可開啟串流播放。
</zh-TW>

*(Older release notes — 1.5.1 and earlier — are archived at the very end of this file to keep the current listing text near the top.)*

These predate the 30-locale copy-paste standard and are kept only for reference; they use the old EN/RU/DE-per-line form. Do not reformat or reuse — new releases follow the STANDARD section at the top of this file.

## 1.5.1 release notes (paste per store)

**RU:** Один новый перевод: белорусский Новый Завет и Псалтирь в переводе
Дзекуць-Малея и Луцкевіча (1931 год, классическая белорусская орфография,
«тарашкевица») — теперь 33 перевода на 28 языках. Белорусский язык также
добавлен в интерфейс — итого 25 языков интерфейса.

**EN:** One new translation: the Belarusian New Testament and Psalms
translated by Dzyakuts-Maley and Lutskevich (1931, classical Belarusian
orthography) — bringing the total to 33 translations in 28 languages.
Belarusian also joins the interface languages, for 25 languages total.

**DE:** Eine neue Übersetzung: das belarussische Neue Testament und die
Psalmen, übersetzt von Dzyakuts-Maley und Lutskevich (1931, klassische
belarussische Orthographie) — jetzt 33 Übersetzungen in 28 Sprachen.
Belarussisch ist außerdem als neue Oberflächensprache hinzugekommen,
insgesamt 25 Sprachen.

**ES:** Una nueva traducción: el Nuevo Testamento y los Salmos en bielorruso,
traducidos por Dzyakuts-Maley y Lutskevich (1931, ortografía bielorrusa
clásica) — ahora 33 traducciones en 28 idiomas. El bielorruso también se
suma como idioma de interfaz, para un total de 25.

**FR:** Une nouvelle traduction : le Nouveau Testament et les Psaumes en
biélorusse, traduits par Dzyakuts-Maley et Lutskevich (1931, orthographe
biélorusse classique) — portant le total à 33 traductions en 28 langues. Le
biélorusse rejoint aussi les langues d'interface, pour un total de 25.

**PT:** Uma nova tradução: o Novo Testamento e os Salmos em bielorrusso,
traduzidos por Dzyakuts-Maley e Lutskevich (1931, ortografia bielorrussa
clássica) — agora 33 traduções em 28 idiomas. O bielorrusso também passa a
ser um idioma de interface, totalizando 25.

**IT:** Una nuova traduzione: il Nuovo Testamento e i Salmi in bielorusso,
tradotti da Dzyakuts-Maley e Lutskevich (1931, ortografia bielorussa
classica) — ora 33 traduzioni in 28 lingue. Il bielorusso si aggiunge anche
alle lingue dell'interfaccia, per un totale di 25.

**SV:** En ny översättning: det vitryska Nya testamentet och Psaltaren,
översatt av Dzyakuts-Maley och Lutskevich (1931, klassisk vitrysk
ortografi) — nu 33 översättningar på 28 språk. Vitryska tillkommer även som
gränssnittsspråk, totalt 25 språk.

**DA:** En ny oversættelse: det hviderussiske Nye Testamente og Salmerne,
oversat af Dzyakuts-Maley og Lutskevich (1931, klassisk hviderussisk
retskrivning) — nu 33 oversættelser på 28 sprog. Hviderussisk kommer også
til som grænsefladesprog, i alt 25 sprog.

**JA:** 新しい翻訳を1件追加。ジャクーツ=マレイとルツケーヴィチによる
1931年のベラルーシ語新約聖書と詩篇（伝統的なベラルーシ語正書法）—
28言語・33の翻訳になりました。インターフェース言語にもベラルーシ語が
加わり、合計25言語になりました。

**ZH-CN:** 新增1部译本:由德亚库茨-马莱伊与卢茨凯维奇翻译的1931年白俄罗斯
语新约与诗篇(传统白俄罗斯语正字法)——现有28种语言、33部译本。界面语言
新增白俄罗斯语,总数达到25种。

**ZH-TW:** 新增1部譯本:由德亞庫茨-馬萊伊與盧茨凱維奇翻譯的1931年白俄羅斯
語新約與詩篇(傳統白俄羅斯語正字法)——現有28種語言、33部譯本。介面語言
新增白俄羅斯語,總數達到25種。

**TA:** ஒரு புதிய மொழிபெயர்ப்பு: ஜியாகுட்ஸ்-மாலி மற்றும் லுட்ஸ்கேவிச்
மொழிபெயர்த்த 1931 பெலாரூசிய புதிய ஏற்பாடு மற்றும் சங்கீதங்கள்
(பாரம்பரிய பெலாரூசிய எழுத்துமுறை) — இப்போது 28 மொழிகளில் 33
மொழிபெயர்ப்புகள். இடைமுகி மொழிகளிலும் பெலாரூசியன் சேர்க்கப்பட்டு,
மொத்தம் 25 மொழிகள் ஆகின்றன.

## 1.5.0 release notes (paste per store)

**RU:** Одиннадцать новых переводов: нидерландский Statenvertaling, арабский
Ван Дейк, английский Young's Literal Translation, новогреческий Вамвас,
финская Библия 1776 года, польская Гданьская Библия, сербский перевод
Караджича/Даничича (читают и боснийские, и хорватские пользователи),
венгерская Библия Кароли, чешская Кралицкая Библия, западноармянский Новый
Завет 1853 года и латышская Библия Глюка — теперь 32 перевода на 27 языках.
Интерфейс пополнился одиннадцатью языками (арабский, чешский, греческий,
иврит, венгерский, армянский, латышский, нидерландский, польский, сербский,
финский) — итого 24 языка интерфейса; для арабского и иврита добавлена
поддержка письма справа налево, включая перелистывание глав в правильном
направлении. Латышская Библия Глюка получила 12 из 13 второканонических
книг, а Елизаветинская церковнославянская Библия — обе ранее отсутствовавшие
книги (3-я Ездры и 3-я Маккавейская). Также восстановлены 137 надписаний
псалмов в тамильском переводе, утерянных при конвертации.

**EN:** Eleven new translations — Dutch (Statenvertaling), Arabic (Van
Dyck), English (Young's Literal Translation), Modern Greek (Vamvas), Finnish
(Biblia 1776), Polish (Gdańska), Serbian (Karadžić/Daničić, also read by
Bosnian and Croatian speakers), Hungarian (Károli), Czech (Kralická),
Western Armenian NT (1853), and Latvian (Glück) — bring the total to 32
translations in 27 languages. Eleven new interface languages (Arabic, Czech,
Greek, Hebrew, Hungarian, Armenian, Latvian, Dutch, Polish, Serbian,
Finnish) bring the UI to 24 languages total, with right-to-left support for
Arabic and Hebrew, including a fix so the chapter-swipe gesture follows the
reading direction. The Latvian Glück Bible gained 12 of its 13 Apocrypha
books, and the Church Slavonic Elizabeth Bible gained its two previously
missing books (2 Esdras and 3 Maccabees). Also: 137 psalm titles restored in
the Tamil translation that a converter had dropped.

**DE:** Elf neue Übersetzungen (Niederländisch, Arabisch, Englisch — Young's
Literal Translation, Neugriechisch, Finnisch, Polnisch, Serbisch,
Ungarisch, Tschechisch, Armenisch und Lettisch) erhöhen die Gesamtzahl auf
32 Übersetzungen in 27 Sprachen. Elf neue Oberflächensprachen (Arabisch,
Tschechisch, Griechisch, Hebräisch, Ungarisch, Armenisch, Lettisch,
Niederländisch, Polnisch, Serbisch, Finnisch) bringen die App-Sprache auf
insgesamt 24 Sprachen — mit Rechts-nach-links-Unterstützung für Arabisch
und Hebräisch, inklusive einer Korrektur, damit das Wischen zum
Kapitelwechsel der Leserichtung folgt. Die lettische Glück-Bibel erhielt 12
ihrer 13 Apokryphen-Bücher, die kirchenslawische Elisabeth-Bibel ihre beiden
zuvor fehlenden Bücher; außerdem wurden 137 verlorene Psalmüberschriften in
der tamilischen Übersetzung wiederhergestellt.

**ES:** Once traducciones nuevas (neerlandés, árabe, inglés — Young's
Literal Translation, griego moderno, finés, polaco, serbio, húngaro, checo,
armenio y letón) elevan el total a 32 traducciones en 27 idiomas. Once
idiomas nuevos de interfaz (árabe, checo, griego, hebreo, húngaro, armenio,
letón, neerlandés, polaco, serbio, finés) llevan la interfaz a 24 idiomas en
total, con soporte de derecha a izquierda para árabe y hebreo, incluida una
corrección para que el gesto de deslizar capítulos siga el sentido de
lectura. La Biblia letona de Glück recibió 12 de sus 13 libros apócrifos, y
la Biblia eslava eclesiástica de Isabel sus dos libros que faltaban; además
se restauraron 137 títulos de salmos perdidos en la traducción tamil.

**FR:** Onze nouvelles traductions (néerlandais, arabe, anglais — Young's
Literal Translation, grec moderne, finnois, polonais, serbe, hongrois,
tchèque, arménien et letton) portent le total à 32 traductions en 27
langues. Onze nouvelles langues d'interface (arabe, tchèque, grec, hébreu,
hongrois, arménien, letton, néerlandais, polonais, serbe, finnois) portent
l'interface à 24 langues au total, avec la prise en charge de l'écriture de
droite à gauche pour l'arabe et l'hébreu, y compris une correction du
balayage de chapitre pour suivre le sens de lecture. La Bible lettone de
Glück a reçu 12 de ses 13 livres apocryphes, et la Bible slavonne
d'Élisabeth ses deux livres manquants ; 137 titres de psaumes perdus ont
aussi été restaurés dans la traduction tamoule.

**PT:** Onze novas traduções (holandês, árabe, inglês — Young's Literal
Translation, grego moderno, finlandês, polonês, sérvio, húngaro, tcheco,
armênio e letão) elevam o total a 32 traduções em 27 idiomas. Onze novos
idiomas de interface (árabe, tcheco, grego, hebraico, húngaro, armênio,
letão, holandês, polonês, sérvio, finlandês) levam a interface a 24 idiomas
no total, com suporte da direita para a esquerda no árabe e no hebraico,
incluindo uma correção para que o gesto de deslizar capítulos siga o
sentido de leitura. A Bíblia letã de Glück recebeu 12 de seus 13 livros
apócrifos, e a Bíblia eslava eclesiástica de Isabel seus dois livros que
faltavam; também foram restaurados 137 títulos de salmos perdidos na
tradução tâmil.

**IT:** Undici nuove traduzioni (olandese, arabo, inglese — Young's Literal
Translation, greco moderno, finlandese, polacco, serbo, ungherese, ceco,
armeno e lettone) portano il totale a 32 traduzioni in 27 lingue. Undici
nuove lingue dell'interfaccia (arabo, ceco, greco, ebraico, ungherese,
armeno, lettone, olandese, polacco, serbo, finlandese) portano l'interfaccia
a 24 lingue totali, con supporto da destra a sinistra per arabo ed ebraico,
inclusa una correzione per far seguire allo scorrimento tra i capitoli il
verso di lettura. La Bibbia lettone di Glück ha ricevuto 12 dei suoi 13
libri apocrifi, e la Bibbia slava ecclesiastica di Elisabetta i suoi due
libri mancanti; sono stati inoltre ripristinati 137 titoli dei salmi perduti
nella traduzione tamil.

**SV:** Elva nya översättningar (nederländska, arabiska, engelska —
Young's Literal Translation, nygrekiska, finska, polska, serbiska,
ungerska, tjeckiska, armeniska och lettiska) höjer totalen till 32
översättningar på 27 språk. Elva nya gränssnittsspråk (arabiska, tjeckiska,
grekiska, hebreiska, ungerska, armeniska, lettiska, nederländska, polska,
serbiska, finska) tar gränssnittet till 24 språk totalt, med stöd för
höger-till-vänster-skrift för arabiska och hebreiska, inklusive en fix så
att kapitelbyte med svep följer läsriktningen. Den lettiska Glück-bibeln
fick 12 av sina 13 apokryfiska böcker, och den kyrkoslaviska
Elisabetbibeln sina två saknade böcker; dessutom återställdes 137 förlorade
psalmrubriker i den tamilska översättningen.

**DA:** Elleve nye oversættelser (hollandsk, arabisk, engelsk — Young's
Literal Translation, nygræsk, finsk, polsk, serbisk, ungarsk, tjekkisk,
armensk og lettisk) bringer totalen op på 32 oversættelser på 27 sprog.
Elleve nye sprog i brugerfladen (arabisk, tjekkisk, græsk, hebraisk,
ungarsk, armensk, lettisk, hollandsk, polsk, serbisk, finsk) bringer
brugerfladen op på i alt 24 sprog, med understøttelse af
højre-til-venstre-skrift for arabisk og hebraisk, inklusive en rettelse så
kapitelswipe følger læseretningen. Den lettiske Glück-bibel fik 12 af sine
13 apokryfe bøger, og den kirkeslaviske Elisabeth-bibel sine to manglende
bøger; desuden blev 137 mistede salmeoverskrifter genskabt i den tamilske
oversættelse.

**JA:** 新しい翻訳を11件追加（オランダ語のスターテン訳、アラビア語のヴァ
ンダイク訳、英語のYoung's Literal Translation、現代ギリシャ語のヴァンヴァ
ス訳、フィンランド語の1776年訳、ポーランド語のグダニスク聖書、セルビア語
のカラジッチ/ダニチッチ訳、ハンガリー語のカーロリ訳、チェコ語のクラリツ
ェ聖書、1853年の西アルメニア語新約聖書、ラトビア語のグリュック聖書）—
27言語・32の翻訳になりました。インターフェース言語も11言語追加（アラビ
ア語、チェコ語、ギリシャ語、ヘブライ語、ハンガリー語、アルメニア語、ラト
ビア語、オランダ語、ポーランド語、セルビア語、フィンランド語）され、合計
24言語に。アラビア語・ヘブライ語では右から左に読む表示に対応し、章送り
のスワイプ操作も読む方向に合わせて修正しました。ラトビア語グリュック聖書
に外典13巻中12巻を追加、教会スラヴ語エリザベス聖書には欠けていた2巻（エ
ズラ記第二・マカバイ記第三）を追加。タミル語訳では失われていた詩篇の表題
137件も復元しました。

**ZH-CN:** 新增11部译本（荷兰语司泰顿译本、阿拉伯语范戴克译本、英语
Young's Literal Translation、现代希腊语瓦姆瓦斯译本、芬兰语1776年圣经、
波兰语格但斯克圣经、塞尔维亚语卡拉季奇/达尼契奇译本、匈牙利语卡罗利译
本、捷克语克拉利采圣经、1853年西亚美尼亚语新约、拉脱维亚语格吕克圣经）
——现有27种语言、32部译本。界面新增11种语言（阿拉伯语、捷克语、希腊语、
希伯来语、匈牙利语、亚美尼亚语、拉脱维亚语、荷兰语、波兰语、塞尔维亚语、
芬兰语），界面语言总数达到24种；阿拉伯语和希伯来语现已支持从右到左显示，
章节滑动手势也已按阅读方向修正。拉脱维亚语格吕克圣经新增13卷次经中的12
卷，教会斯拉夫语伊丽莎白圣经补全了此前缺失的两卷（以斯拉记下、马加比三
书）；泰米尔语译本中丢失的137个诗篇标题也已恢复。

**ZH-TW:** 新增11部譯本（荷蘭語司泰頓譯本、阿拉伯語范戴克譯本、英語
Young's Literal Translation、現代希臘語瓦姆瓦斯譯本、芬蘭語1776年聖經、
波蘭語格但斯克聖經、塞爾維亞語卡拉季奇/達尼契奇譯本、匈牙利語卡羅利譯
本、捷克語克拉利采聖經、1853年西亞美尼亞語新約、拉脫維亞語格呂克聖經）
——現有27種語言、32部譯本。介面新增11種語言（阿拉伯語、捷克語、希臘語、
希伯來語、匈牙利語、亞美尼亞語、拉脫維亞語、荷蘭語、波蘭語、塞爾維亞語、
芬蘭語），介面語言總數達到24種；阿拉伯語和希伯來語現已支援從右到左顯示，
章節滑動手勢也已依閱讀方向修正。拉脫維亞語格呂克聖經新增13卷次經中的12
卷，教會斯拉夫語伊麗莎白聖經補全了先前缺失的兩卷（以斯拉記下、馬加比三
書）；泰米爾語譯本中遺失的137個詩篇標題也已恢復。

**TA:** 11 புதிய மொழிபெயர்ப்புகள் (டச்சு Statenvertaling, அரபு Van Dyck,
ஆங்கிலம் Young's Literal Translation, நவீன கிரேக்கம் Vamvas, பின்னிஷ்
Biblia 1776, போலிஷ் Gdańska, செர்பியன் Karadžić/Daničić, ஹங்கேரியன்
Károli, செக் Kralická, 1853 மேற்கு அர்மேனிய புதிய ஏற்பாடு, லாட்வியன் Glück)
சேர்க்கப்பட்டு — இப்போது 27 மொழிகளில் 32 மொழிபெயர்ப்புகள். இடைமுகத்திலும்
11 புதிய மொழிகள் (அரபு, செக், கிரேக்கம், ஹீப்ரு, ஹங்கேரியன், அர்மேனியன்,
லாட்வியன், டச்சு, போலிஷ், செர்பியன், பின்னிஷ்) சேர்க்கப்பட்டு மொத்தம் 24
இடைமுகி மொழிகள் ஆகின்றன; அரபு மற்றும் ஹீப்ருவிற்கு வலமிருந்து இடமாகப்
படிக்கும் திசைக்கு ஏற்ப காட்சியும் அத்தியாய ஸ்வைப் திசையும்
திருத்தப்பட்டன. தமிழ் மொழிபெயர்ப்பில் மாற்றியமைப்பின்போது இழந்த 137
சங்கீத தலைப்புகள் மீட்டெடுக்கப்பட்டன; லாட்வியன் க்ளூக் பைபிளுக்கு
அபோக்ரிபாவின் 13 புத்தகங்களில் 12 சேர்க்கப்பட்டன, மேலும் சர்ச் ஸ்லாவோனிக்
எலிசபெத் பைபிளில் விடுபட்டிருந்த இரு புத்தகங்களும் (2 எஸ்றா, 3 மக்கபேயர்)
சேர்க்கப்பட்டன.

## 1.4.3 release notes (paste per store; 1.4.2 was never uploaded — these notes fold its changes in)

**RU:** Два новых перевода: полная тамильская Библия (IRV 2019) и
латинская Вульгата (Климентина, 1592) с второканоническими книгами —
22 перевода на 17 языках. Подстрочник заговорил по-русски:
грамматический разбор каждого греческого и еврейского слова — на
языке приложения. Заметки и выделения остаются на своём стихе при
смене перевода (старые пометки в Псалтири могли сместиться —
выделите заново). Интерфейс на тамильском.

**EN:** Two new translations: the complete Tamil Bible (IRV 2019) and
the Latin Vulgate (Clementine, 1592) with the Deuterocanon — 22
translations in 17 languages. The interlinear now speaks your
language: the grammar of every Greek and Hebrew word appears in the
app language. Notes and highlights stay on the right verse when you
switch translations. Tamil UI added.

**DE:** Zwei neue Übersetzungen: die vollständige tamilische Bibel
(IRV 2019) und die lateinische Vulgata (Clementina, 1592) mit
Deuterokanon — 22 Übersetzungen in 17 Sprachen. Die Interlinearansicht
spricht jetzt Deutsch: Die Grammatik jedes griechischen und
hebräischen Wortes erscheint in der App-Sprache. Notizen und
Markierungen bleiben beim Übersetzungswechsel am richtigen Vers.

**ES:** Dos traducciones nuevas: la Biblia tamil completa (IRV 2019) y
la Vulgata latina (Clementina, 1592) con los deuterocanónicos — 22
traducciones en 17 idiomas. La interlineal ahora habla español: la
gramática de cada palabra griega y hebrea se muestra en el idioma de
la aplicación. Las notas y los resaltados permanecen en el versículo
correcto al cambiar de traducción.

**FR:** Deux nouvelles traductions : la Bible tamoule complète (IRV
2019) et la Vulgate latine (Clémentine, 1592) avec les
deutérocanoniques — 22 traductions en 17 langues. L'interlinéaire
parle désormais français : la grammaire de chaque mot grec et hébreu
s'affiche dans la langue de l'application. Les notes et surlignages
restent sur le bon verset lors d'un changement de traduction.

**PT:** Duas novas traduções: a Bíblia tâmil completa (IRV 2019) e a
Vulgata latina (Clementina, 1592) com os deuterocanônicos — 22
traduções em 17 idiomas. A interlinear agora fala português: a
gramática de cada palavra grega e hebraica aparece no idioma do
aplicativo. As notas e os destaques permanecem no versículo certo ao
trocar de tradução.

**IT:** Due nuove traduzioni: la Bibbia tamil completa (IRV 2019) e la
Vulgata latina (Clementina, 1592) con i deuterocanonici — 22
traduzioni in 17 lingue. L'interlineare ora parla italiano: la
grammatica di ogni parola greca ed ebraica appare nella lingua
dell'app. Note ed evidenziazioni restano sul versetto giusto quando si
cambia traduzione.

**SV:** Två nya översättningar: hela tamilska Bibeln (IRV 2019) och
latinska Vulgata (Clementina, 1592) med apokryferna — 22
översättningar på 17 språk. Interlinjären talar nu svenska:
grammatiken för varje grekiskt och hebreiskt ord visas på appens
språk. Anteckningar och markeringar stannar på rätt vers när du byter
översättning.

**DA:** To nye oversættelser: hele den tamilske Bibel (IRV 2019) og
den latinske Vulgata (Clementina, 1592) med apokryferne — 22
oversættelser på 17 sprog. Interlineæren taler nu dansk: grammatikken
for hvert græsk og hebraisk ord vises på appens sprog. Noter og
fremhævninger bliver på det rigtige vers, når du skifter oversættelse.

**JA:** 新しい翻訳を2つ追加：タミル語聖書全巻（IRV 2019）と第二正典付き
ラテン語ウルガタ（クレメンティナ、1592年）— 17言語・22の翻訳に。イン
ターリニアが日本語に対応：ギリシャ語・ヘブライ語の各単語の文法解析が
アプリの言語で表示されます。翻訳を切り替えても、メモとハイライトが正
しい節に残ります。

**ZH-CN:** 新增两部译本：泰米尔语圣经全书（IRV 2019）和含次经的拉丁语
武加大译本（克莱门汀，1592年）——现有17种语言、22部译本。逐字对照现在
说中文：每个希腊文和希伯来文单词的语法分析以应用语言显示。切换译本时，
笔记和高亮停留在正确的经节上。

**ZH-TW:** 新增兩部譯本：泰米爾語聖經全書（IRV 2019）和含次經的拉丁語
武加大譯本（克萊門汀，1592年）——現有17種語言、22部譯本。逐字對照現在
說中文：每個希臘文和希伯來文單詞的語法分析以應用程式語言顯示。切換譯
本時，筆記和螢光標記停留在正確的經節上。

**TA:** முழுத் தமிழ் வேதாகமம் (IRV 2019) இப்போது ஹெக்ஸாப்லாவில் —
தமிழ் இடைமுகத்துடன்! மேலும் லத்தீன் வுல்காத்தா (1592) — 17 மொழிகளில்
22 மொழிபெயர்ப்புகள். கிரேக்க/எபிரெய வார்த்தைகளின் இலக்கண விளக்கம்
தமிழிலேயே. மொழிபெயர்ப்பை மாற்றினாலும் குறிப்புகளும் வண்ணக்
குறியீடுகளும் சரியான வசனத்திலேயே இருக்கும்.

## 1.4.2 release notes (paste per store; Play has all 10 listing languages — use the matching line)

**RU:** Подстрочник заговорил по-русски: грамматический разбор каждого
греческого и еврейского слова теперь на языке приложения. Заметки и
выделения остаются на своём стихе при смене перевода (старые пометки
в Псалтири могли сместиться на стих — просто выделите заново).
Закладки в списке упорядочены точно по тексту.

**EN:** The interlinear now speaks your language: the grammar of every
Greek and Hebrew word appears in the app language. Notes and highlights
now stay on the right verse when you switch translations. Bookmarks
list in true verse order.

**DE:** Die Interlinearansicht spricht jetzt Deutsch: Die Grammatik
jedes griechischen und hebräischen Wortes erscheint in der App-Sprache.
Notizen und Markierungen bleiben beim Übersetzungswechsel jetzt am
richtigen Vers. Lesezeichen erscheinen in echter Versreihenfolge.

**ES:** La interlineal ahora habla español: la gramática de cada
palabra griega y hebrea se muestra en el idioma de la aplicación. Las
notas y los resaltados ahora permanecen en el versículo correcto al
cambiar de traducción. Los marcadores se ordenan por su lugar real.

**FR:** L'interlinéaire parle désormais français : la grammaire de
chaque mot grec et hébreu s'affiche dans la langue de l'application.
Les notes et les surlignages restent désormais sur le bon verset lors
d'un changement de traduction. Les signets suivent l'ordre réel des
versets.

**PT:** A interlinear agora fala português: a gramática de cada palavra
grega e hebraica aparece no idioma do aplicativo. As notas e os
destaques agora permanecem no versículo certo ao trocar de tradução.
Os marcadores seguem a ordem real dos versículos.

**IT:** L'interlineare ora parla italiano: la grammatica di ogni parola
greca ed ebraica appare nella lingua dell'app. Note ed evidenziazioni
ora restano sul versetto giusto quando si cambia traduzione. I
segnalibri seguono l'ordine reale dei versetti.

**SV:** Interlinjären talar nu svenska: grammatiken för varje grekiskt
och hebreiskt ord visas på appens språk. Anteckningar och markeringar
stannar nu på rätt vers när du byter översättning. Bokmärken listas i
äkta versordning.

**DA:** Interlineæren taler nu dansk: grammatikken for hvert græsk og
hebraisk ord vises på appens sprog. Noter og fremhævninger bliver nu
på det rigtige vers, når du skifter oversættelse. Bogmærker vises i
ægte versrækkefølge.

**JA:** インターリニアが日本語に対応：ギリシャ語・ヘブライ語の各単語の
文法解析がアプリの言語で表示されます。翻訳を切り替えても、メモとハイ
ライトが正しい節に残るようになりました。しおりは正確な節順に並びます。

**ZH-CN:** 逐字对照现在说中文：每个希腊文和希伯来文单词的语法分析以
应用语言显示。切换译本时，笔记和高亮现在会停留在正确的经节上。书签
按真实经节顺序排列。

**ZH-TW:** 逐字對照現在說中文：每個希臘文和希伯來文單詞的語法分析以
應用程式語言顯示。切換譯本時，筆記和螢光標記現在會停留在正確的經節
上。書籤按真實經節順序排列。

## 1.4.1 release notes (paste per store)

**RU:** Новое: санскритский Новый Завет 1851 года (20-й перевод);
интерфейс на 12 языках (добавлены pt/it/sv/da/ja/zh); восстановлены
пропущенные стихи в KJV (Мф 2:16 и др.); исправлены шведский и
датский тексты; завершён Тиндейл (33 книги); точное постишное
сопоставление переводов в параллельном режиме; экран приветствия
открывает Евангелие от Иоанна; исправления ошибок.

**EN:** New: the Sanskrit New Testament of 1851 (20th translation);
UI in 12 languages (pt/it/sv/da/ja/zh added); missing KJV verses
restored (Mt 2:16 et al.); Swedish and Danish texts repaired;
Tyndale completed (33 books); precise verse-by-verse alignment in
split view; welcome screen opens the Gospel of John; bug fixes.

---
