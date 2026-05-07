package dev.edgepulse.perception

import dev.edgepulse.data.PerceptionEvent

data class HandSignal(
    val indexExtended: Boolean,
    val middleExtended: Boolean,
    val ringExtended: Boolean,
    val pinkyExtended: Boolean,
    val thumbExtended: Boolean,
    val wristY: Float,
    val averageTipY: Float,
)

object GestureHeuristics {
    fun classify(signal: HandSignal?, faceTilt: Float?, source: String = "android-s21-fe"): PerceptionEvent {
        val gesture = when {
            signal == null -> "none"
            signal.indexExtended && signal.middleExtended && signal.ringExtended && signal.pinkyExtended &&
                signal.averageTipY < signal.wristY - 0.18f -> "raised_hand"
            signal.indexExtended && !signal.middleExtended && !signal.ringExtended && !signal.pinkyExtended -> "pointing"
            signal.thumbExtended && !signal.indexExtended && !signal.middleExtended && !signal.ringExtended && !signal.pinkyExtended -> "thumbs_up"
            signal.indexExtended && signal.middleExtended && signal.ringExtended && signal.pinkyExtended -> "open_palm"
            else -> "none"
        }

        val headPose = when {
            faceTilt == null -> "unknown"
            faceTilt > 0.035f -> "tilted_left"
            faceTilt < -0.035f -> "tilted_right"
            else -> "center"
        }

        val attention = when (headPose) {
            "center" -> "focused"
            "tilted_left", "tilted_right" -> "confused"
            else -> "unknown"
        }

        return PerceptionEvent(
            source = source,
            gesture = gesture,
            attention = attention,
            headPose = headPose,
            confidence = if (gesture == "none") 0.45 else 0.80,
        )
    }
}
