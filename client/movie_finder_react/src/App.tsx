import { createContext, useState } from 'react';
import './App.css'
import NavRoutes from "./components/nav_routes/NavRoutes";
import Navbar from "./components/navbar/Navbar";
import Footer from "./components/footer/Footer";

interface AppContextType {
  test: number
}

const defaultAppContextValue: AppContextType = {
  test: 1
};

export const AppContext = createContext<AppContextType>(defaultAppContextValue);

function App() {
  const [ test, _ ] = useState<number>(1);

  return (
    <>
      <div className='app'>
        <AppContext.Provider value={{test}}>
          <Navbar/>
          <NavRoutes/>
          <Footer/>
        </AppContext.Provider>
      </div>
    </>
  )
}

export default App
