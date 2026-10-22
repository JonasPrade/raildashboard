/// <reference types="vite/client" />

// allow importing plain CSS files in TS
declare module "*.css";

interface ImportMetaEnv {
    readonly REACT_APP_TILE_LAYER_URL?: string;
    readonly REACT_APP_TILE_LAYER_URL_DARK?: string;
}

interface ImportMeta {
    readonly env: ImportMetaEnv;
}

// Build version shown in the footer ("Fassung"); vite.config.ts defines it from
// VITE_APP_VERSION (short commit SHA in release builds, "dev" locally).
declare const __APP_VERSION__: string;
