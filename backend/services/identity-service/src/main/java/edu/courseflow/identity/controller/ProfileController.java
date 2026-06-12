package edu.courseflow.identity.controller;

import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.identity.dto.UserDto;
import edu.courseflow.identity.service.UserService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/** User-facing identity endpoints. Admin user management stays under /backoffice. */
@RestController
public class ProfileController {

    private final UserService userService;

    public ProfileController(UserService userService) {
        this.userService = userService;
    }

    @GetMapping("/users/me")
    public ResponseEntity<UserDto> me(CurrentUser currentUser) {
        return ResponseEntity.ok(userService.getById(currentUser.id()));
    }
}
