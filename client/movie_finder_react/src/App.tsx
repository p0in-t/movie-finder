import { createContext, useState } from 'react';
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

type Session = { "id": number, "title": string, "started_at": Date};

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
  sessionID: number;
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
  sessionID: -1,
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
    sessionID: -1,
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