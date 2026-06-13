package edu.courseflow.gateway;

import java.time.Duration;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.BodyInserters;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

@Component
class HttpInternalTokenConverterClient implements InternalTokenConverterClient {

    static final String TOKEN_EXCHANGE_GRANT = "urn:ietf:params:oauth:grant-type:token-exchange";
    static final String ACCESS_TOKEN_TYPE = "urn:ietf:params:oauth:token-type:access_token";

    private final WebClient webClient;
    private final TokenConverterProperties properties;

    HttpInternalTokenConverterClient(WebClient.Builder webClientBuilder,
            TokenConverterProperties properties) {
        this.webClient = webClientBuilder.baseUrl(properties.uri()).build();
        this.properties = properties;
    }

    @Override
    public boolean enabled() {
        return true;
    }

    @Override
    public boolean required() {
        return properties.mode() == TokenConverterProperties.Mode.REQUIRED;
    }

    @Override
    public Mono<String> exchange(String subjectToken) {
        if (!enabled()) {
            return Mono.empty();
        }
        return webClient.post()
                .uri("/oauth/token")
                .contentType(MediaType.APPLICATION_FORM_URLENCODED)
                .body(BodyInserters.fromFormData("grant_type", TOKEN_EXCHANGE_GRANT)
                        .with("subject_token_type", ACCESS_TOKEN_TYPE)
                        .with("subject_token", subjectToken)
                        .with("audience", properties.audience())
                        .with("client_id", properties.clientId())
                        .with("client_secret", properties.clientSecret()))
                .retrieve()
                .bodyToMono(TokenExchangeResponse.class)
                .map(TokenExchangeResponse::access_token)
                .filter(token -> token != null && !token.isBlank())
                .timeout(Duration.ofMillis(properties.timeoutMs()));
    }

    record TokenExchangeResponse(String access_token, String issued_token_type, String token_type, long expires_in,
            String scope) {
    }
}
