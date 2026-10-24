package local.northstar.exercise;

import java.time.*;

/** Self-rating intervals only; this is not a measured mastery model. */
public final class SimpleScheduler {
    private SimpleScheduler() {}
    public static Instant next(Clock clock, String rating, int previousSuccesses) {
        return clock.instant().plus(rating.equals("again") ? Duration.ofMinutes(1)
                : Duration.ofDays(1L << Math.min(previousSuccesses, 5)));
    }
}
