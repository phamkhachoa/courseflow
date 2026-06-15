import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter_appauth/flutter_appauth.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_envelope.dart';
import '../../../core/api/api_exception.dart';
import '../../../core/api/dio_client.dart';
import '../domain/auth_models.dart';
import 'auth_config.dart';

/// Talks to Keycloak with Authorization Code + PKCE via AppAuth, then hydrates
/// display profile data from user-management-service through the gateway.
class AuthRepository {
  AuthRepository(this._client, [FlutterAppAuth? appAuth])
      : _appAuth = appAuth ?? const FlutterAppAuth();

  final DioClient _client;
  final FlutterAppAuth _appAuth;
  Dio get _dio => _client.dio;

  Future<AuthSession> loginWithKeycloak() async {
    try {
      final token = await _appAuth.authorizeAndExchangeCode(
        AuthorizationTokenRequest(
          kKeycloakClientId,
          kKeycloakRedirectUrl,
          issuer: kKeycloakIssuer,
          scopes: kKeycloakScopes,
          promptValues: const ['login'],
          allowInsecureConnections: kKeycloakAllowInsecureConnections,
        ),
      );
      if (token.accessToken == null) {
        throw const ApiException(
          code: 'KEYCLOAK_LOGIN_CANCELLED',
          message: 'Keycloak login was cancelled.',
        );
      }
      return _hydrateProfile(_sessionFromKeycloakToken(
        accessToken: token.accessToken!,
        refreshToken: token.refreshToken ?? '',
        idToken: token.idToken,
        expiresInSeconds: _secondsUntil(token.accessTokenExpirationDateTime),
      ));
    } on ApiException {
      rethrow;
    } catch (e) {
      throw ApiException(
        code: 'KEYCLOAK_LOGIN_FAILED',
        message: e.toString(),
      );
    }
  }

  /// Used by the Dio interceptor on `401`. Carries `skipAuth` so it never
  /// recurses through the refresh logic itself.
  Future<AuthSession> refresh(String refreshToken) async {
    return _refreshKeycloak(refreshToken);
  }

  Future<void> logout({String? idToken}) async {
    if (idToken == null || idToken.isEmpty) return;
    try {
      await _appAuth.endSession(
        EndSessionRequest(
          idTokenHint: idToken,
          postLogoutRedirectUrl: kKeycloakPostLogoutRedirectUrl,
          issuer: kKeycloakIssuer,
          allowInsecureConnections: kKeycloakAllowInsecureConnections,
        ),
      );
    } catch (_) {
      // Best-effort: local sign-out proceeds regardless of IAM reachability.
      return;
    }
  }

  Future<AuthUser> me() async {
    try {
      final res = await _dio.get<Object?>('/v1/users/me');
      return AuthUser.fromJson(ApiEnvelope.unwrapObject(res.data));
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }

  Future<AuthSession> _refreshKeycloak(String refreshToken) async {
    try {
      final token = await _appAuth.token(
        TokenRequest(
          kKeycloakClientId,
          kKeycloakRedirectUrl,
          issuer: kKeycloakIssuer,
          refreshToken: refreshToken,
          scopes: kKeycloakScopes,
          allowInsecureConnections: kKeycloakAllowInsecureConnections,
        ),
      );
      if (token.accessToken == null) {
        throw const ApiException(
          code: 'KEYCLOAK_REFRESH_FAILED',
          message: 'Keycloak did not return an access token.',
        );
      }
      return _hydrateProfile(_sessionFromKeycloakToken(
        accessToken: token.accessToken!,
        refreshToken: token.refreshToken ?? refreshToken,
        idToken: token.idToken,
        expiresInSeconds: _secondsUntil(token.accessTokenExpirationDateTime),
      ));
    } on ApiException {
      rethrow;
    } catch (e) {
      throw ApiException(
        code: 'KEYCLOAK_REFRESH_FAILED',
        message: e.toString(),
      );
    }
  }

  Future<AuthSession> _hydrateProfile(AuthSession session) async {
    try {
      final res = await _dio.get<Object?>(
        '/v1/users/me',
        options: Options(
          headers: {'Authorization': 'Bearer ${session.accessToken}'},
          extra: {'skipAuth': true},
        ),
      );
      final currentUser = AuthUser.fromJson(ApiEnvelope.unwrapObject(res.data));
      return session.copyWith(
        user: session.user.copyWith(
          id: currentUser.id == 0 ? session.user.id : currentUser.id,
          email: currentUser.email.isEmpty ? session.user.email : currentUser.email,
          fullName: currentUser.fullName.isEmpty
              ? session.user.fullName
              : currentUser.fullName,
          role: currentUser.role.isEmpty ? session.user.role : currentUser.role,
          status: currentUser.status.isEmpty ? session.user.status : currentUser.status,
          avatarUrl: currentUser.avatarUrl,
        ),
      );
    } on DioException {
      return session;
    } on ApiException {
      return session;
    }
  }

  AuthSession _sessionFromKeycloakToken({
    required String accessToken,
    required String refreshToken,
    required String? idToken,
    required int expiresInSeconds,
  }) {
    final claims = _decodeJwt(idToken ?? accessToken);
    final email = (claims['email'] ?? claims['preferred_username'] ?? '')
        .toString();
    final nameParts = [claims['given_name'], claims['family_name']]
        .whereType<String>()
        .where((part) => part.isNotEmpty)
        .join(' ');
    final fullName = (claims['name'] ?? (nameParts.isEmpty ? email : nameParts))
        .toString();
    return AuthSession(
      accessToken: accessToken,
      refreshToken: refreshToken,
      idToken: idToken,
      tokenType: 'Bearer',
      expiresInSeconds: expiresInSeconds,
      user: AuthUser(
        id: 0,
        email: email,
        fullName: fullName.isEmpty ? email : fullName,
        role: 'UNRESOLVED',
        status: 'ACTIVE',
      ),
    );
  }

  Map<String, dynamic> _decodeJwt(String token) {
    final parts = token.split('.');
    if (parts.length < 2) return const {};
    try {
      final normalized = base64Url.normalize(parts[1]);
      final decoded = utf8.decode(base64Url.decode(normalized));
      final payload = jsonDecode(decoded);
      return payload is Map<String, dynamic> ? payload : const {};
    } catch (_) {
      return const {};
    }
  }

  int _secondsUntil(DateTime? expiration) {
    if (expiration == null) return 0;
    return expiration
        .difference(DateTime.now())
        .inSeconds
        .clamp(0, 1 << 31)
        .toInt();
  }
}

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  return AuthRepository(ref.watch(dioClientProvider));
});
