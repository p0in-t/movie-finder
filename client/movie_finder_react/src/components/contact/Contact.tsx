import './Contact.css';
import React from 'react';

const Contact: React.FC = () => {
    const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault();

        alert('Your message has been sent!');
    };

    return (
        <div className='contact-main-container'>
            <div className='contact-form-container'>
                <form className='contact-form' onSubmit={handleSubmit}>
                    <header className="form-header" style={{fontFamily: 'Corbel', fontSize: '24px', fontWeight: 'bold'}}>
                        Contact Us
                    </header><br/>
                    <label htmlFor="reg-form">
                        Fill up the form below to send us a message
                    </label><br/>

                    <div className='horizontal-entry'>
                        <label htmlFor="full-name">Full Name</label>
                        <input type="text" className="full-name" name="full-name" placeholder="John Doe" required/><br></br>
                    </div>
                    
                    <div className='horizontal-entry'>
                        <label htmlFor="email">Email</label>
                        <input type="email" className="email" name="email" placeholder="example@company.com" required/><br></br>
                    </div>

                    <div className='horizontal-entry'>
                        <label htmlFor="gender">Gender</label>
                        <label>
                            <input type="radio" name="gender" value="male" required/>
                            Male
                        </label>
                        <label>
                        <input type="radio" name="gender" value="female" required/>
                            Female
                        </label><br/>
                    </div>

                    <label htmlFor="checkboxWOM">Where did you find about us</label><br/>

                    <div className='checkbox-container'>
                        <div className="checkbox-wrapper-4">
                            <input className="inp-cbx" id='wom' name='wom' type="checkbox"/>
                            <label className="cbx" htmlFor="wom"><span>
                            <svg width="12px" height="10px">
                            <use xlinkHref="#check-4"></use>
                            </svg></span><span>Word of mouth</span></label>
                                <svg className="inline-svg">
                                <symbol id="check-4" viewBox="0 0 12 10">
                                <polyline points="1.5 6 4.5 9 10.5 1"></polyline>
                                </symbol>
                            </svg>
                        </div>

                        <div className="checkbox-wrapper-4">
                            <input className="inp-cbx" id="sn" name='sn' type="checkbox"/>
                            <label className="cbx" htmlFor="sn"><span>
                            <svg width="12px" height="10px">
                            <use xlinkHref="#check-4"></use>
                            </svg></span><span>Social network</span></label>
                                <svg className="inline-svg">
                                <symbol id="check-4" viewBox="0 0 12 10">
                                <polyline points="1.5 6 4.5 9 10.5 1"></polyline>
                                </symbol>
                            </svg>
                        </div>

                        <div className="checkbox-wrapper-4">
                            <input className="inp-cbx" id="searchf" name='search' type="checkbox"/>
                            <label className="cbx" htmlFor="searchf"><span>
                            <svg width="12px" height="10px">
                            <use xlinkHref="#check-4"></use>
                            </svg></span><span>Search</span></label>
                                <svg className="inline-svg">
                                <symbol id="check-4" viewBox="0 0 12 10">
                                <polyline points="1.5 6 4.5 9 10.5 1"></polyline>
                                </symbol>
                            </svg>
                        </div>
                    </div>

                    <div className='text-area-container'>
                        <label htmlFor="message">Feel free to leave a message!</label><br/>
                        <textarea rows={3} placeholder="Message..." name="message" required></textarea><br/>
                    </div>

                    <div className="checkbox-wrapper-4">
                            <input className="inp-cbx" id='nl' name='nl' type="checkbox"/>
                            <label className="cbx" htmlFor="nl"><span>
                            <svg width="12px" height="10px">
                            <use xlinkHref="#check-4"></use>
                            </svg></span><span>Would you like to subscribe to our newsletter?</span></label>
                            <svg className="inline-svg">
                                <symbol id="check-4" viewBox="0 0 12 10">
                                <polyline points="1.5 6 4.5 9 10.5 1"></polyline>
                                </symbol>
                            </svg>
                    </div>

                    <button type="submit">Submit</button><br/>
                </form>
            </div>
        </div>
    );
}

export default Contact;