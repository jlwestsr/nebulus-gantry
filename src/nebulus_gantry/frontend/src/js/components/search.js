import { Component } from '../core/component.js';
import { Icons } from '../core/icons.js';
import { appStore } from '../core/store.js';

export class Search extends Component {
    constructor(elementOrId) {
        // Create container if it doesn't exist (Modal Overlay)
        let el = typeof elementOrId === 'string' ? document.getElementById(elementOrId) : elementOrId;
        if (!el) {
            el = document.createElement('div');
            el.id = 'search-modal-overlay';
            document.body.appendChild(el);
        }
        super(el, { isOpen: false, results: [], query: '' });

        // Bind methods
        this.close = this.close.bind(this);
        this.handleInput = this.handleInput.bind(this);
        this.handleKeydown = this.handleKeydown.bind(this);
    }

    init() {
        this.render();
        this.setupGlobalListeners();
    }

    setupGlobalListeners() {
        // Expose open method globally or listen to store
        // Strategy: Listen for custom event 'nebulus:open-search'
        document.addEventListener('nebulus:open-search', () => this.open());

        // Also close on Escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.props.isOpen) this.close();
        });
    }

    open() {
        this.setProps({ isOpen: true });
        setTimeout(() => {
            const input = this.find('#search-input');
            if (input) input.focus();
        }, 50);
    }

    close() {
        this.setProps({ isOpen: false, results: [], query: '' });
    }

    async performSearch(query) {
        this.setProps({ query }); // Update query state to trigger typing feedback if needed
        if (query.length < 2) {
            this.setProps({ results: [] });
            return;
        }

        try {
            const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
            const data = await res.json();
            this.setProps({ results: data });
        } catch (err) {
            console.error("Search failed", err);
            // Could set error state here
        }
    }

    handleInput(e) {
        const val = e.target.value;
        if (this.timeout) clearTimeout(this.timeout);
        this.timeout = setTimeout(() => this.performSearch(val), 300);
    }

    handleKeydown(e) {
        if (e.key === 'Escape') this.close();
    }

    selectResult(chatId) {
        // Navigate
        window.location.href = `/?chat_id=${chatId}`;
        this.close();
    }

    render() {
        if (!this.element) return;
        const { isOpen, results, query } = this.props;

        if (isOpen) {
            this.element.classList.add('open');
        } else {
            this.element.classList.remove('open');
        }

        // Only re-render content if structure is missing or just opening?
        // Ideally we differentiate between full render and partial updates.
        // For simplicity in this base class, we re-render HTML. Assumes strict MVC.

        this.element.innerHTML = `
            <div id="search-modal">
                <div class="search-header">
                    ${Icons.search}
                    <input type="text" id="search-input" placeholder="Search chats..." autocomplete="off" value="${query}">
                </div>
                <div class="search-results" id="search-results">
                    ${this.renderResults(results, query)}
                </div>
            </div>
        `;

        // Re-bind events since innerHTML was wiped
        const overlay = this.element;
        // Self-click to close (overlay click)
        overlay.onclick = (e) => {
            if (e.target === overlay) this.close();
        };

        const input = this.find('#search-input');
        if (input) {
            input.oninput = this.handleInput;
            // Restore focus if we re-rendered while typing
            // This is a downside of innerHTML re-render.
            // Better MVC would rely on finer grained DOM updates, but for this task:
            if (isOpen) {
                // input.focus(); // Aggressive refocuser
                // Selection range?
            }
        }

        // Bind result clicks
        this.findAll('.search-result-item').forEach(el => {
            el.onclick = () => this.selectResult(el.dataset.id);
        });
    }

    renderResults(results, query) {
        if (!query || query.length < 2) {
            return '<div style="text-align:center; padding: 20px; color: #555;">Type to search...</div>';
        }
        if (results.length === 0) {
            return '<div style="text-align:center; padding: 20px; color: #7d8590;">No results found.</div>';
        }

        const escapeHtml = (unsafe) => {
            return unsafe
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        };

        return results.map(item => `
            <div class="search-result-item" data-id="${item.chat_id}">
                <div class="result-title">${escapeHtml(item.title)}</div>
                <div class="result-snippet">${escapeHtml(item.snippet)}</div>
                <div class="result-meta">${new Date(item.created_at).toLocaleDateString()}</div>
            </div>
        `).join('');
    }
}
