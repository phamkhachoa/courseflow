package edu.courseflow.identity.controller;

import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.identity.config.JwtIdentityFilter;
import edu.courseflow.identity.dto.ChangePasswordRequestDto;
import edu.courseflow.identity.service.AuthService;
import edu.courseflow.identity.dto.LoginRequestDto;
import edu.courseflow.identity.dto.RefreshRequestDto;
import edu.courseflow.identity.dto.RegisterRequestDto;
import edu.courseflow.identity.dto.TokenResponseDto;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import java.time.Instant;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/auth")
public class AuthController {

    private final AuthService authService;

    public AuthController(AuthService authService) {
        this.authService = authService;
    }

    @PostMapping("/login")
    public ResponseEntity<TokenResponseDto> login(@Valid @RequestBody LoginRequestDto request) {
        return ResponseEntity.ok(authService.login(request));
    }

    @PostMapping("/register")
    public ResponseEntity<TokenResponseDto> register(@Valid @RequestBody RegisterRequestDto request) {
        return ResponseEntity.ok(authService.register(request));
    }

    @PostMapping("/refresh")
    public ResponseEntity<TokenResponseDto> refresh(@Valid @RequestBody RefreshRequestDto request) {
        return ResponseEntity.ok(authService.refresh(request.refreshToken()));
    }

    @PostMapping("/password/change")
    public ResponseEntity<Void> changePassword(@Valid @RequestBody ChangePasswordRequestDto request) {
        authService.changePassword(request);
        return ResponseEntity.noContent().build();
    }

    @PostMapping("/logout")
    public ResponseEntity<Void> logout(CurrentUser currentUser, HttpServletRequest request) {
        if (currentUser.id() != null) {
            authService.logout(currentUser.id(),
                    (String) request.getAttribute(JwtIdentityFilter.ACCESS_TOKEN_JTI_ATTRIBUTE),
                    (Instant) request.getAttribute(JwtIdentityFilter.ACCESS_TOKEN_EXPIRES_AT_ATTRIBUTE));
        }
        return ResponseEntity.noContent().build();
    }
}
