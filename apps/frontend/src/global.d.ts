/// <reference types="vite/client" />

// allow importing plain CSS files in TS
declare module "*.css";

interface ImportMetaEnv {
    readonly REACT_APP_TILE_LAYER_URL?: string;
}

interface ImportMeta {
    readonly env: ImportMetaEnv;
}
