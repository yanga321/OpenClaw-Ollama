package com.openclaw.launcher

import android.Manifest
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.hardware.usb.UsbDevice
import android.hardware.usb.UsbManager
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.view.View
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.openclaw.launcher.databinding.ActivityMainBinding
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.util.concurrent.Executor

/**
 * Main Activity - OpenClaw OTG Launcher
 * Handles USB OTG detection, biometric auth, and main UI
 */
class MainActivity : AppCompatActivity() {

    companion object {
        private const val TAG = "MainActivity"
        private const val ACTION_USB_PERMISSION = "com.openclaw.USB_PERMISSION"
    }

    private lateinit var binding: ActivityMainBinding
    private lateinit var usbManager: UsbManager
    private lateinit var biometricExecutor: Executor
    private val handler = Handler(Looper.getMainLooper())
    
    private var currentOtgDevice: UsbDevice? = null
    private var isBiometricAuthenticated = false

    // Permission launcher
    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val allGranted = permissions.all { it.value }
        if (allGranted) {
            Log.d(TAG, "All permissions granted")
            scanForOtgDevice()
        } else {
            showError("Required permissions denied")
        }
    }

    // USB Permission receiver
    private val usbReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            when (intent.action) {
                ACTION_USB_PERMISSION -> {
                    synchronized(this) {
                        val device: UsbDevice? = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                            intent.getParcelableExtra(UsbManager.EXTRA_DEVICE, UsbDevice::class.java)
                        } else {
                            @Suppress("DEPRECATION")
                            intent.getParcelableExtra(UsbManager.EXTRA_DEVICE)
                        }
                        
                        if (intent.getBooleanExtra(UsbManager.EXTRA_PERMISSION_GRANTED, false)) {
                            device?.let {
                                Log.d(TAG, "USB permission granted for: ${it.deviceName}")
                                onOtgConnected(it)
                            }
                        } else {
                            showError("USB permission denied")
                        }
                    }
                }
                UsbManager.ACTION_USB_DEVICE_ATTACHED -> {
                    Log.d(TAG, "USB device attached")
                    scanForOtgDevice()
                }
                UsbManager.ACTION_USB_DEVICE_DETACHED -> {
                    Log.d(TAG, "USB device detached")
                    onOtgDisconnected()
                }
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        initializeComponents()
        requestPermissions()
        setupClickListeners()
    }

    private fun initializeComponents() {
        usbManager = getSystemService(Context.USB_SERVICE) as UsbManager
        biometricExecutor = ContextCompat.getMainExecutor(this)

        // Register USB receiver
        val filter = IntentFilter().apply {
            addAction(ACTION_USB_PERMISSION)
            addAction(UsbManager.ACTION_USB_DEVICE_ATTACHED)
            addAction(UsbManager.ACTION_USB_DEVICE_DETACHED)
        }
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(usbReceiver, filter, Context.RECEIVER_NOT_EXPORTED)
        } else {
            registerReceiver(usbReceiver, filter)
        }

        Log.d(TAG, "Components initialized")
    }

    private fun requestPermissions() {
        val requiredPermissions = arrayOf(
            Manifest.permission.CAMERA,
            Manifest.permission.RECORD_AUDIO
        )

        val permissionsToRequest = requiredPermissions.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }

        if (permissionsToRequest.isNotEmpty()) {
            permissionLauncher.launch(permissionsToRequest.toTypedArray())
        } else {
            scanForOtgDevice()
        }
    }

    private fun scanForOtgDevice() {
        lifecycleScope.launch {
            showStatus("Scanning for OTG Drive...")
            
            val devices = usbManager.deviceList
            Log.d(TAG, "Found ${devices.size} USB devices")

            if (devices.isEmpty()) {
                withContext(Dispatchers.Main) {
                    showError("No OTG Drive Detected. Please connect the drive.")
                    binding.loadingProgress.visibility = View.GONE
                }
                return@launch
            }

            // Find OTG storage device
            for ((key, device) in devices) {
                Log.d(TAG, "USB Device: $key - VendorID: ${device.vendorId}, ProductID: ${device.productId}")
                
                // Check if it's a mass storage device
                if (isOtgDrive(device)) {
                    currentOtgDevice = device
                    withContext(Dispatchers.Main) {
                        requestUsbPermission(device)
                    }
                    return@launch
                }
            }

            withContext(Dispatchers.Main) {
                showError("No compatible OTG Drive found")
                binding.loadingProgress.visibility = View.GONE
            }
        }
    }

    private fun isOtgDrive(device: UsbDevice): Boolean {
        // Check for mass storage class
        for (i in 0 until device.interfaceCount) {
            val iface = device.getInterface(i)
            if (iface.interfaceClass == UsbConstants.USB_CLASS_MASS_STORAGE) {
                return true
            }
        }
        // Also check vendor/product IDs for known OTG drives
        return device.vendorId == 7504 || device.interfaceCount > 0
    }

    private fun requestUsbPermission(device: UsbDevice) {
        if (usbManager.hasPermission(device)) {
            onOtgConnected(device)
        } else {
            val permissionIntent = PendingIntent.getBroadcast(
                this,
                0,
                Intent(ACTION_USB_PERMISSION),
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
            usbManager.requestPermission(device, permissionIntent)
            showStatus("Requesting USB permission...")
        }
    }

    private fun onOtgConnected(device: UsbDevice) {
        Log.d(TAG, "OTG Drive connected: ${device.deviceName}")
        
        // Get the mount path
        val otgPath = getOtgMountPath(device)
        if (otgPath != null) {
            OpenClawApplication.setOtgPath(otgPath)
            Log.d(TAG, "OTG mounted at: $otgPath")
        }

        currentOtgDevice = device
        updateUiForConnectedState()
        
        // Proceed to biometric authentication
        promptBiometricAuth()
    }

    private fun getOtgMountPath(device: UsbDevice): String? {
        // Try common OTG mount paths
        val possiblePaths = listOf(
            "/storage/usbStorage",
            "/mnt/media_rw/sdcard1",
            "/storage/sdcard1",
            "/mnt/usb_storage",
            "/mnt/usbdam",
            File(externalCacheDir?.absolutePath?.replace("/Android/data", "")).parent
        )

        for (path in possiblePaths) {
            val file = File(path)
            if (file.exists() && file.canRead()) {
                Log.d(TAG, "Found accessible path: $path")
                return path
            }
        }

        // Fallback: use external files dir parent
        return externalFilesDir?.parent?.parent
    }

    private fun onOtgDisconnected() {
        Log.d(TAG, "OTG Drive disconnected")
        currentOtgDevice = null
        OpenClawApplication.setOtgPath("")
        isBiometricAuthenticated = false
        
        updateUiForDisconnectedState()
        showStatus("OTG Drive Disconnected")
    }

    private fun promptBiometricAuth() {
        val biometricManager = BiometricManager.from(this)
        
        when (biometricManager.canAuthenticate(BiometricManager.Authenticators.BIOMETRIC_STRONG or 
                BiometricManager.Authenticators.BIOMETRIC_WEAK)) {
            BiometricManager.BIOMETRIC_SUCCESS -> {
                Log.d(TAG, "Biometric auth available")
                showBiometricPrompt()
            }
            BiometricManager.BIOMETRIC_ERROR_NO_HARDWARE -> {
                Log.w(TAG, "No biometric hardware")
                proceedWithoutBiometrics()
            }
            BiometricManager.BIOMETRIC_ERROR_HW_UNAVAILABLE -> {
                Log.w(TAG, "Biometric hardware unavailable")
                proceedWithoutBiometrics()
            }
            BiometricManager.BIOMETRIC_ERROR_NONE_ENROLLED -> {
                Log.w(TAG, "No biometrics enrolled")
                proceedWithoutBiometrics()
            }
            else -> {
                proceedWithoutBiometrics()
            }
        }
    }

    private fun showBiometricPrompt() {
        val prompt = BiometricPrompt(this, biometricExecutor,
            object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                    super.onAuthenticationSucceeded(result)
                    Log.d(TAG, "Biometric authentication succeeded")
                    isBiometricAuthenticated = true
                    onAuthenticationSuccess()
                }

                override fun onAuthenticationFailed() {
                    super.onAuthenticationFailed()
                    Log.w(TAG, "Biometric authentication failed")
                    Toast.makeText(this@MainActivity, "Authentication failed", Toast.LENGTH_SHORT).show()
                }

                override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                    super.onAuthenticationError(errorCode, errString)
                    if (errorCode == BiometricPrompt.ERROR_USER_CANCELED || 
                        errorCode == BiometricPrompt.ERROR_NEGATIVE_BUTTON) {
                        Log.w(TAG, "User canceled biometric auth")
                        proceedWithoutBiometrics()
                    } else {
                        showError("Authentication error: $errString")
                    }
                }
            })

        val info = BiometricPrompt.PromptInfo.Builder()
            .setTitle(getString(R.string.biometric_prompt))
            .setSubtitle(getString(R.string.biometric_subtitle))
            .setNegativeButtonText(getString(R.string.biometric_negative))
            .build()

        prompt.authenticate(info)
    }

    private fun proceedWithoutBiometrics() {
        Log.w(TAG, "Proceeding without biometric authentication")
        isBiometricAuthenticated = true
        onAuthenticationSuccess()
    }

    private fun onAuthenticationSuccess() {
        showStatus("Initializing AI Engine...")
        loadAiModels()
    }

    private fun loadAiModels() {
        lifecycleScope.launch {
            showStatus("Loading AI Models...")
            
            withContext(Dispatchers.IO) {
                // Simulate model loading delay
                Thread.sleep(2000)
                
                // Check for models on OTG drive
                val modelsDir = OpenClawApplication.modelsDirectory
                if (modelsDir != null && modelsDir.exists()) {
                    val modelFiles = modelsDir.listFiles { file -> 
                        file.extension == "gguf" 
                    } ?: emptyArray()
                    
                    Log.d(TAG, "Found ${modelFiles.size} GGUF models")
                    
                    if (modelFiles.isNotEmpty()) {
                        withContext(Dispatchers.Main) {
                            binding.modelInfo.text = "Model: ${modelFiles.first().name}"
                            binding.modelInfo.setTextColor(ContextCompat.getColor(this@MainActivity, R.color.success))
                        }
                    }
                }
            }

            withContext(Dispatchers.Main) {
                binding.loadingProgress.visibility = View.GONE
                binding.statusMessage.text = getString(R.string.ready)
                binding.statusMessage.setTextColor(ContextCompat.getColor(this@MainActivity, R.color.success))
                updateSystemInfo()
            }
        }
    }

    private fun updateSystemInfo() {
        val runtime = Runtime.getRuntime()
        val totalMemory = runtime.totalMemory() / (1024 * 1024)
        val freeMemory = runtime.freeMemory() / (1024 * 1024)
        val usedMemory = totalMemory - freeMemory

        binding.memoryInfo.text = "RAM: ${usedMemory}MB / ${totalMemory}MB"
        
        // Get temperature (simulated for now)
        binding.tempInfo.text = "Temperature: 35°C"
    }

    private fun setupClickListeners() {
        binding.chatCard.setOnClickListener {
            if (isReady()) {
                Toast.makeText(this, "Opening Chat Mode...", Toast.LENGTH_SHORT).show()
                // TODO: Open chat activity
            } else {
                showError("Please wait for initialization")
            }
        }

        binding.arCard.setOnClickListener {
            if (isReady()) {
                val intent = Intent(this, Class.forName("com.openclaw.launcher.ar.ARCameraActivity"))
                startActivity(intent)
            } else {
                showError("Please wait for initialization")
            }
        }

        binding.swarmCard.setOnClickListener {
            if (isReady()) {
                Toast.makeText(this, "Swarm Mode: Scanning for peers...", Toast.LENGTH_SHORT).show()
                // TODO: Start swarm discovery
            } else {
                showError("Please wait for initialization")
            }
        }

        binding.settingsCard.setOnClickListener {
            Toast.makeText(this, "Opening Settings...", Toast.LENGTH_SHORT).show()
            // TODO: Open settings activity
        }

        binding.navPanic.setOnClickListener {
            showPanicConfirmation()
        }
    }

    private fun isReady(): Boolean {
        return isBiometricAuthenticated && OpenClawApplication.isOtgMounted()
    }

    private fun showPanicConfirmation() {
        // Show confirmation dialog before panic wipe
        androidx.appcompat.app.AlertDialog.Builder(this)
            .setTitle("⚠️ PANIC WIPE")
            .setMessage("This will permanently delete all data on the OTG drive. Are you sure?")
            .setPositiveButton("YES, WIPE EVERYTHING") { _, _ ->
                executePanicWipe()
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun executePanicWipe() {
        lifecycleScope.launch {
            showStatus("Executing Panic Wipe...")
            
            withContext(Dispatchers.IO) {
                val dataDir = OpenClawApplication.dataDirectory
                val modelsDir = OpenClawApplication.modelsDirectory
                
                // Delete all data
                dataDir?.deleteRecursively()
                modelsDir?.deleteRecursively()
                
                Log.e(TAG, "PANIC WIPE EXECUTED")
            }
            
            withContext(Dispatchers.Main) {
                Toast.makeText(this@MainActivity, getString(R.string.panic_wipe), Toast.LENGTH_LONG).show()
                finish()
            }
        }
    }

    private fun updateUiForConnectedState() {
        binding.otgStatusIcon.setImageResource(R.drawable.ic_usb_connected)
        binding.otgStatusText.text = getString(R.string.otg_connected)
        binding.otgStatusText.setTextColor(ContextCompat.getColor(this, R.color.success))
        binding.actionsGrid.visibility = View.VISIBLE
    }

    private fun updateUiForDisconnectedState() {
        binding.otgStatusIcon.setImageResource(R.drawable.ic_usb)
        binding.otgStatusText.text = getString(R.string.otg_disconnected)
        binding.otgStatusText.setTextColor(ContextCompat.getColor(this, R.color.error))
        binding.statusMessage.text = getString(R.string.error_otg_not_found)
        binding.statusMessage.setTextColor(ContextCompat.getColor(this, R.color.error))
        binding.loadingProgress.visibility = View.GONE
        binding.actionsGrid.visibility = View.GONE
        binding.modelInfo.text = "Model: Not Loaded"
        binding.modelInfo.setTextColor(ContextCompat.getColor(this, R.color.warning))
    }

    private fun showStatus(message: String) {
        binding.statusMessage.text = message
        binding.statusMessage.setTextColor(ContextCompat.getColor(this, R.color.white))
    }

    private fun showError(message: String) {
        binding.statusMessage.text = message
        binding.statusMessage.setTextColor(ContextCompat.getColor(this, R.color.error))
        Toast.makeText(this, message, Toast.LENGTH_LONG).show()
    }

    override fun onDestroy() {
        super.onDestroy()
        try {
            unregisterReceiver(usbReceiver)
        } catch (e: Exception) {
            Log.w(TAG, "Receiver not registered", e)
        }
    }

    override fun onResume() {
        super.onResume()
        if (currentOtgDevice != null) {
            updateSystemInfo()
        }
    }
}
