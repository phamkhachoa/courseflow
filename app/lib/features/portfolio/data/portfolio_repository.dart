import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_envelope.dart';
import '../../../core/api/dio_client.dart';
import '../../auth/application/auth_controller.dart';
import '../domain/portfolio_models.dart';

/// Portfolio APIs:
///  - `GET  /v1/portfolios/students/{studentId}/evidence`
///  - `POST /v1/portfolios/students/{studentId}/evidence`
class PortfolioRepository {
  PortfolioRepository(this._client);

  final DioClient _client;
  Dio get _dio => _client.dio;

  Future<List<PortfolioEvidence>> evidence(String studentId) async {
    try {
      final res = await _dio.get<Object?>(
        '/v1/portfolios/students/$studentId/evidence',
      );
      return ApiEnvelope.unwrapList(res.data)
          .map(PortfolioEvidence.fromJson)
          .toList(growable: false);
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }

  Future<void> addEvidence({
    required String studentId,
    required String title,
    required String description,
    required String tag,
  }) async {
    try {
      await _dio.post<Object?>(
        '/v1/portfolios/students/$studentId/evidence',
        data: {'title': title, 'description': description, 'tag': tag},
      );
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }
}

final portfolioRepositoryProvider = Provider<PortfolioRepository>((ref) {
  return PortfolioRepository(ref.watch(dioClientProvider));
});

/// Evidence for the signed-in learner.
final myEvidenceProvider =
    FutureProvider.autoDispose<List<PortfolioEvidence>>((ref) {
      final user = ref.watch(authControllerProvider).user;
      if (user == null) return Future.value(const []);
      return ref
          .watch(portfolioRepositoryProvider)
          .evidence(user.id.toString());
    });
