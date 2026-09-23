# Atlas 示例系统：安装指南

本文档属于虚构的教学系统 Atlas，不是任何真实产品的规格。

## 运行环境
Atlas 要求 Python 3.11 或更高版本。默认服务端口是 8080。
开发环境使用 SQLite，生产环境建议使用 PostgreSQL。

## 启动
配置文件为 atlas.toml，启动命令为 atlas serve。
健康检查路径为 /health。当数据库连接正常时，健康检查返回 ok。
