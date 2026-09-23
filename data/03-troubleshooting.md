# Atlas 示例系统：故障排查

本文档属于虚构的教学系统 Atlas。

## 连接超时
出现 CONNECTION_TIMEOUT 时，先检查数据库地址和网络连通性。
确认防火墙放行后，再检查 connect_timeout 参数，避免仅增加重试次数掩盖故障。

## 内存不足
发生 OUT_OF_MEMORY 时，将 batch_size 从默认的 100 调整为 20。
如果仍然失败，应检查是否加载了过大的文件。

## 端口冲突
出现 ADDRESS_IN_USE 时，检查默认的 8080 端口是否被其他进程占用。
