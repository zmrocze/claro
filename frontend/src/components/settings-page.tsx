import { useCallback, useEffect, useState } from "react";
import { client } from "@/lib/api-config";
import { useShowError } from "@/App";
import { Edit3, Save, X } from "lucide-react";

interface ConfigInfo {
  config_path: string;
  keyring_service: string;
  config_content?: string | null;
  config_exists: boolean;
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
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [configContent, setConfigContent] = useState("");
  const [isSavingConfig, setIsSavingConfig] = useState(false);
  const [configSaveMessage, setConfigSaveMessage] = useState<string | null>(
    null,
  );

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

  useEffect(() => {
    if (config?.config_content) {
      setConfigContent(config.config_content);
    }
  }, [config]);

  const handleSaveConfig = useCallback(async () => {
    setIsSavingConfig(true);
    setConfigSaveMessage(null);

    const response = await client.post({
      url: "/api/settings/config/content",
      body: { content: configContent },
      headers: { "Content-Type": "application/json" },
    });

    setIsSavingConfig(false);

    if ("error" in response && response.error) {
      const errorDetail = (response.error as { detail?: unknown }).detail;
      const detail = typeof errorDetail === "string"
        ? errorDetail
        : JSON.stringify(response.error);
      showError("Failed to save config file", detail);
      return;
    }

    setConfigSaveMessage("Configuration saved successfully!");
    await loadConfig();
    setTimeout(() => {
      setConfigSaveMessage(null);
      setIsModalOpen(false);
    }, 1500);
  }, [configContent, showError, loadConfig]);

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
    <div className="flex flex-col gap-4 px-3 py-2 md:gap-6 md:px-0 md:py-0">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-800 md:text-2xl">
            Settings
          </h2>
          <p className="text-sm text-slate-600">
            Manage configuration and securely store your API keys.
          </p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm md:p-6">
          <h3 className="mb-2 text-lg font-semibold text-slate-800">
            Configuration File
          </h3>
          <p className="mb-4 break-all text-sm text-slate-600">
            {isLoadingConfig && "Loading configuration..."}
            {!isLoadingConfig && config?.config_path}
          </p>

          <button
            type="button"
            onClick={() => setIsModalOpen(true)}
            disabled={isLoadingConfig}
            className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-70"
          >
            <Edit3 className="h-4 w-4" />
            Edit Configuration
          </button>

          {config?.keyring_service && (
            <p className="mt-4 text-xs text-slate-500">
              Secure storage: {config.keyring_service}
            </p>
          )}
        </div>

        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 shadow-sm md:p-6">
          <h3 className="text-lg font-semibold text-slate-800">API Keys</h3>
          <p className="mt-2 text-sm text-slate-600">
            Use a secure system prompt to enter keys; they are saved securely on
            this device.
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

      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
          <div className="max-h-[90vh] w-full max-w-4xl overflow-hidden rounded-lg bg-white shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
              <div>
                <h3 className="text-lg font-semibold text-slate-800">
                  Edit Configuration
                </h3>
                <p className="mt-1 text-xs text-slate-500">
                  {config?.config_path}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="rounded-md p-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="p-6">
              <textarea
                value={configContent}
                onChange={(e) => setConfigContent(e.target.value)}
                placeholder="# Add your notification schedule configuration here...\n# See example_config.yaml for reference"
                className="h-96 w-full rounded-md border border-slate-300 bg-slate-50 p-4 font-mono text-sm text-slate-800 placeholder:text-slate-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                spellCheck={false}
              />
            </div>

            <div className="flex items-center justify-between border-t border-slate-200 px-6 py-4">
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50"
              >
                Cancel
              </button>
              <div className="flex items-center gap-3">
                {configSaveMessage && (
                  <span className="text-sm font-medium text-green-600">
                    {configSaveMessage}
                  </span>
                )}
                <button
                  type="button"
                  onClick={handleSaveConfig}
                  disabled={isSavingConfig}
                  className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-70"
                >
                  <Save className="h-4 w-4" />
                  {isSavingConfig ? "Saving..." : "Save Configuration"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
