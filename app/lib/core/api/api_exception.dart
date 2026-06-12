/// Domain-level error raised by the data layer.
///
/// Backend error envelope (see `backend/docs/api/courseflow-api.md`):
/// ```json
/// { "code": "COURSE_NOT_FOUND", "message": "...", "traceId": "...", "timestamp": "..." }
/// ```
class ApiException implements Exception {
  const ApiException({
    required this.code,
    required this.message,
    this.statusCode,
    this.traceId,
  });

  /// Stable machine code, e.g. `INVALID_CREDENTIALS`, `COURSE_NOT_FOUND`.
  final String code;

  /// Human readable message safe to surface to the user.
  final String message;

  /// HTTP status when available.
  final int? statusCode;

  /// Correlation id echoed by the backend, useful for support tickets.
  final String? traceId;

  bool get isUnauthorized => statusCode == 401;
  bool get isNotFound => statusCode == 404 || code.endsWith('_NOT_FOUND');

  @override
  String toString() => 'ApiException($code, $message, status=$statusCode)';
}
