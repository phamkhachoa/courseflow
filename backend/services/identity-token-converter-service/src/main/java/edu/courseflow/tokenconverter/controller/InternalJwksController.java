package edu.courseflow.tokenconverter.controller;

import edu.courseflow.tokenconverter.config.TokenConverterProperties;
import edu.courseflow.tokenconverter.service.TokenConverterMetrics;
import java.math.BigInteger;
import java.security.interfaces.RSAPublicKey;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
public class InternalJwksController {

    private final TokenConverterProperties properties;
    private final TokenConverterMetrics metrics;

    public InternalJwksController(TokenConverterProperties properties) {
        this(properties, TokenConverterMetrics.noop());
    }

    @Autowired
    public InternalJwksController(TokenConverterProperties properties, TokenConverterMetrics metrics) {
        this.properties = properties;
        this.metrics = metrics;
    }

    @GetMapping({"/oauth/jwks", "/.well-known/jwks.json"})
    public Map<String, Object> jwks() {
        try {
            if (!properties.internalJwtRs256()) {
                throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Internal JWKS is available only for RS256");
            }
            if (!(properties.internalJwtPublicKey() instanceof RSAPublicKey rsa)) {
                throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "Internal JWT key is not RSA");
            }
            metrics.jwks("success");
            return Map.of("keys", List.of(Map.of(
                    "kty", "RSA",
                    "use", "sig",
                    "alg", "RS256",
                    "kid", properties.internalJwtKeyId(),
                    "n", encode(rsa.getModulus()),
                    "e", encode(rsa.getPublicExponent()))));
        } catch (RuntimeException ex) {
            metrics.jwks("failure");
            throw ex;
        }
    }

    private String encode(BigInteger value) {
        byte[] bytes = value.toByteArray();
        if (bytes.length > 1 && bytes[0] == 0) {
            bytes = java.util.Arrays.copyOfRange(bytes, 1, bytes.length);
        }
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }
}
