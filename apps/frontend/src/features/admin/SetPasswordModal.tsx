import { type FormEvent, useState } from "react";
import { Alert, Button, Modal, PasswordInput, Stack } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useSetUserPassword } from "../../shared/api/queries";

type Props = {
    opened: boolean;
    onClose: () => void;
    userId: number;
    username: string;
};

export function SetPasswordModal({ opened, onClose, userId, username }: Props) {
    const [password, setPassword] = useState("");
    const [passwordConfirm, setPasswordConfirm] = useState("");
    const [error, setError] = useState<string | null>(null);

    const setUserPassword = useSetUserPassword();

    const reset = () => {
        setPassword("");
        setPasswordConfirm("");
        setError(null);
    };

    const handleClose = () => {
        reset();
        onClose();
    };

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        setError(null);

        if (password.length < 8) {
            setError("Passwort muss mindestens 8 Zeichen lang sein.");
            return;
        }
        if (password !== passwordConfirm) {
            setError("Passwörter stimmen nicht überein.");
            return;
        }

        try {
            await setUserPassword.mutateAsync({ userId, password });
            notifications.show({
                color: "green",
                message: `Passwort von „${username}" wurde geändert.`,
            });
            reset();
            onClose();
        } catch {
            setError("Passwort konnte nicht geändert werden.");
        }
    };

    return (
        <Modal opened={opened} onClose={handleClose} title={`Passwort setzen: ${username}`} size="sm">
            <form onSubmit={handleSubmit}>
                <Stack gap="sm">
                    {error && (
                        <Alert color="red" variant="light">
                            {error}
                        </Alert>
                    )}
                    <PasswordInput
                        label="Neues Passwort"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                    />
                    <PasswordInput
                        label="Passwort bestätigen"
                        value={passwordConfirm}
                        onChange={(e) => setPasswordConfirm(e.target.value)}
                        required
                    />
                    <Button type="submit" loading={setUserPassword.isPending} fullWidth mt="xs">
                        Passwort setzen
                    </Button>
                </Stack>
            </form>
        </Modal>
    );
}
