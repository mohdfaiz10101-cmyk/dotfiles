{ config, pkgs, lib, ... }:
{
  home.packages = with pkgs; [ neovim helix vscode ];

  programs.neovim = {
    enable = true; defaultEditor = true; vimAlias = true; viAlias = true;
    extraLuaConfig = "vim.opt.number = true\nvim.opt.relativenumber = true\nvim.opt.mouse = 'a'\nvim.opt.clipboard = 'unnamedplus'\nvim.opt.tabstop = 2\nvim.opt.shiftwidth = 2\nvim.opt.expandtab = true\nvim.opt.termguicolors = true\nvim.opt.cursorline = true\nvim.g.mapleader = ' '\nvim.keymap.set('n', '<leader>w', ':w<CR>', { silent = true })\nvim.keymap.set('n', '<leader>q', ':q<CR>', { silent = true })";

    plugins = with pkgs.vimPlugins; [
      catppuccin-nvim nvim-tree-lua telescope-nvim plenary-nvim
      nvim-lspconfig nvim-cmp cmp-nvim-lsp cmp-buffer cmp-path luasnip
      (nvim-treesitter.withAllGrammars) gitsigns-nvim lualine-nvim
    ];

    extraPackages = with pkgs; [
      ripgrep fd tree-sitter nil lua-language-server
      nodePackages.typescript-language-server
    ];
  };
}
