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

## 1.6.0 release notes (paste per store)

**EN:** One new translation: the Persian New Testament in Henry Martyn's
translation (1876) — the first Bible transcribed by the project's own team,
bringing the total to 34 translations in 29 languages. New narration:
Webster's Bible (1833) is now fully read aloud, and the remaining King
James books gain clear narration, so every English chapter has a voice.

**RU:** Один новый перевод: персидский Новый Завет в переводе Генри
Мартина (1876) — первая Библия, расшифрованная командой проекта. Теперь
34 перевода на 29 языках. Новая озвучка: Библия Уэбстера (1833) полностью
озвучена, добавлена озвучка оставшихся книг Библии короля Якова — теперь
у каждой английской главы есть голос.

**DE:** Eine neue Übersetzung: das persische Neue Testament in der
Übersetzung von Henry Martyn (1876) — jetzt 34 Übersetzungen in 29
Sprachen. Neue Audioausgabe: die Webster-Bibel (1833) wird vollständig
vorgelesen, und die übrigen King-James-Bücher erhalten ebenfalls eine
klare Vertonung.

(ES/FR/PT and the other listing languages: same two facts — +Persian
Martyn NT 1876 → 34/29, and full Webster + remaining-KJV narration.
Translate from the EN above per prior-release pattern.)

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

## Русский (primary for RuStore)

**Название:** Гексапла — параллельная Библия

**Краткое описание (до 80 зн.):**
Библия офлайн: 34 перевода, озвучка, планы чтения, симфония Стронга.

**Полное описание:**

Гексапла — полная Библия без интернета, без рекламы, без регистрации и без сбора данных. Всё бесплатно и ничего не заблокировано.

📖 34 классических перевода на 29 языках: Синодальный, Елизаветинская Библия (церковнославянский), KJV 1611 с апокрифами, Библия Уэбстера 1833, Женевская 1599, Уиклиф, Тиндейл, Bible Martin 1744 (франц.), Библия Лютера 1545 (нем.), Карла XII 1703 (швед.), датская 1819, Рейна-Валера 1909 (исп.), Диодати 1649 (итал.), Bíblia Livre — Алмейда TR (порт.), 明治元訳 — первая японская Библия 1880/87, китайская 和合本 1919 (трад. и упрощ. иероглифы), древнееврейский текст (Ленинградский кодекс), греческий Новый Завет (византийский текст), санскритский Новый Завет 1851 года, тамильская Библия (IRV 2019, линия Бауэра 1871), латинская Вульгата (Климентина, 1592), нидерландская Statenvertaling 1637 года, арабская Библия Ван Дейка 1865 года и персидский Новый Завет в переводе Генри Мартина 1876 года — и другие.

✝️ «Благая весть» — план спасения шаг за шагом, только стихи Писания.
🔴 Слова Христа выделены красным.
🎧 Озвучка: живое чтение (LibriVox) и синтез речи с подсветкой стиха и слова, фоновое воспроизведение, таймер сна, скорость.
📚 Номера Стронга с еврейско-греческим словарём; словарь Уэбстера 1828 — значение любого слова английских переводов по касанию.
🔀 Параллельное чтение двух переводов стих в стих и сравнение стиха во всех переводах.
📜 Подстрочник оригинала: коснитесь слова в греческом или еврейском тексте — номер Стронга и полный грамматический разбор.
📅 Планы чтения: Библия за год, хронологический план (вся Библия в порядке событий), НЗ за 90 дней, Евангелия за 30 дней, Притчи, Псалтирь — с прогрессом и серией дней.
🔍 Поиск без учёта диакритики, по всем переводам.
✏️ Закладки, заметки, цветные выделения, перекрёстные ссылки, резервное копирование.
🖼 Стих дня на виджете и в напоминании; классические гравюры Доре и Шнорра.

Все тексты — общественное достояние. Приложение не собирает никаких данных.

---

## English

**Title:** Hexapla — Parallel Bible

**Short description:**
Offline Bible: 34 classic translations, audio, Strong's, reading plans.

**Full description:**

Hexapla is the complete Bible — offline, ad-free, account-free, and it collects no data. Everything is free and nothing is locked.

📖 34 classic translations across 29 languages: KJV 1611 with Apocrypha, Webster 1833, Geneva 1599, Wycliffe, Tyndale, Bible Martin 1744 (French), Luther 1545 (German), Karl XII 1703 (Swedish), Danish 1819/1871, Reina-Valera 1909 (Spanish), Diodati 1649 (Italian), Bíblia Livre — Almeida TR (Portuguese), 明治元訳 Meiji Motoyaku — the first Japanese Bible 1880/87, the Chinese Union Version 和合本 1919 (Traditional and Simplified), Russian Synodal, Church Slavonic, the Hebrew Tanakh (Leningrad Codex), the Greek New Testament (Byzantine Text), the Sanskrit New Testament of 1851, the Tamil Bible (IRV 2019, the 1871 Bower lineage), the Clementine Vulgate of 1592 (Latin), the Dutch Statenvertaling (1637), the Arabic Van Dyck (1865), and the Persian New Testament in Henry Martyn's translation (1876), and more.

✝️ The Good News — God's plan of salvation, step by step, Scripture only.
🔴 Words of Christ in red.
🎧 Audio: human narration (LibriVox) and text-to-speech with verse and word highlighting, background playback, sleep timer, speed control.
📚 Strong's numbers with the full Hebrew/Greek lexicon; Webster's 1828 dictionary — tap any word in the English translations.
🔀 Read two translations side by side, verse-locked, or compare a verse across all translations.
📜 Original-language interlinear: tap a word in the Greek or Hebrew text for its Strong's number and full grammatical parsing.
📅 Reading plans — Bible in a year, chronological year plan (the whole Bible in event order), NT in 90 days, Gospels in 30, Proverbs, Psalms — with progress and streaks.
🔍 Diacritic-insensitive search across all translations.
✏️ Bookmarks, notes, colored highlights, cross-references, backup and restore.
🖼 Verse of the day widget and reminder; classic Doré and Schnorr engravings.

All texts are public domain. The app collects nothing.

---

## Français

**Titre :** Hexapla — Bible parallèle

**Description courte :**
Bible hors ligne : 33 traductions classiques, audio, plans de lecture.

**Description complète :**

Hexapla, c'est la Bible complète — hors ligne, sans publicité, sans compte, sans collecte de données. Tout est gratuit, rien n'est verrouillé.

📖 33 traductions classiques en 28 langues, dont la Bible Martin 1744, la KJV 1611, l'hébreu et le grec originaux. ✝️ La Bonne Nouvelle : le plan du salut, étape par étape, uniquement l'Écriture. 🔴 Paroles du Christ en rouge. 🎧 Lecture audio avec surlignage des versets. 📚 Numéros Strong avec lexique ; interlinéaire grec/hébreu (analyse grammaticale au toucher) ; dictionnaire Webster 1828 pour les traductions anglaises. 📅 Plans de lecture avec progression. ✏️ Signets, notes, surlignages, sauvegarde.

Tous les textes sont dans le domaine public. L'application ne collecte rien.

---

## Deutsch

**Titel:** Hexapla — Parallelbibel

**Kurzbeschreibung:**
Bibel offline: 33 klassische Übersetzungen, Audio, Lesepläne, Strong.

**Vollständige Beschreibung:**

Hexapla ist die vollständige Bibel — offline, werbefrei, ohne Konto, ohne Datensammlung. Alles kostenlos, nichts gesperrt.

📖 33 klassische Übersetzungen in 28 Sprachen, darunter die Lutherbibel 1545, die KJV 1611 sowie Hebräisch und Griechisch im Original. ✝️ Die Gute Nachricht: Gottes Heilsplan Schritt für Schritt, nur Schrift. 🔴 Worte Christi in Rot. 🎧 Audiowiedergabe mit Vershervorhebung. 📚 Strong-Nummern mit Lexikon; Interlinear für Griechisch/Hebräisch (grammatische Analyse per Tipp); Websters Wörterbuch 1828 für die englischen Übersetzungen. 📅 Lesepläne mit Fortschritt. ✏️ Lesezeichen, Notizen, Markierungen, Sicherung.

Alle Texte sind gemeinfrei. Die App sammelt keine Daten.

---

## Español

**Título:** Hexapla — Biblia paralela

**Descripción corta:**
Biblia sin conexión: 33 traducciones clásicas, audio, planes de lectura.

**Descripción completa:**

Hexapla es la Biblia completa — sin conexión, sin anuncios, sin cuentas y sin recopilar datos. Todo es gratis y nada está bloqueado.

📖 33 traducciones clásicas en 28 idiomas, incluida la Reina-Valera 1909, la KJV 1611 y los originales hebreo y griego. ✝️ Las Buenas Nuevas: el plan de salvación de Dios paso a paso, solo Escritura. 🔴 Palabras de Cristo en rojo. 🎧 Audio con resaltado de versículos. 📚 Números Strong con léxico; interlineal griego/hebreo (análisis gramatical al tocar); diccionario Webster 1828 para las traducciones inglesas. 📅 Planes de lectura con progreso. ✏️ Marcadores, notas, resaltados, copia de seguridad.

Todos los textos son de dominio público. La aplicación no recopila nada.


---

## Additional Play listing languages (added 2026-07-11; paste under Store listings → Manage translations)

### English (India) — en-IN (ADD ON PLAY PRODUCTION DAY, not before)

**Title:** Hexapla — Parallel Bible

**Short description (≤80):**
Offline Bible: 33 classic translations incl. Tamil, Latin and the Sanskrit NT, audio, Strong's.

**Full description:**

Hexapla is the complete Bible — offline, ad-free, account-free, and it collects no data. Everything is free and nothing is locked.

📖 33 classic translations across 28 languages — including the **complete Tamil Bible** (IRV 2019, the TR-faithful 1871 Bower lineage), the **Sanskrit New Testament of 1851** (सत्यवेदः, Calcutta Baptist Mission, Devanagari), the Hebrew Tanakh (Leningrad Codex), the Greek New Testament (Byzantine Text), the KJV 1611 with Apocrypha, Geneva 1599, Wycliffe, Tyndale, Luther 1545, and more.
✝️ The Good News — God's plan of salvation, step by step, Scripture only.
🔴 Words of Christ in red.
🎧 Audio: human narration (LibriVox) and text-to-speech with verse highlighting, background playback, sleep timer.
📚 Strong's numbers with the full Hebrew/Greek lexicon; original-language interlinear — tap any Greek or Hebrew word for its parsing.
🔀 Read two translations side by side, verse-locked, or compare a verse across all translations.
📅 Reading plans with progress. 🔍 Search across all translations. ✏️ Bookmarks, notes, highlights, backup.

All texts are public domain. The app collects nothing.

### தமிழ் — ta-IN (ADD TOGETHER WITH THE TAMIL RELEASE, lead with screenshot_reader_ta.png + feature_1024x500_ta.png)

**Title:** Hexapla — இணை வேதாகமம்

**Short description (≤80):**
வேதாகமம் ஆஃப்லைன்: 33 மொழிபெயர்ப்புகள், ஒலி, திட்டங்கள், ஸ்ட்ராங்.

**Full description:**

ஹெக்ஸாப்லா — முழு வேதாகமம்: இணையம் தேவையில்லை, விளம்பரம் இல்லை, பதிவு இல்லை, தரவு சேகரிப்பு இல்லை. எல்லாம் இலவசம், எதுவும் பூட்டப்படவில்லை.

📖 28 மொழிகளில் 33 பாரம்பரிய மொழிபெயர்ப்புகள் — முழு தமிழ் வேதாகமம் (IRV 2019, 1871 பவர்/யூனியன் பாரம்பரியம்), எபிரெய தனக் (லெனின்கிராட் கோடெக்ஸ்), கிரேக்கப் புதிய ஏற்பாடு (பைசந்திய உரை), KJV 1611 (அப்போக்கிரிபாவுடன்), ஜெனீவா 1599, லூத்தர் 1545, சமஸ்கிருதப் புதிய ஏற்பாடு 1851 மற்றும் பல.
✝️ நற்செய்தி — தேவனுடைய இரட்சிப்பின் திட்டம், படிப்படியாக, வேத வசனங்களே.
🔴 கிறிஸ்துவின் வார்த்தைகள் சிவப்பில்.
🎧 ஒலி: மனிதக் குரல் வாசிப்பு (LibriVox) மற்றும் பேச்சு மாற்றம் வசன ஒளிர்வுடன்; பின்னணி இயக்கம், தூக்க டைமர்.
📚 ஸ்ட்ராங் எண்கள் முழு எபிரெய/கிரேக்க அகராதியுடன்; மூல மொழி இடைவரி — எந்தக் கிரேக்க அல்லது எபிரெய வார்த்தையையும் தொட்டால் முழு இலக்கண விளக்கம், தமிழிலேயே.
🔀 இரண்டு மொழிபெயர்ப்புகளை அருகருகே வசனத்துக்கு வசனம் வாசியுங்கள்; அல்லது ஒரு வசனத்தை எல்லா மொழிபெயர்ப்புகளிலும் ஒப்பிடுங்கள்.
📅 முன்னேற்றத்துடன் வாசிப்புத் திட்டங்கள். 🔍 எல்லா மொழிபெயர்ப்புகளிலும் தேடல். ✏️ அடையாளக்குறிகள், குறிப்புகள், வண்ணக் குறியீடுகள், காப்புப்பிரதி.

எல்லா உரைகளும் பொதுக் களம் (public domain). ஆப் எந்தத் தரவையும் சேகரிப்பதில்லை.

### Português (pt-BR, reuse for pt-PT)

**Título:** Hexapla — Bíblia Paralela

**Descrição curta (≤80):**
Bíblia offline: 33 traduções clássicas, áudio, planos de leitura, Strong.

**Descrição completa:**

Hexapla — a Bíblia completa sem internet, sem anúncios, sem cadastro e sem coleta de dados. Tudo gratuito, nada bloqueado.

📖 33 traduções clássicas em 28 idiomas: Almeida (Bíblia Livre, Textus Receptus), KJV 1611 com apócrifos, Webster 1833, Genebra 1599, Diodati 1649, Reina-Valera 1909, Lutero 1545, Martin 1744, Carlos XII 1703 (sueca), dinamarquesa 1819, Sinodal russa, eslavo eclesiástico, 明治元訳 japonesa, 和合本 chinesa, e os originais em hebraico e grego.
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

### Italiano (it-IT)

**Titolo:** Hexapla — Bibbia parallela

**Descrizione breve (≤80):**
Bibbia offline: 33 traduzioni classiche, audio, piani di lettura, Strong.

**Descrizione completa:**

Hexapla — la Bibbia completa senza internet, senza pubblicità, senza registrazione e senza raccolta dati. Tutto gratuito, niente bloccato.

📖 33 traduzioni classiche in 28 lingue: Diodati 1649/1885, KJV 1611 con apocrifi, Webster 1833, Ginevra 1599, Reina-Valera 1909, Almeida TR, Lutero 1545, Martin 1744, Carlo XII 1703, danese 1819, Sinodale russa, slavo ecclesiastico, 明治元訳 giapponese, 和合本 cinese, e gli originali ebraico e greco.
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

### Svenska (sv-SE)

**Titel:** Hexapla — Parallellbibel

**Kort beskrivning (≤80):**
Bibeln offline: 33 klassiska översättningar, ljud, läsplaner, Strong.

**Fullständig beskrivning:**

Hexapla — hela Bibeln utan internet, utan reklam, utan konto och utan datainsamling. Allt gratis, inget låst.

📖 33 klassiska översättningar på 28 språk: Karl XII:s Bibel 1703, KJV 1611 med apokryfer, Webster 1833, Genève 1599, Diodati 1649, Reina-Valera 1909, Luther 1545, Martin 1744, danska 1819, ryska synodala, kyrkoslaviska, japanska 明治元訳, kinesiska 和合本 samt hebreiska och grekiska grundtexterna.
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

### Dansk (da-DK)

**Titel:** Hexapla — Parallelbibel

**Kort beskrivelse (≤80):**
Bibelen offline: 33 klassiske oversættelser, lyd, læseplaner, Strong.

**Fuld beskrivelse:**

Hexapla — hele Bibelen uden internet, uden reklamer, uden konto og uden dataindsamling. Alt er gratis, intet er låst.

📖 33 klassiske oversættelser på 28 sprog: Dansk Bibel 1819, KJV 1611 med apokryfer, Webster 1833, Genève 1599, Diodati 1649, Reina-Valera 1909, Luther 1545, Martin 1744, Karl XII 1703, russisk synodal, kirkeslavisk, japansk 明治元訳, kinesisk 和合本 samt de hebraiske og græske grundtekster.
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

### 日本語 (ja-JP)

**タイトル:** Hexapla — 対照聖書

**簡単な説明 (≤80):**
オフライン聖書：古典訳33種・音声・通読計画・ストロング番号・原語対訳。

**詳細な説明:**

Hexapla（ヘクサプラ）— インターネット不要、広告なし、登録不要、データ収集なしの聖書アプリ。すべて無料、制限はありません。

📖 28言語・33の古典訳：明治元訳（1880/87年、日本初の聖書）、欽定訳 KJV 1611（外典付き）、ウェブスター訳1833、ジュネーブ聖書1599、ディオダティ訳1649、レイナ・バレラ訳1909、ルター訳1545、中国語和合本1919（繁体・簡体）、ロシア語会堂訳ほか、ヘブライ語・ギリシア語原典も収録。
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

### 简体中文 (zh-CN)

**标题:** Hexapla — 对照圣经

**简短说明 (≤80):**
离线圣经：33部经典译本，语音朗读，读经计划，斯特朗编号，原文对照。

**完整说明:**

Hexapla（六栏经）— 完整圣经，无需联网，无广告，无需注册，不收集任何数据。完全免费，没有任何限制。

📖 28种语言、33部经典译本：和合本1919（简体与繁体）、英文钦定本 KJV 1611（含次经）、韦伯斯特1833、日内瓦1599、意大利迪奥达蒂1649、西班牙雷纳-瓦莱拉1909、德文路德1545、日文明治元译，以及希伯来文与希腊文原文。
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

### 繁體中文 (zh-TW)

**標題:** Hexapla — 對照聖經

**簡短說明 (≤80):**
離線聖經：33部經典譯本，語音朗讀，讀經計畫，史特朗編號，原文對照。

**完整說明:**

Hexapla（六欄經）— 完整聖經，無需連網，無廣告，無需註冊，不收集任何資料。完全免費，沒有任何限制。

📖 28種語言、33部經典譯本：和合本1919（繁體與簡體）、英文欽定本 KJV 1611（含次經）、韋伯斯特1833、日內瓦1599、義大利迪奧達蒂1649、西班牙雷納-瓦萊拉1909、德文路德1545、日文明治元譯，以及希伯來文與希臘文原文。
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

### Português de Portugal (pt-PT; também Angola/Moçambique)

**Título:** Hexapla — Bíblia Paralela

**Descrição curta (≤80):**
Bíblia offline: 33 traduções clássicas, áudio, planos de leitura, Strong.

**Descrição completa:**

Hexapla — a Bíblia completa sem internet, sem anúncios, sem registo e sem recolha de dados. Tudo gratuito, nada bloqueado.

📖 33 traduções clássicas em 28 idiomas: Almeida (Bíblia Livre, Textus Receptus), KJV 1611 com apócrifos, Webster 1833, Genebra 1599, Diodati 1649, Reina-Valera 1909, Lutero 1545, Martin 1744, Carlos XII 1703 (sueca), dinamarquesa 1819, Sinodal russa, eslavo eclesiástico, 明治元訳 japonesa, 和合本 chinesa, e os originais em hebraico e grego.
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

### 繁體中文（香港）(zh-HK; 澳門亦適用)

**標題:** Hexapla — 對照聖經

**簡短說明 (≤80):**
離線聖經：33部經典譯本，語音朗讀，讀經計劃，史特朗編號，原文對照。

**完整說明:**

Hexapla（六欄經）— 完整聖經，無需連網，無廣告，無需註冊，不收集任何資料。完全免費，沒有任何限制。

📖 28種語言、33部經典譯本：和合本1919（繁體與簡體）、英文欽定本 KJV 1611（含次經）、韋伯斯特1833、日內瓦1599、義大利迪奧達蒂1649、西班牙雷納-瓦萊拉1909、德文路德1545、日文明治元譯，以及希伯來文與希臘文原文。
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

## Missing-listing gap: 11 shipped translations with no Play listing (audited 2026-07-19)

Below are draft listings for the 11 languages that have a real, shipped Bible
translation in `app/src/main/assets/bibles/` and a `Translation` entry in
`Bible.kt`, but never got a Play Store listing entry (the listing was last
updated for 1.4.3, submitted 2026-07-13; these translations landed
2026-07-16/17). Totals used in the listing bodies below — **33 translations
across 28 languages** — come from the `translations` list in
`app/src/main/java/com/aleks/hexapla/Bible.kt` (34 `Translation`
registrations; the Simplified/Traditional Chinese Union Version pair, `cus`
and `cuv`, is one translation in two scripts, netting 33) cross-checked
against the commit trail (`git log`: `c8c7fc6 Glika Bibele 1685/1689 (glk):
32 translations, 27 languages` — the most recent translation-adding commit as
of 2026-07-19 at the time this audit was first written; the Дзекуць-Малей/
Луцкевіч Belarusian NT+Psalms translation, `dzm`, was added the same day,
bringing the total to 33 translations / 28 languages — Belarusian was not
previously represented by any other entry, so it's a straight +1/+1). All 11
of the languages audited here are NOT yet in a submitted build, **except
Hebrew** — `he_wlc` (Westminster Leningrad Codex) has been live since v1.4/
code 7 (submitted 2026-07-11); its listing gap is a pure oversight,
independent of the other 10, and can go out any time. The other 10 should go
out with whatever release next includes `ar_vandyck.json`,
`cs_kralicka.json`, `el_vamvas.json`, `fi_biblia1776.json`, `hu_karoli.json`,
`hy_west1853.json`, `lv_gluck.json`, `nl_staten.json`, `pl_gdanska.json`,
`sr_karadzic.json`. Belarusian (`be_dzekuc.json`) is a twelfth, separate
addition — it lands with 1.5.1/code 12 itself (not a backlog item), so its
listing entry below is annotated "SHIPPING WITH 1.5.1", not "ADD WITH THE
NEXT RELEASE".

### العربية — Arabic (ar) (ADD WITH THE NEXT RELEASE — ar_vandyck.json is in tree since 2026-07-16, not yet in a submitted build)

**العنوان:** Hexapla — كتاب مقدس موازي

**الوصف القصير (≤80):**
الكتاب المقدس دون إنترنت: 33 ترجمة، صوت، خطط قراءة، أرقام سترونغ.

**الوصف الكامل:**

هكسابلا هو الكتاب المقدس الكامل — دون إنترنت، دون إعلانات، دون حساب، ودون جمع أي بيانات. كل شيء مجاني ولا شيء مقفل.

📖 33 ترجمة كلاسيكية في 28 لغة: ترجمة فان دايك 1865 (العربية)، الملك جيمس KJV 1611 مع الأسفار القانونية الثانية، وبستر 1833، جنيف 1599، ديوداتي 1649، رينا-فاليرا 1909، لوثر 1545، مارتن 1744، كارل الثاني عشر 1703، السينودسية الروسية، السلافية الكنسية، المييجي اليابانية، والنسخة الصينية الموحدة (和合本)، إضافة إلى النصين الأصليين العبري واليوناني.
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

### Čeština — Czech (cs) (ADD WITH THE NEXT RELEASE — cs_kralicka.json is in tree since 2026-07-17, not yet in a submitted build)

**Název:** Hexapla — Paralelní Bible

**Krátký popis (≤80):**
Bible offline: 33 klasických překladů, zvuk, plány čtení, Strong.

**Úplný popis:**

Hexapla je kompletní Bible — offline, bez reklam, bez účtu a bez sběru dat. Vše zdarma, nic není uzamčeno.

📖 33 klasických překladů ve 28 jazycích: Bible kralická 1613, KJV 1611 s apokryfy, Webster 1833, Ženevská bible 1599, Diodati 1649, Reina-Valera 1909, Lutherova bible 1545, Martin 1744, Karel XII. 1703, ruský synodální překlad, církevní slovanština, japonský Meidži, čínský Union Version (和合本), a hebrejský i řecký původní text.
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

### Ελληνικά — Greek (el) (ADD WITH THE NEXT RELEASE — el_vamvas.json is in tree since 2026-07-16, not yet in a submitted build)

**Τίτλος:** Hexapla — Παράλληλη Βίβλος

**Σύντομη περιγραφή (≤80):**
Βίβλος offline: 33 κλασικές μεταφράσεις, ήχος, προγράμματα ανάγνωσης, Strong.

**Πλήρης περιγραφή:**

Το Hexapla είναι η πλήρης Βίβλος — χωρίς σύνδεση στο διαδίκτυο, χωρίς διαφημίσεις, χωρίς λογαριασμό και χωρίς συλλογή δεδομένων. Όλα δωρεάν, τίποτα κλειδωμένο.

📖 33 κλασικές μεταφράσεις σε 28 γλώσσες: η μετάφραση Βάμβα 1850, η KJV 1611 με τα Απόκρυφα, η Webster 1833, η Γενεύη 1599, η Diodati 1649, η Reina-Valera 1909, η Βίβλος του Λούθηρου 1545, η Martin 1744, ο Κάρολος ΙΒ' 1703, η Ρωσική Συνοδική, η Εκκλησιαστική Σλαβονική, η ιαπωνική Meiji, η κινεζική Union Version (和合本), καθώς και τα πρωτότυπα εβραϊκά και ελληνικά κείμενα.
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

### Suomi — Finnish (fi) (ADD WITH THE NEXT RELEASE — fi_biblia1776.json is in tree since 2026-07-16, not yet in a submitted build)

**Nimi:** Hexapla — Rinnakkaisraamattu

**Lyhyt kuvaus (≤80):**
Raamattu offline: 33 klassista käännöstä, ääni, lukusuunnitelmat, Strong.

**Täydellinen kuvaus:**

Hexapla on koko Raamattu — ilman internetiä, ilman mainoksia, ilman tiliä ja ilman tiedonkeruuta. Kaikki on ilmaista, mikään ei ole lukittu.

📖 33 klassista käännöstä 28 kielellä: Vanha kirkkoraamattu 1776, KJV 1611 apokryfikirjoineen, Webster 1833, Geneven raamattu 1599, Diodati 1649, Reina-Valera 1909, Lutherin raamattu 1545, Martin 1744, Kaarle XII:n raamattu 1703, venäläinen synodaalikäännös, kirkkoslaavi, japanilainen Meiji, kiinalainen Union-versio (和合本) sekä heprean- ja kreikankieliset alkutekstit.
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

### עברית — Hebrew (locale code: verify iw vs he at upload time — see report) (ADD ANY TIME — he_wlc.json has shipped since v1.4/code 7, submitted 2026-07-11; this is a pure listing oversight, not gated on the next release)

**שם:** Hexapla — כתבי הקודש במקביל

**תיאור קצר (עד 80 תווים):**
כתבי קודש ללא אינטרנט: 33 תרגומים קלאסיים, שמע, תוכניות קריאה, מספרי סטרונג.

**תיאור מלא:**

Hexapla הוא אוסף כתבי הקודש המלא — ללא אינטרנט, ללא פרסומות, ללא צורך בחשבון וללא איסוף נתונים. הכול חינם וכלום אינו נעול.

📖 33 תרגומים קלאסיים ב-28 שפות: הנוסח העברי של התנ"ך לפי כתב היד של לנינגרד (Westminster Leningrad Codex), ה-KJV משנת 1611 עם הספרים החיצוניים, וובסטר 1833, ג'נבה 1599, דיודאטי 1649, ריינה-ולרה 1909, תרגום לותר 1545, מרטין 1744, קרל ה-12 משנת 1703, הנוסח הסינודלי הרוסי, הסלאבית הכנסייתית, מייג'י היפני, התרגום הסיני 和合本, וכן הטקסט היווני של הברית החדשה.
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

### Magyar — Hungarian (hu) (ADD WITH THE NEXT RELEASE — hu_karoli.json is in tree since 2026-07-17, not yet in a submitted build)

**Cím:** Hexapla — Párhuzamos Biblia

**Rövid leírás (≤80):**
Biblia internet nélkül: 33 klasszikus fordítás, hang, olvasási tervek, Strong.

**Teljes leírás:**

A Hexapla a teljes Biblia — internet nélkül, hirdetések nélkül, regisztráció nélkül és adatgyűjtés nélkül. Minden ingyenes, semmi sincs lezárva.

📖 33 klasszikus fordítás 28 nyelven: Károli Gáspár fordítása 1590/1908, KJV 1611 az apokrifekkel, Webster 1833, Genfi Biblia 1599, Diodati 1649, Reina-Valera 1909, Luther-Biblia 1545, Martin 1744, XII. Károly Bibliája 1703, orosz szinodális fordítás, egyházi szláv, japán Meidzsi, kínai Union-fordítás (和合本), valamint a héber és görög eredeti szövegek.
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

### Հայերեն — Armenian (hy-AM) (ADD WITH THE NEXT RELEASE — hy_west1853.json is in tree since 2026-07-17, not yet in a submitted build)

**Վերնագիր:** Hexapla — Զուգահեռ Սուրբ Գիրք

**Համառոտ նկարագրութիւն (≤80):**
Աստուածաշունչ առանց ինտերնետի. 33 թարգմանութիւն, ձայն, ընթերցման ծրագրեր, Strong

**Ամբողջական նկարագրութիւն:**

Hexapla-ն ամբողջական Աստուածաշունչն է՝ առանց ինտերնետի, առանց գովազդի, առանց հաշուի եւ առանց տուեալների հաւաքման։ Ամէն ինչ անվճար է, ոչինչ փակուած չէ։

📖 33 դասական թարգմանութիւն 28 լեզուներով՝ Արեւմտահայերէն Նոր Կտակարանը (1853), KJV 1611-ը՝ ապոկրիֆներով, Webster 1833, Ժնեւի Աստուածաշունչը 1599, Diodati 1649, Reina-Valera 1909, Լիւթերի Աստուածաշունչը 1545, Martin 1744, Կարլոս XII-ի Աստուածաշունչը 1703, ռուսական սինոդալ թարգմանութիւնը, եկեղեցասլավոներէնը, ճապոներէն Մեիջին, չինական Union տարբերակը (和合本), ինչպէս նաեւ եբրայերէն եւ հունարէն բնագրերը։
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

*Note: hy_west1853 is a New Testament-only translation (Western Armenian, 1853) — named explicitly above ("Նոր Կտակարանը", "New Testament") rather than implied to be a full Bible, matching how the app already discloses grc (Greek NT) and the Sanskrit NT elsewhere. The app as a whole still offers the complete Bible via its other translations, read in parallel.*

### Latviešu — Latvian (lv) (ADD WITH THE NEXT RELEASE — lv_gluck.json is in tree since 2026-07-17, not yet in a submitted build)

**Nosaukums:** Hexapla — Paralēlā Bībele

**Īsais apraksts (≤80):**
Bībele bez interneta: 33 klasiski tulkojumi, audio, lasīšanas plāni, Strong.

**Pilnais apraksts:**

Hexapla ir pilna Bībele — bez interneta, bez reklāmām, bez konta un bez datu vākšanas. Viss ir bez maksas, nekas nav slēgts.

📖 33 klasiski tulkojumi 28 valodās: Glika Bībele 1685/1689, KJV 1611 ar apokrifiem, Webster 1833, Ženēvas Bībele 1599, Diodati 1649, Reina-Valera 1909, Lutera Bībele 1545, Martina Bībele 1744, Kārļa XII Bībele 1703, krievu Sinodālais tulkojums, baznīcslāvu valoda, japāņu Meidzi, ķīniešu Union versija (和合本), kā arī ebreju un grieķu oriģinālteksti.
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

### Nederlands — Dutch (nl) (ADD WITH THE NEXT RELEASE — nl_staten.json is in tree since 2026-07-16, not yet in a submitted build)

**Titel:** Hexapla — Parallelle Bijbel

**Korte beschrijving (≤80):**
Bijbel offline: 33 klassieke vertalingen, audio, leesplannen, Strong.

**Volledige beschrijving:**

Hexapla is de complete Bijbel — offline, zonder advertenties, zonder account en zonder gegevensverzameling. Alles gratis, niets vergrendeld.

📖 33 klassieke vertalingen in 28 talen: de Statenvertaling 1637/1888, de KJV 1611 met apocriefen, Webster 1833, Genève 1599, Diodati 1649, Reina-Valera 1909, Luther 1545, Martin 1744, Karel XII 1703, Russisch-Synodale vertaling, Kerkslavisch, Japans Meiji, Chinese Union-versie (和合本), en de Hebreeuwse en Griekse grondteksten.
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

### Polski — Polish (pl) (ADD WITH THE NEXT RELEASE — pl_gdanska.json is in tree since 2026-07-16, not yet in a submitted build)

**Nazwa:** Hexapla — Biblia Równoległa

**Krótki opis (≤80):**
Biblia offline: 33 klasyczne przekłady, audio, plany czytania, Strong.

**Pełny opis:**

Hexapla to kompletna Biblia — bez internetu, bez reklam, bez konta i bez zbierania danych. Wszystko za darmo, nic nie jest zablokowane.

📖 33 klasyczne przekłady w 28 językach: Biblia Gdańska 1632, KJV 1611 z apokryfami, Webster 1833, Biblia Genewska 1599, Diodati 1649, Reina-Valera 1909, Biblia Lutra 1545, Martin 1744, Biblia Karola XII 1703, rosyjski przekład synodalny, cerkiewnosłowiański, japoński Meiji, chińska Union Version (和合本), a także oryginalne teksty hebrajski i grecki.
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

### Српски / Srpski — Serbian (sr) (ADD WITH THE NEXT RELEASE — sr_karadzic.json is in tree since 2026-07-17, not yet in a submitted build; listing uses Latin script, matching the shipped translation's own script)

**Naziv:** Hexapla — Paralelna Biblija

**Kratak opis (≤80):**
Biblija bez interneta: 33 klasična prevoda, audio, planovi čitanja, Strong.

**Pun opis:**

Hexapla je kompletna Biblija — bez interneta, bez reklama, bez naloga i bez prikupljanja podataka. Sve je besplatno, ništa nije zaključano.

📖 33 klasična prevoda na 28 jezika: Sveto pismo — Karadžić/Daničić, 1847/1865, KJV 1611 sa apokrifima, Webster 1833, Ženevska Biblija 1599, Diodati 1649, Reina-Valera 1909, Lutherova Biblija 1545, Martin 1744, Biblija Karla XII 1703, ruski Sinodalni prevod, crkvenoslovenski, japanski Meiji, kineska Union verzija (和合本), kao i hebrejski i grčki izvorni tekstovi.
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

### Беларуская — Belarusian (be) (SHIPPING WITH 1.5.1 — be_dzekuc.json is in tree since 2026-07-19, registered in Bible.kt as `dzm`; this is the current release cycle, not a future backlog placeholder)

**Назва:** Hexapla — Паралельная Біблія

**Кароткі апіс (≤80):**
Біблія без інтэрнэту: 33 клясычныя пераклады, аўдыё, плян чытаньня, Strong.

**Поўны апіс:**

Hexapla — гэта поўная Біблія — без інтэрнэту, без рэклямы, без рэгістрацыі і без збору даных. Усё бясплатна, нічога не заблакавана.

📖 33 клясычныя пераклады ў 28 мовах: Новы Запавет і Псальмы ў перакладзе Дзекуць-Малея і Луцкевіча (1931), KJV 1611 з апокрыфамі, Webster 1833, Жэнеўская Біблія 1599, Diodati 1649, Reina-Valera 1909, Лютэраўская Біблія 1545, Martin 1744, Біблія Карла XII 1703, расійскі сінадальны пераклад, царкоўнаславянская мова, японская Мэйдзі, кітайская версія Union (和合本), а таксама габрэйскі і грэцкі арыгінальныя тэксты.
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
