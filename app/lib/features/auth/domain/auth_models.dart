/// Authenticated user. Mirrors identity-service `UserDto`
/// (id, email, fullName, role, status).
class AuthUser {
  const AuthUser({
    required this.id,
    required this.email,
    required this.fullName,
    required this.role,
    required this.status,
  });

  final int id;
  final String email;
  final String fullName;
  final String role;
  final String status;

  bool get isAdmin => role == 'ADMIN';
  bool get isProfessor => role == 'PROFESSOR';
  bool get isStudent => role == 'STUDENT';

  factory AuthUser.fromJson(Map<String, dynamic> json) => AuthUser(
    id: (json['id'] as num).toInt(),
    email: json['email'] as String? ?? '',
    fullName: json['fullName'] as String? ?? '',
    role: json['role'] as String? ?? 'STUDENT',
    status: json['status'] as String? ?? 'ACTIVE',
  );
}

/// Token pair + metadata returned by `POST /v1/auth/login` and `/v1/auth/refresh`.
/// Mirrors identity-service `TokenResponseDto`.
class AuthSession {
  const AuthSession({
    required this.accessToken,
    required this.refreshToken,
    required this.tokenType,
    required this.expiresInSeconds,
    required this.user,
  });

  final String accessToken;
  final String refreshToken;
  final String tokenType;
  final int expiresInSeconds;
  final AuthUser user;

  factory AuthSession.fromJson(Map<String, dynamic> json) => AuthSession(
    accessToken: json['accessToken'] as String? ?? '',
    refreshToken: json['refreshToken'] as String? ?? '',
    tokenType: json['tokenType'] as String? ?? 'Bearer',
    expiresInSeconds: (json['expiresInSeconds'] as num?)?.toInt() ?? 0,
    user: AuthUser.fromJson(json['user'] as Map<String, dynamic>),
  );
}
