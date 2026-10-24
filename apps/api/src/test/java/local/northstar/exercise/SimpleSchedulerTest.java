package local.northstar.exercise;
import static org.junit.jupiter.api.Assertions.*;
import java.time.*;
import org.junit.jupiter.api.Test;
class SimpleSchedulerTest {
    @Test void utcIntervalsCrossMidnightAndDstWithoutCalendarDrift() {
        Clock clock=Clock.fixed(Instant.parse("2026-03-08T06:59:30Z"),ZoneId.of("America/New_York"));
        assertEquals(Instant.parse("2026-03-08T07:00:30Z"),SimpleScheduler.next(clock,"again",9));
        assertEquals(Instant.parse("2026-03-09T06:59:30Z"),SimpleScheduler.next(clock,"good",0));
        assertEquals(clock.instant().plus(Duration.ofDays(32)),SimpleScheduler.next(clock,"good",100));
        Clock midnight=Clock.fixed(Instant.parse("2026-12-31T23:59:30Z"),ZoneOffset.UTC);
        assertEquals(Instant.parse("2027-01-01T00:00:30Z"),SimpleScheduler.next(midnight,"again",0));
        assertEquals(midnight.instant().plus(Duration.ofDays(2)),SimpleScheduler.next(midnight,"good",1));
    }
}
