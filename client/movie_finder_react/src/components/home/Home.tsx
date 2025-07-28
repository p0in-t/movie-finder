import './Home.css'
import { useState, useEffect, useRef } from 'react';

const Home = () => {
    const [messageInput, setMessageInput] = useState('');
    const [msgHistory, setMsgHistory] = useState<{id: number, text: string, isUser: boolean, isVisible: boolean}[]>([]);
    const chatDisplayRef = useRef<HTMLDivElement>(null);

    const sendPromptToBackend = async (promptText: string) => {
        try {
            const response = await fetch('https://movie-finder-980543701851.europe-west1.run.app/api/process', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ prompt: promptText }),
                credentials: 'include',
            });

            const data = await response.json();
            console.log('Response from backend:', data.result);

            handleReceiveMessage(data.result)
            
        } catch (error) {
            console.error("Error connecting to the backend:", error);
        }
    };

    const addMessage = (text: string, isUser: boolean) => {
        const new_msg = {
            id: Date.now(),
            text,
            isUser,
            isVisible: false
        }

        setMsgHistory(prevMessages => [...prevMessages, new_msg]);

        console.log(msgHistory)

        setTimeout(() => {
            setMsgHistory(prevMessages =>
                prevMessages.map(msg =>
                    msg.id === new_msg.id ? { ...msg, isVisible: true } : msg
                )
            );
        }, 50);
    };

    const handleSendMessage = () => {
        const trimmedMessage = messageInput.trim();
        if (trimmedMessage) {
            addMessage(trimmedMessage, true);
            setMessageInput('');
            sendPromptToBackend(trimmedMessage);
        }
    };

    const handleKeyDown = (event: React.KeyboardEvent) => {
        if (event.key === 'Enter' && !event.shiftKey) {
            const trimmedMessage = messageInput.trim();
            if (trimmedMessage) {
                addMessage(trimmedMessage, true);
                setMessageInput('');
                sendPromptToBackend(trimmedMessage);
            }
        }
    };

    const handleReceiveMessage = (msg: string) => {
        const trimmedMessage = msg.trim();
        if (trimmedMessage) {
            addMessage(trimmedMessage, false);
            setMessageInput('');
        }
    };

    useEffect(() => {
        if (chatDisplayRef.current) {
            chatDisplayRef.current.scrollTo({
                top: chatDisplayRef.current.scrollHeight,
                behavior: 'smooth'
            });
        }
    }, [msgHistory]);

    return (
        <div className='home-main'>
            <div className='main-io-container'>
                <div className='chat-container' ref={chatDisplayRef}>
                    {
                        msgHistory.map(
                            msg =>
                                msg.isUser ?
                                    <div className={`user-message-container ${msg.isVisible ? 'message-visible' : ''}`} key={msg.id} >
                                        <p className='message'>{msg.text}</p>
                                    </div>
                                    :
                                    <div className={`ai-message-container ${msg.isVisible ? 'message-visible' : ''}`} key={msg.id}>
                                        <p className='message'>{msg.text}</p>
                                    </div>
                        )
                    }
                </div>
                <div className='chat-box-container'>
                    <textarea className='chat-box' onChange={(e) => {setMessageInput(e.target.value)}} value={messageInput} onKeyDown={handleKeyDown}>
                    </textarea>
                    <button className='chat-send-button' onClick={handleSendMessage}>
                        +
                    </button>
                </div>
            </div>
        </div>
    )
};

export default Home;