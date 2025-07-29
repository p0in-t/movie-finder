import { Routes, Route } from "react-router-dom";
import { lazy, Suspense } from "react";

const Loader = lazy(() => import("../loader/Loader"));
const Home = lazy(() => import("../home/Home"));
const Contact = lazy(() => import("../contact/Contact"));
const About = lazy(() => import("../about/About"));

const NavRoutes = () => (
  <Suspense fallback={<Loader/>}>
    <Routes>
      <Route path="/" element={<Home/>}/>
      <Route path="/contact" element={<Contact/>}/>
      <Route path="/about" element={<About/>}/>
    </Routes>
  </Suspense>
);

export default NavRoutes;