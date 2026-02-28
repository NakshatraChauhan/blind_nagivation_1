package com.blindnavai.emergency

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.telephony.SmsManager
import androidx.core.content.ContextCompat
import com.blindnavai.voice.VoiceManager
import com.google.android.gms.location.FusedLocationProviderClient

class EmergencyHandler(
    private val context: Context,
    private val fusedLocationProviderClient: FusedLocationProviderClient,
    private val voiceManager: VoiceManager,
    private val emergencyNumber: String = "112"
) {
    fun trigger(lastKnownLocation: Location?) {
        if (ContextCompat.checkSelfPermission(context, Manifest.permission.SEND_SMS) != PackageManager.PERMISSION_GRANTED) {
            voiceManager.announceHazard("Emergency SMS permission is not granted")
            return
        }

        if (lastKnownLocation != null) {
            sendSms(lastKnownLocation.latitude, lastKnownLocation.longitude)
        } else {
            fusedLocationProviderClient.lastLocation.addOnSuccessListener { location ->
                if (location != null) {
                    sendSms(location.latitude, location.longitude)
                } else {
                    voiceManager.announceHazard("Unable to get location for emergency message")
                }
            }.addOnFailureListener {
                voiceManager.announceHazard("Emergency mode failed to retrieve location")
            }
        }
    }

    private fun sendSms(lat: Double, lon: Double) {
        val mapsLink = "https://maps.google.com/?q=$lat,$lon"
        val message = "BlindNav AI emergency alert. Current location: $lat,$lon. Map: $mapsLink"
        SmsManager.getDefault().sendTextMessage(emergencyNumber, null, message, null, null)
        voiceManager.announceHazard("Emergency message sent with your current coordinates")
    }
}
