package com.blindnavai.voice

import android.content.Context
import android.speech.tts.TextToSpeech
import java.util.Locale
import java.util.UUID
import java.util.concurrent.ConcurrentLinkedQueue

class VoiceManager(context: Context) : TextToSpeech.OnInitListener {
    private val tts = TextToSpeech(context.applicationContext, this)
    private var initialized = false
    private val navigationQueue = ConcurrentLinkedQueue<String>()
    private var lastNavigationUtterance: String? = null

    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            tts.language = Locale.US
            tts.setSpeechRate(1.0f)
            initialized = true
            flushNavigationQueue()
        }
    }

    @Synchronized
    fun enqueueNavigation(text: String) {
        if (!initialized) {
            navigationQueue.add(text)
            return
        }
        lastNavigationUtterance = text
        tts.speak(text, TextToSpeech.QUEUE_ADD, null, UUID.randomUUID().toString())
    }

    @Synchronized
    fun announceHazard(text: String) {
        if (!initialized) return
        val navResume = lastNavigationUtterance
        tts.stop()
        tts.speak(text, TextToSpeech.QUEUE_FLUSH, null, UUID.randomUUID().toString())
        if (!navResume.isNullOrBlank()) {
            tts.speak(navResume, TextToSpeech.QUEUE_ADD, null, UUID.randomUUID().toString())
        }
    }

    private fun flushNavigationQueue() {
        while (navigationQueue.isNotEmpty()) {
            val utterance = navigationQueue.poll() ?: continue
            enqueueNavigation(utterance)
        }
    }

    fun shutdown() {
        tts.stop()
        tts.shutdown()
    }
}
