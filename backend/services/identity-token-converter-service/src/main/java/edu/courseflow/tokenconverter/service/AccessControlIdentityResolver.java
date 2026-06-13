package edu.courseflow.tokenconverter.service;

public interface AccessControlIdentityResolver {

    ResolvedIdentity resolve(ExternalTokenClaims externalClaims);

    static AccessControlIdentityResolver legacyClaims() {
        return LegacyClaimsIdentityResolver.INSTANCE;
    }
}
