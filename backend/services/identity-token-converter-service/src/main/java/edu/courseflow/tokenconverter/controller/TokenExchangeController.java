package edu.courseflow.tokenconverter.controller;

import edu.courseflow.tokenconverter.dto.TokenExchangeResponse;
import edu.courseflow.tokenconverter.service.TokenExchangeService;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class TokenExchangeController {

    private final TokenExchangeService tokenExchangeService;

    public TokenExchangeController(TokenExchangeService tokenExchangeService) {
        this.tokenExchangeService = tokenExchangeService;
    }

    @PostMapping(value = "/oauth/token", consumes = MediaType.APPLICATION_FORM_URLENCODED_VALUE)
    public TokenExchangeResponse exchange(
            @RequestParam("grant_type") String grantType,
            @RequestParam(value = "subject_token_type", required = false) String subjectTokenType,
            @RequestParam(value = "subject_token", required = false) String subjectToken,
            @RequestParam(value = "audience", required = false) String audience,
            @RequestParam(value = "scope", required = false) String scope,
            @RequestParam(value = "client_id", required = false) String clientId,
            @RequestParam(value = "client_secret", required = false) String clientSecret,
            @RequestParam(value = "user_id", required = false) String userId,
            @RequestParam(value = "email", required = false) String email,
            @RequestParam(value = "roles", required = false) String roles,
            @RequestParam(value = "role_assignments", required = false) String roleAssignments,
            @RequestParam(value = "actor_token", required = false) String actorToken) {
        return tokenExchangeService.exchange(grantType, subjectTokenType, subjectToken, audience, scope,
                clientId, clientSecret, userId, email, roles, roleAssignments, actorToken);
    }
}
