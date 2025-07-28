import { Routes, Route } from "react-router-dom";
import { lazy, Suspense } from "react";

const Loader = lazy(() => import("../loader/Loader"));
const Home = lazy(() => import("../home/Home"));

const NavRoutes = () => (
  <Suspense fallback={<Loader/>}>
    <Routes>
      <Route path="/" element={<Home/>}/>
    </Routes>
  </Suspense>
);

export default NavRoutes;