{
  perSystem = { pkgs, ...}:
    {
      devenv.shells.default = {
        cachix.enable = true;

        # https://devenv.sh/basics/
        env.GREET = "devenv";
        enterShell = ''
          hello
          git --version
        '';

        packages = with pkgs; [
          systemd
          # python312packages.pystemd
        ];

        scripts.local-jupyter.exec = "uv run jupyter notebook --no-browser --ip=127.0.0.1 --port=8888 --NotebookApp.token= --NotebookApp.password= --NotebookApp.allow_origin=*";

        # https://devenv.sh/tests/
        enterTest = ''
          echo "Running tests"
          git --version
        '';

        languages.python = {
          enable = true;
          uv = {
            enable = true;
            sync = {
              enable = true;
              allExtras = true;
              allGroups = true;
            };
          };
          package = pkgs.python312;
          # version = "3.12";
        };

        languages.javascript = {
          enable = true;
          package = pkgs.nodejs_20;
          npm.enable = true;
        };

        # https://devenv.sh/git-hooks/
        git-hooks.hooks = {
          shellcheck.enable = true;
          # markdownlint.enable = true; # waste of time
          
          deadnix.enable = true;
          statix.enable = true;
          # nixfmt.enable = true;
          nil.enable = true;

          uv-check.enable = true;
          ruff.enable = true;
          ruff-format.enable = true;
          pyright.enable = true;
        };

        # See full reference at https://devenv.sh/reference/options/
      };
    };
}
