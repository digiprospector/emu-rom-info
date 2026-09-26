# FC/NES 多源复古游戏多媒体数据库构建指令与全流程规范 (AI 指南)

> **使用说明**：本文件专为 AI 编程助手（如 Antigravity、Claude Code、Cursor、GPT-4 等）设计。当您需要从零开始或迁移重建该项目时，只需将本文件的完整内容直接发送给 AI，或将其放置于项目根目录作为核心规范文档，AI 即可严格按照规范从头构建至当前完整状态。

---

## 1. 项目定位与核心目标

你是一名资深的全栈与数据工程师。你的任务是基于根目录下已有的原始文件，从零构建一个名为 `emu-rom-info` 的**红白机/FC/NES/FDS 全谱系多媒体元数据库与自包含交互中心**。

### 核心产出物矩阵：
1. **统一数据资产**：
   - `data/fc_nes_games.json`：全量结构化元数据。
   - `data/fc_nes_games.pkl`：Python 高性能二进制序列化对象。
   - `data/fc_nes_games.py`：可直接 `from fc_nes_games import FC_NES_GAMES` 引用的模块代码。
   - `data/fc_nes_games.csv`：扁平化多版本表格导出。
   - `data/fc_nes_games.xlsx`：带首行冻结、跨区高亮与 B 站超链接的富样式 Excel。
2. **零依赖自包含交互式前端**：
   - `data/fc_nes_games.html`：现代暗色极客美学界面，内嵌全部数据与资源下载中心，支持多维即时筛选、全文检索与 B 站解说视频秒级起播弹窗。
3. **自动化质量防线**：
   - 包含 10 项严苛业务强断言的测试套件（执行命令：`python fetch_fc_nes.py --verify`）。
   - 自动生成的视频与游戏缺失追踪报告（`docs/missing_videos_and_games.md`）。

---

## 2. 外部输入数据源说明

项目根目录下已具备或需抓取的原始数据源如下：

1. **No-Intro 官方权威 DAT 文件（用户已置于根目录）**：
   - `Nintendo - Family Computer Disk System (FDS) (xxxx).dat`
   - `Nintendo - Nintendo Entertainment System (Headered) (xxxx).dat`
   - *特征*：标准 XML 结构，包含每款 ROM 的校验码（CRC/MD5/SHA1/SHA256）以及关键的跨版本克隆属性 `cloneof` / `cloneofid`。
2. **维基百科游戏词条数据**：
   - 抓取或缓存维基百科 NES 欧美版、FC 日版卡带、FDS 磁碟机词条，获取正式发售日期、日文名、英文名、发行商等。
3. **中文民间权威译名库 (`rom-name-cn`)**：
   - 用于补全官方维基未记载的大陆经典民间中文译名（如将《Fester's Quest》译为《福斯特的冒险》）。
4. **B 站红白机编年史解说视频分段（UP 主：雷文）**：
   - 涵盖 01~100+ 期编年史视频（BV 号、分 P、分段章节名、起播时间戳如 `14:38` 并换算为秒数 `878`）。

---

## 3. 核心工程架构原则（硬性约束）

1. **双阶段解耦设计（必须严格遵守）**：
   - **阶段一（网络拉取）**：仅负责外部爬取（维基与 B 站分段），将未处理的原始数据持久化至 `data/raw/*.json`。
   - **阶段二（纯离线清洗与全格式构建）**：**严禁任何外网请求**。完全基于本地 `data/raw/`、根目录 `.dat` 文件与用户规则 `override.yaml`，纯离线执行解析、跨区合并、视频挂载与全格式导出。
2. **测试框架约束**：
   - **严禁使用 pytest**。所有验证统一编写自定义校验函数与断言（通过 `python fetch_fc_nes.py --verify` 运行）。
3. **版本控制安全**：
   - 未经用户明确口头批准，禁止自动执行任何 `git` 写操作（如 `git add`, `git commit`, `git push`）。

---

## 4. 深度数据融合与合并算法规范

### 4.1 跨美日版本同款识别与并查集聚类
- **识别途径**：
  1. 通过 No-Intro DAT 中的 `cloneofid` / `cloneof` 关联（例如美版《Casino Kid》与日版《100万$キッド》属于克隆关系）；
  2. 维基百科同名词条及英日重定向关系；
  3. `rom-name-cn` 中英日交叉映射库；
  4. `override.yaml` 中的用户自定义 `merge_games` 规则。
- **算法模型**：
  - 使用并查集（Union-Find）将属于同一款游戏的 NES/FC/FDS 记录聚合为单个统一游戏条目（`is_cross_region: True`）。
  - 保留各区域的独立发售日：`release_dates: {japan: "...", north_america: "...", europe: "..."}`。

### 4.2 发售时间主导定序规则（核心铁律）
- **全球首发判定**：合并后的游戏条目，以其在日本、北美或欧洲中**最早发售的日期作为该游戏的主发布时间**。
- **跨区同款合并语法规定 (`merge_games`)**：
  - 格式必须为：`"时间在前的游戏ID/名称": "时间在后的游戏ID/名称"`（严格满足 `Key <= Value`）。
  - 合并后条目主 ID 优先继承发售在先的日版/美版 Slug，不得颠倒时间线。

---

## 5. 人工干预机制：`override.yaml` 规则系统

为实现人机协同精确对齐，必须设计并支持根目录下的 `override.yaml` 文件，包含以下 4 个标准配置段：

```yaml
# 1. 规范游戏正式中文名（与B站名称匹配时自动完成视频对齐）
# 严禁多个不同的 Key 映射至同一个中文名！
title_zh:
  "captain-planet-and-the-planeteers": "地球超人"
  "nes-open-tournament-golf": "马里奥高尔夫公开赛"

# 2. 视频强制对齐映射（仅当游戏中文名无需改动，但视频章节名存在特异/双标题后缀时使用）
video_mappings:
  "battle-formula": "超级间谍猎人(US) / 方程式战斗赛车(JP)"

# 3. 跨区同款手动合并（时间早的放 Key，时间晚的放 Value）
merge_games:
  # FC 日版 1991-09-27 在先，NES 美版 1992-02 在后
  "battle-formula": "super-spy-hunter"

# 4. 互斥游戏强制隔离（防止因译名相似被算法误判合并）
separate_games:
  "游戏A": "游戏B"
```

---

## 6. 实施路线图（分步执行计划）

请严格按照以下 5 个 Phase 依次执行，每完成一个阶段必须输出统计并自检：

### Phase 1：数据源探测与结构定义
1. 解析根目录下的两个 No-Intro XML DAT 文件，输出各自的 `<game>` 数量、属性与克隆关系字段样本。
2. 设计 `GameRecord` 标准数据结构（包含 `id`, `title_zh`, `title_en`, `title_ja`, `is_cross_region`, `platforms`, `publishers`, `release_dates`, `versions`, `video`）。
3. 建立 `data/raw/` 目录并固化维基百科基础条目缓存。

### Phase 2：DAT 解析与并查集跨区合并
1. 实现 XML 解析器提取每款 ROM 的克隆关系网。
2. 结合维基百科数据与 `rom-name-cn`，运行并查集（Union-Find）进行聚类。
3. 实现首发日期定序逻辑与 `override.yaml` 的 `merge_games` / `separate_games` 优先判定。
4. 校验合并效果（必须确保诸如《Casino Kid》与《100万$キッド》、《Battle Formula》与《Super Spy Hunter》正确合并）。

### Phase 3：B 站视频提取与多级模糊匹配
1. 实现 B 站分 P 简介时间轴解析器，提取章节名与秒数时间戳。
2. 设计文本归一化算法（去除标点、统一小写、简繁转换、罗马数字转阿拉伯数字如 `III` -> `3`）。
3. 依次执行精确匹配、去后缀匹配与加权相似度匹配，并将匹配结果挂载至游戏的 `video` 属性。

### Phase 4：外部规则加载与双阶段离线构建
1. 实现主构建入口 `python fetch_fc_nes.py --build`。
2. 完整加载 `override.yaml` 中的 4 种调整规则，实现中文名覆盖、视频强制绑定与属性微调。
3. 保证在无外网连接时，从 Raw 数据与 DAT 文件能完全独立重现构建。

### Phase 5：多端数据导出、自包含 HTML 与质量断言
1. 导出全格式：JSON、Pickle、Python 模块、CSV、富样式 Excel。
2. 构建自包含纯单页 HTML（`data/fc_nes_games.html`）：
   - 现代深色极客风格、Glassmorphism 磨砂质感；
   - 纯前端即时搜索、跨区/平台/年代过滤、视频一键弹窗起播、全格式数据下载面板。
3. 固化 10 项强校验系统（`python fetch_fc_nes.py --verify`）：
   - 断言文件完整度与字节大小；
   - 断言总条目数、跨区游戏合并数量；
   - 经典游戏与视频时间轴抽检断言；
   - 前端自包含内嵌数据无外部 JS 依赖断言。
4. 输出未匹配统计报表（`docs/missing_videos_and_games.md`）。
