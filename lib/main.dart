import 'package:flutter/material.dart';
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
  String? error;
  List<dynamic> top = const [];

  @override
  void initState() { super.initState(); refresh(); }

  Future<void> refresh() async {
    setState(() { loading = true; error = null; });
    try {
      final result = await api.top3();
      if (!mounted) return;
      setState(() { top = result; loading = false; });
    } catch (e) {
      if (!mounted) return;
      setState(() { loading = false; error = e.toString(); });
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: const Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('AI 勝率分析師', style: TextStyle(fontWeight: FontWeight.w900)),
        Text('V4 · Backend First', style: TextStyle(fontSize: 11, color: Colors.white54)),
      ]),
      actions: [IconButton(onPressed: refresh, icon: const Icon(Icons.refresh))],
    ),
    body: RefreshIndicator(
      onRefresh: refresh,
      child: ListView(padding: const EdgeInsets.all(16), children: [
        Card(child: Padding(padding: const EdgeInsets.all(18), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('今日投注核心', style: TextStyle(fontSize: 27, fontWeight: FontWeight.w900)),
          const SizedBox(height: 6),
          Text('賽程、盤口、天氣與模型資料統一由 V4 Backend 提供。', style: TextStyle(color: Colors.grey.shade400)),
        ]))),
        const SizedBox(height: 16),
        Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          const Text('TOP 3', style: TextStyle(fontSize: 19, fontWeight: FontWeight.w900)),
          Chip(label: Text(loading ? '同步中' : 'Live API')),
        ]),
        const SizedBox(height: 8),
        if (loading) const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator())),
        if (error != null) Card(child: Padding(padding: const EdgeInsets.all(16), child: Text('Backend 尚未就緒：$error'))),
        if (!loading && error == null && top.isEmpty) const Card(child: Padding(padding: EdgeInsets.all(16), child: Text('目前沒有可用推薦。Backend 回傳空資料時不產生虛構投注訊號。'))),
        for (final item in top) _RecommendationCard(item: item),
        const SizedBox(height: 18),
        const Text('風控原則', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
        const SizedBox(height: 8),
        Card(child: Padding(padding: const EdgeInsets.all(14), child: Text('資料缺失時採 NO BET，不以預設值冒充真實資料；5 星代表訊號強度，不代表保證命中率。', style: TextStyle(color: Colors.grey)))),
      ]),
    ),
  );
}

class _RecommendationCard extends StatelessWidget {
  const _RecommendationCard({required this.item});
  final dynamic item;
  String value(String key) => item is Map ? '${item[key] ?? '—'}' : '—';
  @override
  Widget build(BuildContext context) => Card(
    margin: const EdgeInsets.only(bottom: 10),
    child: Padding(padding: const EdgeInsets.all(15), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
        Text(value('league'), style: const TextStyle(color: Color(0xFFD6B35A), fontWeight: FontWeight.w800)),
        Text(value('confidence'), style: const TextStyle(color: Color(0xFFD6B35A))),
      ]),
      const SizedBox(height: 7),
      Text(value('matchup'), style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w900)),
      const SizedBox(height: 7),
      Text('推薦：${value('pick')}   EV：${value('ev')}', style: const TextStyle(fontWeight: FontWeight.w800)),
    ])),
  );
}
