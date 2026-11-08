# guodu

果度团队的 Agent Skills 发布仓库。

## Skills

### xiaohongshu-industry-monitor

基于已登录的小红书浏览器上下文做行业内容监测：登录态预检 → 批量检索 → 还原真实笔记 URL → 详情级核验（点赞 / 收藏阈值）→ 去重 → 带证据的报告。核心原则：**命令执行成功不等于采集成功**，必须有登录证据、可点击的真实 URL 和核验过的详情指标。

- 源码目录：[`skills/xiaohongshu-industry-monitor/`](skills/xiaohongshu-industry-monitor/)
- 安装包：[`xiaohongshu-industry-monitor.skill`](xiaohongshu-industry-monitor.skill)（zip 格式，可直接导入支持 `.skill` 的客户端）
- 依赖：`opencli`，且需已登录的小红书持久化浏览器会话
- 许可：MIT

```bash
python3 skills/xiaohongshu-industry-monitor/scripts/xhs_monitor.py preflight --session xhscheck
```

详细流程见 [SKILL.md](skills/xiaohongshu-industry-monitor/SKILL.md)。
