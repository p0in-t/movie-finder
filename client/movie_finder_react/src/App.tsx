import { createContext, useEffect, useState } from 'react';
import './App.css'
import NavRoutes from "./components/nav_routes/NavRoutes";
import Navbar from "./components/navbar/Navbar";

interface SettingsContextType {
  geminiApiKey: string;
  setSettingsCtx: React.Dispatch<React.SetStateAction<Omit<SettingsContextType, 'setSettingsCtx'>>>;
}

const defaultSettingsContextValue: SettingsContextType = {
  geminiApiKey: "",
  setSettingsCtx: () => { },
};

type Session = { "session_id": string, "title": string, "started_at": Date};

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
  userID: number;
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
  userID: -1,
  email: "",
  username: "user",
  isActive: false,
  isAdmin: false,
  emailVerified: false,
  hasGeminiAPIKey: false,
  setUserCtx: () => { },
};

export const AppContext = createContext<AppContextType>(defaultAppContextValue);
export const UserContext = createContext<UserContextType>(defaultUserContextValue);
export const SettingsContext = createContext<SettingsContextType>(defaultSettingsContextValue);

function App() {
  const [settings, setSettings] = useState({
    geminiApiKey: "",
  });

  const [app, setApp] = useState({
    userSessions: [] as Session[],
  });

  const [user, setUser] = useState({
    isLoggedIn: false,
    sessionID: "",
    userID: -1,
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
    console.log("trying to get auth status")

    try {
      const response = await fetch('https://movie-finder-980543701851.europe-west1.run.app/api/user/auth-status', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(`Network response was not ok: ${response.statusText}`);
      }

      const data = await response.json();

      const result = data.result;

      if (!result) {
        setUserCtx(prevSettings => ({
          ...prevSettings,
          isLoggedIn: false 
        }));
        throw new Error(`Could not authorize user`);
      }

      setUserCtx(prevSettings => ({
        ...prevSettings,
        isLoggedIn: true,
        sessionID: "",
        username: data.username,
        userID: data.user_id,
        isActive: data.is_active,
        isAdmin: data.is_admin,
        emailVerified: data.email_verified,
        hasGeminiAPIKey: data.has_gemini_api_key,
      }))
    } catch (error) {
      console.error("Error checking auth status", error);
    } finally {
      // setIsResponding(false);
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