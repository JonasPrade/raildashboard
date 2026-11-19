package de.geofabrik.railway_routing.reader;

import java.util.Set;

import com.graphhopper.reader.ReaderWay;

/**
 * Turns the OSM lifecycle tagging of tracks that are not in operation yet into the
 * tagging of a track in operation plus an artificial status tag, so that all other
 * parsers (class, speed, gauge, electrification, access) work unchanged.
 *
 * Supported, each with a track type the router knows (rail, light_rail, tram, subway,
 * narrow_gauge):
 *
 *   railway=proposed     + proposed=TYPE      (or proposed:railway=TYPE)
 *   railway=construction + construction=TYPE  (or construction:railway=TYPE)
 *   proposed:railway=TYPE      without a railway=* tag
 *   construction:railway=TYPE  without a railway=* tag
 *
 * A way without any track type (plain railway=proposed or railway=construction, also
 * with proposed=yes / construction=yes) gets the status tag plus UNTYPED_TAG and keeps
 * its railway=* value: it could be a tram as well as a main line, so its railway_class
 * stays OTHER and a profile admits it only on explicit request (see the patched
 * RailAccessParser, which treats every way with a status tag as accessible). A way
 * whose type is one the router does not know (e.g. construction=platform) stays out.
 *
 * A way that already has a routable railway=* value is in operation; lifecycle
 * prefixes on it describe a planned change of an existing track and are ignored.
 */
public final class LifecycleTags {

    /** Artificial tag, read by OSMRailwayStatusParser. */
    public static final String STATUS_TAG = "_railway_status";

    /** Artificial tag on a planned way without a track type (railway_class OTHER). */
    public static final String UNTYPED_TAG = "_railway_untyped";

    private static final Set<String> TRACK_TYPES = Set.of("rail", "light_rail", "tram", "subway", "narrow_gauge");

    private LifecycleTags() {
    }

    public static void normalize(ReaderWay way) {
        if (way.getTag(STATUS_TAG) != null)
            return;
        String railway = way.getTag("railway");
        if (railway == null) {
            if (!apply(way, "construction", way.getTag("construction:railway")))
                apply(way, "proposed", way.getTag("proposed:railway"));
        } else if (railway.equals("construction") || railway.equals("proposed")) {
            String type = way.getTag(railway);
            if (type == null || !TRACK_TYPES.contains(type))
                type = way.getTag(railway + ":railway");
            if (!apply(way, railway, type) && isUntyped(way, railway)) {
                way.setTag(STATUS_TAG, railway);
                way.setTag(UNTYPED_TAG, "yes");
            }
        }
    }

    /** No type given at all: neither STATUS=TYPE nor STATUS:railway=TYPE (or only "yes"). */
    private static boolean isUntyped(ReaderWay way, String status) {
        return isBlank(way.getTag(status)) && isBlank(way.getTag(status + ":railway"));
    }

    private static boolean isBlank(String value) {
        return value == null || value.isEmpty() || value.equals("yes");
    }

    private static boolean apply(ReaderWay way, String status, String type) {
        if (type == null || !TRACK_TYPES.contains(type))
            return false;
        way.setTag("railway", type);
        way.setTag(STATUS_TAG, status);
        return true;
    }
}
