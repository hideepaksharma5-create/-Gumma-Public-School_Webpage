document.addEventListener('DOMContentLoaded', () => {

    // =====================================================================
    // Password Visual Toggle
    // =====================================================================
    const passwordInput = document.getElementById('password');
    const passwordToggle = document.getElementById('passwordToggle');

    if (passwordToggle && passwordInput) {
        passwordToggle.addEventListener('click', () => {
            const isPassword = passwordInput.getAttribute('type') === 'password';
            passwordInput.setAttribute('type', isPassword ? 'text' : 'password');
            const eyeShow = passwordToggle.querySelector('.eye-show');
            const eyeHide = passwordToggle.querySelector('.eye-hide');
            if (eyeShow && eyeHide) {
                eyeShow.classList.toggle('hidden');
                eyeHide.classList.toggle('hidden');
            }
        });
    }

    // =====================================================================
    // Dismiss Alerts on Typing
    // =====================================================================
    const errorAlert = document.getElementById('error-message');
    if (errorAlert) {
        const inputs = document.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.addEventListener('input', () => {
                errorAlert.style.opacity = '0';
                errorAlert.style.transform = 'translateY(-10px)';
                errorAlert.style.transition = 'all 0.3s ease';
                setTimeout(() => errorAlert.remove(), 300);
            }, { once: true });
        });
    }

    // =====================================================================
    // Table Search & Filtering
    // =====================================================================
    const tableSearch = document.getElementById('tableSearch');
    if (tableSearch) {
        tableSearch.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase().trim();
            const tableRows = document.querySelectorAll('tbody tr');
            tableRows.forEach(row => {
                const cells = row.querySelectorAll('td');
                if (cells.length > 1) {
                    const content = Array.from(cells).map(cell => cell.textContent.toLowerCase()).join(' ');
                    row.style.display = content.includes(query) ? '' : 'none';
                }
            });
        });
    }

    // =====================================================================
    // AI Chatbot Widget — Inject HTML & Wire Interactions
    // =====================================================================
    const CHATBOT_HTML = `
    <!-- Floating Chat Toggle Bubble -->
    <button id="chatbot-toggle" aria-label="Open School AI Assistant">
        <div class="chat-notif-badge">1</div>
        <!-- Chat Icon -->
        <svg class="icon-chat" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
        </svg>
        <!-- Close Icon -->
        <svg class="icon-close" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
    </button>

    <!-- Chat Panel -->
    <div id="chatbot-panel" role="dialog" aria-label="School AI Assistant">
        <!-- Header -->
        <div class="chat-panel-header">
            <div class="chat-bot-avatar">🏫</div>
            <div class="chat-header-text">
                <h4>GPS Assistant</h4>
                <span><span class="status-dot"></span>Online — Gumma Public School</span>
            </div>
        </div>

        <!-- Message Stream -->
        <div class="chat-messages" id="chatMessages"></div>

        <!-- Quick Suggestion Chips -->
        <div class="chat-suggestions">
            <button class="chat-chip" data-query="admission">📋 Admissions</button>
            <button class="chat-chip" data-query="fees">💰 Fees</button>
            <button class="chat-chip" data-query="grades">📚 Grades</button>
            <button class="chat-chip" data-query="timing">🕐 Timings</button>
            <button class="chat-chip" data-query="facilities">🏫 Facilities</button>
            <button class="chat-chip" data-query="scholarship">🏅 Scholarships</button>
            <button class="chat-chip" data-query="contact">📞 Contact</button>
        </div>

        <!-- Input Row -->
        <div class="chat-input-area">
            <input id="chatInputField" type="text" placeholder="Ask about admissions, fees, grades..." autocomplete="off">
            <button id="chatSendBtn" aria-label="Send Message">
                <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="22" y1="2" x2="11" y2="13"></line>
                    <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                </svg>
            </button>
        </div>
    </div>
    `;

    // Inject chatbot into page
    document.body.insertAdjacentHTML('beforeend', CHATBOT_HTML);

    const toggle = document.getElementById('chatbot-toggle');
    const panel = document.getElementById('chatbot-panel');
    const messagesContainer = document.getElementById('chatMessages');
    const inputField = document.getElementById('chatInputField');
    const sendBtn = document.getElementById('chatSendBtn');
    const chips = document.querySelectorAll('.chat-chip');
    const notifBadge = document.querySelector('.chat-notif-badge');

    let isOpen = false;
    let hasBeenOpened = false;

    // ---- Toggle chat panel ----
    toggle.addEventListener('click', () => {
        isOpen = !isOpen;
        toggle.classList.toggle('open', isOpen);
        panel.classList.toggle('open', isOpen);

        if (isOpen) {
            if (notifBadge) notifBadge.style.display = 'none';
            if (!hasBeenOpened) {
                hasBeenOpened = true;
                // Show welcome message on first open
                setTimeout(() => {
                    appendBotMessage(
                        "👋 Hi there! I'm the **GPS Assistant** for **Gumma Public School**.\n\nI can answer questions about:\n• 📋 Admission process\n• 💰 Fee structure\n• 📚 Classes & streams\n• 🏫 School facilities\n• 📞 Contact & location\n\nWhat would you like to know?"
                    );
                }, 350);
            }
            inputField.focus();
        }
    });

    // ---- Close on outside click ----
    document.addEventListener('click', (e) => {
        if (isOpen && !panel.contains(e.target) && !toggle.contains(e.target)) {
            isOpen = false;
            toggle.classList.remove('open');
            panel.classList.remove('open');
        }
    });

    // ---- Send message ----
    function sendMessage() {
        const text = inputField.value.trim();
        if (!text) return;

        appendUserMessage(text);
        inputField.value = '';

        showTypingIndicator();

        fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text })
        })
        .then(res => res.json())
        .then(data => {
            removeTypingIndicator();
            appendBotMessage(data.reply);
        })
        .catch(() => {
            removeTypingIndicator();
            appendBotMessage("⚠️ Sorry, I couldn't connect to the server. Please try again or visit the `/contact` page.");
        });
    }

    sendBtn.addEventListener('click', sendMessage);
    inputField.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    // ---- Quick suggestion chips ----
    chips.forEach(chip => {
        chip.addEventListener('click', () => {
            const query = chip.dataset.query;
            inputField.value = query;
            sendMessage();
        });
    });

    // ---- Helpers ----
    function appendUserMessage(text) {
        const msg = document.createElement('div');
        msg.className = 'chat-msg user';
        msg.innerHTML = `<div class="msg-bubble">${escapeHtml(text)}</div>`;
        messagesContainer.appendChild(msg);
        scrollToBottom();
    }

    function appendBotMessage(text) {
        const msg = document.createElement('div');
        msg.className = 'chat-msg bot';
        // Convert **bold** markdown and newlines
        const formatted = text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');
        msg.innerHTML = `
            <div class="msg-avatar">🤖</div>
            <div class="msg-bubble">${formatted}</div>
        `;
        messagesContainer.appendChild(msg);
        scrollToBottom();
    }

    function showTypingIndicator() {
        const typing = document.createElement('div');
        typing.className = 'chat-typing';
        typing.id = 'chatTyping';
        typing.innerHTML = `
            <div class="msg-avatar">🤖</div>
            <div class="typing-dots">
                <span></span><span></span><span></span>
            </div>
        `;
        messagesContainer.appendChild(typing);
        scrollToBottom();
    }

    function removeTypingIndicator() {
        const typing = document.getElementById('chatTyping');
        if (typing) typing.remove();
    }

    function scrollToBottom() {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    function escapeHtml(text) {
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

});
