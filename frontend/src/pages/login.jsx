import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";
import Link from "next/link";
import { useState } from "react";
import { z } from "zod";

function isEmailValid(email) {
    const emailSchema = z.string().email();
    var valid = true;
    try {
        emailSchema.parse(email);
    } catch {
        valid = false;
    }
    return valid;
}
function isPasswordValid(password) {
    return password.length > 8;
}

export default function Login() {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [showEmailError, setShowEmailError] = useState(false);
    const [showPasswordError, setShowPasswordError] = useState(false);
    return (
        <div className="grid place-items-center h-screen">
            <div className="p-14 w-2/6 shadow-[rgba(0,_0,_0,_0.1)_0px_4px_6px_-1px,_rgba(0,_0,_0,_0.06)_0px_2px_4px_-1px]">
                <div className="font-semibold text-xl py-5">Sign In</div>
                <TextField
                    error={showEmailError}
                    id="outlined-basic"
                    label="email"
                    helperText={showEmailError && "Invalid Email"}
                    className="w-full"
                    onChange={(e) => {
                        setEmail(e.target.value);
                        showEmailError &&
                            setShowEmailError(!isEmailValid(e.target.value));
                    }}
                    onBlur={(e) => {
                        setShowEmailError(!isEmailValid(e.target.value));
                    }}
                />
                <TextField
                    id="outlined-password-input"
                    type="password"
                    className="w-full my-6"
                    error={showPasswordError}
                    helperText={showPasswordError && "Invalid Password"}
                    onChange={(e) => {
                        setPassword(e.target.value);
                        showPasswordError &&
                            setShowPasswordError(
                                !isPasswordValid(e.target.value)
                            );
                    }}
                    onBlur={(e) => {
                        setShowPasswordError(!isPasswordValid(e.target.value));
                    }}
                    label="password"
                    autoComplete="current-password"
                />
                <div className="flex justify-between pt-8">
                    <Link className="text-base" href="/">
                        Forgot password
                    </Link>
                    <Button
                        submit
                        disabled={
                            !isEmailValid(email) || !isPasswordValid(password)
                        }
                        variant="contained"
                    >
                        next
                    </Button>
                </div>
            </div>
        </div>
    );
}
