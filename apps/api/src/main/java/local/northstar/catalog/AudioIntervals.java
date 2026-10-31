package local.northstar.catalog;

import java.util.*;

/** Cross-row rules shared by publication and defensive reads. Intervals are half-open. */
final class AudioIntervals {
    static void validate(List<Map<String,Object>> sentences, Map<String,Long> durations) {
        var ends=new HashMap<String,Long>();
        for(var sentence:sentences) {
            String asset=sentence.get("audioAssetId").toString();
            long start=((Number)sentence.get("startMs")).longValue(),end=((Number)sentence.get("endMs")).longValue();
            Long duration=durations.get(asset);
            if(duration==null || start<0 || end<=start || end>duration || start<ends.getOrDefault(asset,0L))throw new IllegalArgumentException("INTERVAL_INVALID");
            ends.put(asset,end);
        }
    }
}
