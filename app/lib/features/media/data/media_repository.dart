import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../domain/media_models.dart';

/// Module-scoped media is not exposed by the gateway yet. Keep the module
/// screen honest instead of calling `/v1/media/assets` with an unsupported
/// `moduleId` query parameter.
final moduleMediaProvider =
    FutureProvider.autoDispose.family<List<MediaAsset>, String>((ref, _) async {
  return const <MediaAsset>[];
});
