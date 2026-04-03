package com.openclaw.launcher

import android.app.Application
import android.content.Context
import android.util.Log
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.SupervisorJob
import java.io.File

/**
 * Application class for OpenClaw OTG Launcher
 * Handles global app state and initialization
 */
class OpenClawApplication : Application() {

    companion object {
        private const val TAG = "OpenClawApp"
        
        // Application-wide Coroutine scope
        lateinit var applicationScope: CoroutineScope
            private set
        
        // App context reference
        lateinit var appContext: Context
            private set
            
        // OTG Drive root path
        var otgRootPath: String? = null
            private set
        
        // Models directory on OTG
        val modelsDirectory: File?
            get() = otgRootPath?.let { File(it, "models") }
        
        // Data directory on OTG
        val dataDirectory: File?
            get() = otgRootPath?.let { File(it, "data") }
        
        // Initialize OTG path
        fun setOtgPath(path: String) {
            otgRootPath = path
            Log.d(TAG, "OTG path set to: $path")
        }
        
        // Check if OTG is mounted
        fun isOtgMounted(): Boolean {
            return otgRootPath != null && File(otgRootPath!!).exists()
        }
    }

    override fun onCreate() {
        super.onCreate()
        
        appContext = applicationContext
        applicationScope = CoroutineScope(SupervisorJob())
        
        Log.d(TAG, "OpenClaw Application initialized")
        
        // Create necessary directories
        setupDirectories()
    }

    private fun setupDirectories() {
        // Internal app directories
        val filesDir = applicationContext.filesDir
        val cacheDir = applicationContext.cacheDir
        
        // Ensure directories exist
        filesDir.mkdirs()
        cacheDir.mkdirs()
        
        Log.d(TAG, "Internal storage ready: ${filesDir.absolutePath}")
    }

    override fun onTerminate() {
        super.onTerminate()
        Log.d(TAG, "Application terminating")
        applicationScope.cancel()
    }

    override fun onLowMemory() {
        super.onLowMemory()
        Log.w(TAG, "Low memory warning")
        // Trigger memory cleanup
        System.gc()
    }
}
