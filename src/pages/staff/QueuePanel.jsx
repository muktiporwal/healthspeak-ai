// Live visit queue for today (staff: everyone; doctors: only patients assigned to them).
import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { ArrowRight, Search } from "lucide-react";
import { Btn, QUEUE_STATUS, Status } from "../../components/ui.jsx";
import { listQueue } from "../../services/visits.js";
import { PriorityChip } from "./IntakeInsights.jsx";

export default function QueuePanel({ title, eyebrow, onOpen, notify, refreshKey, emptyText, urgentFirst = false }) {
  const { t } = useTranslation();
  const [items, SetItems] = useState(null);
  const [q, SetQ] = useState("");
  const [status, SetStatus] = useState("");

  useEffect(() => {
    let alive = true;
    SetItems(null);
    const timer = setTimeout(() => {
      listQueue({ q: q.trim(), status })
        .then((r) => alive && SetItems(urgentFirst ? [...r].sort((a, b) => (b.priority === "urgent") - (a.priority === "urgent")) : r))
        .catch((err) => {
          if (alive) {
            SetItems([]);
            notify(err.message);
          }
        });
    }, 250); // small delay so typing does not send a request per key
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [q, status, refreshKey]);

  return (
    <section className="queue">
      <div className="section-title">
        <div>
          <span className="eyebrow">{eyebrow}</span>
          <h3>{title}</h3>
        </div>
        <Btn
          kind="outline"
          onClick={() => {
            SetQ("");
            SetStatus("");
          }}
        >
          {t("queue.clear")}
        </Btn>
      </div>
      <div className="queue-tools">
        <div className="search">
          <Search />
          <input
            placeholder={t("queue.search")}
            aria-label={t("queue.search")}
            value={q}
            onChange={(e) => SetQ(e.target.value)}
          />
        </div>
        <select value={status} onChange={(e) => SetStatus(e.target.value)} aria-label={t("common.status")}>
          <option value="">{t("queue.allStatuses")}</option>
          {Object.keys(QUEUE_STATUS).map((k) => (
            <option key={k} value={k}>
              {t(`queue.${k}`)}
            </option>
          ))}
        </select>
      </div>
      <div className="queue-table">
        <div className="queue-row queue-head">
          <span>{t("queue.token")}</span>
          <span>{t("queue.patientName")}</span>
          <span>{t("common.department")}</span>
          <span>{t("queue.doctor")}</span>
          <span>{t("common.status")}</span>
          <span>{t("common.action")}</span>
        </div>
        {items === null && <p className="empty">{t("common.loading")}</p>}
        {items && !items.length && <p className="empty">{emptyText || "No visits match."}</p>}
        {(items || []).map((e) => (
          <div className="queue-row" key={e.id}>
            <span>
              <b>{e.token}</b>
              {e.priority && <PriorityChip priority={e.priority} />}
            </span>
            <span>
              <b>{e.patient.full_name}</b>
              <small>
                {e.patient.age} {t("queue.years")} · {e.patient.gender.replace(/_/g, " ")}
              </small>
            </span>
            <span>{e.department.name}</span>
            <span>{e.doctor ? e.doctor.name : t("queue.notAssigned")}</span>
            <span>
              <Status value={e.status} />
              {e.position !== null && e.position !== undefined && (
                <small className="suggestion">{t("queue.ahead", { n: e.position })}</small>
              )}
            </span>
            <button className="link" onClick={() => onOpen(e.id)}>
              {t("common.open")} <ArrowRight />
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}
