import React from "react";
import ReactDOM from "react-dom/client";
import { init } from "@telegram-apps/sdk";
import App from "./App";
import "./styles.css";

try {
  init();
} catch {
  /* вне Telegram (локальная разработка в браузере) */
}

const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
