import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/dio_client.dart';
import '../../../core/storage/token_storage.dart';
import '../data/auth_repository.dart';
import '../domain/auth_models.dart';

/// Lifecycle of the signed-in session.
enum AuthStatus { unknown, authenticated, unauthenticated }

class AuthState {
  const AuthState({required this.status, this.user});

  final AuthStatus status;
  final AuthUser? user;

  const AuthState.unknown() : this(status: AuthStatus.unknown);
  const AuthState.signedOut() : this(status: AuthStatus.unauthenticated);

  bool get isAuthenticated => status == AuthStatus.authenticated;
}

/// Owns auth state, persists tokens to secure storage, and registers the
/// refresh callback with [DioClient] so every other repository transparently
/// recovers from `401`.
class AuthController extends Notifier<AuthState> {
  late final AuthRepository _repo = ref.read(authRepositoryProvider);
  late final TokenStorage _storage = ref.read(tokenStorageProvider);
  late final DioClient _client = ref.read(dioClientProvider);

  @override
  AuthState build() {
    _client.configureAuth(
      refresher: _refreshAccessToken,
      onSessionExpired: _forceSignOut,
    );
    return const AuthState.unknown();
  }

  /// Called once at startup: restore session from secure storage if a refresh
  /// token is present and still valid.
  Future<void> bootstrap() async {
    final refreshToken = await _storage.readRefreshToken();
    if (refreshToken == null || refreshToken.isEmpty) {
      state = const AuthState.signedOut();
      return;
    }
    try {
      final session = await _repo.refresh(refreshToken);
      await _persist(session);
      state = AuthState(status: AuthStatus.authenticated, user: session.user);
    } catch (_) {
      await _storage.clear();
      state = const AuthState.signedOut();
    }
  }

  Future<void> login() async {
    final session = await _repo.loginWithKeycloak();
    await _persist(session);
    state = AuthState(status: AuthStatus.authenticated, user: session.user);
  }

  Future<void> logout() async {
    await _repo.logout(idToken: await _storage.readIdToken());
    await _storage.clear();
    state = const AuthState.signedOut();
  }

  Future<void> _persist(AuthSession session) => _storage.save(
    accessToken: session.accessToken,
    refreshToken: session.refreshToken,
    idToken: session.idToken,
  );

  /// Interceptor hook: refresh the access token using the stored refresh token.
  Future<String?> _refreshAccessToken() async {
    final refreshToken = await _storage.readRefreshToken();
    if (refreshToken == null || refreshToken.isEmpty) return null;
    try {
      final session = await _repo.refresh(refreshToken);
      await _persist(session);
      return session.accessToken;
    } catch (_) {
      return null;
    }
  }

  void _forceSignOut() {
    _storage.clear();
    state = const AuthState.signedOut();
  }
}

final authControllerProvider = NotifierProvider<AuthController, AuthState>(
  AuthController.new,
);
