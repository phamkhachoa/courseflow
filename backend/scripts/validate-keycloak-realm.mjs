#!/usr/bin/env node

import fs from "node:fs";

const args = process.argv.slice(2);
const realmPath = args.find((arg) => !arg.startsWith("--"));
const prodTemplate = args.includes("--prod-template");

if (!realmPath) {
  console.error("Usage: scripts/validate-keycloak-realm.mjs <realm.json> [--prod-template]");
  process.exit(2);
}

const violations = [];
const realm = JSON.parse(fs.readFileSync(realmPath, "utf8"));

function requireValue(condition, message) {
  if (!condition) {
    violations.push(message);
  }
}

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function client(clientId) {
  return asArray(realm.clients).find((item) => item?.clientId === clientId);
}

function scope(name) {
  return asArray(realm.clientScopes).find((item) => item?.name === name);
}

function containsLocalhost(value) {
  return /(^|[/:.])localhost([/:]|$)|127\.0\.0\.1|\[::1\]/i.test(String(value ?? ""));
}

function validateBaseRealm() {
  requireValue(realm.realm === "courseflow", "realm must be courseflow");
  requireValue(realm.enabled === true, "realm must be enabled");
  requireValue(["external", "all"].includes(realm.sslRequired), "sslRequired must be external or all");
  requireValue(realm.registrationAllowed === false, "self-registration must be disabled");
  requireValue(realm.duplicateEmailsAllowed === false, "duplicate emails must be disabled");
  requireValue(realm.editUsernameAllowed === false, "username editing must be disabled");
  requireValue(realm.resetPasswordAllowed === true, "reset password must be enabled through Keycloak");
  requireValue(realm.bruteForceProtected === true, "brute force protection must be enabled");
}

function validatePolicies() {
  const passwordPolicy = String(realm.passwordPolicy ?? "");
  for (const required of ["length(12)", "digits(1)", "lowerCase(1)", "upperCase(1)", "specialChars(1)", "passwordHistory(5)"]) {
    requireValue(passwordPolicy.includes(required), `passwordPolicy must include ${required}`);
  }
  requireValue(realm.otpPolicyType === "totp", "OTP policy must use TOTP");
  requireValue(Number(realm.otpPolicyDigits) >= 6, "OTP policy must use at least 6 digits");
  requireValue(Number(realm.otpPolicyPeriod) <= 30, "OTP period must be 30 seconds or lower");

  for (const [name, min] of [
    ["ssoSessionIdleTimeout", 900],
    ["ssoSessionMaxLifespan", 3600],
    ["clientSessionIdleTimeout", 900],
    ["clientSessionMaxLifespan", 3600],
    ["offlineSessionIdleTimeout", 86400]
  ]) {
    requireValue(Number(realm[name]) >= min, `${name} must be configured`);
  }

  const requiredActions = new Set(asArray(realm.requiredActions)
    .filter((action) => action?.enabled !== false)
    .map((action) => action.alias));
  requireValue(requiredActions.has("VERIFY_EMAIL"), "VERIFY_EMAIL required action must be enabled");
  requireValue(requiredActions.has("UPDATE_PASSWORD"), "UPDATE_PASSWORD required action must be enabled");
  requireValue(requiredActions.has("CONFIGURE_TOTP"), "CONFIGURE_TOTP required action must be enabled");
}

function validateAudienceScope() {
  const basicScope = scope("basic");
  requireValue(Boolean(basicScope), "basic client scope is required");
  const basicMappers = asArray(basicScope?.protocolMappers);
  const subjectMapper = basicMappers.find((mapper) => mapper.protocolMapper === "oidc-sub-mapper");
  requireValue(subjectMapper?.config?.["access.token.claim"] === "true",
    "basic client scope must emit sub in access tokens");

  const profileScope = scope("profile");
  requireValue(Boolean(profileScope), "profile client scope is required");
  const profileMappers = asArray(profileScope?.protocolMappers);
  const usernameMapper = profileMappers.find((mapper) => mapper?.config?.["claim.name"] === "preferred_username");
  requireValue(usernameMapper?.config?.["access.token.claim"] === "true",
    "profile client scope must emit preferred_username in access tokens");

  const emailScope = scope("email");
  requireValue(Boolean(emailScope), "email client scope is required");
  const emailMappers = asArray(emailScope?.protocolMappers);
  const emailMapper = emailMappers.find((mapper) => mapper?.config?.["claim.name"] === "email");
  requireValue(emailMapper?.config?.["access.token.claim"] === "true",
    "email client scope must emit email in access tokens");

  const audienceScope = scope("courseflow-api-audience");
  requireValue(Boolean(audienceScope), "courseflow-api-audience client scope is required");
  const mappers = asArray(audienceScope?.protocolMappers);
  const audienceMapper = mappers.find((mapper) => mapper.protocolMapper === "oidc-audience-mapper");
  requireValue(audienceMapper?.config?.["included.client.audience"] === "courseflow-api",
    "courseflow-api-audience must map the courseflow-api audience");
  requireValue(audienceMapper?.config?.["access.token.claim"] === "true",
    "courseflow-api audience must be in access tokens");
  requireValue(audienceMapper?.config?.["id.token.claim"] !== "true",
    "courseflow-api audience must not be added to ID tokens");
  const productIdentityMapper = mappers.find((mapper) =>
    mapper?.config?.["claim.name"] === "courseflow_user_id"
      || mapper?.config?.["user.attribute"] === "courseflow_user_id");
  requireValue(!productIdentityMapper,
    "Keycloak access/ID tokens must not emit CourseFlow product identity claim courseflow_user_id");
}

function validatePublicPkceClient(clientId) {
  const item = client(clientId);
  requireValue(Boolean(item), `${clientId} client is required`);
  if (!item) return;
  requireValue(item.publicClient === true, `${clientId} must be a public client`);
  requireValue(item.standardFlowEnabled === true, `${clientId} must use Authorization Code flow`);
  requireValue(item.implicitFlowEnabled === false, `${clientId} must disable implicit flow`);
  requireValue(item.directAccessGrantsEnabled === false, `${clientId} must disable password/direct grant`);
  requireValue(item.serviceAccountsEnabled === false, `${clientId} must not use service accounts`);
  requireValue(item.attributes?.["pkce.code.challenge.method"] === "S256", `${clientId} must require PKCE S256`);
  const scopes = new Set(asArray(item.defaultClientScopes));
  for (const required of ["basic", "profile", "email", "courseflow-api-audience"]) {
    requireValue(scopes.has(required), `${clientId} must include ${required} default scope`);
  }
  requireValue(!scopes.has("roles"), `${clientId} must not include Keycloak roles default scope`);
  if (prodTemplate) {
    for (const raw of [...asArray(item.redirectUris), ...asArray(item.webOrigins), item.attributes?.["post.logout.redirect.uris"]]) {
      requireValue(!containsLocalhost(raw), `${clientId} must not use localhost redirect/web origin in prod template`);
    }
  }
}

function validateInternalClients() {
  const api = client("courseflow-api");
  requireValue(Boolean(api), "courseflow-api client is required");
  if (api) {
    requireValue(api.publicClient === false, "courseflow-api must be confidential/internal");
    requireValue(api.standardFlowEnabled === false, "courseflow-api must not start login flows");
    requireValue(api.directAccessGrantsEnabled === false, "courseflow-api must disable direct grants");
    requireValue(api.serviceAccountsEnabled === false, "courseflow-api must not use service accounts");
  }

  const lifecycle = client("keycloak-user-lifecycle");
  requireValue(Boolean(lifecycle), "keycloak-user-lifecycle client is required");
  if (lifecycle) {
    requireValue(lifecycle.publicClient === false, "keycloak-user-lifecycle must be confidential");
    requireValue(lifecycle.serviceAccountsEnabled === true, "keycloak-user-lifecycle must use service account");
    requireValue(lifecycle.directAccessGrantsEnabled === false, "keycloak-user-lifecycle must disable direct grants");
    if (prodTemplate) {
      requireValue(lifecycle.secret === "__REPLACE_WITH_GENERATED_LIFECYCLE_CLIENT_SECRET__",
        "prod template must keep a generated-secret placeholder, not a real/default secret");
    }
  }
}

function validateProdUsers() {
  if (!prodTemplate) return;
  const realmRoles = asArray(realm.roles?.realm).map((role) => String(role?.name ?? ""));
  for (const productRole of ["ADMIN", "ORG_ADMIN", "INSTRUCTOR", "PROFESSOR", "TA", "STUDENT", "LEARNER"]) {
    requireValue(!realmRoles.includes(productRole),
      `prod template must not define CourseFlow product role ${productRole} in Keycloak`);
  }
  for (const user of asArray(realm.users)) {
    const username = String(user?.username ?? "");
    const serviceAccount = username.startsWith("service-account-");
    requireValue(serviceAccount, `prod template must not contain demo/user account ${username || "<missing>"}`);
    requireValue(!asArray(user?.credentials).length, `prod template user ${username} must not contain credentials`);
  }
}

validateBaseRealm();
if (prodTemplate) {
  validatePolicies();
}
validateAudienceScope();
validateInternalClients();
validatePublicPkceClient("courseflow-learner-web");
validatePublicPkceClient("courseflow-admin-web");
validatePublicPkceClient("courseflow-mobile");
validateProdUsers();

if (violations.length > 0) {
  console.error(`Keycloak realm validation failed for ${realmPath}:`);
  for (const violation of violations) {
    console.error(`  - ${violation}`);
  }
  process.exit(1);
}

console.log(`Keycloak realm validation passed: ${realmPath}`);
