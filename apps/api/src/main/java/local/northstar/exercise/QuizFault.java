package local.northstar.exercise;

import org.springframework.stereotype.Component;

/** Overridden only by integration-test configuration; no runtime fault controls. */
@Component
public class QuizFault {
    public void afterItem(int ordinal,int total) {}
    public void beforeReceipt() {}
}
