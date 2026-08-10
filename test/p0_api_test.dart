import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import '../lib/services/backend_api.dart';

void main() {
  test('top3 decodes backend recommendations', () async {
    final client = MockClient((request) async => http.Response(
      jsonEncode({'recommendations': [{'game': 'LAD'}]}),
      200,
      headers: {'content-type': 'application/json'},
    ));
    final api = BackendApi(client: client);
    final result = await api.top3();
    expect(result.single['game'], 'LAD');
  });

  test('backend errors are surfaced', () async {
    final client = MockClient((request) async => http.Response('error', 503));
    final api = BackendApi(client: client);
    expect(() => api.readiness(), throwsException);
  });
}
