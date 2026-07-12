package com.aleks.hexapla

import android.app.Activity
import android.content.Context
import androidx.compose.runtime.mutableStateOf
import com.android.billingclient.api.BillingClient
import com.android.billingclient.api.BillingClientStateListener
import com.android.billingclient.api.BillingFlowParams
import com.android.billingclient.api.BillingResult
import com.android.billingclient.api.ConsumeParams
import com.android.billingclient.api.PendingPurchasesParams
import com.android.billingclient.api.ProductDetails
import com.android.billingclient.api.Purchase
import com.android.billingclient.api.PurchasesUpdatedListener
import com.android.billingclient.api.QueryProductDetailsParams
import com.android.billingclient.api.QueryPurchasesParams

/**
 * Voluntary tips via Google Play Billing.
 *
 * This is the play/rustore implementation (shared via the src/billing
 * source set); the foss flavor replaces it with a no-op stub in src/foss
 * so the F-Droid build carries no proprietary Play Billing code. The UI
 * only ever sees [TipProduct], never the billing library's types.
 *
 * Tips are CONSUMABLE products that grant nothing: every purchase is consumed
 * immediately so it can be repeated, and no entitlement is ever stored or
 * checked anywhere in the app. There is no premium tier.
 *
 * Create these product IDs in Play Console (Monetize -> Products -> In-app
 * products) with whatever prices you choose. If Play Billing is unavailable
 * (no Play services, RuStore/APK build, de-Googled device), [available] stays
 * false and the UI falls back to the external links in [Donation].
 */
class TipProduct internal constructor(internal val details: ProductDetails) {
    val price: String
        get() = details.oneTimePurchaseOfferDetails?.formattedPrice ?: ""
}

class TipManager(context: Context) : PurchasesUpdatedListener {

    val available = mutableStateOf(false)
    val products = mutableStateOf<List<TipProduct>>(emptyList())

    private val productIds = listOf("tip_small", "tip_medium", "tip_large")

    private val client = BillingClient.newBuilder(context.applicationContext)
        .setListener(this)
        .enablePendingPurchases(
            PendingPurchasesParams.newBuilder().enableOneTimeProducts().build()
        )
        .build()

    fun connect() {
        if (client.isReady) return
        client.startConnection(object : BillingClientStateListener {
            override fun onBillingSetupFinished(result: BillingResult) {
                if (result.responseCode == BillingClient.BillingResponseCode.OK) {
                    available.value = true
                    queryProducts()
                    consumeOutstanding()
                }
            }

            override fun onBillingServiceDisconnected() {
                available.value = false
            }
        })
    }

    private fun queryProducts() {
        val params = QueryProductDetailsParams.newBuilder()
            .setProductList(
                productIds.map {
                    QueryProductDetailsParams.Product.newBuilder()
                        .setProductId(it)
                        .setProductType(BillingClient.ProductType.INAPP)
                        .build()
                }
            )
            .build()
        client.queryProductDetailsAsync(params) { result, details ->
            if (result.responseCode == BillingClient.BillingResponseCode.OK) {
                products.value = details.sortedBy { d ->
                    d.oneTimePurchaseOfferDetails?.priceAmountMicros ?: 0
                }.map { TipProduct(it) }
            }
        }
    }

    fun tip(activity: Activity, product: TipProduct) {
        val params = BillingFlowParams.newBuilder()
            .setProductDetailsParamsList(
                listOf(
                    BillingFlowParams.ProductDetailsParams.newBuilder()
                        .setProductDetails(product.details)
                        .build()
                )
            )
            .build()
        client.launchBillingFlow(activity, params)
    }

    override fun onPurchasesUpdated(result: BillingResult, purchases: MutableList<Purchase>?) {
        if (result.responseCode == BillingClient.BillingResponseCode.OK) {
            purchases?.forEach { consume(it) }
        }
        // User cancellations and errors need no handling: nothing was granted,
        // so there is nothing to roll back.
    }

    /** Consume immediately: a tip is a thank-you, not an entitlement. */
    private fun consume(purchase: Purchase) {
        if (purchase.purchaseState != Purchase.PurchaseState.PURCHASED) return
        val params = ConsumeParams.newBuilder()
            .setPurchaseToken(purchase.purchaseToken)
            .build()
        client.consumeAsync(params) { _, _ -> }
    }

    /** Consume any tips left pending from interrupted sessions. */
    private fun consumeOutstanding() {
        val params = QueryPurchasesParams.newBuilder()
            .setProductType(BillingClient.ProductType.INAPP)
            .build()
        client.queryPurchasesAsync(params) { result, purchases ->
            if (result.responseCode == BillingClient.BillingResponseCode.OK) {
                purchases.forEach { consume(it) }
            }
        }
    }

    fun release() {
        if (client.isReady) client.endConnection()
    }
}
