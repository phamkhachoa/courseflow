package edu.courseflow.identity.service;

import edu.courseflow.identity.config.JwtProperties;
import edu.courseflow.identity.model.Role;
import edu.courseflow.identity.model.User;
import edu.courseflow.identity.model.UserRoleAssignment;
import edu.courseflow.identity.repository.UserRoleAssignmentRepository;
import io.jsonwebtoken.Jwts;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import javax.crypto.SecretKey;
import org.springframework.stereotype.Service;

/**
 * Issues short-lived access tokens. The same secret is shared with the gateway,
 * which verifies
 * the token at the edge. Refresh tokens are opaque random strings handled
 * separately so they can
 * be revoked server-side.
 *
 * <p>
 * The access token carries the caller's effective live role assignments as a
 * {@code roles}
 * claim: each entry is {@code {code, rank, isOperator, scopeType, scopeId}}.
 * The gateway and
 * {@code JwtIdentityFilter} use {@code rank} to pick the single primary role
 * and
 * {@code isOperator} to gate {@code /internal} and {@code /backoffice}, so
 * neither side needs a
 * hardcoded role list.
 */
@Service
public class JwtTokenProvider {

    private final SecretKey secretKey;
    private final long accessTtlSeconds;
    private final String issuer;
    private final UserRoleAssignmentRepository assignments;

    public JwtTokenProvider(JwtProperties jwtProperties, UserRoleAssignmentRepository assignments) {
        this.secretKey = jwtProperties.secretKey();
        this.accessTtlSeconds = jwtProperties.getAccessTokenTtlSeconds();
        this.issuer = jwtProperties.getIssuer();
        this.assignments = assignments;
    }

    public String generateAccessToken(User user) {
        Instant now = Instant.now();
        List<Map<String, Object>> roles = loadRoleClaims(user.getId());
        return Jwts.builder()
                .id(UUID.randomUUID().toString()) // jti — lets future revocation/blacklist target a single token
                .issuer(issuer)
                .subject(user.getEmail())
                .claim("uid", user.getId())
                .claim("roles", roles)
                .issuedAt(Date.from(now))
                .expiration(Date.from(now.plusSeconds(accessTtlSeconds)))
                .signWith(secretKey)
                .compact();
    }

    /**
     * Build the {@code roles} claim from active (non-revoked, non-expired)
     * assignments, sorted by
     * rank descending so the gateway can pick the primary role by reading the first
     * element.
     */
    private List<Map<String, Object>> loadRoleClaims(Long userId) {
        List<UserRoleAssignment> active = assignments.findActiveByUserId(userId, Instant.now());
        List<Map<String, Object>> roleClaims = new ArrayList<>(active.size());
        for (UserRoleAssignment assignment : active) {
            Role role = assignment.getRole();
            Map<String, Object> claim = new HashMap<>();
            claim.put("code", role.getCode());
            claim.put("rank", role.getRank());
            claim.put("isOperator", role.isOperator());
            claim.put("scopeType", assignment.getScopeType());
            claim.put("scopeId", assignment.getScopeId());
            roleClaims.add(claim);
        }
        roleClaims.sort(Comparator.<Map<String, Object>, Integer>comparing(
                m -> ((Number) m.get("rank")).intValue()).reversed());
        return roleClaims;
    }

    public long getAccessTtlSeconds() {
        return accessTtlSeconds;
    }
}
