import { createContext, useEffect, useState } from 'react';
import './App.css'
import NavRoutes from "./components/nav_routes/NavRoutes";
import Navbar from "./components/navbar/Navbar";
import type { JwtPayload } from 'jwt-decode';

interface SettingsContextType {
  geminiApiKey: string;
  setSettingsCtx: React.Dispatch<React.SetStateAction<Omit<SettingsContextType, 'setSettingsCtx'>>>;
}

const defaultSettingsContextValue: SettingsContextType = {
  geminiApiKey: "",
  setSettingsCtx: () => { },
};

export type Session = { "session_id": string, "title": string, "started_at": Date};

interface AppContextType {
  userSessions: Session[];
  setAppCtx: React.Dispatch<React.SetStateAction<Omit<AppContextType, 'setAppCtx'>>>;
}

const defaultAppContextValue: AppContextType = {
  userSessions: [],
  setAppCtx: () => { },
};

interface UserContextType {
  isLoggedIn: boolean;
  sessionID: string;
  userID: string;
  email: string;
  username: string;
  isActive: boolean;
  isAdmin: boolean;
  emailVerified: boolean;
  hasGeminiAPIKey: boolean;
  setUserCtx: React.Dispatch<React.SetStateAction<Omit<UserContextType, 'setUserCtx'>>>;
}

const defaultUserContextValue: UserContextType = {
  isLoggedIn: false,
  sessionID: "",
  userID: "",
  email: "",
  username: "user",
  isActive: false,
  isAdmin: false,
  emailVerified: false,
  hasGeminiAPIKey: false,
  setUserCtx: () => { },
};

export interface JWTPayload extends JwtPayload {
  sub: string;
  username: string;
  is_active: boolean;
  is_admin: boolean;
  email_verified: boolean;
}

export const AppContext = createContext<AppContextType>(defaultAppContextValue);
export const UserContext = createContext<UserContextType>(defaultUserContextValue);
export const SettingsContext = createContext<SettingsContextType>(defaultSettingsContextValue);

function App() {
  const apiUrl = import.meta.env.VITE_APP_API_URL;
  const [settings, setSettings] = useState({
    geminiApiKey: "",
  });

  const [app, setApp] = useState({
    userSessions: [] as Session[],
  });

  const [user, setUser] = useState({
    isLoggedIn: false,
    sessionID: "",
    userID: "",
    email: "",
    username: "user",
    isActive: false,
    isAdmin: false,
    emailVerified: false,
    hasGeminiAPIKey: false,
  });

  const settingsContextValue = {
    ...settings,
    setSettingsCtx: setSettings,
  };

  const appCtxValue = {
    ...app,
    setAppCtx: setApp,
  };

  const userCtxValue = {
    ...user,
    setUserCtx: setUser,
  };

  const setUserCtx = setUser;

  const checkAuthStatus = async () => {
    const token = localStorage.getItem('token');

    if (!token) {
      return;
    }

    try {
      const response = await fetch(`${apiUrl}/users/auth-status`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(`Session verification failed: ${response.statusText}`);
      }

      const userData = await response.json();
      
      setUserCtx(prevSettings => ({
        ...prevSettings,
        isLoggedIn: true,
        userID: userData.sub,
        username: userData.username,
        isActive: userData.is_active,
        isAdmin: userData.is_admin,
        emailVerified: userData.email_verified,
      }));

    } catch (error) {
      console.error("Error verifying session:", error);

      localStorage.removeItem("token");

      setUserCtx(prevSettings => ({
        ...prevSettings,
        isLoggedIn: false,
        sessionID: "",
        userID: "",
        username: "user",
        isActive: false,
        isAdmin: false,
        emailVerified: false,
      }));
    }
  };

  useEffect(() => {
    checkAuthStatus();
  }, []);

  return (
    <>
      <div className='app'>
        <AppContext.Provider value={appCtxValue}>
          <UserContext.Provider value={userCtxValue}>
            <SettingsContext.Provider value={settingsContextValue}>
              <Navbar />
              <NavRoutes />
            </SettingsContext.Provider>
          </UserContext.Provider>
        </AppContext.Provider>
      </div>
    </>
  );
}

export default App;