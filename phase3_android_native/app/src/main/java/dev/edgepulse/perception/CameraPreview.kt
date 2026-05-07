package dev.edgepulse.perception

import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.LocalLifecycleOwner
import dev.edgepulse.data.PerceptionEvent
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicLong

@Composable
fun CameraPreview(
    modifier: Modifier = Modifier,
    onEvent: (PerceptionEvent) -> Unit,
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current

    AndroidView(
        modifier = modifier,
        factory = { ctx ->
            val previewView = PreviewView(ctx)
            val cameraProviderFuture = ProcessCameraProvider.getInstance(ctx)
            val executor = Executors.newSingleThreadExecutor()
            val lastEmitMs = AtomicLong(0)

            cameraProviderFuture.addListener(
                {
                    val cameraProvider = cameraProviderFuture.get()
                    val preview = Preview.Builder().build().also {
                        it.setSurfaceProvider(previewView.surfaceProvider)
                    }
                    val analysis = ImageAnalysis.Builder()
                        .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                        .build()

                    analysis.setAnalyzer(executor) { image ->
                        // Production hook: convert ImageProxy to MPImage and run MediaPipe
                        // GestureRecognizer/HandLandmarker here, then emit classified events.
                        val now = System.currentTimeMillis()
                        if (now - lastEmitMs.get() > 350) {
                            lastEmitMs.set(now)
                            onEvent(
                                PerceptionEvent(
                                    gesture = "none",
                                    attention = "focused",
                                    headPose = "center",
                                    confidence = 0.35,
                                ),
                            )
                        }
                        image.close()
                    }

                    cameraProvider.unbindAll()
                    cameraProvider.bindToLifecycle(
                        lifecycleOwner,
                        CameraSelector.DEFAULT_FRONT_CAMERA,
                        preview,
                        analysis,
                    )
                },
                ContextCompat.getMainExecutor(context),
            )

            previewView
        },
    )
}
