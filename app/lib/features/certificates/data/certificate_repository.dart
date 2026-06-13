import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_envelope.dart';
import '../../../core/api/dio_client.dart';
import '../domain/certificate_models.dart';

/// Certificate APIs:
///  - `GET /v1/certificates/mine`              learner's certificates (auth)
///  - `GET /v1/certificates/verify/{code}`     public verification (no auth)
class CertificateRepository {
  CertificateRepository(this._client);

  final DioClient _client;
  Dio get _dio => _client.dio;

  Future<List<Certificate>> myCertificates() async {
    try {
      final res = await _dio.get<Object?>('/v1/certificates/mine');
      return ApiEnvelope.unwrapList(res.data)
          .map(Certificate.fromJson)
          .toList(growable: false);
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }

  Future<CertificateVerification> verify(String code) async {
    try {
      final res = await _dio.get<Object?>(
        '/v1/certificates/verify/$code',
        options: Options(extra: {'skipAuth': true}),
      );
      return CertificateVerification.fromJson(
        ApiEnvelope.unwrapObject(res.data),
      );
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }
}

final certificateRepositoryProvider = Provider<CertificateRepository>((ref) {
  return CertificateRepository(ref.watch(dioClientProvider));
});

final myCertificatesProvider =
    FutureProvider.autoDispose<List<Certificate>>((ref) {
  return ref.watch(certificateRepositoryProvider).myCertificates();
});
