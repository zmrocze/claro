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

        scripts.generate-types.exec = ''
          echo "🔄 Generating TypeScript types from FastAPI backend..."
          
          # Check if backend is already running
          BACKEND_RUNNING=false
          if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo "✓ Backend is already running"
            BACKEND_RUNNING=true
          else
            echo "⚙️  Starting backend temporarily..."
            uv run -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 > /dev/null 2>&1 &
            BACKEND_PID=$!
            
            # Wait for backend to be ready (max 30 seconds)
            echo "⏳ Waiting for backend to start..."
            for i in {1..30}; do
              if curl -s http://localhost:8000/health > /dev/null 2>&1; then
                echo "✓ Backend is ready"
                break
              fi
              sleep 1
            done
          fi
          
          # Generate types
          echo "📝 Generating TypeScript types..."
          cd frontend
          npm run generate-types
          cd ..
          
          # Stop backend if we started it
          if [ "$BACKEND_RUNNING" = false ]; then
            echo "🛑 Stopping temporary backend..."
            kill $BACKEND_PID 2>/dev/null || true
          fi
          
          echo "✅ TypeScript types generated successfully in frontend/src/api-client/"
        '';

        # https://devenv.sh/tests/
        enterTest = ''
          echo "Running tests"
          git --version
        '';

        languages = {
          python = {
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
          javascript = {
            enable = true;
            package = pkgs.nodejs_20;
            npm = {
              enable = true;
              install.enable = true;
            };
          };

          nix = {
            enable = true;
          };
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
