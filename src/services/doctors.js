// Doctor registration / verification and the doctor's read-only intake view.
// The server decides every permission; nothing here grants access.
import { api, tokenStore } from "./api.js";

// Creates a PENDING doctor account (the server fixes the role; the form cannot choose one).
export async function registerDoctor(payload) {
  const data = await api("/doctors/register", { method: "POST", body: payload, auth: false });
  tokenStore.set(data.access_token);
  return data.user;
}

export const getMyVerification = () => api("/doctors/me/verification");

// ----- administrator -----
export const listDoctorApplications = (status = "") =>
  api(`/admin/doctors?limit=100${status ? `&status=${encodeURIComponent(status)}` : ""}`);
export const approveDoctor = (userId, note) =>
  api(`/admin/doctors/${userId}/approve`, { method: "POST", body: { note: note || null } });
export const rejectDoctor = (userId, note) =>
  api(`/admin/doctors/${userId}/reject`, { method: "POST", body: { note } });

// ----- verified doctor: only intakes of visits assigned to them -----
export const getDoctorIntake = (intakeId) => api(`/doctor/intakes/${intakeId}`);
export const getDoctorIntakeHistory = (intakeId, { limit = 5, offset = 0 } = {}) =>
  api(`/doctor/intakes/${intakeId}/history?limit=${limit}&offset=${offset}`);
