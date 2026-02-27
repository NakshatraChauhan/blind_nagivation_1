[app]
title = BlindNav AI – Environmental Navigation System
package.name = blindnavai
package.domain = org.blindnav
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,osm,torchscript
version = 1.1.0

# Offline, CPU-only stack.
requirements = python3,kivy,plyer,pyjnius,opencv,numpy,torch
orientation = portrait
fullscreen = 0

android.permissions = ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION,CAMERA,VIBRATE,SEND_SMS
android.api = 33
android.minapi = 24
android.archs = arm64-v8a,armeabi-v7a
android.accept_sdk_license = True

# Bundle offline map + model assets.
source.include_patterns = data/*.osm,models/*.torchscript

[buildozer]
log_level = 2
warn_on_root = 1
