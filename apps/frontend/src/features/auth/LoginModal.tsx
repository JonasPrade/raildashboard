import { type FormEvent, useState } from "react";
import { Alert, Modal, PasswordInput, Stack, TextInput } from "@mantine/core";
import { useAuth } from "../../lib/auth";
import { ChronicleButton } from "../../components/chronicle";

type Props = {
    opened: boolean;
    onClose: () => void;
};

export function LoginModal({ opened, onClose }: Props) {
    const { login } = useAuth();
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    const doLogin = async () => {
        setError(null);
        setLoading(true);
        try {
            await login(username, password);
            setUsername("");
            setPassword("");
            onClose();
        } catch {
            setError("Ungültige Anmeldedaten");
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = (e: FormEvent) => {
        e.preventDefault();
        void doLogin();
    };

    const handleClose = () => {
        setError(null);
        onClose();
    };

    return (
        <Modal opened={opened} onClose={handleClose} title="Anmelden" size="sm">
            <form onSubmit={handleSubmit}>
                <Stack gap="sm">
                    {error && (
                        <Alert color="red" variant="light">
                            {error}
                        </Alert>
                    )}
                    <TextInput
                        label="Benutzername"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        autoComplete="username"
                        required
                    />
                    <PasswordInput
                        label="Passwort"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        autoComplete="current-password"
                        required
                        onKeyDown={(e) => {
                            if (e.key === "Enter") {
                                e.preventDefault();
                                void doLogin();
                            }
                        }}
                    />
                    <ChronicleButton type="submit" disabled={loading} style={{ width: "100%", marginTop: "0.5rem" }}>
                        {loading ? "…" : "Anmelden"}
                    </ChronicleButton>
                </Stack>
            </form>
        </Modal>
    );
}
