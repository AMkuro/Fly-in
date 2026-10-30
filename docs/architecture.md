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

<a id="t01-movement-contract"></a>

### T01 — 同時移動・容量とスケジュール合法性

以下は**承認済みの規則・契約であり、Simulation本体への実装を意味しない**。Subject v2.0 VI・VII.2〜VII.5の明文と、プロジェクトが具体化した判定式・境界解釈を区別する。採否・根拠は[DEC-002](decisions.md#dec-002)・[DEC-012](decisions.md#dec-012)・[DEC-013](decisions.md#dec-013)、手計算例は[T01の集約コメント](https://github.com/AMkuro/Fly-in/issues/1#issuecomment-6465527632)を参照する。

#### 移動とZone占有

- 全ドローンの行動はターン開始時の状態から決定し、**同一ターンの移動は同時**に行われる。ある機体を先に更新した結果で別機体の合法性を変えない（Subject v2.0 VII.3）。
- 移動コストは**到着先Zoneのタイプ**に依存する。normal・priorityは1ターン、restrictedへの進入は2ターン、blockedへの進入・通過は禁止。priorityをどう優先して経路選択するかは[T03](https://github.com/AMkuro/Fly-in/issues/3)の対象。
- Zone上の待機は可能であり、待機ターン数の上限は規定されていない。restrictedへのConnection上で追加待機はできず、進入の次ターンに必ず到着する（Subject v2.0 VII.3）。
- start・endを除く各Zone `z` で、ターン `t` 開始時占有数 `O_z(t)`、今ターンの出発数 `D_z(t)`、到着数 `A_z(t)`、容量 `C_z` を定義する。restrictedへの進入は出発、Connectionからの到着は到着に含む。

$$
O_z(t+1)=O_z(t)-D_z(t)+A_z(t)
$$

$$
\forall z\notin\{start,end\}:\quad 0\le O_z(t+1)\le C_z
$$

退出で空いたZone容量は**同じターン**に再利用できる（Subject v2.0 VII.3）。startとendは容量制限なし（VII.4）。startへの再入場も、他の移動・Connection制約を満たせば合法とする（[DEC-013](decisions.md#dec-013)）。

#### Connection容量（OPEN-001を解決・ACCEPTED）

Connectionは双方向の1本の辺であり、両方向の利用数を**同じ容量**へ合算する。仲間への確認に基づくターン終了基準と双方向共有は`CONFIRMED`（[DEC-002](decisions.md#dec-002)）。Subject v2.0 VII.3では、Connectionから退出した機体の分をそのターンに再利用でき、restricted移動中の機体が到着したターンにも別機体が同じConnectionを利用開始できると明記された。

ターン `t` におけるConnection `e` の量を定義する。

| 記号 | 意味 |
|---|---|
| `B_e(t)` | ターン開始時にrestricted移動中でConnection上にいる機体数 |
| `F_e(t)` | 同ターンにConnectionから目的Zoneへ到着し退出する機体数 |
| `S_e(t)` | 同ターンにrestrictedへ向けてConnectionへ進入する機体数 |
| `N_e(t)` | 同ターンにConnectionを1ターンで通常通過する機体数（双方向合計） |
| `C_e` | `max_link_capacity`（Connection容量） |

開発者が承認した容量判定式：

$$
\boxed{0\le U_e(t)=B_e(t)-F_e(t)+S_e(t)+N_e(t)\le C_e}
$$

`U_e(t)`は**Connection容量の判定用利用量**であり、Connection上にターン終了時に残る機体数そのものではない。合法なrestricted移動では、Connection上にいる全機体は次ターンに必ず到着するため`F_e(t)=B_e(t)`。その条件下に限って`S_e(t)+N_e(t)\le C_e`と簡約できる。機体別の強制到着チェックをこの簡約によって省略してはならない。

既存の[開発用検証器](../tools/verify_subject.py)はrestricted移動を到着ターンにも利用数へ加算する。この挙動はSubject v2.0 VII.3と上記契約に矛盾し、[T09](https://github.com/AMkuro/Fly-in/issues/5)で監査する。本体・検証器が承認式に対応済みだとは扱わない。

#### ターン・全スケジュールの合法性

`S_t`をターン開始状態、`M_t`を全機体の同ターン行動集合とし、次状態は`S_{t+1}=T(S_t,M_t)`と表す。ターンの合法性は、**移動規則（隣接性・blocked・コスト・到着後不動）、Zone容量、Connection容量、restrictedの強制到着**の論理積とする。

$$
Valid(S_t,M_t)=L_{move}(t)\land L_{zone}(t)\land L_{connection}(t)\land L_{restricted}(t)
$$

全スケジュールは、ある**有限の**終了ターン `T` に対し次を満たすこと。

$$
\forall t\in\{0,\ldots,T-1\}:\quad Valid(S_t,M_t)
$$

$$
\forall i:\quad s_i(T)=AtZone(end)
$$

到着済みの機体は内部ではendを指す状態として保持し、その後は動かさない（[DEC-001](decisions.md#dec-001)）。これは**移動列の正当性と配送完了**の条件であり、最短ターン数の保証やアルゴリズム選定ではない。個々のターンが合法でも、restrictedの翌ターンの到着先が塞がる計画は全スケジュールとして不正となる。将来予約・先読み・競合解決の具体方式は[T02](https://github.com/AMkuro/Fly-in/issues/2)・[T03](https://github.com/AMkuro/Fly-in/issues/3)に委ねる。

#### 出力・到達不能・境界判断

- restrictedへの移動中は`D<ID>-<connection>`、Zone到着時は`D<ID>-<zone>`を出力する（Subject v2.0 VII.5）。Connection文字列は**移動方向順の`<出発元>-<到着先>`**を採用する。例えば`connection: R-A`であってもA→Rなら`D1-A-R`、到着ターンは`D1-R`。これは[DEC-013](decisions.md#dec-013)のプロジェクト判断であり、内部Connectionの同一性・ID方式を固定しない。
- blockedは進入・通過不可（Subject明文）。実装上の「実効容量0」という表現は**未確定の実装選択**であり、入力の`max_drones`を0とすることはできない。
- startからendへ到達不能なら、パースエラーとは区別して検出・明確に報告し、シミュレーション前に終了する。具体的な承認済み報告形式はstderrへの`Error: No path from start to end.`、終了コード`1`（[DEC-013](decisions.md#dec-013)）。動作の実装は未完了。

### start・endの容量

start_hubとend_hubには容量制限を設けない。ここに書かれた`max_drones`は、正整数ならParserで受理して容量計算では無視し、0以下などの不正値はParserエラーにする（[DEC-010](decisions.md#dec-010)）。
現行Parserは全Zoneに正整数を要求するため検証側は既に満たすが、無視する側は容量計算が未実装のため未実装。
検証器が到着済み機体を`delivered`集合で管理していることも、本体の到着状態契約の実装を意味しない。
監査・整合性判断は別タスクとする。

<a id="t03-pathfinding-policy"></a>

### T03 — 探索基準方式（方針承認・詳細未確定）

**基準方式は、時間付き予約を考慮するA*（Cooperative A*系）**とする（[DEC-014](decisions.md#dec-014)、2026-10-29開発者承認）。これは**アルゴリズム方針の承認であり、探索・Simulation本体の実装完了や最終的なT03のCloseを意味しない**。

- 時刻を含む探索と、他機体が将来利用するZone・Connectionの容量確認を組み合わせ、T01の合法性（同時移動、restrictedの強制到着、双方向共有容量、start/end例外）を満たす全体計画を目指す。
- **初期Plannerは、実際のendまでの全経路候補を探索する**（[DEC-015](decisions.md#dec-015)）。時間窓・中間地点ゴールによる部分経路は初期基準方式に含めず、必要になった場合の拡張候補として残す。経路候補を受け取ってから、Schedulerが検証・予約反映するというT02の部分承認方針を踏まえる。
- **Schedulerは全体計画を初期状態から再構築する方式Cを採用**する（[DEC-016](decisions.md#dec-016)）。SchedulerはPlannerへ探索パラメータを渡し、**経路分散の評価**と**同着候補の選択順**を変更して試行を繰り返せるようにする。各試行で合法な完成計画のMakespanを比較し、最良計画を保持する。局所的な予約取消し方式Bは必要になれば検討する。評価関数の詳細と、試行予算・時刻上限の具体的な値は未決。
- **静的経路が存在するなら、1機ずつendまで完走させる逐次配送をフォールバックとする**（[DEC-017](decisions.md#dec-017)）。start/endの容量は無制限で、通行可能なZone・Connectionの容量は正のため、他機体をstartで待機させれば競合せず有限時間で全機体を配送できる。静的経路がない場合のエラーは[DEC-013](decisions.md#dec-013)。最適化の探索上限などで計画が得られないことを「静的に到達不能」と混同しない。静的経路選択方法と具体的な停止条件は未決。
- **停止規則は3つ**（[DEC-018](decisions.md#dec-018)）：(1) 現在の最良の合法計画のMakespanを`U`とすると、改善試行は全機体の完了を`U-1`ターン以内に制限する。(2) Schedulerの全体再計画には有限の試行予算を設ける。(3) Makespanの証明可能な下界`LB`に`U=LB`で到達したら早期終了する。試行上限の具体値、下界計算方法、探索資源制限は未決。試行に失敗しても保持済みの合法な最良計画を失わない。
- 逐次的な機体割当ては全体Makespanの最小性や探索の完全性を保証しない。Subjectの最適ターン目標と合法性を区別し、実装後にそれぞれ評価する。
- priorityの具体的優先規則、経路分散の評価式（Prim法による木の特徴量利用も未採用）、同着候補の選択規則、**採用済み停止規則を実現する具体的な予算値・下界算出方法**、フォールバック用静的経路の選択方式は**未承認**。予約表や状態の具体的なPython型、所有者、Planner/Scheduler/Simulation間の共有契約も一部のみ承認済みであり、[T02](https://github.com/AMkuro/Fly-in/issues/2)と相互に検討する。
- [T03 / #3](https://github.com/AMkuro/Fly-in/issues/3)は、T02との照合と残る判断の承認を経て完了とする。これらを決める前に本体実装を開始しない。

## Proposed

次は未承認で、現在有効な型・処理境界として採用しない。

- State・Move・Plan・Reservation・Snapshotの正本と保存方法。
- `InTransit`、`PlannedMove`、ターン状態遷移の具体的な型・入出力・エラー表現。
- Planner / Schedulerの分割、予約処理、GUIへのSnapshot受渡し。
- 採用済みの時間付き予約A*を具体化する探索・競合解決・再計画・停止方針、および他方式を追加するかどうか。
- 内部IDの文字列・整数の選択、探索失敗・再計画・終了条件。

未承認案の検討・採否待ち・実装進捗は、[対応するGitHub Issues](https://github.com/AMkuro/Fly-in/issues)（特に[状態・共有契約の設計 / T02](https://github.com/AMkuro/Fly-in/issues/2)・[探索・割当て方式の選定 / T03](https://github.com/AMkuro/Fly-in/issues/3)）で扱う。過去の候補や未決事項の一覧は[引き継ぎ記録](../.agent/handoffs/2026-10-23-design-context.md)に履歴として残す。新たな判断が承認された場合に限り[決定索引](decisions.md)へ採否・根拠を記録する。引き継ぎ記録のサンプル型をそのまま実装契約にしない。
