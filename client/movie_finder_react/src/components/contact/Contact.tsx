import './Contact.css';
import React from 'react';
import { Button } from "@/components/ui/button"
import {
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  RadioGroup,
  RadioGroupItem,
} from "@/components/ui/radio-group"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from '../ui/textarea';
import { useState, useEffect } from "react";
import { AlertCircleIcon, CheckCircle2Icon } from "lucide-react"
import {
    Alert,
    AlertDescription,
    AlertTitle,
} from "@/components/ui/alert"
import { motion, AnimatePresence } from "framer-motion";

function AlertSend() {
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
                <AlertTitle>Success! Your message has been sent</AlertTitle>
                <AlertDescription>
                    Thank you for providing feedback!
                </AlertDescription>
            </Alert>
        </motion.div>
    );
}

export function ContactForm() {
    const [submitted, setSubmitted] = useState(false)

    const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        setSubmitted(true);
    };

    useEffect(() => {
        const timer = setTimeout(() => {
            setSubmitted(false)
        }, 3500);

        return () => clearTimeout(timer);
    }, [submitted])

    return (
        <DialogContent className="dark text-neutral-300">
            <motion.div
                layout
                transition={{ layout: { duration: 0.2, ease: "easeInOut" } }}
                className=""
            >
                <AnimatePresence mode='wait'>
                    {submitted && <AlertSend />}
                </AnimatePresence>
                <DialogHeader>
                    <DialogTitle>Contact us</DialogTitle>
                    <DialogDescription>Fill out the fields to send us feedback!</DialogDescription>
                </DialogHeader>
                <form className='mt-4' onSubmit={handleSubmit}>
                    <div>
                        <div className='mb-4'>
                            <Label className='mb-2' htmlFor='fn1'>Full name</Label>
                            <Input type='text' name='full-name' id='fn1'></Input>
                        </div>
                        <div className='mb-4'>
                            <Label className='mb-2' htmlFor='email1'>Email</Label>
                            <Input type='email' name='email' id='email1'></Input>
                        </div>
                        <div className='mb-4'>
                            <Label htmlFor='radio-gender'>Gender</Label>
                            <RadioGroup id='radio-gender' className='flex flex-row'>
                                <div className='mt-4 mr-4'>
                                    <Label className='mb-2' htmlFor='m'>Male</Label>
                                    <RadioGroupItem value='male' id='m'></RadioGroupItem>
                                </div>
                                <div className='mt-4 mr-4'>
                                    <Label className='mb-2' htmlFor='f'>Female</Label>
                                    <RadioGroupItem value='female' id='f'></RadioGroupItem>
                                </div>
                            </RadioGroup>
                        </div>
                        <Label htmlFor='wdyf'>Where did you find out about us?</Label>
                        <div id='wdyf' className='mb-2 flex flex-row w-full h-full align-center'>
                            <div className='my-4 mr-4'>
                                <Checkbox id='wom'></Checkbox>
                                <Label className='mt-2' htmlFor='wom'>Word of mouth</Label>
                            </div>
                            <div className='my-4 mr-4'>
                                <Checkbox id='sn'></Checkbox>
                                <Label className='mt-2' htmlFor='sn'>Social network</Label>
                            </div>
                            <div className='my-4 mr-4'>
                                <Checkbox id='search'></Checkbox>
                                <Label className='mt-2' htmlFor='search'>Search</Label>
                            </div>
                        </div>
                        <div className='mb-4'>
                            <Label className='mb-4' htmlFor='msg'>Feel free to leave a message!</Label>
                            <Textarea className='resize-none h-16' id='msg'>
                            </Textarea>
                        </div>
                        <div className="mb-4">
                            <div className="flex justify-between items-center w-full">
                                <Label htmlFor="nl" className="mb-0">Would you like to subscribe to our newsletter?</Label>
                                <Checkbox id="nl"/>
                            </div>
                        </div>
                    </div>
                    <DialogFooter>
                        <DialogClose asChild>
                            <Button>Cancel</Button>
                        </DialogClose>
                        <Button type="submit">Send</Button>
                    </DialogFooter>
                </form>
            </motion.div>
        </DialogContent>
    )
}