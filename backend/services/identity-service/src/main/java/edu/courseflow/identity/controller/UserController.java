package edu.courseflow.identity.controller;

import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.identity.dto.CreateUserRequestDto;
import edu.courseflow.identity.dto.ResetPasswordRequestDto;
import edu.courseflow.identity.dto.UserDto;
import edu.courseflow.identity.service.UserService;
import jakarta.validation.Valid;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.util.UriComponentsBuilder;

/**
 * Admin-facing user management. Routes are exposed under {@code /backoffice} so
 * the gateway can
 * require operator role for the whole prefix.
 */
@RestController
@RequestMapping("/backoffice/users")
public class UserController {

    private final UserService userService;

    public UserController(UserService userService) {
        this.userService = userService;
    }

    @GetMapping
    public Page<UserDto> list(Pageable pageable) {
        return userService.list(pageable);
    }

    @GetMapping("/{id}")
    public ResponseEntity<UserDto> getById(@PathVariable Long id) {
        return ResponseEntity.ok(userService.getById(id));
    }

    @PostMapping
    public ResponseEntity<UserDto> create(@Valid @RequestBody CreateUserRequestDto request,
            UriComponentsBuilder uriBuilder,
            CurrentUser caller) {
        UserDto created = userService.create(request, caller);
        return ResponseEntity
                .created(uriBuilder.replacePath("/backoffice/users/{id}").buildAndExpand(created.id()).toUri())
                .body(created);
    }

    @PutMapping("/{id}/password")
    public ResponseEntity<Void> resetPassword(@PathVariable Long id,
            @Valid @RequestBody ResetPasswordRequestDto request,
            CurrentUser caller) {
        userService.resetPassword(id, request, caller);
        return ResponseEntity.noContent().build();
    }

    @PutMapping("/{id}/email-verification")
    public ResponseEntity<UserDto> verifyEmail(@PathVariable Long id, CurrentUser caller) {
        return ResponseEntity.ok(userService.markEmailVerified(id, caller));
    }
}
