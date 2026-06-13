package edu.courseflow.tokenconverter.controller;

import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import edu.courseflow.tokenconverter.dto.TokenExchangeResponse;
import edu.courseflow.tokenconverter.service.TokenExchangeService;
import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

class TokenExchangeControllerTest {

    private final TokenExchangeService service = org.mockito.Mockito.mock(TokenExchangeService.class);
    private final MockMvc mvc = MockMvcBuilders.standaloneSetup(new TokenExchangeController(service)).build();

    @Test
    void acceptsTokenExchangeWithoutLegacyServiceToken() throws Exception {
        when(service.exchange(
                eq(TokenExchangeService.TOKEN_EXCHANGE_GRANT),
                eq(TokenExchangeService.ACCESS_TOKEN_TYPE),
                eq("external"),
                eq("courseflow-services"),
                eq("course:read")))
                .thenReturn(new TokenExchangeResponse(
                        "internal",
                        TokenExchangeService.ACCESS_TOKEN_TYPE,
                        "Bearer",
                        180,
                        "course:read"));

        mvc.perform(post("/oauth/token")
                        .contentType("application/x-www-form-urlencoded")
                        .param("grant_type", TokenExchangeService.TOKEN_EXCHANGE_GRANT)
                        .param("subject_token", "external")
                        .param("subject_token_type", TokenExchangeService.ACCESS_TOKEN_TYPE)
                        .param("audience", "courseflow-services")
                        .param("scope", "course:read"))
                .andExpect(status().isOk());

        verify(service).exchange(
                TokenExchangeService.TOKEN_EXCHANGE_GRANT,
                TokenExchangeService.ACCESS_TOKEN_TYPE,
                "external",
                "courseflow-services",
                "course:read");
    }
}
