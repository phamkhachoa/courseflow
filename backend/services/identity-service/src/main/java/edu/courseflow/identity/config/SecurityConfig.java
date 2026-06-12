package edu.courseflow.identity.config;

import edu.courseflow.identity.service.AccessTokenRevocationService;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

/**
 * Identity service sits behind the gateway, but it does <em>not</em> trust the forwarded
 * {@code X-User-*} headers blindly. {@link JwtIdentityFilter} re-verifies the signed JWT with the
 * shared secret on every protected request, so a caller that reaches the service directly (bypassing
 * the gateway's network isolation) cannot forge an identity or escalate to ADMIN.
 *
 * <ul>
 *   <li>Public endpoints (login/refresh, health) need no token.</li>
 *   <li>Every other endpoint requires a valid Bearer token; verified claims replace any client headers.</li>
 *   <li>{@code /internal/**} and {@code /backoffice/**} require an operator role; role/permission
 *       mutations and role assignments additionally require ADMIN.</li>
 * </ul>
 */
@Configuration
public class SecurityConfig {

    @Bean
    SecurityFilterChain securityFilterChain(HttpSecurity http,
            JwtProperties jwtProperties,
            AccessTokenRevocationService accessTokenRevocationService) throws Exception {
        return http
                .csrf(AbstractHttpConfigurer::disable)
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                // Authorization is enforced by JwtIdentityFilter below (verifies the signed token),
                // so the Spring authorize chain just lets requests through to it.
                .authorizeHttpRequests(auth -> auth.anyRequest().permitAll())
                .addFilterBefore(new JwtIdentityFilter(jwtProperties, accessTokenRevocationService),
                        UsernamePasswordAuthenticationFilter.class)
                .build();
    }

    @Bean
    PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder(12);
    }
}
