import "./Navbar.css";
import { Link } from "react-router-dom";
import { useContext, useState } from "react";
import { AppContext } from '../../App';

const Navbar = () => {
    const ctx = useContext(AppContext);

    if (!ctx) {
        return;
    }

    return (
        <div className="navbar-container">
            <div className="nav-home">
                <Link to="/" className="navbar-home">Home</Link>
            </div>
            <ul className="nav">
                <li className="nav-entry">
                    <Link to="/contact" className="navbar-link">Contact</Link>
                </li>
                <li className="nav-entry">
                    <Link to="/about" className="navbar-link">About</Link>
                </li>
            </ul>
        </div> 
    )
};

export default Navbar;