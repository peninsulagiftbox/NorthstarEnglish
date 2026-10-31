package local.northstar.catalog;

import static org.junit.jupiter.api.Assertions.*;
import java.util.*;
import org.junit.jupiter.api.Test;

class AudioIntervalsTest {
    Map<String,Object> segment(String asset,int start,int end){return Map.of("audioAssetId",asset,"startMs",start,"endMs",end);}
    @Test void acceptsSharedHalfOpenIntervalsGapsAndIndependentFiles(){
        AudioIntervals.validate(List.of(segment("shared",8400,12100),segment("shared",12100,14000),segment("own",0,2000),segment("shared",15000,20000)),Map.of("shared",20000L,"own",2000L));
    }
    @Test void rejectsOverlapReverseMissingAssetAndOutOfBounds(){
        for(var data:List.of(List.of(segment("a",-1,1)),List.of(segment("a",1,1)),List.of(segment("a",0,2001)),List.of(segment("foreign",0,1)),List.of(segment("a",500,1000),segment("a",999,1500))))
            assertThrows(IllegalArgumentException.class,()->AudioIntervals.validate(data,Map.of("a",2000L)));
    }
}
