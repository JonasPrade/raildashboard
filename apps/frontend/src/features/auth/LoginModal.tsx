import { type FormEvent, useState } from "react";
import { Alert, Button, Modal, PasswordInput, Stack, TextInput } from "@mantine/core";
import { useAuth } from "../../lib/auth";

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

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
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
                    />
                    <Button type="submit" loading={loading} fullWidth mt="xs">
                        Anmelden
                    </Button>
                </Stack>
            </form>
        </Modal>
    );
}
