# Redroid Cloud Android

## 当前状态（2026-08-06）

- **宿主機**: Fedora Silverblue, kernel `6.19.10-300.fc44.x86_64`
- **容器引擎**: podman（自定义 root/runroot）
- **目標**: 直接在 host 上运行 redroid，拒絕嵌套 Ubuntu VM

## 已確認結論

- **redroid 12 和 14 都無法在当前宿主機直接啟動**
- 啟動失敗點：`init: Failed to initialize property area` → `InitFatalReboot: signal 6`
- 即使手動 patch `ashmem_linux` 模塊（適配 kernel 6.19 的 `mm_get_unmapped_area` 簽名），仍然失败
- 鏡像內的 `/system/bin/sh`、`/system/bin/toybox`、`/init` 都無法在容器環境中執行，說明不只是 `/init` 的問題
- rootfs 中存在 `linker64 -> /apex/com.android.runtime/bin/linker64`，但容器內無法解析該路徑，導致所有動態鏈接程序無法啟動

## 已嘗試的修復

1. **Patch ashmem_linux**: 從 `remote-android/redroid-modules` 構建，修復 `mm_get_unmapped_area` 調用簽名
2. **手動加載 ashmem_linux.ko**: `dmesg` 顯示 `ashmem: initialized`，但 redroid 仍然崩潰
3. **移除 `androidboot.use_memfd=true`**: 無效
4. **手動指定 redroid 屬性**: `ro.secure=0 ro.debuggable=1 androidboot.hardware=redroid`: 無效
5. **覆蓋 entrypoint 為 `/system/bin/sh` 或 `/system/bin/toybox`**: 容器直接退出，無法進入 shell
6. **啟動容器後手動 exec init**: 不可行，因為容器已退出
7. **檢查鏡像 rootfs**: 確認有 `system/bin/sh`、`system/bin/toybox`、`apex/com.android.runtime/lib64/bionic/libc.so`，但容器內無法使用

## 根本原因判斷

- 鏡像構建時預期 APEX runtime 在 `/apex/com.android.runtime/bin/linker64` 被挂載
- 當前 podman 運行時未能正確建立該路徑，導致所有動態鏈接程序啟動失敗
- 這不是簡單的 kernel module 問題，而是鏡像與容器運行時的兼容性問題

## 可行選項

1. **使用 Ubuntu VM**（`/var/mnt/ai/redroid-vm/redroid-vm.qcow2`）: 已驗證可運行，但用戶最初拒絕嵌套方案
2. **嘗試 redroid 11 或更早版本**: 可能不需要 APEX runtime，但需要從網絡拉取或找到本地鏡像
3. **在宿主機上構建自定義 redroid 鏡像**: 時間成本高，需要 Android build 環境
4. **降級宿主機 kernel**: 風險高，可能影響系統穩定性

## Ubuntu 24.04 VM `22224` Redroid 16 成功方案（2026-08-09）

- VM 磁盘 `/var/mnt/ai/redroid-vm/ubuntu-24.04-server-cloudimg-amd64-overlay-reset.qcow2`
  已从 `3.5G` 扩到 `16G`，guest `/dev/vda1` 自动 grow 到约 `15G`，剩余约 `9G+`。
- VM 登录：`ssh -p 22224 charlie@127.0.0.1`，密码 `123`。Docker 和 `adb` 已安装，
  `redroid16:local` 已由 `/var/mnt/ai/redroid-vm/redroid16-docker.tar` 导入。
- Ubuntu kernel `6.8.0-71-generic` 原生只有：
  `CONFIG_ANDROID_BINDER_IPC=m`、`CONFIG_ANDROID_BINDERFS=m`、
  `CONFIG_ANDROID_BINDER_DEVICES=""`；无 `ashmem_linux`。
- binder 修复关键点：不要把 `/dev/binderfs/binder`、`/dev/binderfs/hwbinder`、
  `/dev/binderfs/vndbinder` 分别 `--device` 映射进容器。必须目录挂载：
  `-v /dev/binderfs:/dev/binderfs`。Redroid init 会通过
  `/vendor/bin/binder_alloc /dev/binderfs/binder-control binder hwbinder vndbinder`
  自己创建 `/dev/binder`、`/dev/hwbinder`、`/dev/vndbinder`。
- ashmem 修复关键点：Redroid 16 即使有 `androidboot.use_memfd=true`、
  `ro.boot.use_memfd=true`、`sys.use_memfd=1`，`SystemServer` 仍会在
  `ApplicationSharedMemory` 调用 ashmem。缺 `/dev/ashmem` 时 fatal：
  `Failed to create ashmem: No such file or directory`。
- 已在 VM 内用 `choff/anbox-modules` 的维护版 `ashmem` 源码编译出
  `ashmem_linux.ko`，安装到：
  `/lib/modules/6.8.0-71-generic/extra/ashmem_linux.ko`，并已 `depmod -a`。
  原始 `anbox/anbox-modules` 会卡在 6.8 API：`vm_flags` 只读、
  `register_shrinker` 移除、`kallsyms_lookup_name` 未导出。
- 当前可用启动脚本在 VM 内：
  `/home/charlie/bin/redroid16-start.sh`

  关键 Docker 参数：

  ```bash
  sudo docker run -d --name redroid16 --restart=no --cpus=1 --memory=1536m \
    --privileged --pull never \
    -v /home/charlie/redroid-data16:/data \
    -v /dev/binderfs:/dev/binderfs \
    --device /dev/ashmem:/dev/ashmem \
    -p 5555:5555 \
    redroid16:local \
    androidboot.use_memfd=true androidboot.redroid_gpu_mode=guest
  ```

- Android 16 `surfaceflinger` 在 guest GPU 下会崩在 `primeShaderCache`；
  容器启动后需执行：

  ```bash
  sudo docker exec redroid16 sh -c 'setprop service.sf.prime_shader_cache 0; setprop debug.sf.prime_shader_cache.hole_punch 0; setprop debug.sf.prime_shader_cache.solid_layers 0; setprop debug.sf.prime_shader_cache.image_layers 0; setprop ctl.restart surfaceflinger'
  ```

- 成功证据：宿主 `adb connect 127.0.0.1:25557` 后，
  `adb -s 127.0.0.1:25557 shell getprop sys.boot_completed` 返回 `1`；
  `system_server`、`zygote64`、`surfaceflinger`、`adbd` 均常驻。

### 手机 Web 访问

- Redroid 16 专用 `ws-scrcpy-web` 实例：
  `ws-scrcpy-web-redroid.service`
- 本地数据目录：
  `/var/home/charlie/.local/share/WsScrcpyWeb-redroid`
- 启动脚本：
  `/var/home/charlie/.local/share/WsScrcpyWeb/start-redroid.sh`
- 端口：
  - Web UI：`0.0.0.0:18182`
  - 独立 ADB server：`127.0.0.1:5040`
  - Redroid ADB target：`127.0.0.1:25557`
- 手机 LAN 入口：
  `http://192.168.123.71:18182/`
- Workbench `/ports` 已加入 `redroid` 入口。不要裸开 DuckDNS 公网
  `18182`，除非先加认证/反代；这是可直接操作云手机的控制面。
- `18182` 点 Connect 后立即断开/闪退时，不要单独升级 bundled
  `scrcpy-server` 到 Genymobile `4.x`。当前 `ws-scrcpy-web` client 协议仍是
  `3.3.4`，单独换 server 会触发版本不匹配。2026-08-09 的 Redroid 16
  故障根因是前端生成的 stream 链接把 `ws=` 自动探测成 Docker 内网
  `ws://172.17.0.2/`，手机无法访问 WebSocket。修复是在
  `/var/home/charlie/.local/share/WsScrcpyWeb/dist-runtime/public/index.html`
  引入 `/redroid-wsfix.js?v=20260809-1`，由
  `/var/home/charlie/.local/share/WsScrcpyWeb/dist-runtime/public/redroid-wsfix.js`
  把所有 `action=stream` 链接的 `ws` 参数重写为当前页面 origin，例如手机 LAN
  是 `ws://192.168.123.71:18182/`。
- 可手动绕过前端链接的直达 URL：
  `http://192.168.123.71:18182/#!action=stream&udid=127.0.0.1%3A25557&player=webcodecs&ws=ws%3A%2F%2F192.168.123.71%3A18182%2F`

## 相關文件

- wrapper: `/var/home/charlie/.local/bin/redroid-r1`
- service: `/var/home/charlie/.config/systemd/user/redroid-r1.service`
- 本地鏡像: `/var/mnt/ai/cache/redroid-12.tar`, `/var/mnt/ai/cache/redroid-14.tar`
- VM 镜像: `/var/mnt/ai/redroid-vm/ubuntu-24.04-server-cloudimg-amd64-overlay-reset.qcow2`
- Redroid 16 Docker tar: `/var/mnt/ai/redroid-vm/redroid16-docker.tar`
- ashmem patch: `/tmp/redroid-modules/ashmem/ashmem_linux.ko`
