package de.geofabrik.railway_routing.reader;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

import org.junit.jupiter.api.Test;

import com.graphhopper.reader.ReaderWay;
import com.graphhopper.routing.ev.ArrayEdgeIntAccess;
import com.graphhopper.routing.ev.EdgeIntAccess;
import com.graphhopper.routing.ev.EncodedValue;
import com.graphhopper.routing.ev.EnumEncodedValue;
import com.graphhopper.storage.IntsRef;

import de.geofabrik.railway_routing.ev.RailwayStatus;
import de.geofabrik.railway_routing.parsers.OSMRailwayStatusParser;

class LifecycleTagsTest {

    private static ReaderWay way(String... keyValues) {
        ReaderWay way = new ReaderWay(1L);
        for (int i = 0; i < keyValues.length; i += 2)
            way.setTag(keyValues[i], keyValues[i + 1]);
        LifecycleTags.normalize(way);
        return way;
    }

    private static RailwayStatus parsedStatus(ReaderWay way) {
        EnumEncodedValue<RailwayStatus> statusEnc = RailwayStatus.create();
        statusEnc.init(new EncodedValue.InitializerConfig());
        EdgeIntAccess edgeIntAccess = new ArrayEdgeIntAccess(1);
        new OSMRailwayStatusParser(statusEnc).handleWayTags(0, edgeIntAccess, way, new IntsRef(2));
        return statusEnc.getEnum(false, 0, edgeIntAccess);
    }

    @Test
    void trackInOperationIsUntouched() {
        ReaderWay way = way("railway", "rail");
        assertEquals("rail", way.getTag("railway"));
        assertNull(way.getTag(LifecycleTags.STATUS_TAG));
        assertEquals(RailwayStatus.EXISTING, parsedStatus(way));
    }

    @Test
    void proposedWithType() {
        ReaderWay way = way("railway", "proposed", "proposed", "rail");
        assertEquals("rail", way.getTag("railway"));
        assertEquals(RailwayStatus.PROPOSED, parsedStatus(way));
    }

    @Test
    void constructionWithType() {
        ReaderWay way = way("railway", "construction", "construction", "rail");
        assertEquals("rail", way.getTag("railway"));
        assertEquals(RailwayStatus.CONSTRUCTION, parsedStatus(way));
    }

    @Test
    void typeFromPrefixedKey() {
        ReaderWay way = way("railway", "proposed", "proposed:railway", "light_rail");
        assertEquals("light_rail", way.getTag("railway"));
        assertEquals(RailwayStatus.PROPOSED, parsedStatus(way));
    }

    @Test
    void lifecyclePrefixWithoutRailwayTag() {
        ReaderWay proposed = way("proposed:railway", "rail");
        assertEquals("rail", proposed.getTag("railway"));
        assertEquals(RailwayStatus.PROPOSED, parsedStatus(proposed));

        ReaderWay construction = way("construction:railway", "rail");
        assertEquals("rail", construction.getTag("railway"));
        assertEquals(RailwayStatus.CONSTRUCTION, parsedStatus(construction));
    }

    @Test
    void constructionWinsOverProposedPrefix() {
        ReaderWay way = way("construction:railway", "rail", "proposed:railway", "rail");
        assertEquals(RailwayStatus.CONSTRUCTION, parsedStatus(way));
    }

    @Test
    void withoutTrackTypeNotRoutable() {
        ReaderWay plain = way("railway", "proposed");
        assertEquals("proposed", plain.getTag("railway"));
        assertNull(plain.getTag(LifecycleTags.STATUS_TAG));

        ReaderWay platform = way("railway", "construction", "construction", "platform");
        assertEquals("construction", platform.getTag("railway"));
        assertNull(platform.getTag(LifecycleTags.STATUS_TAG));

        ReaderWay road = way("highway", "proposed", "proposed", "primary");
        assertNull(road.getTag("railway"));
    }

    @Test
    void trackInOperationWithPlannedChangeStaysExisting() {
        ReaderWay way = way("railway", "rail", "proposed:railway", "light_rail");
        assertEquals("rail", way.getTag("railway"));
        assertEquals(RailwayStatus.EXISTING, parsedStatus(way));
    }

    @Test
    void normalizeIsIdempotent() {
        ReaderWay way = way("railway", "proposed", "proposed", "rail");
        LifecycleTags.normalize(way);
        assertEquals("rail", way.getTag("railway"));
        assertEquals(RailwayStatus.PROPOSED, parsedStatus(way));
    }
}
