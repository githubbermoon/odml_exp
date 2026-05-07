package dev.edgepulse.network

import dev.edgepulse.data.PerceptionEvent
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import java.util.concurrent.TimeUnit

class EventRouter(
    private val endpoint: String,
) {
    private val json = Json { encodeDefaults = true }
    private val client = OkHttpClient.Builder()
        .pingInterval(20, TimeUnit.SECONDS)
        .build()

    private var socket: WebSocket? = null

    fun connect() {
        if (socket != null) return
        val request = Request.Builder().url(endpoint).build()
        socket = client.newWebSocket(request, object : WebSocketListener() {})
    }

    fun send(event: PerceptionEvent) {
        connect()
        socket?.send(json.encodeToString(event))
    }

    fun close() {
        socket?.close(1000, "EdgePulse stopped")
        socket = null
    }
}
