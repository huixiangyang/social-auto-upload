# Arc Home 上传引擎

维护仓库：[huixiangyang/social-auto-upload](https://github.com/huixiangyang/social-auto-upload)。部署分支：`arc-home`。基线：上游 `dreammis/social-auto-upload` 的 `1c66b7db4b30585bbb40c58eb0aa572ffa3cce97`，保留原许可证。

## 本次纳入的修复

- 抖音：按抖音域名检查登录会话，等待扫码与二次验证；验证码按账号隔离，要求文件权限 0600，不将验证码写入日志。
- 抖音：定时时间写入后回读；单次任务最多点击一次发布，180 秒未确认结果时报错，由工作台核对结果。
- 视频号：上传前检查 H.264、时长和码率；定时精确选择分钟并回读；等待服务端切片和提交结果，禁止循环点击发表。
- 视频号：定位当前可见的封面及裁剪弹窗，封面设置失败中止；原创声明只由显式参数启用。
- `ASSET_DIR` 指向源码中的静态资源；`SAU_BASE_DIR` 指定私有账号、日志和临时文件目录。

这些修复来自 X1 原有运行代码。本次将它们纳入版本管理，不代表重新完成了各平台真实发布验收。

## 运行约定

- 源码：`/opt/social-auto-upload`，以 root 管理，部署时固定完整提交号。
- CLI：`/opt/social-auto-upload/.venv/bin/sau`，沿用已安装的 Python 3.12 依赖和浏览器。
- 专用运行用户：`social-upload`。`SAU_BASE_DIR=/var/lib/social-auto-upload`，Cookie 留在其中的 `cookies` 子目录。
- 首次配置由 `conf.example.py` 生成 `conf.py`；现有 `conf.py` 是私有运行配置，更新时保留。
- Arc Home 通过 `arc-home-publisher.service` 的私有 socket 调用 CLI。账号、分组、任务和全部执行日志由工作台保存。
- 标准输出、错误输出与终端输出实时进入工作台运行日志；凭据和验证码在入库前脱敏。重试按执行次数保留历史。
- 不启动上游历史 Web 服务，不另开公网端口，不自动同步上游主线。

## 发布流程

1. 在本分支提交修改并完成必要检查；记录完整提交号。
2. 检查工作台无正在运行的登录、检查或发布任务，备份数据库、源码和运行配置；记录 Cookie 校验值。
3. 从本 fork 获取指定提交，确认工作区无未纳入版本管理的修改，再切换源码。已有 `.venv`、浏览器和账号目录保持原位。
4. 更新 Arc Home 的 `deploy/publisher/source.json`，安装器核对 fork 地址、提交号和干净工作区，不在生产源码上临时打补丁。
5. 重启分发服务，核对私有 socket、工作台接口和日志接口；比对账号、历史任务与 Cookie 校验值。

失败时切回部署前源码并重启分发服务；不以恢复旧数据库的方式丢弃部署后的用户操作。真实扫码或视频发布由用户从工作台主动触发。
