import { useNavigate } from "react-router-dom";
import { useContext, useEffect, useState } from "react";
import { AppContext, UserContext, SettingsContext, type Session } from '../../App';
import { Button } from "@/components/ui/button";
import { Settings, ChevronsLeft, Menu, Contact, Info, ChevronUp, MessageCirclePlus, UserRound, HomeIcon } from "lucide-react";
import ContactForm from "../contact/Contact"
import {
    Dialog,
    DialogTrigger,
} from "@/components/ui/dialog"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  useSidebar,
} from "@/components/ui/sidebar"
import { useIsMobile } from "@/hooks/use-mobile"
import SettingsApp from "../settings/Settings";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "../ui/dropdown-menu";
import { Login } from "../login/Login";

function AppSidebarControlButton({open, isMobile, setOpen} : {open: boolean, isMobile: boolean, setOpen: React.Dispatch<React.SetStateAction<boolean>>}) {
    const { setOpenMobile, openMobile } = useSidebar()

    return (
        <Button
            variant="outline"
            size="icon"
            className={`fixed top-4 z-50 h-10 w-10 rounded-full shadow-lg bg-neutral-600 hover:bg-neutral-500 border-gray-800 transition-all duration-300 hover:shadow-xl
            ${isMobile
                ? (openMobile ? 'left-[19rem]' : 'left-[1rem]')
                : (open ? 'left-[17rem]' : 'left-[4rem]')
            }
`}
            onClick={() => isMobile ? setOpenMobile(true) : setOpen(!open)}
            aria-label={open ? "Collapse sidebar" : "Expand sidebar"}
        >
            {open ? (
                <ChevronsLeft className="h-4 w-4" />
            ) : (
                <Menu className="h-4 w-4" />
            )}
        </Button>
    )
}

function Chats({ open, isLoggedIn, userSessions, handleSelectChat}: { open: boolean, isLoggedIn: boolean, userSessions: Session[], handleSelectChat: (id: string) => void }) {
    const { openMobile } = useSidebar()

    return (
        <>
        { ((open || openMobile) && (isLoggedIn ? userSessions.map((session) => (
            <SidebarMenuItem key={session.session_id}>
                <SidebarMenuButton onClick={() => handleSelectChat(session.session_id)} asChild className="text-gray-200 hover:bg-neutral-800 hover:text-white">
                    <span>{session.title}</span>
                </SidebarMenuButton>
            </SidebarMenuItem>
        )) : <></>))}
        </>
    )
}

function UserButton({ open, isLoggedIn, username }: {open: boolean, isLoggedIn: boolean, username: string}) {
    const { openMobile } = useSidebar()

    return (
        <>
            {(open || openMobile) && (
                <span className="truncate max-w-[8rem]">
                    {isLoggedIn ? username : "Log in"}
                </span>
            )}
        </>
    )
}

export default function AppSidebar() {
    const apiUrl = import.meta.env.VITE_APP_API_URL;
    const isMobile = useIsMobile()
    const navigate = useNavigate();
    const [ open, setOpen ] = useState(false)
    const { isLoggedIn, username, setUserCtx } = useContext(UserContext)
    const { userSessions, setAppCtx } = useContext(AppContext)
    const { setSettingsCtx } = useContext(SettingsContext)
    const [ loginDialogOpen, setLoginDialogOpen ] = useState(false)
    const [ settingsDialogOpen, setSettingsDialogOpen ] = useState(false)

    const sendGetSessions = async () => {
        console.log("trying to get sessions")

        try {
            const token = localStorage.getItem('token');
            const response = await fetch(`${apiUrl}/users/get-sessions`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                credentials: 'include',
            });

            if (!response.ok) {
                throw new Error(`Network response was not ok: ${response.statusText}`);
            }

            const data = await response.json();

            const result = data.result;

            if (!result)
                throw new Error(`Could not authorize user`);

            setAppCtx(prevSettings => ({
                ...prevSettings,
                userSessions: data.sessions
            }));

        } catch (error) {
            console.error("Error connecting to the backend:", error);

        } finally {
            // setIsResponding(false);
        }
    };
    
    const sendStartSession = async () => {
        console.log("trying to start session")

        try {
            const token = localStorage.getItem('token');
            const response = await fetch(`${apiUrl}/users/start-session`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,

                },
                credentials: 'include',
            });

            if (!response.ok) {
                throw new Error(`Network response was not ok: ${response.statusText}`);
            }

            const data = await response.json();

            const result = data.result;

            if (!result) {
                throw new Error(`Could not start session`);
            }

            return data.session_id;

        } catch (error) {
            console.error("Error connecting to the backend:", error);

        } finally {
            // setIsResponding(false);
        }
    };
    
    const handleLogout = () => {
        navigate(`/`);

        localStorage.removeItem('token');
        
        setUserCtx(prevSettings => ({
            ...prevSettings,
            isLoggedIn: false,
            userID: "",
            email: "",
            sessionID: "",
            username: "user",
            isActive: false,
            isAdmin: false,
            emailVerified: false,
            hasGeminiAPIKey: false,
        }));

        setAppCtx(prevSettings => ({
            ...prevSettings,
            userSessions: [],
        }));

        setSettingsCtx(prevSettings => ({
            ...prevSettings,
            geminiApiKey: "",
        }));
    }

    const handleCreateSession = async () => {
        const newSessionID = await sendStartSession();
        console.log(isLoggedIn, newSessionID, username);
        if (newSessionID !== null  && newSessionID !== undefined) {
            setUserCtx(prevSettings => ({
                ...prevSettings,
                sessionID: newSessionID
            }));
            setAppCtx(prev => ({
                ...prev,
                userSessions: [
                    ...prev.userSessions,
                    {
                        session_id: newSessionID,
                        title: "Untitled chat",
                        started_at: new Date(),

                    }
                ]
            }));
            console.log(isLoggedIn, newSessionID, username);
            navigate(`/chat/${newSessionID}`);
        }
    }

    const handleSelectChat = (id: string) => {
        console.log(userSessions);
        if (id !== null && id !== undefined) {
            setUserCtx(prevSettings => ({
                ...prevSettings,
                sessionID: id
            }));
            console.log(isLoggedIn, id, username);
            navigate(`/chat/${id}`);
        }
    }

    useEffect(() => {
        if (isLoggedIn)
            sendGetSessions()
    }, [isLoggedIn]);

    useEffect(() => {
        if (isMobile) {
            setOpen(false)
        }
    }, [isMobile])
    
    return (
        <>
        {open ? (
                <style>{`
                    [data-slot="sidebar-wrapper"] {
                        width: var(--sidebar-width) !important;
                        flex-shrink: 0; /* Prevents it from shrinking */
                    }
                `}</style>
            ) : (
                <style>{`
                    [data-slot="sidebar-wrapper"] {
                        display: contents;
                    }
                `}</style>
            )}
        <SidebarProvider open={open} onOpenChange={setOpen}>
            <Sidebar collapsible="icon" className="dark bg-gray-900 border-neutral-700 focus:outline-none">
                <SidebarContent className="bg-neutral-900">
                <SidebarGroup>
                    <SidebarGroupLabel className="text-gray-200">Movie Finder</SidebarGroupLabel>
                    <SidebarGroupContent>
                    <SidebarMenu>
                        <SidebarMenuItem key='home'>
                            <SidebarMenuButton asChild className="text-gray-200 hover:bg-neutral-800 hover:text-white">
                                <a href='/'>
                                    <HomeIcon />
                                    <span>Home</span>
                                </a>
                            </SidebarMenuButton>
                        </SidebarMenuItem>
                        <SidebarMenuItem key='start-chat'>
                            <SidebarMenuButton onClick={() => handleCreateSession()} asChild className="text-gray-200 hover:bg-neutral-800 hover:text-white">
                                <a>
                                    <MessageCirclePlus />
                                    <span>Start a new chat</span>
                                </a>
                            </SidebarMenuButton>
                        </SidebarMenuItem>
                    </SidebarMenu>
                    </SidebarGroupContent>
                </SidebarGroup>
                <SidebarGroup>
                    <SidebarGroupLabel className="text-gray-200">Previous chats</SidebarGroupLabel>
                    <SidebarGroupContent>
                    <SidebarMenu>
                        <Chats open={open} userSessions={userSessions} isLoggedIn={isLoggedIn} handleSelectChat={handleSelectChat}></Chats>
                    </SidebarMenu>
                    </SidebarGroupContent>
                </SidebarGroup>
                </SidebarContent>
                    <SidebarFooter className="text-gray-200 bg-neutral-900">
                    <SidebarMenu>
                        <SidebarMenuItem className="bg-neutral-900">
                            <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                    <SidebarMenuButton className="flex items-center space-x-2">
                                        <UserRound className="w-6 h-6 flex-shrink-0" />
                                            <UserButton open={open} isLoggedIn={isLoggedIn} username={username}></UserButton>
                                        <ChevronUp className={`ml-auto transition-transform ${open ? 'rotate-180' : ''}`} />
                                    </SidebarMenuButton>
                                </DropdownMenuTrigger>
                                { !isLoggedIn ? (
                                    <DropdownMenuContent
                                        side="top"
                                        className="w-[--radix-popper-anchor-width] dark bg-neutral-900"
                                    >
                                        <DropdownMenuItem onSelect={() => setLoginDialogOpen(true)}>
                                            <span>Log in</span>
                                        </DropdownMenuItem>
                                    </DropdownMenuContent>
                                ) :
                                    <DropdownMenuContent
                                        side="top"
                                        className="w-[--radix-popper-anchor-width] dark bg-neutral-900"
                                    >
                                            <DropdownMenuItem onSelect={() => setSettingsDialogOpen(true)}>
                                            <span>Settings</span>
                                        </DropdownMenuItem>
                                        <DropdownMenuItem onSelect={handleLogout}>
                                            <span>Sign out</span>
                                        </DropdownMenuItem>
                                    </DropdownMenuContent>
                                }
                            </DropdownMenu>
                        </SidebarMenuItem>
                    </SidebarMenu>
                </SidebarFooter>
            </Sidebar>
            <Dialog open={settingsDialogOpen} onOpenChange={setSettingsDialogOpen}>
                <SettingsApp/>
            </Dialog>
            <Dialog open={loginDialogOpen} onOpenChange={setLoginDialogOpen}>
                <Login />
            </Dialog>
            <AppSidebarControlButton isMobile={isMobile} open={open} setOpen={setOpen}/>
        </SidebarProvider>
        </>
    )
}