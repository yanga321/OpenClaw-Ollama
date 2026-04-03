package com.openclaw.chat

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import com.openclaw.launcher.R
import java.text.SimpleDateFormat
import java.util.*

/**
 * Chat Adapter for RecyclerView
 */
class ChatAdapter(
    private val messages: List<ChatMessage>
) : RecyclerView.Adapter<ChatAdapter.ChatViewHolder>() {

    companion object {
        private const val VIEW_TYPE_USER = 1
        private const val VIEW_TYPE_AI = 2
    }

    override fun getItemViewType(position: Int): Int {
        return if (messages[position].isUser) VIEW_TYPE_USER else VIEW_TYPE_AI
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ChatViewHolder {
        val view = when (viewType) {
            VIEW_TYPE_USER -> LayoutInflater.from(parent.context)
                .inflate(R.layout.item_message_user, parent, false)
            else -> LayoutInflater.from(parent.context)
                .inflate(R.layout.item_message_ai, parent, false)
        }
        return ChatViewHolder(view)
    }

    override fun onBindViewHolder(holder: ChatViewHolder, position: Int) {
        holder.bind(messages[position])
    }

    override fun getItemCount() = messages.size

    inner class ChatViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        private val messageText: TextView = itemView.findViewById(R.id.message_text)
        private val timestampText: TextView = itemView.findViewById(R.id.timestamp_text)
        private val streamingIndicator: TextView? = itemView.findViewById(R.id.streaming_indicator)

        fun bind(message: ChatMessage) {
            messageText.text = message.text
            timestampText.text = message.getFormattedTime()
            
            streamingIndicator?.visibility = if (message.isStreaming) View.VISIBLE else View.GONE
            
            // Add typing animation for streaming messages
            if (message.isStreaming) {
                streamingIndicator?.text = " ▍"
            }
        }
    }
}
