package com.blindnavai

import android.Manifest
import android.content.pm.PackageManager
import android.location.Location
import android.os.Bundle
import android.os.Looper
import android.widget.Button
import android.widget.TextView
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.core.content.ContextCompat
import com.blindnavai.emergency.EmergencyHandler
import com.blindnavai.haptic.VibrationManager
import com.blindnavai.navigation.NavigationEngine
import com.blindnavai.risk.RiskEngine
import com.blindnavai.voice.VoiceManager
import com.blindnavai.vision.FrameProcessor
import com.blindnavai.vision.ObjectDetector
import com.google.android.gms.location.LocationCallback
import com.google.android.gms.location.LocationRequest
import com.google.android.gms.location.LocationResult
import com.google.android.gms.location.LocationServices
import org.osmdroid.config.Configuration
import org.osmdroid.tileprovider.tilesource.TileSourceFactory
import org.osmdroid.util.GeoPoint
import org.osmdroid.views.MapView

class MainActivity : AppCompatActivity() {
    private val fusedLocation by lazy { LocationServices.getFusedLocationProviderClient(this) }

    private lateinit var previewView: PreviewView
    private lateinit var mapView: MapView
    private lateinit var statusText: TextView

    private lateinit var voiceManager: VoiceManager
    private lateinit var vibrationManager: VibrationManager
    private lateinit var riskEngine: RiskEngine
    private lateinit var objectDetector: ObjectDetector
    private lateinit var frameProcessor: FrameProcessor
    private lateinit var navigationEngine: NavigationEngine
    private lateinit var emergencyHandler: EmergencyHandler

    private var currentLocation: Location? = null

    private val locationCallback = object : LocationCallback() {
        override fun onLocationResult(result: LocationResult) {
            val location = result.lastLocation ?: return
            currentLocation = location
            val point = GeoPoint(location.latitude, location.longitude)
            mapView.controller.setZoom(18.0)
            mapView.controller.setCenter(point)
            navigationEngine.updateCurrentLocation(point)
        }
    }

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { startIfReady() }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        Configuration.getInstance().load(
            applicationContext,
            getSharedPreferences("osmdroid", MODE_PRIVATE)
        )

        previewView = findViewById(R.id.previewView)
        mapView = findViewById(R.id.mapView)
        statusText = findViewById(R.id.statusText)

        voiceManager = VoiceManager(this)
        vibrationManager = VibrationManager(this)
        riskEngine = RiskEngine()
        objectDetector = ObjectDetector(this, "yolov8n.tflite")
        frameProcessor = FrameProcessor(objectDetector, riskEngine, voiceManager, vibrationManager)
        navigationEngine = NavigationEngine(this, mapView, voiceManager)
        emergencyHandler = EmergencyHandler(this, fusedLocation, voiceManager)

        mapView.setTileSource(TileSourceFactory.MAPNIK)
        mapView.setMultiTouchControls(true)

        findViewById<Button>(R.id.emergencyButton).setOnLongClickListener {
            emergencyHandler.trigger(currentLocation)
            true
        }

        requestPermissionsIfNeeded()
    }

    private fun requestPermissionsIfNeeded() {
        val requiredPermissions = arrayOf(
            Manifest.permission.CAMERA,
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.SEND_SMS,
            Manifest.permission.VIBRATE
        )
        val missing = requiredPermissions.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }
        if (missing.isEmpty()) startIfReady() else permissionLauncher.launch(missing.toTypedArray())
    }

    private fun startIfReady() {
        if (!hasPermission(Manifest.permission.CAMERA) || !hasPermission(Manifest.permission.ACCESS_FINE_LOCATION)) {
            statusText.text = "Permissions required for camera and location."
            return
        }

        startCamera()
        startLocationAndNavigation()
    }

    private fun hasPermission(permission: String): Boolean {
        return ContextCompat.checkSelfPermission(this, permission) == PackageManager.PERMISSION_GRANTED
    }

    private fun startCamera() {
        val providerFuture = ProcessCameraProvider.getInstance(this)
        providerFuture.addListener({
            val provider = providerFuture.get()
            val preview = Preview.Builder().build().also {
                it.surfaceProvider = previewView.surfaceProvider
            }
            val analysis = ImageAnalysis.Builder()
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build()
                .also {
                    it.setAnalyzer(ContextCompat.getMainExecutor(this), frameProcessor)
                }
            provider.unbindAll()
            provider.bindToLifecycle(this, CameraSelector.DEFAULT_BACK_CAMERA, preview, analysis)
        }, ContextCompat.getMainExecutor(this))
    }

    private fun startLocationAndNavigation() {
        val request = LocationRequest.Builder(4_000L)
            .setMinUpdateIntervalMillis(2_000L)
            .setPriority(LocationRequest.PRIORITY_BALANCED_POWER_ACCURACY)
            .build()

        fusedLocation.requestLocationUpdates(request, locationCallback, Looper.getMainLooper())

        navigationEngine.startNavigation(
            destination = GeoPoint(37.4219983, -122.084),
            onStatus = { status -> statusText.text = status }
        )
    }

    override fun onResume() {
        super.onResume()
        mapView.onResume()
    }

    override fun onPause() {
        super.onPause()
        mapView.onPause()
    }

    override fun onDestroy() {
        super.onDestroy()
        fusedLocation.removeLocationUpdates(locationCallback)
        voiceManager.shutdown()
        objectDetector.close()
    }
}
