import './Footer.css'
import { useContext } from 'react';
import { AppContext } from '../../App';

const Footer = () => {
    const ctx = useContext(AppContext);

    return (
        <div className='footer-container'>
            <p>Footer</p>
        </div>
    );
}

export default Footer;