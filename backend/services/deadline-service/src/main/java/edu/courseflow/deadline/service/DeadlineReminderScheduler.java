package edu.courseflow.deadline.service;

import edu.courseflow.deadline.dto.DeadlineDtos.ReminderRunDto;
import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
@ConditionalOnProperty(prefix = "courseflow.deadline.reminders", name = "auto-dispatch-enabled",
        havingValue = "true", matchIfMissing = true)
public class DeadlineReminderScheduler {

    private static final Logger log = LoggerFactory.getLogger(DeadlineReminderScheduler.class);

    private final DeadlineService deadlines;

    public DeadlineReminderScheduler(DeadlineService deadlines) {
        this.deadlines = deadlines;
    }

    @Scheduled(fixedDelayString = "${courseflow.deadline.reminders.dispatch-interval-ms:60000}")
    public void dispatchDueReminders() {
        List<ReminderRunDto> dueRuns = deadlines.dueRuns();
        int dispatched = 0;
        for (ReminderRunDto run : dueRuns) {
            try {
                deadlines.dispatch(java.util.UUID.fromString(run.id()));
                dispatched++;
            } catch (IllegalArgumentException staleOrNotDue) {
                log.debug("deadline reminder {} was already claimed or is no longer due", run.id());
            } catch (RuntimeException ex) {
                log.warn("deadline reminder {} failed to dispatch; it will be retried", run.id(), ex);
            }
        }
        if (dispatched > 0) {
            log.info("deadline reminder scheduler dispatched {} reminder(s)", dispatched);
        }
    }
}
