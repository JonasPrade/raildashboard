package de.geofabrik.railway_routing.parsers;

import com.graphhopper.reader.ReaderWay;
import com.graphhopper.routing.ev.EdgeIntAccess;
import com.graphhopper.routing.ev.EnumEncodedValue;
import com.graphhopper.routing.util.parsers.TagParser;
import com.graphhopper.storage.IntsRef;

import de.geofabrik.railway_routing.ev.RailwayStatus;
import de.geofabrik.railway_routing.reader.LifecycleTags;

/**
 * Stores the lifecycle status that {@link LifecycleTags#normalize(ReaderWay)} wrote
 * to the way while it was read.
 */
public class OSMRailwayStatusParser implements TagParser {

    protected final EnumEncodedValue<RailwayStatus> railwayStatusEnc;

    public OSMRailwayStatusParser(EnumEncodedValue<RailwayStatus> railwayStatusEnc) {
        this.railwayStatusEnc = railwayStatusEnc;
    }

    @Override
    public void handleWayTags(int edgeId, EdgeIntAccess edgeIntAccess, ReaderWay readerWay, IntsRef relationFlags) {
        RailwayStatus status = RailwayStatus.find(readerWay.getTag(LifecycleTags.STATUS_TAG));
        railwayStatusEnc.setEnum(false, edgeId, edgeIntAccess, status);
    }
}
