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
import { useContext, useEffect, useState } from "react"

export function Login() {
    const { setUserCtx } = useContext(UserContext);
    const [localLoginInfo, setLocalLoginInfo] = useState({
        email: "",
        password: "",
    });
    const [ submitted, setSubmitted ] = useState(false)

    const sendLoginInfo = async (email: string, password: string) => {
        try {
            const response = await fetch('https://movie-finder-980543701851.europe-west1.run.app/api/user/log-in', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email, password }),
                credentials: 'include',
            });

            if (!response.ok) {
                throw new Error(`Network response was not ok: ${response.statusText}`);
            }

            const data = await response.json();

            const result = data.result;

            if (!result)
                throw new Error(`Could not authorize user`);

            const lUserID = parseInt(data.user_id);
            const lUsername = data.username;
            const lIsActive = data.is_active;
            const lIsAdmin = data.is_admin;
            const lEmailVerified = data.email_verified;
            const lHasGeminiApiKey = data.has_gemini_api_key;

            setUserCtx(prevSettings => ({
                ...prevSettings,
                isLoggedIn: true,
                userID: lUserID,
                username: lUsername,
                isActive: lIsActive,
                isAdmin: lIsAdmin,
                emailVerified: lEmailVerified,
                hasGeminiAPIKey: lHasGeminiApiKey,
            }));

        } catch (error) {
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

    const handleInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        const { id, value } = event.target;
        setLocalLoginInfo(prevSettings => ({
            ...prevSettings,
            [id]: value,
        }));
    };

    useEffect(() => {
        const timer = setTimeout(() => {
            setSubmitted(false)
        }, 3500);

        return () => clearTimeout(timer);
    }, [submitted])

    return (
        <DialogContent className="p-0 m-0 dark border-none shadow-none w-auto max-w-max">
            <DialogClose className="absolute top-4 right-4" aria-label="Close"></DialogClose>
            <VisuallyHidden asChild>
                <DialogHeader className="mb-8">
                    <DialogTitle>Login</DialogTitle>
                </DialogHeader>
            </VisuallyHidden>
            <Card className="w-[calc(100vw-1rem)] max-w-sm">
                <CardHeader>
                    <CardTitle>Login to your account</CardTitle>
                    <CardDescription>
                        Enter your email below to login to your account
                    </CardDescription>
                    <CardAction>
                        <Button variant="link">Sign Up</Button>
                    </CardAction>
                </CardHeader>
                <CardContent>
                    <form id="loginForm" onSubmit={handleLogin}>
                        <div className="flex flex-col gap-6">
                            <div className="grid gap-2">
                                <Label htmlFor="email">Email</Label>
                                <Input
                                    value={localLoginInfo.email}
                                    onChange={handleInputChange}
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
                                    onChange={handleInputChange}
                                    id="password"
                                    name="password"
                                    type="password"
                                    required
                                />
                            </div>
                        </div>
                    </form>
                </CardContent>
                <CardFooter className="flex-col gap-2">
                    <Button type="submit" form="loginForm" className="w-full">
                        Login
                    </Button>
                    <Button variant="outline" className="w-full">
                        Login with Google
                    </Button>
                </CardFooter>
            </Card>
        </DialogContent>
    )
}