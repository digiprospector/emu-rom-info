# FC / NES / FDS 游戏与 B 站解说视频未对齐数据汇总报告

> 生成时间: 2026-09-26  
> 数据源: `data/fc_nes_games.json` (总计 1518 款游戏) 与 `data/raw/bilibili_segments_raw.json` (雷文鉴赏 01~99 期，共 1190 个视频分段)

## 一、核心数据全景概览

| 统计维度 | 统计对象 | 数量 | 占比 | 详细说明 |
| :--- | :--- | :--- | :--- | :--- |
| **游戏端** | 全局游戏总数 | 1518 款 | 100% | 包含 FC、NES、FDS 全部官方与主流发布作品 |
| | **已挂载视频的游戏** | **1175 款** | **77.4%** | 已成功匹配并绑定 B 站对应分集与时间戳 |
| | **没有视频的游戏 (总计)** | **343 款** | **22.6%** | 详见下方两阶段细分 |
| | ├─ **视频覆盖期内缺失** | **5 款** | **0.4%** | 1983~1991.08（截至《金属荣耀》），多为合辑/比赛卡 |
| | └─ **视频未制作期正常缺少** | **338 款** | **98.8%** | 1991.09~1994年作品，UP主雷文尚未制作鉴赏视频 |
| **视频端** | 视频分段总数 (01~99期) | 1190 个 | 100% | 雷文红白机鉴赏全部章节时间节点 |
| | **已成功匹配游戏的视频** | **1181 个** | **99.2%** | 涵盖单游戏对应及多版本重复介绍 |
| | **没有对应游戏的视频** | **9 个** | **0.8%** | 视频章节中有解说，但游戏库未匹配对应独立条目 |

---

## 二、没有对应游戏的视频清单 (共 9 个)

本部分列出 B 站视频章节中存在解说，但目前尚未对齐到游戏库独立条目的全部视频分段：

| 序号 | 视频期数/标题 | 时间点 | 章节原始名称 | BVID | 在线播放链接 |
| :---: | :--- | :---: | :--- | :---: | :--- |
| 1 | 【雷文】红白机游戏终极鉴赏37期-1988年6-7月篇 / 4K | `22:21` | **魔法弹珠台** | `BV1MU4RzpEZj` | [点击跳转播放](https://www.bilibili.com/video/BV1MU4RzpEZj/?t=1341) |
| 2 | 【雷文】红白机游戏终极鉴赏42期-1988年10月篇 / 4K | `01:02` | **超级马里奥USA** | `BV1LphrzqEaK` | [点击跳转播放](https://www.bilibili.com/video/BV1LphrzqEaK/?t=62) |
| 3 | 【雷文】红白机游戏终极鉴赏46期-1988年12月下篇 / 4K | `09:38` | **燃烧职业足球** | `BV1CLnPznEvz` | [点击跳转播放](https://www.bilibili.com/video/BV1CLnPznEvz/?t=578) |
| 4 | 【雷文】红白机游戏终极鉴赏51期-1989年4月篇 / 4K | `01:11` | **罗罗大冒险** | `BV1mDW1zEEwN` | [点击跳转播放](https://www.bilibili.com/video/BV1mDW1zEEwN/?t=71) |
| 5 | 【雷文】红白机游戏终极鉴赏63期-1990年1月篇 / 4K | `16:15` | **科尔维特ZR-1挑战/亚历克斯德梅奥的美国竞速(US)** | `BV1BwBxBhEks` | [点击跳转播放](https://www.bilibili.com/video/BV1BwBxBhEks/?t=975) |
| 6 | 【雷文】红白机游戏终极鉴赏85期-1990年12月中篇 / 4K | `00:41` | **忍者神龟(JP) / 忍者神龟2(US)** | `BV1b9Eq6iEAM` | [点击跳转播放](https://www.bilibili.com/video/BV1b9Eq6iEAM/?t=41) |
| 7 | 【雷文】红白机游戏终极鉴赏87期-1990年12月下篇 / 4K | `15:32` | **罗罗大冒险3(US)/罗罗大冒险2(JP)** | `BV1Nu7V6xEuf` | [点击跳转播放](https://www.bilibili.com/video/BV1Nu7V6xEuf/?t=932) |
| 8 | 【雷文】红白机游戏终极鉴赏90期-1991年2月上篇 / 4K | `07:09` | **飞龙之拳2（美版）** | `BV14QK36fEFZ` | [点击跳转播放](https://www.bilibili.com/video/BV14QK36fEFZ/?t=429) |
| 9 | 【雷文】红白机游戏终极鉴赏94期-1991年4月篇 / 4K | `00:24` | **新西兰故事** | `BV1VagF6mEcu` | [点击跳转播放](https://www.bilibili.com/video/BV1VagF6mEcu/?t=24) |

---

## 三、没有视频的游戏清单 —— 视频覆盖期内重点缺失游戏 (共 5 款)

此 15 款游戏发售于 1983 年至 1991 年 8 月之间（UP主雷文第 01~99 期视频覆盖范围），目前处于无视频绑定状态，通常为多合一卡带、欧美特殊大赛卡带或命名差异项：

| 序号 | 游戏唯一ID | 中文译名 | 英文名称 | 平台 | 发售日期 (日/美/欧) |
| :---: | :--- | :--- | :--- | :---: | :--- |
| 1 | `donkey-kong-classics` | 大金刚经典合辑 | Donkey Kong Classics | `NES` | 1988年10月 / 1989年8月10日 |
| 2 | `super-mario-bros-duck-hunt` | 超级马力欧兄弟/打野鸭 | Super Mario Bros./Duck Hunt]] | `NES` | 1988年11月 |
| 3 | `super-mario-bros-tetris-nintendo-world-cup` | 超级马力欧兄弟/俄罗斯方块/热血足球 | Super Mario Bros./Tetris/Nintendo World Cup | `NES` | 1988年11月 |
| 4 | `super-mario-bros-duck-hunt-world-class-track-meet` | 超级马力欧兄弟/打野鸭/田径运动会 | Super Mario Bros./Duck Hunt/World Class Track Meet | `NES` | 1990年12月 |
| 5 | `super-spike-v-ball-nintendo-world-cup` | 美国沙滩排球锦标赛 + 热血足球联盟 | Super Spike V'Ball/Nintendo World Cup | `NES` | 1990年12月 |

---

## 四、没有视频的游戏清单 —— 视频未制作期游戏 (共 338 款)

发售于 1991 年 9 月至 1994 年之后，属于 UP 主雷文红白机鉴赏第 99 期之后的时期，目前 UP 主尚未制作发布对应鉴赏视频：

> **平台分布情况**: FC: 144款, NES: 137款, FC/NES: 54款, FDS: 3款

<details>
<summary><b>点击展开查看全部 336 款未制作期游戏列表</b></summary>

| 序号 | 游戏ID | 中文名称 | 英文名称 | 平台 | 发售日期 |
| :---: | :--- | :--- | :--- | :---: | :--- |
| 1 | `adventures-of-lolo-3` | 蛋王子大冒险 3 | Adventures of Lolo 3 | `NES` | 1991年9月 / 1992年5月27日 |
| 2 | `captain-planet-and-the-planeteers` | 星球拯救队 | Captain Planet and the Planeteers | `NES` | 1991年9月 / 1992年8月20日 |
| 3 | `monster-truck-rally` | 大卡车越野赛 | Monster Truck Rally | `NES` | 1991年9月 |
| 4 | `nes-open-tournament-golf` | 马力欧高尔夫公开赛 | NES Open Tournament Golf | `FC/NES` | 1991年9月20日 / 1991年9月 / 1992年6月18日 |
| 5 | `smash-tv` | 电视斗士 | Smash TV | `NES` | 1991年9月 |
| 6 | `super-jeopardy` | 电视问答游戏 危机超级版 | Super Jeopardy! | `NES` | 1991年9月 |
| 7 | `cowboy-kid` | 西部小子 | Cowboy Kid | `FC/NES` | 1991年9月13日 / 1992年1月 |
| 8 | `dezaemon` | 绘描卫门 | Dezaemon | `FC` | 1991年9月13日 |
| 9 | `ufouria-the-saga` | 迷糊蛋 | Ufouria: The Saga | `FC/NES` | 1991年9月20日 / 1992年11月19日 |
| 10 | `nakajima-satoru-f-1-hero-2` | 中屿悟F1英雄2 | Nakajima Satoru - F-1 Hero 2 | `FC` | 1991年9月27日 |
| 11 | `spartan-x-2` | 成龙踢馆2 | Spartan X 2 | `FC` | 1991年9月27日 |
| 12 | `super-spy-hunter` | 方程序战斗赛车 | Super Spy Hunter | `FC/NES` | 1991年9月27日 / 1992年2月 |
| 13 | `ys-3-wanderers-from-ys` | 伊苏III 来自伊苏的冒险者 | Ys 3 - Wanderers From Ys | `FC` | 1991年9月27日 |
| 14 | `american-gladiators` | 美国斗士 | American Gladiators | `NES` | 1991年10月 |
| 15 | `bo-jackson-baseball` | 波杰克森棒球 | Bo Jackson Baseball | `NES` | 1991年10月 |
| 16 | `darkman` | 变形黑侠 | Darkman | `NES` | 1991年10月 |
| 17 | `home-alone` | 小鬼当家 | Home Alone | `NES` | 1991年10月 |
| 18 | `pirates` | 海盗 | Pirates! | `NES` | 1991年10月 |
| 19 | `roger-clemens-mvp-baseball` | 罗杰克莱门斯之MVP棒球 | Roger Clemens' MVP Baseball | `NES` | 1991年10月 |
| 20 | `trog` | 抢救龙蛋大作战 | Trog! | `NES` | 1991年10月 |
| 21 | `where-in-time-is-carmen-sandiego` | 卡门圣地牙哥时刻 | Where in Time Is Carmen Sandiego? | `NES` | 1991年10月 |
| 22 | `wolverine` | 特异功能组 - 金刚狼 | Wolverine | `NES` | 1991年10月 |
| 23 | `chibi-maruko-chan-uki-uki-shopping` | 樱桃小丸子 | Chibi Maruko Chan - Uki Uki Shopping | `FC` | 1991年10月4日 |
| 24 | `karakuri-kengou-den-musashi-road-karakuri-nin-hashiru` | 忍者剑豪传 | Karakuri Kengou Den - Musashi Road - Karakuri Nin Hashiru! | `FC` | 1991年10月5日 |
| 25 | `sd-gundam-gaiden-knight-gundam-monogatari-2-hikari-no-ki` | SD钢弹外传2：光之骑士 | SD Gundam Gaiden - Knight Gundam Monogatari 2 - Hikari no Ki | `FC` | 1991年10月12日 |
| 26 | `chaos-world` | 混沌世界 | Chaos World | `FC` | 1991年10月25日 |
| 27 | `famimaga-disk-vol-5-puyo-puyo` | 法米杂志软盘系列05：魔法气泡 | Famimaga Disk Vol.5 - Puyo Puyo | `FDS` | 1991年10月25日 |
| 28 | `great-deal` | 纸牌游戏 | Great Deal | `FC` | 1991年10月25日 |
| 29 | `time-zone` | 时空地带 | Time Zone | `FC` | 1991年10月25日 |
| 30 | `shatterhand` | 特救指令 | Shatterhand | `FC/NES` | 1991年10月26日 / 1991年12月 / 1992年11月19日 |
| 31 | `barbie` | 芭比娃娃 | Barbie | `NES` | 1991年11月 |
| 32 | `eliminator-boat-duel` | 赛艇决斗 | Eliminator Boat Duel | `NES` | 1991年11月 / 1993年4月29日 |
| 33 | `robin-hood-prince-of-thieves` | 罗宾汉 - 侠盗王子 | Robin Hood: Prince of Thieves | `NES` | 1991年11月 / 1992年12月10日 |
| 34 | `sesame-street-a-b-c-1-2-3` | - | Sesame Street: A-B-C/1-2-3 | `NES` | 1991年11月 |
| 35 | `snow-brothers` | 雪人兄弟 | Snow Brothers | `FC/NES` | 1991年12月6日 / 1991年11月 |
| 36 | `space-shuttle-project` | 太空梭计划 | Space Shuttle Project | `NES` | 1991年11月 |
| 37 | `star-wars` | 星际大战 | Star Wars | `NES` | 1991年11月 / 1992年3月26日 |
| 38 | `the-bard-s-tale` | - | The Bard's Tale | `NES` | 1991年11月 |
| 39 | `wurm-journey-to-the-center-of-the-earth` | JJ大作战 | Wurm: Journey to the Center of the Earth | `FC/NES` | 1991年11月15日 / 1991年11月 |
| 40 | `hammerin-harry` | 大力工头 | Hammerin' Harry | `FC/NES` | 1991年11月15日 / 1992年 |
| 41 | `radia-senki-reimei-hen` | 拉迪亚战记：黎明篇 | Radia Senki - Reimei Hen | `FC` | 1991年11月15日 |
| 42 | `shounen-ashibe-nepal-dai-bouken-no-maki` | 少年亚吉具：尼泊尔大冒险之卷 | Shounen Ashibe - Nepal Dai Bouken no Maki | `FC` | 1991年11月15日 |
| 43 | `bases-loaded-4` | 燃烧棒球最强篇 | Bases Loaded 4 | `FC/NES` | 1991年11月22日 / 1993年4月 |
| 44 | `minna-no-taabou-no-nakayoshi-dai-sakusen` | 大家一起连连看 | Minna no Taabou no Nakayoshi Dai Sakusen | `FC` | 1991年11月22日 |
| 45 | `pachio-kun-4` | 帕青夫君4 | Pachio Kun 4 | `FC` | 1991年11月22日 |
| 46 | `america-oudan-ultra-quiz-shijou-saidai-no-tatakai` | 横贯美国大猜谜 | America Oudan Ultra Quiz - Shijou Saidai no Tatakai | `FC` | 1991年11月29日 |
| 47 | `famicom-igo-nyuumon` | 围棋入门 | Famicom Igo Nyuumon | `FC` | 1991年11月29日 |
| 48 | `rampart` | 领国战役/领土大战 | Rampart | `FC/NES` | 1991年11月29日 / 1992年1月 |
| 49 | `batman-return-of-the-joker` | 炸药蝙蝠侠 | Batman: Return of the Joker | `FC/NES` | 1991年12月20日 / 1991年12月 / 1992年11月19日 |
| 50 | `captain-america-and-the-avengers` | 美国队长与复仇者 | Captain America and The Avengers | `NES` | 1991年12月 |
| 51 | `talespin` | 航空小英雄 | TaleSpin | `NES` | 1991年12月 / 1992年9月24日 |
| 52 | `tecmo-super-bowl` | 特库摩超级美式橄榄球 | Tecmo Super Bowl | `FC/NES` | 1991年12月13日 / 1991年12月 |
| 53 | `the-flintstones-the-rescue-of-dino-hoppy` | 摩登原始人 | The Flintstones: The Rescue of Dino & Hoppy | `FC/NES` | 1992年8月7日 / 1991年12月 / 1992年4月30日 |
| 54 | `the-simpsons-bart-vs-the-world` | 辛普森一家 巴特环游世界 | The Simpsons: Bart vs. the World | `NES` | 1991年12月 / 1992年10月22日 |
| 55 | `tiny-toon-adventures` | 兔宝宝历险记 | Tiny Toon Adventures | `FC/NES` | 1991年12月20日 / 1991年12月 / 1992年10月22日 |
| 56 | `tom-and-jerry` | 汤姆和杰瑞 | Tom and Jerry | `FC/NES` | 1992年11月13日 / 1991年12月 / 1992年10月22日 |
| 57 | `treasure-master` | 寻宝大师 | Treasure Master | `NES` | 1991年12月 |
| 58 | `famicom-jump-2-saikyou-no-7-nin` | 任天堂JUMP：最强的七人/英雄列传2 | Famicom Jump 2 - Saikyou no 7 Nin | `FC` | 1991年12月2日 |
| 59 | `heisei-tensai-bakabon` | 平成天才：笨蛋波恩 | Heisei Tensai Bakabon | `FC` | 1991年12月6日 |
| 60 | `mega-man-4` | 洛克人4 新的野心！！ | Mega Man 4 | `FC/NES` | 1991年12月6日 / 1992年1月 / 1993年1月21日 |
| 61 | `gimmi-a-break-shijou-saikyou-no-quiz-ou-ketteisen` | 史上最强问题王 | Gimmi a Break - Shijou Saikyou no Quiz Ou Ketteisen | `FC` | 1991年12月13日 |
| 62 | `teenage-mutant-ninja-turtles-2` | 忍者神龟 曼哈顿计划 | Teenage Mutant Ninja Turtles 2 | `FC/NES` | 1991年12月13日 / 1992年2月 |
| 63 | `tetris-2-bombliss` | 俄罗斯方块2 | Tetris 2 + Bombliss | `FC` | 1991年12月13日 |
| 64 | `toukyou-pachi-slot-adventure` | 东京帕青哥大冒险 | Toukyou Pachi Slot Adventure | `FC` | 1991年12月13日 |
| 65 | `tsuru-pika-hagemaru-mezase-tsuru-seko-no-akashi` | 光头王子闯天关 | Tsuru Pika Hagemaru - Mezase! Tsuru Seko no Akashi | `FC` | 1991年12月13日 |
| 66 | `yoshi` | 耀西的蛋 | Yoshi | `FC/NES` | 1991年12月14日 / 1992年6月 / 1992年12月30日 |
| 67 | `2nd-super-robot-wars` | 第2次超级机器人大战 | 2nd Super Robot Wars | `FC` | 1991年12月19日 |
| 68 | `asmik-kun-land` | 阿兹米克君 | Asmik Kun Land | `FC` | 1991年12月20日 |
| 69 | `bakushou-jinsei-gekijoh-3` | 爆笑人生剧场3 | Bakushou Jinsei Gekijoh 3 | `FC` | 1991年12月20日 |
| 70 | `banana-prince` | 香蕉王子大冒险 | Banana Prince | `FC/NES` | 1991年12月20日 / 1992年2月 |
| 71 | `famista-92` | 明星职棒92年度版 | Famista '92 | `FC` | 1991年12月20日 |
| 72 | `monster-maker-7-tsu-no-hihou` | 怪兽制造场：七个大密宝 | Monster Maker - 7 Tsu no Hihou | `FC` | 1991年12月20日 |
| 73 | `paaman-part-2-himitsu-kessha-madoodan-wo-taose` | 叮当超人2/小超人帕门2 | Paaman Part 2 - Himitsu Kessha Madoodan wo Taose! | `FC` | 1991年12月20日 |
| 74 | `battle-storm` | 战斗风暴 | Battle Storm | `FC` | 1991年12月21日 |
| 75 | `best-keiba-derby-stallion` | 亚斯基德贝赛马 | Best Keiba - Derby Stallion | `FC` | 1991年12月21日 |
| 76 | `choujin-sentai-jetman` | 鸟人战队：Jetman | Choujin Sentai - Jetman | `FC` | 1991年12月21日 |
| 77 | `nobunaga-no-yabou-bushou-fuuun-roku` | 信长之野望·武将风云录 | Nobunaga no Yabou - Bushou Fuuun Roku | `FC` | 1991年12月21日 |
| 78 | `sd-gundam-gachapon-senshi-4-new-type-story` | SD钢弹扭蛋战士4：新类型故事 | SD Gundam - Gachapon Senshi 4 - New Type Story | `FC` | 1991年12月21日 |
| 79 | `wacky-races` | 顽皮狗 | Wacky Races | `FC/NES` | 1991年12月25日 / 1992年5月 |
| 80 | `hudson-hawk` | 哈得森之鹰 | Hudson Hawk | `FC/NES` | 1991年12月27日 / 1992年2月 |
| 81 | `the-blue-marlin` | 钓鱼模拟游戏：海钓王 | The Blue Marlin | `FC/NES` | 1991年12月27日 / 1992年7月 |
| 82 | `ultraman-club-3-matamata-shutsugeki-ultra-kyodai` | 怪兽超人俱乐部3：再次出击！超人兄弟 | Ultraman Club 3 - Matamata Shutsugeki! Ultra Kyodai | `FC` | 1991年12月29日 |
| 83 | `bucky-o-hare` | 外星战将 | Bucky O'Hare | `FC/NES` | 1992年1月31日 / 1992年1月 / 1993年2月18日 |
| 84 | `cyberball` | 机器人橄榄球大赛 | Cyberball | `NES` | 1992年 |
| 85 | `dropzone` | 降落区 | Dropzone | `NES` | 1992年 |
| 86 | `goal-two` | 足球GOAL！ | Goal! Two | `FC/NES` | 1992年9月25日 / 1992年11月 / 1992年 |
| 87 | `international-cricket` | 国际板球赛 | International Cricket | `NES` | 1992年 |
| 88 | `kick-master` | 踢王 | Kick Master | `NES` | 1992年1月 |
| 89 | `konami-hyper-soccer` | 科乐美超级足球 | Konami Hyper Soccer | `NES` | 1992年 |
| 90 | `legends-of-the-diamond` | - | Legends of the Diamond | `NES` | 1992年1月 |
| 91 | `monster-in-my-pocket` | 魔鬼总动员 | Monster in My Pocket | `NES` | 1992年1月 |
| 92 | `motor-city-patrol` | 都市赛车 | Motor City Patrol | `NES` | 1992年1月 |
| 93 | `nightshade` | 百花百狼 | Nightshade | `NES` | 1992年1月 |
| 94 | `noah-s-ark` | 诺亚方舟 | Noah's Ark | `NES` | 1992年 |
| 95 | `the-addams-family` | - | The Addams Family | `NES` | 1992年1月 / 1992年12月 |
| 96 | `the-addams-family-pugsley-s-scavenger-hunt` | - | The Addams Family: Pugsley's Scavenger Hunt | `NES` | 1993年8月 / 1992年 |
| 97 | `the-legend-of-prince-valiant` | - | The Legend of Prince Valiant | `NES` | 1992年 |
| 98 | `wheel-of-fortune-featuring-vanna-white` | 幸运之轮 凡娜·怀特版 | Wheel of Fortune: Featuring Vanna White | `NES` | 1992年1月 |
| 99 | `ganbare-goemon-gaiden-2-tenka-no-zaihou` | 大盗伍佑卫门外传2：天下的财宝 | Ganbare Goemon Gaiden 2 - Tenka no Zaihou | `FC` | 1992年1月3日 |
| 100 | `pizza-pop` | 批萨大战 | Pizza Pop! | `FC` | 1992年1月7日 |
| 101 | `taiyou-no-yuusha-fighbird` | 太阳勇者 | Taiyou no Yuusha Fighbird | `FC` | 1992年1月11日 |
| 102 | `business-wars` | 商场战争 | Business Wars | `FC` | 1992年1月24日 |
| 103 | `fire-n-ice` | 所罗门之钥2：库尔敏岛救出作战 | Fire 'n Ice | `FC/NES` | 1992年1月24日 / 1993年3月 / 1993年3月18日 |
| 104 | `the-bard-s-tale-2-the-destiny-knight` | 冰城传奇2：命运骑士 | The Bard's Tale 2 - The Destiny Knight | `FC` | 1992年1月25日 |
| 105 | `shougi-meikan-92` | 将棋名鉴92 | Shougi Meikan '92 | `FC` | 1992年1月30日 |
| 106 | `don-doko-don-2` | 木匠兄弟2 | Don Doko Don 2 | `FC` | 1992年1月31日 |
| 107 | `mr-gimmick` | 吉米克！ | Mr. Gimmick! | `FC/NES` | 1992年1月31日 / 1993年5月19日 |
| 108 | `f-15-strike-eagle` | F-15打击之鹰 | F-15 Strike Eagle | `NES` | 1992年2月 / 1993年2月18日 |
| 109 | `godzilla-2-war-of-the-monsters` | 哥斯拉 2 - 怪兽之战争 | Godzilla 2: War of the Monsters | `NES` | 1992年2月 |
| 110 | `m-c-kids` | 麦当劳小子 | M.C. Kids | `NES` | 1992年2月 / 1993年5月19日 |
| 111 | `sesame-street-countdown` | 芝麻街 - 倒计时 | Sesame Street: Countdown | `NES` | 1992年2月 |
| 112 | `star-trek-25th-anniversary` | 星舰迷航记 25周年纪念版 | Star Trek: 25th Anniversary | `NES` | 1992年2月 |
| 113 | `terminator-2-judgement-day` | 魔鬼终结者2 | Terminator 2 - Judgement Day | `FC/NES` | 1992年6月26日 / 1992年2月 |
| 114 | `f1-circus` | F1竞赛场 | F1 Circus | `FC` | 1992年2月7日 |
| 115 | `ike-ike-nekketsu-hockey-bu-subette-koronde-dai-rantou` | 热血曲棍球 | Ike Ike! Nekketsu Hockey Bu - Subette Koronde Dai Rantou | `FC` | 1992年2月7日 |
| 116 | `navy-blue` | 大海军战 | Navy Blue | `FC` | 1992年2月14日 |
| 117 | `advanced-dungeons-dragons-dragons-of-flame` | 龙与地下城：神龙之谜 | Advanced Dungeons & Dragons - Dragons of Flame | `FC` | 1992年2月21日 |
| 118 | `puzslot` | 帕青嫂 | Puzslot | `FC` | 1992年2月28日 |
| 119 | `fisher-price-firehouse-rescue` | 营救消防站 | Fisher-Price: Firehouse Rescue | `NES` | 1992年3月 |
| 120 | `g-i-joe-the-atlantis-factor` | G.I.JOE - 特种部队 | G.I. Joe: The Atlantis Factor | `NES` | 1992年3月 |
| 121 | `ghoul-school` | 幽灵学校 | Ghoul School | `NES` | 1992年3月 |
| 122 | `star-wars-the-empire-strikes-back` | 星球大战：帝国大反击 | Star Wars: The Empire Strikes Back | `FC/NES` | 1993年3月12日 / 1992年3月 |
| 123 | `town-country-ii-thrilla-s-surfari` | - | Town & Country II: Thrilla's Surfari | `NES` | 1992年3月 |
| 124 | `wizards-warriors-iii-kuros-visions-of-power` | 巫术 3 - 看见力量 | Wizards & Warriors III: Kuros: Visions of Power | `NES` | 1992年3月 / 1993年1月21日 |
| 125 | `the-magic-candle` | 魔烛 | The Magic Candle | `FC` | 1992年3月6日 |
| 126 | `utsurun-desu` | 传染总动员 | Utsurun Desu | `FC` | 1992年3月6日 |
| 127 | `igo-shinan-92` | 围棋指南92 | Igo Shinan '92 | `FC` | 1992年3月10日 |
| 128 | `namco-classic-2` | 南梦宫高尔夫2 | Namco Classic 2 | `FC` | 1992年3月13日 |
| 129 | `fire-emblem-gaiden` | 火焰之纹章外传 | Fire Emblem Gaiden | `FC` | 1992年3月14日 |
| 130 | `kyuukyoku-harikiri-koushien` | 究极甲子园 | Kyuukyoku Harikiri Koushien | `FC` | 1992年3月19日 |
| 131 | `soreike-anpanman-minna-de-hiking-game` | 徒步旅行游戏：面包超人 | Soreike! Anpanman - Minna de Hiking Game! | `FC` | 1992年3月20日 |
| 132 | `super-momotarou-dentetsu` | 超级桃太郎电铁 | Super Momotarou Dentetsu | `FC` | 1992年3月20日 |
| 133 | `hello-kitty-world` | 凯蒂猫世界 | Hello Kitty World | `FC` | 1992年3月27日 |
| 134 | `hook` | 虎克船长 | Hook | `FC/NES` | 1992年3月27日 / 1992年4月 |
| 135 | `plasma-ball` | 机器人弹珠柜 | Plasma Ball | `FC` | 1992年3月27日 |
| 136 | `honoo-no-toukyuuji-dodge-danpei` | 火炎斗球儿弹平 | Honoo no Toukyuuji - Dodge Danpei | `FC` | 1992年3月28日 |
| 137 | `aces-iron-eagle-3` | 铁鹰战士 | Aces - Iron Eagle 3 | `FC/NES` | 1992年8月7日 / 1992年4月 |
| 138 | `paperboy-2` | 送报童 2 | Paperboy 2 | `NES` | 1992年4月 |
| 139 | `the-mutant-virus-crisis-in-a-computer-world` | - | The Mutant Virus: Crisis in a Computer World | `NES` | 1992年4月 |
| 140 | `toxic-crusaders` | 毒魔侠 | Toxic Crusaders | `NES` | 1992年4月 |
| 141 | `wizardry-ii-the-knight-of-diamonds` | 巫术II：钻石骑士 | Wizardry II: The Knight of Diamonds | `NES` | 1992年4月 |
| 142 | `masuzoe-youichi-asa-made-famicom` | 舛添要一 | Masuzoe Youichi - Asa Made Famicom | `FC` | 1992年4月17日 |
| 143 | `play-school-soft-hirake-ponkikki` | 幼儿教育软体：打开吧！朋基基 | Play School Soft - Hirake! Ponkikki | `FC` | 1992年4月17日 |
| 144 | `panic-restaurant` | 小厨师 | Panic Restaurant | `FC/NES` | 1992年4月24日 / 1992年8月 / 1994年5月26日 |
| 145 | `hyokkori-hyoutan-jima-nazo-no-kaizokusen` | 葫芦岛之旅 | Hyokkori Hyoutan Jima - Nazo no Kaizokusen | `FC` | 1992年4月25日 |
| 146 | `clu-clu-land-welcome-to-new-cluclu-land` | 豆豆迷魂阵 | Clu Clu Land - Welcome to New Cluclu Land | `FDS` | 1992年4月28日 |
| 147 | `race-america` | - | Race America | `NES` | 1992年5月 |
| 148 | `roundball-2-on-2-challenge` | 二对二篮球挑战赛 | Roundball: 2 on 2 Challenge | `NES` | 1992年5月 |
| 149 | `mahjong-taisen` | 麻将大战 | Mahjong Taisen | `FC` | 1992年5月20日 |
| 150 | `project-q` | 猜谜项目Q | Project Q | `FC` | 1992年5月29日 |
| 151 | `day-dreamin-davey` | 大卫之幻想历险记 | Day Dreamin' Davey | `NES` | 1992年6月 |
| 152 | `disney-s-darkwing-duck` | - | Disney's Darkwing Duck | `NES` | 1992年6月 / 1993年12月9日 |
| 153 | `ferrari-grand-prix-challenge` | 法拉利大赛车 | Ferrari Grand Prix Challenge | `FC/NES` | 1992年11月13日 / 1992年6月 / 1992年6月 |
| 154 | `king-s-quest-v-absence-makes-the-heart-go-yonder` | - | King's Quest V: Absence Makes the Heart Go Yonder! | `NES` | 1992年6月 |
| 155 | `power-punch-ii` | 威力拳击 2 | Power Punch II | `NES` | 1992年6月 |
| 156 | `capcom-s-gold-medal-challenge-92` | 巴塞罗那奥运92 | Capcom's Gold Medal Challenge '92 | `FC/NES` | 1992年6月5日 / 1992年8月 / 1993年6月17日 |
| 157 | `sangokushi-2-haou-no-tairiku` | 三国志II 霸王的大陆 | Sangokushi 2 - Haou no Tairiku | `FC` | 1992年6月10日 |
| 158 | `magical-taruruuto-kun-2-mahou-dai-bouken` | 魔法台风2 | Magical Taruruuto Kun 2 - Mahou Dai Bouken | `FC` | 1992年6月19日 |
| 159 | `crash-n-the-boys-street-challenge` | 热血新纪录 | Crash 'n the Boys: Street Challenge | `FC/NES` | 1992年6月26日 / 1992年10月 |
| 160 | `esper-dream-2-aratanaru-tatakai` | 小超人2：新的战斗 | Esper Dream 2 - Aratanaru Tatakai | `FC` | 1992年6月26日 |
| 161 | `little-samson` | 圣铃传说 | Little Samson | `FC/NES` | 1992年6月26日 / 1992年11月 / 1993年3月18日 |
| 162 | `seiryaku-simulation-inbou-no-wakusei-shancara` | 阴谋惑星 | Seiryaku Simulation - Inbou no Wakusei - Shancara | `FC` | 1992年6月26日 |
| 163 | `advanced-dungeons-dragons-dragonstrike` | 高级地下城与龙 - 龙击 | Advanced Dungeons & Dragons: DragonStrike | `NES` | 1992年7月 |
| 164 | `baseball-stars-2` | - | Baseball Stars 2 | `NES` | 1992年7月 |
| 165 | `defenders-of-dynatron-city` | 城市保卫战 | Defenders of Dynatron City | `NES` | 1992年7月 |
| 166 | `greg-norman-s-golf-power` | 葛瑞诺曼的威力高尔夫 | Greg Norman's Golf Power | `NES` | 1992年7月 |
| 167 | `the-golf-92` | 高尔夫92 | The Golf '92 | `FC` | 1992年7月3日 |
| 168 | `mitsume-ga-tooru` | 三目童子 | Mitsume ga Tooru | `FC` | 1992年7月17日 |
| 169 | `red-ariimaa-2` | 红魔冒险II/魔界村外传 | Red Ariimaa 2 | `FC` | 1992年7月17日 |
| 170 | `sanrio-cup-pon-pon-volley` | 动物排球赛/三立鸥杯排球赛 | Sanrio Cup - Pon Pon Volley | `FC` | 1992年7月17日 |
| 171 | `summer-carnival-92-recca` | 夏日嘉年华'92 烈火 | Summer Carnival '92 - Recca | `FC` | 1992年7月17日 |
| 172 | `pachinko-dai-sakusen-2` | 柏青哥大作战2 | Pachinko Dai Sakusen 2 | `FC` | 1992年7月19日 |
| 173 | `kick-off` | 足球 | Kick Off | `NES` | 1992年7月22日 |
| 174 | `silva-saga` | 魔界佣兵 | Silva Saga | `FC` | 1992年7月24日 |
| 175 | `toukon-club` | 斗魂俱乐部 | Toukon Club | `FC` | 1992年7月24日 |
| 176 | `mahou-no-princess-minky-momo-remember-dream` | 魔法公主 | Mahou no Princess Minky Momo - Remember Dream | `FC` | 1992年7月29日 |
| 177 | `adventure-island-3` | 高桥名人之冒险岛III | Adventure Island 3 | `FC/NES` | 1992年7月31日 / 1992年9月 |
| 178 | `danny-sullivan-s-indy-heat` | 丹尼苏利凡之印地赛车 | Danny Sullivan's Indy Heat | `NES` | 1992年8月 |
| 179 | `robocop-3` | 机器战警 3 | RoboCop 3 | `NES` | 1992年8月 / 1994年7月28日 |
| 180 | `dragon-ball-z-3-ressen-jinzou-ningen` | 七龙珠ZIII 烈战人造人 | Dragon Ball Z 3 - Ressen Jinzou Ningen | `FC` | 1992年8月7日 |
| 181 | `gimmi-a-break-shijou-saikyou-no-quiz-ou-ketteisen-2` | 史上最强问题王2 | Gimmi a Break - Shijou Saikyou no Quiz Ou Ketteisen 2 | `FC` | 1992年8月28日 |
| 182 | `moon-crystal` | 月水晶 | Moon Crystal | `FC` | 1992年8月28日 |
| 183 | `derby-stallion-zenkoku-ban` | 德贝赛马全国版 | Derby Stallion - Zenkoku Ban | `FC` | 1992年8月29日 |
| 184 | `contra-force` | 魂斗罗 Force | Contra Force | `NES` | 1992年9月 |
| 185 | `krusty-s-fun-house` | 辛普森一家 - 超级欢乐屋 | Krusty's Fun House | `NES` | 1992年9月 |
| 186 | `the-blues-brothers` | - | The Blues Brothers | `NES` | 1992年9月 |
| 187 | `wwf-wrestlemania-steel-cage-challenge` | WWF摔跤 - 铁笼挑战赛 | WWF WrestleMania: Steel Cage Challenge | `NES` | 1992年9月 |
| 188 | `1999-hore-mitakotoka-seikimatsu` | 1999世纪末 | 1999 - Hore, Mitakotoka! Seikimatsu | `FC` | 1992年9月18日 |
| 189 | `dream-master` | 梦境之王 | Dream Master | `FC` | 1992年9月22日 |
| 190 | `power-blade-2` | 救助上尉 | Power Blade 2 | `FC/NES` | 1992年9月29日 / 1992年10月 |
| 191 | `mickey-mouse-3-yume-fuusen` | 米老鼠3 | Mickey Mouse 3 - Yume Fuusen | `FC/NES` | 1992年9月30日 / 1993年4月 |
| 192 | `felix-the-cat` | 菲力猫 | Felix the Cat | `NES` | 1992年10月 |
| 193 | `gargoyle-s-quest-ii` | 石像鬼之谜 2 | Gargoyle's Quest II | `NES` | 1992年10月 / 1993年6月17日 |
| 194 | `home-alone-2-lost-in-new-york` | 小鬼当家 2 - 纽约迷途记 | Home Alone 2: Lost in New York | `NES` | 1992年10月 |
| 195 | `legend-of-the-ghost-lion` | - | Legend of the Ghost Lion | `NES` | 1992年10月 |
| 196 | `spider-man-return-of-the-sinister-six` | 蜘蛛人 - 凶恶六人组的复仇 | Spider-Man: Return of the Sinister Six | `NES` | 1992年10月 |
| 197 | `stanley-the-search-for-dr-livingston` | 大探险家史丹立 - 李文斯顿的足迹追踪 | Stanley: The Search for Dr. Livingston | `NES` | 1992年10月 |
| 198 | `shaffle-fight` | 英雄大战 | Shaffle Fight | `FC` | 1992年10月9日 |
| 199 | `best-play-pro-yakyuu-special` | 亚斯基职业棒球特别版 | Best Play Pro Yakyuu Special | `FC` | 1992年10月16日 |
| 200 | `top-striker` | 顶级足球员 | Top Striker | `FC` | 1992年10月22日 |
| 201 | `sd-gundam-gaiden-knight-gundam-monogatari-3-densetsu-no` | SD钢弹外传3：骑士钢弹物语 | SD Gundam Gaiden - Knight Gundam Monogatari 3 - Densetsu no | `FC` | 1992年10月23日 |
| 202 | `double-moon-densetsu` | 变月传说 | Double Moon Densetsu | `FC` | 1992年10月30日 |
| 203 | `james-bond-jr` | 少年詹姆斯·庞德 | James Bond Jr. | `NES` | 1992年11月 |
| 204 | `lemmings` | 百战小旅鼠 | Lemmings | `NES` | 1992年11月 / 1993年5月19日 |
| 205 | `prince-of-persia` | 波斯王子 | Prince of Persia | `NES` | 1992年11月 / 1993年4月29日 |
| 206 | `tecmo-nba-basketball` | Tecmo美国职篮 | Tecmo NBA Basketball | `NES` | 1992年11月 |
| 207 | `widget` | 威奇精灵 | Widget | `NES` | 1992年11月 |
| 208 | `kyouryuu-sentai-juuranger` | 恐龙战队 | Kyouryuu Sentai Juuranger | `FC` | 1992年11月6日 |
| 209 | `columbus-ougon-no-yoake` | 哥伦布传：黄金的拂晓 | Columbus - Ougon no Yoake | `FC` | 1992年11月20日 |
| 210 | `igo-shinan-93` | 围棋指南93 | Igo Shinan '93 | `FC` | 1992年11月20日 |
| 211 | `yoshi-s-cookie` | 耀西的饼干 | Yoshi's Cookie | `FC/NES` | 1992年11月21日 / 1993年4月 / 1994年4月28日 |
| 212 | `tiny-toon-adventures-2-montana-land-he-youkoso` | 兔宝宝历险记2 | Tiny Toon Adventures 2 - Montana Land he Youkoso | `FC/NES` | 1992年11月27日 / 1993年4月 / 1994年1月27日 |
| 213 | `best-of-the-best-championship-karate` | 精英份子 - 自由搏击冠军赛 | Best of the Best: Championship Karate | `NES` | 1992年12月 |
| 214 | `caesars-palace` | 凯萨宫大饭店 | Caesars Palace | `NES` | 1992年12月 |
| 215 | `f-117a-stealth-fighter` | F-117A战斗机 | F-117A Stealth Fighter | `NES` | 1992年12月 |
| 216 | `george-foreman-s-ko-boxing` | 乔治福尔曼的击倒拳击 | George Foreman's KO Boxing | `NES` | 1992年12月 / 1992年12月 |
| 217 | `joe-mac` | 战斗原始人 | Joe & Mac | `NES` | 1992年12月 |
| 218 | `mega-man-5` | 洛克人5 布鲁斯的陷阱！？ | Mega Man 5 | `FC/NES` | 1992年12月4日 / 1992年12月 / 1993年11月18日 |
| 219 | `r-c-pro-am-ii` | 遥控车混合赛 2 | R.C. Pro-Am II | `NES` | 1992年12月 / 1993年9月23日 |
| 220 | `swamp-thing` | 沼泽怪 | Swamp Thing | `NES` | 1992年12月 |
| 221 | `the-adventures-of-rocky-and-bullwinkle-and-friends` | - | The Adventures of Rocky and Bullwinkle and Friends | `NES` | 1992年12月 |
| 222 | `the-great-waldo-search` | - | The Great Waldo Search | `NES` | 1992年12月 |
| 223 | `the-jetsons-cogswell-s-caper` | 杰森一家 | The Jetsons: Cogswell's Caper! | `FC/NES` | 1993年4月23日 / 1992年12月 / 1993年8月26日 |
| 224 | `the-simpsons-bartman-meets-radioactive-man` | 辛普森一家 巴特侠大战放射人 | The Simpsons: Bartman Meets Radioactive Man | `NES` | 1992年12月 |
| 225 | `the-terminator` | - | The Terminator | `NES` | 1992年12月 |
| 226 | `tiny-toon-adventures-cartoon-workshop` | 兔宝宝大冒险 - 卡通工作室 | Tiny Toon Adventures Cartoon Workshop | `NES` | 1992年12月 |
| 227 | `young-indiana-jones-chronicles` | 少年印第安纳琼斯大冒险 | Young Indiana Jones Chronicles | `NES` | 1992年12月 |
| 228 | `chiisana-obake-acchi-socchi-kocchi` | 小小妖怪阿奇、柯奇、索奇 | Chiisana Obake - Acchi Socchi Kocchi | `FC` | 1992年12月4日 |
| 229 | `shougi-meikan-93` | 将棋名鉴93 | Shougi Meikan '93 | `FC` | 1992年12月4日 |
| 230 | `wagan-land-3` | 瓦强世界3 | Wagan Land 3 | `FC` | 1992年12月8日 |
| 231 | `hello-kitty-no-ohanabatake` | 凯蒂猫的花园 | Hello Kitty no Ohanabatake | `FC` | 1992年12月11日 |
| 232 | `rod-land` | 妖精物语 | Rod Land | `FC/NES` | 1992年12月11日 / 1993年 |
| 233 | `just-breed` | 光荣圣战 | Just Breed | `FC` | 1992年12月15日 |
| 234 | `barcode-world` | 条码世界 | Barcode World | `FC` | 1992年12月18日 |
| 235 | `famimaga-disk-vol-6-janken-disk-jou` | 法米杂志软盘系列06：软盘之城 | Famimaga Disk Vol. 6 - Janken Disk Jou | `FDS` | 1992年12月22日 |
| 236 | `famista-93` | 明星职棒93年度版 | Famista '93 | `FC` | 1992年12月22日 |
| 237 | `sd-gundam-gachapon-senshi-5-battle-of-universal-century` | SD钢弹扭蛋战士5：宇宙世纪的战斗 | SD Gundam - Gachapon Senshi 5 - Battle of Universal Century | `FC` | 1992年12月22日 |
| 238 | `nekketsu-kakutou-densetsu` | 热血格斗传说 | Nekketsu Kakutou Densetsu | `FC` | 1992年12月23日 |
| 239 | `aa-yakyuu-jinsei-icchokusen` | 野球人生 | Aa! Yakyuu Jinsei Icchokusen | `FC` | 1992年12月25日 |
| 240 | `great-battle-cyber` | 英雄挑战 | Great Battle Cyber | `FC` | 1992年12月25日 |
| 241 | `ultraman-club-kaijuu-dai-kessen` | 怪兽超人俱乐部：怪兽大决战 | Ultraman Club - Kaijuu Dai Kessen! | `FC` | 1992年12月25日 |
| 242 | `datach-dragon-ball-z-gekitou-tenkaichi-budou-kai` | 读卡机系列：七龙珠Z-天下武道会 | Datach - Dragon Ball Z - Gekitou Tenkaichi Budou Kai | `FC` | 1992年12月29日 |
| 243 | `alfred-chicken` | 神鸡艾烈佛 | Alfred Chicken | `NES` | 1994年2月 / 1993年 |
| 244 | `asterix` | 美丽新世界 | Asterix | `NES` | 1993年 |
| 245 | `batman-returns` | 蝙蝠侠 3 - 大显神威 | Batman Returns | `NES` | 1993年1月 |
| 246 | `battleship` | 海战风云 | Battleship | `NES` | 1993年9月 / 1993年 |
| 247 | `break-time-the-national-pool-tour` | 休闲时间 - 全国撞球巡回赛 | Break Time: The National Pool Tour | `NES` | 1993年1月 |
| 248 | `f-1-sensation` | F1赛车 | F-1 Sensation | `FC/NES` | 1993年1月29日 / 1993年 |
| 249 | `overlord` | 领主之战 | Overlord | `NES` | 1993年1月 |
| 250 | `rackets-rivals` | 网球联赛 | Rackets & Rivals | `NES` | 1993年 |
| 251 | `ultima-v-warriors-of-destiny` | - | Ultima V: Warriors of Destiny | `NES` | 1993年1月 |
| 252 | `sanrio-carnival-2` | 动物方块2/三立鸥嘉年华会2 | Sanrio Carnival 2 | `FC` | 1993年1月14日 |
| 253 | `wily-light-no-rockboard-that-s-paradise` | 洛克人大富翁 | Wily & Light no Rockboard - That's Paradise | `FC` | 1993年1月15日 |
| 254 | `kamen-rider-sd-guranshokkaa-no-yabou` | SD假面骑士 | Kamen Rider SD - Guranshokkaa no Yabou | `FC` | 1993年1月22日 |
| 255 | `rollerblade-racer` | 直排轮大挑战 | Rollerblade Racer | `NES` | 1993年2月 |
| 256 | `battle-baseball` | 战斗棒球 | Battle Baseball | `FC` | 1993年2月19日 |
| 257 | `kero-kero-keroppi-no-dai-bouken-2-donuts-ike-ha-oosawagi` | 青蛙大冒险 | Kero Kero Keroppi no Dai Bouken 2 - Donuts Ike ha Oosawagi | `FC` | 1993年2月19日 |
| 258 | `alien3` | 异形 3 | Alien3 | `NES` | 1993年3月 |
| 259 | `mickey-s-safari-in-letterland` | 米老鼠之字母岛大冒险 | Mickey's Safari in Letterland | `NES` | 1993年3月 |
| 260 | `zen-the-intergalactic-ninja` | - | Zen the Intergalactic Ninja | `NES` | 1993年3月 |
| 261 | `bubble-bobble-part-2` | 泡泡龙2 | Bubble Bobble Part 2 | `FC/NES` | 1993年3月5日 / 1993年8月 |
| 262 | `mezase-top-pro-green-ni-kakeru-yume` | 职业高尔夫 | Mezase Top Pro - Green ni Kakeru Yume | `FC` | 1993年3月5日 |
| 263 | `pro-sport-hockey` | 美式曲棍球 | Pro Sport Hockey | `FC/NES` | 1993年3月6日 / 1993年11月 |
| 264 | `casino-derby` | 竞马大赛场 | Casino Derby | `FC` | 1993年3月19日 |
| 265 | `pyokotan-no-dai-meiro` | 大迷路 | Pyokotan no Dai Meiro | `FC` | 1993年3月19日 |
| 266 | `kirby-s-adventure` | 星之卡比 梦之泉物语 | Kirby's Adventure | `FC/NES` | 1993年3月23日 / 1993年5月 / 1993年12月9日 |
| 267 | `aoki-ookami-to-shiroki-mejika-genchou-hishi` | 苍狼与白鹿 元朝秘史 | Aoki Ookami to Shiroki Mejika - Genchou Hishi | `FC` | 1993年3月25日 |
| 268 | `ai-sensei-no-oshiete-watashi-no-hoshi` | 爱先生 | Ai Sensei no Oshiete - Watashi no Hoshi | `FC` | 1993年3月26日 |
| 269 | `honoo-no-toukyuuji-dodge-danpei-2` | 火炎斗球儿-弹平2 | Honoo no Toukyuuji - Dodge Danpei 2 | `FC` | 1993年3月26日 |
| 270 | `kaiketsu-yanchamaru-3-taiketsu-zouringen` | 快杰洋枪3 | Kaiketsu Yanchamaru 3 - Taiketsu! Zouringen | `FC` | 1993年3月30日 |
| 271 | `casino-kid-2` | - | Casino Kid 2 | `NES` | 1993年4月 |
| 272 | `lethal-weapon` | 致命武器 | Lethal Weapon | `NES` | 1993年4月 |
| 273 | `datach-sd-gundam-gundam-wars` | 读卡机系列：SD钢弹-钢弹大战 | Datach - SD Gundam - Gundam Wars | `FC` | 1993年4月23日 |
| 274 | `datach-ultraman-club-supokon-fight` | 读卡机系列：超人俱乐部 | Datach - Ultraman Club - Supokon Fight! | `FC` | 1993年4月23日 |
| 275 | `ducktales-2` | 唐老鸭梦冒险2 | DuckTales 2 | `FC/NES` | 1993年4月23日 / 1993年6月 / 1993年11月18日 |
| 276 | `kunio-kun-no-nekketsu-soccer-league` | 热血足球2 | Kunio Kun no Nekketsu Soccer League | `FC` | 1993年4月23日 |
| 277 | `gorilla-man` | 猩猩男 | Gorilla Man | `FC` | 1993年4月28日 |
| 278 | `joy-mecha-fight` | 机器人战斗 | Joy Mecha Fight | `FC` | 1993年5月21日 |
| 279 | `battletoads-double-dragon` | 忍者蛙与双截龙 | Battletoads & Double Dragon | `NES` | 1993年6月 |
| 280 | `cool-world` | 美女闯天关 | Cool World | `NES` | 1993年6月 |
| 281 | `jurassic-park` | 侏罗纪公园 | Jurassic Park | `NES` | 1993年6月 / 1993年12月28日 |
| 282 | `mighty-final-fight` | Mighty 快打旋风 | Mighty Final Fight | `FC/NES` | 1993年6月11日 / 1993年7月 |
| 283 | `pachio-kun-5` | 帕青夫君5 | Pachio Kun 5 | `FC` | 1993年6月18日 |
| 284 | `j-league-fighting-soccer-the-king-of-ace-strikers` | J联盟战斗足球 | J League Fighting Soccer - The King of Ace Strikers | `FC` | 1993年6月19日 |
| 285 | `color-a-dinosaur` | 恐龙着色家 | Color a Dinosaur | `NES` | 1993年7月 |
| 286 | `mario-is-missing` | 失踪马里奥 | Mario Is Missing! | `NES` | 1993年7月 |
| 287 | `ushio-to-tora-shinen-no-daiyou` | 魔力大马：深渊的大妖 | Ushio to Tora - Shinen no Daiyou | `FC` | 1993年7月9日 |
| 288 | `super-turrican` | 超级星际战士 | Super Turrican | `NES` | 1993年7月22日 |
| 289 | `puyo-puyo` | 魔法气泡 | Puyo Puyo | `FC` | 1993年7月23日 |
| 290 | `bonk-s-adventure` | FC原人 | Bonk's Adventure | `FC/NES` | 1993年7月30日 / 1994年1月 |
| 291 | `kouryuu-densetsu-villgust-gaiden` | 甲龙传说外传 | Kouryuu Densetsu Villgust Gaiden | `FC` | 1993年7月30日 |
| 292 | `dragon-ball-z-gaiden-saiya-jin-zetsumetsu-keikaku` | 七龙珠Z外传 赛亚人灭绝计划 | Dragon Ball Z Gaiden - Saiya Jin Zetsumetsu Keikaku | `FC` | 1993年8月6日 |
| 293 | `crayon-shin-chan-ora-to-poi-poi` | 蜡笔小新 | Crayon Shin Chan - Ora to Poi Poi | `FC` | 1993年8月27日 |
| 294 | `datach-crayon-shin-chan-ora-to-poi-poi` | 读卡机系列：蜡笔小新 | Datach - Crayon Shin Chan - Ora to Poi Poi | `FC` | 1993年8月27日 |
| 295 | `bram-stoker-s-dracula` | 吸血鬼德古拉 | Bram Stoker's Dracula | `NES` | 1993年9月 |
| 296 | `star-trek-the-next-generation` | 星舰迷航记 - 银河飞龙 | Star Trek: The Next Generation | `NES` | 1993年9月 |
| 297 | `pachi-slot-adventure-2-sorotta-kun-no-pachi-slot-tanteidan` | 帕青哥冒险2 | Pachi Slot Adventure 2 - Sorotta Kun no Pachi Slot Tanteidan | `FC` | 1993年9月17日 |
| 298 | `tetris-2` | 俄罗斯方块Flash | Tetris 2 | `FC/NES` | 1993年9月21日 / 1993年10月 |
| 299 | `championship-pool` | 撞球锦标赛 | Championship Pool | `NES` | 1993年10月 |
| 300 | `last-action-hero` | 最后魔鬼英雄 | Last Action Hero | `NES` | 1993年10月 |
| 301 | `nigel-mansell-s-world-championship-racing` | 尼基·曼赛尔之世界锦标赛 | Nigel Mansell's World Championship Racing | `NES` | 1993年10月 |
| 302 | `the-incredible-crash-dummies` | - | The Incredible Crash Dummies | `NES` | 1994年8月 / 1993年10月21日 |
| 303 | `daiku-no-gen-san-2-akage-no-dan-no-gyakushuu` | 大力工头2：红毛丹的反击 | Daiku no Gen San 2 - Akage no Dan no Gyakushuu | `FC` | 1993年10月22日 |
| 304 | `datach-yuu-yuu-hakusho-bakutou-ankoku-bujutsu-kai` | 读卡机系列：幽游白书爆斗暗黑武术会 | Datach - Yuu Yuu Hakusho - Bakutou Ankoku Bujutsu Kai | `FC` | 1993年10月22日 |
| 305 | `rokudenashi-blues` | 铁拳对钢拳 | Rokudenashi Blues | `FC` | 1993年10月29日 |
| 306 | `cliffhanger` | 巅峰战士 | Cliffhanger | `NES` | 1993年11月 |
| 307 | `jimmy-connors-tennis` | 吉米康诺网球 | Jimmy Connors Tennis | `NES` | 1993年11月 |
| 308 | `ms-pac-man` | 吃豆人小姐 | Ms. Pac-Man | `NES` | 1993年11月 |
| 309 | `the-ren-stimpy-show-buckaroo` | - | The Ren & Stimpy Show: Buckaroo$! | `NES` | 1993年11月 |
| 310 | `wayne-s-world` | 反斗智多星 | Wayne's World | `NES` | 1993年11月 |
| 311 | `wwf-king-of-the-ring` | 世界摔角联盟 - 冠军之路 | WWF King of the Ring | `NES` | 1993年11月 |
| 312 | `mega-man-6` | 洛克人6 史上最大战争！！ | Mega Man 6 | `FC/NES` | 1993年11月5日 / 1994年3月 |
| 313 | `datach-battle-rush-build-up-robot-tournament` | 读卡机系列：机器人大战 | Datach - Battle Rush - Build Up Robot Tournament | `FC` | 1993年11月13日 |
| 314 | `rpg-jinsei-game` | 人生游戏 | RPG Jinsei Game | `FC` | 1993年11月26日 |
| 315 | `famista-94` | 明星职棒94年度版 | Famista '94 | `FC` | 1993年12月1日 |
| 316 | `indiana-jones-and-the-last-crusade-1` | 印地安纳琼斯 - 圣战奇兵 | Indiana Jones and the Last Crusade | `NES` | 1993年12月 |
| 317 | `keroppi-to-keroriinu-no-splash-bomb` | 青蛙方块 | Keroppi to Keroriinu no Splash Bomb! | `FC` | 1993年12月1日 |
| 318 | `chip-n-dale-rescue-rangers-2` | 松鼠大作战2 | Chip 'n Dale Rescue Rangers 2 | `FC/NES` | 1993年12月10日 / 1994年1月 / 1994年9月29日 |
| 319 | `nakayoshi-to-issho` | 和月野兔在一起 | Nakayoshi to Issho | `FC` | 1993年12月10日 |
| 320 | `igo-shinan-94` | 围棋指南94 | Igo Shinan '94 | `FC` | 1993年12月17日 |
| 321 | `momotarou-densetsu-gaiden` | 桃太郎传说外传 | Momotarou Densetsu Gaiden | `FC` | 1993年12月17日 |
| 322 | `nekketsu-street-basket-ganbare-dunk-heroes` | 热血篮球 | Nekketsu! Street Basket - Ganbare Dunk Heroes | `FC` | 1993年12月22日 |
| 323 | `disney-s-beauty-and-the-beast` | 美女与野兽 | Disney's Beauty and the Beast | `NES` | 1994年 |
| 324 | `the-smurfs` | 蓝精灵 | The Smurfs | `NES` | 1994年 |
| 325 | `teenage-mutant-ninja-turtles-tournament-fighters` | 忍者神龟 - 格斗大会 | Teenage Mutant Ninja Turtles: Tournament Fighters | `NES` | 1994年2月 |
| 326 | `wario-s-woods` | 瓦力欧之森 | Wario's Woods | `FC/NES` | 1994年2月19日 / 1994年12月10日 / 1995年 |
| 327 | `the-flintstones-surprise-at-dinosaur-peak` | - | The Flintstones: Surprise at Dinosaur Peak | `NES` | 1994年8月 / 1994年2月24日 |
| 328 | `final-fantasy-1-2` | 最终幻想I·II合辑 | Final Fantasy 1 & 2 | `FC` | 1994年2月27日 |
| 329 | `mickey-s-adventures-in-numberland` | - | Mickey's Adventures in Numberland | `NES` | 1994年3月 |
| 330 | `zoda-s-revenge-startropics-ii` | 佐达的复仇 - 热带之星 2 | Zoda's Revenge: StarTropics II | `NES` | 1994年3月 |
| 331 | `datach-j-league-super-top-players` | 读卡机系列：J联盟足球 | Datach - J League Super Top Players | `FC` | 1994年4月22日 |
| 332 | `pachi-slot-adventure-3-bitaoshii-7-kenzan` | 帕青哥冒险3 | Pachi Slot Adventure 3 - Bitaoshii 7 Kenzan! | `FC` | 1994年5月13日 |
| 333 | `j-league-winning-goal` | J联盟足球 | J League Winning Goal | `FC` | 1994年5月27日 |
| 334 | `mario-s-time-machine` | 马里奥的时光机器 | Mario's Time Machine | `NES` | 1994年6月 |
| 335 | `takahashi-meijin-no-boukenjima-4` | 高桥名人之冒险岛IV | Takahashi Meijin no Boukenjima 4 | `FC` | 1994年6月24日 |
| 336 | `disney-s-the-jungle-book` | - | Disney's The Jungle Book | `NES` | 1994年8月 / 1994年8月25日 |
| 337 | `disney-s-aladdin` | - | Disney's Aladdin | `NES` | 1995年2月23日 |
| 338 | `disney-s-the-lion-king` | - | Disney's The Lion King | `NES` | 1995年5月25日 |

</details>
