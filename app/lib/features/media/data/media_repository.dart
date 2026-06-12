import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_envelope.dart';
import '../../../core/api/dio_client.dart';
import '../domain/media_models.dart';

/// Media APIs:
///  - `GET /v1/media/assets?moduleId=` (filtered to a module's content)
class MediaRepository {
  MediaRepository(this._client);

  final DioClient _client;
  Dio get _dio => _client.dio;

  Future<List<MediaAsset>> assetsForModule(String moduleId) async {
    try {
      final res = await _dio.get<Object?>(
        '/v1/media/assets',
        queryParameters: {'moduleId': moduleId},
      );
      return ApiEnvelope.unwrapList(res.data)
          .map(MediaAsset.fromJson)
          .toList(growable: false);
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }
}

final mediaRepositoryProvider = Provider<MediaRepository>((ref) {
  return MediaRepository(ref.watch(dioClientProvider));
});

final moduleMediaProvider = FutureProvider.autoDispose
    .family<List<MediaAsset>, String>((ref, moduleId) {
      return ref.watch(mediaRepositoryProvider).assetsForModule(moduleId);
    });
