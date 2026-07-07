# Play Billing: keep the classes the Play Store binder reflects into.
-keep class com.android.vending.billing.** { *; }

# Translation/plan JSON is parsed by hand via org.json (no reflection),
# so no model keep rules are needed.
