/// Authenticated user used by the mobile shell.
///
/// Initial identity fields come from OIDC token claims; profile and product
/// role fields are hydrated from user-management-service.
class AuthUser {
  const AuthUser({
    required this.id,
    required this.email,
    required this.fullName,
    required this.role,
    required this.status,
    this.avatarUrl,
  });

  final int id;
  final String email;
  final String fullName;
  final String role;
  final String status;
  final String? avatarUrl;

  bool get isAdmin => role == 'ADMIN';
  bool get isProfessor => role == 'PROFESSOR';
  bool get isStudent => role == 'STUDENT';

  factory AuthUser.fromJson(Map<String, dynamic> json) => AuthUser(
    id: (json['id'] as num).toInt(),
    email: json['email'] as String? ?? '',
    fullName: json['fullName'] as String? ?? '',
    avatarUrl: json['avatarUrl'] as String?,
    role: json['role'] as String? ?? 'STUDENT',
    status: json['status'] as String? ?? 'ACTIVE',
  );

  AuthUser copyWith({
    int? id,
    String? email,
    String? fullName,
    String? role,
    String? status,
    String? avatarUrl,
  }) =>
      AuthUser(
        id: id ?? this.id,
        email: email ?? this.email,
        fullName: fullName ?? this.fullName,
        role: role ?? this.role,
        status: status ?? this.status,
        avatarUrl: avatarUrl ?? this.avatarUrl,
      );
}

/// Token pair + metadata built from AppAuth's Keycloak token response.
class AuthSession {
  const AuthSession({
    required this.accessToken,
    required this.refreshToken,
    required this.tokenType,
    required this.expiresInSeconds,
    required this.user,
    this.idToken,
  });

  final String accessToken;
  final String refreshToken;
  final String? idToken;
  final String tokenType;
  final int expiresInSeconds;
  final AuthUser user;

  factory AuthSession.fromJson(Map<String, dynamic> json) => AuthSession(
    accessToken: json['accessToken'] as String? ?? '',
    refreshToken: json['refreshToken'] as String? ?? '',
    idToken: json['idToken'] as String?,
    tokenType: json['tokenType'] as String? ?? 'Bearer',
    expiresInSeconds: (json['expiresInSeconds'] as num?)?.toInt() ?? 0,
    user: AuthUser.fromJson(json['user'] as Map<String, dynamic>),
  );

  AuthSession copyWith({
    String? accessToken,
    String? refreshToken,
    String? idToken,
    String? tokenType,
    int? expiresInSeconds,
    AuthUser? user,
  }) =>
      AuthSession(
        accessToken: accessToken ?? this.accessToken,
        refreshToken: refreshToken ?? this.refreshToken,
        idToken: idToken ?? this.idToken,
        tokenType: tokenType ?? this.tokenType,
        expiresInSeconds: expiresInSeconds ?? this.expiresInSeconds,
        user: user ?? this.user,
      );
}

class UserProfile {
  const UserProfile({
    required this.userId,
    required this.displayName,
    this.avatarUrl,
  });

  final int userId;
  final String displayName;
  final String? avatarUrl;

  factory UserProfile.fromJson(Map<String, dynamic> json) => UserProfile(
        userId: int.tryParse(json['userId']?.toString() ?? '') ?? 0,
        displayName: json['displayName'] as String? ?? '',
        avatarUrl: json['avatarUrl'] as String?,
      );
}
