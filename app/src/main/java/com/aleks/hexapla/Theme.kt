package com.aleks.hexapla

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

// Light theme: aged-paper reading surface with deep oxblood accents,
// echoing leather-bound scripture rather than a generic material palette.
private val Light = lightColorScheme(
    primary = Color(0xFF6D2A2A),          // oxblood
    onPrimary = Color(0xFFFDF6E9),
    primaryContainer = Color(0xFFEADFC8),
    onPrimaryContainer = Color(0xFF3E2723),
    secondary = Color(0xFF6D4C2B),        // leather brown
    onSecondary = Color(0xFFFDF6E9),
    secondaryContainer = Color(0xFFF0E6D2),
    onSecondaryContainer = Color(0xFF4E342E),
    background = Color(0xFFFAF3E3),       // parchment
    onBackground = Color(0xFF2B2114),
    surface = Color(0xFFFAF3E3),
    onSurface = Color(0xFF2B2114),
    surfaceVariant = Color(0xFFEFE5CF),
    onSurfaceVariant = Color(0xFF5C5240),
    outline = Color(0xFF9C8F76)
)

// Dark theme: near-black with warm candlelight text for night reading.
private val Dark = darkColorScheme(
    primary = Color(0xFFD9A05B),          // candlelight amber
    onPrimary = Color(0xFF2B1A0A),
    primaryContainer = Color(0xFF4A3018),
    onPrimaryContainer = Color(0xFFF2DEC0),
    secondary = Color(0xFFB08D62),
    onSecondary = Color(0xFF241505),
    secondaryContainer = Color(0xFF3A2C1B),
    onSecondaryContainer = Color(0xFFE8D5B8),
    background = Color(0xFF12100C),
    onBackground = Color(0xFFE6DCC8),
    surface = Color(0xFF12100C),
    onSurface = Color(0xFFE6DCC8),
    surfaceVariant = Color(0xFF262118),
    onSurfaceVariant = Color(0xFFBFB39C),
    outline = Color(0xFF6E644F)
)

@Composable
fun BibleTheme(themeMode: String, content: @Composable () -> Unit) {
    val dark = when (themeMode) {
        "light" -> false
        "dark" -> true
        else -> isSystemInDarkTheme()
    }
    MaterialTheme(colorScheme = if (dark) Dark else Light, content = content)
}
