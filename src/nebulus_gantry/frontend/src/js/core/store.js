/**
 * Centralized State Management Store
 * Implements a Pub/Sub pattern for state updates.
 */
export class Store {
    constructor(initialState = {}) {
        this.state = initialState;
        this.listeners = new Set();
    }

    /**
     * Get the current state
     * @returns {Object} A copy of the current state
     */
    getState() {
        return { ...this.state };
    }

    /**
     * Update state and notify listeners
     * @param {Object} newState Partial state update
     */
    setState(newState) {
        this.state = { ...this.state, ...newState };
        this.notify();
    }

    /**
     * Subscribe to state changes
     * @param {Function} listener Callback function
     * @returns {Function} Unsubscribe function
     */
    subscribe(listener) {
        this.listeners.add(listener);
        return () => this.listeners.delete(listener);
    }

    /**
     * Notify all listeners of state change
     */
    notify() {
        this.listeners.forEach((listener) => listener(this.state));
    }
}

// Create a singleton instance for global app state
export const appStore = new Store({
    user: null,
    chats: [],
    currentChatId: null,
    theme: 'system',
    isSidebarOpen: true
});
