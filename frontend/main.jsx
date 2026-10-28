import React from "react";
import { createRoot } from "react-dom/client";
import { Dashboard } from "./dashboard";

const rootElement = document.getElementById("dashboard-widget-root");
const dataElement = document.getElementById("dashboard-data");

if (rootElement && dataElement) {
  const props = JSON.parse(dataElement.textContent);
  createRoot(rootElement).render(<Dashboard {...props} />);
}