import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Persists auth tokens in the platform secure enclave (Keychain / Keystore).
///
/// This is the single source of truth for credentials at rest. The auth
/// controller hydrates from here on startup and writes back on login/refresh.
class TokenStorage {
  TokenStorage([FlutterSecureStorage? storage])
      : _storage = storage ??
            const FlutterSecureStorage(
              aOptions: AndroidOptions(encryptedSharedPreferences: true),
              iOptions: IOSOptions(
                accessibility: KeychainAccessibility.first_unlock,
              ),
            );

  final FlutterSecureStorage _storage;

  static const _kAccess = 'cf.accessToken';
  static const _kRefresh = 'cf.refreshToken';
  static const _kId = 'cf.idToken';

  Future<String?> readAccessToken() => _storage.read(key: _kAccess);
  Future<String?> readRefreshToken() => _storage.read(key: _kRefresh);
  Future<String?> readIdToken() => _storage.read(key: _kId);

  Future<void> save({
    required String accessToken,
    required String refreshToken,
    String? idToken,
  }) async {
    await _storage.write(key: _kAccess, value: accessToken);
    await _storage.write(key: _kRefresh, value: refreshToken);
    if (idToken == null || idToken.isEmpty) {
      await _storage.delete(key: _kId);
    } else {
      await _storage.write(key: _kId, value: idToken);
    }
  }

  Future<void> updateAccessToken(String accessToken) =>
      _storage.write(key: _kAccess, value: accessToken);

  Future<void> clear() async {
    await _storage.delete(key: _kAccess);
    await _storage.delete(key: _kRefresh);
    await _storage.delete(key: _kId);
  }
}

final tokenStorageProvider = Provider<TokenStorage>((ref) => TokenStorage());
