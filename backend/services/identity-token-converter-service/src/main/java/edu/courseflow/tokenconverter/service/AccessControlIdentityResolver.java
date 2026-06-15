package edu.courseflow.tokenconverter.service;

public interface AccessControlIdentityResolver {

    ResolvedIdentity resolve(ExternalTokenClaims externalClaims);
}
