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
| [DroneState](../fly_in/model/drone_state.py) | `AtZone(zone)`・`InTransit(from_zone, to_zone)`とその合併型`DroneState`。Zone名の文字列だけを持つ値オブジェクトで、Zone名の存在・隣接性・遷移の合法性は検証しない。`frozen dataclass`という具体型は[T06 / #7](https://github.com/AMkuro/Fly-in/issues/7)でレビュー中の実装案であり、承認済み契約ではない。Plan・Reservation・StateHistoryからはまだ利用されていない |
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
`AtZone`の型は[実装済みの表](#implemented)のDroneStateにあるが、格納方法・履歴との関係を実装した処理はまだない。
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


<a id="t02-state-sharing-contract"></a>

### T02 — 状態・共有契約（部分承認・未実装）

以下は[T02 / #2](https://github.com/AMkuro/Fly-in/issues/2)で**採用された設計方針**であり、具体的なPython型・メソッド・格納方式まで確定したものではない。[DEC-021](decisions.md#dec-021)〜[DEC-024](decisions.md#dec-024)に採用理由と根拠を記載する。T03で確定した探索戦略は[下記T03節](#t03-pathfinding-policy)を参照する。

#### 状態と時刻

- Droneの物理状態は概念上`AtZone / InTransit`の2種類。到着済みは`AtZone(end)`で保持し、以後の移動は許可せず移動トークンにも含めない（[DEC-001](decisions.md#dec-001)）。
- **状態の場所情報はZone名（`str`）で保持する**（[DEC-026](decisions.md#dec-026)）。概念上、`AtZone`は`zone: str`、`InTransit`は`from_zone: str`と`to_zone: str`を持つ。Zone/Connectionのオブジェクト参照を状態内に保存しない。移動中の出発元・到着先の順序はConnection上の方向を表す。
- 位置・経路の利用者（Planner、Scheduler、Simulation、Renderer等）は必要なマップ属性を`MapGraph.zone(zone_name)`、接続を`MapGraph.connection_between(from_zone, to_zone)`で参照する。MapGraphのZone・Connection情報を状態へ複製しない。無効なZone名・接続・移動は検証時に拒否するが、構築時にどこまで検証するかは未決。
- `S_0`は初期状態、`S_t`はターン`t`の開始状態。ターン`t`の同時行動で`S_(t+1)`になる。外部移動出力の第1行は`S_0 → S_1`に対応する。
- `TurnState`は概念上1時点の全Drone状態。`StateHistory`は`S_0, S_1, …`の確定済み状態列。**各ターンの全Drone状態を保存する履歴方式A**を採用する。確定済みの過去状態は変更せず、CUIの調査やGUIの巻き戻し・再生に利用する。

#### PlanとReservation

- **1機分のPlanは、時刻を添え字とする`list[DroneState]`相当の状態リスト**とする（[DEC-025](decisions.md#dec-025)）。`plan[t]`は時刻`t`の`AtZone / InTransit`を表し、個々の状態要素に時刻を重複保存しない。`plan[0]`は`S_0`、`plan[t]`は`S_t`に対応する。startで待機する時刻も`AtZone(start)`を記録する。Plannerは既存のReservationを参照して実際のendまでの全経路候補を返す（[DEC-015](decisions.md#dec-015)）。**Plan自身にDrone IDは持たせず、専用Planクラスも必須としない。**
- **IDの割当て**：全機体のPlanが確定した後、**確定計画のリスト順に1始まりのDrone ID**を割り当てる（`plans[0]`がDrone 1）。Simulation・StateHistory・CLI・GUIはこの対応を共有し、移動途中で機体IDを交換しない。確定Reservationの中の`list`は後から変更せず、キャッシュ整合性を守る。変更防止・コピーの具体実装は未決（[DEC-025](decisions.md#dec-025)）。
- **Reservationは計画済みDroneの時刻付き全経路を順次追加**する構造を採用する。未計画Droneはstartで待機するとみなすが、未計画機体の各時刻の`AtZone(start)`をReservationに保存しない。全機体数`K`と予約済み経路数`P`から未計画数`K-P`を得られる（1経路が1機体を表すことを前提とする）。`Unplanned`という物理状態・計画済み集合を追加する必要はない。
- ReservationとStateHistoryは**状態要素を共通化**するが、**格納構造まで同一とはしない**。前者は全機体計画が未完成でも使う個別経路集合、後者は検証済み全機体の時系列状態。
- Reservationの時刻別**Zone占有・Connection利用量は、計画済み経路から導出したキャッシュ（案B）**とする（[DEC-027](decisions.md#dec-027)）。定義容量は静的MapGraphのものを参照する。**時刻を第1キーとする疎な辞書**を使い、使用数0のキーは省略・照会時0として扱う。具体的な概念構造は`zone_occupancy[t][zone_name]`と`connection_usage[t][connection_key]`。ゾーン名は文字列、Connectionキーは`MapGraph.connection_key(a, b)`による無向正規化キーとする。
- **時刻の意味は異なる**：`zone_occupancy[t][z]`は状態`S_t`でZone `z`にいる機体数、`connection_usage[t][e]`は`S_t → S_(t+1)`の移動ターン`t`における容量判定用使用量。start/endのZone占有は無制限のためキャッシュから省ける。
- **候補PlanのZone差分**：各`plan[t]`が`AtZone(z)`なら、start/endを除いて`delta_zone[t][z] += 1`。`InTransit`ならZone使用差分はない。
- **候補PlanのConnection差分**：連続する`plan[t] → plan[t+1]`を調べ、通常1ターン移動`AtZone(a) → AtZone(b)`、restrictedへの進入`AtZone(a) → InTransit(a,b)`の場合、それぞれ`delta_connection[t][connection_key(a,b)] += 1`。待機と合法なrestrictedの強制到着`InTransit(a,b) → AtZone(b)`は新たな利用として加算しない。合法な強制到着についてはT01式の`B_e(t)=F_e(t)`によって退出分が同一ターンに解放される。**この簡約を採用する場合も、restrictedの翌ターン強制到着を別途検証する**。
- **差分検証→一括確定**：**Reservationが**候補Planの状態遷移を検証し、既存Reservationを変更せず差分を生成する。全関連時刻で`zone_occupancy + delta_zone`および`connection_usage + delta_connection`がMapGraphの容量を超えないことを確認する。合法なら**候補Planと容量キャッシュを原子的に反映**し、違反なら差分を破棄して既存予約を変更しない（[DEC-028](decisions.md#dec-028)）。Planがendに到着して以降はendに留まるため、終了後のZone容量予約を追加生成しない。キャッシュは**確定済みPlanだけから再構築でき、再構築した値と常に一致**しなければならない。
- 予約候補に対しては[T01の容量・合法性契約](#t01-movement-contract)をそのまま適用する。Zoneでは`O_z(t+1)=O_z(t)-D_z(t)+A_z(t)`かつ`0<=O_z(t+1)<=C_z`、無向Connectionでは双方向合算の`0<=B_e(t)-F_e(t)+S_e(t)+N_e(t)<=C_e`を検証する。restrictedの進入翌ターンの強制到着、blocked禁止、到着後不動、start/endの容量例外も必須。

#### 責務分担・確定境界

**現行の所有関係**：Schedulerは最適化の試行・制御だけを担当する。候補Planの**合法性の判定とReservationの変更**はReservationの操作に閉じ込める。Plannerは確定予約を変更せず、Simulationは完成計画の独立検証を維持する（[DEC-028](decisions.md#dec-028)）。

| 領域 | 承認済みの役割 |
|---|---|
| Planner | 時刻付き予約A*で1機分のPlan候補を探索する。Schedulerの探索条件変更・再探索要求を受ける。**確定Reservationは直接書き換えない** |
| Scheduler | Plannerの探索条件・計画順を変更し、候補をReservationの検証・追加操作に渡して結果に応じて再試行する。全体再計画・合法な完成計画のMakespan比較・最良計画保持を担う。**容量や移動の合法性を直接判定せず、Reservationの正本・キャッシュを直接更新しない**（[DEC-028](decisions.md#dec-028)） |
| Reservation | 既存予約に対して候補Planの**状態遷移・容量合法性を検証**し、差分を算出する。すべて合法なら**Planと容量キャッシュを原子的に追加**する。不合法なら予約を変更しない。正本と導出キャッシュの整合性を所有する（[DEC-028](decisions.md#dec-028)） |
| Simulation | 全Droneの完成計画を**独立して**合法性・全機体end到着まで検証し、確定StateHistoryを生成する |
| CLI / CUI / GUI | 検証済みStateHistoryから規定の移動出力・デバッグ表示・再生を行う。CUIを優先し、既存GUIが問題なければ活用する |

T03の[全体再計画方式C](decisions.md#dec-016)に従い、改善試行ごとにReservationを初期化する。失敗した試行は保持済みの最良完成計画を上書きしない。計画全体を外部出力開始前に完成・独立検証し、**出力・再生中にPlannerを再実行しない**（[DEC-019](decisions.md#dec-019)）。

Subject準拠の移動行とデバッグ情報は区別する。GUIを最終採用しないなら、Subject v2.0の**色付き端末表示**の要件を満たす必要がある。

#### T02の未決事項

- `AtZone / InTransit`の**場所フィールド（Zone名`str`）は決定済み**。その具体的なPython型（dataclass等）、`DroneState`の型別名、`TurnState / Reservation / StateHistory / Move / Snapshot`のフィールド・所有者・読取APIは未決。Planは`list[DroneState]`相当（[DEC-025](decisions.md#dec-025)）。
- Planのend到着後の状態は`AtZone(end)`として暗黙に継続し、容量キャッシュを無限延長しない方針とする。**検証と追加の責務はReservation自身に確定済み**（[DEC-028](decisions.md#dec-028)）。未決なのは検証・追加APIの引数と結果、**原子的更新と例外時の実装保証**、公開・再構築API、Simulationへの引渡し・内部エラー・失敗時のフォールバック切替。
- 確定履歴の不変性の実装、履歴のメモリ負荷、表示用Snapshotの具体的な型・契約、可視化方式の最終選択。

<a id="t03-pathfinding-policy"></a>

### T03 — 探索基準方式（方針承認・詳細未確定）

**基準方式は、時間付き予約を考慮するA*（Cooperative A*系）**とする（[DEC-014](decisions.md#dec-014)、2026-10-29開発者承認）。これは**アルゴリズム方針の承認であり、探索・Simulation本体の実装完了や最終的なT03のCloseを意味しない**。

- 時刻を含む探索と、他機体が将来利用するZone・Connectionの容量確認を組み合わせ、T01の合法性（同時移動、restrictedの強制到着、双方向共有容量、start/end例外）を満たす全体計画を目指す。
- **初期Plannerは、実際のendまでの全経路候補を探索する**（[DEC-015](decisions.md#dec-015)）。時間窓・中間地点ゴールによる部分経路は初期基準方式に含めず、必要になった場合の拡張候補として残す。Schedulerは候補をReservationの検証・追加操作へ渡し、結果を受けて試行を調整する（[DEC-028](decisions.md#dec-028)）。
- **Schedulerは全体計画を初期状態から再構築する方式Cを採用**する（[DEC-016](decisions.md#dec-016)）。SchedulerはPlannerへ探索パラメータを渡し、**経路分散の評価**と**同着候補の選択順**を変更して試行を繰り返せるようにする。各試行で合法な完成計画のMakespanを比較し、最良計画を保持する。局所的な予約取消し方式Bは必要になれば検討する。評価関数の詳細と、試行予算・時刻上限の具体的な値は未決。
- **全機体の計画は実行・出力開始前に完成させる**（[DEC-019](decisions.md#dec-019)）。Schedulerは事前に全体計画の生成・再試行・最良Makespan選択を終え、Simulationへ完成計画を渡す。SimulationはT01合法性と全機体到着を独立検証して確定StateHistoryを生成し、その後CLI/Rendererがターン別の移動出力と表示・再生を行う。確定済み履歴の再生中にPlannerを実行しない。検証失敗時の具体的な内部エラー／フォールバック切替および入出力型はT02で決める。
- **静的経路が存在するなら、1機ずつendまで完走させる逐次配送をフォールバックとする**（[DEC-017](decisions.md#dec-017)）。start/endの容量は無制限で、通行可能なZone・Connectionの容量は正のため、他機体をstartで待機させれば競合せず有限時間で全機体を配送できる。静的経路がない場合のエラーは[DEC-013](decisions.md#dec-013)。最適化の探索上限などで計画が得られないことを「静的に到達不能」と混同しない。静的経路選択方法と具体的な停止条件は未決。
- **停止規則は3つ**（[DEC-018](decisions.md#dec-018)）：(1) 現在の最良の合法計画のMakespanを`U`とすると、改善試行は全機体の完了を`U-1`ターン以内に制限する。(2) Schedulerの全体再計画には有限の試行予算を設ける。(3) Makespanの証明可能な下界`LB`に`U=LB`で到達したら早期終了する。試行上限の具体値、下界計算方法、探索資源制限は未決。試行に失敗しても保持済みの合法な最良計画を失わない。
- **priority Zoneの選好は同着時優先**（[DEC-020](decisions.md#dec-020)）。合法な候補経路同士のend到着時刻が等しい場合にpriority経由を選好し、priorityだけを理由に到着が遅い経路を選ばない。移動コストはnormal同様1ターン。Schedulerの全体計画採否はMakespanを第一基準とする。priority経由の評価尺度・分散評価との同着時の詳細比較は未決。
- 逐次的な機体割当ては全体Makespanの最小性や探索の完全性を保証しない。Subjectの最適ターン目標と合法性を区別し、実装後にそれぞれ評価する。
- priority経由の同着候補間の詳細な比較規則、経路分散の評価式（Prim法による木の特徴量利用も未採用）、priority以外の同着候補選択規則、**採用済み停止規則を実現する具体的な予算値・下界算出方法**、フォールバック用静的経路の選択方式は**未承認**。予約表や状態の具体的なPython型、所有者、Planner/Scheduler/Simulation間の共有契約も一部のみ承認済みであり、[T02](https://github.com/AMkuro/Fly-in/issues/2)と相互に検討する。
- [T03 / #3](https://github.com/AMkuro/Fly-in/issues/3)は、T02との照合と残る判断の承認を経て完了とする。ただし、**T02・T03全体の完了を実装の一律の開始条件とはせず**、承認済み範囲の小単位から実装・テストを並行できる（[DEC-029](decisions.md#dec-029)）。新しい設計判断は引き続き人間の承認を要する。

<a id="incremental-implementation-policy"></a>

### 実装への移行 — 承認済み範囲から段階的に着手

[DEC-029](decisions.md#dec-029)により、**T02・T03の未決事項をすべて解消するまで本体の全実装を停止する運用は採用しない**。既存のT01合法性契約、T02の部分承認済み状態・予約契約、T03の採用済み探索方針を守り、**限定した実装単位のAI実装・単体テストと、人間による読解・レビューを並行**して進める。実装できた範囲と未決事項を区別し、Issue完了を偽らない。

- **初回の実装対象**：T06（[Issue #7](https://github.com/AMkuro/Fly-in/issues/7)）の一部として、`AtZone(zone: str)`・`InTransit(from_zone: str, to_zone: str)`・`DroneState`の具体化と小規模な単体テスト。Python型の具体方式など未承認部分は実装案と理由をレビュー可能にし、重要な契約変更は人間が採否を決める。最初からScheduler・Planner・Reservation・Simulation全部を生成しない。
- **後続の目安（自動の一括承認ではない）**：Reservation（T01合法性と容量キャッシュ・確定時整合性）→Simulation（独立検証・StateHistory・規定CLI出力）→静的逐次配送のフォールバックとPlanner/Schedulerの時間付き予約A*・全体再試行。各工程は必要になった契約の承認済み範囲に限定する。
- **検証と読解**：小単位ごとに、差分・採用理由・データフロー・不変条件・反例を提示し、手計算したテストや独立の確認で点検する。対象テスト・flake8・mypyも実行して結果を記録する。AIが生成したことやテスト成功だけを正当性の根拠としない。
- **依然未決**：Reservationの詳細な例外時原子性・API、Simulationの詳細型とエラー、Rendererの型と最終表示方式、T03の経路分散評価・探索予算・その他の最適化詳細。具体的に必要になる工程で判断し、`OPEN`・`PROPOSED`を独断で確定しない。
- **提出ゲートは維持**：通常の開発作業を許可しても、`master`・42提出リポジトリへの反映は別途人間のレビューと明示承認を要する。作業ルールは[AGENTS.md](../AGENTS.md)、進捗・受け入れ条件はT02/T03/T06/T07のIssuesを正本とする。

## Proposed

次は未承認で、現在の[部分承認済みT02契約](#t02-state-sharing-contract)および[T03方針](#t03-pathfinding-policy)を取り消すものではない。

- State・Move・Reservation・StateHistory・Snapshotの具体的なPython型、所有者・読取API。Planのリスト表現は[DEC-025](decisions.md#dec-025)、`AtZone / InTransit`のZone名フィールドは[DEC-026](decisions.md#dec-026)で承認済み。
- Reservationの**検証・追加APIの具体型、更新・例外時の原子性保証・公開API**、Plan/Stateの確定後の変更防止、Simulation検証失敗の実装契約。キャッシュ構造と差分生成は[DEC-027](decisions.md#dec-027)、検証・追加操作の所有者は[DEC-028](decisions.md#dec-028)で承認済み。
- 予約付きA*の評価関数、経路分散・詳細tie-break、具体的探索予算・停止値と追加最適化（T03の未決事項）。
- RendererへのSnapshot受渡しの具体型と、GUIか色付き端末表示かの最終選択。

未承認案の検討・採否待ち・実装進捗は、[対応するGitHub Issues](https://github.com/AMkuro/Fly-in/issues)（特に[状態・共有契約の設計 / T02](https://github.com/AMkuro/Fly-in/issues/2)・[探索・割当て方式の選定 / T03](https://github.com/AMkuro/Fly-in/issues/3)）で扱う。過去の候補や未決事項は[引き継ぎ記録](../.agent/handoffs/2026-10-23-design-context.md)に履歴として残す。新たな判断が承認された場合に限り[決定索引](decisions.md)へ採否・根拠を記録する。
