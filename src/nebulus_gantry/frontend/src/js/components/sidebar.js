import { Component } from '../core/component.js';
import { appStore } from '../core/store.js';
import { Icons } from '../core/icons.js';

export class Sidebar extends Component {
    constructor(elementOrId) {
        super(elementOrId, {
            collapsed: localStorage.getItem('sidebar-collapsed') === 'true',
            user: null,
            recentChats: []
        });

        // Subscribe to store updates
        this.unsubscribe = appStore.subscribe((state) => {
            if (state.isSidebarOpen !== !this.props.collapsed) {
                this.setProps({ collapsed: !state.isSidebarOpen });
            }
        });
    }

    async init() {
        // Initial Fetch
        try {
            const [history, user] = await Promise.all([
                fetch('/api/history').then(res => res.json()),
                fetch('/me').then(res => res.json())
            ]);

            // Update Store
            appStore.setState({
                user: user,
                chats: history
            });

            this.setProps({ user, recentChats: history });
        } catch (err) {
            console.error("Failed to load sidebar data", err);
            this.setProps({ user: { full_name: "Guest", username: "guest" }, recentChats: [] });
        }
    }

    toggle() {
        const collapsed = !this.props.collapsed;
        this.setProps({ collapsed });
        localStorage.setItem('sidebar-collapsed', collapsed);

        // Update DOM classes globally since CSS relies on body class
        if (collapsed) {
            document.body.classList.add('sidebar-collapsed');
        } else {
            document.body.classList.remove('sidebar-collapsed');
        }

        // Update Store
        appStore.setState({ isSidebarOpen: !collapsed });
    }

    render() {
        if (!this.element) return;

        const { user, recentChats, collapsed } = this.props;
        const initials = user ? (user.full_name || user.username || "G").charAt(0).toUpperCase() : "G";

        // Apply body class for initial state
        if (collapsed) document.body.classList.add('sidebar-collapsed');
        else document.body.classList.remove('sidebar-collapsed');

        this.element.innerHTML = `
            <div class="sidebar-header">
                <img src="/public/sidebar_logo.png" alt="Logo" class="sidebar-logo-img">
                <div class="logo-text">NEBULUS</div>
                <div class="toggle-btn" id="sidebar-toggle-btn">
                    ${collapsed ? Icons.chevronRight : Icons.chevronLeft}
                </div>
            </div>

            <div class="new-chat-container">
                 <div class="new-chat-btn" onclick="window.location.href='/'">
                    <span class="icon-plus">${Icons.plus}</span>
                    <span>New chat</span>
                </div>
            </div>

            <div class="sidebar-scroll-area">
                <div class="sidebar-section my-stuff-section">
                    <div class="my-stuff-grid">
                        <div class="stuff-item" title="Nebulus">
                             <div class="stuff-icon gradient-1">N</div>
                        </div>
                         <div class="stuff-item" title="Gantry">
                             <div class="stuff-icon gradient-2">G</div>
                        </div>
                         <div class="stuff-item" title="Knowledge">
                             <div class="stuff-icon gradient-3">K</div>
                        </div>
                    </div>
                </div>

                <div class="sidebar-section">
                    <div class="nav-item" onclick="window.location.href='/notes'">
                        <div class="nav-icon">${Icons.fileText}</div>
                        <span class="nav-label">Notes</span>
                    </div>
                    <div class="nav-item" onclick="window.location.href='/workspace'">
                        <div class="nav-icon">${Icons.grid}</div>
                        <span class="nav-label">Workspace</span>
                    </div>
                </div>

                <div class="sidebar-section">
                     <div class="nav-item" id="search-trigger">
                        <div class="nav-icon">${Icons.search}</div>
                        <span class="nav-label">Search chats</span>
                    </div>
                    <div class="recent-chats-section">
                        <div id="recent-chats-list" class="recent-chats-list">
                            ${this.renderRecentChats(recentChats)}
                        </div>
                    </div>
                </div>
            </div>

            <div class="sidebar-footer">
                 <div class="user-profile">
                    <div class="user-avatar">${initials}</div>
                    <span class="nav-label">${user ? (user.full_name || user.username) : 'Loading...'}</span>
                </div>
            </div>
        `;

        // Bind Events
        this.find('#sidebar-toggle-btn').addEventListener('click', () => this.toggle());

        // We can bind Search trigger via global event or store logic
        // keeping simple for now
        this.find('#search-trigger').addEventListener('click', () => {
            // In full refactor, Search would be a component listening to Store
            // For now, call global legacy or dispatch event (TODO in Phase 2)
            console.log("Search clicked (TODO: Link to Search Component)");
        });
    }

    renderRecentChats(chats) {
        if (!chats || chats.length === 0) {
            return '<div style="padding: 10px; color: #555; font-size: 0.7rem;" class="nav-label">No recent chats</div>';
        }
        return chats.map(chat => `
            <div class="nav-item sub-item" data-id="${chat.id}">
                <span class="nav-label" onclick="window.location.href='/?chat_id=${chat.id}'">${chat.title}</span>
                <div class="chat-options-btn">⋮</div>
            </div>
        `).join('');
    }
}
