package com.aleks.hexapla

import android.app.Activity
import android.content.Context
import androidx.compose.runtime.mutableStateOf

/**
 * FOSS (F-Droid) build: no Google Play Billing — the proprietary
 * billingclient dependency is excluded from this flavor entirely.
 *
 * Same surface as the real TipManager in src/billing, but [available]
 * stays false forever and [products] stays empty, so SettingsScreen's
 * support section falls through to the external donation links in
 * [Donation] (EXTERNAL_DONATIONS=true for this flavor).
 */
class TipProduct internal constructor() {
    val price: String get() = ""
}

class TipManager(context: Context) {

    val available = mutableStateOf(false)
    val products = mutableStateOf<List<TipProduct>>(emptyList())

    fun connect() {
        // No billing backend; nothing to connect to.
    }

    fun tip(activity: Activity, product: TipProduct) {
        // Unreachable: products is always empty, so the UI never offers tips.
    }

    fun release() {
        // Nothing to release.
    }
}
