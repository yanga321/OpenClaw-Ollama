package com.openclaw.swarm

import android.content.Context
import android.net.wifi.WifiManager
import android.util.Log
import kotlinx.coroutines.*
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import java.util.concurrent.ConcurrentHashMap

/**
 * Swarm Connector - OTG-to-OTG Peer Discovery & Mesh Networking
 * 
 * Features:
 * - UDP broadcast discovery
 * - Peer-to-peer communication
 * - Distributed compute marketplace
 * - Credit-based incentive system
 */
class SwarmConnector(private val context: Context) {

    companion object {
        private const val TAG = "SwarmConnector"
        private const val DISCOVERY_PORT = 8765
        private const val BROADCAST_INTERVAL_MS = 5000L
        private const val PEER_TIMEOUT_MS = 15000L
    }

    private val wifiManager: WifiManager by lazy {
        context.applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
    }

    private val peers = ConcurrentHashMap<String, PeerInfo>()
    private var isDiscovering = false
    private var discoveryJob: Job? = null
    private var broadcastJob: Job? = null
    
    private val onPeerDiscoveredListener: ((PeerInfo) -> Unit)? = null
    private val onPeerLostListener: ((String) -> Unit)? = null

    data class PeerInfo(
        val deviceId: String,
        val deviceName: String,
        val ipAddress: String,
        val port: Int,
        val capabilities: List<String>,
        val credits: Int,
        val lastSeen: Long
    )

    /**
     * Start peer discovery via UDP broadcast
     */
    fun startDiscovery() {
        if (isDiscovering) return
        
        isDiscovering = true
        Log.d(TAG, "Starting peer discovery...")
        
        discoveryJob = CoroutineScope(Dispatchers.IO).launch {
            try {
                val socket = DatagramSocket(DISCOVERY_PORT)
                socket.broadcast = true
                socket.soTimeout = 1000
                
                while (isDiscovering) {
                    try {
                        val buffer = ByteArray(1024)
                        val packet = DatagramPacket(buffer, buffer.size)
                        socket.receive(packet)
                        
                        val message = String(buffer, 0, packet.length)
                        handleDiscoveryMessage(message, packet.address.hostAddress ?: "")
                        
                    } catch (e: Exception) {
                        if (isDiscovering) {
                            Log.e(TAG, "Error receiving discovery packet", e)
                        }
                    }
                }
                
                socket.close()
            } catch (e: Exception) {
                Log.e(TAG, "Failed to start discovery socket", e)
            }
        }
        
        broadcastJob = CoroutineScope(Dispatchers.IO).launch {
            while (isDiscovering) {
                broadcastPresence()
                delay(BROADCAST_INTERVAL_MS)
            }
        }
    }

    /**
     * Stop peer discovery
     */
    fun stopDiscovery() {
        isDiscovering = false
        discoveryJob?.cancel()
        broadcastJob?.cancel()
        Log.d(TAG, "Stopped peer discovery")
    }

    /**
     * Broadcast own presence to network
     */
    private fun broadcastPresence() {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val socket = DatagramSocket()
                socket.broadcast = true
                
                val broadcastAddress = getBroadcastAddress() ?: return@launch
                val message = buildPresenceMessage()
                
                val buffer = message.toByteArray()
                val packet = DatagramPacket(buffer, buffer.size, broadcastAddress, DISCOVERY_PORT)
                socket.send(packet)
                socket.close()
                
                Log.d(TAG, "Broadcasted presence: $message")
            } catch (e: Exception) {
                Log.e(TAG, "Failed to broadcast presence", e)
            }
        }
    }

    /**
     * Handle incoming discovery message
     */
    private fun handleDiscoveryMessage(message: String, senderIp: String) {
        try {
            val parts = message.split("|")
            if (parts.size < 5) return
            
            val peerInfo = PeerInfo(
                deviceId = parts[0],
                deviceName = parts[1],
                ipAddress = senderIp,
                port = parts[2].toInt(),
                capabilities = parts[3].split(","),
                credits = parts[4].toInt(),
                lastSeen = System.currentTimeMillis()
            )
            
            val isNewPeer = !peers.containsKey(peerInfo.deviceId)
            peers[peerInfo.deviceId] = peerInfo
            
            if (isNewPeer) {
                Log.d(TAG, "New peer discovered: ${peerInfo.deviceName} at ${peerInfo.ipAddress}")
                onPeerDiscoveredListener?.invoke(peerInfo)
            }
            
        } catch (e: Exception) {
            Log.e(TAG, "Error parsing discovery message", e)
        }
    }

    /**
     * Build presence broadcast message
     */
    private fun buildPresenceMessage(): String {
        val deviceId = android.provider.Settings.Secure.getString(
            context.contentResolver,
            android.provider.Settings.Secure.ANDROID_ID
        )
        val deviceName = android.os.Build.MODEL
        val port = DISCOVERY_PORT
        val capabilities = "llm,inference,ar" // Capabilities
        val credits = 100 // Starting credits
        
        return "$deviceId|$deviceName|$port|$capabilities|$credits"
    }

    /**
     * Get broadcast address for WiFi network
     */
    private fun getBroadcastAddress(): InetAddress? {
        return try {
            val ip = wifiManager.connectionInfo.ipAddress
            if (ip == 0) return null
            
            val intToIp = { i: Int ->
                InetAddress.getByAddress(
                    byteArrayOf(
                        (i and 0xFF).toByte(),
                        ((i shr 8) and 0xFF).toByte(),
                        ((i shr 16) and 0xFF).toByte(),
                        ((i shr 24) and 0xFF).toByte()
                    )
                )
            }
            
            // Simple broadcast address calculation
            intToIp(ip or 0x000000FF)
        } catch (e: Exception) {
            Log.e(TAG, "Error getting broadcast address", e)
            null
        }
    }

    /**
     * Get list of active peers
     */
    fun getActivePeers(): List<PeerInfo> {
        val now = System.currentTimeMillis()
        return peers.values.filter { now - it.lastSeen < PEER_TIMEOUT_MS }
    }

    /**
     * Send compute task to peer
     */
    suspend fun sendComputeTask(peerId: String, task: ComputeTask): Boolean {
        val peer = peers[peerId] ?: return false
        
        return withContext(Dispatchers.IO) {
            try {
                val socket = DatagramSocket()
                val message = "TASK|${task.id}|${task.type}|${task.payload}"
                val buffer = message.toByteArray()
                val packet = DatagramPacket(
                    buffer,
                    buffer.size,
                    InetAddress.getByName(peer.ipAddress),
                    peer.port
                )
                socket.send(packet)
                socket.close()
                true
            } catch (e: Exception) {
                Log.e(TAG, "Failed to send task to peer", e)
                false
            }
        }
    }

    data class ComputeTask(
        val id: String,
        val type: String,
        val payload: String,
        val rewardCredits: Int
    )
}
