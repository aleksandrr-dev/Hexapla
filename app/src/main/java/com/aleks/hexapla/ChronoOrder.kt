package com.aleks.hexapla

/* Chronological reading order — all 1189 canon chapters, each exactly once,
   in the order the recorded events happened. Curated from internal biblical
   anchors (psalm superscriptions, the prophets' date formulas, the parallel
   histories, Acts and the epistles' writing points); generated and verified
   by tools/build_chrono_plan.py, which documents every placement decision.

   Tokens are "book:chapter" or "book:first-last" — book 0-based, chapters
   1-based in KJV numbering. Expansion is verbatim onto the canonical KJV
   grid (Plans.KJV_CHAPTERS): plan days no longer depend on the loaded
   translation's shape — PlansScreen pivots display and open targets
   through VerseMap and dims chapters the primary translation lacks. */
object ChronoOrder {

    private const val ORDER =
        "0:1-11 17:1-42 0:12-50 1:1-40 2:1-27 3:1-36 4:1-32 18:90-91 4:33-34 " +
        "5:1-24 6:1-21 7:1-4 8:1-18 18:59 8:19-21 18:56 18:34 8:22 18:142 " +
        "18:52 8:23 18:54 18:63 8:24 18:57 8:25-26 18:7 18:5 18:11-14 18:17 " +
        "18:22 18:25-28 18:31 18:35 18:64 18:69 18:86 18:109 18:140-141 " +
        "18:143 8:27-31 12:10 9:1-5 12:11-12 18:2 18:101 18:110 9:6 12:13-16 " +
        "18:96 18:105-106 18:8 18:15 18:19 18:24 18:29 18:33 18:65-68 18:93 " +
        "18:95 18:97-100 18:104 9:7 12:17 18:16 18:23 18:36 18:39 18:62 " +
        "18:84 9:8-9 12:18 18:60 18:108 9:10 12:19 18:9-10 18:20-21 18:44 " +
        "9:11-12 12:20 18:51 18:32 18:38 18:6 9:13-15 18:3-4 18:55 9:16-18 " +
        "18:41 18:61 18:70 9:19-21 18:40 18:58 9:22 18:18 9:23-24 12:21 " +
        "18:30 12:22-25 18:1 18:42-43 18:45 18:49-50 18:53 18:73 18:77-78 " +
        "18:81-82 18:88 18:92 18:94 18:103 18:111-118 18:122 18:124 18:131 " +
        "18:133 18:138-139 18:144-145 12:26-29 10:1-2 18:37 18:71 10:3 13:1 " +
        "18:72 10:4 21:1-8 10:5-6 13:2-3 10:7 13:4 10:8 13:5 18:132 13:6-7 " +
        "18:135-136 10:9 13:8 18:127 19:1-31 10:10 13:9 20:1-12 10:11-14 " +
        "13:10-12 18:89 10:15 13:13-16 10:16 13:17 10:17-22 13:18-20 " +
        "18:46-48 18:83 11:1-8 13:21 11:9-10 13:22 11:11-12 13:23-24 28:1-3 " +
        "11:13-14 13:25 31:1-4 29:1-9 11:15 13:26 22:1-6 13:27 32:1-7 11:16 " +
        "13:28 22:7-12 27:1-14 11:17 18:80 13:29-31 22:13-35 11:18-19 13:32 " +
        "22:36-37 18:75-76 11:20 22:38-66 11:21 13:33 33:1-3 11:22 13:34 " +
        "35:1-3 23:1-6 11:23 13:35 34:1-3 23:26 23:7-20 23:22-23 23:25 " +
        "23:46-47 26:1 23:36 23:45 26:2 23:35 23:48-49 26:3 11:24 23:24 " +
        "23:29 23:27-28 23:50-51 25:1-24 23:21 23:34 23:30-33 23:37-38 " +
        "11:25 13:36 23:39 23:52 24:1-5 30:1 18:74 18:79 18:137 23:40-44 " +
        "25:25-48 26:4 26:7-8 26:5 26:9 18:102 26:6 12:1-9 14:1-3 18:107 " +
        "18:85 18:87 18:126 26:10-12 14:4 36:1-2 37:1-8 14:5-6 37:9-14 " +
        "16:1-10 14:7-10 18:119 15:1-7 18:120-121 18:123 18:125 18:128-130 " +
        "18:134 15:8-13 18:146-150 38:1-4 41:1 39:1 41:2 39:2-3 40:1 41:3 " +
        "42:1 39:4 41:4-5 42:2-5 40:2 39:12 40:3 41:6 39:5-8 41:7 39:11 " +
        "41:8 40:4-5 39:13 39:9-10 39:14 40:6 41:9 42:6 39:15 40:7 39:16 " +
        "40:8 39:17 40:9 39:18 42:7-10 41:10-17 42:11 41:18 39:19 40:10 " +
        "39:20 41:19 42:12 39:21 40:11 39:22 40:12 41:20 39:23-24 40:13 " +
        "41:21 39:25-26 40:14 41:22 42:13-17 39:27 40:15 41:23 42:18-19 " +
        "39:28 40:16 41:24 42:20-21 43:1-12 58:1-5 43:13-15 47:1-6 43:16-18 " +
        "51:1-5 52:1-3 43:19 45:1-16 46:1-13 44:1-16 43:20-28 48:1-6 50:1-4 " +
        "56:1 49:1-4 53:1-6 55:1-3 59:1-5 57:1-13 54:1-4 60:1-3 64:1 61:1-5 " +
        "62:1 63:1 65:1-22"

    /** Historical eras: (book, 0-based KJV chapter) where each era begins
     *  in the order above → heading resource. */
    private val eras = listOf(
        Triple(0, 0, R.string.era_beginning),      // Gen 1
        Triple(17, 0, R.string.era_patriarchs),    // Job 1 (then Gen 12-50)
        Triple(1, 0, R.string.era_exodus),         // Exo 1
        Triple(3, 0, R.string.era_wilderness),     // Num 1
        Triple(5, 0, R.string.era_conquest),       // Jos 1
        Triple(6, 0, R.string.era_judges),         // Jdg 1 (with Ruth)
        Triple(8, 0, R.string.era_saul),           // 1Sa 1
        Triple(12, 9, R.string.era_david),         // 1Ch 10 (Saul falls)
        Triple(10, 0, R.string.era_solomon),       // 1Ki 1
        Triple(10, 11, R.string.era_divided),      // 1Ki 12
        Triple(11, 14, R.string.era_isaiah),       // 2Ki 15 (Uzziah dies)
        Triple(11, 20, R.string.era_last_kings),   // 2Ki 21 (Manasseh)
        Triple(23, 25, R.string.era_fall),         // Jer 26 (Jehoiakim)
        Triple(23, 39, R.string.era_exile),        // Jer 40 (after the fall)
        Triple(12, 0, R.string.era_return),        // 1Ch 1 (bridge to Ezra)
        Triple(41, 0, R.string.era_christ),        // Luk 1
        Triple(43, 0, R.string.era_church),        // Act 1
        Triple(65, 0, R.string.era_revelation)     // Rev 1
    )

    /** Day number → era heading, for the day containing each era's first
     *  chapter. */
    fun eraByDay(days: List<PlanDay>): Map<Int, Int> {
        val m = LinkedHashMap<Int, Int>()
        for ((b, c, res) in eras) {
            val day = days.firstOrNull { d ->
                d.chapters.any { it.first == b && it.second == c }
            } ?: continue
            if (!m.containsKey(day.day)) m[day.day] = res
        }
        return m
    }

    /** Expand ORDER verbatim onto the canonical KJV grid: every canon
     *  chapter exactly once, 1189 in all (checked — ORDER is a static
     *  permutation verified by tools/build_chrono_plan.py). No LXX shift,
     *  no absence filtering: those are display-time concerns now. */
    fun chapters(): List<Pair<Int, Int>> {
        val out = ArrayList<Pair<Int, Int>>(1189)
        val seen = HashSet<Pair<Int, Int>>(2048)
        for (token in ORDER.split(' ')) {
            val (book, range) = token.split(':')
            val b = book.toInt()
            val first = range.substringBefore('-').toInt()
            val last = range.substringAfter('-').toInt()
            for (ch in first..last) {
                val pair = b to ch - 1
                check(seen.add(pair)) { "ORDER repeats chapter $pair" }
                out.add(pair)
            }
        }
        check(out.size == 1189) { "ORDER expands to ${out.size} chapters, expected 1189" }
        return out
    }
}
