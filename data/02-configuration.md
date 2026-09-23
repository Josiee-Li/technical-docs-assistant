# Atlas 示例系统：配置参考

本文档属于虚构的教学系统 Atlas。

## 网络连接
connect_timeout 表示连接超时，默认值为 10 秒。
read_timeout 表示读取超时，默认值为 30 秒。
max_retries 表示失败后的最大重试次数，默认值为 3。
生产环境建议将 connect_timeout 调整为 20 秒。

## 环境差异
开发环境日志级别为 DEBUG，生产环境日志级别为 INFO。
开发环境缓存关闭，生产环境缓存开启，缓存有效期 cache_ttl 为 300 秒。
