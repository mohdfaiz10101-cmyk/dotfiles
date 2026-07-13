# Fedora System Configuration

## NVIDIA Driver
sudo dnf install https://download1.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm
sudo dnf install akmod-nvidia xorg-x11-drv-nvidia-cuda

## Docker
sudo dnf install dnf-plugins-core
sudo dnf config-manager addrepo --from-repofile=https://download.docker.com/linux/fedora/docker-ce.repo
sudo dnf install docker-ce docker-ce-cli containerd.io
sudo systemctl enable --now docker
sudo usermod -aG docker $USER

## KVM
sudo dnf install @virtualization
sudo systemctl enable --now libvirtd
sudo usermod -aG libvirt $USER

## Firewall (from old networking.nix)
sudo firewall-cmd --add-service=ssh --permanent
sudo firewall-cmd --add-port=4000/tcp --permanent
sudo firewall-cmd --add-interface=tailscale0 --zone=trusted --permanent

## Tailscale
sudo dnf install tailscale
sudo systemctl enable --now tailscaled

## Syncthing
sudo dnf install syncthing
systemctl --user enable --now syncthing

## fcitx5
sudo dnf install fcitx5 fcitx5-rime fcitx5-chinese-addons fcitx5-gtk fcitx5-qt fcitx5-configtool
