package com.aleks.hexapla

import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily

/**
 * The reading typeface.
 *
 * Literata (SIL OFL, Google Fonts) is a variable font drawn for long-form
 * reading on screens — its optical-size axis adapts the letterforms as the
 * reader changes text size, which is exactly what this app's font-size slider
 * does. Bundled upright only: italics appear on UI chrome (Vulgate rubrics,
 * the note line), never on scripture, so they fall back to the system face.
 *
 * ⚠⚠ IT COVERS LATIN, GREEK AND CYRILLIC — AND NOTHING ELSE. This app ships
 * thirty languages; Hebrew, Armenian, Georgian, Tamil, Chinese, Japanese,
 * Arabic, Persian and Devanagari have no glyphs in Literata. Android's font
 * fallback usually rescues a missing glyph, but "usually" is not a promise
 * across every OEM font stack, and a reader who opens the Tamil Bible to a
 * screen of tofu has lost their Bible. So the face is chosen by SCRIPT, not
 * applied globally: a translation whose language Literata actually covers
 * gets it, everything else keeps the system serif, which those scripts are
 * already tuned for.
 */
object ReadingFont {
    val literata = FontFamily(Font(R.font.literata))

    /** Languages Literata covers (Latin, Greek, Cyrillic). */
    private val COVERED = setOf(
        "en", "enm", "de", "fr", "es", "pt", "it", "nl", "da", "sv", "fi",
        "pl", "cs", "hu", "lv", "sr", "la", "el", "grc",
        "ru", "be", "cu", "csl",
    )

    /**
     * @param serif the user's "Serif font" preference
     * @param lang  the primary translation's language tag
     */
    fun forLanguage(serif: Boolean, lang: String): FontFamily = when {
        !serif -> FontFamily.SansSerif
        lang in COVERED -> literata
        else -> FontFamily.Serif      // scripts Literata cannot render
    }
}
