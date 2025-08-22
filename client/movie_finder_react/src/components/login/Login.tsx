import { Button } from "@/components/ui/button"
import {
    Card,
    CardAction,
    CardContent,
    CardDescription,
    CardFooter,
    CardHeader,
    CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
    DialogClose,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog"
import { VisuallyHidden } from "@radix-ui/react-visually-hidden"
import { UserContext } from '@/App';
import type { JWTPayload } from '@/App';
import { useContext, useEffect, useState } from "react"
import { jwtDecode } from 'jwt-decode'
import { motion, AnimatePresence } from "framer-motion"
import { CheckCircle2Icon } from "lucide-react"
import {
    Alert,
    AlertTitle,
} from "@/components/ui/alert"

export function Login() {
    const apiUrl = import.meta.env.VITE_APP_API_URL;
    const { setUserCtx, username } = useContext(UserContext);
    const [localLoginInfo, setLocalLoginInfo] = useState({
        email: "",
        password: "",
    });
    const [localSignupInfo, setLocalSignupInfo] = useState({
        email: "",
        password: "",
    });
    const [ formState, setFormState ] = useState('login')
    const [ submitted, setSubmitted ] = useState(false)
    const [ successAction, setSuccessAction ] = useState('success')

    function AlertSave() {
        return (
            <motion.div
                key="alert"
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.4, ease: "easeInOut" }}
                style={{ overflow: "hidden" }}
                className='dark mb-4 w-full max-w-sm'
            >
                <Alert>
                    <CheckCircle2Icon />
                    <AlertTitle>
                        { formState === 'login' ? (
                            (successAction === 'success' ? (
                                `You have successfully logged in, welcome ${username}`
                            ) : ("Failed to log in, incorrect email or password"))
                        ) : (
                            (successAction === 'success' ? (
                                "Successfully created account"
                            ): ("Failed to create account, try with different email/password"))
                        )}
                    </AlertTitle>
                </Alert>
            </motion.div>
        );
    }

    const sendLoginInfo = async (email: string, password: string) => {
        try {
            const response = await fetch(`${apiUrl}/users/log-in`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email, password }),
                credentials: 'include',
            });

            if (!response.ok) {
                setSuccessAction('fail')
                throw new Error(`Network response was not ok: ${response.statusText}`);
            }

            const data = await response.json();

            const result = data.result;

            if (!result) {
                setSuccessAction('fail')
                throw new Error(`Could not authorize user`);
            }

            if (data.access_token) {
                localStorage.setItem('token', data.access_token);
            }
           
            setSuccessAction('success')
            
            const user = jwtDecode<JWTPayload>(data.access_token)

            const lUserID = String(user.sub);
            const lUsername = String(user.username);
            const lIsActive = Boolean(user.is_active);
            const lIsAdmin = Boolean(user.is_admin);
            const lEmailVerified = Boolean(user.email_verified);

            setUserCtx(prevSettings => ({
                ...prevSettings,
                isLoggedIn: true,
                userID: lUserID,
                username: lUsername,
                isActive: lIsActive,
                isAdmin: lIsAdmin,
                emailVerified: lEmailVerified,
            }));

        } catch (error) {
            setSuccessAction('fail')
            console.error("Error connecting to the backend:", error);

        } finally {
            // setIsResponding(false);
        }
    };

    const sendSignupInfo = async (email: string, password: string) => {
        try {
            const response = await fetch(`${apiUrl}/users/sign-up`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email, password }),
                credentials: 'include',
            });

            if (!response.ok) {
                setSuccessAction('fail')
                throw new Error(`Network response was not ok: ${response.statusText}`);
            }

            const data = await response.json();

            const result = data.result;

            if (!result) {
                setSuccessAction('fail')
                throw new Error(`Could not create account`);
            }

            setSuccessAction('success')

            console.log("account has been created with id: ", data.user_id)
        } catch (error) {
            setSuccessAction('fail')
            console.error("Error connecting to the backend:", error);

        } finally {
            // setIsResponding(false);
        }
    };

    const handleLogin = (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault();

        const { email, password } = localLoginInfo;

        if (email && password) {
            sendLoginInfo(email, password);
        }

        setSubmitted(true)
    };

    const handleSignup = (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault();

        const { email, password } = localSignupInfo;

        if (email && password) {
            sendSignupInfo(email, password);
        }

        setSubmitted(true)
    };

    const handleLoginInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        const { id, value } = event.target;
        setLocalLoginInfo(prevSettings => ({
            ...prevSettings,
            [id]: value,
        }));
    };

    const handleSignupInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        const { id, value } = event.target;
        setLocalSignupInfo(prevSettings => ({
            ...prevSettings,
            [id]: value,
        }));
    };

    useEffect(() => {
        const timer = setTimeout(() => {
            setSubmitted(false)
            setSuccessAction('')
        }, 3500);

        return () => clearTimeout(timer);
    }, [submitted])

    return (
        <DialogContent className="p-0 m-0 dark border-none shadow-none w-auto max-w-max">
            <motion.div
                layout
                transition={{ layout: { duration: 0.2, ease: "easeInOut" } }}
                className=""
            >
                <AnimatePresence mode='wait'>
                    {(submitted && successAction !== '') && <AlertSave />}
                </AnimatePresence>
                <DialogClose className="absolute top-4 right-4" aria-label="Close"></DialogClose>
                <VisuallyHidden asChild>
                    <DialogHeader className="mb-8">
                        <DialogTitle>{ formState === 'login' ? ("Log in") : ("Sign up")}</DialogTitle>
                    </DialogHeader>
                </VisuallyHidden>
                <Card className="w-[calc(100vw-1rem)] max-w-sm">
                    <CardHeader>
                        <CardTitle>{formState === 'login' ? ("Log in to your account") : ("Create an account") }</CardTitle>
                        <CardDescription>
                            {formState === 'login' ? "Enter your email below to log in to your account" :
                            ("Enter you email below to create your account")}
                        </CardDescription>
                        <CardAction>
                            < Button 
                                onClick={() => formState === 'login' ? setFormState('signup') : setFormState('login')} 
                                variant="link">{formState === 'login' ? ("Sign up") : ("Log in")}
                            </Button>
                        </CardAction>
                    </CardHeader>
                    <CardContent>
                        {formState === 'login' ? (
                            <form id="loginForm" onSubmit={handleLogin}>
                                <div className="flex flex-col gap-6">
                                    <div className="grid gap-2">
                                        <Label htmlFor="email">Email</Label>
                                        <Input
                                            value={localLoginInfo.email}
                                            onChange={handleLoginInputChange}
                                            id="email"
                                            name="email"
                                            type="email"
                                            required
                                        />
                                    </div>
                                    <div className="grid gap-2">
                                        <div className="flex items-center">
                                            <Label htmlFor="password">Password</Label>
                                            <a
                                                href="#"
                                                className="ml-auto inline-block text-sm underline-offset-4 hover:underline"
                                            >
                                                Forgot your password?
                                            </a>
                                        </div>
                                        <Input
                                            value={localLoginInfo.password}
                                            onChange={handleLoginInputChange}
                                            id="password"
                                            name="password"
                                            type="password"
                                            required
                                        />
                                    </div>
                                </div>
                            </form>) : (
                            <form id="signupForm" onSubmit={handleSignup}>
                                <div className="flex flex-col gap-6">
                                    <div className="grid gap-2">
                                        <Label htmlFor="email">Email</Label>
                                        <Input
                                            value={localSignupInfo.email}
                                            onChange={handleSignupInputChange}
                                            id="email"
                                            name="email"
                                            type="email"
                                            required
                                        />
                                    </div>
                                    <div className="grid gap-2">
                                        <Input
                                            value={localSignupInfo.password}
                                            onChange={handleSignupInputChange}
                                            id="password"
                                            name="password"
                                            type="password"
                                            required
                                        />
                                    </div>
                                </div>
                            </form>
                            )}
                    </CardContent>
                    {formState === 'login' ? (
                        <CardFooter className="flex-col gap-2">
                            <Button type="submit" form="loginForm" className="w-full">
                                Login
                            </Button>
                            <Button variant="outline" className="w-full">
                                Login with Google
                            </Button>
                        </CardFooter>
                    ): (
                        <CardFooter className="flex-col gap-2">
                            <Button type="submit" form="signupForm" className="w-full">
                                Sign up
                            </Button>
                            <Button variant="outline" className="w-full">
                                Sign up with Google
                            </Button>
                        </CardFooter>
                    )}
                </Card>
            </motion.div>
        </DialogContent>
    )
}