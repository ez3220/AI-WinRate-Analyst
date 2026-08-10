import 'dart:convert';
import 'package:http/http.dart' as http;
import '../core/api_config.dart';

class BackendApi {
  const BackendApi({http.Client? client}) : _client = client ?? const http.Client();
  final http.Client _client;

  Uri _uri(String path, [Map<String, String>? query]) =>
      Uri.parse('${ApiConfig.baseUrl}/$path').replace(queryParameters: query);

  Future<Map<String, dynamic>> readiness() async {
    final response = await _client.get(_uri('health/ready'));
    return _decode(response);
  }

  Future<List<dynamic>> games({String? league}) async {
    final response = await _client.get(_uri('games', league == null ? null : {'league': league}));
    final data = _decode(response);
    return (data['games'] as List<dynamic>?) ?? const [];
  }

  Future<List<dynamic>> predictions() async {
    final response = await _client.get(_uri('predictions'));
    final data = _decode(response);
    return (data['predictions'] as List<dynamic>?) ?? const [];
  }

  Future<List<dynamic>> top3() async {
    final response = await _client.get(_uri('top3'));
    final data = _decode(response);
    return (data['recommendations'] as List<dynamic>?) ?? const [];
  }

  Map<String, dynamic> _decode(http.Response response) {
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception('Backend request failed: ${response.statusCode}');
    }
    final decoded = jsonDecode(response.body);
    if (decoded is! Map<String, dynamic>) throw Exception('Invalid backend response');
    return decoded;
  }
}
