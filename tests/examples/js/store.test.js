
import { Store } from '../../../src/nebulus_gantry/frontend/src/js/core/store.js';

describe('Store Core Class', () => {
    let store;

    beforeEach(() => {
        store = new Store({ count: 0 });
    });

    test('should initialize with provided state', () => {
        expect(store.getState()).toEqual({ count: 0 });
    });

    test('setState should update state immutably', () => {
        store.setState({ count: 1 });
        expect(store.getState()).toEqual({ count: 1 });

        // Verify new object reference (shallow check implied by toEqual usually, but let's check explicit change)
        const oldState = store.getState();
        store.setState({ count: 2 });
        expect(store.getState()).not.toBe(oldState);
    });

    test('subscribe should notify listeners on change', () => {
        const listener = jest.fn();
        store.subscribe(listener);

        store.setState({ count: 5 });

        expect(listener).toHaveBeenCalledTimes(1);
        expect(listener).toHaveBeenCalledWith({ count: 5 });
    });

    test('unsubscribe should stop notifications', () => {
        const listener = jest.fn();
        const unsubscribe = store.subscribe(listener);

        store.setState({ count: 1 });
        expect(listener).toHaveBeenCalledTimes(1);

        unsubscribe();
        store.setState({ count: 2 });
        expect(listener).toHaveBeenCalledTimes(1); // Still 1
    });

    test('setState should merge partial updates', () => {
        // Initialize with complex state
        store = new Store({ user: 'Alice', theme: 'dark' });

        store.setState({ theme: 'light' });

        expect(store.getState()).toEqual({ user: 'Alice', theme: 'light' });
    });
});
