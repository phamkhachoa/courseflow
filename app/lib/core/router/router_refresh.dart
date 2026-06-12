import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Bridges a Riverpod provider to a [Listenable] so `go_router`'s
/// `refreshListenable` re-evaluates redirects whenever the watched value
/// changes.
class RouterRefreshNotifier extends ChangeNotifier {
  RouterRefreshNotifier(Ref ref, ProviderListenable<Object?> provider) {
    ref.listen<Object?>(
      provider,
      (_, __) => notifyListeners(),
      fireImmediately: false,
    );
  }
}
