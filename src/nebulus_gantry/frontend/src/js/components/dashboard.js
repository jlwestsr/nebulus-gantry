import { Component } from '../core/component.js';
import { Icons } from '../core/icons.js';
import { appStore } from '../core/store.js';

export class Dashboard extends Component {
    constructor(elementOrId) {
        super(elementOrId, {
            visible: true,
            model: "Llama 3.1",
            user: appStore.getState().user
        });

        // Subscribe to store
        this.unsubscribe = appStore.subscribe((state) => {
            // Visibility logic: If we have a currentChatId in store, dashboard should modify visibility?
            // Actually, dashboard usually checks URL params.
            // Let's assume passed in props or check URL.
            if (state.user && state.user !== this.props.user) {
                this.setProps({ user: state.user });
            }
        });
    }

    init() {
        // Check URL for chat_id
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('chat_id')) {
            this.setProps({ visible: false });
        } else {
            this.render();
        }
    }

    handleSuggestion(text) {
        // Dispatch event for Chat component to handle
        const event = new CustomEvent('nebulus:set-input', { detail: { text, autoSubmit: false } });
        document.dispatchEvent(event);

        // Hide dashboard? Usually we stay until submit, but here we just fill.
        // If autoSubmit is true, we hide.
    }

    handleSubmit() {
        const input = this.find('#dashboard-input');
        if (input && input.value.trim()) {
            const text = input.value.trim();
            // Dispatch event for Chat component to handle
            const event = new CustomEvent('nebulus:set-input', { detail: { text, autoSubmit: true } });
            document.dispatchEvent(event);

            this.setProps({ visible: false });
        }
    }

    render() {
        // If forced hidden or chat_id present
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('chat_id')) {
            if (this.element) this.element.style.display = 'none';
            return;
        }

        if (!this.element) {
            // Create if missing
            this.element = document.createElement('div');
            this.element.id = 'nebulus-dashboard';
            document.body.appendChild(this.element);
        }

        this.element.style.display = this.props.visible ? 'flex' : 'none';
        if (!this.props.visible) return;

        const { user, model } = this.props;
        const name = user ? (user.full_name || user.username || 'User').split(' ')[0] : 'User';

        this.element.innerHTML = `
            <div class="dashboard-content">
                 <div class="dashboard-greeting">
                     <span class="gradient-text">Hi ${name}</span><br>
                     <span>Where should we start?</span>
                </div>

                 <div class="input-pill-container">
                    <div class="input-pill-label">Ask Nebulus</div>
                    <div class="input-pill">
                         <div class="icon-btn">${Icons.plus}</div>
                         <input type="text" id="dashboard-input" placeholder="Type something..." autocomplete="off">
                         <div class="right-actions">
                              <div class="icon-btn" title="Attach file">${Icons.paperclip}</div>
                              <div class="icon-btn" id="dashboard-submit">${Icons.send}</div>
                         </div>
                    </div>
                </div>

                <div class="suggestions-grid">
                    ${this.renderSuggestions()}
                </div>
            </div>
        `;

        // Bindings
        const input = this.find('#dashboard-input');
        input.focus();
        input.onkeydown = (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.handleSubmit();
            }
        };

        this.find('#dashboard-submit').onclick = () => this.handleSubmit();

        this.findAll('.suggestion-pill').forEach(el => {
            el.onclick = () => this.handleSuggestion(el.dataset.text);
        });
    }

    renderSuggestions() {
        const suggestions = [
            { text: 'Create image', icon: '🎨' },
            { text: 'Create video', icon: '🎥' },
            { text: 'Write anything', icon: '✍️' },
            { text: 'Help me learn', icon: '🎓' },
            { text: 'Boost my day', icon: '🚀' },
            { text: 'Stay organized', icon: '📅' },
        ];

        return suggestions.map(s => `
            <div class="suggestion-pill" data-text="${s.text}">
                <span class="emoji">${s.icon}</span> ${s.text}
            </div>
        `).join('');
    }
}
