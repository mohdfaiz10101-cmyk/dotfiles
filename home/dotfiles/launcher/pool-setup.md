# 磁盘池化方案

## 设计原则
- 不绑定 UUID、设备路径、盘数量
- 重装系统后 rebuild 即恢复
- 通过磁盘标签 POOL-xxx 自动发现
- 加盘只需打标签，减盘自动适应

## 盘规划

| 分区 | 当前标签 | 新标签 | 大小 | 角色 |
|---|---|---|---|---|
| sda4 | 拷贝 3 大存储 2 | POOL-A1 | 932G | 数据盘 |
| sdb1 | EXT-Games-2T | POOL-B1 | 1.8T | 数据盘 |
| sdd1 | NixOS-Expand | POOL-D1 | 935G | 数据盘 |
| sde1 | EXT-Archive-4T | POOL-E1 | 3.6T | 数据盘 |
| sdd2 | HDD2-Storage | PARITY-1 | 928G | 校验盘(可选) |

不入池（保留）：
- sda2 HDD1-Backup 53G（太小）
- sda3 HDD1-Games 878G（可以以后加入）
- NVMe 系统盘
