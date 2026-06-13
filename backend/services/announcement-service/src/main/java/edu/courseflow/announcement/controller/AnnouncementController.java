package edu.courseflow.announcement.controller;

import edu.courseflow.announcement.dto.AnnouncementDtos.AnnouncementDto;
import edu.courseflow.announcement.dto.AnnouncementDtos.CreateAnnouncementRequestDto;
import edu.courseflow.announcement.service.AnnouncementService;
import edu.courseflow.commonlibrary.security.CourseAccessClient;
import edu.courseflow.commonlibrary.web.CurrentUser;
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
public class AnnouncementController {

    private final AnnouncementService announcements;
    private final CourseAccessClient courseAccess;

    public AnnouncementController(AnnouncementService announcements, CourseAccessClient courseAccess) {
        this.announcements = announcements;
        this.courseAccess = courseAccess;
    }

    @GetMapping("/internal/announcements")
    public List<AnnouncementDto> list(@RequestParam Optional<UUID> courseId,
                                      @RequestParam Optional<String> status,
                                      CurrentUser user) {
        callerId(user);
        if (isStaff(user)) {
            if (courseId.isPresent()) {
                courseAccess.requireCourseStaffAccess(user, courseId.get());
            } else {
                requirePlatformAdmin(user);
            }
        } else {
            UUID requiredCourseId = courseId.orElseThrow(() ->
                    new ResponseStatusException(HttpStatus.FORBIDDEN, "courseId is required for learner access"));
            courseAccess.requireCourseAccess(user, requiredCourseId);
        }
        Optional<String> effectiveStatus = isStaff(user) ? status : Optional.of("PUBLISHED");
        return announcements.list(courseId, effectiveStatus);
    }

    @PostMapping("/internal/announcements")
    public AnnouncementDto create(@Valid @RequestBody CreateAnnouncementRequestDto request, CurrentUser user) {
        requireStaff(user);
        courseAccess.requireCourseStaffAccess(user, UUID.fromString(request.courseId()));
        CreateAnnouncementRequestDto trusted = new CreateAnnouncementRequestDto(
                request.courseId(),
                callerId(user),
                request.title(),
                request.body(),
                request.audience(),
                request.publishAt());
        return announcements.create(trusted);
    }

    @GetMapping("/internal/announcements/{announcementId}")
    public AnnouncementDto get(@PathVariable UUID announcementId, CurrentUser user) {
        callerId(user);
        AnnouncementDto announcement = announcements.get(announcementId);
        UUID courseId = UUID.fromString(announcement.courseId());
        if (isStaff(user)) {
            courseAccess.requireCourseStaffAccess(user, courseId);
        } else {
            courseAccess.requireCourseAccess(user, courseId);
            if (!"PUBLISHED".equalsIgnoreCase(announcement.status())) {
                throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Announcement not found: " + announcementId);
            }
        }
        return announcement;
    }

    @PostMapping("/internal/announcements/{announcementId}/publish")
    public AnnouncementDto publish(@PathVariable UUID announcementId, CurrentUser user) {
        requireStaff(user);
        AnnouncementDto announcement = announcements.get(announcementId);
        courseAccess.requireCourseStaffAccess(user, UUID.fromString(announcement.courseId()));
        return announcements.publish(announcementId);
    }

    private String callerId(CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Authentication required");
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
        return user != null && user.hasAnyRole("ADMIN", "ORG_ADMIN", "TA", "INSTRUCTOR", "PROFESSOR");
    }

    private void requirePlatformAdmin(CurrentUser user) {
        callerId(user);
        if (!user.hasRole("ADMIN")) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "courseId is required for course staff access");
        }
    }
}
