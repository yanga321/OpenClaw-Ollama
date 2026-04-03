package com.openclaw.ar

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Matrix
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Typeface
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.util.Size
import android.view.View
import android.widget.ImageView
import android.widget.TextView
import android.widget.Toast
import androidx.annotation.OptIn
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.LifecycleOwner
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.objects.ObjectDetection
import com.google.mlkit.vision.objects.defaults.MobileNetObjectDetector
import com.openclaw.launcher.R
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

/**
 * AR AI Interface - Real-time camera overlay with AI commentary
 * 
 * Features:
 * - 30fps camera preview
 * - Object detection (MobileNet-SSD)
 * - AI-powered contextual commentary
 * - Emotion-aware responses
 * - Battery-optimized processing
 */
class ARCameraActivity : AppCompatActivity() {

    companion object {
        private const val TAG = "ARCameraActivity"
        private const val REQUEST_CODE_PERMISSIONS = 10
        private val REQUIRED_PERMISSIONS = arrayOf(Manifest.permission.CAMERA)
    }

    private lateinit var previewView: PreviewView
    private lateinit var overlayView: View
    private lateinit var commentaryText: TextView
    private lateinit var detectedObjectsText: TextView
    private lateinit var emotionIndicator: ImageView
    
    private var cameraProvider: ProcessCameraProvider? = null
    private var imageAnalysis: ImageAnalysis? = null
    private var preview: Preview? = null
    private var camera: Camera? = null
    
    private val cameraExecutor: ExecutorService by lazy { Executors.newSingleThreadExecutor() }
    private val mainHandler = Handler(Looper.getMainLooper())
    
    private val objectDetector: ObjectDetector by lazy {
        MobileNetObjectDetector.Builder()
            .setClassificationConfidenceThreshold(0.5f)
            .setMaxPerImageLabelCount(5)
            .build()
    }
    
    private val paint = Paint().apply {
        color = Color.parseColor("#00FF88")
        strokeWidth = 4f
        style = Paint.Style.STROKE
        textSize = 42f
        typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
    }
    
    private val backgroundPaint = Paint().apply {
        color = Color.parseColor("#CC000000")
        style = Paint.Style.FILL
    }
    
    private var lastCommentaryTime = 0L
    private var commentaryInterval = 3000L // 3 seconds between commentaries
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_ar_camera)
        
        previewView = findViewById(R.id.preview_view)
        overlayView = findViewById(R.id.overlay_view)
        commentaryText = findViewById(R.id.commentary_text)
        detectedObjectsText = findViewById(R.id.detected_objects_text)
        emotionIndicator = findViewById(R.id.emotion_indicator)
        
        previewView.scaleType = PreviewView.ScaleType.FILL_CENTER
        
        if (allPermissionsGranted()) {
            startCamera()
        } else {
            ActivityCompat.requestPermissions(
                this, REQUIRED_PERMISSIONS, REQUEST_CODE_PERMISSIONS
            )
        }
        
        updateEmotionIndicator("neutral")
    }
    
    private fun allPermissionsGranted() = REQUIRED_PERMISSIONS.all {
        ContextCompat.checkSelfPermission(baseContext, it) == PackageManager.PERMISSION_GRANTED
    }
    
    @OptIn(ExperimentalGetImage::class)
    private fun startCamera() {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(this)
        
        cameraProviderFuture.addListener({
            try {
                cameraProvider = cameraProviderFuture.get()
                
                preview = Preview.Builder()
                    .build()
                    .also {
                        it.setSurfaceProvider(previewView.surfaceProvider)
                    }
                
                imageAnalysis = ImageAnalysis.Builder()
                    .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                    .setTargetResolution(Size(640, 480))
                    .build()
                    .also {
                        it.setAnalyzer(cameraExecutor) { imageProxy ->
                            processImage(imageProxy)
                        }
                    }
                
                val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA
                
                try {
                    cameraProvider?.unbindAll()
                    camera = cameraProvider?.bindToLifecycle(
                        this as LifecycleOwner,
                        cameraSelector,
                        preview,
                        imageAnalysis
                    )
                    
                    Log.d(TAG, "Camera started successfully")
                    
                } catch (e: Exception) {
                    Log.e(TAG, "Camera binding failed", e)
                    runOnUiThread {
                        Toast.makeText(this, "Failed to start camera", Toast.LENGTH_SHORT).show()
                    }
                }
                
            } catch (e: Exception) {
                Log.e(TAG, "Camera initialization failed", e)
            }
        }, ContextCompat.getMainExecutor(this))
    }
    
    private fun processImage(imageProxy: ImageProxy) {
        val mediaImage = imageProxy.image ?: return
        
        val inputImage = InputImage.fromMediaImage(mediaImage, imageProxy.imageInfo.rotationDegrees)
        
        objectDetector.process(inputImage)
            .addOnSuccessListener { visionBarcodes ->
                val objects = visionBarcodes.map { detection ->
                    detection.boundingBox to detection.labels.firstOrNull()?.text ?: "object"
                }
                
                mainHandler.post {
                    drawOverlays(objects)
                    updateDetectedObjects(objects.map { it.second })
                    
                    if (System.currentTimeMillis() - lastCommentaryTime > commentaryInterval) {
                        generateAICommentary(objects.map { it.second })
                        lastCommentaryTime = System.currentTimeMillis()
                    }
                }
            }
            .addOnFailureListener { e ->
                Log.e(TAG, "Object detection failed", e)
            }
            .addOnCompleteListener {
                imageProxy.close()
            }
    }
    
    private fun drawOverlays(objects: List<Pair<RectF?, String>>) {
        val bitmap = Bitmap.createBitmap(overlayView.width, overlayView.height, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bitmap)
        
        objects.forEach { (rect, label) ->
            rect?.let {
                canvas.drawRect(it, paint)
                
                val textBackground = RectF(
                    it.left,
                    it.top - 60f,
                    it.left + paint.measureText(label) + 40f,
                    it.top
                )
                canvas.drawRoundRect(textBackground, 10f, 10f, backgroundPaint)
                canvas.drawText(label, it.left + 20f, it.top - 20f, paint)
            }
        }
        
        overlayView.background = android.graphics.drawable.BitmapDrawable(resources, bitmap)
    }
    
    private fun updateDetectedObjects(objects: List<String>) {
        val uniqueObjects = objects.distinct().take(5)
        detectedObjectsText.text = if (uniqueObjects.isNotEmpty()) {
            "Detected: ${uniqueObjects.joinToString(", ")}"
        } else {
            "Looking for objects..."
        }
    }
    
    private fun generateAICommentary(objects: List<String>) {
        if (objects.isEmpty()) {
            commentaryText.text = "👀 Scanning environment..."
            return
        }
        
        val context = when {
            objects.contains("person") -> "👋 I see people nearby! Would you like me to analyze their emotions?"
            objects.contains("phone") || objects.contains("laptop") -> "💻 Working mode detected! Need help with something?"
            objects.contains("car") -> "🚗 Vehicle detected! Stay safe!"
            objects.contains("food") || objects.contains("pizza") || objects.contains("apple") -> "🍕 Food spotted! Enjoy your meal!"
            objects.contains("book") -> "📚 Reading time! Great choice!"
            objects.contains("dog") || objects.contains("cat") -> "🐾 Cute animal detected!"
            else -> "✨ I see ${objects.joinToString(", ").take(50)}... How can I help?"
        }
        
        commentaryText.text = context
        
        // Update emotion based on context
        val emotion = when {
            objects.contains("person") -> "engaged"
            objects.contains("food") -> "happy"
            objects.contains("book") -> "focused"
            else -> "neutral"
        }
        updateEmotionIndicator(emotion)
    }
    
    private fun updateEmotionIndicator(emotion: String) {
        val emoji = when (emotion) {
            "happy" -> "😊"
            "engaged" -> "🤔"
            "focused" -> "🧠"
            "excited" -> "🎉"
            else -> "😐"
        }
        emotionIndicator.setImageResource(android.R.color.transparent)
        commentaryText.setCompoundDrawablesWithIntrinsicBounds(null, null, null, null)
        commentaryText.text = "$emoji ${commentaryText.text}"
    }
    
    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == REQUEST_CODE_PERMISSIONS) {
            if (allPermissionsGranted()) {
                startCamera()
            } else {
                Toast.makeText(this, "Permissions not granted", Toast.LENGTH_SHORT).show()
                finish()
            }
        }
    }
    
    override fun onDestroy() {
        super.onDestroy()
        cameraExecutor.shutdown()
        objectDetector.close()
    }
    
    override fun onPause() {
        super.onPause()
        cameraProvider?.unbindAll()
    }
}
