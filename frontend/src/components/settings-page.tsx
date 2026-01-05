import { useCallback, useEffect, useState } from "react";
import { client } from "@/lib/api-config";
import { useShowError } from "@/App";

interface ConfigInfo {
  config_path: string;
  keyring_service: string;
}

interface ApiKeyResponse {
  saved: boolean;
  message: string;
}

export function SettingsPage() {
  const showError = useShowError();
  const [config, setConfig] = useState<ConfigInfo | null>(null);
  const [isLoadingConfig, setIsLoadingConfig] = useState(true);
  const [savingProvider, setSavingProvider] = useState<"grok" | "zep" | null>(
    null,
  );
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const loadConfig = useCallback(async () => {
    setIsLoadingConfig(true);
    const response = await client.get<ConfigInfo>({
      url: "/api/settings/config",
    });
    setIsLoadingConfig(false);

    if ("error" in response && response.error) {
      showError("Failed to load settings", JSON.stringify(response.error));
      return;
    }

    if (response.data) {
      setConfig(response.data as ConfigInfo);
    }
  }, [showError]);

  useEffect(() => {
    loadConfig();
  }, [loadConfig]);

  const handleSetKey = useCallback(
    async (provider: "grok" | "zep") => {
      setSavingProvider(provider);
      setSuccessMessage(null);

      const response = await client.post<ApiKeyResponse>({
        url: "/api/settings/api-key",
        body: { provider },
        headers: { "Content-Type": "application/json" },
      });

      setSavingProvider(null);

      if ("error" in response && response.error) {
        const errorDetail = (response.error as { detail?: unknown }).detail;
        const detail = typeof errorDetail === "string"
          ? errorDetail
          : JSON.stringify(response.error);
        showError(`Failed to save ${provider} API key`, detail);
        return;
      }

      if (response.data?.saved) {
        setSuccessMessage(response.data.message);
      }
    },
    [showError],
  );

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-slate-800">Settings</h2>
          <p className="text-sm text-slate-600">
            Manage configuration and securely store your API keys.
          </p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-800">
            Configuration
          </h3>
          <p className="mt-2 text-sm text-slate-600">
            {isLoadingConfig && "Loading configuration..."}
            {!isLoadingConfig && config?.config_path}
          </p>
          {config?.keyring_service && (
            <p className="mt-1 text-xs text-slate-500">
              Keyring service: {config.keyring_service}
            </p>
          )}
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-800">API Keys</h3>
          <p className="mt-2 text-sm text-slate-600">
            Use a secure system prompt to enter keys; they are saved directly to
            your keyring.
          </p>

          <div className="mt-4 flex flex-col gap-3">
            <button
              type="button"
              onClick={() => handleSetKey("grok")}
              disabled={savingProvider === "grok"}
              className="inline-flex items-center justify-center rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-70"
            >
              {savingProvider === "grok"
                ? "Opening Grok prompt..."
                : "Set Grok API Key"}
            </button>

            <button
              type="button"
              onClick={() => handleSetKey("zep")}
              disabled={savingProvider === "zep"}
              className="inline-flex items-center justify-center rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-70"
            >
              {savingProvider === "zep"
                ? "Opening Zep prompt..."
                : "Set Zep API Key"}
            </button>
          </div>

          {successMessage && (
            <div className="mt-4 rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-700">
              {successMessage}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
