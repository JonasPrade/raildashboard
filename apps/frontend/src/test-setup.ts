import "@testing-library/jest-dom/vitest";

// jsdom implements neither API, but MantineProvider reads matchMedia for the
// colour scheme and several Mantine components observe their own size. Without
// the stubs every test that renders inside a provider throws on mount.
Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addEventListener: () => {},
        removeEventListener: () => {},
        addListener: () => {},
        removeListener: () => {},
        dispatchEvent: () => false,
    }),
});

class ResizeObserverStub {
    observe() {}
    unobserve() {}
    disconnect() {}
}

window.ResizeObserver ??= ResizeObserverStub as unknown as typeof ResizeObserver;
