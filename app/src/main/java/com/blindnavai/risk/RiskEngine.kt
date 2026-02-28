package com.blindnavai.risk

enum class RiskLevel { LOW, MEDIUM, HIGH }

data class TrackedObject(
    val id: String,
    val label: String,
    val distanceMeters: Float,
    val direction: String,
    val isMovingTowardUser: Boolean
)

data class RiskAssessment(val level: RiskLevel, val message: String, val shouldAnnounce: Boolean)

class RiskEngine {
    private val cooldownMs = 3_000L
    private val lastAnnouncement = mutableMapOf<String, Long>()

    fun assess(obj: TrackedObject, nowMs: Long = System.currentTimeMillis()): RiskAssessment {
        val level = when {
            obj.distanceMeters < 1.8f && obj.isMovingTowardUser -> RiskLevel.HIGH
            obj.distanceMeters < 1.2f -> RiskLevel.HIGH
            obj.distanceMeters < 3.5f && obj.direction == "center" -> RiskLevel.MEDIUM
            obj.isMovingTowardUser && obj.distanceMeters < 5.0f -> RiskLevel.MEDIUM
            else -> RiskLevel.LOW
        }

        val message = when {
            obj.label.contains("car", ignoreCase = true) && obj.isMovingTowardUser ->
                "Car approaching from ${obj.direction}"
            obj.label.contains("stairs", ignoreCase = true) -> "Stairs detected ahead"
            level == RiskLevel.HIGH -> "Obstacle ahead"
            level == RiskLevel.MEDIUM -> "Caution, ${obj.label} on ${obj.direction}"
            else -> "Clear path"
        }

        val shouldAnnounce = when (level) {
            RiskLevel.HIGH -> allowByCooldown(obj.id, nowMs)
            RiskLevel.MEDIUM -> (obj.direction == "center" || obj.isMovingTowardUser) && allowByCooldown(obj.id, nowMs)
            RiskLevel.LOW -> false
        }

        return RiskAssessment(level, message, shouldAnnounce)
    }

    private fun allowByCooldown(objectId: String, nowMs: Long): Boolean {
        val last = lastAnnouncement[objectId] ?: 0L
        return if (nowMs - last >= cooldownMs) {
            lastAnnouncement[objectId] = nowMs
            true
        } else {
            false
        }
    }
}
