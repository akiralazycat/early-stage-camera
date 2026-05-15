# Giroux ダゲレオタイプ・カメラ (1839) — インタラクティブ 3D アセット v2

写真史の黎明を象徴する **1839 年 Alphonse Giroux et Cie 製ダゲレオタイプ・カメラ** を、概念忠実な精度で再構築した手続き生成 3D モデル一式。Web(model-viewer / three.js)上で、操作パネル + ホットスポット + ドラッグ + 露光時間スライダー + シーク再生 + 暗室セーフライト + 音響 + WebXR/AR の体験を提供します。

## 主要機能(v2)

| カテゴリ | 内容 |
|---|---|
| ジオメトリ | ベベル付き木箱、真鍮ネジ(計28本)、摺動レール、革ストラップ、Daguerre 赤蝋封印、Giroux 銘板(三段刻印) |
| 光学 | Chevalier アクロマート(凸クラウン+凹フリント二群)、Waterhouse 型固定絞り(f/14)、内壁艶消し黒 |
| マテリアル | マホガニー木目 / 真鍮 / 革のプロシージャル PBR テクスチャ(numpy 生成、PNG 埋込) |
| アニメ | 16 名前付きクリップ(分解、光学経路、撮影 7 段、化学 5 段) |
| アノテーション | 15 ホットスポット、日英解説、出典、化学式、安全警告 |
| インタラクション | 部品ホットスポット、内箱ピント/キャップ/スライドのドラッグ、露光時間スライダーで像濃度連動、タイムラインのスクラブ・逆再生 |
| 体験モード | レッドセーフライト自動切替、WebAudio 効果音、WebXR/AR Quick Look 対応 |

## 生成物

```
dist/
├── daguerreotype_giroux_1839.blend   (~450 KB)
├── daguerreotype_giroux_1839.glb     (~5.3 MB; テクスチャ埋込)
├── daguerreotype_giroux_1839.usdz    (~5.2 MB; AR Quick Look)
├── annotations.json                   (ホットスポット + 解説)
├── textures/                          (PNG: 木目/真鍮/革/Boulevard du Temple/safelight)
└── audio/                             (WAV: brass_click/wood_slide/dark_slide/chem_bubble)
```

## 動作確認

```bash
cd /Users/manabeakira/Documents/3d
python3 -m http.server 8000
# → http://localhost:8000/viewer.html を Chrome / Safari で開く
```

iOS Safari でアクセスすると右下に AR アイコンが出現し、AR Quick Look (.usdz) で実空間に配置できます。

## 再ビルド

```bash
bash build.sh                                  # アセット生成 + Blender 実行 + エクスポート
# 任意の手動ステップ:
# 1) tools/fetch_assets.py を Blender で再実行(テクスチャ・音声を再生成)
# 2) 実物の《Boulevard du Temple》PD JPG を `dist/textures/_boulevard_src.jpg` に手動配置すると、
#    procedural fallback ではなく実写真が銀板テクスチャに使われます
```

## 操作パネル

### 基本
- **分解 / 再組立** — 全部品が放射状に分離 → 復元
- **初期姿勢** — リセット

### 光学経路
- 入射光円錐 → レンズ屈折 → スリ硝子上の倒立像を表示/非表示
- FOV ≈ 38.7°、f/14 の数値を併記

### 撮影工程(7 段 + 連続再生)
1. プレートホルダー装着
2. ダークスライド引抜
3. キャップ開放(露光開始)
4. 露光(スライダーで像濃度連動)
5. キャップ閉鎖
6. スライド戻し
7. ホルダー取外

### 化学工程(5 段)
- 板研磨 → ヨウ素感光 → 水銀現像 → 定着 → 完成像
- 化学反応式と安全警告を info パネルに同時表示
- 化学クリップ選択時は **自動でレッドセーフライトモード** に切替

### 手動制御(ドラッグ)
- 内箱ピント送り(±80 mm)
- レンズキャップ回転(0〜95°)
- ダークスライド抽き(0〜220 mm)

### タイムライン制御
- スクラブバー、逆再生、速度切替 ×0.5/×1/×2

## ホットスポット

`annotations.json` を fetch して `<button slot="hotspot-N">` を動的生成。クリックすると当該部位の解説 + 出典 + 化学式 + 安全警告を info パネルに表示。15 個の主要部位を網羅:

外箱・レンズアセンブリ・Waterhouse 絞り・レンズキャップ・Giroux 銘板・Daguerre 封印・内箱・スリ硝子・プレートホルダー・ダークスライド・銀板・ヨウ素箱・水銀箱・定着トレイ・三脚

## 史実考証パラメータ

| 部位 | 採用値 |
|---|---|
| 形式 | スライディングボックス式二重木箱 |
| 外箱内寸 | 約 305 × 370 × 510 mm |
| 材質 | マホガニー / 真鍮金具 / 革 |
| レンズ | Charles Chevalier アクロマート(凸クラウン + 凹フリント)、f≈380mm、f/14 |
| シャッター | 機械式なし、真鍮スイベル式キャップ |
| 板サイズ | 165 × 216 mm(plaque entière)銀メッキ銅板 |
| 現像 | 水銀蒸気 ~60°C |
| 定着 | 食塩水(初期) → チオ硫酸ナトリウム(Herschel, 1839 末) |
| 銘板 | "Daguerréotype / Alphonse Giroux et Cie / Rue du Coq-Saint-Honoré, No.7 à Paris" |
| 封印 | Daguerre の赤蝋封(反偽造) |

## 化学反応式(ビューアにも表示)

| 工程 | 反応 |
|---|---|
| ヨウ素感光 | 2 Ag(s) + I₂(g) → 2 AgI(s) |
| 露光 | AgI + hν → Ag⁰ + ½ I₂(潜像) |
| 水銀現像 | Hg(g) + Ag⁰ → Hg·Ag アマルガム |
| 定着 (Herschel) | AgI + 2 Na₂S₂O₃ → Na₃[Ag(S₂O₃)₂] + NaI |

## 安全警告(ビューア化学工程に併記)

- **水銀**: 蒸気は中枢神経毒。19 世紀のダゲレオタイピストには震顫・人格変化等の水銀中毒事例多数。現代では絶対に再現してはならない。
- **ヨウ素**: 蒸気は粘膜刺激性。換気必須。
- **チオ硫酸ナトリウム**: 比較的安全だが酸との混合で SO₂ ガス発生。

## 出典

- Helmut Gernsheim, *The History of Photography from the Camera Obscura to the Beginning of the Modern Era*, McGraw-Hill, 1969.
- Josef Maria Eder, *History of Photography*, Columbia Univ. Press, 1945.
- M. Susan Barger & William B. White, *The Daguerreotype: Nineteenth-Century Technology and Modern Science*, Smithsonian, 1991.
- Janet E. Buerger, *French Daguerreotypes*, Univ. Chicago Press, 1989.
- George Eastman Museum 所蔵記録: "Daguerreotype camera, Alphonse Giroux et Cie, 1839".
- James M. Reilly, *Care and Identification of 19th-Century Photographic Prints*, Eastman Kodak, 1986.
- LACMA / Wikimedia Commons, "Boulevard du Temple" (1838) — PD 画像(本リポジトリでは Wikimedia ホットリンク制限のため procedural fallback を使用)。

## アーキテクチャ

```
build_daguerreotype.py    # bpy 単一ファイル(セクション化されたオーケストレーター)
build.sh                  # アセット生成 → Blender 実行
tools/fetch_assets.py     # numpy + bpy.image でテクスチャ・音声を生成
viewer.html               # model-viewer + 全インタラクション UI
dist/                     # 成果物
```

## 既知の制約

- USDZ は AR Quick Look の制約により1アニメのみ自動再生(現状は最初の export 順に依存)。USDZ への tap-action behavior 注入は `usd-core` 依存で本ビルドでは未実装(README に手順を残す予定)。
- 《Boulevard du Temple》画像は Wikimedia の hot-link 制限で procedural mockup を使用。実写真を `dist/textures/_boulevard_src.jpg` に手動配置 → `tools/fetch_assets.py` を再実行で置換可能。

## ライセンス

スクリプトおよび生成データは社内教育/学術利用を想定。文献図版自体は含まない。
