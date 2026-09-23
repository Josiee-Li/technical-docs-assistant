# Atlas 示例系统：权限与数据管理

本文档属于虚构的教学系统 Atlas。

reader 角色只能读取文档，editor 角色可以新增和修改文档。
admin 角色可以管理用户和删除文档。
生产环境访问服务必须携带 API token，token 通过环境变量 ATLAS_API_TOKEN 注入。
不要将 token 写入知识库文档或日志。审计日志保留 90 天。
