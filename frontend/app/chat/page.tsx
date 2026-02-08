'use client';

import { useState, useRef, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { api, ChatMessage } from '@/lib/api';
import CameraPreview, { CameraPreviewHandle } from '@/components/chat/CameraPreview';

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isCameraOpen, setIsCameraOpen] = useState(false);

  const searchParams = useSearchParams();
  const targetAgent = searchParams.get('agent');

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const cameraRef = useRef<CameraPreviewHandle>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (messageText?: string) => {
    const textToSend = messageText || input;
    if (!textToSend.trim() && !isCameraOpen) return;
    if (loading) return;

    // Capture frame if camera is open
    let images: string[] | undefined = undefined;
    if (isCameraOpen && cameraRef.current) {
      const frame = cameraRef.current.captureFrame();
      if (frame) {
        images = [frame];
      }
    }

    const userMessage: ChatMessage = { role: 'user', content: textToSend };
    setMessages(prev => [...prev, userMessage]);
    if (!messageText) setInput('');
    setLoading(true);

    try {
      const response = await api.sendChatMessage(textToSend, undefined, images, targetAgent || undefined);
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: response.response || 'No response received',
      };
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        await handleVoiceSend(audioBlob);
        // Stop all tracks to release microphone
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (err) {
      console.error('Error accessing microphone:', err);
      alert('Could not access microphone. Please check permissions.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const handleVoiceSend = async (blob: Blob) => {
    setLoading(true);
    try {
      const result = await api.sendVoiceMessage(blob);

      // Add user message (transcription)
      const userMessage: ChatMessage = { role: 'user', content: result.input_text };
      setMessages(prev => [...prev, userMessage]);

      // Add assistant response
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: result.response_text,
      };
      setMessages(prev => [...prev, assistantMessage]);

      // Play audio response
      if (result.audio_url) {
        const fullAudioUrl = `http://localhost:8000${result.audio_url}`;
        const audio = new Audio(fullAudioUrl);
        audio.play().catch(e => console.error('Audio playback failed', e));
      }
    } catch (error) {
      console.error('Voice chat error:', error);
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: 'I heard you, but I had trouble responding. Please try again.',
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-page">
      <div className="messages-container">
        {messages.length === 0 ? (
          <div className="empty-state">
            <span className="empty-icon">💬</span>
            <h3>Start a conversation</h3>
            <p>Ask me anything about your data, or just have a chat!</p>
          </div>
        ) : (
          <div className="messages">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`message ${msg.role}`}
              >
                <div className="message-avatar">
                  {msg.role === 'user' ? 'You' : '🧠'}
                </div>
                <div className="message-content">
                  {msg.content}
                </div>
              </div>
            ))}
            {loading && (
              <div className="message assistant">
                <div className="message-avatar">🧠</div>
                <div className="message-content typing">
                  <span className="dot" />
                  <span className="dot" />
                  <span className="dot" />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      <div className="footer-container">
        {isCameraOpen && (
          <div className="camera-container animate-fade-in">
            <CameraPreview ref={cameraRef} className="camera-preview-box" />
          </div>
        )}

        <div className="input-area glass-card">
          <button
            onClick={() => setIsCameraOpen(!isCameraOpen)}
            className={`btn toggle-btn ${isCameraOpen ? 'active' : ''}`}
            title={isCameraOpen ? 'Close Sight' : 'Enable Sight'}
          >
            👁️
          </button>
          <button
            onClick={isRecording ? stopRecording : startRecording}
            className={`btn mic-btn ${isRecording ? 'recording' : ''}`}
            title={isRecording ? 'Stop Recording' : 'Voice Input'}
            disabled={loading && !isRecording}
          >
            {isRecording ? '🛑' : '🎤'}
          </button>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder={isCameraOpen ? "Point camera and ask what I see..." : isRecording ? "Listening..." : "Type your message..."}
            className="input chat-input"
            rows={1}
            disabled={loading || isRecording}
          />
          <button
            onClick={() => handleSend()}
            disabled={loading || (!input.trim() && !isCameraOpen) || isRecording}
            className="btn btn-primary send-btn"
          >
            {loading ? '...' : 'Send'}
          </button>
        </div>
      </div>

      <style jsx>{`
        .chat-page {
          display: flex;
          flex-direction: column;
          height: calc(100vh - 140px);
          max-width: 900px;
          margin: 0 auto;
        }

        .messages-container {
          flex: 1;
          overflow-y: auto;
          padding: var(--spacing-lg) 0;
        }

        .empty-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 100%;
          text-align: center;
          color: var(--text-secondary);
        }

        .empty-icon {
          font-size: 4rem;
          margin-bottom: var(--spacing-lg);
        }

        .empty-state h3 {
          margin-bottom: var(--spacing-sm);
        }

        .messages {
          display: flex;
          flex-direction: column;
          gap: var(--spacing-lg);
        }

        .message {
          display: flex;
          gap: var(--spacing-md);
          animation: fadeIn var(--transition-base) forwards;
        }

        .message.user {
          flex-direction: row-reverse;
        }

        .message-avatar {
          width: 40px;
          height: 40px;
          border-radius: var(--radius-full);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 0.875rem;
          font-weight: 600;
          flex-shrink: 0;
        }

        .message.user .message-avatar {
          background: var(--accent-gradient);
          color: white;
        }

        .message.assistant .message-avatar {
          background: var(--bg-tertiary);
          font-size: 1.25rem;
        }

        .message-content {
          max-width: 70%;
          padding: var(--spacing-md) var(--spacing-lg);
          border-radius: var(--radius-lg);
          line-height: 1.5;
        }

        .message.user .message-content {
          background: var(--accent-primary);
          color: white;
          border-bottom-right-radius: var(--spacing-xs);
        }

        .message.assistant .message-content {
          background: var(--bg-tertiary);
          color: var(--text-primary);
          border-bottom-left-radius: var(--spacing-xs);
        }

        .typing {
          display: flex;
          gap: 4px;
          padding: var(--spacing-md) var(--spacing-lg);
        }

        .typing .dot {
          width: 8px;
          height: 8px;
          background: var(--text-muted);
          border-radius: 50%;
          animation: pulse 1.4s infinite ease-in-out both;
        }

        .typing .dot:nth-child(1) { animation-delay: -0.32s; }
        .typing .dot:nth-child(2) { animation-delay: -0.16s; }

        .footer-container {
          margin-top: auto;
          display: flex;
          flex-direction: column;
          gap: var(--spacing-md);
        }

        .camera-container {
          width: 100%;
          max-height: 240px;
        }

        :global(.camera-preview-box) {
          width: 100%;
          height: 240px;
        }

        .input-area {
          display: flex;
          gap: var(--spacing-md);
          padding: var(--spacing-md);
        }

        .chat-input {
          flex: 1;
          resize: none;
          min-height: 48px;
          max-height: 120px;
        }

        .send-btn {
          min-width: 80px;
        }

        .toggle-btn {
          font-size: 1.25rem;
          padding: 0 var(--spacing-md);
          background: var(--bg-tertiary);
          border: 1px solid var(--border-subtle);
          border-radius: var(--radius-md);
          transition: all var(--transition-base);
        }

        .toggle-btn.active {
          background: var(--accent-subtle);
          color: var(--accent-primary);
          border-color: var(--accent-primary);
          box-shadow: 0 0 10px rgba(6, 182, 212, 0.2);
        }

        .mic-btn {
          font-size: 1.25rem;
          padding: 0 var(--spacing-md);
          background: var(--bg-tertiary);
          border: 1px solid var(--border-subtle);
          border-radius: var(--radius-md);
          transition: all var(--transition-base);
        }

        .mic-btn:hover {
          background: var(--bg-hover);
        }

        .mic-btn.recording {
          background: var(--error-subtle, #fee2e2);
          color: var(--error-primary, #ef4444);
          border-color: #ef4444;
          animation: pulse 2s infinite;
        }

        @keyframes pulse {
          0% { transform: scale(1); }
          50% { transform: scale(1.1); }
          100% { transform: scale(1); }
        }

        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }

        .animate-fade-in {
          animation: fadeIn var(--transition-base) forwards;
        }
      `}</style>
    </div>
  );
}
