import { useNavigate } from "react-router-dom";
import { useContext, useEffect, useState } from "react";
import { AppContext, UserContext, SettingsContext } from '../../App';
import { Button } from "@/components/ui/button";
import { Settings, ChevronsLeft, Menu, Contact, Info, ChevronUp } from "lucide-react";
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
} from "@/components/ui/sidebar"
import SettingsApp from "../settings/Settings";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "../ui/dropdown-menu";
import { Login } from "../login/Login";

export default function AppSidebar() {
    const navigate = useNavigate();
    const [ open, setOpen ] = useState(true)
    const { isLoggedIn, username, setUserCtx } = useContext(UserContext)
    const { userSessions, setAppCtx } = useContext(AppContext)
    const { setSettingsCtx } = useContext(SettingsContext)
    const [ loginDialogOpen, setLoginDialogOpen ] = useState(false)

    const sendLogoutRequest = async () => {
        console.log("trying to log out")

        try {
            const response = await fetch('https://movie-finder-980543701851.europe-west1.run.app/api/user/log-out', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
            });

            if (!response.ok) {
                throw new Error(`Network response was not ok: ${response.statusText}`);
            }

            const data = await response.json();

            const result = data.result;

            if (!result)
                throw new Error(`Could not log user out`);

            setUserCtx(prevSettings => ({
                ...prevSettings,
                isLoggedIn: false,
                userID: -1,
                email: "",
                sessionID: -1,
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

        } catch (error) {
            console.error("Error connecting to the backend:", error);
        } finally {
            // setIsResponding(false);
        }
    };

    const sendGetSessions = async () => {
        console.log("trying to get sessions")

        try {
            const response = await fetch('https://movie-finder-980543701851.europe-west1.run.app/api/user/get-sessions', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
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
            const response = await fetch('https://movie-finder-980543701851.europe-west1.run.app/api/user/start-session', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
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
        sendLogoutRequest()
    }

    const handleCreateSession = async () => {
        const newSessionID = await sendStartSession();
        console.log(isLoggedIn, newSessionID, username);
        if (newSessionID !== null  && newSessionID !== undefined) {
            setUserCtx(prevSettings => ({
                ...prevSettings,
                sessionID: newSessionID
            }));
            console.log(isLoggedIn, newSessionID, username);
            navigate(`/chat/${newSessionID}`);
        }
    }

    const handleSelectChat = (id: number) => {
        console.log(userSessions);
        navigate(`/chat/${id}`);
    }

    useEffect(() => {
        if (isLoggedIn)
            sendGetSessions()
    }, [isLoggedIn]);
    
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
            <Sidebar collapsible="icon" className="dark bg-gray-900 border-gray-700">
                <SidebarContent className="bg-neutral-900">
                <SidebarGroup>
                    <SidebarGroupLabel className="text-gray-200">Movie Finder</SidebarGroupLabel>
                    <SidebarGroupContent>
                    <SidebarMenu>
                        <SidebarMenuItem key='contact'>
                            <Dialog>
                                <DialogTrigger asChild>
                                    <SidebarMenuButton asChild className="text-gray-200 hover:bg-neutral-800 hover:text-white">
                                        <a>
                                            <Contact />
                                            <span>Contact</span>
                                        </a>
                                    </SidebarMenuButton>
                                </DialogTrigger>
                                <ContactForm></ContactForm>
                            </Dialog>
                        </SidebarMenuItem>
                        <SidebarMenuItem key='about-us'>
                            <SidebarMenuButton asChild className="text-gray-200 hover:bg-neutral-800 hover:text-white">
                                <a href='/about'>
                                    <Info/>
                                    <span>About us</span>
                                </a>
                            </SidebarMenuButton>
                        </SidebarMenuItem>
                        <SidebarMenuItem key='settings'>
                            <SidebarMenuButton asChild className="text-gray-200 hover:bg-neutral-800 hover:text-white">
                                <Dialog>
                                    <DialogTrigger asChild>
                                        <SidebarMenuButton asChild className="text-gray-200 hover:bg-neutral-800 hover:text-white">
                                            <a>
                                                <Settings />
                                                <span>Settings</span>
                                            </a>
                                        </SidebarMenuButton>
                                    </DialogTrigger>
                                    <SettingsApp></SettingsApp>
                                </Dialog>
                            </SidebarMenuButton>
                        </SidebarMenuItem>
                        <SidebarMenuItem key='start-chat'>
                            <SidebarMenuButton onClick={() => handleCreateSession()} asChild className="text-gray-200 hover:bg-neutral-800 hover:text-white">
                                <span>Start new chat</span>
                            </SidebarMenuButton>
                        </SidebarMenuItem>
                    </SidebarMenu>
                    </SidebarGroupContent>
                </SidebarGroup>
                <SidebarGroup>
                    <SidebarGroupLabel className="text-gray-200">Previous chats</SidebarGroupLabel>
                    <SidebarGroupContent>
                    <SidebarMenu>
                        { isLoggedIn ? userSessions.map((session) => (
                            <SidebarMenuItem key={session.session_id}>
                                <SidebarMenuButton onClick={() => handleSelectChat(session.session_id)} asChild>
                                    <span>{session.title}</span>
                                </SidebarMenuButton>
                            </SidebarMenuItem>
                        )) : <></>}
                    </SidebarMenu>
                    </SidebarGroupContent>
                </SidebarGroup>
                </SidebarContent>
                    <SidebarFooter className="text-gray-200 bg-neutral-900">
                    <SidebarMenu>
                        <SidebarMenuItem className="bg-neutral-900">
                            <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                    <SidebarMenuButton>
                                        { isLoggedIn ? (
                                            <span>{username}</span>
                                        ) : (
                                            <span>Logged out</span>
                                        )
                                        }
                                        <ChevronUp className="ml-auto" />
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
                                        <DropdownMenuItem>
                                            <span>Account</span>
                                        </DropdownMenuItem>
                                        <DropdownMenuItem>
                                            <span>Billing</span>
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
            <Dialog open={loginDialogOpen} onOpenChange={setLoginDialogOpen}>
                <Login />
            </Dialog>
            <Button
                variant="outline"
                size="icon"
                className={`fixed top-4 z-50 h-10 w-10 rounded-full shadow-lg bg-neutral-600 hover:bg-neutral-500 border-gray-800 transition-all duration-300 hover:shadow-xl ${
                    open ? 'left-67' : 'left-15'
                }`}
                onClick={() => setOpen(!open)}
                aria-label={open ? "Collapse sidebar" : "Expand sidebar"}
            >
                {open ? (
                    <ChevronsLeft className="h-4 w-4" />
                ) : (
                    <Menu className="h-4 w-4" />
                )}
            </Button>
        </SidebarProvider>
        </>
    )
}