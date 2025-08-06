import { Button } from "@/components/ui/button"
import {
    DialogClose,
    DialogContent,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
    Tabs,
    TabsContent,
    TabsList,
    TabsTrigger,
} from "@/components/ui/tabs"
import { useState, useEffect, useContext } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { CheckCircle2Icon } from "lucide-react"
import {
    Alert,
    AlertTitle,
} from "@/components/ui/alert"
import { SettingsContext } from '../../App';

function AlertSave() {
    return (
        <motion.div
            key="alert"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.4, ease: "easeInOut" }}
            style={{ overflow: "hidden" }} // important!
            className='dark mb-4'
        >
            <Alert>
                <CheckCircle2Icon />
                <AlertTitle>Your settings have been saved</AlertTitle>
            </Alert>
        </motion.div>
    );
}

export default function SettingsApp() {
    const [submitted, setSubmitted] = useState(false)
    const { geminiApiKey, setSettingsCtx } = useContext(SettingsContext);

    const [localSettings, setLocalSettings] = useState({
        // name: displayName,
        geminiApiKey: geminiApiKey,
    });

    const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        setSettingsCtx(prevSettings => ({
            ...prevSettings,
            //displayName: localSettings.name,
            geminiApiKey: localSettings.geminiApiKey,
        }));
        setSubmitted(true);
    };

    const handleInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        const { name, value } = event.target;
        setLocalSettings(prevSettings => ({
            ...prevSettings,
            [name]: value,
        }));
    };

    useEffect(() => {
        const timer = setTimeout(() => {
            setSubmitted(false)
        }, 3500);

        return () => clearTimeout(timer);
    }, [submitted])

    return (
        <div>
            <DialogContent className="dark text-neutral-300">
                <motion.div
                    layout
                    transition={{ layout: { duration: 0.2, ease: "easeInOut" } }}
                    className=""
                >
                    <AnimatePresence mode='wait'>
                        {submitted && <AlertSave />}
                    </AnimatePresence>
                    <DialogHeader className="mb-8">
                        <DialogTitle>Settings</DialogTitle>
                    </DialogHeader>
                    <Tabs defaultValue="account">
                        <TabsList>
                            <TabsTrigger value="account">Account</TabsTrigger>
                            <TabsTrigger value="api">API</TabsTrigger>
                        </TabsList>
                        <TabsContent value="account">
                            <form className='mt-4' onSubmit={handleSubmit}>
                                <div>
                                    <div className='mb-4'>
                                        <Label className='mb-4' htmlFor='n1'>Name</Label>
                                        <Input onChange={handleInputChange} type='text' name='name' id='n1'></Input>
                                    </div>
                                </div>
                                <DialogFooter>
                                    <DialogClose asChild>
                                        <Button>Cancel</Button>
                                    </DialogClose>
                                    <Button type="submit">Save</Button>
                                </DialogFooter>
                            </form>
                        </TabsContent>
                        <TabsContent value="api">
                            <form className='mt-4' onSubmit={handleSubmit}>
                                <div>
                                    <div className='mb-4'>
                                        <Label className='mb-4' htmlFor='geminiapikey'>Gemini API key</Label>
                                        <Input value={localSettings.geminiApiKey} onChange={handleInputChange} type='text' name='gemini-api-key' id='geminiapikey'></Input>
                                    </div>
                                </div>
                                <DialogFooter>
                                    <DialogClose asChild>
                                        <Button>Cancel</Button>
                                    </DialogClose>
                                    <Button type="submit">Save</Button>
                                </DialogFooter>
                            </form>
                        </TabsContent>
                    </Tabs>
                </motion.div>
            </DialogContent>
        </div>
    )
}