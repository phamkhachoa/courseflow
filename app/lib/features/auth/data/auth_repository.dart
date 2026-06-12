import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_envelope.dart';
import '../../../core/api/dio_client.dart';
import '../domain/auth_models.dart';

/// Talks to identity-service auth endpoints through the gateway:
///  - `POST /v1/auth/login`   {email, password} -> TokenResponseDto
///  - `POST /v1/auth/refresh` {refreshToken}     -> TokenResponseDto
///  - `POST /v1/auth/logout`
///  - `GET  /v1/users/me`                        -> UserDto
class AuthRepository {
  AuthRepository(this._client);

  final DioClient _client;
  Dio get _dio => _client.dio;

  Future<AuthSession> login({
    required String email,
    required String password,
  }) async {
    try {
      final res = await _dio.post<Object?>(
        '/v1/auth/login',
        data: {'email': email, 'password': password},
        options: Options(extra: {'skipAuth': true}),
      );
      return AuthSession.fromJson(ApiEnvelope.unwrapObject(res.data));
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }

  /// Used by the Dio interceptor on `401`. Carries `skipAuth` so it never
  /// recurses through the refresh logic itself.
  Future<AuthSession> refresh(String refreshToken) async {
    try {
      final res = await _dio.post<Object?>(
        '/v1/auth/refresh',
        data: {'refreshToken': refreshToken},
        options: Options(extra: {'skipAuth': true}),
      );
      return AuthSession.fromJson(ApiEnvelope.unwrapObject(res.data));
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }

  Future<void> logout() async {
    try {
      await _dio.post<Object?>('/v1/auth/logout');
    } on DioException catch (_) {
      // Best-effort: local sign-out proceeds regardless of server reachability.
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
}

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  return AuthRepository(ref.watch(dioClientProvider));
});
