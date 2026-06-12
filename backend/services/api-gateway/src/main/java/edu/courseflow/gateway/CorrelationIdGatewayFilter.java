package edu.courseflow.gateway;

import edu.courseflow.commonlibrary.constants.GatewayHeaders;
import java.util.UUID;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

/**
 * Ensures every request entering the platform carries a correlation id so a single trace id can
 * be followed across services and Kafka. Runs before authentication.
 */
@Component
public class CorrelationIdGatewayFilter implements GlobalFilter, Ordered {

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        ServerHttpRequest request = exchange.getRequest();
        String correlationId = request.getHeaders().getFirst(GatewayHeaders.CORRELATION_ID);
        if (correlationId == null || correlationId.isBlank()) {
            correlationId = UUID.randomUUID().toString();
        }
        String finalId = correlationId;
        ServerHttpRequest mutated = request.mutate()
                .header(GatewayHeaders.CORRELATION_ID, finalId)
                .build();
        exchange.getResponse().getHeaders().set(GatewayHeaders.CORRELATION_ID, finalId);
        return chain.filter(exchange.mutate().request(mutated).build());
    }

    @Override
    public int getOrder() {
        return Ordered.HIGHEST_PRECEDENCE;
    }
}
