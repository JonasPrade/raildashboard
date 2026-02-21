import { type FormEvent, useState } from "react";
import { Alert, Button, Modal, PasswordInput, Select, Stack, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useCreateUser } from "../../shared/api/queries";

type Props = {
    opened: boolean;
    onClose: () => void;
};

const ROLE_OPTIONS = [
    { value: "viewer", label: "Viewer – nur lesen" },
    { value: "editor", label: "Editor – lesen & bearbeiten" },
    { value: "admin", label: "Admin – voller Zugriff" },
];

export function CreateUserModal({ opened, onClose }: Props) {
    const [username, setUsername] = useState("");
    const [role, setRole] = useState<string>("viewer");
    const [password, setPassword] = useState("");
    const [passwordConfirm, setPasswordConfirm] = useState("");
    const [error, setError] = useState<string | null>(null);

    const createUser = useCreateUser();

    const reset = () => {
        setUsername("");
        setRole("viewer");
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
            await createUser.mutateAsync({ username, password, role });
            notifications.show({
                color: "green",
                title: "Nutzer angelegt",
                message: `Nutzer „${username}" wurde erfolgreich erstellt.`,
            });
            reset();
            onClose();
        } catch {
            setError("Nutzer konnte nicht angelegt werden. Benutzername bereits vergeben?");
        }
    };

    return (
        <Modal opened={opened} onClose={handleClose} title="Neuen Nutzer anlegen" size="sm">
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
                        minLength={3}
                        maxLength={50}
                        required
                    />
                    <Select
                        label="Rolle"
                        data={ROLE_OPTIONS}
                        value={role}
                        onChange={(v) => setRole(v ?? "viewer")}
                        allowDeselect={false}
                        required
                    />
                    <PasswordInput
                        label="Passwort"
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
                    <Button type="submit" loading={createUser.isPending} fullWidth mt="xs">
                        Nutzer anlegen
                    </Button>
                </Stack>
            </form>
        </Modal>
    );
}
