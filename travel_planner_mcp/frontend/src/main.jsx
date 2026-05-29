import React from "react";
import ReactDOM from "react-dom/client";
import { Toaster } from "react-hot-toast";
import { BrowserRouter } from "react-router-dom";

import App from "./App.jsx";
import { AuthProvider } from "./context/AuthContext.jsx";
import { TripProvider } from "./context/TripContext.jsx";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <TripProvider>
          <App />
          <Toaster
            position="top-right"
            toastOptions={{
              className: "border border-white/10 bg-slate-950 text-slate-100",
              duration: 3000,
            }}
          />
        </TripProvider>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
