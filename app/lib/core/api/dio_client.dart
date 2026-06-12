import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../storage/token_storage.dart';

/// Base URL for the API gateway. All traffic (public + BFF + internal) is
/// routed through `/api` on the gateway per `backend/docs/api/courseflow-api.md`.
const String kDefaultBaseUrl = String.fromEnvironment(
  'COURSEFLOW_API_URL',
  defaultValue: 'http://localhost:8080/api',
);

/// Signature the auth layer registers so the client can perform a token
/// refresh on a `401`. Returns the new access token, or null if refresh failed
/// (e.g. refresh token also expired -> caller should force logout).
typedef TokenRefresher = Future<String?> Function();

/// Callback invoked when the session is irrecoverably lost (refresh failed).
typedef SessionExpiredCallback = void Function();

/// Wraps a configured [Dio] instance with:
///  - bearer-token injection from [TokenStorage]
///  - automatic single-flight refresh + retry on `401`
///
/// Error -> [ApiException] mapping happens in the repositories via
/// `ApiEnvelope.toApiException`, keeping this class focused on transport.
class DioClient {
  DioClient({required TokenStorage tokenStorage, String? baseUrl})
    : _tokenStorage = tokenStorage,
      dio = Dio(
        BaseOptions(
          baseUrl: baseUrl ?? kDefaultBaseUrl,
          connectTimeout: const Duration(seconds: 10),
          receiveTimeout: const Duration(seconds: 20),
          contentType: 'application/json',
        ),
      ) {
    dio.interceptors.add(
      InterceptorsWrapper(onRequest: _onRequest, onError: _onError),
    );
  }

  final Dio dio;
  final TokenStorage _tokenStorage;

  TokenRefresher? _refresher;
  SessionExpiredCallback? _onSessionExpired;

  /// Single-flight guard: concurrent 401s share one refresh future.
  Future<String?>? _inFlightRefresh;

  void configureAuth({
    required TokenRefresher refresher,
    required SessionExpiredCallback onSessionExpired,
  }) {
    _refresher = refresher;
    _onSessionExpired = onSessionExpired;
  }

  Future<void> _onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    // Public endpoints don't need (and shouldn't carry) a token.
    if (options.extra['skipAuth'] != true) {
      final token = await _tokenStorage.readAccessToken();
      if (token != null && token.isNotEmpty) {
        options.headers['Authorization'] = 'Bearer $token';
      }
    }
    handler.next(options);
  }

  Future<void> _onError(
    DioException error,
    ErrorInterceptorHandler handler,
  ) async {
    final isAuthError = error.response?.statusCode == 401;
    final canRetry =
        error.requestOptions.extra['retried'] != true &&
        error.requestOptions.extra['skipAuth'] != true &&
        _refresher != null;

    if (isAuthError && canRetry) {
      final newToken = await _refreshOnce();
      if (newToken != null) {
        try {
          final response = await _retry(error.requestOptions, newToken);
          return handler.resolve(response);
        } on DioException catch (e) {
          return handler.next(e);
        }
      }
      // Refresh failed -> session is dead.
      _onSessionExpired?.call();
    }

    handler.next(error);
  }

  /// Ensures only one refresh runs at a time even under concurrent 401s.
  Future<String?> _refreshOnce() {
    return _inFlightRefresh ??= _refresher!().whenComplete(() {
      _inFlightRefresh = null;
    });
  }

  Future<Response<dynamic>> _retry(RequestOptions options, String newToken) {
    final headers = Map<String, dynamic>.from(options.headers)
      ..['Authorization'] = 'Bearer $newToken';
    return dio.fetch(
      options.copyWith(
        headers: headers,
        extra: {...options.extra, 'retried': true},
      ),
    );
  }
}

/// App-wide client. `configureAuth` is wired by the auth controller at startup.
final dioClientProvider = Provider<DioClient>((ref) {
  return DioClient(tokenStorage: ref.watch(tokenStorageProvider));
});
