const String kKeycloakIssuer = String.fromEnvironment(
  'COURSEFLOW_KEYCLOAK_ISSUER',
  defaultValue: 'http://localhost:18080/realms/courseflow',
);

const String kKeycloakClientId = String.fromEnvironment(
  'COURSEFLOW_KEYCLOAK_CLIENT_ID',
  defaultValue: 'courseflow-mobile',
);

const String kKeycloakRedirectUrl = String.fromEnvironment(
  'COURSEFLOW_KEYCLOAK_REDIRECT_URL',
  defaultValue: 'courseflow://auth/callback',
);

const String kKeycloakPostLogoutRedirectUrl = String.fromEnvironment(
  'COURSEFLOW_KEYCLOAK_POST_LOGOUT_REDIRECT_URL',
  defaultValue: 'courseflow://auth/logout',
);

const bool kKeycloakAllowInsecureConnections = bool.fromEnvironment(
  'COURSEFLOW_KEYCLOAK_ALLOW_INSECURE',
  defaultValue: false,
);

const List<String> kKeycloakScopes = ['openid', 'profile', 'email'];
