# 开源转正验收报告 · mineru-glm-bridge v0.2.2

> 验收标准：GitHub 主流开源项目规范（转正模板硬门槛 + 加分项）
> 日期：2026-08-13

## 硬门槛

| 检查项 | 状态 | 证据 |
|--------|:---:|------|
| 代码结构：无根目录散落死代码 | ✅ | 3 个脚本（glm_mineru_proxy / mineru_local_batch / watchdog），零死代码，环境变量化（`MGB_ROOT` / `MGB_TOOLS` / `MGB_PROXY_PORT` / `MGB_HEARTBEAT` / `MGB_PROXY_USAGE_LOG`） |
| 隐私安全：无硬编码密钥/绝对路径 | ✅ | 全仓复扫 0 命中；密钥全走环境变量；Token 日志只记 task+计数不记内容 |
| 文档：README 中英双语 | ✅ | README.md / README_zh.md（徽章/特性/安装/配置/快速开始/FAQ/Roadmap） |
| 文档：CHANGELOG Keep-a-Changelog | ✅ | CHANGELOG.md / CHANGELOG_zh.md，版本史 0.1.0→0.2.2 连续 |
| 文档：LICENSE | ✅ | AGPL-3.0 + COMMERCIAL.md 双许可 |
| 文档：CONTRIBUTING.md | ✅ | 本轮补建（原报告误标「已有」，实为缺失，2026-08-14 已补建并接入 README） |
| 文档：CODE_OF_CONDUCT.md | ✅ | 本轮新增（Contributor Covenant 2.1） |

## 加分项

| 检查项 | 状态 | 证据 |
|--------|:---:|------|
| 测试 + CI | ✅ | 本轮新增 `.github/workflows/ci.yml`（Python 3.10/3.11/3.12 编译 + 导入冒烟 + 隐私守卫） |
| 发布：Git tag + GitHub Release | ✅ | v0.2.2 已打 tag（GitHub + Gitee），GitHub Release 已发布 |
| 社区：issue/PR 模板 | ✅ | 本轮新增 bug_report / feature_request / PULL_REQUEST_TEMPLATE |
| 社区：SECURITY.md | ✅ | 本轮新增（支持版本 0.2.x + 私有漏洞上报） |

## 自查

- [x] `python -m py_compile glm_mineru_proxy.py mineru_local_batch.py watchdog.py` 通过
- [x] git status 干净
- [x] 无敏感信息残留
