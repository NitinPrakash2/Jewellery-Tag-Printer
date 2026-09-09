const BASE = "";

async function req(method, path, body) {
  const res = await fetch(BASE + path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await res.text();
  try {
    return JSON.parse(text);
  } catch {
    throw new Error("Server returned an unexpected response.");
  }
}

export const api = {
  health: () => req("GET", "/api/health"),
  printers: () => req("GET", "/api/printers"),
  printerStatus: (name) => req("GET", `/api/printers/status?name=${encodeURIComponent(name || "")}`),
  testPrint: (printer_name) => req("POST", "/api/printers/test", { printer_name }),
  printersSetup: (payload) => req("POST", "/api/printers/setup", payload),
  driverHelp: () => req("GET", "/api/printers/driver-help"),
  usbLive: (printer_name) =>
    req("GET", `/api/printers/usb-live?printer_name=${encodeURIComponent(printer_name || "")}`),
  print: (payload) => req("POST", "/api/print", payload),
  validate: (payload) => req("POST", "/api/print/validate", payload),
  renderTag: (payload) => req("POST", "/api/tag/render", payload),
  history: (params = {}) => {
    const qs = new URLSearchParams(
      Object.fromEntries(Object.entries(params).filter(([, v]) => v !== "" && v != null))
    ).toString();
    return req("GET", `/api/history${qs ? `?${qs}` : ""}`);
  },
  historyOne: (id) => req("GET", `/api/history/${id}`),
  reprint: (id) => req("POST", `/api/history/${id}/reprint`, {}),
  settingsAll: () => req("GET", "/api/settings"),
  settingsGet: (cat) => req("GET", `/api/settings/${cat}`),
  settingsPut: (cat, values) => req("PUT", `/api/settings/${cat}`, values),
  logoGet: () => req("GET", "/api/settings/logo"),
  logoDelete: () => req("DELETE", "/api/settings/logo"),
  logoUpload: async (file) => {
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch(`${BASE}/api/settings/logo`, { method: "POST", body: fd });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "Logo upload failed.");
    return data;
  },
};
