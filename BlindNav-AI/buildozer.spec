[app]
title = BlindNav AI
package.name = blindnavai
package.domain = org.blindnav
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,txt,md,pt
version = 1.0.0
requirements = python3,kivy,opencv,pyttsx3,ultralytics,numpy,pillow
orientation = portrait
fullscreen = 0
android.permissions = CAMERA,RECORD_AUDIO,INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 24
android.archs = arm64-v8a,armeabi-v7a
android.allow_backup = True
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
