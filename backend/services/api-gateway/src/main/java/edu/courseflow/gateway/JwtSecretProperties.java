package edu.courseflow.gateway;

import io.jsonwebtoken.security.Keys;
import java.nio.charset.StandardCharsets;
import javax.crypto.SecretKey;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * Holds and validates the shared JWT signing secret for the gateway (the edge token authority).
 *
 * <p>The secret is validated <em>fail-fast</em> at startup: the gateway refuses to boot when the
 * secret is missing, blank, shorter than {@value #MIN_SECRET_BYTES} bytes, or still set to the
 * well-known local-development placeholder. This keeps a misconfigured build from verifying tokens
 * with a guessable key. The same secret is shared with identity-service (HS256).
 */
@Component
public class JwtSecretProperties {

    /** HS256 needs a key of at least 256 bits; reject anything weaker. */
    static final int MIN_SECRET_BYTES = 32;

    /** The old hardcoded default. Refuse to start if it is still in use. */
    static final String FORBIDDEN_DEV_SECRET = "local-dev-secret-key-with-at-least-32-bytes";

    private final String secret;

    public JwtSecretProperties(@Value("${courseflow.security.jwt.secret:}") String secret) {
        this.secret = validate(secret);
    }

    static String validate(String secret) {
        if (secret == null || secret.isBlank()) {
            throw new IllegalStateException(
                    "COURSEFLOW_JWT_SECRET is not set. The gateway refuses to start without a JWT signing secret. "
                            + "Provide a random secret of at least " + MIN_SECRET_BYTES + " bytes.");
        }
        if (FORBIDDEN_DEV_SECRET.equals(secret)) {
            throw new IllegalStateException(
                    "COURSEFLOW_JWT_SECRET is still set to the insecure built-in development value. "
                            + "Generate a unique random secret of at least " + MIN_SECRET_BYTES + " bytes.");
        }
        if (secret.getBytes(StandardCharsets.UTF_8).length < MIN_SECRET_BYTES) {
            throw new IllegalStateException(
                    "COURSEFLOW_JWT_SECRET is too short; HS256 requires at least " + MIN_SECRET_BYTES + " bytes.");
        }
        return secret;
    }

    public SecretKey secretKey() {
        return Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
    }
}
