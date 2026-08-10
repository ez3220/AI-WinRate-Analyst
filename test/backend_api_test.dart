import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import '../lib/services/backend_api.dart';

void main() {
  test('top3 decodes backend recommendations', () async {
    final client = MockClient((_) async => http.Response(
      jsonEncode({'recommendations': [{'matchup': 'LAD @ SF'}]}), 200,
      headers: {'content-type': 'application/json'},
    ));
    final api = BackendApi(client: client);
    final result = await api.top3();
    expect(result.single['matchup'], 'LAD @ SF');
  });

  test('backend errors fail closed', () async {
    final client = MockClient((_) async => http.Response('unavailable', 503));
    final api = BackendApi(client: client);
    expect(api.readiness(), throwsException);
  });
}
