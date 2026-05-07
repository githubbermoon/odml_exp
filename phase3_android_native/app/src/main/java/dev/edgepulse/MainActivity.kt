package dev.edgepulse

import android.Manifest
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import dev.edgepulse.data.PerceptionEvent
import dev.edgepulse.network.EventRouter
import dev.edgepulse.ui.EdgePulseScreen

class MainActivity : ComponentActivity() {
    private var latestEvent by mutableStateOf<PerceptionEvent?>(null)
    private var router: EventRouter? = null

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { /* CameraX + MediaPipe graph can start after this in the next phase. */ }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        permissionLauncher.launch(Manifest.permission.CAMERA)

        setContent {
            EdgePulseScreen(
                latestEvent = latestEvent,
                onEndpointChanged = { endpoint ->
                    router?.close()
                    router = EventRouter(endpoint)
                    router?.connect()
                },
                onSendDemo = { gesture ->
                    val event = PerceptionEvent(
                        gesture = gesture,
                        attention = if (gesture == "raised_hand") "focused" else "confused",
                        headPose = if (gesture == "raised_hand") "center" else "tilted_left",
                        confidence = 0.82,
                    )
                    latestEvent = event
                    router?.send(event)
                },
                onCameraEvent = { event ->
                    latestEvent = event
                    router?.send(event)
                },
            )
        }
    }

    override fun onDestroy() {
        router?.close()
        super.onDestroy()
    }
}
