#!/nix/store/f15k3dpilmiyv6zgpib289rnjykgr1r4-bash-5.3p9/bin/bash
ignored=(/nix /dev /proc /etc )
ro_mounts=()
symlinks=()
etc_ignored=()



# loop through all entries of root in the fhs environment, except its /etc.
for i in /nix/store/6vz4zj6qryvwnfrns2z1yflnk41vjy9i-wechat-uos-4.1.0.12-fhsenv-rootfs/*; do
  path="/${i##*/}"
  if [[ $path == '/etc' ]]; then
    :
  elif [[ -L $i ]]; then
    symlinks+=(--symlink "$(/nix/store/i2vmgx46q9hd3z6rigaiman3wl3i2gc4-coreutils-9.9/bin/readlink "$i")" "$path")
    ignored+=("$path")
  else
    ro_mounts+=(--ro-bind "$i" "$path")
    ignored+=("$path")
  fi
done

# loop through the entries of /etc in the fhs environment.
if [[ -d /nix/store/6vz4zj6qryvwnfrns2z1yflnk41vjy9i-wechat-uos-4.1.0.12-fhsenv-rootfs/etc ]]; then
  for i in /nix/store/6vz4zj6qryvwnfrns2z1yflnk41vjy9i-wechat-uos-4.1.0.12-fhsenv-rootfs/etc/*; do
    path="/${i##*/}"
    # NOTE: we're binding /etc/fonts and /etc/ssl/certs from the host so we
    # don't want to override it with a path from the FHS environment.
    if [[ $path == '/fonts' || $path == '/ssl' ]]; then
      continue
    fi
    if [[ -L $i ]]; then
      symlinks+=(--symlink "$i" "/etc$path")
    else
      ro_mounts+=(--ro-bind "$i" "/etc$path")
    fi
    etc_ignored+=("/etc$path")
  done
fi

# propagate /etc from the actual host if nested
if [[ -e /.host-etc ]]; then
  ro_mounts+=(--ro-bind /.host-etc /.host-etc)
else
  ro_mounts+=(--ro-bind /etc /.host-etc)
fi

# link selected etc entries from the actual root
for i in /etc/static /etc/nix /etc/shells /etc/bashrc /etc/zshenv /etc/zshrc /etc/zinputrc /etc/zprofile /etc/passwd /etc/group /etc/shadow /etc/hosts /etc/resolv.conf /etc/nsswitch.conf /etc/profiles /etc/login.defs /etc/sudoers /etc/sudoers.d /etc/localtime /etc/zoneinfo /etc/machine-id /etc/os-release /etc/pam.d /etc/fonts /etc/alsa /etc/asound.conf /etc/ssl/certs /etc/ca-certificates /etc/pki /etc/dconf; do
  if [[ "${etc_ignored[@]}" =~ "$i" ]]; then
    continue
  fi
  if [[ -e $i ]]; then
    symlinks+=(--symlink "/.host-etc/${i#/etc/}" "$i")
  fi
done

declare -a auto_mounts
# loop through all directories in the root
for dir in /*; do
  # if it is a directory and it is not ignored
  if [[ -d "$dir" ]] && [[ ! "${ignored[@]}" =~ "$dir" ]]; then
    # add it to the mount list
    auto_mounts+=(--bind "$dir" "$dir")
  fi
done

declare -a x11_args
# Always mount a tmpfs on /tmp/.X11-unix
# Rationale: https://github.com/flatpak/flatpak/blob/be2de97e862e5ca223da40a895e54e7bf24dbfb9/common/flatpak-run.c#L277
x11_args+=(--tmpfs /tmp/.X11-unix)

# Try to guess X socket path. This doesn't cover _everything_, but it covers some things.
if [[ "$DISPLAY" == *:* ]]; then
  # recover display number from $DISPLAY formatted [host]:num[.screen]
  display_nr=${DISPLAY/#*:} # strip host
  display_nr=${display_nr/%.*} # strip screen
  local_socket=/tmp/.X11-unix/X$display_nr
  x11_args+=(--ro-bind-try "$local_socket" "$local_socket")
fi



cmd=(
  /nix/store/dqzmpjz70l4lzg7lmc3x8wih74nh5bpc-bubblewrap-0.11.0/bin/bwrap
  --dev-bind /dev /dev
  --proc /proc
  --chdir "$(pwd)"
  
  
  
  
  
  
  --die-with-parent
  --bind /nix /nix
  
  # Our glibc will look for the cache in its own path in `/nix/store`.
  # As such, we need a cache to exist there, because pressure-vessel
  # depends on the existence of an ld cache. However, adding one
  # globally proved to be a bad idea (see #100655), the solution we
  # settled on being mounting one via bwrap.
  # Also, the cache needs to go to both 32 and 64 bit glibcs, for games
  # of both architectures to work.
  --tmpfs /nix/store/wb6rhpznjfczwlwx23zmdrrw74bayxw4-glibc-2.42-47/etc \
  --tmpfs /etc \
  --symlink /etc/ld.so.conf /nix/store/wb6rhpznjfczwlwx23zmdrrw74bayxw4-glibc-2.42-47/etc/ld.so.conf \
  --symlink /etc/ld.so.cache /nix/store/wb6rhpznjfczwlwx23zmdrrw74bayxw4-glibc-2.42-47/etc/ld.so.cache \
  --ro-bind /nix/store/wb6rhpznjfczwlwx23zmdrrw74bayxw4-glibc-2.42-47/etc/rpc /nix/store/wb6rhpznjfczwlwx23zmdrrw74bayxw4-glibc-2.42-47/etc/rpc \
  --remount-ro /nix/store/wb6rhpznjfczwlwx23zmdrrw74bayxw4-glibc-2.42-47/etc \
  --symlink /nix/store/00khjq0ssl6w1zqmn5n7ih43qkfss8rr-wechat-uos-4.1.0.12-init /init \
  "${ro_mounts[@]}"
  "${symlinks[@]}"
  "${auto_mounts[@]}"
  --bind /home/charlie/.wechat2-home /home/charlie
  "${x11_args[@]}"
  
  /nix/store/nx9ivl4342idl2hpkd77nw3a82jv3xxy-container-init "$@"
)
exec "${cmd[@]}"

