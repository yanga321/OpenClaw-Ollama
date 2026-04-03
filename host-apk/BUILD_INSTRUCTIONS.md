# Host APK Launcher - Build Instructions

## Prerequisites

1. **Android Studio**: Arctic Fox (2020.3.1) or later
2. **JDK**: Version 17 or higher
3. **Android SDK**: API Level 34
4. **Gradle**: 8.0+

## Project Structure

```
host-apk/
├── app/
│   ├── src/main/
│   │   ├── java/com/openclaw/launcher/
│   │   │   ├── MainActivity.kt          # Main entry point
│   │   │   └── OpenClawApplication.kt   # Application class
│   │   ├── res/
│   │   │   ├── layout/
│   │   │   ├── drawable/
│   │   │   ├── values/
│   │   │   └── xml/
│   │   └── AndroidManifest.xml
│   ├── build.gradle
│   └── proguard-rules.pro
├── build.gradle
├── gradle.properties
└── settings.gradle
```

## Build Steps

### 1. Clone and Setup

```bash
cd /workspace/host-apk
```

### 2. Sync Gradle

Open in Android Studio or run:
```bash
./gradlew sync
```

### 3. Build Debug APK

```bash
./gradlew assembleDebug
```

Output: `app/build/outputs/apk/debug/app-debug.apk`

### 4. Build Release APK

```bash
./gradlew assembleRelease
```

Output: `app/build/outputs/apk/release/app-release-unsigned.apk`

### 5. Install on Device

```bash
adb install app/build/outputs/apk/debug/app-debug.apk
```

## Features Implemented

✅ USB OTG Auto-Detection
✅ Biometric Authentication (Fingerprint/Face)
✅ Panic Wipe Security Feature
✅ Material Design 3 UI
✅ Battery & Memory Monitoring
✅ Quick Action Cards (Chat, AR, Swarm, Settings)

## Next Steps

1. **Integrate llama.cpp** - See `llama_cpp_integration/` directory
2. **Build AR Camera Activity** - See `app/ar/` directory  
3. **Implement Chat Interface** - Create chat activity
4. **Add Swarm Networking** - Integrate with swarm_connector.py

## Testing

### USB OTG Testing
1. Connect OTG drive to Android device
2. Launch app - should auto-detect drive
3. Verify biometric prompt appears
4. Check status shows "OTG Drive Connected"

### Panic Wipe Testing
⚠️ **WARNING**: This will delete all data!
1. Tap panic button (bottom nav)
2. Confirm wipe action
3. Verify data is deleted

## Troubleshooting

### USB Permission Issues
- Ensure USB_HOST feature is declared in manifest
- Check device supports USB OTG
- Try different USB cable/adapter

### Biometric Not Working
- Enroll fingerprint/face in device settings
- App will fallback to PIN if biometrics unavailable

### Build Errors
- Clean project: `./gradlew clean`
- Invalidate caches in Android Studio
- Update Android SDK tools

## APK Size Optimization

Current target: <15MB

Tips:
- Enable R8 shrinking (enabled by default)
- Use vector drawables (all icons are vectors)
- Remove unused resources
- Optimize ProGuard rules

## Signing for Release

Create `keystore.properties`:
```properties
storePassword=your_store_password
keyPassword=your_key_password
keyAlias=your_key_alias
storeFile=/path/to/keystore.jks
```

Then build signed APK:
```bash
./gradlew assembleRelease -PsigningConfig=release
```
