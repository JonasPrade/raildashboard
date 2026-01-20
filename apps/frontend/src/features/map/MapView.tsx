import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";

const tileLayerUrl = import.meta.env.REACT_APP_TILE_LAYER_URL as string | undefined;
const tileAttribution =
    'Kartenhintergrund: <a href="https://www.bkg.bund.de" target="_blank" rel="noopener noreferrer">Bundesamt für Kartographie und Geodäsie</a>';

export default function MapView() {
    const mapContainerRef = useRef<HTMLDivElement | null>(null);

    useEffect(() => {
        if (!tileLayerUrl || !mapContainerRef.current) {
            return undefined;
        }

        const mapInstance = new maplibregl.Map({
            container: mapContainerRef.current,
            style: {
                version: 8,
                sources: {
                    basemap: {
                        type: "raster",
                        tiles: [tileLayerUrl],
                        tileSize: 256,
                        attribution: tileAttribution
                    }
                },
                layers: [
                    {
                        id: "basemap",
                        type: "raster",
                        source: "basemap"
                    }
                ]
            },
            center: [10.0, 51.0],
            zoom: 5
        });

        return () => {
            mapInstance.remove();
        };
    }, [tileLayerUrl]);

    if (!tileLayerUrl) {
        return (
            <div
                style={{
                    height: "800px",
                    backgroundColor: "#f2f2f2",
                    borderRadius: "8px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    padding: "24px",
                    textAlign: "center"
                }}
                role="alert"
            >
                <p>
                    Kartenkachel-URL fehlt. Bitte die Umgebungsvariable
                    <strong> REACT_APP_TILE_LAYER_URL</strong> setzen.
                </p>
            </div>
        );
    }

    return <div ref={mapContainerRef} style={{ height: "800px" }} />;
}
