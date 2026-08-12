class ApiConfig {
  // Public backend URL; secrets remain server-side. Override with --dart-define
  // if the hosting provider assigns a different URL.
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://ai-winrate-backend.onrender.com',
  );
}
