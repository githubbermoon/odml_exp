package dev.edgepulse.data

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import java.util.UUID

@Serializable
data class PerceptionEvent(
    val source: String = "android-s21-fe",
    val gesture: String = "none",
    val attention: String = "unknown",
    val duration: Double = 0.0,
    @SerialName("head_pose") val headPose: String = "unknown",
    val context: String = "coding",
    val confidence: Double = 0.0,
    val landmarks: Map<String, String> = emptyMap(),
    val ts: Double = System.currentTimeMillis() / 1000.0,
    @SerialName("event_id") val eventId: String = UUID.randomUUID().toString(),
)
