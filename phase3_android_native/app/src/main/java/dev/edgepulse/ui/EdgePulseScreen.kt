package dev.edgepulse.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.weight
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import dev.edgepulse.data.PerceptionEvent
import dev.edgepulse.perception.CameraPreview

@Composable
fun EdgePulseScreen(
    latestEvent: PerceptionEvent?,
    onEndpointChanged: (String) -> Unit,
    onSendDemo: (String) -> Unit,
    onCameraEvent: (PerceptionEvent) -> Unit,
) {
    var endpoint by remember { mutableStateOf("ws://100.x.y.z:8765/ws/events") }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFF071014))
            .padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Text("EdgePulse", color = Color.White, style = MaterialTheme.typography.headlineLarge)
        Text("Android sensor hub. MediaPipe events route privately over Tailscale.", color = Color(0xFF9BB2C3))

        OutlinedTextField(
            value = endpoint,
            onValueChange = {
                endpoint = it
                onEndpointChanged(it)
            },
            label = { Text("Mac Tailscale WebSocket URL") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )

        Surface(
            color = Color.Black,
            shape = RoundedCornerShape(8.dp),
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f),
        ) {
            CameraPreview(
                modifier = Modifier.fillMaxSize(),
                onEvent = onCameraEvent,
            )
        }

        Surface(
            color = Color(0xFF101C24),
            shape = RoundedCornerShape(8.dp),
            modifier = Modifier.fillMaxWidth(),
        ) {
            Column(Modifier.padding(16.dp)) {
                Text("Latest event", color = Color(0xFF75E6B0))
                Spacer(Modifier.height(8.dp))
                Text("gesture: ${latestEvent?.gesture ?: "waiting"}", color = Color.White)
                Text("attention: ${latestEvent?.attention ?: "unknown"}", color = Color.White)
                Text("head pose: ${latestEvent?.headPose ?: "unknown"}", color = Color.White)
            }
        }

        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Button(onClick = { onSendDemo("raised_hand") }) { Text("Raised hand") }
            Button(onClick = { onSendDemo("pointing") }) { Text("Pointing") }
        }
    }
}
