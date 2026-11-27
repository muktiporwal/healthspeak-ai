// Administrator overview: totals only (no patient details), system health and kiosks.
import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Activity, Clock3, LayoutDashboard, LogOut, RefreshCw, Users } from "lucide-react";
import { Brand, Btn, Stat, initials, pad2 } from "../../components/ui.jsx";
import LanguageSwitcher from "../../components/LanguageSwitcher.jsx";
import { adminDashboard } from "../../services/visits.js";
import DoctorApprovals from "./DoctorApprovals.jsx";
import { formatDate } from "../../services/intake.js";
import { listKiosks, registerKiosk, rotateKioskKey, setKioskActive, systemHealth } from "../../services/admin.js";

function Table({ title, data, label = (k) => k }) {
  const rows = Object.entries(data || {});
  return (
    <div className="side-card">
      <span className="eyebrow">{title}</span>
      {!rows.length && <p>—</p>}
      {rows.map(([k, v]) => (
        <p key={k} className="kv">
          <span>{label(k)}</span>
          <b>{v}</b>
        </p>
      ))}
    </div>
  );
}

const ok = (good) => <b className={"status " + (good ? "done" : "wait")}>{good ? "OK" : "!"}</b>;

export default function AdminHome({ go, notify, userName, onLogout, onLanguage }) {
  const { t } = useTranslation();
  const [d, SetD] = useState(null);
  const [health, SetHealth] = useState(null);
  const [kiosks, SetKiosks] = useState(null);
  const [newKiosk, SetNewKiosk] = useState({ code: "", name: "", location: "" });
  const [shownKey, SetShownKey] = useState(null);

  const load = () => {
    adminDashboard().then(SetD).catch((err) => notify(err.message));
    systemHealth().then(SetHealth).catch(() => SetHealth(null));
    listKiosks().then(SetKiosks).catch(() => SetKiosks([]));
  };
  useEffect(load, []);

  const run = async (fn) => {
    try {
      await fn();
      load();
    } catch (err) {
      notify(err.message);
    }
  };
  const kioskUrl = (key) => `${window.location.origin}/?kiosk=${encodeURIComponent(key)}`;
  const roleLabel = (r) => t(`roles.${r}`, r);

  return (
    <div className="staff-layout">
      <aside className="staff-sidebar">
        <Brand go={go} />
        <LanguageSwitcher onChange={onLanguage} className="language" />
        <nav>
          <button className="active">
            <LayoutDashboard /> {t("staff.overview")}
          </button>
        </nav>
        <div className="staff-user">
          <div className="avatar">{initials(userName)}</div>
          <div>
            <b>{userName}</b>
            <small>{t("admin.role")}</small>
          </div>
          <button onClick={onLogout} title={t("common.logout")} aria-label={t("common.logout")}>
            <LogOut />
          </button>
        </div>
      </aside>
      <main className="staff-main">
        <header className="dash-head">
          <div>
            <span className="eyebrow">{t("admin.eyebrow")}</span>
            <h2>{t("admin.title")}</h2>
            <p>{t("admin.totalsOnly")}</p>
          </div>
          <button className="link" onClick={load} aria-label="Refresh">
            <RefreshCw />
          </button>
        </header>
        <DoctorApprovals notify={notify} />
        {!d && <p className="empty">{t("common.loading")}</p>}
        {d && (
          <>
            <div className="stats">
              <Stat icon={<Users />} label={t("admin.visitsToday")}
                value={pad2(Object.values(d.queue_today).reduce((a, b) => a + b, 0))} />
              <Stat icon={<Clock3 />} label={t("admin.avgWait")} value={d.average_wait_minutes_today ?? "--"} />
              <Stat icon={<Activity />} label={t("admin.awaiting")}
                value={pad2(d.intakes_by_review_status.pending_review || 0)} />
            </div>
            <div className="admin-grid">
              {health && (
                <div className="side-card health">
                  <span className="eyebrow">{t("admin.systemHealth")}</span>
                  <p className="kv"><span>Database</span>{ok(health.database === "ok")}</p>
                  <p className="kv"><span>ffmpeg (audio)</span>{ok(health.ffmpeg_available)}</p>
                  <p className="kv">
                    <span>Audio storage{health.audio_storage.free_gb != null ? ` (${health.audio_storage.free_gb} GB free)` : ""}</span>
                    {ok(health.audio_storage.writable)}
                  </p>
                  {health.models.map((m) => (
                    <p key={m.name} className="kv" title={m.detail || ""}>
                      <span>
                        {m.name}
                        <br />
                        <small>{m.detail || m.model_id}</small>
                      </span>
                      <b>{m.state.replace(/_/g, " ")}</b>
                    </p>
                  ))}
                  <p className="kv"><span>Transcriptions failed (24 h)</span><b>{health.failures_last_24h.transcriptions_failed}</b></p>
                  <p className="kv"><span>Translations pending / failed</span>
                    <b>{health.failures_last_24h.intakes_translation_pending} / {health.failures_last_24h.intakes_translation_failed}</b></p>
                </div>
              )}
              <div className="side-card kiosks">
                <span className="eyebrow">{t("admin.kiosks")}</span>
                {kiosks === null && <p>{t("common.loading")}</p>}
                {(kiosks || []).map((k) => (
                  <div key={k.id} className="kiosk-row">
                    <p className="kv">
                      <span>
                        <b>{k.name}</b> <small>({k.code})</small>
                        <br />
                        <small>
                          {k.location || ""}{k.location ? " · " : ""}
                          {k.last_seen_at ? t("admin.lastSeen", { t: formatDate(k.last_seen_at) }) : t("admin.never")}
                          {k.last_report && k.last_report.microphone ? ` · mic: ${k.last_report.microphone}` : ""}
                        </small>
                      </span>
                      <b className={"status " + (k.online ? "done" : "wait")}>
                        {k.is_active ? (k.online ? t("admin.online") : t("admin.offline")) : "inactive"}
                      </b>
                    </p>
                    <div className="actions">
                      <button className="link" onClick={() => run(async () => SetShownKey((await rotateKioskKey(k.id)).key))}>
                        New key
                      </button>
                      <button className="link" onClick={() => run(() => setKioskActive(k.id, !k.is_active))}>
                        {k.is_active ? "Deactivate" : "Activate"}
                      </button>
                    </div>
                  </div>
                ))}
                <form
                  className="kiosk-form"
                  onSubmit={(e) => {
                    e.preventDefault();
                    run(async () => {
                      const k = await registerKiosk(newKiosk.code.trim(), newKiosk.name.trim(), newKiosk.location.trim());
                      SetShownKey(k.key);
                      SetNewKiosk({ code: "", name: "", location: "" });
                    });
                  }}
                >
                  <input placeholder="code, e.g. lobby-1" value={newKiosk.code} required
                    onChange={(e) => SetNewKiosk({ ...newKiosk, code: e.target.value })} aria-label="Kiosk code" />
                  <input placeholder="Name" value={newKiosk.name} required
                    onChange={(e) => SetNewKiosk({ ...newKiosk, name: e.target.value })} aria-label="Kiosk name" />
                  <input placeholder="Location (optional)" value={newKiosk.location}
                    onChange={(e) => SetNewKiosk({ ...newKiosk, location: e.target.value })} aria-label="Kiosk location" />
                  <Btn type="submit" kind="outline">Register kiosk</Btn>
                </form>
                {shownKey && (
                  <p className="attention-box">
                    Open this address once on the kiosk (shown only now, keep it private):
                    <br />
                    <code>{kioskUrl(shownKey)}</code>
                    <br />
                    <button className="link" onClick={() => SetShownKey(null)}>{t("common.close")}</button>
                  </p>
                )}
              </div>
              <Table title="ACTIVE ACCOUNTS" data={d.users_by_role} label={roleLabel} />
              <Table title="INTAKES" data={d.intakes_by_review_status} label={(k) => t(`review.${k}`, k)} />
              <Table title="LANGUAGE (30 DAYS)" data={d.intakes_last_30_days_by_language} label={(k) => t(`lang.${k}`, k)} />
              <Table title="CONFIRMED BY DEPARTMENT (30 DAYS)" data={d.confirmed_last_30_days_by_department} />
              <Table title="TRANSLATION" data={d.translation_status} />
              <Table title="VOICE TRANSCRIPTIONS (30 DAYS)" data={d.transcriptions_last_30_days} />
              <Table title="QUEUE TODAY" data={d.queue_today} label={(k) => t(`queue.${k}`, k)} />
            </div>
          </>
        )}
      </main>
    </div>
  );
}
