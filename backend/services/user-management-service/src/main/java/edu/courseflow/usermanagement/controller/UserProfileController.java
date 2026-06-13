package edu.courseflow.usermanagement.controller;

import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.usermanagement.dto.UserProfileDtos.AdminUserPrivacyExportDto;
import edu.courseflow.usermanagement.dto.UserProfileDtos.AdminUserDto;
import edu.courseflow.usermanagement.dto.UserProfileDtos.CreateAdminUserRequest;
import edu.courseflow.usermanagement.dto.UserProfileDtos.CurrentUserDto;
import edu.courseflow.usermanagement.dto.UserProfileDtos.DeactivateAdminUserRequest;
import edu.courseflow.usermanagement.dto.UserProfileDtos.ProfileSummaryBatchRequest;
import edu.courseflow.usermanagement.dto.UserProfileDtos.ProfileSummaryDto;
import edu.courseflow.usermanagement.dto.UserProfileDtos.ProvisionUserProfileRequest;
import edu.courseflow.usermanagement.dto.UserProfileDtos.UpdateMyProfileRequest;
import edu.courseflow.usermanagement.dto.UserProfileDtos.UserDirectoryItemDto;
import edu.courseflow.usermanagement.dto.UserProfileDtos.UserProfileDto;
import edu.courseflow.usermanagement.service.UserProfileService;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.util.UriComponentsBuilder;
import org.springframework.http.ResponseEntity;

@RestController
public class UserProfileController {

    private final UserProfileService profiles;

    public UserProfileController(UserProfileService profiles) {
        this.profiles = profiles;
    }

    @GetMapping("/internal/users/me/profile")
    public UserProfileDto me(CurrentUser user) {
        return profiles.me(user);
    }

    @GetMapping("/internal/users/me")
    public CurrentUserDto currentUser(CurrentUser user) {
        return profiles.currentUser(user);
    }

    @PutMapping("/internal/users/me/profile")
    public UserProfileDto updateMe(CurrentUser user, @Valid @RequestBody UpdateMyProfileRequest request) {
        return profiles.updateMe(user, request);
    }

    @PostMapping("/internal/users/provision-profile")
    public UserProfileDto provisionProfile(CurrentUser caller,
            @Valid @RequestBody ProvisionUserProfileRequest request) {
        return profiles.provisionProfile(caller, request);
    }

    @GetMapping("/internal/profiles/{userId}")
    public UserProfileDto internalProfile(@PathVariable Long userId) {
        return profiles.profile(userId);
    }

    @PostMapping("/internal/profiles/summary:batch")
    public List<ProfileSummaryDto> summaries(@Valid @RequestBody ProfileSummaryBatchRequest request) {
        return profiles.summaries(request.userIds());
    }

    @GetMapping("/public/profiles/{userId}")
    public UserProfileDto publicProfile(@PathVariable Long userId) {
        return profiles.publicProfile(userId);
    }

    @GetMapping("/backoffice/users")
    public List<UserDirectoryItemDto> directory(
            CurrentUser caller,
            @RequestParam(name = "q", required = false) String query,
            @RequestParam(name = "limit", defaultValue = "50") int limit) {
        return profiles.directory(caller, query, limit);
    }

    @GetMapping("/backoffice/admin-users")
    public List<AdminUserDto> adminDirectory(
            CurrentUser caller,
            @RequestParam(name = "q", required = false) String query,
            @RequestParam(name = "limit", defaultValue = "100") int limit) {
        return profiles.adminDirectory(caller, query, limit);
    }

    @GetMapping("/backoffice/admin-users/{userId}")
    public AdminUserDto adminUser(CurrentUser caller, @PathVariable Long userId) {
        return profiles.adminUser(caller, userId);
    }

    @PostMapping("/backoffice/admin-users")
    public ResponseEntity<AdminUserDto> createAdminUser(CurrentUser caller,
            @Valid @RequestBody CreateAdminUserRequest request,
            UriComponentsBuilder uriBuilder) {
        AdminUserDto created = profiles.createAdminUser(caller, request);
        return ResponseEntity
                .created(uriBuilder.replacePath("/backoffice/admin-users/{id}").buildAndExpand(created.id()).toUri())
                .body(created);
    }

    @GetMapping("/backoffice/admin-users/{userId}/privacy-export")
    public AdminUserPrivacyExportDto exportAdminUserPrivacy(CurrentUser caller, @PathVariable Long userId) {
        return profiles.exportAdminUserPrivacy(caller, userId);
    }

    @PostMapping("/backoffice/admin-users/{userId}/deactivate")
    public AdminUserDto deactivateAdminUser(CurrentUser caller,
            @PathVariable Long userId,
            @Valid @RequestBody DeactivateAdminUserRequest request) {
        return profiles.deactivateAdminUser(caller, userId, request);
    }
}
