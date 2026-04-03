# Add project specific ProGuard rules here.
# By default, the flags in this file are appended to flags specified
# in /sdk/tools/proguard/proguard-android.txt

# Keep OpenClaw classes
-keep class com.openclaw.** { *; }

# Keep Kotlin coroutines
-keepnames class kotlinx.coroutines.internal.MainDispatcherFactory {}
-keepnames class kotlinx.coroutines.CoroutineExceptionHandler {}

# Keep USB Serial library
-keep class com.hoho.android.usbserial.** { *; }

# Keep Biometric classes
-keep class androidx.biometric.** { *; }

# Keep OkHttp
-dontwarn okhttp3.**
-keep class okhttp3.** { *; }

# Keep Gson
-keepattributes Signature
-keepattributes *Annotation*
-keep class com.google.gson.** { *; }

# Standard Android optimizations
-optimizations !code/simplification/arithmetic,!field/*,!class/merging/*
