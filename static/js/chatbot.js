// GrievAI Chatbot Widget
(function() {
    let userEmail = 'guest';
    let userType = 'guest';
    let isOpen = false;
    
    const chatbotHTML = `
        <div id="grievai-chatbot" style="position:fixed; bottom:20px; right:20px; z-index:10000; font-family:'Segoe UI',Arial,sans-serif;">
            <div id="chatbot-toggle" style="width:60px; height:60px; background:linear-gradient(135deg,#1B8A4E,#0E6B6B); border-radius:50%; display:flex; align-items:center; justify-content:center; cursor:pointer; box-shadow:0 4px 20px rgba(0,0,0,0.2); transition:transform 0.2s;">
                <span style="font-size:28px;">🤖</span>
            </div>
            
            <div id="chatbot-window" style="display:none; position:absolute; bottom:70px; right:0; width:380px; height:550px; background:#fff; border-radius:20px; box-shadow:0 10px 40px rgba(0,0,0,0.2); overflow:hidden; flex-direction:column; border:1px solid #E2E8F0;">
                <div style="background:linear-gradient(135deg,#1B8A4E,#0E6B6B); padding:15px; color:#fff; display:flex; justify-content:space-between; align-items:center;">
                    <div style="display:flex; align-items:center; gap:10px;">
                        <span style="font-size:24px;">🤖</span>
                        <div>
                            <div style="font-weight:bold;">GrievAI Assistant</div>
                            <div style="font-size:11px; opacity:0.8;">हिंदी | English</div>
                        </div>
                    </div>
                    <button id="chatbot-close" style="background:none; border:none; color:#fff; font-size:20px; cursor:pointer;">✕</button>
                </div>
                
                <div id="chatbot-messages" style="flex:1; overflow-y:auto; padding:15px; background:#F4F6FB;">
                    <div style="text-align:center; margin-bottom:15px;">
                        <div style="background:#E8F5E9; padding:12px; border-radius:15px; font-size:13px; color:#1B8A4E;">
                            👋 <strong>Namaste! Welcome to GrievAI</strong><br><br>
                            मैं आपकी मदद कर सकता हूं:<br>
                            📝 शिकायत कैसे दर्ज करें<br>
                            📋 Complaint ID का स्टेटस<br>
                            🏛 विभागों के बारे में<br>
                            🔑 पासवर्ड रीसेट<br>
                            ⭐ फीडबैक कैसे दें
                        </div>
                    </div>
                </div>
                
                <div style="padding:12px; border-top:1px solid #E2E8F0; background:#fff; display:flex; gap:10px;">
                    <input type="text" id="chatbot-input" placeholder="अपना प्रश्न लिखें..." style="flex:1; padding:10px 12px; border:1.5px solid #E2E8F0; border-radius:25px; font-size:13px; outline:none;">
                    <button id="chatbot-send" style="background:#1B8A4E; border:none; width:40px; height:40px; border-radius:50%; color:#fff; cursor:pointer; font-size:18px;">➤</button>
                </div>
                
                <div style="padding:0 12px 12px 12px; display:flex; justify-content:center;">
                    <button id="chatbot-clear" style="background:#6B3FA0; border:none; padding:8px 20px; border-radius:25px; color:#fff; cursor:pointer; font-size:12px;">🗑 Clear Chat</button>
                </div>
            </div>
        </div>
    `;
    
    function addMessage(text, isUser) {
        const messagesDiv = document.getElementById('chatbot-messages');
        if (!messagesDiv) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.style.marginBottom = '12px';
        messageDiv.style.display = 'flex';
        messageDiv.style.justifyContent = isUser ? 'flex-end' : 'flex-start';
        
        const bubble = document.createElement('div');
        bubble.style.maxWidth = '80%';
        bubble.style.padding = '10px 14px';
        bubble.style.borderRadius = '18px';
        bubble.style.fontSize = '13px';
        bubble.style.lineHeight = '1.5';
        bubble.style.whiteSpace = 'pre-wrap';
        bubble.style.wordBreak = 'break-word';
        
        if (isUser) {
            bubble.style.background = '#1B8A4E';
            bubble.style.color = '#fff';
            bubble.style.borderBottomRightRadius = '4px';
        } else {
            bubble.style.background = '#fff';
            bubble.style.color = '#2D3748';
            bubble.style.border = '1px solid #E2E8F0';
            bubble.style.borderBottomLeftRadius = '4px';
        }
        
        bubble.innerHTML = text.replace(/\n/g, '<br>');
        messageDiv.appendChild(bubble);
        messagesDiv.appendChild(messageDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
    
    function showTyping() {
        const messagesDiv = document.getElementById('chatbot-messages');
        if (!messagesDiv) return;
        
        const typingDiv = document.createElement('div');
        typingDiv.id = 'chatbot-typing';
        typingDiv.style.marginBottom = '12px';
        typingDiv.style.display = 'flex';
        typingDiv.style.justifyContent = 'flex-start';
        
        const bubble = document.createElement('div');
        bubble.style.background = '#fff';
        bubble.style.padding = '12px 18px';
        bubble.style.borderRadius = '18px';
        bubble.style.border = '1px solid #E2E8F0';
        bubble.style.borderBottomLeftRadius = '4px';
        bubble.innerHTML = '<span style="opacity:0.6;">🤖 Thinking...</span>';
        
        typingDiv.appendChild(bubble);
        messagesDiv.appendChild(typingDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
    
    function hideTyping() {
        const typing = document.getElementById('chatbot-typing');
        if (typing) typing.remove();
    }
    
    function clearChat() {
        const messagesDiv = document.getElementById('chatbot-messages');
        if (messagesDiv) {
            messagesDiv.innerHTML = `
                <div style="text-align:center; margin-bottom:15px;">
                    <div style="background:#E8F5E9; padding:12px; border-radius:15px; font-size:13px; color:#1B8A4E;">
                        👋 <strong>Namaste! Welcome to GrievAI</strong><br><br>
                        मैं आपकी मदद कर सकता हूं:<br>
                        📝 शिकायत कैसे दर्ज करें<br>
                        📋 Complaint ID का स्टेटस<br>
                        🏛 विभागों के बारे में<br>
                        🔑 पासवर्ड रीसेट<br>
                        ⭐ फीडबैक कैसे दें
                    </div>
                </div>
            `;
        }
    }
    
    async function sendMessage(message) {
        if (!message.trim()) return;
        
        addMessage(message, true);
        document.getElementById('chatbot-input').value = '';
        
        showTyping();
        
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    message: message, 
                    user_email: userEmail, 
                    user_type: userType
                })
            });
            const data = await response.json();
            hideTyping();
            
            if (data.success) {
                addMessage(data.response, false);
            } else {
                addMessage('❌ Sorry, something went wrong. Please try again.', false);
            }
        } catch (error) {
            hideTyping();
            addMessage('❌ Network error. Please check your connection.', false);
        }
    }
    
    window.initChatbot = function(email, type, dept) {
        userEmail = email || 'guest';
        userType = type || 'guest';
        
        if (!document.getElementById('grievai-chatbot')) {
            document.body.insertAdjacentHTML('beforeend', chatbotHTML);
        }
        
        const toggle = document.getElementById('chatbot-toggle');
        const windowDiv = document.getElementById('chatbot-window');
        const closeBtn = document.getElementById('chatbot-close');
        const sendBtn = document.getElementById('chatbot-send');
        const input = document.getElementById('chatbot-input');
        const clearBtn = document.getElementById('chatbot-clear');
        
        if (toggle) {
            toggle.onclick = () => { 
                isOpen = !isOpen; 
                windowDiv.style.display = isOpen ? 'flex' : 'none'; 
                if (isOpen) setTimeout(() => input.focus(), 100);
            };
        }
        if (closeBtn) closeBtn.onclick = () => { isOpen = false; windowDiv.style.display = 'none'; };
        if (sendBtn) sendBtn.onclick = () => sendMessage(input.value);
        if (input) input.onkeypress = (e) => { if (e.key === 'Enter') sendMessage(input.value); };
        if (clearBtn) clearBtn.onclick = clearChat;
    };
})();