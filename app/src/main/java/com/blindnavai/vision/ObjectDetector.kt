package com.blindnavai.vision

import android.content.Context
import android.graphics.Bitmap
import org.tensorflow.lite.Interpreter
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.exp

data class Detection(
    val label: String,
    val score: Float,
    val left: Float,
    val top: Float,
    val right: Float,
    val bottom: Float
)

class ObjectDetector(
    context: Context,
    modelAssetName: String,
    private val labels: List<String> = cocoLabels
) : AutoCloseable {

    private val inputSize = 640
    private val interpreter: Interpreter

    init {
        val modelBuffer = context.assets.open(modelAssetName).use { it.readBytes() }
        val options = Interpreter.Options().apply { setNumThreads(4) }
        interpreter = Interpreter(ByteBuffer.wrap(modelBuffer), options)
    }

    fun detect(bitmap: Bitmap, threshold: Float = 0.4f): List<Detection> {
        val scaled = Bitmap.createScaledBitmap(bitmap, inputSize, inputSize, true)
        val input = preprocess(scaled)

        val output = Array(1) { Array(84) { FloatArray(8400) } }
        interpreter.run(input, output)

        val detections = mutableListOf<Detection>()
        for (i in 0 until 8400) {
            val cx = output[0][0][i]
            val cy = output[0][1][i]
            val w = output[0][2][i]
            val h = output[0][3][i]

            var bestClass = -1
            var bestScore = 0f
            for (c in 4 until 84) {
                val score = sigmoid(output[0][c][i])
                if (score > bestScore) {
                    bestScore = score
                    bestClass = c - 4
                }
            }

            if (bestClass >= 0 && bestScore >= threshold) {
                detections.add(
                    Detection(
                        label = labels.getOrElse(bestClass) { "object" },
                        score = bestScore,
                        left = (cx - w / 2f).coerceIn(0f, 1f),
                        top = (cy - h / 2f).coerceIn(0f, 1f),
                        right = (cx + w / 2f).coerceIn(0f, 1f),
                        bottom = (cy + h / 2f).coerceIn(0f, 1f)
                    )
                )
            }
        }
        return detections.sortedByDescending { it.score }.take(10)
    }

    private fun preprocess(bitmap: Bitmap): ByteBuffer {
        val buffer = ByteBuffer.allocateDirect(1 * inputSize * inputSize * 3 * 4)
            .order(ByteOrder.nativeOrder())
        val pixels = IntArray(inputSize * inputSize)
        bitmap.getPixels(pixels, 0, inputSize, 0, 0, inputSize, inputSize)
        for (pixel in pixels) {
            buffer.putFloat(((pixel shr 16) and 0xFF) / 255f)
            buffer.putFloat(((pixel shr 8) and 0xFF) / 255f)
            buffer.putFloat((pixel and 0xFF) / 255f)
        }
        buffer.rewind()
        return buffer
    }

    private fun sigmoid(x: Float): Float = (1f / (1f + exp(-x)))

    override fun close() {
        interpreter.close()
    }

    companion object {
        private val cocoLabels = listOf(
            "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat", "traffic light",
            "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", "cow",
            "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
            "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket", "bottle",
            "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
            "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch", "potted plant", "bed",
            "dining table", "toilet", "tv", "laptop", "mouse", "remote", "keyboard", "cell phone", "microwave", "oven",
            "toaster", "sink", "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier", "toothbrush"
        )
    }
}
