import React from "react";
import { createRoot } from "react-dom/client";
import { Dashboard, TradePage } from "./dashboard";

const rootElement =
  document.getElementById("dashboard-widget-root") ||
  document.getElementById("trades-widget-root");

if (rootElement) {
  const Page = rootElement.id === "trades-widget-root" ? TradePage : Dashboard;
  const dataElement = document.getElementById(
    rootElement.id === "trades-widget-root" ? "trade-data" : "dashboard-data",
  );
  const props = dataElement ? JSON.parse(dataElement.textContent) : {};
  createRoot(rootElement).render(<Page {...props} />);
}