import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.plugin.compose")
}

// Release signing is configured in keystore.properties (never committed).
val keystoreProps = Properties().apply {
    val f = rootProject.file("keystore.properties")
    if (f.exists()) f.inputStream().use { load(it) }
}

android {
    namespace = "com.aleks.hexapla"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.aleks.hexapla"
        minSdk = 26
        targetSdk = 35
        versionCode = 9
        versionName = "1.4.2"
    }

    buildFeatures {
        buildConfig = true
    }

    // Three distribution channels from one codebase:
    //  - play:    Google Play. Tips via Play Billing only; no external
    //             payment links anywhere (payments policy).
    //  - rustore: RuStore / direct APK. Play services absent, so the
    //             support section shows the external donation link.
    //  - foss:    F-Droid. No proprietary code at all — the Play Billing
    //             dependency is excluded (see flavor-scoped dependencies
    //             below and the TipManager stub in src/foss); donation
    //             links only.
    flavorDimensions += "distribution"
    productFlavors {
        create("play") {
            dimension = "distribution"
            buildConfigField("boolean", "EXTERNAL_DONATIONS", "false")
        }
        create("rustore") {
            dimension = "distribution"
            buildConfigField("boolean", "EXTERNAL_DONATIONS", "true")
        }
        create("foss") {
            dimension = "distribution"
            buildConfigField("boolean", "EXTERNAL_DONATIONS", "true")
        }
    }

    // play and rustore share the real Play Billing TipManager from
    // src/billing; foss uses the no-op stub in src/foss instead, so
    // src/main never imports com.android.billingclient.
    sourceSets {
        getByName("play") { kotlin.srcDir("src/billing/kotlin") }
        getByName("rustore") { kotlin.srcDir("src/billing/kotlin") }
    }

    signingConfigs {
        if (keystoreProps.isNotEmpty()) {
            create("release") {
                storeFile = file(keystoreProps.getProperty("storeFile"))
                storePassword = keystoreProps.getProperty("storePassword")
                keyAlias = keystoreProps.getProperty("keyAlias")
                keyPassword = keystoreProps.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
            if (keystoreProps.isNotEmpty()) {
                signingConfig = signingConfigs.getByName("release")
            }
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    buildFeatures {
        compose = true
    }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2024.10.00")
    implementation(composeBom)

    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.activity:activity-compose:1.9.2")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.6")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("androidx.navigation:navigation-compose:2.8.2")
    implementation("androidx.datastore:datastore-preferences:1.1.1")
    implementation("androidx.media:media:1.7.0")
    implementation("com.google.zxing:core:3.5.3")

    // Proprietary Google Play Billing — store flavors only. The foss
    // (F-Droid) variant must not link it; src/foss stubs TipManager.
    "playImplementation"("com.android.billingclient:billing-ktx:7.1.1")
    "rustoreImplementation"("com.android.billingclient:billing-ktx:7.1.1")
}
