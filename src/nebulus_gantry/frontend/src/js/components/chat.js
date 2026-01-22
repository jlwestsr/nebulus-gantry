import { Component } from '../core/component.js';
import { Icons } from '../core/icons.js';
import { appStore } from '../core/store.js';

export class Chat extends Component {
    constructor(elementOrId) {
        // Chat component often binds to existing DOM structures provided by Chainlit
        // or injects interaction layers.
        super(elementOrId, {});

        this.handleClearAll = this.handleClearAll.bind(this);
    }

    init() {
        this.setupCommandInterception();
        this.listenForInputEvents();
    }

    listenForInputEvents() {
        // Listen for events from Dashboard or other components
        document.addEventListener('nebulus:set-input', (e) => {
            const { text, autoSubmit } = e.detail;
            this.setInput(text, autoSubmit);
        });
    }

    setupCommandInterception() {
        const handler = (e) => {
            // 1. Identify input
            let input = document.getElementById('chat-input');
            if (!input && document.activeElement && (document.activeElement.tagName === 'TEXTAREA' || document.activeElement.tagName === 'INPUT')) {
                input = document.activeElement;
            }
            if (!input) return;

            const val = input.value.trim();
            if (val !== '/clear_all') return;

            // 2. Trigger check
            let isTrigger = false;
            if (e.type === 'keydown' && e.key === 'Enter' && !e.shiftKey) isTrigger = true;
            if (e.type === 'click' && e.target.closest('#chat-submit, button[type="submit"]')) isTrigger = true;

            if (isTrigger) {
                e.preventDefault();
                e.stopImmediatePropagation();

                // TODO: Replace with Modal Component
                if (confirm("Delete All Chats?\n\nAre you sure you want to delete all chat history? This action cannot be undone.")) {
                    this.handleClearAll();
                }
            }
        };

        document.addEventListener('keydown', handler, true);
        document.addEventListener('click', handler, true);
    }

    async handleClearAll() {
        try {
            const res = await fetch('/api/chats', { method: 'DELETE' });
            const data = await res.json();
            if (data.status === 'success') {
                const input = document.getElementById('chat-input');
                if (input) input.value = '';

                // Refresh Sidebar via Store or Event
                // Ideally dispatch event "nebulus:refresh-sidebar"
                // For now, reload to be safe or redirect
                const urlParams = new URLSearchParams(window.location.search);
                if (urlParams.get('chat_id')) {
                    window.location.href = '/';
                } else {
                    // Reload sidebar logic?
                    // appStore.dispatch('refreshSidebar')
                    window.location.reload();
                }
            } else {
                alert("Failed to delete chats");
            }
        } catch (err) {
            console.error(err);
            alert("Error deleting chats");
        }
    }

    setInput(text, autoSubmit = false) {
        const textarea = document.querySelector('#chat-input, textarea');
        if (textarea) {
            // React state hack
            const nativeTextAreaValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
            nativeTextAreaValueSetter.call(textarea, text);
            textarea.dispatchEvent(new Event('input', { bubbles: true }));
            textarea.focus();

            if (autoSubmit) {
                setTimeout(() => {
                    const event = new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', which: 13, keyCode: 13, bubbles: true, cancelable: true });
                    textarea.dispatchEvent(event);
                    // Backup click
                    setTimeout(() => {
                        if (textarea.value === text) {
                            const btn = document.getElementById('chat-submit');
                            if (btn) btn.click();
                        }
                    }, 200);
                }, 100);
            }
        }
    }

    loadHistory(chatId) {
        // SPA Logic
        if (window.location.pathname === '/' || window.location.pathname === '') {
            const newUrl = `/?chat_id=${chatId}`;
            history.pushState({ chat_id: chatId }, "", newUrl);

            // Hide Dashboard
            // appStore.setState({ dashboardVisible: false }); // Todo: wire store
            const dash = document.getElementById('nebulus-dashboard');
            if (dash) dash.style.display = 'none';

            this.setInput(`/load_history ${chatId}`, true);
        } else {
            window.location.href = `/?chat_id=${chatId}`;
        }
    }
}
