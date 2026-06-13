package edu.courseflow.gateway;

import reactor.core.publisher.Mono;

public interface GatewayExternalTokenVerifier {
    Mono<Void> verify(String token);
}
