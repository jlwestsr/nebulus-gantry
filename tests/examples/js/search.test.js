
/**
 * @jest-environment jsdom
 */

// Mock the Component base class and Icons if not using a full transformer
// For this example, we assume we are testing the logic of Search independent of the complex base class DOM manipulation if possible,
// or we mock the dependencies.
// However, the user asked for ES6 class testing. We'll simulate a standard Jest import.

import { Search } from '../../../src/nebulus_gantry/frontend/src/js/components/search.js';
import { appStore } from '../../../src/nebulus_gantry/frontend/src/js/core/store.js';

// Mock dependencies
jest.mock('../../../src/nebulus_gantry/frontend/src/js/core/icons.js', () => ({
    Icons: { search: '<svg>search</svg>' }
}));

// Mock Fetch Global
global.fetch = jest.fn();

describe('Search Component', () => {
    let searchComponent;
    let container;

    beforeEach(() => {
        // Setup DOM
        container = document.createElement('div');
        container.id = 'search-container';
        document.body.appendChild(container);

        searchComponent = new Search('search-container');
    });

    afterEach(() => {
        document.body.innerHTML = '';
        jest.clearAllMocks();
    });

    test('should initialize with isOpen false', () => {
        expect(searchComponent.props.isOpen).toBe(false);
        expect(container.classList.contains('open')).toBe(false);
    });

    test('open() should set isOpen true and focus input', (done) => {
        searchComponent.open();

        expect(searchComponent.props.isOpen).toBe(true);
        // We need to wait for the setTimeout(..., 50) in open()
        setTimeout(() => {
            expect(container.querySelector('#search-input')).toBe(document.activeElement);
            done();
        }, 60);
    });

    test('performSearch() should update results on success', async () => {
        const mockData = [{ title: "Result 1", chat_id: "123", snippet: "text", created_at: new Date().toISOString() }];

        fetch.mockResolvedValueOnce({
            json: async () => mockData
        });

        await searchComponent.performSearch("test");

        expect(fetch).toHaveBeenCalledWith("/api/search?q=test");
        expect(searchComponent.props.results).toEqual(mockData);
        // Verify render happened
        expect(container.innerHTML).toContain("Result 1");
    });

    test('performSearch() should handle empty requests', async () => {
        await searchComponent.performSearch("a"); // Too short

        expect(fetch).not.toHaveBeenCalled();
        expect(searchComponent.props.results).toEqual([]);
    });

    test('render() should display no results message when empty', () => {
        searchComponent.setProps({ isOpen: true, results: [], query: "xyz" });
        expect(container.innerHTML).toContain("No results found");
    });
});
