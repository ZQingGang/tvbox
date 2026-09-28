# 影视仓/TVBox 配置源 · 自动更新

一个**自己维护、定时自动爬取 + 校验 + 自动更新**的影视仓配置源项目。
最终产出 `tvbox.json`，把这个文件的 raw 直链填进影视仓「配置地址」即可。

## 文件说明

| 文件 | 作用 |
|---|---|
| `update_source.py` | 核心脚本：展开多仓、识别单仓、校验可达性、去重、生成 `tvbox.json`。仅用 Python 标准库，零第三方依赖 |
| `sources.txt` | **你日常维护的文件**：手动收藏/新增的源，每行 `名称,URL` 或纯 URL |
| `tvbox.json` | 脚本生成的最终源文件（影视仓里填这个） |
| `update.log` | 每次运行的校验日志 |
| `run_update.ps1` | 本机手动/计划任务执行入口（方案 B 用） |
| `.github/workflows/update.yml` | GitHub Actions 定时任务（方案 A 用，云端全自动） |

## 工作原理

```
种子多仓(SEED_HOUSES) + 自维护(sources.txt)
        ↓
逐层展开多仓(storeHouse/urls/TXT) → 识别叶子「单仓」(含 sites)
        ↓
逐一校验可达性 → 过滤失效源 → 去重
        ↓
生成标准 storeHouse 多仓 JSON → tvbox.json + update.log
```

- `SEED_HOUSES`（在 `update_source.py` 顶部）里放「种子多仓源」，维护者会持续更新其中的子源，脚本借此**自动发现新源**。
- `sources.txt` 里放你**手动锁定**的源（无论单仓多仓都保留）。

## 部署方案

### 方案 A（推荐 · 全云端自动，不依赖电脑开机）

1. **新建 GitHub 仓库**，把本项目所有文件推上去（`tvbox-source` 目录就是仓库根）。
2. GitHub → 仓库 → **Settings → Actions → General** → 勾选 *Read and write permissions*。
3. 到 **Actions** 页手动跑一次，确认生成/更新了 `tvbox.json`。
4. （可选双推到 Gitee）在仓库 **Settings → Secrets → Actions** 添加：
   - `GITEE_REPO`：如 `你的Gitee用户名/仓库名`
   - `GITEE_TOKEN`：Gitee 私人令牌（设置 → 私人令牌 → 生成，勾选 projects 权限）
   然后在 `update.yml` 里把「Push to Gitee」那一步取消注释。
5. 到 **Gitee** 新建同仓库（或用第 4 步的双推，或 Gitee「从 GitHub 导入」）。
6. 拿地址：
   - Gitee：`https://gitee.com/你的用户名/仓库名/raw/main/tvbox.json`
   - 直接 GitHub raw 也可（国内慢，可套 `https://ghproxy.com/` 前缀）。

### 方案 B（纯 Gitee · 靠本机定时）

1. Gitee 新建仓库，`git clone` 到本地。
2. 把本项目文件复制进仓库目录。
3. 测试：`powershell -ExecutionPolicy Bypass -File run_update.ps1`
4. 加 Windows 计划任务：
   ```
   schtasks /Create /SC DAILY /ST 06:00 /TN "TVBoxSourceUpdate" /TR "powershell -ExecutionPolicy Bypass -File C:\路径\run_update.ps1"
   ```
   （需要电脑在该时间点开机）

## 日常维护

- **想固定保留某个源** → 加一行到 `sources.txt`。
- **想接入新的种子多仓** → 在 `update_source.py` 顶部 `SEED_HOUSES` 加一条。
- **想改更新频率** → 改 `update.yml` 里的 cron（当前每 6 小时一次）。
- 每次更新后，Git 提交记录和 `update.log` 就是你的「更新历史」，可随时回滚。

## 注意

- 公开影视源**天然不稳定**，随时可能失效；本项目的意义就是**自动过滤失效源、持续保留可用源**。
- 请自行确认所收录源的合规性与使用权限，本项目仅做技术聚合。
