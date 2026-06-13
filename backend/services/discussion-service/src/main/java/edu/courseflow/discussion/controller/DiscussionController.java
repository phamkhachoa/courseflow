package edu.courseflow.discussion.controller;

import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.commonlibrary.security.CourseAccessClient;
import edu.courseflow.discussion.dto.DiscussionDtos.CreateCommentRequestDto;
import edu.courseflow.discussion.dto.DiscussionDtos.CreateThreadRequestDto;
import edu.courseflow.discussion.dto.DiscussionDtos.DiscussionCommentDto;
import edu.courseflow.discussion.dto.DiscussionDtos.DiscussionThreadDto;
import edu.courseflow.discussion.service.DiscussionService;
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
public class DiscussionController {

    private final DiscussionService discussions;
    private final CourseAccessClient courseAccess;

    public DiscussionController(DiscussionService discussions, CourseAccessClient courseAccess) {
        this.discussions = discussions;
        this.courseAccess = courseAccess;
    }

    @GetMapping("/internal/discussions/threads")
    public List<DiscussionThreadDto> listThreads(@RequestParam Optional<UUID> courseId,
                                                 @RequestParam Optional<UUID> assignmentId,
                                                 CurrentUser user) {
        callerId(user);
        if (courseId.isPresent()) {
            if (isStaff(user)) {
                courseAccess.requireCourseStaffAccess(user, courseId.get());
            } else {
                courseAccess.requireCourseAccess(user, courseId.get());
            }
        } else if (!isPlatformAdmin(user)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "courseId is required for scoped discussion access");
        }
        return discussions.listThreads(courseId, assignmentId);
    }

    @PostMapping("/internal/discussions/threads")
    public DiscussionThreadDto createThread(@Valid @RequestBody CreateThreadRequestDto request,
                                            CurrentUser user) {
        courseAccess.requireCourseAccess(user, UUID.fromString(request.courseId()));
        CreateThreadRequestDto trusted = new CreateThreadRequestDto(
                request.courseId(),
                request.assignmentId(),
                callerId(user),
                request.title());
        return discussions.createThread(trusted);
    }

    @GetMapping("/internal/discussions/threads/{threadId}")
    public DiscussionThreadDto getThread(@PathVariable UUID threadId, CurrentUser user) {
        callerId(user);
        DiscussionThreadDto thread = discussions.getThread(threadId);
        if (isStaff(user)) {
            courseAccess.requireCourseStaffAccess(user, UUID.fromString(thread.courseId()));
        } else {
            courseAccess.requireCourseAccess(user, UUID.fromString(thread.courseId()));
        }
        return thread;
    }

    @PostMapping("/internal/discussions/threads/{threadId}/comments")
    public DiscussionCommentDto addComment(@PathVariable UUID threadId,
                                           @Valid @RequestBody CreateCommentRequestDto request,
        CurrentUser user) {
        DiscussionThreadDto thread = discussions.getThread(threadId);
        if (isStaff(user)) {
            courseAccess.requireCourseStaffAccess(user, UUID.fromString(thread.courseId()));
        } else {
            courseAccess.requireCourseAccess(user, UUID.fromString(thread.courseId()));
        }
        CreateCommentRequestDto trusted = new CreateCommentRequestDto(callerId(user), request.body());
        return discussions.addComment(threadId, trusted);
    }

    @PostMapping("/internal/discussions/threads/{threadId}/comments/{commentId}/accept")
    public DiscussionThreadDto acceptComment(@PathVariable UUID threadId, @PathVariable UUID commentId,
                                             CurrentUser user) {
        requireStaff(user);
        DiscussionThreadDto thread = discussions.getThread(threadId);
        courseAccess.requireCourseStaffAccess(user, UUID.fromString(thread.courseId()));
        return discussions.acceptComment(threadId, commentId);
    }

    private String callerId(CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Authenticated user required");
        }
        return String.valueOf(user.id());
    }

    private void requireStaff(CurrentUser user) {
        callerId(user);
        if (!isStaff(user)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Requires ADMIN or INSTRUCTOR role");
        }
    }

    private boolean isStaff(CurrentUser user) {
        return user != null && user.hasAnyRole("ADMIN", "ORG_ADMIN", "INSTRUCTOR", "PROFESSOR", "TA");
    }

    private boolean isPlatformAdmin(CurrentUser user) {
        return user != null && user.hasPlatformRole("ADMIN");
    }
}
