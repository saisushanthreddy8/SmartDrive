import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource-variable/instrument-sans/standard.css"; // weight + width axes (narrow headlines)
import "@fontsource-variable/jetbrains-mono/wght.css";
import "./styles.css";
import App from "./App.jsx";

createRoot(document.getElementById("root")).render(<StrictMode><App /></StrictMode>);
