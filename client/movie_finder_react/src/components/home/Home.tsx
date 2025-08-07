import './Home.css'
import { useState, useEffect, useRef, useContext } from 'react';
import AppSidebar from "../sidebar/Sidebar"
import { motion, AnimatePresence } from "framer-motion";
import { Skeleton } from '../ui/skeleton';
import { UserContext } from '@/App';
import { useParams } from 'react-router-dom';

const Home = () => {
    const [messageInput, setMessageInput] = useState('');
    const [msgHistory, setMsgHistory] = useState<{ id: number, text: string, isUser: boolean, isLoading?: boolean }[]>([]);
    const [isResponding, setIsResponding] = useState(false);
    const chatDisplayRef = useRef<HTMLDivElement>(null);
    const { isLoggedIn, userID, sessionID, username, isActive, emailVerified } = useContext(UserContext);
    const { id } = useParams<{ id: string }>();

    const sendPromptToBackend = async (promptText: string, sid: string, skeletonMessageId: number) => {
        console.log(sessionID)

        if (!(isLoggedIn && sessionID !== "" && isActive && emailVerified))
            throw new Error(`User is not authorized`);

        setIsResponding(true);
        try {
            const response = await fetch('https://movie-finder-980543701851.europe-west1.run.app/api/process', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ prompt: promptText, session_id: sid }),
                credentials: 'include',
            });

            if (!response.ok) {
                throw new Error(`Network response was not ok: ${response.statusText}`);
            }

            const data = await response.json();

            setMsgHistory(prevMessages =>
                prevMessages.map(msg =>
                    msg.id === skeletonMessageId
                        ? { ...msg, text: data.answer, isLoading: false }
                        : msg
                )
            );

        } catch (error) {
            console.error("Error connecting to the backend:", error);
            setMsgHistory(prev => prev.filter(msg => msg.id !== skeletonMessageId));

        } finally {
            setIsResponding(false);
        }
    };

    const sendGetSession = async (sid: string) => {
        console.log("getting chat")

        if (!(isLoggedIn && isActive && emailVerified))
            throw new Error(`User is not authorized`);

        try {
            const response = await fetch('https://movie-finder-980543701851.europe-west1.run.app/api/user/get-chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ session_id: sid }),
                credentials: 'include',
            });

            if (!response.ok) {
                throw new Error(`Network response was not ok: ${response.statusText}`);
            }

            const data = await response.json();
            const result = data.result;

            console.log("got messages: ", data)

            if (result && data.messages) {
                const formattedMessages = data.messages.map((msg: { sender: string, message: string }, index: number) => ({
                    id: index,
                    text: msg.message,
                    isUser: msg.sender === 'user',
                    isLoading: false,
                }));
                setMsgHistory(formattedMessages);
            } else {
                setMsgHistory([]);
            }
        } catch (error) {
            console.error("Error connecting to the backend:", error);
            setMsgHistory([]);
        }
    };

    const handleGetChat = (id: string) => {
        sendGetSession(id);
    }

    const handleSendMessage = () => {
        const trimmedMessage = messageInput.trim();
        if (trimmedMessage && !isResponding) {
            const userMessage = { id: Date.now(), text: trimmedMessage, isUser: true };
            const skeletonMessageId = Date.now() + 1;
            const skeletonMessage = { id: skeletonMessageId, text: '', isUser: false, isLoading: true };

            setMsgHistory(prevMessages => [...prevMessages, userMessage, skeletonMessage]);
            setMessageInput('');
            sendPromptToBackend(trimmedMessage, sessionID, skeletonMessageId);
        }
    };

    const handleKeyDown = (event: React.KeyboardEvent) => {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            handleSendMessage();
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

    useEffect(() => {
        console.log("from useffect for loading chat")

        if (
            isLoggedIn &&
            id &&
            sessionID !== "" &&
            userID !== -1
        ) {
            console.log("getting chat useeffect")
            handleGetChat(sessionID);
        }
    }, [id, isLoggedIn, sessionID, userID]);

    return (
        <div className='main-container flex h-screen'>
            <AppSidebar />
            <div className='io-container flex flex-col flex-1 h-full'>
                <div className='flex-1 overflow-auto' ref={chatDisplayRef}>
                    <div className='flex flex-col h-full'>
                        <div className='flex-1 flex flex-col justify-end'>
                            <div className='w-full max-w-5xl mx-auto px-4'>
                                {msgHistory.length === 0 && !isResponding ? (
                                    <AnimatePresence>
                                        <motion.div
                                            key="hello-user"
                                            className="flex items-center justify-center h-full min-h-[50vh]"
                                            initial={{ opacity: 0, scale: 0.95 }}
                                            animate={{ opacity: 1, scale: 1 }}
                                            exit={{ opacity: 0, scale: 0.95 }}
                                            transition={{ duration: 1.0, ease: "easeInOut" }}
                                        >
                                            <h1 className="font-family-Onest text-center text-white text-4xl font-extrabold tracking-tight whitespace-nowrap">
                                                Hello, {username}
                                            </h1>
                                        </motion.div>
                                    </AnimatePresence>
                                ) : (
                                    <div className="py-4">
                                        <div className="flex flex-col text-white p-2">
                                            {msgHistory.map(msg => (
                                                <motion.div
                                                    layout="position"
                                                    key={msg.id}
                                                    initial={{ opacity: 0, y: 15, scale: 0.98 }}
                                                    animate={{ opacity: 1, y: 0, scale: 1 }}
                                                    transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
                                                    className={`${msg.isUser ? 'user-message-container' : 'ai-message-container'} flex items-center`}
                                                >
                                                    <AnimatePresence mode="wait">
                                                        <motion.div
                                                            key={msg.isLoading ? 'skeleton' : 'text'}
                                                            initial={{ opacity: 0, y: -10 }}
                                                            animate={{ opacity: 1, y: 0 }}
                                                            exit={{ opacity: 0, y: 10 }}
                                                            transition={{ duration: 0.3, ease: 'easeInOut' }}
                                                        >
                                                            {msg.isLoading ? (
                                                                <div className='message'>
                                                                    <Skeleton className="dark h-4 w-48 mb-2" />
                                                                    <Skeleton className="dark h-4 w-32" />
                                                                </div>
                                                            ) : (
                                                                <p className='message'>{msg.text}</p>
                                                            )}
                                                        </motion.div>
                                                    </AnimatePresence>
                                                </motion.div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>

                <div className='flex-shrink-0 p-4 border-t border-gray-700/30'>
                    <div className='flex w-full max-w-4xl rounded-3xl bg-[rgb(29,29,29)] mx-auto relative items-center justify-center'>
                        <textarea
                            className='chat-box flex-1'
                            onChange={(e) => setMessageInput(e.target.value)}
                            value={messageInput}
                            onKeyDown={handleKeyDown}
                            placeholder={isResponding ? "Waiting for response..." : "Type a message..."}
                            disabled={isResponding || !isLoggedIn || !emailVerified || !isActive}
                        />
                        <button className='chat-send-button ml-2' onClick={handleSendMessage} disabled={isResponding || !isLoggedIn || !emailVerified || !isActive}>
                            +
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
};

export default Home;