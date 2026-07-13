{ config, pkgs, lib, ... }:
{
  programs.kitty = {
    enable = true;
    settings = { font_size = 13; scrollback_lines = 10000; cursor_shape = "beam"; window_padding_width = 4; background_opacity = "0.95"; };
    theme = "Catppuccin-Mocha";
  };

  gtk = { enable = true; theme.name = "Catppuccin-Mocha-Standard-Mauve-Dark"; iconTheme.name = "Papirus-Dark"; cursorTheme.name = "Catppuccin-Mocha-Dark-Cursors"; cursorTheme.size = 24; };
  qt = { enable = true; platformTheme.name = "gtk"; };

  home.packages = with pkgs; [
    grim slurp swappy swaybg mako libnotify wofi imv wl-clipboard
    cliphist swaylock swayidle brightnessctl waybar
    fcitx5 fcitx5-rime fcitx5-gtk
    catppuccin-cursors.mochaDark catppuccin-gtk papirus-icon-theme
  ];

  home.sessionVariables = { GTK_IM_MODULE = "fcitx"; QT_IM_MODULE = "fcitx"; XMODIFIERS = "@im=fcitx"; };

  wayland.windowManager.hyprland = {
    enable = true;
    settings = {
      monitor = [ "HDMI-A-1,1920x1080@60,0x0,1.25" ];
      env = [ "LIBVA_DRIVER_NAME,nvidia" "__GLX_VENDOR_LIBRARY_NAME,nvidia" "ELECTRON_OZONE_PLATFORM_HINT,auto" "NIXOS_OZONE_WL,1" ];
      exec-once = [ "fcitx5 -d --replace" "waybar" "mako" ];
      input = { kb_layout = "us"; follow_mouse = 1; touchpad.natural_scroll = true; };
      general = { gaps_in = 4; gaps_out = 8; border_size = 2; "col.active_border" = "rgba(89b4faee)"; "col.inactive_border" = "rgba(313244aa)"; layout = "dwindle"; };
      decoration = { rounding = 8; blur.enabled = true; blur.size = 6; blur.passes = 2; };
      animations = { enabled = true; bezier = "myBezier, 0.05, 0.9, 0.1, 1.05"; animation = [ "windows, 1, 4, myBezier" "windowsOut, 1, 4, default, popin 80%" "fade, 1, 4, default" "workspaces, 1, 4, default" ]; };
      cursor = { no_hardware_cursors = true; inactive_timeout = 5; hide_on_key_press = true; };
      misc = { disable_hyprland_logo = true; disable_splash_rendering = true; vfr = true; };
      bind = [
        "SUPER, Return, exec, kitty" "SUPER, Q, killactive"
        "SUPER, d, fullscreen, 1" "SUPER, V, togglefloating"
        "SUPER, Space, exec, wofi --show drun" "SUPER SHIFT, Q, exit"
        "SUPER, H, movefocus, l" "SUPER, L, movefocus, r"
        "SUPER, K, movefocus, u" "SUPER, J, movefocus, d"
        "SUPER CTRL, H, resizeactive, -20 0" "SUPER CTRL, L, resizeactive, 20 0"
        "SUPER CTRL, K, resizeactive, 0 -20" "SUPER CTRL, J, resizeactive, 0 20"
        "SUPER, 1, workspace, 1" "SUPER, 2, workspace, 2" "SUPER, 3, workspace, 3"
        "SUPER, 4, workspace, 4" "SUPER, 5, workspace, 5"
        "SUPER SHIFT, 1, movetoworkspace, 1" "SUPER SHIFT, 2, movetoworkspace, 2"
        "SUPER SHIFT, 3, movetoworkspace, 3" "SUPER SHIFT, 4, movetoworkspace, 4"
        "SUPER SHIFT, 5, movetoworkspace, 5"
        "SUPER, mouse_down, workspace, e+1" "SUPER, mouse_up, workspace, e-1"
      ];
      bindm = [ "SUPER, mouse:272, movewindow" "SUPER, mouse:273, resizewindow" ];
      workspace = [ "1, persistent:true" "2, persistent:true" "3, persistent:true" "4, persistent:true" "5, persistent:true" ];
    };
  };
}
