import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import AppErrorBoundary from "./components/AppErrorBoundary";
import { AuthProvider } from "./context/AuthContext";
import { BookingProvider } from "./context/BookingContext";
import { FeaturesProvider } from "./context/FeaturesContext";
import { AppearanceProvider } from "./context/AppearanceContext";
import { UserPreferencesProvider } from "./context/UserPreferencesContext";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <AppErrorBoundary>
      <BrowserRouter>
        <FeaturesProvider>
          <AppearanceProvider>
            <UserPreferencesProvider>
              <AuthProvider>
                <BookingProvider>
                  <App />
                </BookingProvider>
              </AuthProvider>
            </UserPreferencesProvider>
          </AppearanceProvider>
        </FeaturesProvider>
      </BrowserRouter>
    </AppErrorBoundary>
  </React.StrictMode>
);
