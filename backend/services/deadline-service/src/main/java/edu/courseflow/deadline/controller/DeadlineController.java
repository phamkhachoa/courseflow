package edu.courseflow.deadline.controller;

import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.deadline.dto.DeadlineDtos.CreateReminderPolicyRequestDto;
import edu.courseflow.deadline.dto.DeadlineDtos.ReminderPolicyDto;
import edu.courseflow.deadline.dto.DeadlineDtos.ReminderRunDto;
import edu.courseflow.deadline.dto.DeadlineDtos.ScheduleReminderRequestDto;
import edu.courseflow.deadline.service.DeadlineService;
import jakarta.validation.Valid;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
public class DeadlineController {

    private final DeadlineService deadlines;

    public DeadlineController(DeadlineService deadlines) {
        this.deadlines = deadlines;
    }

    @GetMapping("/internal/deadlines/policies")
    public List<ReminderPolicyDto> policies(@RequestParam Optional<UUID> courseId, CurrentUser user) {
        callerId(user);
        return deadlines.listPolicies(courseId);
    }

    @PostMapping("/internal/deadlines/policies")
    public ReminderPolicyDto createPolicy(@Valid @RequestBody CreateReminderPolicyRequestDto request,
                                          CurrentUser user) {
        requireStaff(user);
        return deadlines.createPolicy(request);
    }

    @PostMapping("/internal/deadlines/reminders")
    public ReminderRunDto schedule(@Valid @RequestBody ScheduleReminderRequestDto request, CurrentUser user) {
        requireStaff(user);
        return deadlines.schedule(request);
    }

    @GetMapping("/internal/deadlines/reminders/due")
    public List<ReminderRunDto> dueRuns(CurrentUser user) {
        requireStaff(user);
        return deadlines.dueRuns();
    }

    @PostMapping("/internal/deadlines/reminders/{reminderRunId}/dispatch")
    public ReminderRunDto dispatch(@PathVariable UUID reminderRunId, CurrentUser user) {
        requireStaff(user);
        return deadlines.dispatch(reminderRunId);
    }

    private String callerId(CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Authentication required");
        }
        return String.valueOf(user.id());
    }

    private void requireStaff(CurrentUser user) {
        callerId(user);
        if (!user.hasAnyRole("ADMIN", "ORG_ADMIN", "INSTRUCTOR")) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN,
                    "Requires ADMIN, ORG_ADMIN or INSTRUCTOR role");
        }
    }
}
