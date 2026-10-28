import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import 'services/backend_api.dart';

void main() => runApp(const WinRateApp());

class WinRateApp extends StatelessWidget {
  const WinRateApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
        debugShowCheckedModeBanner: false,
        title: 'AI 勝率分析師',
        theme: ThemeData.dark(useMaterial3: true).copyWith(
          scaffoldBackgroundColor: const Color(0xFF080A0F),
          colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFFD6B35A)),
          appBarTheme: const AppBarTheme(backgroundColor: Color(0xFF080A0F)),
        ),
        home: const Dashboard(),
      );
}

class Dashboard extends StatefulWidget {
  const Dashboard({super.key});

  @override
  State<Dashboard> createState() => _DashboardState();
}

class _DashboardState extends State<Dashboard> {
  final BackendApi api = BackendApi();
  bool loading = true;
  bool ready = false;
  String? error;
  List<dynamic> top = const [];
  List<Map<String, dynamic>> schedule = const [];
  Map<String, dynamic>? meta;
  DateTime? lastUpdated;

  String get taipeiDate =>
      DateTime.now().toUtc().add(const Duration(hours: 8)).toIso8601String().substring(0, 10);

  @override
  void initState() {
    super.initState();
    refresh();
  }

  Future<List<Map<String, dynamic>>> _loadOfficialSchedule() async {
    final today = DateTime.parse('${taipeiDate}T00:00:00Z');
    final start = today.subtract(const Duration(days: 1)).toIso8601String().substring(0, 10);
    final end = today.add(const Duration(days: 1)).toIso8601String().substring(0, 10);
    final uri = Uri.https('statsapi.mlb.com', '/api/v1/schedule', {
      'sportId': '1',
      'startDate': start,
      'endDate': end,
      'hydrate': 'team,probablePitcher,venue',
    });
    final response = await http.get(uri).timeout(const Duration(seconds: 12));
    if (response.statusCode != 200) {
      throw Exception('MLB 官方賽程回應異常（${response.statusCode}）');
    }
    final payload = jsonDecode(response.body) as Map<String, dynamic>;
    final dates = (payload['dates'] as List<dynamic>? ?? const []);
    final games = <Map<String, dynamic>>[];
    for (final day in dates) {
      for (final item in (day['games'] as List<dynamic>? ?? const [])) {
        if (item is Map<String, dynamic>) {
          final gameDate = item['gameDate']?.toString() ?? '';
          final parsed = DateTime.tryParse(gameDate);
          final taipeiGameDate = parsed == null
              ? (item['officialDate']?.toString() ?? '')
              : parsed.toUtc().add(const Duration(hours: 8)).toIso8601String().substring(0, 10);
          if (taipeiGameDate == taipeiDate || item['officialDate'] == taipeiDate) {
            games.add(item);
          }
        }
      }
    }
    games.sort((a, b) => (a['gameDate']?.toString() ?? '')
        .compareTo(b['gameDate']?.toString() ?? ''));
    return games;
  }

  Future<void> refresh() async {
    setState(() {
      loading = true;
      error = null;
      ready = false;
    });

    // Fetch the official schedule independently so a backend outage does not
    // make the entire mobile app unusable.
    final scheduleFuture = _loadOfficialSchedule();
    try {
      final health = await api.readiness().timeout(const Duration(seconds: 12));
      if (health['ready'] != true) {
        throw Exception('AI 推薦服務尚未就緒');
      }
      final result = await api.top3().timeout(const Duration(seconds: 12));
      final officialGames = await scheduleFuture;
      if (!mounted) return;
      setState(() {
        ready = true;
        top = result;
        schedule = officialGames;
        meta = health;
        lastUpdated = DateTime.now();
        loading = false;
      });
    } catch (e) {
      List<Map<String, dynamic>> officialGames = const [];
      String? scheduleError;
      try {
        officialGames = await scheduleFuture;
      } catch (scheduleException) {
        scheduleError = scheduleException.toString();
      }
      if (!mounted) return;
      setState(() {
        ready = false;
        top = const [];
        schedule = officialGames;
        meta = null;
        lastUpdated = DateTime.now();
        loading = false;
        error = scheduleError == null
            ? 'AI 推薦服務暫時無法連線；已切換官方賽程模式。'
            : 'AI 服務未就緒，官方賽程也暫時無法載入。請確認網路後重試。';
      });
    }
  }

  String _teamName(dynamic team) {
    if (team is Map<String, dynamic>) {
      final name = team['name'];
      if (name != null) return name.toString();
    }
    return '待確認';
  }

  String _pitcher(dynamic teamSide) {
    if (teamSide is Map<String, dynamic>) {
      final pitcher = teamSide['probablePitcher'];
      if (pitcher is Map<String, dynamic> && pitcher['fullName'] != null) {
        return pitcher['fullName'].toString();
      }
    }
    return '尚未公布';
  }

  String _startTime(Map<String, dynamic> game) {
    final raw = game['gameDate']?.toString();
    if (raw == null) return game['officialDate']?.toString() ?? '時間待確認';
    final parsed = DateTime.tryParse(raw);
    if (parsed == null) return raw;
    final local = parsed.toUtc().add(const Duration(hours: 8));
    final y = local.year.toString().padLeft(4, '0');
    final m = local.month.toString().padLeft(2, '0');
    final d = local.day.toString().padLeft(2, '0');
    final h = local.hour.toString().padLeft(2, '0');
    final min = local.minute.toString().padLeft(2, '0');
    return '$y/$m/$d $h:$min 台灣時間';
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('AI 勝率分析師',
                  style: TextStyle(fontWeight: FontWeight.w900)),
              Text('手機試用版 · MLB 官方賽程',
                  style: TextStyle(fontSize: 11, color: Colors.white54)),
            ],
          ),
          actions: [
            IconButton(
              tooltip: '重新整理',
              onPressed: loading ? null : refresh,
              icon: const Icon(Icons.refresh),
            ),
          ],
        ),
        body: RefreshIndicator(
          onRefresh: refresh,
          child: ListView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 28),
            children: [
              _statusCard(),
              const SizedBox(height: 14),
              if (loading)
                const Padding(
                  padding: EdgeInsets.all(28),
                  child: Center(child: CircularProgressIndicator()),
                ),
              if (!loading && error != null) ...[
                _notice(error!, warning: true),
                const SizedBox(height: 10),
              ],
              if (!loading && ready) ...[
                _sectionTitle('AI 今日推薦', '後端驗證'),
                if (top.isEmpty)
                  _notice('目前沒有通過驗證的推薦。依風控規則，暫不投注。')
                else
                  for (final item in top) _RecommendationCard(item: item),
                const SizedBox(height: 18),
              ],
              _sectionTitle('今日 MLB 賽程', '${schedule.length} 場'),
              if (!loading && schedule.isEmpty)
                _notice('目前沒有找到台灣時間今日的賽程，或官方服務暫時無法連線。請下拉重新整理。'),
              for (final game in schedule) _ScheduleCard(
                game: game,
                teamName: _teamName,
                pitcher: _pitcher,
                startTime: _startTime,
                aiReady: ready,
              ),
              const SizedBox(height: 16),
              _sectionTitle('投注風控', '必要提醒'),
              _notice(
                '後端未就緒、盤口缺失或模型資料不足時，推薦狀態會維持 NO BET。勝率與 EV 不代表保證獲利；投注前請再次核對先發與最新賠率。',
              ),
              if (lastUpdated != null)
                Padding(
                  padding: const EdgeInsets.only(top: 12),
                  child: Text(
                    '最後更新：${lastUpdated!.toLocal().toString().substring(0, 19)}',
                    style: const TextStyle(color: Colors.white38, fontSize: 11),
                    textAlign: TextAlign.center,
                  ),
                ),
            ],
          ),
        ),
      );

  Widget _statusCard() => Card(
        color: const Color(0xFF171A23),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('今日市場掃描',
                  style: TextStyle(fontSize: 24, fontWeight: FontWeight.w900)),
              const SizedBox(height: 6),
              Text(
                ready
                    ? 'AI 推薦服務已連線；賽程與推薦分開顯示。'
                    : '即使 AI 後端暫時離線，仍會嘗試載入 MLB 官方賽程。',
                style: TextStyle(color: Colors.grey.shade400),
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Icon(ready ? Icons.cloud_done : Icons.cloud_off,
                      color: ready ? Colors.greenAccent : Colors.orangeAccent,
                      size: 18),
                  const SizedBox(width: 7),
                  Expanded(
                    child: Text(
                      ready ? 'AI 後端已就緒' : '官方賽程備援模式',
                      style: const TextStyle(fontWeight: FontWeight.w800),
                    ),
                  ),
                  if (loading)
                    const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    ),
                ],
              ),
            ],
          ),
        ),
      );

  Widget _sectionTitle(String title, String label) => Padding(
        padding: const EdgeInsets.fromLTRB(0, 8, 0, 10),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(title,
                style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w900)),
            Chip(label: Text(label), visualDensity: VisualDensity.compact),
          ],
        ),
      );

  Widget _notice(String message, {bool warning = false}) => Card(
        color: warning ? const Color(0xFF2A2116) : const Color(0xFF171A23),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Text(message,
              style: TextStyle(
                  color: warning ? Colors.orangeAccent : Colors.white70)),
        ),
      );
}

class _ScheduleCard extends StatelessWidget {
  const _ScheduleCard({
    required this.game,
    required this.teamName,
    required this.pitcher,
    required this.startTime,
    required this.aiReady,
  });

  final Map<String, dynamic> game;
  final String Function(dynamic) teamName;
  final String Function(dynamic) pitcher;
  final String Function(Map<String, dynamic>) startTime;
  final bool aiReady;

  @override
  Widget build(BuildContext context) {
    final teams = game['teams'] as Map<String, dynamic>? ?? const {};
    final away = teams['away'] as Map<String, dynamic>? ?? const {};
    final home = teams['home'] as Map<String, dynamic>? ?? const {};
    final awayTeam = away['team'];
    final homeTeam = home['team'];
    final venue = game['venue'] as Map<String, dynamic>? ?? const {};
    final status = game['status'] as Map<String, dynamic>? ?? const {};
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.sports_baseball, color: Color(0xFFD6B35A)),
                const SizedBox(width: 7),
                Expanded(
                  child: Text(startTime(game),
                      style: const TextStyle(
                          color: Colors.white70, fontSize: 12)),
                ),
                Text(status['detailedState']?.toString() ?? '賽程',
                    style: const TextStyle(fontSize: 11, color: Colors.white54)),
              ],
            ),
            const SizedBox(height: 9),
            Text(
              '${teamName(awayTeam)} @ ${teamName(homeTeam)}',
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900),
            ),
            const SizedBox(height: 7),
            Text('先發：${pitcher(away)} vs ${pitcher(home)}',
                style: const TextStyle(color: Colors.white70, fontSize: 12)),
            if (venue['name'] != null)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text('球場：${venue['name']}',
                    style: const TextStyle(color: Colors.white54, fontSize: 12)),
              ),
            const SizedBox(height: 10),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: const Color(0xFF0D1016),
                borderRadius: BorderRadius.circular(9),
              ),
              child: Text(
                aiReady
                    ? '若此場未出現在上方 AI 推薦，代表目前沒有可展示的驗證訊號。'
                    : 'NO BET｜AI 後端未就緒；這張卡只提供賽程與先發，不是投注推薦。',
                style: const TextStyle(color: Color(0xFFD6B35A), fontSize: 12),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _RecommendationCard extends StatelessWidget {
  const _RecommendationCard({required this.item});
  final dynamic item;

  String value(String key) =>
      item is Map ? '${item[key] ?? '—'}' : '—';

  @override
  Widget build(BuildContext context) => Card(
        margin: const EdgeInsets.only(bottom: 10),
        child: Padding(
          padding: const EdgeInsets.all(15),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(value('league'),
                      style: const TextStyle(
                          color: Color(0xFFD6B35A),
                          fontWeight: FontWeight.w800)),
                  Text(value('confidence'),
                      style: const TextStyle(color: Color(0xFFD6B35A))),
                ],
              ),
              const SizedBox(height: 7),
              Text(value('matchup'),
                  style: const TextStyle(
                      fontSize: 19, fontWeight: FontWeight.w900)),
              const SizedBox(height: 7),
              Text('推薦：${value('pick')}   EV：${value('ev')}',
                  style: const TextStyle(fontWeight: FontWeight.w800)),
              if (value('reason') != '—') ...[
                const SizedBox(height: 7),
                Text(value('reason'),
                    style: const TextStyle(color: Colors.white70, fontSize: 12)),
              ],
            ],
          ),
        ),
      );
}
