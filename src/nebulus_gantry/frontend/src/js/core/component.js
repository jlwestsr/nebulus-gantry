/**
 * Base Component Class
 * All UI components should extend this.
 */
export class Component {
    /**
     * @param {string|HTMLElement} elementOrId - The DOM element or ID to bind to
     * @param {Object} props - Initial properties
     */
    constructor(elementOrId, props = {}) {
        this.element = typeof elementOrId === 'string'
            ? document.getElementById(elementOrId)
            : elementOrId;

        this.props = props;

        if (this.element) {
            this.init();
        } else {
            console.warn(`Component initialized with missing element: ${elementOrId}`);
        }
    }

    /**
     * Initialize the component (event listeners, initial render)
     * Override this in subclasses.
     */
    init() {
        this.render();
    }

    /**
     * Render the component content or updates
     * Override this in subclasses.
     */
    render() {
        // Default: do nothing
    }

    /**
     * Helper to find a child element within this component
     * @param {string} selector
     * @returns {HTMLElement}
     */
    find(selector) {
        return this.element ? this.element.querySelector(selector) : null;
    }

    /**
     * Helper to find multiple child elements
     * @param {string} selector
     * @returns {NodeList}
     */
    findAll(selector) {
        return this.element ? this.element.querySelectorAll(selector) : [];
    }

    /**
     * Update props and re-render if needed
     * @param {Object} newProps
     */
    setProps(newProps) {
        this.props = { ...this.props, ...newProps };
        this.render();
    }
}
