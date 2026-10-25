# Fly-in architecture

現在の実装構成と承認済み共有契約の正本。初期調査は2026-10-24 JST、実装の基準は`2698224`。以後、責務・共有契約・実装状態が変わった変更と同時に更新する。
採用理由・承認根拠は[決定索引](decisions.md)、操作手順は[development.md](development.md)を参照する。

| 状態 | 意味 |
|---|---|
| `Implemented` | コード上に実装がある。テスト成功やSubject適合性を保証する表示ではない |
| `Accepted / Pending` | 承認済みの契約だが、本体には未実装 |
| `Proposed` | 未承認。現行アーキテクチャの契約として採用しない |

## Implemented

| 領域・コード | 現在の責務と境界 |
|---|---|
| [CLI](../fly-in.py)、[FlyInApp](../fly_in/orchestra.py) | 引数を解析し、Parserを呼ぶ。`MapGraph`を生成するが後続処理には渡していない。通常実行はマップ概要、`--gui`は静的Viewerを開く。移動列は生成しない |
| [Parser](../fly_in/parse/map_parser.py)、[RawMap生成](../fly_in/parse/raw_map_builder.py)、[検証アダプタ](../fly_in/parse/validation_adapter.py) | 読込・行解析・RawMap構築・Pydantic検証を分担する。`load()`の戻り値は`MapData`。入力構文の型は[map_format_def.py](../fly_in/parse/map_format_def.py)にある |
| [MapData・Zone・Connection](../fly_in/model/map_data.py) | Pydanticで入力事実と構造上の制約を保持・検証する。Zoneは名前をキーとする辞書、Connectionはリスト。容量フィールドの存在は、ターンごとの容量計算式の承認を意味しない |
| [MapGraph](../fly_in/model/map_graph.py) | `MapData`から隣接関係・Connection索引を構築する。Zone名は文字列、双方向Connectionの検索キーは名前の順序を正規化した組。blockedもトポロジーに残す。経路の合法性を計算する処理はまだない |
| [ViewerApp](../fly_in/rendering/viewer_app.py)、[MapView](../fly_in/rendering/map_view.py) | `MapData`に基づく静的描画と検査表示。Viewerは部品とイベントを接続し、MapViewはCanvas描画、[Viewport](../fly_in/rendering/viewport.py)は座標変換、[InspectorPanel](../fly_in/rendering/inspector_panel.py)は対象情報を表示する。探索・移動合法性は判定しない |
| [PlaybackController](../fly_in/rendering/playback_controller.py)、[PlaybackControls](../fly_in/rendering/playback_panel.py) | 再生位置・タイマーと操作UIの部品は存在する。Viewerには未接続で、Snapshot生成処理もない。`Sequence[object]`を承認済みSnapshot型とは扱わない |
| [開発用検証器](../tools/verify_subject.py) | Parserが返す入力事実を使ってCLI出力を再生検証する。本体のGraph・探索・Schedulerは呼ばない。Simulation本体でも、Subject適合性の確定した根拠でもない |

現時点の接続は`CLI → FlyInApp → Parser → MapData`であり、そこからGraph生成と静的表示へ進む。
[simple_dijkstra.py](../fly_in/pathfinding/simple_dijkstra.py)は空で、[simulation](../fly_in/simulation/__init__.py)にも実装はない。ファイル名からDijkstraの採用を推定しない。
現在のデータ形式は実装の観測結果であり、将来も固定する契約ではない（[DEC-003](decisions.md#dec-003)）。

<a id="pending"></a>

## Accepted / Pending

### 到着済みの状態

本体の状態モデルでは、end到着後も`AtZone(goal)`として保持し、endを指すことから到着を判定する。到着後は移動させない。
Pythonクラスの定義、格納方法、履歴との関係は未承認で、`AtZone`自体も未実装。
採用理由は[DEC-001](decisions.md#dec-001)を参照する。

### Connection容量の確認済み部分

Connectionの占有はターン終了時の状態を基準としてよく、容量は双方向で共有する。
これは仲間への確認に基づく`CONFIRMED`の解釈で、Subject本文の引用ではない。
Subject v2.0 VII.3は次の2点を明文で定める。

- そのターンにZoneやConnectionから出る機体の分の容量は、同じターン内に別の機体が使える。
- restricted Connectionは機体が到着先Zoneに着いたターンに空き、別の機体はそのターンから同じConnectionを渡り始めてよい。

**それ以外の具体的な容量計算式は未承認・保留（OPEN-001）であり、上記だけから式を確定しない。**
確認根拠と管理先は[DEC-002](decisions.md#dec-002)を参照する。

既存検証器はrestricted移動の出発・到着ターン双方で利用数を加算しており、到着ターンの加算は上記の明文と矛盾する。

### start・endの容量

start_hubとend_hubには容量制限を設けない。ここに書かれた`max_drones`は、正整数ならParserで受理して容量計算では無視し、0以下などの不正値はParserエラーにする（[DEC-010](decisions.md#dec-010)）。
現行Parserは全Zoneに正整数を要求するため検証側は既に満たすが、無視する側は容量計算が未実装のため未実装。
検証器が到着済み機体を`delivered`集合で管理していることも、本体の到着状態契約の実装を意味しない。
監査・整合性判断は別タスクとする。

## Proposed

次は未承認で、現在有効な型・処理境界として採用しない。

- State・Move・Plan・Reservation・Snapshotの正本と保存方法。
- `InTransit`、`PlannedMove`、ターン状態遷移の具体的な型・入出力・エラー表現。
- Planner / Schedulerの分割、予約処理、GUIへのSnapshot受渡し。
- BFS、A*、予約方式、最大フロー等の探索・競合解決方式。
- 内部IDの文字列・整数の選択、探索失敗・再計画・終了条件。

候補の詳細と未解決事項の管理先は[決定索引](decisions.md#open-items)を参照する。引き継ぎ記録のサンプル型をそのまま実装契約にしない。
