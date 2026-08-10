import 'dart:io' show Platform;

class ApiConfig {
  static const String productionBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://api.example.com',
  );

  static String get baseUrl {
    if (productionBaseUrl.isNotEmpty) return productionBaseUrl.replaceAll(RegExp(r'/$'), '');
    return 'http://localhost:8000';
  }
}
