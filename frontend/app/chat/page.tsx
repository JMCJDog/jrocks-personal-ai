'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { useSearchParams } from 'next/navigation';
import { api, ChatMessage } from '@/lib/api';
import CameraPreview, { CameraPreviewHandle } from '@/components/chat/CameraPreview';

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isCameraOpen, setIsCameraOpen] = useState(false);
  const [isWatchMode, setIsWatchMode] = useState(false);
  const [pendingFiles, setPendingFiles] = useState<any[]>([]);
  const [lastAutoFrame, setLastAutoFrame] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const searchParams = useSearchParams();
  const targetAgent = searchParams.get('agent');

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const cameraRef = useRef<CameraPreviewHandle>(null);
  const recognitionRef = useRef<any>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (messageText?: string, metadata?: any) => {
    const textToSend = messageText || input;
    if (!textToSend.trim() && !isCameraOpen && pendingFiles.length === 0) return;
    if (loading) return;

    // Default metadata if not provided
    let finalMetadata = metadata || {};
    if (!metadata) {
      if (isWatchMode) finalMetadata = { input_mode: 'watch' };
      else if (isCameraOpen) finalMetadata = { input_mode: 'camera' };
      else if (pendingFiles.length > 0) finalMetadata = { input_mode: 'upload' };
    }

    // Capture frame if camera is open
    let images: string[] | undefined = undefined;
    if (isCameraOpen && cameraRef.current) {
      const frame = cameraRef.current.captureFrame();
      if (frame) {
        images = [frame];
      }
    }

    // Add auto-captured frame if in watch mode and no fresh capture
    if (isWatchMode && !images && lastAutoFrame) {
      images = [lastAutoFrame];
    }

    const userMessage: ChatMessage = {
      role: 'user',
      content: textToSend || (pendingFiles.length > 0 ? `Uploaded ${pendingFiles.length} files` : "Captured image")
    };

    setMessages(prev => [...prev, userMessage]);
    if (!messageText) setInput('');
    setLoading(true);

    try {
      const response = await api.sendChatMessage(
        textToSend,
        undefined,
        images,
        targetAgent || undefined,
        pendingFiles.length > 0 ? pendingFiles : undefined,
        finalMetadata
      );

      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: response.response || 'No response received',
      };
      setMessages(prev => [...prev, assistantMessage]);
      setPendingFiles([]); // Clear files after send
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

  const startRecording = useCallback(() => {
    // Check for Web Speech API support
    const SpeechRecognitionAPI =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;

    if (!SpeechRecognitionAPI) {
      alert('Voice input is not supported in this browser. Try Chrome or Edge.');
      return;
    }

    const recognition: any = new SpeechRecognitionAPI();
    recognition.lang = 'en-US';
    recognition.interimResults = true;   // Show live transcription as you speak
    recognition.maxAlternatives = 1;
    recognition.continuous = false;      // Auto-stops after a pause

    recognitionRef.current = recognition;

    recognition.onstart = () => {
      setIsRecording(true);
      setInput('');  // Clear any previous text
    };

    // Live: update the input textarea with interim results so the user sees transcription in real-time
    recognition.onresult = (event: any) => {
      let transcript = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        transcript += event.results[i][0].transcript;
      }
      setInput(transcript);
    };

    // When the user stops talking, auto-send
    recognition.onend = () => {
      setIsRecording(false);
      // Read the final input value and send it
      setInput(prev => {
        if (prev.trim()) {
          // Use setTimeout to allow state to settle before sending
          setTimeout(() => handleSend(prev.trim(), { input_mode: 'voice' }), 100);
        }
        return prev;
      });
      recognitionRef.current = null;
    };

    recognition.onerror = (event: any) => {
      console.error('Speech recognition error:', event.error);
      setIsRecording(false);
      recognitionRef.current = null;
      if (event.error !== 'no-speech') {
        alert(`Voice input error: ${event.error}. Check microphone permissions.`);
      }
    };

    recognition.start();
  }, []);

  const stopRecording = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();  // triggers onend → auto-sends
      setIsRecording(false);
    }
  }, []);

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;

    Array.from(files).forEach(file => {
      const reader = new FileReader();
      reader.onload = (event) => {
        const base64 = event.target?.result as string;
        setPendingFiles(prev => [...prev, {
          name: file.name,
          type: file.type,
          data: base64
        }]);
      };
      reader.readAsDataURL(file);
    });
    // Reset input
    e.target.value = '';
  };

  const removeFile = (index: number) => {
    setPendingFiles(prev => prev.filter((_, i) => i !== index));
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
          <div className="camera-container animate-fade-in relative">
            <CameraPreview
              ref={cameraRef}
              className="camera-preview-box"
              autoCaptureInterval={isWatchMode ? 5000 : undefined}
              onCapture={(frame) => setLastAutoFrame(frame)}
            />
            <button
              onClick={() => setIsWatchMode(!isWatchMode)}
              className={`watch-mode-btn ${isWatchMode ? 'active' : ''}`}
              title="Continuous Watch Mode"
            >
              {isWatchMode ? '👁️ WATCHING' : '👁️ WATCH'}
            </button>
          </div>
        )}

        {pendingFiles.length > 0 && (
          <div className="file-preview-strip animate-slide-up">
            {pendingFiles.map((file, idx) => (
              <div key={idx} className="file-preview-item glass-card">
                {file.type.startsWith('image/') ? (
                  <img src={file.data} alt={file.name} className="file-thumb" />
                ) : (
                  <div className="file-icon">📄</div>
                )}
                <span className="file-label">{file.name}</span>
                <button onClick={() => removeFile(idx)} className="remove-file">✕</button>
              </div>
            ))}
          </div>
        )}

        <div className="input-area glass-card">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            multiple
            className="hidden"
            accept="image/*,video/*,application/pdf,text/*"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            className="btn toggle-btn"
            title="Attach Files"
          >
            📎
          </button>
          <button
            onClick={() => {
              setIsCameraOpen(!isCameraOpen);
              if (isCameraOpen) setIsWatchMode(false);
            }}
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
            placeholder={
              isWatchMode ? "AI is watching... ask it anything" :
                isCameraOpen ? "Point camera and ask what I see..." :
                  isRecording ? "Listening..." :
                    "Type your message..."
            }
            className="input chat-input"
            rows={1}
            disabled={loading || isRecording}
          />
          <button
            onClick={() => handleSend()}
            disabled={loading || (!input.trim() && !isCameraOpen && pendingFiles.length === 0) || isRecording}
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

        .watch-mode-btn {
          position: absolute;
          top: 12px;
          right: 12px;
          padding: 6px 12px;
          background: rgba(0, 0, 0, 0.6);
          backdrop-filter: blur(8px);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: var(--radius-md);
          font-size: 10px;
          font-weight: 700;
          color: white;
          letter-spacing: 0.1em;
          transition: all 0.3s ease;
          z-index: 10;
        }

        .watch-mode-btn.active {
          background: rgba(6, 182, 212, 0.3);
          border-color: #06b6d4;
          color: #06b6d4;
          box-shadow: 0 0 15px rgba(6, 182, 212, 0.4);
        }

        .file-preview-strip {
          display: flex;
          gap: 12px;
          padding: 8px;
          overflow-x: auto;
          background: rgba(255, 255, 255, 0.03);
          border-radius: var(--radius-lg);
          border: 1px solid rgba(255, 255, 255, 0.05);
        }

        .file-preview-item {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 4px 8px;
          min-width: 120px;
          max-width: 200px;
          position: relative;
        }

        .file-thumb {
          width: 32px;
          height: 32px;
          object-fit: cover;
          border-radius: var(--radius-sm);
        }

        .file-icon {
          font-size: 18px;
        }

        .file-label {
          font-size: 11px;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          color: var(--text-secondary);
        }

        .remove-file {
          background: none;
          border: none;
          color: var(--text-muted);
          cursor: pointer;
          font-size: 10px;
          padding: 4px;
        }

        .remove-file:hover {
          color: #ef4444;
        }

        @keyframes slideUp {
          from { transform: translateY(20px); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }

        .animate-slide-up {
          animation: slideUp 0.3s ease-out forwards;
        }

        .animate-fade-in {
          animation: fadeIn var(--transition-base) forwards;
        }
      `}</style>
    </div>
  );
}
