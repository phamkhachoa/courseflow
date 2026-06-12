import 'package:dio/dio.dart';

import 'api_exception.dart';

/// Helpers for the CourseFlow response envelope.
///
/// Success envelope:
/// ```json
/// { "data": {...}, "traceId": "...", "timestamp": "..." }
/// ```
/// Some public endpoints return the payload directly (bare list/object), so the
/// unwrap logic tolerates both shapes.
class ApiEnvelope {
  const ApiEnvelope._();

  /// Pulls the meaningful payload out of a response body.
  ///
  /// - `{ "data": X, ... }`  -> X
  /// - bare list / object    -> returned as-is
  static Object? unwrap(Object? body) {
    if (body is Map<String, dynamic> && body.containsKey('data')) {
      return body['data'];
    }
    return body;
  }

  /// Unwraps a payload expected to be a JSON object.
  static Map<String, dynamic> unwrapObject(Object? body) {
    final data = unwrap(body);
    if (data is Map<String, dynamic>) return data;
    throw const ApiException(
      code: 'MALFORMED_RESPONSE',
      message: 'Expected a JSON object from the server.',
    );
  }

  /// Unwraps a payload expected to be a JSON list. Returns `[]` when null.
  static List<Map<String, dynamic>> unwrapList(Object? body) {
    final data = unwrap(body);
    if (data == null) return const [];
    if (data is List) {
      return data.whereType<Map<String, dynamic>>().toList(growable: false);
    }
    throw const ApiException(
      code: 'MALFORMED_RESPONSE',
      message: 'Expected a JSON array from the server.',
    );
  }

  /// Converts a Dio failure into a typed [ApiException] carrying the backend
  /// `code`/`message` when present.
  static ApiException toApiException(DioException error) {
    final response = error.response;
    final status = response?.statusCode;
    final body = response?.data;

    if (body is Map<String, dynamic>) {
      final code = body['code'];
      final message = body['message'];
      if (code is String) {
        return ApiException(
          code: code,
          message: message is String ? message : code,
          statusCode: status,
          traceId: body['traceId'] as String?,
        );
      }
    }

    final code = switch (error.type) {
      DioExceptionType.connectionTimeout ||
      DioExceptionType.sendTimeout ||
      DioExceptionType.receiveTimeout =>
        'NETWORK_TIMEOUT',
      DioExceptionType.connectionError => 'NETWORK_UNAVAILABLE',
      _ => 'NETWORK_ERROR',
    };
    return ApiException(
      code: code,
      message: switch (code) {
        'NETWORK_TIMEOUT' => 'The server took too long to respond.',
        'NETWORK_UNAVAILABLE' =>
          'Cannot reach CourseFlow. Check your connection.',
        _ => error.message ?? 'Unexpected network error.',
      },
      statusCode: status,
    );
  }
}
