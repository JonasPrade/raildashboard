package de.geofabrik.railway_routing.ev;

import com.graphhopper.routing.ev.EnumEncodedValue;
import com.graphhopper.util.Helper;

/**
 * Lifecycle status of a track: in operation, under construction or only proposed.
 * Tracks that are not in operation are imported so that a profile can opt in to them;
 * every profile that does not must exclude them explicitly (railway_status != EXISTING).
 */
public enum RailwayStatus {
    EXISTING, CONSTRUCTION, PROPOSED;

    public static final String KEY = "railway_status";

    public static EnumEncodedValue<RailwayStatus> create() {
        return new EnumEncodedValue<>(RailwayStatus.KEY, RailwayStatus.class);
    }

    @Override
    public String toString() {
        return Helper.toLowerCase(super.toString());
    }

    public static RailwayStatus find(String name) {
        if (name == null || name.isEmpty())
            return EXISTING;
        try {
            return RailwayStatus.valueOf(Helper.toUpperCase(name));
        } catch (IllegalArgumentException ex) {
            return EXISTING;
        }
    }
}
