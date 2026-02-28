package com.blindnavai.vision

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.ImageFormat
import android.graphics.Rect
import android.graphics.YuvImage
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import com.blindnavai.haptic.VibrationManager
import com.blindnavai.risk.RiskEngine
import com.blindnavai.risk.RiskLevel
import com.blindnavai.risk.TrackedObject
import com.blindnavai.voice.VoiceManager
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import java.io.ByteArrayOutputStream

class FrameProcessor(
    private val detector: ObjectDetector,
    private val riskEngine: RiskEngine,
    private val voiceManager: VoiceManager,
    private val vibrationManager: VibrationManager
) : ImageAnalysis.Analyzer {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private var lastFrameTime = 0L
    private var previousCenters = mutableMapOf<String, Float>()

    override fun analyze(image: ImageProxy) {
        val now = System.currentTimeMillis()
        if (now - lastFrameTime < 200L) {
            image.close()
            return
        }
        lastFrameTime = now

        val bitmap = imageProxyToBitmap(image)
        image.close()
        if (bitmap == null) return

        scope.launch {
            val detections = detector.detect(bitmap)
            val newCenters = mutableMapOf<String, Float>()

            detections.forEachIndexed { index, det ->
                val centerX = (det.left + det.right) / 2f
                val id = "${det.label}-$index"
                val previous = previousCenters[id]

                val width = (det.right - det.left).coerceAtLeast(0.01f)
                val estimatedDistance = (2.2f / width).coerceIn(0.5f, 15f)
                val direction = when {
                    centerX < 0.33f -> "left"
                    centerX > 0.66f -> "right"
                    else -> "center"
                }
                val movingToward = previous != null && kotlin.math.abs(previous - centerX) < 0.05f && estimatedDistance < 4f

                newCenters[id] = centerX
                val assessment = riskEngine.assess(
                    TrackedObject(
                        id = id,
                        label = det.label,
                        distanceMeters = estimatedDistance,
                        direction = direction,
                        isMovingTowardUser = movingToward
                    )
                )

                if (assessment.shouldAnnounce) {
                    voiceManager.announceHazard(assessment.message)
                    when (assessment.level) {
                        RiskLevel.HIGH -> vibrationManager.vibrateImmediateHazard()
                        RiskLevel.MEDIUM -> if (movingToward) vibrationManager.vibrateMovingObject() else vibrationManager.vibrateMinor()
                        RiskLevel.LOW -> Unit
                    }
                }
            }
            previousCenters = newCenters
        }
    }

    private fun imageProxyToBitmap(image: ImageProxy): Bitmap? {
        val yBuffer = image.planes[0].buffer
        val uBuffer = image.planes[1].buffer
        val vBuffer = image.planes[2].buffer

        val ySize = yBuffer.remaining()
        val uSize = uBuffer.remaining()
        val vSize = vBuffer.remaining()

        val nv21 = ByteArray(ySize + uSize + vSize)
        yBuffer.get(nv21, 0, ySize)
        vBuffer.get(nv21, ySize, vSize)
        uBuffer.get(nv21, ySize + vSize, uSize)

        val yuvImage = YuvImage(nv21, ImageFormat.NV21, image.width, image.height, null)
        val out = ByteArrayOutputStream()
        yuvImage.compressToJpeg(Rect(0, 0, image.width, image.height), 80, out)
        val bytes = out.toByteArray()
        return BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
    }
}
