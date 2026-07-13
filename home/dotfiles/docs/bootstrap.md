# Bootstrap Guide

## New Machine Setup
```bash
git clone <repo-url> ~/dotfiles && cd ~/dotfiles
./scripts/bootstrap-fedora.sh
. ~/.nix-profile/etc/profile.d/nix.sh
./scripts/apply-home.sh fedora-laptop
./scripts/doctor.sh
```

## Daily Usage
```bash
cd ~/dotfiles && git pull
home-manager switch --flake .#fedora-laptop
nix develop
```
