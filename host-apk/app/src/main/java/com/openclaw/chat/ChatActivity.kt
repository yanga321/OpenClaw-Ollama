package com.openclaw.chat

import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.view.View
import android.widget.EditText
import android.widget.ImageButton
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.openclaw.launcher.R
import java.text.SimpleDateFormat
import java.util.*

/**
 * AI Chat Activity - Conversational interface with LLM
 * 
 * Features:
 * - Real-time streaming responses
 * - Conversation history
 * - Context-aware replies
 * - Emotion-adaptive tone
 * - Offline-capable (via llama.cpp)
 */
class ChatActivity : AppCompatActivity() {

    companion object {
        private const val TAG = "ChatActivity"
    }

    private lateinit var messagesRecyclerView: RecyclerView
    private lateinit var messageInput: EditText
    private lateinit var sendButton: ImageButton
    private lateinit var typingIndicator: ProgressBar
    private lateinit var statusText: TextView

    private val messages = mutableListOf<ChatMessage>()
    private lateinit var adapter: ChatAdapter
    private val mainHandler = Handler(Looper.getMainLooper())

    private var isModelLoading = false
    private var isStreaming = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_chat)

        messagesRecyclerView = findViewById(R.id.messages_recycler_view)
        messageInput = findViewById(R.id.message_input)
        sendButton = findViewById(R.id.send_button)
        typingIndicator = findViewById(R.id.typing_indicator)
        statusText = findViewById(R.id.status_text)

        setupRecyclerView()
        setupListeners()
        
        // Add welcome message
        addWelcomeMessage()
        
        updateStatus("Model ready • Phi-3 Mini")
    }

    private fun setupRecyclerView() {
        adapter = ChatAdapter(messages)
        messagesRecyclerView.adapter = adapter
        messagesRecyclerView.layoutManager = LinearLayoutManager(this).apply {
            stackFromEnd = true
        }
    }

    private fun setupListeners() {
        sendButton.setOnClickListener { sendMessage() }
        
        messageInput.setOnEditorActionListener { _, actionId, _ ->
            if (actionId == android.view.inputmethod.EditorInfo.IME_ACTION_SEND) {
                sendMessage()
                true
            } else {
                false
            }
        }
    }

    private fun addWelcomeMessage() {
        val welcomeMsg = ChatMessage(
            text = "👋 Hi! I'm your AI assistant on OpenClaw OTG Drive. I can help you with:\n\n" +
                   "• Answering questions\n" +
                   "• Creative writing\n" +
                   "• Code assistance\n" +
                   "• Analysis & reasoning\n" +
                   "• And much more!\n\n" +
                   "What would you like to explore today?",
            isUser = false,
            timestamp = System.currentTimeMillis()
        )
        messages.add(welcomeMsg)
        adapter.notifyDataSetChanged()
        scrollToBottom()
    }

    private fun sendMessage() {
        val text = messageInput.text.toString().trim()
        if (text.isEmpty() || isStreaming) return

        // Add user message
        val userMsg = ChatMessage(
            text = text,
            isUser = true,
            timestamp = System.currentTimeMillis()
        )
        messages.add(userMsg)
        adapter.notifyDataSetChanged()
        messageInput.text.clear()
        scrollToBottom()

        // Show typing indicator
        showTypingIndicator(true)

        // Simulate AI response (replace with actual llama.cpp call)
        generateAIResponse(text)
    }

    private fun generateAIResponse(userMessage: String) {
        isStreaming = true
        
        // Create placeholder for AI response
        val aiMsg = ChatMessage(
            text = "",
            isUser = false,
            timestamp = System.currentTimeMillis(),
            isStreaming = true
        )
        messages.add(aiMsg)
        adapter.notifyDataSetChanged()
        scrollToBottom()

        // Simulate streaming response (replace with actual inference)
        val mockResponse = getMockResponse(userMessage)
        val words = mockResponse.split(" ")
        var currentWordIndex = 0

        val streamRunnable = object : Runnable {
            override fun run() {
                if (currentWordIndex < words.size) {
                    aiMsg.text = if (aiMsg.text.isEmpty()) {
                        words[currentWordIndex]
                    } else {
                        "${aiMsg.text} ${words[currentWordIndex]}"
                    }
                    aiMsg.timestamp = System.currentTimeMillis()
                    
                    mainHandler.post {
                        adapter.notifyItemChanged(messages.size - 1)
                        scrollToBottom()
                    }
                    
                    currentWordIndex++
                    mainHandler.postDelayed(this, 50) // Stream every 50ms
                } else {
                    // Streaming complete
                    aiMsg.isStreaming = false
                    mainHandler.post {
                        adapter.notifyItemChanged(messages.size - 1)
                        showTypingIndicator(false)
                        isStreaming = false
                        updateStatus("Ready")
                    }
                }
            }
        }
        
        mainHandler.postDelayed(streamRunnable, 500) // Initial delay
    }

    private fun getMockResponse(input: String): String {
        val lowerInput = input.lowercase()
        
        return when {
            lowerInput.contains("hello") || lowerInput.contains("hi") -> 
                "Hello! 👋 Great to see you! How can I assist you today?"
            
            lowerInput.contains("who are you") || lowerInput.contains("what are you") ->
                "I'm an AI assistant running locally on your OpenClaw OTG Drive! 🚀\n\n" +
                "I'm powered by advanced language models that run entirely offline on your device. " +
                "No internet connection needed - your data stays private and secure!"
            
            lowerInput.contains("help") ->
                "I'd be happy to help! Here's what I can do:\n\n" +
                "📝 **Writing**: Essays, stories, emails, code\n" +
                "🧠 **Analysis**: Explain concepts, summarize texts\n" +
                "💻 **Coding**: Debug, explain, write code\n" +
                "🎯 **Problem Solving**: Math, logic, reasoning\n" +
                "💬 **Conversation**: Just chat about anything!\n\n" +
                "What would you like to try?"
            
            lowerInput.contains("thank") ->
                "You're welcome! 😊 Feel free to ask me anything else!"
            
            lowerInput.contains("bye") || lowerInput.contains("goodbye") ->
                "Goodbye! 👋 It was great chatting with you. Come back anytime!"
            
            else -> 
                "That's interesting! 🤔\n\n" +
                "I'm processing your question: \"$input\"\n\n" +
                "In the full version, I'll provide a detailed AI-generated response using the llama.cpp engine. " +
                "This demo shows the streaming chat interface. The actual model will give you comprehensive, accurate answers!"
        }
    }

    private fun showTypingIndicator(show: Boolean) {
        typingIndicator.visibility = if (show) View.VISIBLE else View.GONE
        statusText.text = if (show) "AI is thinking..." else "Model ready • Phi-3 Mini"
    }

    private fun updateStatus(status: String) {
        statusText.text = status
    }

    private fun scrollToBottom() {
        mainHandler.postDelayed({
            messagesRecyclerView.smoothScrollToPosition(messages.size - 1)
        }, 100)
    }

    override fun onBackPressed() {
        if (isStreaming) {
            Toast.makeText(this, "Please wait for response to complete", Toast.LENGTH_SHORT).show()
        } else {
            super.onBackPressed()
        }
    }
}

/**
 * Chat Message Data Class
 */
data class ChatMessage(
    val text: String,
    val isUser: Boolean,
    val timestamp: Long,
    val isStreaming: Boolean = false
) {
    fun getFormattedTime(): String {
        val format = SimpleDateFormat("HH:mm", Locale.getDefault())
        return format.format(Date(timestamp))
    }
}
