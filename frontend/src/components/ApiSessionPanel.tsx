import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  fetchAuthStatus,
  getAccessToken,
  loginWithPassword,
  logoutSession,
  type AuthStatus,
} from "../api/client";

export function ApiSessionPanel() {
  const { t } = useTranslation();
  const [status, setStatus] = useState<AuthStatus | null>(null);
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [localErr, setLocalErr] = useState<string | null>(null);
  const [hasSession, setHasSession] = useState(() => Boolean(getAccessToken()));

  const refreshStatus = useCallback(() => {
    void fetchAuthStatus()
      .then((s) => {
        setStatus(s);
        setLocalErr(null);
      })
      .catch(() => {
        setStatus(null);
      });
  }, []);

  useEffect(() => {
    refreshStatus();
  }, [refreshStatus]);

  const onLogin = () => {
    setBusy(true);
    setLocalErr(null);
    void loginWithPassword(password)
      .then(() => {
        setPassword("");
        setHasSession(true);
        refreshStatus();
      })
      .catch((e: unknown) => {
        const code = e instanceof Error ? e.message : "";
        setLocalErr(
          code === "TOKEN_LOGIN_DISABLED"
            ? t("apiSession.errTokenDisabled")
            : code === "LOGIN_RATE_LIMITED"
              ? t("apiSession.errRateLimited")
              : t("apiSession.errLoginFailed"),
        );
      })
      .finally(() => {
        setBusy(false);
      });
  };

  const onLogout = () => {
    logoutSession();
    setHasSession(false);
    refreshStatus();
  };

  if (!status?.requiresAuth && !status?.tokenLogin) {
    return null;
  }

  return (
    <section className="mt-4 space-y-2 border-t border-zinc-800 pt-3">
      <h2 className="text-[10px] font-semibold uppercase tracking-wide text-zinc-500">
        {t("apiSession.title")}
      </h2>
      {status.tokenLogin ? (
        <>
          {hasSession ? (
            <p className="text-emerald-600/90">{t("apiSession.signedIn")}</p>
          ) : (
            <label className="block text-zinc-500">
              {t("apiSession.password")}
              <input
                autoComplete="current-password"
                className="mt-0.5 w-full rounded border border-zinc-700 bg-zinc-900 px-1.5 py-1 text-zinc-200"
                onChange={(e) => setPassword(e.target.value)}
                type="password"
                value={password}
              />
            </label>
          )}
          {hasSession ? (
            <button
              className="w-full rounded border border-zinc-700 bg-zinc-900 py-1 hover:bg-zinc-800"
              onClick={onLogout}
              type="button"
            >
              {t("apiSession.signOut")}
            </button>
          ) : (
            <button
              className="w-full rounded border border-zinc-700 bg-zinc-900 py-1 hover:bg-zinc-800 disabled:opacity-40"
              disabled={busy || password.length === 0}
              onClick={onLogin}
              type="button"
            >
              {t("apiSession.signIn")}
            </button>
          )}
        </>
      ) : (
        <p className="text-amber-600/90">{t("apiSession.staticKeyOnly")}</p>
      )}
      {localErr ? <p className="text-red-400/90">{localErr}</p> : null}
    </section>
  );
}
